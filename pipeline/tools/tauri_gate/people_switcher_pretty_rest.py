"""Continuation of people_switcher_pretty."""
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
    _GROUPS_BIND,
    _GROUPS_LABEL_CTRL,
    _CLICK_ATTR,
    _HIDDEN_BIND,
    _TITLE_SKIP_ASSIGN,
    _is_vacuous_chrome_cond,
    _details_always_open,
    _title_flags,
    _is_title_wrapper,
)


def _click_expr(tag: str) -> str:
    m = _CLICK_ATTR.search(tag)
    if not m:
        return ""
    open_i = m.end() - 1
    close = _match_closer(tag, open_i)
    if close < 0:
        return ""
    return tag[open_i + 1 : close]


def _person_title_pos(markup: str) -> int:
    for pat in (
        "{personTitle}",
        'id="personTitle"',
        "id='personTitle'",
        'class="personTitle"',
        "data-person-title",
        "person-title",
    ):
        i = markup.find(pat)
        if i >= 0:
            return i
    return markup.find("personTitle")


def _identity_title_toggle(markup: str, whole: str) -> tuple[set[str], bool]:
    """Flags assigned by clicking the person title, and whether the title is a <summary>."""
    pos = _person_title_pos(markup)
    if pos < 0:
        return set(), False
    tags = _ancestor_tags(markup, pos)
    candidates: list[str] = []
    if tags:
        candidates.append(tags[0])
        for tag in tags[1:]:
            if _is_title_wrapper(tag):
                candidates.append(tag)
    title_in_summary = any(re.match(r"<summary\b", t, re.I) for t in candidates)
    flags: set[str] = set()
    for tag in candidates:
        expr = _click_expr(tag)
        if expr:
            flags |= _title_flags(expr, whole)
            break
    return flags, title_in_summary


def _hidden_flags_before(markup: str, pos: int) -> set[str]:
    window = markup[max(0, pos - 500) : pos]
    flags: set[str] = set()
    skip = _TITLE_SKIP_ASSIGN | {
        "hidden",
        "true",
        "false",
        "null",
        "undefined",
        "class",
        "aria",
    }
    exprs: list[str] = []
    for m in _HIDDEN_BIND.finditer(window):
        close = _match_closer(window, m.end() - 1)
        if close >= 0:
            exprs.append(window[m.end() : close])
    for m in re.finditer(r"\bclass\s*=\s*\{", window, re.I):
        close = _match_closer(window, m.end() - 1)
        if close < 0:
            continue
        expr = window[m.end() : close]
        if "hidden" in expr.lower():
            exprs.append(expr)
    for expr in exprs:
        for ident in re.findall(r"\b([A-Za-z_]\w*)\b", expr):
            if ident not in skip:
                flags.add(ident)
    return flags


def _chrome_hidden_by_default(markup: str, pos: int) -> bool:
    for kind, a, b in _template_stack(markup, pos):
        if kind == "if" and not _is_vacuous_chrome_cond(a):
            return True
        if kind == "tag" and a.lower() == "details" and not _details_always_open(b):
            return True
    return bool(_hidden_flags_before(markup, pos))


def _chrome_toggled_by_title(
    markup: str, pos: int, flags: set[str], title_in_summary: bool
) -> bool:
    for kind, a, b in _template_stack(markup, pos):
        if kind == "if" and flags and _cond_uses_flag(a, flags):
            return True
        if kind == "tag" and a.lower() == "details" and not _details_always_open(b):
            if title_in_summary:
                return True
            if flags and _cond_uses_flag(b, flags):
                return True
    hidden_fs = _hidden_flags_before(markup, pos)
    return bool(flags and hidden_fs & flags)


def _flag_default_open(logic: str, name: str) -> bool:
    m = re.search(
        rf"\b(?:let|const|var)\s+{re.escape(name)}\s*=\s*"
        rf"(?:\$state\s*(?:<[^>]*>)?\s*\(\s*)?([^\n;)]+)",
        logic,
    )
    if not m:
        return False
    val = m.group(1).strip().rstrip(")").strip()
    return val in {"true", "1", '"open"', "'open'"} or val.startswith("true")


def _person_chrome_markup(text: str) -> str:
    """Person column, including the title open tag (h1 / button / summary onclick)."""
    idx = text.find("{personTitle}")
    if idx < 0:
        idx = text.find("data-conversation-switcher")
    if idx < 0:
        return _person_detail_markup(text)
    # Look back far enough for a wrapping <button>/<summary>/<details>, not to {#if st}.
    start = max(0, idx - 600)
    end = text.find("Bodies are text", idx)
    if end > start:
        return text[start:end]
    return text[start:]


def _person_pane_markups(crate: Path) -> list[str]:
    found: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        text = p.read_text()
        if not (
            "{personTitle}" in text
            or "data-conversation-switcher" in text
            or "openMerge" in text
        ):
            continue
        found.append(_person_chrome_markup(text))
    return found


def _groups_ctrl_pos(detail: str) -> int:
    m = _GROUPS_BIND.search(detail)
    if m:
        return m.start()
    m = _GROUPS_LABEL_CTRL.search(detail)
    if m and re.search(r"<input\b", m.group(0), re.I):
        return m.start()
    return -1


def _is_compact_enclosure(stack: list[tuple[str, str, str]], logic: str = "") -> bool:
    compact_parts = {
        "select",
        "details",
        "popover",
        "dropdownmenu",
        "dropdown",
        "combobox",
        "menu",
    }
    for kind, a, b in stack:
        if kind == "tag":
            parts = a.lower().split(".")
            if any(p in compact_parts for p in parts):
                if "details" in parts and _details_always_open(b):
                    continue
                return True
        if kind == "if" and not _is_vacuous_chrome_cond(a):
            ident = a.strip()
            if ident.isidentifier() and _flag_default_open(logic, ident):
                continue
            return True
    return False


def _always_expanded_conversation_list(crate: Path, logic: str = "") -> bool:
    """True if {#each conversations} is a second always-visible list, not a compact control."""
    for pane in _person_pane_markups(crate):
        for m in _CONV_EACH.finditer(pane):
            if _is_compact_enclosure(_template_stack(pane, m.start()), logic):
                continue
            return True
    return False

__all__ = [
    "_CONV_EACH",
    "_CONV_SWITCHER_HOOK",
    "_CONV_SELECT",
    "_CONV_STATE_DEFAULT_ALL",
    "_CONV_RESET_ALL",
    "_CONV_ALL_LABEL",
    "_CONV_TITLE",
    "_CONV_LABEL_HELPER_NAMES",
    "_RAW_GMAIL",
    "_TITLE_EQ_PERSON",
    "_EMPTY_TITLE",
    "_DISTINCT_TITLE",
    "_RAW_TITLE_HEADING",
    "_SUBTITLE_EL",
    "_CONV_PLATFORM",
    "_CONV_LAST_AT",
    "_CONV_ID_TEXT",
    "_CONV_ID_FALLBACK",
    "_CONV_PICK",
    "_CONV_CREATE",
    "_CONV_MUTE",
    "_CONV_PIN",
    "_PERSON_TIMELINE_CALL",
    "_MERGE_CTRL",
    "_UNLINK_CTRL",
    "_GROUPS_BIND",
    "_GROUPS_LABEL_CTRL",
    "_CLICK_ATTR",
    "_HIDDEN_BIND",
    "_TITLE_SKIP_ASSIGN",
    "_TW_Z_INDEX",
    "_CSS_Z_INDEX",
    "_CLASS_Z_DIR",
    "_TW_STACK_BG",
    "_CSS_STACK_BG",
    "_TIMELINE_INNER",
    "_DAY_HEADING_CSS",
    "_without_calls",
    "_strip_tag_attrs",
    "_visible_switcher_text",
    "_conversation_switcher_blocks",
    "_is_vacuous_chrome_cond",
    "_details_always_open",
    "_title_flags",
    "_is_title_wrapper",
    "_click_expr",
    "_person_title_pos",
    "_identity_title_toggle",
    "_hidden_flags_before",
    "_chrome_hidden_by_default",
    "_chrome_toggled_by_title",
    "_flag_default_open",
    "_person_chrome_markup",
    "_person_pane_markups",
    "_groups_ctrl_pos",
    "_is_compact_enclosure",
    "_always_expanded_conversation_list",
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
]

__all__ = [
    "_click_expr",
    "_person_title_pos",
    "_identity_title_toggle",
    "_hidden_flags_before",
    "_chrome_hidden_by_default",
    "_chrome_toggled_by_title",
    "_flag_default_open",
    "_person_chrome_markup",
    "_person_pane_markups",
    "_groups_ctrl_pos",
    "_is_compact_enclosure",
    "_always_expanded_conversation_list",
    "__all__",
]
