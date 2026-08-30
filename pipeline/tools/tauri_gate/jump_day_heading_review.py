"""#311 fold — PR #336 review bugs (in-flight jump abort / find snap).

Sibling of jump_day_heading.py (466). Do not grow that file. Lock the
two review bugs only. Keep-checks for date control / Load older /
localDay / quiet miss / no-calendar stay here so they still pass first.

Must-IDs: jump-day-gen-abort, jump-day-find-pin,
jump-day-keep-date, jump-day-keep-older, jump-day-keep-localday,
jump-day-keep-quiet, jump-day-keep-nocalendar.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.find_in_conversation import _FIND_HOOK
from tauri_gate.jump_day_heading import (
    _CALENDAR,
    _ISSUE,
    _LOCALDAY_CALL,
    _LOOP,
    _NEAREST,
    _OLDER,
    _SHORT,
    _TOAST,
    _jump_pane_tags,
    _jump_src,
    _read,
)
from tauri_gate.scan import (
    _function_body,
    _match_closer,
    _svelte_markup,
    _ts_fn_body,
    _without_comments,
)

_GO_NAMES = (
    "goToJumpDay",
    "onJumpDay",
    "onJumpDayChange",
    "handleJumpDay",
    "jumpDayChanged",
)
_GEN_NAME = (
    r"(?:tlGen|jumpGen|jumpDayGen|dayJumpGen|jumpToken|jumpAbortGen)"
)
_GEN_BUMP = re.compile(
    rf"(?:\+\+\s*{_GEN_NAME}|{_GEN_NAME}\s*\+\+"
    rf"|{_GEN_NAME}\s*(?:\+=\s*1|=\s*{_GEN_NAME}\s*\+\s*1))"
)
_STALE_HELPER = re.compile(
    r"\b(?:stale|isStale|jumpStale|aborted|isAborted|cancelled|isCancelled|"
    r"isCurrent|stillCurrent|alive|jumpAlive|jumpCurrent|isJumpCurrent|"
    r"sameJump|jumpMatches|genCurrent|jumpGenCurrent)\s*\("
)
_ID_STALE = re.compile(
    r"\b(?:selectedId|currentId|currentSelectedId|capturedId)\b\s*"
    r"(?:!==?|===?|\(\s*\))"
    r"|(?:!==?|===?)\s*(?:ctx\.)?(?:selectedId|currentId|capturedId)\b"
)
_KEY_STALE = re.compile(
    r"\b(?:jumpDay|dayKey|jumpKey|capturedKey|currentKey)\b\s*"
    r"(?:!==?|===?|\(\s*\))"
    r"|(?:!==?|===?)\s*(?:ctx\.)?(?:jumpDay|dayKey|jumpKey|capturedKey|currentKey)\b"
    r"|(?:ctx\.)?key\s*(?:!==?|===?|\(\s*\))"
)
_GEN_STALE = re.compile(
    rf"(?:\b(?:gen|capturedGen|currentGen|jumpGen|jumpDayGen|tlGen"
    rf"|dayJumpGen)\b\s*(?:!==?|===?|\(\s*\))"
    rf"|(?:!==?|===?)\s*(?:ctx\.)?(?:{_GEN_NAME}|gen|capturedGen|currentGen)\b)"
)
_EXPAND_SKIP = frozenset(
    {
        "selectPerson",
        "openPersonAtMessage",
        "pickConversation",
        "snapFindHit",
        "findHitIndices",
        "nearestVisibleTlIndex",
        "tick",
    }
)
_HIT_GUARD = re.compile(
    r"\b(?:hits|findHits|dayHits|findHitIndices|snapFindHit|dayHit)\b"
    r"|\.includes\s*\(\s*(?:item\.index|[\w.]*index)"
    r"|\blocalDay\b|\bsameDay\b|\bonThatDay\b|\bfindQ\b"
)
_DAY_ROW_RHS = re.compile(
    r"(?:item|row|hit|first)\.index"
    r"|filteredTimeline\s*\[\s*[\w.]+\s*\]\s*\.\s*index"
)
_PIN = re.compile(r"\b(?:pinDayAtTop|scrollDayHeadingToTop)\s*\(")
_TL_ASSIGN = re.compile(r"\btlIndex\s*=")


def _fn(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name) or ""


def _expand_skip(src: str, body: str, skip: frozenset[str] = _EXPAND_SKIP) -> str:
    chunks = [body]
    seen: set[str] = set(skip)
    queue = [body]
    while queue:
        blob = queue.pop()
        for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob):
            if name in seen:
                continue
            seen.add(name)
            inner = _fn(src, name)
            if not inner:
                continue
            chunks.append(inner)
            queue.append(inner)
    return "\n".join(chunks)


def _prop_body(src: str, name: str) -> str:
    m = re.search(
        rf"\b{re.escape(name)}\s*:\s*(?:async\s*)?"
        rf"(?:\([^)]*\)|[A-Za-z_]\w*)\s*=>\s*",
        src,
    )
    if not m:
        return ""
    start = m.end()
    if start < len(src) and src[start] == "{":
        close = _match_closer(src, start)
        return src[start + 1 : close] if close > start else src[start + 1 :]
    depth = 0
    i = start
    while i < len(src):
        c = src[i]
        if c in "({[":
            depth += 1
        elif c in ")}]":
            if depth == 0:
                break
            depth -= 1
        elif c == "," and depth == 0:
            break
        i += 1
    return src[start:i]


def _go_body(pane: str) -> str:
    chunks = [_fn(pane, n) for n in _GO_NAMES]
    return "\n".join(c for c in chunks if c.strip())


def _call_positions(src: str, name: str) -> list[int]:
    out: list[int] = []
    for m in re.finditer(rf"\b{re.escape(name)}\s*\(", src):
        pre = src[max(0, m.start() - 48) : m.start()]
        if re.search(r"(?:async\s+)?function\s+$", pre):
            continue
        if re.search(r"(?:const|let|var)\s+$", pre):
            continue
        if re.search(r":\s*(?:async\s*)?$", pre):
            continue
        out.append(m.start())
    return out


def _guarded_call(src: str, pos: int) -> bool:
    pre = src[max(0, pos - 500) : pos]
    if _STALE_HELPER.search(pre):
        return True
    window = pre[-280:]
    if not re.search(r"\breturn\b", window):
        return False
    return bool(
        _ID_STALE.search(window)
        or _KEY_STALE.search(window)
        or _GEN_STALE.search(window)
    )


def _all_calls_guarded(src: str, name: str) -> bool:
    spots = _call_positions(src, name)
    if not spots:
        return False
    return all(_guarded_call(src, p) for p in spots)


def _enclosing_if_cond(src: str, pos: int) -> str:
    for m in re.finditer(r"\bif\s*\(", src[:pos]):
        close = _match_closer(src, m.end() - 1)
        if close < 0:
            continue
        i = close + 1
        while i < len(src) and src[i] in " \t\n\r":
            i += 1
        if i < len(src) and src[i] == "{":
            end = _match_closer(src, i)
            if end >= pos > i:
                return src[m.end() : close]
        elif m.end() - 1 < pos <= i + 80:
            return src[m.end() : close]
    return ""


def _unguarded_day_tlindex(blob: str) -> bool:
    for m in _TL_ASSIGN.finditer(blob):
        rhs = blob[m.end() : m.end() + 80]
        if rhs.lstrip().startswith("$bindable"):
            continue
        if re.match(r"\s*append\s*\?", rhs):
            continue
        if not _DAY_ROW_RHS.search(rhs):
            continue
        cond = _enclosing_if_cond(blob, m.start())
        window = cond + "\n" + blob[max(0, m.start() - 160) : m.start()]
        if not _HIT_GUARD.search(window):
            return True
    return False


def _pin_only_on_hit(blob: str) -> bool:
    pins = list(_PIN.finditer(blob))
    if not pins:
        return True
    for m in pins:
        cond = _enclosing_if_cond(blob, m.start())
        if not cond.strip():
            return False
        if re.search(r"\bfindQ\b", cond) and re.search(r"!", cond):
            continue
        if _HIT_GUARD.search(cond) and not re.search(r"\bfindQ\b", cond):
            continue
        return False
    return True


def assert_jump_day_heading_review(crate: Path) -> None:
    """#311 fold: in-flight jump abort + Find must not steal the heading pin."""
    pane_path = crate / "web" / "lib" / "TimelinePane.svelte"
    if not pane_path.is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (jump generation / find pin)")
    pane_raw = pane_path.read_text()
    pane = _without_comments(pane_raw)
    pane_m = _svelte_markup(pane_raw)
    lst = _without_comments(_read(crate, "TimelineList.svelte"))
    pal = _read(crate, "CommandPalette.svelte")
    helpers = _without_comments(
        _read(crate, "jumpDay.ts")
        + "\n"
        + _read(crate, "jumpToDay.ts")
        + "\n"
        + _read(crate, "jumpToLocalDay.ts")
    )
    src = pane + "\n" + helpers + "\n" + lst
    jump = _jump_src(crate)
    go = _go_body(pane)
    go_x = (
        _expand_skip(src, go, _EXPAND_SKIP | {"jumpToLocalDay", "jumpToDay"})
        if go.strip()
        else ""
    )
    jump_fn = _fn(src, "jumpToLocalDay") or _fn(src, "jumpToDay")
    jump_x = _expand_skip(src, jump_fn) if jump_fn.strip() else ""
    wrappers = "\n".join(
        _prop_body(go or pane, n)
        for n in ("selectPerson", "scrollToPos", "stale", "isCurrent", "alive")
    )
    abort_src = "\n".join((go_x, jump_x, wrappers))
    scroll_src = "\n".join(
        (
            go,
            wrappers,
            _fn(src, "scrollToPos"),
            _fn(src, "pinDayAtTop"),
            _fn(src, "scrollDayHeadingToTop"),
            jump_fn,
        )
    )

    # Keep existing #311 date control / Load older / localDay / quiet / calendar.
    tags = _jump_pane_tags(pane_m)
    if not tags or not _FIND_HOOK.search(pane_m):
        fail(
            f"{_ISSUE}: keep the pane type=\"date\" control next to find "
            "(not #from/#to/#q/data-tl-find)"
        )
    if not _OLDER.search(jump) or not _LOOP.search(jump):
        fail(
            f"{_ISSUE}: keep Load older (selectPerson(..., true) / prepend) "
            "until the heading exists or the thread starts"
        )
    if not _SHORT.search(jump):
        fail(f"{_ISSUE}: keep stop Load older on an empty or short page")
    if not _LOCALDAY_CALL.search(jump) and not re.search(r"\blocalDay\s*\(", jump):
        fail(
            f"{_ISSUE}: keep localDay(sent_at, platform) as the seek key "
            "(host YYYY-MM-DD)"
        )
    if not re.search(r"\bplatform\b", jump):
        fail(f"{_ISSUE}: keep localDay(sent_at, platform) — platform still required")
    if _TOAST.search(jump):
        fail(f"{_ISSUE}: keep a quiet miss (no toast / showErr)")
    if _NEAREST.search(jump):
        fail(f"{_ISSUE}: keep a quiet miss — no snap to the nearest day")
    if _CALENDAR.search(pane + "\n" + lst + "\n" + pal) or len(tags) > 1:
        fail(
            f"{_ISSUE}: keep one pane type=\"date\" — not a calendar product"
        )

    # Bug 1 — in-flight jump has a generation / abort token.
    if not go.strip():
        fail(
            f"{_ISSUE}: goToJumpDay must bump a jump generation "
            "(a second date pick or person switch while Load older is "
            "running must abort the in-flight jump)"
        )
    if not _GEN_BUMP.search(go) and not _GEN_BUMP.search(go_x):
        fail(
            f"{_ISSUE}: goToJumpDay must bump a jump generation "
            "(a second date pick or person switch while Load older is "
            "running must abort the in-flight jump)"
        )
    if not jump_fn.strip():
        fail(
            f"{_ISSUE}: jumpToLocalDay must abort when selectedId, "
            "jumpDay / key, or tlGen is stale (before selectPerson / scrollToPos)"
        )
    if not (
        _ID_STALE.search(abort_src)
        and _KEY_STALE.search(abort_src)
        and _GEN_STALE.search(abort_src)
    ):
        fail(
            f"{_ISSUE}: jumpToLocalDay must abort when selectedId, "
            "jumpDay / key, or tlGen is no longer the captured one"
        )
    if not _all_calls_guarded(abort_src, "selectPerson"):
        fail(
            f"{_ISSUE}: jumpToLocalDay must abort before every selectPerson "
            "if selectedId, jumpDay / key, or tlGen is stale "
            "(do not prepend the old person's page onto the new timeline)"
        )
    if not _all_calls_guarded(abort_src, "scrollToPos"):
        fail(
            f"{_ISSUE}: jumpToLocalDay must abort before every scrollToPos "
            "if selectedId, jumpDay / key, or tlGen is stale "
            "(a superseded jump must not pin the old day)"
        )

    # Bug 2 — #310 find snap must not steal the heading pin.
    if _unguarded_day_tlindex(scroll_src):
        fail(
            f"{_ISSUE}: a day jump must not assign tlIndex to a non-hit "
            "on another day (only the day's first row if it is already a "
            "find hit, or a hit on that local day; otherwise leave tlIndex)"
        )
    if not _PIN.search(scroll_src):
        fail(
            f"{_ISSUE}: a day jump must still pin the heading "
            "(pinDayAtTop / scrollDayHeadingToTop) even if Find has no "
            "hit on that day"
        )
    if _pin_only_on_hit(scroll_src):
        fail(
            f"{_ISSUE}: pin the day's heading even if Find has no hit "
            "on that day (do not skip pinDayAtTop when the first row "
            "is not a find hit)"
        )
