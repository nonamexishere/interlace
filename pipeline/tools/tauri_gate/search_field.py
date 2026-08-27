"""Chrome search field / as-you-type asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.search_field_keys import *
from tauri_gate.search_field_debounce import *


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
    app_only = app_path.read_text()
    app = _web_logic(crate)
    search = _search_pane_blob(crate)
    markup = _svelte_markup(app)
    app_clean = _without_comments(app)
    app_clean_only = _without_comments(app_only)
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
    if re.search(r"id=[\"']q[\"']", _svelte_markup(app_only)):
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
    if _API_SEARCH_CALL.search(app_clean_only):
        fail(
            "#208: App.svelte must not call api.search — SearchPane run() is "
            "the only search IPC"
        )
    if _INVOKE_SEARCH_CMD.search(app_clean_only):
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
    src = _search_pane_blob(crate)
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    app = _web_logic(crate) if app_path.is_file() else ""
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
