#!/usr/bin/env python3
"""Each --must ID must appear in a non-ignored test unless APPROVED_GAPS lists it."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--must", required=True, help="comma-separated IDs")
    args = ap.parse_args()
    ids = [x.strip() for x in args.must.split(",") if x.strip()]
    root = repo_root()
    tests = root / "crates" / "interlace-core" / "tests"
    gaps_file = root / "pipeline" / "stages" / "10-human-gate" / "APPROVED_GAPS"
    approved: set[str] = set()
    if gaps_file.is_file():
        approved = {l.strip() for l in gaps_file.read_text().splitlines() if l.strip() and not l.startswith("#")}
    if not tests.exists():
        missing = [i for i in ids if i not in approved]
        if missing:
            fail(f"no tests dir; missing must-IDs: {missing}")
        print("assert_matrix_not_ignored: approved gaps only")
        return
    blob = "\n".join(p.read_text(errors="replace") for p in tests.rglob("*.rs"))
    missing = []
    ignored = []
    for i in ids:
        if i in approved:
            continue
        if not re.search(rf"\b{re.escape(i)}\b", blob):
            missing.append(i)
            continue
        if re.search(rf"#\[ignore[^\]]*\][^\n]*\n[^\n]*{re.escape(i)}", blob) or re.search(
            rf"#\[ignore[^\]]*\][^\n]*{re.escape(i)}", blob
        ):
            ignored.append(i)
    if missing or ignored:
        fail(f"must-ID missing={missing} ignored={ignored}")
    print("assert_matrix_not_ignored ok:", ",".join(ids))


if __name__ == "__main__":
    main()
