"""Chrome search field / as-you-type asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _FETCH_CALL,
    _PEOPLE_AWAIT_REFRESH,
    _VIEW_SEARCH_ASSIGN,
    _expand_fn_calls,
    _function_body,
    _js_next,
    _match_closer,
    _product_svelte,
    _svelte_markup,
    _template_stack,
    _ts_fn_body,
    _web_sources,
    _without_comments,
)

from tauri_gate.import_boot import (
    _ident_negated,
    _if_gen_eq_contains,
    _people_list_gen,
    _review_if_return_conds,
    _same_block_gen_ne_return,
    _svelte_open_tag_at,
    _try_catch_blocks,
)

from tauri_gate.media_linkify import _hook_element_blocks

from tauri_gate.search_hits import (
    _SEARCH_HIGHLIGHT_HELPER,
    _SEARCH_MARK_TAG,
    _SEARCH_SNIPPET_SPLIT,
)

from tauri_gate.search_picker import (
    _SEARCH_FILTERS_HOOK,
    _SEARCH_Q_ID,
)

from tauri_gate.status_toasts import (
    _FOCUS_SEARCH_Q,
    _claim_without_negation,
    _cond_code,
    _first_substr_pos,
    _owned_skeleton_names,
    _skeleton_hook_positions,
    _svelte_effect_args,
    _tag_inner,
)



_API_SEARCH_CALL = re.compile(r"\bapi\.search\s*\(")
_INVOKE_SEARCH_CMD = re.compile(
    r"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']search(?:_cmd)?[\"']",
    re.I,
)
_CHROME_TO_Q = re.compile(
    r"("
    r"getElementById\s*\(\s*[\"']q[\"']"
    r"|querySelector\s*\(\s*[\"']#q[\"']"
    r"|bind:value=\{[^}]*\bq\b[^}]*\}"
    r"|\bq\s*=\s*"
    r")"
)
_CHROME_FIELD_EL = re.compile(r"<Input\b|<input\b|<form\b", re.I)
_SPOTLIGHT_WORD = re.compile(r"\bspotlight\b", re.I)
_MULTI_ARCHIVE_WORD = re.compile(r"\bmulti[- ]archive\b", re.I)
_REMOTE_SEARCH_WORD = re.compile(
    r"("
    r"\bremote\s+search\b"
    r"|search\s+(?:the\s+)?(?:web|cloud|network)\b"
    r"|https?://[^\s\"']+/search"
    r")",
    re.I,
)


def _chrome_search_handler_surface(app: str, chrome_chunk: str) -> str:
    """Markup around the hook plus named submit/focus/key handlers."""
    parts = [chrome_chunk]
    names = re.findall(
        r"(?:on:submit|onsubmit|on:focus|onfocus|on:keydown|onkeydown|"
        r"on:input|oninput|on:change|onchange|on:click|onclick|on:blur|onblur)"
        r"\s*=\s*\{[^}]{0,160}?\b([A-Za-z_][\w]*)\s*\(",
        chrome_chunk,
    )
    names += re.findall(
        r"(?:on:submit|onsubmit|on:focus|onfocus|on:keydown|onkeydown|"
        r"on:input|oninput|on:change|onchange|on:click|onclick)"
        r"\s*=\s*\{([A-Za-z_][\w]*)\}",
        chrome_chunk,
    )
    for extra in (
        "onChromeSearch",
        "chromeSearch",
        "submitChromeSearch",
        "focusChromeSearch",
        "openChromeSearch",
        "goSearch",
        "routeChromeSearch",
    ):
        names.append(extra)
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        inner = _ts_fn_body(app, name) or _function_body(app, name)
        if inner:
            parts.append(_expand_fn_calls(app, inner))
    return "\n".join(parts)


# #208 — always-available chrome search field (not only the Search tab).
_CHROME_SEARCH_HOOK = re.compile(r"\bdata-chrome-search\b", re.I)


def assert_chrome_search_field(crate: Path) -> None:
    """#208: always-available chrome search field; #q stays canonical.

    data-chrome-search lives in App.svelte chrome (nav/header), not only
    SearchPane. Using it routes to Search and focuses / copies into #q.
    SearchPane run() remains the only api.search caller. No Spotlight,
    no multi-archive, no remote search, no second FTS.
    Not #209 filters, #210 hit density, #211 titlebar, #215 palette,
    #224 virtualizer.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#208: App.svelte required (chrome search field lives in nav/header)")
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#208: SearchPane.svelte required (#q stays the canonical query)")
    app = app_path.read_text()
    search = search_path.read_text()
    markup = _svelte_markup(app)
    app_clean = _without_comments(app)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) Chrome hook in App.svelte nav/header — not only SearchPane.
    if not _CHROME_SEARCH_HOOK.search(app):
        if _CHROME_SEARCH_HOOK.search(search):
            fail(
                "#208: data-chrome-search must be in App.svelte chrome "
                "(nav/header), not only inside SearchPane"
            )
        fail(
            "#208: App.svelte chrome (nav/header) must include a search field "
            "/ wrapper with data-chrome-search (visible when the archive is "
            "open, not only on the Search tab)"
        )
    if not _CHROME_SEARCH_HOOK.search(markup):
        fail(
            "#208: data-chrome-search must be in App.svelte chrome markup "
            "(nav/header), not only a script string"
        )

    chrome_chunks = [
        chunk
        for tag in ("nav", "header")
        for chunk in _tag_inner(markup, tag)
        if _CHROME_SEARCH_HOOK.search(chunk)
    ]
    if not chrome_chunks:
        fail(
            "#208: data-chrome-search must sit in App.svelte <nav> or <header> "
            "chrome, not only inside a pane"
        )
    chrome_chunk = chrome_chunks[0]
    hook = _CHROME_SEARCH_HOOK.search(markup)
    if hook:
        for kind, cond, _extra in _template_stack(markup, hook.start()):
            if kind in {"if", "if-else"} and re.search(
                r"view\s*===?\s*[\"']search[\"']", cond
            ):
                fail(
                    "#208: chrome search (data-chrome-search) must be available "
                    "whenever the archive is open, not only when view === \"search\""
                )
            if (
                kind == "if"
                and re.search(r"\bsetup\b", cond)
                and not re.search(r"!\s*setup", cond)
            ):
                fail(
                    "#208: chrome search must be visible when the archive is "
                    "open (st && !setup), not only on the setup screen"
                )

    # 2) #q stays the canonical field in SearchPane (do not steal the id).
    if not re.search(r"id=[\"']q[\"']", search):
        fail("#208: SearchPane must keep id=\"q\" as the canonical query field")
    if re.search(r"id=[\"']q[\"']", markup):
        fail(
            "#208: #q stays the canonical field in SearchPane — do not give "
            "the chrome field id=\"q\""
        )

    # 3) Chrome field is an input / form (or wraps one).
    around = markup[
        max(0, (hook.start() if hook else 0) - 220) : (hook.end() if hook else 0) + 700
    ]
    if not _CHROME_FIELD_EL.search(chrome_chunk) and not _CHROME_FIELD_EL.search(around):
        fail(
            "#208: data-chrome-search must be a search field or wrap one "
            "(Input / input / form) in App chrome"
        )

    # 4) Chrome path routes to Search and focuses / copies into #q.
    chrome_surface = _chrome_search_handler_surface(app, chrome_chunk + "\n" + around)
    if not _VIEW_SEARCH_ASSIGN.search(chrome_surface):
        fail(
            "#208: chrome search field must route to Search "
            "(view = \"search\") and then focus #q (or copy into #q)"
        )
    if not _CHROME_TO_Q.search(chrome_surface) and not _FOCUS_SEARCH_Q.search(
        chrome_surface
    ):
        fail(
            "#208: chrome search field must focus #q or copy the typed text "
            "into #q (SearchPane query stays canonical)"
        )

    # 5) SearchPane run() remains the only api.search caller.
    run_body = _ts_fn_body(search, "run") or _function_body(search, "run")
    if not run_body or not _API_SEARCH_CALL.search(run_body):
        fail(
            "#208: SearchPane run() must remain the only api.search caller "
            "(do not add a second FTS path)"
        )
    if _API_SEARCH_CALL.search(app_clean):
        fail(
            "#208: App.svelte must not call api.search — SearchPane run() is "
            "the only search IPC"
        )
    if _INVOKE_SEARCH_CMD.search(app_clean):
        fail(
            "#208: App.svelte must not invoke search / search_cmd — SearchPane "
            "run() remains the only api.search caller"
        )
    for p in _product_svelte(crate):
        if p.name == "SearchPane.svelte":
            continue
        other = _without_comments(p.read_text())
        if _API_SEARCH_CALL.search(other):
            fail(
                f"#208: {p.relative_to(crate)} must not call api.search — "
                "SearchPane run() is the only caller"
            )
        if _INVOKE_SEARCH_CMD.search(other):
            fail(
                f"#208: {p.relative_to(crate)} must not invoke search — "
                "SearchPane run() remains the only api.search caller"
            )

    # 6) D24: chrome always available; ⌘F from every view including People → #q;
    #    `/` still people filter.
    if not dtxt.strip():
        fail(
            "#208: docs/user/app.md required — chrome search is always available"
        )
    if not re.search(
        r"("
        r"chrome.{0,48}search.{0,48}(?:always|every|nav|header)"
        r"|search.{0,48}(?:always available|in (?:the )?chrome|in (?:the )?nav)"
        r"|always[- ]available.{0,24}search"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail("#208: docs/user/app.md must say chrome search is always available")
    if not re.search(
        r"("
        r"(?:⌘\s*F|Ctrl\+F|Ctrl-F).{0,160}"
        r"(?:every view|including People|from People).{0,80}(?:#q|Search)"
        r"|(?:every view|including People).{0,80}(?:⌘\s*F|Ctrl\+F|Ctrl-F)"
        r".{0,80}(?:#q|Search)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#208: docs/user/app.md must say ⌘F from every view including "
            "People focuses #q"
        )
    if not re.search(
        r"("
        r"`/`"
        r"|slash"
        r")"
        r".{0,120}"
        r"("
        r"people filter"
        r"|#person-filter"
        r"|person-filter"
        r"|filters? (?:the )?(?:loaded )?people"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#208: docs/user/app.md must keep `/` focusing the people filter"
        )

    # 7) Not: Spotlight, multi-archive, remote search / rewritten FTS.
    #    Do not require #209 filters, #210 hit density, #211 titlebar,
    #    #215 palette, or #224 virtualizer.
    web_claim = "\n".join(p.read_text() for p in _web_sources(crate)) + "\n" + dtxt
    if _claim_without_negation(web_claim, _SPOTLIGHT_WORD):
        fail("#208: not in scope — no Spotlight / OS-wide search")
    if _claim_without_negation(web_claim, _MULTI_ARCHIVE_WORD):
        fail("#208: not in scope — no multi-archive search")
    if _claim_without_negation(web_claim, _REMOTE_SEARCH_WORD):
        fail("#208: not in scope — no remote search")
_SEARCH_Q_TOKEN = re.compile(r"(?<![\w$])q(?![\w$])")
_SEARCH_TYPE_INPUT_ATTR = re.compile(
    r"(?:on:input|oninput|on:keyup|onkeyup)\s*=",
    re.I,
)
_SEARCH_TYPE_HANDLER = re.compile(
    r"(?:on:input|oninput|on:keyup|onkeyup)\s*=\s*\{"
    r"(?:"
    r"\s*([A-Za-z_][\w]*)\s*\}"
    r"|[^}]{0,240}?\b([A-Za-z_][\w]*)\s*\("
    r")",
    re.I,
)
_SEARCH_AS_YOU_TYPE_TRIGGER = re.compile(
    r"("
    r"\brun\s*\("
    r"|\bapi\.search\s*\("
    r"|setTimeout\s*\(\s*(?:async\s*)?(?:\(\s*\)\s*=>\s*)?(?:void\s+)?run\b"
    r"|debounce(?:d)?\s*\(\s*(?:async\s*)?(?:\(\s*\)\s*=>\s*)?(?:void\s+)?run\b"
    r")",
)
_SEARCH_PEOPLE_FROM_RUN = re.compile(
    r"("
    r"\brefreshPeople\s*\("
    r"|\bapplyStatus\s*\("
    r"|\bapi\.people\s*\("
    r"|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']people[\"']"
    r")",
)
_SEARCH_DISABLED_PEOPLE = re.compile(
    r"disabled\s*=\s*\{[^}]*\bpeopleLoading\b",
    re.I,
)
_TANTIVY_WORD = re.compile(r"\btantivy\b", re.I)
_SEARCH_TYPE_HANDLER_SKIP = frozenset(
    {
        "preventDefault",
        "stopPropagation",
        "stopImmediatePropagation",
        "trim",
        "String",
        "Number",
        "Boolean",
        "clearTimeout",
        "setTimeout",
        "requestAnimationFrame",
        "queueMicrotask",
    }
)
_DOCS_TYPE_TO_SEARCH = re.compile(
    r"("
    r"search[- ]as[- ]you[- ]type"
    r"|as[- ]you[- ]type"
    r"|type[- ]to[- ]search"
    r"|typ(?:e|ing|es)\s+(?:a\s+token|in\s+(?:search\s+)?#q|in\s+the\s+query)"
    r".{0,80}(?:search(?:es)?|runs?\s+(?:a\s+)?search|starts?\s+search)"
    r"|typ(?:e|ing)\s+in\s+(?:search\s+)?#q\s+search"
    r")",
    re.I | re.S,
)
_DOCS_SEARCH_NOT_WAIT_PEOPLE = re.compile(
    r"("
    r"(?:search|#q|typ(?:e|ing)).{0,100}"
    r"(?:does not wait|doesn't wait|do not wait|without waiting|"
    r"not blocked|is not blocked|not wait)"
    r".{0,80}people"
    r"|"
    r"(?:does not wait|doesn't wait|without waiting|not blocked)"
    r".{0,80}people.{0,40}(?:list|refresh|rebuild)"
    r"|"
    r"people.{0,40}(?:list|refresh|rebuild).{0,60}"
    r"(?:does not block|doesn't block|do not block|not block)"
    r".{0,40}(?:search|#q)"
    r")",
    re.I | re.S,
)
_SEARCH_HITS_EMPTY = re.compile(
    r"("
    r"!\s*hits(?:\s*\.length)?\b"
    r"|hits\.length\s*(?:===?|<=|<)\s*0\b"
    r"|0\s*(?:===?|>=|>)\s*hits\.length"
    r"|hits\.length\s*<\s*1\b"
    r")",
)
_SEARCH_HITS_NONEMPTY = re.compile(
    r"("
    r"hits\.length\s*(?:>|>=|!==?)\s*0\b"
    r"|hits\.length\s*(?:>|>=)\s*[1-9]"
    r"|(?<!!)\bhits\.length\b"
    r")",
)
_SEARCH_PRE_IPC_EXPANDED = re.compile(
    r"\bexpanded\s*=\s*(?:null|undefined|void\s+0)\b"
)
_SEARCH_PRE_IPC_BODY = re.compile(r"\bbody\s*=\s*(?:\"\"|''|``)")
_SEARCH_PRE_IPC_HITINDEX = re.compile(r"\bhitIndex\s*=(?!=)")
_SEARCH_PRE_IPC_HITS_CLEAR = re.compile(r"\bhits\s*=\s*\[\s*\]")
_SEARCH_CLEAR_TIMEOUT = re.compile(r"\bclear(?:Timeout|Interval)\s*\(")
_SEARCH_TIMER_PERSON_BLUR = re.compile(r"personBlur", re.I)
_SEARCH_ERR_HANDLER = re.compile(r"\b(?:showErr|onError)\b")
_SEARCH_VOID_CALL = re.compile(r"\bvoid\s+([A-Za-z_$][\w$]*)\s*\(")
_SEARCH_RESTATE_DEBOUNCE_COMMENT = re.compile(
    r"Typing in #q searches\s*\(\s*debounce\s*\)",
    re.I,
)


def _search_q_open_tag(markup: str) -> str:
    """Open <Input>/<input> tag that carries id=q."""
    for m in re.finditer(r"<(?:Input|input)\b", markup, re.I):
        tag = _svelte_open_tag_at(markup, m.start())
        if _SEARCH_Q_ID.search(tag):
            return tag
    return ""


def _search_type_input_surface(src: str, q_tag: str) -> str:
    """Named / inline input handlers on the #q field (not the person filter)."""
    if not q_tag or not _SEARCH_TYPE_INPUT_ATTR.search(q_tag):
        return ""
    parts = [q_tag]
    names: list[str] = []
    for m in _SEARCH_TYPE_HANDLER.finditer(q_tag):
        names.extend(n for n in m.groups() if n)
    seen: set[str] = set()
    for name in names:
        if name in seen or name in _SEARCH_TYPE_HANDLER_SKIP:
            continue
        seen.add(name)
        inner = _ts_fn_body(src, name) or _function_body(src, name)
        if inner:
            parts.append(_expand_fn_calls(src, inner))
    return "\n".join(parts)


def _search_as_you_type_surface(src: str, markup: str) -> str:
    """Effect / #q-input blobs that can fire search when the query changes.

    Form onsubmit / chrome requestSubmit do not count (that is submit-only).
    Person-filter oninput does not count (different field).
    """
    parts: list[str] = []
    for arg in _svelte_effect_args(src):
        if not _SEARCH_Q_TOKEN.search(arg):
            continue
        parts.append(_expand_fn_calls(src, arg))
    q_tag = _search_q_open_tag(markup)
    input_surf = _search_type_input_surface(src, q_tag)
    if input_surf.strip():
        parts.append(input_surf)
    return "\n".join(parts)


def _has_search_as_you_type(src: str, markup: str) -> bool:
    surface = _search_as_you_type_surface(src, markup)
    return bool(surface.strip()) and bool(_SEARCH_AS_YOU_TYPE_TRIGGER.search(surface))


def _search_gated_on_people_loading(
    stack: list[tuple[str, str, str]],
) -> bool:
    """True if Search is only mounted when peopleLoading is false."""
    for kind, cond, _extra in stack:
        if not re.search(r"\bpeopleLoading\b", cond):
            continue
        if kind == "if" and re.search(r"!\s*peopleLoading", cond):
            return True
        if kind == "if-else" and not re.search(r"!\s*peopleLoading", cond):
            return True
    return False


def _cond_requires_empty_hits(cond: str) -> bool:
    """True if this {#if} only runs when the hits list is empty."""
    return bool(_SEARCH_HITS_EMPTY.search(_cond_code(cond)))


def _cond_requires_existing_hits(cond: str) -> bool:
    """True if this {#if} only runs when previous hits are on screen."""
    code = _cond_code(cond)
    if _SEARCH_HITS_EMPTY.search(code):
        return False
    return bool(_SEARCH_HITS_NONEMPTY.search(code))


def _stack_searching_true(stack: list[tuple[str, str, str]]) -> bool:
    """True if this markup sits in a branch shown while `searching` is true."""
    for kind, cond, _extra in stack:
        if not re.search(r"\bsearching\b", cond):
            continue
        code = _cond_code(cond)
        if kind == "if":
            return not _ident_negated(code, "searching")
        if kind == "if-else":
            return _ident_negated(code, "searching")
    return False


def _stack_requires_empty_hits(stack: list[tuple[str, str, str]]) -> bool:
    for kind, cond, _extra in stack:
        if kind == "if" and _cond_requires_empty_hits(cond):
            return True
        if kind == "if-else" and _cond_requires_existing_hits(cond):
            return True
    return False


def _stack_requires_existing_hits(stack: list[tuple[str, str, str]]) -> bool:
    for kind, cond, _extra in stack:
        if kind == "if" and _cond_requires_existing_hits(cond):
            return True
        if kind == "if-else" and _cond_requires_empty_hits(cond):
            return True
    return False


def _search_skeleton_stacks(
    markup: str, src: str
) -> list[list[tuple[str, str, str]]]:
    """Template stacks at each #203 skeleton hook in Search markup."""
    names = _owned_skeleton_names(src)
    return [
        _template_stack(markup, pos)
        for pos in _skeleton_hook_positions(markup, names)
    ]


def _blank_returning_blocks(src: str) -> str:
    """Blank `{ … return … }` so error-path assigns are not the start of run()."""
    chars = list(src)
    i = 0
    n = len(src)
    while i < n:
        nxt = _js_next(src, i)
        if nxt != i:
            i = nxt
            continue
        if src[i] == "{":
            close = _match_closer(src, i)
            if close > i and re.search(r"\breturn\b", src[i + 1 : close]):
                for k in range(i, close + 1):
                    if chars[k] not in "\n\r":
                        chars[k] = " "
                i = close + 1
                continue
        i += 1
    return "".join(chars)


def _run_before_ipc(body: str) -> str:
    """run() text before the first `api.search` (error-return blocks blanked)."""
    ipc_at = _first_substr_pos(body, ("api.search",))
    prefix = body if ipc_at < 0 else body[:ipc_at]
    return _blank_returning_blocks(prefix)


def _run_clears_debounce_timer(pre_ipc: str) -> bool:
    """True if the pre-IPC prefix clears a timer other than the person-blur one."""
    for m in _SEARCH_CLEAR_TIMEOUT.finditer(pre_ipc):
        open_p = pre_ipc.find("(", m.start())
        if open_p < 0:
            continue
        close = _match_closer(pre_ipc, open_p)
        arg = pre_ipc[open_p + 1 : close] if close > open_p else ""
        if _SEARCH_TIMER_PERSON_BLUR.search(arg):
            continue
        return True
    return False


def _js_unawaited_calls(blob: str, name: str) -> list[int]:
    """Close-paren index of each `name(` that is not `await` / a definition."""
    out: list[int] = []
    for m in re.finditer(rf"\b{re.escape(name)}\s*\(", blob):
        before = blob[: m.start()]
        if re.search(r"\bawait\s+$", before):
            continue
        if re.search(r"\b(?:async\s+)?function\s+$", before):
            continue
        if re.search(
            rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*"
            rf"(?:async\s*)?(?:function\s*)?$",
            before,
        ):
            continue
        open_p = m.end() - 1
        close = _match_closer(blob, open_p)
        if close > open_p:
            out.append(close)
    return out


def _trailing_catch_has_err(blob: str, close: int) -> bool:
    """True if `name(…)` is followed by `.catch(…showErr|onError…)`."""
    rest = blob[close + 1 :].lstrip()
    if not rest.startswith(".catch"):
        return False
    open_p = blob.find("(", close + 1)
    if open_p < 0:
        return False
    end = _match_closer(blob, open_p)
    if end < 0:
        return False
    return bool(_SEARCH_ERR_HANDLER.search(blob[open_p + 1 : end]))


def _fire_forget_people_caught(app: str, apply_body: str) -> bool:
    """applyStatus's unawaited refreshPeople (or a void wrapper) has .catch."""
    sites = _js_unawaited_calls(apply_body, "refreshPeople")
    if sites:
        return all(_trailing_catch_has_err(apply_body, close) for close in sites)
    for m in _SEARCH_VOID_CALL.finditer(apply_body):
        name = m.group(1)
        if name == "refreshPeople":
            continue
        inner = _ts_fn_body(app, name) or _function_body(app, name)
        if not inner or not re.search(r"\brefreshPeople\s*\(", inner):
            continue
        inner_sites = _js_unawaited_calls(inner, "refreshPeople")
        if inner_sites and all(
            _trailing_catch_has_err(inner, close) for close in inner_sites
        ):
            return True
        return False
    return False


def _hits_key_bails_on_searching(body: str) -> bool:
    """True if a hit-key if-return fires on `searching` while hits exist."""
    for cond in _review_if_return_conds(body):
        if not re.search(r"(?<![\w.])searching\b", cond):
            continue
        if _ident_negated(cond, "searching") and not re.search(
            r"(?<![!\w.])searching\b", cond
        ):
            continue
        # `searching && !hits.length` only — not a bail on a visible list.
        if (
            _SEARCH_HITS_EMPTY.search(cond)
            and "&&" in cond
            and "||" not in cond
        ):
            continue
        return True
    return False


def _js_comment_text(src: str) -> str:
    """`//` and `/*` blobs only (markup / strings skipped via `_js_next`)."""
    bits: list[str] = []
    i = 0
    n = len(src)
    while i < n:
        if src.startswith("//", i) or src.startswith("/*", i):
            end = _js_next(src, i)
            bits.append(src[i:end])
            i = end
            continue
        nxt = _js_next(src, i)
        i = nxt if nxt != i else i + 1
    return "\n".join(bits)


def _js_dot_catch_args(blob: str) -> list[str]:
    """Argument blobs of each `.catch(` (strings / comments skipped)."""
    out: list[str] = []
    i = 0
    n = len(blob)
    while i < n:
        nxt = _js_next(blob, i)
        if nxt != i:
            i = nxt
            continue
        if blob.startswith(".catch", i) and (
            i + 6 >= n or not (blob[i + 6].isalnum() or blob[i + 6] in "_$")
        ):
            j = i + 6
            while j < n and blob[j] in " \t\n\r":
                j += 1
            if j < n and blob[j] == "(":
                close = _match_closer(blob, j)
                if close > j:
                    out.append(blob[j + 1 : close])
                    i = close + 1
                    continue
        i += 1
    return out


def _js_handler_body(arg: str) -> str:
    """Normalize a `.catch` argument to a body-like blob.

    Bare `showErr` / `onError` become `showErr()` so the call regex hits.
    """
    s = arg.strip()
    if not s:
        return ""
    fn = re.match(r"(?:async\s+)?function\b", s)
    if fn:
        brace = s.find("{", fn.end())
        if brace >= 0:
            close = _match_closer(s, brace)
            if close > brace:
                return s[brace + 1 : close]
    arrow = re.match(
        r"(?:async\s+)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>",
        s,
    )
    if arrow:
        rest = s[arrow.end() :].lstrip()
        if rest.startswith("{"):
            close = _match_closer(rest, 0)
            if close > 0:
                return rest[1:close]
        return rest
    if re.fullmatch(r"[A-Za-z_$][\w$]*", s):
        return f"{s}()"
    return s


def _refresh_people_catch_blobs(refresh: str) -> list[str]:
    """try/catch bodies and `.catch` handlers inside refreshPeople."""
    blobs = [catch for _try, catch in _try_catch_blocks(refresh)]
    blobs.extend(_js_handler_body(arg) for arg in _js_dot_catch_args(refresh))
    return [b for b in blobs if b.strip()]


def _site_gen_guarded(body: str, pos: int, local: str, counter: str) -> bool:
    return _if_gen_eq_contains(body, pos, local, counter) or _same_block_gen_ne_return(
        body, pos, local, counter
    )


def _catch_err_positions(catch: str) -> list[int]:
    """showErr / onError / non-empty err= / throw sites in a catch blob."""
    pos: list[int] = []
    for m in re.finditer(r"\b(?:showErr|onError)\s*\(", catch):
        pos.append(m.start())
    for m in re.finditer(r"\berr\s*=(?!=)", catch):
        rest = catch[m.end() :].lstrip()
        if rest.startswith('""') or rest.startswith("''"):
            continue
        if re.match(r"['\"]\s*['\"]", rest):
            continue
        pos.append(m.start())
    for m in re.finditer(r"\bthrow\b", catch):
        pos.append(m.start())
    return pos


def _refresh_people_catch_gen_guarded(
    refresh: str, local: str, counter: str
) -> bool:
    """True if refreshPeople catch only surfaces errors when gen is current.

    Caller `void refreshPeople().catch(showErr)` is not gen-aware: a
    superseded `archive changed` still paints the banner. Requires a
    catch *inside* refreshPeople whose showErr / err= / throw is
    `if (gen === peopleGen)` (or `if (gen !== peopleGen) return`).
    """
    blobs = _refresh_people_catch_blobs(refresh)
    if not blobs:
        return False
    saw_surface = False
    for blob in blobs:
        sites = _catch_err_positions(blob)
        if not sites:
            continue
        saw_surface = True
        for pos in sites:
            if not _site_gen_guarded(blob, pos, local, counter):
                return False
    return saw_surface


def assert_search_as_you_type(crate: Path) -> None:
    """#270: typing in #q searches; do not hitch on a people refresh.

    `#q` / SearchPane needs an input / `$effect` / debounce path to `run()`
    / `api.search` — form submit alone is not enough. `run()` must not call
    `people` / `refreshPeople` / `applyStatus`. `#q` must not be disabled
    (or unmounted) because `peopleLoading` is true. Keep `#q`, `<mark>` /
    `splitSnippet`, `data-search-filters`. No Tantivy, no `fetch(`, no
    remote search. Docs: type-to-search; not blocked on people refresh.
    Do not rewrite #126 / #208 / #209 / #210 / #265.

    Follow-up (type-to-search lag): first in-flight (`searching`, no hits)
    still has the #203 skeleton. Later `run()` must not clear `expanded` /
    `hitIndex` / `body` before `api.search`. Previous `hits` stay until
    the gen-guarded assign — no `hits = []` at the start of `run()`, and
    `{#if searching}` must not paint the skeleton over existing hits.
    Do not rewrite #203 / #205 / the rest of #270.

    Follow-up (PR #288 review fold): `run()` clears the debounce timer
    (or a named timer) before `api.search`. `applyStatus` /
    `refreshPeople` fire-and-forget has `.catch` / `showErr` / `onError`.
    `onHitsKey` does not `return` solely on `searching` when hits exist.
    No restating “Typing in #q searches (debounce)” comment.

    Follow-up (PR #288 peopleGen catch): `refreshPeople` increments
    `peopleGen` and, in `catch`, only `showErr` / assigns error when
    `gen === peopleGen` (or equivalent). `applyStatus` still does not
    `await refreshPeople()`. Do not rewrite #265 / #205 / earlier #270.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#270: SearchPane.svelte required (type-to-search lives on #q)")
    app_path = crate / "web" / "App.svelte"
    src = search_path.read_text()
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    app = app_path.read_text() if app_path.is_file() else ""
    app_clean = _without_comments(app)
    app_markup = _svelte_markup(app) if app else ""
    docs_search = repo_root() / "docs" / "user" / "search.md"
    docs_app = repo_root() / "docs" / "user" / "app.md"
    dtxt = ""
    if docs_app.is_file():
        dtxt += docs_app.read_text() + "\n"
    if docs_search.is_file():
        dtxt += docs_search.read_text()

    # 1) Primary red: typing in #q must run search (debounce OK).
    #    bind:value + form onsubmit is submit-only and is not enough.
    if not _has_search_as_you_type(cleaned, surface):
        fail(
            "#270: #q / SearchPane must search as you type "
            "(input / $effect / debounce → run() / api.search) — "
            "not submit-only"
        )

    # 2) run() (or the as-you-type path) must not wait on a people rebuild.
    run_body = _ts_fn_body(cleaned, "run") or _function_body(cleaned, "run")
    run_surf = _expand_fn_calls(cleaned, run_body) if run_body else ""
    type_surf = _search_as_you_type_surface(cleaned, surface)
    if _SEARCH_PEOPLE_FROM_RUN.search(run_surf) or _SEARCH_PEOPLE_FROM_RUN.search(
        type_surf
    ):
        fail(
            "#270: run() / the as-you-type path must not call people / "
            "refreshPeople / applyStatus (hits stay usable while a people "
            "refresh is in flight)"
        )

    # 3) #q is not disabled or unmounted because people are loading.
    q_tag = _search_q_open_tag(surface) or _search_q_open_tag(src)
    if q_tag and _SEARCH_DISABLED_PEOPLE.search(q_tag):
        fail(
            "#270: #q must not be disabled={peopleLoading} "
            "(typing stays usable while the people list fills)"
        )
    for block in _hook_element_blocks(app_markup, "data-chrome-search"):
        if _SEARCH_DISABLED_PEOPLE.search(block):
            fail(
                "#270: chrome search must not be disabled={peopleLoading} "
                "(#q / the same run() stays usable while people loads)"
            )
    q_pos = _SEARCH_Q_ID.search(surface)
    if q_pos and _search_gated_on_people_loading(
        _template_stack(surface, q_pos.start())
    ):
        fail(
            "#270: #q must not sit behind {#if !peopleLoading} "
            "(Search stays mounted while the people list fills)"
        )
    sp = re.search(r"<SearchPane\b", app_markup)
    if sp and _search_gated_on_people_loading(
        _template_stack(app_markup, sp.start())
    ):
        fail(
            "#270: SearchPane must not sit behind {#if !peopleLoading} "
            "(Search stays usable while the people list fills)"
        )

    # 4) Keep #q, <mark> / splitSnippet, data-search-filters.
    if not _SEARCH_Q_ID.search(surface) and not re.search(r"id=[\"']q[\"']", src):
        fail('#270: keep id="q" as the canonical query field')
    if not _SEARCH_MARK_TAG.search(surface) and not _SEARCH_MARK_TAG.search(src):
        fail("#270: keep <mark> siblings on the search snippet path (#126)")
    if not (
        _SEARCH_HIGHLIGHT_HELPER.search(cleaned)
        or _SEARCH_SNIPPET_SPLIT.search(cleaned)
        or re.search(r"\bsplitSnippet\b", src)
    ):
        fail("#270: keep splitSnippet / snippet split on the hit path (#126)")
    if _SEARCH_FILTERS_HOOK not in surface and _SEARCH_FILTERS_HOOK not in src:
        fail("#270: keep data-search-filters (#209)")

    # 5) Submit still works (as-you-type is extra, not a submit delete).
    if not re.search(
        r"(?:on:submit|onsubmit)\s*=|type\s*=\s*[\"']submit[\"']",
        surface,
        re.I,
    ):
        fail(
            "#270: keep form submit → run() "
            "(as-you-type is in addition to submit, not a replacement)"
        )

    # 6) No Tantivy / no fetch( / remote search.
    rust_path = crate / "src" / "main.rs"
    rust = rust_path.read_text() if rust_path.is_file() else ""
    pkg = (crate / "package.json").read_text() if (crate / "package.json").is_file() else ""
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    product_claim = "\n".join(
        (cleaned, app_clean, rust, pkg, toml, dtxt)
    )
    if _claim_without_negation(product_claim, _TANTIVY_WORD):
        fail("#270: not in scope — no Tantivy (keep FTS5; that is #82)")
    if _FETCH_CALL.search(cleaned) or _FETCH_CALL.search(
        _search_as_you_type_surface(cleaned, surface)
    ):
        fail("#270: not in scope — no fetch( / remote search")
    if _claim_without_negation(product_claim, _REMOTE_SEARCH_WORD):
        fail("#270: not in scope — no remote search")

    # 7) D24: type-to-search; not blocked on people refresh.
    if not dtxt.strip():
        fail(
            "#270: docs/user/app.md required — typing in #q searches; "
            "does not wait for the people list"
        )
    if not _DOCS_TYPE_TO_SEARCH.search(dtxt):
        fail(
            "#270: docs/user/app.md must say typing in #q searches "
            "(search-as-you-type / type-to-search; debounce OK)"
        )
    if not _DOCS_SEARCH_NOT_WAIT_PEOPLE.search(dtxt):
        fail(
            "#270: docs/user/app.md must say search is not blocked on "
            "a people refresh / does not wait for the people list"
        )

    # 8) First in-flight (searching, no hits) still has the #203 skeleton.
    skel_stacks = _search_skeleton_stacks(surface, src)
    first_inflight = [
        st
        for st in skel_stacks
        if _stack_searching_true(st) and not _stack_requires_existing_hits(st)
    ]
    if not first_inflight:
        fail(
            "#270: first in-flight (searching, no hits) must still show "
            "the #203 skeleton — do not paint “No hits” / “Type a query” "
            "while the first api.search is in flight"
        )

    # 9) Follow-up searching must not paint that skeleton over existing hits.
    followup_flash = [
        st
        for st in skel_stacks
        if _stack_searching_true(st) and not _stack_requires_empty_hits(st)
    ]
    if followup_flash:
        fail(
            "#270: {#if searching} must not paint the #203 skeleton over "
            "existing hits — keep the previous list until the new "
            "api.search reply applies (gate the skeleton on no hits)"
        )

    # 10) Follow-up run() does not clear expanded / hitIndex / body before IPC.
    pre_ipc = _run_before_ipc(run_body) if run_body else ""
    if (
        _SEARCH_PRE_IPC_EXPANDED.search(pre_ipc)
        or _SEARCH_PRE_IPC_BODY.search(pre_ipc)
        or _SEARCH_PRE_IPC_HITINDEX.search(pre_ipc)
    ):
        fail(
            "#270: follow-up run() must not clear expanded / hitIndex / "
            "body before api.search — reset those only when applying the "
            "new hits (or on error / idle clear)"
        )

    # 11) Previous hits stay until the gen-guarded assign.
    if _SEARCH_PRE_IPC_HITS_CLEAR.search(pre_ipc):
        fail(
            "#270: previous hits must stay until the gen-guarded assign "
            "— no hits = [] at the start of run()"
        )

    # 12) run() clears the debounce timer before api.search (submit / Retry /
    #     chrome requestSubmit must not leave a second FTS armed).
    pre_timer = _expand_fn_calls(cleaned, pre_ipc) if pre_ipc else ""
    if not _run_clears_debounce_timer(pre_timer or pre_ipc):
        fail(
            "#270: run() must clear the debounce timer (or a named timer) "
            "before api.search — submit / Retry / chrome requestSubmit "
            "must not leave a second FTS armed"
        )

    # 13) applyStatus / refreshPeople fire-and-forget surfaces errors.
    apply_body = _ts_fn_body(app_clean, "applyStatus") or _function_body(
        app_clean, "applyStatus"
    )
    if not apply_body or not _fire_forget_people_caught(app_clean, apply_body):
        fail(
            "#270: applyStatus / refreshPeople fire-and-forget must "
            ".catch(showErr) / onError — do not leave void refreshPeople() "
            "unhandled"
        )

    # 14) Hit-list keys still work while a follow-up search is in flight.
    hits_key = (
        _ts_fn_body(cleaned, "onHitsKey")
        or _function_body(cleaned, "onHitsKey")
        or _ts_fn_body(cleaned, "onHitKey")
        or _function_body(cleaned, "onHitKey")
    )
    if hits_key and _hits_key_bails_on_searching(hits_key):
        fail(
            "#270: onHitsKey must not return solely on searching when "
            "hits exist — gate keyboard nav on !hits.length only"
        )

    # 15) Do not restate the $effect body in a comment.
    if _SEARCH_RESTATE_DEBOUNCE_COMMENT.search(_js_comment_text(src)):
        fail(
            '#270: drop the restating “Typing in #q searches (debounce)” '
            "comment — a one-liner on why the effect must not track "
            "run()’s other inputs is OK"
        )

    # 16) refreshPeople increments peopleGen (keep the success-path guard).
    refresh = _ts_fn_body(app_clean, "refreshPeople") or _function_body(
        app_clean, "refreshPeople"
    )
    people_tok = _people_list_gen(refresh) if refresh else None
    if not refresh or not people_tok:
        fail(
            "#270: refreshPeople must increment peopleGen "
            "(and keep people = next only when that gen is current)"
        )

    # 17) catch only showErr / assigns error when gen === peopleGen.
    #     Today's void refreshPeople().catch(showErr) is not enough —
    #     a superseded archive-changed still paints the banner.
    if not _refresh_people_catch_gen_guarded(
        refresh, people_tok[0], people_tok[1]
    ):
        fail(
            "#270: refreshPeople catch must only showErr / assign error "
            "when gen === peopleGen — a superseded people() "
            "(archive changed) must not paint the banner on the new archive"
        )

    # 18) applyStatus still does not await the people rebuild.
    if apply_body and _PEOPLE_AWAIT_REFRESH.search(apply_body):
        fail(
            "#270: applyStatus must not await refreshPeople() "
            "(search still must not wait on a people rebuild)"
        )
