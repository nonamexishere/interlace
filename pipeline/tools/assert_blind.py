#!/usr/bin/env python3
"""Blindness: IN.md and tests must not reference impl paths. api/*.rs is allowed."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root  # noqa: E402

FORBIDDEN = re.compile(
    r"crates/interlace-core/src/|"
    r"include_str!\s*\(\s*\"[^\"]*src/(import/whatsapp|identity/resolve|search)\.rs|"
    r"(?<![\w/])whatsapp\.rs|(?<![\w/])gmail\.rs|(?<![\w/])resolve\.rs|(?<![\w/])search\.rs",
    re.I,
)


def scan(path: Path) -> list[str]:
    hits = []
    text = path.read_text(errors="replace")
    for i, line in enumerate(text.splitlines(), 1):
        if "api/" in line and "crates/interlace-core/src" not in line:
            continue
        if FORBIDDEN.search(line):
            hits.append(f"{path}:{i}:{line.strip()}")
    return hits


def main() -> None:
    root = repo_root()
    paths = [Path(p) for p in sys.argv[1:]]
    if not paths:
        default = root / "pipeline" / "stages" / "03-test-author" / "IN.md"
        paths = [default]
        tests = root / "crates" / "interlace-core" / "tests"
        if tests.is_dir():
            paths.extend(tests.rglob("*.rs"))
    hits: list[str] = []
    scanned = 0
    for p in paths:
        if not p.is_file():
            continue
        scanned += 1
        hits.extend(scan(p))
    if hits:
        fail("blindness violated:\n" + "\n".join(hits))
    print(f"assert_blind ok ({scanned} files)")


if __name__ == "__main__":
    main()
