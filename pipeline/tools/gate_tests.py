#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root, run  # noqa: E402
from tauri_gate.product_split import assert_product_split  # noqa: E402

MUST = [
    "CAS1", "CAS2", "CAS3",
    "W1", "W2", "W3", "W4",
    "M1", "M2", "M3", "C1",
    "I1", "I2", "I3", "I4", "I5", "I6", "I6b",
    "S1", "S2", "S3",
]


def main() -> None:
    root = repo_root()
    assert_product_split(root / "crates" / "interlace-tauri")
    plan = root / "crates" / "interlace-core" / "test_plan.json"
    if not plan.is_file():
        plan = root / "pipeline" / "stages" / "03-test-author" / "test_plan.json"
    if not plan.is_file():
        fail("missing test_plan.json")
    schema = root / "pipeline" / "contracts" / "test_plan.schema.json"
    chk = run(
        [sys.executable, str(Path(__file__).with_name("check_schema.py")), str(schema), str(plan)],
        cwd=root,
        check=False,
    )
    if chk.returncode != 0:
        fail(chk.stderr or chk.stdout)
    data = json.loads(plan.read_text())
    have = {c["id"] for c in data["cases"]}
    missing = [i for i in MUST if i not in have]
    if missing:
        fail(f"test_plan missing IDs: {missing}")
    todo = run(
        [sys.executable, str(Path(__file__).with_name("assert_no_todo.py")), "crates/interlace-core/tests"],
        cwd=root,
        check=False,
    )
    if todo.returncode != 0:
        fail(todo.stderr or todo.stdout)
    t = run(["cargo", "test", "-p", "interlace-core", "--tests", "--no-run"], cwd=root, check=False)
    if t.returncode != 0:
        fail(t.stderr or t.stdout)
    print("gate_tests ok")


if __name__ == "__main__":
    main()
