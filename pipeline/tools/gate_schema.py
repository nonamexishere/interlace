#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root, run  # noqa: E402


def main() -> None:
    root = repo_root()
    sql = root / "crates" / "interlace-core" / "migrations" / "0001_init.sql"
    if not sql.is_file():
        fail(f"missing {sql} (lands in PR2)")
    lint = run(
        [sys.executable, str(Path(__file__).with_name("sql_lint.py")), str(sql)],
        cwd=root,
        check=False,
    )
    if lint.returncode != 0:
        fail(lint.stderr or lint.stdout)
    # Host `sqlite3` on GitHub macOS runners often lacks the fts5 module.
    # Product sqlite is rusqlite bundled (asserted by migrate_empty). Apply
    # via CLI only when FTS5 is present.
    compile_opts = subprocess.run(
        ["sqlite3", ":memory:", "PRAGMA compile_options;"],
        cwd=root,
        text=True,
        capture_output=True,
    )
    if compile_opts.returncode == 0 and "ENABLE_FTS5" in compile_opts.stdout:
        apply = subprocess.run(
            ["sqlite3", ":memory:", f".read {sql}"],
            cwd=root,
            text=True,
            capture_output=True,
        )
        if apply.returncode != 0:
            fail(f"sqlite3 apply failed\n{apply.stderr}")
    else:
        print("gate_schema: host sqlite3 has no FTS5; skip CLI apply")
    t = run(
        ["cargo", "test", "-p", "interlace-core", "migrate_empty", "--", "--exact"],
        cwd=root,
        check=False,
    )
    if t.returncode != 0:
        fail(f"migrate_empty failed\n{t.stdout}\n{t.stderr}")
    print("gate_schema ok")


if __name__ == "__main__":
    main()
