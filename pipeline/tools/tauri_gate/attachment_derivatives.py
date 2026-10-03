"""#427 — the People timeline bubble uses a content-addressed still.

The photo, the video poster, and the PDF first page are marked
data-deriv-still and named by derivative_cas_hash. Open and playback stay
on cas_hash. Search, the gallery, and avatars do not switch.
"""

from __future__ import annotations

from pathlib import Path

from common import fail


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _has_deriv_name(src: str) -> bool:
    return "derivative_cas_hash" in src or "derivativeCasHash" in src


def _nearest_branch_condition(src: str, marker: str) -> str:
    """Nearest `{#if` / `{:else if` condition before `marker`, braces included."""
    at = src.find(marker)
    if at < 0:
        return ""
    head = src[:at]
    start = max(head.rfind("{#if"), head.rfind("{:else if"))
    if start < 0:
        return ""
    end = src.find("}", start)
    if end < 0 or end > at:
        return src[start:at]
    return src[start : end + 1]


def _overlay_only_span(src: str) -> str:
    """Text from `overlayOnly` through the next `/>`."""
    at = src.find("overlayOnly")
    if at < 0:
        return ""
    end = src.find("/>", at)
    if end < 0:
        return src[at:]
    return src[at : end + 2]


def _review_fix_bits(cas: str) -> list[str]:
    bits: list[str] = []
    cond = _nearest_branch_condition(cas, "data-cas-image-slot")
    if "srcs[" not in cond:
        shown = " ".join(cond.split()) or "missing"
        bits.append(
            "DERIV-STILL-MISSING: image slot branch does not require srcs[ (" + shown + ")"
        )
    if "overlayOnly" not in cas:
        bits.append("DERIV-VIDEO-POSTER: CasAttach has no overlayOnly")
    elif "broken =" in _overlay_only_span(cas):
        bits.append("DERIV-VIDEO-POSTER: overlayOnly through /> contains broken =")
    return bits


def assert_attachment_derivatives(crate: Path) -> None:
    """#427: timeline stills use the derivative; open stays the original."""
    web = crate / "web" / "lib"
    cas = _text(web / "CasAttach.svelte")
    api = _text(web / "api.ts")
    video = _text(web / "CasVideo.svelte")
    walk = _text(web / "threadWalk.ts")
    search = _text(web / "SearchHits.svelte")
    gallery = _text(web / "PersonMediaDialog.svelte")
    avatar = _text(web / "PersonAvatar.svelte")
    bits: list[str] = []
    if "data-deriv-still" not in cas:
        bits.append("CasAttach has no data-deriv-still")
    if not _has_deriv_name(cas):
        bits.append("CasAttach does not name derivative_cas_hash")
    if not _has_deriv_name(api):
        bits.append("api.ts Attachment does not include derivative_cas_hash")
    if "data-cas-video-overlay" not in video or "<video" not in video:
        bits.append("video overlay no longer plays a local <video>")
    if "casDataUrl" not in walk:
        bits.append("thread lightbox no longer loads casDataUrl of the original")
    if _has_deriv_name(walk) or "data-deriv-still" in walk:
        bits.append("thread lightbox switched onto the derivative")
    for label, src in (
        ("SearchHits", search),
        ("PersonMediaDialog", gallery),
        ("PersonAvatar", avatar),
    ):
        if _has_deriv_name(src) or "data-deriv-still" in src:
            bits.append(f"{label} switched onto the derivative")
    if bits:
        fail("DERIV-BUBBLE: " + "; ".join(bits))
    extra = _review_fix_bits(cas)
    if extra:
        fail("; ".join(extra))
