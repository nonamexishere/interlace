#!/usr/bin/env python3
"""UI0: unpublished tauri shell, macOS deny exception, CSP, no network entitlement."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root, run  # noqa: E402

# IPC-only connect-src (no general http/https). 'none' blanks the .app (#107).
CSP = (
    "default-src 'self'; img-src 'self' asset: data: cas:; media-src 'self' cas: data:; "
    "style-src 'self' 'unsafe-inline'; "
    "connect-src ipc: http://ipc.localhost https://ipc.localhost; "
    "frame-src 'none'; font-src 'self'"
)


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
    if "Opening last archive" not in app:
        fail("boot screen must say Opening last archive (no blank flash)")
    doctor = crate / "web" / "lib" / "DoctorPane.svelte"
    if not doctor.is_file():
        fail("DoctorPane.svelte required for UI7")
    dtxt = doctor.read_text()
    if "Not encrypted at rest" not in dtxt or "FileVault" not in dtxt:
        fail("Doctor pane must say not encrypted at rest; FileVault is encryption")
    if "database is encrypted" in dtxt or "your data is encrypted" in dtxt.lower():
        fail("UI must not claim the DB is encrypted at rest")
    if "doctorRun" not in dtxt:
        fail("Doctor pane must call doctorRun (not only CLI copy)")
    if "data-cloud-warning" not in app:
        fail("App.svelte must show a persistent cloud-path banner")
    if "UI7 will run doctor" in app:
        fail("placeholder UI7 CLI-only copy must be gone")
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
