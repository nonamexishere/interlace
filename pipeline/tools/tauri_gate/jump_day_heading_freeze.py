"""#311 fold — jump freeze / lag (dogfood).

Sibling of jump_day_heading.py (466) and jump_day_heading_review.py (368).
Do not grow those files. Lock range-miss / older-still / page-cap / yield.
Keep-checks for date / Load older / localDay / quiet / gen abort stay
here so they still pass first.

Must-IDs: jump-day-range-miss, jump-day-older-still, jump-day-page-cap,
jump-day-yield, jump-day-keep-date, jump-day-keep-older,
jump-day-keep-localday, jump-day-keep-quiet, jump-day-keep-gen.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.find_in_conversation import _FIND_HOOK
from tauri_gate.jump_day_heading import (
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
_RANGE_HELPER = re.compile(
    r"\b(?:loadedDayRange|shouldLoadOlderForJump|dayRange|loadedRange|"
    r"jumpDayRange|timelineDayRange)\b"
)
# Day-range bounds — not oldestCursor (paging cursor already on the tree).
_OLDEST = re.compile(
    r"\b(?:minDay|oldestDay|loadedOldest|oldestLoaded)\b"
    r"|(?:range|dayRange|loaded|bounds)\s*\.\s*oldest\b"
    r"|\boldest\b(?!\s*Cursor)"
)
_NEWEST = re.compile(
    r"\b(?:maxDay|newestDay|loadedNewest|newestLoaded)\b"
    r"|(?:range|dayRange|loaded|bounds)\s*\.\s*newest\b"
    r"|\bnewest\b"
)
_KEY_LT_OLDEST = re.compile(
    r"(?:shouldLoadOlderForJump\s*\("
    r"|(?:key|dayKey|jumpKey|target)\s*<\s*"
    r"(?:(?:range|dayRange|loaded|bounds)\s*\.\s*)?"
    r"(?:oldest|minDay|oldestDay|loadedOldest|oldestLoaded)\b"
    r"|(?:(?:range|dayRange|loaded|bounds)\s*\.\s*)?"
    r"(?:oldest|minDay|oldestDay|loadedOldest|oldestLoaded)\b"
    r"\s*>\s*(?:key|dayKey|jumpKey|target))"
)
_KEY_GT_NEWEST = re.compile(
    r"(?:(?:key|dayKey|jumpKey|target)\s*>\s*"
    r"(?:(?:range|dayRange|loaded|bounds)\s*\.\s*)?"
    r"(?:newest|maxDay|newestDay|loadedNewest|newestLoaded)\b"
    r"|(?:(?:range|dayRange|loaded|bounds)\s*\.\s*)?"
    r"(?:newest|maxDay|newestDay|loadedNewest|newestLoaded)\b"
    r"\s*<\s*(?:key|dayKey|jumpKey|target)"
    r"|(?:key|dayKey|jumpKey|target)\s*>=?\s*"
    r"(?:(?:range|dayRange|loaded|bounds)\s*\.\s*)?"
    r"(?:oldest|minDay|oldestDay|loadedOldest|oldestLoaded)\b)"
)
_PAGE_CAP_CONST = re.compile(
    r"\b(?:JUMP_DAY_PAGE_CAP|MAX_JUMP_PAGES|JUMP_PAGE_CAP|PAGE_CAP)\s*=\s*(\d+)"
)
_PAGE_CAP_USE = re.compile(
    r"\b(?:JUMP_DAY_PAGE_CAP|MAX_JUMP_PAGES|JUMP_PAGE_CAP|PAGE_CAP)\b"
)
_PAGES_CMP = re.compile(
    r"\b(?:pages?|pageCount|nPages|loadCount|prepends?|loads)\s*"
    r"(?:<|<=)\s*(\d+|"
    r"JUMP_DAY_PAGE_CAP|MAX_JUMP_PAGES|JUMP_PAGE_CAP|PAGE_CAP)\b"
)
_PAGES_INC = re.compile(
    r"(?:\+\+\s*(?:pages?|pageCount|nPages|loadCount|prepends?|loads)"
    r"|(?:pages?|pageCount|nPages|loadCount|prepends?|loads)\s*\+\+"
    r"|(?:pages?|pageCount|nPages|loadCount|prepends?|loads)\s*"
    r"(?:\+=\s*1|=\s*\w+\s*\+\s*1))"
)
_TL_LOADING_TICK = re.compile(
    r"while\s*\(\s*(?:ctx\.)?tlLoading\s*\(\s*\)\s*\)\s*"
    r"await\s+tick\s*\(\s*\)\s*;?"
)
_AWAIT_TICK = re.compile(r"\bawait\s+tick\s*\(\s*\)")
_SELECT_PERSON_CALL = re.compile(
    r"(?:await\s+)?(?:ctx\.)?selectPerson\s*\([^;]*\)\s*;?"
)


def _fn(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name) or ""


def _go_body(pane: str) -> str:
    chunks = [_fn(pane, n) for n in _GO_NAMES]
    return "\n".join(c for c in chunks if c.strip())


def _jump_fn(src: str) -> str:
    return _fn(src, "jumpToLocalDay") or _fn(src, "jumpToDay")


def _cap_value(body: str) -> int | None:
    """Return a numeric page cap ≤ 80 if the prepend loop is bounded."""
    const_vals: dict[str, int] = {}
    for m in _PAGE_CAP_CONST.finditer(body):
        const_vals[m.group(0).split("=")[0].strip().split()[-1]] = int(m.group(1))
    # Named const used in a pages comparison.
    if const_vals and _PAGES_CMP.search(body):
        for name, n in const_vals.items():
            if name in body and n <= 80:
                return n
    if const_vals and _PAGE_CAP_USE.search(body) and _PAGES_INC.search(body):
        for n in const_vals.values():
            if n <= 80:
                return n
    best: int | None = None
    for m in _PAGES_CMP.finditer(body):
        raw = m.group(1)
        if raw.isdigit():
            n = int(raw)
        else:
            n = const_vals.get(raw)
            if n is None:
                cm = re.search(rf"\b{re.escape(raw)}\s*=\s*(\d+)", body)
                n = int(cm.group(1)) if cm else None
        if n is None or n > 80 or n < 1:
            continue
        if best is None or n < best:
            best = n
    if best is not None and _PAGES_INC.search(body):
        return best
    if best is not None and re.search(r"\b(?:for|while)\b", body):
        # for (pages = 0; pages < N; pages++) — INC may sit in the for-head
        if re.search(
            r"for\s*\([^;]*;(?:[^;]*\b(?:pages?|pageCount|nPages|loadCount|"
            r"prepends?|loads)\b[^;]*);",
            body,
        ):
            return best
    return None


def _has_range_miss_gate(body: str) -> bool:
    """Target > newest or in-range gap must return without selectPerson."""
    if _RANGE_HELPER.search(body):
        # Helper present: still need oldest/newest (or shouldLoadOlder only
        # when key < oldest) and a path that skips Load older.
        if _KEY_LT_OLDEST.search(body) or re.search(
            r"shouldLoadOlderForJump",
            body,
        ):
            return True
        if _OLDEST.search(body) and _NEWEST.search(body):
            return True
    # Inline min/max over localDay + key vs oldest/newest.
    if (
        re.search(r"\blocalDay\s*\(", body)
        and _OLDEST.search(body)
        and _NEWEST.search(body)
        and (_KEY_LT_OLDEST.search(body) or _KEY_GT_NEWEST.search(body))
    ):
        return True
    if _KEY_LT_OLDEST.search(body) and _KEY_GT_NEWEST.search(body):
        return True
    return False


def _has_older_still(body: str) -> bool:
    if not _OLDER.search(body) or not _LOOP.search(body):
        return False
    if not _SHORT.search(body):
        return False
    # Load older only when target is older than oldest loaded day.
    if re.search(r"shouldLoadOlderForJump", body):
        return True
    if _KEY_LT_OLDEST.search(body):
        return True
    return False


def _strip_tl_loading_ticks(body: str) -> str:
    return _TL_LOADING_TICK.sub(" ", body)


def _has_yield_after_select(body: str) -> bool:
    """await tick() after selectPerson — not the tlLoading spin."""
    cleaned = _strip_tl_loading_ticks(body)
    if not _SELECT_PERSON_CALL.search(cleaned):
        return False
    # selectPerson(...); ... await tick()
    for m in _SELECT_PERSON_CALL.finditer(cleaned):
        after = cleaned[m.end() : m.end() + 240]
        # Ignore ticks that are only inside a nested tlLoading while
        # (already stripped). Any await tick in the near tail counts.
        if _AWAIT_TICK.search(after):
            return True
    # tick() then continue loop is also fine if it follows selectPerson
    # via a helper — expand not required if inline.
    return False


def assert_jump_day_heading_freeze(crate: Path) -> None:
    """#311 fold: range-miss / page-cap / yield so a day pick cannot freeze."""
    pane_path = crate / "web" / "lib" / "TimelinePane.svelte"
    if not pane_path.is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (jump freeze / lag fold)")
    pane_raw = pane_path.read_text()
    pane = _without_comments(pane_raw)
    pane_m = _svelte_markup(pane_raw)
    helpers = _without_comments(
        _read(crate, "jumpDay.ts")
        + "\n"
        + _read(crate, "jumpToDay.ts")
        + "\n"
        + _read(crate, "jumpToLocalDay.ts")
    )
    src = pane + "\n" + helpers
    jump = _jump_src(crate)
    jump_fn = _jump_fn(src)
    body = jump_fn if jump_fn.strip() else jump
    go = _go_body(pane)

    # Keep existing #311 date / Load older / localDay / quiet / gen abort.
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
    if not go.strip() or (
        not _GEN_BUMP.search(go) and not _GEN_BUMP.search(body)
    ):
        fail(
            f"{_ISSUE}: keep goToJumpDay bumping a jump generation "
            "(jumpGen abort still present)"
        )

    if not body.strip():
        fail(
            f"{_ISSUE}: jumpToLocalDay required — range-miss / page-cap / "
            "yield live on the seek body"
        )

    # 1) jump-day-range-miss — future or in-range gap must not selectPerson.
    if not _has_range_miss_gate(body + "\n" + helpers):
        fail(
            f"{_ISSUE}: jumpToLocalDay must quiet-miss when the target day is "
            "newer than the newest loaded localDay, or inside the loaded "
            "oldest…newest range and absent (do not selectPerson / Load older "
            "for a future day or in-range gap — loadedDayRange / "
            "shouldLoadOlderForJump or inline min-max)"
        )

    # 2) jump-day-older-still — key < oldest still Load olders.
    if not _has_older_still(body + "\n" + helpers):
        fail(
            f"{_ISSUE}: when the target day is older than the oldest loaded "
            "localDay, still Load older (selectPerson(..., true) / prepend) "
            "until the heading exists, empty/short page, or the page cap "
            "(shouldLoadOlderForJump / key < oldest)"
        )

    # 3) jump-day-page-cap — prepend loop capped at ≤ 80 pages, then quiet miss.
    cap = _cap_value(body + "\n" + helpers)
    if cap is None:
        fail(
            f"{_ISSUE}: jumpToLocalDay prepend loop must cap pages at ≤ 80 "
            "(pages < N / JUMP_DAY_PAGE_CAP) then quiet miss — do not "
            "while (true) walk the whole thread"
        )

    # 4) jump-day-yield — await tick() after selectPerson (not only tlLoading).
    if not _has_yield_after_select(body):
        fail(
            f"{_ISSUE}: await tick() after each selectPerson prepend so the UI "
            "can paint and take a second date pick (the while (tlLoading()) "
            "await tick() spin does not count)"
        )
