#!/usr/bin/env python3
"""UI8: built Interlace.app keeps sandbox, allows WKWebView client, omits server."""

from __future__ import annotations

import plistlib
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root  # noqa: E402


def main() -> None:
    root = repo_root()
    bundle_dir = root / "target" / "release" / "bundle" / "macos"
    apps = sorted(bundle_dir.glob("*.app")) if bundle_dir.is_dir() else []
    if not apps:
        fail(f"no .app under {bundle_dir} (run npm run tauri:build first)")
    app = apps[0]
    exe = app / "Contents" / "MacOS" / "interlace-app"
    if not exe.is_file():
        # productName may name the binary Interlace
        macos = app / "Contents" / "MacOS"
        bins = [p for p in macos.iterdir() if p.is_file()] if macos.is_dir() else []
        if not bins:
            fail(f"no MacOS binary in {app}")
        exe = bins[0]

    proc = subprocess.run(
        ["codesign", "-d", "--entitlements", ":-", str(exe)],
        check=False,
        capture_output=True,
    )
    blob = proc.stdout or b""
    # codesign prints a warning on stderr and XML on stdout
    if proc.returncode != 0 and not blob.strip().startswith(b"<?xml"):
        fail(
            f"codesign -d --entitlements failed for {exe}\n"
            f"{proc.stderr.decode('utf-8', 'replace')}"
        )
    xml = blob[blob.find(b"<?xml") :]
    if not xml:
        fail(f"no entitlements XML on {exe}")
    data = plistlib.loads(xml)
    if not data.get("com.apple.security.app-sandbox"):
        fail("built app lost app-sandbox")
    if data.get("com.apple.security.network.server"):
        fail("built app must not have network.server")
    if not data.get("com.apple.security.network.client"):
        fail("built app must have network.client (WKWebView; else blank window)")
    print(f"gate_app_bundle ok ({app.name})")


if __name__ == "__main__":
    main()
