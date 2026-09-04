"""#314 fold — keep #113 / #224 / #310 / #311; no autoscroll; D24; locale.

Do not rewrite those older asserts. Chrome measure still includes
[data-load-older]. Key and click stay explicit. Visible Load older stays
hardcoded English unless someone moves it to t() (then en+tr, no third pack).
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

_ISSUE = "#314"
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][\w]*)["']""")
_PREPEND_CALL = re.compile(
    r"\bselectPerson\s*\(\s*[^,)]+\s*,\s*(?:true|append)\s*[,)]"
    r"|\b(?:loadOlder|onPrepend|prependOlder|loadOlderPage)\s*\("
)
_IO = re.compile(r"\bIntersectionObserver\b")
_DOCS_KEYS = re.compile(
    r"(?:⌘\s*↑|⌘↑|Cmd\s*\+\s*↑|Ctrl\s*\+\s*↑).{0,100}Home"
    r"|Home.{0,100}(?:⌘\s*↑|⌘↑|Cmd\s*\+\s*↑|Ctrl\s*\+\s*↑)",
    re.I | re.S,
)
_DOCS_PREPEND = re.compile(
    r"(?:⌘\s*↑|⌘↑|Home|Load older).{0,220}"
    r"(?:prepend|without jump(?:ing)?|does not jump)"
    r"|(?:prepend|without jump(?:ing)?).{0,220}"
    r"(?:⌘\s*↑|⌘↑|Home|Load older)",
    re.I | re.S,
)
_DOCS_NO_OLDER = re.compile(
    r"(?:no older(?: page)?|without an older page).{0,100}(?:no-op|noop|does nothing)"
    r"|(?:no-op|noop|does nothing).{0,100}(?:no older|older page)",
    re.I | re.S,
)
_DOCS_JK = re.compile(
    r"(?:j\s*/\s*k|j/k).{0,80}(?:unchanged|still|do not change|not changing)"
    r"|(?:unchanged|still).{0,80}(?:j\s*/\s*k|j/k)",
    re.I | re.S,
)
_DOCS_END = re.compile(
    r"\bEnd\b.{0,100}(?:unchanged|still|Latest)"
    r"|(?:unchanged|still|Latest).{0,100}\bEnd\b",
    re.I | re.S,
)


def _read(crate: Path, rel: str) -> str:
    p = crate / "web" / "lib" / rel
    return p.read_text() if p.is_file() else ""


def _fn(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name) or ""


def _near_hook(markup: str, hook: str, n: int = 280) -> str:
    at = markup.find(hook)
    if at < 0:
        return ""
    return markup[max(0, at - n) : at + n]


def assert_keyboard_load_older_fold(crate: Path) -> None:
    """#314 keep-checks + not-autoscroll / D24 / locale."""
    list_path = crate / "web" / "lib" / "TimelineList.svelte"
    pane_path = crate / "web" / "lib" / "TimelinePane.svelte"
    rows_path = crate / "web" / "lib" / "TimelineRows.svelte"
    if not list_path.is_file():
        fail(f"{_ISSUE}: TimelineList.svelte required (keep #113 pin + prepend)")
    if not pane_path.is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (keep #113 / #310 / #311)")
    if not rows_path.is_file():
        fail(f"{_ISSUE}: TimelineRows.svelte required (keep [data-load-older])")
    lst = list_path.read_text()
    pane = pane_path.read_text()
    rows = rows_path.read_text()
    list_c = _without_comments(lst)
    pane_c = _without_comments(pane)
    list_m = _svelte_markup(lst)
    pane_m = _svelte_markup(pane)
    rows_m = _svelte_markup(rows)
    virt = _read(crate, "TimelineVirtual.ts")
    logic = _web_logic(crate)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) load-older-keep-113-224
    if not _SCROLL_TO_BOTTOM.search(logic):
        fail(f"{_ISSUE}: keep #113 open-person pin to latest (scrollTop = scrollHeight)")
    if not _SCROLL_PRESERVE.search(logic):
        fail(f"{_ISSUE}: keep #113 Load older prepend without jumping the viewport")
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
    if not _VIRTUALIZE.search(virt) and not _VIRTUALIZE.search(list_c):
        fail(f"{_ISSUE}: keep #224 VIRTUALIZE_AFTER = 250")
    if not _EST.search(virt) and not _EST.search(list_c):
        fail(f"{_ISSUE}: keep #224 ESTIMATED_ROW_HEIGHT = 88")
    if "spacerTop" not in list_c or "spacerBottom" not in list_c:
        fail(f"{_ISSUE}: keep #224 spacerTop / spacerBottom (measured-height window)")
    if "data-load-older" not in virt:
        fail(
            f"{_ISSUE}: chrome measure still includes [data-load-older] "
            "(measureTimelineChrome)"
        )

    # 2) load-older-keep-310-311
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
    select = _fn(pane_c, "selectPerson") or pane_c
    if not re.search(r"append\s*&&\s*tlLoading", select):
        fail(
            f"{_ISSUE}: keep the in-flight jump tlLoading prepend guard "
            "(do not require canceling day pin or clearing findQ)"
        )

    # 3) load-older-not-autoscroll
    for name in ("onTimelineScroll", "onTimelineWheel"):
        body = _fn(list_c, name)
        if _PREPEND_CALL.search(body):
            fail(
                f"{_ISSUE}: no infinite auto-load on scroll — key and click "
                f"remain explicit (do not prepend from {name})"
            )
    for blob, label in (
        (list_c, "TimelineList"),
        (rows_m + "\n" + _without_comments(rows), "TimelineRows"),
        (pane_c, "TimelinePane"),
    ):
        for m in _IO.finditer(blob):
            window = blob[max(0, m.start() - 240) : m.end() + 240]
            if _PREPEND_CALL.search(window) or _LOAD_HOOK.search(window):
                fail(
                    f"{_ISSUE}: no infinite auto-load on scroll / intersection "
                    f"({label} IntersectionObserver must not prepend)"
                )

    # 4) load-older-locale — do not require t(); keep English if still hardcoded.
    hook = _near_hook(rows_m, "data-load-older")
    if "Load older" in hook or "Load older" in rows_m:
        pass
    else:
        used = _T_CALL.findall(hook)
        if not used:
            fail(
                f"{_ISSUE}: keep visible Load older English "
                "(do not require t(); leave the hardcoded label unless both packs have it)"
            )
        en_p = crate / "web" / "lib" / "locales" / "en.ts"
        tr_p = crate / "web" / "lib" / "locales" / "tr.ts"
        en = _chrome_pack_entries(en_p.read_text()) if en_p.is_file() else {}
        tr = _chrome_pack_entries(tr_p.read_text()) if tr_p.is_file() else {}
        for k in used:
            if k not in en or not str(en[k]).strip() or k not in tr or not str(tr[k]).strip():
                fail(
                    f"{_ISSUE}: Load older key {k!r} must exist in en.ts and tr.ts "
                    "(#131; no third pack) if the label moves to t()"
                )
        loc = crate / "web" / "lib" / "locales"
        extra = [
            p.name
            for p in loc.iterdir()
            if p.is_file() and p.suffix in {".ts", ".json"} and p.stem not in {"en", "tr"}
        ]
        if extra:
            fail(f"{_ISSUE}: no third locale pack ({', '.join(sorted(extra))})")

    # 5) load-older-d24
    if not dtxt.strip():
        fail(
            f"{_ISSUE}: docs/user/app.md required — ⌘↑ / Home at the top of a "
            "long thread prepends without jumping"
        )
    if not _DOCS_KEYS.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must name ⌘↑ / Home "
            "(at the top of a long thread prepends without jumping)"
        )
    if not _DOCS_PREPEND.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say ⌘↑ / Home at the top of a "
            "long thread prepends without jumping"
        )
    if not _DOCS_NO_OLDER.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must say no older page is a no-op")
    if not _DOCS_JK.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must say j/k are unchanged")
    if not _DOCS_END.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must say End is unchanged")
