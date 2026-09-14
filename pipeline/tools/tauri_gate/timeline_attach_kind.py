"""#362 — person timeline attach-kind filter (B + A's chrome).

Wired immediately after assert_timeline_kind_filter (#115 / #116 filter
family). Third TimelineFilters row, not the #361 gallery family.

Confirmed mix: optional attach-kind on person_timeline /
person_timeline_rows_for / api.personTimeline. All = omit the arg / no
EXISTS. State name attachKindFilter (not kindFilter). Toolbar:
data-attach-kind-filter, closed All | Photos | Voice | Video | Files.
Platform + conversation-kind stay client AND. Include-groups unchanged.
Gallery unchanged. Load older = one page. Empty next action clears
attachKindFilter to all. Person switch / openPersonAtMessage / Show all
reset it.

Placeholders only (Ada / Berk).
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.scan import (
    _function_body,
    _rust_fn_signature,
    _rust_function_body,
    _svelte_markup,
    _tauri_rust_blob,
    _ts_fn_body,
    _without_comments,
)
from tauri_gate.status_toasts_chrome import (
    _invoke_payloads,
    _payload_has_path_or_url,
    _windows_around,
)

_ISSUE = "#362"

_ATTACH_HOOK = re.compile(r"\bdata-attach-kind-filter\b")
_KIND_HOOK = re.compile(r"\bdata-kind-filter\b")
_PLATFORM_HOOK = re.compile(r"\bdata-platform-filter\b")
_FILTERS_HOOK = re.compile(r"\bdata-timeline-filters\b")
_ATTACH_STATE = re.compile(
    r"\battachKindFilter\s*=\s*\$state\s*(?:<[^>]*>)?\s*\(\s*[\"']all[\"']\s*\)"
    r"|\battachKindFilter\s*=\s*\$bindable\s*\(\s*[\"']all[\"']\s*\)"
)
_KIND_STATE = re.compile(r"\bkindFilter\b")
_PLATFORM_STATE = re.compile(r"\bplatformFilter\b")
_CHIP_PHOTOS = re.compile(r"\bPhotos\b|t\s*\(\s*[\"'][^\"']*[Pp]hotos[^\"']*[\"']\s*\)")
_CHIP_VOICE = re.compile(r"\bVoice\b|t\s*\(\s*[\"'][^\"']*[Vv]oice[^\"']*[\"']\s*\)")
_CHIP_VIDEO = re.compile(r"\bVideo\b|t\s*\(\s*[\"'][^\"']*[Vv]ideo[^\"']*[\"']\s*\)")
_CHIP_FILES = re.compile(r"\bFiles\b|t\s*\(\s*[\"'][^\"']*[Ff]iles[^\"']*[\"']\s*\)")
_CHIP_ALL = re.compile(r">\s*All\s*<|t\s*\(\s*[\"'](?:all|attachKindAll)[\"']\s*\)")
_FILTERED = re.compile(
    r"\bfilteredTimeline\s*=\s*\$derived\s*(?:\.by\s*)?\("
)
_INCLUDE_GROUPS = re.compile(r"\bincludeGroups\b")
_RESET_ALL = re.compile(r"\battachKindFilter\s*=\s*[\"']all[\"']")
_EMPTY = re.compile(r"\bEmptyState\b|\bdata-empty\b")
_INNERHTML = re.compile(r"\binnerHTML\b|\{@html\b")
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][\w]*)["']\s*\)""")
_T_FN = re.compile(r"export\s+function\s+t\s*\(\s*key\s*:\s*ChromeKey\s*\)")
_T_NOT_KEY = re.compile(
    r"""\bt\s*\(\s*(?:[\w$.]*\b(?:display_name|displayName|value|name|body_text|filename)\b)"""
)
_PLACEHOLDERS = re.compile(r"\bAda\b|\bBerk\b")
_GALLERY_OPEN = re.compile(r"\bdata-person-gallery-open\b")
_GALLERY_GRID = re.compile(r"\bdata-person-gallery(?!-)")
_HANDLER = re.compile(r"generate_handler!\s*\[(.*?)\]", re.S)
_CLIENT_PARAM = re.compile(
    r"\b(?:path|url|file|href|uri|dest|source|root)\s*:",
    re.I,
)
_CAS_HASH_NOT_NULL = re.compile(r"cas_hash\s+IS\s+NOT\s+NULL", re.I)
_OMITTED_ZERO = re.compile(r"omitted\s*(?:=|==|<>|!=)\s*0", re.I)
_MISSING_ZERO = re.compile(r"missing\s*(?:=|==|<>|!=)\s*0", re.I)
_AUTO_PREPEND = re.compile(
    r"while\s*\([^)]{0,200}attachKindFilter"
    r"|for\s*\([^)]{0,80}attachKindFilter[^)]{0,80}\)"
    r"|attachKindFilter\s*!==?\s*[\"']all[\"'][\s\S]{0,240}"
    r"selectPerson\s*\([^)]*true",
    re.I,
)
_KEEP_KEYS = frozenset(
    {
        "findInThread",
        "jumpToDay",
        "media",
        "inspector",
        "identities",
        "lastActivity",
        "inThisGroup",
        "includeGroups",
        "import",
        "retry",
        "showAll",
        "people",
    }
)
_DOCS_CHIPS = re.compile(
    r"All.{0,20}Photos.{0,20}Voice.{0,20}Video.{0,20}Files",
    re.I | re.S,
)
_DOCS_AND = re.compile(
    r"(?:AND|and).{0,40}(?:platform|kind)|(?:platform|kind).{0,40}(?:AND|and)",
    re.I | re.S,
)
_DOCS_DEFAULT = re.compile(r"\bAll\b.{0,40}default|default.{0,40}\bAll\b", re.I)
_DOCS_RESET = re.compile(
    r"(?:switch(?:ing)? (?:people|person)|person switch).{0,60}reset"
    r"|reset.{0,60}(?:switch(?:ing)? (?:people|person)|person switch)",
    re.I | re.S,
)
_DOCS_EMPTY = re.compile(
    r"(?:empty|no video).{0,80}(?:clear|Show all|show all)",
    re.I | re.S,
)
_DOCS_TIMELINE = re.compile(
    r"(?:person timeline|timeline).{0,80}(?:Photos|attach(?:ment)?[- ]kind|media[- ]kind)"
    r"|(?:Photos|attach(?:ment)?[- ]kind|media[- ]kind).{0,80}(?:person timeline|timeline)",
    re.I | re.S,
)


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


def _attach_toolbar_block(filters: str) -> str:
    m = _ATTACH_HOOK.search(filters)
    if not m:
        return ""
    start = filters.rfind("<", 0, m.start())
    if start < 0:
        start = m.start()
    return filters[start : m.end() + 900]


def _heading_keys(blob: str) -> list[str]:
    keys: list[str] = []
    for k in _T_CALL.findall(blob):
        if k not in _KEEP_KEYS and k not in keys:
            keys.append(k)
    return keys


def assert_timeline_attach_kind(crate: Path) -> None:
    """#362: attach-kind toolbar + optional person_timeline arg (mix B + A chrome)."""
    filters_path = crate / "web" / "lib" / "TimelineFilters.svelte"
    pane_path = crate / "web" / "lib" / "TimelinePane.svelte"
    empty_path = crate / "web" / "lib" / "TimelineEmpty.svelte"
    if not filters_path.is_file() or not pane_path.is_file():
        fail(f"{_ISSUE}: toolbar missing")

    filters_raw = filters_path.read_text()
    pane_raw = pane_path.read_text()
    empty_raw = _text(empty_path)
    filters = _without_comments(filters_raw)
    pane = _without_comments(pane_raw)
    empty = _without_comments(empty_raw)
    toolbar = _attach_toolbar_block(filters_raw)
    toolbar_c = _without_comments(toolbar) if toolbar else ""

    # 1) media-kind-toolbar — first red today.
    if not _ATTACH_HOOK.search(filters_raw) and not _ATTACH_HOOK.search(filters):
        fail(f"{_ISSUE}: toolbar missing")
    if not _FILTERS_HOOK.search(filters_raw):
        fail(
            f"{_ISSUE}: data-attach-kind-filter must live in TimelineFilters "
            "(data-timeline-filters third row), not the Find / Jump row"
        )
    if _ATTACH_HOOK.search(filters_raw) and not re.search(
        r"data-timeline-filters[\s\S]{0,4000}data-attach-kind-filter",
        filters_raw,
    ):
        fail(
            f"{_ISSUE}: data-attach-kind-filter must be a third row inside "
            "data-timeline-filters"
        )
    if not _ATTACH_STATE.search(pane) and not _ATTACH_STATE.search(filters):
        fail(
            f"{_ISSUE}: attachKindFilter must default to All "
            '($state("all") / $bindable("all") — do not reuse kindFilter)'
        )
    if re.search(
        r"\bkindFilter\s*=\s*[\"'](?:photos|voice|video|files)[\"']",
        pane + "\n" + filters,
        re.I,
    ):
        fail(
            f"{_ISSUE}: do not reuse kindFilter for attachment kind "
            "(that name is conversation kind)"
        )
    if _KIND_HOOK.search(toolbar_c) or (
        _ATTACH_HOOK.search(filters_raw) and not _KIND_HOOK.search(filters_raw)
    ):
        fail(
            f"{_ISSUE}: do not reuse data-kind-filter for Photos | Voice | "
            "Video | Files (keep conversation-kind on data-kind-filter)"
        )
    chip_src = toolbar_c if toolbar_c.strip() else filters
    if not (
        _CHIP_PHOTOS.search(chip_src)
        and _CHIP_VOICE.search(chip_src)
        and _CHIP_VIDEO.search(chip_src)
        and _CHIP_FILES.search(chip_src)
    ):
        fail(
            f"{_ISSUE}: closed chips All | Photos | Voice | Video | Files "
            "required on data-attach-kind-filter"
        )
    if not _CHIP_ALL.search(chip_src) and not re.search(
        r"attachKindFilter\s*=\s*[\"']all[\"']", chip_src
    ):
        fail(f"{_ISSUE}: attach-kind toolbar must offer All (default)")
    if "selectedId" in pane_raw and not re.search(
        r"<TimelineFilters\b", pane_raw
    ):
        fail(f"{_ISSUE}: attach-kind toolbar is shown when a person is selected")

    # 2) media-kind-and — attach-kind ANDs with platform + conversation_kind.
    filt_body = ""
    fm = _FILTERED.search(pane)
    if fm:
        filt_body = pane[fm.start() : fm.end() + 500]
    and_src = filt_body if filt_body.strip() else pane
    if not re.search(r"\battachKindFilter\b", and_src):
        fail(
            f"{_ISSUE}: filteredTimeline must AND attachKindFilter with "
            "platformFilter and kindFilter"
        )
    if not re.search(r"\bplatformFilter\b", and_src) or not re.search(
        r"\bkindFilter\b", and_src
    ):
        fail(
            f"{_ISSUE}: attach-kind ANDs with platform + conversation-kind "
            "(do not replace those chips)"
        )
    if not _INCLUDE_GROUPS.search(pane):
        fail(f"{_ISSUE}: include-groups must still gate group rows")
    if re.search(
        r"attachKindFilter\s*===?\s*[\"'](?:photos|voice|video|files)[\"']"
        r"[^;{]{0,200}includeGroups\s*=\s*(?:true|!0|1)\b",
        pane,
        re.I | re.S,
    ):
        fail(
            f"{_ISSUE}: attach-kind must not force includeGroups=true "
            "(groups still need the tick)"
        )

    # 3) media-kind-reset — person switch / openPersonAtMessage / Show all.
    select_fn = _function_body(pane, "selectPerson") or _ts_fn_body(
        pane, "selectPerson"
    )
    open_fn = _function_body(pane, "openPersonAtMessage") or _ts_fn_body(
        pane, "openPersonAtMessage"
    )
    show_win = _windows_around(
        pane_raw + "\n" + pane, re.compile(r"\bonShowAll\b"), 40, 280
    )
    if not select_fn or not _RESET_ALL.search(select_fn):
        fail(
            f"{_ISSUE}: switching people must set attachKindFilter to all "
            "(selectPerson when !append && id !== selectedId)"
        )
    if not open_fn or not _RESET_ALL.search(open_fn):
        fail(
            f"{_ISSUE}: openPersonAtMessage must set attachKindFilter to all"
        )
    if not _RESET_ALL.search(show_win) and not _RESET_ALL.search(empty):
        fail(
            f"{_ISSUE}: Show all / empty next action must set "
            "attachKindFilter to all"
        )

    # 4) media-kind-empty-clear — no videos + Video → data-empty + clear.
    empty_src = empty_raw + "\n" + empty + "\n" + pane
    if not _EMPTY.search(empty_src):
        fail(
            f"{_ISSUE}: Ada with no videos + Video must show data-empty "
            "(not a blank pane, not Skeleton-forever)"
        )
    if not re.search(r"\battachKindFilter\b", empty) and not re.search(
        r"attachKindFilter", show_win
    ):
        fail(
            f"{_ISSUE}: empty + Video must clear attachKindFilter "
            "(not only platformFilter / kindFilter; mix B SQL empty is "
            "still a filter-empty, not Import-only)"
        )
    if re.search(
        r"tlLoading\s*&&\s*!tlAppending[\s\S]{0,200}Skeleton"
        r"|Skeleton[\s\S]{0,200}attachKindFilter",
        empty_src,
    ) and not re.search(
        r"filteredTimeline\.length\s*===?\s*0[\s\S]{0,200}(?:EmptyState|data-empty)",
        empty_src,
    ):
        fail(
            f"{_ISSUE}: no videos + Video is EmptyState + clear, "
            "not a stuck spinner / Skeleton-forever"
        )

    # 5) media-kind-filtered-walk — virtualizer / Load older / jump / find / j/k.
    root = repo_root()
    tl_list = _text(crate / "web" / "lib" / "TimelineList.svelte")
    jump = _text(crate / "web" / "lib" / "jumpDay.ts")
    find = _text(crate / "web" / "lib" / "findHighlight.ts")
    keys = _text(crate / "web" / "lib" / "PeopleKeys.ts")
    if not re.search(r"\bfilteredTimeline\b", tl_list):
        fail(
            f"{_ISSUE}: virtualizer / Load older must walk filteredTimeline "
            "(attach-filtered set)"
        )
    if not re.search(
        r"filteredTimeline\.length\s*>\s*0", tl_list
    ) and not re.search(r"showLoadOlder", tl_list):
        fail(
            f"{_ISSUE}: Load older stays hidden when the filtered list is empty"
        )
    if not re.search(r"\bfilteredTimeline\b", jump):
        fail(f"{_ISSUE}: day jump must walk filteredTimeline")
    if not re.search(r"\bfilteredTimeline\b", find):
        fail(f"{_ISSUE}: in-thread find must walk filteredTimeline")
    if not re.search(r"\bvisibleTlIndices\b", keys + "\n" + pane):
        fail(f"{_ISSUE}: j/k must walk visibleTlIndices from filteredTimeline")
    if _AUTO_PREPEND.search(pane):
        fail(
            f"{_ISSUE}: Load older is one page (today) — do not auto-prepend "
            "until N attach-kind matches"
        )

    # 6) media-kind-ipc — optional attach-kind; All omits; no path/url.
    rust = _tauri_rust_blob(crate)
    rust_c = _without_comments(rust)
    api = _text(crate / "web" / "lib" / "api.ts")
    core = _people_core_blob(root)
    cmd = "person_timeline"
    if cmd not in _handler_names(rust):
        fail(f"{_ISSUE}: keep person_timeline in generate_handler")
    sig = _rust_fn_signature(rust, cmd)
    if not re.search(r"\battach_kind\b|\battachKind\b", sig):
        fail(
            f"{_ISSUE}: person_timeline must take optional attach-kind "
            "(All omits the arg / no EXISTS)"
        )
    if _CLIENT_PARAM.search(sig):
        fail(f"{_ISSUE}: person_timeline takes no path / root / URL")
    core_sig = _rust_fn_signature(core, "person_timeline_rows_for")
    if not re.search(r"\battach_kind\b", core_sig):
        fail(
            f"{_ISSUE}: person_timeline_rows_for must take optional attach-kind "
            "(All = omit / no EXISTS; membership SQL unchanged)"
        )
    api_fn = _ts_fn_body(api, "personTimeline") or ""
    api_win = _windows_around(api, re.compile(r"\bpersonTimeline\b"), 40, 320)
    if not re.search(r"\battachKind\b|\battach_kind\b", api_win + "\n" + api_fn):
        fail(
            f"{_ISSUE}: api.personTimeline must take optional attachKind "
            "(All omits)"
        )
    for payload in _invoke_payloads(
        api_win + "\n" + api_fn, re.compile(r"person_timeline")
    ):
        if _payload_has_path_or_url(payload):
            fail(f"{_ISSUE}: api.personTimeline must not send a path / URL")
    call_win = "\n".join(
        [
            _windows_around(pane, re.compile(r"\bpersonTimeline\b"), 40, 280),
            select_fn or "",
            open_fn or "",
        ]
    )
    if not re.search(r"\battachKind\b|\battach_kind\b", call_win):
        fail(
            f"{_ISSUE}: selectPerson / Load older / openPersonAtMessage must "
            "pass the current attach-kind (All omits)"
        )
    if not re.search(
        r"attachKindFilter\s*===?\s*[\"']all[\"']"
        r"|attachKindFilter\s*!==?\s*[\"']all[\"']"
        r"|attachKind\s*:\s*attachKindFilter",
        call_win,
    ):
        fail(
            f"{_ISSUE}: All omits attach-kind on personTimeline "
            "(do not send Photos/Voice/… when the chip is All)"
        )

    # 7) media-kind-gallery-untouched.
    gal_path = crate / "web" / "lib" / "PersonMediaDialog.svelte"
    gal_raw = _text(gal_path)
    gal = _without_comments(gal_raw)
    media_sig = _rust_fn_signature(rust, "person_media")
    media_q = _rust_function_body(core, "person_media_rows_for")
    if re.search(r"\battachKindFilter\b", gal):
        fail(
            f"{_ISSUE}: PersonMediaDialog must ignore attachKindFilter "
            "(gallery still ignores timeline chips)"
        )
    if re.search(r"\battach_kind\b|\battachKind\b", media_sig):
        fail(
            f"{_ISSUE}: person_media must not take attach-kind "
            "(gallery membership unchanged)"
        )
    if media_q:
        if not _CAS_HASH_NOT_NULL.search(media_q):
            fail(
                f"{_ISSUE}: do not change person_media_rows_for membership "
                "(cas_hash IS NOT NULL stays)"
            )
        if not _OMITTED_ZERO.search(media_q) or not _MISSING_ZERO.search(media_q):
            fail(
                f"{_ISSUE}: do not change person_media_rows_for membership "
                "(omitted=0 / missing=0 stay)"
            )
    api_media = _windows_around(api, re.compile(r"\bpersonMedia\b"), 40, 240)
    if re.search(r"\battachKind\b|\battach_kind\b", api_media):
        fail(f"{_ISSUE}: api.personMedia must not grow an attach-kind arg")

    # 8) media-kind-locale — new keys both packs; tr not English; t() key-only.
    i18n = _text(crate / "web" / "lib" / "i18n.ts")
    en = _chrome_pack_entries(_text(crate / "web" / "lib" / "locales" / "en.ts"))
    tr = _chrome_pack_entries(_text(crate / "web" / "lib" / "locales" / "tr.ts"))
    heading = _heading_keys(toolbar + "\n" + empty_raw + "\n" + filters_raw)
    if not heading:
        fail(
            f"{_ISSUE}: new en+tr chrome keys required "
            "(Photos / Voice / Video / Files / empty); t() stays key-only"
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
            f"{_ISSUE}: same ChromeKey on both en and tr packs — "
            + "; ".join(bits)
        )
    for hkey in heading:
        if hkey not in en or hkey not in tr:
            fail(
                f"{_ISSUE}: {hkey} must exist on both en.ts and tr.ts "
                "(same ChromeKey)"
            )
        if not (en.get(hkey) or "").strip() or not (tr.get(hkey) or "").strip():
            fail(f"{_ISSUE}: {hkey} must have copy on both packs")
        if (en.get(hkey) or "").strip() == (tr.get(hkey) or "").strip():
            fail(f"{_ISSUE}: tr {hkey} must not be an English copy")
    if not _T_FN.search(i18n):
        fail(f"{_ISSUE}: t() stays key-only (ChromeKey → string)")
    if _T_NOT_KEY.search(toolbar_c) or _T_NOT_KEY.search(empty):
        fail(
            f"{_ISSUE}: t() stays key-only "
            "(do not t(body_text) / t(filename) / t(name))"
        )
    for pack in (en, tr):
        for val in pack.values():
            if _PLACEHOLDERS.search(val):
                fail(
                    f"{_ISSUE}: placeholder names (Ada, Berk) stay out of "
                    "the chrome pack"
                )

    # 9) media-kind-no-innerhtml — chip labels / empty as text nodes.
    if _INNERHTML.search(toolbar_c) or _INNERHTML.search(
        _svelte_markup(filters_raw)
    ):
        fail(
            f"{_ISSUE}: chip labels are text nodes "
            "(no innerHTML of chat text)"
        )
    if _INNERHTML.search(empty) or _INNERHTML.search(_svelte_markup(empty_raw)):
        fail(
            f"{_ISSUE}: empty copy is a text node "
            "(no innerHTML of chat text)"
        )

    # 10) media-kind-keep-115-116-361.
    if not _PLATFORM_HOOK.search(filters_raw) or not _KIND_HOOK.search(
        filters_raw
    ):
        fail(
            f"{_ISSUE}: keep #115 / #116 data-platform-filter and "
            "data-kind-filter"
        )
    if not _PLATFORM_STATE.search(pane) or not _KIND_STATE.search(pane):
        fail(f"{_ISSUE}: keep platformFilter + kindFilter (conversation kind)")
    if not _GALLERY_OPEN.search(pane_raw):
        fail(f"{_ISSUE}: keep #361 data-person-gallery-open")
    if not gal_path.is_file() or not _GALLERY_GRID.search(gal_raw):
        fail(f"{_ISSUE}: keep #361 PersonMediaDialog / data-person-gallery")

    # 11) D24 docs/user/app.md.
    dtxt = _text(root / "docs" / "user" / "app.md")
    if not dtxt.strip():
        fail(
            f"{_ISSUE}: docs/user/app.md required — All | Photos | Voice | "
            "Video | Files on the person timeline"
        )
    if not _DOCS_CHIPS.search(dtxt) or not _DOCS_TIMELINE.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say All | Photos | Voice | "
            "Video | Files on the person timeline"
        )
    if not _DOCS_AND.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say attach-kind ANDs with "
            "platform / kind"
        )
    if not _DOCS_DEFAULT.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must say All is the default")
    if not _DOCS_RESET.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say switching people resets "
            "the attach-kind filter"
        )
    if not _DOCS_EMPTY.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say empty + clear "
            "(no videos + Video is not a stuck spinner)"
        )
