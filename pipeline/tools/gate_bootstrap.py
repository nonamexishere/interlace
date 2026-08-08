#!/usr/bin/env python3
"""Workspace exists, 0.0.1 versions, cargo check core, deny.toml lock."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root, run  # noqa: E402


def pkg_version(toml: Path) -> str:
    text = toml.read_text()
    if "version.workspace = true" in text:
        root = repo_root() / "Cargo.toml"
        m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', root.read_text())
        if not m:
            fail(f"no workspace version in {root}")
        return m.group(1)
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    if not m:
        fail(f"no version in {toml}")
    return m.group(1)


def main() -> None:
    root = repo_root()
    ws = root / "Cargo.toml"
    if "[workspace]" not in ws.read_text():
        fail("root Cargo.toml is not a workspace")
    for name in ("interlace", "interlace-core", "interlace-cli"):
        p = root / "crates" / name / "Cargo.toml"
        if not p.is_file():
            fail(f"missing {p}")
        v = pkg_version(p)
        if v != "0.0.1":
            fail(f"{p} version is {v}, want 0.0.1")
    if not (root / "deny.toml").is_file():
        fail("missing deny.toml")
    r = run(["cargo", "check", "-p", "interlace-core"], cwd=root, check=False)
    if r.returncode != 0:
        fail(f"cargo check -p interlace-core failed\n{r.stderr}")
    lock = run([sys.executable, str(Path(__file__).with_name("deny_toml_lock.py"))], cwd=root, check=False)
    if lock.returncode != 0:
        fail(lock.stderr or lock.stdout)
    print("gate_bootstrap ok")


if __name__ == "__main__":
    main()
