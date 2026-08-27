"""Import drag-drop / progress / cancel chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.import_doctor_drop import *
from tauri_gate.import_doctor_cancel import *


def assert_drag_drop_import(crate: Path) -> None:
    """#134: drop local ZIP/mbox → existing importStart + progress; reject URLs.

    Tauri file-drop (onDragDropEvent), not HTML ondrop of remote URLs and not
    fetch. First local path into importStart (auto-detect). Switch to Import
    so the existing progress UI shows. No new folder-of-folders walker.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#134: App.svelte required (window-level drop must reach Import)")
    app = _web_logic(crate)
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
    rust = _tauri_rust_blob(crate) if rust_path.is_file() else ""
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
    app = _web_logic(crate) if app_path.is_file() else ""
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = _search_pane_blob(crate) if search_path.is_file() else ""
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

from tauri_gate.import_doctor_more import assert_import_cancel
