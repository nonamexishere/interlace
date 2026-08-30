"""#311 fold — PR #336 review fold3 (scroll cancel / pin retry / comments).

Sibling of jump_day_heading_fold.py. Do not grow fold / image / stutter2 /
stutter / freeze / review / heading modules. Lock scroll-path pin cancel
(not wheel-only), pin retry or heading-height estimate, one-line JSDoc on
dayPinTlIndex / applyJumpScrollPos / jumpToLocalDay. Keep measureEpoch /
TIMELINE_PAGE_LIMIT / applyJumpScrollPos / cancelDayHeadingPin /
cas-image-slot.

Must-IDs: jump-day-scroll-cancels-pin, jump-day-pin-retry,
jump-day-comments, jump-day-keep-measure-epoch, jump-day-keep-page-limit,
jump-day-keep-scrollpos, jump-day-keep-pin-cancel, jump-day-keep-image-slot.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.jump_day_heading import _ISSUE, _read
from tauri_gate.jump_day_heading_stutter import (
    _fn,
    _has_pin_cancel,
    _jump_src,
    _list_src,
    _virt_src,
    _wheel_body,
)
from tauri_gate.scan import _without_comments

_EPOCH = (
    r"(?:measureEpoch|measureGen|measureToken|rowMeasureGen|rowMeasureEpoch|"
    r"measureFlushGen|flushEpoch|flushGen|adjEpoch|adjGen|heightMeasureGen)"
)
_EPOCH_BUMP = re.compile(
    rf"(?:\+\+\s*{_EPOCH}|{_EPOCH}\s*\+\+"
    rf"|{_EPOCH}\s*(?:\+=\s*1|=\s*{_EPOCH}\s*\+\s*1))"
)
_TICK_THEN = re.compile(
    r"(?:void\s+)?tick\s*\(\s*\)\s*\.then\s*\(|\bawait\s+tick\s*\(\s*\)"
)
_WRITE = re.compile(r"\bwriteScrollTop\s*\(|\.scrollTop\s*(?:\+=|=)")
_SLOT = re.compile(r"data-cas-image-slot\b|\bcas-image-slot\b", re.I)
_PAGE_EXPORT = re.compile(
    r"\bexport\s+const\s+(?P<name>"
    r"TIMELINE_PAGE_LIMIT|JUMP_DAY_PAGE_SIZE|PERSON_TIMELINE_LIMIT|"
    r"TIMELINE_PAGE_SIZE|PAGE_SIZE|TL_PAGE_LIMIT|PERSON_PAGE_LIMIT"
    r")\s*=\s*(?P<n>\d+)"
)
_CLEAR_NAMES = (
    "clearDayPin",
    "onUserScroll",
    "onClearDayPin",
    "clearPaneDayPin",
    "onDayPinClear",
    "releaseDayPin",
    "endDayPin",
    "onTimelineUserScroll",
)
_CLEAR_RX = re.compile(r"\b(?:" + "|".join(_CLEAR_NAMES) + r")\b")
_PIN_F = re.compile(r"\bdayPin\s*=\s*false\b")
_CANCEL_PIN = re.compile(
    r"\b(?:"
    r"cancelDayHeadingPin|cancelHeadingPin|cancelDayPin|"
    r"bumpDayHeadingPin|bumpDayPinGen|cancelDayHeadingScroll"
    r")\b"
)
_PROG_GUARD = re.compile(
    r"if\s*\(\s*programmaticScroll\s*\)\s*return"
    r"|if\s*\(\s*programmaticScroll\s*\)\s*\{[^}]{0,40}return"
)
_POINTER_GUARD = re.compile(
    r"if\s*\(\s*!\s*pointerOnTimeline\s*\)\s*return"
    r"|if\s*\(\s*pointerOnTimeline\s*\)\s*\{"
    r"|if\s*\(\s*!\s*pointerOnTimeline\s*\)\s*\{"
)
_RETRY_MARK = re.compile(
    r"\b(?:retry|reEstimate|reestimate|secondPass|pinRetry|retryPin|"
    r"scheduleRetry|retryScroll|pinAgain|correctAgain|tryPin|pinAttempt)\b",
    re.I,
)
_HEADING_EST = re.compile(
    r"\b(?:HEADING_HEIGHT|DAY_HEADING_HEIGHT|dayHeadingHeight|headingHeight|"
    r"DAY_HEADING_H|tlHeadingHeight|HEADING_H)\b"
    r"|\bdayHeading\b\s*[\*\+\-]"
    r"|[\+\-]\s*(?:HEADING_HEIGHT|DAY_HEADING_HEIGHT|dayHeadingHeight|headingHeight|HEADING_H)"
    r"|headingInc(?:rement)?|perDayHeading|dayChangeCount",
    re.I,
)
_DOC_NAMES = ("dayPinTlIndex", "applyJumpScrollPos", "jumpToLocalDay")


def _expand_calls(src: str, *pools: str) -> str:
    exp = src
    for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", src):
        for pool in pools:
            body = _fn(pool, name)
            if body:
                exp += "\n" + body
                break
    return exp


def _has_measure_epoch(list_s: str) -> bool:
    flush = _fn(list_s, "flushRowMeasures")
    clear = _fn(list_s, "clearPendingMeasures")
    if not flush.strip() or not _TICK_THEN.search(flush) or not _WRITE.search(flush):
        return False
    if not _EPOCH_BUMP.search(clear):
        return False
    if not re.search(_EPOCH, flush):
        return False
    for m in _TICK_THEN.finditer(flush):
        win = flush[m.start() : m.start() + 520]
        if _WRITE.search(win) and re.search(_EPOCH, win) and re.search(
            r"!==|===|==|!=|return", win
        ):
            return True
    return bool(
        re.search(
            rf"await\s+tick\s*\(\s*\)[\s\S]{{0,200}}{_EPOCH}[\s\S]{{0,120}}"
            r"(?:return|writeScrollTop)",
            flush,
        )
    )


def _has_page_limit(jump: str) -> bool:
    m = _PAGE_EXPORT.search(jump)
    return bool(m and 1 <= int(m.group("n")) <= 500)


def _has_apply_jump_scroll(jump: str, pane: str) -> bool:
    if re.search(r"\bexport\s+(?:async\s+)?function\s+applyJumpScrollPos\b", jump):
        return True
    if re.search(r"\bexport\s+const\s+applyJumpScrollPos\b", jump):
        return True
    body = _fn(jump, "applyJumpScrollPos") or _fn(pane, "applyJumpScrollPos")
    return bool(body.strip() and "\n" in body)


def _scroll_body(list_s: str) -> str:
    body = _fn(list_s, "onTimelineScroll")
    if body.strip():
        return body
    m = re.search(
        r"id\s*=\s*[\"']person-timeline[\"'][^>]*\bonscroll\s*=\s*\{([^}]+)\}",
        list_s,
    )
    if m:
        return m.group(1)
    m = re.search(r"\bonscroll\s*=\s*\{([^}]+)\}", list_s)
    return m.group(1) if m else ""


def _clears_day_pin(exp: str, list_s: str, pane: str, jump: str) -> bool:
    if _PIN_F.search(exp):
        return True
    if not _CLEAR_RX.search(exp):
        return bool(re.search(r"\bdayPin\b", list_s) and _PIN_F.search(exp))
    if re.search(
        r"(?:"
        + "|".join(_CLEAR_NAMES)
        + r")\s*=\s*\{[^}]{0,120}dayPin\s*=\s*false",
        pane,
    ):
        return True
    for name in _CLEAR_NAMES:
        body = _fn(pane, name)
        if body and _PIN_F.search(body):
            return True
    if re.search(
        r"(?:"
        + "|".join(_CLEAR_NAMES)
        + r")[\s\S]{0,160}?dayPin\s*=\s*false"
        r"|dayPin\s*=\s*false[\s\S]{0,160}?(?:"
        + "|".join(_CLEAR_NAMES)
        + r")",
        pane,
    ):
        return True
    # prop optional call alone is enough if pane wires dayPin = false
    if _CLEAR_RX.search(exp) and (
        _PIN_F.search(pane) or re.search(r"onClearDayPin|clearDayPin", pane)
    ):
        return True
    return False


def _has_scroll_cancels_pin(list_s: str, pane: str, jump: str) -> bool:
    """onTimelineScroll cancels pin + clears dayPin after programmatic guard."""
    scroll = _scroll_body(list_s)
    if not scroll.strip():
        return False
    # Cancel must not live only before the programmaticScroll early-return.
    prog = list(_PROG_GUARD.finditer(scroll))
    if prog:
        after = scroll[prog[0].end() :]
    else:
        # Accept cancel in the scroll handler if no guard is present at all
        # only when the whole body still cancels (impl may name the flag differently).
        after = scroll
    # pointerOnTimeline must not gate the cancel path in `after`.
    # Fail if cancel only appears inside a pointerOnTimeline-true branch, or
    # if a !pointerOnTimeline return sits before cancel with no cancel before it.
    exp_after = _expand_calls(after, list_s, pane, jump)
    if not _CANCEL_PIN.search(exp_after) and not _CANCEL_PIN.search(after):
        return False
    if not _clears_day_pin(exp_after, list_s, pane, jump) and not _clears_day_pin(
        after, list_s, pane, jump
    ):
        return False
    # Locate cancel relative to pointer guard in the post-programmatic region.
    ptr = _POINTER_GUARD.search(after)
    if ptr:
        # Cancel must appear before any !pointerOnTimeline return, or outside
        # a pointerOnTimeline-true block (not gated on pointer).
        cancel_m = _CANCEL_PIN.search(after) or _CANCEL_PIN.search(exp_after)
        if not cancel_m:
            return False
        # If the first pointer guard is `if (!pointerOnTimeline) return`,
        # cancel must be before that return.
        if re.match(
            r"if\s*\(\s*!\s*pointerOnTimeline\s*\)\s*return",
            ptr.group(0),
        ):
            if cancel_m.start() > ptr.start() and cancel_m.start() < len(after):
                # cancel only after the pointer return → gated → fail
                pre = after[: ptr.start()]
                if not _CANCEL_PIN.search(pre):
                    return False
        elif re.match(r"if\s*\(\s*pointerOnTimeline\s*\)\s*\{", ptr.group(0)):
            # cancel must not be only inside that block
            block_start = after.find("{", ptr.start())
            if block_start >= 0:
                depth = 0
                end = block_start
                for j in range(block_start, len(after)):
                    if after[j] == "{":
                        depth += 1
                    elif after[j] == "}":
                        depth -= 1
                        if depth == 0:
                            end = j
                            break
                inside = after[block_start : end + 1]
                outside = after[:block_start] + after[end + 1 :]
                if _CANCEL_PIN.search(inside) and not _CANCEL_PIN.search(outside):
                    if not _CANCEL_PIN.search(_expand_calls(outside, list_s, pane, jump)):
                        return False
    return True


def _brace_block(src: str, open_idx: int) -> str:
    """open_idx at '{'; return body inside matching braces."""
    if open_idx < 0 or open_idx >= len(src) or src[open_idx] != "{":
        return ""
    depth = 0
    for j in range(open_idx, min(len(src), open_idx + 2500)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[open_idx + 1 : j]
    return ""


def _has_heading_estimate(pin_day: str, offset: str, pin: str, virt: str) -> bool:
    est_surface = "\n".join(x for x in (pin_day, offset, pin) if x)
    if _HEADING_EST.search(est_surface):
        return True
    for body in (offset, _fn(virt, "offsetAt") or "", _fn(virt, "offsetOf") or ""):
        if not body.strip():
            continue
        if re.search(
            r"\blocalDay\b|prevDay|lastDay|dayKey|dayChange|headingHeight|"
            r"HEADING_HEIGHT|dayHeadingHeight|perDay",
            body,
        ):
            return True
    # pinDayAtTop estimate adds a named heading term beyond chrome+offsetOf
    if pin_day and re.search(
        r"tlChromeHeight\s*\+\s*offsetOf\s*\([^)]*\)\s*\+"
        r"|offsetOf\s*\([^)]*\)\s*\+\s*(?!0\b)",
        pin_day,
    ):
        return True
    return False


def _miss_block_retries(pin: str) -> bool:
    """True when a missing heading/row branch contains retry work (not bare return)."""
    for m in re.finditer(
        r"if\s*\(\s*!\s*(?:\(\s*)?(?:heading|row)\b[^;{]{0,80}\)\s*\{",
        pin,
    ):
        brace = pin.find("{", m.start())
        body = _brace_block(pin, brace)
        if not body.strip():
            continue
        # bare { return; } is not retry
        if re.fullmatch(r"\s*return\s*;?\s*", body):
            continue
        if re.search(
            r"requestAnimationFrame|writeScrollTop|data-tl-index|day-heading|"
            r"tick\s*\(|reEstimate|estimateTop|offsetOf|retry",
            body,
            re.I,
        ):
            return True
    return False


def _has_pin_retry(jump: str, list_s: str, virt: str) -> bool:
    pin = (
        _fn(jump, "scrollDayHeadingToTop")
        or _fn(list_s, "scrollDayHeadingToTop")
        or ""
    )
    pin_day = _fn(list_s, "pinDayAtTop") or _fn(jump, "pinDayAtTop") or ""
    offset = (
        _fn(list_s, "offsetOf")
        or _fn(virt, "offsetOf")
        or _fn(virt, "offsetAt")
        or _fn(list_s, "offsetAt")
        or ""
    )

    # (b) heading height in estimate / offsetOf
    if _has_heading_estimate(pin_day, offset, pin, virt):
        return True

    surface = pin + "\n" + pin_day
    if not pin.strip() and not pin_day.strip():
        return False

    # (a) retry when row/heading missing after the first rAF correction
    if _RETRY_MARK.search(surface):
        return True
    # Two or more [data-tl-index] lookups ⇒ second attempt
    if len(re.findall(r"data-tl-index", pin)) >= 2:
        return True
    # Loop around the DOM correction
    if re.search(r"\bwhile\s*\(", pin) and re.search(
        r"data-tl-index|day-heading", pin
    ):
        return True
    if _miss_block_retries(pin):
        return True
    # Bare `if (!(heading instanceof HTMLElement)) return` (today) — no retry
    if re.search(
        r"if\s*\(\s*!\s*\(\s*heading\s+instanceof\s+HTMLElement\s*\)\s*\)\s*return",
        pin,
    ):
        return False
    if re.search(
        r"if\s*\(\s*!\s*(?:heading|row)\b[^)]*\)\s*return",
        pin,
    ):
        return False
    # No miss return and no second attempt — still fail (no retry machinery)
    return False


def _jsdoc_before(raw: str, name: str) -> str | None:
    """Return the /** ... */ immediately before export function/const name, or None."""
    rx = re.compile(
        rf"(?:export\s+)?(?:async\s+)?function\s+{re.escape(name)}\s*\("
        rf"|(?:export\s+)?(?:const|let)\s+{re.escape(name)}\s*="
    )
    for m in rx.finditer(raw):
        pre = raw[: m.start()].rstrip()
        if not pre.endswith("*/"):
            continue
        # Walk back to matching /**
        end = len(pre)
        start = pre.rfind("/**")
        if start < 0:
            continue
        block = pre[start:end]
        if "*/" not in block[3:]:
            continue
        # Ensure nothing but whitespace between */ and the decl
        after_block = raw[start + len(block) : m.start()]
        if after_block.strip():
            continue
        return block
    return None


def _is_multiline_jsdoc(block: str) -> bool:
    # One-line /** ... */ is OK; any newline inside the block fails.
    inner = block.strip()
    if "\n" not in inner:
        return False
    return True


def _has_clean_jump_comments(raw_jump: str) -> bool:
    for name in _DOC_NAMES:
        block = _jsdoc_before(raw_jump, name)
        if block is None:
            continue
        if _is_multiline_jsdoc(block):
            return False
    return True


def assert_jump_day_heading_fold2(crate: Path) -> None:
    """#311 fold3: scroll cancels pin, pin retry/heading est, one-line JSDoc."""
    if not (crate / "web" / "lib" / "TimelineList.svelte").is_file():
        fail(f"{_ISSUE}: TimelineList.svelte required (jump day review fold3)")
    if not (crate / "web" / "lib" / "TimelinePane.svelte").is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (jump day review fold3)")

    list_s = _list_src(crate)
    pane = _without_comments(_read(crate, "TimelinePane.svelte"))
    jump = _jump_src(crate)
    virt = _virt_src(crate)
    cas = _without_comments(_read(crate, "CasAttach.svelte"))
    raw_jump = _read(crate, "jumpDay.ts")
    if not raw_jump.strip():
        raw_jump = (
            _read(crate, "jumpToDay.ts")
            + "\n"
            + _read(crate, "jumpToLocalDay.ts")
        )

    # --- keep (already green after fold / fold2 impl) ---
    if not _has_measure_epoch(list_s):
        fail(
            f"{_ISSUE}: keep measureEpoch bump in clearPendingMeasures + "
            "compare in flushRowMeasures tick callback before writeScrollTop"
        )
    if not _has_page_limit(jump):
        fail(
            f"{_ISSUE}: keep exported TIMELINE_PAGE_LIMIT (or JUMP_DAY_PAGE_SIZE / "
            "PERSON_TIMELINE_LIMIT) page-size constant"
        )
    if not _has_apply_jump_scroll(jump, pane):
        fail(
            f"{_ISSUE}: keep applyJumpScrollPos helper (named scrollToPos split "
            "for day-jump pin)"
        )
    if not _has_pin_cancel(jump, list_s):
        fail(
            f"{_ISSUE}: keep cancelDayHeadingPin on wheel "
            "(scrollDayHeadingToTop cancellable; onTimelineWheel cancels)"
        )
    if not _SLOT.search(cas):
        fail(
            f"{_ISSUE}: keep reserved cas-image-slot / data-cas-image-slot "
            "on the loadable image path"
        )
    # Wheel path may still clear; keep probe that wheel body exists.
    if not _wheel_body(list_s).strip():
        fail(f"{_ISSUE}: keep onTimelineWheel on #person-timeline")

    # --- new (fail today) ---
    if not _has_scroll_cancels_pin(list_s, pane, jump):
        fail(
            f"{_ISSUE}: onTimelineScroll (not only onTimelineWheel) must call "
            "cancelDayHeadingPin and clear pane dayPin (onClearDayPin / "
            "dayPin = false) after the programmaticScroll guard — cancel must "
            "not be gated on pointerOnTimeline (keyboard / scrollbar have no "
            "pointer; wheel-only cancel leaves the delayed pin write live)"
        )
    if not _has_pin_retry(jump, list_s, virt):
        fail(
            f"{_ISSUE}: scrollDayHeadingToTop / pinDayAtTop must retry when "
            "[data-tl-index] / .day-heading is missing after the first rAF "
            "correction (another rAF / re-estimate / second writeScrollTop), "
            "or the pin estimate / offsetOf must add a heading height "
            "(HEADING_HEIGHT / dayHeading / day-change count) — fail if one "
            "querySelector then return on miss and estimate is only "
            "tlChromeHeight + offsetOf"
        )
    if not _has_clean_jump_comments(raw_jump):
        fail(
            f"{_ISSUE}: jumpDay.ts dayPinTlIndex / applyJumpScrollPos / "
            "jumpToLocalDay must not carry a multi-line /** block that narrates "
            "steps — one-line /** ... */ is OK (Find-on pin leave-tlIndex and "
            "prepend-policy belong in the issue, not a three-line JSDoc)"
        )
