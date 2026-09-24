"""#418 fold — windowed measure must not yank off Load newer.

When flushRowMeasures is windowed and adj < 0, do not write scrollTop if the
viewport is already within one screen of the bottom. Positive adj still
writes. The jump pin still re-pins. Placeholders only; no message bodies.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.scan_parse import _call_arg, _function_body, _match_closer, _without_comments

_ISSUE = "#418"
_GAP_EXPR = re.compile(
    r"scrollHeight\s*-\s*[\w.]+\s*-\s*[\w.]*clientHeight"
)
_CMP_CH = re.compile(
    r"clientHeight\s*[<>]=?|[<>]=?\s*[\w.]*clientHeight"
)
_ADJ_WRITE = re.compile(r"writeScrollTop\s*\([^)]*scrollTop\s*\+\s*adj")
_REPIN = re.compile(
    r"pinJump\s*\(\s*pin\s*\)"
    r"|if\s*\(\s*jumpPinIndex\s*>=\s*0\s*\)\s*pinJump\s*\("
)
_WINDOWED = re.compile(r"\.length\s*>\s*VIRTUALIZE_AFTER|\bwindowed\b")
_NEG_ADJ = re.compile(r"\badj\s*<\s*0\b|\badj\s*>=\s*0\b|\badj\s*>\s*0\b")
_OLD_TOP = re.compile(r"\boldTop\s*<\s*listScroll\b")
_ADJ_ACCUM = re.compile(r"\badj\s*\+=\s*h\s*-\s*prev\b")


def _named_fn_body(src: str, name: str) -> str:
    """Function body, including a TypeScript return type before `{`."""
    found = _function_body(src, name)
    if found.strip():
        return found
    m = re.search(rf"\bfunction\s+{re.escape(name)}\s*\(", src)
    if not m:
        return ""
    paren = src.find("(", m.end() - 1)
    close = _match_closer(src, paren)
    if close < 0:
        return ""
    j = _skip_ws(src, close + 1)
    if j < len(src) and src[j] == ":":
        while j < len(src) and src[j] != "{":
            j += 1
    if j >= len(src) or src[j] != "{":
        return ""
    end = _match_closer(src, j)
    if end < 0:
        return src[j + 1 :]
    return src[j + 1 : end]


def _skip_ws(src: str, i: int) -> int:
    while i < len(src) and src[i] in " \t\r\n":
        i += 1
    return i


def _stmt_or_block(src: str, j: int) -> tuple[str, int]:
    """Return (text, index_after) for a brace block or one semicolon statement."""
    n = len(src)
    if j < n and src[j] == "{":
        end = _match_closer(src, j)
        if end < 0:
            return src[j:], n
        return src[j + 1 : end], end + 1
    semi = src.find(";", j)
    if semi < 0:
        return src[j:], n
    return src[j:semi], semi + 1


def _if_arms(src: str) -> list[tuple[str, str, str]]:
    arms: list[tuple[str, str, str]] = []
    i = 0
    n = len(src)
    while i < n:
        m = re.search(r"\bif\s*\(", src[i:])
        if not m:
            break
        start = i + m.start()
        paren = src.find("(", start)
        if paren < 0:
            break
        cond = _call_arg(src, paren)
        close_paren = _match_closer(src, paren)
        if close_paren < 0:
            break
        body, k = _stmt_or_block(src, _skip_ws(src, close_paren + 1))
        else_body = ""
        e = _skip_ws(src, k)
        if src.startswith("else", e) and not (
            e + 4 < n and (src[e + 4].isalnum() or src[e + 4] == "_")
        ):
            e2 = _skip_ws(src, e + 4)
            if src.startswith("if", e2):
                paren2 = src.find("(", e2)
                close2 = _match_closer(src, paren2) if paren2 >= 0 else -1
                if close2 >= 0:
                    else_body, _after = _stmt_or_block(src, _skip_ws(src, close2 + 1))
                    else_body = src[e2 : _after]
            else:
                else_body, _after = _stmt_or_block(src, e2)
        arms.append((cond, body, else_body))
        i = start + 2
    return arms


def _gap_names(src: str) -> set[str]:
    assigns = list(re.finditer(r"(?:const|let|var)\s+(\w+)\s*=\s*([^;]+)", src))
    names: set[str] = set()
    changed = True
    while changed:
        changed = False
        for m in assigns:
            name, expr = m.group(1), m.group(2)
            if name in names:
                continue
            if _GAP_EXPR.search(expr):
                names.add(name)
                changed = True
                continue
            if any(re.search(rf"\b{re.escape(g)}\b", expr) for g in names) and (
                "clientHeight" in expr
            ):
                names.add(name)
                changed = True
    return names


def _mentions_gap(cond: str, src: str) -> bool:
    if _GAP_EXPR.search(cond) and _CMP_CH.search(cond):
        return True
    for name in _gap_names(src):
        if not re.search(rf"\b{name}\b", cond):
            continue
        m = re.search(rf"(?:const|let|var)\s+{name}\s*=\s*([^;]+)", src)
        expr = m.group(1) if m else ""
        if _CMP_CH.search(expr) or _CMP_CH.search(cond):
            return True
    return False


def _is_negated(cond: str) -> bool:
    stripped = cond.strip()
    if stripped.startswith("!"):
        return True
    # windowed && !(adj < 0 && nearBottom) still skips the write.
    if re.search(r"!\s*\([\s\S]*\badj\s*<\s*0\b", cond):
        return True
    if re.search(r"\badj\s*>=\s*0\b|\badj\s*>\s*0\b", cond) and not re.search(
        r"\badj\s*<\s*0\b", cond
    ):
        return True
    return False


def _skips_neg_adj_near_bottom(flush: str) -> bool:
    """True when a negative adj near the bottom does not write scrollTop + adj.

    Positive adj still has to write. The jump-pin re-pin is a separate keep.
    """
    if not _ADJ_WRITE.search(flush):
        return False
    for cond, body, else_body in _if_arms(flush):
        if not (_NEG_ADJ.search(cond) and _mentions_gap(cond, flush)):
            continue
        write_body = bool(_ADJ_WRITE.search(body))
        write_else = bool(_ADJ_WRITE.search(else_body))
        if _is_negated(cond) and write_body:
            return True
        if not _is_negated(cond) and not write_body and write_else:
            return True
    return False


def assert_around_scroll(crate: Path) -> None:
    """#418: windowed negative adj must not write scrollTop within one screen of the bottom."""
    path = crate / "web" / "lib" / "TimelineList.svelte"
    virt_path = crate / "web" / "lib" / "TimelineVirtual.ts"
    if not path.is_file():
        fail(f"{_ISSUE}: TimelineList.svelte required (flushRowMeasures)")
    flush = _named_fn_body(_without_comments(path.read_text()), "flushRowMeasures")
    if not flush.strip():
        fail(f"{_ISSUE}: flushRowMeasures required")
    if not _WINDOWED.search(flush):
        fail(
            f"{_ISSUE}: keep the windowed guard "
            "(filteredTimeline.length > VIRTUALIZE_AFTER or windowed) "
            "on flushRowMeasures"
        )
    if "pinLatestObs" not in flush:
        fail(f"{_ISSUE}: keep pinLatestObs on the flushRowMeasures write")
    if "scrollAdjForHeightChanges" not in flush:
        fail(f"{_ISSUE}: keep scrollAdjForHeightChanges in flushRowMeasures")
    helper = ""
    if virt_path.is_file():
        helper = _named_fn_body(
            _without_comments(virt_path.read_text()),
            "scrollAdjForHeightChanges",
        )
    adj_src = flush + "\n" + helper
    if not _OLD_TOP.search(adj_src):
        fail(
            f"{_ISSUE}: keep oldTop < listScroll in scrollAdjForHeightChanges"
        )
    if not _ADJ_ACCUM.search(adj_src):
        fail(f"{_ISSUE}: keep adj += h - prev in scrollAdjForHeightChanges")
    if not _REPIN.search(flush):
        fail(
            f"{_ISSUE}: keep the jump-pin re-pin "
            "(pinJump(pin) or jumpPinIndex >= 0 pinJump) in flushRowMeasures"
        )
    if not _skips_neg_adj_near_bottom(flush):
        fail(
            f"{_ISSUE}: flushRowMeasures calls writeScrollTop(sc, sc.scrollTop + adj) "
            "for every non-zero adj while windowed, with no skip when adj < 0 and "
            "scrollHeight - scrollTop - clientHeight < clientHeight"
        )
