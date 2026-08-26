"""CAS video / PDF chrome assert. Imported by gate_tauri.py."""
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

from tauri_gate.import_boot import _element_block_at

from tauri_gate.media_lightbox import (
    _HEIC_TRANSCODE,
    _LIGHTBOX_VIDEO_CHROME,
    _VOICE_MISSING,
    _VOICE_OMITTED,
    _cas_attach_and_lightbox_sources,
)

from tauri_gate.media_linkify import _hook_element_blocks

from tauri_gate.status_toasts import _svelte_if_chains




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


def assert_cas_video_pdf(crate: Path) -> None:
    """#271: video / PDF CAS attachments open in-window (local only).

    Acceptance: loadable video plays via <video> (or a named video surface)
    from casDataUrl / data: / srcs — no autoplay, no http(s) src. Loadable
    PDF opens in-window (iframe / embed / object / overlay) from the same
    local bytes — no remote PDF host. Stickers that decode as images stay
    on the #118 lightbox path (kind === \"sticker\" in isImage). Omitted /
    missing stay placeholders. Photo lightbox (#118) still has no <video>.
    Docs: video + PDF local in-window; no autoplay; no remote stream.
    Not: streaming from the internet, HTML mail layout, auto-playing media.
    Do not rewrite #118 / #119 / #135 / #170.
    Follow-up: PDF iframe requires frame-src data: (not 'none', not *,
    not http(s)). Keep-check + assert stay in lockstep. connect-src
    stays IPC-only (ipc: / ipc.localhost).
    Follow-up: visible Interlace expand / full-size control (native
    <video controls> is not enough on WKWebView). Opening it shows a
    full-size in-window overlay <video> from local srcs / casDataUrl /
    data: — not data-photo-lightbox, no autoplay, Esc / Close / backdrop
    dismisses. Docs: stored video can be opened full-size in-window.
    """
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail("#271: CasAttach.svelte required for video / PDF / sticker CAS")
    cas = cas_path.read_text()
    extra = _cas_video_pdf_extra(crate, cas)
    surface = cas if not extra else cas + "\n" + extra
    cleaned = _without_comments(surface)
    cleaned_cas = _without_comments(cas)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 0) Local CAS path only — same casDataUrl / data: as photos / voice.
    if "casDataUrl" not in cas:
        fail(
            "#271: video / PDF must load via casDataUrl (local data: URL), "
            "not a remote stream"
        )
    if re.search(r"[\"']https?://", cleaned_cas) or re.search(
        r"src\s*=\s*[\"']https?://", cas, re.I
    ):
        fail("#271: CasAttach must not use remote http(s) URLs for attachments")

    # 1) In-window video surface — today's “Stored locally” fallback is not enough.
    if not _has_cas_video_surface(surface):
        fail(
            "#271: loadable video CAS attachments must play in-window "
            "(<video> or a named video surface from casDataUrl / data:) — "
            "not the \"Stored locally\" fallback"
        )

    # 2) Classify video (kind, mime, or extension) so it is not stuffed
    # into the photo lightbox or left on the file fallback.
    if not _CAS_VIDEO_KIND.search(cas) and not _CAS_VIDEO_KIND.search(surface):
        fail(
            "#271: CasAttach must detect video attachments "
            "(kind === \"video\", video/* mime, or .mp4/.mov/.mkv/.avi/.webm)"
        )

    # 3) Viewer src stays local — no autoplay, no http(s).
    if not _CAS_VIDEO_LOCAL_SRC.search(surface):
        fail(
            "#271: <video> (or named video surface) src must be local "
            "casDataUrl / data: / srcs — no remote stream"
        )
    if _CAS_VIDEO_REMOTE_SRC.search(surface) or _CAS_VIDEO_REMOTE_SRC.search(cleaned):
        fail(
            "#271: video player must not use http(s) src — only local "
            "casDataUrl / data: / srcs"
        )
    if _CAS_VIDEO_AUTOPLAY.search(surface) or _CAS_VIDEO_AUTOPLAY.search(cleaned):
        fail(
            "#271: video must not autoplay "
            "(honor reduced motion; user starts playback)"
        )

    # 4) PDF: in-window open from local bytes; no remote host.
    if not _CAS_PDF_KIND.search(cas) and not _CAS_PDF_KIND.search(surface):
        fail(
            "#271: CasAttach must detect PDF attachments "
            "(.pdf / application/pdf) so they are not left as "
            "\"Stored locally\" text"
        )
    if not _CAS_PDF_EL.search(surface):
        fail(
            "#271: loadable PDF CAS attachments must open in-window "
            "(iframe / embed / object / overlay from local casDataUrl / data:) "
            "— not a remote viewer and not only \"Stored locally\""
        )
    if not _CAS_PDF_LOCAL_SRC.search(surface):
        fail(
            "#271: PDF viewer src must be local casDataUrl / data: / srcs "
            "— not a remote PDF host"
        )
    if _CAS_PDF_REMOTE.search(surface) or _CAS_PDF_REMOTE.search(cleaned):
        fail(
            "#271: PDF must not use a remote host "
            "(no Google Viewer / PDF.js CDN / http(s) .pdf)"
        )

    # 5) Sticker: kind === "sticker" still treated as image / lightbox.
    if not _sticker_treated_as_image(cas):
        fail(
            "#271: kind === \"sticker\" must still be treated as image / "
            "lightbox (keep isImage or equivalent) — do not drop stickers "
            "to the \"Stored locally\" line"
        )

    # 6) Omitted / missing stay placeholders — no video/PDF on those branches.
    if not _VOICE_OMITTED.search(cas):
        fail(
            "#271: omitted attachments must stay placeholders "
            "(branch on .omitted — no fake video / PDF viewer)"
        )
    if not _VOICE_MISSING.search(cas):
        fail(
            "#271: missing attachments must stay placeholders "
            "(branch on .missing / not stored — no fake video / PDF viewer)"
        )
    video_guards = (
        "isVideo",
        "video/",
        'kind === "video"',
        "kind === 'video'",
        "data-cas-video",
        ".mp4",
        ".mov",
    )
    pdf_guards = (
        "isPdf",
        "application/pdf",
        ".pdf",
        "data-cas-pdf",
        'kind === "pdf"',
        "kind === 'pdf'",
    )
    for rx, guards, label in (
        (_CAS_VIDEO_EL, video_guards, "video player"),
        (_CAS_PDF_EL, pdf_guards, "PDF viewer"),
    ):
        m = rx.search(cas)
        if not m:
            m = rx.search(surface)
            branch_src = surface if m else cas
        else:
            branch_src = cas
        if not m:
            continue
        which = _cas_media_on_placeholder_branch(branch_src, m, guards)
        if which:
            fail(
                f"#271: do not put the {label} on the {which} branch — "
                f"{which} stays a placeholder"
            )

    # 7) #118 photo lightbox still has no <video>. Video/PDF are a
    # separate surface, not stuffed into data-photo-lightbox.
    lightbox_blocks = _hook_element_blocks(surface, "data-photo-lightbox")
    if not lightbox_blocks:
        cas_only, lightbox_extra, _logic = _cas_attach_and_lightbox_sources(crate)
        lightbox_blocks = _hook_element_blocks(
            cas_only + "\n" + lightbox_extra, "data-photo-lightbox"
        )
        if _LIGHTBOX_VIDEO_CHROME.search(cas_only + "\n" + lightbox_extra):
            fail(
                "#271: #118 photo lightbox must still have no <video> — "
                "video is a separate surface"
            )
    for block in lightbox_blocks:
        if _CAS_VIDEO_EL.search(block):
            fail(
                "#271: #118 photo lightbox must still have no <video> — "
                "video is a separate surface (not data-photo-lightbox)"
            )

    # 8) No plugin-shell / opener / remote fetch for video or PDF.
    if _CAS_VIDEO_PDF_OPENER.search(cleaned) or _CAS_VIDEO_PDF_OPENER.search(surface):
        fail(
            "#271: do not add tauri-plugin-shell / opener for video / PDF "
            "(in-window local viewer only; Reveal in Finder stays hash-only)"
        )
    if _CAS_VIDEO_PDF_FETCH.search(cleaned) or _CAS_VIDEO_PDF_FETCH.search(surface):
        fail(
            "#271: do not http(s) fetch video / PDF "
            "(local casDataUrl / data: only)"
        )
    if _HEIC_TRANSCODE.search(blob):
        fail(
            "#271: do not add HEIC transcode — HEIC stays placeholder "
            "unless already decoded (keep #118)"
        )

    # 9) Docs: video + PDF local in-window; no autoplay; no remote stream.
    # Window on video/PDF lines so #222 “no auto-playing media” is not a hit.
    if not dtxt.strip():
        fail("#271: docs/user/app.md required (local video + PDF in-window)")
    if not re.search(r"\bvideos?\b", dtxt, re.I):
        fail(
            "#271: docs/user/app.md must say video opens in-window from local CAS"
        )
    if not re.search(r"\bPDF\b", dtxt):
        fail(
            "#271: docs/user/app.md must say PDF opens in-window from local CAS"
        )
    media_doc = ""
    for m in re.finditer(
        r".{0,180}(?:\bvideos?\b|\bPDF\b).{0,180}",
        dtxt,
        re.I | re.S,
    ):
        media_doc += m.group(0) + "\n"
    if not re.search(r"in-window|in the (?:app|window|timeline)", media_doc, re.I):
        fail(
            "#271: docs/user/app.md must say video + PDF open in-window "
            "(local CAS; not a remote viewer)"
        )
    if not re.search(
        r"("
        r"(?:no |not |never |without )autoplay"
        r"|autoplay is off"
        r"|does not autoplay"
        r"|autoplay off"
        r")",
        media_doc,
        re.I,
    ):
        fail("#271: docs/user/app.md must say video does not autoplay")
    if not re.search(
        r"("
        r"never a remote stream"
        r"|no remote stream"
        r"|not a remote stream"
        r"|no remote (?:host|viewer)"
        r"|never a remote"
        r")",
        media_doc,
        re.I,
    ):
        fail(
            "#271: docs/user/app.md must say video / PDF are not a remote stream"
        )
    if not re.search(r"\bstickers?\b", dtxt, re.I):
        fail(
            "#271: docs/user/app.md must say stickers that are images still lightbox"
        )

    # 10) Follow-up: PDF iframe requires frame-src data:. Read production
    # CSP from tauri.conf.json — do not only trust the shared constant.
    # Keep-check (CSP not in conf) + this assert stay in lockstep.
    conf_path = crate / "tauri.conf.json"
    if not conf_path.is_file():
        fail("#271: tauri.conf.json required (PDF iframe needs frame-src data:)")
    import json

    try:
        prod_csp = str(
            (
                (json.loads(conf_path.read_text()).get("app") or {}).get(
                    "security"
                )
                or {}
            ).get("csp")
            or ""
        )
    except json.JSONDecodeError:
        fail("#271: tauri.conf.json must be valid JSON (need production CSP)")

    for label, csp in (
        ("tauri.conf.json", prod_csp),
        ("shared CSP constant", CSP),
    ):
        frame = _csp_directive_sources(csp, "frame-src")
        if frame is None:
            fail(
                f"#271: {label} CSP must include frame-src data: "
                "so WKWebView can load a local PDF iframe"
            )
        frame_toks = frame.split()
        if "data:" not in frame_toks:
            fail(
                f"#271: {label} CSP must include frame-src data: "
                "so WKWebView can load a local PDF iframe"
            )
        if "'none'" in frame_toks:
            fail(
                f"#271: {label} CSP must not set frame-src 'none' "
                "(WKWebView refuses the PDF iframe)"
            )
        if "*" in frame_toks:
            fail(
                f"#271: {label} CSP must not set frame-src * "
                "(local data: frames only)"
            )
        if any(re.match(r"https?:", tok, re.I) for tok in frame_toks):
            fail(
                f"#271: {label} CSP must not allow http(s) in frame-src "
                "(no remote frames)"
            )
        connect = _csp_directive_sources(csp, "connect-src")
        if connect is None:
            fail(
                f"#271: {label} CSP must keep connect-src IPC-only "
                "(ipc: / ipc.localhost)"
            )
        bad = [
            tok
            for tok in connect.split()
            if tok.lower() not in {a.lower() for a in _CSP_IPC_CONNECT}
        ]
        if bad:
            fail(
                f"#271: {label} connect-src must stay IPC-only "
                f"(ipc: / ipc.localhost); not {bad[0]}"
            )

    # 11) Follow-up: visible Interlace expand / full-size control.
    # Native <video controls> is not enough — WKWebView has no fullscreen
    # button (especially with playsinline). requestFullscreen alone is
    # not visible chrome.
    if not _cas_video_has_expand_control(cas, extra, surface):
        fail(
            "#271: video surface must have a visible Interlace expand / "
            "full-size / fullscreen control (button or data-cas-video-* hook) "
            "— native <video controls> is not enough (WKWebView has no "
            "fullscreen button)"
        )

    # 12) Opening expand shows a full-size in-window <video> overlay.
    overlay_blocks = _cas_video_overlay_blocks(surface)
    if not overlay_blocks:
        photo_blocks = _hook_element_blocks(surface, "data-photo-lightbox")
        if any(_CAS_VIDEO_EL.search(b) for b in photo_blocks):
            fail(
                "#271: video full-size overlay must not be data-photo-lightbox "
                "(#118 stays images only)"
            )
        fail(
            "#271: opening expand must show a full-size in-window <video> "
            "(overlay / dialog / fixed inset-0, or data-cas-video-overlay / "
            "data-video-overlay containing <video> from local srcs / "
            "casDataUrl / data:) — not the inline max-h-64 player"
        )

    # 13) That overlay is not the photo lightbox.
    for block in overlay_blocks:
        if re.search(r"\bdata-photo-lightbox\b", block):
            fail(
                "#271: video full-size overlay must not be data-photo-lightbox "
                "(#118 stays images only)"
            )

    # 14) Overlay <video> is local and has no autoplay.
    if not any(_CAS_VIDEO_OVERLAY_LOCAL.search(b) for b in overlay_blocks):
        fail(
            "#271: overlay <video> src must be local srcs / casDataUrl / data:"
        )
    for block in overlay_blocks:
        if _CAS_VIDEO_AUTOPLAY.search(block):
            fail(
                "#271: overlay <video> must not autoplay "
                "(honor reduced motion; user starts playback)"
            )

    # 15) Overlay / expand path has a dismiss control in the markup.
    overlay_blob = "\n".join(overlay_blocks)
    if not _cas_video_has_overlay_close(overlay_blob, extra):
        fail(
            "#271: video overlay / expand path must have a close "
            "(Esc / Close / backdrop / data-cas-video-close)"
        )

    # 16) Docs: full-size / expand / fullscreen for local video.
    # Window on video-play / video-open lines so photo “full-size”
    # lightbox copy is not a hit unless that window also talks about video.
    video_doc = ""
    for m in re.finditer(
        r".{0,160}(?:"
        r"\bvideos?\s+(?:play|open|expand)"
        r"|(?:play|open|expand)\w*\s+[^\n.]{0,40}\bvideos?"
        r"|\bvideos?\b[^\n.]{0,80}(?:full-?size|full\s+size|full-?screen|fullscreen|expand)"
        r"|(?:full-?size|full\s+size|full-?screen|fullscreen|expand)\w*[^\n.]{0,80}\bvideos?"
        r").{0,160}",
        dtxt,
        re.I | re.S,
    ):
        video_doc += m.group(0) + "\n"
    if not re.search(
        r"(?:full-?size|full\s+size|full-?screen|fullscreen|\bexpand(?:ed|s|ing)?\b)",
        video_doc,
        re.I,
    ):
        fail(
            "#271: docs/user/app.md must say a stored video can be opened "
            "full-size / expanded in-window (photo lightbox “full-size” "
            "does not count unless that window also talks about video)"
        )
