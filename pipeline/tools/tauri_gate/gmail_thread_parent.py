"""#424 — a mail reply can jump to its parent.

The reply row uses chrome key jumpToParent. TimelineRow carries the
parent message id. English is Parent. Turkish lives in tr.ts only.
No third locale. Do not require body_html.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.last_read import _text, _web_file
from tauri_gate.locale_pack import _chrome_pack_entries

_ISSUE = "#424"
_PARENT_FIELD = re.compile(
    r"\b(?:thread_parent_id|parent_message_id|parentMessageId)\b"
)
_ROW_TYPE = re.compile(r"export type TimelineRow = \{([\s\S]*?)\n\};")


def assert_gmail_thread_parent(crate: Path) -> None:
    """#424: reply row jumps with jumpToParent; TimelineRow has a parent id."""
    rows_path = _web_file(crate, "TimelineRows.svelte")
    rows = _text(rows_path) if rows_path.is_file() else ""
    api_path = _web_file(crate, "api.ts")
    api = _text(api_path) if api_path.is_file() else ""
    row_m = _ROW_TYPE.search(api)
    row_type = row_m.group(1) if row_m else ""
    uses_key = "jumpToParent" in rows
    has_parent = bool(_PARENT_FIELD.search(row_type))
    if not uses_key or not has_parent:
        bits: list[str] = []
        if not uses_key:
            bits.append(
                "the timeline reply row does not use chrome key jumpToParent"
            )
        if not has_parent:
            bits.append(
                "TimelineRow in web/lib/api.ts has no parent message id"
            )
        fail(f"{_ISSUE}: " + "; ".join(bits))

    en_path = crate / "web" / "lib" / "locales" / "en.ts"
    tr_path = crate / "web" / "lib" / "locales" / "tr.ts"
    en = _chrome_pack_entries(_text(en_path)) if en_path.is_file() else {}
    tr = _chrome_pack_entries(_text(tr_path)) if tr_path.is_file() else {}
    if en.get("jumpToParent") != "Parent":
        fail(f"{_ISSUE}: en.ts jumpToParent must be Parent")
    if not tr.get("jumpToParent", "").strip():
        fail(f"{_ISSUE}: tr.ts must define jumpToParent (no third locale)")
