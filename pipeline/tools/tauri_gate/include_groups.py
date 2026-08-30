"""#309 — remember include-groups locally (`interlace.includeGroups`).

Restore at onMount before restoreLastPerson. Persist inspector tick +
empty-state Include groups. jumpToMessage must not setItem. Keep #308
in-memory reset; leave the pref; re-read on Open B. Search stays
unpersisted. Keep #212 / #276 / #305. No config.toml / iCloud.

Must-IDs: groups-pref-write, groups-restore-onmount,
groups-restore-before-load, groups-d24, groups-keep-212-276-305,
groups-keep-308-reset, groups-search-separate.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.import_boot_guards import _ls_pref_keys
from tauri_gate.reopen_last_lib import (
    _GETITEM,
    _SETITEM,
    _fn_body,
    _onmount_body,
)
from tauri_gate.scan import (
    _CONFIG_TOML,
    _LAST_PATH_API,
    _LS_BRACKET,
    _match_closer,
    _rust_fn_body,
    _search_pane_blob,
    _web_logic,
    _without_comments,
)
from tauri_gate.status_toasts_chrome import _toml_keys_in_fn, _windows_around
from tauri_gate.status_toasts_toast import _svelte_effect_args

_GROUPS_KEY = "interlace.includeGroups"
_GROUPS_KEY_RX = re.compile(r"interlace\.includeGroups")
_GROUPS_PREF_NAME = re.compile(
    r"\b(?:GROUPS_PREF|INCLUDE_GROUPS_PREF|INCLUDE_GROUPS_KEY)\b"
)
_READ_GROUPS = re.compile(
    r"\b(?:readIncludeGroupsPref|readGroupsPref|restoreIncludeGroups)\b"
)
_WRITE_GROUPS = re.compile(
    r"\b(?:writeIncludeGroupsPref|persistIncludeGroups|writeGroupsPref|"
    r"persistGroupsPref)\b"
)
_GROUPS_STATE_FALSE = re.compile(
    r"\blet\s+includeGroups\s*=\s*\$state(?:<[^>]*>)?\s*\(\s*false\s*\)"
)
_GROUPS_FALSE = re.compile(r"\bincludeGroups\s*=\s*false\b")
_ON_TOKEN = re.compile(r"""===\s*["'](?:1|true|on)["']""")
_CLOSED_WRITE = re.compile(
    r"""\?\s*["'](?:1|true|on)["']\s*:\s*["'](?:0|false|off)["']"""
)
_SET_ON = re.compile(r"""setItem\s*\([^;]{0,160}["'](?:1|true|on)["']""")
_SET_OFF = re.compile(r"""setItem\s*\([^;]{0,160}["'](?:0|false|off)["']""")
_REMOVE_ITEM = re.compile(r"\bremoveItem\s*\(")
_KEEP_SIDEBAR = re.compile(r"interlace\.peopleSidebarCollapsed")
_KEEP_DENSITY = re.compile(r"interlace\.density")
_KEEP_LAST_VIEW = re.compile(r"interlace\.lastView")
_KEEP_LAST_PERSON = re.compile(r"interlace\.lastPersonId")
_ICLOUD = re.compile(r"\biCloud\b|CloudKit|NSUbiquitous")
_INSPECTOR_BIND = re.compile(r"bind:checked=\{includeGroups\}")
_SEARCH_BIND = re.compile(r"bind:includeGroups")
_DOCS_REMEMBER = re.compile(
    r"include groups?.{0,200}(?:remembered|remember|persisted|localStorage|local(?:ly)?)"
    r"|(?:remembered|remember|persisted|localStorage|local(?:ly)?).{0,200}include groups?",
    re.I | re.S,
)
_DOCS_NOT_ICLOUD = re.compile(
    r"(?:include groups?|groups (?:checkbox|pref|preference)).{0,240}not iCloud"
    r"|not iCloud.{0,240}(?:include groups?|groups (?:checkbox|pref|preference))",
    re.I | re.S,
)
_JUMP_SKIP = frozenset(
    "if for while switch catch function selectPerson openPersonAtMessage "
    "personShow tick api String Number Boolean toLowerCase console void "
    "peopleShell setTimeout Promise".split()
)


def _arrow_prop(src: str, name: str) -> str:
    """Body of `name: (args) => {…}` / `name={() => {…}}` / `name={() => expr}`."""
    m = re.search(
        rf"{re.escape(name)}\s*(?::|=)\s*\{{?\s*(?:async\s*)?\([^)]*\)\s*=>",
        src,
    )
    if not m:
        return ""
    i = m.end()
    n = len(src)
    while i < n and src[i].isspace():
        i += 1
    if i < n and src[i] == "{":
        close = _match_closer(src, i)
        return src[i + 1 : close] if close >= 0 else src[i + 1 :]
    j = i
    depth = 0
    while j < n:
        c = src[j]
        if c in "{(":
            depth += 1
        elif c in "})":
            if depth == 0:
                break
            depth -= 1
        elif c in ";," and depth == 0:
            break
        j += 1
    return src[i:j]


def _open_tag(src: str, name: str) -> str:
    m = re.search(rf"<{re.escape(name)}\b", src)
    if not m:
        return ""
    gt = src.find(">", m.end())
    if gt < 0:
        return src[m.start() : m.start() + 400]
    return src[m.start() : gt + 1]


def _writes_groups_pref(blob: str) -> bool:
    if _WRITE_GROUPS.search(blob):
        return True
    if not _SETITEM.search(blob):
        return False
    return bool(_GROUPS_KEY_RX.search(blob) or _GROUPS_PREF_NAME.search(blob))


def _reads_groups_pref(blob: str) -> bool:
    if _READ_GROUPS.search(blob):
        return True
    if not (_GETITEM.search(blob) or _LS_BRACKET.search(blob)):
        return False
    return bool(_GROUPS_KEY_RX.search(blob) or _GROUPS_PREF_NAME.search(blob))


def _blob_writes_groups(src: str, blob: str, skip: frozenset[str] | None = None) -> bool:
    if _writes_groups_pref(blob):
        return True
    banned = skip or frozenset()
    seen: set[str] = set()
    for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob):
        if name in seen or name in banned:
            continue
        seen.add(name)
        inner = _fn_body(src, name)
        if inner and _writes_groups_pref(inner):
            return True
    return False


def _blob_reads_groups(src: str, blob: str) -> bool:
    if _reads_groups_pref(blob):
        return True
    seen: set[str] = set()
    for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob):
        if name in seen:
            continue
        seen.add(name)
        inner = _fn_body(src, name)
        if inner and _reads_groups_pref(inner):
            return True
    return False


def _groups_effect_writes(app: str) -> bool:
    for arg in _svelte_effect_args(app):
        if "includeGroups" in arg and _writes_groups_pref(arg):
            return True
    return False


def _closed_on_off(blob: str) -> bool:
    if _CLOSED_WRITE.search(blob):
        return True
    return bool(_SET_ON.search(blob) and _SET_OFF.search(blob))


def _mount_pref_head(mount: str) -> str:
    """onMount prefs before startPeopleBoot / first restoreLastPerson."""
    cuts = []
    for rx in (
        re.compile(r"\bstartPeopleBoot\s*\("),
        re.compile(r"\brestoreLastPerson\s*\("),
        re.compile(r"\bselectPerson\s*\("),
    ):
        m = rx.search(mount)
        if m:
            cuts.append(m.start())
    return mount[: min(cuts)] if cuts else mount


def assert_remember_include_groups(crate: Path) -> None:
    """#309: persist People include-groups in localStorage; restore on open."""
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#309: App.svelte required (include-groups restore / persist lives there)")
    prefs_path = crate / "web" / "lib" / "PeoplePrefs.ts"
    insp_path = crate / "web" / "lib" / "PeopleInspector.svelte"
    shell_path = crate / "web" / "lib" / "PeopleShell.svelte"
    tl_path = crate / "web" / "lib" / "TimelinePane.svelte"
    boot_path = crate / "web" / "lib" / "PeopleBoot.ts"
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    app_raw = app_path.read_text()
    app = _without_comments(app_raw)
    prefs = _without_comments(prefs_path.read_text()) if prefs_path.is_file() else ""
    insp = _without_comments(insp_path.read_text()) if insp_path.is_file() else ""
    shell = _without_comments(shell_path.read_text()) if shell_path.is_file() else ""
    tl = _without_comments(tl_path.read_text()) if tl_path.is_file() else ""
    boot = _without_comments(boot_path.read_text()) if boot_path.is_file() else ""
    search = _without_comments(search_path.read_text()) if search_path.is_file() else ""
    web = _without_comments(_web_logic(crate))
    combo = "\n".join([app, prefs, insp, shell, tl, boot])
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    session_path = repo_root() / "crates" / "interlace-core" / "src" / "session.rs"
    session = session_path.read_text() if session_path.is_file() else ""

    # 1) groups-pref-write — exact namespaced key, getItem + setItem.
    ls_keys = _ls_pref_keys(web)
    if _GROUPS_KEY not in ls_keys:
        fail(
            "#309: persist include groups in namespaced localStorage "
            "(getItem + setItem; interlace.includeGroups) — "
            "not write_last_path / config.toml / iCloud"
        )

    persist_surface = "\n".join(
        [
            _windows_around(web, _GROUPS_KEY_RX, before=160, after=220),
            _windows_around(web, _GROUPS_PREF_NAME, before=160, after=220),
            _windows_around(web, _WRITE_GROUPS, before=80, after=200),
            _windows_around(web, _READ_GROUPS, before=80, after=200),
            _fn_body(combo, "writeIncludeGroupsPref"),
            _fn_body(combo, "persistIncludeGroups"),
            _fn_body(combo, "readIncludeGroupsPref"),
        ]
    )

    if not _SETITEM.search(persist_surface):
        fail(
            "#309: persist include groups with localStorage.setItem "
            "(interlace.includeGroups; closed on/off token)"
        )
    if not _GETITEM.search(persist_surface) and not _LS_BRACKET.search(persist_surface):
        fail(
            "#309: restore include groups from localStorage.getItem "
            "(same interlace.includeGroups key)"
        )

    # 2) Closed on/off token; missing / wiped / junk → off.
    write_blob = persist_surface + "\n" + _fn_body(combo, "writeGroupsPref")
    if not _closed_on_off(write_blob):
        fail(
            "#309: write interlace.includeGroups as a closed on/off token "
            "(sidebar-style 1/0)"
        )
    read_blob = "\n".join(
        [
            persist_surface,
            _fn_body(combo, "readIncludeGroupsPref"),
            _fn_body(combo, "readGroupsPref"),
            _windows_around(web, _GETITEM, before=40, after=80),
        ]
    )
    if not _ON_TOKEN.search(read_blob):
        fail(
            "#309: missing / wiped / junk interlace.includeGroups must stay off "
            "(compare getItem to the on token; first-run stays off)"
        )

    # 3) Not config.toml / write_last_path / iCloud.
    if _LAST_PATH_API.search(persist_surface) or _CONFIG_TOML.search(persist_surface):
        fail(
            "#309: do not persist include groups via write_last_path / "
            "read_last_path / config.toml (localStorage only)"
        )
    if _ICLOUD.search(persist_surface):
        fail("#309: do not persist include groups to iCloud")
    if not session_path.is_file():
        fail("#309: crates/interlace-core/src/session.rs required (do not stash UI prefs there)")
    wl = _rust_fn_body(_without_comments(session), "write_last_path")
    if re.search(r"include_groups|includeGroups", wl, re.I):
        fail(
            "#309: do not rewrite session.rs write_last_path to dump include groups "
            "(config.toml is the last-archive pointer, not chrome prefs)"
        )
    extra = [k for k in _toml_keys_in_fn(wl) if "group" in k.lower()]
    if extra:
        fail(
            "#309: do not rewrite session.rs write_last_path to dump extra keys "
            "(include groups is not last_archive_path / config.toml)"
        )

    # 4) First-run default still off.
    if not _GROUPS_STATE_FALSE.search(app):
        fail(
            "#309: first-run includeGroups still defaults off "
            "($state(false); missing key → off)"
        )

    # 5) Inspector tick writes. Empty-state Include groups writes.
    if not insp_path.is_file():
        fail("#309: PeopleInspector.svelte required (include-groups checkbox)")
    if not _INSPECTOR_BIND.search(insp):
        fail(
            "#309: keep the People inspector include-groups checkbox "
            "(bind:checked={includeGroups})"
        )
    tick_surface = "\n".join(
        [
            insp,
            _arrow_prop(insp, "onchange"),
            _arrow_prop(shell, "onReloadPerson"),
            _fn_body(combo, "onReloadPerson"),
        ]
    )
    if not _blob_writes_groups(combo, tick_surface):
        fail(
            "#309: ticking the People inspector include-groups checkbox must "
            "setItem interlace.includeGroups"
        )
    empty_surface = "\n".join(
        [
            _arrow_prop(tl, "onIncludeGroups"),
            _fn_body(combo, "onIncludeGroups"),
        ]
    )
    if not _blob_writes_groups(combo, empty_surface):
        fail(
            "#309: empty-state Include groups must setItem interlace.includeGroups "
            "(same People pref)"
        )

    # 6) jumpToMessage auto-enable must not persist. No follow-every-assignment $effect.
    if _groups_effect_writes(app):
        fail(
            "#309: do not persist include groups from a bare $effect on includeGroups "
            "(jumpToMessage auto-enable and #308 setSetup would write; persist from "
            "the inspector tick and empty-state Include groups only)"
        )
    jump = _fn_body(app, "jumpToMessage") or _fn_body(app_raw, "jumpToMessage")
    if _blob_writes_groups(combo, jump, skip=_JUMP_SKIP):
        fail(
            "#309: jumpToMessage auto-enable must not setItem interlace.includeGroups "
            "(in-memory only)"
        )

    # 7) groups-restore-onmount — getItem at sidebar / density / last-view moment.
    mount = _onmount_body(app)
    if not mount.strip():
        fail(
            "#309: restore includeGroups at onMount "
            "(same moment as sidebar / density / last view)"
        )
    mount_head = _mount_pref_head(mount)
    if not _blob_reads_groups(combo, mount_head):
        fail(
            "#309: restore includeGroups at onMount "
            "(same moment as sidebar / density / last view) — "
            "getItem before restoreLastPerson / selectPerson"
        )

    # 8) groups-restore-before-load — first All / switcher sees the stored flag.
    refresh = _fn_body(app, "refreshPeople") or _fn_body(app_raw, "refreshPeople")
    people_at = None
    for m in re.finditer(r"\bpeople\s*=", refresh):
        people_at = m.start()
    after_people = refresh[people_at:] if people_at is not None else ""
    if _blob_reads_groups(combo, after_people) and not _blob_reads_groups(
        combo, mount_head
    ):
        fail(
            "#309: restore includeGroups before the first restoreLastPerson / "
            "selectPerson so All / the switcher can include groups "
            "(do not restore only after people =)"
        )

    # 9) groups-d24
    if not dtxt.strip():
        fail(
            "#309: docs/user/app.md required — include groups is remembered "
            "locally (localStorage, not iCloud)"
        )
    if not _DOCS_REMEMBER.search(dtxt):
        fail(
            "#309: docs/user/app.md must say include groups is remembered locally "
            "(localStorage)"
        )
    if not _DOCS_NOT_ICLOUD.search(dtxt):
        fail(
            "#309: docs/user/app.md must say include groups is remembered locally "
            "(not iCloud)"
        )

    # 10) groups-keep-212-276-305
    if not _KEEP_SIDEBAR.search(web):
        fail("#309: keep #212 sidebar persist (interlace.peopleSidebarCollapsed)")
    if not _KEEP_DENSITY.search(web):
        fail("#309: keep #276 density persist (interlace.density)")
    if not _KEEP_LAST_VIEW.search(web) or not _KEEP_LAST_PERSON.search(web):
        fail(
            "#309: keep #305 last view / last person keys "
            "(interlace.lastView / interlace.lastPersonId)"
        )
    if "restoreLastView" not in app or "restoreLastPerson" not in app:
        fail("#309: keep the #305 restore path (restoreLastView / restoreLastPerson)")
    if "persistSidebar" not in app or "persistDensity" not in app:
        fail("#309: keep persistSidebar / persistDensity (#212 / #276)")
    if "SIDEBAR_PREF" not in prefs or "DENSITY_PREF" not in prefs:
        fail("#309: keep SIDEBAR_PREF / DENSITY_PREF (#212 / #276)")
    if "LAST_VIEW_PREF" not in prefs or "LAST_PERSON_PREF" not in prefs:
        fail("#309: keep LAST_VIEW_PREF / LAST_PERSON_PREF (#305)")

    # 11) groups-keep-308-reset — in-memory false; leave the pref; re-read on Open B.
    setup_body = _arrow_prop(app, "setSetup") or _fn_body(app, "setSetup")
    if not _GROUPS_FALSE.search(setup_body):
        fail("#309: keep #308 in-memory includeGroups = false on setSetup(true)")
    switch = _fn_body(boot, "switchToSetup") or _fn_body(combo, "switchToSetup")
    for m in _REMOVE_ITEM.finditer(switch):
        window = switch[max(0, m.start() - 40) : m.end() + 80]
        if _GROUPS_KEY_RX.search(window) or _GROUPS_PREF_NAME.search(window):
            fail(
                "#309: do not removeItem interlace.includeGroups in switchToSetup "
                "(leave the pref)"
            )
    apply_st = _fn_body(app, "applyStatus") or _fn_body(app_raw, "applyStatus")
    apply_ok = _blob_reads_groups(combo, apply_st)
    rp_at = refresh.find("restoreLastPerson")
    refresh_head = refresh[: rp_at] if rp_at >= 0 else ""
    refresh_ok = bool(refresh_head.strip()) and _blob_reads_groups(combo, refresh_head)
    if not apply_ok and not refresh_ok:
        fail(
            "#309: on successful Open B (applyStatus / leave setup) re-read "
            "interlace.includeGroups so B’s first All / switcher load includes groups"
        )

    # 12) groups-search-separate — Search keeps its own unpersisted $state(false).
    search_blob = search or _without_comments(_search_pane_blob(crate))
    if not search_path.is_file():
        fail("#309: SearchPane.svelte required (own includeGroups, not the People pref)")
    if not _GROUPS_STATE_FALSE.search(search_blob):
        fail(
            "#309: SearchPane must keep its own unpersisted includeGroups = $state(false) "
            "(do not bind Search to the People pref)"
        )
    if (
        _GROUPS_KEY_RX.search(search_blob)
        or _GROUPS_PREF_NAME.search(search_blob)
        or _READ_GROUPS.search(search_blob)
        or _WRITE_GROUPS.search(search_blob)
        or _SETITEM.search(search_blob)
        or _GETITEM.search(search_blob)
        or _SEARCH_BIND.search(search_blob)
    ):
        fail(
            "#309: SearchPane must keep its own unpersisted includeGroups = $state(false) "
            "(do not persist Search; do not bind it to the People pref)"
        )
    if re.search(r"includeGroups", _open_tag(app_raw, "SearchPane")):
        fail(
            "#309: do not pass / bind App includeGroups into SearchPane "
            "(Search stays its own checkbox)"
        )
