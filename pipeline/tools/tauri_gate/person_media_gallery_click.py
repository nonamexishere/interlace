"""#361 click — per-open overlay token + one overlay field.

Sibling of person_media_gallery_race.py (do not grow that file). One
review bug only. Do not reopen the #361 mix, the video-stack / scroll
folds, or the race galleryGen / open-gate.

openPhoto / openVideo only skip the overlay assign when
gen !== galleryGen || !open. galleryGen does not change on another
cell click. Videos skip windowed prefetch, so every video click
awaits. Click video A, then photo B (B usually already in srcs):
when A's bytes return, videoSrc is set without clearing lightboxSrc.

Must-IDs: gallery-overlay-click-gen, gallery-overlay-one.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.person_media_gallery_race import (
    _PHOTO_NAMES,
    _VIDEO_NAMES,
    _click_path,
    _cond_has_gen_eq,
    _cond_has_gen_ne,
    _enclosing_if_conds,
    _first_await_cas,
    _if_return_conds,
    _non_null_assigns,
    _same_block_prefix,
)
from tauri_gate.scan import _js_next, _match_closer, _without_comments


_ISSUE = "#361"

_CLICK_COUNTER = r"overlayGen|clickGen|openGen|cellGen|overlayToken"
_INC_CAPTURE = re.compile(
    r"(?:const|let|var)\s+(\w+)\s*=\s*(?:\+\+\s*("
    + _CLICK_COUNTER
    + r")|("
    + _CLICK_COUNTER
    + r")\s*\+\+|("
    + _CLICK_COUNTER
    + r")\s*\+=\s*1)"
)
_INC_STMT = re.compile(
    r"\+\+\s*("
    + _CLICK_COUNTER
    + r")|("
    + _CLICK_COUNTER
    + r")\s*\+\+|("
    + _CLICK_COUNTER
    + r")\s*\+=\s*1"
)
_CAPTURE_CLICK = re.compile(
    r"(?:const|let|var)\s+(\w+)\s*=\s*(" + _CLICK_COUNTER + r")\b"
)
_WANTED_NAME = (
    r"(?:overlay)?wanted(?:Hash|Cas|CasHash)?"
    r"|overlayHash|wantedOverlay|wantedCas"
)
_WANTED_WRITE = re.compile(rf"(?<![.\w])({_WANTED_NAME})\s*=")
_CLOSE_OVERLAYS = re.compile(r"\bcloseOverlays\s*\(")
_OTHER_ID = r"(?!null\b|undefined\b|true\b|false\b)[\w.]+"


def _outer_prefix(body: str, at: int) -> str:
    """Text before the first block that contains `at` (top-level of the fn)."""
    if at < 0:
        return body
    i = 0
    while i < at:
        nxt = _js_next(body, i)
        if nxt != i:
            i = nxt
            continue
        if body[i] == "{":
            close = _match_closer(body, i)
            if close < 0:
                break
            if close >= at:
                return body[:i]
            i = close + 1
            continue
        i += 1
    return body[:at]


def _click_inc_capture(prefix: str) -> tuple[str, str] | None:
    """`(local, overlayGen)` when the prefix increments and snapshots it."""
    m = _INC_CAPTURE.search(prefix)
    if m:
        return m.group(1), m.group(2) or m.group(3) or m.group(4)
    inc = _INC_STMT.search(prefix)
    if not inc:
        plus = re.search(
            rf"\b({_CLICK_COUNTER})\s*=\s*\1\s*\+\s*1",
            prefix,
        )
        if not plus:
            return None
        counter = plus.group(1)
    else:
        counter = next(g for g in inc.groups() if g)
    cap = _CAPTURE_CLICK.search(prefix)
    if cap and cap.group(2) == counter:
        return cap.group(1), counter
    return None


def _wanted_write(prefix: str) -> str | None:
    """Component-level wanted hash write (not `const hash = row.cas_hash`)."""
    for m in _WANTED_WRITE.finditer(prefix):
        before = prefix[: m.start()]
        if re.search(r"(?:const|let|var)\s+$", before):
            continue
        return m.group(1)
    return None


def _click_token_guarded(body: str, pos: int, local: str, counter: str) -> bool:
    wraps = _enclosing_if_conds(body, pos)
    if any(_cond_has_gen_eq(c, local, counter) for c in wraps):
        return True
    rets = _if_return_conds(_same_block_prefix(body, pos))
    return any(_cond_has_gen_ne(c, local, counter) for c in rets)


def _wanted_guarded(body: str, pos: int, wanted: str) -> bool:
    eq = re.compile(
        rf"\b{re.escape(wanted)}\s*===?\s*{_OTHER_ID}"
        rf"|{_OTHER_ID}\s*===?\s*{re.escape(wanted)}\b"
    )
    ne = re.compile(
        rf"\b{re.escape(wanted)}\s*!==?\s*{_OTHER_ID}"
        rf"|{_OTHER_ID}\s*!==?\s*{re.escape(wanted)}\b"
    )
    wraps = _enclosing_if_conds(body, pos)
    if any(eq.search(c) for c in wraps):
        return True
    rets = _if_return_conds(_same_block_prefix(body, pos))
    return any(ne.search(c) for c in rets)


def _assign_sites(body: str, dest: str) -> tuple[int, list[int]]:
    await_at = _first_await_cas(body)
    assigns = _non_null_assigns(body, dest)
    if await_at >= 0:
        posts = [p for p in assigns if p > await_at]
        return await_at, posts
    return await_at, assigns


def _click_gen_why(body: str, dest: str) -> str | None:
    """None if the click path bumps a per-open token and skips a stale assign."""
    if not body.strip():
        return "missing"
    await_at, posts = _assign_sites(body, dest)
    if not posts:
        return "assign"
    at = await_at if await_at >= 0 else posts[0]
    prefix = _outer_prefix(body, at)
    token = _click_inc_capture(prefix)
    wanted = _wanted_write(prefix)
    if not token and not wanted:
        return "token"
    for pos in posts:
        ok = False
        if token:
            local, counter = token
            ok = _click_token_guarded(body, pos, local, counter)
        if not ok and wanted:
            ok = _wanted_guarded(body, pos, wanted)
        if not ok:
            return "guard"
    return None


def _same_block_suffix(body: str, pos: int) -> str:
    same = _same_block_prefix(body, pos)
    enclosing = pos - len(same)
    if enclosing >= 0 and enclosing < len(body) and body[enclosing] == "{":
        end = _match_closer(body, enclosing)
        if end > pos:
            return body[pos:end]
    return body[pos:]


def _post_await_prefix(body: str, await_at: int, pos: int) -> str:
    same = _same_block_prefix(body, pos)
    enclosing = pos - len(same)
    if await_at < enclosing:
        return same
    return same[await_at - enclosing :]


def _one_overlay_ok(body: str, dest: str, other: str) -> bool:
    """Post-await dest assign is paired with closeOverlays or other = null."""
    if not body.strip():
        return False
    await_at, posts = _assign_sites(body, dest)
    if not posts:
        return False
    other_null = re.compile(
        rf"\b{re.escape(other)}\s*=\s*(?:null|undefined|\"\"|'')"
    )
    for pos in posts:
        if await_at >= 0:
            region = _post_await_prefix(body, await_at, pos)
        else:
            region = _same_block_prefix(body, pos)
        if _CLOSE_OVERLAYS.search(region) or other_null.search(region):
            continue
        if other_null.search(_same_block_suffix(body, pos)):
            continue
        return False
    return True


def assert_person_media_gallery_click(crate: Path) -> None:
    """#361 click: per-open token + only one overlay field after a successful open."""
    dlg_path = crate / "web" / "lib" / "PersonMediaDialog.svelte"
    if not dlg_path.is_file():
        fail(
            f"{_ISSUE}: PersonMediaDialog.svelte required "
            "(openPhoto / openVideo must increment overlayGen or set "
            "wanted cas_hash before await casDataUrl and skip a stale "
            "lightboxSrc / videoSrc assign)"
        )
    dlg_raw = dlg_path.read_text()
    dlg = _without_comments(dlg_raw)

    photo_name, photo = _click_path(dlg, "lightboxSrc", _PHOTO_NAMES)
    if not photo:
        photo_name, photo = _click_path(dlg_raw, "lightboxSrc", _PHOTO_NAMES)
    video_name, video = _click_path(dlg, "videoSrc", _VIDEO_NAMES)
    if not video:
        video_name, video = _click_path(dlg_raw, "videoSrc", _VIDEO_NAMES)

    # --- gallery-overlay-click-gen (primary red today) ---
    for name, body, dest, kind in (
        (video_name, video, "videoSrc", "video"),
        (photo_name, photo, "lightboxSrc", "photo"),
    ):
        why = _click_gen_why(body, dest)
        if not why:
            continue
        other = "lightboxSrc" if kind == "video" else "videoSrc"
        overlay = "#271 overlay" if kind == "video" else "#118 lightbox"
        if why == "missing":
            fail(
                f"{_ISSUE}: {name} required — increment overlayGen "
                f"(or set wanted cas_hash) before await casDataUrl and "
                f"skip {dest} when that token/hash is stale "
                f"(another cell click must not leave an in-flight "
                f"{overlay} able to assign {dest} after {other} is set)"
            )
        if why == "assign":
            fail(
                f"{_ISSUE}: {name} must assign {dest} after await "
                f"casDataUrl only when the per-open overlayGen "
                f"(or wanted cas_hash) is still current"
            )
        if why == "guard":
            fail(
                f"{_ISSUE}: {name} must skip {dest} when overlayGen "
                f"(or wanted cas_hash) is stale — increment the token "
                f"on this click, then after await casDataUrl ignore the "
                f"assign if another cell has been clicked "
                f"(galleryGen / open alone do not invalidate an "
                f"in-flight {overlay})"
            )
        fail(
            f"{_ISSUE}: {name} must increment overlayGen "
            f"(or set wanted cas_hash) before await casDataUrl and "
            f"skip {dest} when that token/hash is stale — another "
            f"cell click does not bump galleryGen, so a late "
            f"{dest} assign can stack on {other}"
        )

    # --- gallery-overlay-one ---
    for name, body, dest, other in (
        (video_name, video, "videoSrc", "lightboxSrc"),
        (photo_name, photo, "lightboxSrc", "videoSrc"),
    ):
        if _one_overlay_ok(body, dest, other):
            continue
        fail(
            f"{_ISSUE}: {name} must assign only one overlay after "
            f"await — closeOverlays() immediately before {dest} = …, "
            f"or set {other} = null (a late {dest} assign must not "
            f"leave both #118 lightboxSrc and #271 videoSrc set; "
            f"closeOverlays() before the await does not count)"
        )
