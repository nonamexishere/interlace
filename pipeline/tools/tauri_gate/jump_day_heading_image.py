"""#311 fold — CAS image reserved slot (photo hitch on timeline).

Sibling of jump_day_heading_stutter2.py. Do not grow stutter2 / stutter /
freeze / review / heading modules. Lock reserved image slot before casDataUrl,
object-contain thumbnail, no Loading-line image placeholder. Keep casDataUrl /
lightbox / sticker isImage / max-h-64.

Must-IDs: cas-image-slot, cas-image-contain, cas-image-no-loading-line,
cas-image-d24, cas-image-keep-casDataUrl, cas-image-keep-lightbox,
cas-image-keep-sticker, cas-image-keep-max-h-64.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.jump_day_heading import _ISSUE
from tauri_gate.scan import _function_body, _without_comments

_SLOT_MARK = re.compile(
    r"data-cas-image-slot\b|\bcas-image-slot\b",
    re.I,
)
_IMAGE_IF = re.compile(
    r"\{(?::else\s*)?if\s+([^}]*\bisImage\b[^}]*)\}",
    re.I,
)
_SRCS_GATE = re.compile(r"\bsrcs\s*\[|\bsrcs\s*\.|casDataUrl\s*\([^)]*\)\s*(?:&&|\?)")
_HTTP_SRC = re.compile(
    r"[\"']https?://|src\s*=\s*[\"']https?://",
    re.I,
)
_THUMB_MAX_H = re.compile(r"\bmax-h-64\b")
_OBJECT_CONTAIN_CLASS = re.compile(r"\bobject-contain\b")
_OBJECT_FIT_CONTAIN = re.compile(r"object-fit\s*:\s*contain", re.I)
_LOADING_PLACEHOLDER = re.compile(
    r"Loading\s*\{|Loading\s*\$\{",
)
_LIGHTBOX_OPEN = re.compile(
    r"\bopenLightbox\b|\bopenPhoto\b|\bshowLightbox\b",
    re.I,
)
_BTN_IMG = re.compile(
    r"<button\b[\s\S]{0,500}<img\b|<img\b[\s\S]{0,200}(?:on:click|onclick)",
    re.I,
)
_STICKER_IN_IS_IMAGE = re.compile(
    r"(?:"
    r"function\s+isImage[\s\S]{0,500}[\"']sticker[\"']"
    r"|isImage\s*=[\s\S]{0,500}[\"']sticker[\"']"
    r"|kind\s*===?\s*[\"']sticker[\"']"
    r")",
    re.I,
)
_D24 = re.compile(
    r"(?:"
    r"(?:photo|image|thumbnail|sticker).{0,120}"
    r"(?:reserv(?:e|es|ed)|slot|fixed\s+(?:box|height|size|aspect))"
    r".{0,120}"
    r"(?:jump|hitch|shift|layout|timeline|scroll)"
    r"|"
    r"(?:reserv(?:e|es|ed)|slot).{0,80}"
    r"(?:photo|image|thumbnail).{0,120}"
    r"(?:jump|hitch|shift|layout|timeline|scroll)"
    r"|"
    r"(?:photo|image|thumbnail).{0,80}"
    r"(?:does\s+not|without|no)\s+"
    r"(?:jump|hitch|shift).{0,60}"
    r"(?:timeline|scroll|layout|row)?"
    r")",
    re.I | re.S,
)
# Lightbox full-size path uses max-h-[90vh] — not the timeline thumbnail.
_LIGHTBOX_IMG_SIZE = re.compile(r"max-h-\[90vh\]|max-w-\[90vw\]|data-photo-lightbox")


def _css_src(crate: Path) -> str:
    # app.css lives next to lib/, not under web/lib/.
    p = crate / "web" / "app.css"
    return p.read_text() if p.is_file() else ""


def _docs() -> str:
    p = repo_root() / "docs" / "user" / "app.md"
    return p.read_text() if p.is_file() else ""


def _branch_window(src: str, start: int, limit: int = 900) -> str:
    """Markup after an {#if}/{ :else if} open, cut at next sibling branch."""
    chunk = src[start : start + limit]
    # Stop at next top-ish branch marker after some content.
    m = re.search(r"\{:else(?:\s+if\b)?|\{\/if\}", chunk[40:] if len(chunk) > 40 else chunk)
    if m:
        # m is relative to chunk[40:] when we sliced
        if len(chunk) > 40:
            return chunk[: 40 + m.start()]
        return chunk[: m.start()]
    return chunk


def _has_reserved_image_slot(cas: str) -> bool:
    """Loadable isImage path mounts cas-image-slot not gated on srcs/casDataUrl."""
    if not _SLOT_MARK.search(cas):
        return False

    # Slot marker must sit on an isImage branch whose condition is not srcs-gated.
    for m in _IMAGE_IF.finditer(cas):
        cond = m.group(1)
        if _SRCS_GATE.search(cond):
            continue
        # Still require loadable (not omitted/missing-only). Soft: isImage present.
        body = _branch_window(cas, m.end())
        if _SLOT_MARK.search(body):
            return True

    # Slot next to isImage with no srcs gate in a nearby condition window.
    for sm in _SLOT_MARK.finditer(cas):
        win = cas[max(0, sm.start() - 350) : sm.end() + 200]
        if not re.search(r"\bisImage\b", win):
            continue
        # Reject if the only nearby image condition still requires srcs[.
        conds = list(_IMAGE_IF.finditer(cas))
        nearest = None
        nearest_dist = 10**9
        for cm in conds:
            d = abs(cm.start() - sm.start())
            if d < nearest_dist:
                nearest_dist = d
                nearest = cm
        if nearest is not None and nearest_dist < 500:
            if not _SRCS_GATE.search(nearest.group(1)):
                return True
        elif re.search(r"\bisImage\b", win) and not _SRCS_GATE.search(win[: win.find(sm.group(0))]):
            return True
    return False


def _thumb_has_object_contain(cas: str, css: str) -> bool:
    """Thumbnail <img> is object-contain / object-fit: contain inside the slot."""
    # CSS on the slot
    if re.search(
        r"(?:\.cas-image-slot|\[data-cas-image-slot\])[^{}]*\{[^}]*object-fit\s*:\s*contain",
        css,
        re.I | re.S,
    ):
        return True
    if re.search(
        r"(?:\.cas-image-slot|\[data-cas-image-slot\])[^{}]*\{[^}]*object-fit\s*:\s*contain",
        cas,
        re.I | re.S,
    ):
        return True

    # Class on thumbnail img (max-h-64 path), not only lightbox 90vh.
    for im in re.finditer(r"<img\b[^>]*>", cas, re.I | re.S):
        tag = im.group(0)
        if _LIGHTBOX_IMG_SIZE.search(tag):
            continue
        if not (_THUMB_MAX_H.search(tag) or _SLOT_MARK.search(cas[max(0, im.start() - 200) : im.end()])):
            # Require thumb sizing or slot neighborhood.
            around = cas[max(0, im.start() - 220) : im.end() + 40]
            if not (_THUMB_MAX_H.search(around) or _SLOT_MARK.search(around)):
                continue
        if _OBJECT_CONTAIN_CLASS.search(tag) or _OBJECT_FIT_CONTAIN.search(tag):
            return True
        around = cas[max(0, im.start() - 220) : im.end() + 80]
        if _SLOT_MARK.search(around) and (
            _OBJECT_CONTAIN_CLASS.search(around) or _OBJECT_FIT_CONTAIN.search(around)
        ):
            return True

    # Slot wrapper carries object-contain and wraps img
    if re.search(
        r"(?:data-cas-image-slot|cas-image-slot)[^>]{0,200}object-contain[\s\S]{0,400}<img\b"
        r"|object-contain[^>]{0,200}(?:data-cas-image-slot|cas-image-slot)[\s\S]{0,400}<img\b",
        cas,
        re.I,
    ):
        return True
    return False


def _image_uses_loading_line(cas: str) -> bool:
    """True when the image branch still uses Loading {…} as the unloaded placeholder."""
    if not _LOADING_PLACEHOLDER.search(cas):
        return False

    # Good: isImage branch not gated on srcs, body has slot/img, no Loading inside.
    for m in _IMAGE_IF.finditer(cas):
        cond = m.group(1)
        if _SRCS_GATE.search(cond):
            continue
        body = _branch_window(cas, m.end(), limit=1100)
        if _LOADING_PLACEHOLDER.search(body):
            return True
        if _SLOT_MARK.search(body) or re.search(r"<img\b", body, re.I):
            # Reserved path handles unloaded image without Loading line.
            return False

    # isImage path gated on srcs → unloaded images fall through to Loading.
    gated_image = False
    for m in _IMAGE_IF.finditer(cas):
        if _SRCS_GATE.search(m.group(1)):
            gated_image = True
            break
    if gated_image and _LOADING_PLACEHOLDER.search(cas):
        return True

    # Loading line sits on a branch that isImage can still reach (!srcs, no isVideo etc.)
    for m in _LOADING_PLACEHOLDER.finditer(cas):
        before = cas[max(0, m.start() - 500) : m.start()]
        cond_m = None
        for cm in re.finditer(r"\{(?::else\s*)?if\s+([^}]*)\}", before, re.I):
            cond_m = cm
        if cond_m is None:
            continue
        cond = cond_m.group(1)
        # Shared !srcs loading fallback — images hit it when isImage&&srcs failed.
        if re.search(r"!\s*srcs\s*\[|!srcs\s*\[|srcs\s*\[\s*[^\]]+\]\s*\}", cond) or re.search(
            r"!\s*srcs\b|!broken", cond
        ):
            # If this fallback does not exclude isImage, images use it.
            if not re.search(r"!\s*isImage\b|isVideo|isPdf|isAudio", cond):
                return True
    return True


def _max_h64_on_thumb(cas: str) -> bool:
    """max-h-64 still on the thumbnail path (not only lightbox)."""
    for im in re.finditer(r"<img\b[^>]*>", cas, re.I | re.S):
        tag = im.group(0)
        if _LIGHTBOX_IMG_SIZE.search(tag):
            continue
        around = cas[max(0, im.start() - 180) : im.end() + 40]
        if _THUMB_MAX_H.search(tag) or _THUMB_MAX_H.search(around):
            return True
    # Slot CSS max-height: 16rem (h-64) also acceptable with class on slot.
    if re.search(
        r"(?:cas-image-slot|data-cas-image-slot)[^;}{]{0,120}max-h-64",
        cas,
        re.I,
    ):
        return True
    return bool(_THUMB_MAX_H.search(cas))


def _sticker_is_image(cas: str) -> bool:
    body = _function_body(cas, "isImage") or ""
    if body and re.search(r"[\"']sticker[\"']", body):
        return True
    return bool(_STICKER_IN_IS_IMAGE.search(cas))


def assert_jump_day_heading_image(crate: Path) -> None:
    """#311 fold: reserved CAS image slot before src; object-contain; no Loading line."""
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail(f"{_ISSUE}: CasAttach.svelte required (CAS image slot / photo hitch)")
    cas_raw = cas_path.read_text()
    cas = _without_comments(cas_raw)
    css = _without_comments(_css_src(crate))
    dtxt = _docs()

    # --- keep (already green) ---
    if "casDataUrl" not in cas_raw:
        fail(
            f"{_ISSUE}: keep casDataUrl for CAS image bytes "
            "(local data: URL only — do not fetch http(s))"
        )
    if _HTTP_SRC.search(cas) or _HTTP_SRC.search(cas_raw):
        fail(f"{_ISSUE}: keep CasAttach free of remote http(s) src for attachments")

    if not re.search(r"<img\b", cas_raw, re.I):
        fail(
            f"{_ISSUE}: keep CAS <img> thumbnail "
            "(#118 click → lightbox still needs an img)"
        )
    if not (
        _LIGHTBOX_OPEN.search(cas_raw)
        or _BTN_IMG.search(cas_raw)
        or re.search(r"data-photo-lightbox|lightboxOpen", cas_raw)
    ):
        fail(
            f"{_ISSUE}: keep #118 lightbox open path "
            "(openLightbox / button around img / click on thumbnail)"
        )

    if not _sticker_is_image(cas_raw):
        fail(
            f"{_ISSUE}: keep isImage treating kind === \"sticker\" "
            "(stickers stay on the image / lightbox path)"
        )

    if not _max_h64_on_thumb(cas_raw):
        fail(
            f"{_ISSUE}: keep max-h-64 on the photo thumbnail path "
            "(same cap as today's CAS image)"
        )

    # --- new (fail today) ---
    # 1) cas-image-slot — reserved box before src; <img> may still wait on srcs
    # inside the slot. Fail when there is no ungated slot (today: only
    # {#if isImage && srcs}<img>).
    if not _has_reserved_image_slot(cas_raw):
        fail(
            f"{_ISSUE}: loadable image/sticker path must mount a reserved "
            "slot (data-cas-image-slot or class cas-image-slot) that is not "
            "gated on srcs[ / casDataUrl — fail if the only image UI is "
            "{#if srcs…}<img> (Loading line then max-h-64 hitch)"
        )

    # 2) cas-image-contain
    if not _thumb_has_object_contain(cas_raw, css):
        fail(
            f"{_ISSUE}: thumbnail <img> must be object-contain / "
            "object-fit: contain inside the cas-image-slot "
            "(decode must not grow the reserved box)"
        )

    # 3) cas-image-no-loading-line
    if _image_uses_loading_line(cas_raw):
        fail(
            f"{_ISSUE}: image/sticker branch must not use "
            "'Loading {' / 'Loading ${' as the photo placeholder "
            "(video / PDF / voice may keep that line)"
        )

    # 4) cas-image-d24
    if not _D24.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say a photo thumbnail reserves its "
            "slot / does not jump the timeline (D24)"
        )
