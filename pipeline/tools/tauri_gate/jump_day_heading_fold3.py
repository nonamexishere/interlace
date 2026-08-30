"""#311 fold — PR #336 review fold4 (clear aborts gen / stop cancels pin / heading est).

Sibling of jump_day_heading_fold2.py. Do not grow fold2 / fold / image /
stutter2 / stutter / freeze / review / heading modules. Lock clear+Find
jumpGen abort, stopPin cancelDayHeadingPin, heading-height estimate or
miss re-estimate. Keep scroll-cancel / measureEpoch / TIMELINE_PAGE_LIMIT /
applyJumpScrollPos / cas-image-slot.

Must-IDs: jump-day-clear-aborts-gen, jump-day-stop-cancels-pin,
jump-day-heading-est, jump-day-keep-scroll-cancels-pin,
jump-day-keep-measure-epoch, jump-day-keep-page-limit,
jump-day-keep-scrollpos, jump-day-keep-image-slot.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.jump_day_heading import _ISSUE, _read
from tauri_gate.jump_day_heading_fold2 import (
    _SLOT,
    _brace_block,
    _expand_calls,
    _has_apply_jump_scroll,
    _has_heading_estimate,
    _has_measure_epoch,
    _has_page_limit,
    _has_scroll_cancels_pin,
    _scroll_body,
)
from tauri_gate.jump_day_heading_stutter import (
    _fn,
    _jump_src,
    _list_src,
    _virt_src,
)
from tauri_gate.scan import _without_comments

_GEN = (
    r"(?:jumpGen|jumpDayGen|tlGen|dayJumpGen|jumpToken|jumpDayToken)"
)
_GEN_BUMP = re.compile(
    rf"(?:\+\+\s*{_GEN}|{_GEN}\s*\+\+"
    rf"|{_GEN}\s*(?:\+=\s*1|=\s*{_GEN}\s*\+\s*1))"
)
_PIN_F = re.compile(r"\bdayPin\s*=\s*false\b")
_CANCEL_PIN = re.compile(
    r"\b(?:"
    r"cancelDayHeadingPin|cancelHeadingPin|cancelDayPin|"
    r"bumpDayHeadingPin|bumpDayPinGen|cancelDayHeadingScroll"
    r")\b"
)
_TOKEN_BUMP = re.compile(
    r"(?:\+\+\s*(?:dayPinToken|dayHeadingPinToken|headingPinToken|dayPinGen|"
    r"dayHeadingPinGen|headingPinGen|pinToken)"
    r"|(?:dayPinToken|dayHeadingPinToken|headingPinToken|dayPinGen|"
    r"dayHeadingPinGen|headingPinGen|pinToken)\s*\+\+"
    r"|(?:dayPinToken|dayHeadingPinToken|headingPinToken|dayPinGen|"
    r"dayHeadingPinGen|headingPinGen|pinToken)\s*"
    r"(?:\+=\s*1|=\s*\w+\s*\+\s*1))"
)
_WRITE = re.compile(r"\bwriteScrollTop\s*\(|\.scrollTop\s*(?:\+=|=)")
_REEST = re.compile(
    r"\b(?:offsetOf|offsetAt|reEstimate|reestimate|estimateScroll|"
    r"headingHeight|HEADING_HEIGHT|DAY_HEADING_HEIGHT|dayHeadingHeight|"
    r"heightOf|prefixSum)\b"
    r"|\bestimateTop\s*="
    r"|\b(?:HEADING_HEIGHT|DAY_HEADING_HEIGHT|dayHeadingHeight|HEADING_H)\b",
    re.I,
)
_CLEAR_NAMES = (
    "clearDayPin",
    "onClearDayPin",
    "clearPaneDayPin",
    "onDayPinClear",
    "releaseDayPin",
    "endDayPin",
    "abortDayJump",
    "clearDayJump",
)


def _handler_body(src: str, prop: str) -> str:
    """Inline `{...}` or identifier body for a Svelte prop/handler assignment."""
    m = re.search(
        rf"\b{re.escape(prop)}\s*=\s*\{{([\s\S]*?)\}}",
        src,
    )
    if m:
        inner = m.group(1).strip()
        # arrow: () => expr  or  () => { ... }
        am = re.match(
            r"(?:async\s+)?\([^)]*\)\s*=>\s*(\{[\s\S]*\}|[\s\S]+)",
            inner,
        )
        if am:
            body = am.group(1).strip()
            if body.startswith("{") and body.endswith("}"):
                return body[1:-1]
            return body
        return inner
    m = re.search(rf"\b{re.escape(prop)}\s*=\s*{{?([A-Za-z_][A-Za-z0-9_]*)}}?", src)
    if m:
        name = m.group(1)
        return _fn(src, name) or name
    return ""


def _path_aborts_gen(body: str, pane: str, list_s: str, jump: str) -> bool:
    """True when handler body clears dayPin and bumps jump gen (expanded)."""
    if not body.strip():
        return False
    exp = _expand_calls(body, pane, list_s, jump)
    surface = body + "\n" + exp
    if not _PIN_F.search(surface) and "dayPin" not in surface:
        # may only call a helper — expand already folded; require pin clear somewhere
        if not _PIN_F.search(exp) and not re.search(
            r"\bdayPin\s*=\s*!?\s*(?:false|0)\b", surface
        ):
            # still accept if body is only gen bump via named clearer that we expand
            pass
    if not (_PIN_F.search(surface) or re.search(r"\bdayPin\s*=\s*false\b", surface)):
        # If the outer wiring already sets dayPin=false beside a call, caller checks.
        if not _PIN_F.search(body):
            return False
    return bool(_GEN_BUMP.search(surface))


def _inline_or_fn_clears_and_aborts(src: str, prop: str, pane: str, list_s: str, jump: str) -> bool:
    body = _handler_body(src, prop)
    if not body.strip():
        # prop={name} form
        m = re.search(rf"\b{re.escape(prop)}\s*=\s*\{{?\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}}?", src)
        if m:
            body = _fn(src, m.group(1)) or _fn(pane, m.group(1)) or ""
    if _path_aborts_gen(body, pane, list_s, jump):
        return True
    # Multi-statement arrow without nested braces fully captured — scan nearby assign.
    m = re.search(
        rf"\b{re.escape(prop)}\s*=\s*\{{([^}}]{{0,200}})\}}",
        src,
    )
    if m and _PIN_F.search(m.group(1)) and _GEN_BUMP.search(m.group(1)):
        return True
    # Named helper assigned in script: look for functions that set dayPin=false + gen
    for name in _CLEAR_NAMES:
        fb = _fn(pane, name) or _fn(src, name)
        if fb and _PIN_F.search(fb) and _GEN_BUMP.search(fb):
            # must be wired to prop
            if re.search(rf"\b{re.escape(prop)}\s*=\s*\{{[^}}]*\b{name}\b", src) or re.search(
                rf"\b{re.escape(prop)}\s*=\s*\{{?\s*{name}\s*\}}?", src
            ):
                return True
    return False


def _find_oninput_body(pane: str) -> str:
    """Find-in-thread input oninput handler body (data-tl-find / id=tl-find)."""
    # Prefer the Find field specifically.
    for rx in (
        r'(?:id\s*=\s*["\']tl-find["\']|data-tl-find)[^>]*\boninput\s*=\s*\{([^}]+)\}',
        r'oninput\s*=\s*\{([^}]+)\}[^>]*(?:id\s*=\s*["\']tl-find["\']|data-tl-find)',
        r'data-tl-find[\s\S]{0,200}?oninput\s*=\s*\{([^}]+)\}',
    ):
        m = re.search(rx, pane)
        if m:
            return m.group(1).strip()
    # Fallback: any oninput that touches dayPin
    for m in re.finditer(r"\boninput\s*=\s*\{([^}]+)\}", pane):
        if "dayPin" in m.group(1) or "jumpGen" in m.group(1) or "clear" in m.group(1).lower():
            return m.group(1).strip()
    return ""


def _arrow_body(expr: str) -> str:
    expr = expr.strip()
    am = re.match(r"(?:async\s+)?\([^)]*\)\s*=>\s*(\{[\s\S]*\}|[\s\S]+)", expr)
    if not am:
        # bare call name
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expr):
            return expr
        return expr
    body = am.group(1).strip()
    if body.startswith("{") and body.endswith("}"):
        return body[1:-1]
    # unwrap parens: (dayPin = false)
    if body.startswith("(") and body.endswith(")"):
        return body[1:-1]
    return body


def _has_clear_aborts_gen(pane: str, list_s: str, jump: str) -> bool:
    """onClearDayPin wiring AND Find oninput bump jumpGen as well as dayPin=false."""
    # --- onClearDayPin path ---
    clear_ok = _inline_or_fn_clears_and_aborts(
        pane, "onClearDayPin", pane, list_s, jump
    )
    if not clear_ok:
        # list may define default; still require pane wiring
        raw_clear = _handler_body(pane, "onClearDayPin")
        if raw_clear:
            ab = _arrow_body(raw_clear) if "=>" in raw_clear or raw_clear.startswith("(") else raw_clear
            # also try full prop match with nested braces
            m = re.search(r"\bonClearDayPin\s*=\s*\{([\s\S]*?)\}\s*(?:/>|>|on[A-Z])", pane)
            if m:
                ab = _arrow_body(m.group(1).strip())
            exp = _expand_calls(ab, pane, list_s, jump)
            if (_PIN_F.search(ab) or _PIN_F.search(exp)) and _GEN_BUMP.search(
                ab + "\n" + exp
            ):
                clear_ok = True
            elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", ab.strip()):
                fb = _fn(pane, ab.strip())
                if fb and _PIN_F.search(fb) and _GEN_BUMP.search(fb):
                    clear_ok = True
        # Script-level: onClearDayPin={() => { dayPin=false; jumpGen++ }} with nested {}
        m = re.search(
            r"\bonClearDayPin\s*=\s*\{(\(\)\s*=>\s*\{[\s\S]*?\})\}",
            pane,
        )
        if m:
            inner = m.group(1)
            if _PIN_F.search(inner) and _GEN_BUMP.search(inner):
                clear_ok = True
    if not clear_ok:
        return False

    # --- Find oninput path ---
    onin = _find_oninput_body(pane)
    if not onin.strip():
        return False
    ab = _arrow_body(onin)
    exp = _expand_calls(ab, pane, list_s, jump)
    surface = ab + "\n" + exp
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", ab.strip()):
        fb = _fn(pane, ab.strip()) or ""
        surface = ab + "\n" + fb + "\n" + _expand_calls(fb, pane, list_s, jump)
    if not _PIN_F.search(surface):
        return False
    if not _GEN_BUMP.search(surface):
        return False
    return True


def _has_stop_cancels_pin(list_s: str, jump: str, pane: str) -> bool:
    """stopPin (TimelineList) must cancelDayHeadingPin or bump dayPinToken."""
    stop = _fn(list_s, "stopPin")
    if not stop.strip():
        # export const stopPin = ...
        m = re.search(
            r"(?:export\s+)?function\s+stopPin\s*\(|(?:export\s+)?(?:const|let)\s+stopPin\s*=",
            list_s,
        )
        if not m:
            return False
        stop = _fn(list_s, "stopPin")
    if not stop.strip():
        return False
    exp = _expand_calls(stop, list_s, jump, pane)
    surface = stop + "\n" + exp
    if _CANCEL_PIN.search(surface):
        return True
    if _TOKEN_BUMP.search(surface):
        return True
    # cancel helper body is just dayPinToken++
    for name in (
        "cancelDayHeadingPin",
        "cancelHeadingPin",
        "cancelDayPin",
        "bumpDayHeadingPin",
        "cancelDayHeadingScroll",
    ):
        if re.search(rf"\b{name}\s*\(", stop) or re.search(rf"\b{name}\s*\(", exp):
            return True
    return False


def _strip_inner_fn(src: str, name: str) -> str:
    """Remove a nested function/const body named `name` so its writes are ignored."""
    out = src
    for rx in (
        rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{",
        rf"(?:const|let)\s+{re.escape(name)}\s*=\s*(?:async\s*)?\([^)]*\)\s*=>\s*\{{",
        rf"(?:const|let)\s+{re.escape(name)}\s*=\s*function\s*\([^)]*\)\s*\{{",
    ):
        m = re.search(rx, out)
        if not m:
            continue
        brace = out.find("{", m.start())
        body = _brace_block(out, brace)
        if body is None:
            continue
        # drop from match start through closing brace
        end = brace + 1 + len(body) + 1
        out = out[: m.start()] + out[end:]
    return out


def _has_miss_reestimate(pin: str, pin_day: str, list_s: str, virt: str, jump: str) -> bool:
    """On miss, re-estimate a new top and writeScrollTop — not only tryPin() again."""
    surface = pin + "\n" + pin_day
    if not surface.strip():
        return False
    # Path A: after tryPin() fails, write a new estimated top
    for m in re.finditer(
        r"if\s*\(\s*tryPin\s*\(\s*\)\s*\)\s*return"
        r"|if\s*\(\s*!\s*tryPin\s*\(\s*\)\s*\)",
        pin,
    ):
        after = pin[m.end() : m.end() + 900]
        exp = _expand_calls(after, pin, pin_day, list_s, virt, jump)
        win = after + "\n" + exp
        # must write scroll with a recompute term — not only tryPin()
        if _WRITE.search(win) and _REEST.search(win):
            return True
        # named retry that re-estimates
        if re.search(r"\b(?:reEstimate|reestimate|estimateTop\s*=)\b", win) and _WRITE.search(
            win
        ):
            return True
    # Path B: miss branch on heading/row with writeScrollTop + recompute
    pin_wo = _strip_inner_fn(pin, "tryPin")
    for m in re.finditer(
        r"if\s*\(\s*!\s*(?:\(\s*)?(?:heading|row)\b[^;{]{0,100}\)(?:\s*return)?\s*\{{?",
        pin_wo,
    ):
        # statement or block after miss
        rest = pin_wo[m.start() : m.start() + 600]
        if re.search(r"return\s*;", rest) and not _WRITE.search(rest):
            continue
        brace = pin_wo.find("{", m.start(), m.start() + 120)
        if brace >= 0 and pin_wo[m.start():brace].count("\n") <= 2:
            body = _brace_block(pin_wo, brace)
            if body and _WRITE.search(body) and _REEST.search(body):
                return True
        if _WRITE.search(rest) and _REEST.search(rest):
            return True
    # Path C: pinDayAtTop recomputes estimateTop with heading term already handled
    # elsewhere; here accept explicit second writeScrollTop outside tryPin using offsetOf
    outer = _strip_inner_fn(pin, "tryPin")
    # count writeScrollTop in outer (initial estimate + re-estimate)
    writes = list(_WRITE.finditer(outer))
    if len(writes) >= 2 and _REEST.search(outer):
        # second write should not be only the initial estimateTop param passthrough
        second = outer[writes[1].start() : writes[1].start() + 120]
        if _REEST.search(outer[writes[0].end() : writes[1].start() + 120]) or _REEST.search(
            second
        ):
            return True
    # retryPin / second pass body expands to writeScrollTop + offsetOf
    for name in ("retryPin", "reEstimate", "reestimate", "secondPass", "pinRetry"):
        body = _fn(pin, name)
        # nested arrows: const retryPin = () => { ... }
        if not body.strip():
            m = re.search(
                rf"(?:const|let)\s+{name}\s*=\s*(?:async\s*)?\([^)]*\)\s*=>\s*\{{",
                pin,
            )
            if m:
                body = _brace_block(pin, pin.find("{", m.start()))
        if body and _WRITE.search(body) and _REEST.search(body):
            return True
        if body and _WRITE.search(body) and re.search(r"\boffsetOf\b|\bestimateTop\b", body):
            return True
    return False


def _has_heading_est(list_s: str, jump: str, virt: str) -> bool:
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
    if _has_heading_estimate(pin_day, offset, pin, virt):
        return True
    if _has_miss_reestimate(pin, pin_day, list_s, virt, jump):
        return True
    return False


def assert_jump_day_heading_fold3(crate: Path) -> None:
    """#311 fold4: clear aborts gen, stopPin cancels pin, heading est / re-estimate."""
    if not (crate / "web" / "lib" / "TimelineList.svelte").is_file():
        fail(f"{_ISSUE}: TimelineList.svelte required (jump day review fold4)")
    if not (crate / "web" / "lib" / "TimelinePane.svelte").is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (jump day review fold4)")

    list_s = _list_src(crate)
    pane = _without_comments(_read(crate, "TimelinePane.svelte"))
    jump = _jump_src(crate)
    virt = _virt_src(crate)
    cas = _without_comments(_read(crate, "CasAttach.svelte"))

    # --- keep (green after fold3 / fold2 impl) ---
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
    if not _has_scroll_cancels_pin(list_s, pane, jump):
        fail(
            f"{_ISSUE}: keep onTimelineScroll cancelDayHeadingPin + clear dayPin "
            "after programmaticScroll (not gated on pointerOnTimeline)"
        )
    if not _SLOT.search(cas):
        fail(
            f"{_ISSUE}: keep reserved cas-image-slot / data-cas-image-slot "
            "on the loadable image path"
        )
    # scroll handler must still exist
    if not _scroll_body(list_s).strip():
        fail(f"{_ISSUE}: keep onTimelineScroll on #person-timeline")

    # --- new (fail today) ---
    if not _has_clear_aborts_gen(pane, list_s, jump):
        fail(
            f"{_ISSUE}: onClearDayPin (pane wiring) and Find oninput must bump "
            "jumpGen (or jumpDayGen / tlGen) as well as dayPin = false — "
            "clearing the pin without aborting gen leaves jumpToLocalDay / "
            "applyJumpScrollPos alive through Load older and re-pins"
        )
    if not _has_stop_cancels_pin(list_s, jump, pane):
        fail(
            f"{_ISSUE}: stopPin (TimelineList) must call cancelDayHeadingPin "
            "(or bump dayPinToken) — stopPinLatest-only leaves a scheduled "
            "tick+rAF writeScrollTop live across person switch"
        )
    if not _has_heading_est(list_s, jump, virt):
        fail(
            f"{_ISSUE}: pinDayAtTop / scrollDayHeadingToTop / offsetOf must "
            "include a heading-height term (HEADING_HEIGHT / DAY_HEADING_HEIGHT / "
            "dayHeadingHeight / day-change count / localDay walk) or on miss "
            "re-estimate (offsetOf / estimateTop / writeScrollTop with a new top) "
            "— fail if estimate is only tlChromeHeight + offsetOf and retry is "
            "tryPin() again at the same scrollTop"
        )
