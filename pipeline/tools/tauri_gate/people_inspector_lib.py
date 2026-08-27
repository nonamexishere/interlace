"""Helpers extracted from people_inspector.py (people_inspector_lib)."""
from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _expand_fn_calls,
    _INSPECTOR_HOOK,
    _matching_each_end,
    _open_tag_around,
    _search_pane_blob,
    _strip_html_comments,
    _svelte_interpolations,
    _svelte_markup,
    _template_stack,
    _TIMELINE_EACH_NAMES,
    _web_logic,
    _web_sources,
    _without_comments,
    CSP,
)

from tauri_gate.import_boot_guards import (
    _HUMAN_TIME_HELPERS,
    _app_keydown_body,
    _input_guard_span,
)

from tauri_gate.people_filter import _interp_dumps_iso_activity

from tauri_gate.people_switcher_pretty import (
    _MERGE_CTRL,
    _UNLINK_CTRL,
    _chrome_hidden_by_default,
    _flag_default_open,
    _groups_ctrl_pos,
    _hidden_flags_before,
    _is_vacuous_chrome_cond,
    _strip_tag_attrs,
)
from tauri_gate.people_switcher_markup import _element_span

from tauri_gate.status_toasts_chrome import (
    _KEY_ESC,
    _windows_around,
    _without_input_guard,
)



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

__all__ = [
    "_INSPECTOR_FLAG",
    "_INSPECTOR_CLOSE_ASSIGN",
    "_INSPECTOR_TIME_CALL",
    "_INSPECTOR_ID_VISIBLE",
    "_INSPECTOR_ID_FALLBACK",
    "_INSPECTOR_REMOTE_IMG",
    "_INSPECTOR_FOCUS",
    "_DOCS_INSPECTOR",
    "_DOCS_INSPECTOR_OFF",
    "_DOCS_INSPECTOR_META",
    "_DOCS_INSPECTOR_CHROME",
    "_DOCS_INSPECTOR_NOT_TL",
    "_inspector_spans",
    "_inspector_surface",
    "_inspector_in_span",
    "_inspector_ident_each",
    "_inspector_toggle_flags",
    "_inspector_hidden_by_default",
    "_chrome_dump_above_timeline",
    "_inspector_esc_surface",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_INSPECTOR_HOOK",
    "_search_pane_blob",
    "_strip_html_comments",
    "_svelte_interpolations",
    "_svelte_markup",
    "_TIMELINE_EACH_NAMES",
    "_web_logic",
    "_without_comments",
    "CSP",
    "_app_keydown_body",
    "_input_guard_span",
    "_interp_dumps_iso_activity",
    "_MERGE_CTRL",
    "_UNLINK_CTRL",
    "_flag_default_open",
    "_groups_ctrl_pos",
    "_strip_tag_attrs",
    "_KEY_ESC",
    "_without_input_guard",
    "annotations",
    "_expand_fn_calls",
    "_matching_each_end",
    "_open_tag_around",
    "_template_stack",
    "_web_sources",
    "_HUMAN_TIME_HELPERS",
    "_chrome_hidden_by_default",
    "_hidden_flags_before",
    "_is_vacuous_chrome_cond",
    "_element_span",
    "_windows_around",
]
