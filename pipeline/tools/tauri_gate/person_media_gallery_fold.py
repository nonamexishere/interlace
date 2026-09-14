"""#361 fold — gallery video one overlay + scroll reset.

Sibling of person_media_gallery.py (do not grow that file). Two review
bugs only. Do not reopen the #361 mix or review suggestions 3–6.

Video: mount CasVideo overlay-only (skip the inline max-h-64 player).
Open the existing #271 overlay (data-cas-video-overlay). Do not wrap
CasVideo in a second photo-lightbox / second gallery X / programmatic
expand-click. Close / backdrop / Esc of that overlay clears gallery
videoSrc (onClose, or drop videoSrc when the overlay unmounts). Keep
#271 hooks on CasVideo (overlay, close, expand still exists for
timeline). No autoplay. No <video> in data-photo-lightbox.

Scroll: the reload effect (open / selectedId / includeGroups) sets
scrollTop = 0 and zeros the bound scroller (galleryEl.scrollTop = 0).
On scroller bind, read viewportH from clientHeight (not only onscroll).

Must-IDs: gallery-video-one-overlay, gallery-scroll-reset.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.media_cas_lib import _CAS_VIDEO_AUTOPLAY
from tauri_gate.person_media_gallery import _matching_if_end
from tauri_gate.scan import (
    _function_body,
    _match_closer,
    _svelte_markup,
    _without_comments,
)
from tauri_gate.status_toasts_toast import _svelte_effect_args, _svelte_if_chains

_ISSUE = "#361"

_OVERLAY_ONLY = re.compile(
    r"\b(?:overlayOnly|overlay_only|noInline|skipInline|startExpanded|"
    r"openOverlay|galleryOverlay|forceOverlay)\b"
    r"|overlay\s*=\s*\{?\s*true\b"
    r"|inline\s*=\s*\{?\s*false\b"
)
_ON_CLOSE = re.compile(
    r"\b(?:onClose|onclose|onDismiss|onOverlayClose|onVideoClose)\b"
)
_EXPAND_HACK = re.compile(
    r"querySelector(?:All)?\s*\(\s*[`'\"][^`'\"]*data-cas-video-expand"
    r"|data-cas-video-expand[\s\S]{0,240}?\.click\s*\(",
    re.I | re.S,
)
_VIDEO_IN_LB = re.compile(
    r"data-photo-lightbox[\s\S]{0,800}<video\b|<video\b[\s\S]{0,800}data-photo-lightbox",
    re.I,
)
_STATE_SCROLL_ZERO = re.compile(r"(?<!\.)\bscrollTop\s*=\s*0\b")
_EL_SCROLL_ZERO = re.compile(
    r"(?:"
    r"galleryEl\s*(?:&&\s*\(?\s*galleryEl\s*)?\.scrollTop\s*=\s*0"
    r"|\bel\s*(?:&&\s*\(?\s*el\s*)?\.scrollTop\s*=\s*0"
    r"|galleryEl\s*&&\s*\(?galleryEl\.scrollTop\s*=\s*0"
    r")"
)
_VIEWPORT_ASSIGN = re.compile(r"\b(?:viewportH|viewportHeight|viewH|galleryH)\s*=")
_BIND_CLIENT_H = re.compile(
    r"bind:clientHeight\s*=\s*\{?\s*(?:viewportH|viewportHeight|viewH|galleryH)"
)
_CAS_VIDEO_TAG = re.compile(r"<CasVideo\b[^>]*>", re.I)
_KEEP_OVERLAY = re.compile(r"\bdata-cas-video-overlay\b")
_KEEP_CLOSE = re.compile(r"\bdata-cas-video-close\b")
_KEEP_EXPAND = re.compile(r"\bdata-cas-video-expand\b")
_KEEP_INLINE = re.compile(r"\bdata-cas-video\b|max-h-64")


def _text(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _if_block(src: str, cond_rx: re.Pattern[str]) -> str:
    for m in re.finditer(r"\{#if\s+([^}]+)\}", src):
        if cond_rx.search(m.group(1)):
            end = _matching_if_end(src, m.start())
            if end > 0:
                return src[m.start() : end]
    return ""


def _video_mount_block(dlg: str) -> str:
    """Markup around the gallery CasVideo mount ({#if videoSrc} or a window)."""
    block = _if_block(dlg, re.compile(r"\bvideoSrc\b"))
    if block and re.search(r"<CasVideo\b", block):
        return block
    m = re.search(r"<CasVideo\b", dlg)
    if not m:
        return ""
    return dlg[max(0, m.start() - 900) : min(len(dlg), m.end() + 240)]


def _has_second_video_wrapper(dlg: str) -> bool:
    """Second lightbox / second X / expand-click hack around gallery CasVideo."""
    if re.search(r"\bdata-person-gallery-video\b", dlg):
        return True
    if _EXPAND_HACK.search(dlg):
        return True
    block = _video_mount_block(dlg)
    if not block or not re.search(r"<CasVideo\b", block):
        return False
    wrapper = bool(
        re.search(r"\bphoto-lightbox\b", block) or re.search(r"fixed\s+inset-0", block)
    )
    second_x = bool(
        re.search(r"\bdata-lightbox-close\b", block) or re.search(r"<X\b", block)
    )
    return wrapper and second_x


def _gallery_cas_video_tags(dlg: str) -> list[str]:
    return _CAS_VIDEO_TAG.findall(dlg)


def _gallery_overlay_only(dlg: str) -> bool:
    return any(_OVERLAY_ONLY.search(tag) for tag in _gallery_cas_video_tags(dlg))


def _inline_player_gated(cas: str) -> bool:
    """Inline max-h-64 / data-cas-video player can be skipped (overlay-only)."""
    for chain in _svelte_if_chains(cas):
        for cond, body in chain:
            if "data-cas-video-overlay" in body and "max-h-64" not in body:
                continue
            if "max-h-64" not in body and "data-cas-video" not in body:
                continue
            if "data-cas-video-overlay" in body:
                ov = body.find("data-cas-video-overlay")
                inline = body.find("max-h-64")
                if inline < 0:
                    inline = body.find("data-cas-video")
                if inline >= 0 and ov < inline:
                    continue
            if _OVERLAY_ONLY.search(cond) or re.search(r"!", cond):
                return True
    return False


def _overlay_opens_when_only(cas: str) -> bool:
    """#271 overlay mounts on the gallery overlay-only path (no expand click)."""
    for chain in _svelte_if_chains(cas):
        for cond, body in chain:
            if "data-cas-video-overlay" in body and _OVERLAY_ONLY.search(cond):
                return True
    # Initial expanded must come from the overlay-only prop — not
    # `expanded = true` inside openExpanded (timeline expand).
    if re.search(
        r"(?:let|const)\s+expanded\s*=\s*\$state\s*\(\s*"
        r"(?:overlayOnly|overlay_only|noInline|skipInline|startExpanded|"
        r"openOverlay|galleryOverlay|forceOverlay)\b",
        cas,
    ):
        return True
    if re.search(
        r"(?:let|const)\s+expanded\s*=\s*"
        r"(?:overlayOnly|overlay_only|noInline|skipInline|startExpanded|"
        r"openOverlay|galleryOverlay|forceOverlay)\b",
        cas,
    ):
        return True
    return False


def _cas_dismiss_calls_onclose(cas: str) -> bool:
    """Close / backdrop / Esc on the #271 overlay invokes onClose (or synonym)."""
    close_fn = (
        _function_body(cas, "closeExpanded")
        or _function_body(cas, "closeOverlay")
        or ""
    )
    key_fn = (
        _function_body(cas, "onOverlayKeydown")
        or _function_body(cas, "onOverlayKey")
        or ""
    )
    markup = _svelte_markup(cas)
    ov_at = markup.find("data-cas-video-overlay")
    overlay_win = markup[ov_at : ov_at + 900] if ov_at >= 0 else ""
    called = (
        bool(_ON_CLOSE.search(close_fn))
        or bool(_ON_CLOSE.search(key_fn))
        or bool(_ON_CLOSE.search(overlay_win))
    )
    if not called:
        return False
    if not re.search(r"(?:key|code)\s*===?\s*[\"']Escape[\"']", cas) and not re.search(
        r"\bdata-cas-video-close\b", cas
    ):
        return False
    return True


def _callee_clears_video(dlg: str, name: str) -> bool:
    body = _function_body(dlg, name)
    if not body:
        return False
    if re.search(r"\bvideoSrc\s*=\s*null\b", body):
        return True
    for m in re.finditer(r"\b([A-Za-z_][\w]*)\s*\(", body):
        inner = _function_body(dlg, m.group(1))
        if inner and re.search(r"\bvideoSrc\s*=\s*null\b", inner):
            return True
    return False


def _gallery_clears_video_on_overlay_close(dlg: str) -> bool:
    """Gallery drops videoSrc via onClose / closeOverlays / overlay unmount."""
    for tag in _gallery_cas_video_tags(dlg):
        if not _ON_CLOSE.search(tag):
            continue
        if re.search(r"\bvideoSrc\s*=\s*null\b", tag):
            return True
        for name in (
            "closeOverlays",
            "closeVideo",
            "clearVideo",
            "dismissVideo",
            "onVideoClose",
        ):
            if re.search(rf"\b{name}\b", tag) and _callee_clears_video(dlg, name):
                return True
        m = re.search(
            r"on(?:Close|close|Dismiss|OverlayClose|VideoClose)\s*=\s*\{([^}]*)\}",
            tag,
        )
        if m and re.search(r"\bvideoSrc\s*=\s*null\b", m.group(1)):
            return True
        if m:
            ident = re.match(r"\s*([A-Za-z_][\w]*)\s*$", m.group(1) or "")
            if ident and _callee_clears_video(dlg, ident.group(1)):
                return True
    # Drop videoSrc when the #271 overlay unmounts / expanded goes false.
    for arg in _svelte_effect_args(dlg):
        if not re.search(r"\bvideoSrc\s*=\s*null\b", arg):
            continue
        if re.search(
            r"data-cas-video-overlay|\bexpanded\b|\boverlayOnly\b|\bonClose\b",
            arg,
        ):
            return True
    return False


def _reload_effects(src: str) -> list[str]:
    """$effect that reloads on open / selectedId / includeGroups (clears rows)."""
    out: list[str] = []
    for arg in _svelte_effect_args(src):
        has_open = bool(re.search(r"\bopen\b", arg))
        has_id = bool(re.search(r"\bselectedId\b", arg))
        has_groups = bool(re.search(r"\bincludeGroups\b", arg))
        clears = bool(
            re.search(r"\b(?:mediaRows|galleryRows|rows)\s*=\s*\[\s*\]", arg)
            or re.search(r"\b(?:srcs|thumbs|thumbSrcs)\s*=\s*(?:\{\s*\}|\[\s*\])", arg)
        )
        if (has_open and has_id and has_groups) or (
            clears and (has_open or has_id or has_groups)
        ):
            out.append(arg)
    return out


def _zeros_bound_scroller(body: str) -> bool:
    if _EL_SCROLL_ZERO.search(body):
        return True
    if re.search(r"\bgalleryEl\b", body) and re.search(
        r"\.scrollTop\s*=\s*0\b", body
    ):
        return True
    return False


def _onscroll_spans(src: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for m in re.finditer(r"onscroll\s*=\s*\{", src):
        open_b = src.find("{", m.end() - 1)
        if open_b < 0:
            continue
        close = _match_closer(src, open_b)
        if close > open_b:
            spans.append((open_b, close))
    return spans


def _viewport_from_bind(dlg: str) -> bool:
    """viewportH (or equivalent) from scroller clientHeight on bind/mount."""
    if _BIND_CLIENT_H.search(dlg):
        return True
    if re.search(r"bind:this\s*=\s*\{[^}]{0,320}clientHeight", dlg, re.S):
        return True
    spans = _onscroll_spans(dlg)
    for m in re.finditer(
        r"\b(?:viewportH|viewportHeight|viewH|galleryH)\s*=\s*([^;\n]+)", dlg
    ):
        if "clientHeight" not in m.group(1):
            continue
        pos = m.start()
        if any(a <= pos <= b for a, b in spans):
            continue
        return True
    for arg in _svelte_effect_args(dlg):
        if not _VIEWPORT_ASSIGN.search(arg):
            continue
        if not re.search(r"\bclientHeight\b", arg):
            continue
        if re.search(r"\bgalleryEl\b|\bel\b", arg):
            return True
    return False


def assert_person_media_gallery_fold(crate: Path) -> None:
    """#361 fold: one #271 overlay for gallery video; reload resets scroll."""
    dlg_path = crate / "web" / "lib" / "PersonMediaDialog.svelte"
    cas_path = crate / "web" / "lib" / "CasVideo.svelte"
    attach_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not dlg_path.is_file():
        fail(
            f"{_ISSUE}: PersonMediaDialog.svelte required "
            "(gallery video overlay + scroll reset fold)"
        )
    if not cas_path.is_file():
        fail(f"{_ISSUE}: CasVideo.svelte required (keep #271 overlay / expand)")
    dlg_raw = dlg_path.read_text()
    cas_raw = cas_path.read_text()
    attach_raw = _text(attach_path)
    dlg = _without_comments(dlg_raw)
    cas = _without_comments(cas_raw)
    mark = _svelte_markup(dlg_raw)

    # --- gallery-video-one-overlay ---
    if not re.search(r"<CasVideo\b", dlg_raw) and not re.search(r"<CasVideo\b", dlg):
        fail(
            f"{_ISSUE}: gallery video path must mount CasVideo "
            "(existing #271 overlay, not a second lightbox)"
        )
    if not _KEEP_OVERLAY.search(cas_raw) and not _KEEP_OVERLAY.search(cas):
        fail(f"{_ISSUE}: keep #271 data-cas-video-overlay on CasVideo")

    # 1) no second wrapper / expand-click — primary red today.
    if _has_second_video_wrapper(dlg_raw) or _has_second_video_wrapper(dlg):
        fail(
            f"{_ISSUE}: gallery video must mount CasVideo overlay-only "
            "(existing #271 data-cas-video-overlay) — do not wrap it in a "
            "second photo-lightbox / second gallery X / "
            "data-person-gallery-video expand-click "
            "(querySelector + [data-cas-video-expand] + click()); "
            "CasVideo Close leaves that stacked wrapper today"
        )

    if not _gallery_overlay_only(dlg_raw) and not _gallery_overlay_only(dlg):
        fail(
            f"{_ISSUE}: gallery CasVideo must skip the inline max-h-64 player "
            "(overlay-only) so a video thumb opens data-cas-video-overlay "
            "directly — no leftover inline player under the overlay"
        )
    if not _inline_player_gated(cas_raw) and not _inline_player_gated(cas):
        fail(
            f"{_ISSUE}: CasVideo inline max-h-64 player must be skippable "
            "on the gallery overlay-only path (keep it for the timeline)"
        )
    if not _overlay_opens_when_only(cas_raw) and not _overlay_opens_when_only(cas):
        fail(
            f"{_ISSUE}: gallery overlay-only path must open "
            "data-cas-video-overlay immediately "
            "(do not require a programmatic expand click)"
        )

    if not _cas_dismiss_calls_onclose(cas) and not _cas_dismiss_calls_onclose(cas_raw):
        fail(
            f"{_ISSUE}: CasVideo Close / backdrop / Esc must call onClose "
            "(or drop the overlay so the gallery can clear videoSrc) — "
            "setting expanded = false alone leaves the gallery wrapper"
        )
    if not _gallery_clears_video_on_overlay_close(dlg) and not (
        _gallery_clears_video_on_overlay_close(dlg_raw)
    ):
        fail(
            f"{_ISSUE}: Close / backdrop / Esc on the #271 overlay must "
            "clear gallery videoSrc (CasVideo onClose, or drop videoSrc "
            "when the overlay unmounts) — Media Dialog stays open"
        )

    gal_blob = dlg_raw + "\n" + cas_raw
    if _CAS_VIDEO_AUTOPLAY.search(gal_blob) or _CAS_VIDEO_AUTOPLAY.search(
        dlg + "\n" + cas
    ):
        fail(f"{_ISSUE}: gallery video must not autoplay")
    if _VIDEO_IN_LB.search(mark) or _VIDEO_IN_LB.search(dlg_raw):
        fail(f"{_ISSUE}: do not stuff <video> inside data-photo-lightbox")

    # Timeline #271 keep — do not delete expand / overlay / inline player.
    if not _KEEP_EXPAND.search(cas_raw) and not _KEEP_EXPAND.search(cas):
        fail(
            f"{_ISSUE}: keep #271 data-cas-video-expand on CasVideo "
            "(timeline still has the inline player + expand)"
        )
    if not _KEEP_CLOSE.search(cas_raw) and not _KEEP_CLOSE.search(cas):
        fail(f"{_ISSUE}: keep #271 data-cas-video-close on CasVideo")
    if not _KEEP_INLINE.search(cas_raw) and not _KEEP_INLINE.search(cas):
        fail(
            f"{_ISSUE}: keep the #271 inline <video> / max-h-64 player "
            "on CasVideo for the timeline"
        )
    if attach_path.is_file() and not re.search(r"<CasVideo\b", attach_raw):
        fail(
            f"{_ISSUE}: keep timeline CasVideo on CasAttach "
            "(do not delete #271 to fix the gallery stack)"
        )

    # --- gallery-scroll-reset ---
    reloads = _reload_effects(dlg) or _reload_effects(dlg_raw)
    if not reloads:
        fail(
            f"{_ISSUE}: gallery reload $effect (open / selectedId / "
            "includeGroups) required — it must zero scrollTop"
        )
    reload_blob = "\n".join(reloads)
    if not _STATE_SCROLL_ZERO.search(reload_blob):
        fail(
            f"{_ISSUE}: gallery reload (open / selectedId / includeGroups) "
            "must assign scrollTop = 0 "
            "(virtualized padTop must not reopen mid-grid)"
        )
    if not _zeros_bound_scroller(reload_blob):
        fail(
            f"{_ISSUE}: gallery reload must also zero the bound scroller "
            "(galleryEl.scrollTop = 0 / el.scrollTop = 0)"
        )
    if not _viewport_from_bind(dlg_raw) and not _viewport_from_bind(dlg):
        fail(
            f"{_ISSUE}: read viewportH (or equivalent) from the scroller "
            "clientHeight on bind/mount — not only in onscroll"
        )
