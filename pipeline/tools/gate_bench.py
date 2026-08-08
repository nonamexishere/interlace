#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root, run  # noqa: E402


def main() -> None:
    root = repo_root()
    out = root / "pipeline" / "stages" / "07-bench" / "OUT.json"
    if not out.is_file():
        fail(f"missing {out} (lands with PR11)")
    r = run(
        [sys.executable, str(Path(__file__).with_name("bench_gate.py")), str(out)],
        cwd=root,
        check=False,
    )
    if r.returncode != 0:
        fail(r.stderr or r.stdout)
    print("gate_bench ok")


if __name__ == "__main__":
    main()
