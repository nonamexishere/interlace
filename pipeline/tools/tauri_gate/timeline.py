"""Timeline chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _BUBBLE_ME_VARS,
    _BUBBLE_THEM_VARS,
    _HEIGHT_CACHE,
    _HTML_BODY,
    _HUMAN_TIME_HELPERS,
    _INCLUDE_GROUPS_LABEL,
    _MONTH_SHORT,
    _PRETTY_GMAIL,
    _PRETTY_WHATSAPP,
    _PRE_WRAP,
    _RAW_WHATSAPP,
    _SCROLL_HELPER_SKIP,
    _SHOW_QUOTED,
    _TIMELINE_EACH_NAMES,
    _call_arg,
    _css_var,
    _function_body,
    _helper_with_callees,
    _match_closer,
    _matching_each_end,
    _person_detail_markup,
    _svelte_markup,
    _tag_name,
    _template_stack,
    _timeline_block,
    _ts_function_body,
    _web_logic,
    _web_sources,
    _without_comments,
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
_BUBBLE_ME_USE = ("var(--bubble-me)", "var(--color-bubble-me)", "bg-bubble-me", "bubble-me")
_BUBBLE_THEM_USE = (
    "var(--bubble-them)",
    "var(--color-bubble-them)",
    "bg-bubble-them",
    "bubble-them",
)

# #112 — day heading when the calendar day of sent_at changes.
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
# Calendar day of sent_at: UTC ISO prefix, UTC getters, or host-local getters / Intl.
# #268: slice(0, 10) is not the only legal day key.
_ISO_DAY = re.compile(
    r"("
    r"\.slice\s*\(\s*0\s*,\s*10\s*\)"
    r"|\.substring\s*\(\s*0\s*,\s*10\s*\)"
    r"|toISOString\s*\(\s*\)\s*\.\s*slice\s*\(\s*0\s*,\s*10\s*\)"
    r"|getUTCFullYear"
    r"|getFullYear"
    r"|getMonth"
    r"|getDate"
    r"|toLocaleDateString"
    r"|Intl\.DateTimeFormat"
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
# Timeline row loop — full list names or windowed variants (#120).
_EACH_TIMELINE = re.compile(
    r"\{#each\s+(?:"
    r"timeline|dayGroups|"
    r"windowed(?:Day)?Groups|visible(?:Day)?Groups|virtual(?:Day)?Groups|"
    r"rendered(?:Day)?Groups|windowedRows|visibleRows|virtualRows|renderedRows|"
    r"windowedTimeline|visibleTimeline|virtualTimeline|renderedTimeline|"
    r"windowedItems|visibleItems|virtualItems"
    r")\b"
)
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
    """#112: day heading (DD/MM/YYYY) when sent_at's day changes; sticky."""
    block = _timeline_block(crate)
    app = (crate / "web" / "App.svelte").read_text()
    logic = _web_logic(crate)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    if not _DAY_HEADING.search(block):
        fail(
            "#112: person timeline must insert a day heading "
            "(h2–h4, role=heading, or day-heading) when the calendar day changes"
        )
    # Heading is a timeline separator, not a label inside the #111 bubble.
    outside_bubbles = block
    for btn in re.findall(r"<button\b.*?</button>", block, re.S):
        outside_bubbles = outside_bubbles.replace(btn, "", 1)
    if not _DAY_HEADING.search(outside_bubbles):
        fail(
            "#112: day heading must sit on the timeline when the calendar day changes, "
            "not inside a chat bubble"
        )

    if_conds = _HEADING_IF.findall(block)
    if not if_conds:
        fail(
            "#112: day heading must be conditional "
            "(when sent_at's calendar day changes; no heading if sent_at is missing)"
        )
    if not any(
        re.search(
            r"sent_at|utcDay|localDay|hostDay|dayKey|calendarDay|isoDay|\bday\b",
            c,
            re.I,
        )
        for c in if_conds
    ):
        fail(
            "#112: day heading {#if} must key off the calendar day of sent_at "
            "(do not invent a heading for a row with no date)"
        )

    if not _PREV_DAY.search(block) and not _PREV_DAY.search(app):
        fail(
            "#112: must compare the current row's calendar day to the previous "
            "row (timeline[i - 1]) so a multi-year DM gets day/month/year separators"
        )

    has_day_key = (
        _ISO_DAY.search(app)
        or _ISO_DAY.search(block)
        or _ISO_DAY.search(logic)
        or _LOCAL_DAY.search(app)
        or _LOCAL_DAY.search(block)
        or _LOCAL_DAY.search(logic)
    )
    if not has_day_key:
        fail(
            "#112: compare days on the calendar day of sent_at "
            "(local getFullYear/getMonth/getDate, Intl, or ISO prefix / UTC getters)"
        )
    if not re.search(
        r"("
        r"utcDayLabel"
        r"|localDayLabel"
        r"|hostDayLabel"
        r"|calendarDayLabel"
        r"|split\s*\(\s*[\"']-[\"']\s*\)"
        r"|/\$\{"
        r"|day\s*/\s*month"
        r"|padStart"
        r")",
        app + "\n" + logic,
        re.I,
    ):
        fail("#112: day headings must display day/month/year (15/03/2024), not YYYY-MM-DD")

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

    if not re.search(r"(day heading|day separator)", dtxt, re.I):
        fail("#112: docs/user/app.md must describe day headings")
    if not re.search(r"(day/month/year|DD/MM/YYYY|15/03/2024)", dtxt, re.I):
        fail("#112: docs/user/app.md must say day headings are day/month/year")

    sticky_src = "\n".join(p.read_text() for p in _web_sources(crate))
    if not re.search(r"(position\s*:\s*sticky|\bsticky\b)", sticky_src, re.I):
        fail("#112: day heading must stick to the top of the message list while scrolling")


# #268 — host-TZ day headings + short times; storage stays UTC ISO.
_DAY_KEY_HELPERS = (
    "utcDay",
    "utc_day",
    "localDay",
    "local_day",
    "hostDay",
    "calendarDay",
    "dayKey",
    "isoDay",
)
_TIME_HELPERS = (
    "utcTime",
    "localTime",
    "hostTime",
    "bubbleTime",
)
_UTC_ISO_DAY_SLICE = re.compile(
    r"\.slice\s*\(\s*0\s*,\s*10\s*\)|\.substring\s*\(\s*0\s*,\s*10\s*\)"
)
_LOCAL_CAL_GETTERS = re.compile(
    r"("
    r"\bgetFullYear\s*\("
    r"|\bgetMonth\s*\("
    r"|\bgetDate\s*\("
    r"|toLocaleDateString"
    r"|Intl\.DateTimeFormat"
    r")"
)
_LOCAL_HM_GETTERS = re.compile(
    r"("
    r"\bgetHours\s*\("
    r"|\bgetMinutes\s*\("
    r"|\bgetDate\s*\("
    r"|toLocaleString"
    r"|toLocaleTimeString"
    r"|Intl\.DateTimeFormat"
    r"|hour\s*:\s*[\"']2-digit[\"']"
    r")"
)
_FORCED_UTC_TZ = re.compile(r"timeZone\s*:\s*[\"']UTC[\"']")
_PARSE_ISO_UTC = re.compile(r"new\s+Date\s*\(|Date\.parse\s*\(")
_TZDATA_DEP = re.compile(
    r"("
    r"\btzdata\b"
    r"|\bchrono-tz\b"
    r"|\biana-time-zone\b"
    r"|\bmoment-timezone\b"
    r"|\bluxon\b"
    r"|timezonedb"
    r"|worldtimeapi"
    r")",
    re.I,
)
_SEARCH_TYPE_DATE = re.compile(r"type\s*=\s*\{?\s*[\"']date[\"']")
_WA_OR_WALLCLOCK = re.compile(
    r"("
    r"\bwhatsapp\b"
    r"|wall[-_ ]?clock"
    r"|\bexport\b"
    r")",
    re.I,
)
_ISO_DIGIT_ESCAPE = re.compile(
    r"("
    r"\.slice\s*\("
    r"|\.substring\s*\("
    r"|\.substr\s*\("
    r"|split\s*\(\s*[\"']T[\"']"
    r"|\.match\s*\("
    r")"
)
_DOCS_WA_WALL = re.compile(
    r"("
    r"whatsapp.{0,140}(?:wall[- ]?clock|export(?:ed)?\s+time|export\s+wall)"
    r"|(?:wall[- ]?clock|export(?:ed)?\s+time).{0,140}whatsapp"
    r")",
    re.I | re.S,
)
_DOCS_GMAIL_ZONE = re.compile(
    r"("
    r"gmail.{0,140}(?:host|Mac)(?:'s)?\s+time\s*zone"
    r"|(?:host|Mac)(?:'s)?\s+time\s*zone.{0,140}gmail"
    r"|zoned.{0,100}(?:gmail|time\s*zone|host|Mac)"
    r"|gmail.{0,100}zoned"
    r")",
    re.I | re.S,
)


def _fn_body(src: str, name: str) -> str:
    return _ts_function_body(src, name) or _function_body(src, name) or ""


def _host_local_day_ok(body: str) -> bool:
    """Parse ISO as UTC, then host-local calendar getters.

    Dual-path bodies may also slice WhatsApp wall-clock digits. Slice-only
    (no Date + local getters) still fails.
    """
    if not body or _FORCED_UTC_TZ.search(body):
        return False
    if not _PARSE_ISO_UTC.search(body):
        return False
    return bool(_LOCAL_CAL_GETTERS.search(body))


def _human_time_host_local(body: str) -> bool:
    """Month + hour:minute from host-local getters / Intl, not the UTC ISO slice."""
    if not body or _FORCED_UTC_TZ.search(body):
        return False
    if not _PARSE_ISO_UTC.search(body):
        return False
    has_month = bool(_MONTH_SHORT.search(body) or re.search(r"\bgetMonth\s*\(", body))
    has_local_hm = bool(_LOCAL_HM_GETTERS.search(body))
    return has_month and has_local_hm


def _called_day_keys(region: str) -> list[str]:
    found: list[str] = []
    for name in _DAY_KEY_HELPERS:
        if re.search(rf"\b{re.escape(name)}\s*\(", region):
            found.append(name)
    return found


def _split_tz_helper_names() -> tuple[str, ...]:
    names: list[str] = []
    for name in (
        *_DAY_KEY_HELPERS,
        "localDayLabel",
        "utcDayLabel",
        *_TIME_HELPERS,
        *_HUMAN_TIME_HELPERS,
    ):
        if name not in names:
            names.append(name)
    return tuple(names)


def _whatsapp_escape_ok(body: str) -> bool:
    """WhatsApp / omitted-platform path uses stored wall-clock digits."""
    if not body:
        return False
    if not _WA_OR_WALLCLOCK.search(body):
        return False
    return bool(_ISO_DIGIT_ESCAPE.search(body))


def _zoned_gmail_ok(body: str) -> bool:
    """Gmail / zoned path: new Date + host-local getters, not forced UTC."""
    if not body or _FORCED_UTC_TZ.search(body):
        return False
    if not _PARSE_ISO_UTC.search(body):
        return False
    return bool(_LOCAL_CAL_GETTERS.search(body) or _LOCAL_HM_GETTERS.search(body))


def _helper_call_args(src: str, name: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(rf"\b{re.escape(name)}\s*\(", src):
        out.append(_call_arg(src, m.end() - 1))
    return out


def _assert_typed_fn_body_visible() -> None:
    """Depth-0 `{` after `: string` is the function body, not a type object."""
    typed_day = (
        "export function localDay(iso: string | null | undefined): string {\n"
        "  return 'ok';\n"
        "}\n"
    )
    if not _ts_function_body(typed_day, "localDay").strip():
        fail(
            "#268: _ts_function_body must find the body of "
            "export function localDay(...): string {"
        )
    foo_src = "function foo(): string { return 1 }"
    if "return 1" not in _ts_function_body(foo_src, "foo"):
        fail(
            "#268: _ts_function_body must extract a typed "
            "function foo(): string { return 1 } body"
        )


def assert_local_tz_display(crate: Path) -> None:
    """#268: day headings + people-row times follow the host timezone.

    Parse stored `sent_at` ISO as UTC, then local getters / Intl. Storage /
    api.ts stay ISO UTC. No TZ picker, no tzdata crate. Search type=date stays.
    Docs: display follows the host / Mac timezone; storage stays UTC.

    Follow-up: WhatsApp / omitted platform displays wall-clock export digits;
    Gmail / zoned still Date-converts. Timeline / Search pass platform.
    `_ts_function_body` must see `export function localDay(...): string {`.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#268: App.svelte required (host-TZ day headings)")
    app = app_path.read_text()
    logic = _web_logic(crate)
    cleaned = _without_comments(app + "\n" + logic)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) Day heading / grouping key is the host calendar day, not UTC slice(0, 10).
    script_end = app.rfind("</script>")
    markup = app[script_end:] if script_end >= 0 else app
    regions = "\n".join(
        p
        for p in (
            _fn_body(app, "isGroupedFollower"),
            _fn_body(app, "isGrouped"),
            _grouping_logic_src(cleaned),
            _derived_body(app, "windowedDayGroups") or "",
            _derived_body(app, "dayGroups") or "",
            markup,
        )
        if p
    )
    called = _called_day_keys(regions)
    host_local = False
    if called:
        for name in called:
            body = _fn_body(app, name) or _fn_body(logic, name) or _fn_body(cleaned, name)
            if _host_local_day_ok(body):
                host_local = True
            else:
                fail(
                    "#268: day headings must use the host calendar day of sent_at "
                    "(parse ISO as UTC, then getFullYear/getMonth/getDate or Intl) "
                    "— not slice(0, 10) of the UTC ISO as the displayed day"
                )
    elif _host_local_day_ok(regions):
        host_local = True
    if not host_local:
        fail(
            "#268: day headings must use the host calendar day of sent_at "
            "(parse ISO as UTC, then getFullYear/getMonth/getDate or Intl) "
            "— not slice(0, 10) of the UTC ISO as the displayed day"
        )

    # 2) People-row short time is host-local month + hour:minute.
    human_ok = False
    for name in _HUMAN_TIME_HELPERS:
        body = _fn_body(logic, name)
        if body and _human_time_host_local(body):
            human_ok = True
            break
    if not human_ok:
        fail(
            "#268: humanTime (or same helper) must format people-row short times "
            "with host-local month + hour:minute (getHours/getDate or Intl), "
            "not the UTC ISO prefix / T slice"
        )

    # 3) Bubble hour:minute uses the same host-TZ conversion.
    time_ok = False
    for name in _TIME_HELPERS:
        body = _fn_body(app, name) or _fn_body(logic, name)
        if (
            body
            and _PARSE_ISO_UTC.search(body)
            and re.search(r"\bget(?:Hours|Minutes)\s*\(", body)
            and not _FORCED_UTC_TZ.search(body)
        ):
            time_ok = True
            break
    if not time_ok:
        fail(
            "#268: bubble hour:minute must use the host timezone "
            "(parse ISO as UTC, then getHours/getMinutes) so the caption "
            "agrees with the local day heading"
        )

    # 4) Storage / api.ts sent_at and last_activity_at stay ISO strings.
    api_path = crate / "web" / "lib" / "api.ts"
    if not api_path.is_file():
        fail("#268: web/lib/api.ts required (sent_at / last_activity_at stay ISO UTC)")
    api = api_path.read_text()
    if not re.search(r"\blast_activity_at\??\s*:\s*string", api):
        fail(
            "#268: api.ts last_activity_at must stay an ISO UTC string "
            "(do not rewrite stored timestamps)"
        )
    if not re.search(r"\bsent_at\??\s*:\s*string", api):
        fail(
            "#268: api.ts sent_at must stay an ISO UTC string "
            "(do not rewrite stored timestamps)"
        )
    if re.search(r"\b(?:sent_at|last_activity_at)\??\s*:\s*Date\b", api):
        fail("#268: api.ts sent_at / last_activity_at must stay ISO strings, not Date")

    # 5) No timezone picker. No tzdata / network TZ database.
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    if _TZ_PICKER.search(app) or _TZ_PICKER.search(search):
        fail("#268: no timezone picker")
    dep_files = (
        repo_root() / "Cargo.toml",
        crate / "Cargo.toml",
        repo_root() / "crates" / "interlace-core" / "Cargo.toml",
        crate / "package.json",
    )
    for dep in dep_files:
        if dep.is_file() and _TZDATA_DEP.search(dep.read_text()):
            fail("#268: no tzdata / network TZ database / tzdata crate")
    if _TZDATA_DEP.search(cleaned):
        fail("#268: no tzdata / network TZ database / tzdata crate")

    # 6) Search type=date from/to filters stay.
    if not search_path.is_file():
        fail("#268: SearchPane.svelte required (type=date from/to filters stay)")
    if not _SEARCH_TYPE_DATE.search(search):
        fail(
            "#268: Search type=date filters must still exist "
            "(do not remove or rewrite from/to)"
        )
    if not re.search(r"\bid=[\"']from[\"']", search) or not re.search(
        r"\bid=[\"']to[\"']", search
    ):
        fail(
            "#268: Search type=date from/to filters must still exist "
            "(do not remove or rewrite them)"
        )

    # 7) Docs: display follows the host / Mac timezone; storage stays UTC.
    if not dtxt.strip():
        fail(
            "#268: docs/user/app.md required — display follows the host / Mac "
            "timezone; storage stays UTC"
        )
    if not re.search(
        r"("
        r"(?:follow|follows|use|uses)\s+(?:the\s+)?(?:host|Mac)(?:'s)?\s+time\s*zone"
        r"|display.{0,80}(?:host|Mac).{0,24}time\s*zone"
        r"|(?:host|Mac)(?:'s)?\s+time\s*zone.{0,60}(?:display|heading|people)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#268: docs/user/app.md must say display follows the host / Mac timezone"
        )
    if re.search(
        r"("
        r"days are\s+UTC"
        r"|day headings are UTC"
        r"|not the host time\s*zone"
        r")",
        dtxt,
        re.I,
    ):
        fail(
            "#268: docs/user/app.md must not say timeline days are UTC / "
            "not the host timezone"
        )
    if not re.search(
        r"("
        r"(?:stor(?:e|age|ed)|archive JSON|SQLite).{0,80}UTC"
        r"|UTC.{0,80}(?:stor(?:e|age|ed)|archive JSON|SQLite)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail("#268: docs/user/app.md must say storage stays UTC")
    if re.search(r"timezone picker|time-zone picker", dtxt, re.I):
        fail("#268: no timezone picker (docs must not add one)")

    # 8) Typed helper body is visible (`: string {` is the body, not a type).
    _assert_typed_fn_body_visible()
    if not (_fn_body(logic, "localDay") or _fn_body(app, "localDay")).strip():
        fail(
            "#268: localDay helper body must be visible "
            "(including with a : string return type)"
        )

    # 9) WhatsApp / wall-clock escape AND Gmail / zoned Date + local getters.
    saw_split_helper = False
    for name in _split_tz_helper_names():
        body = (
            _helper_with_callees(logic, name)
            or _fn_body(logic, name)
            or _fn_body(app, name)
        )
        if not body.strip():
            continue
        saw_split_helper = True
        if not _whatsapp_escape_ok(body):
            fail(
                "#268: day/time helper "
                f"{name} must mention a whatsapp (or wall-clock / export) "
                "branch — do not Date-convert every ISO"
            )
        if not _zoned_gmail_ok(body):
            fail(
                "#268: day/time helper "
                f"{name} must still parse zoned/Gmail ISO with new Date + "
                "local getters — do not only slice(0, 10) every ISO"
            )
    if not saw_split_helper:
        fail(
            "#268: day/time helpers (localDay / humanTime / utcTime) "
            "must exist so WhatsApp wall-clock and Gmail zoned paths can split"
        )

    # 10) Timeline / Search sent_at call sites pass platform. last_activity_at
    #     has no Person.platform — omit is the wall-clock path; do not require it.
    tl_has_platform = False
    search_has_platform = False
    for name in _split_tz_helper_names():
        for args in _helper_call_args(app, name):
            if re.search(r"\bsent_at\b", args) and not re.search(
                r"\bplatform\b", args
            ):
                fail(
                    "#268: Timeline / Search day-time helpers must pass "
                    "platform (row.platform / h.platform) so WhatsApp "
                    "wall-clock and Gmail zoned paths can split"
                )
            if re.search(r"\bplatform\b", args):
                tl_has_platform = True
        for args in _helper_call_args(search, name):
            if re.search(r"\bsent_at\b", args) and not re.search(
                r"\bplatform\b", args
            ):
                fail(
                    "#268: Timeline / Search day-time helpers must pass "
                    "platform (row.platform / h.platform) so WhatsApp "
                    "wall-clock and Gmail zoned paths can split"
                )
            if re.search(r"\bplatform\b", args):
                search_has_platform = True
    if not tl_has_platform or not search_has_platform:
        fail(
            "#268: Timeline / Search day-time helpers must pass "
            "platform (row.platform / h.platform) so WhatsApp "
            "wall-clock and Gmail zoned paths can split"
        )

    # 11) Docs: WhatsApp wall-clock; Gmail / zoned follow Mac TZ; storage UTC.
    if not _DOCS_WA_WALL.search(dtxt):
        fail(
            "#268: docs/user/app.md must say WhatsApp export times "
            "display as wall-clock"
        )
    if not _DOCS_GMAIL_ZONE.search(dtxt):
        fail(
            "#268: docs/user/app.md must say Gmail / zoned times "
            "follow the Mac timezone"
        )


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


def _svelte_snippet_body(src: str, name: str) -> str:
    """Body of `{#snippet name …}…{/snippet}` (no nested snippet support)."""
    head = re.search(rf"\{{#snippet\s+{re.escape(name)}\b[^}}]*\}}", src)
    if not head:
        return ""
    end = src.find("{/snippet}", head.end())
    if end < 0:
        return src[head.end() :]
    return src[head.end() : end]


def _person_detail_with_renders(app: str) -> str:
    """Person-column markup plus any `{@render snippet()}` bodies it invokes."""
    detail = _person_detail_markup(app)
    extra: list[str] = []
    for m in re.finditer(r"\{@render\s+([A-Za-z_]\w*)\s*\(", detail):
        extra.append(_svelte_snippet_body(app, m.group(1)))
    return detail + ("\n" + "\n".join(extra) if extra else "")


# #115 — platform chip on timeline bubbles + All | platform toolbar filter.
_PLATFORM_CHIP = re.compile(
    r"("
    r"data-platform-chip"
    r"|platform-chip"
    r"|platformChip"
    r"|class:[A-Za-z0-9_-]*chip\b"
    r"|class=[\"'][^\"']*\b(?:platform-)?chip\b"
    r"|class=[\"'][^\"']*\bbadge\b"
    r"|class:badge\b"
    r"|class=\{[^}]*(?:chip|badge)[^}]*\}"
    r")",
    re.I,
)
_PLATFORM_CHIP_NEAR = re.compile(
    r"("
    r"data-platform-chip"
    r"|platform-chip"
    r"|platformChip"
    r"|\bchip\b[^;{]{0,160}(?:\.platform\b|platformLabel|platform)"
    r"|(?:\.platform\b|platformLabel|platform)[^;{]{0,160}\bchip\b"
    r"|\bbadge\b[^;{]{0,160}(?:\.platform\b|platformLabel|platform)"
    r"|(?:\.platform\b|platformLabel|platform)[^;{]{0,160}\bbadge\b"
    r")",
    re.I | re.S,
)
_REMOTE_PLATFORM_IMG = re.compile(
    r"<img\b[^>]{0,400}https?://[^>]{0,200}"
    r"(?:logo|brand|whatsapp|gmail|favicon|cdn)",
    re.I | re.S,
)
_REMOTE_PLATFORM_URL = re.compile(
    r"url\(\s*['\"]?https?://[^)]*(?:logo|brand|whatsapp|gmail|cdn)",
    re.I,
)
_PLATFORM_FILTER_STATE = re.compile(
    r"\b(?:"
    r"selectedPlatform|platformFilter|timelinePlatform|tlPlatform|"
    r"platformTab|activePlatform|pickedPlatform|filterPlatform|"
    r"platformOnly|timelinePlatformFilter"
    r")\b"
)
_PLATFORM_FILTER_HOOK = re.compile(
    r"(data-platform-filter|id=[\"']platform-filter[\"']|"
    r"data-timeline-platform|class=[\"'][^\"']*platform-filter)",
    re.I,
)
_PLATFORM_TOOLBAR_ALL = re.compile(
    r"("
    r">\s*All\s*<"
    r"|[\"']All[\"']"
    r"|platformFilter\s*===\s*[\"']all[\"']"
    r"|selectedPlatform\s*(?:===?|==)\s*(?:null|undefined|[\"']all[\"'])"
    r")",
    re.I,
)
_PRETTY_PLATFORM_MAP = re.compile(
    r"("
    r"[\"']whatsapp[\"']\s*[:=]\s*[\"']WhatsApp[\"']"
    r"|[\"']gmail[\"']\s*[:=]\s*[\"']Gmail[\"']"
    r"|case\s+[\"']whatsapp[\"']\s*:[^;]{0,40}WhatsApp"
    r"|case\s+[\"']gmail[\"']\s*:[^;]{0,40}Gmail"
    r"|platform\s*===\s*[\"']whatsapp[\"'][^?]{0,40}\?\s*[\"']WhatsApp[\"']"
    r"|platform\s*===\s*[\"']gmail[\"'][^?]{0,40}\?\s*[\"']Gmail[\"']"
    r")",
    re.I,
)
# Client-side: keep row when All or row.platform matches the selection.
_CLIENT_PLATFORM_FILTER = re.compile(
    r"("
    r"\.filter\s*\(\s*(?:\(?)(?:row|r|item|m|msg|t|tl)[^)]{0,80}"
    r"\.platform\b"
    r"|(?:row|r|item|m)\.platform\s*===?\s*(?:selectedPlatform|platformFilter|"
    r"timelinePlatform|tlPlatform|activePlatform|pickedPlatform|filterPlatform|"
    r"platformOnly|p|plat)\b"
    r"|(?:selectedPlatform|platformFilter|timelinePlatform|tlPlatform|"
    r"activePlatform|pickedPlatform|filterPlatform|platformOnly)"
    r"\s*===?\s*(?:row|r|item|m)\.platform\b"
    r"|(?:selectedPlatform|platformFilter|timelinePlatform|tlPlatform|"
    r"activePlatform|filterPlatform)\s*(?:===?|==)\s*[\"']all[\"']"
    r"[^|]{0,80}\|\|"
    r")",
    re.I | re.S,
)
# API / core: personTimeline({ … platform: … }) or person_timeline platform arg.
_API_PLATFORM_FILTER = re.compile(
    r"("
    r"personTimeline\s*\(\s*\{[^}]{0,400}\bplatform\s*:"
    r"|\bplatform\s*:\s*(?:selectedPlatform|platformFilter|timelinePlatform|"
    r"tlPlatform|activePlatform|filterPlatform|null)"
    r")",
    re.I | re.S,
)
# Toolbar options come from this person's conversations / timeline platforms.
_PLATFORM_OPTIONS_FROM_DATA = re.compile(
    r"("
    r"(?:conversations|convos|timeline|personConversations|conversationList)"
    r"\s*(?:\?\.|\.)\s*(?:map|flatMap|reduce|forEach|filter)\s*\([^)]{0,120}"
    r"\.platform\b"
    r"|\.platform\b[\s\S]{0,100}(?:Set|unique|uniq|platformsFor|personPlatforms|"
    r"availablePlatforms|timelinePlatforms|presentPlatforms)"
    r"|(?:Set|unique|uniq|platformsFor|personPlatforms|availablePlatforms|"
    r"timelinePlatforms|presentPlatforms|platformOptions)"
    r"[\s\S]{0,180}\.platform\b"
    r"|new\s+Set\s*\([^)]{0,200}\.platform\b"
    r"|for\s*\(\s*(?:const|let)\s+\w+\s+of\s+"
    r"(?:conversations|convos|timeline|personConversations)\b[^)]{0,80}\)"
    r"[\s\S]{0,220}\.platform\b"
    r"|(?:conversations|convos|timeline|personConversations)"
    r"[\s\S]{0,220}\.platform\b[\s\S]{0,80}(?:add|push|Set)"
    r"|\{#each\s+(?:availablePlatforms|platformOptions|presentPlatforms|"
    r"personPlatforms|timelinePlatforms)\b"
    r")",
    re.I | re.S,
)
# Hard-coded forever list of invented platforms (slack/discord/telegram/signal…)
# used as the toolbar source without deriving from the person.
_INVENTED_PLATFORM_LIST = re.compile(
    r"\[\s*[\"'](?:whatsapp|gmail|contacts)[\"']\s*,\s*"
    r"[\"'](?:whatsapp|gmail|contacts|telegram|signal|slack|discord|imessage|"
    r"sms|messenger|instagram|twitter)[\"']"
    r"[^\]]{0,200}\]",
    re.I,
)

# #116 — conversation kind filter (All | dm | email_thread | group).
_KIND_FILTER_STATE = re.compile(
    r"\b(?:"
    r"kindFilter|conversationKindFilter|timelineKind|tlKind|"
    r"selectedKind|activeKind|pickedKind|filterKind|"
    r"kindOnly|timelineKindFilter|conversationKind|"
    r"kindTab|selectedConversationKind"
    r")\b"
)
_KIND_FILTER_HOOK = re.compile(
    r"(data-kind-filter|id=[\"']kind-filter[\"']|"
    r"data-timeline-kind|class=[\"'][^\"']*kind-filter|"
    r"aria-label=[\"'][^\"']*[Kk]ind)",
    re.I,
)
_KIND_TOOLBAR_ALL = re.compile(
    r"("
    r">\s*All\s*<"
    r"|[\"']All[\"']"
    r"|kindFilter\s*===\s*[\"']all[\"']"
    r"|conversationKindFilter\s*===\s*[\"']all[\"']"
    r"|selectedKind\s*(?:===?|==)\s*(?:null|undefined|[\"']all[\"'])"
    r"|timelineKind\s*(?:===?|==)\s*(?:null|undefined|[\"']all[\"'])"
    r")",
    re.I,
)
# Pretty labels or raw archive kinds in helpers / options (not required all-at-once).
_KIND_OPT_DM = re.compile(
    r"("
    r">\s*DMs?\s*<"
    r"|[\"']DMs?[\"']"
    r"|[\"']dm[\"']"
    r")",
    re.I,
)
_KIND_OPT_EMAIL = re.compile(
    r"("
    r">\s*Email(?:\s+threads?)?\s*<"
    r"|[\"']Email(?:\s+threads?)?[\"']"
    r"|[\"']email_thread[\"']"
    r"|[\"']email[\"']"
    r")",
    re.I,
)
_KIND_OPT_GROUP = re.compile(
    r"("
    r">\s*Groups?\s*<"
    r"|[\"']Groups?[\"']"
    r"|[\"']group[\"']"
    r")",
    re.I,
)
# Kind toolbar options come from this person's conversations / timeline kinds.
# Dynamic {#each availableKinds} is OK for chrome, but the list itself must be
# harvested from data (not a hard-coded forever All|DMs|Email|Groups matrix).
# PersonConversation uses `.kind`; TimelineRow uses `.conversation_kind`.
# Require collecting into a Set/array (add/push) so the filteredTimeline row
# filter alone is not mistaken for option derivation.
_KIND_OPTIONS_FROM_DATA = re.compile(
    r"("
    r"for\s*\(\s*(?:const|let)\s+\w+\s+of\s+"
    r"(?:conversations|convos|timeline|personConversations)\b[^)]{0,80}\)"
    r"[\s\S]{0,220}\.(?:conversation_kind|kind)\b[\s\S]{0,80}(?:\.add\b|push\s*\()"
    r"|(?:availableKinds|kindOptions|presentKinds|personKinds|timelineKinds|"
    r"kindsPresent)\b[\s\S]{0,500}"
    r"(?:for\s*\(\s*(?:const|let)\s+\w+\s+of\s+"
    r"(?:conversations|convos|timeline|personConversations)\b"
    r"|(?:conversations|convos|timeline|personConversations)\s*"
    r"(?:\?\.|\.)\s*(?:map|flatMap|reduce|forEach)\b)"
    r"[\s\S]{0,240}\.(?:conversation_kind|kind)\b"
    r"|(?:conversations|convos|timeline|personConversations)\s*"
    r"(?:\?\.|\.)\s*(?:map|flatMap)\s*\(\s*\w+\s*=>\s*\w+\.(?:conversation_kind|kind)\b"
    r"|new\s+Set\s*\(\s*(?:conversations|convos|timeline|personConversations)"
    r"\s*(?:\?\.|\.)\s*map\s*\([^)]{0,80}\.(?:conversation_kind|kind)\b"
    r")",
    re.I | re.S,
)
# Forever-hard-coded kind toolbar: static onclick targets for dm + email_thread +
# group without a data-derived options list (WhatsApp path must not force Email).
_STATIC_KIND_MATRIX = re.compile(
    r"(?:kindFilter|conversationKindFilter|timelineKind|selectedKind|filterKind)"
    r"\s*=\s*[\"']dm[\"']"
    r"[\s\S]{0,500}"
    r"(?:kindFilter|conversationKindFilter|timelineKind|selectedKind|filterKind)"
    r"\s*=\s*[\"']email_thread[\"']"
    r"[\s\S]{0,500}"
    r"(?:kindFilter|conversationKindFilter|timelineKind|selectedKind|filterKind)"
    r"\s*=\s*[\"']group[\"']",
    re.I,
)
# Client-side: keep row when All or row.conversation_kind matches.
_CLIENT_KIND_FILTER = re.compile(
    r"("
    r"\.filter\s*\(\s*(?:\(?)(?:row|r|item|m|msg|t|tl|x)[^)]{0,100}"
    r"\.conversation_kind\b"
    r"|(?:row|r|item|m|x)\.conversation_kind\s*===?\s*"
    r"(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
    r"selectedKind|activeKind|pickedKind|filterKind|kindOnly|k|kind)\b"
    r"|(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
    r"selectedKind|activeKind|pickedKind|filterKind|kindOnly)"
    r"\s*===?\s*(?:row|r|item|m|x)\.conversation_kind\b"
    r"|(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
    r"selectedKind|filterKind|kindOnly)"
    r"\s*(?:===?|==)\s*[\"']all[\"']"
    r"[^|]{0,100}\|\|"
    r"|conversation_kind\s*===?\s*[\"'](?:dm|email_thread|group)[\"']"
    r")",
    re.I | re.S,
)
# Derived list that reads conversation_kind (filteredTimeline / visibleTimeline…).
_DERIVED_KIND_FILTER = re.compile(
    r"("
    r"(?:filteredTimeline|visibleTimeline|timelineRows|kindRows|"
    r"shownTimeline|displayTimeline|tlRows|visibleRows)"
    r"[^;]{0,400}\.conversation_kind\b"
    r"|\.conversation_kind\b[^;]{0,300}"
    r"(?:filteredTimeline|visibleTimeline|kindRows|displayTimeline|"
    r"shownTimeline|tlRows)"
    r")",
    re.I | re.S,
)
# API / core: personTimeline({ … kind: … }) — optional; client-side is enough.
_API_KIND_FILTER = re.compile(
    r"("
    r"personTimeline\s*\(\s*\{[^}]{0,400}\b(?:kind|conversation_kind)\s*:"
    r"|\b(?:kind|conversationKind)\s*:\s*(?:kindFilter|conversationKindFilter|"
    r"timelineKind|tlKind|selectedKind|activeKind|filterKind|null)"
    r")",
    re.I | re.S,
)
# Platform and kind both participate in the same filter path (AND).
_COMBINED_FILTER_PATH = re.compile(
    r"("
    # Single filter callback / expression that mentions both fields.
    r"\.filter\s*\([^)]{0,200}\.platform\b[^)]{0,200}\.conversation_kind\b"
    r"|\.filter\s*\([^)]{0,200}\.conversation_kind\b[^)]{0,200}\.platform\b"
    # Derived list that chains / includes both predicates nearby.
    r"|(?:filteredTimeline|visibleTimeline|timelineRows|shownTimeline|"
    r"displayTimeline|tlRows)"
    r"[^;]{0,500}\.platform\b[^;]{0,500}\.conversation_kind\b"
    r"|(?:filteredTimeline|visibleTimeline|timelineRows|shownTimeline|"
    r"displayTimeline|tlRows)"
    r"[^;]{0,500}\.conversation_kind\b[^;]{0,500}\.platform\b"
    # Both filter states referenced near the same derived / filter site.
    r"|(?:platformFilter|selectedPlatform|timelinePlatform|tlPlatform|"
    r"activePlatform|filterPlatform)"
    r"[^;]{0,400}"
    r"(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
    r"selectedKind|filterKind|kindOnly)"
    r"|(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
    r"selectedKind|filterKind|kindOnly)"
    r"[^;]{0,400}"
    r"(?:platformFilter|selectedPlatform|timelinePlatform|tlPlatform|"
    r"activePlatform|filterPlatform)"
    r")",
    re.I | re.S,
)
# j/k / highlight use indices from the filtered (visible) list.
_VISIBLE_KIND_JK = re.compile(
    r"("
    r"visibleTlIndices|visibleIndices|visibleTimeline|filteredTimeline"
    r"|nearestVisibleTlIndex"
    r")",
    re.I,
)
# Empty when the *filtered* timeline is empty (not only the raw unfiltered list).
_FILTERED_EMPTY = re.compile(
    r"("
    r"(?:filteredTimeline|visibleTimeline|timelineRows|kindRows|"
    r"shownTimeline|displayTimeline|tlRows|visibleRows)"
    r"\s*(?:\?\.|\.)?\s*length\s*===?\s*0"
    r"|!\s*(?:filteredTimeline|visibleTimeline|timelineRows|kindRows|"
    r"shownTimeline|displayTimeline|tlRows|visibleRows)"
    r"\s*(?:\?\.|\.)?\s*length"
    r"|(?:filteredTimeline|visibleTimeline|timelineRows|kindRows|"
    r"shownTimeline|displayTimeline|tlRows|visibleRows)"
    r"\s*\.length\s*(?:===?|==)\s*0"
    r"|(?:filteredTimeline|visibleTimeline)\s*\.length\s*===\s*0"
    r")",
    re.I,
)
# Kind=group must not force includeGroups on / bypass the D18 groups gate.
_KIND_BYPASS_GROUPS = re.compile(
    r"("
    r"(?:kindFilter|conversationKindFilter|timelineKind|selectedKind|filterKind)"
    r"[^;]{0,120}===?\s*[\"']group[\"'][^;]{0,160}"
    r"includeGroups\s*=\s*true"
    r"|includeGroups\s*=\s*true[^;]{0,160}"
    r"(?:kindFilter|conversationKindFilter|timelineKind|selectedKind|filterKind)"
    r"[^;]{0,80}===?\s*[\"']group[\"']"
    r"|(?:kindFilter|conversationKindFilter|selectedKind)\s*===?\s*[\"']group[\"']"
    r"[^;]{0,200}personTimeline\s*\([^)]{0,200}includeGroups\s*:\s*true"
    r")",
    re.I | re.S,
)


def assert_timeline_platform_chips(crate: Path) -> None:
    """#115: platform chip on each bubble + All + data-derived platform toolbar.

    Acceptance: “WhatsApp only” hides Gmail for that person. Chip is text/badge,
    not a remote CDN brand image. Toolbar offers All plus only platforms present
    for this person (from conversations / timeline) — dynamic {#each} is OK;
    a forever-visible WhatsApp+Gmail button matrix is not required. Client filter
    on row.platform is OK; API/core platform arg also OK when paging.
    """
    app = (crate / "web" / "App.svelte").read_text()
    logic = _web_logic(crate)
    api_src = (crate / "web" / "lib" / "api.ts").read_text()
    whole = app + "\n" + logic
    cleaned = _without_comments(whole)
    block = _timeline_block(crate)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    detail = _person_detail_markup(app)

    # 1) Bubble/row shows platform as a chip/badge — not only bare caption text.
    chip_in_row = bool(_PLATFORM_CHIP.search(block)) and (
        "platform" in block or "platformLabel" in block or "PlatformChip" in block
    )
    if not chip_in_row:
        chip_in_row = bool(_PLATFORM_CHIP_NEAR.search(block))
    if not chip_in_row:
        # Dedicated chip component used from the row (markup may live next door).
        chip_component = bool(
            re.search(
                r"<(?:PlatformChip|platform-chip)\b|data-platform-chip",
                block,
                re.I,
            )
        ) or (
            bool(re.search(r"data-platform-chip|PlatformChip|platform-chip", blob, re.I))
            and bool(
                re.search(
                    r"<(?:PlatformChip|platform-chip)\b|data-platform-chip",
                    block + "\n" + cleaned,
                    re.I,
                )
            )
        )
        if not chip_component:
            fail(
                "#115: each timeline bubble/row must show platform as a chip "
                "(text chip / badge / data-platform-chip), not only bare caption "
                "text like {row.platform}"
            )
    if not re.search(r"\.platform\b|platformLabel|row\.platform", block + "\n" + cleaned):
        fail("#115: chip must still come from the row/conversation platform field")

    # 2) Chip is not a remote image / CDN brand logo.
    timeline_chrome = block + "\n" + detail
    if _REMOTE_PLATFORM_IMG.search(timeline_chrome) or _REMOTE_PLATFORM_IMG.search(blob):
        fail("#115: platform chip must not be a remote <img> / CDN brand logo")
    if _REMOTE_PLATFORM_URL.search(blob):
        fail("#115: platform chip must not load brand logos via url(https://…)")
    if re.search(
        r"<img\b[^>]{0,200}(?:platform|whatsapp|gmail)[^>]{0,200}"
        r"src\s*=\s*[\"']https?://",
        blob,
        re.I | re.S,
    ):
        fail("#115: platform chip must not be an http(s) image (text chip only)")

    # Pretty labels (WhatsApp / Gmail) are OK; raw whatsapp/gmail also OK on chip.
    has_pretty = bool(_PRETTY_WHATSAPP.search(cleaned) and _PRETTY_GMAIL.search(cleaned))
    has_map = bool(_PRETTY_PLATFORM_MAP.search(cleaned))
    if not (has_pretty or has_map or _RAW_WHATSAPP.search(block)):
        # Still require some platform surface on the row.
        if "row.platform" not in block and ".platform" not in block:
            fail(
                "#115: chip may use pretty labels (WhatsApp / Gmail) or raw "
                "platform; must still bind the row platform"
            )

    # 3) Platform filter toolbar: All + data-derived options (not conversation switcher alone).
    # Dynamic {#each availablePlatforms} is OK — do not require WhatsApp and Gmail
    # as always-rendered static buttons for every person.
    has_filter_state = bool(_PLATFORM_FILTER_STATE.search(cleaned))
    has_filter_hook = bool(_PLATFORM_FILTER_HOOK.search(blob))
    toolbar_blob = detail if detail.strip() else app
    # Exclude the message {#each} body so conversation switcher / caption is not enough.
    toolbar_only = toolbar_blob
    for m in _EACH_TIMELINE.finditer(toolbar_blob):
        end = _matching_each_end(toolbar_blob, m.start())
        if end > m.start():
            toolbar_only = toolbar_only.replace(toolbar_blob[m.start() : end], "", 1)
    has_toolbar_all = bool(_PLATFORM_TOOLBAR_ALL.search(toolbar_only)) or bool(
        _PLATFORM_TOOLBAR_ALL.search(cleaned)
    )
    has_dynamic_each = bool(
        re.search(
            r"\{#each\s+(?:availablePlatforms|platformOptions|presentPlatforms|"
            r"personPlatforms|timelinePlatforms|platformsFor)\b",
            toolbar_only + "\n" + app,
            re.I,
        )
    )
    options_from_data = bool(_PLATFORM_OPTIONS_FROM_DATA.search(cleaned))
    if not (has_filter_state or has_filter_hook):
        fail(
            "#115: person timeline must have a platform filter toolbar state "
            "(selectedPlatform / platformFilter / data-platform-filter) — "
            "All + platforms present for this person"
        )
    if not has_toolbar_all:
        fail(
            "#115: platform filter toolbar must offer All when the platform "
            "dimension is active (default = every platform)"
        )
    if not options_from_data:
        fail(
            "#115: platform toolbar options must come from platforms present for "
            "this person (unique platform values from conversations / timeline "
            "via map/Set/for…of), not a hard-coded forever list"
        )
    # Labels / raw values may live only in a helper; dynamic each is enough chrome.
    if not (
        has_dynamic_each
        or has_pretty
        or has_map
        or re.search(
            r"(?:platformFilter|selectedPlatform|timelinePlatform|tlPlatform|"
            r"activePlatform|filterPlatform|platformOnly)[^;]{0,200}"
            r"[\"'](?:whatsapp|gmail)[\"']",
            cleaned,
            re.I | re.S,
        )
        or re.search(r">\s*(?:WhatsApp|Gmail)\s*<|[\"'](?:WhatsApp|Gmail)[\"']", cleaned)
    ):
        fail(
            "#115: platform filter must surface platform options "
            "(data-derived {#each}, pretty labels, or raw platform values)"
        )

    # Default selection is All (null / undefined / "all").
    if not re.search(
        r"(?:selectedPlatform|platformFilter|timelinePlatform|tlPlatform|"
        r"activePlatform|pickedPlatform|filterPlatform|platformOnly|"
        r"timelinePlatformFilter)"
        r"\s*=\s*\$state\s*(?:<[^>]*>)?\s*\(\s*(?:null|undefined|[\"']all[\"'])",
        cleaned,
        re.I,
    ) and not re.search(
        r"(?:selectedPlatform|platformFilter|timelinePlatform|tlPlatform|"
        r"activePlatform|filterPlatform|platformOnly)"
        r"\s*=\s*(?:null|undefined|[\"']all[\"'])",
        cleaned,
        re.I,
    ):
        fail(
            "#115: platform filter must default to All "
            "(selected platform state starts null / undefined / \"all\")"
        )

    # 4) Filtering WhatsApp excludes other platforms (client row.platform or API arg).
    client_ok = bool(_CLIENT_PLATFORM_FILTER.search(cleaned))
    api_ok = bool(_API_PLATFORM_FILTER.search(cleaned))
    # Also accept derived list filtered by platform before {#each}.
    derived_ok = bool(
        re.search(
            r"(?:filteredTimeline|visibleTimeline|timelineRows|platformRows|"
            r"shownTimeline|displayTimeline|tlRows)"
            r"[^;]{0,300}\.platform\b"
            r"|\.platform\b[^;]{0,200}"
            r"(?:filteredTimeline|visibleTimeline|platformRows|displayTimeline)",
            cleaned,
            re.I | re.S,
        )
    )
    if not (client_ok or api_ok or derived_ok):
        fail(
            "#115: “WhatsApp only” must hide other platforms for that person "
            "(filter timeline rows by row.platform client-side, or pass platform "
            "into personTimeline / the core query so Load older stays consistent)"
        )

    # If filter is pushed into the API, personTimeline args must accept platform.
    if api_ok:
        api_args = re.search(
            r"personTimeline\s*:\s*\(\s*args\s*:\s*\{([^}]*)\}",
            api_src,
            re.S,
        )
        if not api_args or not re.search(r"\bplatform\b", api_args.group(1)):
            fail(
                "#115: personTimeline args must include optional platform when "
                "the UI passes a platform filter into the timeline query"
            )

    # 5) Only platforms present for this person — not a hard-coded invented forever-list.
    # (options_from_data already required in §3; still reject invented-only lists.)
    for m in _INVENTED_PLATFORM_LIST.finditer(cleaned):
        window = cleaned[max(0, m.start() - 80) : m.end() + 80]
        if re.search(
            r"platformFilter|selectedPlatform|platformOptions|toolbar|platforms\s*=",
            window,
            re.I,
        ) and not _PLATFORM_OPTIONS_FROM_DATA.search(
            cleaned[max(0, m.start() - 400) : m.end() + 400]
        ):
            fail(
                "#115: do not invent toolbar platforms (slack/discord/…) — "
                "only offer platforms that exist for this person"
            )


def assert_timeline_kind_filter(crate: Path) -> None:
    """#116: All + data-derived kind filter, AND with platform filter.

    Acceptance: Email-only shows conversation_kind === email_thread only.
    Kind toolbar options come from kinds present for this person (conversations /
    timeline) — dynamic {#each} is OK; a forever-visible All|DMs|Email|Groups
    button matrix is not required (WhatsApp path must not force Email threads
    buttons into the markup). Empty state when the combined filter yields no rows.
    Load older must not be required / shown under that empty filtered view.
    Groups still need include-groups (kind=Groups must not invent group rows).
    j/k walks visible (combined-filtered) indices. Client-side like #115 is OK.
    """
    app = (crate / "web" / "App.svelte").read_text()
    logic = _web_logic(crate)
    api_src = (crate / "web" / "lib" / "api.ts").read_text()
    whole = app + "\n" + logic
    cleaned = _without_comments(whole)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    detail = _person_detail_markup(app)

    # 1) Kind filter toolbar state / hook (distinct from the #114 conversation switcher).
    has_filter_state = bool(_KIND_FILTER_STATE.search(cleaned))
    has_filter_hook = bool(_KIND_FILTER_HOOK.search(blob))
    if not (has_filter_state or has_filter_hook):
        fail(
            "#116: person timeline must have a conversation-kind filter "
            "(kindFilter / conversationKindFilter / data-kind-filter) — "
            "All + kinds present for this person"
        )

    # Toolbar chrome: All for the active kind dimension. Kind chips themselves
    # must be data-derived (not a forever-hard-coded full matrix always in DOM).
    toolbar_blob = detail if detail.strip() else app
    toolbar_only = toolbar_blob
    for m in _EACH_TIMELINE.finditer(toolbar_blob):
        end = _matching_each_end(toolbar_blob, m.start())
        if end > m.start():
            toolbar_only = toolbar_only.replace(toolbar_blob[m.start() : end], "", 1)
    has_toolbar_all = bool(_KIND_TOOLBAR_ALL.search(toolbar_only)) or bool(
        _KIND_TOOLBAR_ALL.search(cleaned)
    )
    options_from_data = bool(_KIND_OPTIONS_FROM_DATA.search(cleaned))
    has_dynamic_each = bool(
        re.search(
            r"\{#each\s+(?:availableKinds|kindOptions|presentKinds|personKinds|"
            r"timelineKinds|kindsPresent)\b",
            toolbar_only + "\n" + app,
            re.I,
        )
    )
    if not has_toolbar_all:
        fail(
            "#116: kind filter must offer All when the kind dimension is active "
            "(default = every kind / D18 merged)"
        )
    if not options_from_data:
        fail(
            "#116: kind toolbar options must come from kind / conversation_kind "
            "values present for this person (conversations / timeline via "
            "map/Set/for…of into availableKinds), not a hard-coded forever "
            "All|DMs|Email|Groups matrix always rendered for every person"
        )
    # Static onclick matrix for dm + email_thread + group always in the toolbar
    # forces Email threads under a WhatsApp-only person — reject that.
    if _STATIC_KIND_MATRIX.search(toolbar_only):
        fail(
            "#116: do not hard-code always-rendered DMs + Email threads + Groups "
            "buttons — derive kind chips from this person's conversation_kind "
            "values (dynamic {#each} is OK; WhatsApp must not force Email threads)"
        )
    # Pretty labels / raw archive kinds may live in a helper map; not all required
    # to be visible at once. At least one known kind token should exist for UX.
    has_kind_token = bool(
        _KIND_OPT_DM.search(cleaned)
        or _KIND_OPT_EMAIL.search(cleaned)
        or _KIND_OPT_GROUP.search(cleaned)
        or re.search(r"[\"'](?:dm|email_thread|group)[\"']", cleaned)
    )
    if not (has_kind_token or has_dynamic_each):
        fail(
            "#116: kind filter must be able to select archive kinds "
            "(dm / email_thread / group labels or values, or {#each} over them)"
        )

    # Default selection is All (null / undefined / "all").
    if not re.search(
        r"(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
        r"selectedKind|activeKind|pickedKind|filterKind|kindOnly|"
        r"timelineKindFilter|selectedConversationKind)"
        r"\s*=\s*\$state\s*(?:<[^>]*>)?\s*\(\s*(?:null|undefined|[\"']all[\"'])",
        cleaned,
        re.I,
    ) and not re.search(
        r"(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
        r"selectedKind|activeKind|filterKind|kindOnly)"
        r"\s*=\s*(?:null|undefined|[\"']all[\"'])",
        cleaned,
        re.I,
    ):
        fail(
            "#116: kind filter must default to All "
            "(kind state starts null / undefined / \"all\")"
        )

    # 2) Filtering by kind keeps only matching conversation_kind rows.
    client_ok = bool(_CLIENT_KIND_FILTER.search(cleaned))
    derived_ok = bool(_DERIVED_KIND_FILTER.search(cleaned))
    api_ok = bool(_API_KIND_FILTER.search(cleaned))
    if not (client_ok or derived_ok or api_ok):
        fail(
            "#116: Email-only must show email_thread rows only "
            "(filter timeline rows by row.conversation_kind client-side, "
            "or pass kind into personTimeline / the core query)"
        )
    # Prefer conversation_kind field (archive / TimelineRow), not invented labels alone.
    if not re.search(r"\bconversation_kind\b", cleaned):
        fail(
            "#116: kind filter must key off conversation_kind on timeline rows "
            "(dm / group / email_thread)"
        )

    if api_ok:
        api_args = re.search(
            r"personTimeline\s*:\s*\(\s*args\s*:\s*\{([^}]*)\}",
            api_src,
            re.S,
        )
        if not api_args or not re.search(
            r"\b(?:kind|conversation_kind)\b", api_args.group(1)
        ):
            fail(
                "#116: personTimeline args must include optional kind / "
                "conversation_kind when the UI passes a kind filter into the query"
            )

    # 3) AND with the platform filter — both present on the filter path.
    has_platform = bool(_PLATFORM_FILTER_STATE.search(cleaned)) or bool(
        _PLATFORM_FILTER_HOOK.search(blob)
    )
    if not has_platform:
        fail(
            "#116: platform filter (#115) must remain; kind filter ANDs with it "
            "(Email + WhatsApp keeps only matching rows)"
        )
    if not _COMBINED_FILTER_PATH.search(cleaned):
        fail(
            "#116: kind filter must AND with the platform filter "
            "(same filter path / derived list must consider both "
            "conversation_kind and platform — not replace the platform toolbar)"
        )

    # 4) Groups still require include-groups; kind=Groups must not invent group rows.
    if not _INCLUDE_GROUPS_LABEL.search(app) and not _INCLUDE_GROUPS_LABEL.search(blob):
        fail("#116: include groups toggle must remain (groups still require it)")
    if _KIND_BYPASS_GROUPS.search(cleaned):
        fail(
            "#116: kind=Groups must not force includeGroups=true or bypass the "
            "include-groups gate — groups stay out of the stream when groups are off"
        )
    # Selecting Groups must not be the only way groups appear; includeGroups still gates load.
    if re.search(
        r"(?:kindFilter|conversationKindFilter|selectedKind)\s*===?\s*[\"']group[\"']"
        r"[^;{]{0,200}includeGroups\s*=\s*(?:true|!0|1)\b",
        cleaned,
        re.I | re.S,
    ):
        fail(
            "#116: do not auto-enable include groups when the kind filter is Groups"
        )

    # 5) Empty state when the combined filtered list is empty (email-only, no mail).
    # Raw timeline.length === 0 alone is not enough once filters hide every row.
    # Require EmptyState (or data-empty) in a branch that keys off the *filtered* list,
    # not merely filteredTimeline.length used for day-grouping loops.
    empty_src = app + "\n" + blob
    markup = app
    script_end = app.rfind("</script>")
    if script_end >= 0:
        markup = app[script_end:]
    filtered_empty_cond = re.compile(
        r"("
        r"\{#if\s+[^}]{0,200}"
        r"(?:filteredTimeline|visibleTimeline|timelineRows|displayTimeline|"
        r"shownTimeline|tlRows|visibleRows)"
        r"[^}]{0,80}(?:length|===?\s*0)"
        r"|\{:else\s+if\s+[^}]{0,200}"
        r"(?:filteredTimeline|visibleTimeline|timelineRows|displayTimeline|"
        r"shownTimeline|tlRows|visibleRows)"
        r"[^}]{0,80}(?:length|===?\s*0)"
        r"|(?:filteredTimeline|visibleTimeline|timelineRows|displayTimeline|"
        r"shownTimeline|tlRows|visibleRows)"
        r"\s*(?:\?\.|\.)?\s*length\s*===?\s*0"
        r"|!\s*(?:filteredTimeline|visibleTimeline|timelineRows|displayTimeline|"
        r"shownTimeline|tlRows|visibleRows)"
        r"\s*(?:\?\.|\.)?\s*length"
        r")",
        re.I,
    )
    # Walk markup: filtered-empty condition must sit near EmptyState / data-empty.
    empty_ok = False
    for m in filtered_empty_cond.finditer(markup + "\n" + cleaned):
        window = (markup + "\n" + cleaned)[m.start() : m.end() + 280]
        if re.search(r"EmptyState|data-empty", window, re.I):
            empty_ok = True
            break
    # Script-side flag that drives EmptyState is also OK.
    if not empty_ok and re.search(
        r"(?:filteredEmpty|isFilterEmpty|noVisibleRows|filterEmpty|tlEmpty)\s*=",
        cleaned,
        re.I,
    ):
        if re.search(
            r"(?:filteredEmpty|isFilterEmpty|noVisibleRows|filterEmpty|tlEmpty)"
            r"[\s\S]{0,400}(?:EmptyState|data-empty)"
            r"|(?:EmptyState|data-empty)[\s\S]{0,400}"
            r"(?:filteredEmpty|isFilterEmpty|noVisibleRows|filterEmpty|tlEmpty)",
            empty_src,
            re.I,
        ):
            empty_ok = True
    if not empty_ok:
        fail(
            "#116: when the kind/platform filter yields no rows "
            "(e.g. Email-only and the person has no mail), show an empty state "
            "on the filtered list — not only when the unfiltered timeline is empty"
        )
    # Empty copy should be reachable in the person timeline pane (static presence).
    # `{@render timelinePaneState()}` hosts EmptyState in a snippet above this
    # window; expand renders so we do not require a fake data-empty on the list.
    pane_empty = _person_detail_with_renders(app)
    if not re.search(
        r"EmptyState|data-empty", pane_empty if pane_empty.strip() else app, re.I
    ):
        fail("#116: person timeline must keep an EmptyState path for the empty filter case")

    # 5b) Load older must not show under the empty filtered view.
    # #113 still requires the control to exist in markup; it must not be required
    # (or left visible) when filteredTimeline is empty next to "No messages…".
    if re.search(r"Load older", markup, re.I):
        load_guarded = False
        for m in re.finditer(r"\{#if\s+([^}]+)\}", markup):
            cond = m.group(1)
            block_start = m.end()
            # End at matching {/if} at depth 1 from this {#if}, approx via next Load older.
            next_load = markup.find("Load older", block_start)
            if next_load < 0:
                continue
            between = markup[block_start:next_load]
            # Skip if another {#if} opens first without this cond applying directly —
            # require Load older appears before any nested {#if} or only simple content.
            if re.search(r"\{#if\b", between):
                continue
            if re.search(
                r"(?:filteredTimeline|visibleTimeline|timelineRows|displayTimeline|"
                r"shownTimeline|tlRows|visibleRows)",
                cond,
                re.I,
            ):
                load_guarded = True
                break
        # Also accept: Load older only after an {:else} of a filtered-empty branch
        # (empty filtered → EmptyState; else → Load older path).
        if not load_guarded and re.search(
            r"(?:filteredTimeline|visibleTimeline|timelineRows|displayTimeline|"
            r"shownTimeline|tlRows|visibleRows)"
            r"[^}]{0,80}(?:length\s*===?\s*0|!\s*\w+\.length)"
            r"[\s\S]{0,400}\{:else\b[\s\S]{0,400}Load older",
            markup,
            re.I,
        ):
            load_guarded = True
        if not load_guarded:
            fail(
                "#116: Load older must not show under the empty filtered view "
                "(gate it on filteredTimeline.length / visible rows — do not "
                "require Load older when the kind/platform filter hides every row)"
            )

    # 6) j/k / highlight walk visible indices from the combined-filtered list.
    if not _VISIBLE_KIND_JK.search(cleaned):
        fail(
            "#116: j/k must walk only visible (combined-filtered) timeline rows "
            "(visibleTlIndices / filteredTimeline), not the full unfiltered list"
        )
    # visible indices derivation should hang off the same filtered list that applies kind.
    if not re.search(
        r"(?:visibleTlIndices|visibleIndices)\s*=\s*\$derived\s*\("
        r"[^)]{0,200}(?:filteredTimeline|visibleTimeline|timelineRows)",
        cleaned,
        re.I | re.S,
    ) and not re.search(
        r"(?:filteredTimeline|visibleTimeline)[^;]{0,200}"
        r"(?:visibleTlIndices|visibleIndices|\.map\s*\([^)]*index)",
        cleaned,
        re.I | re.S,
    ):
        # Softer: onKey / j/k references filtered or visible indices at all.
        if not re.search(
            r"(?:key\s*===?\s*[\"']j[\"']|[\"']j[\"']\s*\|\||ArrowDown)"
            r"[\s\S]{0,400}"
            r"(?:visibleTlIndices|visibleIndices|filteredTimeline|visibleTimeline)",
            cleaned,
            re.I,
        ) and not re.search(
            r"(?:visibleTlIndices|visibleIndices|filteredTimeline)"
            r"[\s\S]{0,400}"
            r"(?:key\s*===?\s*[\"']j[\"']|[\"']j[\"']|ArrowDown)",
            cleaned,
            re.I,
        ):
            fail(
                "#116: j/k (and the selection ring) must use the combined-filtered "
                "visible indices so hidden kind/platform rows are skipped"
            )


# #117 — Gmail / email_thread timeline rows: subject title + fold quoted tails.
_MAIL_ROW_GATE = re.compile(
    r"("
    r"(?:platform|row\.platform|\.platform)\s*===?\s*[\"']gmail[\"']"
    r"|[\"']gmail[\"']\s*===?\s*(?:platform|row\.platform|\.platform)"
    r"|(?:conversation_kind|row\.conversation_kind|\.conversation_kind)"
    r"\s*===?\s*[\"']email_thread[\"']"
    r"|[\"']email_thread[\"']\s*===?\s*"
    r"(?:conversation_kind|row\.conversation_kind|\.conversation_kind)"
    r"|\bisMail(?:Row|Bubble|Message)?\b"
    r"|\bisEmail(?:Row|Bubble|Message|Thread)?\b"
    r"|\bisGmail(?:Row|Bubble|Message)?\b"
    r"|\bmailRow\b"
    r"|\bemailRow\b"
    # Subject present ⇒ mail-ish title branch (WA subjects are null).
    r"|\{#if\s+[^}]{0,120}(?:item\.)?row\.subject\b"
    r"|(?:item\.)?row\.subject\s*(?:\?\.|\.)?trim\s*\([^)]*\)\s*(?:&&|\?)"
    r"|(?:item\.)?row\.subject\s*&&"
    r")",
    re.I,
)
# Standalone subject title binding — not body_text || subject body fallback.
_SUBJECT_TITLE_HELPER = re.compile(
    r"("
    r"\{[^}]{0,80}(?:subjectTitle|mailSubject|emailSubject|"
    r"rowSubject|displaySubject)[^}]{0,40}\}"
    r"|data-mail-subject"
    r"|class=[\"'][^\"']*\b(?:mail-)?subject\b"
    r"|class:(?:mail-)?subject\b"
    r")",
    re.I,
)
# Sole body fallback that treats subject as body when body is empty — not a title.
_SUBJECT_BODY_FALLBACK_ONLY = re.compile(
    r"(?:body_text\s*\|\|\s*(?:(?:item\.)?row\.)?subject"
    r"|(?:displayBody|bodyText)\s*\(\s*(?:(?:item\.)?row\.)?body_text\s*\|\|"
    r"\s*(?:(?:item\.)?row\.)?subject)",
    re.I,
)


def _standalone_subject_bindings(block: str) -> list[str]:
    """{…row.subject…} expressions that are titles, not body_text||subject."""
    out: list[str] = []
    for m in re.finditer(
        r"\{([^{}]{0,160}(?:item\.)?row\.subject[^{}]{0,80})\}",
        block,
    ):
        expr = m.group(1)
        if "body_text" in expr and "||" in expr:
            continue
        if re.search(r"body_text\s*\|\|", expr):
            continue
        if re.search(r"displayBody\s*\(", expr) and "||" in expr:
            continue
        out.append(expr)
    return out
_QUOTE_SPLIT = re.compile(
    r"("
    # “On … wrote:” marker (literal, regex, or template).
    r"On\s+.{0,60}wrote\s*:"
    r"|On\s+\\?\$\{[^}]{0,40}\}\s+wrote"
    r"|/On\s+.+?wrote\s*:/"
    r"|[\"']On [\"'][^;]{0,80}wrote"
    r"|[\"']wrote:[\"']"
    r"|wrote:"
    # Named pure split / fold helpers (synthetic placeholders only in tests).
    r"|splitQuoted(?:Body|Tail|Text)?"
    r"|splitQuote(?:d)?(?:Body|Tail)?"
    r"|quoteTail"
    r"|quotedTail"
    r"|quotedBody"
    r"|foldQuoted"
    r"|quoteSplit"
    r"|mailQuote"
    r"|extractQuoted"
    r"|stripQuoted"
    r"|unquotedBody"
    r"|bodyWithoutQuote"
    r"|mainBody(?:Text)?"
    # Leading “>” quote lines.
    r"|startsWith\s*\(\s*[\"']>[\"']"
    r"|lines?\s*\.?\s*(?:filter|map|find|some|every|startsWith)"
    r"[^;]{0,80}[\"']>[\"']"
    r"|[\"']>[\"']\s*===?\s*.{0,20}(?:trim|charAt|\[0\])"
    r")",
    re.I | re.S,
)
_CID_IMG = re.compile(
    r"("
    r"cid:"
    r"|src\s*=\s*[\"']cid:"
    r"|src\s*=\s*\{[^}]*cid:"
    r")",
    re.I,
)
_SEND_MAIL_UI = re.compile(
    r"("
    r">\s*Send\s+(?:mail|email|message)\s*<"
    r"|[\"']Send (?:mail|email|message)[\"']"
    r"|compose(?:Mail|Email|Message)"
    r"|data-compose-mail"
    r"|reply-all"
    r"|Reply all"
    r"|mailto:"
    r"|type=[\"']email[\"'][^>]{0,80}compose"
    r"|placeholder=[\"'][^\"']*(?:Write a (?:mail|reply)|Compose)"
    r")",
    re.I,
)
_WA_PLAIN_BODY = re.compile(
    r"("
    r"(?:platform|row\.platform)\s*===?\s*[\"']whatsapp[\"']"
    r"|[\"']whatsapp[\"']\s*===?\s*(?:platform|row\.platform)"
    r"|\bisWhats?App\b"
    r"|!\s*(?:isMail|isEmail|isGmail|mailRow|emailRow)\b"
    r"|\{:else\b"
    r")",
    re.I,
)


def assert_gmail_timeline_rows(crate: Path) -> None:
    """#117: Gmail/email_thread rows — subject title, fold quotes; WA plain.

    Acceptance: long reply chains stay one screen until “Show quoted” expands.
    Subject is a title on mail rows (not only body_text||subject fallback).
    Body stays text nodes (whitespace-pre-wrap / plain); no {@html}, no cid:
    images, no send/compose chrome. WhatsApp / non-mail rows keep a plain body
    path and are not forced through the mail layout.
    """
    app = (crate / "web" / "App.svelte").read_text()
    logic = _web_logic(crate)
    block = _timeline_block(crate)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    whole = app + "\n" + logic
    cleaned = _without_comments(whole)
    detail = _person_detail_markup(app)
    timeline_chrome = block + "\n" + detail

    # 1) Mail-aware path: gmail platform and/or email_thread kind.
    if not _MAIL_ROW_GATE.search(cleaned) and not _MAIL_ROW_GATE.search(block):
        fail(
            "#117: email_thread / gmail timeline rows need a mail-aware path "
            "(platform === \"gmail\" and/or conversation_kind === \"email_thread\", "
            "isMail/isEmail helper, or {#if row.subject} title branch) — "
            "subject title + quote fold only apply there"
        )

    # 2) Subject shown as a title on mail rows — not only body_text || subject.
    standalone_subjects = _standalone_subject_bindings(block)
    has_subject_title = bool(standalone_subjects) or bool(
        _SUBJECT_TITLE_HELPER.search(block)
    )
    if not has_subject_title:
        has_subject_title = bool(
            re.search(
                r"(?:subjectTitle|mailSubject|emailSubject|rowSubject|displaySubject|"
                r"mail-subject|data-mail-subject)"
                r"[\s\S]{0,200}"
                r"(?:\.subject\b|row\.subject)"
                r"|(?:function|const|let)\s+(?:subjectTitle|mailSubject|emailSubject|"
                r"displaySubject)\b",
                cleaned,
                re.I,
            )
        )
    # Title may live in a small child component used from the row.
    if not has_subject_title:
        has_subject_title = bool(
            re.search(
                r"<(?:MailBubble|EmailBubble|GmailRow|MailRow|MailBody)\b[^>]{0,200}"
                r"subject",
                block + "\n" + blob,
                re.I,
            )
        )
    if not has_subject_title:
        fail(
            "#117: for email_thread / gmail, show subject as a title on the bubble "
            "(bind row.subject / mailSubject as its own text node), not only as "
            "displayBody(body_text || subject) fallback"
        )

    # If the only subject use in the row is still the body fallback, fail even
    # when a helper name exists elsewhere (Search hits subject).
    if _SUBJECT_BODY_FALLBACK_ONLY.search(block) and not standalone_subjects:
        if not _SUBJECT_TITLE_HELPER.search(block) and not re.search(
            r"subjectTitle|mailSubject|emailSubject|displaySubject|data-mail-subject",
            block,
            re.I,
        ):
            fail(
                "#117: subject must be a title on mail rows — "
                "body_text || subject alone is the body fallback, not a title"
            )

    # Subject title must be reachable from the mail gate (not a global force that
    # rewrites WhatsApp). Prefer an isMail / gmail / email_thread condition near
    # the subject surface, or a helper that only returns subject for mail rows.
    mail_subject_ok = bool(
        re.search(
            r"(?:isMail|isEmail|isGmail|mailRow|emailRow|"
            r"platform\s*===?\s*[\"']gmail[\"']|"
            r"conversation_kind\s*===?\s*[\"']email_thread[\"'])"
            r"[\s\S]{0,500}"
            r"(?:\.subject\b|subjectTitle|mailSubject|emailSubject|displaySubject|"
            r"data-mail-subject|mail-subject)"
            r"|(?:\.subject\b|subjectTitle|mailSubject|emailSubject|displaySubject|"
            r"data-mail-subject|mail-subject)"
            r"[\s\S]{0,500}"
            r"(?:isMail|isEmail|isGmail|mailRow|emailRow|"
            r"platform\s*===?\s*[\"']gmail[\"']|"
            r"conversation_kind\s*===?\s*[\"']email_thread[\"'])",
            cleaned,
            re.I,
        )
    ) or bool(
        re.search(
            r"(?:subjectTitle|mailSubject|displaySubject|emailSubject)\s*=\s*"
            r"(?:function|\([^)]*\)\s*=>|\$derived)",
            cleaned,
            re.I,
        )
    )
    if not mail_subject_ok:
        # Markup {#if isMail} … {row.subject} is enough when both tokens are in block.
        if not (
            _MAIL_ROW_GATE.search(block + "\n" + cleaned)
            and (
                standalone_subjects
                or _SUBJECT_TITLE_HELPER.search(block)
                or re.search(
                    r"subjectTitle|mailSubject|emailSubject|data-mail-subject",
                    block,
                    re.I,
                )
            )
        ):
            fail(
                "#117: subject-as-title must be gated to email_thread / gmail "
                "(do not force a mail subject title onto every WhatsApp bubble)"
            )

    # 3) Quoted tails collapsed behind “Show quoted” (or similar expand control).
    if not _SHOW_QUOTED.search(blob) and not _SHOW_QUOTED.search(cleaned):
        fail(
            "#117: fold quoted reply tails behind an expand control "
            "(“Show quoted” / showQuoted / data-show-quoted) so a long chain "
            "is one screen until expanded"
        )
    if not _QUOTE_SPLIT.search(cleaned):
        fail(
            "#117: split mail body on common quote markers "
            "(“On … wrote:”, lines starting with “>”) — pure text split / "
            "quoteTail / splitQuoted helper is fine; still text nodes, not HTML"
        )
    # Expand control must sit on the timeline / person detail, not only Search.
    if not _SHOW_QUOTED.search(timeline_chrome) and not _SHOW_QUOTED.search(block):
        # Allow control label only in script if data-show-quoted / toggle is in row.
        if not re.search(
            r"(?:showQuoted|quotedExpanded|expandQuoted|data-show-quoted|"
            r"quotedTail|quoteTail|splitQuoted)",
            block + "\n" + timeline_chrome,
            re.I,
        ):
            fail(
                "#117: “Show quoted” (or the quote expand toggle) must be on the "
                "person timeline bubble for mail rows, not only in Search/Review"
            )

    # 4) Body remains text nodes — no {@html} for mail body; pre-wrap / plain ok.
    if _HTML_BODY.search(block) or _HTML_BODY.search(timeline_chrome):
        fail(
            "#117: mail body must stay text nodes (whitespace-pre-wrap or plain) — "
            "no {@html} for the message body (not HTML MIME layout)"
        )
    # Timeline body still needs a readable text surface (#111 pre-wrap or plain).
    if not re.search(r"whitespace-pre-wrap|whitespace-pre\b", block) and not re.search(
        r"\{(?:displayBody|mainBody|visibleBody|unquotedBody|bodyWithoutQuote|"
        r"(?:item\.)?row\.body_text)[^}]*\}",
        block,
    ):
        fail(
            "#117: timeline body must remain a text binding "
            "(whitespace-pre-wrap / plain text node), including after quote fold"
        )

    # 5) No cid: remote images; no send/compose chrome on the person timeline.
    if _CID_IMG.search(timeline_chrome) or _CID_IMG.search(block):
        fail("#117: no cid: images in the person timeline (not HTML MIME / inline cid)")
    if re.search(
        r"<img\b[^>]{0,200}src\s*=\s*[\"'](?:cid:|https?://)",
        timeline_chrome + "\n" + block,
        re.I | re.S,
    ):
        fail("#117: timeline must not render remote or cid: <img> for mail bodies")
    if _SEND_MAIL_UI.search(timeline_chrome) or _SEND_MAIL_UI.search(block):
        fail(
            "#117: no send / compose mail UI on the person timeline "
            "(read-only archive — fold quotes only, do not add reply chrome)"
        )

    # 6) WhatsApp / non-mail path stays plain body — not forced through mail layout.
    # Require either an explicit {:else} / !isMail branch, or that mail-only helpers
    # do not wrap every row (subject title + show-quoted only under mail gate).
    wa_plain = bool(_WA_PLAIN_BODY.search(block + "\n" + cleaned))
    # Plain body_text for non-mail: displayBody(body_text) without requiring subject title.
    plain_body_binding = bool(
        re.search(
            r"(?:displayBody\s*\(\s*(?:(?:item\.)?row\.)?body_text"
            r"|\{(?:(?:item\.)?row\.)?body_text\s*\}\s*)",
            block,
        )
    )
    if not (wa_plain and plain_body_binding) and not (
        _MAIL_ROW_GATE.search(cleaned)
        and plain_body_binding
        and re.search(r"\{:else\b", block)
    ):
        # Soften: if quote fold / subject title are clearly mail-gated, WA inherits
        # the existing pre-wrap body_text path from #111.
        if not (
            _MAIL_ROW_GATE.search(cleaned)
            and (
                re.search(r"body_text", block)
                or re.search(r"displayBody", block)
            )
            and not re.search(
                r"(?:showQuoted|Show quoted|subjectTitle|mailSubject)"
                r"[^;]{0,120}(?:whatsapp|for\s+each|every\s+row)",
                cleaned,
                re.I,
            )
        ):
            fail(
                "#117: WhatsApp / non-mail rows must keep a plain body path "
                "(body_text / displayBody) and must not be forced through the "
                "mail subject-title + quote-fold layout"
            )


# #120 — virtualize person timeline (visible + overscan only in the DOM).
# Static analysis: fail naive full {#each dayGroups}→{#each group.rows} without a window.
# No FPS/perf assertions in CI; dogfood measures 10k scroll.
_VIRT_SIGNAL = re.compile(
    r"("
    r"\boverscan\b"
    r"|\bvirtual(?:ize|ized|izing|isation|ization)?\b"
    r"|\bVirtualList\b"
    r"|\bvirtual(?:List|Rows?|Window|Scroll|Range|Items?)\b"
    r"|\bwindow(?:ed|ing)(?:Rows?|Items?|Groups?|Range|Start|End|Slice|Timeline|DayGroups?)?\b"
    r"|\bvisible(?:Range|Start|End|Count|Window|Slice|Rows?|Items?|Groups?|DayGroups?|"
    r"Indices|Index)\b"
    r"|\b(?:start|end)(?:Index|Row|Offset)\b"
    r"|\b(?:first|last)Visible(?:Index|Row|Item)?\b"
    r"|\brender(?:ed)?(?:Rows?|Items?|Range|Window|Slice|Groups?)\b"
    r"|\bviewport(?:Rows?|Range|Height|Top)\b"
    r"|\b(?:row|item)(?:Height|Size)\b"
    r"|\bestimated(?:Row|Item)?(?:Height|Size)\b"
    r"|\btotalHeight\b"
    r"|\bspacer(?:Height|Top|Bottom)?\b"
    r"|\bscrollMargin\b"
    r"|\bsvelte-virtual(?:-list)?\b"
    r"|@tanstack/(?:svelte-)?virtual\b"
    r"|\bcreateVirtualizer\b"
    r"|\buseVirtualizer\b"
    r"|\bVirtualizer\b"
    r")",
    re.I,
)
# Classic anti-pattern: full dayGroups then every group.rows (no window).
_NAIVE_DAYGROUPS_ROWS = re.compile(
    r"\{#each\s+dayGroups\b[^}]*\}[\s\S]{0,1200}?\{#each\s+group\.rows\b",
    re.I,
)
# Full unwindowed list each (flat timeline / filtered list of every row).
_NAIVE_FULL_ROW_EACH = re.compile(
    r"\{#each\s+(?:timeline|filteredTimeline)\b",
    re.I,
)
_BODY_INNER_HTML = re.compile(
    r"("
    r"\{@html\b"
    r"|\.innerHTML\s*="
    r"|insertAdjacentHTML\s*\("
    r")",
)
_SCOPE_10M = re.compile(
    r"("
    r"10\s*[Mm](?:illion)?\b[^.\n]{0,80}"
    r"(?:one view|single view|in (?:the )?DOM|all (?:at )?once|in one (?:list|view))"
    r"|(?:render|mount|load)\s+(?:all\s+)?10\s*[Mm]"
    r")",
    re.I,
)
_SCOPE_LAZY_EVERY_PHOTO = re.compile(
    r"("
    r"lazy[- ]decode\s+every\s+(?:photo|image|cas|attachment)"
    r"|decode\s+every\s+(?:photo|image)\s+laz"
    r"|lazyDecodeEvery"
    r")",
    re.I,
)
_JK_KEY = re.compile(
    r"("
    r"key\s*===?\s*[\"']j[\"']"
    r"|[\"']j[\"']\s*===?\s*key"
    r"|key\s*===?\s*[\"']k[\"']"
    r"|[\"']k[\"']\s*===?\s*key"
    r"|visibleTlIndices"
    r"|nearestVisibleTlIndex"
    r")",
    re.I,
)


def _derived_body(cleaned: str, name: str) -> str | None:
    """Return the body of `const name = $derived...` / `$derived.by` if present."""
    m = re.search(
        rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*\$derived(?:\.by)?\s*\(",
        cleaned,
    )
    if not m:
        return None
    open_idx = m.end() - 1
    close = _match_closer(cleaned, open_idx)
    if close < 0:
        return cleaned[m.end() : m.end() + 2500]
    return cleaned[open_idx + 1 : close]


def _body_has_row_window(body: str) -> bool:
    """True if a derived-list body actually bounds rows (not only ISO day slice)."""
    if re.search(
        r"\boverscan\b|\bvirtual|\bwindow(?:ed|ing|Start|End|Range)|"
        r"\bvisible(?:Range|Start|End|Window|Slice|Rows?|Groups?)|"
        r"\b(?:start|end)(?:Index|Row)\b|"
        r"\b(?:first|last)Visible\b|"
        r"createVirtualizer|useVirtualizer",
        body,
        re.I,
    ):
        return True
    # .slice(a, b) row window — exclude the common day-prefix .slice(0, 10).
    for sm in re.finditer(r"\.slice\s*\(\s*([^)]*)\)", body):
        args = sm.group(1)
        if re.match(r"\s*0\s*,\s*10\s*$", args):
            continue
        if "," in args:
            return True
    return False


def _list_source_is_windowed(cleaned: str, name: str) -> bool:
    """True if `name` is derived/assigned with a real row window (not a rename alone)."""
    body = _derived_body(cleaned, name)
    if body and _body_has_row_window(body):
        return True
    # Non-$derived assignment / helper: name = windowRows(...) / slice(...)
    m = re.search(
        rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?!\$derived)([^;]{{0,400}})",
        cleaned,
    )
    if m and _body_has_row_window(m.group(1)):
        return True
    if re.search(
        rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*"
        r"(?:\$derived(?:\.by)?\s*\()?"
        r"[\s\S]{0,240}"
        r"(?:window(?:ed|ing)\w*|virtual(?:ize|Rows|List|Items?)?|"
        r"visible(?:Range|Rows|Groups?|Window)|"
        r"overscan|createVirtualizer|useVirtualizer)",
        cleaned,
        re.I,
    ):
        return True
    return False


def _timeline_each_names_in_markup(markup: str) -> list[str]:
    """Names used in {#each ...} that look like timeline row sources."""
    names: list[str] = []
    for m in re.finditer(r"\{#each\s+([A-Za-z_]\w*)\b", markup):
        name = m.group(1)
        if name in _TIMELINE_EACH_NAMES or re.match(
            r"^(?:windowed|visible|virtual|rendered)",
            name,
            re.I,
        ):
            names.append(name)
        elif name in {"timeline", "filteredTimeline", "dayGroups"}:
            names.append(name)
    return names


def _naive_full_timeline_mount(markup: str, cleaned: str) -> bool:
    """True if the person timeline always mounts every filtered row (no window)."""
    # 1) {#each dayGroups} → {#each group.rows} with unwindowed dayGroups.
    if _NAIVE_DAYGROUPS_ROWS.search(markup):
        if not _list_source_is_windowed(cleaned, "dayGroups"):
            return True
    # 2) Flat {#each timeline|filteredTimeline} without windowing that source.
    for m in _NAIVE_FULL_ROW_EACH.finditer(markup):
        mm = re.search(r"\{#each\s+(\w+)", m.group(0))
        name = mm.group(1) if mm else "timeline"
        if not _list_source_is_windowed(cleaned, name):
            return True
    # 3) Any timeline-ish each whose source is not windowed (rename without window).
    for name in _timeline_each_names_in_markup(markup):
        if name in {"dayGroups", "timeline", "filteredTimeline"}:
            continue  # already covered; dayGroups alone without rows is headings-only
        # Nested group.rows is not a top-level list name.
        if not _list_source_is_windowed(cleaned, name):
            # Only treat as naive if the each body looks like message rows.
            for em in re.finditer(rf"\{{#each\s+{re.escape(name)}\b[^}}]*\}}", markup):
                end = _matching_each_end(markup, em.start())
                chunk = markup[em.start() : end if end > 0 else em.start() + 800]
                if re.search(
                    r"from_me|body_text|data-from-me|bubble-me|group\.rows",
                    chunk,
                    re.I,
                ):
                    return True
    return False


def _has_windowed_render_path(markup: str, cleaned: str) -> bool:
    """True if some timeline {#each} iterates a really windowed list (or VirtualList)."""
    for name in _timeline_each_names_in_markup(markup):
        if _list_source_is_windowed(cleaned, name):
            return True
    # Virtual list component / helper owns the window even without a named slice.
    if re.search(
        r"<Virtual(?:List|Scroll|izer)?\b|createVirtualizer\s*\(|useVirtualizer\s*\(",
        markup + "\n" + cleaned,
        re.I,
    ):
        return True
    # dayGroups itself windowed (still named dayGroups) + nested group.rows.
    if re.search(r"\{#each\s+dayGroups\b", markup) and _list_source_is_windowed(
        cleaned, "dayGroups"
    ):
        return True
    return False


def assert_virtualized_timeline(crate: Path) -> None:
    """#120: window person timeline (visible + overscan); keep j/k + Load older.

    Acceptance: synthetic 10k DM does not lock the window — only visible + overscan
    rows (and needed day headings) mount. Bodies still text nodes.
    Static gate: fail naive full {#each dayGroups}→{#each group.rows} without a
    window. No FPS assertions in CI (dogfood measures scroll).
    Not: 10M in one view, lazy-decode every photo.
    """
    app = (crate / "web" / "App.svelte").read_text()
    logic = _web_logic(crate)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    whole = app + "\n" + logic
    cleaned = _without_comments(whole)
    markup = _svelte_markup(app)
    # Prefer person-timeline pane if present.
    pt = markup.find("person-timeline")
    if pt >= 0:
        timeline_markup = markup[pt:]
    else:
        timeline_markup = markup
    block = _timeline_block(crate)

    # 1) Reject naive full double-each over dayGroups/rows (current App.svelte).
    # Prefer this message as the pre-impl red gate so the fix target is obvious.
    if _naive_full_timeline_mount(timeline_markup, cleaned):
        fail(
            "#120: do not always mount every filtered row "
            "({#each dayGroups} → {#each group.rows} over the full list, or "
            "{#each timeline|filteredTimeline} without a window). "
            "Window to visible + overscan only so a synthetic 10k DM stays scrollable"
        )

    # 2) Virtualization / windowing signal must exist (overscan, virtual list, …).
    if not _VIRT_SIGNAL.search(cleaned) and not _VIRT_SIGNAL.search(blob):
        fail(
            "#120: person timeline must window the list "
            "(only visible + overscan rows in the DOM — overscan / virtual list / "
            "visibleRange / startIndex+endIndex / windowed rows; "
            "do not always mount every filtered bubble)"
        )

    # 3) Positive: render path must each a windowed list (or VirtualList).
    if not _has_windowed_render_path(timeline_markup, cleaned):
        fail(
            "#120: person timeline render path must iterate a windowed list "
            "(windowed/visible/virtual/rendered rows or groups, or a list derived "
            "with overscan/slice/startIndex — not the full filtered set)"
        )

    # 4) Keep Load older (#113) — still at the list, not dropped by virtualization.
    if not _LOAD_OLDER.search(markup) and not _LOAD_OLDER.search(app):
        fail("#120: keep Load older when virtualizing (do not regress #113)")

    # 5) Keep j/k on visible (filtered) indices (#113 / #116).
    if not _JK_KEY.search(cleaned) and not _VISIBLE_KIND_JK.search(cleaned):
        fail(
            "#120: keep j/k walking visible timeline rows "
            "(visibleTlIndices / j|k handlers — do not regress #113/#116)"
        )

    # 6) Bodies still text nodes — no {@html} / innerHTML of message body.
    body_surface = block + "\n" + timeline_markup
    if _HTML_BODY.search(body_surface) or _BODY_INNER_HTML.search(body_surface):
        # Allow innerHTML only outside body bindings (e.g. unrelated); still forbid {@html}.
        if _HTML_BODY.search(body_surface):
            fail(
                "#120: bodies still text nodes — no {@html} of the message body "
                "(keep whitespace-pre-wrap / plain text bindings)"
            )
        # innerHTML near body_text / displayBody is the product footgun.
        if re.search(
            r"(?:body_text|displayBody|message\.body|row\.body)[\s\S]{0,120}\.innerHTML\s*="
            r"|\.innerHTML\s*=[\s\S]{0,120}(?:body_text|displayBody)",
            body_surface,
            re.I,
        ):
            fail(
                "#120: bodies still text nodes — no innerHTML of the message body"
            )

    # 7) Not in scope: 10M-in-one-view / lazy-decode-every-photo (product claims).
    scope_src = _without_comments(blob)
    # Ignore this gate file and issue notes if they ever land under web/ (they should not).
    if _SCOPE_10M.search(scope_src):
        fail(
            "#120: not in scope — do not claim or build 10M messages in one view "
            "(window the list for 10k-class DMs only)"
        )
    if _SCOPE_LAZY_EVERY_PHOTO.search(scope_src):
        fail(
            "#120: not in scope — lazy-decode every photo / CAS is a separate concern, "
            "not part of timeline windowing"
        )
_TL_INDEX_READ = re.compile(
    r"("
    r"\[data-tl-index\]"
    r"|getAttribute\s*\(\s*[\"']data-tl-index[\"']"
    r"|dataset\.tlIndex"
    r")"
)
_HEIGHT_OF = re.compile(
    r"\b("
    r"heightOf"
    r"|rowHeightOf"
    r"|heightAt"
    r"|tlHeightOf"
    r"|rowHeightAt"
    r")\b"
)
_OFFSET_OF = re.compile(
    r"\b("
    r"offsetOf"
    r"|rowOffsetOf"
    r"|offsetAt"
    r"|tlOffsetOf"
    r"|rowOffsetAt"
    r"|prefixSum(?:s|Of)?"
    r"|prefixOffset"
    r"|rowOffsets"
    r")\b"
)
_LIVE_AVG = re.compile(
    r"\b("
    r"measuredSum"
    r"|measuredCount"
    r"|measuredAvg"
    r"|averageHeight"
    r"|avgHeight"
    r"|medianHeight"
    r"|runningAverage"
    r"|meanHeight"
    r")\b"
)
_FIXED_INDEX_TIMES_EST = re.compile(
    r"("
    r"(?:startIndex|endIndex|\bpos\b|\bindex\b|tlIndex)"
    r"\s*\*\s*(?:ESTIMATED_ROW_HEIGHT|88)\b"
    r"|(?:ESTIMATED_ROW_HEIGHT|88)\s*\*\s*"
    r"(?:startIndex|endIndex|\bpos\b|\bindex\b|tlIndex)"
    r"|(?:\.length\s*-\s*(?:visibleRange\.)?endIndex)"
    r"\s*\*\s*(?:ESTIMATED_ROW_HEIGHT|88)\b"
    r")"
)
_SCROLL_DIV_EST = re.compile(
    r"(?:tlScrollTop|scrollTop)\s*/\s*(?:ESTIMATED_ROW_HEIGHT|88)\b"
)
_CONST_FALLBACK = re.compile(
    r"(?:\?\?|\|\||:\s*|=\s*)ESTIMATED_ROW_HEIGHT\b"
    r"|\bESTIMATED_ROW_HEIGHT\b[^;\n]{0,40}\?\?"
)
_HEIGHT_OF_NAMES = (
    "heightOf",
    "rowHeightOf",
    "heightAt",
    "tlHeightOf",
    "rowHeightAt",
)
_OFFSET_OF_NAMES = (
    "offsetOf",
    "rowOffsetOf",
    "offsetAt",
    "tlOffsetOf",
    "rowOffsetAt",
    "prefixSum",
    "prefixSumOf",
    "prefixOffset",
)


def _row_measure_path(cleaned: str) -> bool:
    """True if JS measures [data-tl-index] into a height cache (not pin-latest)."""
    if not _HEIGHT_CACHE.search(cleaned):
        return False
    if not _TL_INDEX_READ.search(cleaned):
        return False
    if re.search(r"\bgetBoundingClientRect\s*\(", cleaned):
        return True
    for m in re.finditer(r"new\s+ResizeObserver\s*\(", cleaned):
        arg = _call_arg(cleaned, cleaned.find("(", m.start()))
        if not arg:
            continue
        # #113 pin-latest only slams scrollTop = scrollHeight.
        if re.search(r"scrollHeight", arg) and not (
            _HEIGHT_CACHE.search(arg) or _TL_INDEX_READ.search(arg)
        ):
            continue
        if (
            _HEIGHT_CACHE.search(arg)
            or _TL_INDEX_READ.search(arg)
            or re.search(r"contentRect|\.height\b", arg)
        ):
            return True
    # Svelte action / $effect: observer + cache + [data-tl-index] in one file.
    return bool(re.search(r"\bResizeObserver\b", cleaned))


def _uses_prefix_sum(body: str) -> bool:
    if not body:
        return False
    if _OFFSET_OF.search(body) or _HEIGHT_OF.search(body):
        return True
    if re.search(r"\b(?:rowOffsets|prefixSums|offsets)\s*\[", body):
        return True
    return False


def _height_lookup_uses_constant(cleaned: str) -> bool:
    """Unmeasured slots must be ESTIMATED_ROW_HEIGHT, not a live average."""
    for name in _HEIGHT_OF_NAMES:
        body = _function_body(cleaned, name)
        if body:
            return bool(re.search(r"\bESTIMATED_ROW_HEIGHT\b", body))
        m = re.search(
            rf"(?:const|let|var|function)\s+{name}\b[\s\S]{{0,240}}"
            r"ESTIMATED_ROW_HEIGHT",
            cleaned,
        )
        if m:
            return True
    # Inline cache miss: rowHeights.get(i) ?? ESTIMATED_ROW_HEIGHT
    return bool(
        _HEIGHT_CACHE.search(cleaned)
        and _CONST_FALLBACK.search(cleaned)
        and re.search(
            rf"(?:{_HEIGHT_CACHE.pattern})\s*(?:\?\.|\.)?(?:get|\[\s*)",
            cleaned,
        )
    )


def assert_variable_height_timeline(crate: Path) -> None:
    """#224: measure-and-cache row heights; prefix-sum spacers; constant 88.

    Keep the #120 window. Unmeasured slots stay ESTIMATED_ROW_HEIGHT (not a
    live average). CI proves source shapes, not FPS.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#224: App.svelte required (variable-height person timeline)")
    app = app_path.read_text()
    logic = _web_logic(crate)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    cleaned = _without_comments(app + "\n" + logic)
    markup = _svelte_markup(app)
    pt = markup.find("person-timeline")
    timeline_markup = markup[pt:] if pt >= 0 else markup
    block = _timeline_block(crate)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) Still windowed — #120 stays; re-check the window hooks.
    if not re.search(r"\bvisibleRange\b", cleaned) and not re.search(
        r"\bwindowedDayGroups\b", cleaned
    ):
        fail(
            "#224: keep the #120 window "
            "(visibleRange / windowedDayGroups — do not remount every filtered row)"
        )

    # 2) Height cache + measure path on [data-tl-index].
    if not _row_measure_path(cleaned):
        fail(
            "#224: person timeline must measure-and-cache variable row heights "
            "(rowHeights plus ResizeObserver / getBoundingClientRect on "
            "[data-tl-index]); unmeasured slots keep constant "
            "ESTIMATED_ROW_HEIGHT = 88 — not startIndex * 88 spacers"
        )

    # 3) heightOf / offsetOf (or equivalent prefix-sum helpers) + constant 88.
    if not _HEIGHT_OF.search(cleaned) and not (
        _HEIGHT_CACHE.search(cleaned) and _CONST_FALLBACK.search(cleaned)
    ):
        fail(
            "#224: heightOf (or equivalent) must look up the rowHeights cache "
            "and fall back to constant ESTIMATED_ROW_HEIGHT"
        )
    if not _OFFSET_OF.search(cleaned):
        fail(
            "#224: offsetOf (or equivalent prefix-sum helper) must exist so "
            "spacers / visibleRange / j/k use measured (or constant-fallback) heights"
        )
    if not re.search(r"ESTIMATED_ROW_HEIGHT\s*=\s*88", cleaned):
        fail(
            "#224: unmeasured slots must use constant ESTIMATED_ROW_HEIGHT = 88 "
            "(do not drop the #120 estimate; do not replace it with a live average)"
        )
    if _LIVE_AVG.search(cleaned):
        fail(
            "#224: unmeasured slots must use constant ESTIMATED_ROW_HEIGHT — "
            "not a live average (measuredSum / measuredCount / fallbackHeight "
            "that divides measured stats)"
        )
    fb = _function_body(cleaned, "fallbackHeight")
    if fb and re.search(r"measuredSum|measuredCount|/\s*\w+", fb):
        fail(
            "#224: unmeasured slots must use constant ESTIMATED_ROW_HEIGHT — "
            "not fallbackHeight() that divides measured stats"
        )
    if not _height_lookup_uses_constant(cleaned):
        fail(
            "#224: heightOf / cache miss must use constant ESTIMATED_ROW_HEIGHT "
            "(not a running average of measured heights)"
        )
    for name in _OFFSET_OF_NAMES:
        body = _function_body(cleaned, name)
        if not body:
            continue
        if _FIXED_INDEX_TIMES_EST.search(body) and not (
            _HEIGHT_OF.search(body) or _HEIGHT_CACHE.search(body)
        ):
            fail(
                "#224: offsetOf must sum measured (or constant-fallback) heights, "
                "not return index * ESTIMATED_ROW_HEIGHT"
            )

    # 4) Spacers are prefix sums, not startIndex * 88 / (total - endIndex) * 88.
    spacer_top = _derived_body(cleaned, "spacerTop") or ""
    spacer_bottom = _derived_body(cleaned, "spacerBottom") or ""
    if not spacer_top or not spacer_bottom:
        fail(
            "#224: spacerTop / spacerBottom must exist and use prefix sums "
            "(offsetOf), not startIndex * ESTIMATED_ROW_HEIGHT"
        )
    if _FIXED_INDEX_TIMES_EST.search(spacer_top) or _FIXED_INDEX_TIMES_EST.search(
        spacer_bottom
    ):
        fail(
            "#224: spacerTop / spacerBottom must not be "
            "startIndex * ESTIMATED_ROW_HEIGHT / "
            "(total - endIndex) * ESTIMATED_ROW_HEIGHT — use offsetOf "
            "(prefix sums of measured or constant-fallback heights)"
        )
    if not _uses_prefix_sum(spacer_top) or not _uses_prefix_sum(spacer_bottom):
        fail(
            "#224: spacerTop / spacerBottom must use prefix sums "
            "(offsetOf or equivalent), not a fixed row estimate"
        )

    # 5) visibleRange walks prefix sums, not scrollTop / 88.
    vr = _derived_body(cleaned, "visibleRange") or ""
    if not vr:
        fail(
            "#224: visibleRange must walk prefix sums of measured "
            "(or constant-fallback) heights, not tlScrollTop / ESTIMATED_ROW_HEIGHT"
        )
    if _SCROLL_DIV_EST.search(vr):
        fail(
            "#224: visibleRange must not be only tlScrollTop / ESTIMATED_ROW_HEIGHT "
            "— walk prefix sums / measured heights"
        )
    if not _uses_prefix_sum(vr):
        fail(
            "#224: visibleRange must walk prefix sums / measured heights "
            "(offsetOf / heightOf), not divide scrollTop by 88"
        )

    # 6) ensureTlIndexVisible uses prefix sums, not pos * 88.
    ensure = _function_body(cleaned, "ensureTlIndexVisible")
    if not ensure:
        fail(
            "#224: keep ensureTlIndexVisible and point it at prefix sums "
            "(not pos * ESTIMATED_ROW_HEIGHT)"
        )
    if _FIXED_INDEX_TIMES_EST.search(ensure):
        fail(
            "#224: ensureTlIndexVisible must use prefix sums "
            "(offsetOf), not pos * ESTIMATED_ROW_HEIGHT"
        )
    if not _uses_prefix_sum(ensure):
        fail(
            "#224: ensureTlIndexVisible must use prefix sums of measured "
            "(or constant-fallback) heights so j/k lands on the selected bubble"
        )

    # 7) j/k + Load older + text bodies stay (#120 / #113 / #116).
    if not _LOAD_OLDER.search(markup) and not _LOAD_OLDER.search(app):
        fail("#224: keep Load older when measuring row heights (do not regress #113)")
    if not _JK_KEY.search(cleaned) and not _VISIBLE_KIND_JK.search(cleaned):
        fail(
            "#224: keep j/k walking visible timeline rows "
            "(do not regress #113/#116/#120)"
        )
    body_surface = block + "\n" + timeline_markup
    if _HTML_BODY.search(body_surface):
        fail(
            "#224: bodies still text nodes — no {@html} of the message body "
            "(keep whitespace-pre-wrap / displayBody)"
        )
    if not _PRE_WRAP.search(block):
        fail("#224: bodies still whitespace-pre-wrap text nodes")

    # 8) D24: measured row heights so two-sided DMs scroll without jumping.
    if not dtxt.strip():
        fail(
            "#224: docs/user/app.md required — person timeline virtualizes with "
            "measured row heights so two-sided DMs scroll without jumping"
        )
    if not re.search(r"only the rows in \(and near\) the viewport", dtxt, re.I):
        fail(
            "#224: keep the existing “only the rows in (and near) the viewport” "
            "sentence in docs/user/app.md"
        )
    if not re.search(r"measured\s+row\s+heights?", dtxt, re.I):
        fail(
            "#224: docs/user/app.md must say the person timeline virtualizes "
            "with measured row heights so two-sided DMs scroll without jumping"
        )

    # 9) Not in scope (same spirit as #120).
    scope_src = _without_comments(blob)
    if _SCOPE_10M.search(scope_src):
        fail(
            "#224: not in scope — do not claim or build 10M messages in one view"
        )
    if _SCOPE_LAZY_EVERY_PHOTO.search(scope_src):
        fail(
            "#224: not in scope — lazy-decode every photo / CAS is a separate "
            "concern, not part of variable-height windowing"
        )


# #206 — group consecutive same-side / same-conversation / same-calendar-day bubbles.
# Static: followers omit the run caption; grouping keys off filteredTimeline[i-1].
_GROUPING_COND = re.compile(
    r"("
    r"\bgrouped\b"
    r"|\bisGrouped(?:Follower|Row)?"
    r"|\brunStart\b|\bisRunStart\b"
    r"|\bfirstOfRun\b|\bisFirst(?:InRun|OfRun)\b"
    r"|\bshowCaption\b|\bhideCaption\b|\bcaptionVisible\b"
    r"|\bisFollower\b"
    r"|\bsameRun\b|\binSameRun\b|\bisSameRun\b|\bsameCaptionRun\b"
    r"|\bgroupStart\b|\bisGroupStart\b|\bfirstInGroup\b"
    r"|\brunHead\b|\bisRunHead\b"
    r")",
    re.I,
)
_CAPTION_MARK = re.compile(
    r"("
    r"class\s*=\s*[\"'][^\"']*\bcaption\b"
    r"|data-platform-chip"
    r"|<time\b"
    r")",
    re.I,
)
_CAPTION_OMIT_ATTR = re.compile(
    r"("
    r"class:hidden\s*=\s*\{[^}]{0,80}"
    r"(?:grouped|isFollower|isGrouped|!?\s*(?:runStart|showCaption|firstOfRun))"
    r"|hidden\s*=\s*\{[^}]{0,80}"
    r"(?:grouped|isFollower|isGrouped|!?\s*(?:runStart|showCaption|firstOfRun))"
    r"|class:opacity-0\s*=\s*\{[^}]{0,80}(?:grouped|isFollower|isGrouped)"
    r")",
    re.I,
)
_HOVER_ONLY_TIME = re.compile(
    r"("
    r"hover:opacity"
    r"|focus(?:-visible)?:opacity"
    r"|hover:visible"
    r"|focus(?:-visible)?:visible"
    r"|group-hover:"
    r"|group-focus:"
    r")",
    re.I,
)
_FILTERED_PREV = re.compile(
    r"filteredTimeline\s*(?:"
    r"\[[^\]]{0,80}-\s*1\s*\]"
    r"|\.at\s*\(\s*[^)]{0,60}-\s*1\s*\)"
    r")",
    re.I,
)
_PREV_INDEX = re.compile(
    r"("
    r"\[[^\]]{0,60}-\s*1\s*\]"
    r"|\.at\s*\(\s*[^)]{0,40}-\s*1\s*\)"
    r"|\bprev(?:ious)?(?:Row|Item|Msg|Filtered)?\b"
    r")",
    re.I,
)
_GROUP_DAY_KEY = re.compile(
    r"\butcDay\b|\butc_day\b|\blocalDay\b|\blocal_day\b|\bhostDay\b|"
    r"\bcalendarDay\b|\bdayKey\b|\bisoDay\b"
)
_NET_AVATAR = re.compile(
    r"("
    r"<img\b[^>]{0,400}src\s*=\s*[\"']https?://"
    r"|src\s*=\s*\{[^}]{0,160}https?://"
    r"|slack[-_]?avatar"
    r"|gravatar"
    r"|cdn\.slack"
    r"|face[-_]?pile"
    r")",
    re.I | re.S,
)
_GROUP_HELPER_NAMES = (
    "sameCaptionRun",
    "isGroupedFollower",
    "isRunFollower",
    "sameRun",
    "inSameRun",
    "isSameRun",
    "isCaptionGrouped",
    "groupedWithPrev",
    "isFollower",
    "isGrouped",
    "runStart",
    "isRunStart",
    "firstOfRun",
    "showCaption",
    "sameSenderRun",
)


def _grouping_if_at(markup: str, pos: int) -> bool:
    for kind, cond, _extra in _template_stack(markup, pos):
        if kind in {"if", "if-else"} and _GROUPING_COND.search(cond):
            return True
    return False


def _tag_at(markup: str, pos: int) -> str:
    start = markup.rfind("<", 0, pos + 1)
    if start < 0:
        return ""
    end = markup.find(">", start)
    if end < 0:
        return ""
    return markup[start : end + 1]


def _caption_el_omitted(markup: str, pos: int) -> bool:
    tag = _tag_at(markup, pos)
    if tag and _CAPTION_OMIT_ATTR.search(tag):
        return True
    # Chip / <time> may sit inside <p class="caption" hidden={grouped}>.
    start = markup.rfind("<", 0, pos + 1)
    if start <= 0:
        return False
    parent = _tag_at(markup, start - 1)
    return bool(parent and _CAPTION_OMIT_ATTR.search(parent))


def _hover_only_time(markup: str, pos: int) -> bool:
    tag = _tag_at(markup, pos)
    if tag and _HOVER_ONLY_TIME.search(tag):
        return True
    start = markup.rfind("<", 0, pos + 1)
    if start <= 0:
        return False
    parent = _tag_at(markup, start - 1)
    return bool(parent and _HOVER_ONLY_TIME.search(parent))


def _followers_omit_caption(markup: str) -> bool:
    """True when run-start can show time+chip and followers can skip that caption."""
    has_gated_caption = False
    for m in _CAPTION_MARK.finditer(markup):
        token = m.group(0)
        gated = _grouping_if_at(markup, m.start()) or _caption_el_omitted(markup, m.start())
        if gated:
            has_gated_caption = True
            continue
        is_time = token.lower().startswith("<time")
        if is_time and _hover_only_time(markup, m.start()):
            continue
        # Ungated .caption / chip / always-visible <time> — every bubble still
        # paints the run caption.
        return False
    return has_gated_caption or bool(re.search(r"\bdata-grouped\b", markup, re.I))


def _grouping_logic_src(cleaned: str) -> str:
    parts: list[str] = []
    for name in _GROUP_HELPER_NAMES:
        body = _function_body(cleaned, name)
        if body:
            parts.append(body)
        derived = _derived_body(cleaned, name)
        if derived:
            parts.append(derived)
    w = _derived_body(cleaned, "windowedDayGroups")
    if w and re.search(r"from_me|grouped|conversation_id", w):
        parts.append(w)
    return "\n".join(parts)


def _has_three_key_run(src: str) -> bool:
    """from_me + conversation_id + calendar day compared against a previous row."""
    for m in re.finditer(r"conversation_id", src):
        win = src[max(0, m.start() - 500) : m.end() + 500]
        if not re.search(r"\bfrom_me\b", win):
            continue
        if not _GROUP_DAY_KEY.search(win):
            continue
        if not _PREV_INDEX.search(win):
            continue
        return True
    return False


def _grouping_uses_filtered_prev(cleaned: str) -> bool:
    if _FILTERED_PREV.search(cleaned):
        return True
    for m in re.finditer(r"filteredTimeline\s*\.\s*map\s*\(", cleaned):
        open_p = m.end() - 1
        close = _match_closer(cleaned, open_p)
        blob = cleaned[open_p : close] if close >= 0 else cleaned[m.end() : m.end() + 800]
        if _PREV_INDEX.search(blob):
            return True
    for name in _GROUP_HELPER_NAMES:
        body = _function_body(cleaned, name)
        if not body:
            continue
        if not _PREV_INDEX.search(body):
            continue
        if re.search(rf"{re.escape(name)}\s*\(\s*filteredTimeline", cleaned):
            return True
        if re.search(r"filteredTimeline", body):
            return True
    return False


def _docs_206_ok(dtxt: str) -> bool:
    """Consecutive same-side / same-conversation / same calendar day share one caption."""
    if not re.search(r"hour:minute", dtxt, re.I):
        return False
    if not re.search(r"platform chip", dtxt, re.I):
        return False
    for m in re.finditer(r"consecutive", dtxt, re.I):
        win = dtxt[max(0, m.start() - 80) : m.end() + 240]
        if not re.search(r"same[- ]side|same[- ]sender|from[_ ]me", win, re.I):
            continue
        if not re.search(r"same[- ]conversation", win, re.I):
            continue
        if not re.search(
            r"same[- ](?:UTC[- ]|calendar[- ])day|same (?:UTC |calendar )?day",
            win,
            re.I,
        ):
            continue
        if not re.search(r"share one|one caption|quieter", win, re.I):
            continue
        return True
    return False


def _casattach_stripped_from_followers(markup: str) -> bool:
    """True if CasAttach only mounts on the run-start branch."""
    hits = list(re.finditer(r"<CasAttach\b", markup))
    if not hits:
        return True
    ungated = [m for m in hits if not _grouping_if_at(markup, m.start())]
    if ungated:
        return False
    kinds = set()
    for m in hits:
        for kind, cond, _extra in _template_stack(markup, m.start()):
            if kind in {"if", "if-else"} and _GROUPING_COND.search(cond):
                kinds.add(kind)
    return not ({"if", "if-else"} <= kinds)


def assert_timeline_grouped_runs(crate: Path) -> None:
    """#206: consecutive same from_me + conversation + calendar day share one caption.

    Acceptance: a 5-message run shows one caption then four quieter bubbles.
    Grouping keys off the filtered list (previous index), not only the previous
    windowed row. Day headings stay. Each message stays its own row (j/k).
    Bodies stay text nodes. CasAttach stays on followers. No network avatars.
    Do not soften #111/#112/#113/#115/#120/#205.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#206: App.svelte required (person-timeline caption grouping)")
    app = app_path.read_text()
    logic = _web_logic(crate)
    cleaned = _without_comments(app + "\n" + logic)
    block = _timeline_block(crate)
    markup = _svelte_markup(app)
    pt = markup.find("person-timeline")
    timeline_markup = markup[pt:] if pt >= 0 else markup
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) Followers omit the run caption (or time on hover/focus only).
    #    Grep hook: data-grouped, or {#if} / hidden that skips .caption / chip.
    if not _followers_omit_caption(timeline_markup) and not _followers_omit_caption(block):
        fail(
            "#206: consecutive filtered rows with the same from_me, same "
            "conversation_id, and same calendar day must form a run — run-start "
            "keeps the caption (time + platform chip); followers omit it "
            "(data-grouped, or {#if} that skips .caption / data-platform-chip). "
            "Do not paint a caption on every bubble"
        )

    # 2) Grouping must key off the filtered list, not only the windowed row.
    if not _grouping_uses_filtered_prev(cleaned):
        fail(
            "#206: grouping must key off the filtered list "
            "(filteredTimeline[i-1] / previous filtered index), not only the "
            "previous windowed row — otherwise scrolling mid-run would re-show "
            "captions"
        )

    # 3) Break the run when from_me, conversation_id, or calendar day changes.
    group_src = _grouping_logic_src(cleaned)
    if not _has_three_key_run(group_src) and not _has_three_key_run(cleaned):
        fail(
            "#206: grouping key is from_me + conversation_id + calendar day "
            "(break the run when any of those change). Do not group across "
            "different conversation_id or a different calendar day"
        )
    identity_src = group_src or cleaned
    for m in re.finditer(r"sender_identity_id", identity_src):
        win = identity_src[max(0, m.start() - 280) : m.end() + 280]
        if _GROUPING_COND.search(win) or re.search(r"\bfrom_me\b", win):
            fail(
                "#206: grouping key is from_me + conversation_id + calendar day — "
                "do not invent sender_identity_id (that is #207)"
            )

    # 4) Each message stays its own row; j/k still walks every data-tl-index.
    if not re.search(r"data-tl-index", block):
        fail(
            "#206: each message stays its own row (data-tl-index); "
            "do not collapse a run into one DOM node"
        )
    if not re.search(r"<article\b", block, re.I):
        fail(
            "#206: each message stays its own article row; "
            "do not collapse five messages into one DOM node"
        )
    if not _JK_KEY.search(cleaned):
        fail(
            "#206: do not soften #120 — j/k must still walk every "
            "data-tl-index row"
        )

    # 5) Day headings stay (#112). Run-start still has caption/time/platform (#111/#115).
    if not _DAY_HEADING.search(block):
        fail(
            "#206: do not soften #112 — day headings (day-heading) stay when "
            "the calendar day changes"
        )
    if "caption" not in block.lower() and "<time" not in block.lower():
        fail(
            "#206: do not soften #111 — run-start keeps the caption / <time>"
        )
    if (
        "row.platform" not in block
        and "platformLabel" not in block
        and "data-platform-chip" not in block
    ):
        fail(
            "#206: do not soften #111/#115 — run-start keeps the platform chip"
        )
    if not re.search(r"ESTIMATED_ROW_HEIGHT\s*=\s*88", cleaned):
        fail(
            "#206: do not soften #120/#224 — keep ESTIMATED_ROW_HEIGHT = 88"
        )
    if not re.search(r"\bOVERSCAN\s*=\s*15\b", cleaned):
        fail("#206: do not soften #120/#224 — keep OVERSCAN = 15")
    if "data-partial" not in app and "data-partial" not in logic:
        fail("#206: do not soften #205 — pane Error+Retry (data-partial) stays")

    # 6) Bodies stay text nodes; CasAttach stays on followers.
    if not _PRE_WRAP.search(block):
        fail("#206: bodies stay whitespace-pre-wrap text nodes")
    if _HTML_BODY.search(block) or _HTML_BODY.search(timeline_markup):
        fail("#206: bodies stay text nodes — no {@html}")
    if "displayBody" not in block and "body_text" not in block:
        fail("#206: bodies stay text nodes (displayBody / body_text)")
    if _casattach_stripped_from_followers(timeline_markup):
        fail(
            "#206: do not strip attachments / CasAttach from follower bubbles"
        )

    # 7) No network avatars / Slack-style face pile.
    if _NET_AVATAR.search(timeline_markup) or _NET_AVATAR.search(block):
        fail(
            "#206: no network avatars (no http(s) <img> / slack avatar / "
            "CDN face pile)"
        )

    # 8) D24: consecutive same-side / same-conversation / same calendar day share one caption.
    if not dtxt.strip():
        fail(
            "#206: docs/user/app.md required — consecutive same-side / "
            "same-conversation / same-calendar-day bubbles share one caption "
            "(keep the existing hour:minute + platform chip sentence)"
        )
    if not _docs_206_ok(dtxt):
        fail(
            "#206: docs/user/app.md must say consecutive same-side / "
            "same-conversation / same-calendar-day bubbles share one caption "
            "(keep the existing hour:minute + platform chip sentence for "
            "the run-start)"
        )


# #207 — one bubble stack: identity/time → body/subject → attachments.
_BUBBLE_META = "data-bubble-meta"
_BUBBLE_BODY = "data-bubble-body"
_BUBBLE_ATTACH = "data-bubble-attach"
_ODD_STACK_SPACE = re.compile(
    r"(?<![\w-])(?:[mp](?:[trblxy])?|gap(?:-[xy])?)-\[(\d+)(?:px)?\]"
)
_FRAC_STACK_SPACE = re.compile(
    r"(?<![\w-])(?:[mp](?:[trblxy])?|gap(?:-[xy])?)-(\d+)-(\d+)\b"
)
_STACK_FLEX_COL = re.compile(r"(?<![\w-])flex-col\b")
_STACK_GAP_48 = re.compile(r"(?<![\w-])gap-[23]\b")
_STACK_PAD_48 = re.compile(r"(?<![\w-])(?:p|px|py|pt|pb|pl|pr)-[23]\b")
_REACTIONS_UI = re.compile(
    r"("
    r">\s*Add reaction\s*<"
    r"|data-reaction(?:s)?\b"
    r"|reaction-bar"
    r"|emoji-picker"
    r")",
    re.I,
)
_NEW_PLATFORM_ON_BUBBLE = re.compile(
    r"""platform\s*===?\s*['\"](?:twitter|slack|discord|telegram|imessage|signal)['\"]""",
    re.I,
)
_SENDER_NAME_ON_BUBBLE = re.compile(
    r"\{[^{}]{0,80}(?:sender_identity_id|senderName|sender_name|senderDisplayName)[^{}]{0,40}\}"
)
_CAS_ITEMS_LEN_COND = re.compile(r"items\s*\??\s*\.\s*length|(?=.*\bitems\b)(?=.*\blength\b).*")
_UL_MT2_STATIC = re.compile(r"""class\s*=\s*["'][^"']*\bmt-2\b""")
_UL_MT2_LIT = re.compile(r"class\s*=\s*\{\s*[`'\"][^`'\"]*\bmt-2\b")
_MT2_TOKEN = re.compile(r"(?<![\w-])mt-2\b")
_NOMARGIN_PROP = re.compile(
    r"\b(?:flush|noMargin|nomargin|compact|tight|dense|bare|plain|noMt|unspaced)\b"
)
_BUBBLE_HTML_TOKEN = re.compile(
    r"<!--.*?-->"
    r"|</([A-Za-z][\w:.-]*)\s*>"
    r"|<([A-Za-z][\w:.-]*)\b([^>]*?)>",
    re.S,
)
_BUBBLE_VOID = frozenset(
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


def _timeline_articles(markup: str) -> list[str]:
    """Person-timeline <article>…</article> blobs (not nested)."""
    out: list[str] = []
    i = 0
    while True:
        m = re.search(r"<article\b", markup[i:], re.I)
        if not m:
            break
        start = i + m.start()
        end = re.search(r"</article\s*>", markup[start:], re.I)
        if not end:
            out.append(markup[start:])
            break
        out.append(markup[start : start + end.end()])
        i = start + end.end()
    return out


def _article_open_tag(article: str) -> str:
    m = re.match(r"<article\b[^>]*>", article, re.I | re.S)
    return m.group(0) if m else ""


def _split_mail_else(article: str) -> tuple[str, str] | None:
    """Mail {#if isMailRow…}{:else} split (skip the caption-only You {#if})."""
    for head in re.finditer(r"\{#if\s+([^}]*isMail[^}]*)\}", article, re.I):
        depth = 0
        then_start = head.end()
        else_start: int | None = None
        then_body = ""
        i = head.start()
        for m in re.finditer(r"\{#if\b|\{:else\s+if\b|\{:else\}|\{/if\}", article[i:]):
            tok = m.group(0)
            abs_at = i + m.start()
            if tok.startswith("{#if"):
                depth += 1
            elif tok.startswith("{:else if"):
                continue
            elif tok.startswith("{:else}"):
                if depth == 1 and else_start is None:
                    else_start = i + m.end()
                    then_body = article[then_start:abs_at]
            else:
                depth -= 1
                if depth == 0:
                    if else_start is None:
                        break
                    return then_body, article[else_start:abs_at]
    return None


def _hook_pos(blob: str, name: str) -> int:
    return blob.find(name)


def _casattach_pos(blob: str) -> int:
    m = re.search(r"<CasAttach\b", blob)
    return m.start() if m else -1


def _attach_wraps_cas(article: str) -> bool:
    """data-bubble-attach is on CasAttach or on a wrapper that precedes it."""
    for m in re.finditer(r"<CasAttach\b[^>]*>", article):
        if _BUBBLE_ATTACH in m.group(0):
            return True
    a = _hook_pos(article, _BUBBLE_ATTACH)
    c = _casattach_pos(article)
    return a >= 0 and c >= 0 and a < c


def _stack_class_blobs(article: str) -> list[str]:
    """Article open tag + any flex-col wrapper (not caption chip rows)."""
    blobs: list[str] = []
    open_tag = _article_open_tag(article)
    if open_tag:
        blobs.append(open_tag)
    for m in re.finditer(r"<([a-zA-Z][\w:-]*)\b[^>]*>", article):
        tag = m.group(0)
        if _STACK_FLEX_COL.search(tag) and tag not in blobs:
            blobs.append(tag)
    return blobs


def _odd_stack_token(blobs: list[str]) -> str | None:
    """First off-scale arbitrary / fractional spacing token on the stack."""
    for blob in blobs:
        for m in _ODD_STACK_SPACE.finditer(blob):
            px = int(m.group(1))
            if px % 4 != 0:
                return m.group(0)
        for m in _FRAC_STACK_SPACE.finditer(blob):
            # gap-1.5 is tokenized as gap-1 only by the integer class; catch gap-[n]/[d]
            return m.group(0)
        if re.search(r"(?<![\w-])(?:[mp](?:[trblxy])?|gap(?:-[xy])?)-\d+\.\d+\b", blob):
            frac = re.search(
                r"(?<![\w-])(?:[mp](?:[trblxy])?|gap(?:-[xy])?)-\d+\.\d+\b",
                blob,
            )
            if frac:
                return frac.group(0)
    return None


def _stack_uses_48(blobs: list[str]) -> bool:
    """flex-col + gap-2/gap-3 and/or p-2/p-3 (or px/py-2/3) on the stack."""
    text = "\n".join(blobs)
    has_col_gap = bool(_STACK_FLEX_COL.search(text) and _STACK_GAP_48.search(text))
    has_pad = bool(_STACK_PAD_48.search(text))
    return has_col_gap or has_pad


def _docs_207_ok(dtxt: str) -> bool:
    """Every bubble stacks identity/time, then body/subject, then attachments."""
    stacked = re.search(
        r"identity\s*/\s*time.{0,120}body\s*/\s*subject.{0,120}attachment",
        dtxt,
        re.I | re.S,
    )
    same = re.search(
        r"("
        r"whatsapp.{0,80}gmail.{0,40}(?:same|stack|order)"
        r"|gmail.{0,80}whatsapp.{0,40}(?:same|stack|order)"
        r"|WA and Gmail"
        r"|the same"
        r")",
        dtxt,
        re.I | re.S,
    )
    if stacked and same:
        # "the same" must sit near the stack sentence, not an unrelated line.
        win = dtxt[max(0, stacked.start() - 80) : stacked.end() + 160]
        if re.search(
            r"("
            r"whatsapp"
            r"|gmail"
            r"|WA and Gmail"
            r"|the same"
            r")",
            win,
            re.I,
        ):
            return True
    for m in re.finditer(r"stack", dtxt, re.I):
        win = dtxt[max(0, m.start() - 100) : m.end() + 220]
        if not re.search(r"identity\s*/\s*time", win, re.I):
            continue
        if not re.search(r"body\s*/\s*subject", win, re.I):
            continue
        if not re.search(r"attachment", win, re.I):
            continue
        if not re.search(r"whatsapp|gmail|\bWA\b|the same", win, re.I):
            continue
        return True
    return False


def _casattach_open(blob: str) -> str:
    m = re.search(r"<CasAttach\b[^>]*>", blob)
    return m.group(0) if m else ""


def _path_has_body_then_attach(blob: str) -> bool:
    """A WA or Gmail branch (or shared tail) keeps body before attach."""
    body = _hook_pos(blob, _BUBBLE_BODY)
    attach = _hook_pos(blob, _BUBBLE_ATTACH)
    cas = _casattach_pos(blob)
    if body >= 0 and attach >= 0 and attach < body:
        return False
    if body >= 0 and cas >= 0 and cas < body:
        return False
    if attach >= 0 and cas >= 0 and attach > cas:
        if _BUBBLE_ATTACH not in _casattach_open(blob):
            return False
    return True


def _cond_is_attach_len(cond: str) -> bool:
    """{#if} that mounts only when attachments.length is truthy."""
    if re.search(r"attachments\s*\??\s*\.\s*length", cond):
        return True
    return bool(re.search(r"\battachments\b", cond) and re.search(r"\blength\b", cond))


def _attach_len_gated(markup: str, pos: int) -> bool:
    for kind, cond, _extra in _template_stack(markup, pos):
        if kind == "if" and _cond_is_attach_len(cond):
            return True
    return False


def _html_open_stack(markup: str, pos: int) -> list[tuple[int, str, str]]:
    """(start, name, attrs) for unclosed HTML/component tags at pos."""
    stack: list[tuple[int, str, str]] = []
    for m in _BUBBLE_HTML_TOKEN.finditer(markup):
        if m.start() >= pos:
            break
        raw = m.group(0)
        if raw.startswith("<!--"):
            continue
        if m.group(1):
            name = m.group(1)
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][1].lower() == name.lower():
                    del stack[i:]
                    break
            continue
        name = m.group(2) or ""
        attrs = m.group(3) or ""
        self_close = raw.rstrip().endswith("/>") or name.lower() in _BUBBLE_VOID
        if self_close:
            continue
        stack.append((m.start(), name, attrs))
    return stack


def _empty_attach_wrapper_name(article: str) -> str | None:
    """Tag name of an always-on attach flex sibling, if any."""
    for m in re.finditer(re.escape(_BUBBLE_ATTACH), article):
        host = _tag_at(article, m.start())
        name = _tag_name(host)
        if name.lower() == "casattach":
            continue
        if name.lower() in {"div", "span"} and not _attach_len_gated(article, m.start()):
            return name
    cas = _casattach_pos(article)
    if cas < 0:
        return None
    for start, name, attrs in reversed(_html_open_stack(article, cas)):
        if name.lower() == "article":
            break
        if _BUBBLE_BODY in attrs or _BUBBLE_META in attrs:
            break
        if name.lower() in {"div", "span"}:
            if not _attach_len_gated(article, start):
                return name
            break
    return None


def _cas_items_ul_open(cas: str) -> str:
    markup = _svelte_markup(cas)
    for m in re.finditer(r"\{#if\s+([^}]+)\}", markup):
        if _CAS_ITEMS_LEN_COND.search(m.group(1)):
            um = re.search(r"<ul\b[^>]*>", markup[m.end() : m.end() + 600])
            if um:
                return um.group(0)
    um = re.search(r"<ul\b[^>]*>", markup)
    return um.group(0) if um else ""


def _ul_mt2_unconditional(ul_open: str) -> bool:
    if _UL_MT2_STATIC.search(ul_open):
        return True
    if _UL_MT2_LIT.search(ul_open) and not re.search(r"\?|&&|\|\|", ul_open):
        return True
    return False


def _cas_default_class_has_mt2(cas: str) -> bool:
    return bool(
        re.search(
            r"""(?:class(?:Name)?\s*:\s*\w+\s*=\s*|class(?:Name)?\s*=\s*)["'][^"']*\bmt-2\b""",
            cas,
        )
    )


def _timeline_cas_drops_mt2(cas: str, article: str, ul_open: str) -> bool:
    """True when the timeline CasAttach instance does not apply ul.mt-2."""
    if _ul_mt2_unconditional(ul_open):
        return False
    cas_open = _casattach_open(article)
    if not _MT2_TOKEN.search(ul_open) and not _cas_default_class_has_mt2(cas):
        return True
    if re.search(r"\b(?:class|className|ulClass|listClass)\b", ul_open + cas):
        cm = re.search(r"""\bclass\s*=\s*["']([^"']*)["']""", cas_open)
        if cm is not None and not _MT2_TOKEN.search(cm.group(1)):
            return True
        dyn = re.search(r"\bclass\s*=\s*\{([^}]+)\}", cas_open)
        if dyn and not _MT2_TOKEN.search(dyn.group(1)):
            return True
    for prop in _NOMARGIN_PROP.findall(cas):
        if not re.search(rf"\b{re.escape(prop)}\b", ul_open + cas_open):
            continue
        if re.search(
            rf"\b{re.escape(prop)}(?:\s*(?:/|>)|\s*=\s*\{{\s*true\s*\}})",
            cas_open,
        ):
            return True
    return False


def _article_has_col_gap23(article: str) -> bool:
    text = "\n".join(_stack_class_blobs(article))
    return bool(_STACK_FLEX_COL.search(text) and _STACK_GAP_48.search(text))


def assert_timeline_bubble_hierarchy(crate: Path) -> None:
    """#207: identity/time → body/subject → attachments on every bubble.

    WA and Gmail share that stack. Attachments never sit above the body.
    4/8 spacing on the stack. Followers may omit data-bubble-meta (#206).
    Do not soften #111/#117/#206/#120/#205. Not HTML mail / reactions /
    new platforms / sender_identity_id.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#207: App.svelte required (person-timeline bubble stack)")
    app = app_path.read_text()
    logic = _web_logic(crate)
    cleaned = _without_comments(app + "\n" + logic)
    block = _timeline_block(crate)
    markup = _svelte_markup(app)
    pt = markup.find("person-timeline")
    timeline_markup = markup[pt:] if pt >= 0 else markup
    articles = _timeline_articles(timeline_markup) or _timeline_articles(block)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    if not articles:
        fail("#207: person-timeline must render each message as an <article>")
    article = articles[0]

    # 1) Named stack hooks so the gate can see the order.
    have = {
        _BUBBLE_META: _hook_pos(article, _BUBBLE_META) >= 0,
        _BUBBLE_BODY: _hook_pos(article, _BUBBLE_BODY) >= 0,
        _BUBBLE_ATTACH: _hook_pos(article, _BUBBLE_ATTACH) >= 0,
    }
    missing = [name for name, ok in have.items() if not ok]
    if missing:
        fail(
            "#207: person-timeline <article> must name one stack with "
            "data-bubble-meta (identity/time), data-bubble-body (body/subject), "
            "and data-bubble-attach (CasAttach) — missing "
            + ", ".join(missing)
            + ". Source order on the article must be meta, then body, then "
            "attach. WA (isMailRow false) and Gmail (isMailRow true) share "
            "that order. Followers may omit data-bubble-meta (#206)"
        )

    meta_at = _hook_pos(article, _BUBBLE_META)
    body_at = _hook_pos(article, _BUBBLE_BODY)
    attach_at = _hook_pos(article, _BUBBLE_ATTACH)
    cas_at = _casattach_pos(article)

    # 2) Source order: meta → body → attach (meta may be gated for #206).
    if not (meta_at < body_at < attach_at):
        fail(
            "#207: source order on the person-timeline <article> must be "
            "data-bubble-meta, then data-bubble-body, then data-bubble-attach "
            "(identity/time → body/subject → attachments)"
        )

    # 3) CasAttach / attachments must not sit above the body wrapper.
    if cas_at >= 0 and cas_at < body_at:
        fail(
            "#207: CasAttach / attachments must not appear above the "
            "data-bubble-body wrapper in the person-timeline <article>"
        )
    if not _attach_wraps_cas(article):
        fail(
            "#207: data-bubble-attach must wrap CasAttach "
            "(attribute on CasAttach or on a wrapper that precedes it)"
        )

    # 4) WA and Gmail share that order (mail if / else both keep body before attach).
    branches = _split_mail_else(article)
    if branches:
        mail_br, wa_br = branches
        # Shared hooks wrapping both branches sit outside; each branch
        # must not reverse body/attach if it names them or mounts CasAttach.
        if mail_br and not _path_has_body_then_attach(mail_br):
            fail(
                "#207: Gmail (isMailRow true) path must keep data-bubble-body "
                "before data-bubble-attach / CasAttach — same stack as WA"
            )
        if wa_br and not _path_has_body_then_attach(wa_br):
            fail(
                "#207: WA (isMailRow false) path must keep data-bubble-body "
                "before data-bubble-attach / CasAttach — same stack as Gmail"
            )
        # Shared wrapper sits outside both branches; otherwise each branch
        # must name data-bubble-body (subject+quoted vs WA plain).
        mail_has = _BUBBLE_BODY in mail_br
        wa_has = _BUBBLE_BODY in wa_br
        body_wraps_both = (not mail_has) and (not wa_has) and body_at >= 0
        if not body_wraps_both and not (mail_has and wa_has):
            fail(
                "#207: WA and Gmail must share the same stack — put "
                "data-bubble-body around subject+body+quoted and the WA "
                "plain body (one wrapper, or the hook on both branches)"
            )
    elif _MAIL_ROW_GATE.search(article) is None and _MAIL_ROW_GATE.search(block):
        # Mail gate lives in script; both platforms still share one article stack.
        pass
    else:
        # No isMail split: one body path is fine if hooks are ordered.
        pass

    # 5) 4/8 spacing on the bubble stack — no odd arbitrary padding.
    stack_blobs = _stack_class_blobs(article)
    odd = _odd_stack_token(stack_blobs)
    if odd:
        fail(
            f"#207: bubble stack spacing must stay on the 4/8 scale "
            f"(gap-2 / gap-3, p-2 / p-3) — not {odd}"
        )
    if not _stack_uses_48(stack_blobs):
        fail(
            "#207: bubble stack must use 4/8 spacing "
            "(flex-col + gap-2/gap-3 and/or p-2/p-3 on the <article> or a "
            "flex-col wrapper). Do not change ESTIMATED_ROW_HEIGHT"
        )

    # 6) #111 stays: from_me left/right, run-start caption/<time>+platform,
    #    whitespace-pre-wrap, long URLs wrap.
    if not _FROM_ME_LAYOUT.search(block):
        fail(
            "#207: do not soften #111 — from_me must still choose a "
            "right/left bubble"
        )
    if "caption" not in block.lower() and "<time" not in block.lower():
        fail(
            "#207: do not soften #111 — run-start keeps the caption / <time>"
        )
    if (
        "row.platform" not in block
        and "platformLabel" not in block
        and "data-platform-chip" not in block
    ):
        fail(
            "#207: do not soften #111 — run-start keeps the platform chip"
        )
    if not _PRE_WRAP.search(block):
        fail("#207: do not soften #111 — bodies stay whitespace-pre-wrap")
    if not (
        "break-words" in block
        or "overflow-wrap" in block
        or "break-all" in block
    ):
        fail("#207: do not soften #111 — long URLs still wrap (break-words)")

    # 7) #117 stays: mail subject title, Show quoted, no {@html}, no cid:.
    if not (
        _standalone_subject_bindings(block)
        or _SUBJECT_TITLE_HELPER.search(block)
        or re.search(r"mail-subject|data-mail-subject", block, re.I)
    ):
        fail("#207: do not soften #117 — mail subject title stays")
    if not _SHOW_QUOTED.search(block) and not _SHOW_QUOTED.search(timeline_markup):
        fail("#207: do not soften #117 — Show quoted stays")
    if _HTML_BODY.search(block) or _HTML_BODY.search(article):
        fail("#207: do not soften #117 — no {@html} for bodies (not HTML mail)")
    if _CID_IMG.search(block) or _CID_IMG.search(article):
        fail("#207: do not soften #117 — no cid: images")

    # 8) #206 stays: followers may omit data-bubble-meta / caption.
    if not _followers_omit_caption(timeline_markup) and not _followers_omit_caption(block):
        fail(
            "#207: do not soften #206 — followers may omit data-bubble-meta / "
            "the caption; do not paint identity/time on every bubble"
        )

    # 9) #120 88/15 and #205 data-partial stay. Do not require a new height.
    if not re.search(r"ESTIMATED_ROW_HEIGHT\s*=\s*88", cleaned):
        fail("#207: do not soften #120 — keep ESTIMATED_ROW_HEIGHT = 88")
    if not re.search(r"\bOVERSCAN\s*=\s*15\b", cleaned):
        fail("#207: do not soften #120 — keep OVERSCAN = 15")
    if "data-partial" not in app and "data-partial" not in logic:
        fail("#207: do not soften #205 — pane Error+Retry (data-partial) stays")

    # 10) Not in scope.
    if re.search(r"\bsender_identity_id\b", article):
        fail(
            "#207: not in scope — do not add sender_identity_id on the bubble "
            "(no new IPC / sender display-name)"
        )
    if _SENDER_NAME_ON_BUBBLE.search(article):
        fail(
            "#207: not in scope — do not invent a sender display-name on the "
            "bubble (identity is from_me + the caption row)"
        )
    if _REACTIONS_UI.search(article) or _REACTIONS_UI.search(timeline_markup):
        fail("#207: not in scope — no reactions UI")
    if _NEW_PLATFORM_ON_BUBBLE.search(article):
        fail("#207: not in scope — no new platforms on the bubble")

    # 11) D24: keep #111/#117/#206 sentences; add the shared stack line.
    if not dtxt.strip():
        fail(
            "#207: docs/user/app.md required — every bubble stacks "
            "identity/time, then body/subject, then attachments "
            "(WA and Gmail the same)"
        )
    if not re.search(r"Long URLs wrap", dtxt):
        fail("#207: do not drop the #111 wrap sentence in docs/user/app.md")
    if not re.search(r"whitespace-pre-wrap", dtxt):
        fail(
            "#207: do not drop the #111 whitespace-pre-wrap sentence in "
            "docs/user/app.md"
        )
    if not re.search(r"hour:minute", dtxt, re.I):
        fail(
            "#207: do not drop the #111 hour:minute caption sentence in "
            "docs/user/app.md"
        )
    if not re.search(r"Show quoted", dtxt):
        fail("#207: do not drop the #117 fold sentence in docs/user/app.md")
    if not _docs_206_ok(dtxt):
        fail(
            "#207: do not drop the #206 consecutive-caption sentence in "
            "docs/user/app.md"
        )
    if not _docs_207_ok(dtxt):
        fail(
            "#207: docs/user/app.md must say every bubble stacks "
            "identity/time, then body/subject, then attachments "
            "(WA and Gmail the same)"
        )


def assert_timeline_attach_slot(crate: Path) -> None:
    """#207 follow-up: no empty attach flex sibling; no gap-2 + ul.mt-2.

    Person-timeline must not keep an always-on empty attach wrapper. Hook
    on <CasAttach> (empty component is not a flex item) or wrap it in
    {#if item.row.attachments?.length}. Timeline body-to-attach spacing
    is only the article gap-2/gap-3 — CasAttach ul.mt-2 must not stack
    on the timeline call. SearchPane may keep mt-2. Do not soften the
    #207 stack-order hooks or #111/#117/#206/#120/#205.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#207: App.svelte required (person-timeline attach slot)")
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail("#207: CasAttach.svelte required (timeline attach slot / gap)")
    app = app_path.read_text()
    cas = cas_path.read_text()
    markup = _svelte_markup(app)
    pt = markup.find("person-timeline")
    timeline_markup = markup[pt:] if pt >= 0 else markup
    block = _timeline_block(crate)
    articles = _timeline_articles(timeline_markup) or _timeline_articles(block)
    if not articles:
        fail("#207: person-timeline must render each message as an <article>")

    empty_name: str | None = None
    double_gap = False
    ul_open = _cas_items_ul_open(cas)
    for article in articles:
        if empty_name is None:
            empty_name = _empty_attach_wrapper_name(article)
        if _article_has_col_gap23(article) and not _timeline_cas_drops_mt2(
            cas, article, ul_open
        ):
            double_gap = True

    problems: list[str] = []
    if empty_name:
        problems.append(
            "person-timeline must not keep an always-on empty attach flex "
            f"sibling — data-bubble-attach is on a wrapper <{empty_name}> "
            "that is not gated by attachments length and is not <CasAttach> "
            "itself (put the hook on <CasAttach>, or wrap it in "
            "{#if item.row.attachments?.length})"
        )
    if double_gap:
        problems.append(
            "timeline body-to-attach must not stack article gap-2/gap-3 "
            "plus CasAttach inner mt-2 (drop ul.mt-2 on the timeline "
            "CasAttach via a no-margin prop/class; SearchPane may keep mt-2)"
        )
    if problems:
        fail("#207: " + "; ".join(problems))
