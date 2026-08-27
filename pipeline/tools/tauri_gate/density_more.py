"""Additional density asserts."""
from __future__ import annotations

from tauri_gate.density_steps import *
from tauri_gate.density_chrome import *


def assert_light_chrome(crate: Path) -> None:
    """#277: leftover chrome readable in system light via named --chrome-* vars.

    Six surfaces (people preview, data-platform-chip, data-person-inspector,
    data-review-card, data-command-palette, data-toast) use dedicated leftovers,
    not only generic muted. No amber/yellow. Dark media keeps the current
    --color-background / --search-mark / --color-warning strings. No Theme
    menu. Docs: leftover chrome readable in system light; dark archival.
    Do not rewrite #198 / #217 / #218 / #219 / #276.
    """
    css_path = crate / "web" / "app.css"
    if not css_path.is_file():
        fail("#277: web/app.css required (named leftover-chrome light vars)")
    css = css_path.read_text()
    css_clean = _css_without_comments(css)
    light_blob = _contrast_light_blob(css)
    dark_blob = _contrast_dark_blob(css)

    # 1) Named leftover-chrome CSS variables in light (@theme / non-dark :root).
    defs = _chrome_light_defs(css)
    by_fam = _chrome_by_family(defs)
    if not defs:
        fail(
            "#277: named leftover-chrome CSS variables required in light "
            "(@theme / non-dark :root) — `--chrome-preview-fg`, "
            "`--chrome-chip-bg` / `--chrome-chip-fg`, `--chrome-inspector-fg`, "
            "`--chrome-review-card`, `--chrome-palette`, `--chrome-toast` "
            "(names may vary; must be `--chrome-*` or equivalent dedicated "
            "leftovers, not only generic `--color-muted`)"
        )
    missing = [fam for fam in _CHROME_FAMILIES if not by_fam[fam]]
    if missing:
        examples = ", ".join(
            ex
            for fam, ex in zip(_CHROME_FAMILIES, _CHROME_FAMILY_EXAMPLES)
            if fam in missing
        )
        fail(
            "#277: light leftover-chrome vars must cover preview, chips, "
            "inspector, review, palette, and toast "
            f"(missing: {', '.join(missing)}; e.g. {examples}) — "
            "not only generic `--color-muted`"
        )
    generic_fams = [
        fam
        for fam, names in by_fam.items()
        if names and all(_chrome_value_is_generic(defs[n], light_blob) for n in names)
    ]
    if generic_fams:
        fail(
            "#277: leftover-chrome light vars must be dedicated leftovers "
            "(not only aliases of `--color-muted` / `--color-muted-foreground` "
            f"/ `--color-background`); generic-only families: "
            + ", ".join(generic_fams)
        )

    # 2) The six surfaces use those vars.
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#277: App.svelte required (people preview / chips / inspector)")
    app = _web_logic(crate)
    review_path = crate / "web" / "lib" / "ReviewPane.svelte"
    review = review_path.read_text() if review_path.is_file() else ""
    pal_path = crate / "web" / "lib" / "CommandPalette.svelte"
    pal = pal_path.read_text() if pal_path.is_file() else ""
    toast_path = crate / "web" / "lib" / "components" / "ui" / "toast" / "toast.svelte"
    toast = toast_path.read_text() if toast_path.is_file() else ""
    svelte_blob = "\n".join(p.read_text() for p in _product_svelte(crate))
    hook_src = {
        "chip": svelte_blob,
        "inspector": app,
        "review": review or svelte_blob,
        "palette": pal or svelte_blob,
        "toast": toast or svelte_blob,
    }

    preview_blob = _chrome_preview_blob(app) or _chrome_preview_blob(svelte_blob)
    if not preview_blob.strip():
        fail(
            "#277: people preview / last-activity line required "
            "(wire `--chrome-preview-fg` or equivalent, not only muted)"
        )
    if not _chrome_blob_uses_vars(
        preview_blob, css_clean, "", by_fam["preview"]
    ):
        fail(
            "#277: people preview must use a named leftover-chrome var "
            "(`--chrome-preview-fg` / `var(--chrome-preview-*)` / "
            "`text-chrome-preview-fg`) — not only `text-muted-foreground`"
        )

    for fam, hook in _CHROME_HOOKS:
        blob = _chrome_hook_blob(hook_src[fam], hook)
        if not blob.strip() or hook not in blob:
            fail(
                f"#277: {hook} required (wire `--chrome-{fam}*` leftover, "
                "not only generic muted / background)"
            )
        if not _chrome_blob_uses_vars(blob, css_clean, hook, by_fam[fam]):
            fail(
                f"#277: {hook} must use a named leftover-chrome var "
                f"(`--chrome-{fam}*`) — not only generic muted / background"
            )

    # 3) No amber-* / yellow-* in product Svelte.
    svelte_files = _product_svelte(crate)
    if not svelte_files:
        fail("#277: crates/interlace-tauri/web/**/*.svelte required (light chrome)")
    offenders: list[str] = []
    for p in svelte_files:
        hits = [
            h
            for h in _hue_findings(p.read_text())
            if h.startswith("amber") or h.startswith("yellow")
        ]
        if hits:
            offenders.append(f"{p.relative_to(crate)}: {'; '.join(hits)}")
    if offenders:
        fail(
            "#277: product Svelte must not contain amber-* / yellow-* "
            "(CSS variables only). Found:\n  " + "\n  ".join(offenders)
        )

    # 4) Dark media still has the current dark strings (dark unchanged).
    if not dark_blob.strip():
        fail(
            "#277: keep @media (prefers-color-scheme: dark) — "
            "dark is unchanged (archival look)"
        )
    if not _CHROME_DARK_BG.search(dark_blob):
        fail(
            "#277: dark @media must keep the current "
            "`--color-background: hsl(240 10% 3.9%)` (dark unchanged)"
        )
    if not _CHROME_DARK_MARK.search(dark_blob):
        fail(
            "#277: dark @media must keep `--search-mark` "
            "(dark unchanged; do not drop #217)"
        )
    if not _CHROME_DARK_MARK_VAL.search(dark_blob):
        fail(
            "#277: dark @media must keep the current "
            "`--search-mark: hsl(45 93% 32% / 0.6)` (dark unchanged)"
        )
    if not _CHROME_DARK_WARN.search(dark_blob):
        fail(
            "#277: dark @media must keep `--color-warning` "
            "(dark unchanged; do not drop #219)"
        )
    if not _CHROME_DARK_WARN_VAL.search(dark_blob):
        fail(
            "#277: dark @media must keep the current "
            "`--color-warning: hsl(38 48% 70%)` (dark unchanged)"
        )

    # 5) No Theme / Appearance menu / data-theme.
    theme_hits: list[str] = []
    for p in svelte_files:
        surface = _hue_surface(p.read_text())
        if _APPEARANCE_THEME_UI.search(surface) or _APPEARANCE_MENU_LABEL.search(surface):
            theme_hits.append(str(p.relative_to(crate)))
    rust_path = crate / "src" / "main.rs"
    rust = rust_path.read_text() if rust_path.is_file() else ""
    rust_surface = _without_comments(rust)
    if _APPEARANCE_THEME_UI.search(rust_surface) or _APPEARANCE_MENU_LABEL.search(
        rust_surface
    ):
        theme_hits.append("src/main.rs")
    if theme_hits:
        fail(
            "#277: not in scope — no Theme / Appearance menu / data-theme "
            "(OS appearance only; leftover chrome is CSS variables). Found in: "
            + ", ".join(theme_hits)
        )

    # 6) Docs: leftover chrome readable in system light; dark archival;
    #    no Theme menu.
    docs_path = repo_root() / "docs" / "user" / "app.md"
    if not docs_path.is_file():
        fail(
            "#277: docs/user/app.md required — leftover chrome readable in "
            "system light; dark archival; no Theme menu"
        )
    dtxt = docs_path.read_text()
    if not _DOCS_LEFTOVER_CHROME.search(dtxt) and not _DOCS_LEFTOVER_SURFACES.search(
        dtxt
    ):
        fail(
            "#277: docs/user/app.md must say leftover chrome "
            "(preview, chips, inspector, review, palette, toasts) "
            "is readable in system light"
        )
    if not _DOCS_LIGHT_READABLE.search(dtxt):
        fail(
            "#277: docs/user/app.md must say leftover chrome is readable "
            "in system light"
        )
    if not _APPEARANCE_DOCS_ARCHIVAL.search(dtxt):
        fail("#277: docs/user/app.md must say dark stays the archival look")
    if not _APPEARANCE_DOCS_NO_THEME.search(dtxt):
        fail("#277: docs/user/app.md must say there is no Theme menu")

    # Keep #217 muted L / search-mark, #218 color-scheme, #219 warning,
    # #276 density. Do not rewrite those asserts.
    light_muted = _css_var(light_blob, ("--color-muted-foreground",))
    if not light_muted or not _hsl_tuple(light_muted):
        fail("#277: keep #217 light --color-muted-foreground (HSL)")
    if (_hsl_tuple(light_muted) or (0, 0, 99))[2] > 40:
        fail("#277: keep #217 light --color-muted-foreground HSL L ≤ 40")
    if not _css_var(light_blob, _CONTRAST_SEARCH_MARK_NAMES) or not _css_var(
        dark_blob, _CONTRAST_SEARCH_MARK_NAMES
    ):
        fail("#277: keep #217 --search-mark in light and dark")
    if not _CONTRAST_COLOR_SCHEME.search(css):
        fail("#277: keep #218 color-scheme: light dark on :root / html")
    if not _css_var(light_blob, _STATUS_WARNING_NAMES):
        fail("#277: keep #219 --warning / --color-warning in light")
    web = app + "\n" + pal + "\n" + css_clean
    if not _DENSITY_HOOK.search(web) and not _DENSITY_IDENT.search(web):
        fail("#277: keep #276 local density (`data-density` / fontDensity)")
