#!/usr/bin/env python3
"""Fail if todo! or unimplemented! appears under PATH (tests)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root  # noqa: E402

NEEDLES = ("todo!", "unimplemented!")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: assert_no_todo.py PATH")
    root = repo_root()
    target = (root / sys.argv[1]).resolve()
    if not target.exists():
        print(f"assert_no_todo: {target} missing (ok until tests exist)")
        return
    hits: list[str] = []
    files = [target] if target.is_file() else list(target.rglob("*.rs"))
    for f in files:
        text = f.read_text(errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            if any(n in line for n in NEEDLES):
                hits.append(f"{f}:{i}:{line.strip()}")
    if hits:
        fail("todo!/unimplemented! in tests:\n" + "\n".join(hits))
    print(f"assert_no_todo ok ({len(files)} files)")


if __name__ == "__main__":
    main()
