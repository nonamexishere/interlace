"""#313 — quiet Latest overlay; reuse #113 pin.

Sibling overlay of #person-timeline (copy-menu pattern), not inside the
scroller, not window-fixed, not a Find/Jump chrome-bar button. Show when
not at the bottom; hide at the bottom (4px slop). Click / End reuse
pinTimelineLatest + watchPinLatest (600ms), then stop. Instant always.
Visible Latest via t() in en+tr. Keep findQ; cancel day pin; do not
clear chips. No Home. No palette item.

Must-IDs: latest-appears, latest-click-pin, latest-hide-at-bottom,
latest-reduced-motion, latest-locale. End is a confirmed SPEC_GAP fill.
Keep / not-unread / not-autostick / D24 live in scroll_to_latest_fold.py.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.find_in_conversation import _FIND_HOOK
from tauri_gate.import_boot_guards import _input_guard_span
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.scan import (
    _expand_fn_calls,
    _function_body,
    _open_tag_before,
    _svelte_markup,
    _ts_fn_body,
    _without_comments,
)
from tauri_gate.timeline_latest import _derived_body
from tauri_gate.timeline_rows_lib import _SEARCH_TYPE_DATE

_ISSUE = "#313"
_PANE = ("TimelineList.svelte", "TimelinePane.svelte")
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][\w]*)["']""")
_LATEST_TEXT = re.compile(r">\s*Latest\s*<")
_ONCLICK = re.compile(
    r"(?:on:click|onclick)\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}",
    re.S,
)
_AT_FLAG = re.compile(
    r"\b(?:showLatest|atBottom|tlAtBottom|atTlBottom|latestVisible|"
    r"showScrollLatest|scrolledFromLatest|notAtBottom|tlShowLatest)\b"
)
_SLOP = re.compile(
    r"scrollTop\s*\+\s*(?:[\w.]+\.)?clientHeight\s*[<>]=?\s*"
    r"(?:[\w.]+\.)?scrollHeight\s*-\s*4"
    r"|(?:[\w.]+\.)?scrollHeight\s*-\s*4"
)
_PIN = re.compile(r"\bpinTimelineLatest\b")
_WATCH = re.compile(r"\bwatchPinLatest\b")
_ENSURE = re.compile(r"\bensureTlIndexVisible\b")
_HEIGHT = re.compile(
    r"scrollTop\s*=\s*[^;\n]*scrollHeight"
    r"|writeScrollTop\s*\([^)]*scrollHeight"
)
_SMOOTH = re.compile(r"""behavior\s*:\s*["']smooth["']""")
_END = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']End[\"']|[\"']End[\"']\s*===?\s*(?:e\.)?key"
)
_HOME = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']Home[\"']|[\"']Home[\"']\s*===?\s*(?:e\.)?key"
)
_FIND_CLEAR = re.compile(r"""findQ\s*=\s*(?:["']{2}|""|'')""")
_CLEAR_CHIPS = re.compile(
    r"""platformFilter\s*=\s*["']all["']|kindFilter\s*=\s*["']all["']"""
)
_CANCEL_DAY = re.compile(r"\b(?:cancelDayHeadingPin|onClearDayPin)\b")
_FIELD = re.compile(
    r"tagName\s*===?\s*[\"']INPUT[\"']"
    r"|#tl-find|id\s*===?\s*[\"']tl-find[\"']|id\s*===?\s*[\"']q[\"']"
    r"|getElementById\s*\(\s*[\"']q[\"']"
    r"|data-tl-find|contentEditable|isContentEditable"
)
_FIXED = re.compile(r"""(?:^|[\s"'])fixed(?:[\s"']|$)|position\s*:\s*fixed""")
_ABS = re.compile(r"""(?:^|[\s"'])absolute(?:[\s"']|$)|position\s*:\s*absolute""")
_REL = re.compile(r"""(?:^|[\s"'])relative(?:[\s"']|$)""")
_PIN_NAMES = (
    "scrollToLatest",
    "goToLatest",
    "onLatestClick",
    "handleLatest",
    "pinTimelineLatest",
    "watchPinLatest",
    "applyOpenPersonWindow",
    "syncOpenPersonScroll",
)


def _read(crate: Path, rel: str) -> str:
    p = crate / "web" / "lib" / rel
    return p.read_text() if p.is_file() else ""


def _fn(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name) or ""


def _en_latest_keys(en: dict[str, str]) -> list[str]:
    return [k for k, v in en.items() if v.strip() == "Latest"]


def _latest_hits(markup: str, keys: list[str]) -> list[int]:
    hits = [m.start() for m in _LATEST_TEXT.finditer(markup)]
    for k in keys:
        hits.extend(
            m.start()
            for m in re.finditer(rf"""\bt\s*\(\s*["']{re.escape(k)}["']""", markup)
        )
    return sorted(set(hits))


def _scroller_span(markup: str) -> tuple[int, int] | None:
    m = re.search(
        r"<ScrollArea\b[\s\S]{0,500}?id\s*=\s*"
        r"(?:[\"']person-timeline[\"']|\{[\"']person-timeline[\"']\})",
        markup,
        re.I,
    )
    if not m:
        return None
    start = markup.rfind("<ScrollArea", 0, m.end())
    if start < 0:
        start = m.start()
    end = markup.find("</ScrollArea>", m.end())
    if end < 0:
        return (start, m.end())
    return (start, end + len("</ScrollArea>"))


def _find_row_span(pane_m: str) -> tuple[int, int] | None:
    m = re.search(r"""id\s*=\s*[\"']tl-find[\"']""", pane_m)
    if not m:
        return None
    start = pane_m.rfind("<div", 0, m.start())
    if start < 0:
        start = m.start()
    end = pane_m.find("</div>", m.end())
    if end < 0:
        return (start, m.end())
    return (start, end + 6)


def _inside(span: tuple[int, int] | None, pos: int) -> bool:
    return bool(span and span[0] <= pos < span[1])


def _tag_at(markup: str, pos: int) -> str:
    found = _open_tag_before(markup, pos)
    return found[1] if found else ""


def _near(markup: str, pos: int, n: int = 360) -> str:
    return markup[max(0, pos - n) : pos + n]


def _click_blob(markup: str, src: str, pos: int) -> str:
    blob = _tag_at(markup, pos) + "\n" + _near(markup, pos, 240)
    m = _ONCLICK.search(blob)
    expr = (m.group(1) or "").strip() if m else ""
    if not expr:
        return ""
    ident = re.fullmatch(r"([A-Za-z_][\w]*)", expr)
    body = _fn(src, ident.group(1)) if ident else expr
    extra = "\n".join(_fn(src, n) for n in _PIN_NAMES)
    return _expand_fn_calls(src, (body or expr) + "\n" + extra, 3)


def _is_pin_path(blob: str) -> bool:
    return bool(_WATCH.search(blob) and (_PIN.search(blob) or _HEIGHT.search(blob)))


def _slop_for_visibility(src: str) -> bool:
    for m in _AT_FLAG.finditer(src):
        if _SLOP.search(src[max(0, m.start() - 280) : m.end() + 280]):
            return True
    for name in (
        "showLatest",
        "atBottom",
        "tlAtBottom",
        "atTlBottom",
        "latestVisible",
        "notAtBottom",
        "tlShowLatest",
    ):
        body = _derived_body(src, name) or ""
        if body and _SLOP.search(body):
            return True
    return False


def _gated(markup: str, pos: int) -> bool:
    before = markup[max(0, pos - 420) : pos]
    if re.search(
        r"\{#if\s+[^}]*\b(?:showLatest|atBottom|tlAtBottom|notAtBottom|"
        r"latestVisible|tlShowLatest|scrolledFromLatest)\b",
        before,
    ):
        return True
    tag = _tag_at(markup, pos)
    return bool(
        re.search(
            r"\b(?:hidden|invisible|opacity-0|showLatest|atBottom|tlAtBottom|"
            r"notAtBottom|latestVisible|tlShowLatest)\b",
            tag,
        )
    )


def _end_skips_fields(src: str, pos: int) -> bool:
    guard = _input_guard_span(src)
    if guard and guard[0] < pos and guard[1] <= pos:
        return True
    window = src[max(0, pos - 420) : pos + 420]
    if _FIELD.search(window):
        return True
    return bool(re.search(r"person-timeline", window))


def _end_on_timeline(src: str, pos: int) -> bool:
    window = src[max(0, pos - 700) : pos + 200]
    if re.search(r"person-timeline", window):
        return True
    if re.search(r"view\s*!==?\s*[\"']people[\"']", src[:pos]):
        return True
    return bool(re.search(r"\bselectedId\b", window))


def assert_scroll_to_latest(crate: Path) -> None:
    """#313: overlay Latest; click / End reuse the #113 pin."""
    list_path = crate / "web" / "lib" / "TimelineList.svelte"
    pane_path = crate / "web" / "lib" / "TimelinePane.svelte"
    if not list_path.is_file():
        fail(f"{_ISSUE}: TimelineList.svelte required (Latest overlay + #113 pin)")
    if not pane_path.is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (find / jump stay; End / day pin)")
    lst = list_path.read_text()
    pane = pane_path.read_text()
    list_c = _without_comments(lst)
    pane_c = _without_comments(pane)
    list_m = _svelte_markup(lst)
    pane_m = _svelte_markup(pane)
    keys_c = _without_comments(_read(crate, "PeopleKeys.ts"))
    pal = _read(crate, "CommandPalette.svelte")
    pal_m = _svelte_markup(pal)
    app = _without_comments(_read(crate, "../App.svelte"))
    en_p = crate / "web" / "lib" / "locales" / "en.ts"
    tr_p = crate / "web" / "lib" / "locales" / "tr.ts"
    en = _chrome_pack_entries(en_p.read_text()) if en_p.is_file() else {}
    tr = _chrome_pack_entries(tr_p.read_text()) if tr_p.is_file() else {}
    latest_keys = _en_latest_keys(en)
    src = list_c + "\n" + pane_c + "\n" + keys_c
    list_hits = _latest_hits(list_m, latest_keys)
    pane_hits = _latest_hits(pane_m, latest_keys)

    # 1) latest-appears
    if not list_hits and not pane_hits:
        fail(
            f"{_ISSUE}: quiet Latest control required on the person timeline "
            "after you scroll up (sibling overlay, not inside "
            "#person-timeline scroll content)"
        )

    # 2) placement — sibling overlay, not scroller, not chrome-bar, not fixed.
    scroller = _scroller_span(list_m)
    find_row = _find_row_span(pane_m)
    tl_at = pane_m.find("<TimelineList")
    chrome_span = (0, tl_at) if tl_at >= 0 else None
    placed = False
    for pos in list_hits:
        if _inside(scroller, pos):
            fail(
                f"{_ISSUE}: Latest must not sit inside #person-timeline "
                "scroll content (sibling overlay — copy-menu pattern)"
            )
        tag = _tag_at(list_m, pos) + _near(list_m, pos, 200)
        if _FIXED.search(tag):
            fail(
                f"{_ISSUE}: Latest is a pane overlay — not position:fixed "
                "on the window (do not steal the toast stack)"
            )
        if _ABS.search(tag) and (
            _REL.search(_near(list_m, pos, 700)) or _REL.search(list_m[:pos][-400:])
        ):
            placed = True
        elif pos > (scroller[1] if scroller else 0):
            placed = True
    for pos in pane_hits:
        if _inside(find_row, pos) or _inside(chrome_span, pos):
            fail(
                f"{_ISSUE}: Latest is a sibling overlay on the pane "
                "(copy-menu pattern) — not a chrome-bar button next to "
                "Find / Jump"
            )
        tag = _tag_at(pane_m, pos) + _near(pane_m, pos, 200)
        if _FIXED.search(tag):
            fail(
                f"{_ISSUE}: Latest is a pane overlay — not position:fixed "
                "on the window (do not steal the toast stack)"
            )
        if _ABS.search(tag) and _REL.search(_near(pane_m, pos, 700)):
            placed = True
    if not placed:
        fail(
            f"{_ISSUE}: Latest must be a sibling overlay of #person-timeline "
            "(parent relative, control absolute — copy-menu / pane overlay "
            "pattern; not inside the scroller)"
        )

    # 3) latest-hide-at-bottom — 4px slop; derive hide from at-bottom.
    if not _slop_for_visibility(src):
        fail(
            f"{_ISSUE}: at-bottom is scrollTop + clientHeight >= "
            "scrollHeight - 4 (same slop as today’s pinLatest cancel); "
            "derive Latest hide from that — no sticky show flag"
        )
    if not any(_gated(list_m, p) for p in list_hits) and not any(
        _gated(pane_m, p) for p in pane_hits
    ):
        fail(
            f"{_ISSUE}: Latest must show when the pane is not at the bottom "
            "and hide when it is (including a short thread that already fits)"
        )

    # 4) latest-click-pin — #113 pin, not ensureTlIndexVisible alone.
    clicks = [_click_blob(list_m, src, p) for p in list_hits] + [
        _click_blob(pane_m, src, p) for p in pane_hits
    ]
    click = "\n".join(c for c in clicks if c)
    named = "\n".join(_fn(src, n) for n in _PIN_NAMES)
    pin_blob = click + "\n" + named
    if not click.strip() or not _is_pin_path(pin_blob):
        fail(
            f"{_ISSUE}: clicking Latest must reuse the #113 pin "
            "(pinTimelineLatest + watchPinLatest, 600ms settle, then stop) "
            "— scrollTop = scrollHeight, not ensureTlIndexVisible alone "
            "and not a new last-row seek"
        )
    if _ENSURE.search(click) and not _is_pin_path(click + "\n" + named):
        fail(
            f"{_ISSUE}: do not use ensureTlIndexVisible as the Latest path "
            "(that nudges a row; Acceptance is the newest bubble above the footer)"
        )
    if re.search(r"timeline-end|lastElementChild|scrollIntoView", click) and not _HEIGHT.search(
        pin_blob
    ):
        fail(
            f"{_ISSUE}: newest row is the last filtered / rendered list "
            "(scrollHeight / spacers) — not #timeline-end / last article"
        )
    if _FIND_CLEAR.search(click) or _FIND_CLEAR.search(named):
        fail(f"{_ISSUE}: keep findQ on Latest click (only move the viewport)")
    if not (
        re.search(r"\bcancelDayHeadingPin\b", pin_blob)
        and re.search(r"\bonClearDayPin\b", pin_blob)
    ):
        fail(
            f"{_ISSUE}: Latest click (and End) must cancel the day pin "
            "(cancelDayHeadingPin / onClearDayPin)"
        )
    if _CLEAR_CHIPS.search(click) or _CLEAR_CHIPS.search(named):
        fail(
            f"{_ISSUE}: newest row is the last filtered / rendered list — "
            "do not clear platform / kind chips"
        )

    # 5) latest-reduced-motion — instant always; fade uses chromeMotionMs.
    motion_src = click + "\n" + named + "\n" + list_c
    if _SMOOTH.search(motion_src):
        fail(
            f"{_ISSUE}: Latest scroll stays instant always "
            '(no behavior: "smooth"; reduced motion is already duration 0)'
        )
    fade_hit = False
    for pos in list_hits + pane_hits:
        mk = list_m if pos in list_hits else pane_m
        if re.search(r"\b(?:transition|in|out)\s*:\s*(?:fade|fly|slide)\b", _near(mk, pos, 280)):
            fade_hit = True
    if fade_hit and "chromeMotionMs" not in (list_c + "\n" + pane_c):
        fail(
            f"{_ISSUE}: if the Latest control fades, use chromeMotionMs() "
            "(0 when reduced)"
        )
    motion = _read(crate, "motion.ts")
    if "chromeMotionMs" not in motion or "prefersReducedMotion" not in motion:
        fail(f"{_ISSUE}: keep chromeMotionMs / prefersReducedMotion (#222)")

    # 6) latest-locale — visible Latest via t() in en+tr; no third pack.
    used = set(_T_CALL.findall(list_m + "\n" + pane_m))
    wired = [k for k in latest_keys if k in used]
    if not wired:
        fail(
            f"{_ISSUE}: visible Latest copy must use t() in en.ts + tr.ts "
            "(#131; no hardcoded English; no third pack)"
        )
    for k in wired:
        if k not in tr or not str(tr[k]).strip():
            fail(
                f"{_ISSUE}: Latest key {k!r} must exist in en.ts and tr.ts "
                "(#131; no third pack)"
            )
    loc = crate / "web" / "lib" / "locales"
    extra = [
        p.name
        for p in loc.iterdir()
        if p.is_file() and p.suffix in {".ts", ".json"} and p.stem not in {"en", "tr"}
    ]
    if extra:
        fail(f"{_ISSUE}: no third locale pack ({', '.join(sorted(extra))})")

    # 7) End — same pin when the timeline is focused; not while a field types.
    end_src = keys_c + "\n" + list_c + "\n" + pane_c + "\n" + app
    end_m = _END.search(end_src)
    if not end_m:
        fail(
            f"{_ISSUE}: End must call the same pin when the person timeline "
            "is focused (not a palette item)"
        )
    end_blob = _expand_fn_calls(
        src + "\n" + app,
        end_src[max(0, end_m.start() - 200) : end_m.end() + 400] + "\n" + named,
        3,
    )
    if not _is_pin_path(end_blob):
        fail(
            f"{_ISSUE}: End must call the same pin as Latest "
            "(pinTimelineLatest + watchPinLatest)"
        )
    if not _end_skips_fields(end_src, end_m.start()):
        fail(
            f"{_ISSUE}: do not fire End while #tl-find, #q, or another field "
            "is the target"
        )
    if not _end_on_timeline(end_src, end_m.start()):
        fail(
            f"{_ISSUE}: End calls the same pin when the timeline is focused "
            "(people + open person / #person-timeline — not every view)"
        )
    if not (
        re.search(r"\bcancelDayHeadingPin\b", end_blob)
        or re.search(r"\bonClearDayPin\b", end_blob)
    ):
        fail(f"{_ISSUE}: End must cancel the day pin (cancelDayHeadingPin / onClearDayPin)")
    for hm in _HOME.finditer(end_src):
        home_blob = _expand_fn_calls(
            src,
            end_src[max(0, hm.start() - 160) : hm.end() + 240] + "\n" + named,
            2,
        )
        if _is_pin_path(home_blob) or re.search(r"\bscrollToLatest\b", home_blob):
            fail(f"{_ISSUE}: no Home key — End only")
    if _LATEST_TEXT.search(pal_m) or any(
        re.search(rf"""\bt\s*\(\s*["']{re.escape(k)}["']""", pal) for k in latest_keys
    ):
        fail(f"{_ISSUE}: no palette Latest item (End + the overlay only)")
    if re.search(r"\b(?:scrollToLatest|jumpToLatest|goToLatest)\b", pal):
        fail(f"{_ISSUE}: no palette Latest item")
    if not _FIND_HOOK.search(pane_m) or not _SEARCH_TYPE_DATE.search(pane_m):
        fail(f"{_ISSUE}: keep #310 find + #311 jump-to-day (do not steal those controls)")
    if re.search(r"/Users/|/home/", list_c + "\n" + pane_c):
        fail(f"{_ISSUE}: tests stay placeholders (Ada) — no real home paths")
