"""Additional contrast asserts."""
from __future__ import annotations

from tauri_gate.contrast_lib import *


def assert_appearance_os(crate: Path) -> None:
    """#218: OS appearance only — named overlay/scrim, no Theme menu / network theme."""
    svelte_files = _product_svelte(crate)
    if not svelte_files:
        fail("#218: crates/interlace-tauri/web/**/*.svelte required (OS appearance)")

    svelte_blob = "\n".join(p.read_text() for p in svelte_files)
    rust_path = crate / "src" / "main.rs"
    rust = rust_path.read_text() if rust_path.is_file() else ""
    css_path = crate / "web" / "app.css"
    if not css_path.is_file():
        fail("#218: web/app.css required (named overlay / lightbox scrim)")
    css = css_path.read_text()
    index_path = crate / "index.html"
    index = index_path.read_text() if index_path.is_file() else ""

    # 1) No Theme / Appearance menu / data-theme / theme-picker.
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
            "#218: no Theme / Appearance menu / data-theme / theme-picker "
            "(system appearance is the only switch). Found in: "
            + ", ".join(theme_hits)
        )

    # 2) No fetch( / HTTP / https:// theme load.
    net_blob = (
        _hue_surface(svelte_blob)
        + "\n"
        + _css_without_comments(css)
        + "\n"
        + _without_comments(index)
        + "\n"
        + rust_surface
    )
    if _APPEARANCE_FETCH.search(net_blob):
        fail(
            "#218: do not fetch( a theme — appearance is OS-only "
            "(no HTTP theme load)"
        )
    if _THEME_CDN.search(net_blob) or _APPEARANCE_THEME_HTTP.search(net_blob):
        fail(
            "#218: do not load a theme from https:// / CDN / @import "
            "(system appearance only)"
        )

    # 3) --overlay or --scrim / --lightbox-scrim; dialog + .photo-lightbox use var(...).
    if not _css_var(css, _APPEARANCE_SCRIM_NAMES):
        fail(
            "#218: app.css must define --overlay or --scrim / --lightbox-scrim "
            "so dialog overlay and .photo-lightbox use var(...) "
            "(not bg-black/50 or a one-off hsl scrim)"
        )
    lightbox_rules = _photo_lightbox_rule_bodies(css)
    if not lightbox_rules:
        fail("#218: .photo-lightbox rule required (named overlay / lightbox scrim)")
    if not any(_APPEARANCE_SCRIM_VAR.search(body) for body in lightbox_rules):
        fail(
            "#218: .photo-lightbox must use var(--overlay) / var(--scrim) / "
            "var(--lightbox-scrim) (not a one-off hsl scrim)"
        )
    dialog_path = (
        crate / "web" / "lib" / "components" / "ui" / "dialog" / "dialog-content.svelte"
    )
    if not dialog_path.is_file():
        fail("#218: dialog-content.svelte required (dialog overlay uses var(...))")
    dialog_src = dialog_path.read_text()
    overlay_tag = _appearance_overlay_tag(dialog_src)
    if not overlay_tag:
        fail(
            "#218: Dialog overlay (DialogPrimitive.Overlay) required "
            "(use var(--overlay) / var(--scrim) / var(--lightbox-scrim))"
        )
    if not _appearance_tag_uses_scrim(overlay_tag, css):
        fail(
            "#218: dialog overlay (dialog-content.svelte) must use "
            "var(--overlay) / var(--scrim) / var(--lightbox-scrim)"
        )

    # 4) No bg-black/50 / black/70 / bg-black/80 on overlay or lightbox buttons.
    if _APPEARANCE_BLACK_WASH.search(overlay_tag):
        fail(
            "#218: Dialog overlay must not use bg-black/50 / black/70 / "
            "bg-black/80 (use the named overlay / scrim token)"
        )
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail("#218: CasAttach.svelte required (lightbox buttons, no bg-black/50)")
    cas = cas_path.read_text()
    wash_hits: list[str] = []
    for hook in ("data-lightbox-close", "data-lightbox-prev", "data-lightbox-next"):
        at = cas.find(hook)
        if at < 0:
            continue
        tag = _markup_open_tag(cas, cas.rfind("<", 0, at + 1))
        if _APPEARANCE_BLACK_WASH.search(tag):
            wash_hits.append(hook)
    if wash_hits:
        fail(
            "#218: lightbox buttons (CasAttach.svelte) must not use "
            "bg-black/50 / black/70 / bg-black/80 "
            "(use a CSS class from app.css). Found on: "
            + ", ".join(wash_hits)
        )

    # 5) Toast stays bg-background + text-foreground.
    toast_path = crate / "web" / "lib" / "components" / "ui" / "toast" / "toast.svelte"
    toast_src = toast_path.read_text() if toast_path.is_file() else ""
    toast_tag = _contrast_surface_tag(toast_src or svelte_blob, "data-toast")
    if not toast_tag:
        fail("#218: data-toast required (bg-background + text-foreground)")
    if "bg-background" not in toast_tag or "text-foreground" not in toast_tag:
        fail(
            "#218: data-toast must use bg-background and text-foreground "
            "(same tokens as the rest of chrome)"
        )

    # 6) Boot splash still flips on prefers-color-scheme: dark.
    if not index.strip():
        fail("#218: index.html required (keep prefers-color-scheme: dark on the splash)")
    if not re.search(r"prefers-color-scheme\s*:\s*dark", index):
        fail(
            "#218: index.html must keep prefers-color-scheme: dark "
            "(splash matches OS before JS)"
        )

    # 7) Keep color-scheme: light dark + dark media token overrides.
    if not _CONTRAST_COLOR_SCHEME.search(css):
        fail(
            "#218: keep color-scheme: light dark on :root / html "
            "(#217; OS appearance flips without a reload)"
        )
    dark_blob = _contrast_dark_blob(css)
    if not dark_blob.strip():
        fail("#218: keep @media (prefers-color-scheme: dark) token overrides")
    if not _css_var(
        dark_blob,
        ("--color-background", "--color-foreground", "--color-muted-foreground"),
    ):
        fail(
            "#218: prefers-color-scheme: dark must still override tokens "
            "(background / foreground / muted-foreground)"
        )

    # 8) Docs: follow OS; dark archival; lightbox + dialogs match; no Theme menu.
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    if not dtxt.strip():
        fail(
            "#218: docs/user/app.md required — follow OS / system appearance; "
            "dark archival look; lightbox + dialogs match; no Theme menu"
        )
    if not _CONTRAST_DOCS_SYSTEM.search(dtxt):
        fail(
            "#218: docs/user/app.md must say the app follows OS / system appearance"
        )
    if not _APPEARANCE_DOCS_ARCHIVAL.search(dtxt):
        fail(
            "#218: docs/user/app.md must say dark is the intended archival look"
        )
    if not _APPEARANCE_DOCS_MATCH.search(dtxt):
        fail(
            "#218: docs/user/app.md must say lightbox and dialogs match "
            "(same tokens / appearance)"
        )
    if not _APPEARANCE_DOCS_NO_THEME.search(dtxt):
        fail("#218: docs/user/app.md must say there is no Theme menu")

    # 10) Do not soften #q, sidebar, overlay titlebar, inspector, CSP, #217.
    app_path = crate / "web" / "App.svelte"
    app = _web_logic(crate) if app_path.is_file() else ""
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = _search_pane_blob(crate) if search_path.is_file() else ""
    conf = (crate / "tauri.conf.json").read_text()
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#218: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#218: keep data-people-sidebar (#159 / #212)")
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#218: keep the overlay titlebar (#211)")
    if not re.search(r"\bdata-person-inspector\b", app):
        fail("#218: keep data-person-inspector (#213)")
    if CSP not in conf:
        fail("#218: do not soften tauri CSP")
    light_blob = _contrast_light_blob(css)
    light_muted = _css_var(light_blob, ("--color-muted-foreground",))
    light_hsl = _hsl_tuple(light_muted) if light_muted else None
    if not light_hsl or light_hsl[2] > 40:
        fail(
            "#218: keep #217 light --color-muted-foreground HSL L ≤ 40 "
            "(@theme / non-dark :root)"
        )
    dark_muted = _css_var(dark_blob, ("--color-muted-foreground",))
    dark_hsl = _hsl_tuple(dark_muted) if dark_muted else None
    if not dark_hsl or dark_hsl[2] < 62:
        fail(
            "#218: keep #217 dark --color-muted-foreground HSL L ≥ 62 "
            "(inside prefers-color-scheme: dark)"
        )
    if not _css_var(light_blob, _CONTRAST_SEARCH_MARK_NAMES) or not _css_var(
        dark_blob, _CONTRAST_SEARCH_MARK_NAMES
    ):
        fail("#218: keep #217 --search-mark / --color-search-mark on both sides")
    mark_rules = _search_mark_rule_bodies(css)
    if not mark_rules or not any(
        _CONTRAST_SEARCH_MARK_VAR.search(body) for body in mark_rules
    ):
        fail("#218: keep #217 .search-mark on var(--search-mark)")
