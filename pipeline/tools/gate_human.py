#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root  # noqa: E402


def main() -> None:
    p = repo_root() / "pipeline" / "stages" / "10-human-gate" / "APPROVED"
    if not p.is_file():
        fail(f"missing {p}")
    print("gate_human ok")


if __name__ == "__main__":
    main()
