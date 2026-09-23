"""#380: when a People-timeline voice note ends, play the next one.

One hidden host sits beside TimelineList. The row player stays for
#119, #170, and #316. Search preview does not chain.
"""

from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.scan_parse import _svelte_markup, _without_comments
from tauri_gate.status_toasts_toast import _svelte_effect_args

_ISSUE = "#380"
_HOST_ATTR = re.compile(r"\bdata-[\w-]*host[\w-]*", re.I)
_ROW_AUDIO = (
    '#person-timeline [data-tl-index="${ctx.tlIndex}"] [data-voice-note] audio'
)
_AUDIO_EXT = re.compile(r"opus|ogg|mp3|m4a|aac|wav", re.I)
_MEDIA_KEY = re.compile(r"MediaPlayPause|MediaTrackNext|mediaSession")
_HTTP = re.compile(r"[\"']https?://")
_FN = re.compile(
    r"(?:export\s+)?(?:async\s+)?function\s+{name}\s*\("
    r"|const\s+{name}\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_]\w*)\s*=>"
)


def _read(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _lib(crate: Path) -> Path:
    return crate / "web" / "lib"


def _brace_end(src: str, open_at: int) -> int:
    depth = 0
    i = open_at
    n = len(src)
    while i < n:
        c = src[i]
        if c in "\"'`":
            q = c
            i += 1
            while i < n and src[i] != q:
                if src[i] == "\\":
                    i += 2
                    continue
                i += 1
            i += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _fn_body(src: str, name: str) -> str:
    m = re.search(_FN.pattern.format(name=re.escape(name)), src)
    if not m:
        return ""
    brace = src.find("{", m.end())
    if brace < 0:
        return ""
    end = _brace_end(src, brace)
    if end < 0:
        return src[brace:]
    return src[brace : end + 1]


def _imports(src: str) -> list[str]:
    return re.findall(r"""from\s+["'](\./[^"']+)["']""", src)


def _chain_blob(crate: Path, pane: str) -> str:
    """TimelinePane plus a helper it imports for the host, not the photo walk."""
    parts = [pane]
    lib = _lib(crate)
    for rel in _imports(pane):
        for suffix in ("", ".ts", ".svelte"):
            path = lib / f"{rel}{suffix}"
            if not path.is_file():
                continue
            text = _without_comments(_read(path))
            if _HOST_ATTR.search(text) or re.search(r"\bonended\b", text):
                parts.append(text)
            break
    return "\n".join(parts)


_CALL_SKIP = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "return",
    "await",
    "function",
}


def _callees(body: str) -> list[str]:
    return [
        name
        for name in re.findall(r"\b([A-Za-z_]\w*)\s*\(", body)
        if name not in _CALL_SKIP
    ]


def _onended_expr(host: str) -> str:
    m = re.search(r"\bonended\s*=\s*\{", host)
    if not m:
        return ""
    expr = _brace_end(host, m.end() - 1)
    if expr < 0:
        return ""
    return host[m.start() : expr + 1]


def _ended_walk(host: str, chain: str) -> str:
    """Handler on the host's ended event, plus the functions it calls."""
    expr = _onended_expr(host)
    if not expr:
        return ""
    parts = [expr]
    seen: set[str] = set()
    queue = _callees(expr) + re.findall(r"\b([A-Za-z_]\w*)\b", expr)
    queue = [name for name in queue if name not in _CALL_SKIP and name != "onended"]
    while queue and len(seen) < 12:
        name = queue.pop(0)
        if name in seen:
            continue
        seen.add(name)
        body = _fn_body(chain, name)
        if not body:
            continue
        parts.append(body)
        queue.extend(_callees(body))
    blob = "\n".join(parts)
    if "filteredTimeline" not in blob:
        return ""
    return blob


def _stops_host(chain: str, body: str) -> bool:
    if ".pause(" in body and _clears_src(body):
        return True
    for name in _callees(body):
        callee = _fn_body(chain, name)
        if callee and ".pause(" in callee and _clears_src(callee):
            return True
    return False


def _host_tag(markup: str) -> str:
    for m in re.finditer(r"<audio\b[^>]*>", markup, re.S):
        tag = m.group(0)
        window = markup[max(0, m.start() - 400) : m.end() + 80]
        if _HOST_ATTR.search(tag) or _HOST_ATTR.search(window):
            return window
    return ""


def _effect_mentions_groups(src: str) -> bool:
    for arg in _svelte_effect_args(src):
        if re.search(r"\bincludeGroups\b", arg):
            return True
    return False


def _clears_src(body: str) -> bool:
    return bool(
        re.search(r"\bsrc\s*=\s*(?:null|[\"']{2}|\"\"|'')", body)
        or re.search(r"\.src\s*=\s*(?:null|[\"'][\"'])", body)
        or re.search(r"removeAttribute\(\s*[\"']src[\"']\s*\)", body)
    )


def assert_voice_next(crate: Path) -> None:
    """#380: host ended starts the next filtered voice; pause does not."""
    lib = _lib(crate)
    pane_raw = _read(lib / "TimelinePane.svelte")
    cas_raw = _read(lib / "CasAttach.svelte")
    keys_raw = _read(lib / "PeopleKeys.ts")
    voice_raw = _read(lib / "CasVoice.ts")
    video_raw = _read(lib / "CasVideo.svelte")
    list_raw = _read(lib / "TimelineList.svelte")
    rows_raw = _read(lib / "TimelineRows.svelte")
    search_raw = _read(lib / "SearchHits.svelte")
    walk_raw = _read(lib / "threadWalk.ts")
    mail_raw = _read(lib / "TimelineMail.ts")
    prefs_raw = _read(lib / "PeoplePrefs.ts")
    app_raw = _read(crate / "web" / "App.svelte")
    shell_raw = _read(lib / "PeopleShell.svelte")
    insp_raw = _read(lib / "PeopleInspector.svelte")
    if not pane_raw or not cas_raw:
        fail(f"{_ISSUE}: TimelinePane.svelte and CasAttach.svelte are required")

    pane = _without_comments(pane_raw)
    cas = _without_comments(cas_raw)
    keys = _without_comments(keys_raw)
    voice = _without_comments(voice_raw)
    video = _without_comments(video_raw)
    list_c = _without_comments(list_raw)
    rows = _without_comments(rows_raw)
    search = _without_comments(search_raw)
    walk = _without_comments(walk_raw)
    mail = _without_comments(mail_raw)
    chain = _chain_blob(crate, pane)
    pane_mark = _svelte_markup(pane_raw)
    cas_mark = _svelte_markup(cas_raw)

    # Keeps that already hold on master (#119, #170, #316, #379, #309).
    if "<audio" not in cas or "data-voice-note" not in cas:
        fail(f"{_ISSUE}: the row <audio data-voice-note> in CasAttach stays")
    if "data-voice-play" not in cas or "data-voice-seek" not in cas:
        fail(f"{_ISSUE}: keep data-voice-play and data-voice-seek on the row")
    if "data-voice-time" not in cas:
        fail(f"{_ISSUE}: keep data-voice-time (elapsed/duration)")
    if "Pause voice note" not in cas or "Play voice note" not in cas:
        fail(f"{_ISSUE}: keep the Play / Pause voice note labels")
    if "Play" not in cas or "Pause" not in cas:
        fail(f"{_ISSUE}: keep the Lucide Play / Pause swap")
    if not re.search(r"<audio\b[^>]*preload=[\"']metadata[\"']", cas, re.S):
        fail(f"{_ISSUE}: row audio stays preload=\"metadata\"")
    if re.search(r"<audio\b[^>]*\bautoplay\b", cas, re.S | re.I):
        fail(f"{_ISSUE}: row audio must not autoplay")
    if "casDataUrl" not in cas or _HTTP.search(cas):
        fail(f"{_ISSUE}: row audio stays on local casDataUrl (no http(s))")
    if "omitted" not in cas or "missing" not in cas:
        fail(f"{_ISSUE}: omitted and missing stay placeholders")
    if not re.search(r"kind\s*===\s*[\"']voice[\"']", cas):
        fail(f"{_ISSUE}: isAudio still includes kind voice")
    if "audio/" not in cas or not _AUDIO_EXT.search(cas):
        fail(f"{_ISSUE}: isAudio still includes audio/* and opus/ogg/mp3/m4a/aac/wav")
    if not re.search(r"\.currentTime\s*=", cas):
        fail(f"{_ISSUE}: seek still writes currentTime on the row path")
    if "filteredTimeline" in cas:
        fail(f"{_ISSUE}: CasAttach must not walk filteredTimeline (Search would chain)")
    if _ROW_AUDIO not in keys:
        fail(
            f"{_ISSUE}: Space selector stays "
            '`#person-timeline [data-tl-index="${tlIndex}"] [data-voice-note] audio`'
        )
    if _HOST_ATTR.search(keys):
        fail(f"{_ISSUE}: do not point the Space query at the host")
    handle = _fn_body(keys, "handleAppKey") or keys
    space_at = handle.find(_ROW_AUDIO)
    if space_at < 0:
        fail(f"{_ISSUE}: Space looks up the highlighted row audio")
    space_win = handle[max(0, space_at - 500) : space_at + 220]
    if "preventDefault" not in space_win.split(_ROW_AUDIO, 1)[-1]:
        fail(f"{_ISSUE}: preventDefault only after the row audio exists")
    if not re.search(
        r"tagName\s*===\s*[\"']INPUT[\"'][\s\S]{0,80}TEXTAREA[\s\S]{0,40}SELECT",
        handle,
    ):
        fail(f"{_ISSUE}: INPUT / TEXTAREA / SELECT still return before Space")
    early = handle[: handle.find("INPUT")] if "INPUT" in handle else handle
    if "preventDefault" in early and re.search(r"key\s*===\s*[\"'] [\"']|code\s*===\s*[\"']Space[\"']", early):
        fail(f"{_ISSUE}: a field Space must not preventDefault before the field return")
    for blob, label in (
        (keys, "PeopleKeys"),
        (cas, "CasAttach"),
        (voice, "CasVoice"),
        (pane, "TimelinePane"),
    ):
        if _MEDIA_KEY.search(blob):
            fail(f"{_ISSUE}: no media keys in {label}")
        if "playbackRate" in blob:
            fail(f"{_ISSUE}: no playback speed in {label}")
    if re.search(r"voice.*(chain|next|playlist)|playlist", prefs_raw, re.I):
        fail(f"{_ISSUE}: no PeoplePrefs key for chain play")
    if "VIRTUALIZE_AFTER" not in list_c or "filteredTimeline.slice" not in list_c:
        fail(f"{_ISSUE}: the virtual window still unmounts rows outside the slice")
    if not re.search(r"as item \(item\.index\)", rows):
        fail(f"{_ISSUE}: row each stays keyed by item.index (prepend may destroy the row audio)")
    if "id=\"person-timeline\"" not in list_raw and "id='person-timeline'" not in list_raw:
        fail(f"{_ISSUE}: #person-timeline stays on the list, not on the host")
    if "filteredTimeline" in search or "data-thread-lightbox" in search:
        fail(f"{_ISSUE}: SearchHits does not walk the timeline or host the thread lightbox")
    search_tag = ""
    mtag = re.search(r"<CasAttach\b[^>]*>", search, re.S)
    if mtag:
        search_tag = mtag.group(0)
    if "onOpenImage" in search_tag or _HOST_ATTR.search(search):
        fail(f"{_ISSUE}: Search preview CasAttach does not use the timeline host")
    if "isVoiceStep" not in walk or "isThreadStep" not in walk:
        fail(f"{_ISSUE}: voice stays out of threadImages")
    step = _fn_body(walk, "isThreadStep")
    if "isVoiceStep" not in step:
        fail(f"{_ISSUE}: do not put voice notes into the photo lightbox")
    voice_attach = _fn_body(mail, "isVoiceAttach")
    if voice_attach and _AUDIO_EXT.search(voice_attach):
        fail(f"{_ISSUE}: do not widen isVoiceAttach (voice chip stays as it is)")
    if "[data-voice-note] audio" not in video:
        fail(f"{_ISSUE}: CasVideo still pauses every [data-voice-note] audio")
    if "filteredTimeline" in video or re.search(r"\bonended\b", video):
        fail(f"{_ISSUE}: opening a video pauses voice notes and does not advance")
    if "[data-voice-note] audio" not in voice:
        fail(f"{_ISSUE}: togglePlay still pauses other [data-voice-note] audio")
    if "filteredTimeline" in voice:
        fail(f"{_ISSUE}: togglePlay pause-others must not start the next note")
    for label, src in (
        ("App.svelte", app_raw),
        ("TimelinePane.svelte", pane_raw),
        ("PeopleShell.svelte", shell_raw),
        ("PeopleInspector.svelte", insp_raw),
    ):
        if _effect_mentions_groups(src):
            fail(
                f"{_ISSUE}: no $effect in {label} whose body mentions includeGroups"
            )
    if _HOST_ATTR.search(app_raw) or re.search(r"new\s+Audio\s*\(", app_raw):
        fail(f"{_ISSUE}: the host lives in TimelinePane and dies with People")

    host = _host_tag(pane_mark)
    if not host:
        fail(
            f"{_ISSUE}: one hidden host <audio> in TimelinePane, sibling of "
            "TimelineList, with data-voice-note and a distinct host mark"
        )
    if "data-voice-note" not in host:
        fail(f"{_ISSUE}: the host carries data-voice-note so pause-all sees it")
    if not re.search(r"\bhidden\b|class=\"[^\"]*\bhidden\b", host):
        fail(f"{_ISSUE}: the host audio is hidden")
    if re.search(r"\bautoplay\b", host, re.I):
        fail(f"{_ISSUE}: the host must not autoplay")
    if _HTTP.search(host):
        fail(f"{_ISSUE}: the host src is local casDataUrl, not http(s)")
    if "person-timeline" in host or "data-thread-lightbox" in host:
        fail(f"{_ISSUE}: host sits outside #person-timeline and outside the photo lightbox")
    if "data-thread-lightbox" in (lib / "TimelineLightbox.svelte").read_text() and "<audio" in _read(
        lib / "TimelineLightbox.svelte"
    ):
        fail(f"{_ISSUE}: do not put a voice stream in the photo lightbox")
    if "id=\"person-timeline\"" in pane_mark or "id='person-timeline'" in pane_mark:
        fail(f"{_ISSUE}: do not move #person-timeline onto the host sibling")
    if not re.search(r"\bcasDataUrl\b", chain):
        fail(f"{_ISSUE}: the host loads the note with casDataUrl")

    if re.search(r"\bonpause\s*=", host):
        fail(f"{_ISSUE}: host pause must not advance; only host ended walks")
    walk_body = _ended_walk(host, chain)
    if not walk_body:
        fail(
            f"{_ISSUE}: only the host ended event walks filteredTimeline "
            "to the next note (no chain today)"
        )
    if re.search(r"toReversed\s*\(|\.reverse\s*\(", walk_body):
        fail(f"{_ISSUE}: walk filteredTimeline toward the bottom (newer), attachments in array order")
    if "%" in walk_body:
        fail(f"{_ISSUE}: after the last loaded playable note, stop (do not wrap)")
    for banned, why in (
        ("personTimeline", "do not fetch the next page"),
        ("collectOlderThreadRows", "do not reuse the photo older-page walk"),
        ("findQ", "find does not remove rows; a non-hit voice is still next"),
        ("findHit", "find does not remove rows"),
    ):
        if banned in walk_body:
            fail(f"{_ISSUE}: {why}")
    if re.search(r"\bafter\s*:", walk_body):
        fail(f"{_ISSUE}: do not pass an after cursor to load a newer page")
    if "message_id" not in walk_body:
        fail(f"{_ISSUE}: two messages that share a cas_hash are two steps (message_id)")
    if "keyOf" not in walk_body and "cas_hash" not in walk_body:
        fail(f"{_ISSUE}: same-message attachments walk in array order; one keyOf per hash")
    if not re.search(r"\bomitted\b", walk_body) or not re.search(r"\bmissing\b", walk_body):
        fail(f"{_ISSUE}: omitted and missing attachments are not steps")
    if "broken" not in walk_body:
        fail(f"{_ISSUE}: a broken note is not a step; keep walking")
    if not re.search(
        r"(?:src|url|casDataUrl)[\s\S]{0,120}\bcontinue\b|\bcontinue\b[\s\S]{0,120}(?:src|url|casDataUrl)",
        walk_body,
    ):
        fail(f"{_ISSUE}: a note still waiting on casDataUrl is not a step; keep walking")
    if not re.search(r"kind\s*===\s*[\"']voice[\"']|isAudio|audio/", walk_body):
        fail(f"{_ISSUE}: a step is the same isAudio set as the bubble player")
    if not re.search(r"\bseek", walk_body, re.I):
        fail(
            f"{_ISSUE}: a seek that fires ended is not this end; "
            "only a natural host ended advances"
        )

    if "data-voice-now" not in cas:
        fail(f"{_ISSUE}: set data-voice-now on the mounted playing [data-voice-note]")
    now_at = cas.find("data-voice-now")
    now_win = cas[max(0, now_at - 500) : now_at + 160]
    if "data-voice-note" not in now_win:
        fail(f"{_ISSUE}: data-voice-now sits on the voice bubble, not a status line")
    now = re.search(r"data-voice-now=\{([^}]*)\}", cas)
    if now and re.fullmatch(r"\s*playing\s*\[[^\]]*\]\s*", now.group(1) or ""):
        fail(f"{_ISSUE}: playing[key] on the row is not the source of truth")
    if re.search(r"Now playing|playlist|Playback speed", cas + pane, re.I):
        fail(f"{_ISSUE}: no status line, playlist region, or speed control")

    seek = _fn_body(cas, "seekVoice") or ""
    if "currentTime" not in seek or (
        "host" not in seek.lower() and not _HOST_ATTR.search(seek)
    ):
        fail(f"{_ISSUE}: a row seek still writes currentTime and also moves the host")
    toggle = _fn_body(voice, "togglePlay") or ""
    if "host" not in toggle.lower() and not _HOST_ATTR.search(toggle):
        fail(
            f"{_ISSUE}: play, pause, and Space on the bubble drive the host; "
            "the row audio stays paused while the host owns the note"
        )

    select = _fn_body(pane, "selectPerson")
    opened = _fn_body(pane, "openPersonAtMessage")
    if not _stops_host(chain, select):
        fail(
            f"{_ISSUE}: selectPerson pauses the host and clears src "
            "(switching person stops playback)"
        )
    guarded = False
    for m in re.finditer(r"!\s*append", select):
        if _stops_host(chain, select[m.start() : m.start() + 700]):
            guarded = True
    if not guarded:
        fail(f"{_ISSUE}: stop on non-append reload only; append / load-older keeps the host")
    for m in re.finditer(r"if\s*\(\s*append\s*\)\s*\{", select):
        brace = select.find("{", m.end() - 1)
        end = _brace_end(select, brace) if brace >= 0 else -1
        block = select[brace : end + 1] if end >= 0 else ""
        if block and _stops_host(chain, block):
            fail(f"{_ISSUE}: append / load-older must not stop the host")
    if not _stops_host(chain, opened):
        fail(f"{_ISSUE}: openPersonAtMessage stops the host (same id or another person)")
    chip = False
    for name in re.findall(r"function\s+([A-Za-z_]\w*)\s*\(", pane):
        if name in {"selectPerson", "openPersonAtMessage"}:
            continue
        body = _fn_body(pane, name)
        if (
            "filteredTimeline" in body
            and ".pause(" in body
            and "message_id" in body
            and "findQ" not in body
        ):
            chip = True
    for arg in _svelte_effect_args(pane_raw):
        if "includeGroups" in arg or "findQ" in arg:
            continue
        blob = arg
        for name in _callees(arg):
            blob += "\n" + _fn_body(chain, name)
        if "filteredTimeline" in blob and ".pause(" in blob and "message_id" in blob:
            chip = True
    if not chip:
        fail(
            f"{_ISSUE}: when a chip drops the playing message out of "
            "filteredTimeline, stop the host; find does not"
        )

    docs = _read(repo_root() / "docs" / "user" / "app.md").lower()
    sentence = ""
    hit = re.search(r"when a voice note ends.{0,500}", docs)
    if hit:
        sentence = hit.group(0)
    if not sentence or not all(
        piece in sentence for piece in ("next voice", "pause", "scroll", "person")
    ):
        fail(
            f"{_ISSUE}: docs/user/app.md must say that in the People timeline, "
            "when a voice note ends the next voice starts, pause does not skip, "
            "scrolling the row away keeps it playing, and switching person stops it"
        )
