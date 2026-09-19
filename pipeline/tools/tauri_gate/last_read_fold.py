"""#369 fold — PR #396 review (flex-col stretch, File → Open leftover, filter-miss).

Sibling of last_read.py (do not grow that file). Outer data-tl-index stays a
row flex (`flex min-w-0 pb-2`), not flex-col. Marker + article sit in an
inner `flex w-fit max-w-[94%] flex-col` (`ml-auto` when from_me).
t("lastTime") stays a sibling of <article> on that wrapper. Keep #111 / #206
hugging bubbles. Paint/write last-read only when captured loadedArchiveId
equals live archive_id (set on successful selectPerson / openPersonAtMessage).
jumpToMessageId: loaded timeline has the id and filteredTimeline does not →
quiet false, no prepend. Still prepend when the id is older than the window.
Do not auto-clear chips. Do not start Issue 4 (Find snap / dayPin).

Must-IDs: last-read-fold-flex-col, last-read-fold-leftover,
last-read-fold-filter-miss, last-read-fold-keep-111-206-369.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.jump_day_heading import _LOOP
from tauri_gate.last_read import (
    _CLEAR_CHIPS,
    _FILTERED,
    _JUMP_MSG,
    _LAST_TIME_T,
    _MESSAGE_ID,
    _article_span,
    _jump_blob,
    _web_file,
)
from tauri_gate.reopen_last_lib import _fn_body
from tauri_gate.scan import _expand_fn_calls, _svelte_markup, _without_comments

_ISSUE = "#369"
_FLEX_COL = re.compile(r"(?<![\w-])flex-col(?![\w-])")
_FLEX_ROW = re.compile(r"(?<![\w-])flex(?![\w-])")
_MIN_W0 = re.compile(r"(?<![\w-])min-w-0(?![\w-])")
_PB2 = re.compile(r"(?<![\w-])pb-2(?![\w-])")
_W_FIT = re.compile(r"(?<![\w-])w-fit(?![\w-])")
_MAX94 = "max-w-[94%]"
_ML_AUTO_ME = re.compile(r"class:ml-auto\s*=\s*\{[^}]*from_me")
_BUBBLE_ME = re.compile(r"class:bubble-me\s*=\s*\{[^}]*from_me")
_TL_OPEN = re.compile(r"<div\b[^>]*\bdata-tl-index\b[^>]*>", re.I)
_LOADED = re.compile(r"\b(?:loadedArchiveId|loaded_archive_id)\b")
_LOADED_STATE = re.compile(
    r"\b(?:loadedArchiveId|loaded_archive_id)\s*=\s*\$state\b"
)
_LOADED_DERIVED = re.compile(
    r"\b(?:loadedArchiveId|loaded_archive_id)\s*=\s*\$derived\b"
)
_CAPTURE_ASSIGN = re.compile(
    r"\b(?:loadedArchiveId|loaded_archive_id)\s*=\s*"
    r"(?:archive_id|st\.archive_id)"
)
_LOADED_CMP = re.compile(
    r"(?:loadedArchiveId|loaded_archive_id)\s*!==?\s*archive_id"
    r"|archive_id\s*!==?\s*(?:loadedArchiveId|loaded_archive_id)"
    r"|(?:loadedArchiveId|loaded_archive_id)\s*===?\s*archive_id"
    r"|archive_id\s*===?\s*(?:loadedArchiveId|loaded_archive_id)"
)
_PREPEND = re.compile(r"selectPerson\s*\([^)]*true|\bonPrepend\b")
_UNFILTERED_TL = re.compile(
    r"(?:ctx\.)?timeline\s*\(\s*\)"
    r"|\btimeline\s*:\s*\(\s*\)"
    r"|\bunfilteredTimeline\b"
    r"|\bloadedTimeline\b"
    r"|\btimeline\s*\.(?:some|find|findIndex)\b"
)
_CALL_TL = re.compile(
    r"\btimeline\s*:\s*\(\s*\)\s*=>\s*timeline\b"
)
_WRITE_LAST = re.compile(
    r"\b(?:writeLastReadPref|writeLastRead|writePersonLastRead|"
    r"persistLastRead|setLastRead|rememberLastRead|saveLastRead)\b"
)


def _tl_open_tag(src: str) -> str:
    m = _TL_OPEN.search(src)
    return m.group(0) if m else ""


def _between_tl_and_article(src: str) -> str:
    m = _TL_OPEN.search(src)
    if not m:
        return ""
    art = src.find("<article", m.end())
    return src[m.end() : art] if art >= 0 else src[m.end() : m.end() + 800]


def _tl_window(src: str, n: int = 1800) -> str:
    m = re.search(r"\bdata-tl-index\b", src)
    return src[m.start() : m.start() + n] if m else src


def _derived_window(src: str, name: str, n: int = 700) -> str:
    m = re.search(rf"(?:const|let)\s+{re.escape(name)}\s*=\s*\$derived", src)
    if not m:
        m = re.search(rf"(?:const|let)\s+{re.escape(name)}\s*=", src)
    return src[m.start() : m.start() + n] if m else ""


def _capture_on_success(body: str) -> bool:
    if not _CAPTURE_ASSIGN.search(body):
        return False
    tl = [m.start() for m in re.finditer(r"\btimeline\s*=", body)]
    if not tl:
        return True
    return any(a.start() >= min(tl) for a in _CAPTURE_ASSIGN.finditer(body))


def _prefix_before_prepend(jmp: str) -> str:
    m = _PREPEND.search(jmp)
    return jmp[: m.start()] if m else jmp


def assert_last_read_fold(crate: Path) -> None:
    """#369 fold: no flex-col stretch; leftover archive gate; filter-miss quiet."""
    rows_path = _web_file(crate, "TimelineRows.svelte")
    pane_path = _web_file(crate, "TimelinePane.svelte")
    if not rows_path.is_file():
        fail(f"{_ISSUE}: TimelineRows.svelte required (data-tl-index row flex)")
    if not pane_path.is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (loadedArchiveId + jump)")

    rows_raw, pane_raw = rows_path.read_text(), pane_path.read_text()
    rows, pane = _without_comments(rows_raw), _without_comments(pane_raw)
    rows_m, pane_m = _svelte_markup(rows_raw), _svelte_markup(pane_raw)
    jump = _jump_blob(crate, pane)
    jmp = _fn_body(jump, "jumpToMessageId") or _fn_body(pane, "jumpToMessageId")
    sel = _fn_body(pane, "selectPerson") or _fn_body(pane_raw, "selectPerson")
    open_at = (
        _fn_body(pane, "openPersonAtMessage")
        or _fn_body(pane_raw, "openPersonAtMessage")
    )
    persist = (
        _fn_body(pane, "persistLastRead")
        or _fn_body(pane_raw, "persistLastRead")
    )
    paint = _derived_window(pane, "lastReadMessageId")
    row_src = rows_m if _LAST_TIME_T.search(rows_m) else rows
    wrap = _tl_window(row_src)
    open_tag = _tl_open_tag(row_src)
    inner = _between_tl_and_article(row_src)

    # Keep #369 Last time + #111 / #206 hugging (pass today).
    if not _LAST_TIME_T.search(row_src):
        fail(f"{_ISSUE}: keep quiet t(\"lastTime\") on the data-tl-index wrapper")
    if "data-tl-index" not in row_src:
        fail(f"{_ISSUE}: keep data-tl-index on the bubble wrapper (#310 / #206)")
    mark_at = _LAST_TIME_T.search(row_src)
    article = _article_span(row_src)
    if mark_at and article and article.find(mark_at.group(0)) >= 0:
        fail(
            f"{_ISSUE}: t(\"lastTime\") stays a sibling of <article> "
            "(not inside the bubble; grouped followers still mark)"
        )
    if _MAX94 not in wrap:
        fail(
            f"{_ISSUE}: keep #111 / #206 hugging bubbles "
            "(max-w-[94%] on the inner stack or article)"
        )
    if not _ML_AUTO_ME.search(wrap) or not _BUBBLE_ME.search(wrap):
        fail(
            f"{_ISSUE}: keep #111 / #206 hugging bubbles "
            "(ml-auto / bubble-me when from_me)"
        )
    if not _JUMP_MSG.search(jump + "\n" + pane):
        fail(f"{_ISSUE}: keep jumpToMessageId (sibling of jumpToLocalDay)")
    if not _PREPEND.search(jmp) or not _LOOP.search(jmp):
        fail(
            f"{_ISSUE}: keep Load older prepend when the stored id is older "
            "than the loaded timeline window"
        )
    if _CLEAR_CHIPS.search(jmp):
        fail(f"{_ISSUE}: filtered-out last-read does not auto-clear chips")

    # 1) flex-col stretch — outer data-tl-index is a row flex, not a column.
    if not open_tag:
        fail(f"{_ISSUE}: data-tl-index wrapper required (row flex, not flex-col)")
    if _FLEX_COL.search(open_tag):
        fail(
            f"{_ISSUE}: data-tl-index wrapper must not be flex-col "
            "(row flex like flex min-w-0 pb-2; marker + article sit in an inner "
            "flex-col w-fit max-w-[94%])"
        )
    if not (
        _FLEX_ROW.search(open_tag) and _MIN_W0.search(open_tag) and _PB2.search(open_tag)
    ):
        fail(
            f"{_ISSUE}: data-tl-index wrapper stays a row flex "
            "(flex min-w-0 pb-2), not flex-col"
        )
    if not (
        _W_FIT.search(inner) and _MAX94 in inner and _FLEX_COL.search(inner)
    ):
        fail(
            f"{_ISSUE}: marker + article sit in an inner "
            "flex w-fit max-w-[94%] flex-col (Ada short ok hugs; not a 94% bar)"
        )
    if not _ML_AUTO_ME.search(inner):
        fail(
            f"{_ISSUE}: inner stack gets ml-auto when from_me "
            "(Berk me-right stack, not only the article)"
        )
    if mark_at and inner.find(mark_at.group(0)) < 0:
        fail(
            f"{_ISSUE}: t(\"lastTime\") stays a sibling of <article> "
            "inside the data-tl-index wrapper (inner stack)"
        )

    # 2) File → Open leftover — paint/write only when loadedArchiveId === archive_id.
    pane_blob = pane + "\n" + pane_raw
    if not _LOADED.search(pane_blob):
        fail(
            f"{_ISSUE}: capture loadedArchiveId on a successful person timeline "
            "load (File → Open leftover Ada rows must not take Berk's Last time)"
        )
    if _LOADED_DERIVED.search(pane_blob):
        fail(
            f"{_ISSUE}: loadedArchiveId is a captured load id ($state), "
            "not $derived from live archive_id (applyStatus must not re-sync "
            "onto leftover rows)"
        )
    if not _LOADED_STATE.search(pane_blob):
        fail(
            f"{_ISSUE}: loadedArchiveId is $state "
            "(empty / mismatch → no marker, no persistLastRead)"
        )
    if not _capture_on_success(sel):
        fail(
            f"{_ISSUE}: set loadedArchiveId = archive_id on successful "
            "selectPerson (after timeline =, not before the load)"
        )
    if not _capture_on_success(open_at):
        fail(
            f"{_ISSUE}: set loadedArchiveId = archive_id on successful "
            "openPersonAtMessage (after timeline =)"
        )
    if not _LOADED_CMP.search(paint):
        fail(
            f"{_ISSUE}: paint Last time only when loadedArchiveId === archive_id "
            "(empty / File → Open mismatch → no marker on leftover rows)"
        )
    if not _LOADED_CMP.search(persist) or not _WRITE_LAST.search(persist):
        fail(
            f"{_ISSUE}: persistLastRead / writeLastRead only when "
            "loadedArchiveId === archive_id (do not write Ada's leftover "
            "message_id into Berk's map)"
        )

    # 3) Filtered-out Last time jump — already loaded, not in filteredTimeline.
    prefix = _prefix_before_prepend(jmp)
    prefix_x = _expand_fn_calls(jump, prefix, 2)
    if not _UNFILTERED_TL.search(prefix_x):
        fail(
            f"{_ISSUE}: jumpToMessageId must look at loaded timeline[] "
            "(unfiltered) before prepending — a chip-hidden id is not older"
        )
    if not _FILTERED.search(prefix_x) or not _MESSAGE_ID.search(prefix_x):
        fail(
            f"{_ISSUE}: jumpToMessageId still seeks message_id in "
            "filteredTimeline (quiet stay when the loaded id is filtered out)"
        )
    loaded_at = _UNFILTERED_TL.search(prefix_x)
    rest = prefix_x[loaded_at.start() :] if loaded_at else ""
    if not re.search(r"\breturn\s+false\b", rest):
        fail(
            f"{_ISSUE}: jumpToMessageId returns false without selectPerson(..., true) "
            "when the stored message_id is already in loaded timeline but not in "
            "filteredTimeline (quiet stay; no Load older)"
        )
    if not _CALL_TL.search(pane + "\n" + pane_m):
        fail(
            f"{_ISSUE}: jumpToMessageId call passes timeline: () => timeline "
            "(unfiltered loaded window, not filteredTimeline)"
        )
