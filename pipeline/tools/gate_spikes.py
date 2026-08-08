#!/usr/bin/env python3
"""Spike OUT.json: schema, blocked!=true, spike 3 pass, spike 1 fail-open with caveats."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root, run  # noqa: E402


def main() -> None:
    root = repo_root()
    out = root / "pipeline" / "stages" / "01-spikes" / "OUT.json"
    schema = root / "pipeline" / "contracts" / "spike_report.schema.json"
    if not out.is_file():
        fail(f"missing {out}")
    chk = run(
        [sys.executable, str(Path(__file__).with_name("check_schema.py")), str(schema), str(out)],
        cwd=root,
        check=False,
    )
    if chk.returncode != 0:
        fail(chk.stderr or chk.stdout)
    data = json.loads(out.read_text())
    if data.get("blocked") is True:
        fail("spikes blocked=true")
    s3 = data["spikes"]["3"]
    if s3.get("pass") is not True:
        fail("spike 3 must pass (fail-closed)")
    s1 = data["spikes"]["1"]
    if s1.get("pass") is not True and not s1.get("caveats"):
        fail("spike 1 fail-open requires non-empty caveats[]")
    for n in ("1", "2", "3", "4"):
        report = root / "pipeline" / "stages" / "01-spikes" / "reports" / f"spike-{n}.md"
        if not report.is_file():
            fail(f"missing {report}")
    print("gate_spikes ok")


if __name__ == "__main__":
    main()
