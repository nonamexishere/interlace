"""Contrast / appearance / status-token chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.contrast_lib import *


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
    app = _web_logic(crate)
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
    search = _search_pane_blob(crate) if search_path.is_file() else ""
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

from tauri_gate.contrast_more import assert_appearance_os
from tauri_gate.contrast_status_tokens import assert_status_tokens
