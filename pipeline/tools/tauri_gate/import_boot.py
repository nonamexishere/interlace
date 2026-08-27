"""Boot spinner / first-run chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.import_boot_guards import *
from tauri_gate.import_boot_setup import *


def assert_boot_spinner(crate: Path) -> None:
    """#156: centered CSS spinner on pre-JS splash and Opening-last-archive.

    Cold launch must not be a blank page with a corner Loading line. Spinner is
    CSS-only (no network images / CDN). Keep exact copy “Opening last archive”.
    Light/dark aware. Not: splash video, server progress %, people skeleton.
    """
    index = crate / "index.html"
    if not index.is_file():
        fail("#156: crates/interlace-tauri/index.html missing (pre-JS splash)")
    html = index.read_text()
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#156: App.svelte missing (Opening-last-archive boot state)")
    app = _web_logic(crate)
    css_blob = "\n".join(
        p.read_text() for p in _web_sources(crate) if p.suffix == ".css"
    )
    boot = _boot_opening_block(app)

    # 1) Pre-JS splash: centered CSS spinner in index.html (inline — Vite CSS
    # loads with JS, so corner text-only “Loading Interlace…” is not enough).
    if _plain_corner_loading(html):
        fail(
            "#156: pre-JS splash must not be a plain corner Loading line — "
            "index.html needs a centered CSS spinner (inline <style> / classes) "
            "plus short status, not only “Loading Interlace…”"
        )
    # Spinner styles for pre-JS must live in index.html itself (not only app.css).
    if not _has_css_spinner(html):
        fail(
            "#156: pre-JS splash (index.html) must include a CSS-only rotating "
            "spinner (@keyframes / animate-spin / border ring) — no network image"
        )
    if not _is_viewport_centered(html):
        fail(
            "#156: pre-JS splash must center the spinner in the viewport "
            "(flex/grid + items/justify center + min-h-screen/full), "
            "not leave status text in the corner"
        )
    if _NET_IMG.search(html) or _CDN_HINT.search(html):
        fail(
            "#156: pre-JS spinner must be CSS-only — no http(s) image URLs or CDN"
        )
    if _SPLASH_VIDEO.search(html):
        fail("#156: no branded splash <video> (out of scope)")

    # 2) Post-mount boot: booting || opening UI — centered spinner + copy.
    if not boot:
        fail(
            "#156: App.svelte must keep a {#if booting || opening} (or opening || booting) "
            "branch for the Opening-last-archive state"
        )
    en_pack = _chrome_en_text(crate)
    boot_has_copy = "Opening last archive" in boot
    pack_has_copy = "Opening last archive" in en_pack
    boot_uses_chrome = _markup_uses_chrome_helper(boot, _chrome_helper_names(_web_logic(crate)))
    if not boot_has_copy and "Opening last archive" not in app:
        if not (pack_has_copy and boot_uses_chrome):
            fail(
                "#156: boot screen must keep the exact copy substring "
                "“Opening last archive” (existing gate string; English default / en pack)"
            )
    if not boot_has_copy:
        if not (pack_has_copy and boot_uses_chrome):
            fail(
                "#156: “Opening last archive” must appear in the booting/opening branch "
                "(literal English, or chrome helper + en pack — default stays English)"
            )
    # Spinner may use Tailwind utilities in the branch and/or shared CSS.
    boot_with_css = boot + "\n" + css_blob
    if not _has_css_spinner(boot) and not (
        _has_css_spinner(boot_with_css) and _SPINNER_NAME.search(boot)
    ):
        # Accept spinner markup in branch that relies on global .spinner / animate-spin CSS.
        if not (
            (_SPINNER_NAME.search(boot) or re.search(r"animate-spin", boot))
            and _SPIN_ANIM.search(boot_with_css)
        ):
            fail(
                "#156: Opening-last-archive state must show a CSS rotating spinner "
                "(animate-spin / @keyframes spin / spinner class), not status text only"
            )
    if not _is_viewport_centered(boot):
        fail(
            "#156: Opening-last-archive state must be viewport-centered "
            "(flex/grid + center + full height), not a left-aligned loading line"
        )
    if _NET_IMG.search(boot) or _CDN_HINT.search(boot):
        fail(
            "#156: boot spinner must not load network images or CDN assets"
        )
    if _SPLASH_VIDEO.search(boot):
        fail("#156: no splash <video> on the Opening-last-archive state")
    if _SERVER_PROGRESS.search(boot):
        fail(
            "#156: boot status must not show server/network progress percent "
            "(out of scope)"
        )

    # 3) Light/dark aware — soft: dark: utilities, prefers-color-scheme, or theme vars.
    theme_blob = html + "\n" + app + "\n" + css_blob
    if not _LIGHT_DARK.search(theme_blob):
        fail(
            "#156: boot chrome must follow light/dark "
            "(dark: classes, prefers-color-scheme, or --color-background/foreground)"
        )


def assert_first_run(crate: Path) -> None:
    """#275: first-run is one calm screen, not a form wall.

    Setup: offline / no account, required #region, Create + Open.
    Owner name / emails / phones are not always-visible primary
    fields (disclosure or absent). createArchive still requires
    region and calls api.init; empty optional owner fields OK.
    FileVault / not encrypted; folder picker only; no carousel /
    account / sample cloud archive. Keep #137 sandbox sentence
    and #156 “Opening last archive”. Docs: one first-run screen;
    optional owner fields not required first.
    Do not rewrite #137 / #156 / #274.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#275: App.svelte required (setup / first-run screen)")
    app = _web_logic(crate)
    setup = _setup_branch(app)
    if not setup.strip():
        fail(
            "#275: App.svelte must have a setup / first-run branch "
            "({:else if setup} or {#if setup})"
        )
    extra = _setup_mounted_extra(crate, setup)
    extra_m = _svelte_markup(extra) if extra else extra
    surface = setup + ("\n" + extra_m if extra_m else "")
    wall = _strip_setup_disclosures(surface)

    # 1) Form wall — name / emails / phones must not be always-visible
    #    siblings of #region. Disclosure or absent is OK.
    visible = _setup_visible_owner_fields(wall)
    if visible:
        listed = " / ".join(visible)
        fail(
            "#275: setup must not be a form wall — owner "
            f"{listed} "
            "are still always-visible primary fields next to #region; "
            "put them behind a disclosure (`<details>` / More) or leave "
            "them for the inspector"
        )

    # 2) Offline / no account copy on the setup screen.
    if not re.search(r"\boffline\b", surface, re.I):
        fail("#275: setup screen must say this is an offline archive")
    if not re.search(r"\bno account\b", surface, re.I):
        fail("#275: setup screen must say no account")

    # 3) Required phone-region field (#region).
    if not _setup_has_field(surface, "region"):
        fail(
            "#275: setup must have a required phone-region field (#region)"
        )
    if not re.search(r"required|phone-region|ISO", surface, re.I):
        fail(
            "#275: #region must be marked required "
            "(ISO-2 phone-region, no silent default)"
        )

    # 4) Create + Open actions.
    if not re.search(r"\bcreateArchive\b", surface):
        fail("#275: setup must have a Create action (createArchive)")
    if not re.search(r"\bopenPicker\b", surface):
        fail("#275: setup must have an Open action (openPicker)")

    # 5) createArchive still requires region and calls api.init.
    create = _setup_fn(app, extra, "createArchive")
    if not create.strip():
        fail("#275: createArchive required (init still needs a region)")
    if not re.search(r"\bapi\.init\s*\(", create):
        fail("#275: createArchive must call api.init")
    region_required = bool(
        re.search(r"phone-region is required", create, re.I)
        or (
            re.search(r"\bregion\b", create)
            and re.search(r"if\s*\(\s*!", create)
            and re.search(r"\breturn\b", create)
        )
    )
    if not region_required:
        fail(
            "#275: createArchive must require phone-region "
            "(no silent default; empty region errors)"
        )
    if _SETUP_REQUIRE_OWNER.search(create):
        fail(
            "#275: createArchive must not require owner name / emails / "
            "phones — empty or null optional owner fields are OK"
        )
    if not re.search(r"\bapplyStatus\s*\(", create):
        fail("#275: createArchive must applyStatus after api.init (land on People)")

    # 6) FileVault / not encrypted; folder picker only; no carousel /
    #    account / sample cloud archive.
    if not re.search(r"\bFileVault\b", surface):
        fail("#275: setup must keep FileVault (not encrypted at rest)")
    if not re.search(r"not encrypted", surface, re.I):
        fail("#275: setup must keep “not encrypted at rest”")
    open_p = _setup_fn(app, extra, "openPicker")
    pick_src = create + "\n" + open_p + "\n" + surface
    if not re.search(r"\bpickFolder\b|\bpick_folder\b", pick_src):
        fail(
            "#275: Create / Open must use the folder picker "
            "(pickFolder / pick_folder) — no URLs"
        )
    if not re.search(r"folder picker|no URLs", surface, re.I):
        fail("#275: setup must say folder picker only — no URLs")
    if _SETUP_URL_FIELD.search(surface):
        fail("#275: setup must not take an archive URL (folder picker only)")
    if _SETUP_CAROUSEL.search(surface):
        fail("#275: no onboarding carousel (one first-run screen)")
    if _SETUP_ACCOUNT_ACTION.search(surface):
        fail("#275: no account / sign-in on first-run")
    if _SETUP_SAMPLE_CLOUD.search(surface):
        fail("#275: no sample / cloud archive on first-run")

    # 7) Keep #137 sandbox-denied sentence on setup / err.
    #    Keep #156 “Opening last archive”.
    if not _SANDBOX_137.search(app) and "SANDBOX_DENIED" not in app:
        fail(
            "#275: keep the #137 sandbox-denied sentence on setup / err: "
            "macOS blocked that folder. Use Open existing… once so Interlace "
            "can remember it."
        )
    err_branch = _svelte_if_true_branch(app, "err")
    if not err_branch or not re.search(r"\{err\}", err_branch):
        fail(
            "#275: keep the in-page {#if err} banner so the #137 sandbox "
            "sentence can show on setup"
        )
    if "Opening last archive" not in app:
        fail('#275: keep #156 “Opening last archive”')

    # 8) docs/user/app.md — one first-run screen; optional fields not first.
    docs_path = repo_root() / "docs" / "user" / "app.md"
    if not docs_path.is_file():
        fail("#275: docs/user/app.md required (first-run is one screen)")
    docs = docs_path.read_text()
    if not _SETUP_DOC_ONE_SCREEN.search(docs):
        fail(
            "#275: docs/user/app.md must say first-run is one screen "
            "(offline / no account, required region, Create / Open)"
        )
    if not re.search(r"\boffline\b", docs, re.I) or not re.search(
        r"\bno account\b", docs, re.I
    ):
        fail("#275: docs/user/app.md must say offline / no account")
    if not re.search(r"phone-region|required.{0,40}region|region.{0,40}required", docs, re.I):
        fail("#275: docs/user/app.md must say phone-region is required")
    if not re.search(r"create.{0,40}open|open.{0,40}create", docs, re.I):
        fail("#275: docs/user/app.md must say Create / Open")
    if not _SETUP_DOC_OPTIONAL.search(docs):
        fail(
            "#275: docs/user/app.md must say optional owner fields "
            "(name / emails / phones) are not required first"
        )
