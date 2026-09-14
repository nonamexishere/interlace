"""#362 fold — attach-kind reload must keep the open conversation.

Sibling of timeline_attach_kind.py (do not grow / rewrite that file).
Chip change and Show all / empty-clear reload the current person with
keepConversation true so selectedConversationId is not nulled. Fail-today:
selectPerson(selectedId) without that flag.

Must-ID: media-kind-keep-conversation.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.include_groups import _arrow_prop
from tauri_gate.scan import (
    _call_arg,
    _function_body,
    _ts_fn_body,
    _without_comments,
)

_ISSUE = "#362"
_KEEP_NAMED = re.compile(r"\bkeepConversation\s*:\s*true\b")
_TRUE = re.compile(r"^(?:true|!0|1)\b")
_IDENT = re.compile(r"^[A-Za-z_][\w]*$")


def _handler_body(src: str, name: str) -> str:
    body = _arrow_prop(src, name)
    if body.strip():
        return body
    m = re.search(rf"{re.escape(name)}\s*=\s*\{{([A-Za-z_][\w]*)\}}", src)
    if not m:
        return ""
    ident = m.group(1)
    return _function_body(src, ident) or _ts_fn_body(src, ident) or ""


def _split_args(args: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    for c in args:
        if c in "({[":
            depth += 1
            buf.append(c)
        elif c in ")}]":
            depth = max(0, depth - 1)
            buf.append(c)
        elif c == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(c)
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def _select_args(src: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"\bselectPerson\s*\(", src):
        out.append(_call_arg(src, m.end() - 1))
    return out


def _ident_true(handler: str, name: str) -> bool:
    return bool(
        re.search(
            rf"\b(?:const|let|var)\s+{re.escape(name)}\s*=\s*true\b"
            rf"|\b{re.escape(name)}\s*=\s*true\b",
            handler,
        )
    )


def _keep_true(args: str, handler: str) -> bool:
    if _KEEP_NAMED.search(args):
        return True
    parts = _split_args(args)
    if len(parts) < 3:
        return False
    third = parts[2].strip()
    if _TRUE.search(third):
        return True
    return bool(_IDENT.fullmatch(third) and _ident_true(handler, third))


def _reload_keeps(src: str) -> bool:
    calls = _select_args(src)
    return bool(calls) and all(_keep_true(a, src) for a in calls)


def assert_timeline_attach_kind_fold(crate: Path) -> None:
    """#362 fold: attach-kind / Show all reload keeps the conversation."""
    pane_path = crate / "web" / "lib" / "TimelinePane.svelte"
    filters_path = crate / "web" / "lib" / "TimelineFilters.svelte"
    empty_path = crate / "web" / "lib" / "TimelineEmpty.svelte"
    if not pane_path.is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (keepConversation on attach-kind)")
    pane = _without_comments(pane_path.read_text())
    filters = _without_comments(filters_path.read_text()) if filters_path.is_file() else ""
    empty = _without_comments(empty_path.read_text()) if empty_path.is_file() else ""

    chip = "\n".join(
        [
            _handler_body(pane, "onAttachKindChange"),
            _function_body(filters, "pickAttachKind") or _ts_fn_body(filters, "pickAttachKind"),
        ]
    )
    show = "\n".join(
        [
            _handler_body(pane, "onShowAll"),
            _handler_body(empty, "onAction"),
        ]
    )

    # 1) media-kind-keep-conversation — first red today.
    if not _reload_keeps(chip):
        fail(
            f"{_ISSUE}: attach-kind chip change must call selectPerson with "
            "keepConversation true (third arg true / keepConversation: true) "
            "— selectPerson(selectedId) drops the thread"
        )
    if not _reload_keeps(show):
        fail(
            f"{_ISSUE}: Show all / empty-clear must call selectPerson with "
            "keepConversation true (third arg true / keepConversation: true) "
            "— selectPerson(selectedId) drops the thread"
        )
