"""Helpers extracted from palette.py (palette_lib)."""
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




# #215 — command palette (⌘K): owned bits-ui Command, local views + people.
# People items: filter + cap ≤32, not the full {#each people}.
# Palette field keeps Ctrl/⌘A; chrome shortcuts do not steal keys from
# [data-command-palette].
# _KEY_K is timeline j/k (lowercase only). Palette must accept k/K like ⌘F.
_KEY_CMD_K = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']k[\"']"
    r"|[\"']k[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']K[\"']"
    r"|[\"']K[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*\.\s*toLowerCase\s*\(\s*\)\s*===?\s*[\"']k[\"']"
    r"|(?:e\.)?code\s*===?\s*[\"']KeyK[\"']"
    r")",
    re.I,
)
_BITS_COMMAND_IMPORT = re.compile(
    r"import\s*\{[^}]*\bCommand\b[^}]*\}\s*from\s*[\"']bits-ui[\"']"
    r"|import\s+\*\s+as\s+\w+\s+from\s*[\"']bits-ui[\"']",
)
_PALETTE_VIEW_LABELS = ("People", "Search", "Review", "Import", "Doctor")
_PALETTE_OPEN_ASSIGN = re.compile(
    r"("
    r"(?:command|palette)\w*\s*=\s*true"
    r"|(?:command|palette)\w*\s*=\s*!\s*(?:command|palette)\w*"
    r"|open(?:Command|Palette)\s*\("
    r"|show(?:Command|Palette)\s*\("
    r")",
    re.I,
)
_PALETTE_CLOSE_ASSIGN = re.compile(
    r"("
    r"(?:command|palette)\w*\s*=\s*false"
    r"|close(?:Command|Palette)\s*\("
    r")",
    re.I,
)
_PALETTE_OPEN_GATE = re.compile(
    r"("
    r"(?:command|palette)\w*"
    r"|data-command-palette"
    r")",
    re.I,
)
_PALETTE_PEOPLE_SRC = re.compile(
    r"("
    r"\{#each\s+people\b"
    r"|\bpeople\s*\.\s*(?:map|filter|flatMap|forEach)\s*\("
    r"|\bfor\s*\([^)]*\bof\s+people\b"
    r")"
)
_PALETTE_BANNED = re.compile(
    r"("
    r"\bapi\s*\.\s*search\s*\("
    r"|\bfts\b"
    r"|spotlight"
    r"|NSUserActivity"
    r"|fetch\s*\("
    r"|https?://"
    r")",
    re.I,
)
_DOCS_CMD_K = re.compile(
    r"("
    r"⌘\s*K"
    r"|Cmd(?:-|\s*|\+)\s*K"
    r"|Command(?:-|\s*|\+)\s*K"
    r"|Ctrl(?:-|\s*|\+)\s*K"
    r")",
    re.I,
)
_DOCS_CMD_PALETTE = re.compile(r"command palette", re.I)
_DOCS_PERSON_JUMP = re.compile(
    r"("
    r"(?:type|jump).{0,80}person"
    r"|person.{0,60}(?:jump|name)"
    r")",
    re.I | re.S,
)
_DOCS_PALETTE_SEARCH_Q = re.compile(
    r"("
    r"(?:command palette|⌘\s*K|Ctrl(?:-|\s*|\+)\s*K).{0,280}"
    r"Search.{0,100}#q"
    r"|Search.{0,80}#q.{0,200}(?:command palette|⌘\s*K|local)"
    r")",
    re.I | re.S,
)
_DOCS_PALETTE_ESC = re.compile(
    r"("
    r"(?:[Ee]sc(?:ape)?).{0,80}(?:close[sd]?).{0,80}(?:palette|command)"
    r"|(?:palette|command).{0,80}(?:[Ee]sc(?:ape)?).{0,40}close"
    r")",
    re.I | re.S,
)
_DOCS_PALETTE_LOCAL = re.compile(
    r"("
    r"local.{0,120}(?:loaded people|people \+ views|not.{0,40}(?:full-?text|Spotlight|FTS))"
    r"|loaded people.{0,80}(?:view|not.{0,40}(?:full-?text|Spotlight|FTS))"
    r"|not.{0,60}(?:archive full-?text|full-?text|Spotlight)"
    r")",
    re.I | re.S,
)
_CMD_PALETTE_FROM = re.compile(
    r"from\s*[\"'](?:cmdk|svelte-command(?:-palette)?)[\"']",
    re.I,
)
# Raw palette {#each} of the loaded array (sidebar {#each filtered} is fine).
_PALETTE_RAW_PEOPLE_EACH = re.compile(r"\{#each\s+people\s+(?:as|\()")
_PALETTE_PEOPLE_FILTER = re.compile(r"\bpeople\s*\.\s*filter\s*\(")
_PALETTE_SLICE_0_N = re.compile(r"\.\s*slice\s*\(\s*0\s*,\s*(\d+)\s*\)")
_PALETTE_SLICE_0_NAME = re.compile(
    r"\.\s*slice\s*\(\s*0\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)"
)
_PALETTE_PEOPLE_CAP_CONST = re.compile(
    r"\b(PALETTE_PEOPLE_CAP|PEOPLE_CAP|MAX_PALETTE_PEOPLE|MAX_PEOPLE|"
    r"PALETTE_LIMIT|PEOPLE_LIMIT|palettePeopleCap|peopleCap)\s*=\s*(\d+)",
    re.I,
)
# Palette field: Ctrl/⌘A select-all + in-palette chrome skip.
_KEY_CMD_A = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']a[\"']"
    r"|[\"']a[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']A[\"']"
    r"|[\"']A[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*\.\s*toLowerCase\s*\(\s*\)\s*===?\s*[\"']a[\"']"
    r"|(?:e\.)?code\s*===?\s*[\"']KeyA[\"']"
    r")",
    re.I,
)
_PALETTE_IN_FIELD = re.compile(
    r"("
    r"closest[\s?.]*\(\s*[\"']\[data-command-palette\][\"']"
    r"|matches[\s?.]*\(\s*[\"']\[data-command-palette\][\"']"
    r"|data-command-palette"
    r")"
)
_PALETTE_FIELD_FLAG = re.compile(
    r"\b(?:command|palette)(?:Open|Shown|Visible|_open)\b"
    r"|\b(?:is|show|open)(?:Command|Palette)(?:Open)?\b",
    re.I,
)
_PALETTE_SELECT_ALL = re.compile(r"\b(?:select|setSelectionRange)\s*\(")
# Palette field: Ctrl/⌘C / V / X via navigator.clipboard (no plugin).
_KEY_CMD_C = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']c[\"']"
    r"|[\"']c[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']C[\"']"
    r"|[\"']C[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*\.\s*toLowerCase\s*\(\s*\)\s*===?\s*[\"']c[\"']"
    r"|(?:e\.)?code\s*===?\s*[\"']KeyC[\"']"
    r")",
    re.I,
)
_KEY_CMD_V = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']v[\"']"
    r"|[\"']v[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']V[\"']"
    r"|[\"']V[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*\.\s*toLowerCase\s*\(\s*\)\s*===?\s*[\"']v[\"']"
    r"|(?:e\.)?code\s*===?\s*[\"']KeyV[\"']"
    r")",
    re.I,
)
_KEY_CMD_X = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']x[\"']"
    r"|[\"']x[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']X[\"']"
    r"|[\"']X[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*\.\s*toLowerCase\s*\(\s*\)\s*===?\s*[\"']x[\"']"
    r"|(?:e\.)?code\s*===?\s*[\"']KeyX[\"']"
    r")",
    re.I,
)
_PALETTE_READ_TEXT = re.compile(
    r"("
    r"navigator\.clipboard\.readText"
    r"|clipboard\.readText"
    r")"
)
_CLIPBOARD_PLUGIN = re.compile(
    r"("
    r"tauri-plugin-clipboard"
    r"|plugin-clipboard-manager"
    r"|clipboard-manager"
    r")"
)


def _command_ui_dir(crate: Path) -> Path:
    return crate / "web" / "lib" / "components" / "ui" / "command"


def _command_dir_blob(cmd: Path) -> str:
    parts: list[str] = []
    if not cmd.is_dir():
        return ""
    for p in sorted(cmd.rglob("*")):
        if p.is_file() and p.suffix in {".svelte", ".ts", ".js"}:
            parts.append(p.read_text())
    return "\n".join(parts)


def _palette_named_fns(src: str) -> str:
    names: set[str] = set()
    for m in re.finditer(
        r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*(?:[Cc]ommand|[Pp]alette)[A-Za-z0-9_]*)",
        src,
    ):
        names.add(m.group(1))
    for m in re.finditer(
        r"(?:const|let)\s+([A-Za-z_][A-Za-z0-9_]*(?:[Cc]ommand|[Pp]alette)[A-Za-z0-9_]*)\s*=",
        src,
    ):
        names.add(m.group(1))
    chunks: list[str] = []
    for name in names:
        if name in _KEYMAP_CALL_SKIP:
            continue
        inner = _ts_fn_body(src, name) or _function_body(src, name)
        if inner:
            chunks.append(inner)
    return "\n".join(chunks)

from tauri_gate.palette_lib_rest import (
    _palette_surface,
    _mod_k_windows,
    _mod_a_windows,
    _mod_c_windows,
    _mod_v_windows,
    _mod_x_windows,
    _palette_esc_close_end,
    _palette_chrome_shortcut_at,
    _in_palette_skip_ok,
    _palette_people_cap_ok,
    __all__,
)

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
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_CMD_PALETTE_PKG",
    "_expand_fn_calls",
    "_function_body",
    "_KEYMAP_CALL_SKIP",
    "_match_closer",
    "_MOD_EITHER",
    "_PALETTE_HOOK",
    "_product_svelte",
    "_search_pane_blob",
    "_strip_html_comments",
    "_svelte_markup",
    "_ts_fn_body",
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
    "_SECOND_UI_KIT",
    "_WRITE_TEXT",
    "_has_mod_combo",
    "_split_people_only",
    "_windows_around",
    "_without_input_guard",
    "_KEY_F",
]
