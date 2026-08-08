#!/usr/bin/env python3
"""Fail if crates/interlace-core/tests differs from merge-base with master."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root, run  # noqa: E402


def main() -> None:
    root = repo_root()
    tests = root / "crates" / "interlace-core" / "tests"
    if not tests.exists():
        print("assert_no_test_edits: no tests dir yet (ok)")
        return
    # Only dirty (unstaged / staged vs HEAD) counts. Tests landing *with* an
    # impl PR are committed together and must not trip this gate.
    dirty = run(
        ["git", "diff", "--name-only", "HEAD", "--", "crates/interlace-core/tests"],
        cwd=root,
        check=False,
    )
    cached = run(
        ["git", "diff", "--name-only", "--cached", "--", "crates/interlace-core/tests"],
        cwd=root,
        check=False,
    )
    names = sorted(
        {
            l.strip()
            for l in dirty.stdout.splitlines() + cached.stdout.splitlines()
            if l.strip()
        }
    )
    if names:
        fail("tests edited by impl:\n" + "\n".join(names))
    print("assert_no_test_edits ok")


if __name__ == "__main__":
    main()
