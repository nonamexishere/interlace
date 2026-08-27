"""Helpers extracted from locale.py (locale_menu)."""
from __future__ import annotations

from __future__ import annotations

from __future__ import annotations
import re
from pathlib import Path
from common import fail, repo_root
from tauri_gate.scan import (_CHROME_PACK_NS, _FETCH_CALL, _SCROLL_HELPER_SKIP, _call_arg, _chrome_en_text, _chrome_lang_text, _chrome_pack_files, _function_body, _js_next, _match_closer, _stem_chrome_lang, _tauri_rust_blob, _web_logic, _web_pack_candidates, _without_comments)
from tauri_gate.import_boot_guards import (
    _empty_state_blocks,
    _markup_uses_chrome_helper,
)
from tauri_gate.status_toasts_chrome import _chrome_helper_names
from tauri_gate.status_toasts_toast import _chrome_helper_on_body


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

from tauri_gate.locale_menu_rest import (
    _DIR_RTL,
    _chrome_tr_text,
    _control_inners,
    _nav_block,
    _locale_resolver_surface,
    _heading_inners,
    _toml_top_keys,
    _assert_wa_locale_not_chrome,
    _PANE_CHROME_FILES,
    _PANE_CHROME_PHRASES,
    _PANE_EN_REQUIRED,
    _PANE_BACKUP_LEFTOVER,
    _DOCS_PANE_CHROME_LOCALE,
    _DOCS_PANE_BODIES_STAY,
    _LOCALE_FETCH,
    _THIRD_PACK_STEM,
    _pane_file,
    _svelte_attr_raw,
    __all__,
)

__all__ = [
    "_TAURI_MENU_API",
    "_MENU_ATTACH",
    "_ABOUT_ITEM",
    "_QUIT_ITEM",
    "_FILE_SUBMENU",
    "_VIEW_SUBMENU",
    "_OPEN_ITEM",
    "_IMPORT_ITEM",
    "_CHECK_UPDATES_ITEM",
    "_PREFERENCES_ITEM",
    "_ICLOUD_MENU_ITEM",
    "_ABOUT_ANCHOR",
    "_MENU_HANDLER_NAMES",
    "_LISTEN_CALL",
    "_VIEW_MENU_TOKENS",
    "_ABOUT_OFFLINE",
    "_ABOUT_NOT_ENCRYPTED",
    "_ABOUT_FILEVAULT",
    "_DOCS_MENU",
    "_menu_web_blob",
    "_on_menu_event_bodies",
    "_listen_bodies",
    "_menu_handler_surface",
    "_about_copy_surface",
    "_quoted_view_token",
    "_WA_PARSER_KEYS",
    "_WA_UI_BAN",
    "_EN_EMPTY_TITLES",
    "_OS_LOCALE_READ",
    "_TR_STAR_PICK",
    "_EN_DEFAULT_PICK",
    "_CHROME_OVERRIDE_UI",
    "_DIR_RTL",
    "_chrome_tr_text",
    "_control_inners",
    "_nav_block",
    "_locale_resolver_surface",
    "_heading_inners",
    "_toml_top_keys",
    "_assert_wa_locale_not_chrome",
    "_PANE_CHROME_FILES",
    "_PANE_CHROME_PHRASES",
    "_PANE_EN_REQUIRED",
    "_PANE_BACKUP_LEFTOVER",
    "_DOCS_PANE_CHROME_LOCALE",
    "_DOCS_PANE_BODIES_STAY",
    "_LOCALE_FETCH",
    "_THIRD_PACK_STEM",
    "_pane_file",
    "_svelte_attr_raw",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_CHROME_PACK_NS",
    "_FETCH_CALL",
    "_SCROLL_HELPER_SKIP",
    "_call_arg",
    "_chrome_en_text",
    "_chrome_lang_text",
    "_chrome_pack_files",
    "_function_body",
    "_js_next",
    "_match_closer",
    "_stem_chrome_lang",
    "_tauri_rust_blob",
    "_web_logic",
    "_web_pack_candidates",
    "_without_comments",
    "_empty_state_blocks",
    "_markup_uses_chrome_helper",
    "_chrome_helper_names",
    "_chrome_helper_on_body",
]
