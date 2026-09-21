"""#372 — Search this conversation (bubble item + search_cmd wire + chip).

Confirmed mix (2026-09-21): bubble context menu only (new
t("searchThisConversation") after t("search"); keep Copy + #273).
Wire SearchArgs.conversation_id (serde default, camelCase conversationId)
through existing search_cmd / api.search / SearchPane.run(). One-shot App
seed (id + pretty title + kind) like seedPerson; snapshot before
view = "search". Person filter clears. Keep #q / #318. Chip next to #q
outside data-search-filters; title via conversationLabel; clears with the
tab. Group sets Search includeGroups on for this search only (not #309).
Other filters AND. Desktop-only. Do not unhide the switcher. Do not
client-filter hits. Do not add a second IPC. Do not rewrite search.rs.

Placeholders Ada / Berk / Self. Never a raw conversation id in chrome,
tests, or docs copy.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.find_in_conversation import _FIND_HOOK
from tauri_gate.import_boot_guards import _ls_pref_keys
from tauri_gate.include_groups import (
    _GROUPS_KEY_RX,
    _READ_GROUPS,
    _WRITE_GROUPS,
)
from tauri_gate.last_read import _text, _web_file
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.media_linkify_lib import _hook_element_blocks
from tauri_gate.reopen_last_lib import _SETITEM
from tauri_gate.scan import (
    _match_closer,
    _rust_function_body,
    _search_pane_blob,
    _svelte_markup,
    _without_comments,
)
from tauri_gate.search_field_keys import _API_SEARCH_CALL, _INVOKE_SEARCH_CMD
from tauri_gate.search_filters_lib import _SEARCH_API_PLATFORM_ARG
from tauri_gate.search_hit_preview import _NEW_INVOKE, _fn
from tauri_gate.search_hits_jump import _HIT_PERSON_ID_READ
from tauri_gate.search_picker_lib import (
    _SEARCH_FILTERS_HOOK,
    _SEARCH_Q_ID,
    _search_run_surface,
)

_ISSUE = "#372"

_MENU_THIS = re.compile(r"""t\s*\(\s*["']searchThisConversation["']\s*\)""")
_MENU_SEARCH = re.compile(r"""t\s*\(\s*["']search["']\s*\)""")
_MENU_COPY = re.compile(
    r"""t\s*\(\s*["']copyText["']\s*\)|t\s*\(\s*["']copyN["']\s*\)"""
)
_COPY_MENU_HOOK = re.compile(r"\bdata-copy-menu\b")
_CHIP_HOOK = re.compile(r"\bdata-search-conversation\b")
_CHROME_SEARCH = re.compile(r"\bdata-chrome-search\b")
_SEARCH_Q_BIND = re.compile(r"bind:q\s*=\s*\{searchQ\}")
_SEED_PERSON_PROP = re.compile(r"\{seedPerson\}|seedPerson\s*=")
_PICK_PERSON = re.compile(r"\bpickPerson\s*\(")
_SEARCHQ_NAME = re.compile(r"\bsearchQ\s*=\s*\w+\.display_name\b")
_SEARCHQ_TITLE = re.compile(
    r"\bsearchQ\s*=\s*(?:conversationTitle|title|conversation_title|"
    r"conversationLabel|chatTitle)\b"
)
_VIEW_SEARCH = re.compile(r"""view\s*=\s*["']search["']""")
_WHEN_READY = re.compile(r"\bwhenSearchPaneReady\b")
_BIND_CONV = re.compile(
    r"bind:(?:conversationId|conversationTitle|searchConversationId|"
    r"searchConversationTitle|scopedConversationId)\b"
)
_LIVE_SELECTED = re.compile(r"\bselectedConversationId\b")
_CONV_ID_STATE = re.compile(
    r"\blet\s+(?:conversationId|searchConversationId|scopedConversationId)\s*="
    r"\s*\$state"
)
_CONV_ID_BINDABLE = re.compile(
    r"\b(?:conversationId|searchConversationId|scopedConversationId)\s*="
    r"\s*\$bindable"
)
_SEED_CONV = re.compile(
    r"\b(?:seedConversation|searchConversationSeed|conversationSeed|"
    r"seedConversationId|seedSearchConversation)\b"
)
_KIND_GROUP = re.compile(
    r"""(?:kind|conversationKind|conversation_kind)\s*===?\s*["']group["']"""
)
_INCLUDE_TRUE = re.compile(r"\bincludeGroups\s*=\s*true\b")
_PERSON_NULL = re.compile(r"\bpersonId\s*=\s*null\b")
_CLIENT_FILTER = re.compile(
    r"\bhits\s*=\s*\w+\.filter\s*\("
    r"|\.filter\s*\(\s*(?:h|hit|row)\s*=>[^{]{0,160}conversation_id"
)
_RAW_ID_TEXT = re.compile(
    r"\{(?:conversationId|searchConversationId|scopedConversationId|"
    r"copyMenu\.conversationId|row\.conversation_id)\}"
    r"|String\s*\(\s*(?:row\.)?conversation_id\s*\)"
    r"|String\s*\(\s*conversationId\s*\)"
)
_STRING_ID_TITLE = re.compile(
    r"(?:title|label|conversationTitle)\s*:\s*String\s*\(\s*"
    r"(?:row\.)?(?:conversation_id|conversationId)\s*\)"
)
_JID = re.compile(r"@g\.us|@s\.whatsapp\.net|@lid\b", re.I)
_NEW_INVOKE_CONV = re.compile(
    r"""invoke\s*(?:<[^>]*>)?\s*\(\s*["']search_conversation"""
)
_CLI_CONV = re.compile(
    r"""--conversation\b|#\[arg[^\]]*long\s*=\s*["']conversation["']"""
)
_HANDLER = re.compile(r"generate_handler!\s*\[(.*?)\]", re.S)
_GMAIL_LABEL = re.compile(r"\bdata-gmail-label\b")
_PREVIEW_HOOK = re.compile(r"\bdata-search-preview\b")
_HIT_PERSON = re.compile(r"\bsearch_hit_person\b")
_SEARCH_CALL = re.compile(r"\bsearch\s*\(")
_IF_FALSE_SWITCHER = re.compile(
    r"\{#if\s+false\}[\s\S]{0,500}data-conversation-switcher"
)
_Q_TRIM = r"(?:query|q)\s*(?:\?|\.)\s*trim\s*\(\s*\)"
_CLEAR_IDLE = re.compile(r"\bclearHitsIdle\s*\(")
_CONV_ID_NULL = re.compile(
    r"\b(?:conversationId|searchConversationId|scopedConversationId)\s*="
    r"\s*(?:null|undefined)\b"
)
_RUN_CALL = re.compile(r"\brun\s*\(")
_LS_ALLOWED = frozenset(
    {
        "interlace.peopleSidebarCollapsed",
        "interlace.density",
        "interlace.lastView",
        "interlace.lastPersonId",
        "interlace.includeGroups",
        "interlace.peopleSort",
        "interlace.lastRead",
    }
)
_DOCS_SEARCH_THIS = re.compile(r"Search this conversation", re.I)
_DOCS_CHIP = re.compile(
    r"(?:chip|chat title|conversation title|group title)",
    re.I,
)
_DOCS_CLEAR = re.compile(
    r"(?:clear|dismiss).{0,120}(?:unscoped|same query|same \#q)"
    r"|(?:unscoped|same query|same \#q).{0,120}(?:clear|dismiss)",
    re.I | re.S,
)
_DOCS_RAW_ID = re.compile(
    r"conversation(?:_id|\s+id)\s*[:=]\s*\d+"
    r"|conversation\s+\d{2,}",
    re.I,
)
_DOCS_BUBBLE_PERSON = re.compile(
    r"Search.{0,80}(?:person|Ada)|bubble.{0,80}Search.{0,80}(?:person|Ada|name)",
    re.I | re.S,
)
_DOCS_FIND = re.compile(
    r"timeline find stays on the thread|find stays on the thread|#tl-find",
    re.I,
)
_BUTTON = re.compile(r"<button\b[^>]*>[\s\S]{0,500}?</button>", re.I)


def _rust_struct_body(src: str, name: str) -> str:
    m = re.search(rf"(?:pub\s+)?struct\s+{re.escape(name)}\s*\{{", src)
    if not m:
        return ""
    start = src.find("{", m.start())
    if start < 0:
        return ""
    end = _match_closer(src, start)
    if end < 0:
        return src[start:]
    return src[start : end + 1]


def _search_query_literal(cmd: str) -> str:
    m = re.search(r"\bSearchQuery\s*\{", cmd)
    if not m:
        return ""
    start = cmd.find("{", m.start())
    if start < 0:
        return ""
    end = _match_closer(cmd, start)
    if end < 0:
        return cmd[start : start + 800]
    return cmd[start : end + 1]


def _menu_onclick_for_t(src: str, key: str) -> str:
    for block in _BUTTON.findall(src):
        if re.search(rf"""t\s*\(\s*["']{re.escape(key)}["']\s*\)""", block):
            om = re.search(r"onclick=\{([^}]+)\}", block)
            return (om.group(1) if om else "").strip()
    return ""


def _prop_ident(expr: str) -> str:
    expr = expr.strip()
    m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)", expr)
    return m.group(1) if m else ""


def _idle_on_empty_q(blob: str) -> bool:
    if not re.search(_Q_TRIM, blob) and not re.search(r"!\s*q\b", blob):
        return False
    if _CLEAR_IDLE.search(blob) and re.search(r"\breturn\b", blob):
        return True
    for m in re.finditer(rf"if\s*\(\s*!\s*{_Q_TRIM}\s*\)", blob):
        rest = blob[m.end() : m.end() + 200]
        if re.search(r"\breturn\b", rest) or _CLEAR_IDLE.search(rest):
            return True
    return False


def _seed_effect(search: str) -> str:
    parts: list[str] = []
    for m in re.finditer(r"\$effect\s*\(\s*\(\s*\)\s*=>", search):
        i = m.end()
        n = len(search)
        while i < n and search[i].isspace():
            i += 1
        if i < n and search[i] == "{":
            close = _match_closer(search, i)
            body = search[i + 1 : close] if close >= 0 else search[i + 1 : i + 800]
        else:
            body = search[i : i + 400]
        if _SEED_CONV.search(body) or re.search(
            r"\b(?:conversationId|conversationTitle)\b", body
        ):
            if re.search(r"\bseedPerson\b", body) and not _SEED_CONV.search(body):
                continue
            parts.append(body)
    return "\n".join(parts)


def _this_app_handler(app: str) -> str:
    for name in (
        "searchThisConversation",
        "searchFromConversation",
        "onSearchThisConversation",
        "searchConversationFromBubble",
    ):
        body = _fn(app, name)
        if body:
            return body
    m = re.search(
        r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*\{",
        app,
    )
    # Fall back: a function that assigns a conversation seed and is not
    # searchFromBubble.
    blobs: list[str] = []
    for name in re.findall(r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", app):
        if name == "searchFromBubble":
            continue
        body = _fn(app, name)
        if body and _SEED_CONV.search(body):
            blobs.append(body)
    return "\n".join(blobs)


def _list_this_handler(lst: str, prop: str) -> str:
    for name in (
        prop,
        "searchThisConversation",
        "searchFromConversation",
        "onSearchThisConversation",
    ):
        if not name:
            continue
        body = _fn(lst, name)
        if body:
            return body
    return _fn(lst, "searchFromBubble")


def assert_search_this_conversation(crate: Path) -> None:
    """#372: bubble Search this conversation scopes archive Search to that chat."""
    root = repo_root()
    menu_path = _web_file(crate, "TimelineCopyMenu.svelte")
    list_path = _web_file(crate, "TimelineList.svelte")
    pane_path = _web_file(crate, "TimelinePane.svelte")
    shell_path = _web_file(crate, "PeopleShell.svelte")
    search_path = _web_file(crate, "SearchPane.svelte")
    hits_path = _web_file(crate, "SearchHits.svelte")
    nav_path = _web_file(crate, "PeopleNav.svelte")
    app_path = crate / "web" / "App.svelte"
    api_path = _web_file(crate, "api.ts")
    ipc_path = crate / "src" / "ipc.rs"
    docs_path = root / "docs" / "user" / "app.md"
    en_path = crate / "web" / "lib" / "locales" / "en.ts"
    tr_path = crate / "web" / "lib" / "locales" / "tr.ts"
    cli_rs = root / "crates" / "interlace-core" / "src" / "cli.rs"
    cli_search = root / "crates" / "interlace-core" / "src" / "cli" / "search.rs"

    menu_raw = _text(menu_path)
    lst_raw = _text(list_path)
    pane_raw = _text(pane_path)
    shell_raw = _text(shell_path)
    search_raw = _search_pane_blob(crate) if search_path.is_file() else ""
    hits_raw = _text(hits_path)
    nav_raw = _text(nav_path)
    app_raw = _text(app_path)
    api_raw = _text(api_path)
    ipc_raw = _text(ipc_path)
    docs_raw = _text(docs_path)
    main_raw = _text(crate / "src" / "main.rs")

    menu = _without_comments(menu_raw)
    lst = _without_comments(lst_raw)
    pane = _without_comments(pane_raw)
    shell = _without_comments(shell_raw)
    search = _without_comments(search_raw)
    hits = _without_comments(hits_raw)
    nav = _without_comments(nav_raw)
    app = _without_comments(app_raw)
    api = _without_comments(api_raw)
    menu_m = _svelte_markup(menu_raw)
    search_m = _svelte_markup(search_raw)
    nav_m = _svelte_markup(nav_raw)
    pane_m = _svelte_markup(pane_raw)
    app_m = _svelte_markup(app_raw)

    # 1) menu-new-item — primary red today.
    if not menu_path.is_file() or not _MENU_THIS.search(menu_m or menu):
        fail(
            f'{_ISSUE}: bubble context menu must add Search this conversation '
            '(t("searchThisConversation")) after t("search")'
        )
    search_t = _MENU_SEARCH.search(menu_m or menu)
    this_t = _MENU_THIS.search(menu_m or menu)
    if search_t and this_t and this_t.start() < search_t.start():
        fail(
            f'{_ISSUE}: t("searchThisConversation") must come after t("search") '
            "(keep #273 Search; this is a new item)"
        )
    if not _COPY_MENU_HOOK.search(menu_m or menu):
        fail(f"{_ISSUE}: keep data-copy-menu / data-context-menu for the bubble menu")

    this_click = _menu_onclick_for_t(menu_m or menu, "searchThisConversation")
    search_click = _menu_onclick_for_t(menu_m or menu, "search")
    this_prop = _prop_ident(this_click)
    search_prop = _prop_ident(search_click)
    if this_prop and search_prop and this_prop == search_prop:
        fail(
            f"{_ISSUE}: Search this conversation must not replace #273 Search "
            "(distinct handler; keep t(\"search\") → searchFromBubble)"
        )

    # 2) keep-273 menu Copy + person-name Search.
    if not _MENU_COPY.search(menu_m or menu):
        fail(f"{_ISSUE}: keep Copy on the bubble menu (#273 / #135)")
    if not _MENU_SEARCH.search(menu_m or menu):
        fail(f'{_ISSUE}: keep t("search") on the bubble menu (#273 person-name Search)')
    bubble = _fn(app, "searchFromBubble") or _fn(app_raw, "searchFromBubble")
    if not bubble:
        fail(f"{_ISSUE}: keep searchFromBubble (#273)")
    if not _SEARCHQ_NAME.search(bubble):
        fail(
            f"{_ISSUE}: keep #273 — searchFromBubble still seeds #q with "
            "display_name (Ada), not body_text"
        )
    if not re.search(r"\bseedPerson\s*=", bubble):
        fail(f"{_ISSUE}: keep #273 — searchFromBubble still sets seedPerson")

    # 3) bubble-search-this-pass — row id+pretty title+kind up to App.
    open_fn = _fn(lst, "openCopyMenu") or _fn(lst_raw, "openCopyMenu")
    if not re.search(r"\bconversation_id\b", open_fn):
        fail(
            f"{_ISSUE}: copyMenu must keep the row conversation id + title "
            "(id is IPC-only, never chrome text)"
        )
    if not (
        re.search(r"\bconversationLabel\s*\(", open_fn)
        or re.search(r"\bconversation_title\b", open_fn)
        or re.search(r"\bplatformLabel\s*\(", open_fn)
    ):
        fail(
            f"{_ISSUE}: pass a pretty chat title via conversationLabel "
            "(group title / pretty platform — not String(id))"
        )
    if _STRING_ID_TITLE.search(open_fn) or _STRING_ID_TITLE.search(lst):
        fail(
            f"{_ISSUE}: chip / menu title must not be String(conversation id) "
            "— use conversationLabel"
        )
    if not re.search(
        r"\b(?:kind|conversation_kind|conversationKind)\b", open_fn
    ):
        fail(
            f"{_ISSUE}: snapshot kind with the id + title "
            "(group turns Search includeGroups on)"
        )
    list_handler = _list_this_handler(lst, this_prop)
    if this_prop and this_prop not in lst_raw and this_prop not in lst:
        fail(
            f"{_ISSUE}: TimelineList must wire {this_prop} from the new "
            "menuitem (pass id + title + kind, not selectedConversationId)"
        )
    if list_handler and _LIVE_SELECTED.search(list_handler):
        fail(
            f"{_ISSUE}: Search this conversation uses the row's chat, not "
            "selectedConversationId (All still has a row conversation)"
        )
    if this_prop:
        if this_prop not in pane_raw and this_prop not in pane:
            fail(
                f"{_ISSUE}: TimelinePane must pass {this_prop} through to "
                "TimelineList (do not read the hidden switcher)"
            )
        if this_prop not in shell_raw and this_prop not in shell:
            fail(
                f"{_ISSUE}: PeopleShell must pass {this_prop} through to "
                "TimelinePane"
            )
        if this_prop not in app_raw and this_prop not in app:
            fail(
                f"{_ISSUE}: App must handle {this_prop} (one-shot seed, "
                "not searchFromBubble)"
            )

    # 4) one-shot App seed; not live-bind; snapshot before view = search.
    app_this = _this_app_handler(app) or _this_app_handler(app_raw)
    if not app_this:
        fail(
            f"{_ISSUE}: App one-shot seed (id + pretty title + kind) like "
            "seedPerson — snapshot before view = \"search\""
        )
    if not _SEED_CONV.search(app_this) and not _SEED_CONV.search(app):
        fail(
            f"{_ISSUE}: one-shot seedConversation (id + pretty title + kind) "
            "on App, like seedPerson"
        )
    if _LIVE_SELECTED.search(app_this):
        fail(
            f"{_ISSUE}: do not live-bind selectedConversationId "
            "(PeopleShell unmounts on Search; seed the row snapshot)"
        )
    if not (_WHEN_READY.search(app_this) or _VIEW_SEARCH.search(app_this)):
        fail(
            f"{_ISSUE}: Search this conversation must open Search "
            "(whenSearchPaneReady / view = \"search\")"
        )
    seed_before = True
    ready_at = -1
    for rx in (_WHEN_READY, _VIEW_SEARCH):
        m = rx.search(app_this)
        if m and (ready_at < 0 or m.start() < ready_at):
            ready_at = m.start()
    seed_m = _SEED_CONV.search(app_this)
    if ready_at >= 0 and seed_m and seed_m.start() > ready_at:
        seed_before = False
    if not seed_before:
        fail(
            f"{_ISSUE}: snapshot the conversation seed before view = \"search\" "
            "(SearchPane must see it on mount)"
        )
    if not re.search(
        r"\b(?:seedConversation|searchConversationSeed|conversationSeed|"
        r"seedConversationId)\s*=\s*null\b",
        app_this,
    ) and not re.search(
        r"\b(?:seedConversation|searchConversationSeed|conversationSeed|"
        r"seedConversationId)\s*=\s*null\b",
        app,
    ):
        fail(
            f"{_ISSUE}: seed is one-shot — clear it after whenSearchPaneReady "
            "(like seedPerson = null; chip is SearchPane-local)"
        )

    # 5) search-this-keeps-q — do not overwrite #q.
    if _SEARCHQ_NAME.search(app_this) or _SEARCHQ_TITLE.search(app_this):
        fail(
            f"{_ISSUE}: Search this conversation must not assign #q "
            "(keep current query / #318; do not write Ada or the chat title)"
        )
    if re.search(r"\bsearchQ\s*=", app_this):
        fail(
            f"{_ISSUE}: Search this conversation must not assign searchQ "
            "(keep #q / #318 last query)"
        )

    # 6) person-filter clears (not seedPerson / pickPerson).
    if re.search(r"\bseedPerson\s*=\s*(?!null\b)", app_this):
        fail(
            f"{_ISSUE}: person filter clears — do not seedPerson / pickPerson "
            "on Search this conversation (user may re-pick Ada in Filters)"
        )
    if _PICK_PERSON.search(app_this):
        fail(
            f"{_ISSUE}: person filter clears — do not pickPerson on "
            "Search this conversation"
        )
    seed_fx = _seed_effect(search)
    if _PICK_PERSON.search(seed_fx) or re.search(r"\bseedPerson\b", seed_fx):
        fail(
            f"{_ISSUE}: conversation seed must not pickPerson / seedPerson "
            "(person filter clears; leftover person is AND only if re-picked)"
        )

    mount = ""
    mm = re.search(r"<SearchPane\b", app_m or app_raw)
    if mm:
        gt = (app_m or app_raw).find(">", mm.start())
        mount = (app_m or app_raw)[mm.start() : gt + 1 if gt >= 0 else mm.start() + 500]
    if _BIND_CONV.search(mount) or _CONV_ID_BINDABLE.search(search):
        fail(
            f"{_ISSUE}: chip clears with the tab — do not bind conversation "
            "id/title onto App (#318 keeps #q only)"
        )
    if not _SEED_CONV.search(mount) and not _SEED_CONV.search(search):
        fail(
            f"{_ISSUE}: SearchPane must take a one-shot conversation seed "
            "(id + pretty title + kind), not a live selectedConversationId"
        )
    if _LIVE_SELECTED.search(search):
        fail(
            f"{_ISSUE}: SearchPane must not live-bind selectedConversationId"
        )

    # 7) SearchArgs.conversation_id → SearchQuery; not a literal None.
    args = _rust_struct_body(ipc_raw, "SearchArgs")
    if not re.search(r"\bconversation_id\s*:\s*Option\s*<\s*i64\s*>", args):
        fail(
            f"{_ISSUE}: SearchArgs.conversation_id: Option<i64> "
            "(serde camelCase conversationId, default None)"
        )
    field_m = re.search(r"\bconversation_id\s*:", args)
    if field_m:
        pre = args[max(0, field_m.start() - 160) : field_m.start()]
        if "serde(default)" not in pre and "#[serde(default)]" not in pre:
            fail(
                f"{_ISSUE}: SearchArgs.conversation_id needs #[serde(default)] "
                "(omit / null = today's unscoped search)"
            )
    cmd = _rust_function_body(ipc_raw, "search_cmd")
    if not cmd:
        fail(f"{_ISSUE}: search_cmd required (pass conversation_id through)")
    qlit = _search_query_literal(cmd)
    if re.search(r"\bconversation_id\s*:\s*None\b", qlit):
        fail(
            f"{_ISSUE}: search_cmd still hardcodes conversation_id: None — "
            "pass SearchArgs.conversation_id into SearchQuery"
        )
    if not re.search(r"\bconversation_id\s*:\s*args\.conversation_id\b", qlit):
        fail(
            f"{_ISSUE}: search_cmd must copy args.conversation_id into "
            "SearchQuery (not a literal None; do not rewrite search.rs)"
        )

    # 8) api.search conversationId on the existing search_cmd; no second IPC.
    search_fn = _fn(api, "search") or api
    if not re.search(r"\bconversationId\b", search_fn):
        fail(
            f"{_ISSUE}: api.search must take conversationId?: number | null "
            "on the existing search_cmd invoke (not a new command)"
        )
    if not _INVOKE_SEARCH_CMD.search(api) and not re.search(
        r"""["']search_cmd["']""", api
    ):
        fail(f"{_ISSUE}: api.search still invokes search_cmd (no second IPC)")
    if _NEW_INVOKE_CONV.search(api) or _NEW_INVOKE_CONV.search(search):
        fail(
            f"{_ISSUE}: do not add search_conversation IPC — "
            "one field on existing search_cmd"
        )
    rust_blob = ipc_raw + "\n" + main_raw
    h = _HANDLER.search(rust_blob)
    if h and re.search(r"\bsearch_conversation", h.group(1)):
        fail(f"{_ISSUE}: do not add a second search command to generate_handler")

    # 9) run() sends pane-state conversationId; App still does not api.search.
    run_all, _run_before = _search_run_surface(search)
    api_m = _SEARCH_API_PLATFORM_ARG.search(search)
    run_args = api_m.group(1) if api_m else run_all
    if not re.search(r"\bconversationId\s*:", run_args):
        fail(
            f"{_ISSUE}: SearchPane run() must send conversationId from pane "
            "state (null when unscoped)"
        )
    if re.search(r"\bconversationId\s*:\s*\d+", run_args):
        fail(
            f"{_ISSUE}: run() conversationId comes from pane state, "
            "not a hard-coded number"
        )
    if _API_SEARCH_CALL.search(app):
        fail(
            f"{_ISSUE}: keep #208 — App.svelte must not call api.search "
            "(SearchPane run() is the only caller)"
        )

    # 10) other-filters AND (do not wipe Filters / #365).
    for field in (
        "personId",
        "platform",
        "conversationKind",
        "attachmentFilter",
        "labelId",
        "includeGroups",
    ):
        if not re.search(rf"\b{field}\s*:", run_args):
            fail(
                f"{_ISSUE}: scoped search still ANDs other Filters "
                f"(run() must still send {field})"
            )
    if not re.search(r"\bfrom\s*:", run_args) or not re.search(r"\bto\s*:", run_args):
        fail(f"{_ISSUE}: scoped search still ANDs date filters (from / to)")

    # 11) chip next to #q, outside Filters; pretty title; not chrome-search.
    surface = search_m if search_m.strip() else search_raw
    if not _CHIP_HOOK.search(surface):
        fail(
            f"{_ISSUE}: Search must show a dismissible conversation chip next "
            "to #q (data-search-conversation)"
        )
    filt_blocks = _hook_element_blocks(surface, _SEARCH_FILTERS_HOOK)
    filt_blob = "\n".join(filt_blocks)
    if _CHIP_HOOK.search(filt_blob):
        fail(
            f"{_ISSUE}: conversation chip sits with #q, not inside "
            "data-search-filters (Filters stay secondary)"
        )
    q_m = _SEARCH_Q_ID.search(surface)
    chip_m = _CHIP_HOOK.search(surface)
    filt_m = re.search(r"\bdata-search-filters\b", surface)
    if not q_m:
        fail(f'{_ISSUE}: keep id="q" as the canonical query field (#208)')
    if chip_m and filt_m and not (q_m.start() < chip_m.start() < filt_m.start()) and not (
        chip_m.start() < filt_m.start()
    ):
        fail(
            f"{_ISSUE}: chip is in the Query / #q block (next to / under #q), "
            "not below Filters"
        )
    if chip_m and filt_m and chip_m.start() > filt_m.start():
        fail(
            f"{_ISSUE}: chip is next to / under #q, outside data-search-filters"
        )
    if _CHIP_HOOK.search(nav_m or nav):
        fail(
            f"{_ISSUE}: chip is Search pane #q only — not on data-chrome-search"
        )
    chip_blocks = _hook_element_blocks(surface, "data-search-conversation")
    chip_blob = "\n".join(chip_blocks) if chip_blocks else surface
    if _RAW_ID_TEXT.search(chip_blob) or _RAW_ID_TEXT.search(surface):
        fail(
            f"{_ISSUE}: chip shows the chat title (conversationLabel), "
            "never a raw numeric conversation id"
        )
    if _JID.search(chip_blob):
        fail(
            f"{_ISSUE}: chip label is the group title / pretty platform, "
            "never a JID"
        )
    if re.search(r">\s*group\s*<", chip_blob, re.I) and not re.search(
        r"conversationTitle|conversationLabel|chatTitle", chip_blob
    ):
        fail(
            f"{_ISSUE}: group chip is the group title, not the word \"group\""
        )
    if not re.search(
        r"\{(?:conversationTitle|scopedTitle|chatTitle|conversationLabel|"
        r"seedConversation\.title)\}",
        chip_blob,
    ) and not re.search(
        r"conversationTitle|conversationLabel|chatTitle", chip_blob
    ):
        fail(
            f"{_ISSUE}: chip text is the pretty chat title "
            "(Ada / Berk / Self / group title / WhatsApp|Gmail)"
        )
    if re.search(r"""id\s*=\s*["']q["']""", chip_blob) and chip_blocks:
        fail(f'{_ISSUE}: do not steal id="q" onto the chip (#208)')

    # 12) chip-clear-unscoped — null the id and re-run the same #q.
    if not _CONV_ID_NULL.search(search):
        fail(
            f"{_ISSUE}: Clear on the chip sets conversationId null and "
            "re-runs the same #q (unscoped hits)"
        )
    # A clear control that calls run() without wiping q.
    if not (
        re.search(
            r"onclick=\{[^}]{0,400}(?:clearConversation|clearScope|"
            r"onClearConversation|conversationId\s*=\s*null)",
            chip_blob,
        )
        or (
            _CONV_ID_NULL.search(search)
            and _RUN_CALL.search(search)
            and re.search(r"clearConversation|clearScope|onClearConversation", search)
        )
        or (
            _CONV_ID_NULL.search(search)
            and re.search(
                r"(?:conversationId\s*=\s*null)[\s\S]{0,240}\brun\s*\(",
                search,
            )
        )
    ):
        fail(
            f"{_ISSUE}: chip Clear drops the conversation scope and re-run()s "
            "the same #q (do not clearHitsIdle unless #q is empty)"
        )
    if re.search(
        r"(?:conversationId\s*=\s*null)[\s\S]{0,200}\bsearchQ\s*=",
        search,
    ) or re.search(
        r"(?:conversationId\s*=\s*null)[\s\S]{0,200}\bq\s*=\s*[\"']{2}",
        search,
    ):
        fail(
            f"{_ISSUE}: clearing the chip must not wipe #q "
            "(same query, now unscoped)"
        )

    # 13) empty #q stays idle even when scoped (#270).
    if not _idle_on_empty_q(search):
        fail(
            f"{_ISSUE}: empty #q still clearHitsIdle / no api.search "
            "even when a conversation is scoped (do not browse with empty q)"
        )
    if run_all and not _idle_on_empty_q(run_all) and re.search(
        r"\bconversationId\b", run_all
    ):
        # run() itself must not FTS an empty q just because a chip is on.
        if not re.search(rf"if\s*\(\s*!\s*{_Q_TRIM}\s*\)", run_all):
            fail(
                f"{_ISSUE}: run() must not api.search an empty #q just because "
                "conversationId is set (keep #270 idle)"
            )

    # 14) group → Search includeGroups on; do not persist #309.
    if not (
        _KIND_GROUP.search(seed_fx)
        and _INCLUDE_TRUE.search(seed_fx)
        or re.search(
            r"""["']group["'][\s\S]{0,240}includeGroups\s*=\s*true"""
            r"""|includeGroups\s*=\s*true[\s\S]{0,240}["']group["']""",
            seed_fx + "\n" + search,
        )
    ):
        fail(
            f"{_ISSUE}: scoping a group must set Search includeGroups = true "
            "before run() (do not persist interlace.includeGroups)"
        )
    if (
        _GROUPS_KEY_RX.search(search)
        or _WRITE_GROUPS.search(search)
        or _READ_GROUPS.search(search)
        or _SETITEM.search(search)
    ):
        fail(
            f"{_ISSUE}: do not write interlace.includeGroups from Search "
            "(#309 Search tick stays unpersisted; this search only)"
        )
    if re.search(r"includeGroups", mount):
        fail(
            f"{_ISSUE}: do not pass App includeGroups into SearchPane "
            "(#309 Search stays its own checkbox; set local tick for groups)"
        )

    # 15) no client-filter of hits.
    apply_hits = ""
    idx = search.find("api.search")
    if idx >= 0:
        apply_hits = search[idx : idx + 900]
    if _CLIENT_FILTER.search(apply_hits) or _CLIENT_FILTER.search(hits):
        fail(
            f"{_ISSUE}: do not client-filter hits by conversation_id — "
            "scope is the search_cmd arg"
        )

    # 16) keep-session: chip is SearchPane-local; #318 keeps #q only.
    if not _CONV_ID_STATE.search(search):
        fail(
            f"{_ISSUE}: conversation scope is SearchPane $state "
            "(clears with the tab; do not lift onto App like searchQ)"
        )
    if not _SEARCH_Q_BIND.search(app_m or app):
        fail(f"{_ISSUE}: keep bind:q={{searchQ}} (#318 last query)")
    if not _SEED_PERSON_PROP.search(mount):
        fail(f"{_ISSUE}: keep {{seedPerson}} on SearchPane (#273)")
    ls_keys = set(_ls_pref_keys(search) + _ls_pref_keys(app))
    extra_ls = [k for k in ls_keys if k not in _LS_ALLOWED and "conversation" in k.lower()]
    if extra_ls:
        fail(
            f"{_ISSUE}: no localStorage / config.toml key for the conversation "
            "chip (session RAM only; clears with the tab)"
        )
    if re.search(r"\bsessionStorage\b", search) and re.search(
        r"conversation", search, re.I
    ):
        fail(f"{_ISSUE}: do not persist the conversation chip in sessionStorage")
    if not re.search(r"\bsearchQ\s*=\s*[\"']{2}", app):
        fail(f"{_ISSUE}: keep #308 / setup — searchQ = \"\" still clears the query")
    if _SEED_CONV.search(app) and not re.search(
        r"\b(?:seedConversation|searchConversationSeed|conversationSeed|"
        r"seedConversationId)\s*=\s*null\b",
        app,
    ):
        fail(
            f"{_ISSUE}: setup / #308 still clears the one-shot conversation seed"
        )

    # 17) switcher-all-hide; do not unwrap {#if false}.
    if not _IF_FALSE_SWITCHER.search(pane_raw):
        fail(
            f"{_ISSUE}: do not unwrap {{#if false}} on data-conversation-switcher "
            "(#385 parked; no switcher control this ticket)"
        )
    if _MENU_THIS.search(pane_m or pane) or _MENU_THIS.search(pane):
        fail(
            f"{_ISSUE}: no Search-this-conversation control on the conversation "
            "switcher (All has no id; bubble is the entry)"
        )

    # 18) desktop-only — no clap --conversation.
    cli = _text(cli_rs) + "\n" + _text(cli_search)
    if _CLI_CONV.search(cli):
        fail(
            f"{_ISSUE}: desktop-only — do not add clap --conversation "
            "(cmd_search stays None)"
        )

    # 19) locale — same ChromeKey on en.ts + tr.ts; tr is not an English copy.
    en = _chrome_pack_entries(_text(en_path))
    tr = _chrome_pack_entries(_text(tr_path))
    extra_en = set(en) - set(tr)
    extra_tr = set(tr) - set(en)
    if extra_en or extra_tr:
        bits: list[str] = []
        if extra_en:
            bits.append("in en only: " + ", ".join(sorted(extra_en)))
        if extra_tr:
            bits.append("in tr only: " + ", ".join(sorted(extra_tr)))
        fail(f"{_ISSUE}: same ChromeKey on both en and tr packs — " + "; ".join(bits))
    if "searchThisConversation" not in en or "searchThisConversation" not in tr:
        fail(
            f"{_ISSUE}: searchThisConversation ChromeKey on both en.ts and tr.ts "
            "(#278)"
        )
    if (en.get("searchThisConversation") or "").strip() == (
        tr.get("searchThisConversation") or ""
    ).strip():
        fail(
            f"{_ISSUE}: tr searchThisConversation is not an English copy"
        )
    for pack in (en, tr):
        for key, val in pack.items():
            if re.search(r"\bAda\b|\bBerk\b", val):
                fail(
                    f"{_ISSUE}: locale packs stay chrome only — no placeholder "
                    "names in t() values"
                )

    # 20) keep #124 / #208 / #310 / #365 / #371 / #402.
    activate = _fn(search, "activateHit") or _fn(search_raw, "activateHit")
    if not activate or not _HIT_PERSON_ID_READ.search(activate):
        fail(
            f"{_ISSUE}: keep #124 activateHit — Enter still jumps h.person_id"
        )
    if not _FIND_HOOK.search(pane_m or pane_raw):
        fail(
            f"{_ISSUE}: keep #310 #tl-find on the People timeline "
            "(do not replace in-thread find)"
        )
    if not re.search(r"id=[\"']tl-find[\"']", pane_raw) and not re.search(
        r"id=[\"']tl-find[\"']", pane
    ):
        fail(f'{_ISSUE}: keep id="tl-find" (#310)')
    if not _GMAIL_LABEL.search(surface):
        fail(f"{_ISSUE}: keep data-gmail-label (#365)")
    if not _PREVIEW_HOOK.search(hits) and not _PREVIEW_HOOK.search(
        _svelte_markup(hits_raw)
    ):
        fail(f"{_ISSUE}: keep data-search-preview (#371)")
    if _NEW_INVOKE.search(search) or _NEW_INVOKE.search(hits):
        fail(
            f"{_ISSUE}: keep #371 — no new invoke name on SearchPane / SearchHits "
            "(search_cmd / search_body / labels_list only)"
        )
    if not _HIT_PERSON.search(cmd):
        fail(
            f"{_ISSUE}: keep #402 search_hit_person remap in search_cmd "
            "(do not reopen the peer)"
        )
    if not _SEARCH_CALL.search(cmd):
        fail(
            f"{_ISSUE}: keep FTS search() in search_cmd "
            "(do not rewrite search.rs; conversation_id is an arg)"
        )
    if _CHROME_SEARCH.search(app_m or app_raw) is None and not _CHROME_SEARCH.search(
        nav_m or nav
    ):
        fail(f"{_ISSUE}: keep data-chrome-search (#208)")

    # 21) D24 — docs/user/app.md; no raw id; keep #273 / #310.
    if not _DOCS_SEARCH_THIS.search(docs_raw):
        fail(
            f"{_ISSUE}: docs/user/app.md must describe Search this conversation "
            "(Ada's group; chip is the chat title)"
        )
    if not _DOCS_CHIP.search(docs_raw):
        fail(
            f"{_ISSUE}: docs must say the chip shows the chat title "
            "(not a raw conversation id)"
        )
    if not _DOCS_CLEAR.search(docs_raw):
        fail(
            f"{_ISSUE}: docs must say clearing the chip returns unscoped hits "
            "for the same query"
        )
    if _DOCS_RAW_ID.search(docs_raw):
        fail(
            f"{_ISSUE}: docs must not show a raw numeric conversation id "
            "(placeholders Ada / Berk / Self only)"
        )
    if not _DOCS_BUBBLE_PERSON.search(docs_raw):
        fail(
            f"{_ISSUE}: keep docs for bubble Search (#273) — person name + hits"
        )
    if not _DOCS_FIND.search(docs_raw):
        fail(
            f"{_ISSUE}: keep docs — People timeline find stays on the thread "
            "(#310)"
        )
