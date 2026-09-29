"""#426 — an edit, a delete, or a reaction is chrome on one non-mail bubble.

messageEdited is "Edited" / "Düzenlendi". messageDeleted is
"This message was deleted" / "Bu mesaj silindi". The non-mail bubble renders
those keys, and a reaction (actor + emoji) on that same bubble. A tombstone
does not print the row body as the bubble text.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.last_read import _text, _web_file
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.scan import _without_comments
from tauri_gate.search_jump_onscreen import _fn

_ISSUE = "#426"
_IF_TOKEN = re.compile(r"\{#if\b|\{:else if\b|\{:else\}|\{/if\}")
_T_CALL = re.compile(r"""t\(\s*['"]([A-Za-z_][A-Za-z0-9_]*)['"]\s*\)""")
_ACTOR = re.compile(r"actor|display_name|displayName")


def _else_arm(src: str, if_at: int) -> str:
    """Body of the `{#if}` at if_at, from its `{else}` through the matching end."""
    depth = 0
    else_at = None
    for m in _IF_TOKEN.finditer(src, if_at):
        tok = m.group(0)
        if tok.startswith("{#if"):
            depth += 1
        elif tok == "{:else}" and depth == 1 and else_at is None:
            else_at = m.end()
        elif tok.startswith("{/if"):
            depth -= 1
            if depth == 0:
                if else_at is None:
                    return ""
                return src[else_at : m.start()]
    return ""


def _if_arm(src: str, if_at: int) -> str:
    """Body of `{#if}` before its `{:else}` / `{/if}`."""
    depth = 0
    start = None
    for m in _IF_TOKEN.finditer(src, if_at):
        tok = m.group(0)
        if tok.startswith("{#if"):
            depth += 1
            if depth == 1:
                start = m.end()
        elif tok.startswith("{:else") and depth == 1:
            return src[start : m.start()] if start is not None else ""
        elif tok.startswith("{/if"):
            depth -= 1
            if depth == 0 and start is not None:
                return src[start : m.start()]
    return ""


def _non_mail_region(rows: str) -> str:
    parts: list[str] = []
    mail = re.search(r"\{#if\s+isMailRow\(", rows)
    if mail:
        parts.append(_else_arm(rows, mail.start()))
    for m in re.finditer(r"\{#if\s*!isMailRow\(", rows):
        parts.append(_if_arm(rows, m.start()))
    return "\n".join(p for p in parts if p)


def _with_helpers(region: str, src: str) -> str:
    blobs = [region]
    for name in set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", region)):
        body = _fn(src, name)
        if body:
            blobs.append(body)
    return "\n".join(blobs)


def _has_key(region: str, key: str) -> bool:
    return key in {m.group(1) for m in _T_CALL.finditer(region)}


def _renders_reaction(region: str, src: str) -> bool:
    blob = _with_helpers(region, src)
    for m in re.finditer(r"emoji", blob):
        window = blob[max(0, m.start() - 400) : m.end() + 400]
        if _ACTOR.search(window):
            return True
    return False


def _tight_arm(src: str, idx: int) -> str:
    """Innermost if/else arm that contains idx. The whole src if none."""
    stack: list[tuple[int, int]] = []
    arms: list[tuple[int, int]] = []
    for m in _IF_TOKEN.finditer(src):
        tok = m.group(0)
        if tok.startswith("{#if"):
            stack.append((len(stack) + 1, m.end()))
        elif tok.startswith("{:else"):
            if stack:
                _, start = stack[-1]
                arms.append((start, m.start()))
                stack[-1] = (stack[-1][0], m.end())
        elif tok.startswith("{/if") and stack:
            _, start = stack.pop()
            arms.append((start, m.start()))
    covering = [(s, e) for s, e in arms if s <= idx < e]
    if not covering:
        return src
    start, end = min(covering, key=lambda se: se[1] - se[0])
    return src[start:end]


def _arm_leaks_body(arm: str, src: str) -> bool:
    if "body_text" in arm:
        return True
    for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", arm):
        if name == "t":
            continue
        body = _fn(src, name)
        if body and "body_text" in body:
            return True
    return False


def _tombstone_prints_body(region: str, src: str) -> bool:
    """True when the deleted bubble is missing or still prints the row body."""
    found = False
    for m in _T_CALL.finditer(region):
        if m.group(1) != "messageDeleted":
            continue
        found = True
        if _arm_leaks_body(_tight_arm(region, m.start()), src):
            return True
    return not found


def assert_message_events(crate: Path) -> None:
    """#426: non-mail bubble shows edited, deleted, and reaction chrome."""
    path = _web_file(crate, "TimelineRows.svelte")
    raw = _text(path) if path.is_file() else ""
    rows = _without_comments(raw)
    region = _non_mail_region(rows)
    en_path = crate / "web" / "lib" / "locales" / "en.ts"
    tr_path = crate / "web" / "lib" / "locales" / "tr.ts"
    en = _chrome_pack_entries(_text(en_path)) if en_path.is_file() else {}
    tr = _chrome_pack_entries(_text(tr_path)) if tr_path.is_file() else {}
    bits: list[str] = []
    if en.get("messageEdited") != "Edited":
        bits.append("chrome key messageEdited is absent from en.ts")
    if tr.get("messageEdited") != "Düzenlendi":
        bits.append("chrome key messageEdited is absent from tr.ts")
    if en.get("messageDeleted") != "This message was deleted":
        bits.append("chrome key messageDeleted is absent from en.ts")
    if tr.get("messageDeleted") != "Bu mesaj silindi":
        bits.append("chrome key messageDeleted is absent from tr.ts")
    if not _has_key(region, "messageEdited"):
        bits.append("TimelineRows does not render messageEdited on a non-mail bubble")
    if not _has_key(region, "messageDeleted"):
        bits.append("TimelineRows does not render messageDeleted on a non-mail bubble")
    if not _renders_reaction(region, rows):
        bits.append("a non-mail bubble does not render a reaction (actor + emoji)")
    if _tombstone_prints_body(region, rows):
        bits.append("a tombstone prints the row body as the bubble text")
    if bits:
        fail(f"{_ISSUE}: " + "; ".join(bits))
