"""Person inspector chrome assert. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    CSP,
    _INSPECTOR_HOOK,
    _TIMELINE_EACH_NAMES,
    _expand_fn_calls,
    _matching_each_end,
    _open_tag_around,
    _strip_html_comments,
    _svelte_interpolations,
    _svelte_markup,
    _template_stack,
    _web_logic,
    _web_sources,
    _without_comments,
)

from tauri_gate.import_boot import (
    _HUMAN_TIME_HELPERS,
    _app_keydown_body,
    _input_guard_span,
)

from tauri_gate.people_list import _interp_dumps_iso_activity

from tauri_gate.people_switcher_label import (
    _MERGE_CTRL,
    _UNLINK_CTRL,
    _chrome_hidden_by_default,
    _element_span,
    _flag_default_open,
    _groups_ctrl_pos,
    _hidden_flags_before,
    _is_vacuous_chrome_cond,
    _strip_tag_attrs,
)

from tauri_gate.status_toasts import (
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
