"""Media / bubble chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    CSP,
    _ARBITRARY_SHELL,
    _CHROME_SEARCH_HOOK,
    _FOCUS_SEARCH_Q,
    _HTML_BODY,
    _KEY_F,
    _LINKIFY_FETCH,
    _MIN_W0,
    _OVERFLOW_X_HIDDEN,
    _PLUGIN_SHELL,
    _SHELL_CAP,
    _SHOW_QUOTED,
    _VIEW_SEARCH_ASSIGN,
    _WRITE_TEXT,
    _app_keydown_body,
    _call_arg,
    _element_block_at,
    _expand_fn_calls,
    _function_body,
    _hook_element_blocks,
    _invoke_payloads,
    _payload_has_path_or_url,
    _rust_body_with_callees,
    _rust_call_arg,
    _rust_fn_signature,
    _rust_function_body,
    _svelte_if_chains,
    _svelte_markup,
    _tauri_rust_blob,
    _timeline_block,
    _ts_fn_body,
    _ts_function_body,
    _web_logic,
    _web_sources,
    _windows_around,
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


# #272 — linkify http(s) URLs in timeline bubbles (text nodes / <a> siblings).
_LINKIFY_UNSPLIT_BODY = re.compile(
    r"(?<![=])\{displayBody\s*\(\s*"
    r"(?:"
    r"(?:(?:item\.)?row\.)?body_text"
    r"|parts\.(?:main|quoted)"
    r")"
)
_LINKIFY_EACH = re.compile(
    r"\{#each\s+(?:"
    r"[^}]*\b(?:seg(?:ment)?s?|parts|chunks|links|tokens|urls)\b"
    r"|[^}]{0,100}(?:splitUrl|splitLink|splitHttp|linkify|urlSeg|"
    r"bodySeg|segmentUrl|parseUrl)"
    r")",
    re.I,
)
_LINKIFY_SEG_TEXT = re.compile(
    r"\{(?:seg|s|part|chunk|token|link|item)\.text\}"
)
_LINKIFY_ANCHOR = re.compile(r"<a\b", re.I)
_LINKIFY_NAMED_BTN = re.compile(
    r"("
    r"data-(?:bubble-link|body-link|url-link|open-url|linkify|url-button)"
    r"|<button\b[^>]{0,260}(?:openUrl|openURL|openLink|openBubbleUrl|"
    r"openHttp|onBubbleLink|onUrlClick|confirmOpenUrl)"
    r")",
    re.I,
)
_LINKIFY_HELPER_FN = re.compile(
    r"\b(?:"
    r"splitUrls|splitUrl|splitLinks|splitLink|splitBodyUrls|splitBodyLinks|"
    r"linkifyBody|linkifySegments|urlSegments|splitHttpUrls|splitHttp|"
    r"bodySegments|segmentUrls|parseUrls|extractUrls|linkify"
    r")\b"
)
_LINKIFY_KIND_URL = re.compile(
    r"kind\s*:\s*[\"']url[\"']|kind\s*===?\s*[\"']url[\"']"
)
_LINKIFY_HTTP_DETECT = re.compile(
    r"("
    r"https://example\.com/a"
    r"|https\?:\\?/\\?/"
    r"|https\?://"
    r"|[\"']https?://[\"']"
    r"|startsWith\s*\(\s*[\"']https?://"
    r"|starts_with\s*\(\s*[\"']https?://"
    r"|[\"']https://[\"'][\s\S]{0,120}[\"']http://"
    r"|[\"']http://[\"'][\s\S]{0,120}[\"']https://"
    r")",
    re.I,
)
_LINKIFY_BROAD_SCHEME = re.compile(
    r"("
    r"\[a-zA-Z\]\[a-zA-Z0-9+.\-\]\*:/"
    r"|\\\\w\+:/"
    r"|\[a-zA-Z\]\[a-zA-Z0-9+.\-\]\*:"
    r")"
)
_LINKIFY_BAD_SCHEME_ALLOW = re.compile(
    r"("
    r"(?:scheme|protocol)s?\s*=\s*\[[^\]]*(?:javascript:|data:|file:|tauri:)"
    r"|[\"'](?:javascript|data|file|tauri)://?[\"'][^;]{0,160}"
    r"[\"']https?://"
    r"|[\"']https?://[\"'][^;]{0,160}"
    r"[\"'](?:javascript|data|file|tauri):"
    r")",
    re.I,
)
_LINKIFY_UNSAFE_HTML = re.compile(
    r"("
    r"\{@html\b"
    r"|\.innerHTML\s*="
    r"|insertAdjacentHTML\s*\("
    r"|dangerouslySetInnerHTML"
    r")"
)
_LINKIFY_HTML_STRING = re.compile(
    r"("
    r"\.replace\s*\([^)]{0,200},\s*[`'\"][^`'\"]*<a\b"
    r"|return\s+[`'\"][^`'\"]*<a\b"
    r")",
    re.I,
)
_LINKIFY_NAVIGATE = re.compile(
    r"("
    r"window\.open\s*\("
    r"|location\.href\s*="
    r"|location\.assign\s*\("
    r")"
)
_LINKIFY_OPEN_FN = re.compile(
    r"\b(?:"
    r"openUrl|openURL|openLink|openBubbleUrl|openHttp|openHttps|"
    r"openExternal|openExternalUrl|confirmOpenUrl|confirmUrl|"
    r"onBubbleLink|onUrlClick|askOpenUrl"
    r")\b"
)
_LINKIFY_CMD_SNAKE = (
    "open_url",
    "open_http",
    "open_https",
    "open_http_url",
    "open_https_url",
    "open_external_url",
    "open_external",
    "open_bubble_url",
    "open_link",
    "open_os_url",
)
_LINKIFY_SKIP_EXTRA = frozenset(
    {
        "App.svelte",
        "SearchPane.svelte",
        "snippetHighlight.ts",
        "ConfirmDialog.svelte",
        "CasAttach.svelte",
        "CasVideo.svelte",
        "CasPdf.svelte",
        "ReviewPane.svelte",
        "ImportPane.svelte",
        "DoctorPane.svelte",
        "EmptyState.svelte",
        "api.ts",
    }
)


def _bubble_body_blocks(src: str) -> list[str]:
    """data-bubble-body element(s), including WA + Gmail branches."""
    return _hook_element_blocks(src, "data-bubble-body")


def _bubble_linkify_extra(crate: Path, host: str) -> str:
    """Helpers / child chrome App actually mounts for bubble URL split.

    Unwired drafts do not count. snippetHighlight / SearchPane stay #126.
    """
    web = crate / "web"
    if not web.is_dir():
        return ""
    extra: list[str] = []
    for p in sorted(web.rglob("*")):
        if "node_modules" in p.parts:
            continue
        if p.suffix not in {".svelte", ".ts"}:
            continue
        if p.name in _LINKIFY_SKIP_EXTRA:
            continue
        name_hit = bool(
            re.search(
                r"linkify|splitUrl|urlSeg|bodyLink|bubbleLink|bodyUrl|httpUrl",
                p.name,
                re.I,
            )
        )
        text = p.read_text()
        hook = bool(
            _LINKIFY_KIND_URL.search(text)
            or _LINKIFY_NAMED_BTN.search(text)
            or _LINKIFY_HELPER_FN.search(text)
        )
        if not name_hit and not hook:
            continue
        stem = p.stem
        if stem in host or re.search(
            rf"\b{re.escape(stem)}\b|{re.escape(p.name)}", host
        ):
            extra.append(text)
    return "\n".join(extra)


def _strip_anchor_tags(src: str) -> str:
    return re.sub(r"<a\b[^>]*>[\s\S]*?</a>", " ", src, flags=re.I)


def _has_url_split_render(src: str) -> bool:
    """Sibling <a> or named button plus a segment each — not one HTML string."""
    clickable = bool(_LINKIFY_ANCHOR.search(src) or _LINKIFY_NAMED_BTN.search(src))
    split = bool(_LINKIFY_EACH.search(src) or _LINKIFY_HELPER_FN.search(src))
    segs = bool(_LINKIFY_SEG_TEXT.search(src))
    return clickable and split and segs


def _has_text_node_segments(src: str) -> bool:
    """Surrounding words are `{seg.text}` (or equivalent), not only inside <a>."""
    if re.search(
        r"\{:else(?:\s+if\s+[^}]*)?\}[\s\S]{0,240}" + _LINKIFY_SEG_TEXT.pattern,
        src,
    ):
        return True
    if re.search(
        r"kind\s*===?\s*[\"']text[\"'][\s\S]{0,240}" + _LINKIFY_SEG_TEXT.pattern,
        src,
    ):
        return True
    return bool(_LINKIFY_SEG_TEXT.search(_strip_anchor_tags(src)))


def _linkify_split_src(app: str, extra: str, body: str) -> str:
    """Bodies of the URL-split helper(s) actually used on the bubble."""
    parts = [extra, body]
    names = set(_LINKIFY_HELPER_FN.findall(body + "\n" + extra))
    for m in re.finditer(r"\{#each\s+([^}]+)\}", body + "\n" + extra):
        for ident in re.findall(r"\b([A-Za-z_]\w*)\s*\(", m.group(1)):
            names.add(ident)
    for m in re.finditer(
        r"\b([A-Za-z_]\w*)\s*\(\s*displayBody\s*\(", body + "\n" + extra
    ):
        names.add(m.group(1))
    blob = app + "\n" + extra
    for name in names:
        fn = _ts_function_body(blob, name) or _function_body(blob, name)
        if fn:
            parts.append(fn)
    return "\n".join(parts)


def _linkify_open_handler(app: str, extra: str) -> str:
    blob = app + "\n" + extra
    chunks: list[str] = []
    for m in _LINKIFY_OPEN_FN.finditer(blob):
        name = m.group(0)
        fn = _ts_function_body(blob, name) or _function_body(blob, name)
        if fn:
            chunks.append(fn)
    if not chunks:
        # onclick / ask() around a url argument on the bubble surface.
        chunks.append(
            _windows_around(
                blob,
                re.compile(
                    r"\bask\s*\([\s\S]{0,200}\b(?:url|href|link)\b"
                    r"|\b(?:url|href|link)\b[\s\S]{0,200}\bask\s*\("
                    r"|confirmDesc\s*=\s*[^\n]{0,80}\burl\b",
                    re.I,
                ),
                before=80,
                after=240,
            )
        )
    return "\n".join(chunks)


def _find_open_url_cmd(rust: str, web: str) -> str:
    """Rust command that OS-opens a URL (not reveal_cas)."""
    blob = rust + "\n" + web
    for name in _LINKIFY_CMD_SNAKE:
        if re.search(rf"\bfn\s+{re.escape(name)}\b", rust) or re.search(
            rf"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']{re.escape(name)}[\"']",
            web,
        ):
            return name
    camel = re.search(
        r"\bopen(?:Url|URL|Http|Https|ExternalUrl|BubbleUrl|Link)\s*[:=]",
        web,
    )
    if camel:
        for name in _LINKIFY_CMD_SNAKE:
            if name.replace("_", "") in camel.group(0).lower():
                if re.search(rf"\bfn\s+{re.escape(name)}\b", rust):
                    return name
    gh = re.search(r"generate_handler!\s*\[([^\]]*)\]", rust, re.S)
    if not gh:
        return ""
    for name in re.findall(r"\b([a-z][a-z0-9_]*)\b", gh.group(1)):
        if name == "reveal_cas":
            continue
        sig = _rust_fn_signature(rust, name)
        body = _rust_function_body(rust, name)
        if "/usr/bin/open" in body and re.search(r"\burl\b", sig, re.I):
            return name
    if "open_url" in blob or "openUrl" in web:
        if re.search(r"\bfn\s+open_url\b", rust):
            return "open_url"
    return ""


def _rust_http_only(body: str) -> bool:
    """True when the command allows http/https and not javascript/data/file/tauri."""
    http = bool(
        re.search(
            r"("
            r"starts_with\s*\(\s*[\"']https?://"
            r"|starts_with\s*\(\s*[\"']http://"
            r"[\s\S]{0,160}starts_with\s*\(\s*[\"']https://"
            r"|starts_with\s*\(\s*[\"']https://"
            r"[\s\S]{0,160}starts_with\s*\(\s*[\"']http://"
            r"|https\?://"
            r"|(?:scheme|protocol)\s*==\s*[\"']https?[\"']"
            r")",
            body,
        )
    )
    if not http:
        return False
    if _LINKIFY_BAD_SCHEME_ALLOW.search(body):
        return False
    # file:/javascript: OR'd into the same allow as http.
    if re.search(
        r"starts_with\s*\(\s*[\"'](?:http://|https://)[\"'][\s\S]{0,200}"
        r"starts_with\s*\(\s*[\"'](?:javascript|data|file|tauri):",
        body,
    ):
        return False
    return True


# #272 follow-up — long URL overflow + visible Open link.
# break-words (overflow-wrap: break-word) is not enough for a no-space URL.
_LINKIFY_WRAP_ANY = re.compile(
    r"("
    r"\bbreak-all\b"
    r"|overflow-wrap\s*:\s*anywhere"
    r"|overflow-wrap-anywhere"
    r"|\[overflow-wrap:anywhere\]"
    r"|wrap-anywhere"
    r"|break-anywhere"
    r")",
    re.I,
)
_LINKIFY_OPEN_LINK_LABEL = re.compile(r"Open link")
_LINKIFY_CONFIRM_LABEL_PROP = re.compile(r"\bconfirmLabel\b")


def _linkify_anchor_surface(surface: str) -> str:
    """The bubble <a data-bubble-link> / named link button — not the body <p>."""
    for hook in (
        "data-bubble-link",
        "data-body-link",
        "data-url-link",
        "data-open-url",
        "data-linkify",
        "data-url-button",
    ):
        blocks = _hook_element_blocks(surface, hook)
        if blocks:
            return "\n".join(blocks)
    return _windows_around(surface, re.compile(r"<a\b", re.I), before=0, after=240)


def _linkify_confirm_desc_blob(confirm_src: str, desc_src: str) -> str:
    """ConfirmDialog description chrome — not the whole dialog / title."""
    parts = [
        _windows_around(
            confirm_src, re.compile(r"\{description\}"), before=160, after=40
        ),
        "\n".join(_hook_element_blocks(confirm_src, "Dialog.Description")),
        desc_src,
    ]
    return "\n".join(parts)


def _linkify_dialog_content_blob(confirm_src: str, content_src: str) -> str:
    """ConfirmDialog Content open-tag classes and/or shared dialog-content."""
    opens = re.findall(r"<Dialog\.Content\b[^>]*>", confirm_src)
    return "\n".join(opens) + "\n" + content_src


def _linkify_width_capped(blob: str) -> bool:
    """min-w-0 and/or overflow-x-hidden — max-w-md alone still grows min-content."""
    return bool(_MIN_W0.search(blob) or _OVERFLOW_X_HIDDEN.search(blob))


def assert_bubble_linkify(crate: Path) -> None:
    """#272: http(s) URLs in timeline bubbles are sibling <a> / button.

    Acceptance: a bubble with https://example.com/a is clickable; the rest
    of the sentence stays a text node; no {@html of the body. Confirm
    before OS-open. Rust command accepts only http/https. Keep displayBody,
    whitespace-pre-wrap, break-words, Gmail quote fold, #126 <mark>.
    Not: HTML mail, markdown, tracking redirects.
    Do not rewrite #111 / #117 / #126 / #135 / #207 / #120 / #224 / #271.
    Follow-up: long http(s) URL wraps on <a data-bubble-link> (break-all /
    overflow-wrap anywhere) and in the ConfirmDialog description; Content /
    dialog-content is min-w-0 and/or overflow-x-hidden; App URL confirm
    uses confirmLabel Open link. Keep break-words on the body.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#272: App.svelte required (timeline data-bubble-body linkify)")
    app = app_path.read_text()
    markup = _svelte_markup(app)
    pt = markup.find("person-timeline")
    timeline_markup = markup[pt:] if pt >= 0 else markup
    blocks = _bubble_body_blocks(timeline_markup) or _bubble_body_blocks(app)
    body = "\n".join(blocks)
    extra = _bubble_linkify_extra(crate, app + "\n" + body)
    surface = body if not extra else body + "\n" + extra
    cleaned_surface = _without_comments(surface)
    split_src = _linkify_split_src(app, extra, body)
    cleaned_split = _without_comments(split_src)
    web = _web_logic(crate)
    rust = _tauri_rust_blob(crate)
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    pkg = (crate / "package.json").read_text() if (crate / "package.json").is_file() else ""
    caps_path = crate / "capabilities" / "default.json"
    caps = caps_path.read_text() if caps_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""

    # 1) Primary red: WA / mail body is still one unsplit {displayBody(...)}.
    unsplit = bool(_LINKIFY_UNSPLIT_BODY.search(body))
    if (
        unsplit
        or not _has_url_split_render(surface)
        or not _has_text_node_segments(surface)
    ):
        fail(
            "#272: timeline data-bubble-body must split http(s) URLs into "
            "sibling <a> (or a named link button); surrounding words stay "
            "text nodes ({seg.text}) — do not leave the WA / mail body as "
            "one unsplit {displayBody(...)}"
        )

    # 2) https://example.com/a (or https?:// detect) is in the split path.
    if not _LINKIFY_HTTP_DETECT.search(cleaned_split) and not _LINKIFY_HTTP_DETECT.search(
        split_src
    ):
        fail(
            "#272: https://example.com/a (or equivalent https?:// detect) "
            "must be in the URL-split path — not only the drop-URL rejector"
        )

    # 3) No {@html / innerHTML / insertAdjacentHTML of the bubble body.
    if (
        _LINKIFY_UNSAFE_HTML.search(cleaned_surface)
        or _LINKIFY_UNSAFE_HTML.search(body)
        or _HTML_BODY.search(body)
        or _HTML_BODY.search(surface)
    ):
        fail(
            "#272: no {@html / innerHTML / insertAdjacentHTML of body_text / "
            "displayBody / the bubble body (a body containing <script> or "
            "<a href=…> as text stays text)"
        )
    if _LINKIFY_HTML_STRING.search(cleaned_split) or _LINKIFY_HTML_STRING.search(
        split_src
    ):
        fail(
            "#272: surrounding words stay Svelte text nodes ({seg.text}) — "
            "do not build one HTML string of the body"
        )

    # 4) Only http / https become clickable.
    if _LINKIFY_BROAD_SCHEME.search(cleaned_split) and not _LINKIFY_HTTP_DETECT.search(
        cleaned_split
    ):
        fail(
            "#272: only http / https become clickable — a generic scheme "
            "matcher would treat javascript: / data: / file: / tauri: as links"
        )
    if re.search(r"\bisDroppedUrl\b", split_src):
        fail(
            "#272: only http / https become clickable — do not reuse "
            "isDroppedUrl (it matches every scheme) as the split"
        )
    if _LINKIFY_BAD_SCHEME_ALLOW.search(cleaned_split):
        fail(
            "#272: javascript: / data: / file: / tauri: must not become "
            "clickable — only http / https"
        )

    # 5) ConfirmDialog (or the existing confirm chrome) before OS-open.
    confirm_path = crate / "web" / "lib" / "ConfirmDialog.svelte"
    if not confirm_path.is_file() or "ConfirmDialog" not in app:
        fail(
            "#272: reuse ConfirmDialog (title + the URL in the description) "
            "before OS-open"
        )
    handler = _linkify_open_handler(app, extra)
    if not re.search(r"\bask\s*\(|confirmOpen\s*=\s*true|ConfirmDialog", handler):
        fail(
            "#272: ConfirmDialog (or the existing ask / confirm chrome) "
            "must run before OS-open — Cancel does nothing; Confirm hands "
            "the URL to the OS"
        )
    if not re.search(r"\b(?:url|href|link)\b", handler, re.I):
        fail(
            "#272: ConfirmDialog description must include the URL "
            "(title + the URL; Cancel does nothing)"
        )
    if _LINKIFY_NAVIGATE.search(_without_comments(surface + "\n" + handler)):
        fail(
            "#272: do not navigate the webview — confirm, then OS-open "
            "the http(s) string as written"
        )

    # 6) OS-open is a Rust command that only accepts http/https.
    cmd = _find_open_url_cmd(rust, web)
    if not cmd:
        fail(
            "#272: OS-open must be a Rust command (e.g. open_url) that only "
            "accepts http/https — no tauri-plugin-shell / opener"
        )
    sig = _rust_fn_signature(rust, cmd)
    cmd_body = _rust_body_with_callees(rust, cmd)
    if not re.search(r"\burl\b", sig, re.I):
        fail(
            f"#272: {cmd} must take the URL string "
            "(not a CAS hash — reveal_cas stays file-only)"
        )
    if not _rust_http_only(cmd_body):
        fail(
            f"#272: {cmd} must only accept http/https "
            "(reject javascript: / data: / file: / tauri:)"
        )
    if "/usr/bin/open" not in cmd_body:
        fail(
            f"#272: {cmd} must OS-open via /usr/bin/open on the validated "
            "http(s) URL (same spirit as reveal_cas; do not add a plugin)"
        )
    if not re.search(r"std::process|Command::new", cmd_body):
        fail(
            f"#272: {cmd} must use std::process::Command "
            "(/usr/bin/open) — not tauri-plugin-shell / opener"
        )
    if not re.search(
        r"generate_handler!\s*\[[^\]]*\b" + re.escape(cmd) + r"\b", rust, re.S
    ):
        fail(f"#272: register {cmd} in generate_handler")
    if _PLUGIN_SHELL.search(toml) or _PLUGIN_SHELL.search(pkg):
        fail(
            "#272: do not add tauri-plugin-shell / opener "
            "(Rust command, not a plugin)"
        )
    if _PLUGIN_SHELL.search(rust) or _PLUGIN_SHELL.search(web):
        fail(
            "#272: do not add tauri-plugin-shell / opener "
            "(Rust command, not a plugin)"
        )
    if _SHELL_CAP.search(caps):
        fail(
            "#272: capabilities must not add shell:allow-execute / "
            "shell:allow-open / opener — OS-open is a Rust command"
        )
    if (
        _LINKIFY_FETCH.search(cleaned_surface)
        or _LINKIFY_FETCH.search(handler)
        or _LINKIFY_FETCH.search(_without_comments(web))
    ):
        fail(
            '#272: do not fetch("http the bubble URL — open the string '
            "as written (no tracking redirects)"
        )
    if re.search(r"\b(?:reqwest|ureq|hyper::Client)\b", cmd_body):
        fail(
            "#272: do not fetch / follow redirects — "
            "/usr/bin/open the http(s) string as written"
        )

    # 7) Keep displayBody, wrap, Gmail fold, #126 search <mark>.
    if "displayBody" not in app:
        fail("#272: keep displayBody in the pipeline (do not soften #111 / #117 / #207)")
    if "displayBody" not in body and "displayBody" not in extra:
        fail(
            "#272: keep displayBody on the timeline bubble body "
            "(split after displayBody so #111 / #117 / #207 stay green)"
        )
    if "whitespace-pre-wrap" not in body:
        fail("#272: keep whitespace-pre-wrap on the bubble body")
    if "break-words" not in body:
        fail("#272: keep break-words so long URLs still wrap")
    if not re.search(r"\bsplitQuotedBody\b", app) and not re.search(
        r"\bsplitQuotedBody\b", extra
    ):
        fail("#272: keep Gmail splitQuotedBody / quote fold (#117)")
    if not _SHOW_QUOTED.search(body) and not _SHOW_QUOTED.search(app):
        fail("#272: keep Gmail Show quoted (#117)")
    if not search.strip() or not re.search(r"<mark\b", search, re.I):
        fail(
            "#272: keep #126 search <mark> "
            "(do not require search hits to linkify)"
        )
    if "splitSnippet" not in search:
        fail(
            "#272: keep #126 splitSnippet "
            "(do not require search hits to linkify)"
        )

    # 8) Docs: clickable http(s) in bubbles; rest stays text; confirm; not HTML mail.
    if not dtxt.strip():
        fail(
            "#272: docs/user/app.md required — http(s) URLs in a timeline "
            "bubble are clickable; the rest of the sentence stays a text "
            "node; confirm before the OS browser opens; still not HTML "
            "mail / markdown"
        )
    url_doc = ""
    for m in re.finditer(
        r".{0,180}(?:"
        r"\bURLs?\b"
        r"|http\(s\)"
        r"|https?"
        r"|linkify"
        r"|timeline bubble"
        r"|text node"
        r"|HTML mail"
        r"|markdown"
        r").{0,180}",
        dtxt,
        re.I | re.S,
    ):
        url_doc += m.group(0) + "\n"
    if not re.search(r"clickable", url_doc, re.I):
        fail(
            "#272: docs/user/app.md must say http(s) URLs in a timeline "
            "bubble are clickable"
        )
    if not re.search(r"text node", url_doc, re.I):
        fail(
            "#272: docs/user/app.md must say the rest of the sentence "
            "stays a text node"
        )
    if not re.search(r"confirm", url_doc, re.I):
        fail(
            "#272: docs/user/app.md must say confirm before the OS browser opens"
        )
    if not re.search(r"(?:OS\s+)?browser", url_doc, re.I):
        fail(
            "#272: docs/user/app.md must say confirm before the OS browser opens"
        )
    if not re.search(r"HTML mail", url_doc, re.I):
        fail("#272: docs/user/app.md must say this is still not HTML mail")
    if not re.search(r"markdown", url_doc, re.I):
        fail("#272: docs/user/app.md must say this is still not markdown")

    # 9) Follow-up: long URL wraps on the link + confirm; Open link label.
    #    Keep-checks 1–8 already cover only-http/https, no {@html, no
    #    plugin-shell, displayBody / break-words / #126 search <mark>.
    link_el = _linkify_anchor_surface(surface)
    if not _LINKIFY_WRAP_ANY.search(link_el):
        fail(
            "#272: timeline bubble <a data-bubble-link> (or the link surface) "
            "must wrap a long http(s) URL with break-all or overflow-wrap "
            "anywhere — keep break-words on the bubble body"
        )
    confirm_src = confirm_path.read_text()
    desc_path = (
        crate / "web" / "lib" / "components" / "ui" / "dialog" / "dialog-description.svelte"
    )
    desc_src = desc_path.read_text() if desc_path.is_file() else ""
    desc_blob = _linkify_confirm_desc_blob(confirm_src, desc_src)
    if not _LINKIFY_WRAP_ANY.search(desc_blob):
        fail(
            "#272: ConfirmDialog description must wrap a long http(s) URL "
            "(break-all or overflow-wrap anywhere) so Cancel + confirm stay "
            "on-screen"
        )
    content_path = (
        crate / "web" / "lib" / "components" / "ui" / "dialog" / "dialog-content.svelte"
    )
    content_src = content_path.read_text() if content_path.is_file() else ""
    content_blob = _linkify_dialog_content_blob(confirm_src, content_src)
    if not _linkify_width_capped(content_blob):
        fail(
            "#272: ConfirmDialog Content and/or shared dialog-content must "
            "be width-capped (min-w-0 and/or overflow-x-hidden) so a long "
            "URL cannot grow the dialog with min-content and push Cancel / "
            "confirm off-screen"
        )
    app_clean = _without_comments(app)
    handler_clean = _without_comments(handler)
    has_open_link = bool(_LINKIFY_OPEN_LINK_LABEL.search(app_clean))
    has_confirm_prop = bool(_LINKIFY_CONFIRM_LABEL_PROP.search(app_clean))
    tied = bool(
        _LINKIFY_OPEN_LINK_LABEL.search(handler_clean)
        or _LINKIFY_CONFIRM_LABEL_PROP.search(handler_clean)
        or (
            has_open_link
            and has_confirm_prop
            and re.search(
                r"<ConfirmDialog\b[\s\S]{0,400}\bconfirmLabel\b", app_clean
            )
        )
    )
    if not (has_open_link and has_confirm_prop and tied):
        fail(
            "#272: App URL confirm must use the existing confirmLabel "
            "Open link (Cancel still dismisses; do not leave the default "
            "Confirm)"
        )
    if not re.search(r">\s*Cancel\s*<", confirm_src):
        fail("#272: ConfirmDialog Cancel must still dismiss")


# #273 — jump from a timeline bubble to Search (person name; hits load).
_BUBBLE_SEARCH_HOOK = re.compile(
    r"data-(?:bubble-search|search-from-bubble|bubble-to-search|"
    r"search-this|search-person|timeline-search)"
)
_BUBBLE_SEARCH_HOOK_NAMES = (
    "data-bubble-search",
    "data-search-from-bubble",
    "data-bubble-to-search",
    "data-search-this",
    "data-search-person",
    "data-timeline-search",
)
_BUBBLE_SEARCH_MENU_LABEL = re.compile(
    r"("
    r">\s*Search(?:\s+this(?:\s+person)?|\s+person)?\s*<"
    r"|t\(\s*[\"']search(?:FromBubble|This|Person|OpenPerson|Bubble)?[\"']\s*\)"
    r"|aria-label\s*=\s*[\"']Search(?: this(?: person)?| person)?[\"']"
    r")"
)
_BUBBLE_SEARCH_FN = re.compile(
    r"\b(?:"
    r"searchFromBubble|searchBubble|openBubbleSearch|searchThisPerson|"
    r"searchPersonFromBubble|onBubbleSearch|handleBubbleSearch|"
    r"jumpToSearch|openSearchFromBubble|searchOpenPerson|"
    r"searchFromTimeline|openSearchForPerson"
    r")\b"
)
_BUBBLE_SEARCH_SKIP_EXTRA = frozenset(
    {
        "App.svelte",
        "SearchPane.svelte",
        "CasAttach.svelte",
        "CommandPalette.svelte",
        "ConfirmDialog.svelte",
        "ReviewPane.svelte",
        "ImportPane.svelte",
        "DoctorPane.svelte",
        "EmptyState.svelte",
        "api.ts",
    }
)
_BUBBLE_SEARCH_HANDLER_SKIP = frozenset(
    {
        "t",
        "e",
        "event",
        "true",
        "false",
        "void",
        "closeCopyMenu",
        "copyText",
        "copyMenu",
        "undefined",
        "null",
        "console",
        "preventDefault",
        "stopPropagation",
    }
)
_BUBBLE_SEARCH_NAME_PREFILL = re.compile(
    r"("
    r"\bpickPerson\s*\("
    r"|personFilter\s*=\s*personLabel\s*\("
    r"|personFilter\s*=\s*[^;\n]{0,120}display_name"
    r"|personFilter\s*=\s*personTitle\b"
    r"|personFilter\s*=\s*personLabel\b"
    r"|personLabel\s*\("
    r")"
)
_BUBBLE_SEARCH_RAW_ID_LABEL = re.compile(
    r"("
    r"personFilter\s*=\s*(?:String\s*\(\s*)?(?:selectedId|personId|selected_id|"
    r"p\.id|person\.id|id)\b"
    r"|personFilter\s*=\s*`[^`]*\$\{(?:selectedId|personId|p\.id|person\.id)"
    r")"
)
_BUBBLE_SEARCH_Q_NAME = re.compile(
    r"("
    r"(?:searchQ|(?<![\w.])q)\s*=\s*personLabel\s*\("
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*[^;\n]{0,120}display_name"
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*personTitle\b"
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*personFilter\b"
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*personLabel\b"
    r")"
)
_BUBBLE_SEARCH_Q_BODY = re.compile(
    r"("
    r"(?:searchQ|(?<![\w.])q)\s*=\s*displayBody\s*\("
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*(?:copyMenu(?:\?)?\.)?text\b"
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*(?:row|item\.row|copyMenu)\s*"
    r"(?:\?)?\.\s*(?:body_text|subject|text)\b"
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*(?:row|item)\.body_text"
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*body_text\b"
    r")"
)
_BUBBLE_SEARCH_SELECTION = re.compile(
    r"("
    r"\bgetSelection\s*\("
    r"|\bwindow\.getSelection\s*\("
    r"|\bselectedText\b"
    r"|\bselectedSpan\b"
    r")"
)
_BUBBLE_SEARCH_RUN = re.compile(
    r"("
    r"\brun\s*\("
    r"|requestSubmit\s*\("
    r"|api\.search\s*\("
    r")"
)
_BUBBLE_SEARCH_SEED_PROP = re.compile(
    r"("
    r"\b(?:seedPerson|selectedPerson|openPerson|searchSeed|fromBubble|"
    r"bubblePerson|initialPerson|prefillPerson)\b"
    r"|personFilter\s*=\s*\$bindable"
    r"|personId\s*=\s*\$bindable"
    r"|bind:personFilter"
    r"|bind:personId"
    r")"
)
_BUBBLE_SEARCH_DOC = re.compile(
    r"("
    r"timeline bubble"
    r"|from a (?:timeline )?bubble"
    r"|bubble.{0,80}Search"
    r"|Search.{0,80}(?:from a )?(?:timeline )?bubble"
    r"|right-click.{0,80}Search"
    r"|context menu.{0,80}Search"
    r")",
    re.I | re.S,
)


def _copy_context_menu_blocks(markup: str) -> list[str]:
    blocks: list[str] = []
    for hook in ("data-copy-menu", "data-context-menu"):
        blocks.extend(_hook_element_blocks(markup, hook))
    return blocks


def _menu_looks_like_bubble_search(block: str) -> bool:
    if _BUBBLE_SEARCH_HOOK.search(block):
        return True
    if _BUBBLE_SEARCH_FN.search(block):
        return True
    return bool(_BUBBLE_SEARCH_MENU_LABEL.search(block))


def _bubble_search_control_src(markup: str) -> str:
    """Copy/context-menu Search item and/or named quiet hook on the timeline."""
    parts: list[str] = []
    for block in _copy_context_menu_blocks(markup):
        if _menu_looks_like_bubble_search(block):
            parts.append(block)
    for hook in _BUBBLE_SEARCH_HOOK_NAMES:
        parts.extend(_hook_element_blocks(markup, hook))
    # Dedup overlapping slices (menu that is also the named hook).
    seen: set[str] = set()
    uniq: list[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return "\n".join(uniq)


def _bubble_search_extra(crate: Path, host: str) -> str:
    """Helpers App actually mounts for bubble → Search. Unwired drafts do not count."""
    web = crate / "web"
    if not web.is_dir():
        return ""
    extra: list[str] = []
    for p in sorted(web.rglob("*")):
        if "node_modules" in p.parts:
            continue
        if p.suffix not in {".svelte", ".ts"}:
            continue
        if p.name in _BUBBLE_SEARCH_SKIP_EXTRA:
            continue
        name_hit = bool(
            re.search(r"bubbleSearch|searchFromBubble|searchBubble", p.name, re.I)
        )
        text = p.read_text()
        hook = bool(_BUBBLE_SEARCH_HOOK.search(text) or _BUBBLE_SEARCH_FN.search(text))
        if not name_hit and not hook:
            continue
        stem = p.stem
        if stem in host or re.search(
            rf"\b{re.escape(stem)}\b|{re.escape(p.name)}", host
        ):
            extra.append(text)
    return "\n".join(extra)


def _bubble_search_handler_src(app: str, extra: str, control: str) -> str:
    blob = app + "\n" + extra
    names: set[str] = set(_BUBBLE_SEARCH_FN.findall(blob))
    names.update(_BUBBLE_SEARCH_FN.findall(control))
    for m in re.finditer(
        r"(?:onclick|on:click)\s*=\s*\{([^}]{0,400})\}",
        control,
    ):
        names.update(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", m.group(1)))
    chunks = [control]
    for name in sorted(names):
        if name in _BUBBLE_SEARCH_HANDLER_SKIP:
            continue
        fn = (
            _ts_function_body(blob, name)
            or _ts_fn_body(blob, name)
            or _function_body(blob, name)
        )
        if fn:
            chunks.append(fn)
            chunks.append(_expand_fn_calls(blob, fn))
    return "\n".join(chunks)


def _search_props_blob(search: str) -> str:
    m = re.search(r"=\s*\$props\s*\(\s*\)", search)
    if not m:
        return ""
    start = search.rfind("let", 0, m.start())
    if start < 0:
        start = max(0, m.start() - 900)
    return search[start : m.end()]


def _search_seed_effects(search: str) -> str:
    parts: list[str] = []
    for m in re.finditer(r"\$effect(?:\.pre)?\s*\(", search):
        arg = _call_arg(search, m.end() - 1)
        if re.search(
            r"pickPerson|personFilter|seedPerson|selectedPerson|openPerson|"
            r"fromBubble|bubbleSearch|searchFromBubble",
            arg,
        ):
            parts.append(arg)
    return "\n".join(parts)


def _bubble_search_seed_src(app: str, search: str, handler: str) -> str:
    mount = _windows_around(app, re.compile(r"<SearchPane\b"), before=0, after=700)
    effects = _search_seed_effects(search)
    props = _search_props_blob(search)
    surface = "\n".join([handler, mount, props, effects])
    parts = [surface]
    # Only expand helpers the jump / seed path actually calls (do not
    # treat today's unused pickPerson body as a prefill).
    for name in (
        "pickPerson",
        "seedPerson",
        "prefillPerson",
        "applySeed",
        "searchFromBubble",
        "openFromBubble",
    ):
        if not re.search(rf"\b{re.escape(name)}\b", surface):
            continue
        fn = _ts_fn_body(search, name) or _function_body(search, name)
        if fn:
            parts.append(fn)
    return "\n".join(parts)


def _bubble_search_q_body_is_default(seed: str) -> bool:
    """True when #q default is body_text / displayBody, not a selected span."""
    if not _BUBBLE_SEARCH_Q_BODY.search(seed):
        return False
    for m in _BUBBLE_SEARCH_Q_BODY.finditer(seed):
        win = seed[max(0, m.start() - 160) : m.end() + 80]
        if _BUBBLE_SEARCH_SELECTION.search(win):
            continue
        # `body || name` still dumps the full body as the default.
        return True
    return False


def assert_bubble_search(crate: Path) -> None:
    """#273: from a timeline bubble, open Search with that person.

    Context menuitem on data-copy-menu / data-context-menu, or a named
    quiet control (data-bubble-search), opens Search and focuses #q.
    Person picker is the open person's display name (pickPerson /
    personLabel) — never a raw numeric id. Hits load: short name query
    in #q or existing run() / api.search (not empty-q idle only).
    Do not assign body_text / displayBody to #q by default.
    Keep Copy text, #q, splitSnippet / <mark>, person picker, #124
    hit→timeline, ⌘F → #q. Docs: bubble → Search; name; hits; ⌘F.
    Do not rewrite #123 / #124 / #126 / #135 / #208 / #270 / #272.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#273: App.svelte required (timeline bubble → Search)")
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#273: SearchPane.svelte required (reuse #q / pickPerson / run)")
    app = app_path.read_text()
    search = search_path.read_text()
    markup = _svelte_markup(app)
    extra = _bubble_search_extra(crate, app)
    extra_markup = _svelte_markup(extra) if extra else ""
    surface = markup if not extra_markup else markup + "\n" + extra_markup
    control = _bubble_search_control_src(surface)
    app_clean = _without_comments(app)
    search_clean = _without_comments(search)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) Primary red: no timeline → Search control.
    if not control.strip():
        fail(
            "#273: timeline bubble must have a Search control "
            "(context menuitem on data-copy-menu / data-context-menu, "
            "or a named quiet control data-bubble-search) that opens Search"
        )

    handler = _bubble_search_handler_src(app + "\n" + extra, extra, control)
    seed = _bubble_search_seed_src(app, search, handler)

    # 2) That path sets Search view and focuses #q.
    opens = bool(
        re.search(r"\bwhenSearchPaneReady\b", handler)
        or _VIEW_SEARCH_ASSIGN.search(handler)
    )
    focuses = bool(
        re.search(r"\bwhenSearchPaneReady\b", handler)
        or _FOCUS_SEARCH_Q.search(handler)
    )
    if not opens or not focuses:
        fail(
            "#273: bubble Search path must set Search view and focus #q "
            "(whenSearchPaneReady or getElementById(\"q\") — same path as ⌘F)"
        )

    # 3) Person picker prefilled with the open person's display name.
    mount = _windows_around(app, re.compile(r"<SearchPane\b"), before=0, after=700)
    props = _search_props_blob(search)
    wired = bool(
        _BUBBLE_SEARCH_SEED_PROP.search(props)
        or _BUBBLE_SEARCH_SEED_PROP.search(mount)
        or _BUBBLE_SEARCH_SEED_PROP.search(seed)
        or re.search(
            r"\b(?:seedPerson|selectedPerson|openPerson|searchSeed|fromBubble|"
            r"selectedId)\b",
            mount,
        )
    )
    has_name = bool(_BUBBLE_SEARCH_NAME_PREFILL.search(seed))
    has_raw = bool(_BUBBLE_SEARCH_RAW_ID_LABEL.search(seed))
    if not wired or not has_name:
        fail(
            "#273: person picker must be prefilled with the open person's "
            "display name (pickPerson / personLabel / display_name) — "
            "never a raw numeric person id"
        )
    if has_raw:
        fail(
            "#273: person picker visible label must be the display name "
            "(Ada / Ada (self) via pickPerson / personLabel) — "
            "not a raw numeric person id"
        )

    # 4) Hits load: short name query in #q, or existing run() / api.search.
    has_name_q = bool(_BUBBLE_SEARCH_Q_NAME.search(seed))
    has_run = bool(_BUBBLE_SEARCH_RUN.search(seed))
    if not has_name_q and not has_run:
        fail(
            "#273: hits must load — #q gets a short name query "
            "(display name) or existing run() / api.search is invoked "
            "on this jump (not empty-q idle / clearHitsIdle only)"
        )

    # 5) #q is not assigned body_text / displayBody as the default query.
    if _bubble_search_q_body_is_default(seed):
        fail(
            "#273: #q must not be assigned body_text / displayBody(...) "
            "as the default query — prefer the person name "
            "(a selected span is optional, not the default)"
        )

    # 6) ⌘F / chrome search / whenSearchPaneReady still focuses #q.
    key_body = _app_keydown_body(app_clean) or _app_keydown_body(app)
    key_x = _expand_fn_calls(app_clean, key_body) if key_body else ""
    f_surface = _windows_around(key_x, _KEY_F) if key_x else ""
    if not (
        re.search(r"\bwhenSearchPaneReady\b", f_surface)
        or _FOCUS_SEARCH_Q.search(f_surface)
    ):
        fail(
            "#273: ⌘F must still switch to Search and focus #q "
            "(whenSearchPaneReady / getElementById(\"q\") — "
            "do not require the new bubble menu)"
        )
    if not re.search(r"\bwhenSearchPaneReady\b", app_clean) and not re.search(
        r"\bwhenSearchPaneReady\b", app
    ):
        fail(
            "#273: keep whenSearchPaneReady so chrome search / ⌘F "
            "still focus #q"
        )
    if not _CHROME_SEARCH_HOOK.search(markup) and not _CHROME_SEARCH_HOOK.search(app):
        fail("#273: keep data-chrome-search (#208) — chrome search still focuses #q")

    # 7) Keep Copy text, #q, splitSnippet / <mark>, person picker, #124 jump.
    if not _COPY_TEXT_LABEL.search(app) and not re.search(r"\bcopyText\b", app):
        fail("#273: keep Copy text on the bubble context menu (#135)")
    if not re.search(r"id=[\"']q[\"']", search):
        fail('#273: keep id="q" as the canonical query field (#208 / #270)')
    if not re.search(r"<mark\b", search, re.I):
        fail("#273: keep #126 search <mark> siblings")
    if "splitSnippet" not in search:
        fail("#273: keep #126 splitSnippet")
    if not re.search(r"\bpickPerson\b", search_clean) and not re.search(
        r"\bpersonLabel\b", search_clean
    ):
        fail("#273: keep the #123 person picker (pickPerson / personLabel)")
    if "data-person-picker" not in search and "data-person-picker" not in search_clean:
        fail("#273: keep the #123 person picker (data-person-picker)")
    if not re.search(
        r"\b(?:onJumpToMessage|jumpToMessage|activateHit)\b",
        app_clean + "\n" + search_clean,
    ):
        fail(
            "#273: keep #124 hit→timeline jump "
            "(activateHit / onJumpToMessage / jumpToMessage)"
        )

    # 8) Docs: bubble → Search; person name (not id); hits; ⌘F still #q.
    if not dtxt.strip():
        fail(
            "#273: docs/user/app.md required — from a timeline bubble you "
            "can open Search with that person (name, not id); hits load; "
            "⌘F still focuses #q"
        )
    doc_win = ""
    for m in _BUBBLE_SEARCH_DOC.finditer(dtxt):
        i = m.start()
        doc_win += dtxt[max(0, i - 80) : m.end() + 200] + "\n"
    if not doc_win.strip() or not re.search(
        r"("
        r"(?:timeline )?bubble.{0,120}Search"
        r"|Search.{0,120}(?:from a )?(?:timeline )?bubble"
        r"|right-click.{0,80}Search"
        r"|context menu.{0,80}Search"
        r")",
        doc_win,
        re.I | re.S,
    ):
        fail(
            "#273: docs/user/app.md must say from a timeline bubble you "
            "can open Search with that person"
        )
    if not re.search(
        r"("
        r"name,?\s+not\s+(?:an? )?(?:raw )?(?:numeric )?id"
        r"|display name"
        r"|person(?:'s)? name"
        r"|\bAda\b"
        r")",
        doc_win,
        re.I,
    ):
        fail(
            "#273: docs/user/app.md must say the bubble → Search person "
            "is a name, not a raw id"
        )
    if not re.search(r"\bhits?\b", doc_win, re.I):
        fail("#273: docs/user/app.md must say hits load on the bubble → Search jump")
    if not re.search(
        r"(?:⌘\s*F|Ctrl\+F|Ctrl-F).{0,80}#q|#q.{0,80}(?:⌘\s*F|Ctrl\+F|Ctrl-F)",
        doc_win,
        re.I | re.S,
    ):
        fail(
            "#273: docs/user/app.md must say ⌘F still focuses #q "
            "(bubble → Search does not replace Find)"
        )


# #135 — copy message text / reveal CAS file in Finder (hash only; file open).
_CONTEXTMENU = re.compile(
    r"("
    r"on:contextmenu"
    r"|oncontextmenu"
    r"|addEventListener\s*\(\s*[\"']contextmenu[\"']"
    r"|ContextMenu(?:\.\w+)?"
    r"|data-context-menu"
    r"|contextMenu"
    r")",
    re.I,
)
_COPY_TEXT_LABEL = re.compile(r"Copy text")
_REVEAL_LABEL = re.compile(r"Reveal in Finder")
_REVEAL_CMD_NAMES = (
    "reveal_cas",
    "revealCas",
    "reveal_in_finder",
    "revealInFinder",
)
_REVEAL_CMD = re.compile(
    r"\b(?:" + "|".join(re.escape(n) for n in _REVEAL_CMD_NAMES) + r")\b"
)
_REVEAL_INVOKE = re.compile(
    r"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"'](?:"
    + "|".join(re.escape(n) for n in _REVEAL_CMD_NAMES)
    + r")[\"']"
)
_SHARE_AIRDROP = re.compile(
    r"("
    r"AirDrop"
    r"|Share sheet"
    r"|share sheet"
    r"|NSSharingService"
    r"|showShareSheet"
    r"|ShareLink\b"
    r"|share-sheet"
    r")",
    re.I,
)
_SHARE_ITEM = re.compile(
    r"("
    r">\s*Share\s*<"
    r"|[\"']Share[\"']"
    r"|label\s*:\s*[\"']Share[\"']"
    r")"
)
_COPY_FN_NAMES = (
    "copyText",
    "copyMessage",
    "copyBubble",
    "copyBubbleText",
    "onCopyText",
    "handleCopy",
    "handleCopyText",
)
_BUBBLE_MENU_SKIP = frozenset(
    {
        "App.svelte",
        "CasAttach.svelte",
        "SearchPane.svelte",
        "ReviewPane.svelte",
        "ImportPane.svelte",
        "DoctorPane.svelte",
        "ConfirmDialog.svelte",
        "EmptyState.svelte",
    }
)


def _bubble_and_attach_surface(crate: Path) -> str:
    """Person-timeline bubbles + CasAttach + components they reference."""
    parts = [_timeline_block(crate)]
    app_path = crate / "web" / "App.svelte"
    if app_path.is_file():
        parts.append(app_path.read_text())
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if cas_path.is_file():
        parts.append(cas_path.read_text())
    used = "\n".join(parts)
    web = crate / "web"
    if web.is_dir():
        for p in sorted(web.rglob("*.svelte")):
            if "node_modules" in p.parts or p.name in _BUBBLE_MENU_SKIP:
                continue
            if re.search(rf"\b{re.escape(p.stem)}\b", used):
                parts.append(p.read_text())
    return "\n".join(parts)


def _copy_handler_surface(web: str) -> str:
    chunks = [_windows_around(web, _WRITE_TEXT, before=500, after=160)]
    for name in _COPY_FN_NAMES:
        body = _ts_function_body(web, name) or _function_body(web, name)
        if body:
            chunks.append(body)
        chunks.append(
            _windows_around(web, re.compile(rf"\b{re.escape(name)}\s*\("), before=220, after=80)
        )
    return "\n".join(chunks)


def _copy_logs_body(surf: str) -> bool:
    """True if the copy path logs the message body (console / eprintln)."""
    for m in re.finditer(r"console\.(?:log|debug|info|dir|trace)\s*\(", surf):
        arg = _call_arg(surf, m.end() - 1)
        if re.search(
            r"body_text|displayBody|copiedText|\bbody\b|\btext\b|\bmsg\b|\bmessage\b",
            arg,
            re.I,
        ):
            return True
    for m in re.finditer(r"(?:eprintln|println|dbg)\s*!", surf):
        window = surf[m.start() : m.end() + 200]
        if re.search(r"body_text|displayBody|\bbody\b", window, re.I):
            return True
    return False


def _reveal_cmd_name(rust: str, web: str) -> str:
    blob = rust + "\n" + web
    m = _REVEAL_CMD.search(blob)
    return m.group(0) if m else ""


def assert_copy_reveal_cas(crate: Path) -> None:
    """#135: bubble context menu Copy text; cas_hash attachment Reveal in Finder.

    Reveal command takes the hash only, resolves cas/ab/cd/<hash> via
    cas_blob_path, opens the local file (std::process /usr/bin/open -R or
    file://). Copy does not log the body. No plugin-shell / Share / AirDrop.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#135: App.svelte required (person-timeline bubble context menu)")
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail("#135: CasAttach.svelte required (Reveal in Finder on cas_hash)")
    web = _web_logic(crate)
    surface = _bubble_and_attach_surface(crate)
    rust = _tauri_rust_blob(crate)
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    pkg = (crate / "package.json").read_text() if (crate / "package.json").is_file() else ""
    caps_path = crate / "capabilities" / "default.json"
    caps = caps_path.read_text() if caps_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) Context menu on a person-timeline bubble.
    if not _CONTEXTMENU.search(surface):
        fail(
            "#135: person-timeline bubble must have a context menu "
            "(on:contextmenu / ContextMenu) for Copy text"
        )

    # 2) Custom menu: Copy text → clipboard (message text).
    if not _COPY_TEXT_LABEL.search(surface) and not _COPY_TEXT_LABEL.search(web):
        fail("#135: context menu must include Copy text")
    if not _WRITE_TEXT.search(web):
        fail(
            "#135: Copy text must write the message text to the clipboard "
            "(navigator.clipboard.writeText)"
        )
    copy_surf = _copy_handler_surface(web)
    if not re.search(r"body_text|displayBody|bodyText", copy_surf):
        fail("#135: clipboard write must be the message text (body_text / displayBody)")

    # 3) Copy does not log the body.
    if _copy_logs_body(copy_surf) or _copy_logs_body(_windows_around(web, _WRITE_TEXT)):
        fail(
            "#135: Copy must not log the message body "
            "(no console.log / eprintln of the text)"
        )

    # 4) Attachment with cas_hash → Reveal in Finder.
    if not _REVEAL_LABEL.search(surface) and not _REVEAL_LABEL.search(web):
        fail(
            "#135: attachment with cas_hash must offer Reveal in Finder "
            "(context menu on the attachment)"
        )
    reveal_win = _windows_around(surface, _REVEAL_LABEL, before=520, after=240)
    if not reveal_win.strip():
        reveal_win = _windows_around(web, _REVEAL_LABEL, before=520, after=240)
    if not re.search(r"cas_hash|casHash|hashOf", reveal_win + "\n" + surface):
        fail("#135: Reveal in Finder is only for an attachment that has cas_hash")

    # 5) Frontend sends only the hash to the reveal command.
    cmd = _reveal_cmd_name(rust, web)
    if not cmd:
        fail(
            "#135: frontend must invoke a reveal command that takes the hash only "
            "(e.g. reveal_cas) — not a path or URL"
        )
    payloads = _invoke_payloads(web, _REVEAL_INVOKE)
    if not payloads:
        # api.revealCas(hash) wrapper — still must mention hash, not path/url.
        call_win = _windows_around(web, _REVEAL_CMD, before=80, after=160)
        if not re.search(r"\bhash\b", call_win, re.I):
            fail(
                "#135: frontend must send only the hash to reveal "
                "(invoke reveal_cas with { hash })"
            )
        if _payload_has_path_or_url(call_win):
            fail(
                "#135: frontend must send only the hash to reveal "
                "(do not pass a path or URL from the webview)"
            )
    for payload in payloads:
        if not re.search(r"\bhash\b", payload, re.I):
            fail(
                "#135: frontend must send only the hash to reveal "
                "(invoke reveal_cas with { hash })"
            )
        if _payload_has_path_or_url(payload):
            fail(
                "#135: frontend must send only the hash to reveal "
                "(do not pass a path or URL from the webview)"
            )

    # 6) Rust command: hash only; cas_blob_path; under cas/; file-only open.
    sig = _rust_fn_signature(rust, cmd)
    body = _rust_body_with_callees(rust, cmd)
    if not body.strip():
        fail(
            f"#135: Rust command {cmd} must resolve cas/ab/cd/<hash> "
            "(fn reveal_cas taking the hash only)"
        )
    if not re.search(r"\bhash\b", sig, re.I):
        fail("#135: reveal command must take a hash (not a path or URL)")
    if re.search(r"\b(?:path|url|file|href|uri)\s*:", sig, re.I):
        fail(
            "#135: reveal command must take the hash only — "
            "do not take a path or URL from the webview"
        )
    if "cas_blob_path" not in body:
        fail(
            "#135: reveal must resolve cas/ab/cd/<hash> via cas_blob_path "
            "(64 hex only — reject anything else)"
        )
    if not re.search(r"\bcanonicalize\s*\(", body):
        fail("#135: reveal must canonicalize the CAS path")
    if not re.search(
        r"("
        r"starts_with"
        r"|outside cas"
        r"|join\(\s*[\"']cas[\"']"
        r"|[\"']cas/"
        r")",
        body,
    ):
        fail("#135: reveal must refuse anything outside cas/")
    if not re.search(r"generate_handler!\s*\[[^\]]*\b" + re.escape(cmd) + r"\b", rust, re.S):
        fail(f"#135: register {cmd} in generate_handler")

    if not re.search(r"std::process|\buse\s+std::process", rust):
        fail(
            "#135: open Finder with std::process "
            "(not tauri-plugin-shell / plugin-opener)"
        )
    if not re.search(r"Command::new|std::process::Command", body):
        fail(
            "#135: reveal must open the local file with std::process::Command "
            "(/usr/bin/open -R or a file:// URL)"
        )
    if "/usr/bin/open" not in body:
        fail("#135: open the local CAS file with /usr/bin/open (file only, not http)")
    if not re.search(r"[\"']-R[\"']", body) and "file://" not in body:
        fail("#135: use /usr/bin/open -R or a file:// URL to the CAS path")
    if re.search(r"[\"']https?://", body):
        fail("#135: reveal must not open http(s) — file only")
    if _ARBITRARY_SHELL.search(body) or _ARBITRARY_SHELL.search(rust):
        fail("#135: no shell of arbitrary commands — only /usr/bin/open on the CAS file")
    for m in re.finditer(r"Command::new\s*\(", body):
        arg = _rust_call_arg(body, m.end() - 1)
        if "/usr/bin/open" not in arg:
            fail(
                "#135: no shell of arbitrary commands — "
                "Command::new must be /usr/bin/open on the CAS file"
            )

    # 7) Bans: plugin-shell / opener / shell caps / Share / AirDrop.
    if _PLUGIN_SHELL.search(toml) or _PLUGIN_SHELL.search(pkg):
        fail(
            "#135: do not add tauri-plugin-shell / tauri-plugin-opener "
            "(std::process file-only open)"
        )
    if _PLUGIN_SHELL.search(rust) or _PLUGIN_SHELL.search(web):
        fail(
            "#135: do not add tauri-plugin-shell / tauri-plugin-opener "
            "(std::process file-only open)"
        )
    if _SHELL_CAP.search(caps):
        fail(
            "#135: capabilities must not add shell:allow-execute / "
            "shell:allow-open / opener (no arbitrary Command)"
        )
    if _SHARE_AIRDROP.search(web) or _SHARE_AIRDROP.search(rust) or _SHARE_ITEM.search(surface):
        fail("#135: no Share sheet / AirDrop")

    # 8) Docs: right-click copy text; reveal local CAS in Finder; no Share / AirDrop.
    if not dtxt.strip():
        fail("#135: docs/user/app.md required (right-click copy text; reveal in Finder)")
    doc_win = ""
    for m in re.finditer(
        r".{0,180}(?:right-click|context menu|Copy text|Reveal in Finder|AirDrop|Share sheet).{0,180}",
        dtxt,
        re.I | re.S,
    ):
        doc_win += m.group(0) + "\n"
    if not doc_win.strip():
        fail(
            "#135: docs/user/app.md must say right-click Copy text "
            "and reveal local CAS in Finder"
        )
    if not re.search(r"right-click|context menu", doc_win, re.I):
        fail("#135: docs/user/app.md must say right-click (or context menu) to copy text")
    if not re.search(r"copy text", doc_win, re.I):
        fail("#135: docs/user/app.md must describe Copy text")
    if not re.search(r"reveal", doc_win, re.I):
        fail("#135: docs/user/app.md must say reveal local CAS in Finder")
    if not re.search(r"Finder", doc_win):
        fail("#135: docs/user/app.md must say reveal local CAS in Finder")
    if not re.search(r"CAS|cas/", doc_win, re.I):
        fail("#135: docs/user/app.md must say the reveal target is a local CAS file")
    if not re.search(
        r"("
        r"no Share"
        r"|not Share"
        r"|Share sheet"
        r"|AirDrop"
        r")",
        doc_win,
        re.I,
    ):
        fail("#135: docs/user/app.md must say no Share / AirDrop")
