"""Helpers extracted from media_cas.py (media_cas_lib)."""
from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    CSP,
    _function_body,
    _web_sources,
    _without_comments,
)

from tauri_gate.import_boot_setup import _element_block_at

from tauri_gate.media_lightbox_lib import (
    _HEIC_TRANSCODE,
    _LIGHTBOX_VIDEO_CHROME,
    _VOICE_MISSING,
    _VOICE_OMITTED,
    _cas_attach_and_lightbox_sources,
)

from tauri_gate.media_linkify_lib import _hook_element_blocks

from tauri_gate.status_toasts_toast import _svelte_if_chains




# #271 — video / PDF / sticker CAS in the timeline (local only; no autoplay).
_CAS_VIDEO_KIND = re.compile(
    r"("
    r"kind\s*===\s*[\"']video[\"']"
    r"|kind\s*==\s*[\"']video[\"']"
    r"|startsWith\s*\(\s*[\"']video/"
    r"|video/\*"
    r"|\.mp4|\.mov|\.mkv|\.avi|\.webm"
    r"|isVideo\s*\("
    r")",
    re.I,
)
_CAS_VIDEO_EL = re.compile(r"<video\b", re.I)
_CAS_VIDEO_NAMED = re.compile(
    r"data-cas-video|data-video-(?:attach|player|surface|overlay)",
    re.I,
)
_CAS_VIDEO_LOCAL_SRC = re.compile(
    r"("
    r"<video\b[\s\S]{0,700}(?:src|bind:src)\s*=\s*\{[^}]{0,200}"
    r"(?:srcs|casDataUrl|data:)"
    r"|<video\b[\s\S]{0,700}src\s*=\s*[\"']data:"
    r"|data-cas-video[\s\S]{0,500}(?:src\s*=\s*\{[^}]{0,200}(?:srcs|casDataUrl|data:)"
    r"|src\s*=\s*[\"']data:)"
    r"|data-video-(?:attach|player|surface|overlay)[\s\S]{0,500}"
    r"(?:src\s*=\s*\{[^}]{0,200}(?:srcs|casDataUrl|data:)|src\s*=\s*[\"']data:)"
    r")",
    re.I,
)
_CAS_VIDEO_REMOTE_SRC = re.compile(
    r"("
    r"<video\b[\s\S]{0,700}src\s*=\s*[\"']https?://"
    r"|<video\b[\s\S]{0,700}src\s*=\s*\{[^}]{0,220}https?://"
    r"|video(?:Src|Url|URL)?\s*=\s*[\"']https?://"
    r")",
    re.I,
)
_CAS_VIDEO_AUTOPLAY = re.compile(
    r"("
    r"<video\b[^>]*\bautoplay\b"
    r"|autoplay\s*=\s*\{?\s*(?:true|!0|1)\b"
    r"|\.autoplay\s*=\s*true"
    r")",
    re.I | re.S,
)
_CAS_PDF_KIND = re.compile(
    r"("
    r"application/pdf"
    r"|isPdf\s*\("
    r"|kind\s*===?\s*[\"']pdf[\"']"
    r"|[\"']\.pdf[\"']"
    r"|\.pdf\b"
    r"|mime[^;\n]{0,80}pdf"
    r")",
    re.I,
)
_CAS_PDF_EL = re.compile(
    r"("
    r"<(?:iframe|embed|object)\b"
    r"|data-cas-pdf"
    r"|data-pdf-(?:attach|viewer|overlay|surface)"
    r")",
    re.I,
)
_CAS_PDF_LOCAL_SRC = re.compile(
    r"("
    r"<(?:iframe|embed|object)\b[\s\S]{0,700}(?:src|data)\s*=\s*\{[^}]{0,200}"
    r"(?:srcs|casDataUrl|data:)"
    r"|<(?:iframe|embed|object)\b[\s\S]{0,700}(?:src|data)\s*=\s*[\"']data:"
    r"|data-cas-pdf[\s\S]{0,500}(?:(?:src|data)\s*=\s*\{[^}]{0,200}"
    r"(?:srcs|casDataUrl|data:)|(?:src|data)\s*=\s*[\"']data:)"
    r"|data-pdf-(?:attach|viewer|overlay|surface)[\s\S]{0,500}"
    r"(?:(?:src|data)\s*=\s*\{[^}]{0,200}(?:srcs|casDataUrl|data:)"
    r"|(?:src|data)\s*=\s*[\"']data:)"
    r")",
    re.I,
)
_CAS_PDF_REMOTE = re.compile(
    r"("
    r"<(?:iframe|embed|object)\b[\s\S]{0,700}(?:src|data)\s*=\s*[\"']https?://"
    r"|<(?:iframe|embed|object)\b[\s\S]{0,700}(?:src|data)\s*=\s*\{[^}]{0,220}https?://"
    r"|docs\.google\.com/(?:viewer|gview)"
    r"|mozilla\.github\.io/pdf"
    r"|cdn(?:js)?\.[^\"'\s)]*pdf"
    r"|unpkg\.com/[^\"'\s)]*pdf"
    r"|jsdelivr[^\"'\s)]*pdf"
    r"|pdfjs\.express"
    r"|https?://[^\"'\s)]+\.pdf\b"
    r")",
    re.I,
)
_CAS_STICKER_KIND = re.compile(r"kind\s*===?\s*[\"']sticker[\"']")
_CAS_VIDEO_PDF_FETCH = re.compile(r"fetch\s*\(\s*[\"']https?://", re.I)
_CAS_VIDEO_PDF_OPENER = re.compile(
    r"("
    r"@tauri-apps/plugin-shell"
    r"|@tauri-apps/plugin-opener"
    r"|tauri-plugin-shell"
    r"|tauri-plugin-opener"
    r"|plugin-opener"
    r")",
    re.I,
)
_CAS_VIDEO_PDF_NAME = re.compile(r"video|pdf", re.I)
_CAS_VIDEO_PDF_HOOK = re.compile(
    r"("
    r"data-cas-video"
    r"|data-cas-pdf"
    r"|data-video-(?:attach|player|surface|overlay)"
    r"|data-pdf-(?:attach|viewer|overlay|surface)"
    r"|function\s+isVideo\b"
    r"|function\s+isPdf\b"
    r")",
    re.I,
)


def _cas_video_pdf_extra(crate: Path, cas: str) -> str:
    """Sibling video/PDF surfaces that CasAttach or App actually mounts.

    Unwired drafts do not count — otherwise an unused CasVideo.svelte
    would green-wash the still-dead “Stored locally” fallback.
    """
    web = crate / "web"
    if not web.is_dir():
        return ""
    app_path = crate / "web" / "App.svelte"
    app = app_path.read_text() if app_path.is_file() else ""
    host = cas + "\n" + app
    extra: list[str] = []
    for p in sorted(web.rglob("*")):
        if "node_modules" in p.parts:
            continue
        if p.suffix not in {".svelte", ".ts"}:
            continue
        if p.name == "CasAttach.svelte":
            continue
        name_hit = bool(_CAS_VIDEO_PDF_NAME.search(p.name))
        text = p.read_text()
        if not name_hit and not _CAS_VIDEO_PDF_HOOK.search(text):
            continue
        stem = p.stem
        if stem in host or re.search(
            rf"\b{re.escape(stem)}\b|{re.escape(p.name)}", host
        ):
            extra.append(text)
    return "\n".join(extra)


def _cas_named_video_is_player(src: str) -> bool:
    """data-cas-video (etc.) counts only if it loads local bytes, not a <p>."""
    for hook in (
        "data-cas-video",
        "data-video-player",
        "data-video-surface",
        "data-video-attach",
        "data-video-overlay",
    ):
        for block in _hook_element_blocks(src, hook):
            if _CAS_VIDEO_EL.search(block):
                return True
            if re.search(
                r"src\s*=\s*\{[^}]{0,200}(?:srcs|casDataUrl|data:)|src\s*=\s*[\"']data:",
                block,
                re.I,
            ) and not re.search(r"Stored locally", block):
                return True
    return False


def _has_cas_video_surface(src: str) -> bool:
    if _CAS_VIDEO_EL.search(src):
        return True
    return _cas_named_video_is_player(src)


def _sticker_treated_as_image(cas: str) -> bool:
    """kind === \"sticker\" still rides isImage / the image+lightbox path."""
    img = _function_body(cas, "isImage") or _function_body(cas, "isImg")
    if img and re.search(r"[\"']sticker[\"']", img):
        return True
    if img and re.search(r"isSticker\s*\(", img):
        stk = _function_body(cas, "isSticker")
        if stk and _CAS_STICKER_KIND.search(stk):
            return True
    # Equivalent classifier that still feeds the <img> / lightbox path.
    if _CAS_STICKER_KIND.search(cas) and re.search(
        r"("
        r"function\s+isImage[\s\S]{0,500}sticker"
        r"|isImage\s*=[\s\S]{0,500}sticker"
        r"|isImage\s*\([^)]*\)[\s\S]{0,200}sticker"
        r")",
        cas,
        re.I,
    ):
        return True
    return False


def _cas_media_on_placeholder_branch(src: str, match: re.Match[str], guards: tuple[str, ...]) -> str | None:
    """Return 'omitted' / 'missing' if the match sits on that placeholder branch."""
    before = src[: match.start()]
    last_omitted = max(before.rfind("omitted"), before.rfind("Media omitted"))
    last_missing = max(
        before.rfind(".missing"),
        before.rfind("not stored"),
        before.rfind("a.missing"),
    )
    last_guard = -1
    for tok in guards:
        last_guard = max(last_guard, before.rfind(tok))
    if last_omitted > last_guard and last_omitted > 0:
        return "omitted"
    if last_missing > last_guard and last_missing > 0:
        return "missing"
    return None


# IPC-only connect-src tokens (http(s)://ipc.localhost is Tauri IPC, not the net).
_CSP_IPC_CONNECT = frozenset(
    {
        "ipc:",
        "http://ipc.localhost",
        "https://ipc.localhost",
    }
)


def _csp_directive_sources(csp: str, name: str) -> str | None:
    """Return the source-list of a CSP directive, or None if absent."""
    for part in csp.split(";"):
        part = part.strip()
        if part.lower() == name.lower():
            return ""
        prefix = name + " "
        if part.lower().startswith(prefix.lower()):
            return part[len(name) :].strip()
    return None


# #271 follow-up — in-window video expand / full-size overlay (not native controls).
# data-cas-video alone is the inline player; the expand hook needs a suffix.
_CAS_VIDEO_EXPAND_HOOK = re.compile(
    r"data-cas-video-(?:expand|fs|full-?screen|full-?size|open|maximize|enlarge)"
    r"|data-video-(?:expand|fs|full-?screen|full-?size|open|maximize)",
    re.I,
)
_CAS_VIDEO_EXPAND_CHROME = re.compile(
    r"("
    r"<button\b[^>]{0,500}(?:aria-label|title)\s*=\s*[\"'][^\"']{0,80}"
    r"(?:expand|full-?size|full\s+size|full-?screen|fullscreen|maximize)"
    r"|<button\b[^>]{0,400}aria-label\s*=\s*\{[`'\"][^}`'\"]{0,80}"
    r"(?:expand|full-?size|full\s+size|full-?screen|fullscreen|maximize)"
    r"|<button\b[^>]{0,400}>\s*(?:Expand|Full[\s-]?size|Fullscreen|Maximize)\b"
    r"|<(?:Maximize2?|Expand|Fullscreen)\b"
    r"|@lucide/svelte/icons/(?:maximize(?:-2)?|expand|fullscreen)"
    r")",
    re.I | re.S,
)
_CAS_VIDEO_OVERLAY_CLOSE = re.compile(
    r"("
    r"data-cas-video-close"
    r"|data-video-(?:overlay-)?close"
    r"|closeVideo"
    r"|closeCasVideo"
    r"|video(?:Overlay|Open|Expanded|Fs|Fullscreen)\s*=\s*(?:false|null|undefined)"
    r"|(?:key|code)\s*===?\s*[\"']Escape[\"']"
    r"|aria-label\s*=\s*[\"'][^\"']*[Cc]lose[^\"']*[\"']"
    r"|>\s*Close\s*<"
    r")",
    re.I,
)
_CAS_VIDEO_OVERLAY_LOCAL = re.compile(
    r"("
    r"<video\b[\s\S]{0,700}(?:src|bind:src)\s*=\s*\{[^}]{0,200}"
    r"(?:srcs|casDataUrl|data:)"
    r"|<video\b[\s\S]{0,700}src\s*=\s*[\"']data:"
    r")",
    re.I,
)


def _cas_video_expand_blobs(cas: str, extra: str) -> str:
    """Markup the expand control may live on — CasVideo + isVideo branch.

    The photo-thumbnail “full size” aria-label is on the isImage branch
    and must not count as video expand chrome.
    """
    parts = [extra, _without_comments(extra)]
    # Only the isVideo / CasVideo branch — not an ancestor {#if items}
    # whose body also happens to contain the photo “full size” button.
    for chain in _svelte_if_chains(cas):
        for cond, body in chain:
            if re.search(r"\bisVideo\b|<CasVideo\b", cond):
                parts.append(body)
    return "\n".join(parts)


def _cas_video_has_expand_control(cas: str, extra: str, surface: str) -> bool:
    """Visible Interlace expand chrome. Native <video controls> does not count."""
    blob = _cas_video_expand_blobs(cas, extra)
    if _CAS_VIDEO_EXPAND_HOOK.search(blob) or _CAS_VIDEO_EXPAND_HOOK.search(surface):
        return True
    if _CAS_VIDEO_EXPAND_CHROME.search(blob):
        return True
    return False


def _cas_video_overlay_blocks(src: str) -> list[str]:
    """Full-size in-window video overlays — not the inline player, not #118."""
    out: list[str] = []
    seen: set[str] = set()

    def add(block: str) -> None:
        block = block.strip()
        if not block or block in seen:
            return
        if not _CAS_VIDEO_EL.search(block):
            return
        head = block[: min(len(block), 480)]
        if re.search(r"\bdata-photo-lightbox\b", head):
            return
        seen.add(block)
        out.append(block)

    for hook in ("data-cas-video-overlay", "data-video-overlay"):
        for block in _hook_element_blocks(src, hook):
            if re.match(r"<video\b", block, re.I) and not re.search(
                r"fixed\s+inset-0|role\s*=\s*[\"']dialog[\"']",
                block,
                re.I,
            ):
                continue
            add(block)

    for m in re.finditer(
        r"<(?:div|aside|section|dialog)\b[^>]{0,900}"
        r"(?:fixed\s+inset-0|role\s*=\s*[\"']dialog[\"'])",
        src,
        re.I | re.S,
    ):
        i = m.start()
        block = _element_block_at(src, i)
        add(block)

    return out


def _cas_video_has_overlay_close(overlay_blob: str, extra: str) -> bool:
    """At least one dismiss path on the overlay / expand surface."""
    blob = overlay_blob + "\n" + extra + "\n" + _without_comments(extra)
    if _CAS_VIDEO_OVERLAY_CLOSE.search(blob):
        return True
    if re.search(
        r"(?:on:click|onclick)(?:\|\w+)*\s*=\s*\{[^}]{0,240}"
        r"(?:closeVideo|closeCasVideo|video(?:Overlay|Open|Expanded)\s*=\s*"
        r"(?:false|null))",
        blob,
        re.I,
    ):
        return True
    return False

__all__ = [
    "_CAS_VIDEO_KIND",
    "_CAS_VIDEO_EL",
    "_CAS_VIDEO_NAMED",
    "_CAS_VIDEO_LOCAL_SRC",
    "_CAS_VIDEO_REMOTE_SRC",
    "_CAS_VIDEO_AUTOPLAY",
    "_CAS_PDF_KIND",
    "_CAS_PDF_EL",
    "_CAS_PDF_LOCAL_SRC",
    "_CAS_PDF_REMOTE",
    "_CAS_STICKER_KIND",
    "_CAS_VIDEO_PDF_FETCH",
    "_CAS_VIDEO_PDF_OPENER",
    "_CAS_VIDEO_PDF_NAME",
    "_CAS_VIDEO_PDF_HOOK",
    "_cas_video_pdf_extra",
    "_cas_named_video_is_player",
    "_has_cas_video_surface",
    "_sticker_treated_as_image",
    "_cas_media_on_placeholder_branch",
    "_CSP_IPC_CONNECT",
    "_csp_directive_sources",
    "_CAS_VIDEO_EXPAND_HOOK",
    "_CAS_VIDEO_EXPAND_CHROME",
    "_CAS_VIDEO_OVERLAY_CLOSE",
    "_CAS_VIDEO_OVERLAY_LOCAL",
    "_cas_video_expand_blobs",
    "_cas_video_has_expand_control",
    "_cas_video_overlay_blocks",
    "_cas_video_has_overlay_close",
    "re",
    "Path",
    "fail",
    "repo_root",
    "CSP",
    "_web_sources",
    "_without_comments",
    "_HEIC_TRANSCODE",
    "_LIGHTBOX_VIDEO_CHROME",
    "_VOICE_MISSING",
    "_VOICE_OMITTED",
    "_cas_attach_and_lightbox_sources",
    "_hook_element_blocks",
    "annotations",
    "_function_body",
    "_element_block_at",
    "_svelte_if_chains",
]
