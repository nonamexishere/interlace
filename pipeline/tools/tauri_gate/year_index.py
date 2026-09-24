"""#419 — person_year_counts reads person_year_index, not messages.

Wired immediately after assert_inspector_year_jump (#378).

The read statement names `person_year_index`, binds `include_groups`, and
does not read `messages`. The CASE / substr / localtime / COUNT(*) / MIN
lock stays on the function that fills `person_year_index` (section 11 of
`inspector_year_jump.py`), not on this read.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.inspector_year_jump import (
    _rust_strings,
    _without_rust_comments,
)
from tauri_gate.last_read import _text
from tauri_gate.scan import _rust_function_body

_ISSUE = "#419"


def _read_body(root: Path) -> str:
    """`person_year_counts` only. Not the depth-2 callee expansion."""
    for rel in (
        "crates/interlace-core/src/people/timeline.rs",
        "crates/interlace-core/src/people.rs",
    ):
        raw = _text(root / rel)
        body = _rust_function_body(raw, "person_year_counts")
        if body:
            return _without_rust_comments(body)
    return ""


def _read_sql(body: str) -> str:
    selected = [
        lit
        for lit in _rust_strings(body)
        if re.search(r"\bSELECT\b", lit, re.I)
    ]
    return "\n".join(selected)


def assert_year_index(crate: Path) -> None:
    """#419: the inspector year read is the stored index for one flag."""
    del crate
    body = _read_body(repo_root())
    sql = _read_sql(body)
    names_index = "person_year_index" in sql
    binds_flag = bool(re.search(r":include_groups\b", sql))
    reads_messages = bool(re.search(r"\bmessages\b", sql, re.I))
    if not body.strip() or not names_index or not binds_flag or reads_messages:
        fail(
            f"{_ISSUE}: person_year_counts still reads messages; the read "
            "statement must name person_year_index and bind include_groups, "
            "and not read messages"
        )
    migration = _text(
        repo_root() / "crates/interlace-core/migrations/0003_person_year_index.sql"
    )
    if "AFTER INSERT" in migration or "year_index_pause" in migration:
        fail(
            f"{_ISSUE}: migrations/0003_person_year_index.sql must not contain "
            "AFTER INSERT or year_index_pause"
        )
