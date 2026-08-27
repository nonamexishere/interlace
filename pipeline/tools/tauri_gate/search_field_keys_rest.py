"""Continuation of search_field_keys."""
from __future__ import annotations

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
from tauri_gate.search_field_keys import (
    _SEARCH_HITS_EMPTY,
    _SEARCH_CLEAR_TIMEOUT,
    _SEARCH_TIMER_PERSON_BLUR,
    _SEARCH_ERR_HANDLER,
    _SEARCH_VOID_CALL,
    _cond_requires_empty_hits,
    _cond_requires_existing_hits,
)


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

__all__ = [
    "_API_SEARCH_CALL",
    "_INVOKE_SEARCH_CMD",
    "_CHROME_TO_Q",
    "_CHROME_FIELD_EL",
    "_SPOTLIGHT_WORD",
    "_MULTI_ARCHIVE_WORD",
    "_REMOTE_SEARCH_WORD",
    "_chrome_search_handler_surface",
    "_CHROME_SEARCH_HOOK",
    "_SEARCH_Q_TOKEN",
    "_SEARCH_TYPE_INPUT_ATTR",
    "_SEARCH_TYPE_HANDLER",
    "_SEARCH_AS_YOU_TYPE_TRIGGER",
    "_SEARCH_PEOPLE_FROM_RUN",
    "_SEARCH_DISABLED_PEOPLE",
    "_TANTIVY_WORD",
    "_SEARCH_TYPE_HANDLER_SKIP",
    "_DOCS_TYPE_TO_SEARCH",
    "_DOCS_SEARCH_NOT_WAIT_PEOPLE",
    "_SEARCH_HITS_EMPTY",
    "_SEARCH_HITS_NONEMPTY",
    "_SEARCH_PRE_IPC_EXPANDED",
    "_SEARCH_PRE_IPC_BODY",
    "_SEARCH_PRE_IPC_HITINDEX",
    "_SEARCH_PRE_IPC_HITS_CLEAR",
    "_SEARCH_CLEAR_TIMEOUT",
    "_SEARCH_TIMER_PERSON_BLUR",
    "_SEARCH_ERR_HANDLER",
    "_SEARCH_VOID_CALL",
    "_SEARCH_RESTATE_DEBOUNCE_COMMENT",
    "_search_q_open_tag",
    "_search_type_input_surface",
    "_search_as_you_type_surface",
    "_has_search_as_you_type",
    "_search_gated_on_people_loading",
    "_cond_requires_empty_hits",
    "_cond_requires_existing_hits",
    "_stack_searching_true",
    "_stack_requires_empty_hits",
    "_stack_requires_existing_hits",
    "_search_skeleton_stacks",
    "_blank_returning_blocks",
    "_run_before_ipc",
    "_run_clears_debounce_timer",
    "_js_unawaited_calls",
    "_trailing_catch_has_err",
    "_fire_forget_people_caught",
    "_hits_key_bails_on_searching",
    "_js_comment_text",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_expand_fn_calls",
    "_FETCH_CALL",
    "_function_body",
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
    "_people_list_gen",
    "_hook_element_blocks",
    "_SEARCH_HIGHLIGHT_HELPER",
    "_SEARCH_MARK_TAG",
    "_SEARCH_SNIPPET_SPLIT",
    "_SEARCH_FILTERS_HOOK",
    "_SEARCH_Q_ID",
    "_FOCUS_SEARCH_Q",
    "_claim_without_negation",
    "_tag_inner",
    "annotations",
    "_js_next",
    "_match_closer",
    "_ident_negated",
    "_if_gen_eq_contains",
    "_review_if_return_conds",
    "_same_block_gen_ne_return",
    "_svelte_open_tag_at",
    "_try_catch_blocks",
    "_cond_code",
    "_first_substr_pos",
    "_owned_skeleton_names",
    "_skeleton_hook_positions",
    "_svelte_effect_args",
]

__all__ = [
    "_stack_requires_empty_hits",
    "_stack_requires_existing_hits",
    "_search_skeleton_stacks",
    "_blank_returning_blocks",
    "_run_before_ipc",
    "_run_clears_debounce_timer",
    "_js_unawaited_calls",
    "_trailing_catch_has_err",
    "_fire_forget_people_caught",
    "_hits_key_bails_on_searching",
    "_js_comment_text",
    "__all__",
]
