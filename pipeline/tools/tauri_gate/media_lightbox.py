"""Photo lightbox / voice-note chrome asserts. Imported by gate_tauri.py."""
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


def assert_photo_lightbox(crate: Path) -> None:
    """#118: click CAS thumbnail → in-window full-size overlay (local data only).

    Acceptance: dogfood JPEG opens large from casDataUrl / data:; still no
    http(s) in the viewer. Esc and/or backdrop closes. Optional left/right among
    attachments on the same message. HEIC stays placeholder unless already
    decoded — no HEIC transcode. Not: system Preview, video player chrome.
    Timeline and/or search CAS images (CasAttach is shared) must open the viewer;
    decorative non-CAS imgs alone are not enough.
    """
    cas, lightbox_extra, logic = _cas_attach_and_lightbox_sources(crate)
    if not cas:
        fail("#118: CasAttach.svelte required (CAS thumbnails already use casDataUrl)")
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    app = (crate / "web" / "App.svelte").read_text()
    search = ""
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if search_path.is_file():
        search = search_path.read_text()
    # Surfaces for the photo viewer only (not merge Dialog / whole App).
    surface = cas + "\n" + lightbox_extra
    cleaned = _without_comments(surface)
    cleaned_cas = _without_comments(cas)

    # 0) Baseline: still load via local casDataUrl, never remote in CasAttach.
    if "casDataUrl" not in cas:
        fail(
            "#118: CAS thumbnails must load via casDataUrl (local data: URL) — "
            "lightbox reuses the same bytes, not a remote host"
        )
    if re.search(r"[\"']https?://", cleaned_cas) or re.search(
        r"src\s*=\s*[\"']https?://", cas, re.I
    ):
        fail("#118: CasAttach must not use remote http(s) URLs for attachments")

    # 1) Open path: click on a CAS image thumbnail (not only decorative img).
    has_img = bool(re.search(r"<img\b", cas, re.I))
    if not has_img:
        fail(
            "#118: CasAttach must render a CAS <img> thumbnail that can open "
            "the lightbox (JPEG/PNG/… already decoded via casDataUrl)"
        )
    open_click = bool(_LIGHTBOX_OPEN_CLICK.search(surface)) or bool(
        _LIGHTBOX_OPEN_CLICK.search(cleaned)
    )
    img_click = bool(_LIGHTBOX_IMG_CLICK.search(surface))
    btn_img = bool(_LIGHTBOX_BUTTON_AROUND_IMG.search(surface))
    # cursor-pointer + click handler on the CAS image surface.
    pointer_click = bool(
        re.search(
            r"(?:cursor-pointer|role\s*=\s*[\"']button[\"'])[\s\S]{0,200}<img\b"
            r"|<img\b[\s\S]{0,200}(?:cursor-pointer|role\s*=\s*[\"']button[\"'])",
            surface,
            re.I,
        )
    ) and bool(
        re.search(
            r"(?:on:click|onclick)(?:\|\w+)*\s*=\s*\{",
            surface,
            re.I,
        )
    )
    if not (open_click or img_click or btn_img or pointer_click):
        fail(
            "#118: CAS photo thumbnail must be clickable to open an in-window "
            "lightbox (onclick / openLightbox / button wrapping <img>) — "
            "passive decorative <img> only is not enough"
        )

    # Timeline and/or search must surface CasAttach (shared component covers both).
    timeline_has_cas = "CasAttach" in app or bool(
        re.search(r"casDataUrl|CasAttach", _timeline_block(crate) + "\n" + app)
    )
    search_has_cas = "CasAttach" in search or bool(
        re.search(r"casDataUrl|CasAttach", search)
    )
    if not (timeline_has_cas or search_has_cas):
        fail(
            "#118: lightbox open path must be reachable from timeline and/or "
            "search CAS images (CasAttach on person timeline / SearchPane)"
        )
    if timeline_has_cas and search_path.is_file() and not search_has_cas:
        if re.search(r"attachments|cas_hash|casHash", search) and re.search(
            r"<img\b", search, re.I
        ):
            fail(
                "#118: SearchPane CAS images must share the lightbox open path "
                "(CasAttach or the same click → overlay handler)"
            )

    # 2) Overlay / lightbox / modal with a full-size image.
    has_token = bool(_LIGHTBOX_TOKEN.search(surface)) or bool(
        _LIGHTBOX_TOKEN.search(cleaned)
    )
    has_overlay = bool(_LIGHTBOX_OVERLAY.search(surface)) or bool(
        _LIGHTBOX_OVERLAY.search(cleaned)
    )
    dialog_lightbox = bool(
        re.search(
            r"Dialog\.(?:Root|Content)\b[\s\S]{0,500}"
            r"(?:lightbox|photoLightbox|photoViewer|viewerOpen|lightboxOpen)"
            r"|(?:lightbox|photoLightbox|photoViewer|viewerOpen|lightboxOpen)"
            r"[\s\S]{0,500}Dialog\.(?:Root|Content)\b",
            surface + "\n" + cleaned,
            re.I,
        )
    )
    if not (has_token and (has_overlay or dialog_lightbox)):
        if not has_overlay and not dialog_lightbox:
            fail(
                "#118: need an in-window photo overlay / lightbox / modal "
                "(fixed inset overlay, data-photo-lightbox, or Dialog bound to "
                "lightbox state) — not only the thumbnail"
            )
        fail(
            "#118: photo lightbox needs a named open state / surface "
            "(lightbox / photoLightbox / data-photo-lightbox / openLightbox)"
        )

    has_full_img = bool(_LIGHTBOX_FULL_IMG.search(surface)) or bool(
        _LIGHTBOX_FULL_IMG.search(cleaned)
    )
    if not has_full_img:
        overlay_img = bool(
            re.search(
                r"(?:lightbox|photoLightbox|photo-viewer|data-photo-lightbox|"
                r"data-lightbox|viewerOpen|lightboxOpen)"
                r"[\s\S]{0,800}<img\b",
                surface + "\n" + cleaned,
                re.I,
            )
        ) and bool(_LIGHTBOX_LOCAL_SRC.search(surface + "\n" + cleaned))
        if not overlay_img:
            fail(
                "#118: lightbox must show a full-size <img> from local "
                "casDataUrl / data: / srcs (same CAS bytes as the thumbnail)"
            )

    # 3) Viewer src stays local — no http(s) remote host.
    if _LIGHTBOX_REMOTE_SRC.search(surface) or _LIGHTBOX_REMOTE_SRC.search(cleaned):
        fail(
            "#118: photo lightbox viewer must not use http(s) src — "
            "only local casDataUrl / data: URLs"
        )
    if re.search(
        r"(?:fetch\s*\(\s*[\"']https?://|axios\.|new\s+Image\s*\([^)]*https?://)",
        cleaned,
        re.I,
    ):
        fail("#118: lightbox must not fetch remote image hosts")

    # 4) Close via Esc and/or backdrop click (scoped to lightbox surface).
    has_esc = _lightbox_esc_near_close(surface) or _lightbox_esc_near_close(cleaned)
    dialog_escape_ok = dialog_lightbox
    # Narrow close: named closeLightbox / lightboxOpen=false — not bare open=false
    # (merge Dialog uses open=false and would false-pass if we scanned App).
    has_close = bool(
        re.search(
            r"("
            r"closeLightbox"
            r"|closePhoto"
            r"|closeViewer"
            r"|lightboxOpen\s*=\s*(?:false|null|undefined|0)"
            r"|setLightbox(?:Open)?\s*\(\s*(?:false|null|undefined)"
            r"|viewerOpen\s*=\s*(?:false|null|undefined)"
            r"|photoLightbox\s*=\s*null"
            r"|data-lightbox-close"
            r")",
            surface + "\n" + cleaned,
            re.I,
        )
    )
    has_backdrop = bool(
        re.search(
            r"("
            r"(?:on:click|onclick)(?:\|\w+)*\s*=\s*\{[^}]{0,200}"
            r"(?:closeLightbox|closePhoto|closeViewer|lightboxOpen\s*=\s*false|"
            r"setLightbox|viewerOpen\s*=\s*false)"
            r"|(?:lightbox|photo-lightbox|data-photo-lightbox|data-lightbox)"
            r"[^;{]{0,200}(?:fixed\s+inset-0|inset-0|bg-black)"
            r"|(?:fixed\s+inset-0|inset-0)[^;{]{0,200}"
            r"(?:lightbox|photo-lightbox|data-photo-lightbox|closeLightbox)"
            r"|backdrop[^;]{0,80}(?:closeLightbox|lightboxOpen)"
            r")",
            surface + "\n" + cleaned,
            re.I | re.S,
        )
    )
    if not (has_esc or dialog_escape_ok):
        fail(
            "#118: lightbox must close on Escape "
            "(keydown Escape → closeLightbox / lightboxOpen=false, "
            "or Dialog.Root bound to lightbox state)"
        )
    if not (has_backdrop or has_close or dialog_lightbox):
        fail(
            "#118: lightbox must close via backdrop click and/or an explicit "
            "close control (closeLightbox / lightboxOpen = false)"
        )
    if not dialog_escape_ok and has_esc and not (has_backdrop or has_close):
        fail(
            "#118: custom lightbox overlay needs backdrop click or close control "
            "in addition to Escape"
        )

    # 5) Optional prev/next among same-message attachments — if present, must
    # stay on the message's attachment list (not a global gallery).
    if _LIGHTBOX_PREV_NEXT.search(surface) or _LIGHTBOX_PREV_NEXT.search(cleaned):
        same_message = bool(
            re.search(
                r"("
                r"items\s*\[|"
                r"attachments\s*\[|"
                r"messageAttachments|"
                r"sameMessage|"
                r"filter\s*\(\s*(?:a|att|item)\s*=>[\s\S]{0,120}isImage|"
                r"lightboxIndex|"
                r"attach(?:ment)?Index|"
                r"imageItems|"
                r"imageAttachments"
                r")",
                surface + "\n" + cleaned,
                re.I,
            )
        )
        if not same_message:
            fail(
                "#118: lightbox prev/next must walk attachments on the same "
                "message (items / attachments / lightboxIndex), not a global "
                "gallery across the archive"
            )

    # 6) HEIC: not required to open; no HEIC transcode code (whole UI).
    if _HEIC_TRANSCODE.search(blob) or _HEIC_TRANSCODE.search(logic):
        fail(
            "#118: do not add HEIC transcode (heic2any / libheif / heicToJpeg) — "
            "HEIC stays placeholder unless already decoded"
        )
    # Explicitly do not require heic in the open path (no fail if absent).

    # 7) No system Preview / external open for the photo viewer.
    if _SYSTEM_PREVIEW.search(surface) or _SYSTEM_PREVIEW.search(cleaned):
        fail(
            "#118: photo lightbox must stay in-window — no system Preview, "
            "shell.open, or revealItemInDir for CAS images"
        )
    if re.search(
        r"(?:openPath|open\s*\()\s*[\s\S]{0,120}"
        r"(?:cas_hash|casHash|filename|\.jpe?g|\.png|\.heic|lightbox)",
        surface,
        re.I,
    ):
        fail(
            "#118: do not shell-open attachment paths from the lightbox "
            "(in-window overlay only; not macOS Preview)"
        )

    # 8) No video player chrome in the photo lightbox (voice-note is #119).
    if _LIGHTBOX_VIDEO_CHROME.search(surface) or _LIGHTBOX_VIDEO_CHROME.search(cleaned):
        fail(
            "#118: photo lightbox must not embed a <video> player "
            "(images only; voice-note chrome is a separate issue)"
        )


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


def assert_voice_note_player(crate: Path) -> None:
    """#119: voice/audio CAS attachments play in-app (local only).

    Acceptance: opus/mp3 (and other audio/* / kind===voice) play via an in-app
    player with play/pause and time/duration chrome. Native <audio controls> is
    enough; custom chrome must expose both. Source is casDataUrl / data: (same
    path as other CAS) — no remote streaming URL. Omitted/missing stay
    placeholders (no fake player). Not: waveform-from-CDN, transcription.
    """
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail("#119: CasAttach.svelte required for voice/audio CAS attachments")
    cas = cas_path.read_text()
    cleaned = _without_comments(cas)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    logic = _web_logic(crate)
    surface = cas + "\n" + logic

    # 0) Local CAS path only — same casDataUrl / data: as photos.
    if "casDataUrl" not in cas:
        fail(
            "#119: voice notes must load via casDataUrl (local data: URL), "
            "not a remote stream"
        )
    if re.search(r"[\"']https?://", cleaned) or re.search(
        r"src\s*=\s*[\"']https?://", cas, re.I
    ):
        fail("#119: CasAttach must not use remote http(s) URLs for voice/audio")
    if _VOICE_REMOTE_SRC.search(cas) or _VOICE_REMOTE_SRC.search(cleaned):
        fail(
            "#119: audio player must not use http(s) src — only local "
            "casDataUrl / data: (no streaming CDN)"
        )

    # 1) Classify voice/audio (kind, mime, or extension).
    if not _VOICE_KIND.search(cas):
        fail(
            "#119: CasAttach must detect voice/audio attachments "
            "(kind === \"voice\", audio/* mime, or .opus/.ogg/.mp3/.m4a/.aac/.wav)"
        )

    # 2) In-app player: native <audio controls> OR custom play/pause + time.
    has_audio = bool(_VOICE_AUDIO_EL.search(cas))
    if not has_audio:
        fail(
            "#119: voice/audio CAS attachments need an in-app <audio> player "
            "(play opus/mp3 in-window; not shell-open only)"
        )
    native = bool(_VOICE_NATIVE_CONTROLS.search(cas))
    custom_play = bool(_VOICE_PLAY_PAUSE.search(cas) or _VOICE_PLAY_PAUSE.search(cleaned))
    custom_time = bool(_VOICE_TIME_CHROME.search(cas) or _VOICE_TIME_CHROME.search(cleaned))
    if not (native or (custom_play and custom_time)):
        fail(
            "#119: audio player needs play/pause and time/duration chrome "
            "(native <audio controls>, or custom play/pause + currentTime/duration)"
        )
    if not _VOICE_LOCAL_SRC.search(cas):
        fail(
            "#119: <audio> src must be local casDataUrl / data: / srcs "
            "(same CAS bytes path as images)"
        )

    # 3) Omitted / missing stay placeholders — no player on those branches.
    if not _VOICE_OMITTED.search(cas):
        fail(
            "#119: omitted attachments must stay placeholders "
            "(branch on .omitted — no fake voice player)"
        )
    if not _VOICE_MISSING.search(cas):
        fail(
            "#119: missing attachments must stay placeholders "
            "(branch on .missing / not stored — no fake voice player)"
        )
    # Audio must not render on the omitted path: require loadable guards
    # (srcs / !broken / !omitted) near <audio>, not a bare always-on player.
    audio_m = _VOICE_AUDIO_EL.search(cas)
    if audio_m:
        window = cas[max(0, audio_m.start() - 400) : audio_m.end() + 200]
        guarded = bool(
            re.search(
                r"("
                r"srcs\s*\[|srcs\s*\.|!broken|broken\s*\[|"
                r"!a\.omitted|!omitted|!a\.missing|!missing|"
                r"hashOf\s*\(|cas_hash|casHash"
                r")",
                window,
                re.I,
            )
        )
        if not guarded:
            fail(
                "#119: <audio> must only render for loadable voice/audio "
                "(srcs / hash present, not omitted/missing) — placeholders otherwise"
            )
        # If audio sits inside the omitted branch, reject.
        before = cas[: audio_m.start()]
        # Last relevant branch marker before <audio>.
        last_omitted = max(before.rfind("omitted"), before.rfind("Media omitted"))
        last_missing = max(
            before.rfind(".missing"),
            before.rfind("not stored"),
            before.rfind("a.missing"),
        )
        last_audio_guard = max(
            before.rfind("isAudio"),
            before.rfind("isVoice"),
            before.rfind("audio/"),
            before.rfind("kind === \"voice\""),
            before.rfind("kind === 'voice'"),
        )
        if last_omitted > last_audio_guard and last_omitted > 0:
            # Only fail if no {:else if isAudio} sits after omitted closer to audio.
            if last_audio_guard < last_omitted:
                fail(
                    "#119: do not put the voice player on the omitted branch — "
                    "omitted stays a placeholder"
                )
        if last_missing > last_audio_guard and last_missing > 0:
            if last_audio_guard < last_missing:
                fail(
                    "#119: do not put the voice player on the missing branch — "
                    "missing stays a placeholder"
                )

    # 4) Reachable from timeline and/or search (shared CasAttach).
    app = (crate / "web" / "App.svelte").read_text()
    search = ""
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if search_path.is_file():
        search = search_path.read_text()
    timeline_has_cas = "CasAttach" in app or bool(
        re.search(r"casDataUrl|CasAttach", _timeline_block(crate) + "\n" + app)
    )
    search_has_cas = "CasAttach" in search
    if not (timeline_has_cas or search_has_cas):
        fail(
            "#119: voice player must be reachable from timeline and/or search "
            "CAS attachments (CasAttach)"
        )

    # 5) Not in scope: waveform-from-CDN, transcription UI.
    if _VOICE_WAVEFORM_CDN.search(surface) or _VOICE_WAVEFORM_CDN.search(blob):
        fail(
            "#119: not in scope — no waveform visualization from a CDN "
            "(wavesurfer / remote wave assets)"
        )
    if _VOICE_TRANSCRIPTION.search(cleaned) or _VOICE_TRANSCRIPTION.search(
        _without_comments(blob)
    ):
        fail(
            "#119: not in scope — no transcription UI "
            "(transcribe / speech-to-text / transcript pane)"
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


def assert_voice_note_seek(crate: Path) -> None:
    """#170: voice-note player has a local-only seek / progress track.

    Acceptance: user can click or drag a progress track to jump mid-note.
    Seeking writes currentTime (or equivalent) on the local <audio>.
    Source stays casDataUrl / data: — no http(s) stream. Play/pause and
    elapsed/duration remain (#119). Omitted/missing stay placeholders
    (no seek bar). Not: CDN waveform, transcription, video scrubber.
    Docs: docs/user/app.md — scrub a local voice note; still no remote stream.
    """
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail("#170: CasAttach.svelte required for the voice-note seek bar")
    cas = cas_path.read_text()
    cleaned = _without_comments(cas)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    logic = _web_logic(crate)
    surface = cas + "\n" + logic
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 0) Local CAS path only — same casDataUrl / data: as #119. No http(s) stream.
    if "casDataUrl" not in cas:
        fail(
            "#170: voice notes must stay on casDataUrl (local data: URL), "
            "not a remote stream"
        )
    if re.search(r"[\"']https?://", cleaned) or re.search(
        r"src\s*=\s*[\"']https?://", cas, re.I
    ):
        fail("#170: CasAttach must not use remote http(s) URLs for voice/audio")
    if _VOICE_REMOTE_SRC.search(cas) or _VOICE_REMOTE_SRC.search(cleaned):
        fail(
            "#170: seek must not stream http(s) — only local "
            "casDataUrl / data:"
        )
    if not _VOICE_LOCAL_SRC.search(cas):
        fail(
            "#170: <audio> src must stay local casDataUrl / data: / srcs "
            "(no http(s) stream)"
        )

    # 1) Progress track the user can click or drag.
    if not _VOICE_SEEK_TRACK.search(cas):
        fail(
            "#170: voice-note player must have a progress track "
            "(range / progress / seek) the user can click or drag"
        )

    # 2) Seeking writes currentTime on the local <audio>.
    if not _VOICE_SEEK_WRITE.search(cas) and not _VOICE_SEEK_WRITE.search(cleaned):
        fail(
            "#170: seeking must write currentTime (or equivalent) "
            "on the local <audio>"
        )

    # 3) Play/pause + elapsed/duration remain (#119).
    has_audio = bool(_VOICE_AUDIO_EL.search(cas))
    if not has_audio:
        fail(
            "#170: voice-note seek bar is on the in-app <audio> player "
            "(keep play/pause + time from #119)"
        )
    native = bool(_VOICE_NATIVE_CONTROLS.search(cas))
    custom_play = bool(_VOICE_PLAY_PAUSE.search(cas) or _VOICE_PLAY_PAUSE.search(cleaned))
    custom_time = bool(_VOICE_TIME_CHROME.search(cas) or _VOICE_TIME_CHROME.search(cleaned))
    if not (native or (custom_play and custom_time)):
        fail(
            "#170: play/pause and elapsed/duration must remain "
            "(#119 chrome stays; seek bar is in addition)"
        )

    # 4) Omitted / missing stay placeholders — no seek bar on those branches.
    if not _VOICE_OMITTED.search(cas):
        fail(
            "#170: omitted attachments must stay placeholders "
            "(no seek bar on omitted)"
        )
    if not _VOICE_MISSING.search(cas):
        fail(
            "#170: missing attachments must stay placeholders "
            "(no seek bar on missing)"
        )
    track_m = _VOICE_SEEK_TRACK.search(cas)
    if track_m:
        before = cas[: track_m.start()]
        last_omitted = max(before.rfind("omitted"), before.rfind("Media omitted"))
        last_missing = max(
            before.rfind(".missing"),
            before.rfind("not stored"),
            before.rfind("a.missing"),
        )
        last_audio_guard = max(
            before.rfind("isAudio"),
            before.rfind("isVoice"),
            before.rfind("data-voice-note"),
            before.rfind("audio/"),
            before.rfind('kind === "voice"'),
            before.rfind("kind === 'voice'"),
        )
        if last_omitted > last_audio_guard and last_omitted > 0:
            fail(
                "#170: do not put the seek bar on the omitted branch — "
                "omitted stays a placeholder"
            )
        if last_missing > last_audio_guard and last_missing > 0:
            fail(
                "#170: do not put the seek bar on the missing branch — "
                "missing stays a placeholder"
            )

    # 5) Not in scope: waveform-from-CDN, transcription, video scrubber.
    if _VOICE_WAVEFORM_CDN.search(surface) or _VOICE_WAVEFORM_CDN.search(blob):
        fail(
            "#170: not in scope — no waveform visualization from a CDN "
            "(wavesurfer / remote wave assets)"
        )
    if _VOICE_TRANSCRIPTION.search(cleaned) or _VOICE_TRANSCRIPTION.search(
        _without_comments(blob)
    ):
        fail(
            "#170: not in scope — no transcription UI "
            "(transcribe / speech-to-text / transcript pane)"
        )
    if _VOICE_VIDEO_SCRUBBER.search(cas) or _VOICE_VIDEO_SCRUBBER.search(cleaned):
        fail("#170: not in scope — no video scrubber")

    # 6) Docs: scrub a local voice note; still no remote stream.
    # Window on voice/audio lines so Search “seeks near sent_at” is not a hit.
    if not dtxt.strip():
        fail("#170: docs/user/app.md required (scrub a local voice note)")
    voice_doc = ""
    for m in re.finditer(
        r".{0,160}(?:voice notes?|audio).{0,160}",
        dtxt,
        re.I | re.S,
    ):
        voice_doc += m.group(0) + "\n"
    if not re.search(r"\b(?:scrub|seek)\w*\b", voice_doc, re.I):
        fail("#170: docs/user/app.md must say you can scrub a local voice note")
    if not re.search(
        r"("
        r"never a remote stream"
        r"|no remote stream"
        r"|not a remote stream"
        r"|remote stream"
        r")",
        voice_doc,
        re.I,
    ):
        fail(
            "#170: docs/user/app.md must still say voice notes are not a remote stream"
        )
