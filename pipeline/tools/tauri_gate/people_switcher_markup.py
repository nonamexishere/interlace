"""Helpers extracted from people_switcher_label.py (people_switcher_markup)."""
from __future__ import annotations

from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import fail

from tauri_gate.scan import (
    _PERSON_PANE_SKIP,
    _PRETTY_GMAIL,
    _RAW_WHATSAPP,
    _SCROLL_HELPER_SKIP,
    _VOID_HTML,
    _ancestor_tags,
    _assigned_idents,
    _call_arg,
    _cond_uses_flag,
    _function_body,
    _helper_with_callees,
    _js_next,
    _match_closer,
    _matching_each_end,
    _open_tag_before,
    _svelte_markup,
    _tag_name,
    _template_stack,
    _web_sources,
)

from tauri_gate.status_toasts_toast import _person_detail_markup
from tauri_gate.people_switcher_pretty import (
    _CONV_EACH,
    _CONV_SWITCHER_HOOK,
    _CONV_SELECT,
    _CONV_LABEL_HELPER_NAMES,
    _RAW_GMAIL,
    _TITLE_EQ_PERSON,
    _EMPTY_TITLE,
    _DISTINCT_TITLE,
    _RAW_TITLE_HEADING,
    _SUBTITLE_EL,
    _TW_Z_INDEX,
    _CSS_Z_INDEX,
    _CLASS_Z_DIR,
    _TW_STACK_BG,
    _CSS_STACK_BG,
    _TIMELINE_INNER,
    _DAY_HEADING_CSS,
    _strip_tag_attrs,
)


def _people_list_hidden_on_select(crate: Path) -> bool:
    for p in _web_sources(crate):
        if p.suffix != ".svelte":
            continue
        markup = _svelte_markup(p.read_text())
        for m in re.finditer(r"\{#each\s+filtered\b", markup):
            for kind, a, _b in _template_stack(markup, m.start()):
                if kind == "if" and re.search(
                    r"!\s*selectedId|selectedId\s*===\s*null|selectedId\s*==\s*null",
                    a,
                ):
                    return True
    return False


def _z_from_text(blob: str) -> int | None:
    """Highest explicit numeric z-index in classes / CSS (z-auto does not count)."""
    best: int | None = None
    for m in _TW_Z_INDEX.finditer(blob):
        n = int(m.group(1) or m.group(2))
        best = n if best is None else max(best, n)
    for m in _CSS_Z_INDEX.finditer(blob):
        n = int(m.group(1))
        best = n if best is None else max(best, n)
    for m in _CLASS_Z_DIR.finditer(blob):
        n = int(m.group(1))
        best = n if best is None else max(best, n)
    return best


def _has_stacking_bg(blob: str) -> bool:
    """Opaque background so a sticky date cannot show through the control."""
    if _CSS_STACK_BG.search(blob):
        return True
    for m in _TW_STACK_BG.finditer(blob):
        if m.group(1):
            continue
        if m.group(3) == "0":
            continue
        return True
    return False


def _class_list(tag: str) -> list[str]:
    m = re.search(r"\bclass(?:Name)?\s*=\s*[\"']([^\"']*)[\"']", tag, re.I)
    if not m:
        m = re.search(
            r"\bclass(?:Name)?\s*=\s*\{[`'\"]([^`'\"]*)[`'\"]\}",
            tag,
            re.I,
        )
    if not m:
        return []
    return m.group(1).split()


def _id_of(tag: str) -> str | None:
    m = re.search(r"\bid\s*=\s*[\"']([^\"']+)[\"']", tag, re.I)
    return m.group(1) if m else None


def _style_attr(tag: str) -> str:
    m = re.search(r"\bstyle\s*=\s*[\"']([^\"']*)[\"']", tag, re.I)
    return m.group(1) if m else ""


def _css_rules_for(css: str, tag: str) -> str:
    chunks: list[str] = []
    for cls in _class_list(tag):
        esc = re.escape(cls)
        chunks.extend(m.group(1) for m in re.finditer(rf"\.{esc}\b[^{{]*\{{([^}}]+)\}}", css))
    el_id = _id_of(tag)
    if el_id:
        esc = re.escape(el_id)
        chunks.extend(m.group(1) for m in re.finditer(rf"#{esc}\b[^{{]*\{{([^}}]+)\}}", css))
    return "\n".join(chunks)


def _layer_blob(tag: str, css: str) -> str:
    return "\n".join((tag, _style_attr(tag), _css_rules_for(css, tag)))


def _layer_stacks(blob: str, day_z: int) -> tuple[bool, int | None, bool]:
    z = _z_from_text(blob)
    bg = _has_stacking_bg(blob)
    return bool(z is not None and z > day_z and bg), z, bg


def _element_span(markup: str, pos: int) -> tuple[int, str, str] | None:
    """Open tag at/before pos and its inner HTML (not descendants' close)."""
    found = _open_tag_before(markup, pos + 1)
    if not found:
        return None
    lt, tag = found
    name = _tag_name(tag)
    if not name or tag.rstrip().endswith("/>") or name in _VOID_HTML:
        return lt, tag, ""
    start = lt + len(tag)
    depth = 1
    rx = re.compile(rf"<{re.escape(name)}\b|</{re.escape(name)}\s*>", re.I)
    for m in rx.finditer(markup, start):
        if markup.startswith("</", m.start()):
            depth -= 1
            if depth == 0:
                return lt, tag, markup[start : m.start()]
        else:
            depth += 1
    return lt, tag, markup[start:]


def _day_heading_z_index(crate: Path) -> int:
    """Sticky day-heading z-index. Missing still stacks as 10 (current .day-heading)."""
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    found: list[int] = []
    for m in _DAY_HEADING_CSS.finditer(blob):
        z = _z_from_text(m.group(1))
        if z is not None:
            found.append(z)
    for m in re.finditer(r"<[^>]+>", blob):
        tag = m.group(0)
        if not re.search(r"day-heading|day-separator|day-sep\b|data-day-heading", tag, re.I):
            continue
        z = _z_from_text(tag)
        if z is not None:
            found.append(z)
    return max(found) if found else 10


def _switcher_hook_positions(markup: str) -> list[int]:
    pos = [m.start() for m in _CONV_SWITCHER_HOOK.finditer(markup)]
    if pos:
        return pos
    pos = [m.start() for m in _CONV_SELECT.finditer(markup)]
    if pos:
        return pos
    return [m.start() for m in _CONV_EACH.finditer(markup)]


def _is_switcher_tag(tag: str) -> bool:
    if _CONV_SWITCHER_HOOK.search(tag) or _CONV_SELECT.search(tag):
        return True
    return _tag_name(tag) in {"details", "select"}


def _child_open_tag(inner: str, rx: re.Pattern[str]) -> str | None:
    m = rx.search(inner)
    if not m:
        return None
    found = _open_tag_before(inner, m.start() + 1)
    return found[1] if found else m.group(0)


def _switcher_summary_and_panel(tag: str, inner: str) -> tuple[str | None, str | None]:
    """Closed control (summary / select) and the open list, if they are separate."""
    if _tag_name(tag) == "select" or _CONV_SELECT.search(tag):
        return tag, None
    summary = _child_open_tag(inner, re.compile(r"<summary\b", re.I))
    panel = _child_open_tag(
        inner,
        re.compile(
            r"<[^>]*\babsolute\b|<[^>]*role\s*=\s*[\"'](?:listbox|menu)[\"']",
            re.I,
        ),
    )
    if panel is None:
        panel = _child_open_tag(inner, re.compile(r"<(?:ul|ol|menu)\b", re.I))
    return summary, panel


def _switcher_above_day_heading(crate: Path) -> tuple[bool, int, int | None, bool]:
    """Whether All / the open panel stack above .day-heading.

    A z-index on the person-pane header or the switcher element covers both
    the closed label and the dropdown (one stacking context). z-index only on
    the panel leaves All under the sticky date; only on the summary leaves
    the open list under it. People-sidebar overflow (#159) is not in scope.
    """
    day_z = _day_heading_z_index(crate)
    css = "\n".join(p.read_text() for p in _web_sources(crate))
    best_z: int | None = None
    saw_bg = False
    saw_switcher = False
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        markup = p.read_text()
        for pos in _switcher_hook_positions(markup):
            saw_switcher = True
            switcher: tuple[int, str, str] | None = None
            headers: list[str] = []
            cur = pos + 1
            for _ in range(12):
                found = _open_tag_before(markup, cur)
                if not found:
                    break
                lt, _open = found
                el = _element_span(markup, lt)
                if not el:
                    break
                _lt, tag, inner = el
                if switcher is None and _is_switcher_tag(tag):
                    switcher = el
                elif switcher is not None and not _TIMELINE_INNER.search(inner):
                    headers.append(tag)
                cur = lt
            if switcher is None:
                switcher = _element_span(markup, pos)
            if switcher is None:
                continue
            _lt, sw_tag, sw_inner = switcher
            summary, panel = _switcher_summary_and_panel(sw_tag, sw_inner)
            sw_blob = _layer_blob(sw_tag, css)
            hd_blobs = [_layer_blob(h, css) for h in headers]
            su_blob = _layer_blob(summary, css) if summary else ""
            pa_blob = _layer_blob(panel, css) if panel else ""
            sw_ok, sw_z, sw_bg = _layer_stacks(sw_blob, day_z)
            hd_hits = [_layer_stacks(b, day_z) for b in hd_blobs]
            hd_ok = any(ok for ok, _z, _bg in hd_hits)
            su_ok, su_z, su_bg = _layer_stacks(su_blob, day_z) if summary else (False, None, False)
            pa_ok, _pa_z, _pa_bg = _layer_stacks(pa_blob, day_z) if panel else (True, None, True)
            for z in (sw_z, su_z, *(z for _ok, z, _bg in hd_hits)):
                if z is None:
                    continue
                best_z = z if best_z is None else max(best_z, z)
            saw_bg = saw_bg or sw_bg or su_bg or any(bg for _ok, _z, bg in hd_hits)
            # Panel-only stacking does not cover the word All.
            if sw_ok or hd_ok or (su_ok and pa_ok):
                return True, day_z, best_z, True
    if not saw_switcher:
        return False, day_z, best_z, saw_bg
    return False, day_z, best_z, saw_bg


def _assignment_rhs(src: str, name: str) -> str:
    m = re.search(
        rf"\b(?:const|let|var)\s+{re.escape(name)}\s*=\s*",
        src,
    )
    if not m:
        return ""
    rest = src[m.end() :]
    dm = re.match(r"\$derived(?:\.by)?\s*\(", rest)
    if dm:
        return _call_arg(rest, dm.end() - 1).strip().rstrip(",")
    depth = 0
    j = 0
    while j < len(rest):
        nxt = _js_next(rest, j)
        if nxt != j:
            j = nxt
            continue
        c = rest[j]
        if c in "({[":
            depth += 1
        elif c in ")}]":
            depth -= 1
        elif c == ";" and depth <= 0:
            break
        j += 1
    return rest[:j].strip()

from tauri_gate.people_switcher_markup_rest import (
    _is_pretty_platform_blob,
    _pretty_platform_helpers,
    _compares_title_to_person,
    _blob_chooses_pretty_platform,
    _conversation_chooser_helpers,
    _closed_switcher_label_markup,
    _switcher_summary_markup,
    _switcher_row_markup,
    _strip_switcher_subtitles,
    _heading_exprs,
    _expr_with_defs,
    _uses_named_helper,
    _is_raw_title_heading,
    _headings_use_label_helper,
    __all__,
)

__all__ = [
    "_people_list_hidden_on_select",
    "_z_from_text",
    "_has_stacking_bg",
    "_class_list",
    "_id_of",
    "_style_attr",
    "_css_rules_for",
    "_layer_blob",
    "_layer_stacks",
    "_element_span",
    "_day_heading_z_index",
    "_switcher_hook_positions",
    "_is_switcher_tag",
    "_child_open_tag",
    "_switcher_summary_and_panel",
    "_switcher_above_day_heading",
    "_assignment_rhs",
    "_is_pretty_platform_blob",
    "_pretty_platform_helpers",
    "_compares_title_to_person",
    "_blob_chooses_pretty_platform",
    "_conversation_chooser_helpers",
    "_closed_switcher_label_markup",
    "_switcher_summary_markup",
    "_switcher_row_markup",
    "_strip_switcher_subtitles",
    "_heading_exprs",
    "_expr_with_defs",
    "_uses_named_helper",
    "_is_raw_title_heading",
    "_headings_use_label_helper",
    "annotations",
    "re",
    "Path",
    "fail",
    "_PERSON_PANE_SKIP",
    "_PRETTY_GMAIL",
    "_RAW_WHATSAPP",
    "_SCROLL_HELPER_SKIP",
    "_VOID_HTML",
    "_ancestor_tags",
    "_assigned_idents",
    "_call_arg",
    "_cond_uses_flag",
    "_function_body",
    "_helper_with_callees",
    "_js_next",
    "_match_closer",
    "_matching_each_end",
    "_open_tag_before",
    "_svelte_markup",
    "_tag_name",
    "_template_stack",
    "_web_sources",
    "_person_detail_markup",
    "_CONV_EACH",
    "_CONV_SWITCHER_HOOK",
    "_CONV_SELECT",
    "_CONV_LABEL_HELPER_NAMES",
    "_RAW_GMAIL",
    "_TITLE_EQ_PERSON",
    "_EMPTY_TITLE",
    "_DISTINCT_TITLE",
    "_RAW_TITLE_HEADING",
    "_SUBTITLE_EL",
    "_TW_Z_INDEX",
    "_CSS_Z_INDEX",
    "_CLASS_Z_DIR",
    "_TW_STACK_BG",
    "_CSS_STACK_BG",
    "_TIMELINE_INNER",
    "_DAY_HEADING_CSS",
    "_strip_tag_attrs",
]
