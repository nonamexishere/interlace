"""Helpers extracted from search_hits.py (search_hits_jump)."""
from __future__ import annotations

from __future__ import annotations

from __future__ import annotations
import re
from pathlib import Path
from common import fail, repo_root
from tauri_gate.scan import (
    _function_body,
    _HTML_BODY,
    _matching_each_end,
    _search_pane_blob,
    _svelte_interpolations,
    _svelte_markup,
    _ts_function_body,
    _web_logic,
    _without_comments,
)
from tauri_gate.import_boot_guards import _HUMAN_TIME_HELPERS
from tauri_gate.status_toasts_toast import _short_time_formatter_ok


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

from tauri_gate.search_hits_jump_rest import (
    _SEARCH_HIGHLIGHT_HELPER,
    _SEARCH_SNIPPET_SPLIT,
    _SEARCH_MARK_TAG,
    _SEARCH_MARK_STYLE,
    _SEARCH_UNSAFE_HTML,
    _SEARCH_REGEX_HTML_MARK,
    _SEARCH_HTML_MAIL,
    _search_highlight_surface,
    _HIT_TIME_EXTRA,
    _HIT_SENT_AT_NO_DATE,
    _HIT_LOG_JOIN,
    _HIT_PERSON_OR_TITLE,
    _HIT_DENSITY_META,
    _HIT_DENSITY_SNIP,
    _HIT_DENSITY_PAD,
    _DOCS_HIT_DENSITY,
    _DOCS_HIT_NOT_ISO,
    _hit_time_helpers,
    _hit_time_call_rx,
    _hits_each_block,
    _interp_dumps_iso_sent_at,
    _hits_uses_short_time,
    __all__,
)

__all__ = [
    "_SEARCH_JUMP_FN",
    "_SEARCH_JUMP_PROP",
    "_VIEW_PEOPLE",
    "_HIT_PERSON_ID_READ",
    "_HIT_MESSAGE_ID_READ",
    "_SEARCH_EXPAND_BODY",
    "_SEARCH_JUMP_SCROLL_HL",
    "_SEARCH_JUMP_LOAD_WINDOW",
    "_SEARCH_JUMP_CALL_RE",
    "_HIT_ACTIVATES_JUMP",
    "_JUMP_BODY_SELECTS_PERSON",
    "_JUMP_BODY_USES_MESSAGE",
    "_HIT_PERSON_GUARD",
    "_IDX_NAME",
    "_LOADED_NAME",
    "_SEARCH_JUMP_LAST_ROW_FALLBACK",
    "_SEARCH_JUMP_TLINDEX_MISS_TERNARY",
    "_SEARCH_JUMP_MISS_ERROR",
    "_search_jump_handler_bodies",
    "_assert_search_jump_miss_path",
    "_SEARCH_HIGHLIGHT_HELPER",
    "_SEARCH_SNIPPET_SPLIT",
    "_SEARCH_MARK_TAG",
    "_SEARCH_MARK_STYLE",
    "_SEARCH_UNSAFE_HTML",
    "_SEARCH_REGEX_HTML_MARK",
    "_SEARCH_HTML_MAIL",
    "_search_highlight_surface",
    "_HIT_TIME_EXTRA",
    "_HIT_SENT_AT_NO_DATE",
    "_HIT_LOG_JOIN",
    "_HIT_PERSON_OR_TITLE",
    "_HIT_DENSITY_META",
    "_HIT_DENSITY_SNIP",
    "_HIT_DENSITY_PAD",
    "_DOCS_HIT_DENSITY",
    "_DOCS_HIT_NOT_ISO",
    "_hit_time_helpers",
    "_hit_time_call_rx",
    "_hits_each_block",
    "_interp_dumps_iso_sent_at",
    "_hits_uses_short_time",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_function_body",
    "_HTML_BODY",
    "_matching_each_end",
    "_search_pane_blob",
    "_svelte_interpolations",
    "_svelte_markup",
    "_ts_function_body",
    "_web_logic",
    "_without_comments",
    "_HUMAN_TIME_HELPERS",
    "_short_time_formatter_ok",
]
