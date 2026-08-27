"""Helpers extracted from search_field.py (search_field_keys)."""
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

from tauri_gate.search_field_keys_rest import (
    _stack_requires_empty_hits,
    _stack_requires_existing_hits,
    _search_skeleton_stacks,
    _blank_returning_blocks,
    _run_before_ipc,
    _run_clears_debounce_timer,
    _js_unawaited_calls,
    _trailing_catch_has_err,
    _fire_forget_people_caught,
    _hits_key_bails_on_searching,
    _js_comment_text,
    __all__,
)

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
