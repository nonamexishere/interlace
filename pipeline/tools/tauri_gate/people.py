"""People / conversation chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    CSP,
    _BODY_T_CALL,
    _CONFIG_TOML,
    _DATA_PEOPLE_SIDEBAR,
    _HUMAN_TIME_HELPERS,
    _INCLUDE_GROUPS_LABEL,
    _INSPECTOR_HOOK,
    _KEY_ESC,
    _LAST_PATH_API,
    _LS_BRACKET,
    _MIN_W0,
    _MOD_EITHER,
    _OVERFLOW_X_HIDDEN,
    _PEOPLE_AWAIT_REFRESH,
    _PEOPLE_EACH,
    _PERSON_PANE_SKIP,
    _PRETTY_GMAIL,
    _PRETTY_WHATSAPP,
    _RAW_WHATSAPP,
    _SCROLL_HELPER_SKIP,
    _TIMELINE_EACH_NAMES,
    _TMPL_TOKEN,
    _VOID_HTML,
    _ancestor_tags,
    _app_keydown_body,
    _assigned_idents,
    _assignment_gen_guarded,
    _call_arg,
    _chrome_helper_names,
    _chrome_helper_on_body,
    _cond_uses_flag,
    _expand_fn_calls,
    _function_body,
    _has_mod_combo,
    _helper_with_callees,
    _input_guard_span,
    _js_next,
    _ls_pref_keys,
    _match_closer,
    _matched_inner,
    _matching_each_end,
    _open_tag_around,
    _open_tag_before,
    _opening_tag,
    _people_each_block,
    _people_list_a11y_surfaces,
    _people_list_gen,
    _people_sidebar_regions,
    _person_detail_markup,
    _rust_fn_body,
    _rust_function_body,
    _short_time_formatter_ok,
    _split_people_only,
    _strip_html_comments,
    _svelte_interpolations,
    _svelte_markup,
    _tag_name,
    _tauri_rust_blob,
    _template_stack,
    _timeline_block,
    _toml_keys_in_fn,
    _ts_fn_body,
    _unguarded_post_ipc_writes,
    _web_logic,
    _web_sources,
    _windows_around,
    _without_comments,
    _without_input_guard,
)


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


def _label_helper_falls_back_to_id(blob: str) -> bool:
    return bool(
        re.search(
            r"("
            r"return\s+[^;\n]{0,80}(?:conversation_id|\.id|person_id|personId)\b"
            r"|(?:title|\|\|)\s*[^\n;]{0,80}(?:conversation_id|\.id|person_id|personId)\b"
            r")",
            blob,
        )
    )


def assert_conversation_switcher(crate: Path) -> None:
    """#114: after a person is selected, switch conversations; default All; no raw ids.

    Groups still need include-groups to appear in the list and in All.
    Identity chrome (Merge, include groups, unlink) stays hidden until the
    person name is clicked. Conversation switcher is a compact header control,
    not a second always-expanded list above the bubbles. People sidebar stays.
    All / the open panel must stack above sticky .day-heading (higher z-index
    + background). Switcher label: empty title or title === personTitle shows
    the pretty platform (WhatsApp, Gmail), not the repeated person name;
    distinct titles stay. Not in scope: create / mute / pin. Keep #111–#113.
    """
    app = (crate / "web" / "App.svelte").read_text()
    logic = _web_logic(crate)
    api_src = (crate / "web" / "lib" / "api.ts").read_text()
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    whole = app + "\n" + logic

    blocks = _conversation_switcher_blocks(crate)
    if not blocks:
        fail(
            "#114: after selecting a person, list their conversations "
            "({#each conversations / convos / personConversations / conversationList, "
            "a conversation <select>, or data-conversation-switcher) "
            "with title + platform + last_at"
        )
    switcher = "\n".join(blocks)

    # People sidebar and chat bubbles are not the switcher.
    if _CONV_EACH.search(switcher) is None and not _CONV_SWITCHER_HOOK.search(switcher):
        if not _CONV_SELECT.search(switcher):
            fail(
                "#114: conversation switcher must be a list or select of conversations, "
                "not the people sidebar and not a caption inside a chat bubble"
            )
    tl = _timeline_block(crate)
    if switcher.strip() and switcher.strip() in tl:
        fail(
            "#114: conversation switcher must sit outside the message bubbles "
            "(list conversations, then filter the timeline)"
        )

    detail = _person_detail_markup(app)
    if not _CONV_ALL_LABEL.search(switcher) and not _CONV_ALL_LABEL.search(detail):
        fail("#114: conversation switcher must offer All (default = current D18 merged stream)")
    if not _CONV_STATE_DEFAULT_ALL.search(logic) and not _CONV_STATE_DEFAULT_ALL.search(app):
        fail(
            "#114: default conversation must be All "
            "(selected conversation state starts null / undefined / \"all\")"
        )

    sel = _function_body(whole, "selectPerson")
    if not sel:
        fail("#114: selectPerson must still open a person (default conversation = All)")
    opened_all = bool(_CONV_RESET_ALL.search(sel)) or bool(
        re.search(
            r"conversation(?:Id|_id)\s*:\s*(?:null|undefined|(?:append\s*\?))",
            sel,
        )
    )
    if not opened_all:
        fail(
            "#114: opening a person must default to All (merged D18 stream), "
            "not leave a previously picked conversation_id selected"
        )

    choosers = _conversation_chooser_helpers(logic)
    pretty_helpers = _pretty_platform_helpers(logic)
    # Distinct titles still show; do not require interpolating conv.title when
    # that title is the open person's name (helper may show WhatsApp / Gmail).
    if not _CONV_TITLE.search(switcher):
        title_in_helper = any(
            re.search(r"(?:conversation_title|\.title\b|\btitle\b)", blob)
            for blob in choosers.values()
        )
        if not title_in_helper:
            fail("#114: each conversation in the list must show its title")

    summary_exprs = _heading_exprs(_switcher_summary_markup(crate))
    row_exprs = _heading_exprs(_switcher_row_markup(crate))
    summary_ok = _headings_use_label_helper(summary_exprs, logic, choosers, pretty_helpers)
    rows_ok = _headings_use_label_helper(row_exprs, logic, choosers, pretty_helpers)
    if not choosers and not (summary_ok and rows_ok):
        fail(
            "#114: conversation switcher label must use a helper "
            "(conversationLabel / switcherLabel / platformLabel) that shows "
            "the pretty platform (WhatsApp, Gmail — not raw whatsapp) when "
            "the title is empty or equals personTitle; distinct titles "
            "(groups, mail subjects) still use title"
        )
    if not summary_ok:
        fail(
            "#114: compact switcher summary must call that label helper "
            "(not raw selectedConversationTitle / conv.title as the only heading)"
        )
    if not rows_ok:
        fail(
            "#114: each switcher row heading must call that label helper "
            "(not raw conv.title; subtitle may still show platform + last_at)"
        )
    for blob in choosers.values():
        if _label_helper_falls_back_to_id(blob):
            fail("#114: do not fall back a missing conversation title to a raw id")

    if not _CONV_PLATFORM.search(switcher):
        fail("#114: each conversation in the list must show its platform")
    if not _CONV_LAST_AT.search(switcher):
        fail(
            "#114: each conversation in the list must show last_at "
            "(last activity time of that conversation for this person)"
        )

    if not _CONV_PICK.search(switcher) and not _CONV_PICK.search(detail):
        fail("#114: picking a conversation must select it (click / change / bind)")

    tl_filtered = False
    for m in _PERSON_TIMELINE_CALL.finditer(whole):
        arg = _call_arg(whole, m.end() - 1)
        if re.search(r"conversation(?:Id|_id)\s*:", arg):
            tl_filtered = True
            if not re.search(r"includeGroups", arg):
                fail(
                    "#114: personTimeline must still pass includeGroups "
                    "(All is the current D18 merged stream; groups stay gated)"
                )
            break
    if not tl_filtered:
        fail(
            "#114: picking one conversation must filter the timeline "
            "(personTimeline must pass conversationId / conversation_id; "
            "All passes null so the stream stays D18 merged)"
        )

    api_args = re.search(r"personTimeline\s*:\s*\(\s*args\s*:\s*\{([^}]*)\}", api_src, re.S)
    if not api_args or not re.search(r"conversation(?:Id|_id)\b", api_args.group(1)):
        fail(
            "#114: personTimeline args must include optional conversationId / conversation_id "
            "(All = omitted/null; pick one = that conversation)"
        )

    if not _INCLUDE_GROUPS_LABEL.search(app):
        fail("#114: include groups toggle must remain (groups still require it)")

    list_src = _without_calls(whole, _PERSON_TIMELINE_CALL) + "\n" + switcher
    group_in_list = re.search(
        r"includeGroups[\s\S]{0,400}[\"']group[\"']|[\"']group[\"'][\s\S]{0,400}includeGroups",
        list_src,
    )
    fetched_with_toggle = re.search(
        r"(?:conversations|convos|personConversations|conversationList|convList"
        r"|visibleConversations|filteredConversations)"
        r"\s*=\s*(?:await\s+)?[^=;\n]{0,200}includeGroups",
        list_src,
        re.I,
    )
    if not group_in_list and not fetched_with_toggle:
        fail(
            "#114: groups must require the include-groups toggle to appear in the "
            "conversation list (and in All) — filter kind === \"group\" with includeGroups, "
            "or load the list with includeGroups"
        )
    if re.search(r"kind\s*===?\s*[\"']dm[\"']", list_src) and not re.search(
        r"[\"']group[\"']|email_thread", list_src
    ):
        fail("#114: list dm / group / email_thread, not only DMs")

    visible = _visible_switcher_text(switcher)
    if _CONV_ID_TEXT.search(visible):
        fail(
            "#114: no raw conversation ids or person ids in the conversation switcher "
            "(show title + platform + last_at; data-conversation-id attributes are fine)"
        )
    if (
        _CONV_ID_FALLBACK.search(switcher)
        or _CONV_ID_FALLBACK.search(sel)
        or _CONV_ID_FALLBACK.search(detail)
    ):
        fail("#114: do not fall back a missing conversation title to a raw id")

    markup = app
    script_end = app.rfind("</script>")
    if script_end >= 0:
        markup = app[script_end:]
    if _CONV_CREATE.search(markup) or _CONV_CREATE.search(switcher):
        fail("#114: not in scope — do not add create-conversation chrome")
    if _CONV_MUTE.search(markup) or _CONV_MUTE.search(switcher):
        fail("#114: not in scope — do not add mute-conversation chrome")
    if _CONV_PIN.search(markup) or _CONV_PIN.search(switcher):
        fail("#114: not in scope — do not add pin-conversation chrome")

    if not re.search(
        r"("
        r"conversation switcher"
        r"|list(?:s|ing)? (?:their |the )?conversations"
        r"|conversations? (?:list|switcher|filter)"
        r")",
        dtxt,
        re.I,
    ):
        fail("#114: docs/user/app.md must describe the conversation switcher")
    if not re.search(
        r"("
        r"\bAll\b.{0,100}(default|merged|D18)"
        r"|(default|merged|D18).{0,100}\bAll\b"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail("#114: docs/user/app.md must say All is the default (merged D18 stream)")
    if not re.search(
        r"("
        r"filter(?:s|ed|ing)? (?:the )?timeline"
        r"|timeline.{0,60}filter"
        r"|picking (?:a |one )?conversation"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail("#114: docs/user/app.md must say picking a conversation filters the timeline")
    if not re.search(
        r"("
        r"include groups?.{0,160}conversation"
        r"|conversation.{0,160}include groups?"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#114: docs/user/app.md must say groups still need include-groups "
            "to appear in the conversation list (and in All)"
        )

    # Dogfood: reading a chat must not be buried under identity admin + a second list.
    panes = _person_pane_markups(crate)
    pane = "\n".join(panes) if panes else detail
    merge_at = _MERGE_CTRL.search(pane)
    unlink_at = _UNLINK_CTRL.search(pane)
    groups_at = _groups_ctrl_pos(pane)
    if not merge_at:
        fail(
            "#114: Merge must remain in the person chrome "
            "(hidden until the person name is clicked; do not remove it)"
        )
    if groups_at < 0:
        fail(
            "#114: include groups toggle must remain in the person chrome "
            "(hidden until the person name is clicked; groups still need it)"
        )
    if not unlink_at:
        fail(
            "#114: unlink must remain in the person chrome "
            "(hidden until the person name is clicked; do not remove it)"
        )

    chrome_sites = (
        ("Merge", merge_at.start()),
        ("include groups", groups_at),
        ("unlink", unlink_at.start()),
    )
    for label, pos in chrome_sites:
        if not _chrome_hidden_by_default(pane, pos):
            fail(
                f"#114: {label} must not show until the user opens identity chrome "
                "(default: behind {{#if …}} / hidden / <details> closed — "
                "not sitting above the timeline after selecting a person; "
                "{{#if selectedId}} alone is not a click-to-open gate)"
            )

    flags, title_in_summary = _identity_title_toggle(pane, whole)
    if not flags and not title_in_summary:
        fail(
            "#114: clicking the person title (h1 / personTitle / a button wrapping "
            "the name) must toggle identity chrome (Merge, include groups, unlink)"
        )
    if flags and any(_flag_default_open(logic, name) for name in flags):
        fail(
            "#114: identity chrome must start closed "
            "(toggle state must default false / closed, not true)"
        )
    for label, pos in chrome_sites:
        if not _chrome_toggled_by_title(pane, pos, flags, title_in_summary):
            fail(
                f"#114: clicking the person title must toggle {label} "
                "(same {{#if}} flag, <details> summary, or hidden binding — "
                "not a separate always-visible control)"
            )

    if flags:
        buried = False
        for rx in (_CONV_SWITCHER_HOOK, _CONV_SELECT, _CONV_EACH):
            hit = rx.search(pane)
            if not hit:
                continue
            stack = _template_stack(pane, hit.start())
            if any(kind == "if" and _cond_uses_flag(a, flags) for kind, a, _b in stack):
                buried = True
                break
        if buried:
            fail(
                "#114: conversation switcher must stay in the header next to the "
                "person name (not inside the identity chrome that opens on click)"
            )

    if _always_expanded_conversation_list(crate, logic):
        fail(
            "#114: conversation switcher must be compact in the header "
            "(a <select>, <details>, or a single closed control) — "
            "not a second always-expanded full-width {#each conversations} "
            "list sitting above the bubbles (data-conversation-switcher can stay; "
            "title + platform + last_at still belong inside the compact control)"
        )

    people_src = "\n".join(
        p.read_text() for p in _web_sources(crate) if p.suffix == ".svelte"
    )
    if not re.search(r"\{#each\s+filtered\b", people_src) and not re.search(
        r"id=[\"']person-filter[\"']", people_src
    ):
        fail("#114: people sidebar must stay (do not hide the people list)")
    if _people_list_hidden_on_select(crate):
        fail(
            "#114: people sidebar must stay — do not hide the people list when a "
            "person is selected (no Back-that-hides-the-list in this issue)"
        )

    if not re.search(
        r"("
        r"compact (conversation )?(switcher|control)"
        r"|(conversation )?(switcher|control).{0,80}compact"
        r"|not a second .{0,60}(list|switcher)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#114: docs/user/app.md must say the conversation switcher is a "
            "compact header control (not a second list above the bubbles)"
        )
    if not re.search(
        r"("
        r"(click(?:s|ing)?|tap(?:s|ping)?) (the )?(person )?(name|title)"
        r".{0,160}(Merge|include groups|unlink|identity)"
        r"|(Merge|include groups|unlink|identity chrome)"
        r".{0,160}(click(?:s|ing)?|hidden until|until you click)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#114: docs/user/app.md must say identity chrome "
            "(Merge, include groups, unlink) is hidden until the person name is clicked"
        )

    # Dogfood: sticky .day-heading must not cover All or the open panel.
    stacked, day_z, chrome_z, chrome_bg = _switcher_above_day_heading(crate)
    if not stacked:
        if chrome_z is None or chrome_z <= day_z:
            fail(
                "#114: conversation switcher (data-conversation-switcher / its "
                "summary or panel) or the person-pane header that contains it "
                f"must stack above .day-heading (higher z-index than {day_z}, "
                "and a background so the date cannot show through) — "
                "fail if the switcher/header z-index is missing or "
                f"≤ the day-heading z-index ({day_z})"
            )
        if not chrome_bg:
            fail(
                "#114: conversation switcher / person-pane header must have a "
                "background so the sticky .day-heading date cannot show through "
                "All or the open panel"
            )
        fail(
            "#114: conversation switcher / person-pane header must stack above "
            f".day-heading (z-index > {day_z} and a background; the date must "
            "not cover All or the dropdown)"
        )
_OVERFLOW_Y_SCROLL = re.compile(
    r"("
    r"overflow-y-(?:auto|scroll)"
    r"|overflow-y\s*:\s*(?:auto|scroll)"
    r"|overflow\s*:\s*auto\b"
    r"|overflow\s*:\s*scroll\b"
    r")",
    re.I,
)
_OVERFLOW_X_VISIBLE = re.compile(
    r"("
    r"overflow-x-(?:auto|scroll|visible)"
    r"|overflow-x\s*:\s*(?:auto|scroll|visible)"
    r")",
    re.I,
)
_TRUNCATE_TOKENS = re.compile(
    r"("
    r"\btruncate\b"
    r"|text-ellipsis"
    r"|text-overflow\s*:\s*ellipsis"
    r"|line-clamp-\d+"
    r"|overflow-hidden"
    r")",
    re.I,
)
_PEOPLE_NAME = re.compile(r"\b(?:display_name|displayName|personName|name)\b")
_PEOPLE_PREVIEW = re.compile(
    r"\b(?:last_activity_at|lastActivityAt|preview|last_at|status)\b"
)
_PEOPLE_ID_VISIBLE = re.compile(
    r"\{[^}]{0,60}(?:\bp\.id\b|\bperson\.id\b|\bfiltered\b[^}]{0,20}\.id)[^}]{0,20}\}"
)
_PEOPLE_ID_FALLBACK = re.compile(
    r"(?:display_name|displayName|name)\s*\|\|\s*[^\n;]{0,60}"
    r"(?:\bp\.id\b|\bperson\.id\b|\.id\b)"
)
_SCROLL_AREA_TAG = re.compile(r"<ScrollArea\b([^>]*)>", re.I | re.S)


def _scroll_area_source(crate: Path) -> str:
    p = crate / "web" / "lib" / "components" / "ui" / "scroll-area" / "scroll-area.svelte"
    return p.read_text() if p.is_file() else ""


def _region_overflow_ok(region: str, scroll_defaults: str) -> bool:
    """True if this people pane (or shared ScrollArea defaults) hide x-scroll."""
    # Explicit overflow-x auto/scroll/visible on the people pane is a fail signal
    # unless a more specific hidden also applies on the same ScrollArea.
    for m in _SCROLL_AREA_TAG.finditer(region):
        attrs = m.group(1)
        if _OVERFLOW_X_VISIBLE.search(attrs) and not _OVERFLOW_X_HIDDEN.search(attrs):
            return False
        if _OVERFLOW_X_HIDDEN.search(attrs) and _OVERFLOW_Y_SCROLL.search(attrs):
            return True
        if _OVERFLOW_X_HIDDEN.search(attrs) and _OVERFLOW_Y_SCROLL.search(scroll_defaults):
            return True
        # ScrollArea with people sidebar + defaults that clip x / allow y.
        if (
            _DATA_PEOPLE_SIDEBAR.search(attrs)
            or "border-r" in attrs
            or "min-w-0" in attrs
        ) and _OVERFLOW_X_HIDDEN.search(scroll_defaults) and _OVERFLOW_Y_SCROLL.search(
            scroll_defaults
        ):
            return True
    if _OVERFLOW_X_HIDDEN.search(region) and _OVERFLOW_Y_SCROLL.search(region):
        return True
    if _OVERFLOW_X_HIDDEN.search(scroll_defaults) and _OVERFLOW_Y_SCROLL.search(
        scroll_defaults
    ):
        # Shared ScrollArea defaults apply when the people pane uses ScrollArea.
        if _SCROLL_AREA_TAG.search(region) or "ScrollArea" in region:
            return True
    return False


def _row_clips_long_text(block: str) -> bool:
    """Names / previews must truncate or otherwise not expand the column."""
    if not block:
        return False
    has_name = bool(_PEOPLE_NAME.search(block))
    has_preview = bool(_PEOPLE_PREVIEW.search(block))
    if not has_name:
        return False
    tokens = _TRUNCATE_TOKENS.findall(block)
    if not tokens:
        return False
    # Name + activity preview both shown → both must clip (two truncate sites,
    # or one shared overflow-hidden/line-clamp wrapper plus another clip).
    if has_preview and len(tokens) < 2:
        return False
    return True


# #138 — people `/` filter: identity values on the loaded list, not display_name only.
_PEOPLE_FILTER_IDENTITY_TOKENS = re.compile(
    r"\b(?:"
    r"identity_values|identityValues|"
    r"filter_haystack|filterHaystack|"
    r"value_normalized|valueNormalized"
    r")\b"
)
# `identities` alone is too broad (person detail chrome). Require a person-field
# access (p.identities / person.identities) or the tokens above.
_PEOPLE_FILTER_IDENTITIES_FIELD = re.compile(
    r"(?:\bp|person|row)\s*\??\.\s*identities\b"
    r"|\bidentities\s*\?\?|\bidentities\s*\|\|"
    r"|\b\.\.\.\s*(?:\bp|person)\s*\??\.\s*identities\b"
)
_PEOPLE_FILTER_SKIP_CALLS = frozenset(
    {
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "function",
        "return",
        "typeof",
        "new",
        "await",
        "void",
        "toLowerCase",
        "toUpperCase",
        "trim",
        "includes",
        "filter",
        "map",
        "join",
        "concat",
        "some",
        "every",
        "find",
        "String",
        "Boolean",
        "Number",
        "Array",
        "Math",
        "parseInt",
        "console",
    }
)


def _people_filter_window(src: str) -> str:
    """Logic for the people sidebar filter (`filtered` derived + named helpers)."""
    m = re.search(
        r"(?:const|let)\s+filtered\s*=\s*\$derived\s*\(",
        src,
    )
    if not m:
        m = re.search(r"(?:const|let)\s+filtered\s*=", src)
    if not m:
        return ""
    window = src[m.start() : m.start() + 1600]
    # Expand small named helpers referenced from the filter expression.
    for call in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", window):
        name = call.group(1)
        if name in _PEOPLE_FILTER_SKIP_CALLS:
            continue
        body = _function_body(src, name)
        if body and len(body) < 4000:
            window += "\n" + body
    return window


def assert_people_filter_identity(crate: Path) -> None:
    """#138: people `/` filter matches linked identity values, not only display_name.

    Static: filter expression (or its helpers) must read identity material from
    the loaded person row (identity_values / filter_haystack / p.identities).
    Display-name-only matching is a fail. Still client-side on the list.
    """
    app = (crate / "web" / "App.svelte").read_text()
    logic = _web_logic(crate)
    src = _without_comments(app + "\n" + logic)

    if "person-filter" not in src:
        fail("#138: people sidebar must keep id=person-filter")
    if not _PEOPLE_EACH.search(app):
        fail("#138: people list must still {#each filtered …} as person rows")

    window = _people_filter_window(src)
    if not window.strip():
        fail("#138: people sidebar `filtered` list derivation missing")

    has_identity = bool(_PEOPLE_FILTER_IDENTITY_TOKENS.search(window)) or bool(
        _PEOPLE_FILTER_IDENTITIES_FIELD.search(window)
    )
    if not has_identity:
        fail(
            "#138: people `/` filter must match linked identity values "
            "(identity_values / filter_haystack / p.identities on the loaded list), "
            "not only display_name"
        )
    if "display_name" not in window and "displayName" not in window:
        fail("#138: people filter must still match display_name")


# #265 — people list must not hold the archive mutex for the whole heavy scan.
_PEOPLE_LIST_HEAVY = re.compile(
    r"\bperson_list(?:_with_groups|_on|_on_conn|_from_conn|_snapshot)?\s*\("
)
_PEOPLE_WITH_ARCH = re.compile(r"\bwith_arch(?:_mut)?\s*\(")
_PEOPLE_TAKE_ARCH = re.compile(r"\.take\s*\(")
_PEOPLE_AWAIT_API_PEOPLE = re.compile(r"await\s+api\s*\.\s*people\s*\(")
_PEOPLE_AWAIT_ONCHANGED = re.compile(r"await\s+onChanged\s*\(")
_PEOPLE_PAGE_API = re.compile(r"api\s*\.\s*people(?:Page|Roster|Chunk|More)\s*\(")
_PEOPLE_VOID_API = re.compile(r"void\s+api\s*\.\s*people\s*\(")
_PEOPLE_THEN_API = re.compile(r"api\s*\.\s*people\s*\([^)]*\)\s*\.then\s*\(")
_PEOPLE_FIRST_PAINT_ASSIGN = re.compile(
    r"\bpeople\s*=\s*await\s+api\s*\.\s*people(?:Page|Roster|Chunk|More)\s*\("
)
_PEOPLE_FIRST_PAINT_PUSH = re.compile(r"\bpeople\s*\.(?:push|unshift|splice|concat)\s*\(")
_PEOPLE_REVIEW_DISABLED_LOADING = re.compile(
    r"disabled\s*=\s*\{[^}]*peopleLoading",
    re.I,
)
_PEOPLE_ASSIGN_AWAIT = re.compile(
    r"\bpeople\s*=\s*await\s+api\s*\.\s*people\s*\("
)
_PEOPLE_LOADING_FALSE = re.compile(r"\bpeopleLoading\s*=\s*false\b")
_PEOPLE_BARE_OPEN = re.compile(r"(?:rusqlite::)?Connection::open\s*\(")
_PEOPLE_OPEN_READONLY = re.compile(r"\bSQLITE_OPEN_READ_ONLY\b")
_PEOPLE_OPEN_FLAGS = re.compile(r"\bOpenFlags\b")
_PEOPLE_READ_ONLY = re.compile(r"\bREAD_ONLY\b")
_PEOPLE_QUERY_ONLY = re.compile(r"\bquery_only\b", re.I)
_PEOPLE_SNAPSHOT_TX = re.compile(r"unchecked_transaction|\bBEGIN\b", re.I)
_PEOPLE_COMMENT_ISSUE = re.compile(r"#265")
_PEOPLE_COMMENT_FLOCK = re.compile(r"Exclusive flock stays", re.I)
_PEOPLE_COMMENT_TAKE = re.compile(
    r"Do not take\s*\(\s*\)\s*the Archive|import pattern", re.I
)


def _people_rust_cmd_body(rust: str) -> str:
    return _rust_function_body(rust, "people") or _rust_fn_body(rust, "people")


def _people_expand_rust_calls(rust: str, blob: str, depth: int = 2) -> str:
    parts = [blob]
    seen = {"people", "with_arch", "with_arch_mut"}
    skip = {
        "Ok",
        "Err",
        "Some",
        "None",
        "vec",
        "format",
        "serde_json",
        "to_value",
        "json",
        "map_err",
        "clone",
        "lock",
        "as_ref",
        "as_mut",
        "expect",
        "unwrap",
        "from",
        "join",
        "open",
        "if",
        "for",
        "while",
        "match",
        "return",
        "person_list",
        "person_list_with_groups",
        "person_list_on",
    }

    def walk(src: str, left: int) -> None:
        if left <= 0:
            return
        for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", src):
            name = m.group(1)
            if name in seen or name in skip:
                continue
            seen.add(name)
            inner = _rust_function_body(rust, name) or _rust_fn_body(rust, name)
            if not inner:
                continue
            parts.append(inner)
            walk(inner, left - 1)

    walk(blob, depth)
    return "\n".join(parts)


def _people_with_arch_wraps_heavy(rust: str, body: str) -> bool:
    """True if a with_arch / with_arch_mut closure (or its callees) runs person_list."""
    for m in _PEOPLE_WITH_ARCH.finditer(body):
        args = _call_arg(body, m.end() - 1)
        if not args:
            continue
        expanded = _people_expand_rust_calls(rust, args)
        if _PEOPLE_LIST_HEAVY.search(expanded):
            return True
    return False


def _people_cmd_takes_archive(rust: str, body: str) -> bool:
    expanded = _people_expand_rust_calls(rust, body)
    return bool(_PEOPLE_TAKE_ARCH.search(expanded))


def _refresh_first_paints_before_full_people(refresh: str) -> bool:
    """True if refreshPeople paints a page / fires-and-forgets before the full list."""
    full = _PEOPLE_AWAIT_API_PEOPLE.search(refresh)
    if not full:
        if _PEOPLE_VOID_API.search(refresh) or _PEOPLE_THEN_API.search(refresh):
            return True
        if _PEOPLE_PAGE_API.search(refresh):
            return True
        return False
    before = refresh[: full.start()]
    if _PEOPLE_FIRST_PAINT_ASSIGN.search(before):
        return True
    if _PEOPLE_FIRST_PAINT_PUSH.search(before):
        return True
    return False


def _apply_status_releases_before_people(apply_st: str) -> bool:
    if _PEOPLE_AWAIT_REFRESH.search(apply_st):
        return False
    return bool(re.search(r"(?:void\s+)?refreshPeople\s*\(", apply_st))


def _people_load_incremental(app: str, logic: str) -> bool:
    src = _without_comments(app + "\n" + logic)
    refresh = _function_body(src, "refreshPeople") or _ts_fn_body(src, "refreshPeople")
    apply_st = _function_body(src, "applyStatus") or _ts_fn_body(src, "applyStatus")
    if refresh and _refresh_first_paints_before_full_people(refresh):
        return True
    if apply_st and _apply_status_releases_before_people(apply_st):
        return True
    return False


def _review_nav_disabled_while_people_loading(app: str) -> bool:
    for m in re.finditer(r"<Button\b[^>]*>", app, re.S):
        tag = m.group(0)
        if "review" not in tag.lower():
            continue
        if _PEOPLE_REVIEW_DISABLED_LOADING.search(tag):
            return True
    return False


def _people_refresh_body(src: str) -> str:
    return _function_body(src, "refreshPeople") or _ts_fn_body(src, "refreshPeople")


def _people_cmd_comment(rust: str) -> str:
    """Comments on `fn people` (leading body + immediately above the fn)."""
    m = re.search(r"(?:pub\s+)?(?:async\s+)?fn\s+people\s*\(", rust)
    if not m:
        return ""
    kept: list[str] = []
    for line in reversed(rust[: m.start()].splitlines()):
        s = line.strip()
        if s == "":
            if kept:
                break
            continue
        if s.startswith("#["):
            continue
        if s.startswith("//") or s.startswith("///") or s.startswith("/*") or s.startswith("*"):
            kept.append(s)
            continue
        break
    header = list(reversed(kept))
    lead: list[str] = []
    for line in _people_rust_cmd_body(rust).splitlines():
        s = line.strip()
        if s == "":
            if lead:
                break
            continue
        if s.startswith("//") or s.startswith("/*") or s.startswith("*"):
            lead.append(s)
            continue
        break
    return "\n".join(header + lead)


def _people_list_on_blob(core: str) -> str:
    """person_list_on / person_list_on_with_groups (+ one hop, not attach)."""
    parts: list[str] = []
    skip = {"attach_identity_values"}
    seen: set[str] = set()
    for name in ("person_list_on", "person_list_on_with_groups"):
        body = _rust_function_body(core, name) or _rust_fn_body(core, name)
        if not body:
            continue
        parts.append(body)
        seen.add(name)
        for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", body):
            callee = m.group(1)
            if callee in seen or callee in skip:
                continue
            seen.add(callee)
            inner = _rust_function_body(core, callee) or _rust_fn_body(core, callee)
            if inner:
                parts.append(inner)
    return "\n".join(parts)


def assert_people_list_lock(crate: Path) -> None:
    """#265: Review / Confirm / Undo stay callable while people is filling.

    Static: `people` must not hold `with_arch` around the entire heavy
    `person_list`, or the UI first-paints without awaiting the full list
    before Review / undo. Do not `take()` the Archive (import pattern).
    Keep #138 identity haystack and #221 void onChanged / close-first.
    Not a wall-clock “minutes” bound. Do not rewrite #203 / #110 / #221.

    #265 follow-up: refreshPeople increments peopleGen and discards stale
    api.people() replies; snapshot is read-only + query_only; list +
    attach_identity_values share one BEGIN / unchecked_transaction;
    people() comment is not the three-line history.
    """
    rust_path = crate / "src" / "main.rs"
    app_path = crate / "web" / "App.svelte"
    review_path = crate / "web" / "lib" / "ReviewPane.svelte"
    confirm_path = crate / "web" / "lib" / "ConfirmDialog.svelte"
    rust = rust_path.read_text() if rust_path.is_file() else ""
    app = app_path.read_text() if app_path.is_file() else ""
    logic = _web_logic(crate)
    review_src = review_path.read_text() if review_path.is_file() else ""
    confirm_src = confirm_path.read_text() if confirm_path.is_file() else ""

    people_body = _people_rust_cmd_body(rust)
    if not people_body.strip():
        fail("#265: people command required (Tauri IPC)")

    if _people_cmd_takes_archive(rust, people_body):
        fail(
            "#265: people must not take() the Archive out of the mutex "
            "(Review / Confirm / Undo would see no archive — that is the import pattern)"
        )

    holds_heavy = _people_with_arch_wraps_heavy(rust, people_body)
    incremental = _people_load_incremental(app, logic)
    if holds_heavy and not incremental:
        fail(
            "#265: people must not hold with_arch around the entire person_list, "
            "or people load must first-paint without awaiting the full list "
            "before Review / undo"
        )

    if _review_nav_disabled_while_people_loading(app):
        fail(
            "#265: Review tab must stay clickable while people is filling "
            "(do not disable Review on peopleLoading)"
        )

    review_clean = _without_comments(review_src)
    if _PEOPLE_AWAIT_ONCHANGED.search(review_clean):
        fail(
            "#265: ReviewPane must not await onChanged() "
            "(keep #221 — People refresh must not block Accept / Reject / Undo)"
        )
    if _PEOPLE_AWAIT_API_PEOPLE.search(review_clean):
        fail(
            "#265: Review / undo must not await api.people() "
            "(keep #221 — Review stays callable while people is filling)"
        )

    if confirm_src:
        confirm_clean = _without_comments(confirm_src)
        go_body = _ts_fn_body(confirm_clean, "go") or _function_body(confirm_clean, "go")
        if go_body:
            await_onconfirm = re.search(r"await\s+onconfirm\s*\(", go_body)
            if await_onconfirm:
                close_open = re.search(r"\bopen\s*=\s*false\b", go_body)
                if not close_open or close_open.start() > await_onconfirm.start():
                    fail(
                        "#265: ConfirmDialog go() must set open = false before "
                        "await onconfirm() (keep #221 close-first)"
                    )

    src = _without_comments(app + "\n" + logic)
    window = _people_filter_window(src)
    has_identity = bool(_PEOPLE_FILTER_IDENTITY_TOKENS.search(window)) or bool(
        _PEOPLE_FILTER_IDENTITIES_FIELD.search(window)
    )
    if not has_identity:
        fail(
            "#265: people `/` filter must still match linked identity values "
            "(identity_values / filter_haystack / p.identities on the loaded list)"
        )

    # Follow-up: stale people reply + read-only snapshot + one-transaction list.
    refresh = _people_refresh_body(src)
    if not refresh.strip():
        fail("#265: refreshPeople required (must discard stale api.people() replies)")
    tok = _people_list_gen(refresh)
    for m in _PEOPLE_ASSIGN_AWAIT.finditer(refresh):
        if not tok or not _assignment_gen_guarded(
            refresh, m.start(), tok[0], tok[1]
        ):
            fail(
                "#265: refreshPeople must not assign unguarded "
                "people = await api.people() "
                "(increment peopleGen and keep the assignment only when gen is current)"
            )
    if not tok:
        fail(
            "#265: refreshPeople must increment a generation "
            "(peopleGen; tlGen only if it is also the people-list gen)"
        )
    if not _PEOPLE_LOADING_FALSE.search(refresh):
        fail(
            "#265: refreshPeople must clear peopleLoading only when the "
            "generation is current"
        )
    bad = _unguarded_post_ipc_writes(
        refresh, tok[0], tok[1], ("people", "peopleLoading"), ("api.people",)
    )
    if bad:
        fail(
            "#265: refreshPeople must not assign people / clear peopleLoading "
            "when the generation is stale"
        )

    snap = _people_expand_rust_calls(rust, people_body)
    if _PEOPLE_BARE_OPEN.search(snap):
        fail(
            "#265: people snapshot must not use bare Connection::open "
            "(open read-only with SQLITE_OPEN_READ_ONLY / OpenFlags + READ_ONLY)"
        )
    readonly = bool(_PEOPLE_OPEN_READONLY.search(snap)) or (
        bool(_PEOPLE_OPEN_FLAGS.search(snap)) and bool(_PEOPLE_READ_ONLY.search(snap))
    )
    if not readonly or not _PEOPLE_QUERY_ONLY.search(snap):
        fail(
            "#265: people snapshot must open read-only "
            "(SQLITE_OPEN_READ_ONLY / OpenFlags + READ_ONLY) and set query_only"
        )

    people_rs = (
        repo_root() / "crates" / "interlace-core" / "src" / "people.rs"
    )
    core_people = people_rs.read_text() if people_rs.is_file() else ""
    list_blob = _people_list_on_blob(core_people)
    if not list_blob.strip():
        fail(
            "#265: person_list_on / person_list_on_with_groups required "
            "(list + attach_identity_values must share one snapshot)"
        )
    if not _PEOPLE_SNAPSHOT_TX.search(list_blob):
        fail(
            "#265: person_list_on / person_list_on_with_groups must use "
            "unchecked_transaction or BEGIN so list + attach_identity_values "
            "are one snapshot"
        )

    comment = _people_cmd_comment(rust)
    if (
        _PEOPLE_COMMENT_ISSUE.search(comment)
        and _PEOPLE_COMMENT_FLOCK.search(comment)
        and _PEOPLE_COMMENT_TAKE.search(comment)
    ):
        fail(
            "#265: people() comment must not be the three-line #265 / "
            "Exclusive flock / take() history (one-line why is OK)"
        )


def assert_people_sidebar_no_x_scroll(crate: Path) -> None:
    """#159: people sidebar must not pan sideways; vertical scroll only.

    Long names and activity previews stay readable via truncate / min-w-0 /
    minmax(0, …) — they must not push the left column wider. People list stays
    when a chat is open. No raw person ids in list labels. Not #114 switcher.
    """
    app = (crate / "web" / "App.svelte").read_text()
    people_src = "\n".join(
        p.read_text() for p in _web_sources(crate) if p.suffix == ".svelte"
    )
    regions = _people_sidebar_regions(crate)
    region_blob = "\n".join(regions) if regions else ""
    scroll_defaults = _scroll_area_source(crate)

    # 1) People list still exists and is not hidden when a person is selected.
    if not _PEOPLE_EACH.search(people_src) and not re.search(
        r"id=[\"']person-filter[\"']", people_src
    ):
        fail(
            "#159: people sidebar must still list people "
            "({#each filtered …} and/or person-filter) — do not remove the left column"
        )
    if _people_list_hidden_on_select(crate):
        fail(
            "#159: people sidebar must stay visible when a person is selected "
            "(do not hide the people list when a chat is open — that is not this issue)"
        )

    # 2) Scroll container: overflow-x hidden; overflow-y auto/scroll.
    if not regions and not (
        _OVERFLOW_X_HIDDEN.search(scroll_defaults)
        and _OVERFLOW_Y_SCROLL.search(scroll_defaults)
        and _SCROLL_AREA_TAG.search(app)
    ):
        fail(
            "#159: people sidebar scroll region not found "
            "({#each filtered}, person-filter, or data-people-sidebar)"
        )

    overflow_ok = False
    if regions:
        overflow_ok = any(_region_overflow_ok(r, scroll_defaults) for r in regions)
    if not overflow_ok:
        # Shared ScrollArea defaults alone are enough when people pane uses it.
        if (
            _SCROLL_AREA_TAG.search(app)
            and _OVERFLOW_X_HIDDEN.search(scroll_defaults)
            and _OVERFLOW_Y_SCROLL.search(scroll_defaults)
            and not _OVERFLOW_X_VISIBLE.search(region_blob)
        ):
            overflow_ok = True
    if not overflow_ok:
        fail(
            "#159: people pane must hide horizontal overflow "
            "(overflow-x: hidden / overflow-x-hidden on the people ScrollArea "
            "or shared ScrollArea defaults) while still allowing vertical scroll "
            "(overflow-y: auto|scroll)"
        )
    if _OVERFLOW_X_VISIBLE.search(region_blob) and not _OVERFLOW_X_HIDDEN.search(
        region_blob + "\n" + scroll_defaults
    ):
        fail(
            "#159: people pane must not enable horizontal pan "
            "(overflow-x auto/scroll/visible without overflow-x hidden)"
        )

    # 3) Long names / previews do not expand the column indefinitely.
    each_blocks = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        text = p.read_text()
        markup = _svelte_markup(text)
        block = _people_each_block(markup)
        if block:
            each_blocks.append(block)
    if not each_blocks:
        fail("#159: people list must still {#each filtered …} as person rows")
    people_rows = "\n".join(each_blocks)
    if not _row_clips_long_text(people_rows):
        fail(
            "#159: long person names and activity previews must truncate "
            "(or ellipsis / line-clamp / overflow-hidden) so they stay readable "
            "without pushing the people column wider"
        )
    # Column track or row ancestors must be able to shrink (min-w-0 / minmax(0, …)).
    column_blob = region_blob + "\n" + app
    if not _MIN_W0.search(column_blob) and not _MIN_W0.search(people_rows):
        fail(
            "#159: people column / row content must allow shrink "
            "(min-w-0 or grid minmax(0, …)) so truncate can take effect"
        )

    # 4) No raw person-id copy in people list labels (undo event ids elsewhere ok).
    visible_rows = _strip_tag_attrs(people_rows)
    visible_rows = re.sub(r"\{[#/:@].*?\}", "", visible_rows, flags=re.S)
    if _PEOPLE_ID_VISIBLE.search(visible_rows):
        fail(
            "#159: no raw person ids in the people list labels "
            "(show display name / preview; data-id attributes are fine)"
        )
    if _PEOPLE_ID_FALLBACK.search(people_rows):
        fail("#159: do not fall back a missing person name to a raw id")
# Selecting / opening a person (existing selectPerson or jump-specific open).
_SELECT_PERSON_CALL = re.compile(
    r"\b(?:"
    r"selectPerson|openPerson|pickPerson|showPerson|loadPerson|"
    r"openPersonAtMessage|selectPersonAtMessage|jumpToPersonMessage"
    r")\s*\(",
    re.I,
)
_HUMAN_TIME_CALL = re.compile(
    r"\b(?:" + "|".join(_HUMAN_TIME_HELPERS) + r")\s*\("
)
_DATE_PICKER = re.compile(
    r"("
    r"\bDatePicker\b"
    r"|date-picker"
    r"|datepicker"
    r"|flatpickr"
    r"|litepicker"
    r"|air-datepicker"
    r"|type\s*=\s*[\"']date[\"']"
    r"|type\s*=\s*[\"']datetime-local[\"']"
    r")",
    re.I,
)


def _interp_dumps_iso_activity(expr: str) -> bool:
    """True if last_activity_at is stringified (raw T…Z), not passed to a formatter."""
    if not re.search(r"\blast_activity_at\b", expr):
        return False
    if re.search(r"[A-Za-z_]\w*\s*\([^)]*\blast_activity_at\b", expr):
        return False
    # Truthiness for a separator (`p.last_activity_at && p.preview ? " · " : ""`).
    if re.search(r"last_activity_at\s*&&", expr) and not re.search(
        r"last_activity_at\s*(?:\?\?|\|\|)", expr
    ):
        return False
    return True


def _attr_brace_values(src: str, attr: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(rf"{re.escape(attr)}\s*=\s*\{{", src, re.I):
        start = m.end() - 1
        end = _match_closer(src, start)
        if end > start:
            out.append(src[start + 1 : end])
    return out


def _people_uses_short_time(people_each: str) -> bool:
    if _HUMAN_TIME_CALL.search(people_each):
        return True
    for expr in _svelte_interpolations(people_each):
        if re.search(r"[A-Za-z_]\w*\s*\([^)]*\blast_activity_at\b", expr):
            return True
    return False


def assert_human_time_people(crate: Path) -> None:
    """#184: people list / VoiceOver show a short time, not raw ISO last_activity_at.

    Visible sidebar options and the name VoiceOver reads are name + a short
    time (e.g. 11 Aug 14:32), not 2024-08-11T14:32:00Z. Archive / api.ts JSON
    still carries ISO last_activity_at. Do not t() bodies. Not a date-picker
    locale pack. Do not require “yesterday” in App.svelte (#112).
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#184: App.svelte required (people list last_activity_at display)")
    app = app_path.read_text()
    logic = _web_logic(crate)
    chrome, people_each = _people_list_a11y_surfaces(crate)
    if not people_each.strip():
        markup = _strip_html_comments(_svelte_markup(app))
        people_each = _people_each_block(markup)
        chrome = markup
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    if not _PEOPLE_EACH.search(app) and not _PEOPLE_EACH.search(chrome):
        fail("#184: people sidebar must still {#each filtered …} as person options")
    if not people_each.strip():
        fail("#184: people list {#each filtered} body missing")

    # 1) Still show last_activity_at — as a short time, not dropped.
    if not re.search(r"\blast_activity_at\b", people_each):
        fail(
            "#184: people list must still show last_activity_at "
            "(as a short time, not drop the activity timestamp)"
        )

    # 2) Visible option text is not the raw ISO T…Z string.
    raw_dump = any(_interp_dumps_iso_activity(expr) for expr in _svelte_interpolations(people_each))
    if raw_dump:
        fail(
            "#184: people list must not display raw ISO last_activity_at "
            "(T…Z / 2024-08-11T14:32:00Z); use a short time (e.g. 11 Aug 14:32)"
        )

    # 3) A formatter exists (month + hour:minute; UTC / ISO prefix). Helper
    #    may live in another web/ file. Do not require “yesterday” in App.svelte.
    if not _short_time_formatter_ok(logic):
        fail(
            "#184: format last_activity_at as a short time "
            "(e.g. 11 Aug 14:32) — month + hour:minute, not YYYY-MM-DDTHH:MM:SSZ"
        )
    if not _people_uses_short_time(people_each):
        fail(
            "#184: people options must pass last_activity_at through a short-time "
            "helper (e.g. humanTime(p.last_activity_at)), not interpolate the ISO"
        )

    # 4) VoiceOver: name + short time, not 2024-08-11T14:32:00Z.
    if not re.search(r"\b(?:display_name|displayName|personLabel|personName)\b", people_each):
        fail(
            "#184: VoiceOver on a person must hear the name plus a short time "
            "(keep display_name / personLabel on the option)"
        )
    labels = _attr_brace_values(people_each, "aria-label")
    if labels:
        for lab in labels:
            has_name = bool(
                re.search(r"display_name|displayName|personLabel|personName", lab)
            )
            wrapped = bool(
                re.search(r"[A-Za-z_]\w*\s*\([^)]*\blast_activity_at\b", lab)
                or _HUMAN_TIME_CALL.search(lab)
            )
            raw_in_label = bool(re.search(r"\blast_activity_at\b", lab)) and not wrapped
            if not has_name:
                fail(
                    "#184: VoiceOver aria-label must include the person name "
                    "plus a short time"
                )
            if raw_in_label:
                fail(
                    "#184: VoiceOver must not read raw ISO last_activity_at "
                    "(2024-08-11T14:32:00Z) — aria-label is name + short time"
                )
            if not wrapped:
                fail(
                    "#184: VoiceOver aria-label must be the name plus a short time "
                    "(not 2024-08-11T14:32:00Z)"
                )

    # 5) Archive / API JSON types still carry ISO last_activity_at.
    api_path = crate / "web" / "lib" / "api.ts"
    if not api_path.is_file():
        fail("#184: web/lib/api.ts required (Person.last_activity_at stays ISO)")
    api = api_path.read_text()
    if not re.search(
        r"export type Person\s*=\s*\{[^}]*\blast_activity_at\??\s*:\s*string",
        api,
        re.S,
    ):
        fail(
            "#184: API Person JSON must still carry ISO last_activity_at "
            "(do not strip the field from api.ts)"
        )

    # 6) Do not t() message bodies or previews.
    helpers = _chrome_helper_names(logic)
    body_blob = logic + "\n" + app
    if _chrome_helper_on_body(body_blob, helpers) or _BODY_T_CALL.search(body_blob):
        fail("#184: do not t() message bodies or previews (t(body_text) / t(preview))")

    # 7) Not a date-picker locale pack.
    if _DATE_PICKER.search(logic) or _DATE_PICKER.search(app):
        fail("#184: not a date-picker locale pack")

    # 8) Docs: people list / VoiceOver use a short time, not the raw ISO.
    if not dtxt.strip():
        fail("#184: docs/user/app.md required (people list / VoiceOver short time)")
    if not re.search(
        r"("
        r"(?:people list|VoiceOver).{0,220}short(?:er)?(?: human)? time"
        r"|short(?:er)?(?: human)? time.{0,220}(?:people list|VoiceOver)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#184: docs/user/app.md must say people list / VoiceOver use a "
            "short time, not the raw ISO"
        )
    if not re.search(
        r"("
        r"not (?:the |a )?raw ISO"
        r"|not (?:the |a )?raw.{0,24}ISO"
        r"|not .{0,40}2024-08-11T"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#184: docs/user/app.md must say people list / VoiceOver time is "
            "not the raw ISO"
        )


# #212 — collapsible people sidebar (fixed width, rail, ⌘\, local persist).
_MINMAX_PEOPLE_TRACK = re.compile(
    r"minmax\s*\(\s*0\s*,\s*(?:18|16)rem\s*\)",
    re.I,
)
_FIXED_PEOPLE_WIDTH = re.compile(
    r"("
    r"(?<![\w-])w-(?:72|64)\b"
    r"|(?<![\w-])w-\[[\"']?(?:18|16)rem[\"']?\]"
    r"|width\s*:\s*(?:18|16)rem"
    r"|grid-cols-\[[^\]]*?(?:18|16)rem"
    r"|grid-template-columns\s*:\s*(?:18|16)rem"
    r")",
    re.I,
)
_RAIL_WIDTH = re.compile(
    r"(?<![\w-])w-(?:12|14|16)\b|(?<![\w-])w-\[[\"']?(?:3(?:\.5)?|4)rem[\"']?\]",
    re.I,
)
_RAIL_ICON = re.compile(
    r"("
    r"@lucide/svelte/icons/(?:user|users|user-round|circle-user)"
    r"|<(?:User|Users|UserRound|CircleUser)\b"
    r"|(?:display_name|displayName|\.name)\s*(?:\?\.|\.)\s*"
    r"(?:charAt\s*\(\s*0\s*\)|slice\s*\(\s*0\s*,\s*1\s*\)|\[0\])"
    r"|\binitials?\b"
    r")",
    re.I,
)
_KEY_BACKSLASH = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']\\\\[\"']"
    r"|[\"']\\\\[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']Backslash[\"']"
    r"|[\"']Backslash[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?code\s*===?\s*[\"']Backslash[\"']"
    r"|[\"']Backslash[\"']\s*===?\s*(?:e\.)?code"
    r")"
)
_ALTGR_SAFE_MOD = re.compile(
    r"(?:e\.)?ctrlKey\s*&&\s*!(?:e\.)?altKey",
)
_COLLAPSE_WORD = re.compile(r"collaps", re.I)
_AUTO_WIDTH = re.compile(
    r"("
    r"\binnerWidth\b"
    r"|\bmatchMedia\s*\("
    r"|addEventListener\s*\(\s*[\"']resize[\"']"
    r"|\bonresize\b"
    r")",
    re.I,
)
_NARROW_PX = re.compile(r"\b(?:880|800)\b")
_SELECT_PERSON_CALL = re.compile(r"\b(?:selectPerson|personShow)\s*\(")
_DOCS_COLLAPSE = re.compile(
    r"(?:people|sidebar).{0,80}collaps|collaps.{0,80}(?:people|sidebar)",
    re.I | re.S,
)
_DOCS_BACKSLASH = re.compile(
    r"("
    r"⌘\s*\\"
    r"|Cmd(?:-|\s*|\+)\s*\\"
    r"|Command(?:-|\s*|\+)\s*\\"
    r"|Ctrl(?:-|\s*|\+)\s*\\"
    r"|ctrl(?:-|\s*|\+)\s*\\"
    r")",
    re.I,
)
_DOCS_LOCAL_PREF = re.compile(
    r"("
    r"local(?:Storage)?"
    r".{0,80}(?:not|never|isn.t).{0,24}iCloud"
    r"|(?:not|never|isn.t).{0,24}iCloud.{0,80}local"
    r"|preference is local"
    r"|local(?:ly)?(?: persist| only| pref)"
    r"|localStorage"
    r")",
    re.I | re.S,
)
_DOCS_NOT_ICLOUD = re.compile(
    r"(?:not|never|isn.t).{0,40}iCloud|iCloud.{0,40}(?:not|never)",
    re.I,
)
_DOCS_800 = re.compile(
    r"(?:~|about |around |near )?\s*800\s*(?:px|pixels)?",
    re.I,
)
_DOCS_EXPAND_NARROW = re.compile(
    r"("
    r"\bexpand(?:s|ed|ing)?\b.{0,120}(?:narrow|under\s*880|< ?880)"
    r"|(?:narrow|under\s*880|< ?880).{0,120}\bexpand(?:s|ed|ing)?\b"
    r")",
    re.I | re.S,
)
_DOCS_SLASH_RAIL = re.compile(
    r"("
    r"(?:^|[\s`])/[\s`].{0,140}(?:\brail\b|when\s+collaps|while\s+collaps)"
    r"|(?:\brail\b|when\s+collaps|while\s+collaps).{0,140}(?:^|[\s`])/"
    r"|person-filter.{0,100}(?:\brail\b|when\s+collaps|while\s+collaps)"
    r"|(?:\brail\b|collaps\w*).{0,80}(?:person-filter|people filter)"
    r"|still\s+filter.{0,80}(?:\brail\b|collaps)"
    r")",
    re.I | re.S,
)
_CLICK_ON = re.compile(
    r"(?:on:click|onclick)\s*=\s*\{",
    re.I,
)
_TITLE_DISPLAY = re.compile(
    r"\btitle\s*=\s*\{[^}]{0,200}(?:display_name|displayName|personLabel)",
    re.I,
)
_TITLE_RAW_ID = re.compile(
    r"\btitle\s*=\s*\{[^}]{0,80}(?:\bp\.id\b|\bperson\.id\b)",
    re.I,
)
_OWNED_TOOLTIP_IMPORT = re.compile(
    r"from\s+[\"']\$lib/components/ui/tooltip(?:/index(?:\.js|\.ts)?)?[\"']",
)
_TOOLTIP_OPEN = re.compile(r"<Tooltip(?:Content|Trigger|Provider|\.Root|\.Content)?\b")
_PERSON_FILTER_MARKUP = re.compile(
    r"""(?:id\s*=\s*(?:["']person-filter["']|\{\s*["']person-filter["']\s*\})|#person-filter)"""
)
_SESSION_OVERRIDE = re.compile(
    r"\b(?:"
    r"forceOpen|forceExpanded|force_open|forceWide|"
    r"sessionOpen|sessionExpanded|sessionOverride|"
    r"expandOverride|openOverride|overrideOpen|overrideNarrow|"
    r"pinnedOpen|stayOpen|stayExpanded|keepOpen|keepExpanded|"
    r"expandNow|force\w*Open|\w*Override"
    r")\b",
)
_CODE_BACKSLASH = re.compile(
    r"(?:e\.)?code\s*===?\s*[\"']Backslash[\"']"
    r"|[\"']Backslash[\"']\s*===?\s*(?:e\.)?code"
)
_CODE_INTL_BACKSLASH = re.compile(
    r"(?:e\.)?code\s*===?\s*[\"']IntlBackslash[\"']"
    r"|[\"']IntlBackslash[\"']\s*===?\s*(?:e\.)?code"
)
_CODE_BACKSLASH_EITHER = re.compile(
    r"("
    r"(?:e\.)?code\s*===?\s*[\"'](?:Intl)?Backslash[\"']"
    r"|[\"'](?:Intl)?Backslash[\"']\s*===?\s*(?:e\.)?code"
    r"|(?:e\.)?code\s*\.includes\s*\(\s*[\"']Backslash[\"']"
    r"|(?:e\.)?code\s*\.endsWith\s*\(\s*[\"']Backslash[\"']"
    r"|\[[^\]]*Backslash[^\]]*\]\s*\.includes\s*\(\s*(?:e\.)?code"
    r")"
)


def _people_collapse_shell(markup: str) -> str:
    """Parent grid + people pane open tag (expanded-width lives here)."""
    m = re.search(r"\bdata-people-sidebar\b", markup)
    if not m:
        return ""
    return markup[max(0, m.start() - 500) : m.end() + 480]


def _has_fixed_people_width(blob: str) -> bool:
    """True when expanded width is a fixed token, not only minmax(0,18rem)."""
    stripped = _MINMAX_PEOPLE_TRACK.sub("", blob)
    return bool(_FIXED_PEOPLE_WIDTH.search(stripped))


def _mentions_backslash_key(src: str) -> bool:
    return bool(_KEY_BACKSLASH.search(src)) or bool(
        re.search(r"[\"']Backslash[\"']", src)
    )


def _pref_key_ok(key: str) -> bool:
    low = key.lower()
    mentions = "sidebar" in low or "collapsed" in low
    namespaced = "interlace" in low or "." in key
    return mentions and namespaced


def _click_handler_names(tag: str) -> list[str]:
    names = re.findall(
        r"(?:on:click|onclick)\s*=\s*\{[^}]*?\b([A-Za-z_][\w]*)\s*\(",
        tag,
        re.I,
    )
    names += re.findall(
        r"(?:on:click|onclick)\s*=\s*\{([A-Za-z_][\w]*)\}",
        tag,
        re.I,
    )
    return names


def _toggle_collapse_surface(app: str, markup: str) -> str:
    """data-sidebar-toggle handlers + named collapse helpers."""
    parts: list[str] = []
    for m in re.finditer(r"\bdata-sidebar-toggle\b", markup):
        tag = _opening_tag(markup, m.start())
        parts.append(tag)
        parts.append(markup[max(0, m.start() - 80) : m.end() + 240])
        for name in _click_handler_names(tag):
            inner = _ts_fn_body(app, name) or _function_body(app, name)
            if inner:
                parts.append(_expand_fn_calls(app, inner))
        # Inline onclick={() => { ... }} body.
        cm = _CLICK_ON.search(tag)
        if cm:
            brace = tag.find("{", cm.end() - 1)
            if brace >= 0:
                parts.append(tag[brace:])
    for name in re.findall(
        r"(?:function|const|let)\s+"
        r"(toggle\w*(?:Sidebar|Collapse)|set\w*(?:Sidebar|Collapsed)\w*)",
        app,
        re.I,
    ):
        inner = _ts_fn_body(app, name) or _function_body(app, name)
        if inner:
            parts.append(_expand_fn_calls(app, inner))
    return "\n".join(parts)


def _gated_on_collapse(markup: str, pos: int) -> bool:
    for kind, cond, _extra in _template_stack(markup, pos):
        if kind not in {"if", "if-else"}:
            continue
        if _COLLAPSE_WORD.search(cond):
            return True
    return False


def _split_if_at(markup: str, if_start: int) -> tuple[str, str]:
    """Then / else bodies of the {#if} starting at if_start."""
    head = re.match(r"\{#if\s+[^}]+\}", markup[if_start:])
    if not head:
        return "", ""
    body_start = if_start + head.end()
    depth = 1
    else_body_start: int | None = None
    then_end: int | None = None
    for t in _TMPL_TOKEN.finditer(markup, body_start):
        tok = t.group(0)
        if tok.startswith("{#if"):
            depth += 1
        elif tok.startswith("{/if}"):
            depth -= 1
            if depth == 0:
                if then_end is None:
                    then_end = t.start()
                then = markup[body_start:then_end]
                els = markup[else_body_start : t.start()] if else_body_start is not None else ""
                return then, els
        elif depth == 1 and (tok.startswith("{:else}") or tok.startswith("{:else if")):
            if then_end is None:
                then_end = t.start()
                else_body_start = t.end()
    then = markup[body_start:then_end] if then_end is not None else markup[body_start:]
    els = markup[else_body_start:] if else_body_start is not None else ""
    return then, els


def _collapsed_people_surface(people_rows: str) -> str:
    """Always-on option tags plus the collapsed / rail {#if} branch."""
    parts: list[str] = []
    for m in re.finditer(
        r"<button\b[^>]*>|<[^>]*\brole\s*=\s*[\"']option[\"'][^>]*>",
        people_rows,
        re.I | re.S,
    ):
        parts.append(m.group(0))
    for m in re.finditer(r"\{#if\s+([^}]*)\}", people_rows):
        if not _COLLAPSE_WORD.search(m.group(1)):
            continue
        then, els = _split_if_at(people_rows, m.start())
        if re.search(r"!\s*[\w.]*collaps", m.group(1), re.I):
            parts.append(els)
        else:
            parts.append(then)
    return "\n".join(parts)


def _people_row_tooltip_ok(app: str, people_rows: str) -> bool:
    """Owned Tooltip on the row (wraps the option) or inside the rail branch."""
    if not _OWNED_TOOLTIP_IMPORT.search(app):
        return False
    if not _TOOLTIP_OPEN.search(people_rows):
        return False
    hover = _collapsed_people_surface(people_rows)
    for m in re.finditer(r"<Tooltip\b", people_rows):
        inner = _matched_inner(people_rows, m.start())
        tree = people_rows[m.start() : m.start() + 240] + "\n" + inner
        if not re.search(r"display_name|displayName|personLabel", tree):
            continue
        wraps_option = bool(re.search(r"\brole\s*=\s*[\"']option[\"']|<button\b", inner, re.I))
        in_rail = bool(_TOOLTIP_OPEN.search(hover)) and (
            people_rows[m.start() : m.start() + 40] in hover or inner[:80] in hover
        )
        if wraps_option or in_rail:
            return True
    return False


def _sidebar_collapsed_rhs(src: str) -> str:
    """RHS of sidebarCollapsed = … / $derived(…)."""
    m = re.search(r"\bsidebarCollapsed\s*=\s*", src)
    if not m:
        return ""
    rest = src[m.end() :]
    dm = re.match(r"\$derived(?:\.by)?\s*\(", rest)
    if dm:
        close = _match_closer(rest, dm.end() - 1)
        return rest[dm.end() : close] if close >= 0 else rest[dm.end() :]
    end = rest.find(";")
    return rest[:end] if end >= 0 else rest[:240]


def _hard_narrow_or_user(rhs: str) -> bool:
    compact = re.sub(r"\s+", "", rhs)
    return bool(
        re.fullmatch(
            r"\(?(narrow\|\|userCollapsed|userCollapsed\|\|narrow)\)?",
            compact,
        )
    )


def _backslash_codes_ok(src: str) -> bool:
    """True when onKey treats physical Backslash and IntlBackslash."""
    if re.search(
        r"(?:e\.)?code\s*\.\s*(?:includes|endsWith)\s*\(\s*[\"']Backslash[\"']",
        src,
    ):
        return True
    arr = re.search(r"\[([^\]]*)\]\s*\.includes\s*\(\s*(?:e\.)?code", src)
    if arr and "Backslash" in arr.group(1) and "IntlBackslash" in arr.group(1):
        return True
    return bool(_CODE_BACKSLASH.search(src) and _CODE_INTL_BACKSLASH.search(src))


def _auto_collapse_surface(app: str, logic: str) -> str:
    cleaned = _without_comments(app)
    blob = cleaned + "\n" + logic
    parts = [_windows_around(blob, _AUTO_WIDTH, before=220, after=520)]
    for m in re.finditer(
        r"addEventListener\s*\(\s*[\"']resize[\"']\s*,\s*([A-Za-z_][\w]*)",
        blob,
    ):
        inner = _ts_fn_body(app, m.group(1)) or _function_body(app, m.group(1))
        if inner:
            parts.append(inner)
    return "\n".join(parts)


def assert_people_sidebar_collapse(crate: Path) -> None:
    """#212: fixed-width people sidebar; collapse to a rail; persist locally.

    Expanded width is a token (w-72 / 18rem), not only shrinking
    minmax(0,18rem). data-sidebar-toggle + collapsed hook. ⌘\\ / Ctrl+\\
    in onKey (AltGr-safe, works from fields). localStorage persist — not
    write_last_path / config.toml. Auto-collapse at 880/800. Toggle must
    not remount the open person. Keep nav + chrome search. Follow-up:
    rail hover name, #person-filter stays mounted, forceOpen so Expand
    works under 880, e.code Backslash / IntlBackslash. Not: liquid
    multi-column, hiding Search/Review.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#212: App.svelte required (people sidebar collapse lives there)")
    app = app_path.read_text()
    markup = _strip_html_comments(_svelte_markup(app))
    app_clean = _without_comments(app)
    logic = _web_logic(crate)
    logic_clean = _without_comments(logic)
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    session_path = repo_root() / "crates" / "interlace-core" / "src" / "session.rs"
    session = session_path.read_text() if session_path.is_file() else ""
    rust = _tauri_rust_blob(crate)
    conf_path = crate / "tauri.conf.json"
    conf = conf_path.read_text() if conf_path.is_file() else ""

    # 1) data-people-sidebar stays; expanded width is a fixed token.
    if re.search(r"\bdata-people-sidebar\b", app) and not re.search(
        r"\bdata-people-sidebar\b", markup
    ):
        fail(
            "#212: data-people-sidebar must stay on the people pane markup "
            "(not only a comment or script string)"
        )
    if not re.search(r"\bdata-people-sidebar\b", markup):
        fail(
            "#212: data-people-sidebar must stay on the left people pane "
            "(collapse is that column, not a new shell)"
        )
    shell = _people_collapse_shell(markup)
    if not _has_fixed_people_width(shell):
        fail(
            "#212: people sidebar expanded width must be a fixed token "
            "(w-72 / 18rem), not only shrinking minmax(0,18rem)"
        )

    # 2) Collapse control + collapsed hook.
    if re.search(r"\bdata-sidebar-toggle\b", app) and not re.search(
        r"\bdata-sidebar-toggle\b", markup
    ):
        fail(
            "#212: data-sidebar-toggle must be in App.svelte markup "
            "(not only a comment or script string)"
        )
    if not re.search(r"\bdata-sidebar-toggle\b", markup):
        fail(
            "#212: people sidebar needs a collapse control "
            "(data-sidebar-toggle) that collapses to a rail"
        )
    toggle_tag = _open_tag_around(markup, r"data-sidebar-toggle")
    pane_tag = _open_tag_around(markup, r"data-people-sidebar")
    has_pane_hook = bool(re.search(r"\bdata-people-sidebar-collapsed\b", markup))
    has_aria = bool(re.search(r"\baria-expanded\b", toggle_tag))
    if not has_pane_hook and not has_aria:
        fail(
            "#212: collapsed state must be visible in markup "
            "(data-people-sidebar-collapsed on the pane or aria-expanded "
            "on data-sidebar-toggle)"
        )
    if has_pane_hook and not re.search(
        r"\bdata-people-sidebar-collapsed\b", pane_tag + "\n" + shell
    ):
        # Hook may sit on the same pane tag or the people column wrapper.
        if not re.search(r"\bdata-people-sidebar-collapsed\b", markup):
            fail(
                "#212: data-people-sidebar-collapsed must sit on the people "
                "pane (or aria-expanded on the toggle)"
            )

    # 3) Rail / icons path; no raw person ids in list labels (#159 spirit).
    regions = _people_sidebar_regions(crate)
    region_blob = "\n".join(regions) if regions else shell
    rail_src = region_blob + "\n" + shell + "\n" + markup
    has_rail_w = bool(_RAIL_WIDTH.search(rail_src))
    has_rail_icon = bool(_RAIL_ICON.search(region_blob) or _RAIL_ICON.search(shell))
    has_collapsed_if = bool(
        re.search(r"\{#if\s+[^}]{0,120}collaps", markup, re.I)
    )
    if not (has_rail_w or has_rail_icon or has_collapsed_if):
        fail(
            "#212: collapsed people sidebar must be a rail / icons path "
            "(w-12 / w-14, or initials / Lucide person icon — not a hidden column)"
        )
    if re.search(
        r"(?:collaps[^;]{0,80}\b(?:hidden|w-0|invisible)\b"
        r"|\b(?:hidden|w-0|invisible)\b[^;]{0,80}collaps)",
        region_blob + "\n" + shell,
        re.I,
    ) and not (has_rail_w or has_rail_icon):
        fail(
            "#212: collapse must go to a rail (w-12 / icons), "
            "not hide the people column"
        )
    each_blocks: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        block = _people_each_block(_svelte_markup(p.read_text()))
        if block:
            each_blocks.append(block)
    people_rows = "\n".join(each_blocks)
    label_src = people_rows + "\n" + region_blob
    visible_rows = _strip_tag_attrs(label_src)
    visible_rows = re.sub(r"\{[#/:@].*?\}", "", visible_rows, flags=re.S)
    if _PEOPLE_ID_VISIBLE.search(visible_rows):
        fail(
            "#212: no raw person ids in people-list / rail labels "
            "(show display name / initial; data-id attributes are fine)"
        )
    if _PEOPLE_ID_FALLBACK.search(label_src):
        fail("#212: do not fall back a missing person name to a raw id")

    # 4) ⌘\\ / Ctrl+\\ in existing onKey — AltGr-safe, works from fields.
    raw_body = _app_keydown_body(app_clean) or _app_keydown_body(app)
    if not raw_body.strip():
        fail(
            "#212: App.svelte must handle window keydown "
            "(onKey) so ⌘\\ / Ctrl+\\ can collapse the sidebar"
        )
    body = _expand_fn_calls(app_clean, raw_body)
    if body == raw_body:
        body = _expand_fn_calls(app, raw_body)
    prefix, tail = _split_people_only(raw_body)
    prefix_x = _expand_fn_calls(app_clean, prefix) if prefix.strip() else body
    if prefix_x == prefix:
        prefix_x = _expand_fn_calls(app, prefix) if prefix.strip() else body
    if not _KEY_BACKSLASH.search(raw_body) and not _KEY_BACKSLASH.search(body):
        fail(
            "#212: App key handler must treat metaKey/ctrlKey + \\ / Backslash "
            "as sidebar collapse (⌘\\ / Ctrl+\\)"
        )
    if tail and _KEY_BACKSLASH.search(tail) and not _KEY_BACKSLASH.search(prefix_x):
        fail(
            "#212: ⌘\\ / Ctrl+\\ must run like ⌘F "
            "(it is after `if (view !== \"people\") return` and would not "
            "fire from an input off People)"
        )
    bs_surface = _windows_around(prefix_x, _KEY_BACKSLASH)
    if not bs_surface.strip():
        bs_surface = _windows_around(body, _KEY_BACKSLASH)
    if not _has_mod_combo(bs_surface) and not _has_mod_combo(prefix_x):
        fail(
            "#212: sidebar collapse must accept metaKey or ctrlKey "
            "(⌘\\ on macOS; Ctrl+\\ so gates/tests see the fallback)"
        )
    if not _ALTGR_SAFE_MOD.search(prefix_x) and not _ALTGR_SAFE_MOD.search(bs_surface):
        fail(
            "#212: ⌘\\ / Ctrl+\\ must use the AltGr-safe mod "
            "(metaKey || (ctrlKey && !altKey)) — same as #132"
        )
    if not _MOD_EITHER.search(bs_surface) and not re.search(r"\bmod\b", bs_surface):
        fail("#212: \\ / Backslash collapse must be a metaKey/ctrlKey combo, not a bare key")
    guard_span = _input_guard_span(raw_body)
    handler = _KEY_BACKSLASH.search(raw_body) or _KEY_BACKSLASH.search(body)
    if guard_span and handler:
        guard = raw_body[guard_span[0] : guard_span[1] + 1]
        after_guard = handler.start() > guard_span[1]
        if after_guard and not _mentions_backslash_key(guard):
            fail(
                "#212: ⌘\\ / Ctrl+\\ must work from an INPUT like ⌘F "
                "(allow the combo through the INPUT/TEXTAREA/SELECT guard)"
            )

    # 5) Persist via namespaced localStorage — not write_last_path / config.toml.
    web_blob = app_clean + "\n" + logic_clean
    if not re.search(r"localStorage\s*\.\s*setItem\s*\(", web_blob):
        fail(
            "#212: persist collapse in localStorage.setItem "
            "(namespaced key; not iCloud, not write_last_path)"
        )
    if not re.search(r"localStorage\s*\.\s*getItem\s*\(", web_blob) and not _LS_BRACKET.search(
        web_blob
    ):
        fail(
            "#212: restore the persisted sidebar collapse from localStorage.getItem "
            "(same namespaced key)"
        )
    ls_keys = _ls_pref_keys(web_blob)
    if not any(_pref_key_ok(k) for k in ls_keys):
        fail(
            "#212: localStorage key must be namespaced and mention sidebar / "
            "collapsed (e.g. interlace.peopleSidebarCollapsed)"
        )
    if not session_path.is_file():
        fail("#212: crates/interlace-core/src/session.rs required (do not stash UI prefs there)")
    wl = _rust_fn_body(_without_comments(session), "write_last_path")
    if not wl.strip():
        fail(
            "#212: keep session.rs write_last_path as the last_archive_path writer "
            "(do not rewrite it to dump UI prefs)"
        )
    extra_keys = [k for k in _toml_keys_in_fn(wl) if k != "last_archive_path"]
    if extra_keys or re.search(r"\b(?:sidebar|collapsed|people_sidebar)\b", wl, re.I):
        fail(
            "#212: do not rewrite session.rs write_last_path to dump extra keys "
            "(sidebar collapse is not last_archive_path / config.toml)"
        )
    persist_bits = [
        _toggle_collapse_surface(app, markup),
        _windows_around(web_blob, re.compile(r"localStorage"), before=160, after=220),
        _windows_around(web_blob, _COLLAPSE_WORD, before=120, after=200),
    ]
    persist_surface = "\n".join(persist_bits)
    if _LAST_PATH_API.search(persist_surface) or _CONFIG_TOML.search(persist_surface):
        fail(
            "#212: do not persist the sidebar pref via write_last_path / "
            "read_last_path / config.toml (localStorage only)"
        )
    rust_clean = _without_comments(session + "\n" + rust)
    for m in re.finditer(r"sidebar|collapsed", rust_clean, re.I):
        window = rust_clean[max(0, m.start() - 360) : m.end() + 360]
        if _LAST_PATH_API.search(window) or _CONFIG_TOML.search(window):
            fail(
                "#212: do not persist the sidebar pref via write_last_path / "
                "read_last_path / config.toml (localStorage only)"
            )

    # 6) Auto-collapse on narrow windows (880 / 800).
    auto_src = _auto_collapse_surface(app, logic)
    if not _AUTO_WIDTH.search(app_clean) and not _AUTO_WIDTH.search(logic_clean):
        fail(
            "#212: auto-collapse the people sidebar on a narrow window "
            "(innerWidth / matchMedia / resize)"
        )
    if not _NARROW_PX.search(auto_src):
        fail(
            "#212: auto-collapse threshold must mention 880 or 800 "
            "(keep the timeline readable at ~800px)"
        )

    # 7) Toggle path does not remount the open person.
    toggle_src = _toggle_collapse_surface(app, markup)
    if _SELECT_PERSON_CALL.search(toggle_src):
        fail(
            "#212: collapse toggle must not call selectPerson / personShow "
            "(do not remount the open person)"
        )
    for m in re.finditer(
        r"""id\s*=\s*["']person-timeline["']|#person-timeline""",
        markup,
    ):
        if _gated_on_collapse(markup, m.start()):
            fail(
                "#212: {#if collapsed} must not wrap the timeline "
                "(#person-timeline stays mounted)"
            )
    for m in re.finditer(r"\{#key\s+([^}]*)\}", markup):
        if _COLLAPSE_WORD.search(m.group(1)) and re.search(
            r"person-timeline", markup[m.end() : m.end() + 8000]
        ):
            fail(
                "#212: {#key collapsed} must not wrap the timeline "
                "(toggling collapse must not remount the open person)"
            )

    # 8) Top nav + chrome search stay (do not hide Search/Review).
    if not re.search(r"<nav\b", markup):
        fail("#212: keep the top nav (People / Search / Review / Import / Doctor)")
    if not re.search(r"\bdata-chrome-search\b", markup):
        fail("#212: keep chrome search field data-chrome-search (do not hide Search chrome)")
    for rx, label in (
        (re.compile(r"<nav\b"), "top nav"),
        (re.compile(r"\bdata-chrome-search\b"), "data-chrome-search"),
    ):
        hit = rx.search(markup)
        if hit and _gated_on_collapse(markup, hit.start()):
            fail(
                f"#212: collapse must not hide the {label} "
                "(Search / Review chrome stays; collapse is the people column only)"
            )

    # 9) Docs: collapse + shortcut + local persist + readable ~800px.
    if not dtxt.strip():
        fail(
            "#212: docs/user/app.md required — people sidebar collapse, "
            "⌘\\ / Ctrl+\\, local persist, readable ~800px"
        )
    if not _DOCS_COLLAPSE.search(dtxt):
        fail(
            "#212: docs/user/app.md must say the people sidebar collapses "
            "(fixed width; control + shortcut)"
        )
    if not _DOCS_BACKSLASH.search(dtxt):
        fail("#212: docs/user/app.md must document ⌘\\ / Ctrl+\\ (collapse the people sidebar)")
    if not _DOCS_LOCAL_PREF.search(dtxt):
        fail(
            "#212: docs/user/app.md must say the collapse preference is local "
            "(localStorage / local, not iCloud)"
        )
    if not _DOCS_NOT_ICLOUD.search(dtxt):
        fail(
            "#212: docs/user/app.md must say the collapse preference is not iCloud"
        )
    if not _DOCS_800.search(dtxt):
        fail(
            "#212: docs/user/app.md must say the timeline stays readable "
            "around 800px"
        )

    # 10) Rail hover name: title={display_name} or owned Tooltip. aria-label stays.
    hover_src = _collapsed_people_surface(people_rows)
    if _TITLE_RAW_ID.search(people_rows) or _TITLE_RAW_ID.search(hover_src):
        fail(
            "#212: rail hover name must interpolate display_name "
            "(no raw person ids on title=)"
        )
    has_title = bool(_TITLE_DISPLAY.search(hover_src))
    has_tip = _people_row_tooltip_ok(app, people_rows)
    if not has_title and not has_tip:
        fail(
            "#212: collapsed / rail person rows must expose a hover name "
            "(title={p.display_name} or owned Tooltip); keep aria-label; "
            "no raw person ids"
        )
    if not re.search(
        r"aria-label\s*=\s*\{[^}]{0,240}(?:display_name|displayName|personLabel)",
        people_rows,
    ):
        fail(
            "#212: keep aria-label on person rows "
            "(hover title is extra; do not drop VoiceOver)"
        )

    # 11) #person-filter stays in the DOM when the rail is showing.
    pf = list(_PERSON_FILTER_MARKUP.finditer(markup))
    if not pf:
        fail(
            "#212: #person-filter must stay in the DOM when the rail is showing "
            "(/ still focuses it; do not unmount the filter)"
        )
    for m in pf:
        if _gated_on_collapse(markup, m.start()):
            fail(
                "#212: #person-filter must not sit inside a {#if …collaps…} block "
                "(/ still filters when the rail is showing; sr-only is OK)"
            )

    # 12) Session override so Expand opens while innerWidth < 880.
    rhs = _sidebar_collapsed_rhs(app_clean) or _sidebar_collapsed_rhs(app)
    if _hard_narrow_or_user(rhs):
        fail(
            "#212: visible collapse must not be only narrow || userCollapsed "
            "(need a session override so Expand can open while innerWidth < 880)"
        )
    if not _SESSION_OVERRIDE.search(rhs):
        fail(
            "#212: people sidebar needs a session override (forceOpen or "
            "equivalent) so Expand / ⌘\\ can open while innerWidth < 880"
        )
    persist_fn = _ts_fn_body(app, "persistSidebar") or _function_body(app, "persistSidebar")
    override_assign = "\n".join(
        [
            toggle_src,
            persist_fn,
            bs_surface,
            _windows_around(app_clean, _SESSION_OVERRIDE, before=80, after=120),
        ]
    )
    if not re.search(
        rf"{_SESSION_OVERRIDE.pattern}\s*=",
        override_assign,
    ):
        fail(
            "#212: Expand / toggle / ⌘\\ must set forceOpen (or equivalent) "
            "so the pane opens immediately under 880"
        )
    clear_bits = [
        auto_src,
        persist_fn,
        _ts_fn_body(app, "syncNarrow") or _function_body(app, "syncNarrow"),
        _windows_around(app_clean, _NARROW_PX, before=160, after=280),
    ]
    clear_surface = "\n".join(clear_bits)
    override_names = _SESSION_OVERRIDE.findall(rhs) or _SESSION_OVERRIDE.findall(app_clean)
    cleared = False
    for name in override_names:
        if re.search(rf"\b{re.escape(name)}\s*=\s*(?:false|0|!1)\b", clear_surface):
            cleared = True
            break
        if re.search(
            rf"if\s*\([^)]{{0,80}}(?:narrow|innerWidth\s*<)[^)]*\)\s*"
            rf"\{{[^}}]{{0,160}}\b{re.escape(name)}\s*=",
            clear_surface,
            re.I,
        ):
            cleared = True
            break
    if not cleared and not re.search(
        r"(?://|/\*)[^\n]{0,200}(?:forceOpen|force.?open|override).{0,80}"
        r"(?:clear|reset|false).{0,60}(?:narrow|880|cross)",
        app,
        re.I,
    ):
        fail(
            "#212: crossing into narrow must clear forceOpen (or equivalent) "
            "so auto-collapse still runs at innerWidth < 880"
        )

    # 13) Physical ⌘\\ : e.code Backslash / IntlBackslash (INPUT guard too).
    code_src = prefix_x + "\n" + body + "\n" + raw_body
    if not _backslash_codes_ok(code_src):
        fail(
            "#212: onKey must match e.code === \"Backslash\" or "
            "\"IntlBackslash\" (keep e.key === \"\\\\\" allowed; Turkish-Q / ISO)"
        )
    if guard_span:
        guard = raw_body[guard_span[0] : guard_span[1] + 1]
        guard_x = _expand_fn_calls(app_clean, guard)
        if guard_x == guard:
            guard_x = _expand_fn_calls(app, guard)
        if not _CODE_BACKSLASH_EITHER.search(guard_x) and not _backslash_codes_ok(guard_x):
            fail(
                "#212: INPUT guard must let the e.code Backslash / IntlBackslash "
                "path through, not only e.key === \"\\\\\""
            )

    # 14) Docs: Expand on a narrow window; / still filters when the rail shows.
    if not _DOCS_EXPAND_NARROW.search(dtxt):
        fail(
            "#212: docs/user/app.md must say Expand works on a narrow window "
            "(innerWidth < 880 is not a hard floor)"
        )
    if not _DOCS_SLASH_RAIL.search(dtxt):
        fail(
            "#212: docs/user/app.md must say / still filters when the rail "
            "is showing (#person-filter stays mounted)"
        )

    # 15) Do not soften #q, chrome search, sidebar, overflow-x, virtualizer,
    #     overlay titlebar, CSP.
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#212: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-chrome-search\b", app):
        fail("#212: keep chrome search field data-chrome-search (#208)")
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#212: keep data-people-sidebar (#159 / #212)")
    if not _OVERFLOW_X_HIDDEN.search(shell) and not _OVERFLOW_X_HIDDEN.search(region_blob):
        fail(
            "#212: keep overflow-x-hidden on the people pane (#159) "
            "(do not rewrite assert_people_sidebar_no_x_scroll)"
        )
    if not re.search(r"\bvisibleRange\b", app + "\n" + logic):
        fail(
            "#212: keep the person-timeline virtualizer visibleRange "
            "(#120 / #224)"
        )
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#212: keep the overlay titlebar (#211)")
    if CSP not in conf:
        fail("#212: do not soften tauri CSP")
_INSPECTOR_FLAG = re.compile(
    r"\b("
    r"showPersonChrome"
    r"|inspectorOpen"
    r"|showInspector"
    r"|personInspector"
    r"|personInspectorOpen"
    r"|inspectorVisible"
    r"|inspectorFocused"
    r")\b"
)
_INSPECTOR_CLOSE_ASSIGN = re.compile(
    r"\b("
    r"showPersonChrome"
    r"|inspectorOpen"
    r"|showInspector"
    r"|personInspector"
    r"|personInspectorOpen"
    r"|inspectorVisible"
    r")\s*=\s*(?:false|!1|0)\b"
    r"|close(?:Person)?Inspector\s*\("
)
_INSPECTOR_TIME_CALL = re.compile(
    r"\b(?:" + "|".join(("utcTime",) + _HUMAN_TIME_HELPERS) + r")\s*\("
)
_INSPECTOR_ID_VISIBLE = re.compile(
    r"\{[^}]{0,80}(?:"
    r"\bident(?:ity)?\.id\b"
    r"|\bidentities\[[^\]]+\]\.id\b"
    r"|\bselectedId\b"
    r"|\bperson_id\b"
    r"|\bpersonId\b"
    r")[^}]{0,40}\}"
)
_INSPECTOR_ID_FALLBACK = re.compile(
    r"(?:display_name|displayName|value|value_normalized)\s*\|\|\s*"
    r"[^\n;]{0,60}\.id\b"
)
_INSPECTOR_REMOTE_IMG = re.compile(
    r"<img\b[^>]{0,400}https?://",
    re.I | re.S,
)
_INSPECTOR_FOCUS = re.compile(
    r"("
    r"data-person-inspector"
    r"|\.closest\s*\("
    r"|\.contains\s*\("
    r"|activeElement"
    r"|inspector"
    r")",
    re.I,
)
_DOCS_INSPECTOR = re.compile(
    r"("
    r"(?:optional|right(?:-hand)?)\s+inspector"
    r"|inspector.{0,40}(?:optional|right|off by default)"
    r")",
    re.I | re.S,
)
_DOCS_INSPECTOR_OFF = re.compile(
    r"("
    r"(?:inspector|it).{0,80}(?:off|hidden|closed) by default"
    r"|(?:off|hidden|closed) by default.{0,80}inspector"
    r")",
    re.I | re.S,
)
_DOCS_INSPECTOR_META = re.compile(
    r"("
    r"identit[\w ]{0,40}last activity"
    r"|last activity[\w ]{0,40}identit"
    r")",
    re.I | re.S,
)
_DOCS_INSPECTOR_CHROME = re.compile(
    r"("
    r"(?:inspector|there).{0,160}Merge.{0,80}include groups.{0,80}unlink"
    r"|Merge.{0,80}include groups.{0,80}unlink.{0,160}(?:inspector|there)"
    r")",
    re.I | re.S,
)
_DOCS_INSPECTOR_NOT_TL = re.compile(
    r"("
    r"not a second timeline"
    r"|not another timeline"
    r"|does not (?:load|open|show|mount) a second timeline"
    r")",
    re.I,
)


def _inspector_spans(markup: str) -> list[tuple[int, int, str]]:
    """(start, end, inner) for each data-person-inspector element."""
    out: list[tuple[int, int, str]] = []
    for m in _INSPECTOR_HOOK.finditer(markup):
        span = _element_span(markup, m.start())
        if not span:
            continue
        lt, tag, inner = span
        out.append((lt, lt + len(tag) + len(inner), inner))
    return out


def _inspector_surface(crate: Path, app_markup: str) -> str:
    """Inspector open tag + inner HTML (App.svelte and any child pane)."""
    parts: list[str] = []
    seen: set[str] = set()
    for p in _web_sources(crate):
        if p.suffix != ".svelte":
            continue
        text = _strip_html_comments(_svelte_markup(p.read_text()))
        if not _INSPECTOR_HOOK.search(text):
            continue
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        for m in _INSPECTOR_HOOK.finditer(text):
            span = _element_span(text, m.start())
            if span:
                _lt, tag, inner = span
                parts.append(tag + "\n" + inner)
    if parts:
        return "\n".join(parts)
    return app_markup


def _inspector_in_span(pos: int, spans: list[tuple[int, int, str]]) -> bool:
    return any(start <= pos < end for start, end, _inner in spans)


def _inspector_ident_each(inner: str) -> str:
    m = re.search(r"\{#each\s+[^}]*\bidentit[^}]*\}", inner, re.I)
    if not m:
        return ""
    end = _matching_each_end(inner, m.start())
    return inner[m.start() : end] if end > 0 else inner[m.start() :]


def _inspector_toggle_flags(markup: str, pos: int) -> set[str]:
    """Non-vacuous {#if} / hidden-bind flags gating the inspector."""
    flags: set[str] = set()
    skip = {
        "true",
        "false",
        "null",
        "undefined",
        "hidden",
        "class",
        "aria",
        "selectedId",
        "selectedPerson",
        "personTitle",
        "view",
        "st",
        "setup",
        "booting",
        "opening",
    }
    for kind, a, _b in _template_stack(markup, pos):
        if kind == "if" and not _is_vacuous_chrome_cond(a):
            for name in re.findall(r"\b([A-Za-z_]\w*)\b", a):
                if name not in skip:
                    flags.add(name)
    flags |= _hidden_flags_before(markup, pos)
    tag = _open_tag_around(markup, r"data-person-inspector")
    if tag:
        flags |= _hidden_flags_before(tag + " ", len(tag))
    return flags


def _inspector_hidden_by_default(markup: str, pos: int) -> bool:
    if _chrome_hidden_by_default(markup, pos):
        return True
    tag = _open_tag_around(markup, r"data-person-inspector")
    if not tag:
        return False
    if re.search(r"(?:\bhidden|class:hidden|aria-hidden)\s*=\s*\{", tag, re.I):
        return True
    if re.search(r"\bclass:hidden\b", tag):
        return True
    return False


def _chrome_dump_above_timeline(markup: str, spans: list[tuple[int, int, str]]) -> bool:
    """True when Merge / include-groups / unlink still sit above #person-timeline outside the inspector."""
    tl = re.search(
        r"""id\s*=\s*["']person-timeline["']|#person-timeline""",
        markup,
    )
    if not tl:
        return False
    cut = tl.start()
    for rx in (_MERGE_CTRL, _UNLINK_CTRL):
        for m in rx.finditer(markup):
            if m.start() < cut and not _inspector_in_span(m.start(), spans):
                return True
    groups_at = _groups_ctrl_pos(markup)
    if 0 <= groups_at < cut and not _inspector_in_span(groups_at, spans):
        return True
    return False


def _inspector_esc_surface(app: str) -> str:
    """onKey Escape windows outside the INPUT blur guard (inspector or a child)."""
    raw = _app_keydown_body(_without_comments(app)) or _app_keydown_body(app)
    if not raw.strip():
        return ""
    cleaned = _without_comments(app)
    body = _expand_fn_calls(cleaned, raw)
    if body == raw:
        body = _expand_fn_calls(app, raw)
    outside = _without_input_guard(body)
    surface = _windows_around(outside, _KEY_ESC, before=80, after=560)
    if not surface.strip():
        surface = _windows_around(body, _KEY_ESC, before=80, after=560)
    return surface


def assert_person_inspector(crate: Path) -> None:
    """#213: optional right inspector — identities and meta, not a second timeline.

    data-person-inspector in the People shell, hidden by default. Display
    name, identities as kind + value (not raw ids), last activity via
    humanTime / utcTime. Merge / include-groups / unlink live inside the
    inspector (one place). Esc closes when focused. No second timeline /
    no network avatars. Docs. Keep #q, sidebar, overlay, visibleRange, CSP.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#213: App.svelte required (person inspector lives in the People shell)")
    app = app_path.read_text()
    markup = _strip_html_comments(_svelte_markup(app))
    app_clean = _without_comments(app)
    logic = _web_logic(crate)
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    conf_path = crate / "tauri.conf.json"
    conf = conf_path.read_text() if conf_path.is_file() else ""

    # 1) data-person-inspector in App.svelte People-shell markup.
    if _INSPECTOR_HOOK.search(app) and not _INSPECTOR_HOOK.search(markup):
        fail(
            "#213: data-person-inspector must be in App.svelte People-shell "
            "markup (not only a comment or script string)"
        )
    if not _INSPECTOR_HOOK.search(markup):
        fail(
            "#213: App.svelte People shell must include data-person-inspector "
            "(optional right inspector)"
        )

    hook = _INSPECTOR_HOOK.search(markup)
    hook_pos = hook.start() if hook else 0
    spans = _inspector_spans(markup)
    inner = "\n".join(s[2] for s in spans)
    surface = _inspector_surface(crate, markup)
    if not inner.strip():
        inner = surface

    # 2) Hidden by default — flag false / {#if} / hidden; selectedId alone is not enough.
    if not _inspector_hidden_by_default(markup, hook_pos):
        fail(
            "#213: person inspector must be hidden by default "
            "(flag default false / {#if} / hidden — {#if selectedId} alone "
            "is not enough)"
        )
    flags = _inspector_toggle_flags(markup, hook_pos)
    if flags and any(_flag_default_open(app_clean + "\n" + logic, name) for name in flags):
        fail(
            "#213: person inspector must start closed "
            "(toggle state must default false / closed, not true)"
        )

    # 3) Display name; identities as kind + value; last activity via humanTime / utcTime.
    if not re.search(r"\{[^}]{0,80}(?:personTitle|display_name|displayName)\b", inner + "\n" + surface):
        fail(
            "#213: inspector must list the open person's display name "
            "(personTitle / display_name — not a raw person id)"
        )
    ident_src = _inspector_ident_each(inner) or _inspector_ident_each(surface)
    if not ident_src.strip():
        ident_src = inner + "\n" + surface
    if not re.search(r"\{#each\s+[^}]*\bidentit", ident_src, re.I) and not re.search(
        r"\bidentit(?:y|ies)\b", ident_src, re.I
    ):
        fail("#213: inspector must list the open person's identities")
    if not re.search(r"\bkind\b", ident_src):
        fail(
            "#213: inspector identity labels must include kind "
            "(Review #128 style — not a bare name)"
        )
    if not re.search(r"\b(?:value_normalized|value|display_name|displayName)\b", ident_src):
        fail(
            "#213: inspector identity labels must include value "
            "(or value_normalized / display_name) — not a raw id"
        )
    visible_idents = _strip_tag_attrs(ident_src)
    visible_idents = re.sub(r"\{[#/:@].*?\}", "", visible_idents, flags=re.S)
    if _INSPECTOR_ID_VISIBLE.search(visible_idents):
        fail(
            "#213: inspector must not use raw ident.id / person id as the "
            "visible identity label (kind + value text; id may stay on unlink)"
        )
    if _INSPECTOR_ID_FALLBACK.search(ident_src):
        fail(
            "#213: do not fall back a missing identity label to a raw id "
            "(use kind + value / display_name)"
        )
    activity_src = inner + "\n" + surface
    if not re.search(r"\blast_activity_at\b", activity_src):
        fail(
            "#213: inspector must show last activity "
            "(Person.last_activity_at via humanTime / utcTime)"
        )
    if any(_interp_dumps_iso_activity(expr) for expr in _svelte_interpolations(activity_src)):
        fail(
            "#213: inspector must not interpolate raw ISO last_activity_at "
            "(use humanTime / utcTime)"
        )
    if not _INSPECTOR_TIME_CALL.search(activity_src) and not any(
        re.search(r"[A-Za-z_]\w*\s*\([^)]*\blast_activity_at\b", expr)
        for expr in _svelte_interpolations(activity_src)
    ):
        fail(
            "#213: inspector last activity must go through humanTime / utcTime "
            "(not a raw ISO last_activity_at interpolation)"
        )

    # 4) Merge / include-groups / unlink live inside the inspector (one place).
    merge_at = _MERGE_CTRL.search(surface) or _MERGE_CTRL.search(markup)
    unlink_at = _UNLINK_CTRL.search(surface) or _UNLINK_CTRL.search(markup)
    groups_at = _groups_ctrl_pos(surface)
    if groups_at < 0:
        groups_at = _groups_ctrl_pos(markup)
    if not merge_at:
        fail(
            "#213: Merge… must live inside data-person-inspector "
            "(#114 still requires it; do not leave it only above the timeline)"
        )
    if groups_at < 0:
        fail(
            "#213: include-groups must live inside data-person-inspector "
            "(#114 still requires it; do not leave it only above the timeline)"
        )
    if not unlink_at:
        fail(
            "#213: unlink must live inside data-person-inspector "
            "(#114 still requires it; do not leave it only above the timeline)"
        )
    pane_merge = _MERGE_CTRL.search(markup)
    pane_unlink = _UNLINK_CTRL.search(markup)
    pane_groups = _groups_ctrl_pos(markup)
    if pane_merge and not _inspector_in_span(pane_merge.start(), spans):
        fail(
            "#213: Merge… must sit inside data-person-inspector "
            "(one place — not a sibling dump above the timeline)"
        )
    if pane_groups >= 0 and not _inspector_in_span(pane_groups, spans):
        fail(
            "#213: include-groups must sit inside data-person-inspector "
            "(one place — not a sibling dump above the timeline)"
        )
    if pane_unlink and not _inspector_in_span(pane_unlink.start(), spans):
        fail(
            "#213: unlink must sit inside data-person-inspector "
            "(one place — not a sibling dump above the timeline)"
        )
    if _chrome_dump_above_timeline(markup, spans):
        fail(
            "#213: Merge / include-groups / unlink must not also sit above "
            "#person-timeline outside the inspector (two homes — move the "
            "old {#if showPersonChrome} dump into data-person-inspector)"
        )

    # 5) Inspector is not a second timeline; no network avatars.
    if re.search(
        r"""id\s*=\s*["']person-timeline["']|#person-timeline""",
        inner,
    ):
        fail(
            "#213: inspector must not contain #person-timeline "
            "(identities and meta, not a second timeline)"
        )
    for name in _TIMELINE_EACH_NAMES:
        if re.search(rf"\{{#each\s+{re.escape(name)}\b", inner):
            fail(
                "#213: inspector must not {{#each}} timeline rows "
                "(not a second timeline)"
            )
    if _INSPECTOR_REMOTE_IMG.search(inner) or _INSPECTOR_REMOTE_IMG.search(surface):
        fail(
            "#213: inspector must not use a network avatar <img> "
            "(no http:// or https://)"
        )

    # 6) Esc closes when the inspector (or a child) is focused.
    raw_body = _app_keydown_body(app_clean) or _app_keydown_body(app)
    if not raw_body.strip():
        fail(
            "#213: App.svelte must handle window keydown (onKey) so Esc "
            "can close the inspector when it is focused"
        )
    esc_surface = _inspector_esc_surface(app)
    if not _KEY_ESC.search(raw_body) and not _KEY_ESC.search(esc_surface):
        fail("#213: onKey must handle Escape so the inspector can close when focused")
    if not _INSPECTOR_FLAG.search(esc_surface) and not _INSPECTOR_HOOK.search(esc_surface):
        fail(
            "#213: Escape must close the inspector when it (or a child) is "
            "focused (showPersonChrome / inspectorOpen / data-person-inspector "
            "in onKey — do not steal Esc from INPUT or from Search→People "
            "when the inspector is not focused)"
        )
    if not _INSPECTOR_CLOSE_ASSIGN.search(esc_surface):
        fail(
            "#213: Escape when the inspector is focused must close it "
            "(showPersonChrome / inspectorOpen = false)"
        )
    guard_span = _input_guard_span(raw_body)
    if guard_span:
        guard = raw_body[guard_span[0] : guard_span[1] + 1]
        outside = _without_input_guard(raw_body)
        if (
            _INSPECTOR_CLOSE_ASSIGN.search(guard)
            and not _INSPECTOR_CLOSE_ASSIGN.search(outside)
            and not _INSPECTOR_FLAG.search(outside)
        ):
            fail(
                "#213: Esc must close the inspector when a control inside it "
                "is focused (not only when an INPUT is focused; INPUT still blurs first)"
            )

    # 7) Docs: optional right inspector, off by default, identities + last
    #    activity, Merge/include-groups/unlink there, not a second timeline.
    if not dtxt.strip():
        fail(
            "#213: docs/user/app.md required — optional right inspector, "
            "off by default, identities + last activity"
        )
    if not _DOCS_INSPECTOR.search(dtxt):
        fail(
            "#213: docs/user/app.md must describe the optional right inspector"
        )
    if not _DOCS_INSPECTOR_OFF.search(dtxt):
        fail(
            "#213: docs/user/app.md must say the inspector is off by default"
        )
    if not re.search(r"\bidentit", dtxt, re.I) or not re.search(
        r"last activity", dtxt, re.I
    ):
        fail(
            "#213: docs/user/app.md must say the inspector lists identities "
            "and last activity"
        )
    if not _DOCS_INSPECTOR_CHROME.search(dtxt):
        fail(
            "#213: docs/user/app.md must say Merge / include-groups / unlink "
            "live in the inspector"
        )
    if not _DOCS_INSPECTOR_NOT_TL.search(dtxt):
        fail(
            "#213: docs/user/app.md must say the inspector is not a second timeline"
        )

    # 8) Do not soften #q, people sidebar, overlay titlebar, virtualizer, CSP.
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#213: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#213: keep data-people-sidebar (#159 / #212)")
    if not re.search(r"\bvisibleRange\b", app + "\n" + logic):
        fail(
            "#213: keep the person-timeline virtualizer visibleRange "
            "(#120 / #224)"
        )
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#213: keep the overlay titlebar (#211)")
    if CSP not in conf:
        fail("#213: do not soften tauri CSP")
