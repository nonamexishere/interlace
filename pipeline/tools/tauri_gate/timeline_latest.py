"""Helpers extracted from timeline_scroll.py (timeline_latest)."""
from __future__ import annotations

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


# j/k / highlight use indices from the filtered (visible) list.
_VISIBLE_KIND_JK = re.compile(
    r"("
    r"visibleTlIndices|visibleIndices|visibleTimeline|filteredTimeline"
    r"|nearestVisibleTlIndex"
    r")",
    re.I,
)
_TL_SPACER = re.compile(
    r"("
    r"\bpb-(?:8|10|12)\b"
    r"|padding-bottom\s*:"
    r"|\bh-(?:8|10|12)\b"
    r"|spacer"
    r")",
    re.I,
)
# Enough pad that the last bubble is not under the text-only chrome (not .day-heading 0.25rem).
_TL_PAD_UTIL = re.compile(r"\bpb-(?:8|10|12)\b")
_TL_LOADING_FALSE = re.compile(r"\btlLoading\s*=\s*false\b")
_SCROLL_TO_BOTTOM = re.compile(
    r"("
    r"scrollTop\s*=\s*[^;\n]*scrollHeight"
    r"|scrollTo\s*\(\s*\{[^}]*scrollHeight"
    r"|scrollIntoView\s*\("
    r")",
    re.I,
)
_SCROLL_PRESERVE = re.compile(
    r"("
    r"scrollTop\s*\+="
    r"|scrollHeight\s*-"
    r"|(?:prev(?:ious)?|old|saved|was)(?:Scroll)?(?:Height|Top)"
    r")",
    re.I,
)
_SCROLL_AFTER_LAYOUT = re.compile(r"requestAnimationFrame\s*\(|scrollIntoView\s*\(")
_RAF_CALL = re.compile(r"\b(?:window\.)?requestAnimationFrame\s*\(")
_PREPEND = re.compile(
    r"("
    r"(?:rows|older|page|reversed|chrono)\s*\.concat\s*\(\s*timeline\s*\)"
    r"|\[\s*\.\.\.[^,\]]+\s*,\s*\.\.\.timeline\s*\]"
    r"|\.unshift\s*\("
    r"|timeline\s*=\s*append\s*\?\s*[^;\n]*\.concat\s*\(\s*timeline\s*\)"
    r")",
)
# Newest-first API page flipped for chat order (older above, newest at the bottom).
_OLDEST_FIRST = re.compile(
    r"("
    r"\.toReversed\s*\("
    r"|\.reverse\s*\("
    r"|oldestFirst"
    r"|\.sort\s*\([^)]*sent_at"
    r")",
    re.I,
)

# #113 — newest page visible at the bottom; Load older at the top; prepend without jump.
# Dogfood: pad the list so the last bubble clears the text-only chrome; scroll after layout.
# Narrow pane: tlLoading = false before the open scroll; nested rAF so wrap has happened.
_LOAD_OLDER = re.compile(r"Load older")
_LAST_ROW = re.compile(
    r"("
    r"lastElementChild"
    r"|lastChild"
    r"|\.at\s*\(\s*-1\s*\)"
    r"|\[\s*length\s*-\s*1\s*\]"
    r"|length\s*-\s*1"
    r"|:last-child"
    r"|last(?:Row|Bubble|Msg|Message|Item)"
    r")",
    re.I,
)
# Whole newest-first store shown oldest-first (concat-then-reverse is ok).
_FULL_REVERSE = re.compile(
    r"("
    r"timeline\.toReversed\s*\("
    r"|timeline\.slice\s*\(\s*\)\s*\.reverse\s*\("
    r"|\[\s*\.\.\.timeline\s*\]\s*\.reverse\s*\("
    r"|\{#each\s+timeline\.toReversed"
    r")",
)
# Timeline row loop — full list names or windowed variants (#120).
_EACH_TIMELINE = re.compile(
    r"\{#each\s+(?:"
    r"timeline|dayGroups|"
    r"windowed(?:Day)?Groups|visible(?:Day)?Groups|virtual(?:Day)?Groups|"
    r"rendered(?:Day)?Groups|windowedRows|visibleRows|virtualRows|renderedRows|"
    r"windowedTimeline|visibleTimeline|virtualTimeline|renderedTimeline|"
    r"windowedItems|visibleItems|virtualItems"
    r")\b"
)
_CONCAT_BOTTOM = re.compile(r"timeline\.concat\s*\(\s*rows\s*\)")




def _person_timeline_open_tag(src: str) -> str:
    m = re.search(
        r"<[^>]*\bid=(?:[\"']person-timeline[\"']|\{[\"']person-timeline[\"']\})[^>]*>",
        src,
        re.I | re.S,
    )
    return m.group(0) if m else ""


def _has_nonzero_padding_bottom(blob: str) -> bool:
    for m in re.finditer(r"padding-bottom\s*:\s*([^;}\n]+)", blob, re.I):
        val = m.group(1).strip().lower()
        if val not in {"0", "0px", "0rem", "0em", "0%", "none"}:
            return True
    return False


def _timeline_css_pad_blocks(blob: str) -> list[str]:
    blocks: list[str] = []
    for rx in (
        r"#person-timeline(?:\s+(?:ol|ul))?\s*\{([^}]+)\}",
        r"\[id=[\"']person-timeline[\"']\](?:\s+(?:ol|ul))?\s*\{([^}]+)\}",
    ):
        blocks.extend(m.group(1) for m in re.finditer(rx, blob, re.I))
    return blocks


def _timeline_has_bottom_pad(crate: Path, app: str) -> bool:
    """True if #person-timeline / the message list pads above the text-only chrome."""
    tag = _person_timeline_open_tag(app)
    if tag and (_TL_PAD_UTIL.search(tag) or _has_nonzero_padding_bottom(tag)):
        return True
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    for block in _timeline_css_pad_blocks(blob):
        if _TL_PAD_UTIL.search(block) or _has_nonzero_padding_bottom(block):
            return True
    for p in _web_sources(crate):
        if p.suffix != ".svelte":
            continue
        text = p.read_text()
        script_end = text.rfind("</script>")
        markup = text[script_end:] if script_end >= 0 else text
        for each in _EACH_TIMELINE.finditer(markup):
            before = markup[: each.start()]
            ol = None
            for m in re.finditer(r"<ol\b[^>]*>", before, re.I | re.S):
                ol = m
            if ol and (
                _TL_PAD_UTIL.search(ol.group(0)) or _has_nonzero_padding_bottom(ol.group(0))
            ):
                return True
            end = _matching_each_end(markup, each.start())
            if end < 0:
                continue
            after = markup[end : end + 900]
            cut = after.lower().find("</scrollarea>")
            if cut < 0:
                cut = after.find("Bodies are text")
            if cut >= 0:
                after = after[:cut]
            if _TL_SPACER.search(after):
                return True
    return False


def _scrolls_after_layout(app: str, logic: str) -> bool:
    """True if open-person scroll waits for layout (rAF and/or last-row scrollIntoView)."""
    src = app + "\n" + logic
    for m in _SCROLL_AFTER_LAYOUT.finditer(src):
        window = src[max(0, m.start() - 500) : m.end() + 500]
        if m.group(0).startswith("requestAnimationFrame"):
            if re.search(r"scrollTop|scrollTo\s*\(|scrollIntoView", window):
                return True
        elif _LAST_ROW.search(window):
            return True
    return False


def _contains_open_latest_scroll(blob: str, whole: str, seen: set[str] | None = None) -> bool:
    """True if blob (or a named rAF callback it references) scrolls to latest."""
    if _SCROLL_TO_BOTTOM.search(blob):
        return True
    found = seen if seen is not None else set()
    for m in _RAF_CALL.finditer(blob):
        arg = _call_arg(blob, m.end() - 1)
        if _SCROLL_TO_BOTTOM.search(arg):
            return True
        ident = re.fullmatch(r"\s*([A-Za-z_]\w*)\s*", arg)
        if ident and ident.group(1) not in found:
            found.add(ident.group(1))
            body = _function_body(whole, ident.group(1))
            if body and _contains_open_latest_scroll(body, whole, found):
                return True
    return False


def _open_person_scroll_anchor(src: str, whole: str) -> int | None:
    """Index of the outer open-person rAF / scrollTop / scrollIntoView (not append +=)."""
    for m in _RAF_CALL.finditer(src):
        arg = _call_arg(src, m.end() - 1)
        if arg and _contains_open_latest_scroll(arg, whole):
            return m.start()
    m = _SCROLL_TO_BOTTOM.search(src)
    return m.start() if m else None


def _clears_loading_before_open_scroll(app: str, logic: str) -> bool:
    """tlLoading = false must appear before the open-person rAF/scroll, not only in finally after."""
    whole = app + "\n" + logic
    fn = _function_body(whole, "selectPerson") or whole
    cleaned = _without_comments(fn)
    whole_c = _without_comments(whole)
    anchor = _open_person_scroll_anchor(cleaned, whole_c)
    if anchor is not None:
        return bool(_TL_LOADING_FALSE.search(cleaned[:anchor]))
    m = _TL_LOADING_FALSE.search(cleaned)
    if not m:
        return False
    after = cleaned[m.end() :]
    for call in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", after):
        name = call.group(1)
        if name in _SCROLL_HELPER_SKIP:
            continue
        body = _function_body(whole_c, name)
        if body and _open_person_scroll_anchor(_without_comments(body), whole_c) is not None:
            return True
    return False


def _nested_raf_around_open_scroll(app: str, logic: str) -> bool:
    """True if a requestAnimationFrame callback itself schedules another rAF that scrolls to latest."""
    whole = _without_comments(app + "\n" + logic)
    for m in _RAF_CALL.finditer(whole):
        arg = _call_arg(whole, m.end() - 1)
        if not arg or not _RAF_CALL.search(arg):
            continue
        if _contains_open_latest_scroll(arg, whole):
            return True
    return False


# #120 — virtualize person timeline (visible + overscan only in the DOM).
# Static analysis: fail naive full {#each dayGroups}→{#each group.rows} without a window.
# No FPS/perf assertions in CI; dogfood measures 10k scroll.
_VIRT_SIGNAL = re.compile(
    r"("
    r"\boverscan\b"
    r"|\bvirtual(?:ize|ized|izing|isation|ization)?\b"
    r"|\bVirtualList\b"
    r"|\bvirtual(?:List|Rows?|Window|Scroll|Range|Items?)\b"
    r"|\bwindow(?:ed|ing)(?:Rows?|Items?|Groups?|Range|Start|End|Slice|Timeline|DayGroups?)?\b"
    r"|\bvisible(?:Range|Start|End|Count|Window|Slice|Rows?|Items?|Groups?|DayGroups?|"
    r"Indices|Index)\b"
    r"|\b(?:start|end)(?:Index|Row|Offset)\b"
    r"|\b(?:first|last)Visible(?:Index|Row|Item)?\b"
    r"|\brender(?:ed)?(?:Rows?|Items?|Range|Window|Slice|Groups?)\b"
    r"|\bviewport(?:Rows?|Range|Height|Top)\b"
    r"|\b(?:row|item)(?:Height|Size)\b"
    r"|\bestimated(?:Row|Item)?(?:Height|Size)\b"
    r"|\btotalHeight\b"
    r"|\bspacer(?:Height|Top|Bottom)?\b"
    r"|\bscrollMargin\b"
    r"|\bsvelte-virtual(?:-list)?\b"
    r"|@tanstack/(?:svelte-)?virtual\b"
    r"|\bcreateVirtualizer\b"
    r"|\buseVirtualizer\b"
    r"|\bVirtualizer\b"
    r")",
    re.I,
)

from tauri_gate.timeline_latest_rest import (
    _NAIVE_DAYGROUPS_ROWS,
    _NAIVE_FULL_ROW_EACH,
    _BODY_INNER_HTML,
    _SCOPE_10M,
    _SCOPE_LAZY_EVERY_PHOTO,
    _JK_KEY,
    _derived_body,
    _body_has_row_window,
    _list_source_is_windowed,
    _timeline_each_names_in_markup,
    _naive_full_timeline_mount,
    _has_windowed_render_path,
    _TL_INDEX_READ,
    _HEIGHT_OF,
    __all__,
)

__all__ = [
    "_VISIBLE_KIND_JK",
    "_TL_SPACER",
    "_TL_PAD_UTIL",
    "_TL_LOADING_FALSE",
    "_SCROLL_TO_BOTTOM",
    "_SCROLL_PRESERVE",
    "_SCROLL_AFTER_LAYOUT",
    "_RAF_CALL",
    "_PREPEND",
    "_OLDEST_FIRST",
    "_LOAD_OLDER",
    "_LAST_ROW",
    "_FULL_REVERSE",
    "_EACH_TIMELINE",
    "_CONCAT_BOTTOM",
    "_person_timeline_open_tag",
    "_has_nonzero_padding_bottom",
    "_timeline_css_pad_blocks",
    "_timeline_has_bottom_pad",
    "_scrolls_after_layout",
    "_contains_open_latest_scroll",
    "_open_person_scroll_anchor",
    "_clears_loading_before_open_scroll",
    "_nested_raf_around_open_scroll",
    "_VIRT_SIGNAL",
    "_NAIVE_DAYGROUPS_ROWS",
    "_NAIVE_FULL_ROW_EACH",
    "_BODY_INNER_HTML",
    "_SCOPE_10M",
    "_SCOPE_LAZY_EVERY_PHOTO",
    "_JK_KEY",
    "_derived_body",
    "_body_has_row_window",
    "_list_source_is_windowed",
    "_timeline_each_names_in_markup",
    "_naive_full_timeline_mount",
    "_has_windowed_render_path",
    "_TL_INDEX_READ",
    "_HEIGHT_OF",
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
]
