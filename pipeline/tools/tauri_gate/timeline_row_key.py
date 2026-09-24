"""#417 — timeline window keyed by message_id.

Static scan. The row {#each} and the height cache use message_id.
data-tl-index, j/k, and Space stay array positions. Load older still
calls shiftHeightsForPrepend, but that body must not renumber keys.
applyOlderThreadRows must not call resetHeights. Person switch still
drops the window. No Rust test. Placeholders Ada / Berk / Self only.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.jump_day_heading import _read
from tauri_gate.jump_day_heading_stutter import _fn
from tauri_gate.scan import _without_comments

_ISSUE = "#417"
_ROW_EACH_INDEX = re.compile(
    r"\{#each\s+group\.rows\s+as\s+item\s*\(\s*item\.index\s*\)"
)
_ROW_EACH_ID = re.compile(
    r"\{#each\s+group\.rows\s+as\s+item\s*\([^)]*\bmessage_id\b"
)
_GROUP_EACH = re.compile(
    r"\{#each\s+windowedDayGroups\s+as\s+group\s*\(([^)]*)\)"
)
_RENUMBER = re.compile(r"Number\s*\(\s*k\s*\)\s*\+\s*n")
_MEASURE_INDEX = re.compile(r"use:measureTlRow=\{item\.index\}")
_MEASURE_ID = re.compile(r"use:measureTlRow=\{[^}]*\bmessage_id\b")
_TL_INDEX_POS = re.compile(r"data-tl-index=\{item\.index\}")
_TL_INDEX_ID = re.compile(r"data-tl-index=\{[^}]*\bmessage_id\b")


def _src(crate: Path, name: str) -> str:
    return _without_comments(_read(crate, name))


def _keep(ok: bool, msg: str) -> None:
    if not ok:
        fail(f"{_ISSUE}: {msg}")


def assert_timeline_row_key(crate: Path) -> None:
    rows = _src(crate, "TimelineRows.svelte")
    list_s = _src(crate, "TimelineList.svelte")
    pane = _src(crate, "TimelinePane.svelte")
    keys = _src(crate, "PeopleKeys.ts")
    virt = _src(crate, "TimelineVirtual.ts")
    jump = _src(crate, "jumpDay.ts")
    walk = _src(crate, "threadWalk.ts")
    shift = _fn(list_s, "shiftHeightsForPrepend")
    reset = _fn(list_s, "resetHeights")
    select = _fn(pane, "selectPerson")
    older = _fn(pane, "applyOlderThreadRows")
    newer = _fn(pane, "loadNewerPage")
    opened = _fn(pane, "openPersonAtMessage")
    height = _fn(list_s, "heightOf") + _fn(list_s, "offsetOf")
    height += _fn(virt, "heightOf") + _fn(virt, "offsetOf")

    _keep(bool(rows and list_s and pane and keys and virt and jump and walk), "timeline row sources are required")
    _keep("shiftHeightsForPrepend" in select, "Load older must still call shiftHeightsForPrepend")
    _keep("resetHeights" in select and bool(reset), "resetHeights must stay on the non-append person path")
    _keep(
        bool(re.search(r"if\s*\(\s*!append\s*\)\s*threadTarget\s*=\s*null", select)),
        "non-append selectPerson must still set threadTarget = null",
    )
    _keep("++tlGen" in select, "person switch must still bump tlGen")
    _keep(
        "added.concat(timeline)" in select and "tlIndex +=" in select,
        "Load older must still prepend and shift tlIndex by added.length",
    )
    selected_effect = re.search(
        r"\$effect\(\(\)\s*=>\s*\{[^}]*\bselectedId\b[^}]*\}",
        list_s,
    )
    _keep(
        bool(selected_effect)
        and (
            "rowHeights = {}" in selected_effect.group(0)
            or "resetHeights" in selected_effect.group(0)
        ),
        "the selectedId effect must still drop rowHeights",
    )
    _keep(
        "shiftHeightsForPrepend" not in newer and "resetHeights" not in newer,
        "Load newer must stay a tail concat with no prepend shift and no wipe",
    )
    _keep("resetHeights" in opened, "search jump must stay a replace plus resetHeights")
    go_day = _fn(pane, "goToJumpDay")
    _keep(
        bool(re.search(
            r"personDayMessage[\s\S]*openPersonAtMessage[\s\S]*pinJump",
            go_day,
        )),
        "day jump must call personDayMessage, then openPersonAtMessage, then pinJump",
    )
    _keep(
        "selectPerson" not in walk and "shiftHeightsForPrepend" not in walk,
        "threadWalk.ts must not call selectPerson or shiftHeightsForPrepend",
    )
    _keep(bool(_TL_INDEX_POS.search(rows)), "data-tl-index must stay the numeric item.index")
    _keep(not _TL_INDEX_ID.search(rows), "data-tl-index must not become message_id")
    _keep("data-message-id" not in rows, "do not add data-message-id on the timeline row")
    _keep(
        'visible.indexOf(ctx.tlIndex)' in keys
        and '[data-tl-index="${ctx.tlIndex}"]' in keys
        and 'e.key === "j"' in keys
        and 'e.key === "k"' in keys
        and "[data-tl-index]" in keys,
        "j/k, Home, and Space must stay on the numeric tlIndex",
    )
    _keep(
        "VIRTUALIZE_AFTER = 250" in virt and "OVERSCAN = 15" in virt,
        "VIRTUALIZE_AFTER must stay 250 and OVERSCAN must stay 15",
    )
    _keep(
        "total <= VIRTUALIZE_AFTER" in virt
        and "filteredTimeline.slice(startIndex, endIndex)" in list_s,
        "mount must stay the full list at VIRTUALIZE_AFTER, otherwise the viewport slice",
    )
    _keep("TIMELINE_PAGE_LIMIT = 80" in jump, "TIMELINE_PAGE_LIMIT must stay 80")
    _keep("DAY_HEADING_HEIGHT" in jump, "a day heading stays DAY_HEADING_HEIGHT, not a cache row")
    _keep(
        'id="person-timeline"' in list_s and "pb-8" in list_s,
        "pb-8 must stay on #person-timeline",
    )
    _keep(
        bool(re.search(r'class="[^"]*overflow-hidden[^"]*flex-col', pane)),
        "the pane column must stay overflow-hidden flex-col",
    )
    row_key = _ROW_EACH_INDEX.search(rows) or _ROW_EACH_ID.search(rows)
    _keep(
        "attachments" in rows and not (row_key and "attachment.id" in row_key.group(0)),
        "one message stays one bubble; do not key the row by attachment.id",
    )
    _keep(bool(shift), "shiftHeightsForPrepend must stay a called function")
    _keep("rowHeights = {}" not in shift, "shiftHeightsForPrepend must not drop measured entries")
    _keep(
        "message_id" in older and "concat" in older,
        "lightbox prepend must still dedupe by message_id and insert above",
    )

    red: list[str] = []
    if _ROW_EACH_INDEX.search(rows) or not _ROW_EACH_ID.search(rows):
        red.append("row {#each} key is still item.index, not message_id")
    group = _GROUP_EACH.search(rows)
    group_key = group.group(1) if group else ""
    if "message_id" not in group_key or re.search(r"\bindex\b", group_key):
        red.append("day-group {#each} key is still the shifting index, not message_id")
    if not shift or _RENUMBER.search(shift):
        red.append("shiftHeightsForPrepend still does Number(k) + n")
    if "resetHeights" in older:
        red.append("applyOlderThreadRows still calls resetHeights")
    if _MEASURE_INDEX.search(rows) or not _MEASURE_ID.search(rows) or "message_id" not in height:
        red.append("the height cache is still keyed by array index, not message_id")
    if red:
        fail(f"{_ISSUE}: " + f"\n{_ISSUE}: ".join(red))
