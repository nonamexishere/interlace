#!/usr/bin/env python3
"""Lint 0001_init.sql: required columns, no is_group, no DROP TABLE of user data."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: sql_lint.py PATH.sql")
    root = repo_root()
    sql_path = Path(sys.argv[1])
    if not sql_path.is_absolute():
        sql_path = root / sql_path
    if not sql_path.is_file():
        fail(f"missing {sql_path}")
    text = sql_path.read_text()
    if re.search(r"(?i)DROP\s+TABLE\s+(messages|persons|identities|attachments)", text):
        fail("DROP TABLE of user data forbidden in 0001")
    for needle in ("heartbeat_at", "photo_dhash"):
        if needle not in text:
            fail(f"0001 missing {needle}")
    if re.search(r"(?i)\bis_group\b", text):
        fail("is_group column forbidden (use conversations.kind)")
    print("sql_lint ok")


if __name__ == "__main__":
    main()
