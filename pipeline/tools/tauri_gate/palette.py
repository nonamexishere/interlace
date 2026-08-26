"""Command-palette chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    CSP,
    _CMD_PALETTE_PKG,
    _KEYMAP_CALL_SKIP,
    _MOD_EITHER,
    _PALETTE_HOOK,
    _expand_fn_calls,
    _function_body,
    _match_closer,
    _product_svelte,
    _strip_html_comments,
    _svelte_markup,
    _ts_fn_body,
    _without_comments,
)

from tauri_gate.import_boot import (
    _app_keydown_body,
    _input_guard_span,
    _owned_imported_names,
)

from tauri_gate.keyboard import (
    _ESC_CLOSE_APP,
    _INPUT_BLUR,
    _INPUT_TAG_GUARD,
    _KEY_K,
    _PREVENT_DEFAULT,
    _VIEW_PEOPLE_ASSIGN,
    _VIEW_TAB_ORDER,
)

from tauri_gate.status_toasts import (
    _FOCUS_SEARCH_Q,
    _KEY_ESC,
    _KEY_F,
    _SECOND_UI_KIT,
    _WRITE_TEXT,
    _has_mod_combo,
    _split_people_only,
    _windows_around,
    _without_input_guard,
)




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


def assert_command_palette(crate: Path) -> None:
    """#215: ⌘K command palette — owned bits-ui Command, local views + people.

    Own web/lib/components/ui/command/ wrapping bits-ui Command. ⌘K / Ctrl+K
    opens from every view (INPUT guard lets k/K through). View items + jump
    to a loaded person. Search focuses #q. Esc closes. No api.search / FTS /
    HTTP / Spotlight. Docs. Do not rewrite #132 / #201 / #214.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#215: App.svelte required (⌘K command palette)")
    app = app_path.read_text()
    app_clean = _without_comments(app)
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    conf_path = crate / "tauri.conf.json"
    conf = conf_path.read_text() if conf_path.is_file() else ""
    pkg_path = crate / "package.json"
    pkg = pkg_path.read_text() if pkg_path.is_file() else ""

    # 1) Owned command/ (at least one .svelte + index.ts).
    cmd = _command_ui_dir(crate)
    if not cmd.is_dir():
        fail(
            "#215: missing owned Command under web/lib/components/ui/command/ "
            "(at least one .svelte + index.ts)"
        )
    if not any(cmd.glob("*.svelte")):
        fail(
            "#215: web/lib/components/ui/command/ needs at least one .svelte "
            "(owned Command wrapper)"
        )
    if not (cmd / "index.ts").is_file():
        fail("#215: web/lib/components/ui/command/index.ts required")
    cmd_blob = _command_dir_blob(cmd)

    # 2) Wraps local bits-ui Command (not cmdk / a second kit).
    if not re.search(r"from\s*[\"']bits-ui[\"']", cmd_blob):
        fail(
            "#215: web/lib/components/ui/command/ must wrap local bits-ui Command "
            '(import { Command … } from "bits-ui")'
        )
    if not re.search(r"\bCommand\b", cmd_blob):
        fail(
            "#215: web/lib/components/ui/command/ must wrap bits-ui Command "
            "(Command / Command.Root / computeCommandScore)"
        )
    if not _BITS_COMMAND_IMPORT.search(cmd_blob):
        fail(
            "#215: web/lib/components/ui/command/ must import Command from "
            "bits-ui (same wrap as Dialog / Tooltip)"
        )
    if _CMD_PALETTE_FROM.search(cmd_blob):
        fail(
            "#215: wrap local bits-ui Command — do not import cmdk / "
            "svelte-command in command/"
        )

    # 3) package.json still has bits-ui; still no cmdk / svelte-command / second kit.
    if not pkg_path.is_file():
        fail("#215: crates/interlace-tauri/package.json required (bits-ui local)")
    if '"bits-ui"' not in pkg:
        fail(
            "#215: package.json must keep bits-ui as a local dependency "
            "(wrap bits-ui Command; do not swap kits)"
        )
    if _CMD_PALETTE_PKG.search(pkg):
        fail(
            "#215: package.json must not add cmdk / svelte-command "
            "(#201 ban stays — wrap local bits-ui Command)"
        )
    if _SECOND_UI_KIT.search(pkg):
        fail(
            "#215: package.json must not add a second UI kit "
            "(@radix-ui / shadcn / daisyui / …) — wrap local bits-ui Command"
        )

    # 4) Chrome imports the owned wrapper, not bits-ui Command in App.
    used_owned = False
    for p in _product_svelte(crate):
        rel = str(p).replace("\\", "/")
        if "/components/ui/command/" in rel:
            continue
        text = p.read_text()
        if _owned_imported_names(text, "command"):
            used_owned = True
            break
    if not used_owned:
        fail(
            "#215: App / chrome must import the owned Command from "
            "$lib/components/ui/command (do not import bits-ui Command in App)"
        )
    if re.search(
        r"import\s*\{[^}]*\bCommand\b[^}]*\}\s*from\s*[\"']bits-ui[\"']",
        app,
    ):
        fail(
            "#215: wrap bits-ui Command in web/lib/components/ui/command/ — "
            "do not import Command from bits-ui in App.svelte"
        )

    raw_body = _app_keydown_body(app_clean) or _app_keydown_body(app)
    if not raw_body.strip():
        fail(
            "#215: App.svelte must handle window keydown (onKey) so ⌘K / "
            "Ctrl+K can open the command palette"
        )
    body = _expand_fn_calls(app_clean, raw_body)
    if body == raw_body:
        body = _expand_fn_calls(app, raw_body)
    prefix, tail = _split_people_only(raw_body)
    prefix_x = _expand_fn_calls(app_clean, prefix) if prefix.strip() else body
    if prefix_x == prefix:
        prefix_x = _expand_fn_calls(app, prefix) if prefix.strip() else body

    # 5) ⌘K / Ctrl+K from every view; INPUT guard lets k/K through; preventDefault.
    k_surface = _mod_k_windows(prefix_x)
    if not k_surface.strip():
        k_surface = _mod_k_windows(prefix)
    if not k_surface.strip():
        tail_k = _mod_k_windows(tail) if tail else ""
        if tail_k.strip() and not _mod_k_windows(prefix_x).strip():
            fail(
                "#215: ⌘K / Ctrl+K must run off People "
                "(it is after `if (view !== \"people\") return`)"
            )
        fail(
            "#215: App key handler must treat metaKey/ctrlKey + k/K as the "
            "command palette (from every view, including when an INPUT is focused)"
        )
    if not _has_mod_combo(k_surface) and not _has_mod_combo(prefix_x):
        fail(
            "#215: command palette must accept metaKey or ctrlKey "
            "(⌘K on macOS; ctrl+K so gates/tests see the fallback)"
        )
    if not _MOD_EITHER.search(k_surface) and not re.search(r"\bmod\b", k_surface):
        fail("#215: k/K palette must be a metaKey/ctrlKey combo, not a bare letter")
    if not re.search(r"altKey|\bmod\b", k_surface) and not re.search(
        r"altKey|\bmod\b", prefix
    ):
        fail(
            "#215: ⌘K / Ctrl+K must use the same AltGr-safe mod as #132 "
            "(metaKey or ctrlKey && !altKey)"
        )
    if not _PREVENT_DEFAULT.search(k_surface) and not _PREVENT_DEFAULT.search(prefix_x):
        fail(
            "#215: ⌘K / Ctrl+K must preventDefault "
            "(webview must not take the key)"
        )
    if not _PALETTE_OPEN_ASSIGN.search(k_surface) and not _PALETTE_OPEN_ASSIGN.search(
        prefix_x
    ):
        fail(
            "#215: ⌘K / Ctrl+K must open the command palette "
            "(set a command/palette flag or call openCommand/openPalette)"
        )
    if not _INPUT_TAG_GUARD.search(raw_body) and not _INPUT_TAG_GUARD.search(body):
        fail(
            "#215: keep the INPUT/TEXTAREA/SELECT guard "
            "(⌘K is an exception next to ⌘F; bare k still must not steal #q)"
        )
    guard_span = _input_guard_span(raw_body)
    if not guard_span:
        fail(
            "#215: INPUT/TEXTAREA/SELECT guard must still wrap the early return "
            "(add k/K next to ⌘F so the combo works from a field)"
        )
    guard = raw_body[guard_span[0] : guard_span[1] + 1]
    if not _KEY_CMD_K.search(guard) and not _KEY_K.search(guard):
        fail(
            "#215: INPUT guard must let ⌘K / Ctrl+K through "
            "(add k/K to the exception next to ⌘F)"
        )

    # 6) data-command-palette on the open palette surface.
    markup = _strip_html_comments(_svelte_markup(app))
    hook_ok = bool(_PALETTE_HOOK.search(markup) or _PALETTE_HOOK.search(app))
    if not hook_ok:
        hook_ok = bool(_PALETTE_HOOK.search(cmd_blob))
    if not hook_ok:
        for p in _product_svelte(crate):
            if _PALETTE_HOOK.search(p.read_text()):
                hook_ok = True
                break
    if not hook_ok:
        fail(
            "#215: open command palette surface must include data-command-palette"
        )

    surface = _palette_surface(crate, app, cmd_blob)
    surface_x = _expand_fn_calls(app_clean, surface) if surface.strip() else surface
    if surface_x == surface:
        surface_x = _expand_fn_calls(app, surface) if surface.strip() else surface

    # 7) View items: People, Search, Review, Import, Doctor.
    for label, tok in zip(_PALETTE_VIEW_LABELS, _VIEW_TAB_ORDER, strict=True):
        if not re.search(rf"\b{re.escape(label)}\b", surface):
            fail(
                f"#215: command palette must include a {label} view item "
                "(People / Search / Review / Import / Doctor)"
            )
        if not re.search(rf"[\"']{tok}[\"']", surface) and not re.search(
            rf"[\"']{tok}[\"']", surface_x
        ):
            fail(
                f'#215: choosing the {label} palette item must set view = "{tok}"'
            )

    # 8) Search path focuses #q (same idea as ⌘F / whenSearchPaneReady).
    if not _FOCUS_SEARCH_Q.search(surface_x) and not re.search(
        r"\bwhenSearchPaneReady\b", surface + "\n" + surface_x
    ):
        fail(
            "#215: choosing Search in the palette must focus #q "
            "(whenSearchPaneReady or getElementById(\"q\") — same path as ⌘F)"
        )

    # 9) Person items from the loaded people array; selectPerson + People view.
    if not _PALETTE_PEOPLE_SRC.search(surface) and not _PALETTE_PEOPLE_SRC.search(
        surface_x
    ):
        fail(
            "#215: palette person items must come from the loaded people array "
            "({#each people / people.map — not api.search / FTS)"
        )
    if not re.search(r"\b(?:display_name|personLabel)\b", surface) and not re.search(
        r"\b(?:display_name|personLabel)\b", surface_x
    ):
        fail(
            "#215: person item labels must use display_name / personLabel "
            "(same list as the sidebar)"
        )
    if not re.search(r"\bselectPerson\s*\(", surface) and not re.search(
        r"\bselectPerson\s*\(", surface_x
    ):
        fail(
            "#215: choosing a person in the palette must call selectPerson"
        )
    if not _VIEW_PEOPLE_ASSIGN.search(surface) and not _VIEW_PEOPLE_ASSIGN.search(
        surface_x
    ):
        fail(
            '#215: choosing a person in the palette must switch to People '
            '(view = "people")'
        )

    # 10) No api.search / FTS / HTTP / Spotlight from the palette.
    banned = _PALETTE_BANNED.search(surface) or _PALETTE_BANNED.search(cmd_blob)
    if banned:
        fail(
            "#215: command palette must stay local (loaded people + views) — "
            "no api.search / FTS / HTTP / Spotlight from the palette"
        )

    # 11) Esc closes the open palette; does not bounce the view; closed Esc stays.
    if not _KEY_ESC.search(raw_body) and not _KEY_ESC.search(body):
        fail("#215: Escape must close the open command palette")
    esc_surface = _windows_around(
        _without_input_guard(raw_body), _KEY_ESC, before=80, after=560
    )
    if not esc_surface.strip():
        esc_surface = _windows_around(raw_body, _KEY_ESC, before=80, after=560)
    esc_x = _expand_fn_calls(app_clean, esc_surface) or _expand_fn_calls(app, esc_surface)
    if not _PALETTE_OPEN_GATE.search(esc_surface) and not _PALETTE_OPEN_GATE.search(
        esc_x
    ):
        fail(
            "#215: Escape must close the open command palette "
            "(gate on the palette open flag / data-command-palette — "
            "do not steal Esc from INPUT when the palette is closed)"
        )
    if not _PALETTE_CLOSE_ASSIGN.search(esc_surface) and not _PALETTE_CLOSE_ASSIGN.search(
        esc_x
    ):
        fail(
            "#215: Escape when the palette is open must close it "
            "(command/palette flag = false) and return"
        )
    close_m = _PALETTE_CLOSE_ASSIGN.search(esc_surface) or _PALETTE_CLOSE_ASSIGN.search(
        esc_x
    )
    if close_m:
        blob = esc_surface if _PALETTE_CLOSE_ASSIGN.search(esc_surface) else esc_x
        after = blob[close_m.end() : close_m.end() + 240]
        view_m = _VIEW_PEOPLE_ASSIGN.search(after)
        if view_m and not re.search(r"\breturn\b", after[: view_m.start()]):
            fail(
                "#215: Esc must close the palette and return "
                "(do not also bounce the view to People)"
            )
    if esc_surface and _ESC_CLOSE_APP.search(esc_surface):
        fail("#215: Escape must not close the app (close the palette only)")
    if not _INPUT_BLUR.search(raw_body) and not _INPUT_BLUR.search(body):
        fail(
            "#215: keep Esc blur on INPUT when the palette is not open "
            "(do not steal Esc from #q / #person-filter)"
        )
    # Palette INPUT is an INPUT — Esc must still close when the palette is open.
    pre = raw_body[: guard_span[0]]
    if not (
        (_KEY_ESC.search(pre) and _PALETTE_CLOSE_ASSIGN.search(pre))
        or (
            _KEY_ESC.search(guard)
            and (
                _PALETTE_CLOSE_ASSIGN.search(guard) or _PALETTE_OPEN_GATE.search(guard)
            )
        )
    ):
        fail(
            "#215: Esc must close the open palette even when its INPUT is focused "
            "(handle it before the INPUT return, or let Escape through when open)"
        )

    # 12) Docs: ⌘K / Ctrl+K, person jump, Search → #q, Esc closes, local-only.
    if not dtxt.strip():
        fail(
            "#215: docs/user/app.md required — ⌘K / Ctrl+K command palette, "
            "person jump, Search → #q, Esc closes, local-only"
        )
    if not _DOCS_CMD_K.search(dtxt):
        fail(
            "#215: docs/user/app.md must document ⌘K / Ctrl+K "
            "(opens a local command palette)"
        )
    if not _DOCS_CMD_PALETTE.search(dtxt):
        fail("#215: docs/user/app.md must mention the command palette")
    if not _DOCS_PERSON_JUMP.search(dtxt):
        fail(
            "#215: docs/user/app.md must say you can type a person name to jump"
        )
    if not _DOCS_PALETTE_SEARCH_Q.search(dtxt):
        fail(
            "#215: docs/user/app.md must say Search in the palette focuses #q"
        )
    if not _DOCS_PALETTE_ESC.search(dtxt):
        fail("#215: docs/user/app.md must say Esc closes the command palette")
    if not _DOCS_PALETTE_LOCAL.search(dtxt):
        fail(
            "#215: docs/user/app.md must say the palette is local "
            "(loaded people + views), not archive full-text / Spotlight"
        )

    # 13) Do not soften ⌘F, ⌘1–5, #q, sidebar, overlay, inspector, CSP.
    if not _KEY_F.search(prefix_x) and not _KEY_F.search(raw_body):
        fail("#215: keep ⌘F / ctrl+F Find (do not rewrite #132)")
    if not _has_mod_combo(prefix_x) and not _has_mod_combo(raw_body):
        fail(
            "#215: keep metaKey or ctrlKey on Find / tab digits "
            "(do not rewrite #132 ⌘F / ⌘1–5)"
        )
    for tok in _VIEW_TAB_ORDER:
        if not re.search(rf"[\"']{tok}[\"']", prefix_x) and not re.search(
            rf"[\"']{tok}[\"']", raw_body
        ):
            fail(
                f'#215: keep ⌘1–5 view "{tok}" '
                "(1 People … 5 Doctor — do not rewrite #132)"
            )
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#215: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#215: keep data-people-sidebar (#159 / #212)")
    if not re.search(r"\bdata-person-inspector\b", app):
        fail("#215: keep data-person-inspector (#213)")
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#215: keep the overlay titlebar (#211)")
    if CSP not in conf:
        fail("#215: do not soften tauri CSP")


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


def assert_command_palette_people_cap(crate: Path) -> None:
    """#215: palette people items are filtered + capped (≤32), not {#each people}.

    CommandPalette / data-command-palette / command/ chrome only — not the
    sidebar {#each filtered}. Do not rewrite assert_command_palette.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#215: App.svelte required (command palette people cap)")
    app = app_path.read_text()
    cmd_blob = _command_dir_blob(_command_ui_dir(crate))
    surface = _palette_surface(crate, app, cmd_blob)
    pal_path = crate / "web" / "lib" / "CommandPalette.svelte"
    if pal_path.is_file():
        surface = surface + "\n" + pal_path.read_text()
    cleaned = _without_comments(surface)

    # 1) Do not mount the raw loaded array as Command.Item rows.
    if _PALETTE_RAW_PEOPLE_EACH.search(cleaned):
        fail(
            "#215: command palette must not mount the raw people array "
            "({#each people as / {#each people () — filter the loaded list "
            "and render at most 32"
        )

    # 2) Filter / slice the loaded people array (not sidebar filtered).
    has_people = bool(
        re.search(r"\bpeople\b", cleaned) or _PALETTE_PEOPLE_SRC.search(cleaned)
    )
    has_filter_or_slice = bool(
        _PALETTE_PEOPLE_FILTER.search(cleaned)
        or re.search(r"\.\s*(?:filter|slice)\s*\(", cleaned)
    )
    if not (_PALETTE_PEOPLE_FILTER.search(cleaned) or (has_people and has_filter_or_slice)):
        fail(
            "#215: palette people items must come from people.filter "
            "(or people + .filter( / .slice() of the loaded array) — "
            "not the full list"
        )

    # 3) Numeric cap ≤32: slice(0, N) or PALETTE_PEOPLE_CAP / similar.
    if not _palette_people_cap_ok(cleaned):
        fail(
            "#215: palette people items must be capped at ≤32 "
            "(slice(0, N) with N<=32, or PALETTE_PEOPLE_CAP / similar)"
        )

    # 4) Keep #215 person jump: labels, selectPerson, People view.
    surface_x = _expand_fn_calls(app, surface) if surface.strip() else surface
    if not re.search(r"\b(?:display_name|personLabel)\b", cleaned) and not re.search(
        r"\b(?:display_name|personLabel)\b", surface_x
    ):
        fail(
            "#215: person item labels must use display_name / personLabel "
            "(same list as the sidebar)"
        )
    if not re.search(r"\bselectPerson\s*\(", cleaned) and not re.search(
        r"\bselectPerson\s*\(", surface_x
    ):
        fail(
            "#215: choosing a person in the palette must call selectPerson"
        )
    if not _VIEW_PEOPLE_ASSIGN.search(cleaned) and not _VIEW_PEOPLE_ASSIGN.search(
        surface_x
    ):
        fail(
            '#215: choosing a person in the palette must switch to People '
            '(view = "people")'
        )

    # 5) Still local — no api.search / FTS / HTTP / Spotlight.
    banned = _PALETTE_BANNED.search(cleaned) or _PALETTE_BANNED.search(cmd_blob)
    if banned:
        fail(
            "#215: command palette must stay local (loaded people + views) — "
            "no api.search / FTS / HTTP / Spotlight from the palette"
        )


def assert_command_palette_field_keys(crate: Path) -> None:
    """#215: palette field keeps Ctrl/⌘A; chrome shortcuts do not steal keys from [data-command-palette]."""
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#215: App.svelte required (palette field keys)")
    app = app_path.read_text()
    app_clean = _without_comments(app)
    raw_body = _app_keydown_body(app_clean) or _app_keydown_body(app)
    if not raw_body.strip():
        fail(
            "#215: App.svelte must handle window keydown (onKey) so the "
            "palette field can keep Ctrl/⌘A"
        )

    # 1) After Esc-close, return when commandOpen + target in [data-command-palette]
    #    — before ⌘K commandOpen=true / ⌘F whenSearchPaneReady.
    chrome_at = _palette_chrome_shortcut_at(raw_body)
    prefix = raw_body[:chrome_at]
    prefix_x = _expand_fn_calls(app_clean, prefix) if prefix.strip() else prefix
    if prefix_x == prefix:
        prefix_x = _expand_fn_calls(app, prefix) if prefix.strip() else prefix
    esc_end = _palette_esc_close_end(raw_body)
    region = raw_body[esc_end:chrome_at] if esc_end is not None else prefix
    if not (
        _in_palette_skip_ok(prefix, region) or _in_palette_skip_ok(prefix_x, region)
    ):
        fail(
            "#215: after Esc-close, onKey must return when commandOpen and "
            "the target is inside [data-command-palette] (before ⌘K / ⌘F — "
            "chrome must not steal field keys)"
        )

    # 2) Palette surface handles meta/ctrl + a/A and select()s the field.
    cmd_blob = _command_dir_blob(_command_ui_dir(crate))
    surface = _palette_surface(crate, app, cmd_blob)
    pal_path = crate / "web" / "lib" / "CommandPalette.svelte"
    if pal_path.is_file():
        surface = surface + "\n" + pal_path.read_text()
    surface_x = _expand_fn_calls(surface, surface) if surface.strip() else surface
    a_surface = _mod_a_windows(surface) or _mod_a_windows(surface_x)
    if not a_surface.strip():
        fail(
            "#215: palette field must handle meta/ctrl + a/A "
            "(select all in [data-command-palette])"
        )
    if not _PALETTE_SELECT_ALL.search(a_surface) and not _PALETTE_SELECT_ALL.search(
        surface
    ):
        fail(
            "#215: palette field Ctrl/⌘A must select() the text "
            "(or setSelectionRange) so WKWebView Select All works"
        )

    # 3) INPUT guard still lets k/K through (⌘K from #q / #person-filter).
    if not _INPUT_TAG_GUARD.search(raw_body):
        fail(
            "#215: keep the INPUT/TEXTAREA/SELECT guard "
            "(⌘K from #q must still open the palette)"
        )
    guard_span = _input_guard_span(raw_body)
    if not guard_span:
        fail(
            "#215: INPUT/TEXTAREA/SELECT guard must still wrap the early return "
            "(k/K stays an exception so ⌘K works from #q)"
        )
    guard = raw_body[guard_span[0] : guard_span[1] + 1]
    if not _KEY_CMD_K.search(guard) and not _KEY_K.search(guard):
        fail(
            "#215: INPUT guard must still let k/K through "
            "(⌘K from #q / #person-filter must still open the palette)"
        )

    # 4) Esc still closes the open palette.
    if not _KEY_ESC.search(raw_body):
        fail("#215: Escape must still close the open command palette")
    if not _PALETTE_CLOSE_ASSIGN.search(raw_body):
        fail(
            "#215: Escape must still close the open palette "
            "(commandOpen = false / closeCommand)"
        )


def assert_command_palette_clipboard(crate: Path) -> None:
    """#215: palette field Ctrl/⌘C / V / X via navigator.clipboard (no plugin)."""
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#215: App.svelte required (palette field clipboard)")
    app = app_path.read_text()
    cmd_blob = _command_dir_blob(_command_ui_dir(crate))
    surface = _palette_surface(crate, app, cmd_blob)
    pal_path = crate / "web" / "lib" / "CommandPalette.svelte"
    if pal_path.is_file():
        surface = surface + "\n" + pal_path.read_text()
    surface_x = _expand_fn_calls(surface, surface) if surface.strip() else surface

    # 1) Palette field: meta/ctrl + c/C → clipboard.writeText (copy).
    c_surface = _mod_c_windows(surface) or _mod_c_windows(surface_x)
    if not c_surface.strip():
        fail(
            "#215: palette field must handle meta/ctrl + c/C "
            "(clipboard.writeText / navigator.clipboard.writeText)"
        )
    if not _WRITE_TEXT.search(c_surface) and not _WRITE_TEXT.search(surface):
        fail(
            "#215: palette field Ctrl/⌘C must call clipboard.writeText "
            "(or navigator.clipboard.writeText) — no clipboard plugin"
        )

    # 2) Palette field: meta/ctrl + v/V → clipboard.readText (paste).
    v_surface = _mod_v_windows(surface) or _mod_v_windows(surface_x)
    if not v_surface.strip():
        fail(
            "#215: palette field must handle meta/ctrl + v/V "
            "(clipboard.readText / navigator.clipboard.readText)"
        )
    if not _PALETTE_READ_TEXT.search(v_surface) and not _PALETTE_READ_TEXT.search(
        surface
    ):
        fail(
            "#215: palette field Ctrl/⌘V must call clipboard.readText "
            "(or navigator.clipboard.readText) — no clipboard plugin"
        )

    # 3) Palette field: meta/ctrl + x/X → clipboard.writeText (cut).
    x_surface = _mod_x_windows(surface) or _mod_x_windows(surface_x)
    if not x_surface.strip():
        fail(
            "#215: palette field must handle meta/ctrl + x/X "
            "(cut via clipboard.writeText / navigator.clipboard.writeText)"
        )
    if not _WRITE_TEXT.search(x_surface) and not _WRITE_TEXT.search(surface):
        fail(
            "#215: palette field Ctrl/⌘X must call clipboard.writeText "
            "(or navigator.clipboard.writeText) so cut copies the selection"
        )

    # 4) Still Ctrl/⌘A select() / setSelectionRange (do not drop #215-keys).
    a_surface = _mod_a_windows(surface) or _mod_a_windows(surface_x)
    if not a_surface.strip():
        fail(
            "#215: palette field must still handle meta/ctrl + a/A "
            "(do not drop #215-keys select-all)"
        )
    if not _PALETTE_SELECT_ALL.search(a_surface) and not _PALETTE_SELECT_ALL.search(
        surface
    ):
        fail(
            "#215: palette field Ctrl/⌘A must still select() the text "
            "(or setSelectionRange)"
        )

    # 5) No tauri-plugin-clipboard* / clipboard-manager in package.json / Cargo.toml.
    pkg_path = crate / "package.json"
    pkg = pkg_path.read_text() if pkg_path.is_file() else ""
    toml_path = crate / "Cargo.toml"
    toml = toml_path.read_text() if toml_path.is_file() else ""
    if _CLIPBOARD_PLUGIN.search(pkg) or _CLIPBOARD_PLUGIN.search(toml):
        fail(
            "#215: do not add tauri-plugin-clipboard / plugin-clipboard-manager "
            "/ clipboard-manager (use navigator.clipboard on the palette field)"
        )

    # 6) Still local — no api.search / FTS / HTTP / Spotlight.
    banned = _PALETTE_BANNED.search(surface) or _PALETTE_BANNED.search(cmd_blob)
    if banned:
        fail(
            "#215: command palette must stay local (loaded people + views) — "
            "no api.search / FTS / HTTP / Spotlight from the palette"
        )
