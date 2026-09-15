"""#363 — person timeline from-me / from-them filter (mix A + fourth row).

Wired immediately after assert_timeline_attach_kind_fold (#362 attach-kind
family). Fourth TimelineFilters row, not the Find / Jump row.

Confirmed mix: client fromMeFilter ($state("all"); values all / them / me).
Do not reuse kindFilter / attachKindFilter / invent senderFilter. Fourth
row data-from-me-filter: All | Them | Me. Me = from_me === true (still
right). Them = from_me === false (only left). All = both. AND with
platform + conversation-kind + attach-kind. No new IPC / person_timeline
from_me arg. Include-groups and gallery unchanged. Load older = one page.
Caption grouping stays isGroupedFollower (filtered previous). Empty +
Show all clears sender and the other chips. Person switch /
openPersonAtMessage / Show all reset fromMeFilter to All. Do not invent
is_self. Do not edit stored sender.

Placeholders only (Ada / Berk).
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.scan import (
    _function_body,
    _match_closer,
    _rust_fn_signature,
    _svelte_markup,
    _tauri_rust_blob,
    _ts_fn_body,
    _without_comments,
)
from tauri_gate.status_toasts_chrome import _windows_around

_ISSUE = "#363"

_FROM_ME_HOOK = re.compile(r"\bdata-from-me-filter\b")
_KIND_HOOK = re.compile(r"\bdata-kind-filter\b")
_PLATFORM_HOOK = re.compile(r"\bdata-platform-filter\b")
_ATTACH_HOOK = re.compile(r"\bdata-attach-kind-filter\b")
_FILTERS_HOOK = re.compile(r"\bdata-timeline-filters\b")
_FIND_HOOK = re.compile(r"\bdata-tl-find\b")
_FROM_ME_STATE = re.compile(
    r"\bfromMeFilter\s*=\s*\$state\s*(?:<[^>]*>)?\s*\(\s*[\"']all[\"']\s*\)"
    r"|\bfromMeFilter\s*=\s*\$bindable\s*\(\s*[\"']all[\"']\s*\)"
)
_SENDER_STATE = re.compile(r"\bsenderFilter\b")
_KIND_STATE = re.compile(r"\bkindFilter\b")
_PLATFORM_STATE = re.compile(r"\bplatformFilter\b")
_ATTACH_STATE = re.compile(r"\battachKindFilter\b")
_CHIP_THEM = re.compile(
    r">\s*Them\s*<|t\s*\(\s*[\"'][^\"']*[Tt]hem[^\"']*[\"']\s*\)"
)
_CHIP_ME = re.compile(
    r">\s*Me\s*<|t\s*\(\s*[\"'][^\"']*[Mm]e[\"']\s*\)"
)
_CHIP_ALL = re.compile(
    r">\s*All\s*<|t\s*\(\s*[\"'](?:all|fromMeAll|attachKindAll)[\"']\s*\)"
)
_VAL_THEM = re.compile(r"[\"']them[\"']")
_VAL_ME = re.compile(r"[\"']me[\"']")
_FILTERED = re.compile(r"\bfilteredTimeline\s*=\s*\$derived\s*(?:\.by\s*)?\(")
_INCLUDE_GROUPS = re.compile(r"\bincludeGroups\b")
_RESET_ALL = re.compile(r"\bfromMeFilter\s*=\s*[\"']all[\"']")
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
_IS_SELF = re.compile(r"\bis_self\b")
_SENDER_ID = re.compile(r"\bsender_identity_id\b")
_IPC_FROM_ME = re.compile(r"\b(?:from_me|fromMe|from_me_filter)\s*:")
_GROUP_HELPER = re.compile(r"\bisGroupedFollower\b")
_AUTO_PREPEND = re.compile(
    r"while\s*\([^)]{0,200}fromMeFilter"
    r"|for\s*\([^)]{0,80}fromMeFilter[^)]{0,80}\)"
    r"|fromMeFilter\s*!==?\s*[\"']all[\"'][\s\S]{0,240}"
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
        "attachKind",
        "attachKindAll",
        "attachKindPhotos",
        "attachKindVoice",
        "attachKindVideo",
        "attachKindFiles",
    }
)
_DOCS_CHIPS = re.compile(r"All.{0,20}Them.{0,20}Me", re.I | re.S)
_DOCS_AND = re.compile(
    r"(?:AND|and).{0,60}(?:platform|kind|attach)"
    r"|(?:platform|kind|attach).{0,60}(?:AND|and)",
    re.I | re.S,
)
_DOCS_DEFAULT = re.compile(r"\bAll\b.{0,40}default|default.{0,40}\bAll\b", re.I)
_DOCS_RESET = re.compile(
    r"(?:switch(?:ing)? (?:people|person)|person switch).{0,60}reset"
    r"|reset.{0,60}(?:switch(?:ing)? (?:people|person)|person switch)",
    re.I | re.S,
)
_DOCS_EMPTY = re.compile(
    r"(?:Them|sender|from-me|from me).{0,80}(?:empty|Show all|show all|clear)"
    r"|(?:empty|Show all|show all|clear).{0,80}(?:Them|sender|from-me|from me)",
    re.I | re.S,
)
_DOCS_GROUP = re.compile(
    r"(?:filtered|visible).{0,50}(?:caption|group)"
    r"|(?:caption|group).{0,50}(?:filtered|visible set|filtered set)",
    re.I | re.S,
)
_DOCS_TIMELINE = re.compile(
    r"(?:person timeline|timeline).{0,80}(?:Them|from-me|from me|sender)"
    r"|(?:Them|from-me|from me|All \| Them \| Me).{0,80}(?:person timeline|timeline)",
    re.I | re.S,
)


def _text(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _from_me_toolbar_block(filters: str) -> str:
    m = _FROM_ME_HOOK.search(filters)
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


def _ts_type_body(src: str, name: str) -> str:
    m = re.search(rf"export\s+type\s+{re.escape(name)}\s*=\s*\{{", src)
    if not m:
        return ""
    start = src.find("{", m.start())
    if start < 0:
        return ""
    end = _match_closer(src, start)
    if end < 0:
        return src[start:]
    return src[start : end + 1]


def _filter_and_src(pane: str, mail: str) -> str:
    filt_body = ""
    fm = _FILTERED.search(pane)
    if fm:
        filt_body = pane[fm.start() : fm.end() + 700]
    and_src = filt_body if filt_body.strip() else pane
    helper_names = re.findall(
        r"\b(rowMatchesFromMe|matchesFromMe|fromMeMatch)\b", and_src
    )
    extra: list[str] = []
    for name in helper_names:
        extra.append(_function_body(mail, name) or _ts_fn_body(mail, name) or "")
        extra.append(_function_body(pane, name) or _ts_fn_body(pane, name) or "")
    return and_src + "\n" + "\n".join(extra)


def _chrome_files(crate: Path) -> dict[str, str]:
    lib = crate / "web" / "lib"
    names = (
        "TimelinePane.svelte",
        "TimelineFilters.svelte",
        "TimelineEmpty.svelte",
        "TimelineRows.svelte",
        "TimelineList.svelte",
        "TimelineMail.ts",
    )
    return {n: _text(lib / n) for n in names}


def assert_timeline_from_me(crate: Path) -> None:
    """#363: All | Them | Me toolbar + client from_me AND (mix A)."""
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
    toolbar = _from_me_toolbar_block(filters_raw)
    toolbar_c = _without_comments(toolbar) if toolbar else ""
    mail = _without_comments(_text(crate / "web" / "lib" / "TimelineMail.ts"))
    rows_raw = _text(crate / "web" / "lib" / "TimelineRows.svelte")
    rows = _without_comments(rows_raw)
    chrome = _chrome_files(crate)

    # 1) from-me-toolbar — first red today.
    if not _FROM_ME_HOOK.search(filters_raw) and not _FROM_ME_HOOK.search(filters):
        fail(f"{_ISSUE}: toolbar missing")
    if not _FILTERS_HOOK.search(filters_raw):
        fail(
            f"{_ISSUE}: data-from-me-filter must live in TimelineFilters "
            "(data-timeline-filters fourth row), not the Find / Jump row"
        )
    if _FROM_ME_HOOK.search(filters_raw) and not re.search(
        r"data-timeline-filters[\s\S]{0,8000}data-from-me-filter",
        filters_raw,
    ):
        fail(
            f"{_ISSUE}: data-from-me-filter must be a fourth row inside "
            "data-timeline-filters"
        )
    find_win = _windows_around(pane_raw, _FIND_HOOK, 80, 500)
    if _FROM_ME_HOOK.search(find_win):
        fail(
            f"{_ISSUE}: data-from-me-filter must not live on the Find / Jump "
            "row (keep it inside data-timeline-filters)"
        )
    if not _FROM_ME_STATE.search(pane) and not _FROM_ME_STATE.search(filters):
        fail(
            f"{_ISSUE}: fromMeFilter must default to All "
            '($state("all") / $bindable("all") — do not reuse kindFilter / '
            "attachKindFilter / senderFilter)"
        )
    if _SENDER_STATE.search(pane) or _SENDER_STATE.search(filters):
        fail(
            f"{_ISSUE}: state name is fromMeFilter "
            "(do not invent senderFilter)"
        )
    if re.search(
        r"\b(?:kindFilter|attachKindFilter)\s*=\s*[\"'](?:me|them)[\"']",
        pane + "\n" + filters,
        re.I,
    ):
        fail(
            f"{_ISSUE}: do not reuse kindFilter / attachKindFilter for "
            "All | Them | Me (those names are conversation kind / attach-kind)"
        )
    if _KIND_HOOK.search(toolbar_c) or _ATTACH_HOOK.search(toolbar_c):
        fail(
            f"{_ISSUE}: do not reuse data-kind-filter / data-attach-kind-filter "
            "for All | Them | Me (keep those rows)"
        )
    chip_src = toolbar_c if toolbar_c.strip() else filters
    if not _CHIP_THEM.search(chip_src) or not _CHIP_ME.search(chip_src):
        fail(
            f"{_ISSUE}: closed chips All | Them | Me required on "
            "data-from-me-filter"
        )
    if not _CHIP_ALL.search(chip_src) and not re.search(
        r"fromMeFilter\s*=\s*[\"']all[\"']", chip_src
    ):
        fail(f"{_ISSUE}: from-me toolbar must offer All (default)")
    if not _VAL_THEM.search(chip_src + "\n" + pane + "\n" + filters):
        fail(f"{_ISSUE}: fromMeFilter values are all / them / me (Them chip)")
    if not _VAL_ME.search(chip_src + "\n" + filters):
        fail(f"{_ISSUE}: fromMeFilter values are all / them / me (Me chip)")
    if "selectedId" in pane_raw and not re.search(r"<TimelineFilters\b", pane_raw):
        fail(f"{_ISSUE}: from-me toolbar is shown when a person is selected")

    # 2) from-me-and — from_me ANDs with platform + conversation_kind + attach-kind.
    and_src = _filter_and_src(pane, mail)
    if not re.search(r"\bfromMeFilter\b", and_src):
        fail(
            f"{_ISSUE}: filteredTimeline must AND fromMeFilter with "
            "platformFilter, kindFilter, and attachKindFilter"
        )
    if not re.search(r"\bplatformFilter\b", and_src) or not re.search(
        r"\bkindFilter\b", and_src
    ):
        fail(
            f"{_ISSUE}: from-me ANDs with platform + conversation-kind "
            "(do not replace those chips)"
        )
    if not re.search(r"\battachKindFilter\b", and_src):
        fail(
            f"{_ISSUE}: from-me ANDs with attach-kind "
            "(do not replace the #362 chip)"
        )
    if not re.search(r"\bfrom_me\b", and_src):
        fail(
            f"{_ISSUE}: Me is from_me === true; Them is from_me === false "
            "(do not invent is_self)"
        )
    if re.search(
        r"fromMeFilter\s*===?\s*[\"']me[\"'][\s\S]{0,160}!\s*(?:item\.)?row\.from_me"
        r"|fromMeFilter\s*===?\s*[\"']them[\"'][\s\S]{0,160}(?:item\.)?row\.from_me\s*===?\s*true",
        and_src,
    ):
        fail(
            f"{_ISSUE}: Me keeps from_me === true; Them keeps from_me === false "
            "(do not flip sides)"
        )
    if _IS_SELF.search(and_src):
        fail(f"{_ISSUE}: do not invent is_self as the from-me predicate")
    if not _INCLUDE_GROUPS.search(pane):
        fail(f"{_ISSUE}: include-groups must still gate group rows")
    if re.search(
        r"fromMeFilter\s*===?\s*[\"'](?:me|them)[\"']"
        r"[^;{]{0,200}includeGroups\s*=\s*(?:true|!0|1)\b",
        pane,
        re.I | re.S,
    ):
        fail(
            f"{_ISSUE}: from-me must not force includeGroups=true "
            "(groups still need the tick)"
        )

    # 3) from-me-reset — person switch / openPersonAtMessage / Show all.
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
            f"{_ISSUE}: switching people must set fromMeFilter to all "
            "(selectPerson when !append && id !== selectedId)"
        )
    if not open_fn or not _RESET_ALL.search(open_fn):
        fail(f"{_ISSUE}: openPersonAtMessage must set fromMeFilter to all")
    if not _RESET_ALL.search(show_win) and not _RESET_ALL.search(empty):
        fail(
            f"{_ISSUE}: Show all / empty next action must set "
            "fromMeFilter to all"
        )

    # 4) from-me-empty-clear — Them + empty → data-empty + Show all.
    empty_src = empty_raw + "\n" + empty + "\n" + pane
    if not _EMPTY.search(empty_src):
        fail(
            f"{_ISSUE}: Them + empty must show data-empty "
            "(not a blank pane, not Skeleton-forever)"
        )
    if not re.search(r"\bfromMeFilter\b", empty):
        fail(
            f"{_ISSUE}: fromMeFilter must be in filterEmpty / TimelineEmpty "
            "(Them + empty is a filter-empty, not Import-only)"
        )
    if not re.search(
        r"fromMeFilter\s*!==?\s*[\"']all[\"']",
        empty,
    ):
        fail(
            f"{_ISSUE}: filterEmpty must treat fromMeFilter !== \"all\" as "
            "filter-empty (Show all clears sender)"
        )
    if not _RESET_ALL.search(show_win):
        fail(
            f"{_ISSUE}: Show all must clear fromMeFilter "
            "(sender + the other chips)"
        )
    if re.search(
        r"tlLoading\s*&&\s*!tlAppending[\s\S]{0,200}Skeleton"
        r"|Skeleton[\s\S]{0,200}fromMeFilter",
        empty_src,
    ) and not re.search(
        r"filteredTimeline\.length\s*===?\s*0[\s\S]{0,200}(?:EmptyState|data-empty)",
        empty_src,
    ):
        fail(
            f"{_ISSUE}: Them + empty is EmptyState + Show all, "
            "not a stuck spinner / Skeleton-forever"
        )

    # 5) from-me-align — Me still from_me / right; Them still !from_me / left.
    if not re.search(r"class:bubble-me\s*=\s*\{[^}]*row\.from_me", rows):
        fail(
            f"{_ISSUE}: Me rows stay bubble-me / right via row.from_me "
            "(do not flip sides)"
        )
    if not re.search(
        r"class:bubble-them\s*=\s*\{!?(?:[^}]*row\.from_me|item\.row\.from_me)",
        rows,
    ):
        fail(
            f"{_ISSUE}: Them rows stay bubble-them / left via !row.from_me "
            "(do not flip sides)"
        )
    if not re.search(r"data-from-me\s*=\s*\{[^}]*row\.from_me", rows):
        fail(f"{_ISSUE}: Me still data-from-me from row.from_me")
    if re.search(r"\bfromMeFilter\b", rows) or _IS_SELF.search(rows):
        fail(
            f"{_ISSUE}: alignment stays row.from_me "
            "(do not bind sides to fromMeFilter / is_self)"
        )

    # 6) from-me-grouping — isGroupedFollower on the filtered previous.
    group_fn = _function_body(mail, "isGroupedFollower") or _ts_fn_body(
        mail, "isGroupedFollower"
    )
    if not group_fn or not _GROUP_HELPER.search(mail):
        fail(
            f"{_ISSUE}: caption grouping stays isGroupedFollower "
            "(do not move / invent a second key)"
        )
    if not re.search(r"\bfilteredTimeline\b", group_fn):
        fail(
            f"{_ISSUE}: isGroupedFollower must key off filteredTimeline "
            "(Me/Them recomputes runs on the visible set)"
        )
    if not re.search(r"filteredTimeline\s*\[\s*i\s*-\s*1\s*\]", group_fn) and not re.search(
        r"prev", group_fn
    ):
        fail(
            f"{_ISSUE}: grouping compares the filtered previous row "
            "(a filtered-out neighbor must not leave a lone caption)"
        )
    if re.search(r"\btimeline\s*\[\s*i\s*-\s*1\s*\]", group_fn):
        fail(
            f"{_ISSUE}: do not group against the unfiltered timeline "
            "(filtered-out neighbor would leave a lone caption)"
        )
    if not re.search(r"\bfrom_me\b", group_fn):
        fail(
            f"{_ISSUE}: grouping key stays from_me + conversation_id + "
            "calendar day on the filtered set"
        )
    if not re.search(r"isGroupedFollower\s*\(\s*item\.index", rows):
        fail(
            f"{_ISSUE}: TimelineRows must still call isGroupedFollower "
            "(caption on run-start; data-grouped on followers)"
        )
    if not re.search(r"data-grouped\s*=\s*\{[^}]*isGroupedFollower", rows):
        fail(f"{_ISSUE}: data-grouped still on followers after Me/Them")
    tl_list = _text(crate / "web" / "lib" / "TimelineList.svelte")
    if not re.search(
        r"groupedFollower\s*\(\s*filteredTimeline",
        _without_comments(tl_list),
    ):
        fail(
            f"{_ISSUE}: TimelineList must pass filteredTimeline into "
            "isGroupedFollower (keep #206)"
        )

    # 7) from-me-filtered-walk — virtualizer / find / jump / j/k.
    root = repo_root()
    jump = _text(crate / "web" / "lib" / "jumpDay.ts")
    find = _text(crate / "web" / "lib" / "findHighlight.ts")
    keys = _text(crate / "web" / "lib" / "PeopleKeys.ts")
    if not re.search(r"\bfilteredTimeline\b", tl_list):
        fail(
            f"{_ISSUE}: virtualizer / Load older must walk filteredTimeline "
            "(sender-filtered set)"
        )
    if not re.search(r"filteredTimeline\.length\s*>\s*0", tl_list) and not re.search(
        r"showLoadOlder", tl_list
    ):
        fail(
            f"{_ISSUE}: Load older stays hidden when the filtered list is empty"
        )
    if not re.search(r"windowedDayGroups", tl_list) or not re.search(
        r"filteredTimeline\.slice", _without_comments(tl_list)
    ):
        fail(
            f"{_ISSUE}: day headings only for days that still have a "
            "matching row (windowedDayGroups from filteredTimeline)"
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
            "until N from-me matches"
        )

    # 8) from-me-no-ipc — mix A: no person_timeline from_me arg; no is_self.
    rust = _tauri_rust_blob(crate)
    api = _text(crate / "web" / "lib" / "api.ts")
    sig = _rust_fn_signature(rust, "person_timeline")
    if _IPC_FROM_ME.search(sig):
        fail(
            f"{_ISSUE}: mix A — do not add a person_timeline from_me arg "
            "(client fromMeFilter only)"
        )
    api_fn = _ts_fn_body(api, "personTimeline") or ""
    api_win = _windows_around(api, re.compile(r"\bpersonTimeline\b"), 40, 320)
    if _IPC_FROM_ME.search(api_win + "\n" + api_fn):
        fail(
            f"{_ISSUE}: mix A — api.personTimeline must not take from_me / "
            "fromMe (no new IPC)"
        )
    call_win = "\n".join(
        [
            _windows_around(pane, re.compile(r"\bpersonTimeline\b"), 40, 280),
            select_fn or "",
            open_fn or "",
        ]
    )
    if re.search(r"\bfromMe\s*:|\bfrom_me\s*:", call_win):
        fail(
            f"{_ISSUE}: mix A — selectPerson must not pass from_me to "
            "personTimeline (client filter only)"
        )
    row_type = _ts_type_body(api, "TimelineRow")
    if _IS_SELF.search(row_type):
        fail(
            f"{_ISSUE}: do not invent is_self on TimelineRow "
            "(keep existing from_me)"
        )
    if _SENDER_ID.search(row_type):
        fail(
            f"{_ISSUE}: do not add sender_identity_id on TimelineRow "
            "(do not edit stored sender)"
        )
    for name, src in chrome.items():
        cleaned = _without_comments(src)
        if name != "TimelineMail.ts" and _IS_SELF.search(cleaned):
            fail(
                f"{_ISSUE}: do not invent is_self on the timeline filter "
                f"({name})"
            )
        if _SENDER_ID.search(cleaned):
            fail(
                f"{_ISSUE}: do not start reading sender_identity_id in the "
                f"web crate for this ticket ({name})"
            )

    # 9) from-me-gallery-untouched.
    gal_path = crate / "web" / "lib" / "PersonMediaDialog.svelte"
    gal_raw = _text(gal_path)
    gal = _without_comments(gal_raw)
    media_sig = _rust_fn_signature(rust, "person_media")
    if re.search(r"\bfromMeFilter\b", gal):
        fail(
            f"{_ISSUE}: PersonMediaDialog must ignore fromMeFilter "
            "(gallery still ignores timeline chips)"
        )
    if _IPC_FROM_ME.search(media_sig):
        fail(
            f"{_ISSUE}: person_media must not take from_me "
            "(gallery membership unchanged)"
        )
    api_media = _windows_around(api, re.compile(r"\bpersonMedia\b"), 40, 240)
    if _IPC_FROM_ME.search(api_media) or re.search(r"\bfromMeFilter\b", api_media):
        fail(f"{_ISSUE}: api.personMedia must not grow a from_me / fromMe arg")

    # 10) from-me-locale — new keys both packs; tr not English; t() key-only.
    i18n = _text(crate / "web" / "lib" / "i18n.ts")
    en = _chrome_pack_entries(_text(crate / "web" / "lib" / "locales" / "en.ts"))
    tr = _chrome_pack_entries(_text(crate / "web" / "lib" / "locales" / "tr.ts"))
    heading = _heading_keys(toolbar + "\n" + empty_raw)
    if not heading:
        fail(
            f"{_ISSUE}: new en+tr chrome keys required "
            "(All / Them / Me / empty); t() stays key-only"
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

    # 11) from-me-no-innerhtml — chip labels / empty as text nodes.
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

    # 12) keep #115 / #116 / #362 / #206 / #111 / #361.
    if not _PLATFORM_HOOK.search(filters_raw) or not _KIND_HOOK.search(
        filters_raw
    ):
        fail(
            f"{_ISSUE}: keep #115 / #116 data-platform-filter and "
            "data-kind-filter"
        )
    if not _ATTACH_HOOK.search(filters_raw):
        fail(f"{_ISSUE}: keep #362 data-attach-kind-filter")
    if (
        not _PLATFORM_STATE.search(pane)
        or not _KIND_STATE.search(pane)
        or not _ATTACH_STATE.search(pane)
    ):
        fail(
            f"{_ISSUE}: keep platformFilter + kindFilter + attachKindFilter"
        )
    if not _GALLERY_OPEN.search(pane_raw):
        fail(f"{_ISSUE}: keep #361 data-person-gallery-open")
    if not gal_path.is_file() or not _GALLERY_GRID.search(gal_raw):
        fail(f"{_ISSUE}: keep #361 PersonMediaDialog / data-person-gallery")

    # 13) D24 docs/user/app.md.
    dtxt = _text(root / "docs" / "user" / "app.md")
    if not dtxt.strip():
        fail(
            f"{_ISSUE}: docs/user/app.md required — All | Them | Me on the "
            "person timeline"
        )
    if not _DOCS_CHIPS.search(dtxt) or not _DOCS_TIMELINE.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say All | Them | Me on the "
            "person timeline"
        )
    if not _DOCS_AND.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say from-me ANDs with "
            "platform / kind / attach-kind"
        )
    if not _DOCS_DEFAULT.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must say All is the default")
    if not _DOCS_RESET.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say switching people resets "
            "the sender filter"
        )
    if not _DOCS_EMPTY.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say Them + empty + Show all "
            "(not a stuck spinner)"
        )
    if not _DOCS_GROUP.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say caption grouping stays on "
            "the filtered set"
        )
