"""Import drag-drop / progress / cancel chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    CSP,
    _APPEARANCE_FETCH,
    _APPEARANCE_MENU_LABEL,
    _APPEARANCE_SCRIM_NAMES,
    _FETCH_CALL,
    _STATUS_CONFETTI,
    _STATUS_GRADIENT,
    _STATUS_WARNING_NAMES,
    _ancestor_tags,
    _call_arg,
    _contrast_dark_blob,
    _css_var,
    _function_body,
    _match_closer,
    _product_svelte,
    _rust_fn_body,
    _tauri_rust_blob,
    _tauri_rust_sources,
    _ts_fn_body,
    _web_logic,
    _web_ts_sources,
    _without_comments,
)

from tauri_gate.contrast import _STATUS_CELEBRATION

from tauri_gate.import_boot import _contrast_light_blob

from tauri_gate.status_toasts import (
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


def _drop_starts_import(crate: Path, surface: str, app: str, import_pane: str) -> bool:
    if _IMPORT_START_CALL.search(surface):
        return True
    if re.search(r"\bstart\s*\(", surface) and _IMPORT_START_CALL.search(import_pane):
        return True
    if _IMPORT_PANE_PATH_PROP.search(app) and _IMPORT_START_CALL.search(import_pane):
        if re.search(
            r"("
            r"droppedPath|dropPath|startPath|importPath|queuedPath|pendingPath"
            r"|\$effect"
            r")",
            import_pane,
        ) and _IMPORT_START_CALL.search(import_pane):
            return True
    return False


def assert_drag_drop_import(crate: Path) -> None:
    """#134: drop local ZIP/mbox → existing importStart + progress; reject URLs.

    Tauri file-drop (onDragDropEvent), not HTML ondrop of remote URLs and not
    fetch. First local path into importStart (auto-detect). Switch to Import
    so the existing progress UI shows. No new folder-of-folders walker.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#134: App.svelte required (window-level drop must reach Import)")
    app = app_path.read_text()
    import_path = crate / "web" / "lib" / "ImportPane.svelte"
    import_pane = import_path.read_text() if import_path.is_file() else ""
    web = _web_logic(crate)
    rust = _tauri_rust_blob(crate)
    blob = web + "\n" + rust
    cleaned = _without_comments(blob)
    caps_path = crate / "capabilities" / "default.json"
    caps = caps_path.read_text() if caps_path.is_file() else ""
    pkg = (crate / "package.json").read_text() if (crate / "package.json").is_file() else ""
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) Tauri drag-drop API — not a raw http fetch, not HTML ondrop alone.
    if "@tauri-apps/api" not in pkg:
        fail("#134: @tauri-apps/api must remain a dependency (onDragDropEvent)")
    if not _TAURI_DRAG_DROP_API.search(cleaned) and not _TAURI_DRAG_DROP_API.search(blob):
        fail(
            "#134: must listen for Tauri file-drop "
            "(getCurrentWebview/Window().onDragDropEvent or on_drag_drop_event), "
            "not a raw http fetch / HTML ondrop of remote URLs"
        )
    api_files = _drop_api_files(crate)
    if not api_files:
        fail(
            "#134: must listen for Tauri file-drop "
            "(getCurrentWebview/Window().onDragDropEvent or on_drag_drop_event)"
        )
    only_import_pane = api_files and all(p.name == "ImportPane.svelte" for p in api_files)
    if only_import_pane and _import_pane_conditionally_mounted(app):
        fail(
            "#134: drop listener must run on any tab "
            "(App / always-mounted helper), not only inside the Import view "
            "(ImportPane unmounts when view !== \"import\")"
        )

    surface = _drop_handler_surface(crate)
    if not surface.strip():
        surface = "\n".join(p.read_text() for p in api_files)

    # 2) Drop branch reads Tauri local paths (payload.paths), not dataTransfer URLs.
    if not _DROP_PATHS.search(surface):
        fail(
            "#134: drop handler must read Tauri local paths "
            "(event.payload.paths) — not HTML dataTransfer of a remote URL"
        )
    if _DATATRANSFER.search(surface) and not _DROP_PATHS.search(surface):
        fail(
            "#134: do not import from HTML dataTransfer URLs; "
            "use Tauri payload.paths (local filesystem only)"
        )
    if not _DROP_EVENT_TYPE.search(surface) and not re.search(
        r"\bpaths\b", surface
    ):
        fail(
            "#134: handle the drop event (payload.type === \"drop\" / "
            "DragDropEvent::Drop), not hover/enter"
        )

    # 3) First local path starts existing import (not only fills the path field).
    if not import_pane.strip():
        fail("#134: ImportPane.svelte required (existing progress UI)")
    if not _drop_starts_import(crate, surface, app, import_pane):
        fail(
            "#134: drop of a local path must call existing importStart "
            "(or ImportPane start / path prop that starts import) — "
            "filling the path field alone is not enough"
        )
    start_win = _windows_around(surface, _IMPORT_START_CALL, before=200, after=240)
    if not start_win.strip():
        start_win = surface
    if _IMPORT_START_CALL.search(surface) and re.search(
        r"kind\s*:\s*[\"']whatsapp[\"']", start_win
    ) and not _IMPORT_START_KIND_AUTO.search(start_win):
        fail(
            "#134: drop must use the picker auto-detect path "
            "(importStart({ path, kind: null })) — not a WhatsApp-only kind"
        )

    # 4) Switch to Import so importProgress / Status running→done is visible.
    if not _VIEW_IMPORT_ASSIGN.search(surface) and not _VIEW_IMPORT_ASSIGN.search(app):
        fail(
            "#134: drop on another tab must set view = \"import\" "
            "so the existing import progress UI is visible"
        )
    if not _VIEW_IMPORT_ASSIGN.search(surface):
        # Assignment exists somewhere in App (⌘4 / nav). Require it on the drop path.
        fail(
            "#134: drop handler must set view = \"import\" "
            "(progress UI is the Import tab; drop may land on People/Search/…)"
        )
    if "importProgress" not in import_pane:
        fail(
            "#134: keep ImportPane importProgress polling "
            "(drop starts the existing progress UI, not a new one)"
        )
    if not re.search(r"progress\.status|Status:", import_pane):
        fail("#134: keep the Import status / progress UI (running → done)")

    # 5) Reject http(s) / URL-scheme drops: show error, do not import.
    if not _drop_rejects_url_scheme(surface):
        fail(
            "#134: drop handler must reject http:// and https:// "
            "(and other URL schemes) — local filesystem paths only"
        )
    if not _SHOW_ERR.search(surface):
        fail(
            "#134: rejected URL drops must show an error "
            "(onError / showErr) and must not call importStart"
        )

    # 6) Bans: fetch of the dropped file, remote URL as import path, new walker.
    if _FETCH_CALL.search(surface) or _XHR.search(surface):
        fail(
            "#134: do not fetch() the dropped file "
            "(no remote URLs as the import path)"
        )
    if re.search(r"importStart\s*\(\s*\{[^}]{0,200}https?://", surface, re.I | re.S):
        fail("#134: importStart path must not be a remote http(s) URL")
    walk_src = surface
    for p in api_files:
        if p.suffix in {".svelte", ".ts", ".js", ".rs"}:
            walk_src += "\n" + p.read_text()
    if _DROP_WALK.search(walk_src) or _DROP_WALK.search(surface):
        fail(
            "#134: do not add a new folder-of-folders walker "
            "(UI5 folder-of-zips via existing importStart auto-detect is OK)"
        )
    if _TAURI_DRAG_DROP_PLUGIN.search(toml) or _TAURI_DRAG_DROP_PLUGIN.search(pkg):
        if "plugin-fs" in toml or "plugin-fs" in pkg or "@tauri-apps/plugin-fs" in web:
            fail(
                "#134: do not add @tauri-apps/plugin-fs / a recursive walk "
                "for drop — pass the local path to existing importStart"
            )
    if _HTTP_CAP.search(caps) or "tauri-plugin-http" in toml:
        fail("#134: no HTTP client capability / tauri-plugin-http (local paths only)")
    if re.search(r"network\.server", caps):
        fail("#134: capabilities must not add network.server")

    # Optional: smallest drag-drop ACL if the generated schema lists one.
    schema_blob = ""
    schemas = crate / "gen" / "schemas"
    if schemas.is_dir():
        for p in schemas.glob("*.json"):
            schema_blob += p.read_text()
    if re.search(r"allow-on-drag-drop-event", schema_blob) and not re.search(
        r"allow-on-drag-drop-event", caps
    ):
        fail(
            "#134: capabilities/default.json must include the smallest "
            "drag-drop permission (core:webview:allow-on-drag-drop-event "
            "or core:window:allow-on-drag-drop-event)"
        )

    # 7) HTML ondrop of remote URLs is not a substitute.
    if _HTML_DROP_ATTR.search(cleaned) and not _TAURI_DRAG_DROP_API.search(cleaned):
        fail(
            "#134: HTML ondrop/ondragover is not enough — "
            "use Tauri onDragDropEvent for local paths"
        )

    # 8) Docs: drop a local ZIP/mbox; no URLs.
    if not dtxt.strip():
        fail("#134: docs/user/app.md required (drop a local ZIP/mbox; no URLs)")
    drop_win = ""
    for m in re.finditer(
        r".{0,160}(?:\bdrop(?:ping|ped)?\b|drag-and-drop|drag and drop).{0,160}",
        dtxt,
        re.I | re.S,
    ):
        drop_win += m.group(0) + "\n"
    if not drop_win.strip():
        fail(
            "#134: docs/user/app.md must say you can drop a local ZIP/mbox "
            "onto the window"
        )
    if not re.search(r"\blocal\b", drop_win, re.I):
        fail("#134: docs/user/app.md must say the drop is a local path (not a URL)")
    if not re.search(r"\bZIP\b|\.zip\b", drop_win, re.I):
        fail("#134: docs/user/app.md must mention dropping a local ZIP")
    if not re.search(r"\bmbox\b", drop_win, re.I):
        fail("#134: docs/user/app.md must mention dropping a local mbox")
    if not re.search(r"URL", drop_win, re.I):
        fail(
            "#134: docs/user/app.md drop line must say no URLs "
            "(local ZIP/mbox only)"
        )
    if not re.search(
        r"("
        r"no URLs"
        r"|not a URL"
        r"|URLs not"
        r"|not URLs"
        r"|never a URL"
        r"|local.{0,40}not.{0,20}URL"
        r")",
        drop_win,
        re.I | re.S,
    ):
        fail("#134: docs/user/app.md must say drop is local ZIP/mbox, no URLs")


# #220 — import progress: Cancel hook + calm done (no thread kill).
# #266 owns enabled Cancel + import_cancel (surgical: this block no
# longer requires disabled / forbids the command / “cannot be stopped”).
_IMPORT_HONEST_COPY = re.compile(
    r"("
    r"cannot stop"
    r"|cannot be stopped"
    r"|no stop"
    r"|cannot be cancelled"
    r"|cannot be canceled"
    r"|not implemented"
    r")",
    re.I,
)
_IMPORT_FAKE_CMD = re.compile(r"\b(?:import_cancel|cancelImport|importCancel)\b")
_IMPORT_THREAD_KILL = re.compile(
    r"("
    r"thread::[^\n]{0,60}\b(?:kill|terminate)\b"
    r"|JoinHandle::[^\n]{0,60}\babort\b"
    r"|\b(?:JoinHandle|join_handle|import_handle)\b[^\n]{0,80}\.abort\s*\("
    r"|\bpthread_kill\b"
    r")"
)
_IMPORT_STATUS_RUNNING = re.compile(
    r"Status[\s\S]{0,160}(?:progress\.status|\brunning\b)",
    re.I,
)
_IMPORT_CONSOLE_PATH = re.compile(
    r"console\.log\s*\((?:[^)]|\n){0,240}(?:\bpath\b|progress\.path|\bprogress\b)",
    re.I,
)
_IMPORT_TOAST_PATH = re.compile(
    r"(?:onToast|toast)\s*\??\s*\((?:[^)]|\n){0,240}(?:\bpath\b|progress\.path)",
    re.I,
)
_IMPORT_PARALLEL = re.compile(
    r"("
    r"parallel[\s_-]*import"
    r"|import[\s_-]*in[\s_-]*parallel"
    r"|concurrent[\s_-]*import"
    r"|data-parallel-import"
    r")",
    re.I,
)
_IMPORT_GC_BTN = re.compile(
    r"("
    r">\s*(?:GC(?:\s+CAS)?|gc_cas|Run GC)\s*<"
    r"|\bgcCas\b"
    r"|\bgc_cas\b"
    r"|background\s+GC"
    r")",
    re.I,
)
_IMPORT_DOCS_PROGRESS = re.compile(
    r"("
    r"progress.{0,40}visible"
    r"|visible.{0,40}progress"
    r"|progress in-window"
    r"|import progress"
    r")",
    re.I | re.S,
)
_IMPORT_DOCS_NO_STOP = re.compile(
    r"("
    r"cannot stop"
    r"|cannot be stopped"
    r"|no stop"
    r"|cannot be cancelled"
    r"|cannot be canceled"
    r"|disabled cancel"
    r"|cancel.{0,80}disabled"
    r"|disabled.{0,80}cancel"
    r")",
    re.I | re.S,
)
_IMPORT_DOCS_QUIET = re.compile(
    r"("
    r"quiet done"
    r"|import done.{0,100}(?:quiet|muted|success)"
    r"|(?:quiet|muted|success).{0,80}import done"
    r")",
    re.I | re.S,
)
_IMPORT_DISABLED = re.compile(
    r"("
    r"(?<![\w-])disabled(?:=\{[^}]*\}|=[\"'][^\"']*[\"'])?(?=[\s/>])"
    r"|aria-disabled\s*=\s*(?:\{true\}|[\"']true[\"'])"
    r")"
)
_IMPORT_DIALOG = re.compile(r"^<(?:Dialog|AlertDialog)\b")
_IMPORT_DESCRIBEDBY = re.compile(
    r"aria-describedby\s*=\s*(?:[\"']([^\"']+)[\"']|\{\s*[\"']([^\"']+)[\"']\s*\})",
    re.I,
)


def _import_describedby_blob(src: str, tag: str) -> str:
    """Text of the element referenced by aria-describedby on the cancel control."""
    m = _IMPORT_DESCRIBEDBY.search(tag)
    if not m:
        return ""
    ident = m.group(1) or m.group(2)
    if not ident:
        return ""
    found = re.search(
        rf"""\bid\s*=\s*(?:["']{re.escape(ident)}["']"""
        rf"""|\{{\s*["']{re.escape(ident)}["']\s*\}})""",
        src,
    )
    if not found:
        return ""
    start = src.rfind("<", 0, found.start() + 1)
    if start < 0:
        start = found.start()
    return src[start : found.end() + 360]


def _import_honest_blob(src: str, tag: str) -> str:
    """Cancel tag + nearby window + described-by target (honest no-stop copy)."""
    return "\n".join(
        (
            tag,
            _status_hook_blob(src, "data-import-cancel"),
            _import_describedby_blob(src, tag),
        )
    )


def assert_import_progress(crate: Path) -> None:
    """#220: import progress — Cancel hook + calm done (no thread kill)."""
    import_path = crate / "web" / "lib" / "ImportPane.svelte"
    import_src = import_path.read_text() if import_path.is_file() else ""

    # 1) data-import-cancel exists in ImportPane.svelte
    if "data-import-cancel" not in import_src:
        fail(
            "#220: data-import-cancel required in ImportPane.svelte "
            "(Cancel while running)"
        )

    rust_path = crate / "src" / "main.rs"
    rust = rust_path.read_text() if rust_path.is_file() else ""
    rust_surf = _without_comments(rust)

    # 2) No thread:: kill / JoinHandle:: abort as “cancel”.
    if _IMPORT_THREAD_KILL.search(rust_surf):
        fail(
            "#220: no thread:: kill / JoinHandle:: abort as cancel "
            "(do not kill the import thread)"
        )

    # 3) Status running still rendered in the import pane.
    if not _IMPORT_STATUS_RUNNING.search(import_src):
        fail("#220: Status running must still be rendered in the import pane")

    # 4) data-import-done still present; no Dialog wrapping done;
    #    no bg-gradient / confetti / celebration on done.
    if "data-import-done" not in import_src:
        fail(
            "#220: keep data-import-done "
            "(quiet counts; no Dialog / bg-gradient / confetti)"
        )
    done_tag = _contrast_surface_tag(import_src, "data-import-done")
    done_at = import_src.find("data-import-done")
    wrap_tags = ([done_tag] if done_tag else []) + _ancestor_tags(
        import_src, done_at, limit=10
    )
    if any(_IMPORT_DIALOG.search(t) for t in wrap_tags):
        fail("#220: data-import-done must not be wrapped in a Dialog")
    done_blob = _status_hook_blob(import_src, "data-import-done")
    if (
        _STATUS_GRADIENT.search(done_blob)
        or _STATUS_CONFETTI.search(done_blob)
        or _STATUS_CELEBRATION.search(_hue_surface(done_blob))
    ):
        fail(
            "#220: data-import-done must not use bg-gradient / confetti / "
            "celebration"
        )

    # 5) No console.log of path; no toast of the import path.
    import_surf = _hue_surface(import_src)
    if _IMPORT_CONSOLE_PATH.search(import_surf):
        fail("#220: do not console.log the import path")
    if _IMPORT_TOAST_PATH.search(import_surf):
        fail("#220: do not toast the import path")

    # 6) No parallel-import UI, no fetch( / HTTP import,
    #    no background GC button on Import.
    if _IMPORT_PARALLEL.search(import_surf):
        fail("#220: no parallel-import UI")
    if _APPEARANCE_FETCH.search(import_surf):
        fail("#220: no fetch( / HTTP import")
    if _IMPORT_GC_BTN.search(import_surf):
        fail("#220: no background GC button on Import")

    # 7) docs/user/app.md: progress visible + quiet done.
    #    (#266 owns “Cancel stops”; do not require “cannot be stopped”.)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    if not dtxt.strip():
        fail(
            "#220: docs/user/app.md required — progress visible + quiet done"
        )
    if not _IMPORT_DOCS_PROGRESS.search(dtxt):
        fail("#220: docs/user/app.md must say import progress is visible")
    if not _IMPORT_DOCS_QUIET.search(dtxt):
        fail("#220: docs/user/app.md must say import done stays quiet")

    # 8) Do not soften #q, sidebar, overlay titlebar, inspector, CSP,
    #     #219 tokens / data-import-done, #218 overlay / no Theme.
    svelte_files = _product_svelte(crate)
    svelte_blob = "\n".join(p.read_text() for p in svelte_files)
    app_path = crate / "web" / "App.svelte"
    app = app_path.read_text() if app_path.is_file() else ""
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    conf = (crate / "tauri.conf.json").read_text()
    css_path = crate / "web" / "app.css"
    css = css_path.read_text() if css_path.is_file() else ""
    light_blob = _contrast_light_blob(css)
    dark_blob = _contrast_dark_blob(css)
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#220: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#220: keep data-people-sidebar (#159 / #212)")
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#220: keep the overlay titlebar (#211)")
    if not re.search(r"\bdata-person-inspector\b", app):
        fail("#220: keep data-person-inspector (#213)")
    if CSP not in conf:
        fail("#220: do not soften tauri CSP")
    if not _css_var(light_blob, _STATUS_WARNING_NAMES) or not _css_var(
        dark_blob, _STATUS_WARNING_NAMES
    ):
        fail("#220: keep #219 --warning / --color-warning in light and dark")
    if "data-import-done" not in svelte_blob:
        fail("#220: keep #219 data-import-done")
    if not _css_var(css, _APPEARANCE_SCRIM_NAMES):
        fail("#220: keep #218 --overlay / --scrim / --lightbox-scrim")
    if _APPEARANCE_THEME_UI.search(svelte_blob) or _APPEARANCE_MENU_LABEL.search(
        svelte_blob
    ):
        fail("#220: keep #218 — no Theme / Appearance menu / data-theme")


# #266 — real import cancel (cooperative flag; Cancel enabled while running).
_IMPORT_CANCEL_CMD = _IMPORT_FAKE_CMD
_IMPORT_CANCEL_UNCOND_DISABLED = re.compile(
    r"("
    r"(?<![\w-])disabled(?:=\{true\}|=[\"']true[\"'])?(?=[\s/>])"
    r"|aria-disabled\s*=\s*(?:\{true\}|[\"']true[\"'])"
    r")"
)
_IMPORT_CANCEL_CLICK = re.compile(r"\b(?:onclick|on:click)\s*=")
_IMPORT_CANCEL_API_CALL = re.compile(
    r"("
    r"\bapi\s*\.\s*importCancel\s*\("
    r"|\bapi\s*\.\s*import_cancel\s*\("
    r"|\bapi\s*\.\s*cancelImport\s*\("
    r"|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']import_cancel[\"']"
    r")"
)
_IMPORT_CANCEL_FLAG = re.compile(
    r"("
    r"\bAtomicBool\b"
    r"|\bImportCancel\b"
    r"|\bcancel\s*:"
    r"|\bis_cancelled\b"
    r"|\bis_canceled\b"
    r")"
)
_IMPORT_TICK_INTERRUPTED = re.compile(
    r"("
    r"""status\s*===\s*["']interrupted["']"""
    r"""|["']interrupted["']\s*===\s*[\w.]*status"""
    r"""|\.includes\s*\(\s*["']interrupted["']"""
    r"""|["']interrupted["']"""
    r")",
)
_IMPORT_DOCS_STOPS = re.compile(
    r"cancel.{0,120}stop",
    re.I | re.S,
)
_IMPORT_SELF_PROBE = re.compile(r"self\s*\.\s*probe\s*\(")
_IMPORT_CANCEL_WORD = re.compile(r"\b(?:Cancelled|is_cancelled|is_canceled)\b")
_IMPORT_STOPS_AFTER_FILE = re.compile(r"Stops after this file")
_IMPORT_AFTER_THIS_FILE = re.compile(r"after this file", re.I)
_IMPORT_CANCEL_OPEN = re.compile(r"\bopen\b", re.I)


def _import_fn_checks_cancel(src: str, name: str) -> bool:
    """`fn name(..., cancel...)` body mentions Cancelled / is_cancelled."""
    if not re.search(rf"fn\s+{re.escape(name)}\s*\([^)]*\bcancel\b", src, re.S):
        return False
    body = _rust_fn_body(src, name)
    return bool(body and _IMPORT_CANCEL_WORD.search(body))


_UPSERT_UPDATE_BLAKE3 = re.compile(
    r"UPDATE\s+sources\b[\s\S]{0,500}\bfile_blake3\b",
    re.I,
)
_UPSERT_SELECT_BLAKE3 = re.compile(r"SELECT\b[^;]{0,200}file_blake3", re.I)
_UPSERT_SELECT_ORIGIN = re.compile(r"SELECT\b[^;]{0,200}origin_path", re.I)


def _upsert_origin_fallback_or_hash_update(upsert: str, abort: str) -> bool:
    """Reuse a hashless sources row: UPDATE file_blake3, or origin_path after a blake3 miss."""
    blob = f"{upsert}\n{abort}"
    if _UPSERT_UPDATE_BLAKE3.search(blob):
        return True
    blake3_sel = _UPSERT_SELECT_BLAKE3.search(upsert)
    if not blake3_sel:
        return False
    for origin_sel in _UPSERT_SELECT_ORIGIN.finditer(upsert):
        if origin_sel.start() <= blake3_sel.start():
            continue
        between = upsert[blake3_sel.end() : origin_sel.start()]
        if "else" not in between:
            return True
    return False


def _wa_media_zip_match_body(wa: str) -> str:
    """`match read_zip_entry_capped(...) { ... }` body (media read, not fn def)."""
    m = re.search(r"match\s+read_zip_entry_capped\s*\(", wa)
    if not m:
        return ""
    paren = wa.find("(", m.start())
    if paren < 0:
        return ""
    close_paren = _match_closer(wa, paren)
    if close_paren < 0:
        return ""
    brace = wa.find("{", close_paren)
    if brace < 0:
        return ""
    close_b = _match_closer(wa, brace)
    if close_b < 0:
        return wa[brace + 1 :]
    return wa[brace + 1 : close_b]


def _import_cancel_struct_docs(model: str) -> str:
    """Rustdoc / attributes immediately above `pub struct ImportCancel`."""
    m = re.search(r"pub struct ImportCancel\b", model)
    if not m:
        return ""
    docs: list[str] = []
    for line in reversed(model[: m.start()].splitlines()):
        s = line.strip()
        if (
            s.startswith("///")
            or s.startswith("//!")
            or s.startswith("//")
            or s.startswith("#[")
            or not s
        ):
            docs.append(line)
            continue
        break
    docs.reverse()
    return "\n".join(docs)


def assert_import_cancel(crate: Path) -> None:
    """#266: cooperative Cancel — enabled while running; in-file abort; sources reuse."""
    root = repo_root()
    import_path = crate / "web" / "lib" / "ImportPane.svelte"
    import_src = import_path.read_text() if import_path.is_file() else ""
    rust_path = crate / "src" / "main.rs"
    rust = rust_path.read_text() if rust_path.is_file() else ""
    api_path = crate / "web" / "lib" / "api.ts"
    api = api_path.read_text() if api_path.is_file() else ""
    rust_surf = _without_comments(rust)
    api_surf = _without_comments(api)

    # 1) import_cancel / importCancel in main.rs AND api.ts (first fail today).
    if not _IMPORT_CANCEL_CMD.search(rust_surf):
        fail(
            "#266: import_cancel (or importCancel) required in "
            "crates/interlace-tauri/src/main.rs"
        )
    if not _IMPORT_CANCEL_CMD.search(api_surf):
        fail(
            "#266: import_cancel (or importCancel) required in "
            "crates/interlace-tauri/web/lib/api.ts"
        )

    # 2) ImportPane click / handler calls that API.
    if "data-import-cancel" not in import_src:
        fail("#266: keep #220 data-import-cancel")
    cancel_tag = _contrast_surface_tag(import_src, "data-import-cancel")
    if not cancel_tag or not _IMPORT_CANCEL_CLICK.search(cancel_tag):
        fail(
            "#266: data-import-cancel must have a click / handler "
            "(onclick / on:click)"
        )
    if not _IMPORT_CANCEL_API_CALL.search(import_src):
        fail(
            "#266: ImportPane must call api.importCancel "
            "(or invoke import_cancel) from the Cancel handler"
        )

    # 3) Cancel is enabled while running (not a bare disabled / {true}).
    if _IMPORT_CANCEL_UNCOND_DISABLED.search(cancel_tag):
        fail(
            "#266: data-import-cancel must be enabled while running "
            "(not a bare disabled / disabled={true}; "
            "disabled={…} only when not running / already cancelling)"
        )

    # 4) Core or Tauri mentions a cancel flag.
    model = (root / "crates" / "interlace-core" / "src" / "model.rs").read_text()
    import_mod = (root / "crates" / "interlace-core" / "src" / "import" / "mod.rs")
    import_txt = import_mod.read_text() if import_mod.is_file() else ""
    ctx_path = root / "crates" / "interlace-core" / "src" / "import" / "context.rs"
    ctx_txt = ctx_path.read_text() if ctx_path.is_file() else ""
    flag_blob = _without_comments(model + "\n" + import_txt + "\n" + ctx_txt + "\n" + rust)
    if not _IMPORT_CANCEL_FLAG.search(flag_blob) and not re.search(
        r"\binterrupted\b", rust_surf
    ):
        fail(
            "#266: core or Tauri must mention a cancel flag "
            "(AtomicBool / ImportCancel / cancel / interrupted)"
        )

    # 5) tick / progress treats interrupted as terminal (not only done/failed).
    tick = _ts_fn_body(import_src, "tick") or _function_body(import_src, "tick")
    if not tick or not _IMPORT_TICK_INTERRUPTED.search(tick):
        fail(
            "#266: tick / progress must treat interrupted "
            "(or failed-on-cancel) as terminal (not only done/failed)"
        )

    # 6) No JoinHandle abort / thread::kill.
    if _IMPORT_THREAD_KILL.search(rust_surf):
        fail(
            "#266: no JoinHandle abort / thread::kill "
            "(cooperative flag only)"
        )

    # 7) docs: Cancel stops the import (not “cannot be stopped”).
    docs = root / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    if not dtxt.strip():
        fail("#266: docs/user/app.md required — Cancel stops the import")
    if _IMPORT_DOCS_NO_STOP.search(dtxt):
        fail(
            "#266: docs/user/app.md must not say Cancel is disabled / "
            "the import cannot be stopped"
        )
    if not _IMPORT_DOCS_STOPS.search(dtxt):
        fail("#266: docs/user/app.md must say Cancel stops the import")

    # 8) WhatsApp import() must not call self.probe( (second full ZIP hash/open).
    wa_path = root / "crates" / "interlace-core" / "src" / "import" / "whatsapp.rs"
    wa = wa_path.read_text() if wa_path.is_file() else ""
    import_body = _rust_fn_body(wa, "import")
    if not import_body.strip():
        fail("#266: crates/interlace-core/src/import/whatsapp.rs fn import required")
    if _IMPORT_SELF_PROBE.search(import_body):
        fail(
            "#266: WhatsApp import() must not call self.probe( "
            "(second full ZIP hash/open)"
        )

    # 9) Cancel on ZIP open / list / hash — not only maybe_commit.
    if not _import_fn_checks_cancel(import_txt, "hash_file"):
        fail(
            "#266: hash_file must check cancel "
            "(Cancelled / is_cancelled), not only maybe_commit"
        )
    if not _import_fn_checks_cancel(wa, "open_zip_cancellable"):
        fail(
            "#266: ZIP open must be cancellable "
            "(open_zip_cancellable + Cancelled / is_cancelled)"
        )
    if not _import_fn_checks_cancel(wa, "list_zip"):
        fail(
            "#266: list_zip must check cancel "
            "(Cancelled / is_cancelled), not only maybe_commit"
        )

    # 10) ImportPane must not promise only “Stops after this file”.
    help_blob = _import_describedby_blob(import_src, cancel_tag)
    pane_cancel = help_blob + "\n" + import_src
    if _IMPORT_STOPS_AFTER_FILE.search(pane_cancel):
        fail(
            "#266: ImportPane must not promise only “Stops after this file”"
        )
    if _IMPORT_AFTER_THIS_FILE.search(help_blob) and not re.search(
        r"\b(?:hash|open|checkpoint)\b", help_blob, re.I
    ):
        fail(
            "#266: ImportPane must not promise only “after this file”"
        )
    if not help_blob.strip() or not _IMPORT_CANCEL_OPEN.search(help_blob):
        fail(
            "#266: ImportPane cancel help must mention ZIP open "
            "(hash / open / checkpoint), not “Stops after this file”"
        )

    # 11) Still no JoinHandle abort / thread::kill (keep #220 / earlier #266).
    if _IMPORT_THREAD_KILL.search(rust_surf):
        fail(
            "#266: no JoinHandle abort / thread::kill "
            "(cooperative flag only)"
        )

    # 12) upsert_source / abort_cancelled: origin_path fallback or UPDATE file_blake3.
    upsert_body = _rust_fn_body(import_txt, "upsert_source")
    abort_body = _rust_fn_body(import_txt, "abort_cancelled")
    if not upsert_body.strip():
        fail("#266: upsert_source required in crates/interlace-core/src/import/mod.rs")
    if not _upsert_origin_fallback_or_hash_update(upsert_body, abort_body):
        fail(
            "#266: upsert_source / abort_cancelled must fall back to "
            "origin_path when blake3 misses, or UPDATE file_blake3 "
            "on the existing row (not a hashless-only insert)"
        )

    # 13) WhatsApp media Err arm near read_zip_entry_capped returns Cancelled.
    media_match = _without_comments(_wa_media_zip_match_body(wa))
    if (
        not media_match.strip()
        or not re.search(r"\bCancelled\b", media_match)
        or not re.search(r"\breturn\b", media_match)
    ):
        fail(
            "#266: WhatsApp media Err arm near read_zip_entry_capped "
            "must return Cancelled (not only ctx.warn / media_read)"
        )

    # 14) ImportCancel docs must not embed #266.
    cancel_docs = _import_cancel_struct_docs(model)
    if "#266" in cancel_docs:
        fail("#266: ImportCancel docs in model.rs must not contain #266")
