"""Helpers extracted from reopen_last.py (reopen_last_lib)."""
from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.boot_helpers import _LS_CALL
from tauri_gate.import_boot_guards import _ls_pref_keys
from tauri_gate.scan import (
    _CONFIG_TOML,
    _LAST_PATH_API,
    _LS_BRACKET,
    _function_body,
    _match_closer,
    _rust_fn_body,
    _ts_fn_body,
    _ts_function_body,
    _web_logic,
    _without_comments,
)
from tauri_gate.status_toasts_toast import _svelte_effect_args
from tauri_gate.status_toasts_chrome import (
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
# #305 fold — view restore at onMount; no late view =; skip a taken person.
_VIEW_ASSIGN = re.compile(r"(?<![\w.$])view\s*=(?!=)")
_LAST_VIEW_TOKEN = re.compile(
    r"("
    r"\bLAST_VIEW(?:_PREF|_KEY)?\b"
    r"|\blastView\b"
    r"|\blast_view\b"
    r"|\blast-view\b"
    r"|interlace\.lastView"
    r"|\bLAST_SESSION(?:_PREF|_KEY)?\b"
    r"|\blastSession\b"
    r"|\blast_session\b"
    r")",
    re.I,
)
_VIEW_RESTORE_CALLEE = re.compile(
    r"(?i)restore|last(?:view|session)|readLast|applyLast"
)
_RESTORE_LAST_VIEW_NAME = re.compile(
    r"\b(?:restoreLastView|readLastView|applyLastView)\b"
)
_SELECT_PERSON_ONLY = re.compile(r"\bselectPerson\s*\(")
_PERSIST_LAST_PERSON_CALL = re.compile(
    r"\bpersistLast(?:Person|Session)\w*\s*\("
)
_PERSON_TAKEN_GUARD = re.compile(
    r"("
    r"if\s*\(\s*selectedId\s*(?:!=|!==)\s*(?:null|undefined)\s*\)"
    r"\s*(?:return\b|\{[^}]{0,120}return\b)"
    r"|if\s*\(\s*selectedId\s*\)\s*(?:return\b|\{[^}]{0,120}return\b)"
    r"|if\s*\(\s*!\s*selectedId\b"
    r"|if\s*\(\s*selectedId\s*==\s*null"
    r"|if\s*\(\s*selectedId\s*===\s*null"
    r"|selectedId\s*==\s*null"
    r"|selectedId\s*===\s*null"
    r"|selectedId\s*!=\s*(?:null|undefined)"
    r"|selectedId\s*!==\s*(?:null|undefined)"
    r"|!\s*selectedId\b"
    r")"
)
_ONMOUNT_PEOPLE_GATE = re.compile(
    r"("
    r"\bawait\b"
    r"|\bpeople\s*="
    r"|\brefreshPeople\s*\("
    r"|\bapi\s*\.\s*people\s*\("
    r")"
)
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


def _onmount_body(src: str) -> str:
    """Callback body of `onMount(() => { … })` (sidebar / density moment)."""
    m = re.search(r"\bonMount\s*\(", src)
    if not m:
        return ""
    open_p = m.end() - 1
    close = _match_closer(src, open_p)
    if close < 0:
        return ""
    arg = src[open_p + 1 : close]
    brace = arg.find("{")
    if brace < 0:
        return arg.strip()
    close_b = _match_closer(arg, brace)
    if close_b < 0:
        return arg[brace + 1 :]
    return arg[brace + 1 : close_b]


def _onmount_sync_prefix(mount: str) -> str:
    """onMount body before the first await / people rebuild (sync prefs)."""
    m = _ONMOUNT_PEOPLE_GATE.search(mount)
    return mount[: m.start()] if m else mount


def _expand_view_restore_callees(src: str, body: str) -> str:
    """Expand restoreLastView / readLastView only — never openPath."""
    chunks = [body]
    seen: set[str] = set()
    for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", body):
        if name in seen or name in _REOPEN_EXPAND_SKIP:
            continue
        if not _VIEW_RESTORE_CALLEE.search(name):
            continue
        seen.add(name)
        inner = _fn_body(src, name)
        if inner:
            chunks.append(inner)
    return "\n".join(chunks)


def _restores_last_view(blob: str) -> bool:
    """getItem / restoreLastView of last view — not sidebar / density."""
    if _RESTORE_LAST_VIEW_NAME.search(blob):
        return True
    has_read = bool(_GETITEM.search(blob) or _LS_BRACKET.search(blob))
    return bool(has_read and _LAST_VIEW_TOKEN.search(blob))


def _person_restore_blobs(app: str, refresh: str) -> str:
    """Restore helpers that selectPerson, plus the post-`people =` tail."""
    parts: list[str] = []
    for name in dict.fromkeys(_RESTORE_FN_NAME.findall(app)):
        body = _fn_body(app, name)
        if body and _SELECT_PERSON.search(body):
            parts.append(body)
    tail = _refresh_after_people(refresh)
    if tail.strip():
        parts.append(tail)
        parts.append(_expand_skip(app, tail))
    return "\n".join(parts)


def _person_restore_skips_taken(blob: str) -> bool:
    return bool(_PERSON_TAKEN_GUARD.search(blob))


def _jump_path_bodies(app: str) -> str:
    open_fn = _fn_body(app, "openPersonAtMessage")
    jump_fn = _fn_body(app, "jumpToMessage")
    return "\n".join(b for b in (open_fn, jump_fn) if b.strip())


def _jump_persists_last_person(app: str, reopen_keys: list[str]) -> bool:
    """Search-jump writes last person like non-append selectPerson."""
    blob = _jump_path_bodies(app)
    if not blob.strip():
        return False
    if _PERSIST_LAST_PERSON_CALL.search(blob) or _SELECT_PERSON_ONLY.search(blob):
        return True
    blob_x = _expand_skip(app, blob)
    return _writes_last_pref(blob_x, reopen_keys) or _writes_last_pref(
        blob, reopen_keys
    )

__all__ = [
    "_VIEW_NAMES",
    "_VIEW_UNION",
    "_KEEP_SIDEBAR_KEY",
    "_KEEP_DENSITY_KEY",
    "_KEEP_SIDEBAR_PREF",
    "_KEEP_DENSITY_PREF",
    "_SELECT_PERSON",
    "_NOT_APPEND",
    "_PEOPLE_ASSIGN",
    "_PEOPLE_HAS_ID",
    "_RAW_PERSON_TITLE",
    "_RESTORE_FN_NAME",
    "_PERSIST_FN_NAME",
    "_LAST_VIEW_WORD",
    "_SETITEM",
    "_GETITEM",
    "_VIEW_DEFAULT_PEOPLE",
    "_VIEW_FROM_RAW_LS",
    "_DOCS_LAST_VIEW",
    "_DOCS_LAST_PERSON",
    "_DOCS_REOPEN",
    "_OTHER_PREF",
    "_VIEW_ASSIGN",
    "_LAST_VIEW_TOKEN",
    "_VIEW_RESTORE_CALLEE",
    "_RESTORE_LAST_VIEW_NAME",
    "_SELECT_PERSON_ONLY",
    "_PERSIST_LAST_PERSON_CALL",
    "_PERSON_TAKEN_GUARD",
    "_ONMOUNT_PEOPLE_GATE",
    "_REOPEN_EXPAND_SKIP",
    "_fn_body",
    "_expand_skip",
    "_norm_key",
    "_reopen_key_ok",
    "_key_covers_view",
    "_key_covers_person",
    "_covers_view_and_person",
    "_ls_windows",
    "_named_fn_blobs",
    "_writes_last_pref",
    "_persist_has_view_union",
    "_refresh_after_people",
    "_restore_blob",
    "_unknown_view_falls_back",
    "_onmount_body",
    "_onmount_sync_prefix",
    "_expand_view_restore_callees",
    "_restores_last_view",
    "_person_restore_blobs",
    "_person_restore_skips_taken",
    "_jump_path_bodies",
    "_jump_persists_last_person",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_LS_CALL",
    "_ls_pref_keys",
    "_CONFIG_TOML",
    "_LAST_PATH_API",
    "_LS_BRACKET",
    "_rust_fn_body",
    "_web_logic",
    "_without_comments",
    "_svelte_effect_args",
    "_toml_keys_in_fn",
    "_windows_around",
    "annotations",
    "_function_body",
    "_match_closer",
    "_ts_fn_body",
    "_ts_function_body",
]
