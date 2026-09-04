"""#312 — People sidebar Recent | A–Z (`interlace.peopleSort`).

Client re-sort of sidebar `filtered` only. Compact control next to
#person-filter. Persist like #309. Keep SQL Recent. No name_fold.
Search / ⌘K / Merge stay Recent. Leave pref on Switch; re-read on Open B.

Must-IDs: sort-control, sort-pref-write, sort-restore-onmount, sort-d24.
A–Z / #110 / keep-checks live in people_sort_fold.py.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.import_boot_guards import _ls_pref_keys
from tauri_gate.include_groups import _mount_pref_head
from tauri_gate.people_collapse_lib import _PERSON_FILTER_MARKUP, _gated_on_collapse
from tauri_gate.reopen_last_lib import _GETITEM, _SETITEM, _fn_body, _onmount_body
from tauri_gate.scan import (
    _CONFIG_TOML,
    _LAST_PATH_API,
    _LS_BRACKET,
    _rust_fn_body,
    _web_logic,
    _without_comments,
)
from tauri_gate.status_toasts_chrome import _toml_keys_in_fn, _windows_around
from tauri_gate.status_toasts_toast import _svelte_effect_args

_SORT_KEY = "interlace.peopleSort"
_SORT_KEY_RX = re.compile(r"interlace\.peopleSort")
_SORT_PREF_NAME = re.compile(r"\b(?:PEOPLE_SORT_PREF|SORT_PREF|PEOPLE_SORT_KEY)\b")
_READ_SORT = re.compile(
    r"\b(?:readPeopleSortPref|readSortPref|restorePeopleSort|readPeopleSort)\b"
)
_WRITE_SORT = re.compile(
    r"\b(?:writePeopleSortPref|persistPeopleSort|writeSortPref|persistSortPref)\b"
)
_SORT_STATE = re.compile(r"\b(?:peopleSort|people_sort|PEOPLE_SORT)\b")
_SORT_STATE_RECENT = re.compile(
    r"""\bpeopleSort\s*(?::[^=]{0,40})?=\s*\$state(?:<[^>]*>)?\s*\(\s*["']recent["']\s*\)"""
)
_AZ_LIT = re.compile(r"""["']az["']""")
_RECENT_LIT = re.compile(r"""["']recent["']""")
_JUNK_AS_AZ = re.compile(
    r"""===\s*["']recent["']\s*\?\s*["']recent["']\s*:\s*["']az["']"""
)
_AZ_ON = re.compile(r"""===\s*["']az["']""")
_REMOVE_ITEM = re.compile(r"\bremoveItem\s*\(")
_ICLOUD = re.compile(r"\biCloud\b|CloudKit|NSUbiquitous")
_RECENT_LABEL = re.compile(r"\bRecent\b")
_AZ_LABEL = re.compile(r"A\s*[–-]\s*Z")
_DOCS_REMEMBER = re.compile(
    r"(?:Recent.{0,48}A\s*[–-]\s*Z|A\s*[–-]\s*Z.{0,48}Recent|people sort)"
    r".{0,220}(?:remembered|remember|persisted|localStorage|local(?:ly)?)"
    r"|(?:remembered|remember|persisted|localStorage|local(?:ly)?)"
    r".{0,220}(?:Recent.{0,48}A\s*[–-]\s*Z|people sort)",
    re.I | re.S,
)
_DOCS_NOT_ICLOUD = re.compile(
    r"(?:Recent.{0,48}A\s*[–-]\s*Z|A\s*[–-]\s*Z.{0,48}Recent|people sort)"
    r".{0,240}not iCloud"
    r"|not iCloud.{0,240}(?:Recent.{0,48}A\s*[–-]\s*Z|people sort)",
    re.I | re.S,
)
_SKIP = frozenset(
    "if for while switch catch function return typeof new await void "
    "String Number Boolean toLowerCase console people filter map sort "
    "toSorted localeCompare".split()
)


def _near_filter(sidebar: str) -> str:
    m = re.search(r"""id\s*=\s*["']person-filter["']""", sidebar)
    if not m:
        return ""
    return sidebar[max(0, m.start() - 500) : m.end() + 500]


def _writes_sort_pref(blob: str) -> bool:
    if _WRITE_SORT.search(blob):
        return True
    if not _SETITEM.search(blob):
        return False
    return bool(_SORT_KEY_RX.search(blob) or _SORT_PREF_NAME.search(blob))


def _reads_sort_pref(blob: str) -> bool:
    if _READ_SORT.search(blob):
        return True
    if not (_GETITEM.search(blob) or _LS_BRACKET.search(blob)):
        return False
    return bool(_SORT_KEY_RX.search(blob) or _SORT_PREF_NAME.search(blob))


def _blob_writes_sort(src: str, blob: str) -> bool:
    if _writes_sort_pref(blob):
        return True
    seen: set[str] = set()
    for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob):
        if name in seen or name in _SKIP:
            continue
        seen.add(name)
        inner = _fn_body(src, name)
        if inner and _writes_sort_pref(inner):
            return True
    return False


def _blob_reads_sort(src: str, blob: str) -> bool:
    if _reads_sort_pref(blob):
        return True
    seen: set[str] = set()
    for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob):
        if name in seen:
            continue
        seen.add(name)
        inner = _fn_body(src, name)
        if inner and _reads_sort_pref(inner):
            return True
    return False


def _sort_effect_writes(app: str) -> bool:
    for arg in _svelte_effect_args(app):
        if _SORT_STATE.search(arg) and _writes_sort_pref(arg):
            return True
    return False


def _control_labels(near: str, en: str) -> bool:
    if _RECENT_LABEL.search(near) and _AZ_LABEL.search(near):
        return True
    return bool(
        re.search(r"\bt\s*\(", near) and _RECENT_LABEL.search(en) and _AZ_LABEL.search(en)
    )


def assert_people_sort(crate: Path) -> None:
    """#312: compact Recent | A–Z on the people list; persist locally."""
    app_path = crate / "web" / "App.svelte"
    side_path = crate / "web" / "lib" / "PeopleSidebar.svelte"
    shell_path = crate / "web" / "lib" / "PeopleShell.svelte"
    prefs_path = crate / "web" / "lib" / "PeoplePrefs.ts"
    boot_path = crate / "web" / "lib" / "PeopleBoot.ts"
    docs = repo_root() / "docs" / "user" / "app.md"
    en_path = crate / "web" / "lib" / "locales" / "en.ts"
    if not app_path.is_file():
        fail("#312: App.svelte required (people-sort restore / persist lives there)")
    if not side_path.is_file():
        fail("#312: PeopleSidebar.svelte required (Recent | A–Z control)")
    if not shell_path.is_file():
        fail("#312: PeopleShell.svelte required (filtered re-sort)")

    app_raw = app_path.read_text()
    app = _without_comments(app_raw)
    sidebar = _without_comments(side_path.read_text())
    shell = _without_comments(shell_path.read_text())
    prefs = _without_comments(prefs_path.read_text()) if prefs_path.is_file() else ""
    boot = _without_comments(boot_path.read_text()) if boot_path.is_file() else ""
    en = en_path.read_text() if en_path.is_file() else ""
    dtxt = docs.read_text() if docs.is_file() else ""
    web = _without_comments(_web_logic(crate))
    combo = "\n".join([app, prefs, sidebar, shell, boot])
    session_path = repo_root() / "crates" / "interlace-core" / "src" / "session.rs"
    session = session_path.read_text() if session_path.is_file() else ""

    # 1) sort-control — compact Recent | A–Z next to #person-filter.
    near = _near_filter(sidebar)
    if not near.strip() or not _control_labels(near, en):
        fail(
            "#312: compact Recent | A–Z control required next to #person-filter "
            "on the people-list chrome (not PeopleNav / palette)"
        )
    for m in list(_RECENT_LABEL.finditer(sidebar)) + list(_AZ_LABEL.finditer(sidebar)):
        if _gated_on_collapse(sidebar, m.start()):
            fail(
                "#312: Recent | A–Z must stay mounted when the rail is collapsed "
                "(sr-only with #person-filter; do not wrap in {#if !collapsed})"
            )
    if "sr-only" not in near or not re.search(r"sidebarCollapsed|collapsed", near):
        fail(
            "#312: Recent | A–Z must be sr-only with #person-filter when the "
            "rail is collapsed; visible when expanded"
        )
    if not _PERSON_FILTER_MARKUP.search(sidebar):
        fail("#312: keep id=person-filter next to the sort control")

    # 2) sort-pref-write — namespaced key, getItem + setItem, recent/az.
    ls_keys = _ls_pref_keys(web)
    if _SORT_KEY not in ls_keys:
        fail(
            "#312: persist people sort in namespaced localStorage "
            "(getItem + setItem; interlace.peopleSort) — "
            "not write_last_path / config.toml / iCloud"
        )
    persist_surface = "\n".join(
        [
            _windows_around(web, _SORT_KEY_RX, before=160, after=220),
            _windows_around(web, _SORT_PREF_NAME, before=160, after=220),
            _windows_around(web, _WRITE_SORT, before=80, after=200),
            _windows_around(web, _READ_SORT, before=80, after=200),
            _fn_body(combo, "writePeopleSortPref"),
            _fn_body(combo, "persistPeopleSort"),
            _fn_body(combo, "readPeopleSortPref"),
        ]
    )
    if not _SETITEM.search(persist_surface):
        fail(
            "#312: persist people sort with localStorage.setItem "
            "(interlace.peopleSort; recent / az)"
        )
    if not _GETITEM.search(persist_surface) and not _LS_BRACKET.search(persist_surface):
        fail(
            "#312: restore people sort from localStorage.getItem "
            "(same interlace.peopleSort key)"
        )
    write_blob = persist_surface + "\n" + sidebar
    if not (_RECENT_LIT.search(write_blob) and _AZ_LIT.search(write_blob)):
        fail("#312: interlace.peopleSort values are recent / az (closed pair)")
    if not _blob_writes_sort(combo, sidebar):
        fail(
            "#312: toggling Recent | A–Z must setItem interlace.peopleSort "
            "(write on the control only)"
        )
    if _sort_effect_writes(app):
        fail(
            "#312: do not persist peopleSort from a bare $effect "
            "(write on the control only; #308 setup must not write)"
        )
    if _LAST_PATH_API.search(persist_surface) or _CONFIG_TOML.search(persist_surface):
        fail(
            "#312: do not persist people sort via write_last_path / "
            "read_last_path / config.toml (localStorage only)"
        )
    if _ICLOUD.search(persist_surface):
        fail("#312: do not persist people sort to iCloud")
    if not session_path.is_file():
        fail("#312: crates/interlace-core/src/session.rs required (do not stash UI prefs there)")
    wl = _rust_fn_body(_without_comments(session), "write_last_path")
    if re.search(r"people_sort|peopleSort", wl, re.I):
        fail(
            "#312: do not rewrite session.rs write_last_path to dump people sort "
            "(config.toml is the last-archive pointer, not chrome prefs)"
        )
    extra = [k for k in _toml_keys_in_fn(wl) if "sort" in k.lower()]
    if extra:
        fail(
            "#312: do not rewrite session.rs write_last_path to dump extra keys "
            "(people sort is not last_archive_path / config.toml)"
        )
    if not _SORT_STATE_RECENT.search(app):
        fail(
            "#312: first-run peopleSort still defaults to recent "
            '($state("recent"); missing key → recent)'
        )

    # 3) sort-restore-onmount — getItem at sidebar / density moment.
    mount = _onmount_body(app)
    if not mount.strip():
        fail(
            "#312: restore peopleSort at onMount "
            "(same moment as sidebar / density / include-groups)"
        )
    mount_head = _mount_pref_head(mount)
    if not _blob_reads_sort(combo, mount_head):
        fail(
            "#312: restore peopleSort at onMount "
            "(same moment as sidebar / density / include-groups) — "
            "getItem interlace.peopleSort"
        )
    read_blob = "\n".join(
        [
            persist_surface,
            _fn_body(combo, "readPeopleSortPref"),
            _fn_body(combo, "readSortPref"),
        ]
    )
    if _JUNK_AS_AZ.search(read_blob) or not (
        _AZ_ON.search(read_blob) and _RECENT_LIT.search(read_blob)
    ):
        fail(
            "#312: missing / wiped / junk interlace.peopleSort must stay recent "
            "(compare getItem to az; first-run stays Recent)"
        )

    # 4) switch-archive — leave the pref; re-read on Open B.
    switch = _fn_body(boot, "switchToSetup") or _fn_body(combo, "switchToSetup")
    for m in _REMOVE_ITEM.finditer(switch):
        window = switch[max(0, m.start() - 40) : m.end() + 80]
        if _SORT_KEY_RX.search(window) or _SORT_PREF_NAME.search(window):
            fail(
                "#312: do not removeItem interlace.peopleSort in switchToSetup "
                "(leave the pref)"
            )
    apply_st = _fn_body(app, "applyStatus") or _fn_body(app_raw, "applyStatus")
    if not _blob_reads_sort(combo, apply_st):
        fail(
            "#312: on successful Open B (applyStatus / leave setup) re-read "
            "interlace.peopleSort so B’s first All already matches"
        )

    # 5) sort-d24
    if not dtxt.strip():
        fail(
            "#312: docs/user/app.md required — Recent | A–Z is remembered "
            "locally (localStorage, not iCloud)"
        )
    if not _DOCS_REMEMBER.search(dtxt):
        fail(
            "#312: docs/user/app.md must say Recent | A–Z is remembered locally "
            "(localStorage)"
        )
    if not _DOCS_NOT_ICLOUD.search(dtxt):
        fail(
            "#312: docs/user/app.md must say Recent | A–Z is remembered locally "
            "(not iCloud)"
        )
