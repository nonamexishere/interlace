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
    base = run(
        ["git", "merge-base", "HEAD", "origin/master"],
        cwd=root,
        check=False,
    )
    if base.returncode != 0 or not base.stdout.strip():
        base_ref = "HEAD"
    else:
        base_ref = base.stdout.strip()
    diff = run(
        ["git", "diff", "--name-only", base_ref, "--", "crates/interlace-core/tests"],
        cwd=root,
        check=False,
    )
    names = [l for l in diff.stdout.splitlines() if l.strip()]
    # unstaged vs HEAD also counts for impl-in-progress
    dirty = run(
        ["git", "diff", "--name-only", "--", "crates/interlace-core/tests"],
        cwd=root,
        check=False,
    )
    names += [l for l in dirty.stdout.splitlines() if l.strip()]
    names = sorted(set(names))
    if names:
        fail("tests edited by impl:\n" + "\n".join(names))
    print("assert_no_test_edits ok")


if __name__ == "__main__":
    main()
