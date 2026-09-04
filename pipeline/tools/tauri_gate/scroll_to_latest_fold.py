"""#313 fold — keep #113 / #224 / #310 / #311; not unread; not auto-stick; D24.

Do not rewrite those older asserts. Latest uses scrollHeight / spacers.
Wheel / pointer still stopPinLatest. 600ms settle must end and must not
restart on measure alone.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.find_in_conversation import _FIND_HOOK
from tauri_gate.jump_day_heading import (
    _EST,
    _LOAD_HOOK,
    _PREPEND_KEEP,
    _PREPEND_SHIFT,
    _VIRTUALIZE,
)
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.scan import (
    _function_body,
    _svelte_markup,
    _ts_fn_body,
    _web_logic,
    _without_comments,
)
from tauri_gate.timeline_latest import (
    _LOAD_OLDER,
    _SCROLL_PRESERVE,
    _SCROLL_TO_BOTTOM,
    _clears_loading_before_open_scroll,
    _nested_raf_around_open_scroll,
    _timeline_has_bottom_pad,
)
from tauri_gate.timeline_rows_lib import _SEARCH_TYPE_DATE

_ISSUE = "#313"
_UNREAD = re.compile(r"\bunread(?:Count|Badge|s)?\b", re.I)
_DOCS_LATEST = re.compile(
    r"(?:scroll(?:s|ed)? up|after you scroll up).{0,240}Latest"
    r"|Latest.{0,240}(?:scroll(?:s|ed)? up|newest bubble|footer)",
    re.I | re.S,
)
_DOCS_HIDE = re.compile(
    r"Latest.{0,220}hid(?:e|es|den).{0,100}bottom"
    r"|hid(?:e|es|den).{0,100}(?:at )?(?:the )?bottom.{0,100}Latest",
    re.I | re.S,
)
_DOCS_REDUCE = re.compile(
    r"Latest.{0,280}reduced[\s-]*motion.{0,80}instant"
    r"|reduced[\s-]*motion.{0,80}instant.{0,280}Latest",
    re.I | re.S,
)
_DOCS_UNREAD = re.compile(
    r"Latest.{0,240}(?:not|no)\s+unread|(?:not|no)\s+unread.{0,240}Latest",
    re.I | re.S,
)
_DOCS_STICK = re.compile(
    r"Latest.{0,240}(?:not|no)\s+auto-?stick|(?:not|no)\s+auto-?stick.{0,240}Latest",
    re.I | re.S,
)
_WATCH_600 = re.compile(r"setTimeout\s*\(\s*stopPinLatest\s*,\s*600\s*\)")
_LATEST_TEXT = re.compile(r">\s*Latest\s*<")
_T_LATEST = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][\w]*)["']""")


def _read(crate: Path, rel: str) -> str:
    p = crate / "web" / "lib" / rel
    return p.read_text() if p.is_file() else ""


def _fn(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name) or ""


def _latest_surface(list_m: str, pane_m: str, list_c: str, pane_c: str, keys: list[str]) -> str:
    chunks = []
    for mk in (list_m, pane_m):
        for m in _LATEST_TEXT.finditer(mk):
            chunks.append(mk[max(0, m.start() - 280) : m.end() + 280])
        for k in keys:
            for m in re.finditer(rf"""\bt\s*\(\s*["']{re.escape(k)}["']""", mk):
                chunks.append(mk[max(0, m.start() - 280) : m.end() + 280])
    for name in (
        "showLatest",
        "scrollToLatest",
        "goToLatest",
        "onLatestClick",
        "handleLatest",
        "tlShowLatest",
        "latestVisible",
    ):
        chunks.append(_fn(list_c + "\n" + pane_c, name))
    return "\n".join(chunks)


def assert_scroll_to_latest_fold(crate: Path) -> None:
    """#313 keep-checks + not-unread / not-autostick / D24."""
    list_path = crate / "web" / "lib" / "TimelineList.svelte"
    pane_path = crate / "web" / "lib" / "TimelinePane.svelte"
    if not list_path.is_file():
        fail(f"{_ISSUE}: TimelineList.svelte required (keep #113 pin + Latest overlay)")
    if not pane_path.is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (keep #113 / #310 / #311)")
    lst = list_path.read_text()
    pane = pane_path.read_text()
    list_c = _without_comments(lst)
    pane_c = _without_comments(pane)
    list_m = _svelte_markup(lst)
    pane_m = _svelte_markup(pane)
    rows_m = _svelte_markup(_read(crate, "TimelineRows.svelte"))
    virt = _read(crate, "TimelineVirtual.ts")
    logic = _web_logic(crate)
    en_p = crate / "web" / "lib" / "locales" / "en.ts"
    en = _chrome_pack_entries(en_p.read_text()) if en_p.is_file() else {}
    latest_keys = [k for k, v in en.items() if v.strip() == "Latest"]
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) latest-keep-113
    if not _SCROLL_TO_BOTTOM.search(logic):
        fail(
            f"{_ISSUE}: keep #113 open-person pin to latest "
            "(scrollTop = scrollHeight)"
        )
    if not _SCROLL_PRESERVE.search(logic):
        fail(
            f"{_ISSUE}: keep #113 Load older prepend without jumping "
            "the viewport"
        )
    if not _LOAD_OLDER.search(list_m) and not _LOAD_OLDER.search(rows_m):
        fail(f"{_ISSUE}: keep #113 Load older at the top of the list")
    if not _clears_loading_before_open_scroll(logic, logic):
        fail(f"{_ISSUE}: keep #113 tlLoading = false before the open-person scroll")
    if not _nested_raf_around_open_scroll(logic, logic):
        fail(f"{_ISSUE}: keep #113 nested requestAnimationFrame around the open-person pin")
    if not _timeline_has_bottom_pad(crate, logic):
        fail(
            f"{_ISSUE}: keep #113 last bubble above the text-only footer "
            "(pb-8 / pad on #person-timeline)"
        )
    if "applyOpenPersonWindow" not in list_c or "watchPinLatest" not in list_c:
        fail(f"{_ISSUE}: keep #113 applyOpenPersonWindow + watchPinLatest")
    if not _PREPEND_SHIFT.search(list_c) or not _PREPEND_KEEP.search(list_c):
        fail(
            f"{_ISSUE}: keep #113/#224 shiftHeightsForPrepend + "
            "preserveScrollAfterPrepend"
        )
    if _LOAD_HOOK.search(rows_m):
        ol = rows_m.find("<ol")
        load_at = rows_m.find("data-load-older")
        if ol >= 0 and load_at > ol:
            fail(f"{_ISSUE}: keep #113 Load older at the top of the list, not under it")

    # 2) latest-keep-224
    if not _VIRTUALIZE.search(virt) and not _VIRTUALIZE.search(list_c):
        fail(f"{_ISSUE}: keep #224 VIRTUALIZE_AFTER = 250")
    if not _EST.search(virt) and not _EST.search(list_c):
        fail(f"{_ISSUE}: keep #224 ESTIMATED_ROW_HEIGHT = 88")
    if "spacerTop" not in list_c or "spacerBottom" not in list_c:
        fail(
            f"{_ISSUE}: keep #224 spacerTop / spacerBottom — Latest uses "
            "scrollHeight / spacers (last row may be unmounted)"
        )
    flush = _fn(list_c, "flushRowMeasures")
    if not re.search(r"!pinLatestObs", flush):
        fail(
            f"{_ISSUE}: keep #224 measure skip — flushRowMeasures must not "
            "writeScrollTop while pinLatestObs is set"
        )

    # 3) latest-keep-310-311
    if not re.search(r"""id=["']tl-find["']""", pane_m) or not _FIND_HOOK.search(pane_m):
        fail(f"{_ISSUE}: keep #310 find field (id=tl-find / data-tl-find)")
    if "data-tl-hit-count" not in pane_m:
        fail(f"{_ISSUE}: keep #310 find hit count (data-tl-hit-count)")
    if not _SEARCH_TYPE_DATE.search(pane_m):
        fail(f"{_ISSUE}: keep #311 jump-to-day type=\"date\" next to find")
    if not re.search(r"\bjumpToLocalDay\b", pane_c):
        fail(f"{_ISSUE}: keep #311 jumpToLocalDay")
    if not re.search(r"\bpinDayAtTop\b", list_c):
        fail(f"{_ISSUE}: keep #311 pinDayAtTop")
    if not re.search(r"\bcancelDayHeadingPin\b", list_c):
        fail(f"{_ISSUE}: keep #311 cancelDayHeadingPin")

    # 4) latest-not-unread
    surface = _latest_surface(list_m, pane_m, list_c, pane_c, latest_keys)
    if _UNREAD.search(surface):
        fail(
            f"{_ISSUE}: no unread badge / unread count on the Latest control "
            "or the pane"
        )
    if re.search(r"\bbadge\b", surface, re.I) and _UNREAD.search(surface):
        fail(f"{_ISSUE}: no unread badge on Latest")

    # 5) latest-not-autostick
    wheel = _fn(list_c, "onTimelineWheel")
    if "stopPinLatest" not in wheel:
        fail(
            f"{_ISSUE}: wheel must still stopPinLatest "
            "(do not auto-stick while reading up)"
        )
    scroll = _fn(list_c, "onTimelineScroll")
    if "stopPinLatest" not in scroll or not re.search(r"scrollHeight\s*-\s*4", scroll):
        fail(
            f"{_ISSUE}: pointer scroll must still stopPinLatest when not at "
            "the bottom (4px slop — do not auto-stick while reading up)"
        )
    watch = _fn(list_c, "watchPinLatest")
    if not _WATCH_600.search(watch) and not _WATCH_600.search(list_c):
        fail(
            f"{_ISSUE}: Latest settle observer must end "
            "(watchPinLatest setTimeout(stopPinLatest, 600)) and must not "
            "restart on measure alone"
        )
    if re.search(r"\bwatchPinLatest\b", flush):
        fail(
            f"{_ISSUE}: measure must not restart watchPinLatest "
            "(settle ends; no auto-stick on measure alone)"
        )

    # 6) latest-d24
    if not dtxt.strip():
        fail(
            f"{_ISSUE}: docs/user/app.md required — after you scroll up, a "
            "quiet Latest returns you to the newest bubble above the footer"
        )
    if not _DOCS_LATEST.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say that after you scroll up, "
            "a quiet Latest returns you to the newest bubble above the footer"
        )
    if not _DOCS_HIDE.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say Latest hides at the bottom"
        )
    if not _DOCS_REDUCE.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say Latest reduced motion is instant"
        )
    if not _DOCS_UNREAD.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must say Latest is not unread")
    if not _DOCS_STICK.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must say Latest is not auto-stick")
