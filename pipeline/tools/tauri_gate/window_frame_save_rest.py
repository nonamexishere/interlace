"""Continuation of window_frame_save."""
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
from tauri_gate.window_frame_save import (
    _SET_SIZE,
    _SET_POSITION,
    _SIZE_READ,
    _POS_READ,
    _AVAILABLE,
    _WORK_AREA,
    _WINDOW_EVENT,
    _EVENT_SAVE,
    _CLAMP_WORD,
    _XY_SHIFT,
    _READ_STORE,
    _PARSE_STORE,
    _JUNK_BRANCH,
    _OTHER_DEFAULT,
    _FRAME_LS,
    _KEEP_LS,
    _IS_MAXIMIZED,
    _IS_FULLSCREEN,
    _FRAME_WRITE,
    _ON_WINDOW_EVENT_CALL,
    _EVENT_VARIANT,
    _ON_WINDOW_EVENT_NAME,
    _HANDLER_NAME,
    _HANDLER_SKIP,
)


def _has_xywh_save(surface: str) -> bool:
    return bool(
        _SIZE_READ.search(surface)
        and _POS_READ.search(surface)
        and (_WINDOW_EVENT.search(surface) or _EVENT_SAVE.search(surface))
    )


def _has_xywh_restore(surface: str) -> bool:
    return bool(_SET_SIZE.search(surface) and _SET_POSITION.search(surface))


def _has_junk_branch(restore: str) -> bool:
    if not restore.strip():
        return False
    if not (_READ_STORE.search(restore) or _PARSE_STORE.search(restore)):
        return False
    return bool(_JUNK_BRANCH.search(restore)) and not _OTHER_DEFAULT.search(restore)


def _has_translate_clamp(surface: str) -> bool:
    return bool(
        _AVAILABLE.search(surface)
        and _WORK_AREA.search(surface)
        and _SET_POSITION.search(surface)
        and (_CLAMP_WORD.search(surface) or _XY_SHIFT.search(surface))
    )


def _frame_ls_keys(keys: list[str]) -> list[str]:
    return [k for k in keys if _FRAME_LS.search(k) and not _KEEP_LS.search(k)]


def _fn_body_named(rust: str, name: str) -> str:
    """Like _rust_fn_body, but also accepts `fn name<R: Trait>(...)`."""
    body = _rust_fn_body(rust, name)
    if body.strip():
        return body
    m = re.search(rf"(?:pub\s+)?(?:async\s+)?fn\s+{re.escape(name)}\b", rust)
    if not m:
        return ""
    i = m.end()
    n = len(rust)
    while i < n and rust[i].isspace():
        i += 1
    if i < n and rust[i] == "<":
        depth = 0
        while i < n:
            if rust[i] == "<":
                depth += 1
            elif rust[i] == ">":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
    paren = rust.find("(", i)
    if paren < 0:
        return ""
    close_paren = paren
    depth = 0
    j = paren
    while j < n:
        if rust[j] == "(":
            depth += 1
        elif rust[j] == ")":
            depth -= 1
            if depth == 0:
                close_paren = j
                break
        j += 1
    else:
        return ""
    brace = rust.find("{", close_paren)
    if brace < 0:
        return ""
    depth = 0
    k = brace
    while k < n:
        if rust[k] == "{":
            depth += 1
        elif rust[k] == "}":
            depth -= 1
            if depth == 0:
                return rust[brace + 1 : k]
        k += 1
    return rust[brace + 1 :]


def _save_fn_body(rust: str) -> str:
    body = _fn_body_named(rust, "save_window_frame")
    if body.strip():
        return body
    for name in ("persist_window_frame", "write_window_frame"):
        body = _fn_body_named(rust, name)
        if body.strip() and (_SIZE_READ.search(body) or _POS_READ.search(body)):
            return body
    return ""


def _save_skips_zoomed(body: str) -> bool:
    """True when both zoomed reads sit before a return that skips the write."""
    if not body.strip():
        return False
    if not _IS_MAXIMIZED.search(body) or not _IS_FULLSCREEN.search(body):
        return False
    last_read = max(
        list(_IS_MAXIMIZED.finditer(body))[-1].end(),
        list(_IS_FULLSCREEN.finditer(body))[-1].end(),
    )
    writes = [m.start() for m in _FRAME_WRITE.finditer(body)]
    if not writes:
        return False
    first_write = min(w for w in writes if w >= last_read) if any(
        w >= last_read for w in writes
    ) else min(writes)
    # is_maximized / is_fullscreen must precede the persist write.
    if last_read > first_write:
        return False
    return any(
        last_read <= m.start() < first_write
        for m in re.finditer(r"\breturn\b", body)
    )


def _on_window_event_blob(rust: str) -> str:
    parts: list[str] = []
    for m in _ON_WINDOW_EVENT_CALL.finditer(rust):
        arg = _call_arg(rust, m.end() - 1)
        if arg.strip():
            parts.append(arg)
            for name in _HANDLER_NAME.findall(arg):
                if name in _HANDLER_SKIP or _ON_WINDOW_EVENT_NAME.fullmatch(name):
                    continue
                body = _fn_body_named(rust, name)
                if body.strip():
                    parts.append(body)
    named = _fn_body_named(rust, "on_window_event")
    if named.strip():
        parts.append(named)
    return "\n".join(parts)


def _pattern_before_arrow(blob: str, arrow: int) -> str:
    """Match-arm pattern left of `=>`, ignoring `{ .. }` struct rest patterns."""
    i = arrow - 1
    depth_brace = 0
    depth_paren = 0
    while i >= 0:
        c = blob[i]
        if c == "}":
            depth_brace += 1
        elif c == "{":
            if depth_brace == 0 and depth_paren == 0:
                return blob[i + 1 : arrow]
            depth_brace -= 1
        elif c == ")":
            depth_paren += 1
        elif c == "(":
            if depth_paren == 0 and depth_brace == 0:
                return blob[i + 1 : arrow]
            depth_paren -= 1
        i -= 1
    return blob[:arrow]


def _arm_patterns_that_save(blob: str) -> list[str]:
    pats: list[str] = []
    for m in _FRAME_WRITE.finditer(blob):
        before = blob[: m.start()]
        arrow = before.rfind("=>")
        if arrow >= 0:
            pats.append(_pattern_before_arrow(blob, arrow))
            continue
        pats.append(before[-500:])
    return pats


def _save_event_names(blob: str) -> set[str]:
    names: set[str] = set()
    for pat in _arm_patterns_that_save(blob):
        names.update(m.group(1) for m in _EVENT_VARIANT.finditer(pat))
    return names

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
    "json",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_ls_pref_keys",
    "CSP",
    "_CONFIG_TOML",
    "_LAST_PATH_API",
    "_rust_fn_body",
    "_tauri_rust_blob",
    "_web_logic",
    "_without_comments",
    "_toml_keys_in_fn",
    "annotations",
    "_call_arg",
    "_windows_around",
]

__all__ = [
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
    "__all__",
]
