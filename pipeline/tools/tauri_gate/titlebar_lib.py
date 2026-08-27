"""Helpers extracted from titlebar.py (titlebar_lib)."""
from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _call_arg,
    _function_body,
    _matched_inner,
    _opening_tag,
    _search_pane_blob,
    _strip_html_comments,
    _svelte_markup,
    _tag_name,
    _tauri_rust_blob,
    _template_stack,
    _web_logic,
    _web_sources,
    _without_comments,
    CSP,
)

from tauri_gate.locale_menu import (
    _FILE_SUBMENU,
    _TAURI_MENU_API,
    _VIEW_SUBMENU,
)

from tauri_gate.status_toasts_chrome import _claim_without_negation
from tauri_gate.status_toasts_toast import _tag_inner





# #129 — native window title follows open person / view (Cmd-tab).
# Separator: em dash (—) preferred; en dash / " - " / " --- " accepted if consistent.
_TITLE_SEP = r"(?:—|–|---| - )"
_SET_TITLE_CALL = re.compile(r"\bsetTitle\s*\(")
_WINDOW_API_IMPORT = re.compile(
    r"from\s+[\"']@tauri-apps/api/window[\"']"
    r"|import\s*\{[^}]*\b(?:getCurrentWindow|Window)\b[^}]*\}\s*from\s*[\"']@tauri-apps/api"
)
_GET_CURRENT_WINDOW = re.compile(r"\bgetCurrentWindow\s*\(")
_DOCK_BADGE_API = re.compile(
    r"("
    r"\bsetBadgeCount\b"
    r"|\bsetBadgeLabel\b"
    r"|\bsetOverlayIcon\b"
    r"|\bdock\s*\.\s*setBadge\b"
    r"|\bbadgeCount\b"
    r"|\bBadgeCount\b"
    r")",
)
# Message fields that must never flow into setTitle args / title helpers.
_TITLE_BODY_LEAK = re.compile(
    r"("
    r"\bbody_text\b"
    r"|\bsnippet\b"
    r"|\bdisplayBody\b"
    r"|\bsearchBody\b"
    r"|\blast_body\b"
    r"|\blastBody\b"
    r"|\blast_preview\b"
    r"|\bactivityPreview\b"
    r")",
)
_TITLE_HELPER_NAMES = (
    "windowTitle",
    "nativeTitle",
    "appTitle",
    "titleForView",
    "titleForWindow",
    "syncWindowTitle",
    "updateWindowTitle",
    "setWindowTitle",
    "computeWindowTitle",
    "formatWindowTitle",
)


def _title_path_sources(crate: Path) -> str:
    """Web logic that may own setTitle (App + helpers; exclude pure UI chrome)."""
    return _web_logic(crate)


def _collect_set_title_args(src: str) -> list[str]:
    args: list[str] = []
    for m in _SET_TITLE_CALL.finditer(src):
        open_paren = m.end() - 1
        if open_paren < 0 or src[open_paren] != "(":
            continue
        arg = _call_arg(src, open_paren)
        if arg is not None:
            args.append(arg)
    return args


def _title_helper_bodies(src: str) -> list[str]:
    bodies: list[str] = []
    for name in _TITLE_HELPER_NAMES:
        body = _function_body(src, name)
        if body:
            bodies.append(body)
    # $derived / const title = (...) => … / function expressions assigned to common names.
    for name in _TITLE_HELPER_NAMES:
        for m in re.finditer(
            rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?:\$derived(?:\.\w+)?\s*)?"
            rf"(?:\([^)]*\)\s*=>\s*|\([^)]*\)\s*=>\s*\{{|"
            rf"function\s*\([^)]*\)\s*\{{)?",
            src,
        ):
            # Prefer brace body via _function_body; also capture arrow expr after =.
            eq = src.find("=", m.start())
            if eq < 0:
                continue
            rest = src[eq + 1 : eq + 1 + 800].lstrip()
            if rest.startswith("$derived"):
                # $derived(expr) or $derived.by(() => …)
                dm = re.match(
                    r"\$derived(?:\.by)?\s*\(",
                    rest,
                )
                if dm:
                    arg = _call_arg(rest, dm.end() - 1)
                    if arg:
                        bodies.append(arg)
            elif rest.startswith("(") or rest.startswith("async"):
                pass  # covered by _function_body when brace form
            else:
                # Arrow/expression form: name = `…` / name = cond ? … : …
                end = rest.find("\n")
                chunk = rest if end < 0 else rest[: max(end, 200)]
                bodies.append(chunk)
    return bodies


# #211 — overlay titlebar: native traffic lights, drag region, no second wordmark.
_DRAG_REGION = re.compile(
    r"\bdata-tauri-drag-region(?:\s*=\s*(?:\"\"|''|true|\{(?:\"\"|'')\}))?",
    re.I,
)
_WORDMARK_BRAND = re.compile(
    r"<(?:strong|b|h1|h2|h3|em)\b[^>]*>\s*Interlace\s*</",
    re.I,
)
_WORDMARK_TEXT = re.compile(r">\s*Interlace\s*<")
_TRAFFIC_NAME = re.compile(r"\btraffic[-_ ]?lights?\b|\bwindow-controls\b", re.I)
_TRAFFIC_HEX = re.compile(
    r"#(?:ff5f57|ff5f56|ff6058|febc2e|ffbd2e|28c840|27c93f)",
    re.I,
)
_CUSTOM_WIN_CTRL = re.compile(
    r"(?:getCurrentWindow\s*\(\s*\)|\bappWindow\b)\s*"
    r"\.\s*(?:close|minimize|toggleMaximize|maximize|unmaximize)\s*\(",
)
_FOREIGN_TITLEBAR = re.compile(
    r"("
    r"(?:target_os\s*=\s*[\"'](?:windows|linux)[\"']"
    r"|cfg!\s*\(\s*windows\s*\)"
    r"|#\[cfg\s*\(\s*windows\s*\))"
    r"[\s\S]{0,400}"
    r"(?:title_?bar|TitleBarStyle|decorations\s*\(|\bgtk\b)"
    r"|(?:title_?bar|TitleBarStyle|decorations\s*\(|\bgtk\b)"
    r"[\s\S]{0,400}"
    r"(?:target_os\s*=\s*[\"'](?:windows|linux)[\"']"
    r"|cfg!\s*\(\s*windows\s*\)"
    r"|#\[cfg\s*\(\s*windows\s*\))"
    r"|\bgtk\b[\s\S]{0,80}(?:titlebar|decorations|HeaderBar)"
    r"|HeaderBar[\s\S]{0,80}gtk"
    r")"
    r"|(?:win32|linux|gtk).{0,100}(?:titleBarStyle|titlebar|decorations)",
    re.I,
)
_DOCS_OVERLAY_BAR = re.compile(
    r"("
    r"overlay(?: / custom)? title\s*bar"
    r"|custom title\s*bar"
    r"|title\s*bar.{0,60}overlay"
    r"|overlay.{0,60}title\s*bar"
    r")",
    re.I | re.S,
)
_DOCS_DRAG_BAR = re.compile(
    r"("
    r"drag.{0,48}(?:the )?(?:top|title)\s*bar"
    r"|(?:top|title)\s*bar.{0,48}drag"
    r")",
    re.I | re.S,
)
_DOCS_NATIVE_LIGHTS = re.compile(
    r"("
    r"(?:native )?(?:close|minimize|zoom|traffic.?lights?)"
    r".{0,80}(?:stay|remain|still|native)"
    r"|(?:native )?(?:close(?:/|,| and )minimize(?:/|,| and )zoom)"
    r"|traffic.?lights?.{0,40}(?:stay|remain|native|clickable)"
    r")",
    re.I | re.S,
)
_DOCS_NO_WORDMARK = re.compile(
    r"("
    r"no second.{0,48}Interlace"
    r"|not a second.{0,48}Interlace"
    r"|without (?:a )?second.{0,48}Interlace"
    r"|no (?:duplicate|in-app|second).{0,24}(?:Interlace )?wordmark"
    r"|no second Interlace wordmark"
    r")",
    re.I | re.S,
)
_INTERACTIVE_TAG = re.compile(
    r"^(?:button|input|select|textarea|a|form|label|Button|Input)$"
)
_TITLEBAR_NAME = re.compile(r"title[-_]?bar|data-titlebar|data-title-bar", re.I)
_PANE_HOOK = re.compile(
    r"<main\b|person-timeline|SearchPane|ReviewPane|DoctorPane|ImportPane",
    re.I,
)


def _main_window_conf(cfg: dict) -> dict:
    windows = (cfg.get("app") or {}).get("windows") or []
    if not isinstance(windows, list):
        return {}
    for w in windows:
        if isinstance(w, dict) and w.get("label") == "main":
            return w
    for w in windows:
        if isinstance(w, dict):
            return w
    return {}


def _looks_like_whole_window(tag: str, inner: str) -> bool:
    name = _tag_name(tag).lower()
    if name in {"html", "body"}:
        return True
    if re.search(r"""\bid\s*=\s*["']app["']""", tag):
        return True
    wraps_chrome = bool(re.search(r"<header\b|<nav\b", inner, re.I))
    wraps_panes = bool(_PANE_HOOK.search(inner))
    if wraps_chrome and wraps_panes:
        return True
    if re.search(r"\bh-full\b", tag) and wraps_panes:
        return True
    return False


def _drag_is_interactive(tag: str) -> bool:
    if _INTERACTIVE_TAG.match(_tag_name(tag)):
        return True
    if re.search(r"\bdata-chrome-search\b", tag):
        return True
    if re.search(r"\bonclick\s*=", tag, re.I) and _tag_name(tag) in {
        "Button",
        "button",
        "a",
    }:
        return True
    return False


def _drag_is_top_chrome(tag: str, inner: str) -> bool:
    if _tag_name(tag).lower() == "header":
        return True
    if _TITLEBAR_NAME.search(tag):
        return True
    if _PANE_HOOK.search(inner):
        return False
    if _looks_like_whole_window(tag, inner):
        return False
    return True


def _drag_gated_to_archive(markup: str, pos: int) -> bool:
    for kind, cond, _extra in _template_stack(markup, pos):
        if kind not in {"if", "if-else"}:
            continue
        if re.search(r"view\s*===?", cond):
            return True
        if re.search(r"!\s*setup", cond) or (
            re.search(r"\bst\b", cond) and not re.search(r"!\s*st\b", cond)
        ):
            return True
    return False


def _header_chrome_chunks(markup: str) -> list[str]:
    chunks = list(_tag_inner(markup, "header"))
    for m in re.finditer(
        r"<([A-Za-z][\w-]*)\b[^>]*(?:titlebar|title-bar|title_bar|data-titlebar)[^>]*>",
        markup,
        re.I,
    ):
        chunks.append(markup[m.start() : m.start() + 2400])
    return chunks


def _custom_traffic_lights(blob: str) -> bool:
    if _claim_without_negation(blob, _TRAFFIC_NAME):
        return True
    if _TRAFFIC_HEX.search(blob):
        return True
    if _CUSTOM_WIN_CTRL.search(blob):
        return True
    colors = 0
    if re.search(r"rounded-full[\s\S]{0,80}(?:bg-red-|bg-\[#ff)", blob, re.I):
        colors += 1
    if re.search(r"rounded-full[\s\S]{0,80}(?:bg-yellow-|bg-\[#fe)", blob, re.I):
        colors += 1
    if re.search(r"rounded-full[\s\S]{0,80}(?:bg-green-|bg-\[#28)", blob, re.I):
        colors += 1
    return colors >= 2

__all__ = [
    "_TITLE_SEP",
    "_SET_TITLE_CALL",
    "_WINDOW_API_IMPORT",
    "_GET_CURRENT_WINDOW",
    "_DOCK_BADGE_API",
    "_TITLE_BODY_LEAK",
    "_TITLE_HELPER_NAMES",
    "_title_path_sources",
    "_collect_set_title_args",
    "_title_helper_bodies",
    "_DRAG_REGION",
    "_WORDMARK_BRAND",
    "_WORDMARK_TEXT",
    "_TRAFFIC_NAME",
    "_TRAFFIC_HEX",
    "_CUSTOM_WIN_CTRL",
    "_FOREIGN_TITLEBAR",
    "_DOCS_OVERLAY_BAR",
    "_DOCS_DRAG_BAR",
    "_DOCS_NATIVE_LIGHTS",
    "_DOCS_NO_WORDMARK",
    "_INTERACTIVE_TAG",
    "_TITLEBAR_NAME",
    "_PANE_HOOK",
    "_main_window_conf",
    "_looks_like_whole_window",
    "_drag_is_interactive",
    "_drag_is_top_chrome",
    "_drag_gated_to_archive",
    "_header_chrome_chunks",
    "_custom_traffic_lights",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_call_arg",
    "_function_body",
    "_matched_inner",
    "_opening_tag",
    "_search_pane_blob",
    "_strip_html_comments",
    "_svelte_markup",
    "_tauri_rust_blob",
    "_web_logic",
    "_web_sources",
    "_without_comments",
    "CSP",
    "_FILE_SUBMENU",
    "_TAURI_MENU_API",
    "_VIEW_SUBMENU",
    "annotations",
    "_tag_name",
    "_template_stack",
    "_claim_without_negation",
    "_tag_inner",
]
