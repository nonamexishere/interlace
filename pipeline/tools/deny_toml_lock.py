#!/usr/bin/env python3
"""SHA-256 of sorted [bans].deny crate names must match pipeline/testdata/deny_bans.sha256."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root  # noqa: E402


def banned_names(deny_toml: Path) -> list[str]:
    text = deny_toml.read_text()
    # crude but stable: crate = "name" inside [bans] deny tables
    names = re.findall(r'^\s*\{\s*crate\s*=\s*"([^"]+)"', text, flags=re.M)
    if not names:
        fail("no banned crates found in deny.toml")
    return sorted(set(names))


def main() -> None:
    root = repo_root()
    deny = root / "deny.toml"
    lock = root / "pipeline" / "testdata" / "deny_bans.sha256"
    listing = root / "pipeline" / "testdata" / "deny_bans.txt"
    if not deny.is_file():
        fail(f"missing {deny}")
    if not lock.is_file():
        fail(f"missing {lock}")
    names = banned_names(deny)
    blob = "\n".join(names) + "\n"
    digest = hashlib.sha256(blob.encode()).hexdigest().strip()
    expected = lock.read_text().strip()
    if listing.read_text() != blob:
        fail("pipeline/testdata/deny_bans.txt is out of date vs deny.toml")
    if digest != expected:
        fail(f"deny ban hash mismatch: got {digest} want {expected}\nnames:\n{blob}")
    print(f"deny_toml_lock ok ({len(names)} crates, {digest[:12]}…)")


if __name__ == "__main__":
    main()
