"""Helpers extracted from window_frame.py (window_frame_save)."""
from __future__ import annotations

from __future__ import annotations

from __future__ import annotations

import json
import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.import_boot_guards import _ls_pref_keys
from tauri_gate.scan import (
    CSP,
    _CONFIG_TOML,
    _LAST_PATH_API,
    _call_arg,
    _rust_fn_body,
    _tauri_rust_blob,
    _web_logic,
    _without_comments,
)
from tauri_gate.status_toasts_chrome import (
    _toml_keys_in_fn,
    _windows_around,
)

_SET_SIZE = re.compile(r"\bset_size\s*\(")
_SET_POSITION = re.compile(r"\bset_position\s*\(")
_SIZE_READ = re.compile(r"\b(?:inner_size|outer_size)\s*\(")
_POS_READ = re.compile(r"\b(?:outer_position|inner_position)\s*\(")
_AVAILABLE = re.compile(r"\bavailable_monitors\s*\(")
_WORK_AREA = re.compile(r"\bwork_area\s*\(")
_WINDOW_EVENT = re.compile(r"\b(?:on_window_event|WindowEvent)\b")
_EVENT_SAVE = re.compile(
    r"\bWindowEvent\s*::\s*(?:Moved|Resized|CloseRequested|Destroyed)\b"
)
_MAIN_GET = re.compile(
    r"\bget_(?:webview_)?window\s*\(\s*[\"']main[\"']|[\"']main[\"']"
)
_SETUP = re.compile(r"\.setup\s*\(")
_PLUGIN = re.compile(r"tauri[-_]plugin[-_]window[-_]state")
_CONFIG_DIR = re.compile(
    r"\bconfig_dir\s*\(|\bINTERLACE_CONFIG_DIR\b|Application Support/Interlace"
)
_BOOKMARK = re.compile(
    r"last-archive\.bookmark|\bLAST_BOOKMARK_FILE\b"
    r"|\b(?:write_last_bookmark|read_last_bookmark)\b"
)
_STORE_MAX = re.compile(
    r"[\"'](?:maximized|fullscreen|zoomed)[\"']"
    r"|\b(?:maximized|fullscreen|zoomed)\s*:"
)
_APPLY_MAX = re.compile(r"\b(?:set_maximized|set_fullscreen)\s*\(")
_PLUGIN_MAX = re.compile(
    r"StateFlags\s*::\s*(?:all\s*\(|FULLSCREEN|MAXIMIZED|VISIBLE)"
)
_AUTOSAVE = re.compile(r"setFrameAutosaveName|objc2-app-kit|objc2_app_kit")
_CLAMP_WORD = re.compile(
    r"\bclamp(?:_frame|_rect|_to)?\b|\bintersect(?:ion|s)?\b"
    r"|\boverlap(?:s|ping)?\b|\btranslate\b",
    re.I,
)
_XY_SHIFT = re.compile(
    r"(?<![\w.])[xy]\s*=|\.[xy]\s*[+\-]|\b(?:max|min)\s*\("
)
_READ_STORE = re.compile(
    r"\b(?:read_to_string|fs\s*::\s*read\b|File\s*::\s*open)\b"
)
_PARSE_STORE = re.compile(
    r"\b(?:serde_json|toml)\s*::\s*from_|\bfrom_(?:str|slice|value)\s*\("
)
_JUNK_BRANCH = re.compile(
    r"if\s+let\s+(?:Ok|Some|Err)\b|\.ok\s*[\(?]|unwrap_or(?:_else|_default)?"
    r"|exists\s*\(|is_file\s*\(|is_err\s*\(|is_none\s*\("
    r"|None\s*=>|Err\s*\(|NotFound"
)
_OTHER_DEFAULT = re.compile(
    r"(?:unwrap_or(?:_else|_default)?|else)\s*[^;]{0,120}"
    r"(?:1024|1280|1440|1920|800|1200)"
)
_WEB_SET_FRAME = re.compile(r"\b(?:setSize|setPosition|setFullscreen)\s*\(")
_FRAME_LS = re.compile(r"window|frame|xywh|position|outer.?size|inner.?size", re.I)
_KEEP_LS = re.compile(r"lastview|lastperson|sidebar|collapsed|density", re.I)
_FRAME_FN_NAME = re.compile(
    r"\b(?:save|persist|write|restore|load|read|clamp|apply)_?"
    r"(?:window_)?frame\w*\b|\bwindow_frame\w*\b",
    re.I,
)
_FN_DEF = re.compile(r"(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_][\w]*)\s*\(")
_DOCS_SIZE_POS = re.compile(
    r"last window size and position|window size and position"
    r"|last window (?:size|frame|position)"
    r"|(?:size and position).{0,40}window",
    re.I | re.S,
)
_DOCS_REOPEN_FRAME = re.compile(
    r"reopen.{0,80}(?:last window|window size|size and position|window position)"
    r"|(?:last window|window size|size and position).{0,80}reopen"
    r"|restores?.{0,48}(?:last window|window size|size and position)",
    re.I | re.S,
)
_DOCS_CLAMP = re.compile(
    r"off[- ]screen.{0,80}clamp|clamp.{0,80}off[- ]screen"
    r"|unplugg.{0,80}(?:visible|clamp|work area)",
    re.I | re.S,
)
_WEBVIEW_ACL = re.compile(r"core:window:allow-set-(?:size|position)\b")
_HTTP_PLUGIN = re.compile(r"tauri-plugin-(?:http|updater)\b")
_FRAME_TOKS = (
    _SET_SIZE, _SET_POSITION, _SIZE_READ, _POS_READ,
    _AVAILABLE, _WORK_AREA, _WINDOW_EVENT, _SETUP, _FRAME_FN_NAME,
)
# #306 fold — skip zoomed save (check 10).
# #306-rerun — live Moved/Resized save, debounce, atomic write (11–13).
_IS_MAXIMIZED = re.compile(r"\bis_maximized\s*\(")
_IS_FULLSCREEN = re.compile(r"\bis_fullscreen\s*\(")
_FRAME_WRITE = re.compile(
    r"\b(?:write_window_frame|save_window_frame|persist_window_frame)\s*\("
    r"|\bfs\s*::\s*write\s*\("
)
_ON_WINDOW_EVENT_CALL = re.compile(r"\.on_window_event\s*\(")
_EVENT_VARIANT = re.compile(
    r"\bWindowEvent\s*::\s*(Moved|Resized|CloseRequested|Destroyed)\b"
)
_LIVE_EVENTS = frozenset({"Moved", "Resized"})
_QUIT_EVENTS = frozenset({"CloseRequested", "Destroyed"})
_ON_WINDOW_EVENT_NAME = re.compile(r"\bon_window_event\b")
_HANDLER_NAME = re.compile(r"\b([A-Za-z_][\w]*)\b")
_HANDLER_SKIP = frozenset(
    {
        "window",
        "event",
        "match",
        "move",
        "if",
        "let",
        "ref",
        "mut",
        "self",
        "Some",
        "None",
        "Ok",
        "Err",
        "true",
        "false",
        "tauri",
        "WindowEvent",
        "Moved",
        "Resized",
        "CloseRequested",
        "Destroyed",
        "save_window_frame",
        "persist_window_frame",
        "write_window_frame",
        "window_frame",
    }
)
_DEBOUNCE_TOK = re.compile(r"\btimeout|\bsleep\b|\bInstant\b|\bdebounce(?:d|r)?\b")
_LIVE_HELPER_NAME = re.compile(
    r"debounce"
    r"|(?:schedule|defer|delay|queue|pending).{0,24}(?:save|write|persist|frame)"
    r"|(?:save|write|persist|frame).{0,24}(?:debounce|later|delayed|scheduled)",
    re.I,
)
_CALL_NAME = re.compile(r"\b(?:[A-Za-z_][\w]*\s*::\s*)*([A-Za-z_][\w]*)\s*\(")
_CALL_SKIP = frozenset(
    {
        "window",
        "event",
        "match",
        "move",
        "if",
        "let",
        "ref",
        "mut",
        "self",
        "Some",
        "None",
        "Ok",
        "Err",
        "true",
        "false",
        "tauri",
        "WindowEvent",
        "Moved",
        "Resized",
        "CloseRequested",
        "Destroyed",
        "for",
        "while",
        "loop",
        "return",
        "break",
        "continue",
        "unsafe",
        "async",
        "clone",
        "ok",
        "as_ref",
        "as_mut",
        "to_string",
        "to_owned",
        "into",
        "from",
        "new",
        "lock",
        "unwrap",
        "unwrap_or",
        "unwrap_or_else",
        "unwrap_or_default",
        "expect",
        "map",
        "and_then",
        "or_else",
        "drop",
        "format",
        "vec",
        "String",
        "thread",
        "std",
        "Duration",
        "from_millis",
        "from_secs",
        "elapsed",
        "spawn",
        "create_dir_all",
        "join",
        "is_err",
        "is_ok",
        "label",
        "is_maximized",
        "is_fullscreen",
        "inner_size",
        "outer_size",
        "inner_position",
        "outer_position",
    }
)
_FRAME_DEST = re.compile(r"window-frame\.json|\bFRAME_FILE\b|\bframe_path\s*\(")
_RENAME = re.compile(r"\brename\s*\(")
_TEMP_FILE = re.compile(
    r"\.tmp\b"
    r"|[\"'][^\"']*tmp[^\"']*[\"']"
    r"|\btmp_path\b|\btemp_path\b|\btmp_file\b"
    r"|\bNamedTempFile\b|\btempfile\b",
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


def _named_bodies(rust: str, pred) -> list[str]:
    bodies: list[str] = []
    seen: set[str] = set()
    for m in _FN_DEF.finditer(rust):
        name = m.group(1)
        if name in seen:
            continue
        body = _rust_fn_body(rust, name)
        if body.strip() and pred(name, body):
            seen.add(name)
            bodies.append(body)
    return bodies


def _around(rust: str, tokens: tuple[re.Pattern[str], ...]) -> list[str]:
    return [_windows_around(rust, rx, before=220, after=500) for rx in tokens]


def _frame_surface(rust: str) -> str:
    parts = _named_bodies(rust, lambda n, _b: bool(_FRAME_FN_NAME.search(n)))
    parts.extend(_around(rust, _FRAME_TOKS))
    parts.append(_rust_fn_body(rust, "main"))
    return "\n".join(parts)


def _restore_surface(rust: str) -> str:
    parts = _named_bodies(
        rust,
        lambda n, b: bool(
            _SET_SIZE.search(b) or _SET_POSITION.search(b) or re.search(r"restore", n, re.I)
        ),
    )
    parts.extend(_around(rust, (_SET_SIZE, _SET_POSITION, _SETUP)))
    return "\n".join(parts)


def _save_surface(rust: str) -> str:
    parts = _named_bodies(
        rust,
        lambda n, b: bool(_FRAME_FN_NAME.search(n))
        and bool(_SIZE_READ.search(b) or _POS_READ.search(b) or re.search(r"save|persist|write", n, re.I)),
    )
    parts.extend(_around(rust, (_SIZE_READ, _POS_READ, _WINDOW_EVENT)))
    return "\n".join(parts)

from tauri_gate.window_frame_save_rest import (
    _has_xywh_save,
    _has_xywh_restore,
    _has_junk_branch,
    _has_translate_clamp,
    _frame_ls_keys,
    _fn_body_named,
    _save_fn_body,
    _save_skips_zoomed,
    _on_window_event_blob,
    _pattern_before_arrow,
    _arm_patterns_that_save,
    _save_event_names,
    __all__,
)

__all__ = [
    "_SET_SIZE",
    "_SET_POSITION",
    "_SIZE_READ",
    "_POS_READ",
    "_AVAILABLE",
    "_WORK_AREA",
    "_WINDOW_EVENT",
    "_EVENT_SAVE",
    "_MAIN_GET",
    "_SETUP",
    "_PLUGIN",
    "_CONFIG_DIR",
    "_BOOKMARK",
    "_STORE_MAX",
    "_APPLY_MAX",
    "_PLUGIN_MAX",
    "_AUTOSAVE",
    "_CLAMP_WORD",
    "_XY_SHIFT",
    "_READ_STORE",
    "_PARSE_STORE",
    "_JUNK_BRANCH",
    "_OTHER_DEFAULT",
    "_WEB_SET_FRAME",
    "_FRAME_LS",
    "_KEEP_LS",
    "_FRAME_FN_NAME",
    "_FN_DEF",
    "_DOCS_SIZE_POS",
    "_DOCS_REOPEN_FRAME",
    "_DOCS_CLAMP",
    "_WEBVIEW_ACL",
    "_HTTP_PLUGIN",
    "_FRAME_TOKS",
    "_IS_MAXIMIZED",
    "_IS_FULLSCREEN",
    "_FRAME_WRITE",
    "_ON_WINDOW_EVENT_CALL",
    "_EVENT_VARIANT",
    "_LIVE_EVENTS",
    "_QUIT_EVENTS",
    "_ON_WINDOW_EVENT_NAME",
    "_HANDLER_NAME",
    "_HANDLER_SKIP",
    "_DEBOUNCE_TOK",
    "_LIVE_HELPER_NAME",
    "_CALL_NAME",
    "_CALL_SKIP",
    "_FRAME_DEST",
    "_RENAME",
    "_TEMP_FILE",
    "_main_window_conf",
    "_named_bodies",
    "_around",
    "_frame_surface",
    "_restore_surface",
    "_save_surface",
    "_has_xywh_save",
    "_has_xywh_restore",
    "_has_junk_branch",
    "_has_translate_clamp",
    "_frame_ls_keys",
    "_fn_body_named",
    "_save_fn_body",
    "_save_skips_zoomed",
    "_on_window_event_blob",
    "_pattern_before_arrow",
    "_arm_patterns_that_save",
    "_save_event_names",
    "annotations",
    "json",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_ls_pref_keys",
    "CSP",
    "_CONFIG_TOML",
    "_LAST_PATH_API",
    "_call_arg",
    "_rust_fn_body",
    "_tauri_rust_blob",
    "_web_logic",
    "_without_comments",
    "_toml_keys_in_fn",
    "_windows_around",
]
