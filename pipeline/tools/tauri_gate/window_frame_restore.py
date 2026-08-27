"""Helpers extracted from window_frame.py (window_frame_restore)."""
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
    _FRAME_WRITE,
    _EVENT_VARIANT,
    _LIVE_EVENTS,
    _DEBOUNCE_TOK,
    _LIVE_HELPER_NAME,
    _CALL_NAME,
    _CALL_SKIP,
    _FRAME_DEST,
    _RENAME,
    _TEMP_FILE,
    _fn_body_named,
)


def _preceded_by_arrow(blob: str, brace: int) -> bool:
    i = brace - 1
    while i >= 0 and blob[i].isspace():
        i -= 1
    return i >= 1 and blob[i - 1 : i + 1] == "=>"


def _this_arm_pattern(blob: str, arrow: int) -> str:
    """Match-arm pattern for this `=>` only (does not swallow prior arms)."""
    i = arrow - 1
    depth_brace = 0
    depth_paren = 0
    close_brace: int | None = None
    while i >= 0:
        c = blob[i]
        if c == "}":
            if depth_brace == 0 and depth_paren == 0:
                close_brace = i
            depth_brace += 1
        elif c == "{":
            if depth_brace == 0 and depth_paren == 0:
                return blob[i + 1 : arrow]
            depth_brace -= 1
            if (
                depth_brace == 0
                and depth_paren == 0
                and close_brace is not None
                and _preceded_by_arrow(blob, i)
            ):
                return blob[close_brace + 1 : arrow]
            if depth_brace == 0 and depth_paren == 0:
                close_brace = None
        elif c == ")":
            depth_paren += 1
        elif c == "(":
            if depth_paren == 0 and depth_brace == 0:
                return blob[i + 1 : arrow]
            depth_paren -= 1
        elif c == "," and depth_brace == 0 and depth_paren == 0:
            return blob[i + 1 : arrow]
        i -= 1
    return blob[:arrow]


def _arrow_arm_body(blob: str, arrow: int) -> str:
    i = arrow + 2
    n = len(blob)
    while i < n and blob[i].isspace():
        i += 1
    if i < n and blob[i] == "{":
        depth = 0
        j = i
        while j < n:
            if blob[j] == "{":
                depth += 1
            elif blob[j] == "}":
                depth -= 1
                if depth == 0:
                    return blob[i + 1 : j]
            j += 1
        return blob[i + 1 :]
    j = i
    depth_paren = 0
    depth_brace = 0
    while j < n:
        c = blob[j]
        if c == "(":
            depth_paren += 1
        elif c == ")":
            if depth_paren:
                depth_paren -= 1
        elif c == "{":
            depth_brace += 1
        elif c == "}":
            if depth_brace:
                depth_brace -= 1
            elif depth_paren == 0:
                return blob[i:j]
        elif c == "," and depth_paren == 0 and depth_brace == 0:
            return blob[i:j]
        j += 1
    return blob[i:]


def _event_arms(blob: str) -> list[tuple[set[str], str]]:
    arms: list[tuple[set[str], str]] = []
    for m in re.finditer(r"=>", blob):
        pat = _this_arm_pattern(blob, m.start())
        names = {g.group(1) for g in _EVENT_VARIANT.finditer(pat)}
        if not names:
            continue
        arms.append((names, _arrow_arm_body(blob, m.start())))
    return arms


def _called_names(body: str) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for m in _CALL_NAME.finditer(body):
        name = m.group(1)
        if name in _CALL_SKIP or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def _arm_saves_live(rust: str, body: str) -> bool:
    """True when a Moved/Resized arm writes or calls a named save/debounce helper."""
    if _FRAME_WRITE.search(body):
        return True
    for name in _called_names(body):
        if _LIVE_HELPER_NAME.search(name):
            return True
        fn = _fn_body_named(rust, name)
        if not fn.strip():
            continue
        if _FRAME_WRITE.search(fn):
            return True
        for inner in _called_names(fn):
            if _LIVE_HELPER_NAME.search(inner):
                return True
            ib = _fn_body_named(rust, inner)
            if ib and _FRAME_WRITE.search(ib):
                return True
    return False


def _live_events_that_save(rust: str, ev: str) -> set[str]:
    found: set[str] = set()
    for names, body in _event_arms(ev):
        live = names & _LIVE_EVENTS
        if live and _arm_saves_live(rust, body):
            found.update(live)
    return found


def _surface_debounced(surface: str) -> bool:
    return bool(surface and _DEBOUNCE_TOK.search(surface))


def _live_path_debounced(rust: str, ev: str) -> bool:
    """True when the Moved/Resized path delays the write (not a bare fs::write)."""
    for names, body in _event_arms(ev):
        if not (names & _LIVE_EVENTS):
            continue
        if _surface_debounced(body):
            return True
        for name in _called_names(body):
            if re.search(r"debounce", name, re.I):
                return True
            fn = _fn_body_named(rust, name)
            if _surface_debounced(fn):
                return True
            for inner in _called_names(fn):
                if re.search(r"debounce", inner, re.I):
                    return True
                if _surface_debounced(_fn_body_named(rust, inner)):
                    return True
    return False


def _persist_write_surface(rust: str) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    seeds = ("write_window_frame", "save_window_frame", "persist_window_frame")
    queue: list[str] = list(seeds)
    while queue:
        name = queue.pop(0)
        if name in seen:
            continue
        seen.add(name)
        body = _fn_body_named(rust, name)
        if not body.strip():
            continue
        parts.append(body)
        if name in seeds:
            queue.extend(_called_names(body))
    return "\n".join(parts)


def _has_atomic_frame_write(rust: str) -> bool:
    surface = _persist_write_surface(rust)
    if not surface.strip():
        return False
    return bool(
        _FRAME_DEST.search(surface)
        and _RENAME.search(surface)
        and _TEMP_FILE.search(surface)
    )

__all__ = [
    "_preceded_by_arrow",
    "_this_arm_pattern",
    "_arrow_arm_body",
    "_event_arms",
    "_called_names",
    "_arm_saves_live",
    "_live_events_that_save",
    "_surface_debounced",
    "_live_path_debounced",
    "_persist_write_surface",
    "_has_atomic_frame_write",
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
    "_FRAME_WRITE",
    "_EVENT_VARIANT",
    "_LIVE_EVENTS",
    "_DEBOUNCE_TOK",
    "_LIVE_HELPER_NAME",
    "_CALL_NAME",
    "_CALL_SKIP",
    "_FRAME_DEST",
    "_RENAME",
    "_TEMP_FILE",
    "_fn_body_named",
]
