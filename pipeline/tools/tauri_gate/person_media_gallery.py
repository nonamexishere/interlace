"""#361 — person media gallery.

Confirmed mix: A's person_media IPC + owned Dialog grid + visible-window
casDataUrl. Quiet Media control on the timeline Find / Jump row. Inspector
Media opens the same Dialog (not a second grid). Do not use B as the
source of truth. Do not use D.

Same membership + group SQL as person_timeline_rows_for (All). Join
attachments where cas_hash IS NOT NULL AND omitted = 0 AND missing = 0
and kinds image / video / sticker, or kind = inline when mime is image/*
or video/*. Newest first. Whole timeline membership (sender or
participant), including from_me. Include-groups follows the timeline
tick. Photo / sticker → #118 data-photo-lightbox. Video thumb → #271
CasVideo (no autoplay). Show in timeline closes the Dialog, then
openPersonAtMessage. EmptyState + next action. Virtualize after 48.
Windowed casDataUrl. Ignore timeline chips. Keep #118 / #271 / #124 /
#309 / #205 / #278 / #213. D24 docs/user/app.md.

Placeholders only (Ada / Berk).
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.locale_more import _chrome_pack_entries
from tauri_gate.media_cas_lib import _CAS_VIDEO_AUTOPLAY, _has_cas_video_surface
from tauri_gate.media_lightbox_lib import _LIGHTBOX_VIDEO_CHROME
from tauri_gate.scan import (
    _function_body,
    _rust_fn_signature,
    _rust_function_body,
    _svelte_markup,
    _tauri_rust_blob,
    _ts_fn_body,
    _web_logic,
    _web_sources,
    _without_comments,
)
from tauri_gate.status_toasts_chrome import (
    _invoke_payloads,
    _payload_has_path_or_url,
    _windows_around,
)

_ISSUE = "#361"
_EXISTING_CORE_FNS = frozenset(
    {
        "person_conversations",
        "person_timeline",
        "person_timeline_rows",
        "person_timeline_rows_for",
        "person_list",
        "person_list_on",
        "person_list_on_with_groups",
        "person_list_with_groups",
        "person_identities",
        "person_display_name",
        "person_show",
        "merge_targets",
        "recent_link_events",
        "attachments_for",
        "complete_attachments",
        "extract_attached_filenames",
        "conversation_participant_names",
        "attach_attachments",
        "enrich_from_body_tokens",
    }
)
_EXISTING_CMDS = frozenset(
    {
        "person_show",
        "person_timeline",
        "person_conversations_cmd",
        "person_merge_cmd",
        "person_unlink_cmd",
        "person_undo_cmd",
        "link_events",
        "people",
        "conversation_participants_cmd",
    }
)
_GALLERY_OPEN = re.compile(
    r"\bdata-person-gallery-open\b|\bdata-person-media-open\b",
    re.I,
)
_GALLERY_GRID = re.compile(r"\bdata-person-gallery(?!-)", re.I)
_MEDIA_T = re.compile(
    r"""\bt\s*\(\s*["'](?:media|personMedia|gallery|personGallery|openGallery)["']\s*\)"""
)
_SELECTED_IF = re.compile(r"\{#if\s+selectedId\b")
_IF_TOKEN = re.compile(r"\{#if\b|\{:else(?:\s+if\b)?|\{/if\}")
_FN_DEF = re.compile(r"(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*\(")
_HANDLER = re.compile(r"generate_handler!\s*\[(.*?)\]", re.S)
_CLIENT_PARAM = re.compile(
    r"\b(?:path|url|file|href|uri|dest|source|root)\s*:",
    re.I,
)
_WITH_ARCH = re.compile(r"\bwith_arch\s*\(")
_OPEN_SECOND = re.compile(r"\bopen_archive\s*\(|LockMode\s*::\s*Exclusive")
_API_MEDIA = re.compile(
    r"\b(personMedia|personMediaRows|personGallery)\s*:",
)
_INVOKE_MEDIA = re.compile(
    r"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']"
    r"(person_media(?:_cmd|_rows)?|person_gallery)[\"']",
    re.I,
)
_CAS_HASH_NOT_NULL = re.compile(r"cas_hash\s+IS\s+NOT\s+NULL", re.I)
_OMITTED_ZERO = re.compile(r"omitted\s*(?:=|==|<>|!=)\s*0", re.I)
_MISSING_ZERO = re.compile(r"missing\s*(?:=|==|<>|!=)\s*0", re.I)
_KIND_IMAGE = re.compile(r"""['"]image['"]""")
_KIND_VIDEO = re.compile(r"""['"]video['"]""")
_KIND_STICKER = re.compile(r"""['"]sticker['"]""")
_KIND_INLINE = re.compile(r"""['"]inline['"]""")
_MIME_IMAGE = re.compile(r"image/", re.I)
_MIME_VIDEO = re.compile(r"video/", re.I)
_GROUP_SQL = re.compile(
    r"kind\s+IN\s*\(\s*['\"]dm['\"]\s*,\s*['\"]email_thread['\"]",
    re.I,
)
_MEMBER_SENDER = re.compile(r"\bsender_identity_id\b")
_MEMBER_PART = re.compile(
    r"\b(?:conversation_participants|person_identities)\b", re.I
)
_SORT_DESC = re.compile(
    r"ORDER\s+BY\s+[^\n]{0,160}sent_at[^\n]{0,80}DESC",
    re.I | re.S,
)
_SORT_ID = re.compile(
    r"ORDER\s+BY\s+[^\n]{0,200}id[^\n]{0,40}DESC",
    re.I | re.S,
)
_BODY_TOKEN = re.compile(r"<attached:|extract_attached|enrich_from_body", re.I)
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][\w]*)["']\s*\)""")
_T_FN = re.compile(r"export\s+function\s+t\s*\(\s*key\s*:\s*ChromeKey\s*\)")
_T_NOT_KEY = re.compile(
    r"""\bt\s*\(\s*(?:[\w$.]*\b(?:display_name|displayName|value|name|body_text|filename)\b)"""
)
_PLACEHOLDERS = re.compile(r"\bAda\b|\bBerk\b")
_INNERHTML = re.compile(r"\binnerHTML\b|\{@html\b")
_HTTP_SRC = re.compile(r"""(?:src|href)\s*=\s*["']https?://|["']https?://""", re.I)
_VIRT_N = re.compile(r"\b48\b")
_VIRT_WINDOW = re.compile(
    r"\b(?:startIndex|endIndex|spacer|virtual(?:ize|ised|ized)?|"
    r"windowStart|visibleStart|visibleEnd|slice\s*\()\b",
    re.I,
)
_GEN_TOKEN = re.compile(
    r"\b(?:galleryGen|mediaGen|personGalleryGen|thumbGen)\b"
    r"|\+\+\s*(?:gallery|media|thumb)Gen"
    r"|(?:gallery|media|thumb)Gen\s*\+\+",
    re.I,
)
_CLEAR_THUMBS = re.compile(
    r"\b(?:srcs|thumbs|thumbSrcs|galleryRows|mediaRows|cells)\s*=\s*(?:\[\s*\]|new\s+Map)",
    re.I,
)
_JUMP_FN = re.compile(r"\bopenPersonAtMessage\s*\(")
_SHOW_IN_TL = re.compile(
    r"showInTimeline|show_in_timeline|data-person-gallery-jump|"
    r"t\s*\(\s*[\"'](?:showInTimeline|showInThread|jumpToMessage)[\"']\s*\)",
    re.I,
)
_DIALOG = re.compile(r"\bDialog\.(?:Root|Content)\b|<Dialog[\s.>]|role\s*=\s*[\"']dialog[\"']")
_EMPTY = re.compile(r"\bEmptyState\b|\bdata-empty\b")
_INCLUDE_ON = re.compile(
    r"includeGroups\s*=\s*true"
    r"|onIncludeGroups"
    r"|writeIncludeGroupsPref\s*\(\s*true",
)
_IMPORT_ACTION = re.compile(r"\bonImport\b|t\s*\(\s*[\"']import[\"']\s*\)", re.I)
_CHIPS = re.compile(r"\b(?:platformFilter|kindFilter)\b")
_SEARCH_PANE = re.compile(r"SearchPane")
_CAS_DATA = re.compile(r"\bcasDataUrl\s*\(")
_CAS_ATTACH = re.compile(r"<CasAttach\b")
_PHOTO_LB = re.compile(r"\bdata-photo-lightbox\b")
_VIDEO_OV = re.compile(r"\bdata-cas-video-overlay\b")
_VIDEO_IN_LB = re.compile(
    r"data-photo-lightbox[\s\S]{0,800}<video\b|<video\b[\s\S]{0,800}data-photo-lightbox",
    re.I,
)
_KEEP_KEYS = frozenset(
    {
        "findInThread",
        "jumpToDay",
        "inspector",
        "identities",
        "lastActivity",
        "inThisGroup",
        "includeGroups",
        "import",
        "retry",
    }
)
_DOCS_GALLERY = re.compile(
    r"("
    r"(?:person|Ada).{0,80}(?:media gallery|Media gallery|gallery)"
    r"|(?:Media gallery|media gallery).{0,80}(?:person|Ada)"
    r"|person.{0,40}Media"
    r")",
    re.I | re.S,
)
_DOCS_KINDS = re.compile(
    r"("
    r"(?:stored|CAS).{0,80}(?:image|photo).{0,40}(?:video).{0,40}sticker"
    r"|image.{0,20}video.{0,20}sticker"
    r")",
    re.I | re.S,
)
_DOCS_INLINE = re.compile(
    r"inline.{0,40}(?:image|video)|gmail.{0,40}inline",
    re.I | re.S,
)
_DOCS_PHOTO_LB = re.compile(
    r"(?:photo|image|sticker).{0,60}lightbox|lightbox.{0,60}(?:photo|image)",
    re.I | re.S,
)
_DOCS_VIDEO = re.compile(
    r"video.{0,80}(?:overlay|no autoplay|autoplay is off|not autoplay)",
    re.I | re.S,
)
_DOCS_JUMP = re.compile(
    r"Show in timeline|show in timeline.{0,80}jump",
    re.I | re.S,
)
_DOCS_EMPTY = re.compile(
    r"(?:empty|no stored).{0,80}(?:next action|Import|include groups)",
    re.I | re.S,
)
_DOCS_GROUPS = re.compile(
    r"include[- ]groups.{0,80}(?:timeline|tick)|follows.{0,40}(?:timeline|include groups)",
    re.I | re.S,
)
_LIGHTBOX_HOOK = re.compile(r"\bdata-photo-lightbox\b")
_CAS_VIDEO_HOOK = re.compile(r"\bdata-cas-video-overlay\b")


def _text(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _people_core_blob(root: Path) -> str:
    """people.rs + people/*.rs only (do not open import / identity / search)."""
    parts: list[str] = []
    src = root / "crates" / "interlace-core" / "src" / "people.rs"
    if src.is_file():
        parts.append(src.read_text())
    d = root / "crates" / "interlace-core" / "src" / "people"
    if d.is_dir():
        for p in sorted(d.glob("*.rs")):
            parts.append(p.read_text())
    return "\n".join(parts)


def _handler_names(rust: str) -> list[str]:
    m = _HANDLER.search(rust)
    if not m:
        return []
    return re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", m.group(1))


def _matching_if_end(src: str, start: int) -> int:
    depth = 0
    i = start
    while True:
        m = _IF_TOKEN.search(src, i)
        if not m:
            return -1
        tok = m.group(0)
        if tok.startswith("{#if"):
            depth += 1
        elif tok == "{/if}":
            depth -= 1
            if depth == 0:
                return m.end()
        i = m.end()


def _find_jump_block(tl: str) -> str:
    """{#if selectedId} that hosts data-tl-find, else a window around the hook."""
    for m in _SELECTED_IF.finditer(tl):
        end = _matching_if_end(tl, m.start())
        block = tl[m.start() : end if end > 0 else m.end() + 800]
        if "data-tl-find" in block:
            return block
    m = re.search(r"data-tl-find", tl)
    if not m:
        return ""
    return tl[max(0, m.start() - 400) : m.end() + 700]


def _gallery_files(crate: Path) -> list[Path]:
    lib = crate / "web" / "lib"
    out: list[Path] = []
    for p in sorted(lib.rglob("*")):
        if p.suffix not in {".svelte", ".ts"}:
            continue
        raw = p.read_text()
        if (
            _GALLERY_GRID.search(raw)
            or _GALLERY_OPEN.search(raw)
            or re.search(r"personMedia|person_media|PersonMedia", raw)
        ):
            out.append(p)
    return out


def _gallery_blob(crate: Path) -> str:
    parts = [_text(p) for p in _gallery_files(crate)]
    for name in (
        "PersonMediaDialog.svelte",
        "PersonGallery.svelte",
        "PersonMedia.svelte",
        "MediaGallery.svelte",
    ):
        p = crate / "web" / "lib" / name
        if p.is_file() and p not in _gallery_files(crate):
            parts.append(p.read_text())
    return "\n".join(parts)


def _media_query(core: str) -> tuple[str, str]:
    for preferred in ("person_media_rows_for", "person_media_rows", "person_media"):
        if re.search(rf"\bfn\s+{preferred}\s*\(", core):
            return preferred, _rust_function_body(core, preferred)
    for m in _FN_DEF.finditer(core):
        name = m.group(1)
        if name in _EXISTING_CORE_FNS:
            continue
        body = _rust_function_body(core, name)
        if not body:
            continue
        if not _CAS_HASH_NOT_NULL.search(body):
            continue
        if not (_KIND_IMAGE.search(body) and _KIND_VIDEO.search(body)):
            continue
        if "attachment" not in body.lower():
            continue
        return name, body
    return "", ""


def _media_cmd(rust: str, query: str) -> tuple[str, str]:
    names = _handler_names(rust)
    for name in names:
        if name in _EXISTING_CMDS:
            continue
        body = _rust_function_body(rust, name)
        if not body:
            continue
        if query and query in body:
            return name, body
        if re.search(r"person_media|person_gallery", name, re.I):
            return name, body
    for m in _FN_DEF.finditer(rust):
        name = m.group(1)
        if name in _EXISTING_CMDS:
            continue
        body = _rust_function_body(rust, name)
        if query and body and query in body:
            return name, body
        if re.search(r"person_media|person_gallery", name, re.I) and body:
            return name, body
    return "", ""


def _api_media_name(api: str) -> str:
    m = _API_MEDIA.search(api)
    if m:
        return m.group(1)
    m = _INVOKE_MEDIA.search(api)
    return m.group(1) if m else ""


def _heading_keys(blob: str) -> list[str]:
    keys: list[str] = []
    for k in _T_CALL.findall(blob):
        if k not in _KEEP_KEYS and k not in keys:
            keys.append(k)
    return keys


def assert_person_media_gallery(crate: Path) -> None:
    """#361: person Media gallery (IPC + Dialog grid + inspector button)."""
    tl_path = crate / "web" / "lib" / "TimelinePane.svelte"
    if not tl_path.is_file():
        fail(
            f"{_ISSUE}: TimelinePane.svelte required "
            "(quiet Media control lives on the Find / Jump row)"
        )
    tl_raw = tl_path.read_text()
    tl = _without_comments(tl_raw)
    find = _find_jump_block(tl_raw)
    find_c = _without_comments(find) if find else ""

    # 1) gallery-control — primary red today.
    if "data-tl-find" not in tl_raw and "data-tl-find" not in tl:
        fail(
            f"{_ISSUE}: Find / Jump row required "
            "(quiet Media control lives next to Find / Jump when selectedId is set)"
        )
    if not find.strip():
        fail(
            f"{_ISSUE}: Find / Jump row ({{#if selectedId}} + data-tl-find) required "
            "for the quiet Media control"
        )
    if not _GALLERY_OPEN.search(find) and not _GALLERY_OPEN.search(find_c):
        if not _MEDIA_T.search(find) and not _MEDIA_T.search(find_c):
            fail(
                f"{_ISSUE}: Find / Jump row must have a quiet Media control "
                "(data-person-gallery-open) when selectedId is set"
            )

    insp_path = crate / "web" / "lib" / "PeopleInspector.svelte"
    insp_raw = _text(insp_path)
    insp = _without_comments(insp_raw)
    api_path = crate / "web" / "lib" / "api.ts"
    api = _text(api_path)
    web = _without_comments(_web_logic(crate))
    rust = _tauri_rust_blob(crate)
    rust_c = _without_comments(rust)
    root = repo_root()
    core = _people_core_blob(root)
    people_rs = _text(root / "crates" / "interlace-core" / "src" / "people.rs")
    lib_rs = _text(root / "crates" / "interlace-core" / "src" / "lib.rs")
    i18n = _text(crate / "web" / "lib" / "i18n.ts")
    en = _chrome_pack_entries(_text(crate / "web" / "lib" / "locales" / "en.ts"))
    tr = _chrome_pack_entries(_text(crate / "web" / "lib" / "locales" / "tr.ts"))
    dtxt = _text(root / "docs" / "user" / "app.md")
    gal_raw = _gallery_blob(crate)
    gal = _without_comments(gal_raw) if gal_raw else ""
    people_web = "\n".join((tl, insp, gal))
    cas = _text(crate / "web" / "lib" / "CasAttach.svelte")
    cas_video = _text(crate / "web" / "lib" / "CasVideo.svelte")
    search = _text(crate / "web" / "lib" / "SearchPane.svelte")
    tl_list = _text(crate / "web" / "lib" / "TimelineList.svelte")

    # Control must actually open the gallery (same Dialog).
    open_win = find_c + "\n" + _windows_around(tl, _GALLERY_OPEN, 80, 240)
    if not (
        re.search(
            r"galleryOpen|mediaOpen|personGallery|openGallery|openPersonGallery|"
            r"showGallery|PersonMedia",
            open_win,
            re.I,
        )
        or _DIALOG.search(open_win)
        or _GALLERY_GRID.search(tl)
    ):
        fail(
            f"{_ISSUE}: data-person-gallery-open must open the person media gallery"
        )

    # 2) gallery-inspector-btn — same Dialog, not a second grid.
    if not insp_path.is_file():
        fail(f"{_ISSUE}: PeopleInspector.svelte required (inspector Media button)")
    insp_ctrl = _GALLERY_OPEN.search(insp) or _MEDIA_T.search(insp)
    if not insp_ctrl:
        fail(
            f"{_ISSUE}: inspector must have a Media control that opens the "
            "same Dialog (not a second grid)"
        )
    if _GALLERY_GRID.search(insp) and not re.search(
        r"PersonMedia|data-person-gallery-open", insp
    ):
        fail(
            f"{_ISSUE}: inspector Media must open the same Dialog "
            "(do not host a second data-person-gallery grid in the inspector)"
        )

    # 3) gallery-surface — owned Dialog + data-person-gallery grid.
    if not _GALLERY_GRID.search(gal_raw) and not _GALLERY_GRID.search(tl_raw):
        fail(
            f"{_ISSUE}: owned Dialog must host a data-person-gallery grid "
            "(not a blank pane)"
        )
    surface = gal_raw if _GALLERY_GRID.search(gal_raw) else tl_raw
    if not _DIALOG.search(surface) and not _DIALOG.search(gal_raw):
        fail(
            f"{_ISSUE}: gallery is an owned Dialog (same primitive as MergeDialog), "
            "not a second lightbox"
        )

    # 4) gallery-ipc — person_media + api.personMedia; id + includeGroups + cursor.
    qname, qbody = _media_query(core)
    cmd, cmd_body = _media_cmd(rust_c, qname)
    if not cmd:
        fail(
            f"{_ISSUE}: thin person_media command required "
            "(id + includeGroups + optional cursor; no path / URL)"
        )
    if cmd not in _handler_names(rust):
        fail(f"{_ISSUE}: register {cmd} in generate_handler")
    sig = _rust_fn_signature(rust, cmd)
    if _CLIENT_PARAM.search(sig):
        fail(f"{_ISSUE}: {cmd} takes no path / root / URL (hash-only later via casDataUrl)")
    if not re.search(r"\b(?:id|person_id)\b", sig):
        fail(f"{_ISSUE}: {cmd} must take the person id")
    if not re.search(r"\binclude_groups\b", sig):
        fail(f"{_ISSUE}: {cmd} must take include_groups (timeline tick, not Search's)")
    if not re.search(r"\bbefore\b", sig):
        fail(f"{_ISSUE}: {cmd} must take an optional before cursor")
    if not _WITH_ARCH.search(cmd_body):
        fail(f"{_ISSUE}: {cmd} reads via with_arch on the held Exclusive")
    if _OPEN_SECOND.search(cmd_body):
        fail(f"{_ISSUE}: do not open_archive a second Exclusive from {cmd}")
    api_name = _api_media_name(api)
    if not api_name:
        fail(
            f"{_ISSUE}: api.personMedia wrapper required "
            "(id + includeGroups + optional cursor; no path / URL)"
        )
    api_fn = _ts_fn_body(api, api_name) or ""
    api_win = _windows_around(api, re.compile(rf"\b{re.escape(api_name)}\b"), 40, 280)
    if not re.search(r"includeGroups", api_win + "\n" + api_fn):
        fail(f"{_ISSUE}: api.{api_name} must take includeGroups")
    for payload in _invoke_payloads(
        api_win + "\n" + api_fn, re.compile(re.escape(cmd))
    ):
        if _payload_has_path_or_url(payload):
            fail(f"{_ISSUE}: api.{api_name} must not send a path / URL")
    if not re.search(rf"\b{re.escape(api_name)}\b", people_web):
        fail(
            f"{_ISSUE}: timeline / gallery must invoke {api_name} "
            "(person id + includeGroups; not a loaded-row scan)"
        )

    # 5) gallery-core — exported helper; kinds + hash + omit/miss + membership.
    if not qname or not qbody:
        fail(
            f"{_ISSUE}: exported person_media_rows_for required "
            "(same membership SQL as person_timeline_rows_for; "
            "cas_hash IS NOT NULL; omitted=0; missing=0; "
            "image/video/sticker + inline image/* or video/*)"
        )
    if not re.search(rf"\b{re.escape(qname)}\b", people_rs):
        fail(f"{_ISSUE}: export {qname} from people.rs")
    if not re.search(rf"\b{re.escape(qname)}\b", lib_rs):
        fail(f"{_ISSUE}: export {qname} from interlace-core lib.rs")
    if not _CAS_HASH_NOT_NULL.search(qbody):
        fail(f"{_ISSUE}: {qname} must require cas_hash IS NOT NULL")
    if not _OMITTED_ZERO.search(qbody):
        fail(f"{_ISSUE}: {qname} must skip omitted (omitted = 0)")
    if not _MISSING_ZERO.search(qbody):
        fail(f"{_ISSUE}: {qname} must skip missing (missing = 0)")
    if not (
        _KIND_IMAGE.search(qbody)
        and _KIND_VIDEO.search(qbody)
        and _KIND_STICKER.search(qbody)
    ):
        fail(f"{_ISSUE}: {qname} kinds are image / video / sticker")
    if not _KIND_INLINE.search(qbody) or not (
        _MIME_IMAGE.search(qbody) or _MIME_VIDEO.search(qbody)
    ):
        fail(
            f"{_ISSUE}: {qname} must include kind=inline when mime is "
            "image/* or video/*"
        )
    if not _MEMBER_SENDER.search(qbody) or not _MEMBER_PART.search(qbody):
        fail(
            f"{_ISSUE}: {qname} uses the same membership as the timeline "
            "(sender or participant; includes from_me)"
        )
    if not _GROUP_SQL.search(qbody) and not re.search(
        r"include_groups", qbody
    ):
        fail(
            f"{_ISSUE}: {qname} must hide group-chat media when "
            "include_groups=false (same group SQL as the timeline)"
        )
    if _BODY_TOKEN.search(qbody):
        fail(
            f"{_ISSUE}: do not treat <attached: body tokens as a source of truth "
            "(attachments table only)"
        )

    # 6) gallery-sort — newest first.
    if not _SORT_DESC.search(qbody):
        fail(f"{_ISSUE}: gallery sort is newest first (sent_at DESC)")
    if not _SORT_ID.search(qbody):
        fail(f"{_ISSUE}: gallery sort ties on id DESC (sent_at DESC, then id DESC)")

    # 7) gallery-omit-miss — no broken thumbs.
    cell = gal_raw + "\n" + surface
    if re.search(
        r"(?:omitted|missing|voice).{0,160}<img\b|<img\b.{0,160}(?:omitted|missing|voice)",
        cell,
        re.I | re.S,
    ):
        fail(
            f"{_ISSUE}: omitted / missing / NULL hash / voice must not render "
            "as <img> / broken thumbs"
        )

    # 8) gallery-groups — timeline includeGroups, not Search's.
    load_win = "\n".join(
        [
            gal,
            _windows_around(people_web, re.compile(rf"\b{re.escape(api_name)}\b"), 80, 240)
            if api_name
            else "",
            _windows_around(people_web, _INVOKE_MEDIA, 80, 240),
        ]
    )
    if not re.search(r"\bincludeGroups\b", load_win + "\n" + gal):
        fail(
            f"{_ISSUE}: gallery membership follows the timeline includeGroups tick"
        )
    if _SEARCH_PANE.search(gal) or re.search(
        r"SearchPane[\s\S]{0,200}personMedia|personMedia[\s\S]{0,200}SearchPane",
        web,
    ):
        fail(
            f"{_ISSUE}: gallery follows the timeline includeGroups tick, "
            "not Search's"
        )

    # 9) gallery-person-switch — generation token drops thumbs.
    switch_src = gal + "\n" + tl
    if not _GEN_TOKEN.search(switch_src) and not (
        re.search(r"selectedId", gal) and _CLEAR_THUMBS.search(switch_src)
    ):
        fail(
            f"{_ISSUE}: selecting another person must drop thumbs "
            "(generation token; Berk must not see Ada's cells)"
        )
    if not re.search(r"\bselectedId\b", switch_src):
        fail(f"{_ISSUE}: person switch must key the gallery off selectedId")
    if not re.search(r"\bincludeGroups\b", switch_src):
        fail(
            f"{_ISSUE}: include-groups change must drop thumbs and re-query"
        )

    # 10) gallery-lightbox — photo/sticker → #118; no <video>; no http(s).
    click_src = gal_raw + "\n" + surface
    if not _PHOTO_LB.search(click_src) and not re.search(
        r"data-photo-lightbox|openLightbox|CasAttach", click_src
    ):
        fail(
            f"{_ISSUE}: photo / sticker click must open existing "
            "data-photo-lightbox from casDataUrl / data:"
        )
    if _VIDEO_IN_LB.search(click_src) or (
        _PHOTO_LB.search(cas) and re.search(r"<video\b", cas)
        and _LIGHTBOX_VIDEO_CHROME.search(cas)
    ):
        fail(f"{_ISSUE}: do not stuff <video> inside data-photo-lightbox")
    if _HTTP_SRC.search(_without_comments(click_src)):
        fail(f"{_ISSUE}: gallery must not use http(s) src (casDataUrl / data: only)")

    # 11) gallery-video-click — CasVideo overlay, no autoplay.
    if not _VIDEO_OV.search(click_src) and not re.search(
        r"CasVideo|data-cas-video-overlay", click_src
    ):
        fail(
            f"{_ISSUE}: video thumb must open existing #271 CasVideo "
            "(data-cas-video-overlay; no autoplay)"
        )
    if _CAS_VIDEO_AUTOPLAY.search(click_src) or _CAS_VIDEO_AUTOPLAY.search(gal):
        fail(f"{_ISSUE}: gallery video must not autoplay")
    if not _has_cas_video_surface(cas + "\n" + cas_video) and not _VIDEO_OV.search(
        cas_video
    ):
        fail(f"{_ISSUE}: keep #271 data-cas-video-overlay (do not rewrite CasVideo)")

    # 12) gallery-jump — close Dialog, then openPersonAtMessage; miss → showErr.
    if not _SHOW_IN_TL.search(click_src) and not _SHOW_IN_TL.search(gal):
        fail(
            f"{_ISSUE}: quiet Show in timeline required "
            "(closes the Dialog, then openPersonAtMessage)"
        )
    jump_win = _windows_around(gal + "\n" + tl, _SHOW_IN_TL, 80, 400)
    jump_win += "\n" + _windows_around(gal + "\n" + tl, _JUMP_FN, 80, 400)
    if not _JUMP_FN.search(jump_win) and not _JUMP_FN.search(gal + "\n" + tl):
        fail(
            f"{_ISSUE}: Show in timeline must call openPersonAtMessage "
            "with that cell's message_id + sent_at"
        )
    if not re.search(r"message_id", jump_win + "\n" + gal):
        fail(f"{_ISSUE}: Show in timeline passes that cell's message_id")
    if not re.search(r"sent_at", jump_win + "\n" + gal):
        fail(f"{_ISSUE}: Show in timeline passes that cell's sent_at")
    if not re.search(
        r"(?:galleryOpen|mediaOpen|open)\s*=\s*false", jump_win + "\n" + gal, re.I
    ):
        fail(
            f"{_ISSUE}: Show in timeline must close the Dialog, then "
            "openPersonAtMessage (not leave the gallery stacked)"
        )
    if not re.search(r"\btlIndex\b|\bdata-tl-index\b", tl):
        fail(
            f"{_ISSUE}: Show in timeline must ring that message_id "
            "(tlIndex / data-tl-index) — keep #124"
        )
    open_fn = _function_body(tl, "openPersonAtMessage") or _ts_fn_body(
        tl, "openPersonAtMessage"
    )
    if open_fn and not re.search(r"\bshowErr\b", open_fn):
        fail(
            f"{_ISSUE}: miss after bounded load → showErr, not the last loaded row "
            "(keep #124)"
        )

    # 13) gallery-empty — EmptyState + next action.
    if not _EMPTY.search(surface) and not _EMPTY.search(gal_raw):
        fail(
            f"{_ISSUE}: person with no stored media → EmptyState (data-empty) "
            "+ next action, not a blank dialog"
        )
    empty_win = _windows_around(gal_raw + "\n" + surface, _EMPTY, 80, 360)
    if not _INCLUDE_ON.search(empty_win) and not _INCLUDE_ON.search(gal):
        fail(
            f"{_ISSUE}: empty + include-groups off → action turns it on and re-queries"
        )
    if not _IMPORT_ACTION.search(empty_win) and not _IMPORT_ACTION.search(gal):
        fail(
            f"{_ISSUE}: empty + include-groups already on → action goes to Import"
        )

    # 14) gallery-virtualize — after 48 cells, window / spacer.
    if not _VIRT_N.search(gal) and not _VIRT_N.search(gal_raw):
        fail(f"{_ISSUE}: virtualize the gallery after 48 cells")
    if not _VIRT_WINDOW.search(gal) and not _VIRT_WINDOW.search(gal_raw):
        fail(
            f"{_ISSUE}: a large gallery must not mount every cell "
            "(window / spacer after 48)"
        )

    # 15) gallery-locale — new en+tr chrome keys; t() key-only.
    heading = _heading_keys(gal_raw + "\n" + find + "\n" + insp_raw)
    if not heading:
        fail(
            f"{_ISSUE}: new en+tr chrome keys required "
            "(Media / Show in timeline / empty); t() stays key-only"
        )
    extra_en = set(en) - set(tr)
    extra_tr = set(tr) - set(en)
    if extra_en or extra_tr:
        bits: list[str] = []
        if extra_en:
            bits.append("in en only: " + ", ".join(sorted(extra_en)))
        if extra_tr:
            bits.append("in tr only: " + ", ".join(sorted(extra_tr)))
        fail(
            f"{_ISSUE}: same ChromeKey on both en and tr packs — " + "; ".join(bits)
        )
    for hkey in heading:
        if hkey not in en or hkey not in tr:
            fail(
                f"{_ISSUE}: {hkey} must exist on both en.ts and tr.ts "
                "(same ChromeKey — #278)"
            )
        if not (en.get(hkey) or "").strip() or not (tr.get(hkey) or "").strip():
            fail(f"{_ISSUE}: {hkey} must have copy on both packs")
        if (en.get(hkey) or "").strip() == (tr.get(hkey) or "").strip():
            fail(f"{_ISSUE}: tr {hkey} must not be an English copy (#278)")
    if not _T_FN.search(i18n):
        fail(f"{_ISSUE}: t() stays key-only (ChromeKey → string)")
    if _T_NOT_KEY.search(gal) or _T_NOT_KEY.search(find_c):
        fail(
            f"{_ISSUE}: t() stays key-only "
            "(do not t(body_text) / t(filename) / t(name))"
        )
    for pack in (en, tr):
        for val in pack.values():
            if _PLACEHOLDERS.search(val):
                fail(
                    f"{_ISSUE}: placeholder names (Ada, Berk) stay out of the chrome pack"
                )

    # 16) gallery-no-innerhtml — filenames as text nodes.
    if _INNERHTML.search(gal) or _INNERHTML.search(_svelte_markup(gal_raw)):
        fail(
            f"{_ISSUE}: no innerHTML of chat text in the gallery "
            "(filenames as text nodes)"
        )

    # 17) gallery-keep-118-271-124 — do not regress those surfaces.
    if not _LIGHTBOX_HOOK.search(cas):
        fail(f"{_ISSUE}: keep #118 data-photo-lightbox on CasAttach")
    if not _CAS_VIDEO_HOOK.search(cas_video):
        fail(f"{_ISSUE}: keep #271 data-cas-video-overlay on CasVideo")
    if not re.search(r"\bopenPersonAtMessage\b", tl):
        fail(f"{_ISSUE}: keep #124 openPersonAtMessage (Show in timeline reuses it)")
    if re.search(r"<video\b", cas) and _LIGHTBOX_HOOK.search(cas):
        # CasAttach may mount CasVideo as a sibling; <video> inside the
        # photo lightbox hook is the #118 contract.
        lb = _windows_around(cas, _LIGHTBOX_HOOK, 40, 400)
        if re.search(r"<video\b", lb):
            fail(f"{_ISSUE}: keep #118 — no <video> inside data-photo-lightbox")
    if not re.search(r"\bjumpToMessage\b|\bopenPersonAtMessage\b", search + "\n" + web):
        fail(f"{_ISSUE}: keep #124 search-hit jump")

    # 18) gallery-windowed-cas — visible window only; not CasAttach $effect.
    if _GALLERY_GRID.search(tl_list):
        fail(
            f"{_ISSUE}: do not mount the gallery grid inside TimelineList spacers"
        )
    if _CAS_ATTACH.search(gal_raw) and re.search(
        r"\{#each\b[^}]{0,160}\}[\s\S]{0,400}<CasAttach\b", gal_raw
    ):
        fail(
            f"{_ISSUE}: do not reuse CasAttach eager $effect on the whole set "
            "(windowed casDataUrl on visible cells only)"
        )
    if not _CAS_DATA.search(gal) and not _CAS_DATA.search(gal_raw):
        fail(
            f"{_ISSUE}: gallery cells call casDataUrl only for the visible window"
        )

    # 19) gallery-ignore-chips — person + include-groups only.
    if _CHIPS.search(qbody):
        fail(
            f"{_ISSUE}: gallery ignores platform / conversation-kind chips "
            "(person + include-groups only)"
        )
    chip_win = _windows_around(
        gal + "\n" + tl, re.compile(rf"\b{re.escape(api_name)}\b") if api_name else _INVOKE_MEDIA,
        80,
        240,
    )
    if _CHIPS.search(chip_win) and not re.search(
        r"platformFilter\s*=\s*[\"']all[\"']|kindFilter\s*=\s*[\"']all[\"']",
        chip_win,
    ):
        fail(
            f"{_ISSUE}: gallery must not key off platformFilter / kindFilter "
            "(ignore timeline chips)"
        )

    # 20) D24 — person Media gallery in docs/user/app.md.
    if not dtxt.strip():
        fail(
            f"{_ISSUE}: docs/user/app.md required — person Media gallery "
            "(stored CAS image/video/sticker + gmail inline; lightbox; "
            "video overlay no autoplay; Show in timeline; empty next action; "
            "include-groups follows the timeline tick)"
        )
    if not _DOCS_GALLERY.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must describe the person Media gallery"
        )
    if not _DOCS_KINDS.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say stored CAS image/video/sticker"
        )
    if not _DOCS_INLINE.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must mention gmail inline image/video"
        )
    if not _DOCS_PHOTO_LB.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say click photo → existing lightbox"
        )
    if not _DOCS_VIDEO.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say video → existing overlay, no autoplay"
        )
    if not _DOCS_JUMP.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must say Show in timeline jumps")
    if not _DOCS_EMPTY.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must say empty has a next action")
    if not _DOCS_GROUPS.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say include-groups follows the "
            "timeline tick"
        )
