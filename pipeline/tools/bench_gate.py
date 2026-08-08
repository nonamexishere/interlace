#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: bench_gate.py OUT.json")
    data = json.loads(Path(sys.argv[1]).read_text())
    p95 = data.get("p95_ms")
    if p95 is None:
        fail("OUT.json missing p95_ms")
    mode = os.environ.get("INTERLACE_BENCH", "PR")
    limit = 50.0 if mode == "PR" else 200.0
    if float(p95) > limit:
        fail(f"p95_ms {p95} > {limit} (mode={mode})")
    print(f"bench_gate ok p95={p95} mode={mode}")


if __name__ == "__main__":
    main()
