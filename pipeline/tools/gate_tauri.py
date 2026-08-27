#!/usr/bin/env python3
"""UI0 + chrome gate for interlace-tauri.

Entry stays `python3 pipeline/tools/gate_tauri.py`. Chrome asserts live in
`pipeline/tools/tauri_gate/` (area modules + scan.py readers). G1–G3 / G5
lock is `assert_gate_tauri_split`. G4 is the rest of this script (npm ci /
build, clippy, deny). Do not add `python3 -m tauri_gate`.

Protected homes: review.py (#128 / #221), contrast.py (#219),
import_doctor.py (#220), motion.py (#222). Move those bodies; do not
rewrite their fail prefixes."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root, run  # noqa: E402
from gate_app_release import assert_app_notarize  # noqa: E402

from tauri_gate.scan import (  # noqa: E402
    CSP,
    _chrome_en_text,
)
from tauri_gate.roster import *  # noqa: E402
from tauri_gate.split_lock import assert_gate_tauri_split  # noqa: E402

def main() -> None:
    root = repo_root()
    crate = root / "crates" / "interlace-tauri"
    toml = (crate / "Cargo.toml").read_text()
    if "publish = false" not in toml:
        fail("interlace-tauri must set publish = false")
    for plug in ("tauri-plugin-http", "tauri-plugin-updater"):
        if plug in toml:
            fail(f"{plug} must not be a dependency")

    ws = (root / "Cargo.toml").read_text()
    if '"crates/interlace-tauri"' not in ws:
        fail("interlace-tauri must be a workspace member")
    dm = ws[ws.find("default-members") : ws.find("[workspace.package]")]
    if "interlace-tauri" in dm:
        fail("interlace-tauri must not be a default-member")

    conf = (crate / "tauri.conf.json").read_text()
    if CSP not in conf:
        fail(f"tauri.conf.json missing exact CSP:\n{CSP}")
    import json

    cfg = json.loads(conf)
    bundle = cfg.get("bundle") or {}
    if bundle.get("active") is not True:
        fail("bundle.active must be true (UI8 unsigned .app/.dmg)")
    targets = bundle.get("targets") or []
    if "app" not in targets or "dmg" not in targets:
        fail("bundle.targets must include app and dmg")
    if bundle.get("createUpdaterArtifacts"):
        fail("createUpdaterArtifacts must stay false (no updater)")
    mac = bundle.get("macOS") or {}
    if mac.get("entitlements") != "Interlace.entitlements":
        fail("bundle.macOS.entitlements must be Interlace.entitlements")
    if mac.get("signingIdentity") != "-":
        fail('signingIdentity must be "-" (ad-hoc / unsigned)')
    icons = bundle.get("icon") or []
    if "icons/icon.icns" not in icons:
        fail("bundle.icon must include icons/icon.icns")
    if not (crate / "icons" / "icon.icns").is_file():
        fail("icons/icon.icns missing")

    ent = (crate / "Interlace.entitlements").read_text()
    if "com.apple.security.app-sandbox" not in ent:
        fail("sandbox entitlement required")
    if "network.server" in ent:
        fail("entitlements must omit network.server")
    # WKWebView will not paint tauri://localhost in a sandbox without this.
    # Measured 2026-08-10: sandbox-only and sandbox+JIT = blank .app;
    # sandbox+network.client shows the UI. Still no HTTP client crate.
    if "network.client" not in ent:
        fail("entitlements must include network.client (WKWebView local UI)")
    if "allow-jit" not in ent:
        fail("entitlements must include cs.allow-jit for WKWebView")

    assert_app_notarize(crate)

    app = (crate / "web" / "App.svelte").read_text()
    if "phones home" not in app or "HTTP" not in app:
        fail("Svelte UI must state no phone-home and no HTTP client")
    if "confirm(" in app:
        fail("App.svelte must not use window.confirm after UI primitives")
    for rel in (
        "web/lib/components/ui/button/button.svelte",
        "web/lib/components/ui/input/input.svelte",
        "web/lib/components/ui/dialog/dialog.svelte",
        "web/lib/components/ui/scroll-area/scroll-area.svelte",
    ):
        if not (crate / rel).is_file():
            fail(f"missing owned primitive {rel}")
    empty = crate / "web" / "lib" / "EmptyState.svelte"
    if not empty.is_file():
        fail("EmptyState.svelte required for UI empty/loading copy")
    en_chrome = app + "\n" + _chrome_en_text(crate)
    if "Opening last archive" not in en_chrome:
        fail("boot screen must say Opening last archive (no blank flash)")
    doctor = crate / "web" / "lib" / "DoctorPane.svelte"
    if not doctor.is_file():
        fail("DoctorPane.svelte required for UI7")
    dtxt = doctor.read_text()
    doctor_en = dtxt + "\n" + _chrome_en_text(crate)
    if "Not encrypted at rest" not in doctor_en or "FileVault" not in doctor_en:
        fail("Doctor pane must say not encrypted at rest; FileVault is encryption")
    if "database is encrypted" in dtxt or "your data is encrypted" in dtxt.lower():
        fail("UI must not claim the DB is encrypted at rest")
    if "doctorRun" not in dtxt:
        fail("Doctor pane must call doctorRun (not only CLI copy)")
    if "data-cloud-warning" not in app:
        fail("App.svelte must show a persistent cloud-path banner")
    if "UI7 will run doctor" in app:
        fail("placeholder UI7 CLI-only copy must be gone")
    assert_chat_bubbles(crate)
    assert_day_separators(crate)
    assert_local_tz_display(crate)
    assert_timeline_latest(crate)
    assert_conversation_switcher(crate)
    assert_timeline_platform_chips(crate)
    assert_timeline_kind_filter(crate)
    assert_gmail_timeline_rows(crate)
    assert_people_sidebar_no_x_scroll(crate)
    assert_people_filter_identity(crate)
    assert_people_list_lock(crate)
    assert_boot_spinner(crate)
    assert_photo_lightbox(crate)
    assert_voice_note_player(crate)
    assert_voice_note_seek(crate)
    assert_cas_video_pdf(crate)
    assert_bubble_linkify(crate)
    assert_bubble_search(crate)
    assert_reveal_archive(crate)
    assert_first_run(crate)
    assert_font_density(crate)
    assert_reopen_last_session(crate)
    assert_persist_window_frame(crate)
    assert_light_chrome(crate)
    assert_chrome_locale_panes(crate)
    assert_gate_tauri_split(crate)
    assert_virtualized_timeline(crate)
    assert_variable_height_timeline(crate)
    assert_search_platform_select(crate)
    assert_search_conversation_kind(crate)
    assert_search_person_picker(crate)
    assert_search_jump_to_message(crate)
    assert_search_attachment_filter(crate)
    assert_search_safe_highlight(crate)
    assert_search_filters_secondary(crate)
    assert_search_hit_density(crate)
    assert_review_identifiers(crate)
    assert_window_title(crate)
    assert_macos_menu(crate)
    assert_chrome_locale(crate)
    assert_keyboard_map(crate)
    assert_chrome_search_field(crate)
    assert_search_as_you_type(crate)
    assert_custom_titlebar(crate)
    assert_people_sidebar_collapse(crate)
    assert_person_inspector(crate)
    assert_keyboard_list_arrows(crate)
    assert_command_palette(crate)
    assert_command_palette_people_cap(crate)
    assert_command_palette_field_keys(crate)
    assert_command_palette_clipboard(crate)
    assert_focus_aria_audit(crate)
    assert_contrast_tokens(crate)
    assert_appearance_os(crate)
    assert_status_tokens(crate)
    assert_import_progress(crate)
    assert_import_cancel(crate)
    assert_review_chrome(crate)
    assert_sidebar_undo_chrome(crate)
    assert_motion(crate)
    assert_a11y_listbox_focus_motion(crate)
    assert_human_time_people(crate)
    assert_drag_drop_import(crate)
    assert_copy_reveal_cas(crate)
    assert_defer_doctor_cas(crate)
    assert_design_tokens(crate)
    assert_typography(crate)
    assert_lucide_icons(crate)
    assert_owned_primitives(crate)
    assert_empty_next_action(crate)
    assert_loading_skeletons(crate)
    assert_timeline_append_skeleton_guard(crate)
    assert_inflight_audible_status(crate)
    assert_recoverable_toasts(crate)
    assert_partial_pane_errors(crate)
    assert_partial_retry_generation(crate)
    assert_timeline_grouped_runs(crate)
    assert_timeline_bubble_hierarchy(crate)
    assert_timeline_attach_slot(crate)
    assert_product_split(crate)
    assert_recent_archives(crate)
    assert_recent_archives_fold(crate)
    assert_switch_archive(crate)
    assert_switch_archive_fold(crate)
    cas = (crate / "web" / "lib" / "CasAttach.svelte").read_text()
    if "casDataUrl" not in cas:
        fail("CAS viewer must load bytes via casDataUrl (data: URL; Vite cannot fetch cas://)")
    if "http://" in cas or "https://" in cas:
        fail("CAS viewer must not use remote URLs")
    if "protocol-asset" in toml or "dangerousRemoteDomainIpcAccess" in conf:
        fail("must not enable remote asset IPC")
    if (crate / "ui" / "app.js").is_file():
        fail("vanilla ui/app.js must be gone after UI-FE")
    if not (crate / "package-lock.json").is_file():
        fail("package-lock.json must be committed")
    pkg = (crate / "package.json").read_text()
    if "bits-ui" not in pkg:
        fail("bits-ui must be a local dependency (no CDN theme)")
    vite = (crate / "vite.config.ts").read_text()
    if 'base: "./"' not in vite and "base: './'" not in vite:
        fail("vite.config.ts must set base: './' so the .app loads JS")
    if "tauri:build" not in pkg:
        fail("package.json must expose tauri:build")

    wf = root / ".github" / "workflows" / "app-release.yml"
    if not wf.is_file():
        fail("app-release.yml missing (UI8 app-v* tags)")
    wtxt = wf.read_text()
    if "app-v*" not in wtxt:
        fail("app-release.yml must trigger on app-v* tags only")
    if "cargo publish" in wtxt or "CARGO_REGISTRY_TOKEN" in wtxt:
        fail("app-release.yml must not publish crates (D3)")
    if "tauri-plugin-updater" in wtxt or "plugin-updater" in wtxt:
        fail("app-release.yml must not install an updater")
    pub = (root / ".github" / "workflows" / "publish.yml").read_text()
    if "tauri:build" in pub or "bundle/dmg" in pub or "Interlace.app" in pub:
        fail("publish.yml is crates.io v* only; do not attach the .dmg there")

    npm = run(
        ["npm", "ci"],
        cwd=crate,
        check=False,
    )
    if npm.returncode != 0:
        fail(npm.stderr or npm.stdout)
    built = run(["npm", "run", "build"], cwd=crate, check=False)
    if built.returncode != 0:
        fail(built.stderr or built.stdout)
    dist = (crate / "dist" / "index.html").read_text()
    if "cdn." in dist or "unpkg.com" in dist:
        fail("production bundle must not load a CDN")
    if 'src="/assets/' in dist or "href=\"/assets/" in dist:
        fail("dist/index.html must use relative asset URLs (vite base ./); absolute /assets blanks the .app")
    if "connect-src 'none'" in conf:
        fail("connect-src 'none' blocks Tauri IPC and blanks the bundled .app")

    chk = run(["cargo", "check", "-p", "interlace-tauri"], cwd=root, check=False)
    if chk.returncode != 0:
        fail(chk.stderr or chk.stdout)

    clip = run(
        ["cargo", "clippy", "-p", "interlace-tauri", "--", "-D", "warnings"],
        cwd=root,
        check=False,
    )
    if clip.returncode != 0:
        fail(clip.stderr or clip.stdout)

    for kind in ("bans", "licenses"):
        d = run(
            [
                "cargo",
                "deny",
                "--manifest-path",
                str(crate / "Cargo.toml"),
                "check",
                kind,
            ],
            cwd=root,
            check=False,
        )
        if d.returncode != 0:
            fail(f"cargo deny check {kind} interlace-tauri failed\n{d.stdout}\n{d.stderr}")

    for name in ("reqwest", "hyper"):
        t = run(
            [
                "cargo",
                "tree",
                "-p",
                "interlace-tauri",
                "-i",
                name,
                "--target",
                "aarch64-apple-darwin",
            ],
            cwd=root,
            check=False,
        )
        out = (t.stdout or "") + (t.stderr or "")
        if "warning: nothing to print" not in out and f"{name} v" in out:
            fail(f"{name} is in the macOS tauri graph\n{out}")

    print("gate_tauri ok")


if __name__ == "__main__":
    main()
