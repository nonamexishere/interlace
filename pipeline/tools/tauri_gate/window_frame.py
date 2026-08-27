"""#306 — persist window size + position (native sibling file).

Approach B: custom Rust under session::config_dir() (not config.toml /
last-archive.bookmark). Translate-only work_area clamp. Do not persist
maximized / fullscreen. Not tauri-plugin-window-state. Not App.svelte
localStorage for the frame.

PR #324 review fold: save_window_frame returns early when
is_maximized() / is_fullscreen() is true (no maximized field, no
set_maximized / set_fullscreen). #306-rerun: on_window_event saves
from Moved / Resized again (debounced + atomic temp/rename write)
so a tauri:dev rerun keeps the new frame."""
from __future__ import annotations

from tauri_gate.window_frame_save import *
from tauri_gate.window_frame_restore import *


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
