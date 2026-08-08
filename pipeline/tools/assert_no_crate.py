#!/usr/bin/env python3
"""Fail if cargo tree -p interlace-core -i NAME succeeds for any NAME."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root, run  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        fail("usage: assert_no_crate.py NAME [NAME...]")
    root = repo_root()
    for name in sys.argv[1:]:
        r = run(
            ["cargo", "tree", "-p", "interlace-core", "-i", name],
            cwd=root,
            check=False,
        )
        if r.returncode == 0:
            fail(f"forbidden crate present: {name}\n{r.stdout}")
    print("assert_no_crate ok:", " ".join(sys.argv[1:]))


if __name__ == "__main__":
    main()
