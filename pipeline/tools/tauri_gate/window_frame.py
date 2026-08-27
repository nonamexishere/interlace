"""#306 — persist window size + position (native sibling file).

Approach B: custom Rust under session::config_dir() (not config.toml /
last-archive.bookmark). Translate-only work_area clamp. Do not persist
maximized / fullscreen. Not tauri-plugin-window-state. Not App.svelte
localStorage for the frame.

PR #324 review fold: save_window_frame returns early when
is_maximized() / is_fullscreen() is true (no maximized field, no
set_maximized / set_fullscreen). #306-rerun: on_window_event saves
from Moved / Resized again (debounced + atomic temp/rename write)
so a tauri:dev rerun keeps the new frame.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.import_boot import _ls_pref_keys
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
from tauri_gate.status_toasts import _toml_keys_in_fn, _windows_around

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


def assert_persist_window_frame(crate: Path) -> None:
    """#306: persist + restore the main window frame (approach B).

    Native x/y + width/height for label `main`, sibling file under
    session::config_dir(), translate-only work_area clamp, first-run
    960×640. Not plugin / webview / config.toml / last-archive.bookmark.
    Do not persist maximized / fullscreen. Keep #212 / #276 / #305,
    Overlay + CSP + entitlements. D24 in docs/user/app.md.

    PR #324 review fold: save_window_frame returns early when
    is_maximized() or is_fullscreen() is true (do not persist a
    maximized / fullscreen field; do not set_maximized / set_fullscreen).
    #306-rerun: on_window_event saves from Moved / Resized (or a named
    debounce helper those events call). Live write is debounced and
    atomic (temp + rename over window-frame.json). CloseRequested /
    Destroyed may still flush immediately.
    """
    main_path = crate / "src" / "main.rs"
    if not main_path.is_file():
        fail(
            "#306: crates/interlace-tauri/src/main.rs required "
            "(native frame persist lives there)"
        )
    rust = _without_comments(_tauri_rust_blob(crate))
    frame = _frame_surface(rust)
    save = _save_surface(rust)
    restore = _restore_surface(rust)
    cargo = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    conf_path = crate / "tauri.conf.json"
    conf = conf_path.read_text() if conf_path.is_file() else ""
    caps = ""
    caps_path = crate / "capabilities" / "default.json"
    if caps_path.is_file():
        caps = caps_path.read_text()
    ent = ""
    ent_path = crate / "Interlace.entitlements"
    if ent_path.is_file():
        ent = ent_path.read_text()
    app_path = crate / "web" / "App.svelte"
    app = app_path.read_text() if app_path.is_file() else ""
    app_clean = _without_comments(app)
    web = _without_comments(app + "\n" + _web_logic(crate))
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    session_path = repo_root() / "crates" / "interlace-core" / "src" / "session.rs"
    session = session_path.read_text() if session_path.is_file() else ""

    # 1) frame-persist-xywh — native save of size + position for label main.
    if not _has_xywh_save(save) and not _has_xywh_save(frame):
        fail(
            "#306: persist the main window frame (x/y + width/height) "
            "in native Rust for label main"
        )

    # 2) frame-restore-on-launch — next launch applies the stored frame.
    if not _has_xywh_restore(restore) and not _has_xywh_restore(frame):
        fail(
            "#306: next launch must apply the stored frame "
            "(set_size + set_position on label main)"
        )
    if not _SETUP.search(rust) and not _MAIN_GET.search(restore + "\n" + frame):
        fail(
            "#306: next launch must apply the stored frame "
            "(set_size + set_position on label main)"
        )

    # 3) frame-first-run-960 — missing / junk store leaves today’s 960×640.
    if not conf.strip():
        fail(
            "#306: tauri.conf.json required — main window must stay "
            "960×640 when no stored frame (first run)"
        )
    try:
        cfg = json.loads(conf)
    except json.JSONDecodeError:
        fail(
            "#306: tauri.conf.json must be valid JSON "
            "(main window 960×640 when no stored frame)"
        )
    main_win = _main_window_conf(cfg)
    if not main_win:
        fail(
            "#306: tauri.conf.json main window required "
            "(label main stays 960×640 when no stored frame)"
        )
    if main_win.get("label") != "main":
        fail("#306: persist/restore the window labeled main")
    if main_win.get("width") != 960 or main_win.get("height") != 640:
        fail(
            "#306: tauri.conf.json main window must stay 960×640 "
            "when no stored frame (first run; do not invent another default size)"
        )
    if not _has_junk_branch(restore) and not _has_junk_branch(frame):
        fail(
            "#306: missing / junk window-frame store must leave today’s 960×640 "
            "(do not invent another default size)"
        )

    # 4) frame-offscreen-clamp — translate onto a visible work_area.
    if not _has_translate_clamp(restore + "\n" + frame):
        fail(
            "#306: restore must translate the saved frame onto a visible "
            "work_area (available_monitors + work_area; positive intersection; "
            "not fully off-screen; translate-only — do not require shrink-to-fit)"
        )

    # 5) frame-not-config-toml — sibling under config_dir(); not bookmark.
    if not session_path.is_file():
        fail(
            "#306: crates/interlace-core/src/session.rs required "
            "(window frame is not write_last_path / config.toml)"
        )
    wl = _rust_fn_body(_without_comments(session), "write_last_path")
    if not wl.strip():
        fail(
            "#306: keep session.rs write_last_path as the last_archive_path writer "
            "(do not rewrite it to dump the window frame)"
        )
    extra = [k for k in _toml_keys_in_fn(wl) if k != "last_archive_path"]
    if extra or re.search(r"\b(?:window|frame|width|height|pos_x|pos_y)\b", wl, re.I):
        fail(
            "#306: do not rewrite session.rs write_last_path to dump extra keys "
            "(window frame is not last_archive_path / config.toml)"
        )
    store_src = frame + "\n" + save + "\n" + restore
    if _LAST_PATH_API.search(store_src) or _CONFIG_TOML.search(store_src):
        fail(
            "#306: do not persist the window frame via write_last_path / "
            "read_last_path / config.toml (sibling file under session::config_dir())"
        )
    if _BOOKMARK.search(store_src):
        fail(
            "#306: window frame is not last-archive.bookmark "
            "(sibling file under session::config_dir())"
        )
    if not _CONFIG_DIR.search(store_src):
        fail(
            "#306: store the window frame in a sibling file under "
            "session::config_dir() (not config.toml / last-archive.bookmark)"
        )

    # 6) frame-not-fullscreen-only — x/y + width/height only; no maximized.
    persist_src = save + "\n" + restore + "\n" + frame
    if _STORE_MAX.search(persist_src) or _APPLY_MAX.search(persist_src):
        fail(
            "#306: do not persist maximized / zoomed / fullscreen "
            "(x/y + width/height only; not maximize-as-the-only-persist)"
        )
    if _PLUGIN_MAX.search(rust) or _AUTOSAVE.search(rust) or _AUTOSAVE.search(cargo):
        fail(
            "#306: do not persist fullscreen / Spaces / maximized "
            "(no plugin StateFlags::all, no Cocoa frame autosave)"
        )

    # 7) frame-keep-212-276-305 — sidebar / density / lastView / lastPersonId.
    if not app_path.is_file():
        fail("#306: App.svelte required (keep #212 / #276 / #305 persist keys)")
    if "interlace.peopleSidebarCollapsed" not in web:
        fail("#306: keep #212 sidebar persist (interlace.peopleSidebarCollapsed)")
    if "interlace.density" not in web:
        fail("#306: keep #276 density persist (interlace.density)")
    if "interlace.lastView" not in web or "interlace.lastPersonId" not in web:
        fail(
            "#306: keep #305 last view / last person keys "
            "(interlace.lastView / interlace.lastPersonId)"
        )
    if "restoreLastView" not in app_clean or "restoreLastPerson" not in app_clean:
        fail("#306: keep the #305 restore path (restoreLastView / restoreLastPerson)")
    if not re.search(r"\bpersistSidebar\b", app_clean) or not re.search(
        r"\bpersistDensity\b", app_clean
    ):
        fail("#306: keep persistSidebar / persistDensity (#212 / #276)")

    # 8) frame-keep-overlay-csp-entitlements + approach B (not A / C).
    if _PLUGIN.search(cargo) or _PLUGIN.search(rust):
        fail(
            "#306: do not add tauri-plugin-window-state "
            "(custom Rust sibling file + work_area clamp)"
        )
    if _WEB_SET_FRAME.search(web):
        fail(
            "#306: do not persist the frame from App.svelte "
            "(no setSize / setPosition; native Rust only)"
        )
    if _frame_ls_keys(_ls_pref_keys(web)):
        fail(
            "#306: do not persist the window frame in localStorage "
            "(native sibling file; keep #212 / #276 / #305 keys as they are)"
        )
    tbs = main_win.get("titleBarStyle") or main_win.get("title_bar_style")
    if not isinstance(tbs, str) or tbs.casefold() != "overlay":
        fail("#306: keep the overlay titlebar (titleBarStyle Overlay)")
    if main_win.get("hiddenTitle") is not True:
        fail("#306: keep hiddenTitle true (overlay titlebar)")
    if CSP not in conf:
        fail("#306: do not soften tauri CSP (connect-src IPC-only)")
    if "network.client" not in ent:
        fail("#306: keep entitlements network.client")
    if "network.server" in ent:
        fail("#306: entitlements must omit network.server")
    if _HTTP_PLUGIN.search(cargo):
        fail("#306: no HTTP client / updater plugin")
    if _WEBVIEW_ACL.search(caps):
        fail(
            "#306: no webview allow-set-size / allow-set-position "
            "(native Rust set_size / set_position only)"
        )

    # 9) frame-d24 — docs: reopen restores last size + position; off-screen clamped.
    if not dtxt.strip():
        fail(
            "#306: docs/user/app.md required — reopen restores last window "
            "size and position; off-screen is clamped"
        )
    if not _DOCS_SIZE_POS.search(dtxt) or not _DOCS_REOPEN_FRAME.search(dtxt):
        fail(
            "#306: docs/user/app.md must say reopen restores the last "
            "window size and position"
        )
    if not _DOCS_CLAMP.search(dtxt):
        fail("#306: docs/user/app.md must say off-screen is clamped")

    # 10) frame-skip-zoomed-save — do not persist a maximized / fullscreen rect.
    save_fn = _save_fn_body(rust)
    if not _save_skips_zoomed(save_fn):
        fail(
            "#306: save_window_frame must return early when is_maximized() "
            "or is_fullscreen() is true (do not persist a zoomed / fullscreen "
            "frame; last normal x/y/w/h stay on disk)"
        )

    # 11) frame-live-save — Moved / Resized (or a named debounce helper).
    ev = _on_window_event_blob(rust)
    live_saving = _live_events_that_save(rust, ev)
    if not ev.strip() or not _LIVE_EVENTS <= live_saving:
        fail(
            "#306: on_window_event must save from Moved / Resized "
            "(or a named debounce helper those events call) so a "
            "tauri:dev rerun keeps the new frame"
        )

    # 12) frame-live-debounce — not a bare fs::write on every pixel.
    if not _live_path_debounced(rust, ev):
        fail(
            "#306: live Moved / Resized save must be debounced "
            "(timeout / sleep / Instant / named debounce; not a bare "
            "fs::write on every pixel)"
        )

    # 13) frame-atomic-write — temp file + rename over window-frame.json.
    if not _has_atomic_frame_write(rust):
        fail(
            "#306: persist window-frame.json via a temp file + rename "
            "(atomic replace so a kill mid-write cannot leave an empty file)"
        )
