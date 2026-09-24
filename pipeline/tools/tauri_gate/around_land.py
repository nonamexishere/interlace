"""#418 fold — day jump lands on the id, including same-sent_at ties.

The first older page stays `before: ${seekAt}~`. A full page that still
misses the id continues with that page's oldest row id (`beforeId` /
`before_id`), and the SQL keeps the rest of that `sent_at`. `pinJump`
in `goToJumpDay` runs only when `openPersonAtMessage` returns true.
Placeholders only; no message bodies.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.scan_parse import _js_next, _match_closer, _without_comments
from tauri_gate.scan_rust import _ts_fn_body
from tauri_gate.scan_rust_rest import _rust_fn_signature
from tauri_gate.scan_tokens import _rust_fn_body
from tauri_gate.search_jump_onscreen import _fn

_ISSUE = "#418"
_FIRST_PAGE = re.compile(r"\$\{seekAt\}~|seekAt\s*\+\s*[\"']~[\"']")
_BEFORE_ID = re.compile(r"\b(?:beforeId|before_id)\b")
_TIE_EQ = re.compile(r"sent_at\s*=\s*:before\b")
_TIE_ID = re.compile(r"\bid\s*<\s*:before_id\b")
_OPEN_AWAIT = re.compile(r"await\s+openPersonAtMessage\s*\(")
_RETURN_FALSE = re.compile(r"\breturn\s+false\b")
_RETURN_TRUE = re.compile(r"\breturn\s+true\b")


def _read(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _older_loop(opened: str) -> str:
    m = re.search(r"\bfor\s*\([^)]*(?:maxPages|\b80\b)[^)]*\)\s*\{", opened)
    if not m:
        return ""
    brace = opened.find("{", m.start())
    if brace < 0:
        return ""
    end = _match_closer(opened, brace)
    if end < 0:
        return ""
    return opened[brace + 1 : end]


def _call_objects(src: str, name: str) -> list[str]:
    out: list[str] = []
    start = 0
    while True:
        i = src.find(name, start)
        if i < 0:
            break
        if i > 0 and (src[i - 1].isalnum() or src[i - 1] == "_"):
            start = i + len(name)
            continue
        paren = src.find("(", i + len(name))
        if paren < 0 or paren - (i + len(name)) > 8:
            start = i + len(name)
            continue
        j = paren + 1
        while j < len(src) and src[j] in " \n\t":
            j += 1
        if j < len(src) and src[j] == "{":
            end = _match_closer(src, j)
            if end > j:
                out.append(src[j : end + 1])
                start = end + 1
                continue
        end = _match_closer(src, paren)
        if end > paren:
            out.append(src[paren + 1 : end])
            start = end + 1
            continue
        start = i + len(name)
    return out


def _loop_blob(pane: str, loop: str) -> str:
    """Older loop plus same-file helpers it calls (one level)."""
    chunks = [loop]
    seen: set[str] = set()
    for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", loop):
        if name in seen or name in {"if", "for", "while", "await", "return"}:
            continue
        seen.add(name)
        inner = _fn(pane, name) or _ts_fn_body(pane, name)
        if inner:
            chunks.append(inner)
    return "\n".join(chunks)


def _id_bound_to_row(blob: str) -> bool:
    """beforeId / before_id is taken from a loaded row's message id."""
    if re.search(
        r"\b(?:beforeId|before_id)\s*[:=]\s*[^;]{0,240}?\.(?:message_id|messageId)\b",
        blob,
    ):
        return True
    names = set(
        re.findall(
            r"(?:const|let|var)\s+([A-Za-z_]\w*)\s*=\s*[^;]{0,160}?\.(?:message_id|messageId)\b",
            blob,
        )
    )
    for name in names:
        if re.search(
            rf"\b(?:beforeId|before_id)\s*[:=]\s*[^;]{{0,120}}?\b{re.escape(name)}\b",
            blob,
        ):
            return True
    return False


def _strip_rust_comments(src: str) -> str:
    src = re.sub(r"/\*[\s\S]*?\*/", "", src)
    return re.sub(r"//.*?$", "", src, flags=re.M)


def _tie_sql(rows_for: str) -> bool:
    return bool(rows_for and _TIE_EQ.search(rows_for) and _TIE_ID.search(rows_for))


def _outer_returns(body: str) -> list[str]:
    """`return` of this function, not of a nested function or arrow."""
    out: list[str] = []
    i = 0
    n = len(body)
    brace = 0
    skip_until: int | None = None
    expect_fn = False
    while i < n:
        nxt = _js_next(body, i)
        if nxt != i:
            i = nxt
            continue
        if body.startswith("function", i) and (
            i == 0 or not (body[i - 1].isalnum() or body[i - 1] == "_")
        ):
            expect_fn = True
            i += 8
            continue
        if body.startswith("=>", i):
            j = i + 2
            while j < n and body[j] in " \t\r\n":
                j += 1
            # Expression arrows (`=> row.message_id`) are not blocks.
            if j < n and body[j] == "{":
                expect_fn = True
            i += 2
            continue
        c = body[i]
        if c == "{":
            if expect_fn and skip_until is None:
                skip_until = brace
                brace += 1
                expect_fn = False
                i += 1
                continue
            brace += 1
            expect_fn = False
            i += 1
            continue
        if c == "}":
            brace -= 1
            if skip_until is not None and brace == skip_until:
                skip_until = None
            i += 1
            continue
        if skip_until is None and body.startswith("return", i) and (
            i == 0 or not (body[i - 1].isalnum() or body[i - 1] == "_")
        ):
            end = i + 6
            while end < n and body[end] not in ";\n}":
                nxt = _js_next(body, end)
                if nxt != end:
                    end = nxt
                    continue
                end += 1
            out.append(body[i:end].strip())
            i = end
            continue
        if c not in " \t\r\n(":
            # `function name` already consumed; other tokens clear a stale flag
            # only when we are not still inside the parameter list.
            if c == ")":
                pass
            elif not expect_fn:
                pass
        i += 1
    return out


def _miss_block(opened: str) -> str:
    i = 0
    while True:
        m = re.search(r"\bif\s*\(", opened[i:])
        if not m:
            return ""
        paren = opened.find("(", i + m.start())
        close = _match_closer(opened, paren) if paren >= 0 else -1
        if close < 0:
            return ""
        j = close + 1
        while j < len(opened) and opened[j] in " \t\r\n":
            j += 1
        if j >= len(opened) or opened[j] != "{":
            i = close + 1
            continue
        end = _match_closer(opened, j)
        if end < 0:
            return ""
        body = opened[j + 1 : end]
        if "tlIndex" in body and "-1" in body and "showErr" in body:
            return body
        i = i + m.start() + 2


def _returns_ok(opened: str) -> bool:
    miss = _miss_block(opened)
    if not miss or not _RETURN_FALSE.search(miss) or _RETURN_TRUE.search(miss):
        return False
    pin_at = opened.find("pinJump")
    if pin_at < 0:
        return False
    outer = _outer_returns(opened)
    trues = [r for r in outer if _RETURN_TRUE.search(r)]
    if len(trues) != 1:
        return False
    if any(not _RETURN_FALSE.search(r) for r in outer if r not in trues):
        return False
    # The true return is on the path that schedules pinJump, not the miss.
    true_at = opened.find(trues[0])
    if true_at < 0:
        return False
    miss_at = opened.find(miss)
    if miss_at >= 0 and miss_at <= true_at <= miss_at + len(miss):
        return False
    return pin_at < true_at


def _assigns_from_open(src: str) -> set[str]:
    return set(
        re.findall(
            r"\b([A-Za-z_]\w*)\s*=\s*await\s+openPersonAtMessage\s*\(",
            src,
        )
    )


def _requires_open_true(cond: str, names: set[str]) -> bool:
    if _OPEN_AWAIT.search(cond):
        return not re.search(r"!\s*(?:\(\s*)?await\s+openPersonAtMessage\b", cond)
    for name in names:
        if not re.search(rf"\b{name}\b", cond):
            continue
        if re.search(rf"!\s*{name}\b", cond):
            return True
        if re.search(rf"\b{name}\s*!==\s*true\b|\b{name}\s*===\s*false\b", cond):
            return True
        if re.search(rf"\b{name}\s*===\s*true\b|\b{name}\s*!==\s*false\b", cond):
            return True
        if re.search(rf"(?<![.!\w]){name}\b", cond):
            return True
    return False


def _enclosing_ifs(src: str, at: int) -> list[str]:
    conds: list[str] = []
    i = 0
    n = len(src)
    while i < n and i < at:
        nxt = _js_next(src, i)
        if nxt != i:
            i = nxt
            continue
        if src.startswith("if", i) and (i == 0 or not (src[i - 1].isalnum() or src[i - 1] == "_")):
            paren = src.find("(", i)
            if paren < 0:
                break
            cond = src[paren + 1 : _match_closer(src, paren)] if _match_closer(src, paren) > paren else ""
            close = _match_closer(src, paren)
            j = close + 1 if close > paren else n
            while j < n and src[j] in " \t\r\n":
                j += 1
            if j < n and src[j] == "{":
                end = _match_closer(src, j)
                if end > j and j < at < end:
                    conds.append(cond)
            i = i + 2
            continue
        i += 1
    return conds


def _pin_requires_open_true(day: str) -> bool:
    pin_at = day.find("pinJump")
    open_at = day.find("openPersonAtMessage")
    if pin_at < 0 or open_at < 0 or not (open_at < pin_at):
        return False
    names = _assigns_from_open(day[:pin_at])
    between = day[open_at:pin_at]
    guards = _enclosing_ifs(day, pin_at)
    # Preceding `if (cond) return` after the await, same block as pinJump.
    prior: list[str] = []
    for m in re.finditer(r"\bif\s*\(([\s\S]*?)\)\s*return\b", between):
        prior.append(m.group(1))
    blob_conds = guards + prior
    if not any(_requires_open_true(c, names) for c in blob_conds):
        if not (_OPEN_AWAIT.search(between) and any(_requires_open_true(c, names) or _OPEN_AWAIT.search(c) for c in guards)):
            # `if (await openPersonAtMessage(...)) { pinJump }` — the await is
            # inside the enclosing condition, so `between` starts at the call.
            if not any(_requires_open_true(c, names) for c in guards):
                return False
    text = between + "\n" + "\n".join(guards)
    if not all(tok in text for tok in ("selectedId", "jumpDay", "jumpGen")):
        return False
    return True


def assert_around_land(crate: Path) -> None:
    """#418: tie cursor on the older walk, and pinJump only after a true open."""
    pane_path = crate / "web" / "lib" / "TimelinePane.svelte"
    api_path = crate / "web" / "lib" / "api.ts"
    core = crate.parent / "interlace-core" / "src" / "people" / "timeline.rs"
    cmd_path = crate / "src" / "people_cmd.rs"
    if not pane_path.is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required")
    pane = _without_comments(pane_path.read_text())
    opened = _fn(pane, "openPersonAtMessage")
    day = _fn(pane, "goToJumpDay")
    if not opened or not day:
        fail(f"{_ISSUE}: openPersonAtMessage and goToJumpDay are required")

    problems: list[str] = []
    if not _FIRST_PAGE.search(opened):
        problems.append(
            f"{_ISSUE}: the first older page must still use before: "
            "${seekAt}~ (or seekAt + \"~\")"
        )
    loop = _older_loop(opened)
    calls = _call_objects(loop, "personTimeline") if loop else []
    passed = any(_BEFORE_ID.search(call) for call in calls)
    bound = _id_bound_to_row(_loop_blob(pane, loop)) if loop else False
    if not passed or not bound:
        problems.append(
            f"{_ISSUE}: openPersonAtMessage's older loop continues with "
            "oldestSentAt only (no beforeId / before_id on the oldest loaded "
            "row's message id), so same-sent_at ties past the 200-row page "
            "are dropped"
        )

    rust = _strip_rust_comments(_read(core))
    cmd = _strip_rust_comments(_read(cmd_path))
    api = _without_comments(_read(api_path))
    rows_for = _rust_fn_body(rust, "person_timeline_rows_for")
    rows_sig = _rust_fn_signature(rust, "person_timeline_rows_for")
    cmd_sig = _rust_fn_signature(cmd, "person_timeline")
    cmd_body = _rust_fn_body(cmd, "person_timeline")
    api_args = re.search(r"personTimeline\s*:\s*\(args\s*:\s*\{([^}]*)\}", api)
    api_ok = bool(api_args and _BEFORE_ID.search(api_args.group(1)))
    if (
        not _tie_sql(rows_for)
        or not rows_sig
        or not _BEFORE_ID.search(rows_sig)
        or not cmd_sig
        or "before_id" not in cmd_sig
        or not cmd_body
        or "before_id" not in cmd_body
        or not api_ok
    ):
        problems.append(
            f"{_ISSUE}: the continuation id must be before_id on "
            "person_timeline / person_timeline_rows_for "
            "(sent_at = :before AND id < :before_id); api.personTimeline "
            "must accept beforeId or before_id"
        )

    if not _returns_ok(opened):
        problems.append(
            f"{_ISSUE}: openPersonAtMessage must return false on the miss "
            "path (tlIndex = -1 / showErr) and return true only on the path "
            "that schedules pinJump"
        )
    if not _pin_requires_open_true(day):
        problems.append(
            f"{_ISSUE}: goToJumpDay calls list?.pinJump(tlIndex) after "
            "jumpGen !== pinnedGen + 1 without requiring openPersonAtMessage "
            "to return true"
        )
    if problems:
        fail("\n".join(problems))
