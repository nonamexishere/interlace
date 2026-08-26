"""#305 — reopen last view + last person. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.boot_helpers import _LS_CALL
from tauri_gate.import_boot import _ls_pref_keys
from tauri_gate.scan import (
    _CONFIG_TOML,
    _LAST_PATH_API,
    _LS_BRACKET,
    _function_body,
    _rust_fn_body,
    _ts_fn_body,
    _ts_function_body,
    _web_logic,
    _without_comments,
)
from tauri_gate.status_toasts import (
    _svelte_effect_args,
    _toml_keys_in_fn,
    _windows_around,
)

# #305 — last view + last person_id in namespaced localStorage (not iCloud).
_VIEW_NAMES = ("people", "search", "review", "import", "doctor")
_VIEW_UNION = re.compile(
    r"[\"']people[\"']\s*\|\s*[\"']search[\"']\s*\|\s*[\"']review[\"']"
    r"\s*\|\s*[\"']import[\"']\s*\|\s*[\"']doctor[\"']"
)
_KEEP_SIDEBAR_KEY = re.compile(r"interlace\.peopleSidebarCollapsed")
_KEEP_DENSITY_KEY = re.compile(r"interlace\.density")
_KEEP_SIDEBAR_PREF = re.compile(r"\bSIDEBAR_PREF\b")
_KEEP_DENSITY_PREF = re.compile(r"\bDENSITY_PREF\b")
_SELECT_PERSON = re.compile(r"\b(?:selectPerson|personShow)\s*\(")
_NOT_APPEND = re.compile(r"!\s*append\b")
_PEOPLE_ASSIGN = re.compile(r"\bpeople\s*=")
_PEOPLE_HAS_ID = re.compile(
    r"("
    r"\bpeople\s*\.\s*(?:some|find|map)\s*\("
    r"|\bnew\s+Set\s*\(\s*people"
    r"|\bids\s*\.\s*has\s*\("
    r")"
)
_RAW_PERSON_TITLE = re.compile(
    r"("
    r"person\s*\$\{"
    r"|personTitle\s*=\s*[`'\"].{0,8}person"
    r")"
)
_RESTORE_FN_NAME = re.compile(
    r"\b(restoreLast\w*|restoreSession|applyLastSession|readLastSession)\b"
)
_PERSIST_FN_NAME = re.compile(
    r"\b(persistLast\w*|persistSession|writeLastSession|saveLastSession)\b"
)
_LAST_VIEW_WORD = re.compile(
    r"("
    r"\blastView\b"
    r"|\blast_view\b"
    r"|\blast-view\b"
    r"|\blastPerson(?:Id)?\b"
    r"|\blast_person(?:_id)?\b"
    r"|\blastSession\b"
    r"|\blast_session\b"
    r"|\breopen\b"
    r")",
    re.I,
)
_SETITEM = re.compile(r"localStorage\s*\.\s*setItem\s*\(")
_GETITEM = re.compile(r"localStorage\s*\.\s*getItem\s*\(")
_VIEW_DEFAULT_PEOPLE = re.compile(
    r"("
    r"\bview\s*=\s*\$state(?:<[^>]*>)?\s*\(\s*[\"']people[\"']"
    r"|(?:let|const|var)\s+view\b[^=]*=\s*[\"']people[\"']"
    r")"
)
_VIEW_FROM_RAW_LS = re.compile(
    r"\bview\s*=\s*(?:localStorage\s*\.\s*getItem|JSON\.parse\s*\(\s*localStorage)"
)
_DOCS_LAST_VIEW = re.compile(r"\blast view\b", re.I)
_DOCS_LAST_PERSON = re.compile(r"\blast(?: selected)? person\b", re.I)
_DOCS_REOPEN = re.compile(
    r"("
    r"\breopen(?:s|ed|ing)?\b.{0,80}\b(?:last|person|view|session)\b"
    r"|\b(?:last|person|view|session)\b.{0,80}\breopen(?:s|ed|ing)?\b"
    r"|\brestores?\b.{0,40}\blast\b"
    r")",
    re.I | re.S,
)
_OTHER_PREF = ("sidebar", "collapsed", "density", "comfortable")
_REOPEN_EXPAND_SKIP = frozenset(
    {
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "function",
        "setItem",
        "getItem",
        "removeItem",
        "JSON",
        "Number",
        "String",
        "Boolean",
        "parseInt",
        "parseFloat",
        "isFinite",
        "isNaN",
        "void",
        "typeof",
        "document",
        "window",
        "localStorage",
        "console",
        "Error",
        "Map",
        "Set",
        "Date",
        "Object",
        "Array",
        "selectPerson",
        "personShow",
        "showErr",
        "api",
    }
)


def _fn_body(src: str, name: str) -> str:
    return (
        _ts_function_body(src, name)
        or _ts_fn_body(src, name)
        or _function_body(src, name)
    )


def _expand_skip(src: str, body: str, depth: int = 2) -> str:
    """Named helpers, but never selectPerson / personShow (raw-title lives there)."""
    chunks = [body]
    seen: set[str] = set()

    def walk(blob: str, left: int) -> None:
        for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob):
            if name in seen or name in _REOPEN_EXPAND_SKIP:
                continue
            seen.add(name)
            inner = _fn_body(src, name)
            if not inner:
                continue
            chunks.append(inner)
            if left > 0:
                walk(inner, left - 1)

    walk(body, depth)
    return "\n".join(chunks)


def _norm_key(key: str) -> str:
    return key.lower().replace("-", "").replace("_", "")


def _reopen_key_ok(key: str) -> bool:
    """Namespaced last-view / last-person / last-session key. Not sidebar/density."""
    low = _norm_key(key)
    if any(h in low for h in _OTHER_PREF):
        return False
    namespaced = "interlace" in low or "." in key
    if not namespaced:
        return False
    if "reopen" in low or "lastsession" in low:
        return True
    return "last" in low and any(t in low for t in ("view", "person", "session"))


def _key_covers_view(key: str) -> bool:
    low = _norm_key(key)
    return any(t in low for t in ("view", "session", "reopen"))


def _key_covers_person(key: str) -> bool:
    low = _norm_key(key)
    return any(t in low for t in ("person", "session", "reopen"))


def _covers_view_and_person(keys: list[str]) -> bool:
    return any(_key_covers_view(k) for k in keys) and any(
        _key_covers_person(k) for k in keys
    )


def _ls_windows(src: str) -> str:
    return "\n".join(
        [
            _windows_around(src, re.compile(r"localStorage"), before=160, after=220),
            _windows_around(src, _LAST_VIEW_WORD, before=160, after=220),
            _windows_around(src, _PERSIST_FN_NAME, before=80, after=200),
            _windows_around(src, _RESTORE_FN_NAME, before=80, after=200),
        ]
    )


def _named_fn_blobs(src: str, rx: re.Pattern[str]) -> str:
    names = list(dict.fromkeys(rx.findall(src)))
    return "\n".join(_fn_body(src, n) for n in names if _fn_body(src, n))


def _writes_last_pref(blob: str, keys: list[str]) -> bool:
    if _SETITEM.search(blob) and (
        _LAST_VIEW_WORD.search(blob) or any(k in blob for k in keys)
    ):
        return True
    return bool(_PERSIST_FN_NAME.search(blob) and _SETITEM.search(blob))


def _persist_has_view_union(blob: str) -> bool:
    if all(re.search(rf"[\"']{n}[\"']", blob) for n in _VIEW_NAMES):
        return True
    if re.search(r"setItem\s*\([^;]{0,160}\bview\b", blob):
        return True
    return bool(re.search(r"JSON\.stringify\s*\(\s*\{[^}]{0,200}\bview\b", blob))


def _refresh_after_people(body: str) -> str:
    last = None
    for m in _PEOPLE_ASSIGN.finditer(body):
        last = m
    return body[last.start() :] if last else ""


def _restore_blob(app: str, refresh: str) -> str:
    named = _named_fn_blobs(app, _RESTORE_FN_NAME)
    tail = _refresh_after_people(refresh)
    effects = [
        a
        for a in _svelte_effect_args(app)
        if _LAST_VIEW_WORD.search(a) or _RESTORE_FN_NAME.search(a)
    ]
    return "\n".join([named, tail, "\n".join(effects)])


def _unknown_view_falls_back(blob: str) -> bool:
    if _VIEW_FROM_RAW_LS.search(blob):
        return False
    if re.search(
        r"(?:includes|has)\s*\([^)]{0,80}\)\s*\?\s*\w+\s*:\s*[\"']people[\"']",
        blob,
    ):
        return True
    if all(re.search(rf"[\"']{n}[\"']", blob) for n in _VIEW_NAMES) and re.search(
        r"[\"']people[\"']", blob
    ):
        return True
    return bool(
        re.search(r"\bview\s*=\s*[\"']people[\"']", blob)
        or re.search(r":\s*[\"']people[\"']", blob)
    )


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
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#305: App.svelte required (reopen last view / last person lives there)")
    app = app_path.read_text()
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
