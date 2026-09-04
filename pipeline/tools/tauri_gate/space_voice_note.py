"""#316 — Space play/pause the highlighted voice note.

PeopleKeys binds bare Space to the tlIndex row’s mounted
[data-voice-note] audio. Same play/pause + pause-others as click.
Fields keep a typed space. No autoplay. No media keys.

Must-IDs: space-voice-toggle, space-field-native, space-no-autoplay,
space-keep-119-170, space-keep-132, space-keep-210, space-keep-314,
space-not-media-keys, space-d24.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.import_boot_guards import _input_guard_span
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.media_lightbox_lib import (
    _VOICE_AUDIO_EL,
    _VOICE_KIND,
    _VOICE_LOCAL_SRC,
    _VOICE_PLAY_PAUSE,
    _VOICE_REMOTE_SRC,
    _VOICE_SEEK_TRACK,
    _VOICE_SEEK_WRITE,
    _VOICE_TIME_CHROME,
    _VOICE_TRANSCRIPTION,
    _VOICE_WAVEFORM_CDN,
)
from tauri_gate.scan import (
    _expand_fn_calls,
    _function_body,
    _open_tag_before,
    _svelte_markup,
    _ts_fn_body,
    _without_comments,
)

_ISSUE = "#316"
_KEY_SPACE = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"'] [\"']"
    r"|[\"'] [\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']Space(?:bar)?[\"']"
    r"|[\"']Space(?:bar)?[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?code\s*===?\s*[\"']Space(?:bar)?[\"']"
    r"|[\"']Space(?:bar)?[\"']\s*===?\s*(?:e\.)?code"
)
_MOD_REQ = re.compile(
    r"(?:(?:e\.)?metaKey|(?:e\.)?ctrlKey|\bmod\b)\s*&&"
    r"|(?:e\.)?(?:key|code)\s*===?\s*[\"'] ?(?:Space(?:bar)?)?[\"']\s*&&\s*"
    r"(?:e\.)?(?:metaKey|ctrlKey|\bmod\b)"
)
_NO_META_CTRL = re.compile(r"!\s*(?:e\.)?(?:metaKey|ctrlKey)|\b!mod\b|!\s*mod\b")
_NO_ALT = re.compile(r"!\s*(?:e\.)?altKey")
_NO_ANY_MOD = re.compile(
    r"!\s*\([^)]*(?:metaKey|ctrlKey|altKey)[^)]*(?:metaKey|ctrlKey|altKey)"
)
_END = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']End[\"']|[\"']End[\"']\s*===?\s*(?:e\.)?key"
)
_HOME = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']Home[\"']"
    r"|[\"']Home[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?code\s*===?\s*[\"']Home[\"']"
)
_ARROW_UP = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']ArrowUp[\"']"
    r"|[\"']ArrowUp[\"']\s*===?\s*(?:e\.)?key"
)
_KEY_J = re.compile(r"(?:e\.)?key\s*===?\s*[\"']j[\"']|[\"']j[\"']\s*===?\s*(?:e\.)?key")
_KEY_K = re.compile(r"(?:e\.)?key\s*===?\s*[\"']k[\"']|[\"']k[\"']\s*===?\s*(?:e\.)?key")
_KEY_C = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']c[\"']"
    r"|(?:e\.)?code\s*===?\s*[\"']KeyC[\"']"
)
_MOD = re.compile(r"\b(?:(?:e\.)?metaKey|(?:e\.)?ctrlKey|\bmod\b)")
_WALK = re.compile(r"\b(?:setTlIndex|ensureTlIndexVisible|visibleTlIndices)\b")
_PREPEND = re.compile(r"\b(?:prependOlder|loadOlder|onPrepend)\s*\(")
_PIN = re.compile(r"\b(?:scrollToLatest|pinTimelineLatest)\b")
_COPY_SEL = re.compile(r"\bcopySelected\s*\(|\.copySelected\b")
_ROW_AUDIO = re.compile(
    r"querySelector(?:All)?\s*(?:<[^>]+>)?\s*\(\s*[`'\"']"
    r"[^`'\"']*#person-timeline[^`'\"']*"
    r"data-tl-index\s*=?\s*[\"']"
    r"[^`'\"']*tlIndex[^`'\"']*"
    r"[\"']"
    r"[^`'\"']*data-voice-note[^`'\"']*audio"
)
_PAUSE_OTHERS = re.compile(
    r"querySelectorAll\s*(?:<[^>]+>)?\s*\(\s*[`'\"']"
    r"[^`'\"']*data-voice-note[^`'\"']*audio"
)
_PLAY = re.compile(r"\.play\s*\(")
_PAUSE = re.compile(r"\.pause\s*\(")
_TOGGLE = re.compile(
    r"\b(?:togglePlay|toggleVoice|toggleVoicePlay|toggleVoiceNote|"
    r"playPauseVoice|playPauseNote)\s*\("
)
_BUTTON_TAG = re.compile(r"tagName\s*===?\s*[\"']BUTTON[\"']")
_VIDEO_TAG = re.compile(r"tagName\s*===?\s*[\"']VIDEO[\"']")
_LIGHTBOX_OPEN = re.compile(
    r"data-photo-lightbox|data-cas-video-overlay|data-lightbox"
    r"|lightboxOpen|photoLightbox|photo-lightbox"
)
_ARTICLE_FOCUS = re.compile(r":focus\b|activeElement|article:focus")
_CLICK_PLAY = re.compile(
    r"data-voice-play[\s\S]{0,80}\.click\s*\("
    r"|\.click\s*\([\s\S]{0,80}data-voice-play"
)
_FOCUS_PLAY = re.compile(
    r"data-voice-play[\s\S]{0,80}\.focus\s*\("
    r"|\.focus\s*\([\s\S]{0,80}voice-play"
)
_TOAST = re.compile(r"\b(?:showToast|toast|onError|showErr)\s*\(")
_MEDIA_KEYS = re.compile(
    r"MediaPlayPause|MediaPlay\b|MediaPause\b|MediaStop\b"
    r"|MediaTrackNext|MediaTrackPrevious|\bmediaSession\b"
)
_AUTOPLAY = re.compile(r"<audio\b[^>]*\bautoplay\b|\bautoplay\s*=", re.I)
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][\w]*)["']""")
_NEW_LOCALE = re.compile(r"space|voicePlay|playVoice|pauseVoice|voiceNote", re.I)
_WIRE_NAME = re.compile(
    r"\b(?:toggleVoice|playVoice|playSelectedVoice|toggleSelectedVoice|"
    r"playHighlightedVoice)\b"
)
_DOCS_SPACE = re.compile(
    r"(?:highlighted|selected).{0,200}(?:voice|audio).{0,200}Space"
    r"|Space.{0,200}(?:play|pause).{0,160}(?:voice|audio|highlighted|selected)"
    r"|(?:voice|audio).{0,200}Space.{0,160}(?:play|pause)",
    re.I | re.S,
)
_DOCS_Q = re.compile(
    r"#q.{0,220}(?:types? a space|typed space|still types)"
    r"|(?:types? a space|typed space).{0,220}#q",
    re.I | re.S,
)
_DOCS_AUTOPLAY = re.compile(
    r"autoplay is off|no autoplay|autoplay off|keep autoplay off",
    re.I,
)
_LOAD_CTRL = re.compile(r"data-load-older")
_TAB_NEG = re.compile(r"""\btabindex\s*=\s*(?:["']-1["']|\{-1\})""")
_ACTIVATE = re.compile(r"\bactivateHit\s*\(")
_SCRIPT_MODULE = re.compile(r"<script\s+module[\s\S]*?</script>", re.I)
_IMPORT_FROM = re.compile(r"""from\s*["']([^"']+)["']""")


def _fn(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name) or ""


def _near(src: str, m: re.Match[str], before: int = 200, after: int = 420) -> str:
    return src[max(0, m.start() - before) : m.end() + after]


def _is_bare_space(src: str, m: re.Match[str]) -> bool:
    tight = _near(src, m, 90, 90)
    if _MOD_REQ.search(tight):
        return False
    w = _near(src, m, 280, 280)
    if _NO_ANY_MOD.search(w):
        return True
    return bool(_NO_META_CTRL.search(w) and _NO_ALT.search(w))


def _space_hits(src: str) -> list[re.Match[str]]:
    return [m for m in _KEY_SPACE.finditer(src) if _is_bare_space(src, m)]


def _people_gated(src: str, pos: int) -> bool:
    head = src[:pos]
    if re.search(r"view\s*!==?\s*[\"']people[\"']", head):
        return True
    return bool(
        re.search(r"view\s*===?\s*[\"']people[\"']", src[max(0, pos - 400) : pos + 80])
    )


def _after_guard(src: str, pos: int) -> bool:
    guard = _input_guard_span(src)
    return bool(guard and guard[0] < pos and guard[1] <= pos)


def _steal_has_space(src: str) -> bool:
    guard = _input_guard_span(src)
    if not guard:
        return False
    blob = src[guard[0] : guard[1]]
    for m in re.finditer(r"mod\s*&&\s*\(([^)]*)\)", blob):
        if _KEY_SPACE.search(m.group(1)):
            return True
    return False


def _read_lib(crate: Path, name: str) -> str:
    p = crate / "web" / "lib" / name
    return p.read_text() if p.is_file() else ""


def _helper_files(crate: Path) -> list[tuple[Path, str]]:
    lib = crate / "web" / "lib"
    out: list[tuple[Path, str]] = []
    if not lib.is_dir():
        return out
    for p in sorted(lib.glob("*.ts")):
        if p.name == "PeopleKeys.ts":
            continue
        txt = p.read_text()
        if _PAUSE_OTHERS.search(txt) and _PLAY.search(txt) and _PAUSE.search(txt):
            out.append((p, txt))
    cas_p = lib / "CasAttach.svelte"
    if cas_p.is_file():
        cas = cas_p.read_text()
        for m in _SCRIPT_MODULE.finditer(cas):
            blob = m.group(0)
            if _PAUSE_OTHERS.search(blob) and _PLAY.search(blob) and _PAUSE.search(blob):
                out.append((cas_p, blob))
    return out


def _import_stems(src: str) -> set[str]:
    stems: set[str] = set()
    for m in _IMPORT_FROM.finditer(src):
        spec = m.group(1).rsplit("/", 1)[-1]
        stems.add(re.sub(r"\.(ts|js|svelte)$", "", spec))
    return stems


def _shared_helper_ok(keys: str, cas: str, helpers: list[tuple[Path, str]]) -> bool:
    if not helpers:
        return False
    key_stems = _import_stems(keys)
    cas_stems = _import_stems(cas)
    for path, blob in helpers:
        stem = path.stem
        names = set(re.findall(r"\bexport\s+(?:function|const)\s+(\w+)", blob))
        names.update(re.findall(r"\bfunction\s+(\w+)", blob))
        called = any(re.search(rf"\b{re.escape(n)}\s*\(", keys) for n in names)
        cas_uses = any(re.search(rf"\b{re.escape(n)}\s*\(", cas) for n in names)
        imported = stem in key_stems and stem in cas_stems
        if (imported or (called and cas_uses)) and names:
            return True
        if imported and _TOGGLE.search(keys) and _TOGGLE.search(cas):
            return True
    return False


def _pd_only_if_audio(window: str) -> bool:
    pd = re.search(r"preventDefault\s*\(", window)
    lookup = _ROW_AUDIO.search(window)
    if not pd or not lookup:
        return False
    if pd.start() < lookup.start():
        return False
    head = window[: pd.start()]
    return bool(
        re.search(r"\b(?:audio|el|node|player|note)\b", head)
        and re.search(r"\bif\s*\(", head)
    )


def assert_space_voice_note(crate: Path) -> None:
    """#316: Space toggles the highlighted voice note; fields type a space."""
    keys_path = crate / "web" / "lib" / "PeopleKeys.ts"
    app_path = crate / "web" / "App.svelte"
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    vid_path = crate / "web" / "lib" / "CasVideo.svelte"
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    rows_path = crate / "web" / "lib" / "TimelineRows.svelte"
    list_path = crate / "web" / "lib" / "TimelineList.svelte"
    pane_path = crate / "web" / "lib" / "TimelinePane.svelte"
    if not keys_path.is_file():
        fail(f"{_ISSUE}: PeopleKeys.ts required (bare Space → voice play/pause)")
    if not app_path.is_file():
        fail(f"{_ISSUE}: App.svelte required (bubble-phase onKey → handleAppKey)")
    if not cas_path.is_file():
        fail(f"{_ISSUE}: CasAttach.svelte required (click togglePlay + <audio>)")

    keys_c = _without_comments(keys_path.read_text())
    app_c = _without_comments(app_path.read_text())
    cas_raw = cas_path.read_text()
    cas_c = _without_comments(cas_raw)
    vid_c = _without_comments(vid_path.read_text()) if vid_path.is_file() else ""
    search_c = _without_comments(search_path.read_text()) if search_path.is_file() else ""
    list_c = _without_comments(list_path.read_text()) if list_path.is_file() else ""
    pane_c = _without_comments(pane_path.read_text()) if pane_path.is_file() else ""
    rows_raw = rows_path.read_text() if rows_path.is_file() else ""
    handle = _fn(keys_c, "handleAppKey") or keys_c
    handle_x = _expand_fn_calls(keys_c, handle, 2)
    on_key = _fn(app_c, "onKey") or app_c
    home_fn = _fn(keys_c, "preventNativeHomeScroll")
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) space-voice-toggle — fail-today: no Space in PeopleKeys.
    hits = _space_hits(handle_x)
    if not hits:
        fail(
            f"{_ISSUE}: PeopleKeys must bind bare Space "
            '(e.key === " " or e.code === "Space", no meta/ctrl/alt) to '
            "play/pause the highlighted voice note"
        )
    if not _space_hits(handle) and not _space_hits(keys_c):
        fail(
            f"{_ISSUE}: bare Space must live on the PeopleKeys window "
            "handler (handleAppKey — not App.svelte-only, not capture-phase)"
        )
    if _KEY_SPACE.search(home_fn) or _TOGGLE.search(home_fn) or _PLAY.search(home_fn):
        fail(
            f"{_ISSUE}: preventNativeHomeScroll stays Home / ⌘↑ only "
            "(do not bind capture-phase Space)"
        )
    for m in re.finditer(r"addEventListener\s*\(\s*[\"']keydown[\"']", app_c):
        window = app_c[m.start() : m.end() + 120]
        if not re.search(r",\s*true\b", window):
            continue
        if "preventNativeHomeScroll" in window:
            continue
        if _KEY_SPACE.search(window) or _TOGGLE.search(window):
            fail(f"{_ISSUE}: Space is not capture-phase")

    key_blob = "\n".join(_near(handle_x, m, 80, 420) for m in hits)
    helpers = _helper_files(crate)
    helper_blob = "\n".join(blob for _p, blob in helpers)

    # 2) End-style focus + after field / palette / view !== "people".
    pal_at = handle.find("data-command-palette")
    view_at = re.search(r"view\s*!==?\s*[\"']people[\"']", handle)
    for m in hits:
        if not _people_gated(handle_x, m.start()):
            fail(
                f"{_ISSUE}: Space uses the same End-style focus "
                "(people view, selectedId, not a field, not the people listbox)"
            )
        if not re.search(r"\bselectedId\b", _near(handle_x, m, 360, 200)):
            fail(
                f"{_ISSUE}: Space uses the same End-style focus "
                "(people view, selectedId, not a field, not the people listbox)"
            )
        if not re.search(r"\binPeopleList\b", _near(handle_x, m, 360, 240) + handle):
            fail(
                f"{_ISSUE}: Space uses the same End-style focus "
                "(!inPeopleList — same as End)"
            )
        if not _after_guard(handle, m.start()) and not _after_guard(handle_x, m.start()):
            fail(
                f"{_ISSUE}: Space must run after the INPUT / TEXTAREA / SELECT "
                "return (do not steal a typed space from a field)"
            )
        if pal_at >= 0 and m.start() < pal_at:
            fail(
                f"{_ISSUE}: Space must run after the palette-target return"
            )
        if view_at and m.start() < view_at.start():
            fail(
                f"{_ISSUE}: Space is people-view only "
                '(after the view !== "people" return — Search-tab Space stays #210)'
            )

    # 3) focus-vs-highlight = tlIndex; several = first mounted audio on that row.
    if not _ROW_AUDIO.search(key_blob) and not _ROW_AUDIO.search(handle_x):
        fail(
            f"{_ISSUE}: look up #person-timeline "
            '[data-tl-index="${tlIndex}"] [data-voice-note] audio '
            "(first note on the highlighted row)"
        )
    if not re.search(r"\btlIndex\b", key_blob):
        fail(
            f"{_ISSUE}: Space uses tlIndex (highlight), not article focus"
        )
    if _ARTICLE_FOCUS.search(key_blob):
        fail(
            f"{_ISSUE}: Space uses tlIndex (highlight), not article focus"
        )
    if re.search(r"querySelectorAll\s*(?:<[^>]+>)?\s*\(\s*[`'\"'][^`'\"']*data-tl-index", key_blob):
        if re.search(r"\.(?:forEach|map)\s*\(|for\s*\(\s*(?:const|let|var)\b|for\s*\(\s*\w+\s+of\b", key_blob):
            fail(
                f"{_ISSUE}: first [data-voice-note] audio on that "
                "data-tl-index row — not every note"
            )
    if _CLICK_PLAY.search(key_blob) or _FOCUS_PLAY.search(key_blob):
        fail(
            f"{_ISSUE}: look up the mounted <audio> and call the shared "
            "helper — do not click / focus [data-voice-play]"
        )

    # 4) shared helper = click togglePlay (play/pause + pause-others).
    if not _shared_helper_ok(keys_c, cas_c, helpers):
        fail(
            f"{_ISSUE}: extract togglePlay to a shared helper "
            "(CasVoice.ts or <script module>) that CasAttach click and "
            "PeopleKeys Space both call — same play/pause + pause-others"
        )
    if not _PAUSE_OTHERS.search(helper_blob) or not _PLAY.search(helper_blob):
        fail(
            f"{_ISSUE}: the shared helper must play/pause and pause other "
            "[data-voice-note] audio (one at a time, same as click)"
        )
    if not _PAUSE.search(helper_blob):
        fail(
            f"{_ISSUE}: the shared helper must pause the same <audio> on "
            "the second Space (play then pause)"
        )
    if not (_TOGGLE.search(key_blob) or _PLAY.search(key_blob)):
        fail(
            f"{_ISSUE}: Space must run the shared play/pause helper when "
            "that row’s <audio> is mounted"
        )

    # 5) no-audio / virtualizer — no-op, no preventDefault, no toast.
    if not _pd_only_if_audio(key_blob):
        fail(
            f"{_ISSUE}: preventDefault only when that row’s mounted "
            "<audio> exists (text-only / omitted / unmounted virtualizer "
            "is a no-op — no preventDefault)"
        )
    if _TOAST.search(key_blob):
        fail(
            f"{_ISSUE}: no-audio / unmounted row is a silent no-op "
            "(no toast)"
        )

    # 6) BUTTON / VIDEO native Space (keep-314 Load older is a button).
    if not _BUTTON_TAG.search(key_blob) and not _BUTTON_TAG.search(handle):
        fail(
            f"{_ISSUE}: if tagName === \"BUTTON\", return "
            "(native Space — play button / Load older / people options)"
        )
    if not _VIDEO_TAG.search(key_blob) and not _VIDEO_TAG.search(handle):
        fail(
            f"{_ISSUE}: if tagName === \"VIDEO\", return (native Space)"
        )
    if not rows_path.is_file():
        fail(f"{_ISSUE}: keep [data-load-older] a native tabbable button")
    rows_m = _svelte_markup(rows_raw)
    hook = rows_m.find("data-load-older")
    if hook < 0:
        fail(f"{_ISSUE}: keep [data-load-older] (native tabbable button)")
    tag = (_open_tag_before(rows_m, hook) or ("", ""))[1]
    if _TAB_NEG.search(tag) or not re.search(r"<(?:Button|button)\b", tag):
        fail(
            f"{_ISSUE}: keep [data-load-older] a native tabbable button "
            "(do not preventDefault Space on that control)"
        )

    # 7) lightbox / video overlay — do not toggle a timeline note.
    if not _LIGHTBOX_OPEN.search(key_blob) and not _LIGHTBOX_OPEN.search(handle):
        fail(
            f"{_ISSUE}: if photo lightbox / video overlay is open, do not "
            "toggle a timeline voice note"
        )

    # 8) space-field-native — do not add Space to the steal list.
    if _steal_has_space(handle) or _steal_has_space(on_key):
        fail(
            f"{_ISSUE}: do not add Space to the field-steal list "
            "(#q / #person-filter / #tl-find keep a typed space)"
        )

    # 9) space-no-autoplay — <audio> has no autoplay; highlight does not play.
    if _AUTOPLAY.search(cas_raw) or _AUTOPLAY.search(cas_c):
        fail(f"{_ISSUE}: CasAttach <audio> must not set autoplay")
    set_tl = _fn(app_c, "onKey")
    if re.search(r"\bsetTlIndex\b[\s\S]{0,160}\.play\s*\(", handle + "\n" + set_tl):
        fail(f"{_ISSUE}: selecting / highlighting a row must not call play()")
    for rx in (_KEY_J, _KEY_K):
        jm = rx.search(keys_c)
        if jm and _PLAY.search(_near(keys_c, jm, 80, 220)):
            fail(f"{_ISSUE}: j/k must not autoplay a voice note")

    # 10) space-keep-119-170 — local player + seek + CasVideo pauses voice.
    if "casDataUrl" not in cas_raw:
        fail(f"{_ISSUE}: voice notes stay on casDataUrl (local data: URL)")
    if _VOICE_REMOTE_SRC.search(cas_c) or re.search(r"[\"']https?://", cas_c):
        fail(f"{_ISSUE}: CasAttach must not use remote http(s) for voice")
    if not _VOICE_KIND.search(cas_raw) or not _VOICE_AUDIO_EL.search(cas_raw):
        fail(f"{_ISSUE}: keep the in-app <audio> player (kind === voice / audio/*)")
    if not _VOICE_LOCAL_SRC.search(cas_raw):
        fail(f"{_ISSUE}: <audio> src stays local casDataUrl / data: / srcs")
    if not _VOICE_PLAY_PAUSE.search(cas_raw) or not _VOICE_TIME_CHROME.search(cas_raw):
        fail(f"{_ISSUE}: keep play/pause + elapsed/duration (#119)")
    if not _VOICE_SEEK_TRACK.search(cas_raw) or not _VOICE_SEEK_WRITE.search(cas_c):
        fail(f"{_ISSUE}: keep the local seek / progress track (#170)")
    if not vid_path.is_file():
        fail(f"{_ISSUE}: keep CasVideo.svelte (video play still pauses voice notes)")
    if not _PAUSE_OTHERS.search(vid_c):
        fail(f"{_ISSUE}: CasVideo must still pause [data-voice-note] audio")
    surface = cas_c + "\n" + vid_c + "\n" + helper_blob
    if _VOICE_WAVEFORM_CDN.search(surface) or _VOICE_TRANSCRIPTION.search(surface):
        fail(f"{_ISSUE}: not in scope — no waveform CDN / transcription")

    # 11) space-keep-132 — j/k, End, Home/⌘↑, ⌘C unchanged.
    if not re.search(r"tagName\s*===?\s*[\"']INPUT[\"']", handle):
        fail(
            f"{_ISSUE}: letter shortcuts still sit behind the "
            "INPUT/TEXTAREA/SELECT guard"
        )
    if not _KEY_J.search(keys_c) or not _KEY_K.search(keys_c):
        fail(f"{_ISSUE}: keep j/k — they still only walk visibleTlIndices")
    if not re.search(r"\bvisibleTlIndices\b", keys_c):
        fail(f"{_ISSUE}: keep j/k walking visibleTlIndices")
    for rx in (_KEY_J, _KEY_K):
        jm = rx.search(keys_c)
        if jm and _PREPEND.search(_near(keys_c, jm, 80, 220)):
            fail(f"{_ISSUE}: j/k still only walk visibleTlIndices")
        if jm and not _WALK.search(_near(keys_c, jm, 80, 220) + keys_c):
            fail(f"{_ISSUE}: j/k still only walk visibleTlIndices")
        if jm and _KEY_SPACE.search(_near(keys_c, jm, 40, 120)):
            fail(f"{_ISSUE}: do not steal j/k for Space")
    end_m = _END.search(keys_c)
    if not end_m or not _PIN.search(_near(keys_c, end_m, 80, 240)):
        fail(f"{_ISSUE}: keep End → Latest (scrollToLatest)")
    if end_m and _TOGGLE.search(_near(keys_c, end_m, 40, 160)):
        fail(f"{_ISSUE}: do not steal End for Space")
    home_m = _HOME.search(keys_c)
    if not home_m or not _PREPEND.search(_near(keys_c, home_m, 80, 360) + keys_c):
        fail(f"{_ISSUE}: keep Home Load older (prependOlder)")
    up_ok = False
    for m in _ARROW_UP.finditer(keys_c):
        w = _near(keys_c, m, 160, 240)
        if _MOD.search(w) and _PREPEND.search(w + keys_c):
            up_ok = True
            break
    if not up_ok:
        fail(f"{_ISSUE}: keep ⌘↑ Load older (prependOlder)")
    if not _KEY_C.search(keys_c) or not _COPY_SEL.search(keys_c):
        fail(f"{_ISSUE}: keep ⌘C / Ctrl+C → copySelected")

    # 12) space-keep-210 — Search-tab Space still activateHit.
    if not search_path.is_file():
        fail(f"{_ISSUE}: keep SearchPane.svelte (Search-tab Space → activateHit)")
    hits_key = _fn(search_c, "onHitsKey")
    if not hits_key:
        fail(f"{_ISSUE}: keep onHitsKey — Search-tab Space still activateHit (#210)")
    if not _KEY_SPACE.search(hits_key):
        fail(f"{_ISSUE}: onHitsKey must still handle Space → activateHit")
    if not _ACTIVATE.search(hits_key):
        fail(f"{_ISSUE}: onHitsKey Space must still call activateHit (#210)")

    # 13) space-not-media-keys + no App / List / Pane wire.
    touched = keys_c + "\n" + cas_c + "\n" + app_c + "\n" + vid_c + "\n" + helper_blob
    if _MEDIA_KEYS.search(touched):
        fail(
            f"{_ISSUE}: no MediaPlayPause / mediaSession "
            "(not global media keys)"
        )
    if _WIRE_NAME.search(app_c) or _WIRE_NAME.search(list_c) or _WIRE_NAME.search(pane_c):
        fail(
            f"{_ISSUE}: no App / TimelineList / TimelinePane wire — "
            "PeopleKeys queries the mounted <audio>"
        )
    if _KEY_SPACE.search(on_key) and (
        _PLAY.search(on_key) or _TOGGLE.search(on_key) or _ROW_AUDIO.search(on_key)
    ):
        fail(
            f"{_ISSUE}: no App.svelte onKey Space branch — handleAppKey owns it"
        )
    if _KEY_SPACE.search(rows_raw) and re.search(r"on:?keydown", rows_raw, re.I):
        fail(f"{_ISSUE}: Space is PeopleKeys, not article onkeydown")

    # 14) locale — no new t() key.
    if _T_CALL.search(key_blob) or _T_CALL.search(helper_blob):
        fail(f"{_ISSUE}: no new t() key on the Space / voice path")
    en_p = crate / "web" / "lib" / "locales" / "en.ts"
    if en_p.is_file():
        extra = [
            k
            for k in _chrome_pack_entries(en_p.read_text())
            if _NEW_LOCALE.search(k)
        ]
        if extra:
            fail(
                f"{_ISSUE}: no new t() key "
                f"({', '.join(sorted(extra))} — no locale string for Space)"
            )

    # 15) space-d24
    if not dtxt.strip():
        fail(
            f"{_ISSUE}: docs/user/app.md required — highlighted voice "
            "bubble, Space play/pause; #q still types a space"
        )
    if not _DOCS_SPACE.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say Space play/pause on the "
            "selected / highlighted voice bubble"
        )
    if not _DOCS_Q.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say #q still types a space"
        )
    if not _DOCS_AUTOPLAY.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must keep autoplay off")
    if re.search(r"/Users/|/home/", keys_c + "\n" + key_blob):
        fail(f"{_ISSUE}: tests stay placeholders (Ada) — no real home paths")
