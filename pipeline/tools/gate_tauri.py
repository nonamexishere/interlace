#!/usr/bin/env python3
"""UI0: unpublished tauri shell, macOS deny exception, CSP, no network entitlement.

#111: person timeline must be chat bubbles (from_me right / else left), not a log.
#112: UTC calendar-day headings (2024-03-15) when sent_at's day changes.
#113: open at latest (scroll after layout); older above; Load older at the top; prepend without jump;
#     last bubble sits above the “Bodies are text only” chrome (list bottom pad);
#     clear tlLoading before the open-person scroll; nested rAF so wrap has happened.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root, run  # noqa: E402

# IPC-only connect-src (no general http/https). 'none' blanks the .app (#107).
CSP = (
    "default-src 'self'; img-src 'self' asset: data: cas:; media-src 'self' cas: data:; "
    "style-src 'self' 'unsafe-inline'; "
    "connect-src ipc: http://ipc.localhost https://ipc.localhost; "
    "frame-src 'none'; font-src 'self'"
)

# #111 — person timeline is a chat (me right / them left), not a metadata log.
_FROM_ME_LAYOUT = re.compile(
    r"(data-from-me\s*=\s*\{(?:\w+\.)?row\.from_me\}"
    r"|class:[A-Za-z0-9_-]+\s*=\s*\{!?(?:\w+\.)?row\.from_me\}"
    r"|class=\{[^}]*row\.from_me[^}]*\})",
)
_ALIGN_RIGHT = (
    "ml-auto",
    "justify-end",
    "self-end",
    "items-end",
    "margin-left: auto",
    "margin-inline-start: auto",
    "justify-content: flex-end",
    "justify-content: end",
    "align-self: flex-end",
    "align-self: end",
)
_ALIGN_LEFT = (
    "mr-auto",
    "justify-start",
    "self-start",
    "items-start",
    "margin-right: auto",
    "margin-inline-end: auto",
    "justify-content: flex-start",
    "justify-content: start",
    "align-self: flex-start",
    "align-self: start",
)
_BUBBLE_ME_VARS = ("--bubble-me", "--color-bubble-me")
_BUBBLE_THEM_VARS = ("--bubble-them", "--color-bubble-them")
_BUBBLE_ME_USE = ("var(--bubble-me)", "var(--color-bubble-me)", "bg-bubble-me", "bubble-me")
_BUBBLE_THEM_USE = (
    "var(--bubble-them)",
    "var(--color-bubble-them)",
    "bg-bubble-them",
    "bubble-them",
)
_PRE_WRAP = re.compile(
    r"<([a-zA-Z][\w:-]*)([^>]*\bwhitespace-pre-wrap\b[^>]*)>(.*?)</\1>",
    re.S,
)

# #112 — day heading when the UTC calendar day of sent_at changes.
_DAY_HEADING = re.compile(
    r"(<h[2-4]\b"
    r"|role\s*=\s*[\"']heading[\"']"
    r"|day-heading"
    r"|day-separator"
    r"|day-sep\b"
    r"|data-day-heading)",
    re.I,
)
_PREV_DAY = re.compile(
    r"("
    r"timeline\s*\[\s*i\s*-\s*1\s*\]"
    r"|prev(?:ious)?Day"
    r"|lastDay"
    r"|dayChanged"
    r"|isNewDay"
    r")",
    re.I,
)
# RFC3339 UTC `2024-03-15T…Z` → calendar day is the `YYYY-MM-DD` prefix (or UTC getters).
_ISO_DAY = re.compile(
    r"("
    r"\.slice\s*\(\s*0\s*,\s*10\s*\)"
    r"|\.substring\s*\(\s*0\s*,\s*10\s*\)"
    r"|toISOString\s*\(\s*\)\s*\.\s*slice\s*\(\s*0\s*,\s*10\s*\)"
    r"|getUTCFullYear"
    r")",
)
_LOCAL_DAY = re.compile(
    r"("
    r"toLocaleDateString"
    r"|\.getFullYear\s*\("
    r"|\.getMonth\s*\("
    r"|\.getDate\s*\("
    r")",
)
_YESTERDAY = re.compile(r"\byesterday\b", re.I)
_TZ_PICKER = re.compile(
    r"(<select\b[^>]{0,120}(timezone|timeZone|tz)\b"
    r"|bind:value=\{[^}]*timeZone"
    r"|name=[\"']timezone[\"'])",
    re.I,
)
_HEADING_IF = re.compile(r"\{#if\s+([^}]+)\}")
_SENT_AT_GUARD = re.compile(
    r"("
    r"sent_at\s*\?\.|"
    r"sent_at\s*&&|"
    r"!\s*(?:row\.)?sent_at|"
    r"if\s*\(\s*!\s*(?:iso|day)\b"
    r")",
)

# #113 — newest page visible at the bottom; Load older at the top; prepend without jump.
# Dogfood: pad the list so the last bubble clears the text-only chrome; scroll after layout.
# Narrow pane: tlLoading = false before the open scroll; nested rAF so wrap has happened.
_LOAD_OLDER = re.compile(r"Load older")
_EACH_TIMELINE = re.compile(r"\{#each\s+(?:timeline|dayGroups)\b")
_CONCAT_BOTTOM = re.compile(r"timeline\.concat\s*\(\s*rows\s*\)")
_PREPEND = re.compile(
    r"("
    r"(?:rows|older|page|reversed|chrono)\s*\.concat\s*\(\s*timeline\s*\)"
    r"|\[\s*\.\.\.[^,\]]+\s*,\s*\.\.\.timeline\s*\]"
    r"|\.unshift\s*\("
    r"|timeline\s*=\s*append\s*\?\s*[^;\n]*\.concat\s*\(\s*timeline\s*\)"
    r")",
)
# Newest-first API page flipped for chat order (older above, newest at the bottom).
_OLDEST_FIRST = re.compile(
    r"("
    r"\.toReversed\s*\("
    r"|\.reverse\s*\("
    r"|oldestFirst"
    r"|\.sort\s*\([^)]*sent_at"
    r")",
    re.I,
)
# Whole newest-first store shown oldest-first (concat-then-reverse is ok).
_FULL_REVERSE = re.compile(
    r"("
    r"timeline\.toReversed\s*\("
    r"|timeline\.slice\s*\(\s*\)\s*\.reverse\s*\("
    r"|\[\s*\.\.\.timeline\s*\]\s*\.reverse\s*\("
    r"|\{#each\s+timeline\.toReversed"
    r")",
)
_SCROLL_TO_BOTTOM = re.compile(
    r"("
    r"scrollTop\s*=\s*[^;\n]*scrollHeight"
    r"|scrollTo\s*\(\s*\{[^}]*scrollHeight"
    r"|scrollIntoView\s*\("
    r")",
    re.I,
)
_SCROLL_PRESERVE = re.compile(
    r"("
    r"scrollTop\s*\+="
    r"|scrollHeight\s*-"
    r"|(?:prev(?:ious)?|old|saved|was)(?:Scroll)?(?:Height|Top)"
    r")",
    re.I,
)
# Enough pad that the last bubble is not under the text-only chrome (not .day-heading 0.25rem).
_TL_PAD_UTIL = re.compile(r"\bpb-(?:8|10|12)\b")
_TL_SPACER = re.compile(
    r"("
    r"\bpb-(?:8|10|12)\b"
    r"|padding-bottom\s*:"
    r"|\bh-(?:8|10|12)\b"
    r"|spacer"
    r")",
    re.I,
)
_SCROLL_AFTER_LAYOUT = re.compile(r"requestAnimationFrame\s*\(|scrollIntoView\s*\(")
_TL_LOADING_FALSE = re.compile(r"\btlLoading\s*=\s*false\b")
_RAF_CALL = re.compile(r"\b(?:window\.)?requestAnimationFrame\s*\(")
_SCROLL_HELPER_SKIP = frozenset(
    {
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "function",
        "return",
        "typeof",
        "new",
        "await",
        "void",
        "requestAnimationFrame",
        "setTimeout",
        "setInterval",
        "queueMicrotask",
        "tick",
        "Promise",
        "Math",
        "Number",
        "String",
        "Boolean",
        "parseInt",
        "document",
        "getElementById",
        "querySelector",
        "querySelectorAll",
        "scrollTo",
        "scrollIntoView",
        "showErr",
        "personShow",
        "personTimeline",
        "toReversed",
        "concat",
    }
)
_LAST_ROW = re.compile(
    r"("
    r"lastElementChild"
    r"|lastChild"
    r"|\.at\s*\(\s*-1\s*\)"
    r"|\[\s*length\s*-\s*1\s*\]"
    r"|length\s*-\s*1"
    r"|:last-child"
    r"|last(?:Row|Bubble|Msg|Message|Item)"
    r")",
    re.I,
)


def _web_sources(crate: Path) -> list[Path]:
    web = crate / "web"
    return [
        p
        for p in sorted(web.rglob("*"))
        if p.suffix in {".svelte", ".css"} and "node_modules" not in p.parts
    ]


def _web_logic(crate: Path) -> str:
    """Svelte + TS sources (helpers may live next to App.svelte)."""
    web = crate / "web"
    parts: list[str] = []
    for p in sorted(web.rglob("*")):
        if p.suffix in {".svelte", ".ts"} and "node_modules" not in p.parts:
            parts.append(p.read_text())
    return "\n".join(parts)


def _timeline_block(crate: Path) -> str:
    found: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte":
            continue
        text = p.read_text()
        i = 0
        while True:
            start = text.find("{#each timeline", i)
            if start < 0:
                start = text.find("{#each dayGroups", i)
            if start < 0:
                break
            end = text.find("{/each}", start)
            if end < 0:
                fail(f"#111: unclosed {{#each timeline}} in {p.relative_to(crate)}")
            found.append(text[start:end])
            i = end + len("{/each}")
    if not found:
        fail("#111: person timeline must {#each timeline} or {#each dayGroups} as chat rows")
    return "\n".join(found)


def _css_var(blob: str, names: tuple[str, ...]) -> str | None:
    for name in names:
        m = re.search(rf"{re.escape(name)}\s*:\s*([^;]+);", blob)
        if m:
            return m.group(1).strip()
    return None


def assert_chat_bubbles(crate: Path) -> None:
    """#111: from_me → right bubble; else left. Caption, not a log dump."""
    block = _timeline_block(crate)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))

    if not _FROM_ME_LAYOUT.search(block):
        fail(
            "#111: from_me must choose a right/left bubble "
            "(class or data-from-me), not a you/them log label"
        )
    # Utility classes must be on the timeline row. Colon tokens live in CSS.
    # "Else left" may be default flow; do not require a left utility. Do forbid
    # forcing the not-from_me branch to the right.
    css_right = tuple(t for t in _ALIGN_RIGHT if ":" in t)
    util_right = tuple(t for t in _ALIGN_RIGHT if ":" not in t)
    util_left = tuple(t for t in _ALIGN_LEFT if ":" not in t)
    me_right = any(t in block for t in util_right) or (
        ("bubble-me" in block or "data-from-me" in block) and any(t in blob for t in css_right)
    )
    if not me_right:
        fail("#111: from_me rows must sit on the right (bubble, not a log)")
    tern = re.search(
        r"row\.from_me\s*\?\s*['\"]([^'\"]*)['\"]\s*:\s*['\"]([^'\"]*)['\"]",
        block,
    )
    if tern:
        them_cls = tern.group(2)
        if any(t in them_cls for t in util_right) and not any(t in them_cls for t in util_left):
            fail("#111: rows that are not from_me must sit on the left")

    if re.search(r"\.join\(\s*[\"'] · [\"']\s*\)", block):
        fail("#111: date/platform must be a caption, not a dumped · field list")
    if "caption" not in block.lower() and "<time" not in block.lower():
        fail("#111: date/platform must be a caption (caption class or <time>), not a dump")
    if "row.platform" not in block:
        fail("#111: caption must still show platform")
    if not re.search(
        r"(utcTime|hh:?mm|slice\s*\(\s*11\s*,\s*16\s*\))",
        block + "\n" + blob,
        re.I,
    ):
        fail("#111: caption must show hour:minute, not the full ISO date again")
    if re.search(r"\{row\.sent_at\s*\|\|", block):
        fail("#111: do not dump the full sent_at ISO string in the bubble caption")

    pre = _PRE_WRAP.search(block)
    if not pre:
        fail("#111: timeline body must stay a whitespace-pre-wrap text node")
    attrs, inner = pre.group(2), pre.group(3)
    if re.search(r"\baria-hidden\b", attrs) or re.search(r"\bsr-only\b", attrs):
        fail("#111: screen reader must still get the visible message text")
    if "displayBody" not in inner and "body_text" not in inner:
        fail("#111: screen reader must still get the message text")
    if not (
        "overflow-wrap" in blob
        or "break-words" in block
        or "break-all" in block
        or "overflow-wrap" in block
    ):
        fail("#111: long tokens (URLs) must wrap inside the bubble")

    me = _css_var(blob, _BUBBLE_ME_VARS)
    them = _css_var(blob, _BUBBLE_THEM_VARS)
    if not me or not them:
        fail(
            "#111: distinct bubble colors via CSS variables "
            "(--bubble-me / --bubble-them or --color-bubble-*)"
        )
    if me == them:
        fail("#111: --bubble-me and --bubble-them must be distinct colors")
    if re.search(r"https?://", me) or re.search(r"https?://", them):
        fail("#111: bubble colors must not load images from the network")
    if not any(tok in blob for tok in _BUBBLE_ME_USE):
        fail("#111: --bubble-me must be applied to the me bubble")
    if not any(tok in blob for tok in _BUBBLE_THEM_USE):
        fail("#111: --bubble-them must be applied to the them bubble")
    if re.search(r"url\(\s*['\"]?https?://", blob, re.I):
        fail("#111: no network images in the person timeline chrome")


def assert_day_separators(crate: Path) -> None:
    """#112: UTC day heading (DD/MM/YYYY) when sent_at's day changes; sticky."""
    block = _timeline_block(crate)
    app = (crate / "web" / "App.svelte").read_text()
    logic = _web_logic(crate)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    if not _DAY_HEADING.search(block):
        fail(
            "#112: person timeline must insert a day heading "
            "(h2–h4, role=heading, or day-heading) when the UTC calendar day changes"
        )
    # Heading is a timeline separator, not a label inside the #111 bubble.
    outside_bubbles = block
    for btn in re.findall(r"<button\b.*?</button>", block, re.S):
        outside_bubbles = outside_bubbles.replace(btn, "", 1)
    if not _DAY_HEADING.search(outside_bubbles):
        fail(
            "#112: day heading must sit on the timeline when the UTC day changes, "
            "not inside a chat bubble"
        )

    if_conds = _HEADING_IF.findall(block)
    if not if_conds:
        fail(
            "#112: day heading must be conditional "
            "(when sent_at's UTC calendar day changes; no heading if sent_at is missing)"
        )
    if not any(re.search(r"sent_at|utcDay|dayKey|calendarDay|isoDay|\bday\b", c, re.I) for c in if_conds):
        fail(
            "#112: day heading {#if} must key off the UTC calendar day of sent_at "
            "(do not invent a heading for a row with no date)"
        )

    if not _PREV_DAY.search(block) and not _PREV_DAY.search(app):
        fail(
            "#112: must compare the current row's UTC calendar day to the previous "
            "row (timeline[i - 1]) so a multi-year DM gets day/month/year separators"
        )

    if not _ISO_DAY.search(app) and not _ISO_DAY.search(block) and not _ISO_DAY.search(logic):
        fail(
            "#112: compare days on the UTC ISO date prefix of sent_at "
            "(slice(0, 10) or UTC getters / toISOString)"
        )
    if not re.search(
        r"("
        r"utcDayLabel"
        r"|split\s*\(\s*[\"']-[\"']\s*\)"
        r"|/\$\{"
        r"|day\s*/\s*month"
        r"|padStart"
        r")",
        app + "\n" + logic,
        re.I,
    ):
        fail("#112: day headings must display day/month/year (15/03/2024), not YYYY-MM-DD")

    chrome = app + "\n" + block
    if _LOCAL_DAY.search(chrome) and not re.search(r"getUTC(?:FullYear|Month|Date)", chrome):
        fail("#112: days are UTC; do not format archive-local or the host timezone")

    if _YESTERDAY.search(block) or _YESTERDAY.search(app):
        fail("#112: day headings must be day/month/year, not relative “yesterday”")

    if _TZ_PICKER.search(app) or _TZ_PICKER.search(block):
        fail("#112: no timezone picker")

    # Caption may use `row.sent_at || "no date"` — that is not a day heading.
    if re.search(r"<h[2-4]\b[^>]*>[^<{]*no date", block, re.I):
        fail("#112: do not invent a day heading for a row with no date")

    if not _SENT_AT_GUARD.search(block) and not _SENT_AT_GUARD.search(app):
        fail(
            "#112: missing sent_at must not crash; guard before reading a calendar day "
            "(do not invent a heading for a row with no date)"
        )
    day_src = app + "\n" + block
    if re.search(r"(?:row\.)?sent_at\.slice\s*\(", day_src) and not re.search(
        r"sent_at\s*\?\.", day_src
    ):
        if not re.search(r"if\s*\(\s*!\s*(?:row\.)?sent_at", day_src):
            fail("#112: missing sent_at must not crash; guard before slicing")

    markup = app
    script_end = app.rfind("</script>")
    if script_end >= 0:
        markup = app[script_end:]
    if "UTC" not in markup and "UTC" not in block:
        fail("#112: say UTC in the UI copy (timeline days are UTC)")

    if "UTC" not in dtxt:
        fail("#112: docs/user/app.md must say timeline days are UTC")
    if not re.search(r"(day heading|day separator)", dtxt, re.I):
        fail("#112: docs/user/app.md must describe UTC day headings")
    if not re.search(r"(day/month/year|DD/MM/YYYY|15/03/2024)", dtxt, re.I):
        fail("#112: docs/user/app.md must say day headings are day/month/year")

    sticky_src = "\n".join(p.read_text() for p in _web_sources(crate))
    if not re.search(r"(position\s*:\s*sticky|\bsticky\b)", sticky_src, re.I):
        fail("#112: day heading must stick to the top of the message list while scrolling")


def _matching_each_end(markup: str, each_start: int) -> int:
    depth = 0
    for m in re.finditer(r"\{#each\b|\{/each\}", markup[each_start:]):
        if m.group(0).startswith("{#each"):
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return each_start + m.end()
    return -1


def _person_timeline_open_tag(src: str) -> str:
    m = re.search(
        r"<[^>]*\bid=(?:[\"']person-timeline[\"']|\{[\"']person-timeline[\"']\})[^>]*>",
        src,
        re.I | re.S,
    )
    return m.group(0) if m else ""


def _has_nonzero_padding_bottom(blob: str) -> bool:
    for m in re.finditer(r"padding-bottom\s*:\s*([^;}\n]+)", blob, re.I):
        val = m.group(1).strip().lower()
        if val not in {"0", "0px", "0rem", "0em", "0%", "none"}:
            return True
    return False


def _timeline_css_pad_blocks(blob: str) -> list[str]:
    blocks: list[str] = []
    for rx in (
        r"#person-timeline(?:\s+(?:ol|ul))?\s*\{([^}]+)\}",
        r"\[id=[\"']person-timeline[\"']\](?:\s+(?:ol|ul))?\s*\{([^}]+)\}",
    ):
        blocks.extend(m.group(1) for m in re.finditer(rx, blob, re.I))
    return blocks


def _timeline_has_bottom_pad(crate: Path, app: str) -> bool:
    """True if #person-timeline / the message list pads above the text-only chrome."""
    tag = _person_timeline_open_tag(app)
    if tag and (_TL_PAD_UTIL.search(tag) or _has_nonzero_padding_bottom(tag)):
        return True
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    for block in _timeline_css_pad_blocks(blob):
        if _TL_PAD_UTIL.search(block) or _has_nonzero_padding_bottom(block):
            return True
    for p in _web_sources(crate):
        if p.suffix != ".svelte":
            continue
        text = p.read_text()
        script_end = text.rfind("</script>")
        markup = text[script_end:] if script_end >= 0 else text
        for each in _EACH_TIMELINE.finditer(markup):
            before = markup[: each.start()]
            ol = None
            for m in re.finditer(r"<ol\b[^>]*>", before, re.I | re.S):
                ol = m
            if ol and (
                _TL_PAD_UTIL.search(ol.group(0)) or _has_nonzero_padding_bottom(ol.group(0))
            ):
                return True
            end = _matching_each_end(markup, each.start())
            if end < 0:
                continue
            after = markup[end : end + 900]
            cut = after.lower().find("</scrollarea>")
            if cut < 0:
                cut = after.find("Bodies are text")
            if cut >= 0:
                after = after[:cut]
            if _TL_SPACER.search(after):
                return True
    return False


def _scrolls_after_layout(app: str, logic: str) -> bool:
    """True if open-person scroll waits for layout (rAF and/or last-row scrollIntoView)."""
    src = app + "\n" + logic
    for m in _SCROLL_AFTER_LAYOUT.finditer(src):
        window = src[max(0, m.start() - 500) : m.end() + 500]
        if m.group(0).startswith("requestAnimationFrame"):
            if re.search(r"scrollTop|scrollTo\s*\(|scrollIntoView", window):
                return True
        elif _LAST_ROW.search(window):
            return True
    return False


def _js_next(src: str, i: int) -> int:
    """Advance past a JS comment or string starting at i; else return i."""
    n = len(src)
    if i >= n:
        return i
    if src.startswith("//", i):
        nl = src.find("\n", i)
        return n if nl < 0 else nl + 1
    if src.startswith("/*", i):
        end = src.find("*/", i + 2)
        return n if end < 0 else end + 2
    q = src[i]
    if q in "'\"`":
        j = i + 1
        while j < n:
            if src[j] == "\\":
                j += 2
                continue
            if src[j] == q:
                return j + 1
            j += 1
        return n
    return i


def _without_comments(src: str) -> str:
    out: list[str] = []
    i = 0
    n = len(src)
    while i < n:
        if src.startswith("//", i) or src.startswith("/*", i):
            i = _js_next(src, i)
            continue
        nxt = _js_next(src, i)
        if nxt != i:
            out.append(src[i:nxt])
            i = nxt
            continue
        out.append(src[i])
        i += 1
    return "".join(out)


def _match_closer(src: str, open_idx: int) -> int:
    opener = src[open_idx]
    closer = ")" if opener == "(" else "}"
    depth = 0
    i = open_idx
    n = len(src)
    while i < n:
        nxt = _js_next(src, i)
        if nxt != i:
            i = nxt
            continue
        c = src[i]
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _call_arg(src: str, open_paren: int) -> str:
    close = _match_closer(src, open_paren)
    if close < 0:
        return ""
    return src[open_paren + 1 : close]


def _function_body(src: str, name: str) -> str:
    rx = re.compile(
        rf"(?:async\s+)?function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{"
        rf"|(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?:async\s*)?"
        rf"(?:function\s*)?\([^)]*\)\s*(?:=>\s*)?\{{"
    )
    m = rx.search(src)
    if not m:
        return ""
    open_b = m.end() - 1
    close_b = _match_closer(src, open_b)
    if close_b < 0:
        return src[open_b + 1 :]
    return src[open_b + 1 : close_b]


def _contains_open_latest_scroll(blob: str, whole: str, seen: set[str] | None = None) -> bool:
    """True if blob (or a named rAF callback it references) scrolls to latest."""
    if _SCROLL_TO_BOTTOM.search(blob):
        return True
    found = seen if seen is not None else set()
    for m in _RAF_CALL.finditer(blob):
        arg = _call_arg(blob, m.end() - 1)
        if _SCROLL_TO_BOTTOM.search(arg):
            return True
        ident = re.fullmatch(r"\s*([A-Za-z_]\w*)\s*", arg)
        if ident and ident.group(1) not in found:
            found.add(ident.group(1))
            body = _function_body(whole, ident.group(1))
            if body and _contains_open_latest_scroll(body, whole, found):
                return True
    return False


def _open_person_scroll_anchor(src: str, whole: str) -> int | None:
    """Index of the outer open-person rAF / scrollTop / scrollIntoView (not append +=)."""
    for m in _RAF_CALL.finditer(src):
        arg = _call_arg(src, m.end() - 1)
        if arg and _contains_open_latest_scroll(arg, whole):
            return m.start()
    m = _SCROLL_TO_BOTTOM.search(src)
    return m.start() if m else None


def _clears_loading_before_open_scroll(app: str, logic: str) -> bool:
    """tlLoading = false must appear before the open-person rAF/scroll, not only in finally after."""
    whole = app + "\n" + logic
    fn = _function_body(whole, "selectPerson") or whole
    cleaned = _without_comments(fn)
    whole_c = _without_comments(whole)
    anchor = _open_person_scroll_anchor(cleaned, whole_c)
    if anchor is not None:
        return bool(_TL_LOADING_FALSE.search(cleaned[:anchor]))
    m = _TL_LOADING_FALSE.search(cleaned)
    if not m:
        return False
    after = cleaned[m.end() :]
    for call in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", after):
        name = call.group(1)
        if name in _SCROLL_HELPER_SKIP:
            continue
        body = _function_body(whole_c, name)
        if body and _open_person_scroll_anchor(_without_comments(body), whole_c) is not None:
            return True
    return False


def _nested_raf_around_open_scroll(app: str, logic: str) -> bool:
    """True if a requestAnimationFrame callback itself schedules another rAF that scrolls to latest."""
    whole = _without_comments(app + "\n" + logic)
    for m in _RAF_CALL.finditer(whole):
        arg = _call_arg(whole, m.end() - 1)
        if not arg or not _RAF_CALL.search(arg):
            continue
        if _contains_open_latest_scroll(arg, whole):
            return True
    return False


def assert_timeline_latest(crate: Path) -> None:
    """#113: newest at bottom; Load older at top; prepend without jump; pad / scroll after layout.

    Narrow-pane dogfood: clear tlLoading before the open-person scroll; nested rAF for wrap.
    """
    app = (crate / "web" / "App.svelte").read_text()
    logic = _web_logic(crate)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    found_each = False
    found_load = False
    for p in _web_sources(crate):
        if p.suffix != ".svelte":
            continue
        text = p.read_text()
        script_end = text.rfind("</script>")
        markup = text[script_end:] if script_end >= 0 else text
        if _LOAD_OLDER.search(markup):
            found_load = True
        each = _EACH_TIMELINE.search(markup)
        if not each:
            continue
        found_each = True
        if not _LOAD_OLDER.search(markup):
            fail("#113: Load older button is required (intersection observer is optional)")
        if markup.find("Load older") > each.start():
            fail("#113: Load older must sit at the top of the message list, not under it")
        # A leftover control under the list is the current bug even if one also sits above.
        after_each = markup.find("{/each}", each.start())
        if after_each >= 0 and "Load older" in markup[after_each:]:
            fail("#113: Load older must sit at the top of the message list, not under it")
    if not found_each:
        fail("#113: person timeline must still {#each timeline} or {#each dayGroups}")
    if not found_load:
        fail("#113: Load older button is required (intersection observer is optional)")

    concat_bottom = bool(_CONCAT_BOTTOM.search(logic))
    prepended = bool(_PREPEND.search(logic))
    full_reverse = bool(_FULL_REVERSE.search(logic))
    oldest_first = bool(_OLDEST_FIRST.search(logic))
    if concat_bottom and not full_reverse:
        fail("#113: older pages must be prepended, not concatenated at the bottom")
    if not (prepended or full_reverse or oldest_first):
        fail(
            "#113: visual order is a chat — older above, newest at the bottom "
            "(reverse or sort the newest-first page; prepend older rows)"
        )

    # Initial fetch is already the newest page (`before` unset). Latest must be visible.
    if not _SCROLL_TO_BOTTOM.search(logic) and not _SCROLL_TO_BOTTOM.search(app):
        fail(
            "#113: opening a person must scroll to the bottom "
            "so the latest messages are visible"
        )

    if not _SCROLL_PRESERVE.search(logic) and not _SCROLL_PRESERVE.search(app):
        fail(
            "#113: preserve scroll position when prepending older rows "
            "(do not jump the viewport to 0)"
        )

    # Last bubble must sit above the “Bodies are text only” chrome, not under it.
    if not _timeline_has_bottom_pad(crate, app):
        fail(
            "#113: last bubble must sit above the “Bodies are text only” chrome — "
            "pad the bottom of the message list / #person-timeline "
            "(pb-8, pb-10, pb-12, padding-bottom, or a spacer after {/each})"
        )

    # tick then scrollTop = scrollHeight runs before day groups / images settle.
    if not _scrolls_after_layout(app, logic):
        fail(
            "#113: opening a person must scroll to the newest message after layout "
            "(requestAnimationFrame and/or scrollIntoView on the last row), "
            "not only await tick() then scrollTop = scrollHeight"
        )

    # Loading line still in the pane (tlLoading true) makes one rAF land short on a wrap.
    if not _clears_loading_before_open_scroll(app, logic):
        fail(
            "#113: clear tlLoading before the open-person scroll to latest "
            "(tlLoading = false must run before that scrollTop / scrollIntoView / "
            "requestAnimationFrame, not only in finally after it — "
            "the loading line must leave the pane first)"
        )
    if not _nested_raf_around_open_scroll(app, logic):
        fail(
            "#113: opening a person must wait for wrap on a short pane "
            "(nested requestAnimationFrame around the open-person scroll to latest; "
            "a single rAF while tlLoading is still true is not enough)"
        )

    if not re.search(
        r"("
        r"opens? at (the )?(latest|newest)"
        r"|(latest|newest) messages"
        r"|scroll(?:s|ed)? to the bottom"
        r")",
        dtxt,
        re.I,
    ):
        fail("#113: docs/user/app.md must say the person timeline opens at the latest messages")
    if not re.search(
        r"Load older.{0,80}(top|above)|(top|above).{0,80}Load older",
        dtxt,
        re.I | re.S,
    ):
        fail("#113: docs/user/app.md must say Load older is at the top")
    if not re.search(
        r"("
        r"does not jump"
        r"|don.?t jump"
        r"|without jump"
        r"|keep(?:s|ing)? (the )?(scroll|viewport|place)"
        r"|preserve(?:s|d)? scroll"
        r"|scroll position"
        r")",
        dtxt,
        re.I,
    ):
        fail("#113: docs/user/app.md must say loading older does not jump the viewport")


def main() -> None:
    root = repo_root()
    crate = root / "crates" / "interlace-tauri"
    toml = (crate / "Cargo.toml").read_text()
    if "publish = false" not in toml:
        fail("interlace-tauri must set publish = false")
    for plug in ("tauri-plugin-http", "tauri-plugin-updater"):
        if plug in toml:
            fail(f"{plug} must not be a dependency")

    ws = (root / "Cargo.toml").read_text()
    if '"crates/interlace-tauri"' not in ws:
        fail("interlace-tauri must be a workspace member")
    dm = ws[ws.find("default-members") : ws.find("[workspace.package]")]
    if "interlace-tauri" in dm:
        fail("interlace-tauri must not be a default-member")

    conf = (crate / "tauri.conf.json").read_text()
    if CSP not in conf:
        fail(f"tauri.conf.json missing exact CSP:\n{CSP}")
    import json

    cfg = json.loads(conf)
    bundle = cfg.get("bundle") or {}
    if bundle.get("active") is not True:
        fail("bundle.active must be true (UI8 unsigned .app/.dmg)")
    targets = bundle.get("targets") or []
    if "app" not in targets or "dmg" not in targets:
        fail("bundle.targets must include app and dmg")
    if bundle.get("createUpdaterArtifacts"):
        fail("createUpdaterArtifacts must stay false (no updater)")
    mac = bundle.get("macOS") or {}
    if mac.get("entitlements") != "Interlace.entitlements":
        fail("bundle.macOS.entitlements must be Interlace.entitlements")
    if mac.get("signingIdentity") != "-":
        fail('signingIdentity must be "-" (ad-hoc / unsigned)')
    icons = bundle.get("icon") or []
    if "icons/icon.icns" not in icons:
        fail("bundle.icon must include icons/icon.icns")
    if not (crate / "icons" / "icon.icns").is_file():
        fail("icons/icon.icns missing")

    ent = (crate / "Interlace.entitlements").read_text()
    if "com.apple.security.app-sandbox" not in ent:
        fail("sandbox entitlement required")
    if "network.server" in ent:
        fail("entitlements must omit network.server")
    # WKWebView will not paint tauri://localhost in a sandbox without this.
    # Measured 2026-08-10: sandbox-only and sandbox+JIT = blank .app;
    # sandbox+network.client shows the UI. Still no HTTP client crate.
    if "network.client" not in ent:
        fail("entitlements must include network.client (WKWebView local UI)")
    if "allow-jit" not in ent:
        fail("entitlements must include cs.allow-jit for WKWebView")

    app = (crate / "web" / "App.svelte").read_text()
    if "phones home" not in app or "HTTP" not in app:
        fail("Svelte UI must state no phone-home and no HTTP client")
    if "confirm(" in app:
        fail("App.svelte must not use window.confirm after UI primitives")
    for rel in (
        "web/lib/components/ui/button/button.svelte",
        "web/lib/components/ui/input/input.svelte",
        "web/lib/components/ui/dialog/dialog.svelte",
        "web/lib/components/ui/scroll-area/scroll-area.svelte",
    ):
        if not (crate / rel).is_file():
            fail(f"missing owned primitive {rel}")
    empty = crate / "web" / "lib" / "EmptyState.svelte"
    if not empty.is_file():
        fail("EmptyState.svelte required for UI empty/loading copy")
    if "Opening last archive" not in app:
        fail("boot screen must say Opening last archive (no blank flash)")
    doctor = crate / "web" / "lib" / "DoctorPane.svelte"
    if not doctor.is_file():
        fail("DoctorPane.svelte required for UI7")
    dtxt = doctor.read_text()
    if "Not encrypted at rest" not in dtxt or "FileVault" not in dtxt:
        fail("Doctor pane must say not encrypted at rest; FileVault is encryption")
    if "database is encrypted" in dtxt or "your data is encrypted" in dtxt.lower():
        fail("UI must not claim the DB is encrypted at rest")
    if "doctorRun" not in dtxt:
        fail("Doctor pane must call doctorRun (not only CLI copy)")
    if "data-cloud-warning" not in app:
        fail("App.svelte must show a persistent cloud-path banner")
    if "UI7 will run doctor" in app:
        fail("placeholder UI7 CLI-only copy must be gone")
    assert_chat_bubbles(crate)
    assert_day_separators(crate)
    assert_timeline_latest(crate)
    cas = (crate / "web" / "lib" / "CasAttach.svelte").read_text()
    if "casDataUrl" not in cas:
        fail("CAS viewer must load bytes via casDataUrl (data: URL; Vite cannot fetch cas://)")
    if "http://" in cas or "https://" in cas:
        fail("CAS viewer must not use remote URLs")
    if "protocol-asset" in toml or "dangerousRemoteDomainIpcAccess" in conf:
        fail("must not enable remote asset IPC")
    if (crate / "ui" / "app.js").is_file():
        fail("vanilla ui/app.js must be gone after UI-FE")
    if not (crate / "package-lock.json").is_file():
        fail("package-lock.json must be committed")
    pkg = (crate / "package.json").read_text()
    if "bits-ui" not in pkg:
        fail("bits-ui must be a local dependency (no CDN theme)")
    vite = (crate / "vite.config.ts").read_text()
    if 'base: "./"' not in vite and "base: './'" not in vite:
        fail("vite.config.ts must set base: './' so the .app loads JS")
    if "tauri:build" not in pkg:
        fail("package.json must expose tauri:build")

    wf = root / ".github" / "workflows" / "app-release.yml"
    if not wf.is_file():
        fail("app-release.yml missing (UI8 app-v* tags)")
    wtxt = wf.read_text()
    if "app-v*" not in wtxt:
        fail("app-release.yml must trigger on app-v* tags only")
    if "cargo publish" in wtxt or "CARGO_REGISTRY_TOKEN" in wtxt:
        fail("app-release.yml must not publish crates (D3)")
    if "tauri-plugin-updater" in wtxt or "plugin-updater" in wtxt:
        fail("app-release.yml must not install an updater")
    pub = (root / ".github" / "workflows" / "publish.yml").read_text()
    if "tauri:build" in pub or "bundle/dmg" in pub or "Interlace.app" in pub:
        fail("publish.yml is crates.io v* only; do not attach the .dmg there")

    npm = run(
        ["npm", "ci"],
        cwd=crate,
        check=False,
    )
    if npm.returncode != 0:
        fail(npm.stderr or npm.stdout)
    built = run(["npm", "run", "build"], cwd=crate, check=False)
    if built.returncode != 0:
        fail(built.stderr or built.stdout)
    dist = (crate / "dist" / "index.html").read_text()
    if "cdn." in dist or "unpkg.com" in dist:
        fail("production bundle must not load a CDN")
    if 'src="/assets/' in dist or "href=\"/assets/" in dist:
        fail("dist/index.html must use relative asset URLs (vite base ./); absolute /assets blanks the .app")
    if "connect-src 'none'" in conf:
        fail("connect-src 'none' blocks Tauri IPC and blanks the bundled .app")

    chk = run(["cargo", "check", "-p", "interlace-tauri"], cwd=root, check=False)
    if chk.returncode != 0:
        fail(chk.stderr or chk.stdout)

    clip = run(
        ["cargo", "clippy", "-p", "interlace-tauri", "--", "-D", "warnings"],
        cwd=root,
        check=False,
    )
    if clip.returncode != 0:
        fail(clip.stderr or clip.stdout)

    for kind in ("bans", "licenses"):
        d = run(
            [
                "cargo",
                "deny",
                "--manifest-path",
                str(crate / "Cargo.toml"),
                "check",
                kind,
            ],
            cwd=root,
            check=False,
        )
        if d.returncode != 0:
            fail(f"cargo deny check {kind} interlace-tauri failed\n{d.stdout}\n{d.stderr}")

    for name in ("reqwest", "hyper"):
        t = run(
            [
                "cargo",
                "tree",
                "-p",
                "interlace-tauri",
                "-i",
                name,
                "--target",
                "aarch64-apple-darwin",
            ],
            cwd=root,
            check=False,
        )
        out = (t.stdout or "") + (t.stderr or "")
        if "warning: nothing to print" not in out and f"{name} v" in out:
            fail(f"{name} is in the macOS tauri graph\n{out}")

    print("gate_tauri ok")


if __name__ == "__main__":
    main()
