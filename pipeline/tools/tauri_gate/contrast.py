"""Contrast / appearance / status-token chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations
import re
from pathlib import Path
from common import fail, repo_root
from tauri_gate.scan import (
    CSP, _APPEARANCE_FETCH, _APPEARANCE_MENU_LABEL, _APPEARANCE_SCRIM_NAMES,
    _CONTRAST_SEARCH_MARK_NAMES, _HUE_YELLOW, _STATUS_CONFETTI, _STATUS_GRADIENT,
    _STATUS_WARNING_NAMES, _ancestor_tags, _chrome_en_text, _contrast_dark_blob,
    _css_brace_body, _css_var, _css_without_comments, _markup_open_tag,
    _open_tag_before, _product_svelte, _without_comments,
)
from tauri_gate.a11y import (
    _A11Y_WCAG_CERT, _has_focus_visible_ring2,
)
from tauri_gate.design import (
    _SHADCN_TOKEN_DEFS, _SHADCN_TOKEN_USES,
)
from tauri_gate.import_boot import (
    _contrast_light_blob, _hue_findings,
)
from tauri_gate.status_toasts import (
    _APPEARANCE_DOCS_ARCHIVAL, _APPEARANCE_DOCS_NO_THEME, _APPEARANCE_THEME_UI, _CONTRAST_COLOR_SCHEME,
    _CONTRAST_DOCS_SYSTEM, _HUE_AMBER, _THEME_CDN, _appearance_class_names,
    _contrast_surface_tag, _hsl_tuple, _hue_surface, _status_hook_blob,
)

_CONTRAST_SEARCH_MARK_VAR = re.compile(
    r"var\(\s*--(?:color-)?search-mark\s*\)",
    re.I,
)
_CONTRAST_MARK_FOREGROUND = re.compile(
    r"color\s*:\s*var\(\s*--(?:color-)?foreground\s*\)",
    re.I,
)
_CONTRAST_TOKEN_CLASS = re.compile(
    r"(?<![\w-])(?:text-muted-foreground|bg-muted|bg-background|"
    r"text-foreground|border-border|"
    r"bg-warning|text-warning|text-warning-foreground|border-warning|"
    r"bg-success|text-success|text-success-foreground|border-success|"
    r"status-warning|status-success)(?![\w-])"
)
_CONTRAST_THEME_PICKER = re.compile(
    r"("
    r"\bdata-theme\b"
    r"|theme-picker"
    r"|Theme menu"
    r"|Appearance menu"
    r"|high-contrast"
    r"|highContrast"
    r")",
    re.I,
)
_CONTRAST_DOCS_NO_RELOAD = re.compile(
    r"("
    r"without (?:a |an )?(?:reload|restart|relaunch)"
    r"|no reload"
    r"|does not (?:require|need) (?:a )?(?:reload|restart|relaunch)"
    r"|updates?(?: the (?:app|chrome|window))? without (?:a )?(?:reload|restart)"
    r")",
    re.I,
)
_CONTRAST_DOCS_READABLE = re.compile(
    r"("
    r"readable.{0,80}(?:on both|in both|light and dark|both (?:light|appearances|modes))"
    r"|(?:on both|light and dark|both (?:appearances|modes)).{0,80}readable"
    r"|preview.{0,80}readable"
    r")",
    re.I | re.S,
)
_CONTRAST_DOCS_MARKS = re.compile(
    r"("
    r"(?:search[- ]?)?marks?.{0,100}"
    r"(?:still work|on both|light and dark|both (?:appearances|modes)|stay yellow|yellow-enough)"
    r"|(?:yellow|highlighted).{0,80}mark.{0,80}"
    r"(?:both|light and dark|still work|without.{0,20}reload)"
    r")",
    re.I | re.S,
)


def _search_mark_rule_bodies(css: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"\.search-mark\b[^{]*\{", css):
        body = _css_brace_body(css, css.find("{", m.start()))
        if body:
            out.append(body)
    return out


def _contrast_tag_ok(tag: str) -> bool:
    if not tag:
        return False
    surface = _hue_surface(tag)
    if _HUE_AMBER.search(surface) or _HUE_YELLOW.search(surface):
        return False
    return bool(_CONTRAST_TOKEN_CLASS.search(tag))
_STATUS_CELEBRATION = re.compile(
    r"("
    r"\bcelebrat(?:e|ion|ing|ory)\b"
    r"|\bcongratulations\b"
    r"|\bhooray\b"
    r"|\bwoo+hoo\b"
    r"|🎉"
    r")",
    re.I,
)


def assert_contrast_tokens(crate: Path) -> None:
    """#217: light + dark contrast via tokens (not a third theme / WCAG cert)."""
    svelte_files = _product_svelte(crate)
    if not svelte_files:
        fail("#217: crates/interlace-tauri/web/**/*.svelte required (contrast tokens)")

    # 1) No text-amber-900 / amber-* / yellow-* in product Svelte (#198 finder).
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
            "#217: product Svelte must not contain text-amber-900 / amber-* / "
            "yellow-* (CSS variables only; reuse #198). Found:\n  "
            + "\n  ".join(offenders)
        )

    css_path = crate / "web" / "app.css"
    if not css_path.is_file():
        fail("#217: web/app.css required (light/dark contrast tokens)")
    css = css_path.read_text()
    light_blob = _contrast_light_blob(css)
    dark_blob = _contrast_dark_blob(css)

    # 2) Light --color-muted-foreground L ≤ 40; dark (prefers-color-scheme) L ≥ 62.
    light_muted = _css_var(light_blob, ("--color-muted-foreground",))
    if not light_muted:
        fail(
            "#217: light --color-muted-foreground required in @theme / "
            "non-dark :root (do not make tokens dark-only)"
        )
    light_hsl = _hsl_tuple(light_muted)
    if not light_hsl:
        fail(
            "#217: light --color-muted-foreground must be HSL so lightness "
            "can be checked (≤ 40)"
        )
    if light_hsl[2] > 40:
        fail(
            "#217: light --color-muted-foreground HSL lightness must be ≤ 40 "
            "(@theme / non-dark :root) so people preview and chips stay "
            f"readable; found L={light_hsl[2]:g}"
        )
    dark_muted = _css_var(dark_blob, ("--color-muted-foreground",))
    if not dark_muted:
        fail(
            "#217: dark --color-muted-foreground required inside "
            "@media (prefers-color-scheme: dark)"
        )
    dark_hsl = _hsl_tuple(dark_muted)
    if not dark_hsl:
        fail(
            "#217: dark --color-muted-foreground must be HSL so lightness "
            "can be checked (≥ 62)"
        )
    if dark_hsl[2] < 62:
        fail(
            "#217: dark --color-muted-foreground HSL lightness must be ≥ 62 "
            "(inside prefers-color-scheme: dark); "
            f"found L={dark_hsl[2]:g}"
        )

    # 3) --search-mark or --color-search-mark in light + dark; .search-mark
    #    uses the var; both hues 40–60 (yellow-enough). Keep foreground color.
    light_mark = _css_var(light_blob, _CONTRAST_SEARCH_MARK_NAMES)
    dark_mark = _css_var(dark_blob, _CONTRAST_SEARCH_MARK_NAMES)
    if not light_mark:
        fail(
            "#217: define --search-mark or --color-search-mark for light "
            "(@theme / :root) — .search-mark must not be a one-off hsl"
        )
    if not dark_mark:
        fail(
            "#217: define --search-mark or --color-search-mark inside "
            "@media (prefers-color-scheme: dark)"
        )
    mark_rules = _search_mark_rule_bodies(css)
    if not mark_rules:
        fail("#217: .search-mark rule required (named search-mark token)")
    if not any(_CONTRAST_SEARCH_MARK_VAR.search(body) for body in mark_rules):
        fail(
            "#217: .search-mark must use var(--search-mark) or "
            "var(--color-search-mark) (not a one-off hsl)"
        )
    if not any(_CONTRAST_MARK_FOREGROUND.search(body) for body in mark_rules):
        fail(
            "#217: .search-mark must keep color: var(--color-foreground) "
            "(or --foreground)"
        )
    light_mark_hsl = _hsl_tuple(light_mark)
    dark_mark_hsl = _hsl_tuple(dark_mark)
    if not light_mark_hsl or not dark_mark_hsl:
        fail(
            "#217: --search-mark / --color-search-mark must be HSL "
            "(hue 40–60, yellow-enough on both)"
        )
    if not (40 <= light_mark_hsl[0] <= 60):
        fail(
            "#217: light search-mark hue must be 40–60 (yellow-enough); "
            f"found H={light_mark_hsl[0]:g}"
        )
    if not (40 <= dark_mark_hsl[0] <= 60):
        fail(
            "#217: dark search-mark hue must be 40–60 (yellow-enough); "
            f"found H={dark_mark_hsl[0]:g}"
        )

    # 4) color-scheme: light dark on :root or html; dark media still overrides.
    if not _CONTRAST_COLOR_SCHEME.search(css):
        fail(
            "#217: :root or html must set color-scheme: light dark "
            "(macOS appearance flips the app without a reload)"
        )
    if not dark_blob.strip():
        fail(
            "#217: keep @media (prefers-color-scheme: dark) so tokens "
            "still override in dark"
        )
    if not _css_var(dark_blob, ("--color-background", "--color-foreground", "--color-muted-foreground")):
        fail(
            "#217: prefers-color-scheme: dark must still override tokens "
            "(background / foreground / muted-foreground)"
        )

    # 5) Preview / chips / cloud / toast / doctor issue box stay on tokens.
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#217: App.svelte required (people preview / chips / banners)")
    app = app_path.read_text()
    toast_path = crate / "web" / "lib" / "components" / "ui" / "toast" / "toast.svelte"
    toast_src = toast_path.read_text() if toast_path.is_file() else ""
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    doctor_src = doctor_path.read_text() if doctor_path.is_file() else ""
    svelte_blob = "\n".join(p.read_text() for p in svelte_files)

    preview_tag = ""
    for src in (app, svelte_blob):
        m = re.search(r"\{p\.preview\b", src)
        if not m:
            continue
        found = _open_tag_before(src, m.start())
        if found:
            preview_tag = found[1]
        for tag in _ancestor_tags(src, m.start(), limit=6):
            if _CONTRAST_TOKEN_CLASS.search(tag):
                preview_tag = tag
                break
        if preview_tag:
            break
    if not preview_tag:
        fail(
            "#217: people preview / last-activity line required "
            "(token classes, not raw amber)"
        )
    if not _contrast_tag_ok(preview_tag):
        fail(
            "#217: people preview / last-activity line must use token classes "
            "(text-muted-foreground / bg-muted / bg-background / "
            "text-foreground / border-border), not raw amber"
        )

    chip_tag = _contrast_surface_tag(svelte_blob, "data-platform-chip")
    if not chip_tag:
        fail("#217: data-platform-chip required (token classes, not raw amber)")
    if not _contrast_tag_ok(chip_tag):
        fail(
            "#217: data-platform-chip must use token classes "
            "(text-muted-foreground / bg-muted / bg-background / "
            "text-foreground / border-border), not raw amber"
        )

    cloud_tag = _contrast_surface_tag(app, "data-cloud-warning")
    if not cloud_tag:
        fail("#217: data-cloud-warning required (token classes, not raw amber)")
    if not _contrast_tag_ok(cloud_tag):
        fail(
            "#217: data-cloud-warning must use token classes "
            "(text-muted-foreground / bg-muted / bg-background / "
            "text-foreground / border-border), not raw amber"
        )

    toast_tag = _contrast_surface_tag(toast_src or svelte_blob, "data-toast")
    if not toast_tag:
        fail("#217: data-toast required (token classes, not raw amber)")
    if not _contrast_tag_ok(toast_tag):
        fail(
            "#217: data-toast must use token classes "
            "(text-muted-foreground / bg-muted / bg-background / "
            "text-foreground / border-border), not raw amber"
        )

    doctor_box = ""
    for src in (app, doctor_src):
        at = src.find("Doctor found")
        if at < 0:
            continue
        for tag in _ancestor_tags(src, at, limit=8):
            if _CONTRAST_TOKEN_CLASS.search(tag) or re.search(
                r"\b(?:rounded-md|border|bg-)\b", tag
            ):
                doctor_box = tag
                break
        if doctor_box:
            break
    if not doctor_box:
        fail("#217: doctor issue box required (token classes, not raw amber)")
    if not _contrast_tag_ok(doctor_box):
        fail(
            "#217: doctor issue box must use token classes "
            "(text-muted-foreground / bg-muted / bg-background / "
            "text-foreground / border-border), not raw amber"
        )

    # 6) No Theme menu / data-theme / high-contrast third theme; light tokens stay.
    if _CONTRAST_THEME_PICKER.search(svelte_blob):
        fail(
            "#217: not in scope — no Theme menu / data-theme / high-contrast "
            "third theme (system appearance only; #218 is later)"
        )
    if not light_blob.strip() or not _css_var(
        light_blob,
        ("--color-background", "--color-foreground", "--color-muted-foreground"),
    ):
        fail(
            "#217: light @theme / :root tokens must still exist "
            "(do not force dark-only)"
        )

    # 8) Docs: system light/dark without a reload; readable on both; marks work.
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    if not dtxt.strip():
        fail(
            "#217: docs/user/app.md required — system light/dark without a "
            "reload; readable on both; marks still work"
        )
    if not _CONTRAST_DOCS_SYSTEM.search(dtxt):
        fail(
            "#217: docs/user/app.md must say chrome follows system light/dark"
        )
    if not _CONTRAST_DOCS_NO_RELOAD.search(dtxt):
        fail(
            "#217: docs/user/app.md must say appearance updates without a reload"
        )
    if not _CONTRAST_DOCS_READABLE.search(dtxt):
        fail(
            "#217: docs/user/app.md must say preview / chips / marks / banners "
            "stay readable on both"
        )
    if not _CONTRAST_DOCS_MARKS.search(dtxt):
        fail(
            "#217: docs/user/app.md must say search marks still work on both"
        )
    if _A11Y_WCAG_CERT.search(dtxt):
        fail(
            "#217: docs/user/app.md must not claim WCAG certified / certificate"
        )

    # 9) Do not soften #q, sidebar, overlay, inspector, CSP, #198, #216 rings.
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    conf = (crate / "tauri.conf.json").read_text()
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#217: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#217: keep data-people-sidebar (#159 / #212)")
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#217: keep the overlay titlebar (#211)")
    if not re.search(r"\bdata-person-inspector\b", app):
        fail("#217: keep data-person-inspector (#213)")
    if CSP not in conf:
        fail("#217: do not soften tauri CSP")
    missing_defs = [name for name in _SHADCN_TOKEN_DEFS if name not in css]
    if missing_defs:
        fail(
            "#217: keep #198 shadcn tokens "
            f"({', '.join(missing_defs)} missing)"
        )
    missing_uses = [tok for tok in _SHADCN_TOKEN_USES if tok not in svelte_blob]
    if missing_uses:
        fail(
            "#217: keep #198 token/variable classes "
            f"({', '.join(missing_uses)} missing)"
        )
    button_path = (
        crate / "web" / "lib" / "components" / "ui" / "button" / "button.svelte"
    )
    input_path = crate / "web" / "lib" / "components" / "ui" / "input" / "input.svelte"
    if not button_path.is_file() or not _has_focus_visible_ring2(
        _without_comments(button_path.read_text())
    ):
        fail("#217: keep #216 Button focus-visible:ring-2 ring-ring")
    if not input_path.is_file() or not _has_focus_visible_ring2(
        _without_comments(input_path.read_text())
    ):
        fail("#217: keep #216 Input focus-visible:ring-2 ring-ring")
_APPEARANCE_SCRIM_VAR = re.compile(
    r"var\(\s*--(?:overlay|scrim|lightbox-scrim)\s*\)",
    re.I,
)
_APPEARANCE_THEME_HTTP = re.compile(
    r"("
    r"(?:theme|appearance|stylesheet)[^;\n]{0,100}https://"
    r"|https://[^;\n]{0,100}(?:theme|appearance|stylesheet)"
    r"|@import\s+(?:url\s*\(\s*)?['\"]https?://"
    r")",
    re.I,
)
_APPEARANCE_BLACK_WASH = re.compile(
    r"(?<![\w-])(?:bg-)?black/(?:50|70|80)(?![\w-])"
)
_APPEARANCE_DOCS_MATCH = re.compile(
    r"("
    r"(?:lightbox|dialogs?).{0,120}(?:lightbox|dialogs?).{0,80}"
    r"(?:match|same (?:tokens?|variables?)|follow)"
    r"|(?:lightbox|dialogs?).{0,80}"
    r"(?:match|same (?:tokens?|variables?)).{0,80}"
    r"(?:lightbox|dialogs?)"
    r")",
    re.I | re.S,
)


def _appearance_tag_uses_scrim(tag: str, css: str) -> bool:
    if _APPEARANCE_SCRIM_VAR.search(tag):
        return True
    for cls in _appearance_class_names(tag):
        for m in re.finditer(rf"\.{re.escape(cls)}\b[^{{]*\{{", css):
            body = _css_brace_body(css, css.find("{", m.start()))
            if body and _APPEARANCE_SCRIM_VAR.search(body):
                return True
    return False


def _photo_lightbox_rule_bodies(css: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"\.photo-lightbox\b[^{]*\{", css):
        body = _css_brace_body(css, css.find("{", m.start()))
        if body:
            out.append(body)
    return out


def _appearance_overlay_tag(dialog_src: str) -> str:
    m = re.search(r"Dialog(?:Primitive)?\.Overlay\b", dialog_src)
    if not m:
        return ""
    return _markup_open_tag(dialog_src, dialog_src.rfind("<", 0, m.start() + 1))


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
    app = app_path.read_text() if app_path.is_file() else ""
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
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
_STATUS_WARNING_FG_NAMES = ("--warning-foreground", "--color-warning-foreground")
_STATUS_SUCCESS_NAMES = ("--success", "--color-success")
_STATUS_SUCCESS_FG_NAMES = ("--success-foreground", "--color-success-foreground")
_STATUS_WARNING_USE = re.compile(
    r"("
    r"(?<![\w-])(?:bg-warning|text-warning|text-warning-foreground|"
    r"border-warning|status-warning)(?![\w-])"
    r"|var\(\s*--(?:color-)?warning(?:-foreground)?\s*\)"
    r")"
)
_STATUS_SUCCESS_USE = re.compile(
    r"("
    r"(?<![\w-])(?:bg-success|text-success|text-success-foreground|"
    r"border-success|status-success)(?![\w-])"
    r"|var\(\s*--(?:color-)?success(?:-foreground)?\s*\)"
    r")"
)
_STATUS_MUTED_USE = re.compile(
    r"(?<![\w-])(?:text-muted-foreground|bg-muted|bg-background|"
    r"text-foreground|border-border)(?![\w-])"
)
_STATUS_RAW_HUE = re.compile(r"(?<![\w-])(?:amber|yellow|emerald|green)-\d+")
_STATUS_AUDIO_CTOR = re.compile(r"\bAudio\s*\(")
_STATUS_SVELTE_TRANSITION = re.compile(r"\b(?:transition|in|out)\s*:\s*([A-Za-z_]\w*)")
_STATUS_DOCS_WARNING = re.compile(
    r"("
    r"warning token"
    r"|--(?:color-)?warning"
    r"|(?:cloud|doctor).{0,120}warning token"
    r"|warnings?.{0,80}warning token"
    r")",
    re.I | re.S,
)
_STATUS_DOCS_QUIET_DONE = re.compile(
    r"("
    r"import done.{0,100}(?:quiet|muted|success)"
    r"|(?:quiet|muted|success).{0,80}import done"
    r"|import (?:done|success).{0,80}(?:quiet|muted|success token)"
    r"|quiet import done"
    r")",
    re.I | re.S,
)
_STATUS_TOAST_FADE_180 = re.compile(
    r"transition\s*:\s*fade\s*=\s*\{\{?\s*duration\s*:\s*180\s*\}"
)


def _status_selector_bodies(css: str, hook: str) -> list[str]:
    """Rule bodies whose selector mentions a data-* hook or a .class."""
    if hook.startswith("data-"):
        sel = rf"\[{re.escape(hook)}\]"
    else:
        sel = rf"\.{re.escape(hook)}\b"
    out: list[str] = []
    for m in re.finditer(rf"{sel}[^{{]*\{{", css):
        body = _css_brace_body(css, css.find("{", m.start()))
        if body:
            out.append(body)
    return out


def _status_surface_uses(
    blob: str,
    css: str,
    use_rx: re.Pattern[str],
    names: tuple[str, ...],
    hooks: tuple[str, ...] = (),
) -> bool:
    if use_rx.search(blob):
        return True
    for hook in hooks:
        for body in _status_selector_bodies(css, hook):
            if use_rx.search(body) or _css_var(body, names):
                return True
    for cls in _appearance_class_names(blob):
        if use_rx.search(cls):
            return True
        for body in _status_selector_bodies(css, cls):
            if use_rx.search(body) or _css_var(body, names):
                return True
    return False


def _status_doctor_box(src: str) -> str:
    """Non-partial doctor issues card (App 'Doctor found' / DoctorPane list)."""
    for needle in ("Doctor found issues", "Doctor found", "{#each issues"):
        at = src.find(needle)
        if at < 0:
            continue
        for tag in _ancestor_tags(src, at, limit=8):
            if "data-partial" in tag:
                continue
            if (
                _CONTRAST_TOKEN_CLASS.search(tag)
                or _STATUS_WARNING_USE.search(tag)
                or re.search(r"\b(?:rounded-md|border|bg-)\b", tag)
            ):
                return tag
    return ""


def _status_require_pair(
    light_blob: str,
    dark_blob: str,
    names: tuple[str, ...],
    fg_names: tuple[str, ...],
    *,
    label: str,
    hue_lo: float,
    hue_hi: float,
) -> None:
    pretty = " / ".join(names)
    pretty_fg = " / ".join(fg_names)
    light = _css_var(light_blob, names)
    if not light:
        fail(
            f"#219: {pretty} required in light (@theme / non-dark :root)"
        )
    dark = _css_var(dark_blob, names)
    if not dark:
        fail(
            f"#219: {pretty} required inside "
            "@media (prefers-color-scheme: dark)"
        )
    light_fg = _css_var(light_blob, fg_names)
    if not light_fg:
        fail(
            f"#219: {pretty_fg} required in light (@theme / non-dark :root)"
        )
    dark_fg = _css_var(dark_blob, fg_names)
    if not dark_fg:
        fail(
            f"#219: {pretty_fg} required inside "
            "@media (prefers-color-scheme: dark)"
        )
    for side, val in (
        ("light", light),
        ("dark", dark),
        ("light foreground", light_fg),
        ("dark foreground", dark_fg),
    ):
        if not _hsl_tuple(val):
            fail(f"#219: {label} tokens must be HSL ({side})")
    light_hsl = _hsl_tuple(light)
    dark_hsl = _hsl_tuple(dark)
    if light_hsl is None or dark_hsl is None:
        fail(f"#219: {label} tokens must be HSL (hue {hue_lo:g}–{hue_hi:g})")
    if not (hue_lo <= light_hsl[0] <= hue_hi):
        fail(
            f"#219: light {pretty} hue must be {hue_lo:g}–{hue_hi:g}; "
            f"found H={light_hsl[0]:g}"
        )
    if not (hue_lo <= dark_hsl[0] <= hue_hi):
        fail(
            f"#219: dark {pretty} hue must be {hue_lo:g}–{hue_hi:g}; "
            f"found H={dark_hsl[0]:g}"
        )


def assert_status_tokens(crate: Path) -> None:
    """#219: status colors via tokens (warning / optional success; no raw amber)."""
    svelte_files = _product_svelte(crate)
    if not svelte_files:
        fail("#219: crates/interlace-tauri/web/**/*.svelte required (status tokens)")

    css_path = crate / "web" / "app.css"
    if not css_path.is_file():
        fail("#219: web/app.css required (warning / success status tokens)")
    css = css_path.read_text()
    light_blob = _contrast_light_blob(css)
    dark_blob = _contrast_dark_blob(css)
    svelte_blob = "\n".join(p.read_text() for p in svelte_files)

    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#219: App.svelte required (cloud banner + Doctor found box)")
    app = app_path.read_text()
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    if not doctor_path.is_file():
        fail("#219: DoctorPane.svelte required (issues card uses warning token)")
    doctor_src = doctor_path.read_text()
    import_path = crate / "web" / "lib" / "ImportPane.svelte"
    import_src = import_path.read_text() if import_path.is_file() else ""

    # 1) --warning / --color-warning + foreground pair in light and dark; HSL;
    #    warning hue 30–55 both sides.
    _status_require_pair(
        light_blob,
        dark_blob,
        _STATUS_WARNING_NAMES,
        _STATUS_WARNING_FG_NAMES,
        label="warning",
        hue_lo=30,
        hue_hi=55,
    )

    # 2) If import-done uses success (not muted): --success pair both sides;
    #    HSL; hue 120–160. Missing success is OK when check 5 stays muted.
    done_src = ""
    done_tag = ""
    for src in (import_src, app, svelte_blob):
        tag = _contrast_surface_tag(src, "data-import-done")
        if tag:
            done_src = src
            done_tag = tag
            break
    done_blob = (
        _status_hook_blob(done_src, "data-import-done") if done_src else done_tag
    )
    done_uses_success = _status_surface_uses(
        done_blob,
        css,
        _STATUS_SUCCESS_USE,
        _STATUS_SUCCESS_NAMES,
        ("data-import-done", "status-success"),
    )
    done_uses_muted = bool(_STATUS_MUTED_USE.search(done_blob))
    if done_uses_success:
        _status_require_pair(
            light_blob,
            dark_blob,
            _STATUS_SUCCESS_NAMES,
            _STATUS_SUCCESS_FG_NAMES,
            label="success",
            hue_lo=120,
            hue_hi=160,
        )

    # 3) data-cloud-warning uses a warning token (not muted-only, not amber-*).
    cloud_tag = _contrast_surface_tag(app, "data-cloud-warning")
    if not cloud_tag:
        fail(
            "#219: data-cloud-warning required (warning token, not muted-only)"
        )
    cloud_blob = _status_hook_blob(app, "data-cloud-warning")
    if _STATUS_RAW_HUE.search(_hue_surface(cloud_blob)):
        fail(
            "#219: data-cloud-warning must not use amber-* / yellow-* / "
            "emerald-* / green-* (warning token only)"
        )
    if not _status_surface_uses(
        cloud_blob,
        css,
        _STATUS_WARNING_USE,
        _STATUS_WARNING_NAMES,
        ("data-cloud-warning", "status-warning"),
    ):
        fail(
            "#219: data-cloud-warning must use a warning token class / "
            "var(--warning) / var(--color-warning) (not muted-only, not amber-*)"
        )

    # 4) App.svelte “Doctor found” box and DoctorPane issues card use warning
    #    (not text-destructive as the status color). Scan/partial may stay.
    app_doctor = _status_doctor_box(app)
    if not app_doctor:
        fail(
            "#219: App.svelte “Doctor found” box required "
            "(warning token, not text-destructive)"
        )
    app_doctor_blob = app_doctor + "\n" + _status_hook_blob(app, "Doctor found")
    if re.search(r"(?<![\w-])text-destructive(?![\w-])", app_doctor):
        fail(
            "#219: App.svelte “Doctor found” box must use a warning token "
            "(not text-destructive as the status color)"
        )
    if not _status_surface_uses(
        app_doctor_blob,
        css,
        _STATUS_WARNING_USE,
        _STATUS_WARNING_NAMES,
        ("status-warning",),
    ):
        fail(
            "#219: App.svelte “Doctor found” box must use a warning token "
            "(not text-destructive as the status color)"
        )

    pane_doctor = _status_doctor_box(doctor_src)
    if not pane_doctor:
        fail(
            "#219: DoctorPane.svelte issues card required "
            "(warning token, not text-destructive)"
        )
    pane_blob = pane_doctor + "\n" + _status_hook_blob(doctor_src, "Doctor found")
    if re.search(r"(?<![\w-])text-destructive(?![\w-])", pane_doctor):
        fail(
            "#219: DoctorPane.svelte issues card must use a warning token "
            "(not text-destructive as the status color)"
        )
    if not _status_surface_uses(
        pane_blob,
        css,
        _STATUS_WARNING_USE,
        _STATUS_WARNING_NAMES,
        ("status-warning",),
    ):
        fail(
            "#219: DoctorPane.svelte issues card must use a warning token "
            "(not text-destructive as the status color)"
        )

    # 5) data-import-done exists; muted token classes or success tokens;
    #    no bg-gradient / confetti / celebration.
    if "data-import-done" not in svelte_blob:
        fail(
            "#219: data-import-done required (muted token classes or success "
            "tokens; no bg-gradient / confetti / celebration)"
        )
    if not done_tag:
        fail(
            "#219: data-import-done required (muted token classes or success "
            "tokens; no bg-gradient / confetti / celebration)"
        )
    if not (done_uses_muted or done_uses_success):
        fail(
            "#219: data-import-done must use muted token classes or success "
            "tokens (no bg-gradient / confetti / celebration)"
        )
    if _STATUS_GRADIENT.search(done_blob) or _STATUS_CONFETTI.search(done_blob):
        fail(
            "#219: data-import-done must not use bg-gradient / confetti / "
            "celebration"
        )
    if _STATUS_CELEBRATION.search(_hue_surface(done_blob)):
        fail(
            "#219: data-import-done must not use bg-gradient / confetti / "
            "celebration"
        )

    # 6) No amber-* / yellow-* / emerald-* / green-* on those three surfaces.
    surface_hits: list[str] = []
    for label, blob in (
        ("data-cloud-warning", cloud_blob),
        ("App.svelte Doctor found", app_doctor_blob),
        ("DoctorPane issues card", pane_blob),
        ("data-import-done", done_blob),
    ):
        found = sorted(set(_STATUS_RAW_HUE.findall(_hue_surface(blob))))
        if found:
            surface_hits.append(f"{label}: {', '.join(found)}")
    if surface_hits:
        fail(
            "#219: no amber-* / yellow-* / emerald-* / green-* on cloud / "
            "doctor / import-done surfaces. Found:\n  "
            + "\n  ".join(surface_hits)
        )

    # 7) No confetti / Audio( / celebration copy.
    chrome_hits: list[str] = []
    for p in svelte_files:
        surface = _hue_surface(p.read_text())
        found: list[str] = []
        if _STATUS_CONFETTI.search(surface):
            found.append("confetti")
        if _STATUS_AUDIO_CTOR.search(surface):
            found.append("Audio(")
        celeb = sorted({m.group(0) for m in _STATUS_CELEBRATION.finditer(surface)})
        if celeb:
            found.append("celebration (" + ", ".join(celeb) + ")")
        if found:
            chrome_hits.append(f"{p.relative_to(crate)}: {', '.join(found)}")
    if chrome_hits:
        fail(
            "#219: no confetti / Audio( / celebration copy. Found:\n  "
            + "\n  ".join(chrome_hits)
        )

    # 8) docs/user/app.md: warning token + quiet import done.
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    if not dtxt.strip():
        fail(
            "#219: docs/user/app.md required — warning token + quiet import done"
        )
    if not _STATUS_DOCS_WARNING.search(dtxt):
        fail(
            "#219: docs/user/app.md must say cloud / doctor warnings use the "
            "warning token"
        )
    if not _STATUS_DOCS_QUIET_DONE.search(dtxt):
        fail(
            "#219: docs/user/app.md must say import done is quiet "
            "(muted or success)"
        )

    # 9) No review-queue chrome rewrite (#221).
    #    Svelte transition durations are #222 (`assert_motion`).
    #    “Loading review queue” may live in the pane or the en pack (#278).
    review_path = crate / "web" / "lib" / "ReviewPane.svelte"
    review = review_path.read_text() if review_path.is_file() else ""
    en_pack = _chrome_en_text(crate)
    if (
        not review
        or "Accept" not in review
        or "Reject" not in review
        or (
            "Loading review queue" not in review
            and "Loading review queue" not in en_pack
        )
        or (
            "identifierLabel" not in review
            and "value_normalized" not in review
        )
        or "reviewList" not in review
        or "reviewAccept" not in review
        or "reviewReject" not in review
    ):
        fail("#219: not in scope — no review-queue chrome rewrite (#221)")

    # 10) Do not soften #q, sidebar, overlay titlebar, inspector, CSP,
    #     #217 muted / search-mark, #218 overlay / no Theme.
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    conf = (crate / "tauri.conf.json").read_text()
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#219: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#219: keep data-people-sidebar (#159 / #212)")
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#219: keep the overlay titlebar (#211)")
    if not re.search(r"\bdata-person-inspector\b", app):
        fail("#219: keep data-person-inspector (#213)")
    if CSP not in conf:
        fail("#219: do not soften tauri CSP")
    light_muted = _css_var(light_blob, ("--color-muted-foreground",))
    light_hsl = _hsl_tuple(light_muted) if light_muted else None
    if not light_hsl or light_hsl[2] > 40:
        fail(
            "#219: keep #217 light --color-muted-foreground HSL L ≤ 40 "
            "(@theme / non-dark :root)"
        )
    dark_muted = _css_var(dark_blob, ("--color-muted-foreground",))
    dark_hsl = _hsl_tuple(dark_muted) if dark_muted else None
    if not dark_hsl or dark_hsl[2] < 62:
        fail(
            "#219: keep #217 dark --color-muted-foreground HSL L ≥ 62 "
            "(inside prefers-color-scheme: dark)"
        )
    if not _css_var(light_blob, _CONTRAST_SEARCH_MARK_NAMES) or not _css_var(
        dark_blob, _CONTRAST_SEARCH_MARK_NAMES
    ):
        fail("#219: keep #217 --search-mark / --color-search-mark on both sides")
    mark_rules = _search_mark_rule_bodies(css)
    if not mark_rules or not any(
        _CONTRAST_SEARCH_MARK_VAR.search(body) for body in mark_rules
    ):
        fail("#219: keep #217 .search-mark on var(--search-mark)")
    if not _css_var(css, _APPEARANCE_SCRIM_NAMES):
        fail("#219: keep #218 --overlay / --scrim / --lightbox-scrim")
    if _APPEARANCE_THEME_UI.search(svelte_blob) or _APPEARANCE_MENU_LABEL.search(
        svelte_blob
    ):
        fail("#219: keep #218 — no Theme / Appearance menu / data-theme")
