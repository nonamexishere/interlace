"""Continuation of people_switcher_markup."""
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
from tauri_gate.people_switcher_label_extra2 import _PRETTY_WHATSAPP
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
from tauri_gate.people_switcher_markup import (
    _element_span,
    _assignment_rhs,
)


def _is_pretty_platform_blob(blob: str) -> bool:
    """Maps raw slugs to WhatsApp / Gmail (not a raw `whatsapp` fallback)."""
    if not (_PRETTY_WHATSAPP.search(blob) and _PRETTY_GMAIL.search(blob)):
        return False
    return bool(_RAW_WHATSAPP.search(blob) and _RAW_GMAIL.search(blob))


def _pretty_platform_helpers(logic: str) -> set[str]:
    names: set[str] = set()
    for name in _CONV_LABEL_HELPER_NAMES:
        blob = _helper_with_callees(logic, name)
        if blob and _is_pretty_platform_blob(blob):
            names.add(name)
    return names


def _compares_title_to_person(blob: str) -> bool:
    if not re.search(r"\bpersonTitle\b", blob):
        return False
    if _TITLE_EQ_PERSON.search(blob):
        return True
    # `person = personTitle` then `title === person`
    return bool(
        re.search(
            r"(?:[\w$]+(?:\?\.|\.))*title\b[^;\n]{0,48}(?:===?|!==?)",
            blob,
        )
    )


def _blob_chooses_pretty_platform(blob: str, pretty_names: set[str]) -> bool:
    """Empty title or title === personTitle → pretty platform; else title."""
    if not _compares_title_to_person(blob):
        return False
    if not _EMPTY_TITLE.search(blob):
        return False
    if not _DISTINCT_TITLE.search(blob):
        return False
    uses_pretty = any(re.search(rf"\b{re.escape(n)}\s*\(", blob) for n in pretty_names)
    if uses_pretty or _is_pretty_platform_blob(blob):
        return True
    return bool(_PRETTY_WHATSAPP.search(blob) and _PRETTY_GMAIL.search(blob))


def _conversation_chooser_helpers(logic: str) -> dict[str, str]:
    """Named helpers that pick pretty platform vs a distinct title."""
    pretty = _pretty_platform_helpers(logic)
    found: dict[str, str] = {}
    for name in _CONV_LABEL_HELPER_NAMES:
        blob = _helper_with_callees(logic, name)
        if blob and _blob_chooses_pretty_platform(blob, pretty | {name}):
            found[name] = blob
    return found


def _closed_switcher_label_markup(tag: str, inner: str) -> str:
    if _tag_name(tag) == "select" or _CONV_SELECT.search(tag):
        return inner
    sm = re.search(r"<summary\b[^>]*>([\s\S]*?)</summary>", inner, re.I)
    if sm:
        return sm.group(1)
    each = _CONV_EACH.search(inner)
    if each:
        return inner[: each.start()]
    bm = re.search(r"<button\b[^>]*>([\s\S]*?)</button>", inner, re.I)
    if bm:
        return bm.group(1)
    return inner


def _switcher_summary_markup(crate: Path) -> str:
    parts: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        text = p.read_text()
        for m in _CONV_SWITCHER_HOOK.finditer(text):
            el = _element_span(text, m.start())
            if not el:
                window = text[max(0, m.start() - 80) : m.end() + 900]
                sm = re.search(r"<summary\b[^>]*>([\s\S]*?)</summary>", window, re.I)
                if sm:
                    parts.append(sm.group(1))
                continue
            _lt, tag, inner = el
            parts.append(_closed_switcher_label_markup(tag, inner))
        if not parts:
            for m in _CONV_SELECT.finditer(text):
                el = _element_span(text, m.start())
                if el:
                    parts.append(el[2])
    return "\n".join(parts)


def _switcher_row_markup(crate: Path) -> str:
    parts: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        text = p.read_text()
        i = 0
        while True:
            m = _CONV_EACH.search(text, i)
            if not m:
                break
            end = _matching_each_end(text, m.start())
            if end < 0:
                break
            parts.append(text[m.start() : end])
            i = end
    return "\n".join(parts)


def _strip_switcher_subtitles(block: str) -> str:
    prev = None
    out = block
    while prev != out:
        prev = out
        out = _SUBTITLE_EL.sub("", out)
    return out


def _heading_exprs(markup: str) -> list[str]:
    """Visible heading mustaches (not {#if}, not All, not last_at subtitle)."""
    cleaned = _strip_switcher_subtitles(markup)
    cleaned = _strip_tag_attrs(cleaned)
    cleaned = re.sub(r"\{[#/:@].*?\}", "", cleaned, flags=re.S)
    cleaned = re.sub(r">\s*All\s*<|[\"']All[\"']", "", cleaned)
    return [m.group(1).strip() for m in re.finditer(r"\{([^{}]+)\}", cleaned)]


def _expr_with_defs(expr: str, logic: str, depth: int = 0) -> str:
    if depth > 4:
        return expr
    parts = [expr]
    skip = _SCROLL_HELPER_SKIP | {
        "conv",
        "c",
        "title",
        "platform",
        "personTitle",
        "null",
        "undefined",
        "true",
        "false",
    }
    for ident in re.findall(r"\b([A-Za-z_]\w*)\b", expr):
        if ident in skip:
            continue
        rhs = _assignment_rhs(logic, ident)
        if rhs:
            parts.append(rhs)
            parts.append(_expr_with_defs(rhs, logic, depth + 1))
    return "\n".join(parts)


def _uses_named_helper(blob: str, names: set[str] | dict[str, str]) -> bool:
    return any(re.search(rf"\b{re.escape(n)}\s*\(", blob) for n in names)


def _is_raw_title_heading(expr: str, logic: str, choosers: dict[str, str]) -> bool:
    s = expr.strip()
    s = re.sub(r"\s*\?\?\s*[\"']{2}\s*$", "", s).strip()
    s = re.sub(r"\s*\|\|\s*[\"']{2}\s*$", "", s).strip()
    if _RAW_TITLE_HEADING.match(s):
        return True
    if re.fullmatch(r"selectedConversationTitle|conversation_title", s):
        rhs = _assignment_rhs(logic, s)
        if rhs and _uses_named_helper(rhs, choosers):
            return False
        if rhs and _blob_chooses_pretty_platform(rhs, _pretty_platform_helpers(logic)):
            return False
        return True
    return False


def _headings_use_label_helper(
    exprs: list[str],
    logic: str,
    choosers: dict[str, str],
    pretty: set[str],
) -> bool:
    """True if the heading calls the chooser (or inlines empty/name → pretty)."""
    if not exprs:
        return False
    if all(_is_raw_title_heading(e, logic, choosers) for e in exprs):
        return False
    blobs = [_expr_with_defs(e, logic) for e in exprs]
    combined = "\n".join(blobs)
    if choosers and _uses_named_helper(combined, choosers):
        return True
    return _blob_chooses_pretty_platform(combined, pretty)

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

__all__ = [
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
    "__all__",
]
