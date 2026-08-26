"""Bubble search / copy-reveal CAS chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _ARBITRARY_SHELL,
    _VIEW_SEARCH_ASSIGN,
    _call_arg,
    _expand_fn_calls,
    _function_body,
    _rust_body_with_callees,
    _rust_call_arg,
    _rust_fn_signature,
    _svelte_markup,
    _tauri_rust_blob,
    _timeline_block,
    _ts_fn_body,
    _ts_function_body,
    _web_logic,
    _without_comments,
)

from tauri_gate.import_boot import _app_keydown_body

from tauri_gate.media_linkify import (
    _PLUGIN_SHELL,
    _SHELL_CAP,
    _hook_element_blocks,
)

from tauri_gate.search_field import _CHROME_SEARCH_HOOK

from tauri_gate.status_toasts import (
    _FOCUS_SEARCH_Q,
    _KEY_F,
    _WRITE_TEXT,
    _invoke_payloads,
    _payload_has_path_or_url,
    _windows_around,
)




# #273 — jump from a timeline bubble to Search (person name; hits load).
_BUBBLE_SEARCH_HOOK = re.compile(
    r"data-(?:bubble-search|search-from-bubble|bubble-to-search|"
    r"search-this|search-person|timeline-search)"
)
_BUBBLE_SEARCH_HOOK_NAMES = (
    "data-bubble-search",
    "data-search-from-bubble",
    "data-bubble-to-search",
    "data-search-this",
    "data-search-person",
    "data-timeline-search",
)
_BUBBLE_SEARCH_MENU_LABEL = re.compile(
    r"("
    r">\s*Search(?:\s+this(?:\s+person)?|\s+person)?\s*<"
    r"|t\(\s*[\"']search(?:FromBubble|This|Person|OpenPerson|Bubble)?[\"']\s*\)"
    r"|aria-label\s*=\s*[\"']Search(?: this(?: person)?| person)?[\"']"
    r")"
)
_BUBBLE_SEARCH_FN = re.compile(
    r"\b(?:"
    r"searchFromBubble|searchBubble|openBubbleSearch|searchThisPerson|"
    r"searchPersonFromBubble|onBubbleSearch|handleBubbleSearch|"
    r"jumpToSearch|openSearchFromBubble|searchOpenPerson|"
    r"searchFromTimeline|openSearchForPerson"
    r")\b"
)
_BUBBLE_SEARCH_SKIP_EXTRA = frozenset(
    {
        "App.svelte",
        "SearchPane.svelte",
        "CasAttach.svelte",
        "CommandPalette.svelte",
        "ConfirmDialog.svelte",
        "ReviewPane.svelte",
        "ImportPane.svelte",
        "DoctorPane.svelte",
        "EmptyState.svelte",
        "api.ts",
    }
)
_BUBBLE_SEARCH_HANDLER_SKIP = frozenset(
    {
        "t",
        "e",
        "event",
        "true",
        "false",
        "void",
        "closeCopyMenu",
        "copyText",
        "copyMenu",
        "undefined",
        "null",
        "console",
        "preventDefault",
        "stopPropagation",
    }
)
_BUBBLE_SEARCH_NAME_PREFILL = re.compile(
    r"("
    r"\bpickPerson\s*\("
    r"|personFilter\s*=\s*personLabel\s*\("
    r"|personFilter\s*=\s*[^;\n]{0,120}display_name"
    r"|personFilter\s*=\s*personTitle\b"
    r"|personFilter\s*=\s*personLabel\b"
    r"|personLabel\s*\("
    r")"
)
_BUBBLE_SEARCH_RAW_ID_LABEL = re.compile(
    r"("
    r"personFilter\s*=\s*(?:String\s*\(\s*)?(?:selectedId|personId|selected_id|"
    r"p\.id|person\.id|id)\b"
    r"|personFilter\s*=\s*`[^`]*\$\{(?:selectedId|personId|p\.id|person\.id)"
    r")"
)
_BUBBLE_SEARCH_Q_NAME = re.compile(
    r"("
    r"(?:searchQ|(?<![\w.])q)\s*=\s*personLabel\s*\("
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*[^;\n]{0,120}display_name"
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*personTitle\b"
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*personFilter\b"
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*personLabel\b"
    r")"
)
_BUBBLE_SEARCH_Q_BODY = re.compile(
    r"("
    r"(?:searchQ|(?<![\w.])q)\s*=\s*displayBody\s*\("
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*(?:copyMenu(?:\?)?\.)?text\b"
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*(?:row|item\.row|copyMenu)\s*"
    r"(?:\?)?\.\s*(?:body_text|subject|text)\b"
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*(?:row|item)\.body_text"
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*body_text\b"
    r")"
)
_BUBBLE_SEARCH_SELECTION = re.compile(
    r"("
    r"\bgetSelection\s*\("
    r"|\bwindow\.getSelection\s*\("
    r"|\bselectedText\b"
    r"|\bselectedSpan\b"
    r")"
)
_BUBBLE_SEARCH_RUN = re.compile(
    r"("
    r"\brun\s*\("
    r"|requestSubmit\s*\("
    r"|api\.search\s*\("
    r")"
)
_BUBBLE_SEARCH_SEED_PROP = re.compile(
    r"("
    r"\b(?:seedPerson|selectedPerson|openPerson|searchSeed|fromBubble|"
    r"bubblePerson|initialPerson|prefillPerson)\b"
    r"|personFilter\s*=\s*\$bindable"
    r"|personId\s*=\s*\$bindable"
    r"|bind:personFilter"
    r"|bind:personId"
    r")"
)
_BUBBLE_SEARCH_DOC = re.compile(
    r"("
    r"timeline bubble"
    r"|from a (?:timeline )?bubble"
    r"|bubble.{0,80}Search"
    r"|Search.{0,80}(?:from a )?(?:timeline )?bubble"
    r"|right-click.{0,80}Search"
    r"|context menu.{0,80}Search"
    r")",
    re.I | re.S,
)


def _copy_context_menu_blocks(markup: str) -> list[str]:
    blocks: list[str] = []
    for hook in ("data-copy-menu", "data-context-menu"):
        blocks.extend(_hook_element_blocks(markup, hook))
    return blocks


def _menu_looks_like_bubble_search(block: str) -> bool:
    if _BUBBLE_SEARCH_HOOK.search(block):
        return True
    if _BUBBLE_SEARCH_FN.search(block):
        return True
    return bool(_BUBBLE_SEARCH_MENU_LABEL.search(block))


def _bubble_search_control_src(markup: str) -> str:
    """Copy/context-menu Search item and/or named quiet hook on the timeline."""
    parts: list[str] = []
    for block in _copy_context_menu_blocks(markup):
        if _menu_looks_like_bubble_search(block):
            parts.append(block)
    for hook in _BUBBLE_SEARCH_HOOK_NAMES:
        parts.extend(_hook_element_blocks(markup, hook))
    # Dedup overlapping slices (menu that is also the named hook).
    seen: set[str] = set()
    uniq: list[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return "\n".join(uniq)


def _bubble_search_extra(crate: Path, host: str) -> str:
    """Helpers App actually mounts for bubble → Search. Unwired drafts do not count."""
    web = crate / "web"
    if not web.is_dir():
        return ""
    extra: list[str] = []
    for p in sorted(web.rglob("*")):
        if "node_modules" in p.parts:
            continue
        if p.suffix not in {".svelte", ".ts"}:
            continue
        if p.name in _BUBBLE_SEARCH_SKIP_EXTRA:
            continue
        name_hit = bool(
            re.search(r"bubbleSearch|searchFromBubble|searchBubble", p.name, re.I)
        )
        text = p.read_text()
        hook = bool(_BUBBLE_SEARCH_HOOK.search(text) or _BUBBLE_SEARCH_FN.search(text))
        if not name_hit and not hook:
            continue
        stem = p.stem
        if stem in host or re.search(
            rf"\b{re.escape(stem)}\b|{re.escape(p.name)}", host
        ):
            extra.append(text)
    return "\n".join(extra)


def _bubble_search_handler_src(app: str, extra: str, control: str) -> str:
    blob = app + "\n" + extra
    names: set[str] = set(_BUBBLE_SEARCH_FN.findall(blob))
    names.update(_BUBBLE_SEARCH_FN.findall(control))
    for m in re.finditer(
        r"(?:onclick|on:click)\s*=\s*\{([^}]{0,400})\}",
        control,
    ):
        names.update(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", m.group(1)))
    chunks = [control]
    for name in sorted(names):
        if name in _BUBBLE_SEARCH_HANDLER_SKIP:
            continue
        fn = (
            _ts_function_body(blob, name)
            or _ts_fn_body(blob, name)
            or _function_body(blob, name)
        )
        if fn:
            chunks.append(fn)
            chunks.append(_expand_fn_calls(blob, fn))
    return "\n".join(chunks)


def _search_props_blob(search: str) -> str:
    m = re.search(r"=\s*\$props\s*\(\s*\)", search)
    if not m:
        return ""
    start = search.rfind("let", 0, m.start())
    if start < 0:
        start = max(0, m.start() - 900)
    return search[start : m.end()]


def _search_seed_effects(search: str) -> str:
    parts: list[str] = []
    for m in re.finditer(r"\$effect(?:\.pre)?\s*\(", search):
        arg = _call_arg(search, m.end() - 1)
        if re.search(
            r"pickPerson|personFilter|seedPerson|selectedPerson|openPerson|"
            r"fromBubble|bubbleSearch|searchFromBubble",
            arg,
        ):
            parts.append(arg)
    return "\n".join(parts)


def _bubble_search_seed_src(app: str, search: str, handler: str) -> str:
    mount = _windows_around(app, re.compile(r"<SearchPane\b"), before=0, after=700)
    effects = _search_seed_effects(search)
    props = _search_props_blob(search)
    surface = "\n".join([handler, mount, props, effects])
    parts = [surface]
    # Only expand helpers the jump / seed path actually calls (do not
    # treat today's unused pickPerson body as a prefill).
    for name in (
        "pickPerson",
        "seedPerson",
        "prefillPerson",
        "applySeed",
        "searchFromBubble",
        "openFromBubble",
    ):
        if not re.search(rf"\b{re.escape(name)}\b", surface):
            continue
        fn = _ts_fn_body(search, name) or _function_body(search, name)
        if fn:
            parts.append(fn)
    return "\n".join(parts)


def _bubble_search_q_body_is_default(seed: str) -> bool:
    """True when #q default is body_text / displayBody, not a selected span."""
    if not _BUBBLE_SEARCH_Q_BODY.search(seed):
        return False
    for m in _BUBBLE_SEARCH_Q_BODY.finditer(seed):
        win = seed[max(0, m.start() - 160) : m.end() + 80]
        if _BUBBLE_SEARCH_SELECTION.search(win):
            continue
        # `body || name` still dumps the full body as the default.
        return True
    return False


def assert_bubble_search(crate: Path) -> None:
    """#273: from a timeline bubble, open Search with that person.

    Context menuitem on data-copy-menu / data-context-menu, or a named
    quiet control (data-bubble-search), opens Search and focuses #q.
    Person picker is the open person's display name (pickPerson /
    personLabel) — never a raw numeric id. Hits load: short name query
    in #q or existing run() / api.search (not empty-q idle only).
    Do not assign body_text / displayBody to #q by default.
    Keep Copy text, #q, splitSnippet / <mark>, person picker, #124
    hit→timeline, ⌘F → #q. Docs: bubble → Search; name; hits; ⌘F.
    Do not rewrite #123 / #124 / #126 / #135 / #208 / #270 / #272.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#273: App.svelte required (timeline bubble → Search)")
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#273: SearchPane.svelte required (reuse #q / pickPerson / run)")
    app = app_path.read_text()
    search = search_path.read_text()
    markup = _svelte_markup(app)
    extra = _bubble_search_extra(crate, app)
    extra_markup = _svelte_markup(extra) if extra else ""
    surface = markup if not extra_markup else markup + "\n" + extra_markup
    control = _bubble_search_control_src(surface)
    app_clean = _without_comments(app)
    search_clean = _without_comments(search)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) Primary red: no timeline → Search control.
    if not control.strip():
        fail(
            "#273: timeline bubble must have a Search control "
            "(context menuitem on data-copy-menu / data-context-menu, "
            "or a named quiet control data-bubble-search) that opens Search"
        )

    handler = _bubble_search_handler_src(app + "\n" + extra, extra, control)
    seed = _bubble_search_seed_src(app, search, handler)

    # 2) That path sets Search view and focuses #q.
    opens = bool(
        re.search(r"\bwhenSearchPaneReady\b", handler)
        or _VIEW_SEARCH_ASSIGN.search(handler)
    )
    focuses = bool(
        re.search(r"\bwhenSearchPaneReady\b", handler)
        or _FOCUS_SEARCH_Q.search(handler)
    )
    if not opens or not focuses:
        fail(
            "#273: bubble Search path must set Search view and focus #q "
            "(whenSearchPaneReady or getElementById(\"q\") — same path as ⌘F)"
        )

    # 3) Person picker prefilled with the open person's display name.
    mount = _windows_around(app, re.compile(r"<SearchPane\b"), before=0, after=700)
    props = _search_props_blob(search)
    wired = bool(
        _BUBBLE_SEARCH_SEED_PROP.search(props)
        or _BUBBLE_SEARCH_SEED_PROP.search(mount)
        or _BUBBLE_SEARCH_SEED_PROP.search(seed)
        or re.search(
            r"\b(?:seedPerson|selectedPerson|openPerson|searchSeed|fromBubble|"
            r"selectedId)\b",
            mount,
        )
    )
    has_name = bool(_BUBBLE_SEARCH_NAME_PREFILL.search(seed))
    has_raw = bool(_BUBBLE_SEARCH_RAW_ID_LABEL.search(seed))
    if not wired or not has_name:
        fail(
            "#273: person picker must be prefilled with the open person's "
            "display name (pickPerson / personLabel / display_name) — "
            "never a raw numeric person id"
        )
    if has_raw:
        fail(
            "#273: person picker visible label must be the display name "
            "(Ada / Ada (self) via pickPerson / personLabel) — "
            "not a raw numeric person id"
        )

    # 4) Hits load: short name query in #q, or existing run() / api.search.
    has_name_q = bool(_BUBBLE_SEARCH_Q_NAME.search(seed))
    has_run = bool(_BUBBLE_SEARCH_RUN.search(seed))
    if not has_name_q and not has_run:
        fail(
            "#273: hits must load — #q gets a short name query "
            "(display name) or existing run() / api.search is invoked "
            "on this jump (not empty-q idle / clearHitsIdle only)"
        )

    # 5) #q is not assigned body_text / displayBody as the default query.
    if _bubble_search_q_body_is_default(seed):
        fail(
            "#273: #q must not be assigned body_text / displayBody(...) "
            "as the default query — prefer the person name "
            "(a selected span is optional, not the default)"
        )

    # 6) ⌘F / chrome search / whenSearchPaneReady still focuses #q.
    key_body = _app_keydown_body(app_clean) or _app_keydown_body(app)
    key_x = _expand_fn_calls(app_clean, key_body) if key_body else ""
    f_surface = _windows_around(key_x, _KEY_F) if key_x else ""
    if not (
        re.search(r"\bwhenSearchPaneReady\b", f_surface)
        or _FOCUS_SEARCH_Q.search(f_surface)
    ):
        fail(
            "#273: ⌘F must still switch to Search and focus #q "
            "(whenSearchPaneReady / getElementById(\"q\") — "
            "do not require the new bubble menu)"
        )
    if not re.search(r"\bwhenSearchPaneReady\b", app_clean) and not re.search(
        r"\bwhenSearchPaneReady\b", app
    ):
        fail(
            "#273: keep whenSearchPaneReady so chrome search / ⌘F "
            "still focus #q"
        )
    if not _CHROME_SEARCH_HOOK.search(markup) and not _CHROME_SEARCH_HOOK.search(app):
        fail("#273: keep data-chrome-search (#208) — chrome search still focuses #q")

    # 7) Keep Copy text, #q, splitSnippet / <mark>, person picker, #124 jump.
    if not _COPY_TEXT_LABEL.search(app) and not re.search(r"\bcopyText\b", app):
        fail("#273: keep Copy text on the bubble context menu (#135)")
    if not re.search(r"id=[\"']q[\"']", search):
        fail('#273: keep id="q" as the canonical query field (#208 / #270)')
    if not re.search(r"<mark\b", search, re.I):
        fail("#273: keep #126 search <mark> siblings")
    if "splitSnippet" not in search:
        fail("#273: keep #126 splitSnippet")
    if not re.search(r"\bpickPerson\b", search_clean) and not re.search(
        r"\bpersonLabel\b", search_clean
    ):
        fail("#273: keep the #123 person picker (pickPerson / personLabel)")
    if "data-person-picker" not in search and "data-person-picker" not in search_clean:
        fail("#273: keep the #123 person picker (data-person-picker)")
    if not re.search(
        r"\b(?:onJumpToMessage|jumpToMessage|activateHit)\b",
        app_clean + "\n" + search_clean,
    ):
        fail(
            "#273: keep #124 hit→timeline jump "
            "(activateHit / onJumpToMessage / jumpToMessage)"
        )

    # 8) Docs: bubble → Search; person name (not id); hits; ⌘F still #q.
    if not dtxt.strip():
        fail(
            "#273: docs/user/app.md required — from a timeline bubble you "
            "can open Search with that person (name, not id); hits load; "
            "⌘F still focuses #q"
        )
    doc_win = ""
    for m in _BUBBLE_SEARCH_DOC.finditer(dtxt):
        i = m.start()
        doc_win += dtxt[max(0, i - 80) : m.end() + 200] + "\n"
    if not doc_win.strip() or not re.search(
        r"("
        r"(?:timeline )?bubble.{0,120}Search"
        r"|Search.{0,120}(?:from a )?(?:timeline )?bubble"
        r"|right-click.{0,80}Search"
        r"|context menu.{0,80}Search"
        r")",
        doc_win,
        re.I | re.S,
    ):
        fail(
            "#273: docs/user/app.md must say from a timeline bubble you "
            "can open Search with that person"
        )
    if not re.search(
        r"("
        r"name,?\s+not\s+(?:an? )?(?:raw )?(?:numeric )?id"
        r"|display name"
        r"|person(?:'s)? name"
        r"|\bAda\b"
        r")",
        doc_win,
        re.I,
    ):
        fail(
            "#273: docs/user/app.md must say the bubble → Search person "
            "is a name, not a raw id"
        )
    if not re.search(r"\bhits?\b", doc_win, re.I):
        fail("#273: docs/user/app.md must say hits load on the bubble → Search jump")
    if not re.search(
        r"(?:⌘\s*F|Ctrl\+F|Ctrl-F).{0,80}#q|#q.{0,80}(?:⌘\s*F|Ctrl\+F|Ctrl-F)",
        doc_win,
        re.I | re.S,
    ):
        fail(
            "#273: docs/user/app.md must say ⌘F still focuses #q "
            "(bubble → Search does not replace Find)"
        )


# #135 — copy message text / reveal CAS file in Finder (hash only; file open).
_CONTEXTMENU = re.compile(
    r"("
    r"on:contextmenu"
    r"|oncontextmenu"
    r"|addEventListener\s*\(\s*[\"']contextmenu[\"']"
    r"|ContextMenu(?:\.\w+)?"
    r"|data-context-menu"
    r"|contextMenu"
    r")",
    re.I,
)
_COPY_TEXT_LABEL = re.compile(r"Copy text")
_REVEAL_LABEL = re.compile(r"Reveal in Finder")
_REVEAL_CMD_NAMES = (
    "reveal_cas",
    "revealCas",
    "reveal_in_finder",
    "revealInFinder",
)
_REVEAL_CMD = re.compile(
    r"\b(?:" + "|".join(re.escape(n) for n in _REVEAL_CMD_NAMES) + r")\b"
)
_REVEAL_INVOKE = re.compile(
    r"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"'](?:"
    + "|".join(re.escape(n) for n in _REVEAL_CMD_NAMES)
    + r")[\"']"
)
_SHARE_AIRDROP = re.compile(
    r"("
    r"AirDrop"
    r"|Share sheet"
    r"|share sheet"
    r"|NSSharingService"
    r"|showShareSheet"
    r"|ShareLink\b"
    r"|share-sheet"
    r")",
    re.I,
)
_SHARE_ITEM = re.compile(
    r"("
    r">\s*Share\s*<"
    r"|[\"']Share[\"']"
    r"|label\s*:\s*[\"']Share[\"']"
    r")"
)
_COPY_FN_NAMES = (
    "copyText",
    "copyMessage",
    "copyBubble",
    "copyBubbleText",
    "onCopyText",
    "handleCopy",
    "handleCopyText",
)
_BUBBLE_MENU_SKIP = frozenset(
    {
        "App.svelte",
        "CasAttach.svelte",
        "SearchPane.svelte",
        "ReviewPane.svelte",
        "ImportPane.svelte",
        "DoctorPane.svelte",
        "ConfirmDialog.svelte",
        "EmptyState.svelte",
    }
)


def _bubble_and_attach_surface(crate: Path) -> str:
    """Person-timeline bubbles + CasAttach + components they reference."""
    parts = [_timeline_block(crate)]
    app_path = crate / "web" / "App.svelte"
    if app_path.is_file():
        parts.append(app_path.read_text())
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if cas_path.is_file():
        parts.append(cas_path.read_text())
    used = "\n".join(parts)
    web = crate / "web"
    if web.is_dir():
        for p in sorted(web.rglob("*.svelte")):
            if "node_modules" in p.parts or p.name in _BUBBLE_MENU_SKIP:
                continue
            if re.search(rf"\b{re.escape(p.stem)}\b", used):
                parts.append(p.read_text())
    return "\n".join(parts)


def _copy_handler_surface(web: str) -> str:
    chunks = [_windows_around(web, _WRITE_TEXT, before=500, after=160)]
    for name in _COPY_FN_NAMES:
        body = _ts_function_body(web, name) or _function_body(web, name)
        if body:
            chunks.append(body)
        chunks.append(
            _windows_around(web, re.compile(rf"\b{re.escape(name)}\s*\("), before=220, after=80)
        )
    return "\n".join(chunks)


def _copy_logs_body(surf: str) -> bool:
    """True if the copy path logs the message body (console / eprintln)."""
    for m in re.finditer(r"console\.(?:log|debug|info|dir|trace)\s*\(", surf):
        arg = _call_arg(surf, m.end() - 1)
        if re.search(
            r"body_text|displayBody|copiedText|\bbody\b|\btext\b|\bmsg\b|\bmessage\b",
            arg,
            re.I,
        ):
            return True
    for m in re.finditer(r"(?:eprintln|println|dbg)\s*!", surf):
        window = surf[m.start() : m.end() + 200]
        if re.search(r"body_text|displayBody|\bbody\b", window, re.I):
            return True
    return False


def _reveal_cmd_name(rust: str, web: str) -> str:
    blob = rust + "\n" + web
    m = _REVEAL_CMD.search(blob)
    return m.group(0) if m else ""


def assert_copy_reveal_cas(crate: Path) -> None:
    """#135: bubble context menu Copy text; cas_hash attachment Reveal in Finder.

    Reveal command takes the hash only, resolves cas/ab/cd/<hash> via
    cas_blob_path, opens the local file (std::process /usr/bin/open -R or
    file://). Copy does not log the body. No plugin-shell / Share / AirDrop.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#135: App.svelte required (person-timeline bubble context menu)")
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail("#135: CasAttach.svelte required (Reveal in Finder on cas_hash)")
    web = _web_logic(crate)
    surface = _bubble_and_attach_surface(crate)
    rust = _tauri_rust_blob(crate)
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    pkg = (crate / "package.json").read_text() if (crate / "package.json").is_file() else ""
    caps_path = crate / "capabilities" / "default.json"
    caps = caps_path.read_text() if caps_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) Context menu on a person-timeline bubble.
    if not _CONTEXTMENU.search(surface):
        fail(
            "#135: person-timeline bubble must have a context menu "
            "(on:contextmenu / ContextMenu) for Copy text"
        )

    # 2) Custom menu: Copy text → clipboard (message text).
    if not _COPY_TEXT_LABEL.search(surface) and not _COPY_TEXT_LABEL.search(web):
        fail("#135: context menu must include Copy text")
    if not _WRITE_TEXT.search(web):
        fail(
            "#135: Copy text must write the message text to the clipboard "
            "(navigator.clipboard.writeText)"
        )
    copy_surf = _copy_handler_surface(web)
    if not re.search(r"body_text|displayBody|bodyText", copy_surf):
        fail("#135: clipboard write must be the message text (body_text / displayBody)")

    # 3) Copy does not log the body.
    if _copy_logs_body(copy_surf) or _copy_logs_body(_windows_around(web, _WRITE_TEXT)):
        fail(
            "#135: Copy must not log the message body "
            "(no console.log / eprintln of the text)"
        )

    # 4) Attachment with cas_hash → Reveal in Finder.
    if not _REVEAL_LABEL.search(surface) and not _REVEAL_LABEL.search(web):
        fail(
            "#135: attachment with cas_hash must offer Reveal in Finder "
            "(context menu on the attachment)"
        )
    reveal_win = _windows_around(surface, _REVEAL_LABEL, before=520, after=240)
    if not reveal_win.strip():
        reveal_win = _windows_around(web, _REVEAL_LABEL, before=520, after=240)
    if not re.search(r"cas_hash|casHash|hashOf", reveal_win + "\n" + surface):
        fail("#135: Reveal in Finder is only for an attachment that has cas_hash")

    # 5) Frontend sends only the hash to the reveal command.
    cmd = _reveal_cmd_name(rust, web)
    if not cmd:
        fail(
            "#135: frontend must invoke a reveal command that takes the hash only "
            "(e.g. reveal_cas) — not a path or URL"
        )
    payloads = _invoke_payloads(web, _REVEAL_INVOKE)
    if not payloads:
        # api.revealCas(hash) wrapper — still must mention hash, not path/url.
        call_win = _windows_around(web, _REVEAL_CMD, before=80, after=160)
        if not re.search(r"\bhash\b", call_win, re.I):
            fail(
                "#135: frontend must send only the hash to reveal "
                "(invoke reveal_cas with { hash })"
            )
        if _payload_has_path_or_url(call_win):
            fail(
                "#135: frontend must send only the hash to reveal "
                "(do not pass a path or URL from the webview)"
            )
    for payload in payloads:
        if not re.search(r"\bhash\b", payload, re.I):
            fail(
                "#135: frontend must send only the hash to reveal "
                "(invoke reveal_cas with { hash })"
            )
        if _payload_has_path_or_url(payload):
            fail(
                "#135: frontend must send only the hash to reveal "
                "(do not pass a path or URL from the webview)"
            )

    # 6) Rust command: hash only; cas_blob_path; under cas/; file-only open.
    sig = _rust_fn_signature(rust, cmd)
    body = _rust_body_with_callees(rust, cmd)
    if not body.strip():
        fail(
            f"#135: Rust command {cmd} must resolve cas/ab/cd/<hash> "
            "(fn reveal_cas taking the hash only)"
        )
    if not re.search(r"\bhash\b", sig, re.I):
        fail("#135: reveal command must take a hash (not a path or URL)")
    if re.search(r"\b(?:path|url|file|href|uri)\s*:", sig, re.I):
        fail(
            "#135: reveal command must take the hash only — "
            "do not take a path or URL from the webview"
        )
    if "cas_blob_path" not in body:
        fail(
            "#135: reveal must resolve cas/ab/cd/<hash> via cas_blob_path "
            "(64 hex only — reject anything else)"
        )
    if not re.search(r"\bcanonicalize\s*\(", body):
        fail("#135: reveal must canonicalize the CAS path")
    if not re.search(
        r"("
        r"starts_with"
        r"|outside cas"
        r"|join\(\s*[\"']cas[\"']"
        r"|[\"']cas/"
        r")",
        body,
    ):
        fail("#135: reveal must refuse anything outside cas/")
    if not re.search(r"generate_handler!\s*\[[^\]]*\b" + re.escape(cmd) + r"\b", rust, re.S):
        fail(f"#135: register {cmd} in generate_handler")

    if not re.search(r"std::process|\buse\s+std::process", rust):
        fail(
            "#135: open Finder with std::process "
            "(not tauri-plugin-shell / plugin-opener)"
        )
    if not re.search(r"Command::new|std::process::Command", body):
        fail(
            "#135: reveal must open the local file with std::process::Command "
            "(/usr/bin/open -R or a file:// URL)"
        )
    if "/usr/bin/open" not in body:
        fail("#135: open the local CAS file with /usr/bin/open (file only, not http)")
    if not re.search(r"[\"']-R[\"']", body) and "file://" not in body:
        fail("#135: use /usr/bin/open -R or a file:// URL to the CAS path")
    if re.search(r"[\"']https?://", body):
        fail("#135: reveal must not open http(s) — file only")
    if _ARBITRARY_SHELL.search(body) or _ARBITRARY_SHELL.search(rust):
        fail("#135: no shell of arbitrary commands — only /usr/bin/open on the CAS file")
    for m in re.finditer(r"Command::new\s*\(", body):
        arg = _rust_call_arg(body, m.end() - 1)
        if "/usr/bin/open" not in arg:
            fail(
                "#135: no shell of arbitrary commands — "
                "Command::new must be /usr/bin/open on the CAS file"
            )

    # 7) Bans: plugin-shell / opener / shell caps / Share / AirDrop.
    if _PLUGIN_SHELL.search(toml) or _PLUGIN_SHELL.search(pkg):
        fail(
            "#135: do not add tauri-plugin-shell / tauri-plugin-opener "
            "(std::process file-only open)"
        )
    if _PLUGIN_SHELL.search(rust) or _PLUGIN_SHELL.search(web):
        fail(
            "#135: do not add tauri-plugin-shell / tauri-plugin-opener "
            "(std::process file-only open)"
        )
    if _SHELL_CAP.search(caps):
        fail(
            "#135: capabilities must not add shell:allow-execute / "
            "shell:allow-open / opener (no arbitrary Command)"
        )
    if _SHARE_AIRDROP.search(web) or _SHARE_AIRDROP.search(rust) or _SHARE_ITEM.search(surface):
        fail("#135: no Share sheet / AirDrop")

    # 8) Docs: right-click copy text; reveal local CAS in Finder; no Share / AirDrop.
    if not dtxt.strip():
        fail("#135: docs/user/app.md required (right-click copy text; reveal in Finder)")
    doc_win = ""
    for m in re.finditer(
        r".{0,180}(?:right-click|context menu|Copy text|Reveal in Finder|AirDrop|Share sheet).{0,180}",
        dtxt,
        re.I | re.S,
    ):
        doc_win += m.group(0) + "\n"
    if not doc_win.strip():
        fail(
            "#135: docs/user/app.md must say right-click Copy text "
            "and reveal local CAS in Finder"
        )
    if not re.search(r"right-click|context menu", doc_win, re.I):
        fail("#135: docs/user/app.md must say right-click (or context menu) to copy text")
    if not re.search(r"copy text", doc_win, re.I):
        fail("#135: docs/user/app.md must describe Copy text")
    if not re.search(r"reveal", doc_win, re.I):
        fail("#135: docs/user/app.md must say reveal local CAS in Finder")
    if not re.search(r"Finder", doc_win):
        fail("#135: docs/user/app.md must say reveal local CAS in Finder")
    if not re.search(r"CAS|cas/", doc_win, re.I):
        fail("#135: docs/user/app.md must say the reveal target is a local CAS file")
    if not re.search(
        r"("
        r"no Share"
        r"|not Share"
        r"|Share sheet"
        r"|AirDrop"
        r")",
        doc_win,
        re.I,
    ):
        fail("#135: docs/user/app.md must say no Share / AirDrop")
