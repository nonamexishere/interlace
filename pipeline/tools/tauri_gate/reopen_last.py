"""#305 — reopen last view + last person. Imported by gate_tauri.py.

PR #323 review fold: view restore at onMount (not after people =);
do not overwrite a user tab / taken person; persist last person from
the Search-jump path."""
from __future__ import annotations

from tauri_gate.reopen_last_lib import *


def assert_reopen_last_session(crate: Path) -> None:
    """#305: reopen on last view + last person (localStorage only).

    Persist people|search|review|import|doctor and the last selected
    person_id in namespaced localStorage (interlace.lastView +
    interlace.lastPersonId, or one JSON). Not write_last_path /
    config.toml / iCloud. Persist on view change and on selectPerson
    (not Load older / append). Restore after a successful refreshPeople
    so existence is people.some(id). Missing / invalid id → no select.
    Unknown stored view → people. First run → today’s empty People.
    Missing person must not set a raw `person ${id}` title. Keep #212
    sidebar and #276 density keys. Docs: reopen last view + last person.

    PR #323 review fold: view restore is getItem / restoreLastView at
    onMount (sidebar/density moment), not after people =. A user tab
    taken before the list arrives is kept (no view = after people =).
    Person restore still waits on people = + people.some; skip if
    selectedId is already taken. openPersonAtMessage / Search-jump
    persists last person the same way a non-append selectPerson does.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#305: App.svelte required (reopen last view / last person lives there)")
    app = _web_logic(crate)
    app_clean = _without_comments(app)
    logic = _web_logic(crate)
    logic_clean = _without_comments(logic)
    web = app_clean + "\n" + logic_clean
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    session_path = repo_root() / "crates" / "interlace-core" / "src" / "session.rs"
    session = session_path.read_text() if session_path.is_file() else ""

    # 1) Namespaced localStorage keys for last view + last person (or one JSON).
    ls_keys = _ls_pref_keys(web)
    reopen_keys = [k for k in ls_keys if _reopen_key_ok(k)]
    if not _covers_view_and_person(reopen_keys):
        fail(
            "#305: persist last view and last person in namespaced localStorage "
            "(getItem + setItem; e.g. interlace.lastView + interlace.lastPersonId, "
            "or one JSON) — not write_last_path / config.toml / iCloud"
        )

    persist_fn = _named_fn_blobs(app_clean, _PERSIST_FN_NAME)
    persist_surface = "\n".join(
        [
            persist_fn,
            _ls_windows(web),
            _windows_around(web, _LS_CALL, before=80, after=160),
        ]
    )

    # 2) Both setItem (write) and getItem (restore) on those keys.
    if not _SETITEM.search(persist_surface):
        fail(
            "#305: persist last view / last person with localStorage.setItem "
            "(namespaced key; not iCloud, not write_last_path)"
        )
    if not _GETITEM.search(persist_surface) and not _LS_BRACKET.search(persist_surface):
        fail(
            "#305: restore last view / last person from localStorage.getItem "
            "(same namespaced key)"
        )

    # 3) Not write_last_path / config.toml.
    if _LAST_PATH_API.search(persist_surface) or _CONFIG_TOML.search(persist_surface):
        fail(
            "#305: do not persist last view / last person via write_last_path / "
            "read_last_path / config.toml (localStorage only)"
        )
    if not session_path.is_file():
        fail("#305: crates/interlace-core/src/session.rs required (do not stash UI prefs there)")
    wl = _rust_fn_body(_without_comments(session), "write_last_path")
    if re.search(r"\b(?:last_view|last_person|last_person_id|last_session)\b", wl, re.I):
        fail(
            "#305: do not rewrite session.rs write_last_path to dump last view / "
            "last person (config.toml is the last-archive pointer, not chrome prefs)"
        )
    extra = [
        k
        for k in _toml_keys_in_fn(wl)
        if k not in {"last_archive_path"}
        and re.search(r"view|person|session|reopen", k, re.I)
    ]
    if extra:
        fail(
            "#305: do not rewrite session.rs write_last_path to dump extra keys "
            "(last view / last person are not last_archive_path / config.toml)"
        )

    # 4) View union people|search|review|import|doctor is what gets persisted.
    if not _VIEW_UNION.search(app_clean):
        fail(
            "#305: persist the people|search|review|import|doctor view union "
            "(unknown stored view → people)"
        )
    view_persist = "\n".join(
        [
            persist_fn,
            _windows_around(persist_surface, _LAST_VIEW_WORD, before=120, after=200),
            _windows_around(persist_surface, _SETITEM, before=80, after=160),
        ]
    )
    if not _persist_has_view_union(view_persist):
        fail(
            "#305: persist the people|search|review|import|doctor view "
            "(setItem last view / last session from `view`, not a different union)"
        )

    # 5) Persist last view when view changes — not only inside selectPerson.
    select = _fn_body(app_clean, "selectPerson") or _fn_body(app, "selectPerson")
    select_x = _expand_skip(app_clean, select) if select else ""
    outside_select = web.replace(select, "") if select else web
    view_effects = [
        a
        for a in _svelte_effect_args(app_clean)
        if re.search(r"(?<![\w.])view(?![\w-])", a)
    ]
    view_write = "\n".join(
        [persist_fn, outside_select, "\n".join(view_effects)]
    )
    if not _writes_last_pref(view_write, reopen_keys):
        fail(
            "#305: persist last view when `view` changes "
            "($effect / persistLastView — not only inside selectPerson)"
        )

    # 6) Persist person id on select (not only on view; not Load older / append).
    if not select.strip():
        fail("#305: selectPerson required (persist last person_id when a person is selected)")
    if not _writes_last_pref(select_x, reopen_keys) and not _writes_last_pref(
        select, reopen_keys
    ):
        fail(
            "#305: persist last person_id from selectPerson "
            "(not only on view change; not Load older / append)"
        )
    persist_in_select = "\n".join(
        [
            _windows_around(select_x, _SETITEM, before=120, after=160),
            _windows_around(select_x, _PERSIST_FN_NAME, before=80, after=160),
            _windows_around(select_x, _LAST_VIEW_WORD, before=80, after=160),
        ]
    )
    if not _NOT_APPEND.search(persist_in_select) and not _NOT_APPEND.search(select):
        fail(
            "#305: persist last person_id when selectPerson selects "
            "(not Load older / append)"
        )

    # 7) Restore after a successful refreshPeople.
    refresh = _fn_body(app_clean, "refreshPeople") or _fn_body(app, "refreshPeople")
    if not refresh.strip():
        fail("#305: refreshPeople required (restore after a successful people list)")
    if not _PEOPLE_ASSIGN.search(refresh):
        fail("#305: restore last view / last person after refreshPeople assigns `people`")
    refresh_x = _expand_skip(app_clean, refresh)
    restore = _restore_blob(app_clean, refresh_x)
    restore_x = _expand_skip(app_clean, restore)
    if not (
        _RESTORE_FN_NAME.search(refresh)
        or _GETITEM.search(restore_x)
        or _LS_BRACKET.search(restore_x)
        or _LAST_VIEW_WORD.search(restore_x)
    ):
        fail(
            "#305: restore last view / last person after a successful refreshPeople "
            "(existence is people.some(id); do not restore from onMount before the list)"
        )

    # 8) selectPerson / equivalent only if that id is in the loaded people list.
    if _SELECT_PERSON.search(restore) and not _PEOPLE_HAS_ID.search(restore_x):
        fail(
            "#305: restore must call selectPerson only if that id is in the "
            "loaded people list (people.some / people.find)"
        )
    if _SELECT_PERSON.search(restore_x) and not _PEOPLE_HAS_ID.search(restore_x):
        fail(
            "#305: restore must call selectPerson only if that id is in the "
            "loaded people list (people.some / people.find)"
        )

    # 9) Missing person does not set a raw `person ${id}` title on the restore path.
    if _RAW_PERSON_TITLE.search(restore):
        fail(
            "#305: missing / invalid last person must not set a raw "
            "`person ${id}` title (no select; People if the stored view was people)"
        )

    # 10) Unknown stored view → people. First run / empty → People, no select.
    if not _VIEW_DEFAULT_PEOPLE.search(app_clean):
        fail(
            "#305: first run / empty localStorage must open People "
            "(view still defaults to people)"
        )
    if not _unknown_view_falls_back(restore_x if restore_x.strip() else restore):
        fail("#305: unknown stored view must fall back to people")

    # 11) Docs: reopen restores last view + last person if they still exist.
    if not dtxt.strip():
        fail(
            "#305: docs/user/app.md required — reopen restores last view and "
            "last person if they still exist"
        )
    if not _DOCS_LAST_VIEW.search(dtxt):
        fail("#305: docs/user/app.md must say reopen restores the last view")
    if not _DOCS_LAST_PERSON.search(dtxt):
        fail(
            "#305: docs/user/app.md must say reopen restores the last person "
            "if they still exist"
        )
    if not _DOCS_REOPEN.search(dtxt):
        fail(
            "#305: docs/user/app.md must say reopen restores last view / last person"
        )

    # 12) Keep #212 sidebar + #276 density persist keys.
    if not _KEEP_SIDEBAR_KEY.search(web) or not _KEEP_SIDEBAR_PREF.search(app_clean):
        fail(
            "#305: keep #212 sidebar persist "
            "(SIDEBAR_PREF / interlace.peopleSidebarCollapsed)"
        )
    if not _KEEP_DENSITY_KEY.search(web) or not _KEEP_DENSITY_PREF.search(app_clean):
        fail(
            "#305: keep #276 density persist "
            "(DENSITY_PREF / interlace.density)"
        )
    if not _fn_body(app_clean, "persistSidebar") or not _fn_body(app_clean, "persistDensity"):
        fail("#305: keep persistSidebar / persistDensity (#212 / #276)")

    # 13) View restore is getItem / restoreLastView at onMount — not after
    #     refreshPeople / people = (PR #323 review fold).
    mount = _onmount_body(app_clean)
    if not mount.strip():
        fail(
            "#305: restore last view at onMount (same moment as sidebar/density) "
            "— getItem / restoreLastView must not wait on refreshPeople / people ="
        )
    mount_sync = _onmount_sync_prefix(mount)
    mount_x = _expand_view_restore_callees(app_clean, mount_sync)
    if not _restores_last_view(mount_x):
        fail(
            "#305: restore last view at onMount (same moment as sidebar/density) "
            "— getItem / restoreLastView must not wait on refreshPeople / people ="
        )

    # 14) A user tab taken before the list arrives is kept (A never assigns
    #     view after people =).
    people_tail = _refresh_after_people(refresh_x)
    people_tail_x = _expand_skip(app_clean, people_tail)
    if _VIEW_ASSIGN.search(people_tail) or _VIEW_ASSIGN.search(people_tail_x):
        fail(
            "#305: if view changed before the people list arrives, restore "
            "must not overwrite that tab — do not assign view after people ="
        )

    # 15) Person restore must not overwrite a person already taken.
    person_restore = _person_restore_blobs(app_clean, refresh_x)
    if _SELECT_PERSON.search(person_restore) and not _person_restore_skips_taken(
        person_restore
    ):
        fail(
            "#305: person restore must not overwrite a person already taken "
            "(selectedId already set) — skip selectPerson when the user "
            "jumped or clicked first"
        )

    # 16) Search-jump / openPersonAtMessage writes last person like
    #     non-append selectPerson.
    if not _jump_persists_last_person(app_clean, reopen_keys):
        fail(
            "#305: openPersonAtMessage / Search-jump must persist last person "
            "the same way a non-append selectPerson does"
        )
