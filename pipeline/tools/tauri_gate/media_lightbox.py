"""Photo lightbox / voice-note chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.media_lightbox_lib import *


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

from tauri_gate.media_lightbox_more import assert_voice_note_seek
