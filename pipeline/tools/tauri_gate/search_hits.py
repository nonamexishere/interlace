"""Search jump / highlight / hit-density asserts. Imported by gate_tauri.py."""
from __future__ import annotations
import re
from pathlib import Path
from common import fail, repo_root
from tauri_gate.scan import (
    _HTML_BODY, _function_body, _matching_each_end, _svelte_interpolations,
    _svelte_markup, _ts_function_body, _web_logic, _without_comments,
)
from tauri_gate.import_boot import _HUMAN_TIME_HELPERS
from tauri_gate.status_toasts import _short_time_formatter_ok


# #124 — search hit jumps to that message on the person timeline (not a dead end).
# Jump / open-at-message handlers (App callback or local + parent wire).
_SEARCH_JUMP_FN = re.compile(
    r"\b(?:"
    r"jumpToMessage|jumpToHit|jumpToSearchHit|openSearchHit|openHit|goToMessage|"
    r"openPersonAtMessage|selectPersonAtMessage|openAtMessage|jumpToPersonMessage|"
    r"onJumpToMessage|onOpenHit|onOpenSearchHit|onJumpHit|onSearchHit|"
    r"handleSearchHit|activateSearchHit|openHitOnTimeline"
    r")\b",
    re.I,
)
# Props / callbacks SearchPane may receive from App for the jump path.
_SEARCH_JUMP_PROP = re.compile(
    r"\b(?:"
    r"onJumpToMessage|onOpenHit|onOpenSearchHit|onJumpHit|onSearchHit|"
    r"jumpToMessage|openSearchHit|openHit|onJump"
    r")\b",
    re.I,
)
# Switching to the People view (leave Search).
_VIEW_PEOPLE = re.compile(
    r"view\s*=\s*[\"']people[\"']"
    r"|view\s*=\s*\{?\s*[\"']people[\"']"
    r"|\bsetView\s*\(\s*[\"']people[\"']\s*\)"
    r"|\bnavigate\s*\(\s*[\"']people[\"']\s*\)",
    re.I,
)
# Hit activation must read person_id from the hit (not the search filter state).
_HIT_PERSON_ID_READ = re.compile(
    r"(?:h|hit|row|item|searchHit)\s*\.\s*(?:person_id|personId)\b"
    r"|\b(?:h|hit|row|item|searchHit)\s*\?\s*\.\s*(?:person_id|personId)\b"
    r"|(?:person_id|personId)\s*:\s*(?:h|hit|row|item|searchHit)\s*\.\s*(?:person_id|personId)",
    re.I,
)
# Message id from the hit carried into the jump / scroll path (not only toggle expand).
_HIT_MESSAGE_ID_READ = re.compile(
    r"(?:h|hit|row|item|searchHit)\s*\.\s*(?:message_id|messageId)\b"
    r"|(?:message_id|messageId)\s*:\s*(?:h|hit|row|item|searchHit)\s*\.\s*(?:message_id|messageId)",
    re.I,
)
# Expand-body path (no person_id / stay on Search) — current toggle + searchBody.
_SEARCH_EXPAND_BODY = re.compile(
    r"\b(?:api\.)?searchBody\s*\("
    r"|\bexpanded\s*="
    r"|\btoggle\s*\(\s*(?:h|hit|id|message_id|messageId)",
    re.I,
)
# Scroll / highlight once the target row is known.
_SEARCH_JUMP_SCROLL_HL = re.compile(
    r"("
    r"\bensureTlIndexVisible\s*\("
    r"|\bscrollIntoView\s*\("
    r"|\btlIndex\s*="
    r"|data-message-id"
    r"|data-tl-index"
    r"|data-message="
    r"|\bfindIndex\s*\([^)]{0,80}(?:message_id|messageId)"
    r"|\.findIndex\s*\("
    r"|\bscrollToMessage\s*\("
    r"|\bscrollMessageIntoView\s*\("
    r"|\bhighlightMessage\s*\("
    r"|ring-2\s+ring-ring"
    r")",
    re.I,
)
# Loading a timeline window that can include the target message (around / after /
# before cursor, or messageId arg). Repeated Load older is OK if bounded — we
# only require some load path that can place message_id in the loaded set.
_SEARCH_JUMP_LOAD_WINDOW = re.compile(
    r"("
    r"\bpersonTimeline\s*\("
    r"|\bapi\.personTimeline\s*\("
    r"|\baround\s*:"
    r"|\bafter\s*:"
    r"|\bbefore\s*:"
    r"|\bmessageId\s*:"
    r"|\bmessage_id\s*:"
    r"|\baroundMessage\b"
    r"|\bloadAround\b"
    r"|\bopenAround\b"
    r"|\bjumpLoad\b"
    r"|\bselectPerson\s*\("
    r")",
    re.I,
)
# Names accepted for the open-hit / jump entry point (click + Enter call this).
# Plain string (adjacent literals) so it embeds cleanly in larger patterns.
_SEARCH_JUMP_CALL_RE = (
    r"jumpToMessage|jumpToHit|jumpToSearchHit|openSearchHit|openHit|goToMessage|"
    r"openPersonAtMessage|selectPersonAtMessage|openAtMessage|jumpToPersonMessage|"
    r"onJumpToMessage|onOpenHit|onOpenSearchHit|onJumpHit|onSearchHit|"
    r"handleSearchHit|activateSearchHit|openHitOnTimeline|activateHit|openHitRow"
)
# Hit click / Enter invokes a jump or activate entry (not only toggle).
_HIT_ACTIVATES_JUMP = re.compile(
    rf"("
    rf"(?:onclick|on:click)(?:\|\w+)*\s*=\s*\{{[\s\S]{{0,400}}\b(?:"
    rf"{_SEARCH_JUMP_CALL_RE}"
    rf")\s*\("
    rf"|(?:onclick|on:click)(?:\|\w+)*\s*=\s*\{{[\s\S]{{0,400}}"
    rf"(?:h|hit)\s*\.\s*(?:person_id|personId)"
    rf"|(?:key|code)\s*===?\s*[\"']Enter[\"'][\s\S]{{0,400}}\b(?:"
    rf"{_SEARCH_JUMP_CALL_RE}"
    rf")\s*\("
    rf"|(?:key|code)\s*===?\s*[\"']Enter[\"'][\s\S]{{0,400}}"
    rf"(?:h|hit)\s*\.\s*(?:person_id|personId)"
    rf")",
    re.I,
)
# Jump handler body must select person + carry message id (not a no-op name).
_JUMP_BODY_SELECTS_PERSON = re.compile(
    r"("
    r"\bselectPerson\s*\("
    r"|\bopenPerson\s*\("
    r"|\bopenPersonAtMessage\s*\("
    r"|\bselectPersonAtMessage\s*\("
    r"|view\s*=\s*[\"']people[\"']"
    r")",
    re.I,
)
_JUMP_BODY_USES_MESSAGE = re.compile(
    r"("
    r"\b(?:message_id|messageId)\b"
    r"|\bensureTlIndexVisible\s*\("
    r"|\btlIndex\s*="
    r"|data-message-id"
    r"|\bfindIndex\s*\("
    r"|\bscrollIntoView\s*\("
    r")",
    re.I,
)
# person_id presence guard on the hit (not the Search filter personId state alone).
_HIT_PERSON_GUARD = re.compile(
    r"("
    r"(?:h|hit|row|item|searchHit)\s*\.\s*(?:person_id|personId)\s*"
    r"(?:\?\?|\|\||&&|!=|!==|==|===|\?)"
    r"|(?:h|hit|row|item|searchHit)\s*\?\s*\.\s*(?:person_id|personId)"
    r"|\bif\s*\([^)]{0,100}(?:h|hit|row|item|searchHit)\s*\.\s*(?:person_id|personId)"
    r"|\b(?:person_id|personId)\s*(?:!=|!==|==|===)\s*(?:null|undefined)[\s\S]{0,120}"
    r"(?:jumpTo|openHit|openSearch|onJump|goToMessage|selectPerson|view\s*=)"
    r")",
    re.I,
)
# #124 miss path — do not treat last loaded row as the hit when findIndex misses.
_IDX_NAME = r"(?:idx|index|foundIdx|foundIndex|tlIdx|pos|foundAt|messageIdx|messageIndex)"
_LOADED_NAME = r"(?:loaded|timeline|rows|chrono|batch|msgs|messages|page|window)"
# tlIndex = idx >= 0 ? idx : Math.max(0, loaded.length - 1)  (and close variants)
_SEARCH_JUMP_LAST_ROW_FALLBACK = re.compile(
    rf"("
    rf"tlIndex\s*=\s*{_IDX_NAME}\s*>=?\s*0\s*\?\s*{_IDX_NAME}\s*:\s*"
    rf"(?:Math\.max\s*\(\s*0\s*,\s*)?{_LOADED_NAME}\s*\.length\s*-\s*1"
    rf"|{_IDX_NAME}\s*>=?\s*0\s*\?\s*{_IDX_NAME}\s*:\s*"
    rf"(?:Math\.max\s*\(\s*0\s*,\s*)?{_LOADED_NAME}\s*\.length\s*-\s*1"
    rf"|{_IDX_NAME}\s*(?:<\s*0|===?\s*-1)\s*\?\s*"
    rf"(?:Math\.max\s*\(\s*0\s*,\s*)?{_LOADED_NAME}\s*\.length\s*-\s*1"
    rf"|findIndex\s*\([\s\S]{{0,160}}(?:message_id|messageId)[\s\S]{{0,280}}"
    rf"tlIndex\s*=\s*[^;\n]{{0,120}}{_LOADED_NAME}\s*\.length\s*-\s*1"
    rf"|tlIndex\s*=\s*{_IDX_NAME}\s*>=?\s*0\s*\?\s*{_IDX_NAME}\s*:"
    rf")",
    re.I,
)
# Any ternary that sets tlIndex from findIndex-style idx with a non-idx false branch
# (wrong-row success) — pairs with the last-row ban above.
_SEARCH_JUMP_TLINDEX_MISS_TERNARY = re.compile(
    rf"tlIndex\s*=\s*{_IDX_NAME}\s*(?:>=?\s*0|<\s*0|===?\s*-1)\s*\?",
    re.I,
)
# Miss branch must surface showErr / onError / throw (not only catch).
_SEARCH_JUMP_MISS_ERROR = re.compile(
    rf"("
    rf"if\s*\(\s*{_IDX_NAME}\s*(?:<\s*0|===?\s*-1)\s*\)\s*\{{[\s\S]{{0,280}}"
    rf"(?:showErr|onError)\s*\("
    rf"|if\s*\(\s*{_IDX_NAME}\s*(?:<\s*0|===?\s*-1)\s*\)[\s\S]{{0,120}}"
    rf"(?:showErr|onError)\s*\("
    rf"|if\s*\(\s*{_IDX_NAME}\s*(?:<\s*0|===?\s*-1)\s*\)\s*\{{[\s\S]{{0,200}}\bthrow\b"
    rf"|if\s*\(\s*{_IDX_NAME}\s*>=?\s*0\s*\)[\s\S]{{0,400}}"
    rf"else\s*\{{[\s\S]{{0,200}}(?:showErr|onError)\s*\("
    rf"|if\s*\(\s*!(?:found|row|hit|target|match|located)\b[\s\S]{{0,160}}"
    rf"(?:showErr|onError)\s*\("
    rf"|if\s*\(\s*!{_LOADED_NAME}\.some\s*\([\s\S]{{0,200}}"
    rf"(?:message_id|messageId)[\s\S]{{0,100}}\)\s*\)\s*\{{[\s\S]{{0,240}}"
    rf"(?:showErr|onError)\s*\("
    rf"|if\s*\(\s*{_LOADED_NAME}\.findIndex\s*\([\s\S]{{0,200}}"
    rf"(?:message_id|messageId)[\s\S]{{0,80}}\)\s*(?:<\s*0|===?\s*-1)"
    rf"[\s\S]{{0,200}}(?:showErr|onError)\s*\("
    rf")",
    re.I,
)


def _search_jump_handler_bodies(blob: str) -> list[str]:
    """Bodies of jump/open-hit functions (placeholder names from the gate list)."""
    names = (
        "jumpToMessage",
        "jumpToHit",
        "jumpToSearchHit",
        "openSearchHit",
        "openHit",
        "goToMessage",
        "openPersonAtMessage",
        "selectPersonAtMessage",
        "openAtMessage",
        "jumpToPersonMessage",
        "handleSearchHit",
        "activateSearchHit",
        "openHitOnTimeline",
        "activateHit",
        "openHitRow",
        "onJumpToMessage",
        "onOpenHit",
        "onOpenSearchHit",
    )
    bodies: list[str] = []
    for name in names:
        body = _function_body(blob, name)
        if body.strip():
            bodies.append(body)
    return bodies


def _assert_search_jump_miss_path(web_blob: str, jump_bodies: list[str]) -> None:
    """#124 miss: error on unfound message_id; never ring last loaded as the hit."""
    path = "\n".join(jump_bodies) if jump_bodies else web_blob
    path_clean = _without_comments(path)
    blob_clean = _without_comments(web_blob)

    # 1) Forbid last-row (or any idx-ternary) fallback as a successful hit ring.
    if _SEARCH_JUMP_LAST_ROW_FALLBACK.search(path_clean) or (
        _SEARCH_JUMP_LAST_ROW_FALLBACK.search(blob_clean)
        and re.search(
            r"findIndex\s*\([\s\S]{0,120}(?:message_id|messageId)",
            blob_clean,
            re.I,
        )
    ):
        fail(
            "#124: when message_id is not in the loaded timeline after the jump walk, "
            "do not set tlIndex to the last loaded row "
            "(tlIndex = idx >= 0 ? idx : Math.max(0, loaded.length - 1)). "
            "That rings an unrelated message with no error. Surface showErr instead"
        )
    if _SEARCH_JUMP_TLINDEX_MISS_TERNARY.search(path_clean):
        fail(
            "#124: do not assign tlIndex via idx-miss ternary "
            "(tlIndex = idx >= 0 ? idx : <fallback>). "
            "On miss: showErr (or equivalent) and return — only set tlIndex when "
            "the hit row is actually found"
        )

    # 2) Require an explicit miss → error path (catch-only showErr is not enough).
    has_miss_err = bool(
        _SEARCH_JUMP_MISS_ERROR.search(path_clean)
        or _SEARCH_JUMP_MISS_ERROR.search(blob_clean)
    )
    if not has_miss_err:
        fail(
            "#124: when the jump path cannot place message_id in the loaded set "
            "(miss after bounded walk / cap), surface an error "
            "(if (idx < 0) { showErr(...); return } / else showErr / "
            "!loaded.some(...message_id) showErr). "
            "Do not treat a wrong row as a successful hit highlight"
        )

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

    search_src = search_path.read_text()
    app_src = app_path.read_text()
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


# #126 — safe search snippet highlight: <mark> siblings, never innerHTML of body.
# Core FTS snippets already wrap hits with «…» (see docs/user/search.md).
_SEARCH_HIGHLIGHT_HELPER = re.compile(
    r"\b(?:"
    r"splitSnippet|snippetSegments|snippetParts|highlightSnippet|highlightSegments|"
    r"markSegments|markSnippet|segmentSnippet|parseSnippet|snippetMarks|"
    r"highlightSearch|searchHighlight|ftsSnippet|splitFtsSnippet|"
    r"splitMarkers|markerSegments|wrapMarks"
    r")\b",
    re.I,
)
# Split evidence: FTS guillemet markers or a snippet-aware split / segment helper.
_SEARCH_SNIPPET_SPLIT = re.compile(
    r"("
    r"[«»]"  # core FTS snippet markers
    r"|\\u00ab|\\u00bb"  # unicode escapes
    r"|\bsplit\s*\([^)]*(?:snippet|«|»|marker)"
    r"|\.split\s*\(\s*(?:/[«»]|[\"']«|new\s+RegExp\s*\(\s*[\"']«)"
    r"|\b(?:snippetSegments|snippetParts|markSegments|highlightSegments|"
    r"segmentSnippet|splitSnippet|splitMarkers|markerSegments)\b"
    r"|\b(?:segments?|parts)\s*(?:=|:)\s*(?:splitSnippet|highlightSnippet|"
    r"snippetSegments|markSegments|segmentSnippet)\b"
    r")",
    re.I,
)
# <mark> with yellow / highlight / mark class, or bare <mark> used as the hit wrap.
_SEARCH_MARK_TAG = re.compile(r"<mark\b", re.I)
_SEARCH_MARK_STYLE = re.compile(
    r"("
    r"<mark\b[^>]{0,200}\bclass\s*=\s*[\"'][^\"']*"
    r"(?:yellow|highlight|mark|bg-yellow|bg-amber|bg-\[|search-hit|hit-mark)"
    r"|<mark\b"  # intentional <mark> (UA default is yellow-ish; class optional)
    r"|\b(?:bg-yellow-\d+|bg-amber-\d+|text-yellow|highlight|hit-mark|search-mark)\b"
    r")",
    re.I,
)
# Dangerous HTML injection on search snippet/body path.
_SEARCH_UNSAFE_HTML = re.compile(
    r"("
    r"\{@html\b"
    r"|\.innerHTML\s*="
    r"|insertAdjacentHTML\s*\("
    r"|dangerouslySetInnerHTML"
    r")",
    re.I,
)
# Building an HTML string of <mark> via replace (regex highlight → inject path).
_SEARCH_REGEX_HTML_MARK = re.compile(
    r"("
    r"\.replace\s*\([^)]{0,200},\s*[`'\"][^`'\"]*<mark\b"
    r"|replace\s*\(\s*(?:new\s+)?RegExp\b[\s\S]{0,200}<mark\b"
    r"|return\s+[`'\"][^`'\"]*<mark\b[^`'\"]*[`'\"]"  # helper returns HTML string
    r")",
    re.I,
)
# HTML mail renderer (out of scope for #126).
_SEARCH_HTML_MAIL = re.compile(
    r"("
    r"\bDOMParser\b"
    r"|\bsrcdoc\s*="
    r"|\brenderHtmlMail\b|\bhtmlMail\b|\bMimeHtml\b|\brenderMime\b"
    r"|iframe[^>]{0,80}(?:body|snippet|mail|message)"
    r")",
    re.I,
)


def _search_highlight_surface(crate: Path) -> tuple[str, str, list[Path]]:
    """SearchPane + relative snippet/highlight helpers (not CasAttach / general UI)."""
    web = crate / "web"
    lib = web / "lib"
    search_path = lib / "SearchPane.svelte"
    paths: list[Path] = []
    seen: set[Path] = set()
    if search_path.is_file():
        paths.append(search_path)
        seen.add(search_path.resolve())
        text = search_path.read_text()
        for m in re.finditer(r"""from\s+["'](\.[^"']+)["']""", text):
            rel = m.group(1)
            base = (search_path.parent / rel).resolve()
            candidates = [base]
            if not base.suffix:
                candidates.extend(
                    [
                        Path(str(base) + ".ts"),
                        Path(str(base) + ".js"),
                        Path(str(base) + ".svelte"),
                        base / "index.ts",
                        base / "index.js",
                    ]
                )
            for c in candidates:
                if not c.is_file() or c.resolve() in seen:
                    continue
                try:
                    c.relative_to(web.resolve())
                except ValueError:
                    continue
                name = c.name.lower()
                body = c.read_text()
                # Only pull helpers involved in snippet split / mark render.
                if re.search(
                    r"snippet|highlight|mark.?segment|fts.?marker|split.?marker",
                    name + "\n" + body[:4000],
                    re.I,
                ) and not re.search(
                    r"CasAttach|EmptyState|DoctorPane|ImportPane|ReviewPane",
                    c.name,
                ):
                    # Skip pure API types modules unless they define a split helper.
                    if c.name in {"api.ts", "api.js"} and not _SEARCH_HIGHLIGHT_HELPER.search(
                        body
                    ):
                        continue
                    paths.append(c)
                    seen.add(c.resolve())
    blob = "\n".join(p.read_text() for p in paths)
    cleaned = _without_comments(blob)
    return blob, cleaned, paths


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
    src = search_path.read_text()
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


# #210 — search hit rows: short time + person/title, then highlighted snippet.
_HIT_TIME_EXTRA = ("utcTime",)
_HIT_SENT_AT_NO_DATE = re.compile(
    r"""(?:h\.)?sent_at\s*\|\|\s*["']no date["']""",
    re.I,
)
_HIT_LOG_JOIN = re.compile(
    r"""\.join\s*\(\s*["']\s*·\s*["']\s*\)""",
)
_HIT_PERSON_OR_TITLE = re.compile(
    r"\b(?:person_name|personName|conversation_title|conversationTitle)\b"
)
_HIT_DENSITY_META = re.compile(
    r"\btext-xs\b|text-\[(?:12|13)px\]",
    re.I,
)
_HIT_DENSITY_SNIP = re.compile(
    r"\btext-sm\b|text-\[(?:14|15)px\]",
    re.I,
)
_HIT_DENSITY_PAD = re.compile(
    r"\b(?:py-1\.5|py-2|gap-1\.5|gap-2)\b",
    re.I,
)
_DOCS_HIT_DENSITY = re.compile(
    r"("
    r"(?:search )?hits?"
    r".{0,200}short(?:er)?(?: UTC| human)? time"
    r".{0,120}person(?:/|\s+or\s+|\s+and/?or\s+)(?:conversation )?title"
    r".{0,100}(?:highlighted )?snippet"
    r")",
    re.I | re.S,
)
_DOCS_HIT_NOT_ISO = re.compile(
    r"("
    r"(?:search )?hits?.{0,220}not (?:a |the )?raw ISO"
    r"|not (?:a |the )?raw ISO dump"
    r")",
    re.I | re.S,
)


def _hit_time_helpers() -> tuple[str, ...]:
    return _HUMAN_TIME_HELPERS + _HIT_TIME_EXTRA


def _hit_time_call_rx() -> re.Pattern[str]:
    return re.compile(r"\b(?:" + "|".join(_hit_time_helpers()) + r")\s*\(")


def _hits_each_block(markup: str) -> str:
    m = re.search(r"\{#each\s+hits\b", markup)
    if not m:
        return ""
    end = _matching_each_end(markup, m.start())
    if end < 0:
        return markup[m.start() :]
    return markup[m.start() : end]


def _interp_dumps_iso_sent_at(expr: str) -> bool:
    """True if sent_at is stringified (raw ISO), not passed to a formatter.

    Jump payload `sentAt: h.sent_at` is API, not display — ignore those.
    """
    stripped = re.sub(r"\bsentAt\s*:\s*(?:[\w.$]+\.)?sent_at\b", "", expr)
    if not re.search(r"\bsent_at\b", stripped):
        return False
    names = "|".join(_hit_time_helpers())
    if re.search(rf"\b(?:{names})\s*\([^)]*\bsent_at\b", stripped):
        return False
    return True


def _hits_uses_short_time(hits_each: str) -> bool:
    if _hit_time_call_rx().search(hits_each):
        return True
    names = "|".join(_hit_time_helpers())
    for expr in _svelte_interpolations(hits_each):
        if re.search(rf"\b(?:{names})\s*\([^)]*\bsent_at\b", expr):
            return True
    return False


def _hits_meta_is_five_field_log(hits_each: str) -> bool:
    """True if one interpolation still joins sent_at + platform + kind."""
    for expr in _svelte_interpolations(hits_each):
        has_sent = bool(re.search(r"\bsent_at\b", expr))
        has_plat = bool(re.search(r"\bplatform\b", expr))
        has_kind = bool(re.search(r"\bconversation_kind\b", expr))
        if has_sent and has_plat and has_kind:
            return True
        if _HIT_LOG_JOIN.search(expr) and has_plat and has_kind:
            return True
    if re.search(
        r"sent_at[\s\S]{0,240}platform[\s\S]{0,240}conversation_kind"
        r"[\s\S]{0,120}\.join\s*\(\s*[\"']\s*·",
        hits_each,
    ):
        return True
    return False


def assert_search_hit_density(crate: Path) -> None:
    """#210: hit rows show short time + person/title, then a highlighted snippet.

    Format `h.sent_at` with existing `humanTime` / `utcTime` (or another name
    in `_HUMAN_TIME_HELPERS`). Quiet meta is short time + person name and/or
    conversation title — not a five-field `sent_at · platform · kind · name ·
    title` dump. Snippet stays splitSnippet + <mark> text children. Keep
    #124 j/k+Enter, #126 mark path, #208 chrome search, #209 filters. Not:
    regex HTML inject, HTML mail renderer, FTS «» rewrite.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#210: SearchPane.svelte required (search hit rows live there)")
    src = search_path.read_text()
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    hits_each = _hits_each_block(surface)
    if not hits_each.strip():
        hits_each = _hits_each_block(src)
    app_path = crate / "web" / "App.svelte"
    app = app_path.read_text() if app_path.is_file() else ""
    logic = _web_logic(crate)
    docs_search = repo_root() / "docs" / "user" / "search.md"
    docs_app = repo_root() / "docs" / "user" / "app.md"
    dtxt = ""
    if docs_search.is_file():
        dtxt += docs_search.read_text() + "\n"
    if docs_app.is_file():
        dtxt += docs_app.read_text()

    # 1) Hits list hooks stay.
    if not re.search(r"\{#each\s+hits\b", surface) and not re.search(
        r"\{#each\s+hits\b", src
    ):
        fail("#210: SearchPane must still list hits ({#each hits})")
    if not hits_each.strip():
        fail("#210: search hits {#each hits} body missing")
    if not re.search(r"\bdata-search-hits\b", surface):
        fail("#210: keep data-search-hits on the hits list")
    if not re.search(r"\bdata-search-hit\b", hits_each):
        fail("#210: keep data-search-hit on each hit row")

    # 2) Still show sent_at — as a short time, not dropped (jump payload alone
    #    does not count; that stays API).
    if not re.search(r"\bsent_at\b", hits_each):
        fail(
            "#210: hit rows must still show sent_at "
            "(as a short time, not drop the timestamp)"
        )

    # 3) Visible hit meta is not the raw ISO T…Z string.
    raw_dump = any(
        _interp_dumps_iso_sent_at(expr) for expr in _svelte_interpolations(hits_each)
    )
    if raw_dump or _HIT_SENT_AT_NO_DATE.search(hits_each):
        fail(
            "#210: hit rows must not display raw ISO sent_at "
            "(T…Z / h.sent_at || \"no date\" in a join); "
            "use humanTime / utcTime (e.g. 11 Aug 14:32)"
        )

    # 4) Five-field log dump is gone (sent_at · platform · kind · name · title).
    if _hits_meta_is_five_field_log(hits_each):
        fail(
            "#210: hit meta must not join sent_at with platform and "
            "conversation_kind as one ` · ` log line; quiet meta is "
            "short time + person/title, then the snippet"
        )

    # 5) A formatter exists and the hit row actually calls it.
    if not _short_time_formatter_ok(logic):
        fail(
            "#210: format sent_at as a short UTC time "
            "(e.g. 11 Aug 14:32) — month + hour:minute, not YYYY-MM-DDTHH:MM:SSZ"
        )
    if not _hits_uses_short_time(hits_each):
        fail(
            "#210: hit meta must pass sent_at through a short-time helper "
            "(humanTime / utcTime / another name in _HUMAN_TIME_HELPERS), "
            "not interpolate the ISO"
        )

    # 6) Person name and/or conversation title stay on the row.
    if not _HIT_PERSON_OR_TITLE.search(hits_each):
        fail(
            "#210: hit rows must show a person name and/or conversation title "
            "(quiet meta is short time + person/title)"
        )

    # 7) Snippet stays splitSnippet + <mark> text children (#126).
    if not re.search(r"\bsplitSnippet\b", hits_each + "\n" + cleaned):
        fail(
            "#210: keep splitSnippet (or the existing #126 helper) so the "
            "snippet is text + <mark> siblings"
        )
    if not _SEARCH_MARK_TAG.search(hits_each):
        fail(
            "#210: keep <mark> text children on the snippet path "
            "(no {@html} / innerHTML of snippet or body)"
        )
    if re.search(
        r"<mark\b[^>]*>\s*\{(?:\(?\s*)?(?:h\.)?snippet\b[^}]{0,120}\}\s*</mark>",
        hits_each,
        re.I,
    ) and not re.search(r"\{#each\s+", hits_each):
        fail(
            "#210: do not wrap the entire raw snippet in one <mark> — "
            "keep splitSnippet + text / <mark> siblings"
        )

    # 8) No {@html} / innerHTML / regex HTML inject / HTML mail on search path.
    blob = hits_each + "\n" + cleaned
    if _SEARCH_UNSAFE_HTML.search(blob) or _SEARCH_UNSAFE_HTML.search(surface):
        unsafe = re.search(
            r"(?:snippet|body_text|searchBody|\bbody\b|highlight|mark)[\s\S]{0,160}"
            r"(?:\{@html\b|\.innerHTML\s*=|insertAdjacentHTML\s*\()"
            r"|(?:\{@html\b|\.innerHTML\s*=|insertAdjacentHTML\s*\()[\s\S]{0,160}"
            r"(?:snippet|body_text|searchBody|\bbody\b|highlight)",
            blob,
            re.I,
        )
        bare_html = _HTML_BODY.search(blob) or re.search(r"\.innerHTML\s*=", blob)
        if unsafe or bare_html:
            fail(
                "#210: never assign innerHTML / {@html on the search snippet or "
                "body path (a body containing <script> must stay text)"
            )
    if re.search(r"\{@html\s+(?:body|body_text|snippet)\b", blob):
        fail(
            "#210: expanded search body / snippet must stay text-safe — "
            "no {@html body} / {@html snippet}"
        )
    if _SEARCH_REGEX_HTML_MARK.search(blob):
        fail(
            "#210: not in scope — regex highlight that builds HTML mark strings "
            "(no FTS marker rewrite; use text + <mark> siblings)"
        )
    if _SEARCH_HTML_MAIL.search(blob):
        fail(
            "#210: not in scope — HTML mail renderer "
            "(DOMParser / srcdoc / htmlMail on search path)"
        )

    # 9) j/k (or arrows) + Enter/Space still activateHit (#124).
    hits_key = _ts_function_body(src, "onHitsKey") or _function_body(src, "onHitsKey")
    if not hits_key:
        fail("#210: keep onHitsKey (#124) — j/k + Enter jump")
    if not re.search(r"""["']j["']""", hits_key) and not re.search(
        r"ArrowDown", hits_key
    ):
        fail("#210: onHitsKey must still handle j / ArrowDown")
    if not re.search(r"""["']k["']""", hits_key) and not re.search(
        r"ArrowUp", hits_key
    ):
        fail("#210: onHitsKey must still handle k / ArrowUp")
    if not re.search(r"""["']Enter["']""", hits_key) and not re.search(
        r"""["'] ["']""", hits_key
    ):
        fail("#210: onHitsKey must still handle Enter / Space → activateHit")
    if not re.search(r"\bactivateHit\b", hits_key):
        fail("#210: onHitsKey Enter / Space must still call activateHit (#124)")

    # 10) Jump payload still carries ISO sent_at (API, not display).
    act = _ts_function_body(src, "activateHit") or _function_body(src, "activateHit")
    if act and not re.search(r"sentAt\s*:\s*(?:h\.)?sent_at\b", act):
        fail(
            "#210: keep sentAt: h.sent_at on the jump payload — "
            "that is API, not display (do not drop the ISO field)"
        )

    # 11) Light people-list density (do not over-constrain Tailwind).
    if not _HIT_DENSITY_META.search(hits_each):
        fail(
            "#210: hit meta should stay people-list scale "
            "(text-xs / 12–13px), not giant cards"
        )
    if not _HIT_DENSITY_SNIP.search(hits_each):
        fail(
            "#210: hit snippet should stay people-list scale "
            "(text-sm / 14–15px)"
        )
    if not _HIT_DENSITY_PAD.search(hits_each):
        fail(
            "#210: hit rows should stay tight (py-2 / gap-2), not giant cards"
        )

    # 12) Do not soften #121–#126 / #205 / #208 / #209.
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", surface):
        fail("#210: keep id=\"q\" as the canonical query field (#208 / #209)")
    if not re.search(r"\bdata-search-filters\b", surface):
        fail("#210: keep data-search-filters (#209)")
    if not re.search(r"\bdata-chrome-search\b", app):
        fail("#210: keep chrome search field data-chrome-search (#208)")
    if re.search(r"\bapi\.search\s*\(", app):
        fail(
            "#210: App.svelte must not call api.search — SearchPane run() stays "
            "the only caller (#208)"
        )
    if not re.search(r"data-person-picker|personFilter|personId", cleaned):
        fail("#210: keep the search person picker (#123)")
    if not re.search(r"\bdata-partial\b", surface):
        fail("#210: keep search data-partial Error+Retry (#205)")

    # 13) Docs (D24): short time + person/title, then highlighted snippet.
    if not _DOCS_HIT_DENSITY.search(dtxt):
        fail(
            "#210: docs/user/search.md and/or docs/user/app.md must say "
            "search hits show a short time + person/title, then a "
            "highlighted snippet"
        )
    if not _DOCS_HIT_NOT_ISO.search(dtxt):
        fail(
            "#210: docs/user/search.md and/or docs/user/app.md must say "
            "search hits are not a raw ISO dump"
        )
