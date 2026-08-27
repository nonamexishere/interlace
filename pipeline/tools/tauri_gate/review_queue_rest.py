"""Continuation of review_queue."""
from __future__ import annotations

from __future__ import annotations

from __future__ import annotations
import re
from pathlib import Path
from common import fail, repo_root
from tauri_gate.scan import (
    _ancestor_tags,
    _APPEARANCE_MENU_LABEL,
    _APPEARANCE_SCRIM_NAMES,
    _contrast_dark_blob,
    _css_var,
    _expand_fn_calls,
    _function_body,
    _js_next,
    _match_closer,
    _open_tag_before,
    _product_svelte,
    _search_pane_blob,
    _STATUS_WARNING_NAMES,
    _svelte_markup,
    _ts_fn_body,
    _web_logic,
    _without_comments,
    CSP,
)
from tauri_gate.import_boot_guards import (
    _contrast_light_blob,
    _review_if_return_conds,
)
from tauri_gate.status_toasts_chrome import (
    _APPEARANCE_THEME_UI,
    _hue_surface,
)
from tauri_gate.review_queue import (
    _REVIEW_OPEN_FALSE,
    _REVIEW_ONERROR_SKIP,
    _review_attr_expr,
    _review_fn_body,
)


def _review_has_try_onerror(src: str, blob: str, depth: int = 1) -> bool:
    if re.search(r"\btry\s*\{", blob) and re.search(
        r"\bcatch\b", blob
    ) and re.search(r"\bonError\s*\(", blob):
        return True
    if depth <= 0:
        return False
    for name in re.findall(r"\b([A-Za-z_]\w*)\s*\(", blob):
        if name in _REVIEW_ONERROR_SKIP:
            continue
        inner = _review_fn_body(src, name)
        if inner and _review_has_try_onerror(src, inner, depth - 1):
            return True
    return False


def _review_onconfirm_blob(src: str) -> str:
    m = re.search(r"\bonconfirm\s*=\s*\{", src)
    if not m:
        return ""
    open_i = m.end() - 1
    close = _match_closer(src, open_i)
    if close < 0:
        return ""
    return src[open_i + 1 : close]


def _confirm_refuses_open_while_busy(src: str) -> bool:
    """True if open=true is ignored / forced false while busy."""
    for m in re.finditer(r"\bif\s*\(", src):
        close = _match_closer(src, m.end() - 1)
        if close < 0:
            continue
        cond = src[m.end() : close]
        if not re.search(r"\bbusy\b", cond):
            continue
        rest = src[close + 1 :].lstrip()
        then = rest
        if rest.startswith("{"):
            open_b = src.find("{", close)
            close_b = _match_closer(src, open_b) if open_b >= 0 else -1
            then = src[open_b + 1 : close_b] if close_b > open_b else rest
        if re.search(r"\breturn\b", then) or _REVIEW_OPEN_FALSE.search(then):
            return True
    for m in re.finditer(r"\$effect(?:\.pre)?\s*\(", src):
        close = _match_closer(src, m.end() - 1)
        if close < 0:
            continue
        body = src[m.end() : close]
        if re.search(r"\bbusy\b", body) and (
            _REVIEW_OPEN_FALSE.search(body) or re.search(r"\bopen\b", body)
        ):
            return True
    return False


def _confirm_go_catches_onconfirm(go_body: str) -> bool:
    """True if onconfirm is in try/catch, chained .catch, or onerror call."""
    if re.search(r"\b(?:onerror|onError)\s*\(", go_body) and re.search(
        r"\bonconfirm\s*\(", go_body
    ):
        return True
    for m in re.finditer(r"\bonconfirm\s*\(", go_body):
        close = _match_closer(go_body, m.end() - 1)
        if close < 0:
            continue
        rest = go_body[close + 1 :].lstrip()
        if rest.startswith(".catch"):
            return True
    for m in re.finditer(r"\btry\s*\{", go_body):
        open_b = m.end() - 1
        close_b = _match_closer(go_body, open_b)
        if close_b < 0:
            continue
        if not re.search(r"\bonconfirm\s*\(", go_body[open_b + 1 : close_b]):
            continue
        rest = go_body[close_b + 1 :].lstrip()
        if rest.startswith("catch"):
            return True
    return False


def _review_component_tag(src: str, name: str) -> str:
    """First <Name ...> opening tag, including {nested} attrs."""
    m = re.search(rf"<{re.escape(name)}\b", src)
    if not m:
        return ""
    found = _open_tag_before(src, min(len(src), m.end() + 1))
    if found and found[0] == m.start():
        return found[1]
    return ""


def _review_undo_control_tag(markup: str) -> str:
    """Opening tag of the Review Undo control (`data-review-undo`)."""
    m = re.search(r"\bdata-review-undo\b", markup)
    if not m:
        return ""
    for tag in _ancestor_tags(markup, m.start(), limit=8):
        if re.match(r"<(?:Button|button)\b", tag, re.I):
            return tag
        if _review_attr_expr(tag, "disabled"):
            return tag
    found = _open_tag_before(markup, m.start() + 1)
    return found[1] if found else ""


# #269 — people sidebar undo chrome (names, skip split_person). Sibling of #221.
_SIDEBAR_UNDO_EACH_SRC = re.compile(
    r"\b(?:events|undoableEvents|undoEvents|sidebarEvents|sidebarUndo|"
    r"undoable|lastUndoable|filteredEvents|linkEvents|undoList)\b",
    re.I,
)
_SIDEBAR_RAW_ID_TITLE = re.compile(
    r"("
    r"#\{\s*(?:e|ev|event|row)\s*\.\s*id\s*\}"
    r"|#\{\s*id\s*\}"
    r")"
)
_SIDEBAR_BARE_ID_TEXT = re.compile(
    r"\{\s*(?:e|ev|event|row)\s*\.\s*id\s*\}"
)
_SIDEBAR_CONFIRM_RAW = re.compile(
    r"("
    r"Undo event\s*\$\{"
    r"|Undo event\s*['\"`]\s*\+"
    r"|event\s+\$\{\s*id"
    r"|event\s+\$\{\s*(?:e|ev|event)\s*\.\s*id"
    r")"
)
_SIDEBAR_UNDO_FN_NAMES = (
    "doUndo",
    "requestUndo",
    "undoLast",
    "undoEvent",
    "askUndo",
    "runUndo",
)
_SIDEBAR_DOCS_UNDO = re.compile(
    r"("
    r"(?:people\s+)?sidebar.{0,160}\bundo\b"
    r"|\bundo\b.{0,160}(?:people\s+)?sidebar"
    r")",
    re.I | re.S,
)
_SIDEBAR_DOCS_SKIP = re.compile(
    r"("
    r"split_person"
    r"|undo-log"
    r"|undo log"
    r"|already[- ]undone"
    r"|skip(?:s|ping)?\s+(?:the\s+)?(?:undo[- ]log|split)"
    r")",
    re.I,
)
_SIDEBAR_DOCS_NO_RAW = re.compile(
    r"("
    r"raw event ids?"
    r"|no raw event"
    r"|not raw event"
    r"|without raw event"
    r"|not.{0,40}(?:raw )?event id"
    r"|event id as (?:the )?(?:title|label|only)"
    r"|name/?op(?: label)?"
    r")",
    re.I,
)

__all__ = [
    "_REVIEW_CARD_IMPORT",
    "_REVIEW_SEP_IMPORT",
    "_REVIEW_ACCEPT",
    "_REVIEW_REJECT",
    "_REVIEW_RAW_VISIBLE",
    "_REVIEW_NAME_SCORE_UI",
    "_REVIEW_SAMPLE_EACH",
    "_REVIEW_SECOND_BODY",
    "_REVIEW_LINK_EVENTS",
    "_REVIEW_UNDO_USE",
    "_REVIEW_AWAIT_ONCONFIRM",
    "_REVIEW_OPEN_FALSE",
    "_REVIEW_AWAIT_CHANGED",
    "_REVIEW_ONERROR_PROP",
    "_REVIEW_APP_CONFIRM_ERR",
    "_REVIEW_INFLIGHT_TOKEN",
    "_REVIEW_BOOL_STATE",
    "_REVIEW_ONERROR_SKIP",
    "_REVIEW_INFLIGHT_SKIP_FLAGS",
    "_REVIEW_DOCS_UNDO",
    "_REVIEW_DOCS_NO_RAW",
    "_REVIEW_DOCS_IDENTS",
    "_review_action_tag",
    "_review_docs_blob",
    "_review_undo_action_blob",
    "_review_attr_expr",
    "_review_top_args",
    "_review_expr_fn_body",
    "_review_derived_body",
    "_review_mentions_inflight",
    "_review_fn_body",
    "_review_inflight_tokens",
    "_review_ask_callback_bodies",
    "_review_has_try_onerror",
    "_review_onconfirm_blob",
    "_confirm_refuses_open_while_busy",
    "_confirm_go_catches_onconfirm",
    "_review_component_tag",
    "_review_undo_control_tag",
    "_SIDEBAR_UNDO_EACH_SRC",
    "_SIDEBAR_RAW_ID_TITLE",
    "_SIDEBAR_BARE_ID_TEXT",
    "_SIDEBAR_CONFIRM_RAW",
    "_SIDEBAR_UNDO_FN_NAMES",
    "_SIDEBAR_DOCS_UNDO",
    "_SIDEBAR_DOCS_SKIP",
    "_SIDEBAR_DOCS_NO_RAW",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_APPEARANCE_MENU_LABEL",
    "_APPEARANCE_SCRIM_NAMES",
    "_contrast_dark_blob",
    "_css_var",
    "_expand_fn_calls",
    "_function_body",
    "_product_svelte",
    "_search_pane_blob",
    "_STATUS_WARNING_NAMES",
    "_svelte_markup",
    "_ts_fn_body",
    "_web_logic",
    "_without_comments",
    "CSP",
    "_contrast_light_blob",
    "_review_if_return_conds",
    "_APPEARANCE_THEME_UI",
    "_hue_surface",
    "annotations",
    "_ancestor_tags",
    "_js_next",
    "_match_closer",
    "_open_tag_before",
]

__all__ = [
    "_review_has_try_onerror",
    "_review_onconfirm_blob",
    "_confirm_refuses_open_while_busy",
    "_confirm_go_catches_onconfirm",
    "_review_component_tag",
    "_review_undo_control_tag",
    "_SIDEBAR_UNDO_EACH_SRC",
    "_SIDEBAR_RAW_ID_TITLE",
    "_SIDEBAR_BARE_ID_TEXT",
    "_SIDEBAR_CONFIRM_RAW",
    "_SIDEBAR_UNDO_FN_NAMES",
    "_SIDEBAR_DOCS_UNDO",
    "_SIDEBAR_DOCS_SKIP",
    "_SIDEBAR_DOCS_NO_RAW",
    "__all__",
]
