"""Continuation of palette_lib."""
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
    _CMD_PALETTE_PKG,
    _expand_fn_calls,
    _function_body,
    _KEYMAP_CALL_SKIP,
    _match_closer,
    _MOD_EITHER,
    _PALETTE_HOOK,
    _product_svelte,
    _search_pane_blob,
    _strip_html_comments,
    _svelte_markup,
    _ts_fn_body,
    _web_logic,
    _without_comments,
    CSP,
)

from tauri_gate.import_boot_guards import (
    _app_keydown_body,
    _input_guard_span,
    _owned_imported_names,
)

from tauri_gate.keyboard_lib import (
    _ESC_CLOSE_APP,
    _INPUT_BLUR,
    _INPUT_TAG_GUARD,
    _KEY_K,
    _PREVENT_DEFAULT,
    _VIEW_PEOPLE_ASSIGN,
    _VIEW_TAB_ORDER,
)

from tauri_gate.status_toasts_chrome import (
    _FOCUS_SEARCH_Q,
    _KEY_ESC,
    _SECOND_UI_KIT,
    _WRITE_TEXT,
    _has_mod_combo,
    _split_people_only,
    _windows_around,
    _without_input_guard,
)
from tauri_gate.status_toasts_toast import _KEY_F
from tauri_gate.palette_lib import (
    _KEY_CMD_K,
    _PALETTE_OPEN_ASSIGN,
    _PALETTE_CLOSE_ASSIGN,
    _PALETTE_OPEN_GATE,
    _PALETTE_SLICE_0_N,
    _PALETTE_SLICE_0_NAME,
    _PALETTE_PEOPLE_CAP_CONST,
    _KEY_CMD_A,
    _PALETTE_IN_FIELD,
    _PALETTE_FIELD_FLAG,
    _KEY_CMD_C,
    _KEY_CMD_V,
    _KEY_CMD_X,
    _palette_named_fns,
)


def _palette_surface(crate: Path, app: str, cmd_blob: str) -> str:
    """command/ sources + data-command-palette windows + *command*/*palette* fns.

    Not the whole App (nav already says People/Search; ⌘F already focuses #q).
    """
    parts = [
        cmd_blob,
        _windows_around(app, _PALETTE_HOOK, before=400, after=2800),
        _palette_named_fns(app),
        _windows_around(app, re.compile(r"<Command(?:\.\w+)?\b"), before=80, after=1200),
    ]
    for p in _product_svelte(crate):
        rel = str(p).replace("\\", "/")
        if "/components/ui/command/" in rel:
            continue
        if p.name == "App.svelte":
            continue
        text = p.read_text()
        if _PALETTE_HOOK.search(text) or _owned_imported_names(text, "command"):
            parts.append(text)
            parts.append(_palette_named_fns(text))
    return "\n".join(parts)


def _mod_k_windows(src: str) -> str:
    """Windows around k/K that are a meta/ctrl (or `mod`) combo, not timeline k."""
    parts: list[str] = []
    for m in _KEY_CMD_K.finditer(src):
        w = src[max(0, m.start() - 360) : m.end() + 640]
        if _MOD_EITHER.search(w) or re.search(r"\bmod\b", w):
            parts.append(w)
    return "\n".join(parts)


def _mod_a_windows(src: str) -> str:
    """Windows around a/A that are a meta/ctrl (or `mod`) combo."""
    parts: list[str] = []
    for m in _KEY_CMD_A.finditer(src):
        w = src[max(0, m.start() - 360) : m.end() + 640]
        if _MOD_EITHER.search(w) or re.search(r"\bmod\b", w):
            parts.append(w)
    return "\n".join(parts)


def _mod_c_windows(src: str) -> str:
    """Windows around c/C that are a meta/ctrl (or `mod`) combo."""
    parts: list[str] = []
    for m in _KEY_CMD_C.finditer(src):
        w = src[max(0, m.start() - 360) : m.end() + 640]
        if _MOD_EITHER.search(w) or re.search(r"\bmod\b", w):
            parts.append(w)
    return "\n".join(parts)


def _mod_v_windows(src: str) -> str:
    """Windows around v/V that are a meta/ctrl (or `mod`) combo."""
    parts: list[str] = []
    for m in _KEY_CMD_V.finditer(src):
        w = src[max(0, m.start() - 360) : m.end() + 640]
        if _MOD_EITHER.search(w) or re.search(r"\bmod\b", w):
            parts.append(w)
    return "\n".join(parts)


def _mod_x_windows(src: str) -> str:
    """Windows around x/X that are a meta/ctrl (or `mod`) combo."""
    parts: list[str] = []
    for m in _KEY_CMD_X.finditer(src):
        w = src[max(0, m.start() - 360) : m.end() + 640]
        if _MOD_EITHER.search(w) or re.search(r"\bmod\b", w):
            parts.append(w)
    return "\n".join(parts)


def _palette_esc_close_end(body: str) -> int | None:
    """End of the open-palette Escape-close block in onKey (if any)."""
    for m in _KEY_ESC.finditer(body):
        start = body.rfind("if", 0, m.start())
        if start < 0:
            continue
        head = body[start : m.end() + 80]
        if not (
            _PALETTE_FIELD_FLAG.search(head)
            or _PALETTE_OPEN_GATE.search(head)
        ):
            continue
        brace = body.find("{", m.start())
        if brace < 0:
            ret = body.find("return", m.start())
            chunk = body[m.start() : (ret + 20 if ret >= 0 else m.end() + 80)]
            if _PALETTE_CLOSE_ASSIGN.search(chunk):
                return ret + 6 if ret >= 0 else m.end()
            continue
        end = _match_closer(body, brace)
        block = body[start : end + 1] if end >= 0 else body[start : brace + 200]
        if _PALETTE_CLOSE_ASSIGN.search(block):
            return end if end >= 0 else brace
    return None


def _palette_chrome_shortcut_at(body: str) -> int:
    """Index of ⌘K open / ⌘F Search handlers (chrome must not run in-field)."""
    spots: list[int] = []
    m = _PALETTE_OPEN_ASSIGN.search(body)
    if m:
        spots.append(m.start())
    m = re.search(r"\bwhenSearchPaneReady\b", body)
    if m:
        spots.append(m.start())
    return min(spots) if spots else len(body)


def _in_palette_skip_ok(src: str, region: str) -> bool:
    """True if src gates a return on the palette flag + [data-command-palette]."""
    for m in _PALETTE_IN_FIELD.finditer(src):
        w = src[max(0, m.start() - 240) : m.end() + 240]
        after = src[m.start() :] + "\n" + region
        if _PALETTE_FIELD_FLAG.search(w) and re.search(r"\breturn\b", after):
            return True
    return False


def _palette_people_cap_ok(src: str) -> bool:
    """True if src proves a people-item cap of ≤32 (slice or named const)."""
    if any(int(n) <= 32 for n in _PALETTE_SLICE_0_N.findall(src)):
        return True
    consts = {
        m.group(1): int(m.group(2)) for m in _PALETTE_PEOPLE_CAP_CONST.finditer(src)
    }
    if any(v <= 32 for v in consts.values()):
        return True
    lower = {name.lower(): val for name, val in consts.items()}
    for name in _PALETTE_SLICE_0_NAME.findall(src):
        val = consts.get(name, lower.get(name.lower()))
        if val is not None and val <= 32:
            return True
    return False

__all__ = [
    "_KEY_CMD_K",
    "_BITS_COMMAND_IMPORT",
    "_PALETTE_VIEW_LABELS",
    "_PALETTE_OPEN_ASSIGN",
    "_PALETTE_CLOSE_ASSIGN",
    "_PALETTE_OPEN_GATE",
    "_PALETTE_PEOPLE_SRC",
    "_PALETTE_BANNED",
    "_DOCS_CMD_K",
    "_DOCS_CMD_PALETTE",
    "_DOCS_PERSON_JUMP",
    "_DOCS_PALETTE_SEARCH_Q",
    "_DOCS_PALETTE_ESC",
    "_DOCS_PALETTE_LOCAL",
    "_CMD_PALETTE_FROM",
    "_PALETTE_RAW_PEOPLE_EACH",
    "_PALETTE_PEOPLE_FILTER",
    "_PALETTE_SLICE_0_N",
    "_PALETTE_SLICE_0_NAME",
    "_PALETTE_PEOPLE_CAP_CONST",
    "_KEY_CMD_A",
    "_PALETTE_IN_FIELD",
    "_PALETTE_FIELD_FLAG",
    "_PALETTE_SELECT_ALL",
    "_KEY_CMD_C",
    "_KEY_CMD_V",
    "_KEY_CMD_X",
    "_PALETTE_READ_TEXT",
    "_CLIPBOARD_PLUGIN",
    "_command_ui_dir",
    "_command_dir_blob",
    "_palette_named_fns",
    "_palette_surface",
    "_mod_k_windows",
    "_mod_a_windows",
    "_mod_c_windows",
    "_mod_v_windows",
    "_mod_x_windows",
    "_palette_esc_close_end",
    "_palette_chrome_shortcut_at",
    "_in_palette_skip_ok",
    "_palette_people_cap_ok",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_CMD_PALETTE_PKG",
    "_expand_fn_calls",
    "_MOD_EITHER",
    "_PALETTE_HOOK",
    "_product_svelte",
    "_search_pane_blob",
    "_strip_html_comments",
    "_svelte_markup",
    "_web_logic",
    "_without_comments",
    "CSP",
    "_app_keydown_body",
    "_input_guard_span",
    "_owned_imported_names",
    "_ESC_CLOSE_APP",
    "_INPUT_BLUR",
    "_INPUT_TAG_GUARD",
    "_KEY_K",
    "_PREVENT_DEFAULT",
    "_VIEW_PEOPLE_ASSIGN",
    "_VIEW_TAB_ORDER",
    "_FOCUS_SEARCH_Q",
    "_KEY_ESC",
    "_KEY_F",
    "_SECOND_UI_KIT",
    "_WRITE_TEXT",
    "_has_mod_combo",
    "_split_people_only",
    "_windows_around",
    "_without_input_guard",
    "annotations",
    "_function_body",
    "_KEYMAP_CALL_SKIP",
    "_match_closer",
    "_ts_fn_body",
]

__all__ = [
    "_palette_surface",
    "_mod_k_windows",
    "_mod_a_windows",
    "_mod_c_windows",
    "_mod_v_windows",
    "_mod_x_windows",
    "_palette_esc_close_end",
    "_palette_chrome_shortcut_at",
    "_in_palette_skip_ok",
    "_palette_people_cap_ok",
    "__all__",
]
