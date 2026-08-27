"""Continuation of timeline_latest."""
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
# Classic anti-pattern: full dayGroups then every group.rows (no window).
_NAIVE_DAYGROUPS_ROWS = re.compile(
    r"\{#each\s+dayGroups\b[^}]*\}[\s\S]{0,1200}?\{#each\s+group\.rows\b",
    re.I,
)
# Full unwindowed list each (flat timeline / filtered list of every row).
_NAIVE_FULL_ROW_EACH = re.compile(
    r"\{#each\s+(?:timeline|filteredTimeline)\b",
    re.I,
)
_BODY_INNER_HTML = re.compile(
    r"("
    r"\{@html\b"
    r"|\.innerHTML\s*="
    r"|insertAdjacentHTML\s*\("
    r")",
)
_SCOPE_10M = re.compile(
    r"("
    r"10\s*[Mm](?:illion)?\b[^.\n]{0,80}"
    r"(?:one view|single view|in (?:the )?DOM|all (?:at )?once|in one (?:list|view))"
    r"|(?:render|mount|load)\s+(?:all\s+)?10\s*[Mm]"
    r")",
    re.I,
)
_SCOPE_LAZY_EVERY_PHOTO = re.compile(
    r"("
    r"lazy[- ]decode\s+every\s+(?:photo|image|cas|attachment)"
    r"|decode\s+every\s+(?:photo|image)\s+laz"
    r"|lazyDecodeEvery"
    r")",
    re.I,
)
_JK_KEY = re.compile(
    r"("
    r"key\s*===?\s*[\"']j[\"']"
    r"|[\"']j[\"']\s*===?\s*key"
    r"|key\s*===?\s*[\"']k[\"']"
    r"|[\"']k[\"']\s*===?\s*key"
    r"|visibleTlIndices"
    r"|nearestVisibleTlIndex"
    r")",
    re.I,
)


def _derived_body(cleaned: str, name: str) -> str | None:
    """Return the body of `const name = $derived...` / `$derived.by` if present."""
    m = re.search(
        rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*\$derived(?:\.by)?\s*\(",
        cleaned,
    )
    if not m:
        return None
    open_idx = m.end() - 1
    close = _match_closer(cleaned, open_idx)
    if close < 0:
        return cleaned[m.end() : m.end() + 2500]
    return cleaned[open_idx + 1 : close]


def _body_has_row_window(body: str) -> bool:
    """True if a derived-list body actually bounds rows (not only ISO day slice)."""
    if re.search(
        r"\boverscan\b|\bvirtual|\bwindow(?:ed|ing|Start|End|Range)|"
        r"\bvisible(?:Range|Start|End|Window|Slice|Rows?|Groups?)|"
        r"\b(?:start|end)(?:Index|Row)\b|"
        r"\b(?:first|last)Visible\b|"
        r"createVirtualizer|useVirtualizer",
        body,
        re.I,
    ):
        return True
    # .slice(a, b) row window — exclude the common day-prefix .slice(0, 10).
    for sm in re.finditer(r"\.slice\s*\(\s*([^)]*)\)", body):
        args = sm.group(1)
        if re.match(r"\s*0\s*,\s*10\s*$", args):
            continue
        if "," in args:
            return True
    return False


def _list_source_is_windowed(cleaned: str, name: str) -> bool:
    """True if `name` is derived/assigned with a real row window (not a rename alone)."""
    body = _derived_body(cleaned, name)
    if body and _body_has_row_window(body):
        return True
    # Non-$derived assignment / helper: name = windowRows(...) / slice(...)
    m = re.search(
        rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?!\$derived)([^;]{{0,400}})",
        cleaned,
    )
    if m and _body_has_row_window(m.group(1)):
        return True
    if re.search(
        rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*"
        r"(?:\$derived(?:\.by)?\s*\()?"
        r"[\s\S]{0,240}"
        r"(?:window(?:ed|ing)\w*|virtual(?:ize|Rows|List|Items?)?|"
        r"visible(?:Range|Rows|Groups?|Window)|"
        r"overscan|createVirtualizer|useVirtualizer)",
        cleaned,
        re.I,
    ):
        return True
    return False


def _timeline_each_names_in_markup(markup: str) -> list[str]:
    """Names used in {#each ...} that look like timeline row sources."""
    names: list[str] = []
    for m in re.finditer(r"\{#each\s+([A-Za-z_]\w*)\b", markup):
        name = m.group(1)
        if name in _TIMELINE_EACH_NAMES or re.match(
            r"^(?:windowed|visible|virtual|rendered)",
            name,
            re.I,
        ):
            names.append(name)
        elif name in {"timeline", "filteredTimeline", "dayGroups"}:
            names.append(name)
    return names


def _naive_full_timeline_mount(markup: str, cleaned: str) -> bool:
    """True if the person timeline always mounts every filtered row (no window)."""
    # 1) {#each dayGroups} → {#each group.rows} with unwindowed dayGroups.
    if _NAIVE_DAYGROUPS_ROWS.search(markup):
        if not _list_source_is_windowed(cleaned, "dayGroups"):
            return True
    # 2) Flat {#each timeline|filteredTimeline} without windowing that source.
    for m in _NAIVE_FULL_ROW_EACH.finditer(markup):
        mm = re.search(r"\{#each\s+(\w+)", m.group(0))
        name = mm.group(1) if mm else "timeline"
        if not _list_source_is_windowed(cleaned, name):
            return True
    # 3) Any timeline-ish each whose source is not windowed (rename without window).
    for name in _timeline_each_names_in_markup(markup):
        if name in {"dayGroups", "timeline", "filteredTimeline"}:
            continue  # already covered; dayGroups alone without rows is headings-only
        # Nested group.rows is not a top-level list name.
        if not _list_source_is_windowed(cleaned, name):
            # Only treat as naive if the each body looks like message rows.
            for em in re.finditer(rf"\{{#each\s+{re.escape(name)}\b[^}}]*\}}", markup):
                end = _matching_each_end(markup, em.start())
                chunk = markup[em.start() : end if end > 0 else em.start() + 800]
                if re.search(
                    r"from_me|body_text|data-from-me|bubble-me|group\.rows",
                    chunk,
                    re.I,
                ):
                    return True
    return False


def _has_windowed_render_path(markup: str, cleaned: str) -> bool:
    """True if some timeline {#each} iterates a really windowed list (or VirtualList)."""
    for name in _timeline_each_names_in_markup(markup):
        if _list_source_is_windowed(cleaned, name):
            return True
    # Virtual list component / helper owns the window even without a named slice.
    if re.search(
        r"<Virtual(?:List|Scroll|izer)?\b|createVirtualizer\s*\(|useVirtualizer\s*\(",
        markup + "\n" + cleaned,
        re.I,
    ):
        return True
    # dayGroups itself windowed (still named dayGroups) + nested group.rows.
    if re.search(r"\{#each\s+dayGroups\b", markup) and _list_source_is_windowed(
        cleaned, "dayGroups"
    ):
        return True
    return False
_TL_INDEX_READ = re.compile(
    r"("
    r"\[data-tl-index\]"
    r"|getAttribute\s*\(\s*[\"']data-tl-index[\"']"
    r"|dataset\.tlIndex"
    r")"
)
_HEIGHT_OF = re.compile(
    r"\b("
    r"heightOf"
    r"|rowHeightOf"
    r"|heightAt"
    r"|tlHeightOf"
    r"|rowHeightAt"
    r")\b"
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
    "re",
    "Path",
    "fail",
    "repo_root",
    "_HTML_BODY",
    "_function_body",
    "_svelte_markup",
    "_timeline_block",
    "_web_logic",
    "_web_sources",
    "_without_comments",
    "_HEIGHT_CACHE",
    "_PRE_WRAP",
    "annotations",
    "_SCROLL_HELPER_SKIP",
    "_TIMELINE_EACH_NAMES",
    "_call_arg",
    "_match_closer",
    "_matching_each_end",
]

__all__ = [
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
    "__all__",
]
