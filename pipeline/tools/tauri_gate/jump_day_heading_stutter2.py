"""#311 fold — jump windowed hitch after tick / keyed each / windowed anchor.

Sibling of jump_day_heading_stutter.py (420). Do not grow stutter / freeze /
review / heading modules. Lock: keyed windowed eaches; writeScrollTop after
tick() following rowHeights assign; windowed #person-timeline overflow-anchor
none. Keep VIRTUALIZE_AFTER / freeze / prefix adj / full-mount no scroll /
pin cancel.

Must-IDs: jump-day-keyed-each, jump-day-adj-after-tick,
jump-day-windowed-anchor, jump-day-keep-virtualize, jump-day-keep-freeze,
jump-day-keep-fullmount-range, jump-day-keep-adj, jump-day-keep-fullmount-no-scroll,
jump-day-keep-pin-cancel, jump-day-keep-est88, jump-day-keep-anchor.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.jump_day_heading import _ISSUE, _read
from tauri_gate.jump_day_heading_stutter import (
    _ANCHOR_NONE,
    _EST88,
    _FREEZE_MARKERS,
    _FULL_RANGE,
    _PREV_88,
    _SELECT_THEN_TICK,
    _VIRTUALIZE,
    _WINDOWED_GUARD,
    _fn,
    _has_fullmount_no_scroll,
    _has_pin_cancel,
    _has_windowed_prefix_adj,
    _list_src,
    _jump_src,
    _css_src,
    _virt_src,
    _flush_surface,
)
from tauri_gate.scan import _without_comments

_ROW_EACH_KEYED = re.compile(
    r"\{#each\s+(?:\w+\.)?rows\s+as\s+\w+\s*\(\s*"
    r"(?:\w+\.)?index\s*\)"
    r"|\{#each\s+group\.rows\s+as\s+item\s*\([^)]*index[^)]*\)"
)
_ROW_EACH_KEYED_LOOSE = re.compile(
    r"\{#each\s+(?:group\.)?rows\s+as\s+\w+\s*\([^)]*\bindex\b[^)]*\)"
)
_GROUP_KEY_OK = re.compile(
    r"\{#each\s+(?:windowedDayGroups|windowedGroups|visibleDayGroups|"
    r"virtualDayGroups|renderedDayGroups|dayGroups)\s+as\s+(\w+)\s*\(([^)]+)\)"
)
_ROW_HEIGHTS_ASSIGN = re.compile(r"\browHeights\s*=\s*(?:next|\{)")
_TICK_CALL = re.compile(r"\b(?:await\s+)?tick\s*\(\s*\)")
_ADJ_WRITE = re.compile(
    r"\bwriteScrollTop\s*\("
    r"|\.scrollTop\s*=\s*[^;\n]*\badj\b"
    r"|\.scrollTop\s*\+=\s*\badj\b"
    r"|\.scrollTop\s*=\s*[^;\n]*\+\s*adj\b"
)
_WINDOWED_CLASS = re.compile(
    r"\b(?:tl-windowed|is-windowed|tlWindowed)\b"
    r"|class:windowed\b"
    r"|class:tl-windowed\b"
)
_PANE_ANCHOR_NONE_CSS = re.compile(
    r"(?:"
    r"#person-timeline\.(?:tl-windowed|windowed|is-windowed)[^}]*"
    r"overflow-anchor\s*:\s*none"
    r"|\.(?:tl-windowed|windowed|is-windowed)[^}]*overflow-anchor\s*:\s*none"
    r"|#person-timeline[^}]*overflow-anchor\s*:\s*none"
    r")",
    re.I | re.S,
)
_STYLE_ANCHOR_NONE = re.compile(
    r"overflow-anchor\s*[:=]\s*['\"]?none"
    r"|overflowAnchor\s*[:=]\s*['\"]?none"
    r"|style\s*[:=]\s*\{[^}]*overflow-anchor[^}]*none",
    re.I,
)


def _rows_src(crate: Path) -> str:
    return _without_comments(_read(crate, "TimelineRows.svelte"))


def _has_keyed_eaches(blob: str) -> bool:
    """windowedDayGroups each keyed + group.rows each keyed by item.index."""
    gm = _GROUP_KEY_OK.search(blob)
    if not gm:
        return False
    key_expr = gm.group(2)
    if not key_expr.strip():
        return False
    # Prefer first-row index / group.key; any non-empty key expr still locks reuse.
    if not re.search(r"\w+", key_expr):
        return False
    if not (_ROW_EACH_KEYED.search(blob) or _ROW_EACH_KEYED_LOOSE.search(blob)):
        return False
    return True


def _flush_adj_write_after_tick(flush: str, list_s: str) -> bool:
    """After rowHeights = next, windowed writeScrollTop must follow tick()."""
    if not flush.strip():
        return False
    # Must still write scroll on the windowed adj path eventually.
    surface = flush
    if not _ADJ_WRITE.search(surface) and not _ADJ_WRITE.search(list_s):
        return False
    if not _WINDOWED_GUARD.search(flush) and not re.search(
        r"\bwindowed\b", flush
    ):
        return False

    rh = list(_ROW_HEIGHTS_ASSIGN.finditer(flush))
    if not rh:
        # Assign might be `rowHeights = next` only when changed — still required.
        return False

    # Prefer the assign that sits near scrollAdj / windowed adj.
    assign = rh[-1]
    after = flush[assign.end() :]

    # Sync write immediately after assign with no tick in between → fail.
    # Accept: await tick(); writeScrollTop / void tick().then(() => writeScrollTop)
    tick_m = _TICK_CALL.search(after)
    write_m = _ADJ_WRITE.search(after)

    if write_m and (not tick_m or write_m.start() < tick_m.start()):
        # Write before any tick after assign — the hitch bug.
        return False

    if tick_m:
        after_tick = after[tick_m.end() :]
        # tick().then(() => { writeScrollTop ... }) — write may be in arrow body
        # still in `after` via .then(
        if _ADJ_WRITE.search(after_tick):
            return True
        # void tick().then(() => writeScrollTop(...)) — write is after .then(
        then_m = re.search(
            r"\.then\s*\(\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_]\w*)\s*=>\s*\{?",
            after[tick_m.start() :],
        )
        if then_m:
            body = after[tick_m.start() + then_m.end() :]
            # Limit to a reasonable callback body window.
            window = body[:800]
            if _ADJ_WRITE.search(window):
                return True
        # await tick() then later write in same fn
        if re.search(r"await\s+tick\s*\(\s*\)", after) and _ADJ_WRITE.search(
            after[tick_m.end() :]
        ):
            return True

    # write only inside a nested helper scheduled with tick from flush
    if tick_m and re.search(
        r"tick\s*\(\s*\)\s*\.then|"
        r"void\s+tick\s*\(\s*\)|"
        r"await\s+tick\s*\(\s*\)",
        after,
    ):
        # Expand one level: callbacks named in .then(name) or following statements
        # that call writeScrollTop with adj.
        for name in re.findall(
            r"\.then\s*\(\s*([A-Za-z_]\w*)\s*\)|"
            r"\b([A-Za-z_]\w*)\s*\(\s*sc\s*,",
            after,
        ):
            n = name[0] or name[1]
            if not n:
                continue
            body = _fn(list_s, n)
            if body and _ADJ_WRITE.search(body):
                return True

    # No tick after assign at all.
    if not tick_m:
        return False
    return False


def _has_windowed_pane_anchor(list_s: str, rows: str, css: str) -> bool:
    """When windowed, #person-timeline is overflow-anchor: none (class or style)."""
    # Spacers already covered by keep-check; still require spacer none here soft.
    blob = list_s + "\n" + rows
    # Style binding path: overflow-anchor none tied to windowed / VIRTUALIZE.
    if re.search(
        r"(?:windowed|VIRTUALIZE_AFTER|isWindowed|tlWindowed)[^;]{0,120}"
        r"overflow-anchor[^;]{0,40}none"
        r"|overflow-anchor[^;]{0,40}none[^;]{0,120}"
        r"(?:windowed|VIRTUALIZE_AFTER|isWindowed|tlWindowed)"
        r"|style\s*=\s*\{[^}]{0,200}overflow-anchor[^}]{0,80}none",
        blob,
        re.I | re.S,
    ):
        return True

    # Class on #person-timeline + CSS none for that class.
    pane = None
    for m in re.finditer(
        r"<ScrollArea\b[^>]*\bid\s*=\s*[\"']person-timeline[\"'][^>]*>|"
        r"<[^>]*\bid\s*=\s*[\"']person-timeline[\"'][^>]*>",
        blob,
        re.I | re.S,
    ):
        pane = m.group(0)
        break
    if pane is None:
        # Multi-line ScrollArea attrs.
        m = re.search(
            r"<ScrollArea\b([\s\S]{0,400}?)\bid\s*=\s*[\"']person-timeline[\"']"
            r"([\s\S]{0,400}?)>",
            blob,
            re.I,
        )
        if m:
            pane = m.group(0)

    has_class = bool(
        pane
        and (
            _WINDOWED_CLASS.search(pane)
            or re.search(
                r"class:?(?:tl-windowed|windowed|is-windowed)\b|"
                r"class=\{[^}]*\b(?:tl-windowed|windowed|isWindowed)\b|"
                r"class=\{[^}]*windowed",
                pane,
            )
        )
    )
    # Class may be on a variable assembled nearby.
    if not has_class and re.search(
        r"(?:tl-windowed|class:tl-windowed|class:windowed)\b", blob
    ):
        # Must still touch person-timeline surface.
        if re.search(
            r"person-timeline[\s\S]{0,300}(?:tl-windowed|class:windowed)|"
            r"(?:tl-windowed|class:windowed)[\s\S]{0,300}person-timeline",
            blob,
        ):
            has_class = True

    css_none = bool(_PANE_ANCHOR_NONE_CSS.search(css))
    # If CSS sets #person-timeline { overflow-anchor: none } always, accept
    # as windowed-safe (full-mount may keep auto via override — optional).
    always_none = bool(
        re.search(
            r"#person-timeline\s*\{[^}]*overflow-anchor\s*:\s*none", css, re.I | re.S
        )
    )
    if always_none:
        return True
    if has_class and (
        css_none
        or re.search(
            r"\.(?:tl-windowed|windowed|is-windowed)[^}]*overflow-anchor\s*:\s*none",
            css,
            re.I | re.S,
        )
    ):
        return True
    # Inline style on the pane element.
    if pane and _STYLE_ANCHOR_NONE.search(pane):
        return True
    return False


def assert_jump_day_heading_stutter2(crate: Path) -> None:
    """#311 fold: keyed each + adj after tick + windowed pane anchor none."""
    list_path = crate / "web" / "lib" / "TimelineList.svelte"
    if not list_path.is_file():
        fail(f"{_ISSUE}: TimelineList.svelte required (jump windowed hitch stutter2)")
    list_s = _list_src(crate)
    rows = _rows_src(crate)
    virt = _virt_src(crate)
    jump = _jump_src(crate)
    css = _css_src(crate)
    flush = _fn(list_s, "flushRowMeasures")
    surface = _flush_surface(list_s, virt)
    markup = list_s + "\n" + rows
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
            f"{_ISSUE}: flushRowMeasures required — windowed adj after tick / "
            "keyed each / windowed anchor live with the measure flush"
        )

    if not _has_windowed_prefix_adj(flush, surface):
        fail(
            f"{_ISSUE}: keep windowed prefix adj "
            "(scrollAdjForHeightChanges / prev ?? ESTIMATED_ROW_HEIGHT / "
            "oldTop < listScroll) before rowHeights write"
        )
    if not _PREV_88.search(surface):
        fail(f"{_ISSUE}: keep first measure prev ?? ESTIMATED_ROW_HEIGHT (88)")

    if not _has_fullmount_no_scroll(flush, surface):
        fail(
            f"{_ISSUE}: keep full-mount measure no unguarded scrollTop — "
            "adj / writeScrollTop behind > VIRTUALIZE_AFTER / windowed"
        )

    if not _has_pin_cancel(jump, list_s):
        fail(
            f"{_ISSUE}: keep cancelDayHeadingPin on wheel "
            "(scrollDayHeadingToTop cancellable; onTimelineWheel cancels)"
        )

    # --- new (fail today) ---
    # 1) jump-day-keyed-each
    if not _has_keyed_eaches(markup):
        fail(
            f"{_ISSUE}: {{#each windowedDayGroups as group (…)}} must be keyed "
            f"(first row index or group.key) and {{#each group.rows as item "
            f"(item.index)}} keyed by item.index — unkeyed each reuses the wrong "
            "bubble when the window slides"
        )

    # 2) jump-day-adj-after-tick
    if not _flush_adj_write_after_tick(flush, list_s):
        fail(
            f"{_ISSUE}: windowed measure path must tick() after rowHeights = next "
            "and before that path's writeScrollTop (sync write immediately after "
            "assign leaves spacerTop unapplied) — accept "
            "void tick().then(() => writeScrollTop…) in flushRowMeasures"
        )

    # 3) jump-day-windowed-anchor
    if not _has_windowed_pane_anchor(list_s, rows, css):
        fail(
            f"{_ISSUE}: when windowed, #person-timeline must be "
            "overflow-anchor: none (class tl-windowed / windowed + CSS, or a "
            "style binding) so only the adj writes; spacers stay none; "
            "full-mount pane may keep auto"
        )
