"""Search jump / highlight / hit-density asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.search_hits_jump import *
from tauri_gate.search_hits_mark import *

    # Prefer (not hard-gated): pass hit.sent_at into onJumpToMessage /
    # openPersonAtMessage when present so the walk can seek near the hit.


def assert_search_jump_to_message(crate: Path) -> None:
    """#124: search hit with person_id jumps to that message on the person timeline.

    With person_id: switch to People, select that person, load a window around
    message_id, scroll the row into view, highlight once (tlIndex / ring as j/k).
    Without person_id: stay on Search and expand body (toggle / searchBody).
    Miss after bounded load: showErr (or equivalent); never ring last-loaded as hit.
    Virtualized timeline (#120): ensure target index enters the window
    (ensureTlIndexVisible / scroll estimate) when that path exists.
    Not: FTS rewrite, inventing a person when person_id is missing.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    app_path = crate / "web" / "App.svelte"
    if not search_path.is_file():
        fail("#124: SearchPane.svelte required (search hit jump lives there)")
    if not app_path.is_file():
        fail("#124: App.svelte required (People view / selectPerson / timeline scroll)")

    search_src = _search_pane_blob(crate)
    app_src = _web_logic(crate)
    logic = _web_logic(crate)
    search_clean = _without_comments(search_src)
    app_clean = _without_comments(app_src)
    logic_clean = _without_comments(logic)
    search_markup = _svelte_markup(search_src)
    surface = search_markup if search_markup.strip() else search_src
    # Jump path may live in SearchPane, App, or a small helper under web/.
    web_blob = search_clean + "\n" + app_clean + "\n" + logic_clean

    # 1) Hits must still be listed and activatable (click and/or keyboard Enter).
    if not re.search(r"\{#each\s+hits\b", surface) and not re.search(
        r"\{#each\s+hits\b", search_src
    ):
        fail("#124: SearchPane must list hits ({#each hits}) so a hit can be opened")
    has_hit_click = bool(
        re.search(r"(?:onclick|on:click)(?:\|\w+)*\s*=\s*\{", surface)
        and re.search(
            r"message_id|messageId|toggle|jump|openHit|openSearch|activate",
            surface + "\n" + search_clean,
            re.I,
        )
    )
    has_hit_enter = bool(
        re.search(r"(?:key|code)\s*===?\s*[\"']Enter[\"']", search_clean)
    )
    if not has_hit_click and not has_hit_enter:
        fail(
            "#124: search hits must be activatable (click and/or Enter) — "
            "a hit is not a dead end"
        )

    # 2) Without person_id: keep expand-body on Search (toggle / searchBody).
    if not _SEARCH_EXPAND_BODY.search(search_clean) and not _SEARCH_EXPAND_BODY.search(
        search_src
    ):
        fail(
            "#124: without person_id, stay on Search and expand body as today "
            "(toggle / api.searchBody / expanded = message_id) — do not invent a person"
        )

    # 3) Hit activation must invoke a jump/activate path (primary pre-impl red).
    #    Current SearchPane only toggle(h.message_id) / Enter → toggle — fail that.
    hit_activates_jump = bool(
        _HIT_ACTIVATES_JUMP.search(search_src)
        or _HIT_ACTIVATES_JUMP.search(search_clean)
        or _HIT_ACTIVATES_JUMP.search(surface)
    )
    if not hit_activates_jump:
        fail(
            "#124: search hit with person_id must not only expand the body on Search — "
            "click/Enter must call a jump handler (jumpToMessage / openSearchHit / "
            "activateHit / onJumpToMessage…) or branch on hit.person_id. "
            "Without person_id, expand body stays"
        )

    # 4) Jump handler must exist and do real work: People + person + message.
    jump_bodies = _search_jump_handler_bodies(web_blob)
    # Inline arrow assigned to prop: onJumpToMessage={async (pid, mid) => { ... }}
    inline_jump = re.findall(
        r"(?:onJumpToMessage|onOpenHit|onOpenSearchHit|onJumpHit|onSearchHit|onJump)\s*="
        r"\s*\{([\s\S]{0,1500}?)\}(?=\s|/?>)",
        app_src + "\n" + search_src,
        re.I,
    )
    jump_bodies.extend(inline_jump)

    has_jump_symbol = bool(
        _SEARCH_JUMP_FN.search(web_blob) or _SEARCH_JUMP_PROP.search(web_blob)
    )
    if not has_jump_symbol and not jump_bodies:
        fail(
            "#124: require a jump handler (jumpToMessage / openSearchHit / "
            "onJumpToMessage / activateHit / …) that opens the hit on the person timeline"
        )

    # App wires SearchPane callback, or SearchPane jumps itself (view/selectPerson).
    app_wires_jump = bool(
        re.search(
            r"<SearchPane\b[^>]{0,500}(?:"
            r"onJumpToMessage|onOpenHit|onOpenSearchHit|onJumpHit|onSearchHit|"
            r"jumpToMessage|openSearchHit|onJump|activateHit"
            r")",
            app_src,
            re.I,
        )
        or re.search(
            r"SearchPane[\s\S]{0,500}(?:"
            r"onJumpToMessage|onOpenHit|onOpenSearchHit|onJumpHit|onSearchHit|"
            r"jumpToMessage|openSearchHit|onJump|activateHit"
            r")",
            app_clean,
            re.I,
        )
    )
    search_jumps_inline = bool(
        _HIT_PERSON_ID_READ.search(search_clean)
        and (
            _VIEW_PEOPLE.search(search_clean)
            or re.search(r"\bselectPerson\s*\(|\bopenPerson\s*\(", search_clean)
        )
    )
    if not app_wires_jump and not search_jumps_inline and not jump_bodies:
        fail(
            "#124: wire SearchPane → App jump (onJumpToMessage={…} / jumpToMessage) "
            "or jump from SearchPane into People + selectPerson"
        )

    # Real work inside a jump handler (reject no-op name-only stubs).
    body_selects = any(_JUMP_BODY_SELECTS_PERSON.search(b) for b in jump_bodies)
    body_message = any(_JUMP_BODY_USES_MESSAGE.search(b) for b in jump_bodies)
    # selectPerson / view=people near a jump call site also counts (thin wrapper).
    jump_call_near_select = bool(
        re.search(
            rf"(?:{_SEARCH_JUMP_CALL_RE})\s*\([\s\S]{{0,600}}"
            r"(?:selectPerson\s*\(|openPerson\s*\(|view\s*=\s*[\"']people[\"'])"
            rf"|(?:selectPerson\s*\(|view\s*=\s*[\"']people[\"'])[\s\S]{{0,600}}"
            rf"(?:{_SEARCH_JUMP_CALL_RE})\s*\(",
            web_blob,
            re.I,
        )
    )
    # Combined handler in SearchPane: if (h.person_id) { onJump… } else toggle
    search_branches_to_jump = bool(
        re.search(
            r"(?:h|hit)\s*\.\s*(?:person_id|personId)[\s\S]{0,200}"
            rf"(?:{_SEARCH_JUMP_CALL_RE})\s*\(",
            search_clean,
            re.I,
        )
    )

    if not (body_selects or jump_call_near_select or search_jumps_inline):
        fail(
            "#124: jump path must switch to People and select the hit's person "
            "(view = \"people\" + selectPerson / openPerson / openPersonAtMessage — "
            "not a no-op jump name)"
        )
    if not (body_message or search_branches_to_jump or _HIT_MESSAGE_ID_READ.search(
        "\n".join(jump_bodies) if jump_bodies else ""
    )):
        # Message id must reach the open/scroll path.
        if not re.search(
            rf"(?:{_SEARCH_JUMP_CALL_RE})\s*\([^)]{{0,120}}"
            r"(?:message_id|messageId|h\.message|hit\.message)",
            web_blob,
            re.I,
        ) and not re.search(
            r"(?:h|hit)\s*\.\s*(?:message_id|messageId)[\s\S]{0,200}"
            rf"(?:{_SEARCH_JUMP_CALL_RE}|selectPerson|tlIndex|ensureTlIndexVisible)",
            web_blob,
            re.I,
        ):
            fail(
                "#124: jump path must carry hit.message_id "
                "(open around that message, set tlIndex / scroll to that row)"
            )

    # 5) Only jump when person_id is present (no inventing a person).
    if not _HIT_PERSON_GUARD.search(web_blob) and not _HIT_PERSON_ID_READ.search(
        search_clean
    ):
        fail(
            "#124: only jump when hit.person_id is present — without it stay on Search "
            "and expand body (do not invent a person from the hit)"
        )
    # Prefer an explicit guard near jump (hit.person_id ? jump : toggle).
    if not _HIT_PERSON_GUARD.search(web_blob):
        fail(
            "#124: branch on hit.person_id before jumping "
            "(if present → People timeline; else → expand body on Search)"
        )

    # 6) Load a window that can contain message_id.
    # Require load signal inside jump bodies or within a jump-related window —
    # not only the ordinary selectPerson used for sidebar clicks.
    load_in_jump = any(_SEARCH_JUMP_LOAD_WINDOW.search(b) for b in jump_bodies)
    load_near_jump = bool(
        re.search(
            rf"(?:{_SEARCH_JUMP_CALL_RE})[\s\S]{{0,800}}"
            r"(?:personTimeline|around\s*:|after\s*:|before\s*:|aroundMessage|"
            r"loadAround|openAround|selectPerson\s*\()"
            rf"|(?:personTimeline|aroundMessage|loadAround)[\s\S]{{0,400}}"
            rf"(?:{_SEARCH_JUMP_CALL_RE}|message_id|messageId)",
            web_blob,
            re.I,
        )
    )
    if not load_in_jump and not load_near_jump and not body_selects:
        fail(
            "#124: jump path must load a timeline window around message_id "
            "(personTimeline before/after/around, or selectPerson load that can "
            "place the hit in the loaded set — bounded Load older OK for dogfood)"
        )

    # 7) Scroll into view + highlight once — must appear in jump path, not only j/k.
    # Require coupling to a jump handler name (bare tlIndex/message_id elsewhere is j/k / mail fold).
    scroll_in_jump = any(_SEARCH_JUMP_SCROLL_HL.search(b) for b in jump_bodies)
    scroll_near_jump = bool(
        re.search(
            rf"(?:{_SEARCH_JUMP_CALL_RE})[\s\S]{{0,900}}"
            r"(?:ensureTlIndexVisible\s*\(|tlIndex\s*=|scrollIntoView\s*\(|"
            r"data-message-id|scrollToMessage|scrollMessageIntoView|findIndex\s*\()"
            rf"|(?:ensureTlIndexVisible\s*\(|scrollToMessage\s*\(|scrollMessageIntoView\s*\()"
            rf"[\s\S]{{0,400}}(?:{_SEARCH_JUMP_CALL_RE}|message_id|messageId)",
            web_blob,
            re.I,
        )
    )
    if not scroll_in_jump and not scroll_near_jump:
        fail(
            "#124: after jump, scroll the target message into view and highlight once "
            "(tlIndex = … / ensureTlIndexVisible / scrollIntoView / data-message-id — "
            "same ring as j/k selection; must be on the jump path, not only j/k)"
        )
    # Virtualized timeline: ensureTlIndexVisible (or scroll) must exist in App.
    if not re.search(r"\bensureTlIndexVisible\s*\(", app_clean) and not re.search(
        r"scrollIntoView|data-message-id", app_clean
    ):
        fail(
            "#124: timeline must be able to bring the jumped-to index into view "
            "(ensureTlIndexVisible or scrollIntoView / data-message-id; "
            "virtualized lists must open the virtual window on that index)"
        )

    # 8) Keep #121–#123 search chrome.
    if not re.search(r"\bplatform\b", search_clean) or not re.search(
        r"<select\b", surface, re.I
    ):
        fail("#124: keep the search platform <select> (#121) when adding jump-to-hit")
    if not re.search(r"conversationKind|conversation_kind", search_clean):
        fail(
            "#124: keep the search conversation-kind <select> (#122) when adding jump-to-hit"
        )
    if not re.search(
        r"personId|person_id|personFilter|data-person-picker", search_clean
    ):
        fail("#124: keep the search person picker (#123) when adding jump-to-hit")

    # 9) Keep api.search (do not rewrite FTS as part of jump-to-hit).
    if not re.search(r"api\.search\s*\(", search_clean):
        fail("#124: keep api.search (do not rewrite FTS as part of jump-to-hit)")

    # 10) Miss path: error when message_id not in loaded set; never ring last row.
    _assert_search_jump_miss_path(web_blob, jump_bodies)


def assert_search_safe_highlight(crate: Path) -> None:
    """#126: highlight search tokens with <mark> siblings; never innerHTML the body.

    Split the snippet on core FTS markers («…») or matched query terms; render
    plain text + <mark> Svelte elements (text children only). Yellow / mark
    styling so query e.g. fatura shows a visible mark. Expanded search body
    (api.searchBody → body_text) stays text — a body containing <script> must
    not execute. Not: regex HTML inject, HTML mail. Keep #121–#125 chrome.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#126: SearchPane.svelte required (search snippet highlight lives there)")
    src = _search_pane_blob(crate)
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    _blob, blob_clean, helper_paths = _search_highlight_surface(crate)
    # Hits list region is the snippet path; expanded body is the other surface.
    hits_m = re.search(
        r"\{#each\s+hits\b[\s\S]{0,8000}?\{/each\}",
        surface,
        re.I,
    )
    hits_region = hits_m.group(0) if hits_m else surface

    # 1) Primary red: snippet path must render <mark> for hit highlights.
    #    Not a single raw string of h.snippet alone.
    has_mark = bool(_SEARCH_MARK_TAG.search(hits_region)) or bool(
        _SEARCH_MARK_TAG.search(surface)
    )
    # Allow a small child component used only for the snippet line (e.g. SnippetHighlight).
    if not has_mark:
        for p in helper_paths:
            if p.suffix == ".svelte" and p.name != "SearchPane.svelte":
                htxt = p.read_text()
                if _SEARCH_MARK_TAG.search(htxt) and re.search(
                    r"snippet|highlight|mark|segment",
                    htxt,
                    re.I,
                ):
                    has_mark = True
                    break
    if not has_mark:
        fail(
            "#126: search snippet path must render <mark> for hit highlights "
            "(text + <mark> Svelte element siblings — not a single raw snippet string). "
            "Split on core FTS markers «…» or matched query terms"
        )

    # 2) Must actually split into segments (siblings), not wrap the whole snippet
    #    once without a split path. Evidence: FTS markers, segment helper, or
    #    {#each} over parts next to <mark>.
    has_split = bool(_SEARCH_SNIPPET_SPLIT.search(blob_clean)) or bool(
        _SEARCH_HIGHLIGHT_HELPER.search(blob_clean)
    )
    has_each_segments = bool(
        re.search(
            r"\{#each\s+(?:[^}]*\b(?:seg(?:ment)?s?|parts|tokens|chunks|marks|"
            r"highlighted|snippetParts|snippetSegments)\b|"
            r"[^}]{0,80}(?:splitSnippet|highlightSnippet|snippetSegments|"
            r"markSegments|segmentSnippet)\s*\()",
            hits_region + "\n" + surface,
            re.I,
        )
    )
    # <mark> text content must be a segment field, not the full raw snippet alone.
    mark_wraps_full_snippet = bool(
        re.search(
            r"<mark\b[^>]*>\s*\{(?:\(?\s*)?(?:h\.)?snippet\b[^}]{0,120}\}\s*</mark>",
            hits_region,
            re.I,
        )
    )
    if not has_split and not has_each_segments:
        fail(
            "#126: split the snippet into plain-text + <mark> siblings "
            "(core FTS markers «…», or a pure segment helper / {#each} over parts) — "
            "do not leave the hit as one unsplit string"
        )
    if mark_wraps_full_snippet and not has_each_segments and not has_split:
        fail(
            "#126: do not wrap the entire raw snippet in one <mark> — "
            "split on matched terms / FTS «…» markers into text + <mark> siblings"
        )

    # 3) Yellow / highlight styling on the mark (class or intentional <mark>).
    style_blob = hits_region + "\n" + surface
    for p in helper_paths:
        if p.suffix in {".svelte", ".css"}:
            style_blob += "\n" + p.read_text()
    if not _SEARCH_MARK_STYLE.search(style_blob):
        fail(
            "#126: <mark> must be visibly highlighted "
            "(yellow/amber/highlight class e.g. bg-yellow-200, or intentional <mark> styling) "
            "so a query match is obvious"
        )

    # 4) Ban innerHTML / {@html on search snippet and expanded body path.
    if _SEARCH_UNSAFE_HTML.search(blob_clean) or _SEARCH_UNSAFE_HTML.search(cleaned):
        # Narrow: only fail if it touches snippet/body/search surfaces (not unrelated).
        unsafe = re.search(
            r"(?:snippet|body_text|searchBody|\bbody\b|highlight|mark)[\s\S]{0,160}"
            r"(?:\{@html\b|\.innerHTML\s*=|insertAdjacentHTML\s*\()"
            r"|(?:\{@html\b|\.innerHTML\s*=|insertAdjacentHTML\s*\()[\s\S]{0,160}"
            r"(?:snippet|body_text|searchBody|\bbody\b|highlight)",
            blob_clean,
            re.I,
        )
        bare_html = _HTML_BODY.search(blob_clean) or re.search(
            r"\.innerHTML\s*=", blob_clean
        )
        if unsafe or bare_html:
            fail(
                "#126: never assign innerHTML / {@html on the search snippet or body path "
                "(render text + <mark> Svelte elements with text children only — "
                "a body containing <script> must stay text)"
            )

    # Expanded body path specifically: {body} / body_text must stay text bindings.
    expanded_region = ""
    exp = re.search(
        r"\{#if\s+expanded\b[\s\S]{0,800}?\{/if\}",
        surface,
        re.I,
    )
    if exp:
        expanded_region = exp.group(0)
    if expanded_region and (
        _HTML_BODY.search(expanded_region)
        or re.search(r"\.innerHTML\s*=", expanded_region)
        or re.search(r"\{@html\s+body\b", expanded_region)
    ):
        fail(
            "#126: expanded search body must stay text-safe "
            "(no {@html body} / innerHTML of full body — <script> in body stays text)"
        )
    # Global SearchPane ban on {@html body} even outside the if-region.
    if re.search(r"\{@html\s+(?:body|body_text|snippet)\b", blob_clean):
        fail(
            "#126: expanded search body / snippet must stay text-safe — "
            "no {@html body} / {@html snippet}"
        )

    # 5) Not: regex highlight that builds HTML strings to inject.
    if _SEARCH_REGEX_HTML_MARK.search(blob_clean):
        fail(
            "#126: not in scope — regex highlight that builds HTML mark strings "
            "(no .replace(…, '<mark>…') inject path; use text + <mark> element siblings)"
        )

    # 6) Not: HTML mail renderer.
    if _SEARCH_HTML_MAIL.search(blob_clean):
        # Ignore false positives in comments already stripped; still scope to search.
        fail(
            "#126: not in scope — HTML mail renderer "
            "(DOMParser / srcdoc / htmlMail on search path); snippets and body stay text"
        )

    # 7) Keep #121–#125 search chrome.
    if not re.search(r"\bplatform\b", cleaned) or not re.search(
        r"<select\b", surface, re.I
    ):
        fail("#126: keep the search platform <select> (#121) when adding safe highlight")
    if not re.search(r"conversationKind|conversation_kind", cleaned):
        fail(
            "#126: keep the search conversation-kind <select> (#122) when adding safe highlight"
        )
    if not re.search(r"personId|person_id|personFilter|data-person-picker", cleaned):
        fail("#126: keep the search person picker (#123) when adding safe highlight")
    if not re.search(r"\{#each\s+hits\b", surface) and not re.search(
        r"\{#each\s+hits\b", src
    ):
        fail("#126: keep search hits list (#124 jump chrome) when adding safe highlight")
    if not re.search(r"attachmentFilter|attachment_filter", cleaned):
        fail(
            "#126: keep the search attachment filter (#125) when adding safe highlight"
        )

from tauri_gate.search_hits_more import assert_search_hit_density
