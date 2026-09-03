"""#312 fold — A–Z compare, Recent D18, Search/palette/Merge, keep-checks.

Sibling of people_sort.py (do not grow that file). After the #138 haystack:
Recent keeps people[] order; A–Z sorts the filtered copy by display_name
via localeCompare(undefined, { sensitivity: "base" }). Ada above Zeynep.
Quiet + self sort with everyone in A–Z. Same name → id ascending.
SQL person_list / people() unchanged. Search picker / ⌘K / Merge stay Recent.

Must-IDs: sort-az-ada-zeynep, sort-recent-d18, sort-quiet-az,
sort-keep-138-110-265, sort-keep-212-276-305-309.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.people_filter import (
    _PEOPLE_FILTER_IDENTITIES_FIELD,
    _PEOPLE_FILTER_IDENTITY_TOKENS,
    _PEOPLE_TAKE_ARCH,
    _people_filter_window,
    _people_list_on_blob,
    _people_rust_cmd_body,
)
from tauri_gate.people_sort import (
    _READ_SORT,
    _SORT_KEY_RX,
    _SORT_PREF_NAME,
    _SORT_STATE,
    _WRITE_SORT,
)
from tauri_gate.reopen_last_lib import _fn_body
from tauri_gate.scan import _call_arg, _web_logic, _without_comments
from tauri_gate.status_toasts_chrome import _PEOPLE_EACH

_AZ_GATE = re.compile(
    r"""(?:peopleSort|people_sort|PEOPLE_SORT|sort)\s*===?\s*["']az["']"""
    r"""|["']az["']\s*===?\s*(?:peopleSort|people_sort|PEOPLE_SORT|sort)"""
)
_LOCALE_COMPARE = re.compile(r"\blocaleCompare\s*\(")
_SENSITIVITY_BASE = re.compile(r"""sensitivity\s*:\s*["']base["']""")
_UNDEFINED_LOCALE = re.compile(r"localeCompare\s*\([^,]+,\s*undefined\s*,")
_DISPLAY_CMP = re.compile(
    r"display_name\s*\.?\s*localeCompare|localeCompare\s*\([^)]*display_name"
)
_NAME_FOLD = re.compile(r"\bname_fold(?:_join)?\b")
_SORT_CALL = re.compile(r"\.(?:sort|toSorted)\s*\(")
_ID_ASC = re.compile(r"""(\w+)\.id\s*-\s*(\w+)\.id""")
_LAST_ACT = re.compile(r"\blast_activity_at\b")
_IS_SELF = re.compile(r"\bis_self\b")
_KEEP_SIDEBAR = re.compile(r"interlace\.peopleSidebarCollapsed")
_KEEP_DENSITY = re.compile(r"interlace\.density")
_KEEP_LAST_VIEW = re.compile(r"interlace\.lastView")
_KEEP_LAST_PERSON = re.compile(r"interlace\.lastPersonId")
_KEEP_GROUPS = re.compile(r"interlace\.includeGroups")
_ORDER_BY = "ORDER BY p.is_self DESC, act.sent_at IS NULL, act.sent_at DESC, p.id"


def _derived_window(src: str, name: str, n: int = 900) -> str:
    m = re.search(rf"(?:const|let)\s+{re.escape(name)}\s*=\s*\$derived\s*\(", src)
    if not m:
        m = re.search(rf"(?:const|let)\s+{re.escape(name)}\s*=", src)
    return src[m.start() : m.start() + n] if m else ""


def _az_compare_blob(filt: str) -> str:
    parts = [filt]
    for m in _SORT_CALL.finditer(filt):
        parts.append(_call_arg(filt, m.end() - 1))
    return "\n".join(parts)


def _rust_params(src: str, name: str) -> str:
    m = re.search(rf"(?:pub\s+)?(?:async\s+)?fn\s+{re.escape(name)}\s*\(([^)]*)\)", src)
    return m.group(1) if m else ""


def _has_sort_arg(params: str) -> bool:
    return bool(re.search(r"\b(?:sort|people_sort|order|collation|az)\b", params, re.I))


def _stays_sql_recent(blob: str, where: str) -> None:
    if (
        _SORT_KEY_RX.search(blob)
        or _SORT_PREF_NAME.search(blob)
        or _READ_SORT.search(blob)
        or _WRITE_SORT.search(blob)
        or _SORT_STATE.search(blob)
    ):
        fail(
            f"#312: {where} must stay SQL Recent "
            "(do not bind interlace.peopleSort / re-sort that list)"
        )
    if _LOCALE_COMPARE.search(blob) and re.search(r"display_name", blob):
        fail(f"#312: {where} must stay SQL Recent (do not re-sort by display_name)")
    if _SORT_CALL.search(blob) and re.search(
        r"display_name|peopleSort|localeCompare", blob
    ):
        fail(
            f"#312: {where} must stay SQL Recent "
            "(Search picker / ⌘K / Merge keep people[] order)"
        )


def assert_people_sort_fold(crate: Path) -> None:
    """#312 fold: A–Z localeCompare on filtered; keep #138 / #110 / #265 / keys."""
    app_path = crate / "web" / "App.svelte"
    side_path = crate / "web" / "lib" / "PeopleSidebar.svelte"
    shell_path = crate / "web" / "lib" / "PeopleShell.svelte"
    prefs_path = crate / "web" / "lib" / "PeoplePrefs.ts"
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    pal_path = crate / "web" / "lib" / "CommandPalette.svelte"
    merge_path = crate / "web" / "lib" / "utils.ts"
    rust_path = crate / "src" / "main.rs"
    people_rs = repo_root() / "crates" / "interlace-core" / "src" / "people.rs"
    if not shell_path.is_file():
        fail("#312: PeopleShell.svelte required (filtered A–Z re-sort)")
    if not side_path.is_file():
        fail("#312: PeopleSidebar.svelte required (keep {#each filtered})")

    app = _without_comments(app_path.read_text()) if app_path.is_file() else ""
    sidebar = _without_comments(side_path.read_text())
    shell = _without_comments(shell_path.read_text())
    prefs = _without_comments(prefs_path.read_text()) if prefs_path.is_file() else ""
    search = _without_comments(search_path.read_text()) if search_path.is_file() else ""
    pal = _without_comments(pal_path.read_text()) if pal_path.is_file() else ""
    merge = _without_comments(merge_path.read_text()) if merge_path.is_file() else ""
    rust = rust_path.read_text() if rust_path.is_file() else ""
    core = people_rs.read_text() if people_rs.is_file() else ""
    web = _without_comments(_web_logic(crate))

    # 1) sort-az-ada-zeynep / sort-quiet-az / fold / self-pin / tie-break.
    filt = _people_filter_window(web)
    if not filt.strip():
        fail("#312: PeopleShell `filtered` derivation required (re-sort the copy)")
    if _NAME_FOLD.search(filt):
        fail(
            "#312: do not call name_fold for A–Z "
            "(identity keying, not display sort; Ada above Zeynep uses localeCompare)"
        )
    if not _AZ_GATE.search(filt):
        fail(
            "#312: A–Z must sort the filtered copy only when az is selected "
            "(Recent keeps people[] / last D18 order)"
        )
    if not _SORT_STATE.search(filt):
        fail("#312: PeopleShell `filtered` must read peopleSort (sidebar only)")
    cmp_blob = _az_compare_blob(filt)
    if not (
        _LOCALE_COMPARE.search(cmp_blob)
        and _UNDEFINED_LOCALE.search(cmp_blob)
        and _SENSITIVITY_BASE.search(cmp_blob)
        and _DISPLAY_CMP.search(cmp_blob)
    ):
        fail(
            "#312: A–Z must sort by display_name.localeCompare(other, undefined, "
            '{ sensitivity: "base" }) — Ada above Zeynep'
        )
    if _LAST_ACT.search(cmp_blob):
        fail(
            "#312: in A–Z a quiet contact (no last_activity_at) sorts with everyone "
            "(quiet Ada still above Zeynep; do not keep NULLS LAST)"
        )
    if _IS_SELF.search(cmp_blob):
        fail(
            "#312: A–Z sorts self with everyone by display_name "
            "(Recent keeps today’s is_self pin; do not pin self in A–Z)"
        )
    if not _ID_ASC.search(cmp_blob):
        fail("#312: same display_name → id ascending (not a user-facing sort key)")

    # 2) sort-recent-d18 + keep #110 SQL + no people() sort arg.
    if not people_rs.is_file():
        fail("#312: crates/interlace-core/src/people.rs required (keep #110 ORDER BY)")
    list_blob = _people_list_on_blob(core)
    if _ORDER_BY not in list_blob and _ORDER_BY not in core:
        fail(
            "#312: keep #110 SQL ORDER BY "
            "(p.is_self DESC, last D18 sent_at NULLS LAST, id) — "
            "Recent is that order; no sort argument"
        )
    for name in ("person_list", "person_list_on", "person_list_on_with_groups"):
        if _has_sort_arg(_rust_params(core, name)):
            fail(
                "#312: person_list / person_list_on must not take a sort argument "
                "(client re-sort of sidebar filtered only)"
            )
    people_body = _people_rust_cmd_body(rust)
    if not people_body.strip():
        fail("#312: keep #265 people() command (snapshot person_list_on)")
    if _has_sort_arg(_rust_params(rust, "people")):
        fail("#312: people() must not take a sort argument (no second scan)")
    if re.search(r"api\s*\.\s*people\s*\(\s*[^)\s]", app + shell):
        fail("#312: do not pass a sort argument to api.people() (keep snapshot Recent)")
    if "person_list_on" not in people_body:
        fail("#312: keep #265 snapshot person_list_on (groups-off; no sort arg)")
    if _PEOPLE_TAKE_ARCH.search(people_body):
        fail("#312: keep #265 — people must not take() the Archive")

    # 3) search-vs-people — picker / ⌘K / Merge stay SQL Recent.
    _stays_sql_recent(_derived_window(search, "filteredPeople"), "Search person picker")
    _stays_sql_recent(_derived_window(pal, "palettePeople"), "⌘K Jump to person")
    _stays_sql_recent(_fn_body(merge, "mergeTargets") or merge, "Merge targets")

    # 4) sort-keep-138-110-265
    if "person-filter" not in sidebar:
        fail("#312: keep #138 id=person-filter")
    if not _PEOPLE_EACH.search(sidebar):
        fail("#312: keep #138 people list {#each filtered}")
    has_identity = bool(_PEOPLE_FILTER_IDENTITY_TOKENS.search(filt)) or bool(
        _PEOPLE_FILTER_IDENTITIES_FIELD.search(filt)
    )
    if not has_identity:
        fail(
            "#312: keep #138 identity haystack "
            "(identity_values / filter_haystack / p.identities on the loaded list)"
        )
    if "display_name" not in filt and "displayName" not in filt:
        fail("#312: keep #138 people filter matching display_name")

    # 5) sort-keep-212-276-305-309
    if not _KEEP_SIDEBAR.search(web):
        fail("#312: keep #212 sidebar persist (interlace.peopleSidebarCollapsed)")
    if not _KEEP_DENSITY.search(web):
        fail("#312: keep #276 density persist (interlace.density)")
    if not _KEEP_LAST_VIEW.search(web) or not _KEEP_LAST_PERSON.search(web):
        fail(
            "#312: keep #305 last view / last person keys "
            "(interlace.lastView / interlace.lastPersonId)"
        )
    if not _KEEP_GROUPS.search(web):
        fail("#312: keep #309 include-groups persist (interlace.includeGroups)")
    if "restoreLastView" not in app or "restoreLastPerson" not in app:
        fail("#312: keep the #305 restore path (restoreLastView / restoreLastPerson)")
    if "persistSidebar" not in app or "persistDensity" not in app:
        fail("#312: keep persistSidebar / persistDensity (#212 / #276)")
    if "readIncludeGroupsPref" not in app:
        fail("#312: keep readIncludeGroupsPref (#309)")
    if not prefs_path.is_file():
        fail("#312: PeoplePrefs.ts required (keep the five existing keys)")
    for tok in (
        "SIDEBAR_PREF",
        "DENSITY_PREF",
        "LAST_VIEW_PREF",
        "LAST_PERSON_PREF",
        "INCLUDE_GROUPS_PREF",
    ):
        if tok not in prefs:
            fail(
                "#312: keep SIDEBAR_PREF / DENSITY_PREF / LAST_VIEW_PREF / "
                "LAST_PERSON_PREF / INCLUDE_GROUPS_PREF "
                "(do not rename / merge / drop the five existing keys)"
            )
