"""Command-palette chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.palette_lib import *


def assert_command_palette(crate: Path) -> None:
    """#215: ⌘K command palette — owned bits-ui Command, local views + people.

    Own web/lib/components/ui/command/ wrapping bits-ui Command. ⌘K / Ctrl+K
    opens from every view (INPUT guard lets k/K through). View items + jump
    to a loaded person. Search focuses #q. Esc closes. No api.search / FTS /
    HTTP / Spotlight. Docs. Do not rewrite #132 / #201 / #214.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#215: App.svelte required (⌘K command palette)")
    app = _web_logic(crate)
    app_clean = _without_comments(app)
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = _search_pane_blob(crate) if search_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    conf_path = crate / "tauri.conf.json"
    conf = conf_path.read_text() if conf_path.is_file() else ""
    pkg_path = crate / "package.json"
    pkg = pkg_path.read_text() if pkg_path.is_file() else ""

    # 1) Owned command/ (at least one .svelte + index.ts).
    cmd = _command_ui_dir(crate)
    if not cmd.is_dir():
        fail(
            "#215: missing owned Command under web/lib/components/ui/command/ "
            "(at least one .svelte + index.ts)"
        )
    if not any(cmd.glob("*.svelte")):
        fail(
            "#215: web/lib/components/ui/command/ needs at least one .svelte "
            "(owned Command wrapper)"
        )
    if not (cmd / "index.ts").is_file():
        fail("#215: web/lib/components/ui/command/index.ts required")
    cmd_blob = _command_dir_blob(cmd)

    # 2) Wraps local bits-ui Command (not cmdk / a second kit).
    if not re.search(r"from\s*[\"']bits-ui[\"']", cmd_blob):
        fail(
            "#215: web/lib/components/ui/command/ must wrap local bits-ui Command "
            '(import { Command … } from "bits-ui")'
        )
    if not re.search(r"\bCommand\b", cmd_blob):
        fail(
            "#215: web/lib/components/ui/command/ must wrap bits-ui Command "
            "(Command / Command.Root / computeCommandScore)"
        )
    if not _BITS_COMMAND_IMPORT.search(cmd_blob):
        fail(
            "#215: web/lib/components/ui/command/ must import Command from "
            "bits-ui (same wrap as Dialog / Tooltip)"
        )
    if _CMD_PALETTE_FROM.search(cmd_blob):
        fail(
            "#215: wrap local bits-ui Command — do not import cmdk / "
            "svelte-command in command/"
        )

    # 3) package.json still has bits-ui; still no cmdk / svelte-command / second kit.
    if not pkg_path.is_file():
        fail("#215: crates/interlace-tauri/package.json required (bits-ui local)")
    if '"bits-ui"' not in pkg:
        fail(
            "#215: package.json must keep bits-ui as a local dependency "
            "(wrap bits-ui Command; do not swap kits)"
        )
    if _CMD_PALETTE_PKG.search(pkg):
        fail(
            "#215: package.json must not add cmdk / svelte-command "
            "(#201 ban stays — wrap local bits-ui Command)"
        )
    if _SECOND_UI_KIT.search(pkg):
        fail(
            "#215: package.json must not add a second UI kit "
            "(@radix-ui / shadcn / daisyui / …) — wrap local bits-ui Command"
        )

    # 4) Chrome imports the owned wrapper, not bits-ui Command in App.
    used_owned = False
    for p in _product_svelte(crate):
        rel = str(p).replace("\\", "/")
        if "/components/ui/command/" in rel:
            continue
        text = p.read_text()
        if _owned_imported_names(text, "command"):
            used_owned = True
            break
    if not used_owned:
        fail(
            "#215: App / chrome must import the owned Command from "
            "$lib/components/ui/command (do not import bits-ui Command in App)"
        )
    if re.search(
        r"import\s*\{[^}]*\bCommand\b[^}]*\}\s*from\s*[\"']bits-ui[\"']",
        app_path.read_text(),
    ):
        fail(
            "#215: wrap bits-ui Command in web/lib/components/ui/command/ — "
            "do not import Command from bits-ui in App.svelte"
        )

    raw_body = _app_keydown_body(app_clean) or _app_keydown_body(app)
    if not raw_body.strip():
        fail(
            "#215: App.svelte must handle window keydown (onKey) so ⌘K / "
            "Ctrl+K can open the command palette"
        )
    body = _expand_fn_calls(app_clean, raw_body)
    if body == raw_body:
        body = _expand_fn_calls(app, raw_body)
    prefix, tail = _split_people_only(raw_body)
    prefix_x = _expand_fn_calls(app_clean, prefix) if prefix.strip() else body
    if prefix_x == prefix:
        prefix_x = _expand_fn_calls(app, prefix) if prefix.strip() else body

    # 5) ⌘K / Ctrl+K from every view; INPUT guard lets k/K through; preventDefault.
    k_surface = _mod_k_windows(prefix_x)
    if not k_surface.strip():
        k_surface = _mod_k_windows(prefix)
    if not k_surface.strip():
        tail_k = _mod_k_windows(tail) if tail else ""
        if tail_k.strip() and not _mod_k_windows(prefix_x).strip():
            fail(
                "#215: ⌘K / Ctrl+K must run off People "
                "(it is after `if (view !== \"people\") return`)"
            )
        fail(
            "#215: App key handler must treat metaKey/ctrlKey + k/K as the "
            "command palette (from every view, including when an INPUT is focused)"
        )
    if not _has_mod_combo(k_surface) and not _has_mod_combo(prefix_x):
        fail(
            "#215: command palette must accept metaKey or ctrlKey "
            "(⌘K on macOS; ctrl+K so gates/tests see the fallback)"
        )
    if not _MOD_EITHER.search(k_surface) and not re.search(r"\bmod\b", k_surface):
        fail("#215: k/K palette must be a metaKey/ctrlKey combo, not a bare letter")
    if not re.search(r"altKey|\bmod\b", k_surface) and not re.search(
        r"altKey|\bmod\b", prefix
    ):
        fail(
            "#215: ⌘K / Ctrl+K must use the same AltGr-safe mod as #132 "
            "(metaKey or ctrlKey && !altKey)"
        )
    if not _PREVENT_DEFAULT.search(k_surface) and not _PREVENT_DEFAULT.search(prefix_x):
        fail(
            "#215: ⌘K / Ctrl+K must preventDefault "
            "(webview must not take the key)"
        )
    if not _PALETTE_OPEN_ASSIGN.search(k_surface) and not _PALETTE_OPEN_ASSIGN.search(
        prefix_x
    ):
        fail(
            "#215: ⌘K / Ctrl+K must open the command palette "
            "(set a command/palette flag or call openCommand/openPalette)"
        )
    if not _INPUT_TAG_GUARD.search(raw_body) and not _INPUT_TAG_GUARD.search(body):
        fail(
            "#215: keep the INPUT/TEXTAREA/SELECT guard "
            "(⌘K is an exception next to ⌘F; bare k still must not steal #q)"
        )
    guard_span = _input_guard_span(raw_body)
    if not guard_span:
        fail(
            "#215: INPUT/TEXTAREA/SELECT guard must still wrap the early return "
            "(add k/K next to ⌘F so the combo works from a field)"
        )
    guard = raw_body[guard_span[0] : guard_span[1] + 1]
    if not _KEY_CMD_K.search(guard) and not _KEY_K.search(guard):
        fail(
            "#215: INPUT guard must let ⌘K / Ctrl+K through "
            "(add k/K to the exception next to ⌘F)"
        )

    # 6) data-command-palette on the open palette surface.
    markup = _strip_html_comments(_svelte_markup(app))
    hook_ok = bool(_PALETTE_HOOK.search(markup) or _PALETTE_HOOK.search(app))
    if not hook_ok:
        hook_ok = bool(_PALETTE_HOOK.search(cmd_blob))
    if not hook_ok:
        for p in _product_svelte(crate):
            if _PALETTE_HOOK.search(p.read_text()):
                hook_ok = True
                break
    if not hook_ok:
        fail(
            "#215: open command palette surface must include data-command-palette"
        )

    surface = _palette_surface(crate, app, cmd_blob)
    surface_x = _expand_fn_calls(app_clean, surface) if surface.strip() else surface
    if surface_x == surface:
        surface_x = _expand_fn_calls(app, surface) if surface.strip() else surface

    # 7) View items: People, Search, Review, Import, Doctor.
    for label, tok in zip(_PALETTE_VIEW_LABELS, _VIEW_TAB_ORDER, strict=True):
        if not re.search(rf"\b{re.escape(label)}\b", surface):
            fail(
                f"#215: command palette must include a {label} view item "
                "(People / Search / Review / Import / Doctor)"
            )
        if not re.search(rf"[\"']{tok}[\"']", surface) and not re.search(
            rf"[\"']{tok}[\"']", surface_x
        ):
            fail(
                f'#215: choosing the {label} palette item must set view = "{tok}"'
            )

    # 8) Search path focuses #q (same idea as ⌘F / whenSearchPaneReady).
    if not _FOCUS_SEARCH_Q.search(surface_x) and not re.search(
        r"\bwhenSearchPaneReady\b", surface + "\n" + surface_x
    ):
        fail(
            "#215: choosing Search in the palette must focus #q "
            "(whenSearchPaneReady or getElementById(\"q\") — same path as ⌘F)"
        )

    # 9) Person items from the loaded people array; selectPerson + People view.
    if not _PALETTE_PEOPLE_SRC.search(surface) and not _PALETTE_PEOPLE_SRC.search(
        surface_x
    ):
        fail(
            "#215: palette person items must come from the loaded people array "
            "({#each people / people.map — not api.search / FTS)"
        )
    if not re.search(r"\b(?:display_name|personLabel)\b", surface) and not re.search(
        r"\b(?:display_name|personLabel)\b", surface_x
    ):
        fail(
            "#215: person item labels must use display_name / personLabel "
            "(same list as the sidebar)"
        )
    if not re.search(r"\bselectPerson\s*\(", surface) and not re.search(
        r"\bselectPerson\s*\(", surface_x
    ):
        fail(
            "#215: choosing a person in the palette must call selectPerson"
        )
    if not _VIEW_PEOPLE_ASSIGN.search(surface) and not _VIEW_PEOPLE_ASSIGN.search(
        surface_x
    ):
        fail(
            '#215: choosing a person in the palette must switch to People '
            '(view = "people")'
        )

    # 10) No api.search / FTS / HTTP / Spotlight from the palette.
    banned = _PALETTE_BANNED.search(surface) or _PALETTE_BANNED.search(cmd_blob)
    if banned:
        fail(
            "#215: command palette must stay local (loaded people + views) — "
            "no api.search / FTS / HTTP / Spotlight from the palette"
        )

    # 11) Esc closes the open palette; does not bounce the view; closed Esc stays.
    if not _KEY_ESC.search(raw_body) and not _KEY_ESC.search(body):
        fail("#215: Escape must close the open command palette")
    esc_surface = _windows_around(
        _without_input_guard(raw_body), _KEY_ESC, before=80, after=560
    )
    if not esc_surface.strip():
        esc_surface = _windows_around(raw_body, _KEY_ESC, before=80, after=560)
    esc_x = _expand_fn_calls(app_clean, esc_surface) or _expand_fn_calls(app, esc_surface)
    if not _PALETTE_OPEN_GATE.search(esc_surface) and not _PALETTE_OPEN_GATE.search(
        esc_x
    ):
        fail(
            "#215: Escape must close the open command palette "
            "(gate on the palette open flag / data-command-palette — "
            "do not steal Esc from INPUT when the palette is closed)"
        )
    if not _PALETTE_CLOSE_ASSIGN.search(esc_surface) and not _PALETTE_CLOSE_ASSIGN.search(
        esc_x
    ):
        fail(
            "#215: Escape when the palette is open must close it "
            "(command/palette flag = false) and return"
        )
    close_m = _PALETTE_CLOSE_ASSIGN.search(esc_surface) or _PALETTE_CLOSE_ASSIGN.search(
        esc_x
    )
    if close_m:
        blob = esc_surface if _PALETTE_CLOSE_ASSIGN.search(esc_surface) else esc_x
        after = blob[close_m.end() : close_m.end() + 240]
        view_m = _VIEW_PEOPLE_ASSIGN.search(after)
        if view_m and not re.search(r"\breturn\b", after[: view_m.start()]):
            fail(
                "#215: Esc must close the palette and return "
                "(do not also bounce the view to People)"
            )
    if esc_surface and _ESC_CLOSE_APP.search(esc_surface):
        fail("#215: Escape must not close the app (close the palette only)")
    if not _INPUT_BLUR.search(raw_body) and not _INPUT_BLUR.search(body):
        fail(
            "#215: keep Esc blur on INPUT when the palette is not open "
            "(do not steal Esc from #q / #person-filter)"
        )
    # Palette INPUT is an INPUT — Esc must still close when the palette is open.
    pre = raw_body[: guard_span[0]]
    if not (
        (_KEY_ESC.search(pre) and _PALETTE_CLOSE_ASSIGN.search(pre))
        or (
            _KEY_ESC.search(guard)
            and (
                _PALETTE_CLOSE_ASSIGN.search(guard) or _PALETTE_OPEN_GATE.search(guard)
            )
        )
    ):
        fail(
            "#215: Esc must close the open palette even when its INPUT is focused "
            "(handle it before the INPUT return, or let Escape through when open)"
        )

    # 12) Docs: ⌘K / Ctrl+K, person jump, Search → #q, Esc closes, local-only.
    if not dtxt.strip():
        fail(
            "#215: docs/user/app.md required — ⌘K / Ctrl+K command palette, "
            "person jump, Search → #q, Esc closes, local-only"
        )
    if not _DOCS_CMD_K.search(dtxt):
        fail(
            "#215: docs/user/app.md must document ⌘K / Ctrl+K "
            "(opens a local command palette)"
        )
    if not _DOCS_CMD_PALETTE.search(dtxt):
        fail("#215: docs/user/app.md must mention the command palette")
    if not _DOCS_PERSON_JUMP.search(dtxt):
        fail(
            "#215: docs/user/app.md must say you can type a person name to jump"
        )
    if not _DOCS_PALETTE_SEARCH_Q.search(dtxt):
        fail(
            "#215: docs/user/app.md must say Search in the palette focuses #q"
        )
    if not _DOCS_PALETTE_ESC.search(dtxt):
        fail("#215: docs/user/app.md must say Esc closes the command palette")
    if not _DOCS_PALETTE_LOCAL.search(dtxt):
        fail(
            "#215: docs/user/app.md must say the palette is local "
            "(loaded people + views), not archive full-text / Spotlight"
        )

    # 13) Do not soften ⌘F, ⌘1–5, #q, sidebar, overlay, inspector, CSP.
    if not _KEY_F.search(prefix_x) and not _KEY_F.search(raw_body):
        fail("#215: keep ⌘F / ctrl+F Find (do not rewrite #132)")
    if not _has_mod_combo(prefix_x) and not _has_mod_combo(raw_body):
        fail(
            "#215: keep metaKey or ctrlKey on Find / tab digits "
            "(do not rewrite #132 ⌘F / ⌘1–5)"
        )
    for tok in _VIEW_TAB_ORDER:
        if not re.search(rf"[\"']{tok}[\"']", prefix_x) and not re.search(
            rf"[\"']{tok}[\"']", raw_body
        ):
            fail(
                f'#215: keep ⌘1–5 view "{tok}" '
                "(1 People … 5 Doctor — do not rewrite #132)"
            )
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#215: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#215: keep data-people-sidebar (#159 / #212)")
    if not re.search(r"\bdata-person-inspector\b", app):
        fail("#215: keep data-person-inspector (#213)")
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#215: keep the overlay titlebar (#211)")
    if CSP not in conf:
        fail("#215: do not soften tauri CSP")


def assert_command_palette_people_cap(crate: Path) -> None:
    """#215: palette people items are filtered + capped (≤32), not {#each people}.

    CommandPalette / data-command-palette / command/ chrome only — not the
    sidebar {#each filtered}. Do not rewrite assert_command_palette.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#215: App.svelte required (command palette people cap)")
    app = _web_logic(crate)
    cmd_blob = _command_dir_blob(_command_ui_dir(crate))
    surface = _palette_surface(crate, app, cmd_blob)
    pal_path = crate / "web" / "lib" / "CommandPalette.svelte"
    if pal_path.is_file():
        surface = surface + "\n" + pal_path.read_text()
    cleaned = _without_comments(surface)

    # 1) Do not mount the raw loaded array as Command.Item rows.
    if _PALETTE_RAW_PEOPLE_EACH.search(cleaned):
        fail(
            "#215: command palette must not mount the raw people array "
            "({#each people as / {#each people () — filter the loaded list "
            "and render at most 32"
        )

    # 2) Filter / slice the loaded people array (not sidebar filtered).
    has_people = bool(
        re.search(r"\bpeople\b", cleaned) or _PALETTE_PEOPLE_SRC.search(cleaned)
    )
    has_filter_or_slice = bool(
        _PALETTE_PEOPLE_FILTER.search(cleaned)
        or re.search(r"\.\s*(?:filter|slice)\s*\(", cleaned)
    )
    if not (_PALETTE_PEOPLE_FILTER.search(cleaned) or (has_people and has_filter_or_slice)):
        fail(
            "#215: palette people items must come from people.filter "
            "(or people + .filter( / .slice() of the loaded array) — "
            "not the full list"
        )

    # 3) Numeric cap ≤32: slice(0, N) or PALETTE_PEOPLE_CAP / similar.
    if not _palette_people_cap_ok(cleaned):
        fail(
            "#215: palette people items must be capped at ≤32 "
            "(slice(0, N) with N<=32, or PALETTE_PEOPLE_CAP / similar)"
        )

    # 4) Keep #215 person jump: labels, selectPerson, People view.
    surface_x = _expand_fn_calls(app, surface) if surface.strip() else surface
    if not re.search(r"\b(?:display_name|personLabel)\b", cleaned) and not re.search(
        r"\b(?:display_name|personLabel)\b", surface_x
    ):
        fail(
            "#215: person item labels must use display_name / personLabel "
            "(same list as the sidebar)"
        )
    if not re.search(r"\bselectPerson\s*\(", cleaned) and not re.search(
        r"\bselectPerson\s*\(", surface_x
    ):
        fail(
            "#215: choosing a person in the palette must call selectPerson"
        )
    if not _VIEW_PEOPLE_ASSIGN.search(cleaned) and not _VIEW_PEOPLE_ASSIGN.search(
        surface_x
    ):
        fail(
            '#215: choosing a person in the palette must switch to People '
            '(view = "people")'
        )

    # 5) Still local — no api.search / FTS / HTTP / Spotlight.
    banned = _PALETTE_BANNED.search(cleaned) or _PALETTE_BANNED.search(cmd_blob)
    if banned:
        fail(
            "#215: command palette must stay local (loaded people + views) — "
            "no api.search / FTS / HTTP / Spotlight from the palette"
        )

from tauri_gate.palette_more import (
    assert_command_palette_field_keys,
    assert_command_palette_clipboard,
)
