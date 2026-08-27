"""Additional palette asserts."""
from __future__ import annotations

from tauri_gate.palette_lib import *


def assert_command_palette_field_keys(crate: Path) -> None:
    """#215: palette field keeps Ctrl/⌘A; chrome shortcuts do not steal keys from [data-command-palette]."""
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#215: App.svelte required (palette field keys)")
    app = _web_logic(crate)
    app_clean = _without_comments(app)
    raw_body = _app_keydown_body(app_clean) or _app_keydown_body(app)
    if not raw_body.strip():
        fail(
            "#215: App.svelte must handle window keydown (onKey) so the "
            "palette field can keep Ctrl/⌘A"
        )

    # 1) After Esc-close, return when commandOpen + target in [data-command-palette]
    #    — before ⌘K commandOpen=true / ⌘F whenSearchPaneReady.
    chrome_at = _palette_chrome_shortcut_at(raw_body)
    prefix = raw_body[:chrome_at]
    prefix_x = _expand_fn_calls(app_clean, prefix) if prefix.strip() else prefix
    if prefix_x == prefix:
        prefix_x = _expand_fn_calls(app, prefix) if prefix.strip() else prefix
    esc_end = _palette_esc_close_end(raw_body)
    region = raw_body[esc_end:chrome_at] if esc_end is not None else prefix
    if not (
        _in_palette_skip_ok(prefix, region) or _in_palette_skip_ok(prefix_x, region)
    ):
        fail(
            "#215: after Esc-close, onKey must return when commandOpen and "
            "the target is inside [data-command-palette] (before ⌘K / ⌘F — "
            "chrome must not steal field keys)"
        )

    # 2) Palette surface handles meta/ctrl + a/A and select()s the field.
    cmd_blob = _command_dir_blob(_command_ui_dir(crate))
    surface = _palette_surface(crate, app, cmd_blob)
    pal_path = crate / "web" / "lib" / "CommandPalette.svelte"
    if pal_path.is_file():
        surface = surface + "\n" + pal_path.read_text()
    surface_x = _expand_fn_calls(surface, surface) if surface.strip() else surface
    a_surface = _mod_a_windows(surface) or _mod_a_windows(surface_x)
    if not a_surface.strip():
        fail(
            "#215: palette field must handle meta/ctrl + a/A "
            "(select all in [data-command-palette])"
        )
    if not _PALETTE_SELECT_ALL.search(a_surface) and not _PALETTE_SELECT_ALL.search(
        surface
    ):
        fail(
            "#215: palette field Ctrl/⌘A must select() the text "
            "(or setSelectionRange) so WKWebView Select All works"
        )

    # 3) INPUT guard still lets k/K through (⌘K from #q / #person-filter).
    if not _INPUT_TAG_GUARD.search(raw_body):
        fail(
            "#215: keep the INPUT/TEXTAREA/SELECT guard "
            "(⌘K from #q must still open the palette)"
        )
    guard_span = _input_guard_span(raw_body)
    if not guard_span:
        fail(
            "#215: INPUT/TEXTAREA/SELECT guard must still wrap the early return "
            "(k/K stays an exception so ⌘K works from #q)"
        )
    guard = raw_body[guard_span[0] : guard_span[1] + 1]
    if not _KEY_CMD_K.search(guard) and not _KEY_K.search(guard):
        fail(
            "#215: INPUT guard must still let k/K through "
            "(⌘K from #q / #person-filter must still open the palette)"
        )

    # 4) Esc still closes the open palette.
    if not _KEY_ESC.search(raw_body):
        fail("#215: Escape must still close the open command palette")
    if not _PALETTE_CLOSE_ASSIGN.search(raw_body):
        fail(
            "#215: Escape must still close the open palette "
            "(commandOpen = false / closeCommand)"
        )


def assert_command_palette_clipboard(crate: Path) -> None:
    """#215: palette field Ctrl/⌘C / V / X via navigator.clipboard (no plugin)."""
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#215: App.svelte required (palette field clipboard)")
    app = _web_logic(crate)
    cmd_blob = _command_dir_blob(_command_ui_dir(crate))
    surface = _palette_surface(crate, app, cmd_blob)
    pal_path = crate / "web" / "lib" / "CommandPalette.svelte"
    if pal_path.is_file():
        surface = surface + "\n" + pal_path.read_text()
    surface_x = _expand_fn_calls(surface, surface) if surface.strip() else surface

    # 1) Palette field: meta/ctrl + c/C → clipboard.writeText (copy).
    c_surface = _mod_c_windows(surface) or _mod_c_windows(surface_x)
    if not c_surface.strip():
        fail(
            "#215: palette field must handle meta/ctrl + c/C "
            "(clipboard.writeText / navigator.clipboard.writeText)"
        )
    if not _WRITE_TEXT.search(c_surface) and not _WRITE_TEXT.search(surface):
        fail(
            "#215: palette field Ctrl/⌘C must call clipboard.writeText "
            "(or navigator.clipboard.writeText) — no clipboard plugin"
        )

    # 2) Palette field: meta/ctrl + v/V → clipboard.readText (paste).
    v_surface = _mod_v_windows(surface) or _mod_v_windows(surface_x)
    if not v_surface.strip():
        fail(
            "#215: palette field must handle meta/ctrl + v/V "
            "(clipboard.readText / navigator.clipboard.readText)"
        )
    if not _PALETTE_READ_TEXT.search(v_surface) and not _PALETTE_READ_TEXT.search(
        surface
    ):
        fail(
            "#215: palette field Ctrl/⌘V must call clipboard.readText "
            "(or navigator.clipboard.readText) — no clipboard plugin"
        )

    # 3) Palette field: meta/ctrl + x/X → clipboard.writeText (cut).
    x_surface = _mod_x_windows(surface) or _mod_x_windows(surface_x)
    if not x_surface.strip():
        fail(
            "#215: palette field must handle meta/ctrl + x/X "
            "(cut via clipboard.writeText / navigator.clipboard.writeText)"
        )
    if not _WRITE_TEXT.search(x_surface) and not _WRITE_TEXT.search(surface):
        fail(
            "#215: palette field Ctrl/⌘X must call clipboard.writeText "
            "(or navigator.clipboard.writeText) so cut copies the selection"
        )

    # 4) Still Ctrl/⌘A select() / setSelectionRange (do not drop #215-keys).
    a_surface = _mod_a_windows(surface) or _mod_a_windows(surface_x)
    if not a_surface.strip():
        fail(
            "#215: palette field must still handle meta/ctrl + a/A "
            "(do not drop #215-keys select-all)"
        )
    if not _PALETTE_SELECT_ALL.search(a_surface) and not _PALETTE_SELECT_ALL.search(
        surface
    ):
        fail(
            "#215: palette field Ctrl/⌘A must still select() the text "
            "(or setSelectionRange)"
        )

    # 5) No tauri-plugin-clipboard* / clipboard-manager in package.json / Cargo.toml.
    pkg_path = crate / "package.json"
    pkg = pkg_path.read_text() if pkg_path.is_file() else ""
    toml_path = crate / "Cargo.toml"
    toml = toml_path.read_text() if toml_path.is_file() else ""
    if _CLIPBOARD_PLUGIN.search(pkg) or _CLIPBOARD_PLUGIN.search(toml):
        fail(
            "#215: do not add tauri-plugin-clipboard / plugin-clipboard-manager "
            "/ clipboard-manager (use navigator.clipboard on the palette field)"
        )

    # 6) Still local — no api.search / FTS / HTTP / Spotlight.
    banned = _PALETTE_BANNED.search(surface) or _PALETTE_BANNED.search(cmd_blob)
    if banned:
        fail(
            "#215: command palette must stay local (loaded people + views) — "
            "no api.search / FTS / HTTP / Spotlight from the palette"
        )
