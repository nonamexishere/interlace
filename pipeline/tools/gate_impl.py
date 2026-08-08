#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root, run  # noqa: E402

STAGE_FILTER = {
    "05a": "cas",
    "05b": "whatsapp",
    "05c": "gmail",
    "05d": "identity",
    "05e": "search",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--must", required=True)
    args = ap.parse_args()
    root = repo_root()
    filt = STAGE_FILTER.get(args.stage, args.stage)
    t = run(["cargo", "test", "-p", "interlace-core", filt], cwd=root, check=False)
    if t.returncode != 0:
        fail(f"cargo test failed\n{t.stdout}\n{t.stderr}")
    clip = run(
        ["cargo", "clippy", "-p", "interlace-core", "--", "-D", "warnings"],
        cwd=root,
        check=False,
    )
    if clip.returncode != 0:
        fail(clip.stderr or clip.stdout)
    fmt = run(["cargo", "fmt", "--check"], cwd=root, check=False)
    if fmt.returncode != 0:
        fail(fmt.stderr or fmt.stdout)
    edits = run(
        [sys.executable, str(Path(__file__).with_name("assert_no_test_edits.py"))],
        cwd=root,
        check=False,
    )
    if edits.returncode != 0:
        fail(edits.stderr or edits.stdout)
    mx = run(
        [
            sys.executable,
            str(Path(__file__).with_name("assert_matrix_not_ignored.py")),
            "--must",
            args.must,
        ],
        cwd=root,
        check=False,
    )
    if mx.returncode != 0:
        fail(mx.stderr or mx.stdout)
    print(f"gate_impl {args.stage} ok")


if __name__ == "__main__":
    main()
