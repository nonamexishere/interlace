#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root, run  # noqa: E402

NAMES = [
    "NewMessage",
    "PersistOutcome",
    "persist_labels",
    "resolve_run",
    "search",
    "open_archive",
    "run_import",
    "person_merge",
    "person_undo",
    "person_unlink",
    "review_resolve",
    "person_timeline",
]


def main() -> None:
    root = repo_root()
    r = run(["cargo", "check", "-p", "interlace-core"], cwd=root, check=False)
    if r.returncode != 0:
        fail(r.stderr)
    blob = ""
    src = root / "crates" / "interlace-core" / "src"
    if not src.is_dir():
        fail("missing core src")
    for p in src.rglob("*.rs"):
        blob += p.read_text(errors="replace") + "\n"
    missing = [n for n in NAMES if n not in blob]
    if missing:
        fail(f"public API names missing: {missing}")
    print("gate_api ok")


if __name__ == "__main__":
    main()
