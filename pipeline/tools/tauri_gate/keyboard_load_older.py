"""#314 — keyboard Load older (⌘↑ / Ctrl+↑ and Home).

PeopleKeys binds the same prepend as the mouse button: selectPerson(id, true)
/ onPrepend → shiftHeightsForPrepend + preserveScrollAfterPrepend. Fire only
when tlIndex is the oldest mounted data-tl-index or the target is
[data-load-older]. Same End-style focus. ⌘↑ is not k. End stays Latest.

Must-IDs: load-older-key, load-older-no-jump, load-older-no-older,
load-older-keep-jk, load-older-keep-end. Keep / autoscroll / D24 / locale
live in keyboard_load_older_fold.py.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.import_boot_guards import _input_guard_span
from tauri_gate.jump_day_heading import _PREPEND_KEEP, _PREPEND_SHIFT
from tauri_gate.scan import (
    _function_body,
    _match_closer,
    _open_tag_before,
    _svelte_markup,
    _ts_fn_body,
    _without_comments,
)

_ISSUE = "#314"
_PREPEND_NAMES = ("loadOlder", "onPrepend", "prependOlder", "loadOlderPage")
_HOME = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']Home[\"']"
    r"|[\"']Home[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?code\s*===?\s*[\"']Home[\"']"
)
_ARROW_UP = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']ArrowUp[\"']"
    r"|[\"']ArrowUp[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?code\s*===?\s*[\"']ArrowUp[\"']"
)
_ARROW_DOWN = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']ArrowDown[\"']"
    r"|[\"']ArrowDown[\"']\s*===?\s*(?:e\.)?key"
)
_END = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']End[\"']|[\"']End[\"']\s*===?\s*(?:e\.)?key"
)
_KEY_J = re.compile(r"(?:e\.)?key\s*===?\s*[\"']j[\"']|[\"']j[\"']\s*===?\s*(?:e\.)?key")
_KEY_K = re.compile(r"(?:e\.)?key\s*===?\s*[\"']k[\"']|[\"']k[\"']\s*===?\s*(?:e\.)?key")
_MOD = re.compile(r"\b(?:(?:e\.)?metaKey|(?:e\.)?ctrlKey|\bmod\b)")
_NO_ALT = re.compile(r"\bmod\b|!\s*(?:e\.)?altKey")
_PREPEND_CALL = re.compile(
    r"\bselectPerson\s*\(\s*[^,)]+\s*,\s*(?:true|append)\s*[,)]"
    r"|\b(?:loadOlder|onPrepend|prependOlder|loadOlderPage)\s*\("
    r"|\.loadOlder\b"
    r"|pane\(\)\s*\??\s*\.\s*selectPerson\s*\(\s*[^,)]+\s*,\s*true\b"
)
_ONE_ARG_SELECT = re.compile(r"\bselectPerson\s*\(\s*[^,)]+\s*\)")
_SCROLL_ZERO = re.compile(r"scrollTop\s*=\s*0\b")
_PIN = re.compile(r"\b(?:scrollToLatest|pinTimelineLatest)\b")
_MOUNTED = re.compile(r"data-tl-index")
_LOAD_CTRL = re.compile(r"data-load-older")
_VISIBLE0 = re.compile(r"visibleTlIndices\s*\[\s*0\s*\]")
_HAS_MORE = re.compile(r"\bhas_more\b")
_TL_LOADING = re.compile(r"append\s*&&\s*tlLoading|\btlLoading\b[\s\S]{0,80}\breturn\b")
_NO_BEFORE = re.compile(r"append\s*&&\s*!before|!\s*before\b")
_WALK = re.compile(r"\b(?:setTlIndex|ensureTlIndexVisible|visibleTlIndices)\b")
_EXCLUDE_MOD = re.compile(r"!\s*(?:e\.)?(?:metaKey|ctrlKey|mod)\b")
_FIELD = re.compile(
    r"tagName\s*===?\s*[\"']INPUT[\"']"
    r"|#tl-find|id\s*===?\s*[\"']tl-find[\"']|id\s*===?\s*[\"']q[\"']"
    r"|data-tl-find"
)
_TAB_NEG = re.compile(r"""\btabindex\s*=\s*(?:["']-1["']|\{-1\})""")


def _fn(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name) or ""


def _prop_fn(src: str, name: str) -> str:
    m = re.search(
        rf"\b{re.escape(name)}\s*:\s*(?:async\s*)?(?:function\s*)?\([^)]*\)\s*=>\s*\{{",
        src,
    )
    if m:
        brace = src.find("{", m.end() - 1)
        if brace >= 0:
            close = _match_closer(src, brace)
            if close >= 0:
                return src[brace + 1 : close]
            return src[brace + 1 :]
    m = re.search(
        rf"\b{re.escape(name)}\s*:\s*(?:async\s*)?\([^)]*\)\s*=>\s*([^,;]+)",
        src,
    )
    return (m.group(1) or "").strip() if m else ""


def _wire(src: str) -> str:
    return "\n".join(_prop_fn(src, n) or _fn(src, n) for n in _PREPEND_NAMES)


def _near(src: str, m: re.Match[str], before: int = 200, after: int = 420) -> str:
    return src[max(0, m.start() - before) : m.end() + after]


def _blob(src: str, m: re.Match[str], before: int = 200, after: int = 420) -> str:
    return _near(src, m, before, after) + "\n" + _wire(src)


def _is_prepend(blob: str) -> bool:
    return bool(_PREPEND_CALL.search(blob))


def _is_mod_up(src: str, m: re.Match[str]) -> bool:
    window = _near(src, m, 160, 160)
    if not _MOD.search(window):
        return False
    return bool(_NO_ALT.search(window) or re.search(r"\bctrlKey\b", window))


def _prepend_hits(src: str, rx: re.Pattern[str], *, mod_up: bool = False) -> list[re.Match[str]]:
    hits = []
    for m in rx.finditer(src):
        if mod_up and not _is_mod_up(src, m):
            continue
        if _is_prepend(_blob(src, m)):
            hits.append(m)
    return hits


def _people_gated(src: str, pos: int) -> bool:
    head = src[:pos]
    if re.search(r"view\s*!==?\s*[\"']people[\"']", head):
        return True
    return bool(re.search(r"view\s*===?\s*[\"']people[\"']", src[max(0, pos - 400) : pos + 80]))


def _skips_fields(src: str, pos: int) -> bool:
    guard = _input_guard_span(src)
    if guard and guard[0] < pos and guard[1] <= pos:
        return True
    return bool(_FIELD.search(src[max(0, pos - 420) : pos + 200]))


def _walk_excludes_mod(keys: str) -> bool:
    for m in _ARROW_UP.finditer(keys):
        w = _near(keys, m, 180, 240)
        if _WALK.search(w) and not _is_prepend(w) and not _EXCLUDE_MOD.search(w):
            return False
    return True


def _mod_up_before_walk(keys: str) -> bool:
    first_pre = None
    first_walk = None
    for m in _ARROW_UP.finditer(keys):
        w = _near(keys, m, 180, 240)
        if _is_prepend(w) and _MOD.search(w):
            if first_pre is None:
                first_pre = m.start()
        elif _WALK.search(w) and first_walk is None:
            first_walk = m.start()
    return first_pre is not None and (first_walk is None or first_pre < first_walk)


def _letter_ok(src: str, rx: re.Pattern[str]) -> bool:
    m = rx.search(src)
    if not m:
        return False
    w = _near(src, m, 80, 220)
    return bool(_WALK.search(w) or _WALK.search(src)) and not _is_prepend(w)


def assert_keyboard_load_older(crate: Path) -> None:
    """#314: ⌘↑ / Home prepend at the oldest mounted row / Load older control."""
    keys_path = crate / "web" / "lib" / "PeopleKeys.ts"
    app_path = crate / "web" / "App.svelte"
    pane_path = crate / "web" / "lib" / "TimelinePane.svelte"
    list_path = crate / "web" / "lib" / "TimelineList.svelte"
    rows_path = crate / "web" / "lib" / "TimelineRows.svelte"
    if not keys_path.is_file():
        fail(f"{_ISSUE}: PeopleKeys.ts required (⌘↑ / Home Load older)")
    if not app_path.is_file():
        fail(f"{_ISSUE}: App.svelte required (wire selectPerson(..., true) / loadOlder)")
    if not pane_path.is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (selectPerson append / oldestCursor)")
    if not list_path.is_file():
        fail(f"{_ISSUE}: TimelineList.svelte required (preserveScrollAfterPrepend)")
    if not rows_path.is_file():
        fail(f"{_ISSUE}: TimelineRows.svelte required ([data-load-older])")

    keys_c = _without_comments(keys_path.read_text())
    app_c = _without_comments(app_path.read_text())
    pane_c = _without_comments(pane_path.read_text())
    list_c = _without_comments(list_path.read_text())
    rows = rows_path.read_text()
    rows_m = _svelte_markup(rows)
    src = keys_c + "\n" + app_c
    handle = _fn(keys_c, "handleAppKey") or keys_c
    select = _fn(pane_c, "selectPerson") or pane_c

    # 1) load-older-key — fail-today: no key prepends.
    home_hits = _prepend_hits(src, _HOME)
    meta_hits = _prepend_hits(src, _ARROW_UP, mod_up=True)
    if not home_hits or not meta_hits:
        fail(
            f"{_ISSUE}: ⌘↑ / Ctrl+↑ and Home must prepend older pages "
            "(selectPerson(..., true) / onPrepend) when the highlight is the "
            "oldest mounted data-tl-index or the Load older control"
        )
    if not _prepend_hits(keys_c, _HOME) and not _prepend_hits(app_c, _HOME):
        fail(
            f"{_ISSUE}: Home Load older must live on the PeopleKeys / App "
            "window handler (same as End — not a scroller-only listener)"
        )
    if not _prepend_hits(keys_c, _ARROW_UP, mod_up=True) and not _prepend_hits(
        app_c, _ARROW_UP, mod_up=True
    ):
        fail(
            f"{_ISSUE}: ⌘↑ / Ctrl+↑ Load older must live on the PeopleKeys / "
            "App window handler (metaKey or ctrlKey without alt + ArrowUp)"
        )

    key_blob = "\n".join(_blob(src, m) for m in home_hits + meta_hits)

    # 2) oldest mounted or [data-load-older]; mid-thread does not prepend.
    if not _MOUNTED.search(key_blob):
        fail(
            f"{_ISSUE}: fire ⌘↑ / Home only when tlIndex is the oldest "
            "mounted data-tl-index (first live [data-tl-index], not "
            "visibleTlIndices[0]) or the event target is [data-load-older] "
            "— mid-thread must not prepend"
        )
    if not _LOAD_CTRL.search(key_blob):
        fail(
            f"{_ISSUE}: ⌘↑ / Home must also fire when the event target is "
            "[data-load-older] (oldest mounted row or the Load older control)"
        )
    if _VISIBLE0.search(key_blob) and not _MOUNTED.search(key_blob):
        fail(
            f"{_ISSUE}: oldest mounted is the first live data-tl-index, not "
            "visibleTlIndices[0] (virtualizer may unmount the top)"
        )

    # 3) End-style focus: people view, selectedId, not a field, !inPeopleList.
    for m in home_hits + meta_hits:
        if not _people_gated(src, m.start()):
            fail(
                f"{_ISSUE}: ⌘↑ / Home use the same End-style focus "
                "(people view, selectedId, not a field, not the people listbox)"
            )
        if not re.search(r"\bselectedId\b", _near(src, m, 360, 200)):
            fail(
                f"{_ISSUE}: ⌘↑ / Home use the same End-style focus "
                "(people view, selectedId, not a field, not the people listbox)"
            )
        if not re.search(r"\binPeopleList\b", _near(src, m, 360, 240) + handle):
            fail(
                f"{_ISSUE}: ⌘↑ / Home use the same End-style focus "
                "(people view, selectedId, not a field, not the people listbox)"
            )
        if not _skips_fields(src, m.start()):
            fail(
                f"{_ISSUE}: do not fire ⌘↑ / Home while #tl-find, #q, or "
                "another field is the target"
            )
        if not re.search(r"preventDefault\s*\(", _near(src, m, 80, 360)):
            fail(f"{_ISSUE}: ⌘↑ / Home must preventDefault")

    # 4) load-older-no-jump — existing prepend, not scrollTop = 0 / replace.
    if not _PREPEND_SHIFT.search(list_c) or not _PREPEND_KEEP.search(list_c):
        fail(
            f"{_ISSUE}: the key path must use the existing prepend "
            "(shiftHeightsForPrepend + preserveScrollAfterPrepend) — not "
            "scrollTop = 0 and not a replace selectPerson(id)"
        )
    if _SCROLL_ZERO.search(key_blob) or _SCROLL_ZERO.search(handle):
        fail(
            f"{_ISSUE}: keyboard Load older must not jump "
            "(not scrollTop = 0; keep preserveScrollAfterPrepend)"
        )
    if _ONE_ARG_SELECT.search(key_blob) and not re.search(
        r"\bselectPerson\s*\(\s*[^,)]+\s*,\s*(?:true|append)\s*[,)]",
        key_blob,
    ):
        fail(
            f"{_ISSUE}: keyboard Load older is selectPerson(..., true) / "
            "onPrepend — not a replace selectPerson(id)"
        )

    # 5) load-older-no-older — tlLoading or no before; do not invent has_more.
    if not _TL_LOADING.search(select):
        fail(
            f"{_ISSUE}: key no-op when tlLoading "
            "(keep the selectPerson append guard)"
        )
    if not _NO_BEFORE.search(select):
        fail(
            f"{_ISSUE}: no older page → keyboard no-op "
            "(tlLoading or no before / oldestCursor; do not invent has_more)"
        )
    if _HAS_MORE.search(key_blob) or _HAS_MORE.search(handle) or _HAS_MORE.search(rows_m):
        fail(f"{_ISSUE}: do not invent has_more (no older page is !before / tlLoading)")

    # 6) load-older-keep-jk — unchorded j/k / arrows still only walk.
    if not _letter_ok(keys_c, _KEY_J) or not _letter_ok(keys_c, _KEY_K):
        fail(
            f"{_ISSUE}: keep j/k — they still only walk visibleTlIndices "
            "and must not prepend"
        )
    if not re.search(r"\bvisibleTlIndices\b", keys_c):
        fail(f"{_ISSUE}: keep j/k walking visibleTlIndices")
    for m in _ARROW_DOWN.finditer(keys_c):
        w = _near(keys_c, m, 120, 220)
        if _WALK.search(w) and _is_prepend(w):
            fail(
                f"{_ISSUE}: unchorded ArrowDown still only walks "
                "visibleTlIndices — it must not prepend"
            )
    if not _walk_excludes_mod(keys_c) and not _mod_up_before_walk(keys_c):
        fail(
            f"{_ISSUE}: ⌘↑ must not remain highlight-up — handle meta/ctrl "
            "ArrowUp as Load older before the k walk, or exclude meta/ctrl "
            "from unchorded ArrowUp"
        )
    for m in _ARROW_UP.finditer(keys_c):
        w = _near(keys_c, m, 160, 220)
        if _WALK.search(w) and not _MOD.search(w) and _is_prepend(w):
            fail(
                f"{_ISSUE}: unchorded ArrowUp still only walks "
                "visibleTlIndices — it must not prepend"
            )

    # 7) load-older-keep-end — End still Latest; Home is not a Latest pin.
    end_m = _END.search(keys_c)
    if not end_m:
        fail(f"{_ISSUE}: keep End → Latest (scrollToLatest) — Load older is not End")
    end_blob = _blob(keys_c, end_m)
    if not _PIN.search(end_blob):
        fail(f"{_ISSUE}: End still pins Latest (scrollToLatest) — do not steal End")
    if _is_prepend(end_blob):
        fail(f"{_ISSUE}: the Load older key is not End")
    for m in _HOME.finditer(src):
        if _PIN.search(_blob(src, m)):
            fail(f"{_ISSUE}: Home must not become a Latest pin (#313) — Home prepends")

    # 8) keep [data-load-older] a native tabbable button.
    hook = rows_m.find("data-load-older")
    if hook < 0:
        fail(f"{_ISSUE}: keep [data-load-older] (native tabbable button)")
    found = _open_tag_before(rows_m, hook)
    tag = found[1] if found else ""
    if _TAB_NEG.search(tag):
        fail(
            f"{_ISSUE}: keep [data-load-older] a native tabbable button "
            "(do not set tabindex=\"-1\")"
        )
    if not re.search(r"<(?:Button|button)\b", tag):
        fail(f"{_ISSUE}: keep [data-load-older] a native button")
    if re.search(r"/Users/|/home/", keys_c + "\n" + key_blob):
        fail(f"{_ISSUE}: tests stay placeholders (Ada) — no real home paths")
