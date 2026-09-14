"""#361 race — stale casDataUrl overlay after close / switch.

Sibling of person_media_gallery_fold.py (do not grow that file). One
review bug only. Do not reopen the #361 mix, the video-stack / scroll
folds, or review suggestions 3–6.

openPhoto / openVideo await casDataUrl then write lightboxSrc /
videoSrc with no galleryGen or open check. Portals are siblings of
Dialog.Content and mount on {#if lightboxSrc} / {#if videoSrc} alone.
Close Media, Show in timeline, person switch, include-groups, or
another cell before the invoke returns can still mount or stack an
overlay.

Must-IDs: gallery-overlay-gen, gallery-overlay-open-gate.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.person_media_gallery import _matching_if_end
from tauri_gate.scan import (
    _function_body,
    _js_next,
    _match_closer,
    _svelte_markup,
    _without_comments,
)

_ISSUE = "#361"

_GEN_COUNTER = (
    r"galleryGen|mediaGen|personGalleryGen|thumbGen|overlayGen"
)
_CAPTURE = re.compile(
    r"(?:const|let|var)\s+(\w+)\s*=\s*(?:\+\+\s*)?(" + _GEN_COUNTER + r")\b"
    r"|(?:const|let|var)\s+(\w+)\s*=\s*(" + _GEN_COUNTER + r")\s*\+\+"
)
_AWAIT_CAS = re.compile(
    r"await\s+(?:api\s*\.\s*)?casDataUrl\s*\("
    r"|(?:api\s*\.\s*)?casDataUrl\s*\([^;]{0,200}?\)\s*\.then\s*\(",
    re.S,
)
_CAS_CALL = re.compile(r"\bcasDataUrl\s*\(")
_FN_HEAD = re.compile(
    r"(?:async\s+)?function\s+(\w+)\s*\([^)]*\)\s*\{"
    r"|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:function\s*)?"
    r"\([^)]*\)\s*(?:=>\s*)?\{"
)
_PHOTO_NAMES = ("openPhoto", "openLightbox", "openImage", "showPhoto")
_VIDEO_NAMES = ("openVideo", "openVideoOverlay", "showVideo")
_PHOTO_HOOK = re.compile(r"\bdata-photo-lightbox\b")
_VIDEO_HOOK = re.compile(r"<CasVideo\b")


def _text(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _capture_in(prefix: str) -> tuple[str, str] | None:
    m = _CAPTURE.search(prefix)
    if not m:
        return None
    local = m.group(1) or m.group(3)
    counter = m.group(2) or m.group(4)
    if local and counter:
        return local, counter
    return None


def _first_await_cas(body: str) -> int:
    m = _AWAIT_CAS.search(body)
    return m.start() if m else -1


def _non_null_assigns(body: str, dest: str) -> list[int]:
    out: list[int] = []
    for m in re.finditer(rf"\b{re.escape(dest)}\s*=", body):
        rhs = body[m.end() :].lstrip()
        if rhs.startswith("null") or rhs.startswith("undefined"):
            continue
        if rhs.startswith('""') or rhs.startswith("''"):
            continue
        out.append(m.start())
    return out


def _all_fn_bodies(src: str) -> list[tuple[str, str]]:
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for m in _FN_HEAD.finditer(src):
        name = m.group(1) or m.group(2)
        if not name or name in seen:
            continue
        body = _function_body(src, name)
        if not body:
            continue
        seen.add(name)
        out.append((name, body))
    return out


def _click_path(src: str, dest: str, preferred: tuple[str, ...]) -> tuple[str, str]:
    for name in preferred:
        body = _function_body(src, name)
        if body and _CAS_CALL.search(body) and _non_null_assigns(body, dest):
            return name, body
    for name, body in _all_fn_bodies(src):
        if not _CAS_CALL.search(body):
            continue
        if _non_null_assigns(body, dest):
            return name, body
    for name in preferred:
        body = _function_body(src, name)
        if body:
            return name, body
    return preferred[0], ""


def _cond_has_gen_ne(cond: str, local: str, counter: str) -> bool:
    return bool(
        re.search(
            rf"{re.escape(local)}\s*!==?\s*{re.escape(counter)}"
            rf"|{re.escape(counter)}\s*!==?\s*{re.escape(local)}",
            cond,
        )
    )


def _cond_has_gen_eq(cond: str, local: str, counter: str) -> bool:
    return bool(
        re.search(
            rf"{re.escape(local)}\s*===?\s*{re.escape(counter)}"
            rf"|{re.escape(counter)}\s*===?\s*{re.escape(local)}",
            cond,
        )
    )


def _cond_has_not_open(cond: str) -> bool:
    return bool(
        re.search(
            r"!\s*open\b|open\s*===?\s*false|open\s*!==?\s*true",
            cond,
        )
    )


def _cond_has_open_true(cond: str) -> bool:
    if re.search(r"!\s*open\b", cond):
        return False
    if re.search(r"\bopen\s*===?\s*false\b", cond):
        return False
    if re.search(r"\|\|\s*open\b|\bopen\s*\|\|", cond):
        return False
    return bool(
        re.search(
            r"(?:^|&&|\()\s*open\b\s*(?:&&|\)|$|===?\s*true)",
            cond.strip(),
        )
    )


def _same_block_prefix(body: str, pos: int) -> str:
    enclosing = 0
    i = 0
    while i < pos:
        nxt = _js_next(body, i)
        if nxt != i:
            i = nxt
            continue
        if body[i] == "{":
            close = _match_closer(body, i)
            if close < 0:
                break
            if close >= pos:
                enclosing = i
                i += 1
            else:
                i = close + 1
            continue
        i += 1
    return body[enclosing:pos]


def _if_return_conds(region: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"\bif\s*\(", region):
        open_p = m.end() - 1
        close_p = _match_closer(region, open_p)
        if close_p < 0:
            continue
        cond = region[open_p + 1 : close_p]
        i = close_p + 1
        while i < len(region) and region[i] in " \t\n\r":
            i += 1
        rest = region[i:]
        if rest.startswith("return") or re.match(r"\{\s*return\b", rest):
            out.append(cond)
    return out


def _enclosing_if_conds(body: str, pos: int) -> list[str]:
    conds: list[str] = []
    for m in re.finditer(r"\bif\s*\(", body):
        if m.start() >= pos:
            continue
        open_p = m.end() - 1
        close_p = _match_closer(body, open_p)
        if close_p < 0 or close_p >= pos:
            continue
        cond = body[open_p + 1 : close_p]
        i = close_p + 1
        while i < len(body) and body[i] in " \t\n\r":
            i += 1
        if i >= len(body):
            continue
        if body[i] == "{":
            end = _match_closer(body, i)
            if end >= pos > i:
                conds.append(cond)
        elif i <= pos:
            semi = body.find(";", i)
            if semi < 0:
                semi = len(body)
            if i <= pos <= semi:
                conds.append(cond)
    return conds


def _stale_guarded(body: str, pos: int, local: str, counter: str) -> bool:
    """Assign at pos is skipped on gen mismatch or !open."""
    wraps = _enclosing_if_conds(body, pos)
    if any(_cond_has_gen_eq(c, local, counter) for c in wraps) and any(
        _cond_has_open_true(c) for c in wraps
    ):
        return True
    rets = _if_return_conds(_same_block_prefix(body, pos))
    has_gen = any(_cond_has_gen_ne(c, local, counter) for c in rets)
    has_open = any(_cond_has_not_open(c) for c in rets)
    return has_gen and has_open


def _if_spans(src: str) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    for m in re.finditer(r"\{#if\s+([^}]+)\}", src):
        end = _matching_if_end(src, m.start())
        if end > 0:
            spans.append((m.group(1).strip(), m.start(), end))
    return spans


def _enclosing_markup_conds(src: str, pos: int) -> list[str]:
    return [cond for cond, a, b in _if_spans(src) if a <= pos < b]


def _portal_region(mark: str) -> str:
    idx = mark.rfind("</Dialog.Content>")
    return mark[idx:] if idx >= 0 else mark


def _portal_open_gated(mark: str, hook: re.Pattern[str], src_name: str) -> bool:
    region = _portal_region(mark)
    m = hook.search(region) or hook.search(mark)
    if not m:
        return False
    blob = region if hook.search(region) else mark
    at = hook.search(blob)
    if not at:
        return False
    conds = _enclosing_markup_conds(blob, at.start())
    if not conds:
        return False
    has_open = any(_cond_has_open_true(c) for c in conds)
    has_src = any(re.search(rf"\b{re.escape(src_name)}\b", c) for c in conds)
    return has_open and has_src


def _path_ok(body: str, dest: str) -> tuple[str, str] | None:
    """None if the click path captures gen and guards dest after await.

    Otherwise ('capture'|'guard'|'await'|'assign', dest).
    """
    if not body.strip():
        return "missing", dest
    if not _CAS_CALL.search(body):
        return "await", dest
    await_at = _first_await_cas(body)
    if await_at < 0:
        return "await", dest
    cap = _capture_in(body[:await_at])
    if not cap:
        return "capture", dest
    assigns = _non_null_assigns(body, dest)
    if not assigns:
        return "assign", dest
    post = [p for p in assigns if p > await_at]
    if not post:
        return "assign", dest
    local, counter = cap
    if any(not _stale_guarded(body, p, local, counter) for p in post):
        return "guard", dest
    return None


def assert_person_media_gallery_race(crate: Path) -> None:
    """#361 race: stale casDataUrl must not mount a closed-Dialog overlay."""
    dlg_path = crate / "web" / "lib" / "PersonMediaDialog.svelte"
    if not dlg_path.is_file():
        fail(
            f"{_ISSUE}: PersonMediaDialog.svelte required "
            "(openPhoto / openVideo must capture galleryGen before "
            "await casDataUrl and skip lightboxSrc / videoSrc when "
            "gen !== galleryGen or !open)"
        )
    dlg_raw = dlg_path.read_text()
    dlg = _without_comments(dlg_raw)
    mark = _svelte_markup(dlg_raw)

    photo_name, photo = _click_path(dlg, "lightboxSrc", _PHOTO_NAMES)
    if not photo:
        photo_name, photo = _click_path(dlg_raw, "lightboxSrc", _PHOTO_NAMES)
    video_name, video = _click_path(dlg, "videoSrc", _VIDEO_NAMES)
    if not video:
        video_name, video = _click_path(dlg_raw, "videoSrc", _VIDEO_NAMES)

    # --- gallery-overlay-gen (primary red today) ---
    for name, body, dest, kind in (
        (photo_name, photo, "lightboxSrc", "photo"),
        (video_name, video, "videoSrc", "video"),
    ):
        bad = _path_ok(body, dest)
        if not bad:
            continue
        why, _ = bad
        overlay = (
            "#118 lightbox"
            if kind == "photo"
            else "#271 overlay"
        )
        if why == "missing":
            fail(
                f"{_ISSUE}: {name} required — capture galleryGen "
                f"(const gen = galleryGen) before await casDataUrl and "
                f"skip {dest} when gen !== galleryGen or !open "
                f"(stale casDataUrl must not mount a {overlay} on a "
                f"closed Dialog)"
            )
        if why == "await":
            fail(
                f"{_ISSUE}: {name} must await casDataUrl and capture "
                f"galleryGen before that await — then skip {dest} when "
                f"gen !== galleryGen or !open"
            )
        if why == "assign":
            fail(
                f"{_ISSUE}: {name} must assign {dest} after await "
                f"casDataUrl only when gen === galleryGen and open "
                f"(skip the assign when gen !== galleryGen or !open)"
            )
        fail(
            f"{_ISSUE}: {name} must capture galleryGen "
            f"(const gen = galleryGen) before await casDataUrl and "
            f"skip {dest} when gen !== galleryGen or !open — "
            f"close Media / Show in timeline / person switch / "
            f"include-groups / another cell must not mount a stale "
            f"{overlay} after the bytes return"
        )

    # --- gallery-overlay-open-gate ---
    if not _portal_open_gated(mark, _PHOTO_HOOK, "lightboxSrc") and not (
        _portal_open_gated(dlg_raw, _PHOTO_HOOK, "lightboxSrc")
    ):
        fail(
            f"{_ISSUE}: photo portal must mount only when "
            f"{{#if open && lightboxSrc}} "
            f"(a late lightboxSrc assign must not paint #118 on a "
            f"closed Dialog)"
        )
    if not _portal_open_gated(mark, _VIDEO_HOOK, "videoSrc") and not (
        _portal_open_gated(dlg_raw, _VIDEO_HOOK, "videoSrc")
    ):
        fail(
            f"{_ISSUE}: video portal must mount only when "
            f"{{#if open && videoSrc}} "
            f"(a late videoSrc assign must not paint a #271 overlay "
            f"on a closed Dialog)"
        )
