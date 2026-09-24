"""#418 — one window around a message_id.

Day and year resolve the earliest message on that local day, then call
openPersonAtMessage and pinJump. Search keeps the #403 bound. Quote fold,
last-read, Latest, and Load older stay off that day path.

Placeholders Ada / Berk / Self only. No message bodies.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.scan import _without_comments
from tauri_gate.search_jump_onscreen import _fn

_ISSUE = "#418"
_LOOKUP = "personDayMessage"


def _read(crate: Path, rel: str) -> str:
    path = crate / "web" / rel if rel.startswith("App.svelte") else crate / "web" / "lib" / rel
    return path.read_text() if path.is_file() else ""


def _order(body: str, *needles: str) -> bool:
    at = 0
    for needle in needles:
        found = body.find(needle, at)
        if found < 0:
            return False
        at = found + len(needle)
    return True


def assert_around_message(crate: Path) -> None:
    """#418: day jump order is personDayMessage, then openPersonAtMessage, then pinJump."""
    pane = _without_comments(_read(crate, "TimelinePane.svelte"))
    app = _without_comments(_read(crate, "App.svelte"))
    rows = _without_comments(_read(crate, "TimelineRows.svelte"))
    hits = _without_comments(_read(crate, "SearchHits.svelte"))
    search = _without_comments(_read(crate, "SearchPane.svelte"))
    gallery = _without_comments(_read(crate, "PersonMediaDialog.svelte"))
    keys = _without_comments(_read(crate, "PeopleKeys.ts"))
    lst = _without_comments(_read(crate, "TimelineList.svelte"))
    if not pane or not app:
        fail(f"{_ISSUE}: TimelinePane.svelte and App.svelte are required")

    opened = _fn(pane, "openPersonAtMessage")
    newer = _fn(pane, "loadNewerPage")
    select = _fn(pane, "selectPerson")
    day = _fn(pane, "goToJumpDay")
    last = _fn(pane, "goToLastRead")
    jump = _fn(app, "jumpToMessage")
    activate = _fn(search, "activateHit")
    show = _fn(gallery, "showInTimeline")
    scroll = _fn(lst, "scrollToLatest")

    if "openPersonAtMessage" not in jump or "onJumpToMessage" not in activate:
        fail(f"{_ISSUE}: Search Enter stays jumpToMessage → openPersonAtMessage")
    if not opened or "pageLimit = 200" not in opened or "maxPages = 80" not in opened:
        fail(f"{_ISSUE}: Search keeps the #403 older walk (page 200, cap 80)")
    if not re.search(r"\$\{seekAt\}~|seekAt\s*\+\s*[\"']~[\"']", opened):
        fail(f"{_ISSUE}: Search keeps before: sentAt~")
    if opened.count("after:") != 1 or "limit: TIMELINE_PAGE_LIMIT" not in opened:
        fail(f"{_ISSUE}: Search keeps one newer page of TIMELINE_PAGE_LIMIT")
    if not newer or "personTimeline" not in newer or "after:" not in newer:
        fail(f"{_ISSUE}: loadNewerPage stays the only way past that newer page")
    if "showErr" in newer or "showToast" in newer or "showToast" in opened:
        fail(f"{_ISSUE}: an empty newer page must not toast")
    if "loaded.concat(added.toReversed())" not in opened:
        fail(f"{_ISSUE}: an empty newer page concatenates nothing")
    if not re.search(r"idx\s*<\s*0", opened) or opened.find("showErr") < opened.find("idx < 0"):
        fail(f"{_ISSUE}: showErr stays on a missed id, not on an empty newer page")
    if "if (!fresh.length) return" not in newer or "timeline.concat(fresh.toReversed())" not in newer:
        fail(f"{_ISSUE}: loadNewerPage must not invent a row when the page is empty")
    if not scroll or "openPersonAtMessage" in scroll or "selectPerson" in scroll:
        fail(f"{_ISSUE}: Latest must not call the jump")
    if 'e.key === "End"' not in keys or "scrollToLatest" not in keys or "openPersonAtMessage" in keys:
        fail(f"{_ISSUE}: End stays scrollToLatest and must not call the jump")
    if "added.concat(timeline)" not in select or "tlIndex +=" not in select:
        fail(f"{_ISSUE}: Load older still prepends and shifts tlIndex")
    if "shiftHeightsForPrepend" not in select or not re.search(
        r"if \(append\) \{.*?shiftHeightsForPrepend.*?\} else \{\s*list\?\.resetHeights",
        select,
        re.S,
    ):
        fail(f"{_ISSUE}: Load older prepends with shiftHeightsForPrepend and without resetHeights")
    if "openPersonAtMessage" in rows or "openPersonAtMessage" in hits or "data-show-quoted" not in rows:
        fail(f"{_ISSUE}: Show quoted stays a fold and must not call openPersonAtMessage")
    if not last or "jumpToMessageId" not in last or "openPersonAtMessage" in last:
        fail(f"{_ISSUE}: goToLastRead still uses jumpToMessageId")
    if not re.search(
        r"openPersonAtMessage\s*\(\s*selectedId\s*,\s*row\.message_id\s*,\s*row\.sent_at\s*\)",
        show,
    ):
        fail(f"{_ISSUE}: media showInTimeline still calls openPersonAtMessage")

    if (
        not day
        or "jumpToLocalDay" in day
        or "pinDayAtTop" in day
        or not _order(day, _LOOKUP, "openPersonAtMessage", "pinJump")
    ):
        fail(
            f"{_ISSUE}: goToJumpDay still calls jumpToLocalDay / pinDayAtTop "
            f"and does not call {_LOOKUP}, then openPersonAtMessage, then pinJump"
        )
