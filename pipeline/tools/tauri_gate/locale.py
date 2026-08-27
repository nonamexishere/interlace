"""Locale / macOS menu chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.locale_menu import *
from tauri_gate.locale_pack import *


def assert_macos_menu(crate: Path) -> None:
    """#130: native macOS menu — About/Quit, File Open+Import, View tabs; no updater."""
    rust = _tauri_rust_blob(crate)
    web_all = _web_logic(crate)
    web_menu = _menu_web_blob(crate)
    menu_src = rust + "\n" + web_menu
    app_path = crate / "web" / "App.svelte"
    app = _web_logic(crate) if app_path.is_file() else ""
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    deny_path = crate / "deny.toml"
    deny = deny_path.read_text() if deny_path.is_file() else ""
    docs_app = repo_root() / "docs" / "user" / "app.md"
    docs_tauri = repo_root() / "docs" / "hacking" / "tauri.md"
    dtxt = (docs_app.read_text() if docs_app.is_file() else "") + "\n" + (
        docs_tauri.read_text() if docs_tauri.is_file() else ""
    )
    caps_path = crate / "capabilities" / "default.json"
    caps = caps_path.read_text() if caps_path.is_file() else ""

    # 1) Native Tauri menu construction (not the default app menu, not HTML nav).
    if not _TAURI_MENU_API.search(menu_src):
        fail(
            "#130: native macOS menu must be built with Tauri Menu / MenuBuilder / "
            "PredefinedMenuItem (or @tauri-apps/api/menu), not the default app menu alone"
        )

    if not _MENU_ATTACH.search(rust) and not _MENU_ATTACH.search(web_menu):
        fail(
            "#130: the constructed menu must be attached to the app "
            "(.menu(...) / set_menu / setMenu) — building items and never installing "
            "them leaves the default macOS menu"
        )

    if "@tauri-apps/api/menu" in web_menu and "core:menu" not in caps:
        fail(
            "#130: JS @tauri-apps/api/menu needs a core:menu capability "
            "(or build the menu in Rust)"
        )

    # 2) App menu: About + Quit (predefined preferred; custom About Interlace / Quit OK).
    if not _ABOUT_ITEM.search(menu_src):
        fail(
            "#130: app menu must include About "
            "(PredefinedMenuItem::about / About Interlace)"
        )
    if not _QUIT_ITEM.search(menu_src):
        fail(
            "#130: app menu must include native Quit "
            "(PredefinedMenuItem::quit — not a custom network-y exit)"
        )

    # 3) File: Open archive + Import.
    if not _FILE_SUBMENU.search(menu_src):
        fail('#130: File submenu required (Open archive + Import)')
    if not _OPEN_ITEM.search(menu_src):
        fail(
            "#130: File menu must include Open archive "
            "(same folder picker as the in-window Open existing… button)"
        )
    if not _IMPORT_ITEM.search(menu_src):
        fail("#130: File menu must include Import")

    # 4) View: People, Search, Review, Doctor (Import may live under File only).
    if not _VIEW_SUBMENU.search(menu_src):
        fail("#130: View submenu required (People, Search, Review, Doctor)")
    for label in ("People", "Search", "Review", "Doctor"):
        if not re.search(rf"[\"']{label}[\"']", menu_src):
            fail(
                f"#130: View menu must include {label} "
                "(same view token as the in-window nav buttons)"
            )

    # 5) About copy: offline + not encrypted at rest + FileVault (About surface, not Doctor).
    about_src = _about_copy_surface(rust, web_menu)
    if not about_src.strip():
        fail(
            "#130: About copy must live on the About item / AboutMetadata "
            "(offline, not encrypted at rest, FileVault — same honesty as Doctor)"
        )
    if not _ABOUT_OFFLINE.search(about_src):
        fail("#130: About copy must say the app is offline")
    if not _ABOUT_NOT_ENCRYPTED.search(about_src):
        fail("#130: About copy must say not encrypted at rest")
    if not _ABOUT_FILEVAULT.search(about_src):
        fail("#130: About copy must mention FileVault")
    if re.search(r"https?://", about_src):
        fail(
            "#130: About must stay offline — no website / http(s) URL on the About item"
        )

    # 6) Open uses the same picker path (pick_folder / openPicker), not a remote open.
    handlers = _menu_handler_surface(rust, web_all)
    if not handlers.strip():
        fail(
            "#130: menu Open must be wired (on_menu_event and/or a frontend listen) "
            "to the existing folder picker — pick_folder / openPicker"
        )
    open_wired = bool(
        re.search(r"\bpick_folder\b", handlers)
        or re.search(r"\bopenPicker\b", handlers)
        or re.search(r"\bpickFolder\b", handlers)
    )
    if not open_wired:
        fail(
            "#130: menu Open must call the same folder picker as the UI button "
            "(openPicker / pickFolder / pick_folder), not a new remote/URL open"
        )
    if re.search(r"https?://", handlers) or re.search(
        r"\b(?:webbrowser|open::that|opener::)\b", handlers
    ):
        fail("#130: menu handlers must not open a remote URL")

    # 7) Import: same Import-tab picker, or switch to Import + existing flow.
    import_wired = bool(
        re.search(r"\bpick_import_path\b", handlers)
        or re.search(r"\bpickImportPath\b", handlers)
        or re.search(r"view\s*=\s*[\"']import[\"']", handlers)
        or re.search(r"[\"'](?:view-|menu-)?import[\"']", handlers)
    )
    if not import_wired:
        fail(
            "#130: menu Import must use pick_import_path / pickImportPath "
            "or switch view to import (existing Import tab flow)"
        )

    # 8) View items set the same `view` tokens as the nav buttons.
    if not re.search(r"\bview\s*=", handlers) and not any(
        _quoted_view_token(handlers, tok) for tok in _VIEW_MENU_TOKENS
    ):
        fail(
            "#130: View menu items must set `view` the same as the nav buttons "
            "(people / search / review / doctor) via on_menu_event emit + listen"
        )
    for tok in _VIEW_MENU_TOKENS:
        if not _quoted_view_token(handlers, tok):
            fail(
                f"#130: View menu must switch to {tok} "
                "(same view token as the in-window nav)"
            )

    # 9) Bans: Check for Updates, updater plugin, Preferences window, iCloud menu.
    if _CHECK_UPDATES_ITEM.search(menu_src) or _CHECK_UPDATES_ITEM.search(handlers):
        fail("#130: no Check for Updates menu item (and no updater plugin)")
    if "tauri-plugin-updater" in toml:
        fail("#130: tauri-plugin-updater must not be a dependency")
    if "tauri-plugin-updater" not in deny:
        fail(
            "#130: crates/interlace-tauri/deny.toml must keep banning "
            "tauri-plugin-updater"
        )
    if _PREFERENCES_ITEM.search(menu_src):
        fail("#130: no Preferences / Settings window or menu item (out of scope)")
    if _ICLOUD_MENU_ITEM.search(menu_src):
        fail("#130: no iCloud / iCloud Drive menu item (out of scope)")

    # 10) User-visible: one line in docs/user/app.md and/or docs/hacking/tauri.md.
    if not _DOCS_MENU.search(dtxt):
        fail(
            "#130: docs/user/app.md and/or docs/hacking/tauri.md must mention "
            "the native menu (File → Open archive; no Check for Updates)"
        )

    # Keep using the existing in-window picker — do not drop openPicker.
    if "openPicker" not in app and "pickFolder" not in web_all:
        fail(
            "#130: keep the in-window openPicker / pickFolder path "
            "(menu Open must share it, not replace it with a second picker)"
        )


def assert_chrome_locale(crate: Path) -> None:
    """#131: en+tr UI chrome packs; OS locale; not bodies; not WA packs.

    Ship chrome strings (nav, setup Open archive, doctor, empty states, backup
    banner, common buttons) as en + tr packs under web/. Resolve from the OS
    locale: tr / tr-TR → tr, everything else → en. Message bodies stay stored.
    English remains the default so existing doctor / empty / backup greps pass.
    """
    root = repo_root()
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#131: App.svelte required (setup Open archive + nav Doctor chrome)")
    app = _web_logic(crate)
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    doctor = doctor_path.read_text() if doctor_path.is_file() else ""
    logic = _web_logic(crate)
    cleaned = _without_comments(logic)
    docs = root / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) en + tr chrome packs under web/ (json / ts / toml) — not WA fixture toml.
    en_files, tr_files, combined = _chrome_pack_files(crate)
    if not en_files and not combined:
        fail(
            "#131: English UI chrome pack missing under crates/interlace-tauri/web/ "
            "(en.json / en.ts / en.toml, or a combined chrome/i18n module) — "
            "not interlace-fixtures/locale/*.toml"
        )
    if not tr_files and not combined:
        fail(
            "#131: Turkish UI chrome pack missing under crates/interlace-tauri/web/ "
            "(tr.json / tr.ts / tr.toml, or a combined chrome/i18n module) — "
            "not interlace-fixtures/locale/*.toml"
        )
    en_text = _chrome_en_text(crate)
    tr_text = _chrome_tr_text(crate)
    if not en_text.strip():
        fail("#131: English chrome pack is empty")
    if not tr_text.strip():
        fail("#131: Turkish chrome pack is empty")

    # 2) Resolver follows OS locale; tr* → tr, else en (English default).
    if not _OS_LOCALE_READ.search(cleaned) and not _OS_LOCALE_READ.search(logic):
        fail(
            "#131: chrome locale must follow the OS "
            "(navigator.language / navigator.languages / Intl / Tauri locale) — "
            "not the Import pane WhatsApp/Gmail probe `locale` field"
        )
    resolver = _locale_resolver_surface(cleaned) or _locale_resolver_surface(logic)
    if not _TR_STAR_PICK.search(resolver):
        fail(
            "#131: OS locale tr / tr-TR / tr* must select the tr chrome pack "
            "(startsWith('tr') or equivalent, next to the OS locale read)"
        )
    if not _EN_DEFAULT_PICK.search(resolver):
        fail(
            "#131: every non-tr OS locale must fall back to the en chrome pack "
            "(English is the default so existing fixture/gate copy still passes)"
        )

    # 3) Acceptance strings in the tr pack.
    if "Arşiv aç" not in tr_text:
        fail('#131: tr chrome pack must contain “Arşiv aç” (Open archive / Open existing)')
    if "Doktor" not in tr_text:
        fail('#131: tr chrome pack must contain “Doktor” (Doctor nav + pane title)')

    # 4) English pack keeps the acceptance keys (default / fixtures).
    if not re.search(r"[\"']Doctor[\"']", en_text) and "Doctor" not in en_text:
        fail(
            "#131: en chrome pack must contain “Doctor” "
            "(English default — existing doctor chrome gates stay green)"
        )
    if not re.search(
        r"Open(?: an)? archive|Open existing",
        en_text,
        re.I,
    ):
        fail(
            "#131: en chrome pack must contain “Open archive” / “Open existing” "
            "(English default for setup)"
        )

    # 5) App setup/nav uses the chrome helper — not only hardcoded English.
    helpers = _chrome_helper_names(logic)
    if not helpers and not any(
        re.search(rf"\b{re.escape(n)}\.\w+", logic) for n in _CHROME_PACK_NS
    ):
        fail(
            "#131: App/setup/nav must use a chrome helper "
            "(t / chromeT / i18n / imported chrome pack) — "
            "not only hardcoded English “Open existing…” / “Doctor”"
        )

    open_inners = _control_inners(app, re.compile(r"\bopenPicker\b"))
    if not open_inners:
        open_inners = _control_inners(app, re.compile(r"\bopenPath\b|\bpickFolder\b"))
    if not open_inners:
        fail(
            "#131: setup Open archive / Open existing control missing "
            "(openPicker button must show the chrome string)"
        )
    if not any(_markup_uses_chrome_helper(inner, helpers, logic) for inner in open_inners):
        fail(
            "#131: setup Open archive / Open existing must use the chrome helper "
            "(tr-TR shows “Arşiv aç” — not only hardcoded English on openPicker)"
        )

    nav = _nav_block(app)
    nav_inners = _control_inners(nav or app, re.compile(r"view\s*=\s*[\"']doctor[\"']"))
    if not nav_inners:
        fail(
            "#131: nav Doctor button missing "
            "(in-window nav must use the chrome helper for “Doktor”)"
        )
    if not any(_markup_uses_chrome_helper(inner, helpers, logic) for inner in nav_inners):
        fail(
            "#131: nav Doctor must use the chrome helper "
            "(tr-TR shows “Doktor” — not only hardcoded English)"
        )

    # Doctor pane title (acceptance: nav + pane).
    if doctor:
        doc_headings = _heading_inners(doctor)
        if not doc_headings:
            fail("#131: Doctor pane must keep a title heading (chrome “Doktor” / “Doctor”)")
        if not any(_markup_uses_chrome_helper(inner, helpers, logic) for inner in doc_headings):
            fail(
                "#131: Doctor pane title must use the chrome helper "
                "(not only hardcoded English “Doctor”)"
            )

    # 6) Never translate stored message bodies / snippets / names via the helper.
    body_blob = logic + "\n" + app + "\n" + doctor
    if _chrome_helper_on_body(body_blob, helpers):
        fail(
            "#131: do not pass body_text / snippet / display_name / preview "
            "through the chrome helper — message bodies stay as stored"
        )

    # 7) WA parser packs must not grow UI chrome strings.
    _assert_wa_locale_not_chrome(root)

    # 8) English empty / doctor / backup copy still present (pack or svelte)
    #    so existing English gates keep passing for the default locale.
    svelte_en = app + "\n" + doctor
    for pane_name in ("EmptyState.svelte", "SearchPane.svelte", "ReviewPane.svelte"):
        p = crate / "web" / "lib" / pane_name
        if p.is_file():
            svelte_en += "\n" + p.read_text()
    en_surface = svelte_en + "\n" + en_text
    missing_empty = [s for s in _EN_EMPTY_TITLES if s not in en_surface]
    if len(missing_empty) == len(_EN_EMPTY_TITLES):
        fail(
            "#131: English empty-state copy must remain in the en pack or the panes "
            f"({_EN_EMPTY_TITLES[0]!r}, …) so existing empty-state gates stay English"
        )
    if "Not encrypted at rest" not in en_surface or "FileVault" not in en_surface:
        fail(
            "#131: English doctor / backup honesty copy must remain in the en pack "
            "or Doctor pane (“Not encrypted at rest”, FileVault)"
        )
    if "backup unit" not in en_surface and "data-cloud-warning" not in app:
        fail(
            "#131: English backup / cloud banner copy must remain "
            "(en pack or existing data-cloud-warning banner)"
        )

    # 9) Docs: chrome follows OS language (en/tr); bodies stay as imported.
    if not re.search(
        r"("
        r"OS language"
        r"|OS locale"
        r"|follows (?:the )?OS"
        r"|chrome follows"
        r"|UI chrome.{0,40}(?:language|locale)"
        r"|en(?:glish)?\s*/\s*tr"
        r")",
        dtxt,
        re.I,
    ):
        fail(
            "#131: docs/user/app.md must say chrome follows the OS language (en/tr)"
        )
    if not re.search(
        r"("
        r"message bodies? stay"
        r"|bodies stay as"
        r"|as (?:imported|stored)"
        r"|not (?:translate|translating) (?:message )?bod"
        r"|bodies? (?:are|stay|remain) (?:as )?(?:imported|stored|unchanged)"
        r")",
        dtxt,
        re.I,
    ):
        fail(
            "#131: docs/user/app.md must say message bodies stay as imported / stored"
        )

    # 10) Out of scope: chrome-language override UI, RTL layout.
    if _CHROME_OVERRIDE_UI.search(app) or _CHROME_OVERRIDE_UI.search(logic):
        fail(
            "#131: no chrome-language override / settings UI "
            "(optional later — Import pane WhatsApp locale probe is not chrome)"
        )
    if _DIR_RTL.search(app) or _DIR_RTL.search(logic):
        fail("#131: RTL layout is out of scope")

from tauri_gate.locale_more import assert_chrome_locale_panes
