"""Helpers extracted from keyboard.py (keyboard_lib)."""
from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _A11Y_ROLE_OPTION,
    _A11Y_TABINDEX_NEG,
    _expand_fn_calls,
    _function_body,
    _KEYMAP_CALL_SKIP,
    _MOD_EITHER,
    _search_pane_blob,
    _strip_html_comments,
    _svelte_markup,
    _ts_fn_body,
    _VIEW_SEARCH_ASSIGN,
    _web_logic,
    _web_sources,
    _without_comments,
    CSP,
)

from tauri_gate.a11y_lib import (
    _A11Y_ROLE_LISTBOX,
    _people_each_block,
    _people_list_a11y_surfaces,
)

from tauri_gate.import_boot_guards import (
    _app_keydown_body,
    _input_guard_span,
)

from tauri_gate.status_toasts_chrome import (
    _FOCUS_SEARCH_Q,
    _KEY_ESC,
    _has_mod_combo,
    _split_people_only,
    _windows_around,
    _without_input_guard,
)
from tauri_gate.status_toasts_toast import _KEY_F



_KEY_SLASH = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']/[\"']"
    r"|[\"']/[\"']\s*===?\s*(?:e\.)?key"
    r")",
)
_KEY_J = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']j[\"']|[\"']j[\"']\s*===?\s*(?:e\.)?key"
)
_KEY_K = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']k[\"']|[\"']k[\"']\s*===?\s*(?:e\.)?key"
)
_FOCUS_PERSON_FILTER = re.compile(
    r"("
    r"getElementById\s*\(\s*[\"']person-filter[\"']"
    r"|querySelector\s*\(\s*[\"']#person-filter[\"']"
    r"|#person-filter"
    r")",
)
_VIEW_PEOPLE_ASSIGN = re.compile(r"\bview\s*=\s*[\"']people[\"']")
_INPUT_TAG_GUARD = re.compile(
    r"tagName\s*===?\s*[\"']INPUT[\"']"
    r".{0,160}tagName\s*===?\s*[\"']TEXTAREA[\"']"
    r".{0,160}tagName\s*===?\s*[\"']SELECT[\"']"
    r"|tagName\s*===?\s*[\"']INPUT[\"']"
    r".{0,80}[\"']TEXTAREA[\"']"
    r".{0,80}[\"']SELECT[\"']",
    re.S,
)
_INPUT_BLUR = re.compile(r"\.blur\s*\(\s*\)")
_PREVENT_DEFAULT = re.compile(r"preventDefault\s*\(")
_DIGIT_KEY = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"'][1-5][\"']"
    r"|(?:e\.)?code\s*===?\s*[\"']Digit[1-5][\"']"
    r"|(?:e\.)?key\s*>=\s*[\"']1[\"']"
    r"|(?:e\.)?key\s*<=\s*[\"']5[\"']"
    r"|Number\s*\(\s*(?:e\.)?key"
    r"|parseInt\s*\(\s*(?:e\.)?key"
    r")"
)
_VIEW_TAB_ORDER = ("people", "search", "review", "import", "doctor")
_VIM_COLON = re.compile(r"(?:e\.)?key\s*===?\s*[\"']:[\"']|[\"']:[\"']\s*===?\s*(?:e\.)?key")
_VIM_COMMAND = re.compile(
    r"("
    r"[\"']:w[\"']"
    r"|[\"']:q[\"']"
    r"|[\"']:wq[\"']"
    r"|\bvimMode\b"
    r"|\bvim-mode\b"
    r"|\bcustomKeybindings\b"
    r")",
    re.I,
)
_ESC_CLOSE_APP = re.compile(
    r"("
    r"getCurrentWindow\s*\(\s*\)\s*\.\s*close\s*\("
    r"|window\s*\.\s*close\s*\("
    r"|app(?:Window)?\s*\.\s*close\s*\("
    r"|app\.exit\s*\("
    r"|process\.exit\s*\("
    r")"
)
_KEYBIND_NAMES = frozenset(
    {
        "keybindings.json",
        "keybindings.toml",
        "key-bindings.json",
        "keymaps.json",
    }
)


def _esc_sets_view_people(src: str, whole: str) -> bool:
    """True if an Escape check outside the input guard assigns view = \"people\"."""
    for m in _KEY_ESC.finditer(src):
        window = src[m.start() : m.end() + 400]
        if _VIEW_PEOPLE_ASSIGN.search(window):
            return True
        for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", window):
            if name in _KEYMAP_CALL_SKIP:
                continue
            inner = _ts_fn_body(whole, name) or _function_body(whole, name)
            if inner and _VIEW_PEOPLE_ASSIGN.search(inner):
                return True
    return False


def _digit_view_map_ok(surface: str) -> bool:
    """True if digit 1..5 map to people/search/review/import/doctor."""
    if not _DIGIT_KEY.search(surface):
        return False
    # Ordered array / tuple used as the tab list.
    joined = r"[\"']people[\"']\s*,\s*[\"']search[\"']\s*,\s*[\"']review[\"']\s*,\s*[\"']import[\"']\s*,\s*[\"']doctor[\"']"
    if re.search(joined, surface):
        return True
    # Object / switch / per-key assigns.
    pairs = (
        (r"[\"']1[\"']|Digit1", "people"),
        (r"[\"']2[\"']|Digit2", "search"),
        (r"[\"']3[\"']|Digit3", "review"),
        (r"[\"']4[\"']|Digit4", "import"),
        (r"[\"']5[\"']|Digit5", "doctor"),
    )
    for digit_rx, view in pairs:
        if not re.search(
            rf"(?:{digit_rx})[\s\S]{{0,220}}[\"']{view}[\"']"
            rf"|[\"']{view}[\"'][\s\S]{{0,220}}(?:{digit_rx})",
            surface,
        ):
            return False
    return True


# #214 — keyboard map: list arrows, roving tabindex, tab path, no trap.
_KEY_ARROW_DOWN = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']ArrowDown[\"']"
    r"|[\"']ArrowDown[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?code\s*===?\s*[\"']ArrowDown[\"']"
    r")"
)
_KEY_ARROW_UP = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']ArrowUp[\"']"
    r"|[\"']ArrowUp[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?code\s*===?\s*[\"']ArrowUp[\"']"
    r")"
)
_KEY_ARROW_EITHER = re.compile(
    r"("
    + _KEY_ARROW_DOWN.pattern
    + r"|"
    + _KEY_ARROW_UP.pattern
    + r")"
)
_LIST_FOCUS = re.compile(
    r"("
    r"(?:closest|matches|querySelector)[\s?.]*\(\s*[^)]{0,120}(?:option|listbox)"
    r"|getAttribute\s*\(\s*[\"']role[\"']\s*\)\s*===?\s*[\"'](?:option|listbox)[\"']"
    r"|\.role\s*===?\s*[\"'](?:option|listbox)[\"']"
    r"|\[role\s*=\s*[\\'\"]?(?:option|listbox)"
    r"|data-people-(?:listbox|option)"
    r")",
    re.I,
)
_LIST_SELECT_PERSON = re.compile(r"\bselectPerson\s*\(")
_FILTERED_LIST = re.compile(r"\bfiltered\b")
_LIST_NEXT_PREV = re.compile(
    r"("
    r"findIndex"
    r"|indexOf"
    r"|\+\s*1"
    r"|-\s*1"
    r"|nextPerson"
    r"|prevPerson"
    r"|nextIndex"
    r"|prevIndex"
    r")"
)
_TABINDEX_ATTR = re.compile(r"\btab(?:[Ii]ndex)\s*=", re.I)
_TABINDEX_DYNAMIC = re.compile(r"\btab(?:[Ii]ndex)\s*=\s*\{", re.I)
_TABINDEX_ZERO = re.compile(
    r"\btab(?:[Ii]ndex)\s*=\s*(?:[\"']0[\"']|\{0\}|\{[^}]{0,240}(?:\b0\b|[\"']0[\"']))",
    re.I,
)
_TABINDEX_NEG1 = re.compile(
    r"\btab(?:[Ii]ndex)\s*=\s*(?:[\"']-1[\"']|\{-1\}|\{[^}]{0,240}(?:-1|[\"']-1[\"']))",
    re.I,
)
_OPEN_OTHER_ARCHIVE = re.compile(r"Open other archive", re.I)
_DOCS_LIST_ARROWS = re.compile(
    r"("
    r"(?:arrow\s*keys?|arrows|ArrowDown|ArrowUp).{0,120}"
    r"(?:people|listbox|person)"
    r"|(?:people|listbox|person).{0,100}"
    r"(?:arrow\s*keys?|arrows)"
    r"|arrows?.{0,80}change.{0,60}person"
    r")",
    re.I | re.S,
)
_DOCS_TAB_PATH = re.compile(
    r"("
    r"Tab.{0,140}(?:filter|#person-filter).{0,100}(?:selected )?person.{0,80}timeline"
    r"|(?:filter|#person-filter).{0,80}(?:selected )?person.{0,80}timeline"
    r"|filter\s*→\s*(?:the\s+)?(?:selected\s+)?person\s*→\s*timeline"
    r"|filter\s*->\s*(?:the\s+)?(?:selected\s+)?person\s*->\s*timeline"
    r")",
    re.I | re.S,
)
_DOCS_JK_MESSAGES = re.compile(
    r"("
    r"[`']?j[`']?\s*/\s*[`']?k[`']?.{0,50}(?:message|timeline)"
    r"|[`']?j[`']?.{0,10}[`']?k[`']?.{0,50}(?:message|timeline)"
    r")",
    re.I | re.S,
)
_DOCS_Q_SAFE = re.compile(
    r"("
    r"(?:#q|Search).{0,120}(?:never intercept|not intercept|is never intercepted)"
    r"|typing.{0,60}(?:Search|#q).{0,80}(?:never|not)\s+intercept"
    r"|letter shortcuts.{0,80}(?:ignored|not applied).{0,60}field"
    r")",
    re.I | re.S,
)
_LIST_ARROW_EXPAND_SKIP = _KEYMAP_CALL_SKIP | frozenset(
    {
        "selectPerson",
        "ensureTlIndexVisible",
        "nearestVisibleTlIndex",
    }
)


def _expand_list_arrow_calls(src: str, body: str, depth: int = 2) -> str:
    """Include named callees, but not selectPerson (its body walks tlIndex)."""
    chunks = [body]
    seen: set[str] = set()

    def walk(blob: str, left: int) -> None:
        for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob):
            if name in seen or name in _LIST_ARROW_EXPAND_SKIP:
                continue
            seen.add(name)
            inner = _ts_fn_body(src, name) or _function_body(src, name)
            if not inner:
                continue
            chunks.append(inner)
            if left > 0:
                walk(inner, left - 1)

    walk(body, depth)
    return "\n".join(chunks)


def _arrow_key_windows(src: str, rx: re.Pattern[str]) -> list[str]:
    return [
        src[max(0, m.start() - 360) : m.end() + 860] for m in rx.finditer(src)
    ]


def _list_arrow_selects_person(body: str, whole: str, rx: re.Pattern[str]) -> bool:
    """True when this arrow key on a listbox/option calls selectPerson on filtered."""
    expanded = _expand_list_arrow_calls(whole, body)
    windows = _arrow_key_windows(expanded, rx) or _arrow_key_windows(body, rx)
    if not windows:
        return False
    has_list = bool(_LIST_FOCUS.search(expanded) or _LIST_FOCUS.search(body))
    if not has_list:
        return False
    for w in windows:
        w_x = _expand_list_arrow_calls(whole, w)
        if (
            _LIST_FOCUS.search(w_x)
            and _LIST_SELECT_PERSON.search(w_x)
            and _FILTERED_LIST.search(w_x)
            and _LIST_NEXT_PREV.search(w_x)
        ):
            return True
        # List-focus may sit just outside the per-key window (shared inList flag).
        if (
            has_list
            and _LIST_SELECT_PERSON.search(w_x)
            and _FILTERED_LIST.search(w_x)
            and _LIST_NEXT_PREV.search(w_x)
        ):
            return True
    return False


def _people_option_tags(people_each: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"<([A-Za-z][\w:-]*)\b", people_each):
        gt = people_each.find(">", m.start())
        if gt < 0:
            continue
        tag = people_each[m.start() : gt + 1]
        if re.search(r"role\s*=\s*[\"']option[\"']", tag, re.I):
            out.append(tag)
    return out


def _option_roving_tabindex_ok(people_each: str) -> bool:
    """Selected option tabindex 0 / {0}; others -1 / {-1}."""
    tags = _people_option_tags(people_each)
    blob = "\n".join(tags) if tags else people_each
    if not _TABINDEX_DYNAMIC.search(blob) and not (
        _TABINDEX_ZERO.search(blob) and _TABINDEX_NEG1.search(blob)
    ):
        return False
    if not _TABINDEX_ZERO.search(blob) or not _TABINDEX_NEG1.search(blob):
        return False
    if not re.search(
        r"selectedId|selected_id|selectedPerson|p\.id|person\.id|aria-selected",
        blob,
    ):
        return False
    return True


def _nearest_open_tag(src: str, pos: int) -> str:
    """Open tag immediately before pos (text-node label → its element)."""
    lt = src.rfind("<", 0, pos)
    if lt < 0:
        return ""
    gt = src.find(">", lt)
    if gt < 0:
        return ""
    return src[lt : gt + 1]


def _sidebar_chrome_untabbable(markup: str) -> bool:
    """Undo / Open other archive are not default-tabbable between filter and timeline."""
    fm = re.search(r"id\s*=\s*[\"']person-filter[\"']", markup)
    tl = re.search(r"id\s*=\s*[\"']person-timeline[\"']", markup)
    if not fm or not tl or tl.start() <= fm.start():
        return False
    mid = markup[fm.start() : tl.start()]
    needed: list[tuple[str, re.Pattern[str]]] = [
        ("undo", re.compile(r">\s*undo\s*<", re.I)),
        ("Open other archive", _OPEN_OTHER_ARCHIVE),
    ]
    for _label, rx in needed:
        hits = list(rx.finditer(mid))
        if not hits:
            # Control not between filter and timeline — tab path is already clear.
            continue
        for m in hits:
            tag = _nearest_open_tag(mid, m.start())
            if not tag or not re.search(r"<Button\b|<button\b", tag, re.I):
                # Walk back to the nearest Button/button.
                search = mid[: m.start()]
                bm = None
                for cand in re.finditer(r"<(?:Button|button)\b[^>]*>", search, re.I | re.S):
                    bm = cand
                if not bm:
                    return False
                tag = bm.group(0)
            if not _TABINDEX_NEG1.search(tag) and not _A11Y_TABINDEX_NEG.search(tag):
                return False
    return True


def _bare_letter_before_guard(pre: str, rx: re.Pattern[str]) -> bool:
    for m in rx.finditer(pre):
        window = pre[max(0, m.start() - 80) : m.end() + 40]
        if _MOD_EITHER.search(window):
            continue
        return True
    return False

__all__ = [
    "_KEY_SLASH",
    "_KEY_J",
    "_KEY_K",
    "_FOCUS_PERSON_FILTER",
    "_VIEW_PEOPLE_ASSIGN",
    "_INPUT_TAG_GUARD",
    "_INPUT_BLUR",
    "_PREVENT_DEFAULT",
    "_DIGIT_KEY",
    "_VIEW_TAB_ORDER",
    "_VIM_COLON",
    "_VIM_COMMAND",
    "_ESC_CLOSE_APP",
    "_KEYBIND_NAMES",
    "_esc_sets_view_people",
    "_digit_view_map_ok",
    "_KEY_ARROW_DOWN",
    "_KEY_ARROW_UP",
    "_KEY_ARROW_EITHER",
    "_LIST_FOCUS",
    "_LIST_SELECT_PERSON",
    "_FILTERED_LIST",
    "_LIST_NEXT_PREV",
    "_TABINDEX_ATTR",
    "_TABINDEX_DYNAMIC",
    "_TABINDEX_ZERO",
    "_TABINDEX_NEG1",
    "_OPEN_OTHER_ARCHIVE",
    "_DOCS_LIST_ARROWS",
    "_DOCS_TAB_PATH",
    "_DOCS_JK_MESSAGES",
    "_DOCS_Q_SAFE",
    "_LIST_ARROW_EXPAND_SKIP",
    "_expand_list_arrow_calls",
    "_arrow_key_windows",
    "_list_arrow_selects_person",
    "_people_option_tags",
    "_option_roving_tabindex_ok",
    "_nearest_open_tag",
    "_sidebar_chrome_untabbable",
    "_bare_letter_before_guard",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_A11Y_ROLE_OPTION",
    "_A11Y_TABINDEX_NEG",
    "_expand_fn_calls",
    "_MOD_EITHER",
    "_search_pane_blob",
    "_strip_html_comments",
    "_svelte_markup",
    "_VIEW_SEARCH_ASSIGN",
    "_web_logic",
    "_web_sources",
    "_without_comments",
    "CSP",
    "_A11Y_ROLE_LISTBOX",
    "_people_each_block",
    "_people_list_a11y_surfaces",
    "_app_keydown_body",
    "_input_guard_span",
    "_FOCUS_SEARCH_Q",
    "_KEY_ESC",
    "_KEY_F",
    "_has_mod_combo",
    "_split_people_only",
    "_windows_around",
    "_without_input_guard",
    "annotations",
    "_function_body",
    "_KEYMAP_CALL_SKIP",
    "_ts_fn_body",
]
