#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root, run  # noqa: E402


def main() -> None:
    root = repo_root()
    t = run(["cargo", "test", "-p", "interlace-fixtures"], cwd=root, check=False)
    if t.returncode != 0:
        fail(t.stderr or t.stdout)
    loc = run(
        [sys.executable, str(Path(__file__).with_name("locale_pack_lint.py"))],
        cwd=root,
        check=False,
    )
    if loc.returncode != 0:
        fail(loc.stderr or loc.stdout)
    print("gate_fixtures ok")


if __name__ == "__main__":
    main()
