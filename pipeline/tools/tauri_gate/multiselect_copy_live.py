"""#370 fold — PR #398 review (live leftover paint + Shift-click focus).

Sibling of multiselect_copy.py / multiselect_copy_keys.py (do not grow /
rewrite those files). Parent #370 range / copy / ring / session-set and
#370-keys j||J / shift-mousedown keep-checks stay. This fold locks the
two GitHub review suggestions only.

Must-IDs: 370-live-derived-set, 370-live-no-effect-clear,
370-live-rows-copy, 370-live-capture-start, 370-live-archive-tlgen,
370-live-shift-focus, 370-live-keep-jk-prevent.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.last_read import _article_span, _text, _web_file
from tauri_gate.last_read_fold import _LOADED_CMP, _derived_window
from tauri_gate.multiselect_copy import _CLEAR_SET, _SET_NAME, _on_sel
from tauri_gate.multiselect_copy_keys import (
    _KEY_J_PAIR,
    _KEY_K_PAIR,
    _PREVENT,
    _SHIFT,
    _down_handler,
    _walk_blob,
)
from tauri_gate.reopen_last_lib import _fn_body
from tauri_gate.scan import _match_closer, _svelte_markup, _without_comments
from tauri_gate.status_toasts_toast import _svelte_effect_args

_ISSUE = "#370"
_LIVE_FN = re.compile(r"\bselectionLive\s*\(")
_NEW_SET = re.compile(r"\bnew\s+Set\s*(?:<[^>\n]+>)?\s*\(")
_FOCUS = re.compile(r"\.focus\s*\(")
_SELECT_NONE = re.compile(r"select-none|user-select\s*:\s*none")
_TABINDEX0 = re.compile(r"""tabindex\s*=\s*["']0["']""")
_CAPTURE_LOCAL = re.compile(
    r"(?:const|let)\s+([A-Za-z_][\w]*)\s*=\s*archive_id\b"
)
_LOADED_WRITE = re.compile(r"\b(?:loadedArchiveId|loaded_archive_id)\s*=")
_TLGEN_BUMP = re.compile(r"\+\+tlGen|\btlGen\s*(?:\+\+|\+=)")
_SKIP_CAPTURE = frozenset({"loadedArchiveId", "loaded_archive_id"})


def _derived_bindings(src: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for m in re.finditer(
        r"(?:const|let)\s+([A-Za-z_][\w]*)\s*=\s*\$derived(?:\.by)?",
        src,
    ):
        d = src.find("$derived", m.start())
        paren = src.find("(", d)
        if paren < 0:
            continue
        close = _match_closer(src, paren)
        body = src[d : close + 1] if close >= 0 else src[d : d + 400]
        out.append((m.group(1), body))
    return out


def _is_live_gate(blob: str) -> bool:
    return bool(_LIVE_FN.search(blob) or _LOADED_CMP.search(blob))


def _derived_live_names(src: str) -> list[str]:
    names: list[str] = []
    for name, body in _derived_bindings(src):
        if _is_live_gate(body) and (_SET_NAME.search(body) or _NEW_SET.search(body)):
            names.append(name)
    return names


def _live_helpers(src: str) -> list[str]:
    names: list[str] = []
    for m in re.finditer(r"(?:export\s+)?function\s+([A-Za-z_][\w]*)\s*\(", src):
        name = m.group(1)
        if name == "selectionLive":
            continue
        body = _fn_body(src, name)
        if _is_live_gate(body) and _NEW_SET.search(body):
            names.append(name)
    return names


def _leftover_effect_clears(src: str) -> bool:
    for arg in _svelte_effect_args(src):
        if not _SET_NAME.search(arg):
            continue
        if not re.search(r"=\s*new\s+Set", arg):
            continue
        if _is_live_gate(arg):
            return True
    return False


def _component_call(src: str, name: str) -> str:
    m = re.search(rf"<{re.escape(name)}\b", src)
    if not m:
        return ""
    end = src.find("/>", m.start())
    close = src.find(f"</{name}>", m.start())
    if end >= 0 and (close < 0 or end < close):
        return src[m.start() : end + 2]
    if close >= 0:
        return src[m.start() : close + len(name) + 3]
    return src[m.start() : m.start() + 900]


def _uses_live(blob: str, names: list[str]) -> bool:
    if _is_live_gate(blob):
        return True
    return any(re.search(rf"\b{re.escape(n)}\b", blob) for n in names)


def _rows_paint_live(rows_call: str, rows: str, art: str, names: list[str]) -> bool:
    if _uses_live(rows_call, names) and not re.search(
        r"\{selectedIds\}", rows_call
    ):
        return True
    if any(
        re.search(rf"selectedIds\s*=\s*\{{\s*{re.escape(n)}", rows_call)
        for n in names
    ):
        return True
    row_live = _derived_live_names(rows)
    if row_live and any(re.search(rf"\b{re.escape(n)}\.has\b", art) for n in row_live):
        return True
    if _is_live_gate(art):
        return True
    return False


def _before_await(body: str) -> str:
    m = re.search(r"\bawait\b", body)
    return body[: m.start()] if m else body[:1200]


def _captured_ids(body: str) -> list[str]:
    prefix = _before_await(body)
    names = [
        n for n in _CAPTURE_LOCAL.findall(prefix) if n not in _SKIP_CAPTURE
    ]
    return names


def _window_gated(win: str, names: list[str]) -> bool:
    for n in names:
        if re.search(
            rf"\b{re.escape(n)}\s*!==?\s*archive_id"
            rf"|archive_id\s*!==?\s*{re.escape(n)}"
            rf"|\b{re.escape(n)}\s*===?\s*archive_id"
            rf"|archive_id\s*===?\s*{re.escape(n)}",
            win,
        ):
            return True
    return False


def _writes_gated(body: str, names: list[str]) -> bool:
    writes = list(_LOADED_WRITE.finditer(body))
    if not writes or not names:
        return False
    return all(
        _window_gated(body[max(0, m.start() - 500) : m.end() + 80], names)
        for m in writes
    )


def _archive_bumps_or_clears(src: str) -> bool:
    for arg in _svelte_effect_args(src):
        if not re.search(r"\barchive_id\b", arg):
            continue
        if _LIVE_FN.search(arg):
            continue
        if _TLGEN_BUMP.search(arg):
            return True
        if _CLEAR_SET.search(arg) or re.search(r"selectedIds\s*=\s*new\s+Set", arg):
            return True
    return False


def assert_multiselect_copy_live(crate: Path) -> None:
    """#370: derived live set for leftover paint; Shift-click focuses article."""
    keys_path = _web_file(crate, "PeopleKeys.ts")
    rows_path = _web_file(crate, "TimelineRows.svelte")
    list_path = _web_file(crate, "TimelineList.svelte")
    pane_path = _web_file(crate, "TimelinePane.svelte")
    sel_path = _web_file(crate, "TimelineSelect.ts")
    if not keys_path.is_file():
        fail(f"{_ISSUE}: PeopleKeys.ts required (Shift+j/k walk)")
    if not rows_path.is_file():
        fail(f"{_ISSUE}: TimelineRows.svelte required (article Shift-click)")
    if not list_path.is_file():
        fail(f"{_ISSUE}: TimelineList.svelte required (copy / menu size)")
    if not pane_path.is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (selectedIds + leftover)")
    if not sel_path.is_file():
        fail(f"{_ISSUE}: TimelineSelect.ts required (selectionLive)")

    keys_raw, rows_raw, list_raw, pane_raw, sel_raw = (
        keys_path.read_text(),
        rows_path.read_text(),
        list_path.read_text(),
        pane_path.read_text(),
        sel_path.read_text(),
    )
    keys, rows, lst, pane, helper = (
        _without_comments(keys_raw),
        _without_comments(rows_raw),
        _without_comments(list_raw),
        _without_comments(pane_raw),
        _without_comments(sel_raw),
    )
    rows_m, list_m = _svelte_markup(rows_raw), _svelte_markup(list_raw)
    app = _without_comments(_text(crate / "web" / "App.svelte"))
    handle = _fn_body(keys, "handleAppKey") or keys
    walk = _walk_blob(handle)
    art = _article_span(rows_m) or _article_span(rows)
    down = _down_handler(art, rows)
    on_sel = _on_sel(list_raw, lst, pane)
    sel_copy = _fn_body(lst, "copySelected") or _fn_body(pane, "copySelected")
    sel_person = _fn_body(pane, "selectPerson") or _fn_body(pane_raw, "selectPerson")
    open_at = (
        _fn_body(pane, "openPersonAtMessage")
        or _fn_body(pane_raw, "openPersonAtMessage")
    )
    paint = _derived_window(pane, "lastReadMessageId")
    rows_call = _component_call(list_m + "\n" + lst, "TimelineRows")
    menu_call = _component_call(list_m + "\n" + lst, "TimelineCopyMenu")
    live_names = (
        _derived_live_names(pane + "\n" + lst + "\n" + rows + "\n" + helper)
        + _live_helpers(helper + "\n" + pane + "\n" + lst)
    )
    leftover_fx = _leftover_effect_clears(pane + "\n" + lst)

    # --- keep (pass today): j||J / k||K, shift preventDefault, #369 leftover ---
    if not _KEY_J_PAIR.search(walk) or not _KEY_K_PAIR.search(walk):
        fail(
            f"{_ISSUE}: keep Shift+j/k matching e.key === \"j\" || e.key === \"J\" "
            "(and k/K) on the walk"
        )
    if not art:
        fail(f"{_ISSUE}: keep bubble <article> (Shift-click ring)")
    if not down or not _SHIFT.search(down) or not _PREVENT.search(down):
        fail(
            f"{_ISSUE}: keep article onmousedown (or onpointerdown) "
            "preventDefault when e.shiftKey — do not blanket select-none"
        )
    if _SELECT_NONE.search(art):
        fail(
            f"{_ISSUE}: do not add blanket select-none on the bubble article "
            "(plain click/drag text can stay)"
        )
    if not _TABINDEX0.search(art):
        fail(f"{_ISSUE}: keep article tabindex=\"0\" (Shift-click .focus())")
    if not _LIVE_FN.search(helper) and not _LIVE_FN.search(pane):
        fail(
            f"{_ISSUE}: keep selectionLive(loadedArchiveId, archive_id) "
            "(leftover File → Open)"
        )
    if not _LOADED_CMP.search(paint):
        fail(
            f"{_ISSUE}: keep #369 leftover last-read derived "
            "(loadedArchiveId !== archive_id → no Last time on leftover rows)"
        )
    if not _SET_NAME.search(pane + "\n" + lst):
        fail(f"{_ISSUE}: keep the session selectedIds set")

    # --- suggestion: live derived set (not leftover $effect after paint) ---
    if leftover_fx or not live_names:
        fail(
            f"{_ISSUE}: rings / copy-count must use a derived live set that is "
            "empty unless selectionLive(loadedArchiveId, archive_id) "
            "(or loadedArchiveId === archive_id) — do not $effect-assign "
            "selectedIds = new Set() after paint (leftover File → Open flash)"
        )
    if not _rows_paint_live(rows_call, rows, art, live_names):
        fail(
            f"{_ISSUE}: pass the derived live set into TimelineRows, not the "
            "raw selectedIds that can still hold Ada's leftover ids"
        )
    copy_blob = sel_copy + "\n" + menu_call
    if not _uses_live(copy_blob, live_names):
        fail(
            f"{_ISSUE}: copySelected and Copy N menu size must use the same "
            "derived live set (leftover File → Open must not Copy N of Ada "
            "onto Berk)"
        )

    # --- suggestion: capture archive_id at load start; bump tlGen ---
    cap_sel, cap_open = _captured_ids(sel_person), _captured_ids(open_at)
    if not cap_sel or not cap_open:
        fail(
            f"{_ISSUE}: capture archive_id at selectPerson / openPersonAtMessage "
            "start; only write loadedArchiveId = archive_id when that capture "
            "still equals live archive_id"
        )
    if not _writes_gated(sel_person, cap_sel) or not _writes_gated(open_at, cap_open):
        fail(
            f"{_ISSUE}: write loadedArchiveId = archive_id only when the "
            "start-of-load capture still equals live archive_id "
            "(in-flight load must not stamp Berk's id onto Ada's leftover rows)"
        )
    if not (
        _archive_bumps_or_clears(pane)
        or _archive_bumps_or_clears(app)
        or _archive_bumps_or_clears(lst)
    ):
        fail(
            f"{_ISSUE}: when live archive_id changes, bump tlGen (or clear the "
            "set) so a stale load cannot keep Ada's ids — not a leftover "
            "$effect after paint"
        )

    # --- suggestion: Shift-click preventDefault AND focus the article ---
    focus_blob = down + "\n" + on_sel + "\n" + art
    if not _FOCUS.search(focus_blob):
        fail(
            f"{_ISSUE}: article onmousedown (or onpointerdown) must "
            "preventDefault when e.shiftKey and .focus() the article "
            "(currentTarget or onSelectIndex) so Shift-click from #q walks "
            "the timeline"
        )
