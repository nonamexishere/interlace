"""#311 — jump to a sticky day heading from a pane date control.

Pane type="date" next to #tl-find (not #from/#to/#q/data-tl-find).
No palette command. jumpToLocalDay: first filteredTimeline row with
localDay(sent_at, platform) === YYYY-MM-DD; that day's first
.day-heading sits at the top of #person-timeline (not only
ensureTlIndexVisible). Older day: Load older / selectPerson(..., true)
/ prepend until the heading exists or the thread starts (empty or
short page). Do not replace the window. No sent_at → no heading.
Quiet miss. Seek in the current platform/kind filter.

Must-IDs: jump-day-mounted, jump-day-older, jump-day-no-sent-at,
jump-day-localday, jump-day-keep-112-268, jump-day-keep-224-113,
jump-day-keep-215-310, jump-day-not-edit, jump-day-not-calendar,
jump-day-d24.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.find_in_conversation import _FIND_HOOK, _filter_pred
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.scan import (
    _function_body,
    _search_pane_blob,
    _svelte_markup,
    _ts_fn_body,
    _without_comments,
)
from tauri_gate.search_field_keys import _API_SEARCH_CALL
from tauri_gate.timeline_rows_lib import _SEARCH_TYPE_DATE, _TZ_PICKER

_ISSUE = "#311"
_PANE = (
    "TimelinePane.svelte",
    "TimelineList.svelte",
    "TimelineRows.svelte",
)
_HELPERS = (
    "jumpDay.ts",
    "jumpToDay.ts",
    "jumpToLocalDay.ts",
    "TimelineJumpDay.ts",
    "formatTime.ts",
)
_JUMP_NAMES = (
    "jumpToLocalDay",
    "scrollDayHeadingToTop",
    "jumpToDay",
    "goToLocalDay",
    "seekLocalDay",
    "jumpDay",
    "goToDay",
    "scrollToDayHeading",
    "seekDayHeading",
    "firstLocalDayIndex",
    "localDayIndex",
    "dayHeadingTop",
)
_JUMP_NAME_RX = re.compile(r"\b(?:" + "|".join(_JUMP_NAMES) + r")\b")
_STOLEN = re.compile(r"""id\s*=\s*[\"'](?:from|to|q)[\"']|data-tl-find\b""")
_HEADING = re.compile(r"day-heading")
_SCROLL_TOP = re.compile(r"\bwriteScrollTop\b|\btlScrollTop\s*=|\.scrollTop\s*=")
_PERSON_TL = re.compile(r"person-timeline")
_ENSURE_ONLY = re.compile(r"\bensureTlIndexVisible\s*\(")
_OLDER = re.compile(
    r"selectPerson\s*\([^)]*true|\bonPrepend\b|personTimeline\s*\("
)
_LOOP = re.compile(r"\b(?:for|while)\b")
_SHORT = re.compile(
    r"\.length\s*[<!=]=?\s*(?:limit|pageLimit|80|batchLimit)|\.length\s*===\s*0"
    r"|batch\.length\s*<|chrono\.length\s*<"
)
_REPLACE = re.compile(r"\bopenPersonAtMessage\s*\(|timeline\s*=\s*loaded\b")
_TOAST = re.compile(r"\bshowToast\s*\(|\bshowErr\s*\(")
_NEAREST = re.compile(r"\bnearestVisibleTlIndex\b|\bnearestDay\b|snapToNearest")
_CLEAR_CHIPS = re.compile(
    r"platformFilter\s*=\s*[\"']all[\"']|kindFilter\s*=\s*[\"']all[\"']"
)
_LOCALDAY_CALL = re.compile(r"\blocalDay\s*\([^)]*\bplatform\b")
_EMPTY_DAY = re.compile(
    r"localDay\s*\([^)]*\)\s*===?\s*[\"'][\"']"
    r"|\bif\s*\(\s*!\s*(?:key|day|dayKey|localDay)"
    r"|if\s*\(\s*!?\s*\w+\s*\)\s*return"
)
_SENT_AT_WRITE = re.compile(
    r"\.sent_at\s*=|update(?:Message)?SentAt|UPDATE\s+\w+\s+SET\b[^;]{0,400}\bsent_at\b",
    re.I | re.S,
)
_CALENDAR = re.compile(
    r"type\s*=\s*[\"']month[\"']|month-grid|calendar-grid|daysWithMail"
    r"|thread[- ]calendar|which days have mail",
    re.I,
)
_PALETTE_DAY = re.compile(
    r"go to day|jump to day|jumpToLocalDay|type\s*=\s*[\"']date[\"']",
    re.I,
)
_DOCS_JUMP = re.compile(
    r"(?:date control|type=\"date\"|jump(?:s)? to (?:a |the )?(?:day|heading))"
    r".{0,200}(?:day heading|sticky heading|sticky day)"
    r"|(?:day heading|sticky heading).{0,200}"
    r"(?:date control|jump(?:s)? to)",
    re.I | re.S,
)
_DOCS_OLDER = re.compile(
    r"(?:older day|jump(?:s)? to an older|Load older).{0,160}"
    r"(?:Load older|heading exists|thread starts|start of the thread)",
    re.I | re.S,
)
_DOCS_HOST = re.compile(r"(?:host|Mac)(?:'s)?\s+time\s*zone", re.I)
_DOCS_UTC = re.compile(r"(?:stor(?:e|age|ed)|archive JSON|SQLite).{0,80}UTC", re.I | re.S)
_DOCS_NO_DATE = re.compile(
    r"(?:no sent_at|without sent_at|missing sent_at|no `sent_at`).{0,80}no heading"
    r"|no heading.{0,80}(?:no sent_at|without sent_at|missing sent_at|no `sent_at`)",
    re.I | re.S,
)
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][\w]*)["']""")
_VIRTUALIZE = re.compile(r"\bVIRTUALIZE_AFTER\s*=\s*250\b")
_EST = re.compile(r"\bESTIMATED_ROW_HEIGHT\s*=\s*88\b")
_LOAD_HOOK = re.compile(r"data-load-older")
_PREPEND_SHIFT = re.compile(r"\bshiftHeightsForPrepend\b")
_PREPEND_KEEP = re.compile(r"\bpreserveScrollAfterPrepend\b")


def _read(crate: Path, rel: str) -> str:
    p = crate / "web" / "lib" / rel
    return p.read_text() if p.is_file() else ""


def _pane_blob(crate: Path) -> str:
    return "\n".join(_read(crate, n) for n in _PANE)


def _helper_blob(crate: Path) -> str:
    return "\n".join(_read(crate, n) for n in _HELPERS)


def _date_tags(markup: str) -> list[str]:
    tags: list[str] = []
    for m in _SEARCH_TYPE_DATE.finditer(markup):
        lt = markup.rfind("<", 0, m.start())
        gt = markup.find(">", m.end())
        if lt >= 0 and gt > lt:
            tags.append(markup[lt : gt + 1])
    return tags


def _jump_pane_tags(markup: str) -> list[str]:
    return [t for t in _date_tags(markup) if not _STOLEN.search(t)]


def _named_bodies(src: str, names: tuple[str, ...]) -> str:
    chunks: list[str] = []
    for name in names:
        body = _ts_fn_body(src, name) or _function_body(src, name)
        if body.strip():
            chunks.append(body)
    return "\n".join(chunks)


def _jump_src(crate: Path) -> str:
    src = _without_comments(_pane_blob(crate) + "\n" + _helper_blob(crate))
    return _named_bodies(src, _JUMP_NAMES)


def _fmt_local_day(crate: Path) -> str:
    src = _without_comments(_read(crate, "formatTime.ts"))
    return _ts_fn_body(src, "localDay") or _function_body(src, "localDay") or ""


def assert_jump_day_heading(crate: Path) -> None:
    """#311: pane type=date jumps to the first sticky day heading."""
    pane_path = crate / "web" / "lib" / "TimelinePane.svelte"
    list_path = crate / "web" / "lib" / "TimelineList.svelte"
    rows_path = crate / "web" / "lib" / "TimelineRows.svelte"
    if not pane_path.is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (pane type=\"date\" next to find)")
    if not list_path.is_file():
        fail(f"{_ISSUE}: TimelineList.svelte required (heading at top of #person-timeline)")
    if not rows_path.is_file():
        fail(f"{_ISSUE}: TimelineRows.svelte required (.day-heading / Load older)")
    pane = pane_path.read_text()
    lst = list_path.read_text()
    rows = rows_path.read_text()
    pane_c = _without_comments(pane)
    list_c = _without_comments(lst)
    rows_c = _without_comments(rows)
    pane_m = _svelte_markup(pane)
    list_m = _svelte_markup(lst)
    rows_m = _svelte_markup(rows)
    pal = _read(crate, "CommandPalette.svelte")
    virt = _read(crate, "TimelineVirtual.ts")
    search = _search_pane_blob(crate)
    api = _read(crate, "api.ts")
    jump = _jump_src(crate)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) jump-day-mounted — pane type=date next to find; heading at top.
    tags = _jump_pane_tags(pane_m)
    if not tags:
        fail(
            f"{_ISSUE}: person timeline pane must have a type=\"date\" control "
            "next to find that jumps to a host-calendar day heading "
            "(not #from/#to/#q/data-tl-find)"
        )
    if _SEARCH_TYPE_DATE.search(list_m) or _SEARCH_TYPE_DATE.search(rows_m):
        fail(
            f"{_ISSUE}: date control lives in TimelinePane chrome next to find, "
            "not inside #person-timeline"
        )
    if not _FIND_HOOK.search(pane_m):
        fail(
            f"{_ISSUE}: keep #310 find (data-tl-find / id tl-find) — "
            "the date control sits next to it"
        )
    if not (
        _FIND_HOOK.search(pane_m)
        and any(_SEARCH_TYPE_DATE.search(t) for t in tags)
    ):
        fail(f"{_ISSUE}: type=\"date\" must sit next to find on the timeline pane")
    if _PALETTE_DAY.search(pal):
        fail(
            f"{_ISSUE}: entry is the pane date control only — "
            "no palette day command"
        )
    if not _JUMP_NAME_RX.search(pane_c + "\n" + jump) or not jump.strip():
        fail(
            f"{_ISSUE}: jumpToLocalDay (or scrollDayHeadingToTop) required — "
            "first filteredTimeline localDay match is that day's first heading"
        )
    if _ENSURE_ONLY.search(jump) and not _HEADING.search(jump):
        fail(
            f"{_ISSUE}: do not reuse ensureTlIndexVisible as the only scroll "
            "(that nudges a bubble; Acceptance is the heading at the top)"
        )
    if not (
        _HEADING.search(jump)
        and _SCROLL_TOP.search(jump)
        and _PERSON_TL.search(jump + "\n" + list_c)
    ):
        fail(
            f"{_ISSUE}: jumping to a host-calendar day already in the loaded "
            "filteredTimeline must put that day's first .day-heading at the "
            "top of #person-timeline"
        )

    # 2) jump-day-older — prepend Load older; do not replace the window.
    if not _OLDER.search(jump) or not _LOOP.search(jump):
        fail(
            f"{_ISSUE}: an older day not in the loaded set must Load older "
            "(selectPerson(..., true) / personTimeline + before prepend) "
            "until that heading exists or the thread starts"
        )
    if not _SHORT.search(jump):
        fail(
            f"{_ISSUE}: stop Load older on an empty or short page "
            "(do not replace the window)"
        )
    if _REPLACE.search(jump):
        fail(
            f"{_ISSUE}: do not replace the loaded window "
            "(openPersonAtMessage shape is a #124 seek, not a day jump)"
        )

    # 3) jump-day-no-sent-at
    if not re.search(
        r"sent_at\s*&&\s*localDay|localDay\([^)]*\)\s*&&",
        rows_m,
    ) and not re.search(
        r"group\.rows\[0\]\?\.row\.sent_at\s*&&\s*localDay",
        rows_c,
    ):
        fail(
            f"{_ISSUE}: a row with no sent_at still has no heading "
            "(do not invent one)"
        )
    if not _EMPTY_DAY.search(jump):
        fail(
            f"{_ISSUE}: jump must not invent a heading when localDay is \"\" "
            "(empty sent_at stays heading-less)"
        )

    # 4) jump-day-localday
    if not _LOCALDAY_CALL.search(jump) and not re.search(
        r"\blocalDay\s*\(",
        jump,
    ):
        fail(
            f"{_ISSUE}: the seek key is localDay(sent_at, platform) "
            "(host YYYY-MM-DD — not UTC slice(0,10) on zoned rows)"
        )
    if not re.search(r"\bplatform\b", jump):
        fail(
            f"{_ISSUE}: localDay must receive platform "
            "(WA / omitted wall-clock digits; Gmail / zoned Date + local getters)"
        )
    ld = _fmt_local_day(crate)
    if not re.search(r"whatsapp|wallClock", ld, re.I):
        fail(
            f"{_ISSUE}: localDay must keep the WhatsApp / omitted wall-clock "
            "escape (do not Date-convert WhatsApp)"
        )
    if not re.search(r"new\s+Date\s*\(", ld) or not re.search(
        r"\bgetFullYear\s*\(",
        ld,
    ):
        fail(
            f"{_ISSUE}: localDay must still Date-convert zoned / Gmail rows "
            "with host getFullYear/getMonth/getDate"
        )
    if re.search(r"sent_at\.slice\s*\(\s*0\s*,\s*10", jump) and not re.search(
        r"\blocalDay\s*\(",
        jump,
    ):
        fail(
            f"{_ISSUE}: do not UTC-slice zoned sent_at as the jump key "
            "(use localDay)"
        )

    # 5) quiet miss + seek in current filter
    if _TOAST.search(jump):
        fail(f"{_ISSUE}: a miss stays quiet (no toast / showErr)")
    if _NEAREST.search(jump):
        fail(f"{_ISSUE}: a miss stays put — no snap to the nearest day")
    if _CLEAR_CHIPS.search(jump):
        fail(
            f"{_ISSUE}: seek in the current platform/kind filteredTimeline "
            "(do not clear chips)"
        )
    if not re.search(r"\bfilteredTimeline\b", jump):
        fail(
            f"{_ISSUE}: seek the first localDay match in filteredTimeline "
            "(a day only in filtered-out rows is a quiet miss)"
        )
    pred = _filter_pred(pane_c)
    if pred and (
        not re.search(r"platformFilter", pred) or not re.search(r"kindFilter", pred)
    ):
        fail(
            f"{_ISSUE}: filteredTimeline stays platform + kind chips "
            "(jump walks that list)"
        )

    # 6) jump-day-keep-112-268
    if not _HEADING.search(rows_m):
        fail(f"{_ISSUE}: keep #112 .day-heading (sticky DD/MM/YYYY)")
    css = _read(crate, "../app.css")
    if not re.search(r"\.day-heading[^}]*sticky|position\s*:\s*sticky", css, re.I | re.S):
        fail(f"{_ISSUE}: keep #112 sticky day headings")
    if not re.search(r"\blocalDayLabel\b", list_c):
        fail(f"{_ISSUE}: keep #112/#268 localDayLabel (DD/MM/YYYY, host TZ)")
    if _TZ_PICKER.search(pane_c) or _TZ_PICKER.search(search):
        fail(f"{_ISSUE}: keep #268 — no timezone picker")
    if not re.search(r"\bsent_at\??\s*:\s*string", api):
        fail(f"{_ISSUE}: keep #268 — api.ts sent_at stays an ISO string")
    if re.search(r"\bsent_at\??\s*:\s*Date\b", api):
        fail(f"{_ISSUE}: api.ts sent_at must stay an ISO string, not Date")
    if not re.search(r"\bid=[\"']from[\"']", search) or not re.search(
        r"\bid=[\"']to[\"']",
        search,
    ):
        fail(f"{_ISSUE}: keep Search #from/#to (do not steal those ids)")
    if not _SEARCH_TYPE_DATE.search(search):
        fail(f"{_ISSUE}: keep Search type=\"date\" #from/#to")

    # 7) jump-day-keep-224-113
    if not _VIRTUALIZE.search(virt) and not _VIRTUALIZE.search(list_c):
        fail(f"{_ISSUE}: keep #224 VIRTUALIZE_AFTER = 250 (do not turn virtualization off)")
    if not _EST.search(virt) and not _EST.search(list_c):
        fail(f"{_ISSUE}: keep #224 ESTIMATED_ROW_HEIGHT = 88")
    if not _LOAD_HOOK.search(rows_m):
        fail(f"{_ISSUE}: keep #113 Load older at the top (data-load-older)")
    ol = rows_m.find("<ol")
    load_at = rows_m.find("data-load-older")
    if ol >= 0 and load_at > ol:
        fail(f"{_ISSUE}: keep #113 Load older at the top of the list, not under it")
    if not _PREPEND_SHIFT.search(list_c) or not _PREPEND_KEEP.search(list_c):
        fail(
            f"{_ISSUE}: keep #113/#224 prepend height shift + "
            "preserveScrollAfterPrepend"
        )
    if re.search(r"VIRTUALIZE_AFTER\s*=\s*(?:Infinity|1e9|99999)", jump + "\n" + list_c):
        fail(f"{_ISSUE}: jump remounts a virtualized day — do not disable virtualization")

    # 8) jump-day-keep-215-310
    if "data-command-palette" not in pal:
        fail(f"{_ISSUE}: keep #215 command palette")
    if _API_SEARCH_CALL.search(pal):
        fail(f"{_ISSUE}: keep #215 palette local (no api.search / FTS)")
    if not re.search(r"onView\([\"']people[\"']\)", pal) or not re.search(
        r"Jump to person",
        pal,
    ):
        fail(f"{_ISSUE}: keep #215 palette views + jump-to-person (loaded people)")
    if not re.search(r"id=[\"']tl-find[\"']", pane_m) or not _FIND_HOOK.search(pane_m):
        fail(f"{_ISSUE}: keep #310 find field (id=tl-find / data-tl-find)")
    find_tag = ""
    fm = _FIND_HOOK.search(pane_m)
    if fm:
        lt = pane_m.rfind("<", 0, fm.start() + 1)
        gt = pane_m.find(">", fm.end())
        find_tag = pane_m[lt : gt + 1] if lt >= 0 and gt > lt else ""
    if find_tag and not re.search(r"type\s*=\s*[\"']search[\"']", find_tag):
        fail(f"{_ISSUE}: keep #310 find as type=\"search\" (date is a sibling)")

    # 9) jump-day-not-edit
    if _SENT_AT_WRITE.search(jump) or _SENT_AT_WRITE.search(pane_c):
        fail(f"{_ISSUE}: jump does not UPDATE messages.sent_at")

    # 10) jump-day-not-calendar
    if _CALENDAR.search(pane_c + "\n" + list_c + "\n" + pal):
        fail(
            f"{_ISSUE}: not a calendar product "
            "(no month grid / thread calendar / which-days-have-mail)"
        )
    if len(tags) > 1:
        fail(f"{_ISSUE}: one pane type=\"date\" day control — not a month grid")

    # 11) jump-day-d24
    if not dtxt.strip():
        fail(f"{_ISSUE}: docs/user/app.md required (jump to a day heading)")
    if not _DOCS_JUMP.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say a date control jumps to "
            "the sticky day heading"
        )
    if not _DOCS_OLDER.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say Load older runs for an older day"
        )
    if not _DOCS_HOST.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must keep host / Mac timezone display")
    if not _DOCS_UTC.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must keep storage UTC")
    if not _DOCS_NO_DATE.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must keep no sent_at → no heading")

    # 12) visible chrome copy is en+tr (#131). Ada only.
    for tag in tags:
        vis = re.search(r"(?:placeholder|aria-label|title)\s*=\s*\{?([^}>\n]+)", tag, re.I)
        if not vis:
            continue
        raw = vis.group(1)
        if re.search(r"[\"'][A-Za-z]", raw) and not _T_CALL.search(raw):
            fail(
                f"{_ISSUE}: date-control visible chrome copy must use t() "
                "(en+tr, #131; placeholders Ada only)"
            )
        km = _T_CALL.search(raw)
        if km:
            key = km.group(1)
            en_p = crate / "web" / "lib" / "locales" / "en.ts"
            tr_p = crate / "web" / "lib" / "locales" / "tr.ts"
            en = _chrome_pack_entries(en_p.read_text()) if en_p.is_file() else {}
            tr = _chrome_pack_entries(tr_p.read_text()) if tr_p.is_file() else {}
            if key not in en or key not in tr:
                fail(
                    f"{_ISSUE}: date-control copy key {key!r} must exist "
                    "in en.ts and tr.ts (#131)"
                )
    if re.search(r"/Users/|/home/", pane_c + "\n" + jump):
        fail(f"{_ISSUE}: tests stay placeholders (Ada) — no real home paths")
