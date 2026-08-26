"""Locale / macOS menu chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations
import re
from pathlib import Path
from common import fail, repo_root
from tauri_gate.scan import (_CHROME_PACK_NS, _FETCH_CALL, _SCROLL_HELPER_SKIP, _call_arg, _chrome_en_text, _chrome_lang_text, _chrome_pack_files, _function_body, _js_next, _match_closer, _stem_chrome_lang, _tauri_rust_blob, _web_logic, _web_pack_candidates, _without_comments)
from tauri_gate.import_boot import _empty_state_blocks, _markup_uses_chrome_helper
from tauri_gate.status_toasts import _chrome_helper_names, _chrome_helper_on_body


# #130 — native macOS menu (About/Quit, File Open+Import, View tabs). No updater.
_TAURI_MENU_API = re.compile(
    r"("
    r"tauri::menu::"
    r"|MenuBuilder"
    r"|SubmenuBuilder"
    r"|MenuItemBuilder"
    r"|PredefinedMenuItem"
    r"|CheckMenuItemBuilder"
    r"|@tauri-apps/api/menu"
    r")",
)
_MENU_ATTACH = re.compile(
    r"("
    r"\.menu\s*\("
    r"|\.set_menu\s*\("
    r"|\bset_menu\s*\("
    r"|\bsetMenu\s*\("
    r"|\bsetAsAppMenu\s*\("
    r"|\bsetAsWindowMenu\s*\("
    r")",
)
_ABOUT_ITEM = re.compile(
    r"("
    r"PredefinedMenuItem::about"
    r"|\.about\s*\("
    r"|item\s*:\s*[\"']About[\"']"
    r"|[\"']About(?: Interlace)?[\"']"
    r")",
)
_QUIT_ITEM = re.compile(
    r"("
    r"PredefinedMenuItem::quit"
    r"|\.quit\s*\("
    r"|item\s*:\s*[\"']Quit[\"']"
    r"|[\"']Quit(?: Interlace)?[\"']"
    r")",
)
_FILE_SUBMENU = re.compile(r"[\"']File[\"']")
_VIEW_SUBMENU = re.compile(r"[\"']View[\"']")
_OPEN_ITEM = re.compile(
    r"[\"']("
    r"Open archive"
    r"|Open existing(?:…|\.\.\.)?"
    r"|Open(?:…|\.\.\.)?"
    r"|open-archive"
    r"|open_archive"
    r"|file-open"
    r"|menu-open"
    r")[\"']",
    re.I,
)
_IMPORT_ITEM = re.compile(
    r"[\"']("
    r"Import(?:…|\.\.\.)?"
    r"|file-import"
    r"|menu-import"
    r"|import-archive"
    r")[\"']",
)
_CHECK_UPDATES_ITEM = re.compile(
    r"[\"']Check for [Uu]pdates?[\"']"
    r"|PredefinedMenuItem::check_for_updates"
    r"|tauri_plugin_updater"
    r"|plugin-updater"
    r"|UpdaterExt",
)
_PREFERENCES_ITEM = re.compile(
    r"("
    r"PredefinedMenuItem::preferences"
    r"|[\"']Preferences(?:…|\.\.\.)?[\"']"
    r"|[\"']Settings(?:…|\.\.\.)?[\"']"
    r"|PreferencesWindow"
    r"|open_preferences"
    r")",
)
_ICLOUD_MENU_ITEM = re.compile(
    r"[\"'][^\"']*iCloud[^\"']*[\"']",
    re.I,
)
_ABOUT_ANCHOR = re.compile(
    r"("
    r"AboutMetadata"
    r"|PredefinedMenuItem::about"
    r"|\.about\s*\("
    r"|[\"']About(?: Interlace)?[\"']"
    r"|(?:const|static|let)\s+ABOUT\w*"
    r")",
)
_MENU_HANDLER_NAMES = (
    "on_menu_event",
    "handle_menu_event",
    "handle_menu",
    "menu_event",
    "applyMenu",
    "onMenu",
    "onMenuEvent",
    "handleMenu",
)
_LISTEN_CALL = re.compile(
    r"\b(?:listen|once|onMenuEvent)\s*\(",
)
_VIEW_MENU_TOKENS = ("people", "search", "review", "doctor")
_ABOUT_OFFLINE = re.compile(r"\boffline\b", re.I)
_ABOUT_NOT_ENCRYPTED = re.compile(r"not encrypted at rest", re.I)
_ABOUT_FILEVAULT = re.compile(r"\bFileVault\b")
_DOCS_MENU = re.compile(
    r"("
    r"native menu"
    r"|menu bar"
    r"|File menu"
    r"|macOS menu"
    r"|Open archive"
    r")",
    re.I,
)


def _menu_web_blob(crate: Path) -> str:
    """Web sources that build a Tauri menu (not the in-window nav / bits-ui menus)."""
    parts: list[str] = []
    web = crate / "web"
    if not web.is_dir():
        return ""
    for p in sorted(web.rglob("*")):
        if p.suffix not in {".svelte", ".ts", ".js"} or "node_modules" in p.parts:
            continue
        text = p.read_text()
        if (
            "@tauri-apps/api/menu" in text
            or "PredefinedMenuItem" in text
            or "MenuItem.new" in text
            or "Menu.new" in text
        ):
            parts.append(text)
    return "\n".join(parts)


def _on_menu_event_bodies(src: str) -> list[str]:
    bodies: list[str] = []
    for m in re.finditer(r"\.on_menu_event\s*\(", src):
        arg = _call_arg(src, m.end() - 1)
        if arg:
            bodies.append(arg)
    for name in _MENU_HANDLER_NAMES:
        body = _function_body(src, name)
        if body:
            bodies.append(body)
    return bodies


def _listen_bodies(src: str) -> list[str]:
    bodies: list[str] = []
    for m in _LISTEN_CALL.finditer(src):
        open_paren = src.find("(", m.start())
        if open_paren < 0:
            continue
        arg = _call_arg(src, open_paren)
        if arg:
            bodies.append(arg)
    return bodies


def _menu_handler_surface(rust: str, web: str) -> str:
    """Rust on_menu_event + frontend listen / menu-handler bodies (and one callee)."""
    chunks = _on_menu_event_bodies(rust) + _listen_bodies(web)
    seen = set(_MENU_HANDLER_NAMES)
    extra: list[str] = []
    blob = "\n".join(chunks)
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", blob):
        name = m.group(1)
        if name in seen or name in _SCROLL_HELPER_SKIP:
            continue
        seen.add(name)
        body = _function_body(web, name) or _function_body(rust, name)
        if body:
            extra.append(body)
    return "\n".join(chunks + extra)


def _about_copy_surface(rust: str, web_menu: str) -> str:
    chunks: list[str] = []
    for src in (rust, web_menu):
        if not src:
            continue
        for m in _ABOUT_ANCHOR.finditer(src):
            chunks.append(src[max(0, m.start() - 200) : m.end() + 900])
    return "\n".join(chunks)


def _quoted_view_token(blob: str, token: str) -> bool:
    return bool(
        re.search(
            rf"("
            rf"view\s*=\s*[\"']{token}[\"']"
            rf"|[\"'](?:view-|menu-)?{token}[\"']"
            rf")",
            blob,
        )
    )


def assert_macos_menu(crate: Path) -> None:
    """#130: native macOS menu — About/Quit, File Open+Import, View tabs; no updater."""
    rust = _tauri_rust_blob(crate)
    web_all = _web_logic(crate)
    web_menu = _menu_web_blob(crate)
    menu_src = rust + "\n" + web_menu
    app_path = crate / "web" / "App.svelte"
    app = app_path.read_text() if app_path.is_file() else ""
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
_WA_PARSER_KEYS = frozenset(
    {
        "id",
        "family_hints",
        "you_tokens",
        "date_time_patterns",
        "media_omitted",
        "file_attached_pattern",
        "file_attached_alt",
        "forwarded_tokens",
        "title_prefixes_dm",
        "title_prefixes_group",
        "system_created_group",
        "system_added",
        "system_subject",
        "system_encryption",
        "encryption_banner_startswith",
    }
)
_WA_UI_BAN = ("Arşiv aç", "Open existing", "Open an archive")
_EN_EMPTY_TITLES = (
    "No people yet",
    "Select a person",
    "No doctor issues",
    "Nothing to review",
    "Type a query",
    "No hits",
)
_OS_LOCALE_READ = re.compile(
    r"("
    r"navigator\.language"
    r"|navigator\.languages"
    r"|Intl\.DateTimeFormat\s*\("
    r"|resolvedOptions\s*\(\s*\)\s*\.\s*locale"
    r"|@tauri-apps/plugin-os"
    r"|\bosLocale\b"
    r"|\bgetLocale\s*\("
    r"|\blocaleIdentifier\b"
    r")",
)
_TR_STAR_PICK = re.compile(
    r"("
    r"startsWith\s*\(\s*[\"']tr"
    r"|starts_with\s*\(\s*[\"']tr"
    r"|slice\s*\(\s*0\s*,\s*2\s*\)\s*===?\s*[\"']tr[\"']"
    r"|substring\s*\(\s*0\s*,\s*2\s*\)\s*===?\s*[\"']tr[\"']"
    r"|===?\s*[\"']tr[\"']"
    r"|===?\s*[\"']tr-[A-Za-z]{2}[\"']"
    r"|/\^tr/i?"
    r"|match\s*\(\s*/\^tr"
    r")",
)
_EN_DEFAULT_PICK = re.compile(
    r"("
    r":\s*[\"']en[\"']"
    r"|\|\|\s*[\"']en[\"']"
    r"|\?\?\s*[\"']en[\"']"
    r"|else\s+[\"']en[\"']"
    r"|return\s+[\"']en[\"']"
    r"|fallback(?:Locale|Lang|Pack)?\s*[:=]\s*[\"']en[\"']"
    r"|default(?:Locale|Lang|Pack)?\s*[:=]\s*[\"']en[\"']"
    r"|\?\s*[\"']tr[\"']\s*:\s*[\"']en[\"']"
    r")",
)
_CHROME_OVERRIDE_UI = re.compile(
    r"("
    r"\bchromeLocale\b"
    r"|\buiLocale\b"
    r"|\buiLanguage\b"
    r"|\bdisplayLanguage\b"
    r"|[\"']UI language[\"']"
    r"|[\"']Display language[\"']"
    r"|[\"']App language[\"']"
    r"|[\"']Chrome language[\"']"
    r")",
    re.I,
)
_DIR_RTL = re.compile(r"\bdir\s*=\s*[\"']rtl[\"']", re.I)


def _chrome_tr_text(crate: Path) -> str:
    return _chrome_lang_text(crate, "tr")


def _control_inners(src: str, needle: re.Pattern[str], tags: tuple[str, ...] = ("Button", "button")) -> list[str]:
    """Inner HTML of a Button/button whose open tag (or nearby) matches needle.

    Closing tags may split across lines (`</Button\\n>`).
    """
    inners: list[str] = []
    for m in needle.finditer(src):
        before = src[: m.start()]
        open_idx = -1
        tag_found = ""
        for tag in tags:
            idx = before.lower().rfind("<" + tag.lower())
            if idx > open_idx:
                open_idx = idx
                tag_found = tag
        if open_idx < 0 or m.start() - open_idx > 900:
            continue
        gt = src.find(">", open_idx)
        if gt < 0:
            continue
        close_m = re.search(rf"</{re.escape(tag_found)}\s*>", src[gt:], re.I)
        if not close_m:
            continue
        inners.append(src[gt + 1 : gt + close_m.start()])
    return inners


def _nav_block(src: str) -> str:
    m = re.search(r"<nav\b[^>]*>(.*?)</nav>", src, re.S | re.I)
    return m.group(0) if m else ""


def _locale_resolver_surface(src: str) -> str:
    """Windows around OS-locale reads / named resolvers — not pack dictionaries."""
    chunks: list[str] = []
    for m in _OS_LOCALE_READ.finditer(src):
        chunks.append(src[max(0, m.start() - 400) : m.end() + 500])
    for name in (
        "resolveLocale",
        "chromeLocale",
        "pickLocale",
        "detectLocale",
        "localeFromOs",
        "osLang",
        "chromeLang",
        "resolvedLocale",
        "uiLang",
    ):
        body = _function_body(src, name)
        if body:
            chunks.append(body)
        for dm in re.finditer(rf"(?:const|let|var|function)\s+{re.escape(name)}\b", src):
            chunks.append(src[dm.start() : dm.start() + 800])
    return "\n".join(chunks)


def _heading_inners(src: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"<h1\b[^>]*>(.*?)</h1>", src, re.S | re.I)]


def _toml_top_keys(text: str) -> set[str]:
    return set(re.findall(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", text, re.M))


def _assert_wa_locale_not_chrome(root: Path) -> None:
    """UI chrome must not land in WhatsApp/Gmail parser packs."""
    for rel in (
        Path("crates") / "interlace-fixtures" / "locale",
        Path("crates") / "interlace-core" / "locale",
    ):
        folder = root / rel
        if not folder.is_dir():
            continue
        for p in sorted(folder.iterdir()):
            if not p.is_file():
                continue
            loc = p.relative_to(root)
            if p.suffix != ".toml":
                fail(
                    f"#131: {loc} is not a WA parser pack — "
                    "do not add UI chrome files under interlace-fixtures/locale "
                    "(or core locale copies)"
                )
            text = p.read_text()
            extra = _toml_top_keys(text) - _WA_PARSER_KEYS
            if extra:
                fail(
                    f"#131: do not add UI chrome keys to WA locale pack {loc}: "
                    f"{sorted(extra)} — chrome lives under crates/interlace-tauri/web/"
                )
            for s in _WA_UI_BAN:
                if s in text:
                    fail(
                        f"#131: do not put UI chrome string {s!r} in WA locale pack {loc}"
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
    app = app_path.read_text()
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


# #278 — finish en+tr chrome (Review / Import / Doctor). Additive;
# do not rewrite #131 assert_chrome_locale.
_PANE_CHROME_FILES = (
    "ReviewPane.svelte",
    "ImportPane.svelte",
    "DoctorPane.svelte",
)
_PANE_CHROME_PHRASES = (
    ("ReviewPane.svelte", "Nothing to review", "Review empty-state title"),
    ("ReviewPane.svelte", "Name-only WhatsApp matches", "Review empty-state body"),
    ("ReviewPane.svelte", "Loading review queue", "Review loading"),
    ("ReviewPane.svelte", "Link these people", "Review confirm “Link these people”"),
    ("ReviewPane.svelte", "Stop suggesting", "Review confirm “Stop suggesting”"),
    ("ReviewPane.svelte", "Undo last link", "Review undo / confirm “Undo last link”"),
    ("ReviewPane.svelte", "Undoing", "Review “Undoing…”"),
    ("ImportPane.svelte", "No file selected", "Import empty-state title"),
    ("ImportPane.svelte", "Pick a WhatsApp ZIP", "Import empty-state body"),
    ("ImportPane.svelte", "Pick file", "Import “Pick file”"),
    ("DoctorPane.svelte", "No doctor issues", "Doctor empty-state title"),
    ("DoctorPane.svelte", "Unreferenced files still need GC", "Doctor empty-state body"),
    ("DoctorPane.svelte", "Run integrity check", "Doctor integrity confirm"),
    ("DoctorPane.svelte", "Rebuild search index", "Doctor rebuild confirm"),
    ("DoctorPane.svelte", "Garbage-collect unused CAS", "Doctor GC confirm"),
)
_PANE_EN_REQUIRED = (
    "Nothing to review",
    "Name-only WhatsApp matches",
    "Loading review queue",
    "Link these people",
    "Stop suggesting",
    "Undo last link",
    "No file selected",
    "Pick a WhatsApp ZIP",
    "Pick file",
    "No doctor issues",
    "Unreferenced files still need GC",
    "Run integrity check",
    "Rebuild search index",
    "Garbage-collect unused CAS",
)
_PANE_BACKUP_LEFTOVER = (
    "There is no separate backup command",
    "Do not keep the",
    "Time Machine",
)
_DOCS_PANE_CHROME_LOCALE = re.compile(
    r"("
    r"Review.{0,80}Import.{0,80}Doctor.{0,100}"
    r"(?:chrome.{0,60})?(?:follows.{0,40}OS|OS language|en\s*/\s*tr)"
    r"|"
    r"(?:Review|Import|Doctor).{0,24}(?:/|,).{0,24}"
    r"(?:Review|Import|Doctor).{0,24}(?:/|,).{0,24}"
    r"(?:Review|Import|Doctor).{0,100}"
    r"(?:chrome.{0,60})?(?:follows.{0,40}OS|OS language|en\s*/\s*tr)"
    r")",
    re.I | re.S,
)
_DOCS_PANE_BODIES_STAY = re.compile(
    r"("
    r"bodies stay as imported"
    r"|message bodies stay as imported"
    r"|bodies stay as (?:imported|stored)"
    r"|bodies? (?:are|stay|remain) (?:as )?(?:imported|stored|unchanged)"
    r")",
    re.I,
)
_LOCALE_FETCH = re.compile(
    r"\bfetch\s*\(\s*[`'\"`][^`'\"`]{0,160}"
    r"(?:locale|locales|i18n|l10n|en\.json|tr\.json)",
    re.I,
)
_THIRD_PACK_STEM = re.compile(
    r"(?:^|[._-])(de|fr|es|it|nl|pt|ru|ja|zh|ar|ko)(?:[-_][A-Za-z]+)?$",
    re.I,
)


def _pane_file(crate: Path, name: str) -> Path:
    return crate / "web" / "lib" / name


def _svelte_attr_raw(tag: str, name: str) -> str:
    m = re.search(
        rf"""\b{re.escape(name)}\s*=\s*(
            \{{(?:[^{{}}]|\{{[^{{}}]*\}})*\}}
            |\"[^\"]*\"
            |'[^']*'
        )""",
        tag,
        re.X | re.S,
    )
    return m.group(1) if m else ""


def _split_first_arg(args: str) -> str:
    i = 0
    n = len(args)
    depth = 0
    while i < n:
        nxt = _js_next(args, i)
        if nxt != i:
            i = nxt
            continue
        c = args[i]
        if c in "({[":
            depth += 1
        elif c in ")}]":
            depth -= 1
        elif c == "," and depth == 0:
            return args[:i].strip()
        i += 1
    return args.strip()


def _call_first_args(src: str, name: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(rf"\b{re.escape(name)}\s*\(", src):
        prefix = src[max(0, m.start() - 80) : m.start()]
        if re.search(r"(?:async\s+)?function\s+$", prefix):
            continue
        if re.search(r"(?:const|let|var)\s+$", prefix):
            continue
        args = _call_arg(src, m.end() - 1)
        if args.strip():
            out.append(_split_first_arg(args))
    return out


def _chrome_pack_entries(text: str) -> dict[str, str]:
    """Parse `key: "value"` entries from a chrome pack object."""
    blob = text
    m = re.search(
        r"export\s+const\s+(?:en|tr)\s*(?::\s*\w+\s*)?=\s*\{",
        text,
    )
    if m:
        brace = text.find("{", m.start())
        end = _match_closer(text, brace)
        if end > brace:
            blob = text[brace + 1 : end]
    entries: dict[str, str] = {}
    i = 0
    n = len(blob)
    key_rx = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*:")
    while i < n:
        km = key_rx.search(blob, i)
        if not km:
            break
        j = km.end()
        while j < n and blob[j] in " \t\n\r":
            j += 1
        if j >= n or blob[j] not in "'\"`":
            i = km.end()
            continue
        end = _js_next(blob, j)
        raw = blob[j + 1 : end - 1] if end > j + 1 else ""
        entries[km.group(1)] = (
            raw.replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace('\\"', '"')
            .replace("\\'", "'")
            .replace("\\\\", "\\")
        )
        i = end
    return entries


def _keys_for_phrase(entries: dict[str, str], phrase: str) -> list[str]:
    return [k for k, v in entries.items() if phrase in v]


def _pane_chrome_phrases(panes: dict[str, str]) -> list[str]:
    leftover = [
        label for name, phrase, label in _PANE_CHROME_PHRASES if phrase in panes[name]
    ]
    if re.search(r">\s*Cancel\s*<", panes["ImportPane.svelte"]):
        leftover.append("Import Cancel")
    return leftover


def _pane_chrome_unwired(
    panes: dict[str, str], helpers: set[str]
) -> list[str]:
    """EmptyState / ask() / undo / pick / cancel still not going through t()."""
    leftover: list[str] = []
    for name in _PANE_CHROME_FILES:
        src = panes[name]
        for block in _empty_state_blocks(src):
            for attr in ("title", "body", "actionLabel"):
                val = _svelte_attr_raw(block, attr)
                if val and not _markup_uses_chrome_helper(val, helpers, src):
                    leftover.append(f"{name.split('.', 1)[0]} EmptyState {attr}")
    for name in ("ReviewPane.svelte", "DoctorPane.svelte"):
        src = panes[name]
        asks = _call_first_args(src, "ask")
        if not asks:
            leftover.append(
                f"{name.split('.', 1)[0]} ConfirmDialog titles "
                "(ask() first arg must be t())"
            )
            continue
        for arg in asks:
            if not _markup_uses_chrome_helper(arg, helpers, src):
                leftover.append(
                    f"{name.split('.', 1)[0]} ConfirmDialog title {arg[:48]}"
                )
    review = panes["ReviewPane.svelte"]
    undo_inners = _control_inners(review, re.compile(r"data-review-undo"))
    if not undo_inners and re.search(r"Undo last link|requestUndo", review):
        undo_inners = _control_inners(review, re.compile(r"requestUndo"))
    if undo_inners and not any(
        _markup_uses_chrome_helper(inner, helpers, review) for inner in undo_inners
    ):
        leftover.append("Review undo label")
    imp = panes["ImportPane.svelte"]
    pick_inners = _control_inners(imp, re.compile(r"pick\(\s*false\s*\)"))
    if pick_inners and not any(
        _markup_uses_chrome_helper(inner, helpers, imp) for inner in pick_inners
    ):
        leftover.append("Import Pick file button")
    cancel_inners = _control_inners(imp, re.compile(r"data-import-cancel"))
    if not cancel_inners:
        leftover.append("Import Cancel")
    elif not any(
        _markup_uses_chrome_helper(inner, helpers, imp) for inner in cancel_inners
    ):
        leftover.append("Import Cancel")
    seen: set[str] = set()
    out: list[str] = []
    for item in leftover:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def assert_chrome_locale_panes(crate: Path) -> None:
    """#278: Review / Import / Doctor remaining chrome uses t().

    Empty states, ConfirmDialog titles (Link these people / Stop suggesting /
    Undo last link / doctor integrity / rebuild / GC), undo label, Pick file,
    and Import Cancel go through t(). New keys exist in both packs; tr values
    are not identical English copies. No t(body_text|snippet|display_name|
    preview). detectLocale stays OS-first (tr* → tr). No third pack. No fetch
    of locale files. Keep #131 Arşiv aç / Doktor. Docs: Review / Import /
    Doctor chrome follows OS language (en/tr); bodies stay as imported.
    Do not rewrite #131.
    """
    root = repo_root()
    panes: dict[str, str] = {}
    for name in _PANE_CHROME_FILES:
        path = _pane_file(crate, name)
        if not path.is_file():
            fail(
                f"#278: {name} required "
                "(Review / Import / Doctor remaining chrome uses t())"
            )
        panes[name] = path.read_text()
    logic = _web_logic(crate)
    cleaned = _without_comments(logic)
    helpers = _chrome_helper_names(logic)
    en_text = _chrome_en_text(crate)
    tr_text = _chrome_tr_text(crate)
    i18n_path = crate / "web" / "lib" / "i18n.ts"
    i18n = i18n_path.read_text() if i18n_path.is_file() else ""

    # 1) Remaining Review / Import / Doctor chrome uses t() — not hardcoded English.
    leftover = _pane_chrome_phrases(panes)
    if leftover:
        fail(
            "#278: Review / Import / Doctor remaining chrome must use t() — "
            "still hardcoded English: " + "; ".join(leftover)
        )
    unwired = _pane_chrome_unwired(panes, helpers)
    if unwired:
        fail(
            "#278: Review / Import / Doctor remaining chrome must use t() "
            "(empty states, ConfirmDialog titles, undo, Pick file, Import Cancel): "
            + "; ".join(unwired)
        )

    # 2) Those strings live in the en pack; same keys in tr; tr is not an English copy.
    if not en_text.strip() or not tr_text.strip():
        fail("#278: en + tr chrome packs required (do not drop #131 packs)")
    en_entries = _chrome_pack_entries(en_text)
    tr_entries = _chrome_pack_entries(tr_text)
    if not en_entries or not tr_entries:
        fail("#278: could not parse chrome pack key/value entries from en.ts / tr.ts")
    missing_en = [p for p in _PANE_EN_REQUIRED if not _keys_for_phrase(en_entries, p)]
    if "Cancel" not in en_entries.values() and not _keys_for_phrase(en_entries, "Cancel"):
        missing_en.append("Cancel")
    if missing_en:
        fail(
            "#278: new Review / Import / Doctor chrome keys must exist in the en pack "
            f"(missing values: {', '.join(missing_en)})"
        )
    extra_en = set(en_entries) - set(tr_entries)
    extra_tr = set(tr_entries) - set(en_entries)
    if extra_en or extra_tr:
        bits: list[str] = []
        if extra_en:
            bits.append("in en only: " + ", ".join(sorted(extra_en)))
        if extra_tr:
            bits.append("in tr only: " + ", ".join(sorted(extra_tr)))
        fail(
            "#278: same ChromeKey on both en and tr packs — " + "; ".join(bits)
        )
    copied: list[str] = []
    seen_keys: set[str] = set()
    for phrase in (*_PANE_EN_REQUIRED, "Cancel"):
        for key in _keys_for_phrase(en_entries, phrase):
            if key in seen_keys:
                continue
            seen_keys.add(key)
            ev = en_entries.get(key, "").strip()
            tv = tr_entries.get(key, "").strip()
            if not tv:
                copied.append(f"{key} missing in tr")
            elif tv == ev:
                copied.append(key)
    if copied:
        fail(
            "#278: for new Review / Import / Doctor keys, tr values must not be "
            "identical English copies: " + ", ".join(copied)
        )

    # 3) Never t(body_text|snippet|display_name|preview).
    body_blob = logic + "\n" + "\n".join(panes[n] for n in _PANE_CHROME_FILES)
    if _chrome_helper_on_body(body_blob, helpers):
        fail(
            "#278: do not pass body_text / snippet / display_name / preview "
            "through t() — message bodies stay as imported"
        )

    # 4) detectLocale still OS-first (tr* → tr). No third pack. No fetch of locale files.
    detect = _function_body(i18n, "detectLocale") or _function_body(cleaned, "detectLocale")
    resolver = detect or _locale_resolver_surface(cleaned) or _locale_resolver_surface(logic)
    if not _OS_LOCALE_READ.search(resolver) and not _OS_LOCALE_READ.search(i18n):
        fail(
            "#278: detectLocale must stay OS-first "
            "(navigator.language / navigator.languages / Intl / Tauri) — "
            "tr* → tr, else en"
        )
    if not _TR_STAR_PICK.search(resolver):
        fail("#278: detectLocale must still map OS locale tr* → tr")
    if not _EN_DEFAULT_PICK.search(resolver):
        fail("#278: detectLocale must still default every non-tr OS locale to en")
    third: list[str] = []
    locale_dir = crate / "web" / "lib" / "locales"
    if locale_dir.is_dir():
        for p in sorted(locale_dir.iterdir()):
            if not p.is_file() or p.name.endswith(".d.ts"):
                continue
            if p.suffix not in {".ts", ".json", ".toml"}:
                continue
            stem = p.stem.lower()
            if stem in {"en", "tr", "index"}:
                continue
            third.append(str(p.relative_to(crate)))
    for p in _web_pack_candidates(crate):
        lang = _stem_chrome_lang(p)
        if lang and lang not in {"en", "tr"}:
            rel = str(p.relative_to(crate))
            if rel not in third:
                third.append(rel)
        elif _THIRD_PACK_STEM.search(p.stem):
            rel = str(p.relative_to(crate))
            if rel not in third:
                third.append(rel)
    if third:
        fail(
            "#278: no third locale pack — en + tr only. Found: " + ", ".join(third)
        )
    fetch_hits: list[str] = []
    for label, src in (
        ("i18n.ts", i18n),
        ("en pack", en_text),
        ("tr pack", tr_text),
        ("ReviewPane", panes["ReviewPane.svelte"]),
        ("ImportPane", panes["ImportPane.svelte"]),
        ("DoctorPane", panes["DoctorPane.svelte"]),
    ):
        surface = _without_comments(src)
        if _FETCH_CALL.search(surface) and (
            label in {"i18n.ts", "en pack", "tr pack"} or _LOCALE_FETCH.search(surface)
        ):
            fetch_hits.append(label)
    if _LOCALE_FETCH.search(cleaned):
        fetch_hits.append("web logic")
    if fetch_hits:
        fail(
            "#278: no fetch( of locale files — chrome packs are bundled. Found in: "
            + ", ".join(dict.fromkeys(fetch_hits))
        )

    # 5) Keep #131 Arşiv aç / Doktor.
    if "Arşiv aç" not in tr_text:
        fail('#278: keep #131 “Arşiv aç” in the tr pack')
    if "Doktor" not in tr_text:
        fail('#278: keep #131 “Doktor” in the tr pack')

    # Leftover Doctor backup sentences (remaining chrome, after the listed panes).
    doctor = panes["DoctorPane.svelte"]
    backup_left = [p for p in _PANE_BACKUP_LEFTOVER if p in doctor]
    if backup_left:
        fail(
            "#278: leftover Doctor backup chrome must use t() — still hardcoded: "
            + ", ".join(backup_left)
        )

    # 6) Docs: Review / Import / Doctor chrome follows OS language; bodies stay imported.
    docs = root / "docs" / "user" / "app.md"
    if not docs.is_file():
        fail(
            "#278: docs/user/app.md required — Review / Import / Doctor chrome "
            "follows OS language (en/tr); bodies stay as imported"
        )
    dtxt = docs.read_text()
    if not _DOCS_PANE_CHROME_LOCALE.search(dtxt):
        fail(
            "#278: docs/user/app.md must say Review / Import / Doctor chrome "
            "follows OS language (en/tr)"
        )
    if not _DOCS_PANE_BODIES_STAY.search(dtxt):
        fail(
            "#278: docs/user/app.md must say message bodies stay as imported"
        )
