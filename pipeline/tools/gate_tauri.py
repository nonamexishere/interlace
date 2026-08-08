#!/usr/bin/env python3
"""UI0: unpublished tauri shell, macOS deny exception, CSP, no network entitlement."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root, run  # noqa: E402

CSP = (
    "default-src 'self'; img-src 'self' asset: data:; style-src 'self' "
    "'unsafe-inline'; connect-src 'none'; frame-src 'none'; font-src 'self'"
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

    ent = (crate / "Interlace.entitlements").read_text()
    for bad in ("network.client", "network.server"):
        if bad in ent:
            fail(f"entitlements must omit {bad}")
    if "com.apple.security.app-sandbox" not in ent:
        fail("sandbox entitlement required")

    app = (crate / "web" / "App.svelte").read_text()
    if "phones home" not in app or "HTTP" not in app:
        fail("Svelte UI must state no phone-home and no HTTP client")
    if (crate / "ui" / "app.js").is_file():
        fail("vanilla ui/app.js must be gone after UI-FE")
    if not (crate / "package-lock.json").is_file():
        fail("package-lock.json must be committed")

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
