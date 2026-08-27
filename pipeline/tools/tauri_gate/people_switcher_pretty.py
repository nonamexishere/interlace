"""Helpers extracted from people_switcher_label.py (people_switcher_pretty)."""
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




# #114 — conversation switcher (title + platform + last_at); default All; no raw ids.
_CONV_EACH = re.compile(
    r"\{#each\s+"
    r"(?:(?:[\w.$]+)?conversations|convos|personConversations|"
    r"conversationList|convList|visibleConversations|filteredConversations)\b"
)
_CONV_SWITCHER_HOOK = re.compile(
    r"(data-conversation-switcher|id=[\"']conversation-switcher[\"'])",
    re.I,
)
_CONV_SELECT = re.compile(
    r"<select\b[^>]{0,400}(conversation|convo)",
    re.I | re.S,
)
_CONV_STATE_DEFAULT_ALL = re.compile(
    r"(?:selectedConversation(?:Id)?|conversationId|conversationFilter|"
    r"selectedConvo|activeConversation|pickedConversation)"
    r"\s*=\s*\$state\s*(?:<[^>]*>)?\s*\(\s*(?:null|undefined|[\"']all[\"'])",
    re.I,
)
_CONV_RESET_ALL = re.compile(
    r"(?:selectedConversation(?:Id)?|conversationId|conversationFilter|"
    r"selectedConvo|activeConversation|pickedConversation)"
    r"\s*=\s*(?:null|undefined|[\"']all[\"'])",
    re.I,
)
_CONV_ALL_LABEL = re.compile(r">\s*All\s*<|[\"']All[\"']")
_CONV_TITLE = re.compile(r"(conversation_title|\.title\b|\{[^}]{0,80}\btitle\b[^}]{0,40}\})")
# #114 dogfood — label helper (pretty platform when title is empty / the person).
_CONV_LABEL_HELPER_NAMES = (
    "conversationLabel",
    "switcherLabel",
    "platformLabel",
    "convLabel",
    "conversationHeading",
    "switcherHeading",
)
_RAW_GMAIL = re.compile(r"[\"']gmail[\"']")
_TITLE_EQ_PERSON = re.compile(
    r"("
    r"(?:[\w$]+(?:\?\.|\.))*title\b[^;\n]{0,48}(?:===?|!==?)[^;\n]{0,48}"
    r"(?:personTitle|personName|displayName|display_name)\b"
    r"|(?:personTitle|personName|displayName|display_name)\b[^;\n]{0,48}"
    r"(?:===?|!==?)[^;\n]{0,48}(?:[\w$]+(?:\?\.|\.))*title\b"
    r")"
)
_EMPTY_TITLE = re.compile(
    r"("
    r"!\s*(?:[\w$]+(?:\?\.|\.))*title\b"
    r"|(?:[\w$]+(?:\?\.|\.))*title\b[^;\n]{0,40}(?:===?|!==?)\s*[\"']{2}"
    r"|(?:[\w$]+(?:\?\.|\.))*title\b\s*\?\?"
    r"|(?:[\w$]+(?:\?\.|\.))*title\b\s*\|\|"
    r"|(?:[\w$]+(?:\?\.|\.))*title\b[^;\n]{0,24}\.trim\s*\("
    r")"
)
_DISTINCT_TITLE = re.compile(
    r"("
    r"return\s+(?:[\w$]+(?:\?\.|\.))*title\b"
    r"|:\s*(?:[\w$]+(?:\?\.|\.))*title\b"
    r")"
)
_RAW_TITLE_HEADING = re.compile(
    r"^(?:[\w$]+(?:\?\.|\.))*title(?:\s*\?\?\s*[\"']{2})?(?:\s*\|\|\s*[\"']{2})?$"
)
_SUBTITLE_EL = re.compile(
    r"<(span|div|p|small|time)\b[^>]*>"
    r"(?:(?!</\1>).)*\b(?:last_at|lastAt|last_activity_at)\b"
    r"(?:(?!</\1>).)*</\1>",
    re.I | re.S,
)
_CONV_PLATFORM = re.compile(r"\bplatform\b")
_CONV_LAST_AT = re.compile(r"\b(?:last_at|lastAt|last_activity_at)\b")
_CONV_ID_TEXT = re.compile(
    r"\{[^}]{0,80}(?:conversation_id|\.id|person_id|personId|selectedId)[^}]{0,40}\}"
)
_CONV_ID_FALLBACK = re.compile(
    r"(?:conversation_title|\.title|title)\s*\|\|\s*[^\n;]{0,80}"
    r"(?:conversation_id|\.id|person_id|personId)\b"
)
_CONV_PICK = re.compile(
    r"("
    r"(?:onclick|onchange|on:click|on:change)\s*=\s*\{[^}]{0,200}"
    r"(?:conversation|convo|Conversation|Convo)"
    r"|bind:value=\{[^}]{0,80}(?:conversation|convo|Conversation|Convo)"
    r")",
    re.I,
)
_CONV_CREATE = re.compile(r"Create conversation|New conversation", re.I)
_CONV_MUTE = re.compile(r">\s*Mute\s*<")
_CONV_PIN = re.compile(r">\s*(?:Un)?[Pp]in\s*<")
_PERSON_TIMELINE_CALL = re.compile(r"\bpersonTimeline\s*\(")

# #114 dogfood — identity chrome + compact switcher (chat must not sit under admin).
# All / the open panel stack above sticky .day-heading (z-index + background).
_MERGE_CTRL = re.compile(r">\s*Merge(?:…|\.{3})?\s*<")
_UNLINK_CTRL = re.compile(r">\s*unlink\s*<", re.I)
_GROUPS_BIND = re.compile(r"bind:checked=\{includeGroups\}")
_GROUPS_LABEL_CTRL = re.compile(
    r"<label\b[^>]*>[\s\S]{0,240}include groups[\s\S]{0,80}</label>",
    re.I,
)
_CLICK_ATTR = re.compile(r"(?:on:click|onclick)(?:\|\w+)*\s*=\s*\{", re.I)
_HIDDEN_BIND = re.compile(
    r"(?:\bhidden|class:hidden|aria-hidden)\s*=\s*\{",
    re.I,
)
_TITLE_SKIP_ASSIGN = frozenset(
    {
        "selectedId",
        "selectedConversationId",
        "view",
        "err",
        "mergeOpen",
        "mergeQuery",
        "mergeKeepId",
        "mergeKeepName",
        "allowSelf",
        "filter",
        "tlIndex",
        "tlLoading",
        "setup",
        "booting",
        "opening",
    }
)
# Sticky .day-heading is z-index 10; All / the open panel must sit above it.
_TW_Z_INDEX = re.compile(r"(?<![\w-])z-(?:\[(\d+)\]|(\d+))(?![\w-])")
_CSS_Z_INDEX = re.compile(r"z-index\s*:\s*(\d+)", re.I)
_CLASS_Z_DIR = re.compile(r"\bclass:z-(\d+)\b")
_TW_STACK_BG = re.compile(
    r"(?<![\w-])((?:(?:group-)?(?:hover|focus|active|focus-visible):)*)"
    r"(bg-(?:background|card|popover|muted|white|black|primary|secondary|accent)"
    r"|bg-\[var\(--color-(?:background|card|popover|muted)\)\])"
    r"(?:/(\d+))?(?![\w-])",
    re.I,
)
_CSS_STACK_BG = re.compile(
    r"background(?:-color)?\s*:\s*(?!none\b|transparent\b)(\S)",
    re.I,
)
_TIMELINE_INNER = re.compile(
    r"(id=[\"']person-timeline[\"']|day-heading|"
    r"\{#each\s+(?:timeline|dayGroups|windowed(?:Day)?Groups|visible(?:Day)?Groups|"
    r"virtual(?:Day)?Groups|rendered(?:Day)?Groups|windowedRows|visibleRows|"
    r"virtualRows|renderedRows|windowedTimeline|visibleTimeline)\b)",
    re.I,
)
_DAY_HEADING_CSS = re.compile(
    r"(?:\.day-heading\b|\.day-separator\b|\.day-sep\b|\[data-day-heading\])[^{]*\{([^}]+)\}",
    re.I,
)


def _without_calls(src: str, rx: re.Pattern[str]) -> str:
    """Blank out `name(` … matching `)` so a later search ignores those args."""
    out: list[str] = []
    i = 0
    for m in rx.finditer(src):
        out.append(src[i : m.start()])
        close = _match_closer(src, m.end() - 1)
        i = (close + 1) if close >= 0 else m.end()
    out.append(src[i:])
    return "".join(out)


def _strip_tag_attrs(block: str) -> str:
    """Leave element text / mustaches; drop attributes (data-id={c.id} is not visible)."""
    no_mustache_attr = re.sub(
        r"\s+[A-Za-z_:][\w:.-]*\s*=\s*\{(?:[^{}]|\{[^{}]*\})*\}",
        "",
        block,
    )
    no_quoted_attr = re.sub(
        r"\s+[A-Za-z_:][\w:.-]*\s*=\s*(?:\"[^\"]*\"|'[^']*')",
        "",
        no_mustache_attr,
    )
    return no_quoted_attr


def _visible_switcher_text(block: str) -> str:
    """User-visible switcher text. Each keys and {#if} tests are not shown."""
    no_attrs = _strip_tag_attrs(block)
    return re.sub(r"\{[#/:@].*?\}", "", no_attrs, flags=re.S)


def _conversation_switcher_blocks(crate: Path) -> list[str]:
    """Conversation list/select chrome — not the people sidebar, not chat bubbles."""
    found: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte":
            continue
        text = p.read_text()
        for m in _CONV_SWITCHER_HOOK.finditer(text):
            found.append(text[max(0, m.start() - 200) : m.end() + 900])
        i = 0
        while True:
            m = _CONV_EACH.search(text, i)
            if not m:
                break
            end = _matching_each_end(text, m.start())
            if end < 0:
                fail(f"#114: unclosed conversation {{#each}} in {p.relative_to(crate)}")
            found.append(text[m.start() : end])
            i = end
        for m in re.finditer(r"<select\b[^>]*>.*?</select>", text, re.I | re.S):
            chunk = m.group(0)
            if re.search(r"conversation|convo", chunk, re.I):
                found.append(chunk)
    return found


def _is_vacuous_chrome_cond(cond: str) -> bool:
    """selectedId / personTitle / true is not 'user opened identity chrome'."""
    parts = re.split(r"&&|\|\|", cond)
    if not parts:
        return True
    for raw in parts:
        p = raw.strip().strip("()")
        p = re.sub(r"^\s*!!?", "", p).strip()
        if re.fullmatch(r"true|1", p, re.I):
            continue
        if re.fullmatch(r"personTitle", p):
            continue
        if re.fullmatch(
            r"(?:selectedId|selectedPerson|identities\.length(?:\s*[><!=]=?\s*0)?"
            r"|personById\s*\([^)]*\)|st|setup|booting|opening"
            r"|view\s*===\s*[\"']\w+[\"'])",
            p,
        ):
            continue
        if re.fullmatch(r"selectedId\s*(?:!=|!==|==|===)\s*(?:null|undefined)", p):
            continue
        return False
    return True


def _details_always_open(attrs: str) -> bool:
    if re.search(r"\bbind:open\b|\bopen\s*=\s*\{", attrs):
        return False
    return bool(re.search(r"\bopen\b", attrs))


def _title_flags(expr: str, whole: str, seen: set[str] | None = None) -> set[str]:
    found = seen if seen is not None else set()
    flags = {a for a in _assigned_idents(expr) if a not in _TITLE_SKIP_ASSIGN}
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", expr):
        name = m.group(1)
        if name in found or name in _SCROLL_HELPER_SKIP or name in _TITLE_SKIP_ASSIGN:
            continue
        found.add(name)
        body = _function_body(whole, name)
        if body:
            flags |= _title_flags(body, whole, found)
    return flags


def _is_title_wrapper(tag: str) -> bool:
    name_m = re.match(r"<([\w.]+)", tag)
    if not name_m:
        return False
    name = name_m.group(1).lower()
    if name in {"button", "summary", "h1", "a"}:
        return True
    return bool(re.search(r"personTitle|person-title|data-person-title", tag))

from tauri_gate.people_switcher_pretty_rest import (
    _click_expr,
    _person_title_pos,
    _identity_title_toggle,
    _hidden_flags_before,
    _chrome_hidden_by_default,
    _chrome_toggled_by_title,
    _flag_default_open,
    _person_chrome_markup,
    _person_pane_markups,
    _groups_ctrl_pos,
    _is_compact_enclosure,
    _always_expanded_conversation_list,
    __all__,
)

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
