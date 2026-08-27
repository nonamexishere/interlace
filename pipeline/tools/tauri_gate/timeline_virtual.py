"""Helpers extracted from timeline_scroll.py (timeline_virtual)."""
from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _HTML_BODY,
    _SCROLL_HELPER_SKIP,
    _TIMELINE_EACH_NAMES,
    _call_arg,
    _function_body,
    _match_closer,
    _matching_each_end,
    _svelte_markup,
    _timeline_block,
    _web_logic,
    _web_sources,
    _without_comments,
)

from tauri_gate.import_boot_guards import (
    _HEIGHT_CACHE,
    _PRE_WRAP,
)
from tauri_gate.timeline_latest import (
    _TL_INDEX_READ,
    _HEIGHT_OF,
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

__all__ = [
    "_OFFSET_OF",
    "_LIVE_AVG",
    "_FIXED_INDEX_TIMES_EST",
    "_SCROLL_DIV_EST",
    "_CONST_FALLBACK",
    "_HEIGHT_OF_NAMES",
    "_OFFSET_OF_NAMES",
    "_row_measure_path",
    "_uses_prefix_sum",
    "_height_lookup_uses_constant",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_HTML_BODY",
    "_SCROLL_HELPER_SKIP",
    "_TIMELINE_EACH_NAMES",
    "_call_arg",
    "_function_body",
    "_match_closer",
    "_matching_each_end",
    "_svelte_markup",
    "_timeline_block",
    "_web_logic",
    "_web_sources",
    "_without_comments",
    "_HEIGHT_CACHE",
    "_PRE_WRAP",
    "_TL_INDEX_READ",
    "_HEIGHT_OF",
]
