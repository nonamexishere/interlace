"""Helpers extracted from media_lightbox.py (media_lightbox_lib)."""
from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _timeline_block,
    _web_logic,
    _web_sources,
    _without_comments,
)





# #118 — in-window photo lightbox from local CAS (timeline / search thumbnails).
_LIGHTBOX_TOKEN = re.compile(
    r"("
    r"\blightbox\b"
    r"|photoLightbox"
    r"|photo-lightbox"
    r"|data-photo-lightbox"
    r"|data-lightbox"
    r"|imageLightbox"
    r"|image-lightbox"
    r"|casLightbox"
    r"|cas-lightbox"
    r"|openLightbox"
    r"|closeLightbox"
    r"|lightboxOpen"
    r"|lightboxSrc"
    r"|lightboxIndex"
    r"|viewerOpen"
    r"|photoViewer"
    r"|photo-viewer"
    r"|data-photo-viewer"
    r"|fullsizeOpen"
    r"|fullSizeOpen"
    r"|fullscreenPhoto"
    r"|mediaLightbox"
    r")",
    re.I,
)
_LIGHTBOX_OPEN_CLICK = re.compile(
    r"("
    r"(?:on:click|onclick)(?:\|\w+)*\s*=\s*\{[^}]{0,240}"
    r"(?:openLightbox|openPhoto|openImage|showLightbox|showPhoto|showImage|"
    r"lightboxOpen|setLightbox|openViewer|openCas|viewPhoto|viewImage|"
    r"lightbox|photoViewer)"
    r"|(?:openLightbox|openPhoto|openImage|showLightbox|showPhoto|showImage|"
    r"setLightbox|openViewer|viewPhoto|viewImage)\s*\("
    r")",
    re.I | re.S,
)
_LIGHTBOX_IMG_CLICK = re.compile(
    r"<img\b[^>]{0,400}(?:on:click|onclick)(?:\|\w+)*\s*=\s*\{",
    re.I | re.S,
)
_LIGHTBOX_BUTTON_AROUND_IMG = re.compile(
    r"<button\b[^>]{0,300}(?:on:click|onclick)(?:\|\w+)*\s*=\s*\{[^}]{0,200}"
    r"(?:lightbox|openPhoto|openImage|openLightbox|showLightbox|photoViewer|"
    r"viewPhoto|viewImage)"
    r"[^}]{0,80}\}[^>]{0,200}>[\s\S]{0,400}<img\b",
    re.I,
)
_LIGHTBOX_OVERLAY = re.compile(
    r"("
    r"data-photo-lightbox"
    r"|data-lightbox"
    r"|data-photo-viewer"
    r"|role\s*=\s*[\"']dialog[\"'][^>]{0,200}"
    r"(?:lightbox|photo|image|viewer|cas)"
    r"|(?:lightbox|photo-lightbox|photo-viewer|image-lightbox|cas-lightbox)"
    r"[^;{]{0,120}(?:fixed|inset-0|z-\[?5)"
    r"|(?:fixed\s+inset-0|fixed inset-0|inset-0\s+fixed)[^;{]{0,200}"
    r"(?:lightbox|photo-viewer|photoLightbox|data-photo)"
    r"|class=[\"'][^\"']*\b(?:lightbox|photo-lightbox|photo-viewer)\b"
    r"|Dialog\.(?:Root|Content)\b[\s\S]{0,400}"
    r"(?:lightbox|photoLightbox|photo-viewer|casDataUrl|data:)"
    r")",
    re.I | re.S,
)
_LIGHTBOX_FULL_IMG = re.compile(
    r"("
    r"<img\b[^>]{0,500}"
    r"(?:lightbox|photoLightbox|lightboxSrc|viewerSrc|fullSrc|fullsize|"
    r"fullSize|data-photo-lightbox|data-lightbox)"
    r"|(?:lightbox|photoLightbox|lightboxSrc|viewerSrc|fullSrc|"
    r"lightboxUrl|viewerUrl)"
    r"[^;]{0,120}"
    r"(?:casDataUrl|srcs\[|data:|src\s*=)"
    r"|(?:src\s*=\s*\{[^}]{0,120}"
    r"(?:lightbox|photoLightbox|lightboxSrc|viewerSrc|fullSrc|srcs\[)"
    r")"
    r")",
    re.I | re.S,
)
_LIGHTBOX_LOCAL_SRC = re.compile(
    r"("
    r"casDataUrl"
    r"|srcs\s*\[|"
    r"data:"
    r"|lightboxSrc"
    r"|viewerSrc"
    r"|fullSrc"
    r")",
    re.I,
)
_LIGHTBOX_REMOTE_SRC = re.compile(
    r"("
    r"src\s*=\s*[\"']https?://"
    r"|src\s*=\s*\{[^}]{0,160}https?://"
    r"|lightboxSrc\s*=\s*[\"']https?://"
    r"|viewerSrc\s*=\s*[\"']https?://"
    r")",
    re.I,
)
_LIGHTBOX_ESC = re.compile(
    r"("
    r"(?:key|code)\s*===?\s*[\"']Escape[\"']"
    r"|[\"']Escape[\"']\s*===?\s*(?:e\.)?(?:key|code)"
    r"|e\.key\s*===?\s*[\"']Esc[\"']"
    r"|keydown[^;]{0,200}Escape"
    r"|on(?:keydown|keyup)(?:\|\w+)*\s*=\s*\{[^}]{0,200}Escape"
    r")",
    re.I | re.S,
)
_LIGHTBOX_CLOSE = re.compile(
    r"("
    r"closeLightbox"
    r"|closePhoto"
    r"|closeViewer"
    r"|lightboxOpen\s*=\s*(?:false|null|undefined|0)"
    r"|setLightbox(?:Open)?\s*\(\s*(?:false|null|undefined)"
    r"|open\s*=\s*false"
    r"|lightbox\s*=\s*null"
    r"|data-lightbox-close"
    r"|aria-label\s*=\s*[\"'][^\"']*[Cc]lose[^\"']*[\"']"
    r")",
    re.I,
)
_LIGHTBOX_BACKDROP = re.compile(
    r"("
    r"backdrop"
    r"|overlay"
    r"|fixed\s+inset-0"
    r"|inset-0[^;{]{0,80}bg-black"
    r"|bg-black/50"
    r"|bg-black\/\d+"
    r"|on(?:click)(?:\|\w+)*\s*=\s*\{[^}]{0,160}"
    r"(?:closeLightbox|closePhoto|closeViewer|lightboxOpen\s*=\s*false|"
    r"setLightbox|onOpenChange)"
    r")",
    re.I | re.S,
)
_LIGHTBOX_PREV_NEXT = re.compile(
    r"("
    r"\b(?:prev|next)(?:Photo|Image|Lightbox|Attach|Attachment)?\b"
    r"|lightboxIndex\s*[+\-]="
    r"|lightboxIndex\s*\+\s*1"
    r"|lightboxIndex\s*-\s*1"
    r"|ArrowLeft|ArrowRight"
    r"|data-lightbox-(?:prev|next)"
    r"|goTo(?:Prev|Next)"
    r"|show(?:Prev|Next)"
    r")",
    re.I,
)
_SYSTEM_PREVIEW = re.compile(
    r"("
    r"Preview\.app"
    r"|open\s+.*Preview"
    r"|NSWorkspace"
    r"|shell\.open"
    r"|plugin-shell"
    r"|@tauri-apps/plugin-shell"
    r"|revealItemInDir"
    r"|openPath\s*\([^)]*(?:\.jpe?g|\.png|\.gif|\.webp|\.heic|cas_hash|casHash)"
    r"|open\s*\(\s*[\"']file:"
    r")",
    re.I | re.S,
)
_LIGHTBOX_VIDEO_CHROME = re.compile(
    r"("
    r"<video\b[^>]{0,200}(?:lightbox|photo-lightbox|photo-viewer)"
    r"|(?:lightbox|photoLightbox|photo-viewer)[\s\S]{0,300}<video\b"
    r"|lightbox[\s\S]{0,200}\.play\s*\("
    r")",
    re.I | re.S,
)
_HEIC_TRANSCODE = re.compile(
    r"("
    r"heic2any"
    r"|heif-convert"
    r"|libheif"
    r"|transcodeHeic"
    r"|heicToJpeg"
    r"|heicToPng"
    r"|convertHeic"
    r"|decodeHeic"
    r"|heic-decode"
    r")",
    re.I,
)


def _lightbox_name_hit(name: str) -> bool:
    n = name.lower()
    return any(
        tok in n
        for tok in (
            "lightbox",
            "photoviewer",
            "photo-viewer",
            "imageviewer",
            "image-viewer",
            "casviewer",
            "cas-viewer",
        )
    )


def _cas_attach_and_lightbox_sources(crate: Path) -> tuple[str, str, str]:
    """Return (cas_attach, lightbox-ish components only, full web logic).

    Lightbox surface is deliberately narrow: CasAttach + files named/content-
    matched as photo lightbox. Full app logic is only used for HEIC/transcode
    bans and CasAttach wiring checks — not Esc/backdrop (those would false-
    pass on merge Dialog / people-filter Escape).
    """
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    cas = cas_path.read_text() if cas_path.is_file() else ""
    logic = _web_logic(crate)
    extra: list[str] = []
    web = crate / "web"
    for p in sorted(web.rglob("*.svelte")):
        if "node_modules" in p.parts:
            continue
        if p.name == "CasAttach.svelte":
            continue
        text = p.read_text()
        if _lightbox_name_hit(p.name) or _LIGHTBOX_TOKEN.search(text):
            extra.append(text)
    # Also pull .ts helpers that only exist for the lightbox.
    for p in sorted(web.rglob("*.ts")):
        if "node_modules" in p.parts:
            continue
        if _lightbox_name_hit(p.name):
            extra.append(p.read_text())
            continue
        text = p.read_text()
        if _LIGHTBOX_TOKEN.search(text) and re.search(
            r"casDataUrl|lightbox|photoViewer|photoLightbox", text, re.I
        ):
            extra.append(text)
    return cas, "\n".join(extra), logic


def _lightbox_esc_near_close(src: str) -> bool:
    """Escape handler that actually closes the lightbox (not people-filter blur)."""
    if not _LIGHTBOX_ESC.search(src):
        return False
    # Require close-ish action within a window of Escape, or lightbox state.
    for m in _LIGHTBOX_ESC.finditer(src):
        window = src[max(0, m.start() - 240) : m.end() + 240]
        if _LIGHTBOX_CLOSE.search(window) or _LIGHTBOX_TOKEN.search(window):
            return True
        if re.search(
            r"lightboxOpen\s*=\s*false|closeLightbox|setLightbox|viewerOpen\s*=\s*false",
            window,
            re.I,
        ):
            return True
    return False


# #119 — voice-note / audio CAS player (local only; play/pause + time).
_VOICE_KIND = re.compile(
    r"("
    r"kind\s*===\s*[\"']voice[\"']"
    r"|kind\s*==\s*[\"']voice[\"']"
    r"|startsWith\s*\(\s*[\"']audio/"
    r"|audio/\*"
    r"|\.opus|\.ogg|\.mp3|\.m4a|\.aac|\.wav"
    r"|isAudio\s*\("
    r"|isVoice\s*\("
    r")",
    re.I,
)
_VOICE_AUDIO_EL = re.compile(r"<audio\b", re.I)
_VOICE_NATIVE_CONTROLS = re.compile(
    r"<audio\b[^>]*\bcontrols\b|\bcontrols\b[^>]*<audio\b",
    re.I | re.S,
)
# Pin local CAS only: srcs map / casDataUrl / data: — not a generic url/src binding.
_VOICE_LOCAL_SRC = re.compile(
    r"("
    r"src\s*=\s*\{[^}]{0,120}(?:srcs|casDataUrl|data:)"
    r"|src\s*=\s*[\"']data:"
    r")",
    re.I,
)
_VOICE_REMOTE_SRC = re.compile(
    r"("
    r"src\s*=\s*[\"']https?://"
    r"|src\s*=\s*\{[^}]{0,160}https?://"
    r"|new\s+Audio\s*\(\s*[\"']https?://"
    r"|audio(?:Src|Url|URL)?\s*=\s*[\"']https?://"
    r")",
    re.I,
)
_VOICE_PLAY_PAUSE = re.compile(
    r"("
    r"\.play\s*\(|\.pause\s*\("
    r"|togglePlay|playPause|isPlaying|playing\s*="
    r"|aria-label\s*=\s*[\"'][^\"']*(?:[Pp]lay|[Pp]ause)[^\"']*[\"']"
    r"|data-voice-(?:play|pause)"
    r")",
    re.I,
)
_VOICE_TIME_CHROME = re.compile(
    r"("
    r"currentTime|\.duration\b"
    r"|formatTime|formatDuration|audioTime|elapsed"
    r"|data-voice-(?:time|duration|elapsed)"
    r"|aria-valuenow"
    r"|timeupdate"
    r")",
    re.I,
)
_VOICE_OMITTED = re.compile(
    r"("
    r"\.omitted\b"
    r"|a\.omitted"
    r"|omitted\s*\?"
    r"|Media omitted"
    r"|omitted in this export"
    r")",
    re.I,
)
_VOICE_MISSING = re.compile(
    r"("
    r"\.missing\b"
    r"|a\.missing"
    r"|not stored"
    r"|Photo/file not stored"
    r"|file not stored"
    r")",
    re.I,
)
_VOICE_WAVEFORM_CDN = re.compile(
    r"("
    r"wavesurfer"
    r"|waveform\.js"
    r"|cdn\.jsdelivr.*wave"
    r"|unpkg\.com.*wave"
    r"|https?://[^\"'\s)]+(?:waveform|wavesurfer)"
    r"|url\s*\(\s*[\"']https?://[^\"']*wave"
    r"|src\s*=\s*[\"']https?://[^\"']*(?:waveform|wave\.png|spectrogram)"
    r")",
    re.I,
)
_VOICE_TRANSCRIPTION = re.compile(
    r"("
    r"\btranscri(?:be|ption|pt)\b"
    r"|speech[-_]?to[-_]?text"
    r"|whisper\.|openai\.audio"
    r"|data-voice-transcript"
    r"|showTranscript|voiceTranscript"
    r")",
    re.I,
)


# #170 — voice-note seek bar (scrub to time, local only). Follow-up to #119.
_VOICE_SEEK_TRACK = re.compile(
    r"("
    r"<input\b[^>]{0,240}type\s*=\s*[\"']range[\"']"
    r"|type\s*=\s*[\"']range[\"']"
    r"|<progress\b"
    r"|data-voice-(?:seek|scrub|progress)"
    r"|role\s*=\s*[\"']slider[\"']"
    r")",
    re.I | re.S,
)
# Write currentTime on the <audio> from a seek — not the onended reset to 0,
# and not currentTimes state used only for elapsed labels.
_VOICE_SEEK_WRITE = re.compile(
    r"("
    r"\.currentTime\s*=\s*(?!0\b)"
    r"|bind:currentTime"
    r")"
)
_VOICE_VIDEO_SCRUBBER = re.compile(
    r"("
    r"<video\b[^>]{0,400}(?:\bcontrols\b|currentTime|type\s*=\s*[\"']range[\"'])"
    r"|data-video-(?:seek|scrub)"
    r"|video\.currentTime\s*="
    r")",
    re.I | re.S,
)

__all__ = [
    "_LIGHTBOX_TOKEN",
    "_LIGHTBOX_OPEN_CLICK",
    "_LIGHTBOX_IMG_CLICK",
    "_LIGHTBOX_BUTTON_AROUND_IMG",
    "_LIGHTBOX_OVERLAY",
    "_LIGHTBOX_FULL_IMG",
    "_LIGHTBOX_LOCAL_SRC",
    "_LIGHTBOX_REMOTE_SRC",
    "_LIGHTBOX_ESC",
    "_LIGHTBOX_CLOSE",
    "_LIGHTBOX_BACKDROP",
    "_LIGHTBOX_PREV_NEXT",
    "_SYSTEM_PREVIEW",
    "_LIGHTBOX_VIDEO_CHROME",
    "_HEIC_TRANSCODE",
    "_lightbox_name_hit",
    "_cas_attach_and_lightbox_sources",
    "_lightbox_esc_near_close",
    "_VOICE_KIND",
    "_VOICE_AUDIO_EL",
    "_VOICE_NATIVE_CONTROLS",
    "_VOICE_LOCAL_SRC",
    "_VOICE_REMOTE_SRC",
    "_VOICE_PLAY_PAUSE",
    "_VOICE_TIME_CHROME",
    "_VOICE_OMITTED",
    "_VOICE_MISSING",
    "_VOICE_WAVEFORM_CDN",
    "_VOICE_TRANSCRIPTION",
    "_VOICE_SEEK_TRACK",
    "_VOICE_SEEK_WRITE",
    "_VOICE_VIDEO_SCRUBBER",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_timeline_block",
    "_web_logic",
    "_web_sources",
    "_without_comments",
    "annotations",
]
