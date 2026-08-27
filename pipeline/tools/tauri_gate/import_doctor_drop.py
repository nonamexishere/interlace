"""Helpers extracted from import_doctor.py (import_doctor_drop)."""
from __future__ import annotations

from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _ancestor_tags,
    _APPEARANCE_FETCH,
    _APPEARANCE_MENU_LABEL,
    _APPEARANCE_SCRIM_NAMES,
    _call_arg,
    _contrast_dark_blob,
    _css_var,
    _FETCH_CALL,
    _function_body,
    _match_closer,
    _product_svelte,
    _rust_fn_body,
    _search_pane_blob,
    _STATUS_CONFETTI,
    _STATUS_GRADIENT,
    _STATUS_WARNING_NAMES,
    _tauri_rust_blob,
    _tauri_rust_sources,
    _ts_fn_body,
    _web_logic,
    _web_ts_sources,
    _without_comments,
    CSP,
)

from tauri_gate.contrast_lib import _STATUS_CELEBRATION

from tauri_gate.import_boot_guards import _contrast_light_blob

from tauri_gate.status_toasts_chrome import (
    _APPEARANCE_THEME_UI,
    _contrast_surface_tag,
    _hue_surface,
    _status_hook_blob,
    _windows_around,
)




# #134 — drag-drop local ZIP/mbox onto the window → existing importStart + progress.
_TAURI_DRAG_DROP_API = re.compile(
    r"("
    r"\.onDragDropEvent\s*\("
    r"|\bon_drag_drop_event\s*\("
    r"|tauri://drag-drop"
    r"|tauri://file-drop"
    r")",
)
_TAURI_DRAG_DROP_TYPE = re.compile(r"\bDragDropEvent\b")
_TAURI_DRAG_DROP_PLUGIN = re.compile(
    r"("
    r"@tauri-apps/plugin-fs"
    r"|tauri-plugin-fs"
    r"|plugin-file-drop"
    r"|tauri-plugin-drag"
    r")",
)
_HTML_DROP_ATTR = re.compile(
    r"("
    r"\bon:?drop\b"
    r"|\bondrop\b"
    r"|\bon:?dragover\b"
    r"|\bondragover\b"
    r"|\bon:?dragenter\b"
    r")",
    re.I,
)
_DROP_EVENT_TYPE = re.compile(
    r"("
    r"(?:payload\.)?type\s*===?\s*[\"']drop[\"']"
    r"|[\"']drop[\"']\s*===?\s*(?:[\w$.]+\.)?type"
    r"|DragDropEvent::Drop"
    r"|DragDrop::Drop"
    r"|WindowEvent::DragDrop"
    r")",
)
_DROP_PATHS = re.compile(
    r"("
    r"(?:payload\.)?paths\b"
    r"|\.paths\s*\["
    r")"
)
_IMPORT_START_CALL = re.compile(r"\b(?:api\.)?importStart\s*\(")
_IMPORT_START_KIND_AUTO = re.compile(
    r"("
    r"kind\s*:\s*null"
    r"|kind\s*:\s*(?:undefined|kind\s*===?\s*[\"']auto[\"']\s*\?\s*null)"
    r")"
)
_VIEW_IMPORT_ASSIGN = re.compile(r"\bview\s*=\s*[\"']import[\"']")
_URL_SCHEME_REJECT = re.compile(
    r"("
    r"https?://"
    r"|/?\\^https\\?:"
    r"|\\bhttps?:"
    r"|startsWith\s*\(\s*[\"']https?"
    r"|includes\s*\(\s*[\"']https?"
    r"|protocol\s*===?\s*[\"']https?:"
    r"|[\"']https?://"
    r"|isRemote(?:Url|Path)?"
    r"|isHttps?"
    r"|isUrl\b"
    r"|looksLikeUrl"
    r"|hasUrlScheme"
    r"|urlScheme"
    r"|reject(?:Http|Url|Remote)"
    r")",
    re.I,
)
_HTTPS_TOKEN = re.compile(r"https://|[\"']https://|https\\?:|[\"']https[\"']", re.I)
_HTTP_TOKEN = re.compile(r"http://|[\"']http://|[\"']http[\"']|https\\?:", re.I)
_SHOW_ERR = re.compile(
    r"("
    r"\bonError\s*\("
    r"|\bshowErr\s*\("
    r"|\berr\s*="
    r"|progress\.error"
    r")",
)
_XHR = re.compile(r"\bXMLHttpRequest\b|\baxios\s*\.")
_DATATRANSFER = re.compile(r"\bdataTransfer\b")
_DROP_WALK = re.compile(
    r"("
    r"\bwalkDir\b"
    r"|\bwalkSync\b"
    r"|\bfs\.walk\b"
    r"|\breadDir\s*\("
    r"|\bread_dir\s*\("
    r"|\breaddir\s*\("
    r"|recursive\s*:\s*true"
    r"|@tauri-apps/plugin-fs"
    r"|\bfolderOfFolders\b"
    r"|\bwalkImport\b"
    r"|\bimportWalk\b"
    r"|\brglob\s*\("
    r")",
)
_HTTP_CAP = re.compile(
    r"("
    r"http:default"
    r"|http:allow-fetch"
    r"|http:allow-request"
    r"|tauri-plugin-http"
    r"|allow-http"
    r")",
    re.I,
)
_IMPORT_PANE_PATH_PROP = re.compile(
    r"<ImportPane\b[^>]{0,500}(?:"
    r"bind:path"
    r"|droppedPath|dropPath|startPath|importPath|queuedPath|pendingPath"
    r"|autoStart|dropQueued"
    r")",
    re.I | re.S,
)
_DROP_CALL_SKIP = frozenset(
    {
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "function",
        "return",
        "typeof",
        "new",
        "await",
        "void",
        "Promise",
        "Math",
        "Number",
        "String",
        "Boolean",
        "parseInt",
        "document",
        "getElementById",
        "querySelector",
        "querySelectorAll",
        "Error",
        "setTimeout",
        "setInterval",
        "clearInterval",
        "requestAnimationFrame",
        "getCurrentWebview",
        "getCurrentWindow",
        "onDragDropEvent",
        "listen",
        "console",
        "JSON",
        "Array",
        "Object",
        "RegExp",
        "Date",
        "Map",
        "Set",
        "unlisten",
        "onMount",
        "tick",
    }
)


def _import_pane_conditionally_mounted(app: str) -> bool:
    """True when every ImportPane mounts only under view === \"import\"."""
    seen = False
    only_conditional = True
    for m in re.finditer(r"<ImportPane\b", app):
        seen = True
        window = app[max(0, m.start() - 400) : m.start()]
        if not re.search(r"view\s*===?\s*[\"']import[\"']", window):
            only_conditional = False
    return seen and only_conditional


def _drop_api_files(crate: Path) -> list[Path]:
    found: list[Path] = []
    for p in _web_ts_sources(crate) + _tauri_rust_sources(crate):
        text = p.read_text()
        if _TAURI_DRAG_DROP_API.search(text) or (
            _TAURI_DRAG_DROP_TYPE.search(text) and re.search(r"\.paths\b", text)
        ):
            found.append(p)
    return found


def _extract_call_callback(src: str, call_rx: re.Pattern[str]) -> list[str]:
    bodies: list[str] = []
    for m in call_rx.finditer(src):
        open_paren = src.find("(", m.start())
        if open_paren < 0:
            continue
        arg = _call_arg(src, open_paren)
        if not arg:
            continue
        bodies.append(arg)
        named = re.match(r"\s*([A-Za-z_][\w]*)\s*$", arg.strip())
        if named and named.group(1) not in _DROP_CALL_SKIP:
            inner = _ts_fn_body(src, named.group(1)) or _function_body(src, named.group(1))
            if inner:
                bodies.append(inner)
    return bodies


def _expand_drop_calls(src: str, body: str, depth: int = 3) -> str:
    chunks = [body]
    seen: set[str] = set()

    def walk(blob: str, left: int) -> None:
        for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob):
            if name in seen or name in _DROP_CALL_SKIP:
                continue
            seen.add(name)
            inner = _ts_fn_body(src, name) or _function_body(src, name)
            if not inner:
                continue
            chunks.append(inner)
            if left > 0:
                walk(inner, left - 1)

    walk(body, depth)
    return "\n".join(chunks)


def _drop_handler_surface(crate: Path) -> str:
    """Bodies that run on Tauri drag-drop (and named callees)."""
    chunks: list[str] = []
    sources: list[str] = []
    for p in _web_ts_sources(crate) + _tauri_rust_sources(crate):
        text = p.read_text()
        cleaned = _without_comments(text)
        sources.append(text)
        sources.append(cleaned)
        chunks.extend(_extract_call_callback(cleaned, re.compile(r"\.onDragDropEvent\s*\(")))
        chunks.extend(_extract_call_callback(text, re.compile(r"\.onDragDropEvent\s*\(")))
        chunks.extend(_extract_call_callback(cleaned, re.compile(r"\bon_drag_drop_event\s*\(")))
        chunks.extend(_extract_call_callback(text, re.compile(r"\bon_drag_drop_event\s*\(")))
        for src in (cleaned, text):
            for m in re.finditer(
                r"listen\s*(?:<[^>]*>)?\s*\(\s*[\"']tauri://(?:drag-drop|file-drop)[\"']",
                src,
            ):
                open_paren = src.find("(", m.start())
                arg = _call_arg(src, open_paren) if open_paren >= 0 else ""
                if arg:
                    chunks.append(arg)
    joined = "\n".join(chunks)
    if not joined.strip():
        return ""
    whole = "\n".join(sources)
    return _expand_drop_calls(whole, joined)


def _drop_rejects_url_scheme(surface: str) -> bool:
    """True if http and https (or a generic URL-scheme helper) are rejected."""
    if not _URL_SCHEME_REJECT.search(surface):
        return False
    has_http = bool(_HTTP_TOKEN.search(surface))
    has_https = bool(_HTTPS_TOKEN.search(surface))
    generic = bool(
        re.search(
            r"("
            r"urlScheme"
            r"|hasUrlScheme"
            r"|looksLikeUrl"
            r"|isUrl\b"
            r"|isRemote"
            r"|reject(?:Http|Url|Remote)"
            r"|/?\\^[a-zA-Z][a-zA-Z0-9+.\-]*:"
            r")",
            surface,
        )
    )
    return (has_http and has_https) or generic

from tauri_gate.import_doctor_drop_rest import (
    _drop_starts_import,
    _IMPORT_HONEST_COPY,
    _IMPORT_FAKE_CMD,
    _IMPORT_THREAD_KILL,
    _IMPORT_STATUS_RUNNING,
    _IMPORT_CONSOLE_PATH,
    _IMPORT_TOAST_PATH,
    _IMPORT_PARALLEL,
    _IMPORT_GC_BTN,
    _IMPORT_DOCS_PROGRESS,
    _IMPORT_DOCS_NO_STOP,
    _IMPORT_DOCS_QUIET,
    _IMPORT_DISABLED,
    _IMPORT_DIALOG,
    _IMPORT_DESCRIBEDBY,
    _import_describedby_blob,
    _import_honest_blob,
    _IMPORT_CANCEL_CMD,
    _IMPORT_CANCEL_UNCOND_DISABLED,
    _IMPORT_CANCEL_CLICK,
    _IMPORT_CANCEL_API_CALL,
    __all__,
)

__all__ = [
    "_TAURI_DRAG_DROP_API",
    "_TAURI_DRAG_DROP_TYPE",
    "_TAURI_DRAG_DROP_PLUGIN",
    "_HTML_DROP_ATTR",
    "_DROP_EVENT_TYPE",
    "_DROP_PATHS",
    "_IMPORT_START_CALL",
    "_IMPORT_START_KIND_AUTO",
    "_VIEW_IMPORT_ASSIGN",
    "_URL_SCHEME_REJECT",
    "_HTTPS_TOKEN",
    "_HTTP_TOKEN",
    "_SHOW_ERR",
    "_XHR",
    "_DATATRANSFER",
    "_DROP_WALK",
    "_HTTP_CAP",
    "_IMPORT_PANE_PATH_PROP",
    "_DROP_CALL_SKIP",
    "_import_pane_conditionally_mounted",
    "_drop_api_files",
    "_extract_call_callback",
    "_expand_drop_calls",
    "_drop_handler_surface",
    "_drop_rejects_url_scheme",
    "_drop_starts_import",
    "_IMPORT_HONEST_COPY",
    "_IMPORT_FAKE_CMD",
    "_IMPORT_THREAD_KILL",
    "_IMPORT_STATUS_RUNNING",
    "_IMPORT_CONSOLE_PATH",
    "_IMPORT_TOAST_PATH",
    "_IMPORT_PARALLEL",
    "_IMPORT_GC_BTN",
    "_IMPORT_DOCS_PROGRESS",
    "_IMPORT_DOCS_NO_STOP",
    "_IMPORT_DOCS_QUIET",
    "_IMPORT_DISABLED",
    "_IMPORT_DIALOG",
    "_IMPORT_DESCRIBEDBY",
    "_import_describedby_blob",
    "_import_honest_blob",
    "_IMPORT_CANCEL_CMD",
    "_IMPORT_CANCEL_UNCOND_DISABLED",
    "_IMPORT_CANCEL_CLICK",
    "_IMPORT_CANCEL_API_CALL",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_ancestor_tags",
    "_APPEARANCE_FETCH",
    "_APPEARANCE_MENU_LABEL",
    "_APPEARANCE_SCRIM_NAMES",
    "_call_arg",
    "_contrast_dark_blob",
    "_css_var",
    "_FETCH_CALL",
    "_function_body",
    "_match_closer",
    "_product_svelte",
    "_rust_fn_body",
    "_search_pane_blob",
    "_STATUS_CONFETTI",
    "_STATUS_GRADIENT",
    "_STATUS_WARNING_NAMES",
    "_tauri_rust_blob",
    "_tauri_rust_sources",
    "_ts_fn_body",
    "_web_logic",
    "_web_ts_sources",
    "_without_comments",
    "CSP",
    "_STATUS_CELEBRATION",
    "_contrast_light_blob",
    "_APPEARANCE_THEME_UI",
    "_contrast_surface_tag",
    "_hue_surface",
    "_status_hook_blob",
    "_windows_around",
]
