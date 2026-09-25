"""#420 — Doctor tab shows last done inserted_messages. CLI doctor stays ok."""
from __future__ import annotations

import re
from pathlib import Path

from common import fail

_ISSUE = "#420"


def _locale_string(text: str, key: str) -> str | None:
    m = re.search(rf"\b{re.escape(key)}\s*:\s*\"((?:\\.|[^\"\\])*)\"", text)
    if m:
        return m.group(1)
    m = re.search(
        rf"\b{re.escape(key)}\s*:\s*\n\s*\"((?:\\.|[^\"\\])*)\"",
        text,
    )
    if m:
        return m.group(1)
    return None


def assert_wa_reimport_doctor(crate: Path) -> None:
    """Doctor muted paragraph shows inserted_messages via an en/tr pair.

    Does not require CLI `doctor` to print the count.
    """
    pane_path = crate / "web" / "lib" / "DoctorPane.svelte"
    if not pane_path.is_file():
        fail(f"{_ISSUE}: DoctorPane.svelte required")
    pane = pane_path.read_text()
    muted = re.findall(
        r"<p\b[^>]*text-sm text-muted-foreground[^>]*>[\s\S]*?</p>",
        pane,
    )
    showing = [block for block in muted if "inserted_messages" in block]
    if not showing:
        fail(
            f"{_ISSUE}: DoctorPane.svelte does not show inserted_messages "
            "in the muted paragraph (text-sm text-muted-foreground)"
        )
    keys = re.findall(r"""\bt\(\s*["']([A-Za-z0-9_]+)["']\s*\)""", showing[0])
    if not keys:
        fail(
            f"{_ISSUE}: Doctor inserted_messages sentence needs an en/tr locale pair"
        )
    key = keys[0]
    en_path = crate / "web" / "lib" / "locales" / "en.ts"
    tr_path = crate / "web" / "lib" / "locales" / "tr.ts"
    en = _locale_string(en_path.read_text(), key) if en_path.is_file() else None
    tr = _locale_string(tr_path.read_text(), key) if tr_path.is_file() else None
    if not en or not tr or en == tr:
        fail(
            f"{_ISSUE}: Doctor inserted_messages needs an en/tr locale pair "
            f"(key {key})"
        )
    if "{n}" not in en and "{count}" not in en:
        fail(
            f"{_ISSUE}: en locale {key} must include a count placeholder "
            "({n} or {count})"
        )
