"""#379: timeline lightbox walks photos across messages.

Search preview stays the #118 same-message viewer. The gallery is untouched.
"""

from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root

_ISSUE = "#379"
_PRIMARY = (
    f"{_ISSUE}: thread lightbox is missing (data-thread-lightbox); "
    "next still stays on this message"
)
_HOMES = (
    "TimelinePane.svelte",
    "TimelineLightbox.svelte",
    "threadWalk.ts",
)


def _read(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _lib(crate: Path) -> Path:
    return crate / "web" / "lib"


def _thread_text(crate: Path) -> str:
    lib = _lib(crate)
    return "\n".join(_read(lib / name) for name in _HOMES)


def _button_tag(text: str, attr: str) -> str:
    for m in re.finditer(r"<button\b[^>]*>", text, re.S):
        if attr in m.group(0):
            return m.group(0)
    return ""


def _disabled_expr(tag: str) -> str:
    m = re.search(r"disabled=\{([^}]*)\}", tag)
    return m.group(1).strip() if m else ""


def assert_lightbox_thread(crate: Path) -> None:
    """#379: next/prev walk the filtered timeline; prev may load older."""
    thread = _thread_text(crate)
    if "data-thread-lightbox" not in thread:
        fail(_PRIMARY)

    rows = _read(_lib(crate) / "TimelineRows.svelte")
    if "data-thread-lightbox" in rows:
        fail(
            f"{_ISSUE}: host the overlay outside the virtual rows "
            "(not inside TimelineRows)"
        )
    if "onOpenImage" not in rows:
        fail(
            f"{_ISSUE}: a timeline photo opens the thread lightbox "
            "(onOpenImage), not only the in-bubble viewer"
        )

    search = _read(_lib(crate) / "SearchHits.svelte")
    if "data-thread-lightbox" in search or "onOpenImage" in search:
        fail(f"{_ISSUE}: Search preview stays a same-message lightbox")

    cas = _read(_lib(crate) / "CasAttach.svelte")
    if "data-photo-lightbox" not in cas or "%" not in cas:
        fail(
            f"{_ISSUE}: keep the #118 CasAttach viewer "
            "(data-photo-lightbox and same-message wrap)"
        )

    gallery = _read(_lib(crate) / "PersonMediaDialog.svelte")
    if "data-lightbox-next" in gallery or "data-lightbox-prev" in gallery:
        fail(f"{_ISSUE}: the media gallery does not gain thread arrows")

    if "message_id" not in thread or "attachment_id" not in thread:
        fail(
            f"{_ISSUE}: the open photo is message_id plus attachment_id "
            "(the same hash on two messages is two steps)"
        )
    if "filteredTimeline" not in thread:
        fail(f"{_ISSUE}: walk filteredTimeline order, not one bubble's items")
    if "casDataUrl" not in thread:
        fail(f"{_ISSUE}: the thread overlay loads the photo with casDataUrl")
    if re.search(r"[\"']https?://", thread):
        fail(f"{_ISSUE}: the thread lightbox must not use a remote http(s) URL")
    if "omitted" not in thread or "missing" not in thread:
        fail(f"{_ISSUE}: omitted and missing attachments are not steps")
    if not re.search(r"kind\s*===\s*[\"']sticker[\"']", thread):
        fail(f"{_ISSUE}: an image sticker is still a step (kind sticker)")
    if re.search(r"\bsrcs\s*\[", thread):
        fail(
            f"{_ISSUE}: membership is the stored attachment, "
            "not bytes already decoded on a mounted bubble"
        )
    if "%" in thread:
        fail(f"{_ISSUE}: thread next/prev do not wrap (%)")
    if "openPersonAtMessage" in thread and re.search(
        r"openPersonAtMessage[\s\S]{0,400}JUMP_DAY_PAGE_CAP"
        r"|JUMP_DAY_PAGE_CAP[\s\S]{0,400}openPersonAtMessage",
        thread,
    ):
        fail(f"{_ISSUE}: do not load the walk with openPersonAtMessage")

    cap_at = thread.find("JUMP_DAY_PAGE_CAP")
    if cap_at < 0:
        fail(
            f"{_ISSUE}: prev stops after JUMP_DAY_PAGE_CAP older pages "
            "(no toast)"
        )
    window = thread[max(0, cap_at - 900) : cap_at + 900]
    walk = _read(_lib(crate) / "threadWalk.ts")
    if "fetchPage" not in window:
        fail(
            f"{_ISSUE}: deep prev fetches older pages off the list, "
            "then the thread updates once"
        )
    if "selectPerson" in walk or "shiftHeightsForPrepend" in walk:
        fail(
            f"{_ISSUE}: the older-page loop must not call selectPerson "
            "or shift row heights on every page"
        )
    if "TIMELINE_PAGE_LIMIT" not in window and not re.search(r"\b80\b", window):
        fail(f"{_ISSUE}: a short older page stops the walk (TIMELINE_PAGE_LIMIT)")
    if "oldestCursor" not in window and "oldestSentAt" not in window:
        fail(f"{_ISSUE}: prev stops when there is no older cursor")
    if "showToast" in window or "showErr" in window:
        fail(f"{_ISSUE}: a prev miss stays quiet (no toast, no showErr)")
    if "alive" not in window:
        fail(f"{_ISSUE}: an in-flight prev stops when the person changes")
    if not re.search(
        r"if\s*\(\s*!append\s*\)\s*threadTarget\s*=\s*null",
        thread,
    ):
        fail(
            f"{_ISSUE}: a non-append reload closes the thread lightbox "
            "(if (!append) threadTarget = null); append does not"
        )

    if "data-lightbox-next" not in thread or "data-lightbox-prev" not in thread:
        fail(f"{_ISSUE}: the thread overlay has next and prev buttons")
    nxt = _button_tag(thread, "data-lightbox-next")
    prv = _button_tag(thread, "data-lightbox-prev")
    if "disabled=" not in nxt or _disabled_expr(nxt) in {"", "false"}:
        fail(f"{_ISSUE}: next is disabled on the newest loaded photo")
    prev_expr = _disabled_expr(prv)
    if "disabled=" not in prv or prev_expr in {"", "false", "true"}:
        fail(
            f"{_ISSUE}: prev is disabled only when older pages are exhausted"
        )
    if "oldestCursor" not in prev_expr and not re.search(
        rf"\b{re.escape(prev_expr)}\b[\s\S]{{0,600}}oldestCursor"
        rf"|oldestCursor[\s\S]{{0,600}}\b{re.escape(prev_expr)}\b",
        thread,
    ):
        fail(
            f"{_ISSUE}: prev stays enabled while oldestCursor can load "
            "another page (do not disable it only because this is index 0)"
        )

    if re.search(r"\btransition:", thread) or re.search(
        r"translate[XY]?\(", thread
    ):
        fail(f"{_ISSUE}: no swipe bounce and no new transition on the thread lightbox")

    pane = _read(_lib(crate) / "TimelinePane.svelte")
    if not re.search(r"seen\.has\([^)]*message_id", pane):
        fail(
            f"{_ISSUE}: an older page must not append a message_id "
            "already in the thread"
        )
    walk = _read(_lib(crate) / "threadWalk.ts")
    if walk.count("oldestCursor()") < 3:
        fail(
            f"{_ISSUE}: prev stops when an older page does not move oldestCursor"
        )
    if not re.search(r'<div class="[^"]*overflow-hidden[^"]*flex-col', pane):
        fail(
            f"{_ISSUE}: the thread column clips above the footer "
            "so a bubble cannot draw through it"
        )
    if "resetHeights" not in pane:
        fail(
            f"{_ISSUE}: after a thread prepend the row-height cache is remeasured"
        )

    docs = _read(repo_root() / "docs" / "user" / "app.md").lower()
    if "across messages" not in docs or "older" not in docs:
        fail(
            f"{_ISSUE}: docs/user/app.md must say the timeline lightbox "
            "walks photos across messages and prev loads older pages"
        )
