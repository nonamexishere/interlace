"""#425 — a WhatsApp quote jumps with the around-message window.

A resolved quote calls openPersonAtMessage. A miss uses chrome key
quoteNotInArchive. English is "Not in this archive". Turkish lives in
tr.ts only. Show quoted must not call openPersonAtMessage. Gmail
jumpToParent stays jumpToMessageId.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.last_read import _text, _web_file
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.scan import _without_comments
from tauri_gate.search_jump_onscreen import _fn

_ISSUE = "#425"
_SKIP_CALLS = {
    "LinkifyBody",
    "displayBody",
    "splitUrls",
    "openUrl",
    "findQ",
    "t",
    "item",
    "onJumpToParent",
    "jumpToParentMessage",
    "jumpToMessageId",
    "toggleQuoted",
}


def _read(crate: Path, name: str) -> str:
    path = _web_file(crate, name)
    if not path.is_file():
        path = crate / "web" / "lib" / name
    return _without_comments(_text(path) if path.is_file() else "")


def _non_mail_branch(rows: str) -> str:
    i = rows.find("{:else}")
    if i < 0:
        return ""
    j = rows.find("{/if}", i)
    return rows[i:j if j >= 0 else None]


def _show_quoted_calls_open(rows: str) -> bool:
    for m in re.finditer(r"data-show-quoted", rows):
        chunk = rows[max(0, m.start() - 500) : m.end() + 200]
        if "openPersonAtMessage" in chunk:
            return True
    return False


def _expr_is_quote_jump(expr: str) -> bool:
    return (
        "openPersonAtMessage" in expr
        and "jumpToMessageId" not in expr
        and "jumpToParentMessage" not in expr
        and "jumpToParent" not in expr
    )


def _lookup_fn(name: str, *srcs: str) -> str:
    for src in srcs:
        body = _fn(src, name)
        if body:
            return body
    return ""


def _wa_quote_calls_open(rows: str, pane: str, lst: str) -> bool:
    branch = _non_mail_branch(rows)
    if not branch:
        return False
    if _expr_is_quote_jump(branch):
        return True
    names = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", branch))
    names |= set(re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", branch))
    names -= _SKIP_CALLS
    blob = pane + "\n" + lst
    for name in names:
        body = _lookup_fn(name, pane, lst)
        if body and _expr_is_quote_jump(body):
            return True
        for m in re.finditer(rf"\b{re.escape(name)}\s*=\{{([^}}]*)\}}", blob):
            expr = m.group(1).strip()
            if _expr_is_quote_jump(expr):
                return True
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expr):
                bound = _lookup_fn(expr, pane, lst)
                if bound and _expr_is_quote_jump(bound):
                    return True
    return False


def assert_wa_quote_jump(crate: Path) -> None:
    """#425: WhatsApp quote uses openPersonAtMessage; Show quoted and Parent stay."""
    rows = _read(crate, "TimelineRows.svelte")
    pane = _read(crate, "TimelinePane.svelte")
    lst = _read(crate, "TimelineList.svelte")
    en_path = crate / "web" / "lib" / "locales" / "en.ts"
    tr_path = crate / "web" / "lib" / "locales" / "tr.ts"
    en = _chrome_pack_entries(_text(en_path)) if en_path.is_file() else {}
    tr = _chrome_pack_entries(_text(tr_path)) if tr_path.is_file() else {}
    bits: list[str] = []
    if _show_quoted_calls_open(rows):
        bits.append("Show quoted calls openPersonAtMessage")
    parent = _fn(pane, "jumpToParentMessage")
    if (
        "jumpToParent" not in rows
        or "onJumpToParent" not in rows
        or "jumpToMessageId" not in parent
        or "onJumpToParent={jumpToParentMessage}" not in pane
        or en.get("jumpToParent") != "Parent"
        or not tr.get("jumpToParent", "").strip()
    ):
        bits.append("Gmail jumpToParent path must remain")
    if en.get("quoteNotInArchive") != "Not in this archive":
        bits.append("chrome key quoteNotInArchive is absent from en.ts")
    if not tr.get("quoteNotInArchive", "").strip():
        bits.append("chrome key quoteNotInArchive is absent from tr.ts")
    if "quoteNotInArchive" not in rows or not _wa_quote_calls_open(rows, pane, lst):
        bits.append("a WhatsApp quote does not call openPersonAtMessage")
    if bits:
        fail(f"{_ISSUE}: " + "; ".join(bits))
