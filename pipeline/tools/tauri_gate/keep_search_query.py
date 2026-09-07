"""#318 — keep last Search query when leaving the tab (session-only).

Confirmed mix: SearchPane still remounts. Parent `searchQ` already
lives on App and binds to chrome + `bind:q`. Remount must not write
`$bindable("")` back over a non-empty parent `searchQ`. Hits refresh
once via the existing `#270` `$effect` → `run()` (debounce OK). Do
not `clearHitsIdle` a restored non-empty `q`. Do not persist. Do not
lift hits / filters / keep-alive. Close-to-setup still `searchQ = ""`.
Placeholders Ada only.

Must-IDs: keep-q-roundtrip, keep-hits-refresh-once, keep-session-only,
keep-308-reset, keep-208, keep-270, keep-273, keep-209, keep-d24.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.import_boot_guards import _ls_pref_keys
from tauri_gate.reopen_last_lib import _GETITEM, _SETITEM
from tauri_gate.scan import (
    _CONFIG_TOML,
    _LAST_PATH_API,
    _function_body,
    _match_closer,
    _svelte_markup,
    _template_stack,
    _ts_fn_body,
    _web_logic,
    _without_comments,
)
from tauri_gate.search_field_keys import (
    _API_SEARCH_CALL,
    _CHROME_SEARCH_HOOK,
    _INVOKE_SEARCH_CMD,
    _SEARCH_Q_TOKEN,
    _SPOTLIGHT_WORD,
    _has_search_as_you_type,
    _search_q_open_tag,
)
from tauri_gate.search_picker_lib import _SEARCH_FILTERS_HOOK, _SEARCH_Q_ID
from tauri_gate.status_toasts_chrome import _claim_without_negation, _windows_around
from tauri_gate.status_toasts_toast import _svelte_effect_args

_ISSUE = "#318"
_Q_BINDABLE_EMPTY = re.compile(
    r"\bq\s*=\s*\$bindable\s*(?:<[^>]*>)?\s*\(\s*(?:\"\"|''|``)\s*\)"
)
_SEARCHQ_STATE = re.compile(
    r"\blet\s+searchQ\s*=\s*\$state(?:<[^>]*>)?\s*\("
)
_BIND_Q_SEARCHQ = re.compile(r"bind:q\s*=\s*\{searchQ\}")
_BIND_VALUE_Q = re.compile(r"bind:value\s*=\s*\{q\}")
_SEARCHQ_CLEAR = re.compile(r"\bsearchQ\s*=\s*(?:\"\"|''|``)")
_SETUP_RESET = re.compile(
    r"\bsetSetup\b|\bsetup\s*=\s*true\b|\bif\s*\(\s*v\s*\)"
)
_Q_TRIM = r"(?:query|q)\s*(?:\?|\.)\s*trim\s*\(\s*\)"
_IF_EMPTY_Q = re.compile(rf"if\s*\(\s*!\s*{_Q_TRIM}\s*\)")
_IF_NONEMPTY_Q = re.compile(rf"if\s*\(\s*{_Q_TRIM}\s*\)")
_CLEAR_IDLE = re.compile(r"\bclearHitsIdle\s*\(")
_RUN_OR_SEARCH = re.compile(r"\brun\s*\(|\bapi\.search\s*\(")
_SEARCH_GEN = re.compile(r"\bsearchGen\b")
_SEARCH_GEN_INC = re.compile(r"\+\+\s*searchGen|\bsearchGen\s*\+\+")
_SESSION_STORE = re.compile(r"\bsessionStorage\b")
_ICLOUD = re.compile(r"\biCloud\b|CloudKit|NSUbiquitous")
_PERSIST_Q_HITS = re.compile(
    r"("
    r"\bsearchQ\b"
    r"|\blastQuery\b"
    r"|\blastSearchQ\b"
    r"|\bsearchHits\b"
    r"|\blastHits\b"
    r"|\bkeepSearch\b"
    r"|\bsavedQuery\b"
    r"|interlace\.(?:lastQuery|searchQ|searchHits|lastSearch|keepSearch)"
    r"|LAST_SEARCH|SEARCH_Q_PREF|SEARCH_HITS_PREF"
    r")",
    re.I,
)
_Q_HITS_KEY = re.compile(
    r"("
    r"last(?:Search)?(?:Q|Query)|searchQ|searchHits|lastHits|"
    r"keepSearch|searchSession|savedQuery|lastQuery"
    r")",
    re.I,
)
_ALLOWED_LS = frozenset(
    {
        "interlace.peopleSidebarCollapsed",
        "interlace.density",
        "interlace.lastView",
        "interlace.lastPersonId",
        "interlace.includeGroups",
        "interlace.peopleSort",
    }
)
_BUBBLE_NAME_Q = re.compile(r"\bsearchQ\s*=\s*\w+\.display_name\b")
_BUBBLE_BODY_Q = re.compile(r"\bsearchQ\s*=\s*.{0,80}\bbody_text\b")
_DOCS_LEAVE_BACK = re.compile(
    r"("
    r"(?:leave|leaving)\s+Search.{0,240}"
    r"(?:come back|return(?:ing)?|back to Search).{0,240}"
    r"(?:last query|query (?:is )?still|still (?:be )?there|#q)"
    r"|"
    r"(?:come back|return(?:ing)?)\s+(?:to\s+)?Search.{0,200}"
    r"(?:last query|query (?:is )?still|still there)"
    r")",
    re.I | re.S,
)
_DOCS_REFRESH_ONCE = re.compile(
    r"("
    r"hits.{0,80}refresh(?:es)?\s+once"
    r"|refresh(?:es)?\s+once.{0,80}hits"
    r")",
    re.I | re.S,
)
_DOCS_SAME_SESSION = re.compile(r"same session", re.I)
_MULTI_TAB = re.compile(r"\bmulti[- ]tab\b", re.I)
_SURVIVES_QUIT = re.compile(
    r"survives?\s+quit|across\s+quit|after\s+(?:a\s+)?quit",
    re.I,
)
_ONMOUNT_CALL = re.compile(r"\bonMount\s*\(")


def _read(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _skip_ws(src: str, i: int) -> int:
    n = len(src)
    while i < n and src[i] in " \t\n\r":
        i += 1
    return i


def _stmt_or_block(src: str, i: int) -> tuple[str, int]:
    i = _skip_ws(src, i)
    if i >= len(src):
        return "", i
    if src[i] == "{":
        close = _match_closer(src, i)
        if close < 0:
            return src[i + 1 :], len(src)
        return src[i + 1 : close], close + 1
    j = i
    n = len(src)
    depth = 0
    while j < n:
        c = src[j]
        if c in "{(":
            depth += 1
        elif c in "})":
            if depth == 0:
                break
            depth -= 1
        elif c == ";" and depth == 0:
            j += 1
            break
        j += 1
    return src[i:j], j


def _parse_if(src: str, if_start: int) -> tuple[str, str, str, int]:
    """`if (cond) then [else else]` → (cond, then, else, end)."""
    p = src.find("(", if_start)
    if p < 0:
        return "", "", "", if_start
    pc = _match_closer(src, p)
    if pc < 0:
        return "", "", "", if_start
    cond = src[p + 1 : pc]
    then, j = _stmt_or_block(src, pc + 1)
    j = _skip_ws(src, j)
    else_body = ""
    if src.startswith("else", j) and (
        j + 4 >= len(src) or not (src[j + 4].isalnum() or src[j + 4] in "_$")
    ):
        else_body, j = _stmt_or_block(src, j + 4)
    return cond, then, else_body, j


def _search_pane_remounts(app_markup: str) -> bool:
    """True if `<SearchPane>` is gated on `view === "search"` (destroyed on leave)."""
    m = re.search(r"<SearchPane\b", app_markup)
    if not m:
        return False
    for kind, cond, _extra in _template_stack(app_markup, m.start()):
        if kind == "if" and re.search(r"view\s*===?\s*[\"']search[\"']", cond):
            return True
        if kind == "if-else" and re.search(
            r"view\s*!==?\s*[\"']search[\"']", cond
        ):
            return True
    return False


def _q_bindable_empty_default(search: str) -> bool:
    return bool(_Q_BINDABLE_EMPTY.search(search))


def _is_state_init(src: str, pos: int) -> bool:
    pre = src[max(0, pos - 80) : pos]
    return bool(
        re.search(r"\$state(?:<[^>]*>)?\s*\(\s*$", pre)
        or re.search(r"(?:let|const|var)\s+searchQ\s*=\s*$", pre)
    )


def _in_setup_reset(src: str, pos: int) -> bool:
    window = src[max(0, pos - 600) : pos + 40]
    return bool(_SETUP_RESET.search(window))


def _searchq_clear_sites(app: str) -> list[int]:
    return [
        m.start()
        for m in _SEARCHQ_CLEAR.finditer(app)
        if not _is_state_init(app, m.start())
    ]


def _q_effect_blobs(src: str) -> list[str]:
    out: list[str] = []
    for arg in _svelte_effect_args(src):
        if not _SEARCH_Q_TOKEN.search(arg):
            continue
        if re.search(r"\b(?:run|clearHitsIdle|api\.search)\b", arg) or not re.search(
            r"\bseedPerson\b", arg
        ):
            out.append(arg)
    return out


def _q_effect_paths(effect: str) -> tuple[str, str]:
    """(empty-q body, non-empty-q body) from the `#270` `$effect`."""
    m = _IF_EMPTY_Q.search(effect)
    if m:
        _cond, then, els, end = _parse_if(effect, m.start())
        nonempty = els if els.strip() else effect[end:]
        return then, nonempty
    m = _IF_NONEMPTY_Q.search(effect)
    if m:
        _cond, then, els, _end = _parse_if(effect, m.start())
        return els, then
    return "", effect


def _onmount_blob(src: str) -> str:
    m = _ONMOUNT_CALL.search(src)
    if not m:
        return ""
    close = _match_closer(src, m.end() - 1)
    if close < 0:
        return ""
    return src[m.end() : close]


def _persist_windows(src: str) -> str:
    parts = [
        _windows_around(src, _SETITEM, before=80, after=160),
        _windows_around(src, _GETITEM, before=80, after=160),
        _windows_around(src, _SESSION_STORE, before=80, after=160),
        _windows_around(src, _CONFIG_TOML, before=80, after=160),
        _windows_around(src, _LAST_PATH_API, before=80, after=160),
        _windows_around(src, _ICLOUD, before=40, after=80),
    ]
    return "\n".join(p for p in parts if p.strip())


def assert_keep_search_query(crate: Path) -> None:
    """#318: leave Search and come back → last `#q` stays; hits refresh once.

    Session RAM only (`searchQ` on App). Remount-safe `q` bindable (no
    empty default write-back). Existing `run()` / `api.search` once on
    remount with a non-empty restored `q` (debounce OK). Do not
    `clearHitsIdle` that `q`. No new persist key. Close-to-setup still
    `searchQ = ""`. Keep `#208` / `#270` / `#273` / `#209`. D24.
    Do not lift hits / filters / keep-alive. Do not rewrite those asserts.
    """
    app_path = crate / "web" / "App.svelte"
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    nav_path = crate / "web" / "lib" / "PeopleNav.svelte"
    prefs_path = crate / "web" / "lib" / "PeoplePrefs.ts"
    if not app_path.is_file():
        fail(f"{_ISSUE}: App.svelte required (session searchQ lives on the shell)")
    if not search_path.is_file():
        fail(f"{_ISSUE}: SearchPane.svelte required (#q / remount-safe q bind)")

    app_only = app_path.read_text()
    search_only = search_path.read_text()
    nav = _read(nav_path)
    prefs = _read(prefs_path)
    app_clean = _without_comments(app_only)
    search_clean = _without_comments(search_only)
    nav_clean = _without_comments(nav)
    prefs_clean = _without_comments(prefs)
    app_markup = _svelte_markup(app_only)
    search_markup = _svelte_markup(search_only)
    search_surface = search_markup if search_markup.strip() else search_only
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    remounts = _search_pane_remounts(app_markup)

    # 1) keep-q-roundtrip — remount-safe keep (primary red today).
    #    SearchPane still remounts. `$bindable("")` writes empty back
    #    over a leftover parent searchQ. Do not lock keep-alive: if the
    #    pane is no longer view-gated, this arm does not apply.
    if remounts and _q_bindable_empty_default(search_clean):
        fail(
            f"{_ISSUE}: remount-safe keep required — SearchPane "
            "q = $bindable(\"\") writes the empty default back over parent "
            "searchQ (use $bindable() without an empty default so remount "
            "binds the same searchQ / #q)"
        )

    # 2) Same `searchQ` / `q` / `#q` bind. Chrome must not steal id="q".
    if not _SEARCHQ_STATE.search(app_clean):
        fail(
            f"{_ISSUE}: App.svelte must keep session searchQ = $state "
            "(chrome + SearchPane bind the same string)"
        )
    mount = _windows_around(app_markup, re.compile(r"<SearchPane\b"), before=0, after=500)
    if not _BIND_Q_SEARCHQ.search(mount) and not _BIND_Q_SEARCHQ.search(app_markup):
        fail(
            f"{_ISSUE}: remount must bind the same q / searchQ "
            "(<SearchPane bind:q={{searchQ}}>)"
        )
    q_tag = _search_q_open_tag(search_surface) or _search_q_open_tag(search_only)
    if not _SEARCH_Q_ID.search(search_surface) and not re.search(
        r"id=[\"']q[\"']", search_only
    ):
        fail(f'{_ISSUE}: SearchPane must keep id="q" as the canonical query field')
    if q_tag and not _BIND_VALUE_Q.search(q_tag):
        fail(f"{_ISSUE}: #q must bind:value={{q}} (same string as parent searchQ)")
    if re.search(r"id=[\"']q[\"']", app_markup):
        fail(
            f'{_ISSUE}: #q stays on SearchPane — do not steal id="q" onto chrome'
        )
    if nav and re.search(r"id=[\"']q[\"']", _svelte_markup(nav)):
        fail(
            f'{_ISSUE}: #q stays on SearchPane — do not steal id="q" onto PeopleNav'
        )

    # 3) Leaving Search (People / other view) does not assign searchQ = ""
    #    except close-to-setup (#308).
    if _SEARCHQ_CLEAR.search(nav_clean):
        fail(
            f"{_ISSUE}: PeopleNav must not assign searchQ = \"\" on a tab flip "
            "(leave Search does not wipe the query except close-to-setup)"
        )
    for pos in _searchq_clear_sites(app_clean):
        if not _in_setup_reset(app_clean, pos):
            fail(
                f"{_ISSUE}: leaving Search (People / other view) must not "
                "assign searchQ = \"\" — only close-to-setup (#308) clears it"
            )

    # 4) keep-hits-refresh-once — remount with non-empty q calls existing
    #    run() / api.search once (debounce OK). Must not clearHitsIdle a
    #    restored non-empty q. Do not require lifted hits / App-held list.
    q_effects = _q_effect_blobs(search_clean)
    if not q_effects:
        fail(
            f"{_ISSUE}: remount with a non-empty restored q must call "
            "existing run() / api.search once (debounce OK) — keep the "
            "#270 $effect on q"
        )
    saw_refresh = False
    for blob in q_effects:
        empty_body, nonempty_body = _q_effect_paths(blob)
        if _CLEAR_IDLE.search(nonempty_body):
            fail(
                f"{_ISSUE}: remount must not clearHitsIdle a restored "
                "non-empty q (steady state is not empty-idle when q is "
                "non-empty)"
            )
        if _RUN_OR_SEARCH.search(nonempty_body):
            saw_refresh = True
        if empty_body.strip() and _RUN_OR_SEARCH.search(empty_body) and not _CLEAR_IDLE.search(
            empty_body
        ):
            fail(
                f"{_ISSUE}: empty q must still idle (clearHitsIdle / no "
                "useless FTS) — keep #270"
            )
    if not saw_refresh:
        fail(
            f"{_ISSUE}: remount with a non-empty restored q must call "
            "existing run() / api.search once (debounce OK) — do not "
            "require a lifted App hit list"
        )
    mount_blob = _onmount_blob(search_clean)
    if mount_blob and _CLEAR_IDLE.search(mount_blob):
        empty_m, nonempty_m = _q_effect_paths(mount_blob)
        if _CLEAR_IDLE.search(nonempty_m) or (
            not empty_m.strip() and _CLEAR_IDLE.search(mount_blob)
        ):
            fail(
                f"{_ISSUE}: remount / onMount must not clearHitsIdle a "
                "restored non-empty q"
            )

    # 5) keep-session-only — no new persist key for q or hits.
    web = _web_logic(crate)
    web_clean = _without_comments(web)
    persist_src = "\n".join((app_clean, search_clean, prefs_clean, nav_clean))
    persist_win = _persist_windows(persist_src)
    if _PERSIST_Q_HITS.search(persist_win) and (
        _SETITEM.search(persist_win)
        or _GETITEM.search(persist_win)
        or _SESSION_STORE.search(persist_win)
    ):
        fail(
            f"{_ISSUE}: no new localStorage / sessionStorage key for q or "
            "hits (session RAM / searchQ only; new session may start empty)"
        )
    for key in _ls_pref_keys(web_clean):
        if key not in _ALLOWED_LS and _Q_HITS_KEY.search(key):
            fail(
                f"{_ISSUE}: no new PeoplePrefs / localStorage key for q or "
                f"hits (found {key!r}; session RAM only)"
            )
    if _SESSION_STORE.search(search_clean) or _SESSION_STORE.search(prefs_clean):
        sess = _windows_around(search_clean + "\n" + prefs_clean, _SESSION_STORE)
        if _PERSIST_Q_HITS.search(sess) or _SEARCH_Q_TOKEN.search(sess):
            fail(
                f"{_ISSUE}: do not sessionStorage q or hits "
                "(session RAM / searchQ on App only)"
            )
    if _CONFIG_TOML.search(search_clean) or (
        _CONFIG_TOML.search(app_clean) and _PERSIST_Q_HITS.search(app_clean)
    ):
        fail(f"{_ISSUE}: do not persist q or hits in config.toml")
    if _LAST_PATH_API.search(search_clean):
        fail(f"{_ISSUE}: do not persist q or hits via write_last_path")
    if _ICLOUD.search(persist_win) and _PERSIST_Q_HITS.search(persist_win):
        fail(f"{_ISSUE}: do not invent an iCloud key for q or hits")

    # 6) keep-308-reset — close-to-setup still searchQ = "".
    if not any(_in_setup_reset(app_clean, pos) for pos in _searchq_clear_sites(app_clean)):
        fail(
            f"{_ISSUE}: close-to-setup (#308) must still assign searchQ = \"\""
        )

    # 7) keep-208 — chrome field; App / PeopleNav still do not call api.search.
    if not _CHROME_SEARCH_HOOK.search(app_only) and not _CHROME_SEARCH_HOOK.search(nav):
        fail(
            f"{_ISSUE}: keep data-chrome-search (#208) — chrome field stays "
            "while the archive is open"
        )
    if _API_SEARCH_CALL.search(app_clean) or _INVOKE_SEARCH_CMD.search(app_clean):
        fail(
            f"{_ISSUE}: App.svelte must not call api.search — SearchPane "
            "run() stays the only search IPC (#208)"
        )
    if _API_SEARCH_CALL.search(nav_clean) or _INVOKE_SEARCH_CMD.search(nav_clean):
        fail(
            f"{_ISSUE}: PeopleNav must not call api.search — SearchPane "
            "run() stays the only search IPC (#208)"
        )

    # 8) keep-270 — typing in #q still searches; empty still idles; submit;
    #    searchGen stays.
    if not _has_search_as_you_type(search_clean, search_surface):
        fail(
            f"{_ISSUE}: keep type-to-search (#270) — #q / $effect / "
            "debounce → run() / api.search"
        )
    if not _CLEAR_IDLE.search(search_clean):
        fail(
            f"{_ISSUE}: keep clearHitsIdle on empty q (#270) — no useless FTS"
        )
    if not re.search(
        r"(?:on:submit|onsubmit)\s*=|type\s*=\s*[\"']submit[\"']",
        search_surface,
        re.I,
    ):
        fail(f"{_ISSUE}: keep form submit → run() (#270)")
    run_body = _ts_fn_body(search_clean, "run") or _function_body(search_clean, "run")
    if not run_body or not _SEARCH_GEN.search(search_clean) or not _SEARCH_GEN_INC.search(
        run_body
    ):
        fail(f"{_ISSUE}: keep searchGen on run() (#270)")

    # 9) keep-273 — bubble Search still sets a short name query + seedPerson.
    bubble = _ts_fn_body(app_clean, "searchFromBubble") or _function_body(
        app_clean, "searchFromBubble"
    )
    if not bubble:
        fail(
            f"{_ISSUE}: keep searchFromBubble (#273) — name query + seedPerson"
        )
    if not _BUBBLE_NAME_Q.search(bubble) or not re.search(r"\bseedPerson\s*=", bubble):
        fail(
            f"{_ISSUE}: bubble Search must still set searchQ = display_name "
            "and seedPerson (#273; Ada — the name, not a raw id)"
        )
    if _BUBBLE_BODY_Q.search(bubble):
        fail(
            f"{_ISSUE}: bubble Search must not assign body_text to #q / "
            "searchQ (#273)"
        )
    if not re.search(r"\bwhenSearchPaneReady\b", bubble):
        fail(
            f"{_ISSUE}: bubble Search must still whenSearchPaneReady / "
            "focus #q (#273)"
        )

    # 10) keep-209 — filters stay; j/k / Enter not intercepted inside
    #     filters / #q. Filters are not required to survive remount.
    if _SEARCH_FILTERS_HOOK not in search_surface and _SEARCH_FILTERS_HOOK not in search_only:
        fail(f"{_ISSUE}: keep data-search-filters (#209)")
    hits_key = _ts_fn_body(search_clean, "onHitsKey") or _function_body(
        search_clean, "onHitsKey"
    )
    if hits_key:
        if not re.search(r"data-search-filters", hits_key):
            fail(
                f"{_ISSUE}: onHitsKey must still return inside "
                "data-search-filters (#209-keys)"
            )
        if not re.search(r"INPUT", hits_key):
            fail(
                f"{_ISSUE}: onHitsKey must still return inside #q / INPUT "
                "(#209-keys — j/k / Enter are not intercepted there)"
            )

    # 11) keep-d24 — leave Search and come back in the same session.
    if not dtxt.strip():
        fail(
            f"{_ISSUE}: docs/user/app.md required — leave Search and come "
            "back in the same session → last query is still there; hits "
            "refresh once"
        )
    leave = _DOCS_LEAVE_BACK.search(dtxt)
    if not leave:
        fail(
            f"{_ISSUE}: docs/user/app.md must say leave Search and come "
            "back in the same session → last query is still there"
        )
    keep_win = dtxt[max(0, leave.start() - 80) : leave.end() + 280]
    if not _DOCS_SAME_SESSION.search(keep_win) and not _DOCS_SAME_SESSION.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say the last query stays in "
            "the same session (not across quit)"
        )
    if not _DOCS_REFRESH_ONCE.search(keep_win) and not _DOCS_REFRESH_ONCE.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say hits refresh once when "
            "coming back to Search"
        )
    if _claim_without_negation(keep_win, _SPOTLIGHT_WORD):
        fail(f"{_ISSUE}: not in scope — not Spotlight")
    if _claim_without_negation(keep_win, _MULTI_TAB):
        fail(f"{_ISSUE}: not in scope — not multi-tab search history")
    if _claim_without_negation(keep_win, _SURVIVES_QUIT):
        fail(f"{_ISSUE}: not in scope — last query does not survive quit")
