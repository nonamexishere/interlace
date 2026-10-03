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
