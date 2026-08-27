"""Additional contrast asserts."""
from __future__ import annotations

from tauri_gate.contrast_lib import *


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
    app = _web_logic(crate)
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
    search = _search_pane_blob(crate) if search_path.is_file() else ""
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
