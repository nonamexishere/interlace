#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root, run  # noqa: E402


def main() -> None:
    root = repo_root()
    t = run(
        [
            "cargo",
            "test",
            "--workspace",
            "--exclude",
            "interlace-tauri",
            "--exclude",
            "interlace-fixtures",
        ],
        cwd=root,
        check=False,
    )
    if t.returncode != 0:
        fail(t.stderr or t.stdout)
    clip = run(
        [
            "cargo",
            "clippy",
            "--workspace",
            "--exclude",
            "interlace-tauri",
            "--exclude",
            "interlace-fixtures",
            "--",
            "-D",
            "warnings",
        ],
        cwd=root,
        check=False,
    )
    if clip.returncode != 0:
        fail(clip.stderr or clip.stdout)
    help_ = run(["cargo", "run", "-p", "interlace", "--", "--help"], cwd=root, check=False)
    if help_.returncode != 0:
        fail(f"interlace --help failed\n{help_.stderr}")
    text = (help_.stdout or "") + (help_.stderr or "")
    for w in ("init", "import", "search", "person", "review", "doctor"):
        if w not in text:
            fail(f"interlace --help missing {w}")
    print("gate_cli ok")


if __name__ == "__main__":
    main()
