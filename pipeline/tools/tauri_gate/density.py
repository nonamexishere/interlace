"""Font-density / light-chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.density_steps import *
from tauri_gate.density_chrome import *


def assert_font_density(crate: Path) -> None:
    """#276: local Default / Comfortable density; persist in localStorage.

    Comfortable enlarges timeline bubble bodies without a reload
    (data-density / CSS variable / class on html/body). Keep the
    system font. No Theme / Appearance menu (#218). Reduced motion
    unchanged (#222). No remote/webfont, no per-bubble font picker.
    Docs: local density; no reload; system font; OS appearance;
    no Theme menu.
    Follow-up: density change wipes the timeline height cache
    (clearPendingMeasures + rowHeights = {}). Keep VIRTUALIZE_AFTER,
    data-bubble-body, no location.reload.
    Do not rewrite #199 / #218 / #222 / #212 / #275.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#276: App.svelte required (local density control)")
    css_path = crate / "web" / "app.css"
    if not css_path.is_file():
        fail("#276: web/app.css required (system font + density size)")
    app = _web_logic(crate)
    css = css_path.read_text()
    pal_path = crate / "web" / "lib" / "CommandPalette.svelte"
    pal = pal_path.read_text() if pal_path.is_file() else ""
    web_raw = _density_web_src(crate)
    web = _without_comments(web_raw)
    app_clean = _without_comments(app)
    pal_clean = _without_comments(pal)
    css_clean = _css_without_comments(css)

    # 1) A local density control exists (Default / Comfortable or Compact /
    #    Comfortable). Quiet chrome and/or a command-palette item.
    if not _density_has_control(web):
        fail(
            "#276: a local density control is required "
            "(Default / Comfortable or Compact / Comfortable) — "
            "quiet chrome (`data-density` / `data-density-toggle`) "
            "and/or a command-palette item, not a Theme / Appearance menu"
        )

    # 2) At least two steps.
    if not _density_has_two_steps(web):
        fail(
            "#276: density control must have at least two steps "
            "(Default / Comfortable or Compact / Comfortable)"
        )

    # 3) Surface is quiet chrome and/or the command palette — not a Theme menu.
    chrome_ok = bool(
        _DENSITY_HOOK.search(app_clean)
        or _DENSITY_CHROME.search(app_clean)
        or _DENSITY_IDENT.search(app_clean)
        or _DENSITY_STATE.search(app_clean)
        or _DENSITY_VALUE.search(app_clean)
        or _DENSITY_LABEL.search(app_clean)
    )
    palette_ok = bool(
        _DENSITY_HOOK.search(pal_clean)
        or _DENSITY_PALETTE_ITEM.search(pal_clean)
        or _DENSITY_IDENT.search(pal_clean)
        or _DENSITY_VALUE.search(pal_clean)
        or _DENSITY_LABEL.search(pal_clean)
        or _DENSITY_STEP_COMFORTABLE.search(pal_clean)
    )
    if not chrome_ok and not palette_ok:
        fail(
            "#276: density control must be quiet chrome and/or a "
            "command-palette item — not a Theme / Appearance menu"
        )

    # 4) Persist in namespaced localStorage (getItem + setItem).
    ls_keys = _ls_pref_keys(web)
    density_keys = [k for k in ls_keys if _density_key_ok(k)]
    persist_bits = [
        _windows_around(web, re.compile(r"localStorage"), before=160, after=220),
        _windows_around(web, _DENSITY_WORD, before=160, after=220),
        _windows_around(web, _DENSITY_VALUE, before=160, after=220),
    ]
    persist_surface = "\n".join(persist_bits)
    if not density_keys:
        fail(
            "#276: persist density in namespaced localStorage "
            "(getItem + setItem; e.g. interlace.density) — "
            "not config.toml / write_last_path"
        )
    if not re.search(r"localStorage\s*\.\s*setItem\s*\(", persist_surface):
        fail(
            "#276: persist density with localStorage.setItem "
            "(namespaced key; not iCloud, not write_last_path)"
        )
    if not re.search(r"localStorage\s*\.\s*getItem\s*\(", persist_surface) and not _LS_BRACKET.search(
        persist_surface
    ):
        fail(
            "#276: restore density from localStorage.getItem "
            "(same namespaced key)"
        )

    # 5) Do not write density to config.toml / write_last_path.
    if _LAST_PATH_API.search(persist_surface) or _CONFIG_TOML.search(persist_surface):
        fail(
            "#276: do not persist density via write_last_path / "
            "read_last_path / config.toml (localStorage only)"
        )
    session_path = repo_root() / "crates" / "interlace-core" / "src" / "session.rs"
    rust_path = crate / "src" / "main.rs"
    session = session_path.read_text() if session_path.is_file() else ""
    rust = rust_path.read_text() if rust_path.is_file() else ""
    if session_path.is_file():
        wl = _rust_fn_body(_without_comments(session), "write_last_path")
        if _DENSITY_WORD.search(wl) or any(
            "density" in k.lower() for k in _toml_keys_in_fn(wl)
        ):
            fail(
                "#276: do not rewrite session.rs write_last_path to dump "
                "density (config.toml is the last-archive pointer, not chrome prefs)"
            )
    rust_clean = _without_comments(session + "\n" + rust)
    for m in _DENSITY_WORD.finditer(rust_clean):
        window = rust_clean[max(0, m.start() - 360) : m.end() + 360]
        if _LAST_PATH_API.search(window) or _CONFIG_TOML.search(window):
            fail(
                "#276: do not persist density via write_last_path / "
                "read_last_path / config.toml (localStorage only)"
            )

    # 6) Comfortable / larger step changes bubble body size. No reload.
    apply_src = app_clean + "\n" + pal_clean + "\n" + css_clean + "\n" + web
    if not _DENSITY_APPLY.search(apply_src):
        fail(
            "#276: Comfortable must change timeline bubble body size via "
            "`data-density` / a CSS variable / a class on html/body "
            "(or the bubble) — apply without a reload"
        )
    if not (
        _density_css_bumps_body(css_clean)
        or _BUBBLE_DENSITY_CLASS.search(web)
    ):
        fail(
            "#276: Comfortable / the larger step must change timeline "
            "bubble body size (CSS `[data-density=…]` / `--bubble-body` "
            "variable / density class on the bubble)"
        )
    if "data-bubble-body" not in web:
        fail(
            "#276: keep data-bubble-body — Comfortable enlarges timeline "
            "bubble bodies"
        )
    density_set = "\n".join(
        [
            persist_surface,
            _windows_around(web, _DENSITY_HOOK, before=160, after=240),
            _windows_around(web, _DENSITY_APPLY, before=160, after=240),
        ]
    )
    if _DENSITY_RELOAD.search(density_set) or _DENSITY_RELOAD.search(
        _windows_around(web, _DENSITY_WORD, before=200, after=240)
    ):
        fail(
            "#276: density must apply without a reload (no location.reload)"
        )

    # 7) Keep the system font. No remote / webfont.
    fm = _TYPO_FONT_SANS.search(css)
    if not fm:
        fail("#276: keep --font-sans as the system UI stack (font-sans / --font-sans)")
    stack = fm.group(1)
    if "ui-sans-serif" not in stack or "-apple-system" not in stack:
        fail(
            "#276: --font-sans must stay system UI "
            "(ui-sans-serif and -apple-system still present)"
        )
    if "font-sans" not in css_clean and "var(--font-sans)" not in css_clean:
        fail("#276: keep font-sans / var(--font-sans) as the system stack")
    svelte_files = _product_svelte(crate)
    font_blob = css_clean + "\n" + "\n".join(
        _hue_surface(p.read_text()) for p in svelte_files
    )
    splash = crate / "index.html"
    if splash.is_file():
        font_blob += "\n" + splash.read_text()
    if (
        _TYPO_REMOTE_FONT.search(font_blob)
        or _THEME_CDN.search(font_blob)
        or _DENSITY_FONT_FACE_HTTP.search(font_blob)
    ):
        fail(
            "#276: no remote/webfont "
            "(fonts.googleapis / @font-face url http) — keep the system font"
        )

    # 8) Keep #218: no Theme / Appearance menu / data-theme.
    #    Keep color-scheme: light dark.
    svelte_files = svelte_files or _product_svelte(crate)
    theme_hits: list[str] = []
    for p in svelte_files:
        surface = _hue_surface(p.read_text())
        if _APPEARANCE_THEME_UI.search(surface) or _APPEARANCE_MENU_LABEL.search(surface):
            theme_hits.append(str(p.relative_to(crate)))
    rust_surface = _without_comments(rust)
    if _APPEARANCE_THEME_UI.search(rust_surface) or _APPEARANCE_MENU_LABEL.search(
        rust_surface
    ):
        theme_hits.append("src/main.rs")
    if theme_hits:
        fail(
            "#276: keep #218 — no Theme / Appearance menu / data-theme "
            "(density is not a color theme). Found in: "
            + ", ".join(theme_hits)
        )
    if not _CONTRAST_COLOR_SCHEME.search(css):
        fail(
            "#276: keep color-scheme: light dark on :root / html "
            "(#218; OS appearance flips without a reload)"
        )

    # 9) Keep #222 reduced motion. No per-bubble font picker.
    js_blob = _motion_js_blob(crate)
    if not _MOTION_JS_REDUCE.search(js_blob):
        fail(
            "#276: keep #222 reduced motion "
            "(matchMedia / MediaQuery / prefersReducedMotion)"
        )
    if not _MOTION_DURATION_ZERO.search(js_blob):
        fail("#276: keep #222 reduced-motion duration 0")
    if _PER_BUBBLE_FONT.search(web):
        fail(
            "#276: no per-bubble font picker "
            "(one local density control, not a font per message)"
        )

    # 10) Docs: local Default / Comfortable; enlarges bubble bodies
    #     without reload; system font; OS appearance; no Theme menu.
    docs_path = repo_root() / "docs" / "user" / "app.md"
    if not docs_path.is_file():
        fail(
            "#276: docs/user/app.md required — local Default / Comfortable "
            "density; enlarges bubble bodies without reload; system font; "
            "OS appearance; no Theme menu"
        )
    dtxt = docs_path.read_text()
    if not _DOCS_DENSITY_STEPS.search(dtxt) or not _DOCS_LOCAL_DENSITY.search(dtxt):
        fail(
            "#276: docs/user/app.md must say local Default / Comfortable "
            "(or Compact / Comfortable) density"
        )
    if not _DOCS_DENSITY_BODIES.search(dtxt):
        fail(
            "#276: docs/user/app.md must say density enlarges bubble bodies"
        )
    if not _DOCS_DENSITY_NO_RELOAD.search(dtxt):
        fail(
            "#276: docs/user/app.md must say density enlarges bubble bodies "
            "without a reload"
        )
    if not _DOCS_TYPO_NO_REMOTE_FONT.search(dtxt):
        fail(
            "#276: docs/user/app.md must say system font / no remote font"
        )
    if not _CONTRAST_DOCS_SYSTEM.search(dtxt):
        fail(
            "#276: docs/user/app.md must say the app follows OS / system appearance"
        )
    if not _APPEARANCE_DOCS_NO_THEME.search(dtxt):
        fail("#276: docs/user/app.md must say there is no Theme menu")

    # 11) Density change wipes the timeline height cache.
    persist_x, density_change = _density_change_blobs(app_clean, web)
    if not _density_path_wipes(density_change):
        if persist_x and _density_persist_only_pref(persist_x):
            fail(
                "#276: persistDensity must wipe the timeline height cache "
                "(clearPendingMeasures + rowHeights = {}) — "
                "do not only write density / localStorage; Comfortable "
                "changes bubble heights and stale rowHeights jump a "
                "virtualized list"
            )
        fail(
            "#276: persistDensity (or a density $effect) must wipe the "
            "timeline height cache (clearPendingMeasures + rowHeights = {}) "
            "when density changes"
        )

    # 12) Keep VIRTUALIZE_AFTER = 250, data-bubble-body, no location.reload.
    if not _DENSITY_VIRTUALIZE_AFTER.search(app_clean):
        fail(
            "#276: keep VIRTUALIZE_AFTER = 250 — density must not turn off "
            "or retune #224 virtualize-after-250"
        )
    if "data-bubble-body" not in web:
        fail(
            "#276: keep data-bubble-body — Comfortable enlarges timeline "
            "bubble bodies (density wipe is not a reason to drop the hook)"
        )
    if _DENSITY_RELOAD.search(density_change) or _DENSITY_RELOAD.search(
        _windows_around(web, _DENSITY_WORD, before=200, after=240)
    ):
        fail(
            "#276: density must apply without a reload (no location.reload) "
            "— wipe rowHeights in-process"
        )

from tauri_gate.density_more import assert_light_chrome
