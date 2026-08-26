"""Timeline row chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations
import re
from pathlib import Path
from common import fail, repo_root
from tauri_gate.scan import (
    _BUBBLE_ME_VARS, _BUBBLE_THEM_VARS, _HTML_BODY, _call_arg,
    _css_var, _function_body, _helper_with_callees, _timeline_block,
    _ts_function_body, _web_logic, _web_sources, _without_comments,
)
from tauri_gate.import_boot import (
    _HUMAN_TIME_HELPERS, _PRE_WRAP,
)
from tauri_gate.media_linkify import _SHOW_QUOTED
from tauri_gate.status_toasts import (
    _MONTH_SHORT, _person_detail_markup,
)
from tauri_gate.timeline_hierarchy import (
    _CID_IMG,
    _DAY_HEADING,
    _FROM_ME_LAYOUT,
    _MAIL_ROW_GATE,
    _SUBJECT_TITLE_HELPER,
    _grouping_logic_src,
    _standalone_subject_bindings,
)
from tauri_gate.timeline_scroll import _derived_body
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
# Sole body fallback that treats subject as body when body is empty — not a title.
_SUBJECT_BODY_FALLBACK_ONLY = re.compile(
    r"(?:body_text\s*\|\|\s*(?:(?:item\.)?row\.)?subject"
    r"|(?:displayBody|bodyText)\s*\(\s*(?:(?:item\.)?row\.)?body_text\s*\|\|"
    r"\s*(?:(?:item\.)?row\.)?subject)",
    re.I,
)
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
