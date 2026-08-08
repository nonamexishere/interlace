"""Shared helpers for pipeline gates. Stdlib only."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "Cargo.toml").is_file() and (p / "crates").is_dir():
            return p
    print("error: cannot find workspace root", file=sys.stderr)
    sys.exit(1)


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd or repo_root(),
        text=True,
        capture_output=True,
        check=check,
    )


def fail(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def ok(msg: str) -> None:
    print(msg)
    sys.exit(0)
