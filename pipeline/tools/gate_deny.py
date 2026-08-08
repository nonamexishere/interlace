#!/usr/bin/env python3
"""deny bans+licenses on three pkgs + hash lock + no reqwest/hyper/tokio."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root, run  # noqa: E402

PKGS = ("interlace-core", "interlace", "interlace-cli")


def main() -> None:
    root = repo_root()
    lock = run([sys.executable, str(Path(__file__).with_name("deny_toml_lock.py"))], cwd=root, check=False)
    if lock.returncode != 0:
        fail(lock.stderr or lock.stdout)
    for pkg in PKGS:
        manifest = root / "crates" / pkg / "Cargo.toml"
        for kind in ("bans", "licenses"):
            r = run(
                ["cargo", "deny", "--manifest-path", str(manifest), "check", kind],
                cwd=root,
                check=False,
            )
            if r.returncode != 0:
                fail(f"cargo deny check {kind} {pkg} failed\n{r.stdout}\n{r.stderr}")
    noc = run(
        [sys.executable, str(Path(__file__).with_name("assert_no_crate.py")), "reqwest", "hyper", "tokio"],
        cwd=root,
        check=False,
    )
    if noc.returncode != 0:
        fail(noc.stderr or noc.stdout)
    print("gate_deny ok")


if __name__ == "__main__":
    main()
