"""Timeline row chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.timeline_rows_lib import *


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
    app = _web_logic(crate)
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

    if (
        not _PREV_DAY.search(block)
        and not _PREV_DAY.search(app)
        and not _PREV_DAY.search(logic)
    ):
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

    if (
        not _SENT_AT_GUARD.search(block)
        and not _SENT_AT_GUARD.search(app)
        and not _SENT_AT_GUARD.search(logic)
    ):
        fail(
            "#112: missing sent_at must not crash; guard before reading a calendar day "
            "(do not invent a heading for a row with no date)"
        )
    day_src = app + "\n" + block + "\n" + logic
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
    app = _web_logic(crate)
    logic = app
    cleaned = _without_comments(app)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) Day heading / grouping key is the host calendar day, not UTC slice(0, 10).
    markup = _svelte_markup(app)
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
    search = _search_pane_blob(crate) if search_path.is_file() else ""
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

from tauri_gate.timeline_rows_more import assert_gmail_timeline_rows
