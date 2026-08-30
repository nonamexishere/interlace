"""#311 fold — PR #336 review (measure epoch / dayPin / page size / scrollToPos).

Sibling of jump_day_heading_image.py. Do not grow image / stutter2 / stutter /
freeze / review / heading modules. Lock measure-epoch on deferred adj write,
dayPin only on real pin or clear-on-miss, wheel clears pane dayPin, one page
size constant, multi-line / helper scrollToPos. Keep VIRTUALIZE_AFTER / freeze /
post-tick adj / pin cancel / cas-image-slot.

Must-IDs: jump-day-measure-epoch, jump-day-pin-on-scroll,
jump-day-wheel-clears-pin, jump-day-page-size, jump-day-scrollpos-split,
jump-day-keep-virtualize, jump-day-keep-freeze, jump-day-keep-adj-tick,
jump-day-keep-pin-cancel, jump-day-keep-image-slot.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.jump_day_heading import _ISSUE, _read
from tauri_gate.jump_day_heading_stutter import (
    _FREEZE_MARKERS,
    _VIRTUALIZE,
    _fn,
    _has_pin_cancel,
    _jump_src,
    _list_src,
    _virt_src,
    _wheel_body,
)
from tauri_gate.jump_day_heading_stutter2 import _flush_adj_write_after_tick
from tauri_gate.scan import _without_comments

_GO_NAMES = (
    "goToJumpDay",
    "onJumpDay",
    "onJumpDayChange",
    "handleJumpDay",
    "jumpDayChanged",
)
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
_PIN_T = re.compile(r"\bdayPin\s*=\s*true\b")
_PIN_F = re.compile(r"\bdayPin\s*=\s*false\b")
_JUMP_CALL = re.compile(r"\bjumpToLocalDay\s*\(|\bjumpToDay\s*\(")
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
_PAGE_NAMES = (
    "TIMELINE_PAGE_LIMIT",
    "JUMP_DAY_PAGE_SIZE",
    "PERSON_TIMELINE_LIMIT",
    "TIMELINE_PAGE_SIZE",
    "PAGE_SIZE",
    "TL_PAGE_LIMIT",
    "PERSON_PAGE_LIMIT",
)
_PAGE_EXPORT = re.compile(
    r"\bexport\s+const\s+(?P<name>"
    + "|".join(_PAGE_NAMES)
    + r")\s*=\s*(?P<n>\d+)"
)
_PAGE_CONST = re.compile(
    r"\bconst\s+(?P<name>" + "|".join(_PAGE_NAMES) + r")\s*=\s*(?P<n>\d+)"
)
_SLOT = re.compile(r"data-cas-image-slot\b|\bcas-image-slot\b", re.I)
_PIN_DAY = re.compile(r"\bpinDayAtTop\b|\bscrollDayHeadingToTop\b")


def _go(pane: str) -> str:
    return "\n".join(c for n in _GO_NAMES if (c := _fn(pane, n)).strip())


def _jtl(jump: str) -> str:
    return _fn(jump, "jumpToLocalDay") or _fn(jump, "jumpToDay") or ""


def _brace_body(src: str, open_idx: int) -> str:
    """open_idx points at '{'; return '{...}' with matching close."""
    if open_idx < 0 or open_idx >= len(src) or src[open_idx] != "{":
        return ""
    depth = 0
    for j in range(open_idx, min(len(src), open_idx + 1500)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[open_idx : j + 1]
    return ""


def _stp_bodies(go: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"scrollToPos\s*:", go):
        rest = go[m.end() :]
        am = re.match(
            r"\s*(?:async\s*)?(?:\(?\s*\w+\s*\)?\s*=>\s*|function\s*\([^)]*\)\s*)",
            rest,
        )
        if not am:
            # method ref: scrollToPos: name
            cm = re.match(r"\s*([A-Za-z_]\w*)\s*[,}]", rest)
            if cm:
                out.append(cm.group(1))
            continue
        after = rest[am.end() :]
        if after.startswith("{"):
            out.append(_brace_body(after, 0))
        else:
            # expression body up to comma/newline
            em = re.match(r"[^,\n]+", after)
            if em:
                out.append(em.group(0).strip())
    return out


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
    reset = _fn(list_s, "resetHeights")
    shift = _fn(list_s, "shiftHeightsForPrepend")
    if not flush.strip() or not _TICK_THEN.search(flush) or not _WRITE.search(flush):
        return False
    # Bump lives in clearPendingMeasures (preferred) or reset+shift.
    bumped = bool(_EPOCH_BUMP.search(clear))
    if not bumped:
        if _EPOCH_BUMP.search(reset) and _EPOCH_BUMP.search(shift):
            bumped = True
        elif ("clearPendingMeasures" in reset or "clearPendingMeasures" in shift) and _EPOCH_BUMP.search(
            clear
        ):
            bumped = True
    if not bumped:
        return False
    if not re.search(_EPOCH, flush):
        return False
    # Capture + compare around deferred write
    if not re.search(
        rf"(?:const|let)\s+\w+\s*=\s*{_EPOCH}"
        rf"|{_EPOCH}\s*(?:!==|===|==|!=)"
        rf"|(?:!==|===|==|!=)\s*{_EPOCH}"
        rf"|if\s*\([^)]*{_EPOCH}[^)]*\)",
        flush,
    ):
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


def _has_pin_on_scroll(pane: str, jump: str) -> bool:
    go = _go(pane)
    jtl = _jtl(jump)
    if not go.strip():
        return False
    bodies = _stp_bodies(go)
    stp = "\n".join(bodies)
    m_jump = _JUMP_CALL.search(go)

    # A: no unconditional dayPin=true before jump; true only on scroll/pin path
    if m_jump:
        pre = go[: m_jump.start()]
        pre_stripped = pre
        for b in bodies:
            if b.startswith("{"):
                pre_stripped = pre_stripped.replace(b, " ")
        if not _PIN_T.search(pre_stripped):
            if _PIN_T.search(stp):
                return True
            # true only via helper on scroll path; go itself never sets true
            if not _PIN_T.search(go) and _PIN_DAY.search(stp or go):
                for name in (
                    "applyJumpScrollPos",
                    "pinJumpDay",
                    "scrollToJumpPos",
                    "onJumpScrollPos",
                    "applyDayPin",
                    "pinDayScroll",
                ):
                    b = _fn(pane, name) or _fn(jump, name)
                    if b and _PIN_T.search(b):
                        return True
                # dayPin=true only inside a scrollToPos-named helper string body
                if _PIN_T.search(pane) and re.search(
                    r"scrollToPos\s*:\s*(?:async\s*)?\(?\s*\w+\s*\)?\s*=>\s*"
                    r"[A-Za-z_]\w*\s*\(",
                    go,
                ):
                    return True
            # post-jump success set
            post = go[m_jump.end() :]
            if _PIN_T.search(post) and re.search(
                r"scrolled|ok|hit|found|pinned|success", post, re.I
            ):
                return True

    # B: clear on miss — await/then jump result clears dayPin
    if re.search(
        r"await\s+jumpToLocalDay\s*\(|"
        r"jumpToLocalDay\s*\([\s\S]{0,900}?\)\s*\.then\s*\(",
        go,
    ) and (
        re.search(
            r"(?:"
            r"if\s*\(\s*!\s*\w+\s*\)\s*\{?[^}]{0,80}dayPin\s*=\s*false"
            r"|if\s*\(\s*!\s*\w+\s*\)\s*dayPin\s*=\s*false"
            r"|else\s*\{?[^}]{0,80}dayPin\s*=\s*false"
            r"|dayPin\s*=\s*(?:false|scrolled|ok|hit|!!)"
            r"|clearDayPin\s*\(|releaseDayPin\s*\(|setDayPin\s*\(\s*false"
            r")",
            go,
            re.I | re.S,
        )
    ):
        return True
    # onMiss callback in ctx
    if re.search(r"onMiss\s*:|onQuietMiss\s*:|onJumpMiss\s*:", go) and (
        _PIN_F.search(go) or re.search(r"setDayPin\s*\(\s*false|clearDayPin\s*\(", go)
    ):
        return True
    # jump returns status + go clears
    if jtl and re.search(
        r"return\s+(?:false|true|\{[^}]*scrolled|\"miss\"|'miss'|\"scrolled\")",
        jtl,
    ):
        if _PIN_F.search(go) or re.search(r"dayPin\s*=\s*(?:false|scrolled|ok)", go):
            return True
    return False


def _has_wheel_clears_pin(list_s: str, pane: str, jump: str) -> bool:
    wheel = _wheel_body(list_s)
    if not wheel.strip():
        return False
    exp = _expand_calls(wheel, list_s, pane, jump)
    if _PIN_F.search(exp):
        return True
    if not _CLEAR_RX.search(exp):
        # bindable dayPin on list
        return bool(re.search(r"\bdayPin\b", list_s) and _PIN_F.search(exp))
    # Callback path: pane must assign dayPin = false via that name
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
    return False


def _page_const(blob: str) -> tuple[str, int] | None:
    m = _PAGE_EXPORT.search(blob) or _PAGE_CONST.search(blob)
    if not m:
        return None
    name, n = m.group("name"), int(m.group("n"))
    if name == "JUMP_DAY_PAGE_CAP" or n < 1 or n > 500:
        return None
    # bare const must still be exported
    if not _PAGE_EXPORT.search(blob) and not re.search(
        rf"\bexport\s*\{{[^}}]*\b{re.escape(name)}\b|\bexport\s+const\s+{re.escape(name)}\b",
        blob,
    ):
        # _PAGE_CONST matched non-export — require export somewhere
        if not re.search(rf"\bexport\b[^;]{{0,80}}\b{re.escape(name)}\b", blob):
            return None
    return name, n


def _has_shared_page_size(pane: str, jump: str) -> bool:
    found = _page_const(jump) or _page_const(pane) or _page_const(jump + "\n" + pane)
    if not found:
        return False
    name, _n = found
    select = _fn(pane, "selectPerson") or pane
    if not re.search(rf"\blimit\s*:\s*{re.escape(name)}\b", select) and not re.search(
        rf"\blimit\s*:\s*{re.escape(name)}\b", pane
    ):
        return False
    jtl = _jtl(jump) or jump
    if not re.search(rf"\b{re.escape(name)}\b", jtl):
        return False
    return bool(
        re.search(
            rf"(?:"
            rf"\.length\s*[<!=]=?\s*{re.escape(name)}\b"
            rf"|{re.escape(name)}\s*[>!=]=?\s*\w+\.length"
            rf"|\blimit\s*=\s*{re.escape(name)}\b"
            rf"|page\.length\s*[<!=]=?\s*{re.escape(name)}\b"
            rf")",
            jtl,
        )
    )


def _scrollpos_split(pane: str, jump: str) -> bool:
    go = _go(pane)
    if not go.strip():
        return False
    # method ref or one-line delegate to named helper
    if re.search(r"scrollToPos\s*:\s*[A-Za-z_]\w*\s*[,}]", go):
        return True
    if re.search(
        r"scrollToPos\s*:\s*(?:async\s*)?\(?\s*\w+\s*\)?\s*=>\s*"
        r"(?:return\s+)?[A-Za-z_]\w*\s*\(",
        go,
    ):
        return True
    for body in _stp_bodies(go):
        if not body:
            continue
        # named helper only
        if re.fullmatch(r"[A-Za-z_]\w*", body):
            return True
        if "\n" not in body:
            # packed one-liner with pin work — fail this body
            if _PIN_DAY.search(body) or "dayPinTlIndex" in body:
                continue
            if re.match(r"^\{?\s*return\s+[A-Za-z_]\w*\s*\(", body.strip()):
                return True
            continue
        # multi-line
        if _PIN_DAY.search(body) or "dayPinTlIndex" in body or "tlIndex" in body:
            return True
        if re.search(r"\b[A-Za-z_]\w*\s*\(", body):
            return True
    # helper defined in jumpDay and used from pane
    if re.search(
        r"scrollToPos\s*:\s*(?:async\s*)?\(?\s*\w+\s*\)?\s*=>\s*\{?\s*"
        r"(?:return\s+)?(?:applyJump|pinJump|jumpScroll|scrollJump|"
        r"onJumpPin|applyDayPin|pinDayScroll|runScrollToPos|scrollToJumpDay)\w*\s*\(",
        go,
    ):
        return True
    for name in ("applyJumpScrollPos", "pinJumpScroll", "scrollToJumpPos"):
        b = _fn(jump, name) or _fn(pane, name)
        if b and "\n" in b and (_PIN_DAY.search(b) or "dayPinTlIndex" in b):
            if name in go:
                return True
    return False


def assert_jump_day_heading_fold(crate: Path) -> None:
    """#311 fold: measure epoch, dayPin, wheel clear, page size, scrollToPos split."""
    if not (crate / "web" / "lib" / "TimelineList.svelte").is_file():
        fail(f"{_ISSUE}: TimelineList.svelte required (jump day review fold)")
    if not (crate / "web" / "lib" / "TimelinePane.svelte").is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (jump day review fold)")

    list_s = _list_src(crate)
    pane = _without_comments(_read(crate, "TimelinePane.svelte"))
    jump = _jump_src(crate)
    virt = _virt_src(crate)
    cas = _without_comments(_read(crate, "CasAttach.svelte"))
    flush = _fn(list_s, "flushRowMeasures")

    # --- keep (already green) ---
    if not _VIRTUALIZE.search(virt) and not _VIRTUALIZE.search(list_s):
        fail(
            f"{_ISSUE}: keep #224 VIRTUALIZE_AFTER = 250 "
            "(do not turn virtualization off / Infinity)"
        )
    if re.search(r"VIRTUALIZE_AFTER\s*=\s*(?:Infinity|1e9|99999)", virt + "\n" + list_s):
        fail(f"{_ISSUE}: keep VIRTUALIZE_AFTER = 250 — not Infinity")
    for rx in _FREEZE_MARKERS:
        if not rx.search(jump):
            fail(
                f"{_ISSUE}: keep freeze fold "
                "(shouldLoadOlderForJump / loadedDayRange / JUMP_DAY_PAGE_CAP)"
            )
    if not flush.strip():
        fail(
            f"{_ISSUE}: flushRowMeasures required — measure-epoch / post-tick "
            "adj live on the measure flush"
        )
    if not _flush_adj_write_after_tick(flush, list_s):
        fail(
            f"{_ISSUE}: keep windowed measure path tick() after rowHeights = next "
            "before writeScrollTop (void tick().then(() => writeScrollTop…))"
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

    # --- new (fail today) ---
    if not _has_measure_epoch(list_s):
        fail(
            f"{_ISSUE}: flushRowMeasures deferred writeScrollTop (tick().then / "
            "await tick) must consult a measureEpoch / measureGen / token that "
            "clearPendingMeasures (or resetHeights / shiftHeightsForPrepend) "
            "bumps — fail if the tick callback only checks !pinLatestObs "
            "(stale adj after prepend / person switch)"
        )
    if not _has_pin_on_scroll(pane, jump):
        fail(
            f"{_ISSUE}: dayPin = true must not be the unconditional first act of "
            "goToJumpDay with no clear on miss — set dayPin only inside "
            "scrollToPos / successful pin, or clear dayPin when jumpToLocalDay "
            "misses (quiet miss must restore Find snap)"
        )
    if not _has_wheel_clears_pin(list_s, pane, jump):
        fail(
            f"{_ISSUE}: onTimelineWheel (or its callees) must clear pane dayPin "
            "(dayPin = false or onUserScroll / clearDayPin that assigns false) "
            "— cancelDayHeadingPin + stopPinLatest alone leave Find snap suppressed"
        )
    if not _has_shared_page_size(pane, jump):
        fail(
            f"{_ISSUE}: one exported page-size constant "
            "(TIMELINE_PAGE_LIMIT / JUMP_DAY_PAGE_SIZE / PERSON_TIMELINE_LIMIT) "
            "must be the personTimeline / selectPerson limit and the "
            "jumpToLocalDay short-page check — not a bare const limit = 80 in "
            "the jump loop plus a separate limit: 80 in selectPerson "
            "(JUMP_DAY_PAGE_CAP is page count, not page size)"
        )
    if not _scrollpos_split(pane, jump):
        fail(
            f"{_ISSUE}: scrollToPos body in TimelinePane must not be a single "
            "packed line — use a named helper in jumpDay.ts or a multi-line "
            "function (pane is near the 500-line cap)"
        )
