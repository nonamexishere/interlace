#!/usr/bin/env python3
"""UI0: unpublished tauri shell, macOS deny exception, CSP, no network entitlement.

#111: person timeline must be chat bubbles (from_me right / else left), not a log.
#112: UTC calendar-day headings (2024-03-15) when sent_at's day changes.
#113: open at latest (scroll after layout); older above; Load older at the top; prepend without jump;
#     last bubble sits above the “Bodies are text only” chrome (list bottom pad);
#     clear tlLoading before the open-person scroll; nested rAF so wrap has happened.
#114: after selecting a person, list conversations (dm / group / email_thread) with
#     title + platform + last_at; default All (D18 merged); pick one to filter the
#     timeline; groups still need include-groups in the list and in All; no raw ids.
#     Identity chrome (Merge, include groups, unlink) is hidden until the person
#     name is clicked. Conversation switcher is a compact header control, not a
#     second always-expanded list above the bubbles. People sidebar stays.
#     All / the open panel must stack above sticky .day-heading (higher z-index
#     than the heading, plus a background so the date cannot show through).
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

# #114 — conversation switcher (title + platform + last_at); default All; no raw ids.
_CONV_EACH = re.compile(
    r"\{#each\s+"
    r"(?:(?:[\w.$]+)?conversations|convos|personConversations|"
    r"conversationList|convList|visibleConversations|filteredConversations)\b"
)
_CONV_SWITCHER_HOOK = re.compile(
    r"(data-conversation-switcher|id=[\"']conversation-switcher[\"'])",
    re.I,
)
_CONV_SELECT = re.compile(
    r"<select\b[^>]{0,400}(conversation|convo)",
    re.I | re.S,
)
_CONV_STATE_DEFAULT_ALL = re.compile(
    r"(?:selectedConversation(?:Id)?|conversationId|conversationFilter|"
    r"selectedConvo|activeConversation|pickedConversation)"
    r"\s*=\s*\$state\s*(?:<[^>]*>)?\s*\(\s*(?:null|undefined|[\"']all[\"'])",
    re.I,
)
_CONV_RESET_ALL = re.compile(
    r"(?:selectedConversation(?:Id)?|conversationId|conversationFilter|"
    r"selectedConvo|activeConversation|pickedConversation)"
    r"\s*=\s*(?:null|undefined|[\"']all[\"'])",
    re.I,
)
_CONV_ALL_LABEL = re.compile(r">\s*All\s*<|[\"']All[\"']")
_CONV_TITLE = re.compile(r"(conversation_title|\.title\b|\{[^}]{0,80}\btitle\b[^}]{0,40}\})")
_CONV_PLATFORM = re.compile(r"\bplatform\b")
_CONV_LAST_AT = re.compile(r"\b(?:last_at|lastAt|last_activity_at)\b")
_CONV_ID_TEXT = re.compile(
    r"\{[^}]{0,80}(?:conversation_id|\.id|person_id|personId|selectedId)[^}]{0,40}\}"
)
_CONV_ID_FALLBACK = re.compile(
    r"(?:conversation_title|\.title|title)\s*\|\|\s*[^\n;]{0,80}"
    r"(?:conversation_id|\.id|person_id|personId)\b"
)
_CONV_PICK = re.compile(
    r"("
    r"(?:onclick|onchange|on:click|on:change)\s*=\s*\{[^}]{0,200}"
    r"(?:conversation|convo|Conversation|Convo)"
    r"|bind:value=\{[^}]{0,80}(?:conversation|convo|Conversation|Convo)"
    r")",
    re.I,
)
_CONV_CREATE = re.compile(r"Create conversation|New conversation", re.I)
_CONV_MUTE = re.compile(r">\s*Mute\s*<")
_CONV_PIN = re.compile(r">\s*(?:Un)?[Pp]in\s*<")
_PERSON_TIMELINE_CALL = re.compile(r"\bpersonTimeline\s*\(")
_INCLUDE_GROUPS_LABEL = re.compile(r"include groups", re.I)

# #114 dogfood — identity chrome + compact switcher (chat must not sit under admin).
# All / the open panel stack above sticky .day-heading (z-index + background).
_MERGE_CTRL = re.compile(r">\s*Merge(?:…|\.{3})?\s*<")
_UNLINK_CTRL = re.compile(r">\s*unlink\s*<", re.I)
_GROUPS_BIND = re.compile(r"bind:checked=\{includeGroups\}")
_GROUPS_LABEL_CTRL = re.compile(
    r"<label\b[^>]*>[\s\S]{0,240}include groups[\s\S]{0,80}</label>",
    re.I,
)
_CLICK_ATTR = re.compile(r"(?:on:click|onclick)(?:\|\w+)*\s*=\s*\{", re.I)
_TMPL_TOKEN = re.compile(
    r"\{#if\s+([^}]+)\}"
    r"|\{:else\s+if\s+([^}]+)\}"
    r"|\{:else\}"
    r"|\{/if\}"
    r"|\{#each\s+([^}]+)\}"
    r"|\{/each\}"
    r"|\{#await\b[^}]*\}"
    r"|\{/await\}"
    r"|\{#key\b[^}]*\}"
    r"|\{/key\}"
    r"|<((?:[A-Za-z][\w]*\.)?(?:Select|Popover|DropdownMenu|Dropdown|Combobox|Menu)"
    r"(?:\.\w+)?|details|select)\b([^>]*)>"
    r"|</((?:[A-Za-z][\w]*\.)?(?:Select|Popover|DropdownMenu|Dropdown|Combobox|Menu)"
    r"(?:\.\w+)?|details|select)\s*>",
    re.I,
)
_HIDDEN_BIND = re.compile(
    r"(?:\bhidden|class:hidden|aria-hidden)\s*=\s*\{",
    re.I,
)
_TITLE_SKIP_ASSIGN = frozenset(
    {
        "selectedId",
        "selectedConversationId",
        "view",
        "err",
        "mergeOpen",
        "mergeQuery",
        "mergeKeepId",
        "mergeKeepName",
        "allowSelf",
        "filter",
        "tlIndex",
        "tlLoading",
        "setup",
        "booting",
        "opening",
    }
)
_PERSON_PANE_SKIP = frozenset(
    {
        "SearchPane.svelte",
        "ReviewPane.svelte",
        "ImportPane.svelte",
        "DoctorPane.svelte",
        "ConfirmDialog.svelte",
        "EmptyState.svelte",
        "CasAttach.svelte",
    }
)
# Sticky .day-heading is z-index 10; All / the open panel must sit above it.
_TW_Z_INDEX = re.compile(r"(?<![\w-])z-(?:\[(\d+)\]|(\d+))(?![\w-])")
_CSS_Z_INDEX = re.compile(r"z-index\s*:\s*(\d+)", re.I)
_CLASS_Z_DIR = re.compile(r"\bclass:z-(\d+)\b")
_TW_STACK_BG = re.compile(
    r"(?<![\w-])((?:(?:group-)?(?:hover|focus|active|focus-visible):)*)"
    r"(bg-(?:background|card|popover|muted|white|black|primary|secondary|accent)"
    r"|bg-\[var\(--color-(?:background|card|popover|muted)\)\])"
    r"(?:/(\d+))?(?![\w-])",
    re.I,
)
_CSS_STACK_BG = re.compile(
    r"background(?:-color)?\s*:\s*(?!none\b|transparent\b)(\S)",
    re.I,
)
_VOID_HTML = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
_TIMELINE_INNER = re.compile(
    r"(id=[\"']person-timeline[\"']|day-heading|\{#each\s+(?:timeline|dayGroups)\b)",
    re.I,
)
_DAY_HEADING_CSS = re.compile(
    r"(?:\.day-heading\b|\.day-separator\b|\.day-sep\b|\[data-day-heading\])[^{]*\{([^}]+)\}",
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


def _without_calls(src: str, rx: re.Pattern[str]) -> str:
    """Blank out `name(` … matching `)` so a later search ignores those args."""
    out: list[str] = []
    i = 0
    for m in rx.finditer(src):
        out.append(src[i : m.start()])
        close = _match_closer(src, m.end() - 1)
        i = (close + 1) if close >= 0 else m.end()
    out.append(src[i:])
    return "".join(out)


def _strip_tag_attrs(block: str) -> str:
    """Leave element text / mustaches; drop attributes (data-id={c.id} is not visible)."""
    no_mustache_attr = re.sub(
        r"\s+[A-Za-z_:][\w:.-]*\s*=\s*\{(?:[^{}]|\{[^{}]*\})*\}",
        "",
        block,
    )
    no_quoted_attr = re.sub(
        r"\s+[A-Za-z_:][\w:.-]*\s*=\s*(?:\"[^\"]*\"|'[^']*')",
        "",
        no_mustache_attr,
    )
    return no_quoted_attr


def _visible_switcher_text(block: str) -> str:
    """User-visible switcher text. Each keys and {#if} tests are not shown."""
    no_attrs = _strip_tag_attrs(block)
    return re.sub(r"\{[#/:@].*?\}", "", no_attrs, flags=re.S)


def _person_detail_markup(app: str) -> str:
    """Person column chrome (title → text-only footer), not the people sidebar."""
    start = app.find("{personTitle}")
    if start < 0:
        start = app.find("personTitle")
    end = app.find("Bodies are text")
    if start >= 0 and end > start:
        return app[start:end]
    markup = app
    script_end = app.rfind("</script>")
    if script_end >= 0:
        markup = app[script_end:]
    return markup


def _conversation_switcher_blocks(crate: Path) -> list[str]:
    """Conversation list/select chrome — not the people sidebar, not chat bubbles."""
    found: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte":
            continue
        text = p.read_text()
        for m in _CONV_SWITCHER_HOOK.finditer(text):
            found.append(text[max(0, m.start() - 200) : m.end() + 900])
        i = 0
        while True:
            m = _CONV_EACH.search(text, i)
            if not m:
                break
            end = _matching_each_end(text, m.start())
            if end < 0:
                fail(f"#114: unclosed conversation {{#each}} in {p.relative_to(crate)}")
            found.append(text[m.start() : end])
            i = end
        for m in re.finditer(r"<select\b[^>]*>.*?</select>", text, re.I | re.S):
            chunk = m.group(0)
            if re.search(r"conversation|convo", chunk, re.I):
                found.append(chunk)
    return found


def _svelte_markup(text: str) -> str:
    end = text.rfind("</script>")
    return text[end:] if end >= 0 else text


def _template_stack(markup: str, pos: int) -> list[tuple[str, str, str]]:
    """Open {#if}/{#each}/compact tags at pos. {:else} is if-else (not a closed gate)."""
    stack: list[tuple[str, str, str]] = []
    for m in _TMPL_TOKEN.finditer(markup):
        if m.start() >= pos:
            break
        tok = m.group(0)
        if tok.startswith("{#if"):
            stack.append(("if", (m.group(1) or "").strip(), ""))
        elif tok.startswith("{:else if"):
            if stack and stack[-1][0] in {"if", "if-else"}:
                stack[-1] = ("if", (m.group(2) or "").strip(), "")
        elif tok.startswith("{:else}"):
            if stack and stack[-1][0] == "if":
                stack[-1] = ("if-else", stack[-1][1], "")
        elif tok.startswith("{/if}"):
            while stack and stack[-1][0] not in {"if", "if-else"}:
                stack.pop()
            if stack:
                stack.pop()
        elif tok.startswith("{#each"):
            stack.append(("each", (m.group(3) or "").strip(), ""))
        elif tok.startswith("{/each}"):
            while stack and stack[-1][0] != "each":
                stack.pop()
            if stack:
                stack.pop()
        elif tok.startswith("{#await") or tok.startswith("{#key"):
            stack.append(("block", tok[:6], ""))
        elif tok.startswith("{/await}") or tok.startswith("{/key}"):
            if stack and stack[-1][0] == "block":
                stack.pop()
        elif tok.startswith("</"):
            name = (m.group(6) or "").lower()
            if stack and stack[-1][0] == "tag" and stack[-1][1].lower() == name:
                stack.pop()
        else:
            stack.append(("tag", (m.group(4) or "").lower(), m.group(5) or ""))
    return stack


def _is_vacuous_chrome_cond(cond: str) -> bool:
    """selectedId / personTitle / true is not 'user opened identity chrome'."""
    parts = re.split(r"&&|\|\|", cond)
    if not parts:
        return True
    for raw in parts:
        p = raw.strip().strip("()")
        p = re.sub(r"^\s*!!?", "", p).strip()
        if re.fullmatch(r"true|1", p, re.I):
            continue
        if re.fullmatch(r"personTitle", p):
            continue
        if re.fullmatch(
            r"(?:selectedId|selectedPerson|identities\.length(?:\s*[><!=]=?\s*0)?"
            r"|personById\s*\([^)]*\)|st|setup|booting|opening"
            r"|view\s*===\s*[\"']\w+[\"'])",
            p,
        ):
            continue
        if re.fullmatch(r"selectedId\s*(?:!=|!==|==|===)\s*(?:null|undefined)", p):
            continue
        return False
    return True


def _details_always_open(attrs: str) -> bool:
    if re.search(r"\bbind:open\b|\bopen\s*=\s*\{", attrs):
        return False
    return bool(re.search(r"\bopen\b", attrs))


def _assigned_idents(expr: str) -> set[str]:
    return set(re.findall(r"\b([A-Za-z_]\w*)\s*=(?!=)", expr))


def _cond_uses_flag(cond: str, flags: set[str]) -> bool:
    return any(re.search(rf"\b{re.escape(f)}\b", cond) for f in flags)


def _title_flags(expr: str, whole: str, seen: set[str] | None = None) -> set[str]:
    found = seen if seen is not None else set()
    flags = {a for a in _assigned_idents(expr) if a not in _TITLE_SKIP_ASSIGN}
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", expr):
        name = m.group(1)
        if name in found or name in _SCROLL_HELPER_SKIP or name in _TITLE_SKIP_ASSIGN:
            continue
        found.add(name)
        body = _function_body(whole, name)
        if body:
            flags |= _title_flags(body, whole, found)
    return flags


def _open_tag_before(markup: str, pos: int) -> tuple[int, str] | None:
    n = len(markup)
    i = pos
    while i > 0:
        lt = markup.rfind("<", 0, i)
        if lt < 0:
            return None
        if markup.startswith("</", lt) or markup.startswith("<!--", lt):
            i = lt
            continue
        j = lt + 1
        q = None
        brace = 0
        while j < n:
            c = markup[j]
            if q:
                if c == q:
                    q = None
            elif c in "'\"":
                q = c
            elif c == "{":
                brace += 1
            elif c == "}":
                if brace:
                    brace -= 1
            elif c == ">" and brace == 0:
                return lt, markup[lt : j + 1]
            j += 1
        return None
    return None


def _is_title_wrapper(tag: str) -> bool:
    name_m = re.match(r"<([\w.]+)", tag)
    if not name_m:
        return False
    name = name_m.group(1).lower()
    if name in {"button", "summary", "h1", "a"}:
        return True
    return bool(re.search(r"personTitle|person-title|data-person-title", tag))


def _ancestor_tags(markup: str, pos: int, limit: int = 4) -> list[str]:
    tags: list[str] = []
    cur = pos
    for _ in range(limit):
        found = _open_tag_before(markup, cur)
        if not found:
            break
        lt, tag = found
        tags.append(tag)
        cur = lt
    return tags


def _click_expr(tag: str) -> str:
    m = _CLICK_ATTR.search(tag)
    if not m:
        return ""
    open_i = m.end() - 1
    close = _match_closer(tag, open_i)
    if close < 0:
        return ""
    return tag[open_i + 1 : close]


def _person_title_pos(markup: str) -> int:
    for pat in (
        "{personTitle}",
        'id="personTitle"',
        "id='personTitle'",
        'class="personTitle"',
        "data-person-title",
        "person-title",
    ):
        i = markup.find(pat)
        if i >= 0:
            return i
    return markup.find("personTitle")


def _identity_title_toggle(markup: str, whole: str) -> tuple[set[str], bool]:
    """Flags assigned by clicking the person title, and whether the title is a <summary>."""
    pos = _person_title_pos(markup)
    if pos < 0:
        return set(), False
    tags = _ancestor_tags(markup, pos)
    candidates: list[str] = []
    if tags:
        candidates.append(tags[0])
        for tag in tags[1:]:
            if _is_title_wrapper(tag):
                candidates.append(tag)
    title_in_summary = any(re.match(r"<summary\b", t, re.I) for t in candidates)
    flags: set[str] = set()
    for tag in candidates:
        expr = _click_expr(tag)
        if expr:
            flags |= _title_flags(expr, whole)
            break
    return flags, title_in_summary


def _hidden_flags_before(markup: str, pos: int) -> set[str]:
    window = markup[max(0, pos - 500) : pos]
    flags: set[str] = set()
    skip = _TITLE_SKIP_ASSIGN | {
        "hidden",
        "true",
        "false",
        "null",
        "undefined",
        "class",
        "aria",
    }
    exprs: list[str] = []
    for m in _HIDDEN_BIND.finditer(window):
        close = _match_closer(window, m.end() - 1)
        if close >= 0:
            exprs.append(window[m.end() : close])
    for m in re.finditer(r"\bclass\s*=\s*\{", window, re.I):
        close = _match_closer(window, m.end() - 1)
        if close < 0:
            continue
        expr = window[m.end() : close]
        if "hidden" in expr.lower():
            exprs.append(expr)
    for expr in exprs:
        for ident in re.findall(r"\b([A-Za-z_]\w*)\b", expr):
            if ident not in skip:
                flags.add(ident)
    return flags


def _chrome_hidden_by_default(markup: str, pos: int) -> bool:
    for kind, a, b in _template_stack(markup, pos):
        if kind == "if" and not _is_vacuous_chrome_cond(a):
            return True
        if kind == "tag" and a.lower() == "details" and not _details_always_open(b):
            return True
    return bool(_hidden_flags_before(markup, pos))


def _chrome_toggled_by_title(
    markup: str, pos: int, flags: set[str], title_in_summary: bool
) -> bool:
    for kind, a, b in _template_stack(markup, pos):
        if kind == "if" and flags and _cond_uses_flag(a, flags):
            return True
        if kind == "tag" and a.lower() == "details" and not _details_always_open(b):
            if title_in_summary:
                return True
            if flags and _cond_uses_flag(b, flags):
                return True
    hidden_fs = _hidden_flags_before(markup, pos)
    return bool(flags and hidden_fs & flags)


def _flag_default_open(logic: str, name: str) -> bool:
    m = re.search(
        rf"\b(?:let|const|var)\s+{re.escape(name)}\s*=\s*"
        rf"(?:\$state\s*(?:<[^>]*>)?\s*\(\s*)?([^\n;)]+)",
        logic,
    )
    if not m:
        return False
    val = m.group(1).strip().rstrip(")").strip()
    return val in {"true", "1", '"open"', "'open'"} or val.startswith("true")


def _person_chrome_markup(text: str) -> str:
    """Person column, including the title open tag (h1 / button / summary onclick)."""
    idx = text.find("{personTitle}")
    if idx < 0:
        idx = text.find("data-conversation-switcher")
    if idx < 0:
        return _person_detail_markup(text)
    # Look back far enough for a wrapping <button>/<summary>/<details>, not to {#if st}.
    start = max(0, idx - 600)
    end = text.find("Bodies are text", idx)
    if end > start:
        return text[start:end]
    return text[start:]


def _person_pane_markups(crate: Path) -> list[str]:
    found: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        text = p.read_text()
        if not (
            "{personTitle}" in text
            or "data-conversation-switcher" in text
            or "openMerge" in text
        ):
            continue
        found.append(_person_chrome_markup(text))
    return found


def _groups_ctrl_pos(detail: str) -> int:
    m = _GROUPS_BIND.search(detail)
    if m:
        return m.start()
    m = _GROUPS_LABEL_CTRL.search(detail)
    if m and re.search(r"<input\b", m.group(0), re.I):
        return m.start()
    return -1


def _is_compact_enclosure(stack: list[tuple[str, str, str]], logic: str = "") -> bool:
    compact_parts = {
        "select",
        "details",
        "popover",
        "dropdownmenu",
        "dropdown",
        "combobox",
        "menu",
    }
    for kind, a, b in stack:
        if kind == "tag":
            parts = a.lower().split(".")
            if any(p in compact_parts for p in parts):
                if "details" in parts and _details_always_open(b):
                    continue
                return True
        if kind == "if" and not _is_vacuous_chrome_cond(a):
            ident = a.strip()
            if ident.isidentifier() and _flag_default_open(logic, ident):
                continue
            return True
    return False


def _always_expanded_conversation_list(crate: Path, logic: str = "") -> bool:
    """True if {#each conversations} is a second always-visible list, not a compact control."""
    for pane in _person_pane_markups(crate):
        for m in _CONV_EACH.finditer(pane):
            if _is_compact_enclosure(_template_stack(pane, m.start()), logic):
                continue
            return True
    return False


def _people_list_hidden_on_select(crate: Path) -> bool:
    for p in _web_sources(crate):
        if p.suffix != ".svelte":
            continue
        markup = _svelte_markup(p.read_text())
        for m in re.finditer(r"\{#each\s+filtered\b", markup):
            for kind, a, _b in _template_stack(markup, m.start()):
                if kind == "if" and re.search(
                    r"!\s*selectedId|selectedId\s*===\s*null|selectedId\s*==\s*null",
                    a,
                ):
                    return True
    return False


def _z_from_text(blob: str) -> int | None:
    """Highest explicit numeric z-index in classes / CSS (z-auto does not count)."""
    best: int | None = None
    for m in _TW_Z_INDEX.finditer(blob):
        n = int(m.group(1) or m.group(2))
        best = n if best is None else max(best, n)
    for m in _CSS_Z_INDEX.finditer(blob):
        n = int(m.group(1))
        best = n if best is None else max(best, n)
    for m in _CLASS_Z_DIR.finditer(blob):
        n = int(m.group(1))
        best = n if best is None else max(best, n)
    return best


def _has_stacking_bg(blob: str) -> bool:
    """Opaque background so a sticky date cannot show through the control."""
    if _CSS_STACK_BG.search(blob):
        return True
    for m in _TW_STACK_BG.finditer(blob):
        if m.group(1):
            continue
        if m.group(3) == "0":
            continue
        return True
    return False


def _tag_name(tag: str) -> str:
    m = re.match(r"</?([A-Za-z][\w:.-]*)", tag)
    return (m.group(1) if m else "").lower()


def _class_list(tag: str) -> list[str]:
    m = re.search(r"\bclass(?:Name)?\s*=\s*[\"']([^\"']*)[\"']", tag, re.I)
    if not m:
        m = re.search(
            r"\bclass(?:Name)?\s*=\s*\{[`'\"]([^`'\"]*)[`'\"]\}",
            tag,
            re.I,
        )
    if not m:
        return []
    return m.group(1).split()


def _id_of(tag: str) -> str | None:
    m = re.search(r"\bid\s*=\s*[\"']([^\"']+)[\"']", tag, re.I)
    return m.group(1) if m else None


def _style_attr(tag: str) -> str:
    m = re.search(r"\bstyle\s*=\s*[\"']([^\"']*)[\"']", tag, re.I)
    return m.group(1) if m else ""


def _css_rules_for(css: str, tag: str) -> str:
    chunks: list[str] = []
    for cls in _class_list(tag):
        esc = re.escape(cls)
        chunks.extend(m.group(1) for m in re.finditer(rf"\.{esc}\b[^{{]*\{{([^}}]+)\}}", css))
    el_id = _id_of(tag)
    if el_id:
        esc = re.escape(el_id)
        chunks.extend(m.group(1) for m in re.finditer(rf"#{esc}\b[^{{]*\{{([^}}]+)\}}", css))
    return "\n".join(chunks)


def _layer_blob(tag: str, css: str) -> str:
    return "\n".join((tag, _style_attr(tag), _css_rules_for(css, tag)))


def _layer_stacks(blob: str, day_z: int) -> tuple[bool, int | None, bool]:
    z = _z_from_text(blob)
    bg = _has_stacking_bg(blob)
    return bool(z is not None and z > day_z and bg), z, bg


def _element_span(markup: str, pos: int) -> tuple[int, str, str] | None:
    """Open tag at/before pos and its inner HTML (not descendants' close)."""
    found = _open_tag_before(markup, pos + 1)
    if not found:
        return None
    lt, tag = found
    name = _tag_name(tag)
    if not name or tag.rstrip().endswith("/>") or name in _VOID_HTML:
        return lt, tag, ""
    start = lt + len(tag)
    depth = 1
    rx = re.compile(rf"<{re.escape(name)}\b|</{re.escape(name)}\s*>", re.I)
    for m in rx.finditer(markup, start):
        if markup.startswith("</", m.start()):
            depth -= 1
            if depth == 0:
                return lt, tag, markup[start : m.start()]
        else:
            depth += 1
    return lt, tag, markup[start:]


def _day_heading_z_index(crate: Path) -> int:
    """Sticky day-heading z-index. Missing still stacks as 10 (current .day-heading)."""
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    found: list[int] = []
    for m in _DAY_HEADING_CSS.finditer(blob):
        z = _z_from_text(m.group(1))
        if z is not None:
            found.append(z)
    for m in re.finditer(r"<[^>]+>", blob):
        tag = m.group(0)
        if not re.search(r"day-heading|day-separator|day-sep\b|data-day-heading", tag, re.I):
            continue
        z = _z_from_text(tag)
        if z is not None:
            found.append(z)
    return max(found) if found else 10


def _switcher_hook_positions(markup: str) -> list[int]:
    pos = [m.start() for m in _CONV_SWITCHER_HOOK.finditer(markup)]
    if pos:
        return pos
    pos = [m.start() for m in _CONV_SELECT.finditer(markup)]
    if pos:
        return pos
    return [m.start() for m in _CONV_EACH.finditer(markup)]


def _is_switcher_tag(tag: str) -> bool:
    if _CONV_SWITCHER_HOOK.search(tag) or _CONV_SELECT.search(tag):
        return True
    return _tag_name(tag) in {"details", "select"}


def _child_open_tag(inner: str, rx: re.Pattern[str]) -> str | None:
    m = rx.search(inner)
    if not m:
        return None
    found = _open_tag_before(inner, m.start() + 1)
    return found[1] if found else m.group(0)


def _switcher_summary_and_panel(tag: str, inner: str) -> tuple[str | None, str | None]:
    """Closed control (summary / select) and the open list, if they are separate."""
    if _tag_name(tag) == "select" or _CONV_SELECT.search(tag):
        return tag, None
    summary = _child_open_tag(inner, re.compile(r"<summary\b", re.I))
    panel = _child_open_tag(
        inner,
        re.compile(
            r"<[^>]*\babsolute\b|<[^>]*role\s*=\s*[\"'](?:listbox|menu)[\"']",
            re.I,
        ),
    )
    if panel is None:
        panel = _child_open_tag(inner, re.compile(r"<(?:ul|ol|menu)\b", re.I))
    return summary, panel


def _switcher_above_day_heading(crate: Path) -> tuple[bool, int, int | None, bool]:
    """Whether All / the open panel stack above .day-heading.

    A z-index on the person-pane header or the switcher element covers both
    the closed label and the dropdown (one stacking context). z-index only on
    the panel leaves All under the sticky date; only on the summary leaves
    the open list under it. People-sidebar overflow (#159) is not in scope.
    """
    day_z = _day_heading_z_index(crate)
    css = "\n".join(p.read_text() for p in _web_sources(crate))
    best_z: int | None = None
    saw_bg = False
    saw_switcher = False
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        markup = p.read_text()
        for pos in _switcher_hook_positions(markup):
            saw_switcher = True
            switcher: tuple[int, str, str] | None = None
            headers: list[str] = []
            cur = pos + 1
            for _ in range(12):
                found = _open_tag_before(markup, cur)
                if not found:
                    break
                lt, _open = found
                el = _element_span(markup, lt)
                if not el:
                    break
                _lt, tag, inner = el
                if switcher is None and _is_switcher_tag(tag):
                    switcher = el
                elif switcher is not None and not _TIMELINE_INNER.search(inner):
                    headers.append(tag)
                cur = lt
            if switcher is None:
                switcher = _element_span(markup, pos)
            if switcher is None:
                continue
            _lt, sw_tag, sw_inner = switcher
            summary, panel = _switcher_summary_and_panel(sw_tag, sw_inner)
            sw_blob = _layer_blob(sw_tag, css)
            hd_blobs = [_layer_blob(h, css) for h in headers]
            su_blob = _layer_blob(summary, css) if summary else ""
            pa_blob = _layer_blob(panel, css) if panel else ""
            sw_ok, sw_z, sw_bg = _layer_stacks(sw_blob, day_z)
            hd_hits = [_layer_stacks(b, day_z) for b in hd_blobs]
            hd_ok = any(ok for ok, _z, _bg in hd_hits)
            su_ok, su_z, su_bg = _layer_stacks(su_blob, day_z) if summary else (False, None, False)
            pa_ok, _pa_z, _pa_bg = _layer_stacks(pa_blob, day_z) if panel else (True, None, True)
            for z in (sw_z, su_z, *(z for _ok, z, _bg in hd_hits)):
                if z is None:
                    continue
                best_z = z if best_z is None else max(best_z, z)
            saw_bg = saw_bg or sw_bg or su_bg or any(bg for _ok, _z, bg in hd_hits)
            # Panel-only stacking does not cover the word All.
            if sw_ok or hd_ok or (su_ok and pa_ok):
                return True, day_z, best_z, True
    if not saw_switcher:
        return False, day_z, best_z, saw_bg
    return False, day_z, best_z, saw_bg


def assert_conversation_switcher(crate: Path) -> None:
    """#114: after a person is selected, switch conversations; default All; no raw ids.

    Groups still need include-groups to appear in the list and in All.
    Identity chrome (Merge, include groups, unlink) stays hidden until the
    person name is clicked. Conversation switcher is a compact header control,
    not a second always-expanded list above the bubbles. People sidebar stays.
    All / the open panel must stack above sticky .day-heading (higher z-index
    + background). Not in scope: create / mute / pin. Keep #111–#113.
    """
    app = (crate / "web" / "App.svelte").read_text()
    logic = _web_logic(crate)
    api_src = (crate / "web" / "lib" / "api.ts").read_text()
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    whole = app + "\n" + logic

    blocks = _conversation_switcher_blocks(crate)
    if not blocks:
        fail(
            "#114: after selecting a person, list their conversations "
            "({#each conversations / convos / personConversations / conversationList, "
            "a conversation <select>, or data-conversation-switcher) "
            "with title + platform + last_at"
        )
    switcher = "\n".join(blocks)

    # People sidebar and chat bubbles are not the switcher.
    if _CONV_EACH.search(switcher) is None and not _CONV_SWITCHER_HOOK.search(switcher):
        if not _CONV_SELECT.search(switcher):
            fail(
                "#114: conversation switcher must be a list or select of conversations, "
                "not the people sidebar and not a caption inside a chat bubble"
            )
    tl = _timeline_block(crate)
    if switcher.strip() and switcher.strip() in tl:
        fail(
            "#114: conversation switcher must sit outside the message bubbles "
            "(list conversations, then filter the timeline)"
        )

    detail = _person_detail_markup(app)
    if not _CONV_ALL_LABEL.search(switcher) and not _CONV_ALL_LABEL.search(detail):
        fail("#114: conversation switcher must offer All (default = current D18 merged stream)")
    if not _CONV_STATE_DEFAULT_ALL.search(logic) and not _CONV_STATE_DEFAULT_ALL.search(app):
        fail(
            "#114: default conversation must be All "
            "(selected conversation state starts null / undefined / \"all\")"
        )

    sel = _function_body(whole, "selectPerson")
    if not sel:
        fail("#114: selectPerson must still open a person (default conversation = All)")
    opened_all = bool(_CONV_RESET_ALL.search(sel)) or bool(
        re.search(
            r"conversation(?:Id|_id)\s*:\s*(?:null|undefined|(?:append\s*\?))",
            sel,
        )
    )
    if not opened_all:
        fail(
            "#114: opening a person must default to All (merged D18 stream), "
            "not leave a previously picked conversation_id selected"
        )

    if not _CONV_TITLE.search(switcher):
        fail("#114: each conversation in the list must show its title")
    if not _CONV_PLATFORM.search(switcher):
        fail("#114: each conversation in the list must show its platform")
    if not _CONV_LAST_AT.search(switcher):
        fail(
            "#114: each conversation in the list must show last_at "
            "(last activity time of that conversation for this person)"
        )

    if not _CONV_PICK.search(switcher) and not _CONV_PICK.search(detail):
        fail("#114: picking a conversation must select it (click / change / bind)")

    tl_filtered = False
    for m in _PERSON_TIMELINE_CALL.finditer(whole):
        arg = _call_arg(whole, m.end() - 1)
        if re.search(r"conversation(?:Id|_id)\s*:", arg):
            tl_filtered = True
            if not re.search(r"includeGroups", arg):
                fail(
                    "#114: personTimeline must still pass includeGroups "
                    "(All is the current D18 merged stream; groups stay gated)"
                )
            break
    if not tl_filtered:
        fail(
            "#114: picking one conversation must filter the timeline "
            "(personTimeline must pass conversationId / conversation_id; "
            "All passes null so the stream stays D18 merged)"
        )

    api_args = re.search(r"personTimeline\s*:\s*\(\s*args\s*:\s*\{([^}]*)\}", api_src, re.S)
    if not api_args or not re.search(r"conversation(?:Id|_id)\b", api_args.group(1)):
        fail(
            "#114: personTimeline args must include optional conversationId / conversation_id "
            "(All = omitted/null; pick one = that conversation)"
        )

    if not _INCLUDE_GROUPS_LABEL.search(app):
        fail("#114: include groups toggle must remain (groups still require it)")

    list_src = _without_calls(whole, _PERSON_TIMELINE_CALL) + "\n" + switcher
    group_in_list = re.search(
        r"includeGroups[\s\S]{0,400}[\"']group[\"']|[\"']group[\"'][\s\S]{0,400}includeGroups",
        list_src,
    )
    fetched_with_toggle = re.search(
        r"(?:conversations|convos|personConversations|conversationList|convList"
        r"|visibleConversations|filteredConversations)"
        r"\s*=\s*(?:await\s+)?[^=;\n]{0,200}includeGroups",
        list_src,
        re.I,
    )
    if not group_in_list and not fetched_with_toggle:
        fail(
            "#114: groups must require the include-groups toggle to appear in the "
            "conversation list (and in All) — filter kind === \"group\" with includeGroups, "
            "or load the list with includeGroups"
        )
    if re.search(r"kind\s*===?\s*[\"']dm[\"']", list_src) and not re.search(
        r"[\"']group[\"']|email_thread", list_src
    ):
        fail("#114: list dm / group / email_thread, not only DMs")

    visible = _visible_switcher_text(switcher)
    if _CONV_ID_TEXT.search(visible):
        fail(
            "#114: no raw conversation ids or person ids in the conversation switcher "
            "(show title + platform + last_at; data-conversation-id attributes are fine)"
        )
    if (
        _CONV_ID_FALLBACK.search(switcher)
        or _CONV_ID_FALLBACK.search(sel)
        or _CONV_ID_FALLBACK.search(detail)
    ):
        fail("#114: do not fall back a missing conversation title to a raw id")

    markup = app
    script_end = app.rfind("</script>")
    if script_end >= 0:
        markup = app[script_end:]
    if _CONV_CREATE.search(markup) or _CONV_CREATE.search(switcher):
        fail("#114: not in scope — do not add create-conversation chrome")
    if _CONV_MUTE.search(markup) or _CONV_MUTE.search(switcher):
        fail("#114: not in scope — do not add mute-conversation chrome")
    if _CONV_PIN.search(markup) or _CONV_PIN.search(switcher):
        fail("#114: not in scope — do not add pin-conversation chrome")

    if not re.search(
        r"("
        r"conversation switcher"
        r"|list(?:s|ing)? (?:their |the )?conversations"
        r"|conversations? (?:list|switcher|filter)"
        r")",
        dtxt,
        re.I,
    ):
        fail("#114: docs/user/app.md must describe the conversation switcher")
    if not re.search(
        r"("
        r"\bAll\b.{0,100}(default|merged|D18)"
        r"|(default|merged|D18).{0,100}\bAll\b"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail("#114: docs/user/app.md must say All is the default (merged D18 stream)")
    if not re.search(
        r"("
        r"filter(?:s|ed|ing)? (?:the )?timeline"
        r"|timeline.{0,60}filter"
        r"|picking (?:a |one )?conversation"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail("#114: docs/user/app.md must say picking a conversation filters the timeline")
    if not re.search(
        r"("
        r"include groups?.{0,160}conversation"
        r"|conversation.{0,160}include groups?"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#114: docs/user/app.md must say groups still need include-groups "
            "to appear in the conversation list (and in All)"
        )

    # Dogfood: reading a chat must not be buried under identity admin + a second list.
    panes = _person_pane_markups(crate)
    pane = "\n".join(panes) if panes else detail
    merge_at = _MERGE_CTRL.search(pane)
    unlink_at = _UNLINK_CTRL.search(pane)
    groups_at = _groups_ctrl_pos(pane)
    if not merge_at:
        fail(
            "#114: Merge must remain in the person chrome "
            "(hidden until the person name is clicked; do not remove it)"
        )
    if groups_at < 0:
        fail(
            "#114: include groups toggle must remain in the person chrome "
            "(hidden until the person name is clicked; groups still need it)"
        )
    if not unlink_at:
        fail(
            "#114: unlink must remain in the person chrome "
            "(hidden until the person name is clicked; do not remove it)"
        )

    chrome_sites = (
        ("Merge", merge_at.start()),
        ("include groups", groups_at),
        ("unlink", unlink_at.start()),
    )
    for label, pos in chrome_sites:
        if not _chrome_hidden_by_default(pane, pos):
            fail(
                f"#114: {label} must not show until the user opens identity chrome "
                "(default: behind {{#if …}} / hidden / <details> closed — "
                "not sitting above the timeline after selecting a person; "
                "{{#if selectedId}} alone is not a click-to-open gate)"
            )

    flags, title_in_summary = _identity_title_toggle(pane, whole)
    if not flags and not title_in_summary:
        fail(
            "#114: clicking the person title (h1 / personTitle / a button wrapping "
            "the name) must toggle identity chrome (Merge, include groups, unlink)"
        )
    if flags and any(_flag_default_open(logic, name) for name in flags):
        fail(
            "#114: identity chrome must start closed "
            "(toggle state must default false / closed, not true)"
        )
    for label, pos in chrome_sites:
        if not _chrome_toggled_by_title(pane, pos, flags, title_in_summary):
            fail(
                f"#114: clicking the person title must toggle {label} "
                "(same {{#if}} flag, <details> summary, or hidden binding — "
                "not a separate always-visible control)"
            )

    if flags:
        buried = False
        for rx in (_CONV_SWITCHER_HOOK, _CONV_SELECT, _CONV_EACH):
            hit = rx.search(pane)
            if not hit:
                continue
            stack = _template_stack(pane, hit.start())
            if any(kind == "if" and _cond_uses_flag(a, flags) for kind, a, _b in stack):
                buried = True
                break
        if buried:
            fail(
                "#114: conversation switcher must stay in the header next to the "
                "person name (not inside the identity chrome that opens on click)"
            )

    if _always_expanded_conversation_list(crate, logic):
        fail(
            "#114: conversation switcher must be compact in the header "
            "(a <select>, <details>, or a single closed control) — "
            "not a second always-expanded full-width {#each conversations} "
            "list sitting above the bubbles (data-conversation-switcher can stay; "
            "title + platform + last_at still belong inside the compact control)"
        )

    people_src = "\n".join(
        p.read_text() for p in _web_sources(crate) if p.suffix == ".svelte"
    )
    if not re.search(r"\{#each\s+filtered\b", people_src) and not re.search(
        r"id=[\"']person-filter[\"']", people_src
    ):
        fail("#114: people sidebar must stay (do not hide the people list)")
    if _people_list_hidden_on_select(crate):
        fail(
            "#114: people sidebar must stay — do not hide the people list when a "
            "person is selected (no Back-that-hides-the-list in this issue)"
        )

    if not re.search(
        r"("
        r"compact (conversation )?(switcher|control)"
        r"|(conversation )?(switcher|control).{0,80}compact"
        r"|not a second .{0,60}(list|switcher)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#114: docs/user/app.md must say the conversation switcher is a "
            "compact header control (not a second list above the bubbles)"
        )
    if not re.search(
        r"("
        r"(click(?:s|ing)?|tap(?:s|ping)?) (the )?(person )?(name|title)"
        r".{0,160}(Merge|include groups|unlink|identity)"
        r"|(Merge|include groups|unlink|identity chrome)"
        r".{0,160}(click(?:s|ing)?|hidden until|until you click)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#114: docs/user/app.md must say identity chrome "
            "(Merge, include groups, unlink) is hidden until the person name is clicked"
        )

    # Dogfood: sticky .day-heading must not cover All or the open panel.
    stacked, day_z, chrome_z, chrome_bg = _switcher_above_day_heading(crate)
    if not stacked:
        if chrome_z is None or chrome_z <= day_z:
            fail(
                "#114: conversation switcher (data-conversation-switcher / its "
                "summary or panel) or the person-pane header that contains it "
                f"must stack above .day-heading (higher z-index than {day_z}, "
                "and a background so the date cannot show through) — "
                "fail if the switcher/header z-index is missing or "
                f"≤ the day-heading z-index ({day_z})"
            )
        if not chrome_bg:
            fail(
                "#114: conversation switcher / person-pane header must have a "
                "background so the sticky .day-heading date cannot show through "
                "All or the open panel"
            )
        fail(
            "#114: conversation switcher / person-pane header must stack above "
            f".day-heading (z-index > {day_z} and a background; the date must "
            "not cover All or the dropdown)"
        )


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
    assert_conversation_switcher(crate)
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
