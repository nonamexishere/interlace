"""Additional media_lightbox asserts."""
from __future__ import annotations

from tauri_gate.media_lightbox_lib import *


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
