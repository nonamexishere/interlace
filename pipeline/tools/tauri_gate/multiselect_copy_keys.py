"""#370 fold — PR #398 review (Shift+j/k, Shift-click native highlight, JSDoc).

Sibling of multiselect_copy.py (do not grow / rewrite that file). Parent
#370 range / copy / ring / session-set keep-checks stay. This fold locks
the PR-review bug + two suggestions only.

Must-IDs: 370-keys-shift-jk, 370-keys-shift-mousedown, 370-keys-jsdoc,
370-keys-keep-arrows-extend.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.last_read import _article_span, _web_file
from tauri_gate.multiselect_copy import (
    _ARROW_DOWN,
    _ARROW_UP,
    _EXTEND,
    _KEY_J,
    _KEY_K,
    _WALK,
)
from tauri_gate.reopen_last_lib import _fn_body
from tauri_gate.scan import _svelte_markup, _without_comments

_ISSUE = "#370"
# Same shape as the existing copy chord: e.key === "c" || e.key === "C".
_KEY_J_PAIR = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']j[\"']\s*\|\|\s*(?:e\.)?key\s*===?\s*[\"']J[\"']"
    r"|(?:e\.)?key\s*===?\s*[\"']J[\"']\s*\|\|\s*(?:e\.)?key\s*===?\s*[\"']j[\"']"
)
_KEY_K_PAIR = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']k[\"']\s*\|\|\s*(?:e\.)?key\s*===?\s*[\"']K[\"']"
    r"|(?:e\.)?key\s*===?\s*[\"']K[\"']\s*\|\|\s*(?:e\.)?key\s*===?\s*[\"']k[\"']"
)
_DOWN = re.compile(
    r"\bon(?:mouse|pointer)down\s*=\s*\{"
    r"|\bon:(?:mouse|pointer)down\s*=\s*\{",
    re.I,
)
_JOIN_FN = re.compile(r"(?:export\s+)?function\s+joinSelectedBodies\s*\(")
_RESTATE = re.compile(
    r"in-memory|timeline\[\]|blank[- ]line|⌘C of N|sent_at|message_id",
    re.I,
)
_SHIFT = re.compile(r"\b(?:e\.)?shiftKey\b")
_PREVENT = re.compile(r"\bpreventDefault\s*\(")


def _walk_blob(handle: str) -> str:
    """j/k caret walk — after visibleTlIndices, not the ⌘K / people-list arrows."""
    m = re.search(r"\bvisibleTlIndices\b", handle)
    if m:
        return handle[m.start() :]
    m = _KEY_J.search(handle)
    return handle[m.start() :] if m else handle


def _brace_after(src: str, start: int) -> str:
    brace = src.find("{", start)
    if brace < 0:
        return ""
    depth, i = 1, brace + 1
    while i < len(src) and depth:
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
        i += 1
    return src[brace + 1 : i - 1]


def _down_handler(art: str, rows: str) -> str:
    m = _DOWN.search(art)
    if not m:
        return ""
    inner = _brace_after(art, m.start())
    parts = [inner]
    for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", inner):
        body = _fn_body(rows, name)
        if body:
            parts.append(body)
    return "\n".join(parts)


def _comment_above_join(raw: str) -> str:
    m = _JOIN_FN.search(raw)
    if not m:
        return ""
    prefix = raw[: m.start()].rstrip()
    if prefix.endswith("*/"):
        start = prefix.rfind("/*")
        return prefix[start:] if start >= 0 else ""
    lines: list[str] = []
    for line in reversed(prefix.splitlines()):
        s = line.strip()
        if s.startswith("//"):
            lines.append(s)
        elif s == "":
            if lines:
                break
        else:
            break
    return "\n".join(reversed(lines))


def assert_multiselect_copy_keys(crate: Path) -> None:
    """#370: Shift+j/J + Shift+k/K extend; article shift mousedown; no join JSDoc."""
    keys_path = _web_file(crate, "PeopleKeys.ts")
    rows_path = _web_file(crate, "TimelineRows.svelte")
    mail_path = _web_file(crate, "TimelineMail.ts")
    if not keys_path.is_file():
        fail(f"{_ISSUE}: PeopleKeys.ts required (Shift+j/k walk)")
    if not rows_path.is_file():
        fail(f"{_ISSUE}: TimelineRows.svelte required (article Shift-click)")
    if not mail_path.is_file():
        fail(f"{_ISSUE}: TimelineMail.ts required (joinSelectedBodies)")

    keys_raw, rows_raw, mail_raw = (
        keys_path.read_text(),
        rows_path.read_text(),
        mail_path.read_text(),
    )
    keys = _without_comments(keys_raw)
    rows = _without_comments(rows_raw)
    handle = _fn_body(keys, "handleAppKey") or keys
    walk = _walk_blob(handle)
    rows_m = _svelte_markup(rows_raw)
    art = _article_span(rows_m) or _article_span(rows)

    # --- keep (pass today): ArrowDown/Up walk + extendSelection + join fn ---
    if not _KEY_J.search(walk) or not _ARROW_DOWN.search(walk):
        fail(f"{_ISSUE}: keep j / ArrowDown walking visibleTlIndices")
    if not _KEY_K.search(walk) or not _ARROW_UP.search(walk):
        fail(f"{_ISSUE}: keep k / ArrowUp on the same walk as j")
    if not _EXTEND.search(walk):
        fail(f"{_ISSUE}: keep extendSelection on the Shift+j/k walk")
    if not _WALK.search(walk):
        fail(
            f"{_ISSUE}: keep setTlIndex / ensureTlIndexVisible on the j/k walk "
            "(last-read caret)"
        )
    if not art:
        fail(f"{_ISSUE}: keep bubble <article> (Shift-click ring)")
    if not _JOIN_FN.search(mail_raw):
        fail(f"{_ISSUE}: joinSelectedBodies must stay in TimelineMail.ts")

    # --- bug: Shift+j / Shift+k (KeyboardEvent.key is "J" / "K") ---
    if not _KEY_J_PAIR.search(walk):
        fail(
            f"{_ISSUE}: Shift+j must match e.key === \"j\" || e.key === \"J\" "
            "(KeyboardEvent.key is \"J\" with Shift; same shape as \"c\"/\"C\")"
        )
    if not _KEY_K_PAIR.search(walk):
        fail(
            f"{_ISSUE}: Shift+k must match e.key === \"k\" || e.key === \"K\" "
            "(same shape as \"c\"/\"C\"; walk only, not the ⌘K palette chord)"
        )

    # --- suggestion: Shift-click native highlight ---
    down = _down_handler(art, rows)
    if not down or not _SHIFT.search(down) or not _PREVENT.search(down):
        fail(
            f"{_ISSUE}: article onmousedown (or onpointerdown) must "
            "preventDefault when e.shiftKey — do not blanket select-none"
        )

    # --- suggestion: drop restating JSDoc on joinSelectedBodies ---
    cmt = _comment_above_join(mail_raw)
    if cmt.startswith("/*") or (cmt and _RESTATE.search(cmt)):
        fail(
            f"{_ISSUE}: joinSelectedBodies must not have a restating JSDoc "
            "(in-memory / message_id / sent_at / blank-line)"
        )
