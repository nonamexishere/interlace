"""Helpers extracted from search_field.py (search_field_debounce)."""
from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _expand_fn_calls,
    _FETCH_CALL,
    _function_body,
    _js_next,
    _match_closer,
    _PEOPLE_AWAIT_REFRESH,
    _product_svelte,
    _search_pane_blob,
    _svelte_markup,
    _template_stack,
    _ts_fn_body,
    _VIEW_SEARCH_ASSIGN,
    _web_logic,
    _web_sources,
    _without_comments,
)

from tauri_gate.import_boot_guards import (
    _ident_negated,
    _if_gen_eq_contains,
    _people_list_gen,
    _review_if_return_conds,
    _same_block_gen_ne_return,
    _svelte_open_tag_at,
)
from tauri_gate.import_boot_setup import _try_catch_blocks

from tauri_gate.media_linkify_lib import _hook_element_blocks

from tauri_gate.search_hits_jump import (
    _SEARCH_HIGHLIGHT_HELPER,
    _SEARCH_MARK_TAG,
    _SEARCH_SNIPPET_SPLIT,
)

from tauri_gate.search_picker_lib import (
    _SEARCH_FILTERS_HOOK,
    _SEARCH_Q_ID,
)

from tauri_gate.status_toasts_chrome import (
    _FOCUS_SEARCH_Q,
    _claim_without_negation,
    _cond_code,
    _first_substr_pos,
    _owned_skeleton_names,
    _skeleton_hook_positions,
)
from tauri_gate.status_toasts_toast import (
    _svelte_effect_args,
    _tag_inner,
)


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

__all__ = [
    "_js_dot_catch_args",
    "_js_handler_body",
    "_refresh_people_catch_blobs",
    "_site_gen_guarded",
    "_catch_err_positions",
    "_refresh_people_catch_gen_guarded",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_expand_fn_calls",
    "_FETCH_CALL",
    "_function_body",
    "_js_next",
    "_match_closer",
    "_PEOPLE_AWAIT_REFRESH",
    "_product_svelte",
    "_search_pane_blob",
    "_svelte_markup",
    "_template_stack",
    "_ts_fn_body",
    "_VIEW_SEARCH_ASSIGN",
    "_web_logic",
    "_web_sources",
    "_without_comments",
    "_ident_negated",
    "_if_gen_eq_contains",
    "_people_list_gen",
    "_review_if_return_conds",
    "_same_block_gen_ne_return",
    "_svelte_open_tag_at",
    "_try_catch_blocks",
    "_hook_element_blocks",
    "_SEARCH_HIGHLIGHT_HELPER",
    "_SEARCH_MARK_TAG",
    "_SEARCH_SNIPPET_SPLIT",
    "_SEARCH_FILTERS_HOOK",
    "_SEARCH_Q_ID",
    "_FOCUS_SEARCH_Q",
    "_claim_without_negation",
    "_cond_code",
    "_first_substr_pos",
    "_owned_skeleton_names",
    "_skeleton_hook_positions",
    "_svelte_effect_args",
    "_tag_inner",
]
