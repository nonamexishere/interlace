"""Continuation of locale_menu."""
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
from tauri_gate.locale_menu import (
    _WA_PARSER_KEYS,
    _WA_UI_BAN,
    _OS_LOCALE_READ,
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
    "re",
    "Path",
    "fail",
    "repo_root",
    "_CHROME_PACK_NS",
    "_FETCH_CALL",
    "_chrome_en_text",
    "_chrome_pack_files",
    "_function_body",
    "_stem_chrome_lang",
    "_tauri_rust_blob",
    "_web_logic",
    "_web_pack_candidates",
    "_without_comments",
    "_markup_uses_chrome_helper",
    "_chrome_helper_names",
    "_chrome_helper_on_body",
    "annotations",
    "_SCROLL_HELPER_SKIP",
    "_call_arg",
    "_chrome_lang_text",
    "_js_next",
    "_match_closer",
    "_empty_state_blocks",
]

__all__ = [
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
    "__all__",
]
