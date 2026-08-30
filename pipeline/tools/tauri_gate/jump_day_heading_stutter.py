"""#311 fold — jump windowed hitch / pin cancel (dogfood).

Sibling of jump_day_heading_freeze.py (321). Do not grow freeze / review /
heading modules. Lock windowed prefix-sum measure adj, full-mount measure
still does not write scrollTop, pending day-heading pin cancel on wheel.

Must-IDs: jump-day-windowed-adj, jump-day-fullmount-no-scroll,
jump-day-pin-cancel, jump-day-keep-virtualize, jump-day-keep-freeze,
jump-day-keep-fullmount-range, jump-day-keep-anchor, jump-day-keep-est88.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.jump_day_heading import _ISSUE, _read
from tauri_gate.scan import (
    _function_body,
    _ts_fn_body,
    _without_comments,
)

_VIRTUALIZE = re.compile(r"\bVIRTUALIZE_AFTER\s*=\s*250\b")
_EST88 = re.compile(r"\bESTIMATED_ROW_HEIGHT\s*=\s*88\b")
_FULL_RANGE = re.compile(
    r"\btotal\s*<=\s*VIRTUALIZE_AFTER\b"
    r"|\blength\s*<=\s*VIRTUALIZE_AFTER\b"
    r"|\bfilteredTimeline\.length\s*<=\s*VIRTUALIZE_AFTER\b"
    r"|\btotal\s*<=\s*250\b"
)
_ANCHOR_NONE = re.compile(
    r"(?:timeline-spacer(?:-top|-bottom)?[^}]*overflow-anchor\s*:\s*none"
    r"|overflow-anchor\s*:\s*none[^}]*timeline-spacer)",
    re.I | re.S,
)
_FREEZE_MARKERS = (
    re.compile(r"\bshouldLoadOlderForJump\b"),
    re.compile(r"\bloadedDayRange\b"),
    re.compile(r"\bJUMP_DAY_PAGE_CAP\b"),
)
_SELECT_THEN_TICK = re.compile(
    r"(?:await\s+)?(?:ctx\.)?selectPerson\s*\([^;]*\)\s*;?"
    r"[\s\S]{0,200}?\bawait\s+tick\s*\(\s*\)"
)
_PREV_88 = re.compile(
    r"\?\?\s*(?:ESTIMATED_ROW_HEIGHT|88)\b"
    r"|(?:prev|oldH|oldHeight|previous)\s*=\s*[^;\n]{0,80}"
    r"\?\?\s*(?:ESTIMATED_ROW_HEIGHT|88)\b"
)
_PREFIX_HELPER = re.compile(
    r"\b(?:offsetOf|offsetAt|prefixFromMap|prefixSum(?:Of|s)?|prefixOffset)\b"
)
_ADJ_HELPER_NAMES = (
    "scrollAdjForHeightChanges",
    "scrollAdjFromHeightDeltas",
    "measureScrollAdj",
    "prefixFromMap",
    "prefixSumAdj",
    "heightChangeScrollAdj",
)
_LIST_SCROLL = re.compile(
    r"\blistScroll\b"
    r"|(?:scrollTop|tlScrollTop)\s*-?\s*tlChromeHeight"
    r"|tlChromeHeight\s*\)"
)
_ABOVE_VIEW = re.compile(
    r"(?:oldTop|oldOffset|prefixTop|rowTop)\s*<\s*"
    r"(?:listScroll|[^;\n]{0,40}tlChromeHeight)"
    r"|(?:listScroll)\s*>\s*(?:oldTop|oldOffset|prefixTop|rowTop)"
)
_ADJ_ACCUM = re.compile(
    r"\badj\s*\+\="
    r"|\badj\s*=\s*adj\s*\+"
    r"|\badj\s*=\s*\([^)]*\+\s*\([^)]*-\s*(?:prev|old)"
)
_WRITE_SCROLL = re.compile(
    r"\bwriteScrollTop\s*\("
    r"|\.scrollTop\s*=\s*[^;\n]*\badj\b"
    r"|\.scrollTop\s*\+=\s*\badj\b"
)
_PIN_LATEST_GUARD = re.compile(r"\bpinLatestObs\b|\bpinLatest\b")
_USER_SCROLL_SKIP = re.compile(
    r"if\s*\(\s*(?:!)?\s*userScrolling\b"
    r"|if\s*\(\s*userScrolling\b"
    r"|userScrolling\s*\)\s*return"
)
_DOM_ABOVE = re.compile(
    r"\b(?:querySelector|getBoundingClientRect|rowOffsetInPane)\b"
)
_WINDOWED_GUARD = re.compile(
    r"(?:filteredTimeline\.length|\.length|\btotal\b|\bn\b|\bcount\b)"
    r"\s*>\s*(?:VIRTUALIZE_AFTER|250)\b"
    r"|\bwindowed\b"
    r"|\bisWindowed\b"
    r"|\buseWindow\b"
)
_ROW_HEIGHTS_ASSIGN = re.compile(r"\browHeights\s*=\s*(?:next|\{)")
_PIN_CANCEL_NAME = re.compile(
    r"\b(?:"
    r"cancelDayHeadingPin|cancelHeadingPin|cancelDayPin|"
    r"bumpDayHeadingPin|bumpDayPinGen|cancelDayHeadingScroll"
    r")\b"
)
_PIN_TOKEN = re.compile(
    r"\b(?:"
    r"dayHeadingPinGen|dayPinGen|headingPinGen|dayHeadingPinToken|"
    r"headingPinToken|dayPinToken|pinToken|dayPinAlive"
    r")\b"
)
_PIN_TOKEN_BUMP = re.compile(
    r"(?:\+\+\s*(?:dayHeadingPinGen|dayPinGen|headingPinGen|pinToken|dayPinToken)"
    r"|(?:dayHeadingPinGen|dayPinGen|headingPinGen|pinToken|dayPinToken)\s*\+\+"
    r"|(?:dayHeadingPinGen|dayPinGen|headingPinGen|pinToken|dayPinToken)\s*"
    r"(?:\+=\s*1|=\s*\w+\s*\+\s*1)"
    r"|(?:dayPinAlive|alive)\s*=\s*false)"
)
_PIN_GUARD_IN_FN = re.compile(
    r"(?:"
    r"(?:gen|token|pinGen|dayPinGen|headingPinGen|dayHeadingPinGen|"
    r"dayPinToken|pinToken|myGen|captured)\s*(?:!==|===|==|!=)"
    r"|(?:!==|===|==|!=)\s*(?:gen|token|pinGen|dayPinGen|headingPinGen|"
    r"dayHeadingPinGen|dayPinToken|pinToken|myGen|captured)"
    r"|\bif\s*\([^)]*\b(?:cancelled|canceled|alive|stale)\b"
    r"|\b(?:cancelled|canceled|alive|stale)\b[^;]{0,40}return"
    r")"
)
_DELAYED_PIN = re.compile(r"\btick\s*\(|\brequestAnimationFrame\s*\(")


def _fn(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name) or ""


def _list_src(crate: Path) -> str:
    return _without_comments(_read(crate, "TimelineList.svelte"))


def _virt_src(crate: Path) -> str:
    return _without_comments(
        _read(crate, "TimelineVirtual.ts") + "\n" + _read(crate, "TimelineVirtual.svelte")
    )


def _jump_src(crate: Path) -> str:
    return _without_comments(
        _read(crate, "jumpDay.ts")
        + "\n"
        + _read(crate, "jumpToDay.ts")
        + "\n"
        + _read(crate, "jumpToLocalDay.ts")
    )


def _css_src(crate: Path) -> str:
    p = crate / "web" / "app.css"
    return p.read_text() if p.is_file() else ""


def _adj_helpers(virt: str, list_s: str) -> str:
    chunks: list[str] = []
    for name in _ADJ_HELPER_NAMES + (
        "offsetOf",
        "offsetAt",
        "heightOf",
        "heightAt",
        "flushRowMeasures",
    ):
        body = _fn(virt, name) or _fn(list_s, name)
        if body.strip():
            chunks.append(f"// {name}\n{body}")
    return "\n".join(chunks)


def _flush_surface(list_s: str, virt: str) -> str:
    flush = _fn(list_s, "flushRowMeasures")
    helpers = _adj_helpers(virt, list_s)
    # Prefer helpers referenced from flush; still include all adj helpers.
    return flush + "\n" + helpers


def _has_windowed_prefix_adj(flush: str, surface: str) -> bool:
    """Windowed measure flush: old prefix adj before rowHeights, then writeScrollTop."""
    if not flush.strip():
        return False
    # First measure uses prev ?? 88.
    if not _PREV_88.search(surface):
        return False
    # Old prefix via offsetOf / offsetAt / prefixFromMap (not DOM rects).
    if not _PREFIX_HELPER.search(surface):
        return False
    # listScroll = scrollTop - tlChromeHeight (or named listScroll).
    if not _LIST_SCROLL.search(surface) and not re.search(
        r"\btlChromeHeight\b", surface
    ):
        return False
    if not _ABOVE_VIEW.search(surface):
        return False
    if not _ADJ_ACCUM.search(surface):
        return False
    if not _WRITE_SCROLL.search(surface):
        return False
    if not _PIN_LATEST_GUARD.search(surface):
        return False
    # Do not skip because userScrolling.
    if _USER_SCROLL_SKIP.search(flush) or _USER_SCROLL_SKIP.search(surface):
        # Allow markUserScrolling elsewhere; only fail if adj path returns on it.
        adj_zone = surface
        if re.search(
            r"userScrolling[\s\S]{0,120}(?:return|adj\s*=\s*0)"
            r"|(?:if\s*\([^)]*userScrolling[^)]*\)\s*(?:return|\{[^}]*adj))",
            adj_zone,
        ):
            return False
    # Prefix / adj must run before rowHeights = next (old map).
    rh = _ROW_HEIGHTS_ASSIGN.search(flush)
    if rh:
        before = flush[: rh.start()]
        if not (
            _PREFIX_HELPER.search(before)
            or re.search(
                r"\b(?:scrollAdjForHeightChanges|scrollAdjFromHeightDeltas|"
                r"measureScrollAdj|prefixFromMap|heightChangeScrollAdj|adj)\b",
                before,
            )
        ):
            # Helper may own the whole adj+assign; surface still needs adj before assign.
            rh2 = _ROW_HEIGHTS_ASSIGN.search(surface)
            if rh2:
                before2 = surface[: rh2.start()]
                if not (_PREFIX_HELPER.search(before2) or re.search(r"\badj\b", before2)):
                    return False
    # No DOM above-viewport test on the adj path.
    # Ban querySelector / getBoundingClientRect only when tied to oldTop/listScroll.
    for m in _DOM_ABOVE.finditer(surface):
        window = surface[max(0, m.start() - 120) : m.end() + 120]
        if re.search(r"oldTop|listScroll|above|adj\s*\+=", window):
            return False
    return True


def _has_fullmount_no_scroll(flush: str, surface: str) -> bool:
    """adj / writeScrollTop in measure flush is behind > VIRTUALIZE_AFTER / windowed."""
    if not flush.strip():
        return False
    # Positive structure: windowed gate present on the measure adj path.
    if not _WINDOWED_GUARD.search(flush) and not _WINDOWED_GUARD.search(surface):
        return False
    # If write/adj exists, it must sit with the guard (not unguarded on full mount).
    writes = list(_WRITE_SCROLL.finditer(flush)) + list(
        re.finditer(r"\badj\s*\+\=|\bwriteScrollTop\s*\(", flush)
    )
    if not writes:
        # Adj may live only in a helper called behind the guard.
        if not (
            re.search(
                r"scrollAdjForHeightChanges|scrollAdjFromHeightDeltas|"
                r"measureScrollAdj|heightChangeScrollAdj",
                flush + "\n" + surface,
            )
            or _ADJ_ACCUM.search(surface)
        ):
            return False
        # Helper path still needs the windowed guard at the call site or helper entry.
        if not _WINDOWED_GUARD.search(flush) and not _WINDOWED_GUARD.search(surface):
            return False
        return True
    for w in writes:
        # Look backward for a windowed guard in the same function scope.
        back = flush[max(0, w.start() - 400) : w.start()]
        if not _WINDOWED_GUARD.search(back) and not _WINDOWED_GUARD.search(flush):
            return False
    # Explicit fail: writeScrollTop with no windowed mention anywhere in flush surface.
    if _WRITE_SCROLL.search(flush) and not _WINDOWED_GUARD.search(flush + "\n" + surface):
        return False
    return True


def _wheel_body(list_s: str) -> str:
    body = _fn(list_s, "onTimelineWheel")
    if body.strip():
        return body
    # Inline onwheel handler on #person-timeline.
    m = re.search(
        r"id\s*=\s*[\"']person-timeline[\"'][^>]*\bonwheel\s*=\s*\{([^}]+)\}",
        list_s,
    )
    if m:
        return m.group(1)
    m = re.search(r"\bonwheel\s*=\s*\{([^}]+)\}", list_s)
    return m.group(1) if m else ""


def _has_pin_cancel(jump: str, list_s: str) -> bool:
    """scrollDayHeadingToTop delayed write is cancellable; wheel cancels it."""
    pin = _fn(jump, "scrollDayHeadingToTop") or _fn(list_s, "scrollDayHeadingToTop")
    if not pin.strip():
        return False
    if not _DELAYED_PIN.search(pin):
        return False
    blob = jump + "\n" + list_s
    has_api = bool(_PIN_CANCEL_NAME.search(blob) or _PIN_TOKEN.search(blob))
    if not has_api:
        return False
    # Delayed path must consult the token / cancel flag before writeScrollTop.
    if not _PIN_GUARD_IN_FN.search(pin) and not _PIN_TOKEN.search(pin):
        return False
    # Still need a real comparison / early return, not only a param name.
    if not _PIN_GUARD_IN_FN.search(pin):
        # Accept cancelDayHeadingPin() polled inside the delayed callback.
        if not _PIN_CANCEL_NAME.search(pin) and not re.search(
            r"\b(?:cancelled|canceled|alive|stale)\b", pin
        ):
            return False
    wheel = _wheel_body(list_s)
    if not wheel.strip():
        return False
    # Expand one level of callees from wheel.
    expanded = wheel
    for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", wheel):
        inner = _fn(list_s, name) or _fn(jump, name)
        if inner:
            expanded += "\n" + inner
    if _PIN_CANCEL_NAME.search(expanded) or _PIN_TOKEN_BUMP.search(expanded):
        return True
    if _PIN_TOKEN.search(expanded) and re.search(
        r"\+\+|=\s*false|cancelled|canceled", expanded
    ):
        return True
    return False


def assert_jump_day_heading_stutter(crate: Path) -> None:
    """#311 fold: windowed measure adj + full-mount no scroll + pin cancel."""
    list_path = crate / "web" / "lib" / "TimelineList.svelte"
    if not list_path.is_file():
        fail(f"{_ISSUE}: TimelineList.svelte required (jump windowed hitch fold)")
    list_s = _list_src(crate)
    virt = _virt_src(crate)
    jump = _jump_src(crate)
    css = _css_src(crate)
    flush = _fn(list_s, "flushRowMeasures")
    surface = _flush_surface(list_s, virt)
    jump_fn = _fn(jump, "jumpToLocalDay") or _fn(jump, "jumpToDay") or jump

    # --- keep (already green) ---
    if not _VIRTUALIZE.search(virt) and not _VIRTUALIZE.search(list_s):
        fail(
            f"{_ISSUE}: keep #224 VIRTUALIZE_AFTER = 250 "
            "(do not turn virtualization off / Infinity)"
        )
    if not _EST88.search(virt) and not _EST88.search(list_s):
        fail(f"{_ISSUE}: keep constant ESTIMATED_ROW_HEIGHT = 88")
    if re.search(r"VIRTUALIZE_AFTER\s*=\s*(?:Infinity|1e9|99999)", virt + "\n" + list_s):
        fail(f"{_ISSUE}: keep VIRTUALIZE_AFTER = 250 — not Infinity")

    for rx in _FREEZE_MARKERS:
        if not rx.search(jump):
            fail(
                f"{_ISSUE}: keep freeze fold "
                "(shouldLoadOlderForJump / loadedDayRange / JUMP_DAY_PAGE_CAP)"
            )
    if not _SELECT_THEN_TICK.search(jump_fn) and not _SELECT_THEN_TICK.search(jump):
        fail(
            f"{_ISSUE}: keep freeze fold await tick() after selectPerson "
            "(jumpToLocalDay yield)"
        )

    # computeVisibleRange still full-mounts when total <= VIRTUALIZE_AFTER.
    # (TS return-type braces break _ts_fn_body — match the virt module text.)
    if not _FULL_RANGE.search(virt) and not _FULL_RANGE.search(list_s):
        fail(
            f"{_ISSUE}: keep computeVisibleRange full list when "
            "total <= VIRTUALIZE_AFTER (≤250 full mount)"
        )

    if not _ANCHOR_NONE.search(css) and not re.search(
        r"overflow-anchor\s*:\s*none", css
    ):
        fail(
            f"{_ISSUE}: keep spacer overflow-anchor: none "
            "(.timeline-spacer-top / .timeline-spacer-bottom in app.css)"
        )

    if not flush.strip():
        fail(
            f"{_ISSUE}: flushRowMeasures required — windowed prefix adj / "
            "full-mount no scrollTop live on the measure flush"
        )

    # 1) jump-day-windowed-adj
    if not _has_windowed_prefix_adj(flush, surface):
        fail(
            f"{_ISSUE}: when the filtered list is windowed "
            "(length > VIRTUALIZE_AFTER / > 250), measure flush must compute a "
            "scroll adj from old prefix sums (offsetOf / offsetAt / prefixFromMap) "
            "before writing rowHeights — first measure prev ?? ESTIMATED_ROW_HEIGHT "
            "(88); if oldTop < listScroll (scrollTop - tlChromeHeight) adj += h - prev; "
            "then writeScrollTop if adj !== 0 and not pinLatestObs "
            "(no querySelector / getBoundingClientRect for the above-viewport test; "
            "do not skip because userScrolling; helper scrollAdjForHeightChanges / "
            "prefixFromMap ok in TimelineVirtual.ts)"
        )

    # 2) jump-day-fullmount-no-scroll
    if not _has_fullmount_no_scroll(flush, surface):
        fail(
            f"{_ISSUE}: when length <= VIRTUALIZE_AFTER (full mount), measure must "
            "not write scrollTop / writeScrollTop (224-page) — adj / writeScrollTop "
            "in the flush must sit behind a > VIRTUALIZE_AFTER / > 250 / windowed check"
        )

    # 3) jump-day-pin-cancel
    if not _has_pin_cancel(jump, list_s):
        fail(
            f"{_ISSUE}: scrollDayHeadingToTop must be cancellable "
            "(generation / token); onTimelineWheel (wheel on #person-timeline) "
            "must call cancelDayHeadingPin / bump the token so the delayed "
            "tick + rAF writeScrollTop cannot yank after the user scrolls"
        )
