"""Helpers extracted from people_collapse.py (people_collapse_lib)."""
from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _CONFIG_TOML,
    _expand_fn_calls,
    _function_body,
    _LAST_PATH_API,
    _LS_BRACKET,
    _match_closer,
    _matched_inner,
    _MOD_EITHER,
    _open_tag_around,
    _opening_tag,
    _PERSON_PANE_SKIP,
    _rust_fn_body,
    _search_pane_blob,
    _strip_html_comments,
    _svelte_markup,
    _tauri_rust_blob,
    _template_stack,
    _TMPL_TOKEN,
    _ts_fn_body,
    _web_logic,
    _web_sources,
    _without_comments,
    CSP,
)

from tauri_gate.a11y_lib import _people_each_block

from tauri_gate.import_boot_guards import (
    _app_keydown_body,
    _input_guard_span,
    _ls_pref_keys,
)

from tauri_gate.media_linkify_lib import _OVERFLOW_X_HIDDEN

from tauri_gate.people_filter import (
    _PEOPLE_ID_FALLBACK,
    _PEOPLE_ID_VISIBLE,
)

from tauri_gate.people_switcher_pretty import _strip_tag_attrs

from tauri_gate.status_toasts_chrome import (
    _has_mod_combo,
    _split_people_only,
    _toml_keys_in_fn,
    _windows_around,
)
from tauri_gate.status_toasts_toast import _people_sidebar_regions




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

__all__ = [
    "_MINMAX_PEOPLE_TRACK",
    "_FIXED_PEOPLE_WIDTH",
    "_RAIL_WIDTH",
    "_RAIL_ICON",
    "_KEY_BACKSLASH",
    "_ALTGR_SAFE_MOD",
    "_COLLAPSE_WORD",
    "_AUTO_WIDTH",
    "_NARROW_PX",
    "_SELECT_PERSON_CALL",
    "_DOCS_COLLAPSE",
    "_DOCS_BACKSLASH",
    "_DOCS_LOCAL_PREF",
    "_DOCS_NOT_ICLOUD",
    "_DOCS_800",
    "_DOCS_EXPAND_NARROW",
    "_DOCS_SLASH_RAIL",
    "_CLICK_ON",
    "_TITLE_DISPLAY",
    "_TITLE_RAW_ID",
    "_OWNED_TOOLTIP_IMPORT",
    "_TOOLTIP_OPEN",
    "_PERSON_FILTER_MARKUP",
    "_SESSION_OVERRIDE",
    "_CODE_BACKSLASH",
    "_CODE_INTL_BACKSLASH",
    "_CODE_BACKSLASH_EITHER",
    "_people_collapse_shell",
    "_has_fixed_people_width",
    "_mentions_backslash_key",
    "_pref_key_ok",
    "_click_handler_names",
    "_toggle_collapse_surface",
    "_gated_on_collapse",
    "_split_if_at",
    "_collapsed_people_surface",
    "_people_row_tooltip_ok",
    "_sidebar_collapsed_rhs",
    "_hard_narrow_or_user",
    "_backslash_codes_ok",
    "_auto_collapse_surface",
    "re", "Path", "fail", "repo_root", "CSP",
    "_CONFIG_TOML", "_expand_fn_calls", "_function_body", "_LAST_PATH_API",
    "_LS_BRACKET", "_MOD_EITHER", "_open_tag_around", "_PERSON_PANE_SKIP",
    "_rust_fn_body", "_search_pane_blob", "_strip_html_comments",
    "_svelte_markup", "_tauri_rust_blob", "_ts_fn_body", "_web_logic",
    "_web_sources", "_without_comments", "_people_each_block",
    "_app_keydown_body", "_input_guard_span", "_ls_pref_keys",
    "_OVERFLOW_X_HIDDEN", "_PEOPLE_ID_FALLBACK", "_PEOPLE_ID_VISIBLE",
    "_strip_tag_attrs", "_has_mod_combo", "_people_sidebar_regions",
    "_split_people_only", "_toml_keys_in_fn", "_windows_around",
    "_match_closer", "_matched_inner", "_opening_tag", "_template_stack",
    "_TMPL_TOKEN",
]
