"""Helpers extracted from review.py (review_queue)."""
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


# #221 — review queue chrome: Card/Separator, no raw ids, undo on the pane.
_REVIEW_CARD_IMPORT = re.compile(
    r"import\s+(?:\{[^}]*\bCard\b[^}]*\}|\bCard\b)\s+from\s+"
    r"[\"']\$lib/components/ui/card(?:/[^\"']*)?[\"']",
    re.S,
)
_REVIEW_SEP_IMPORT = re.compile(
    r"import\s+(?:\{[^}]*\bSeparator\b[^}]*\}|\bSeparator\b)\s+from\s+"
    r"[\"']\$lib/components/ui/separator(?:/[^\"']*)?[\"']",
    re.S,
)
_REVIEW_ACCEPT = re.compile(r">\s*Accept\s*<")
_REVIEW_REJECT = re.compile(r">\s*Reject\s*<")
_REVIEW_RAW_VISIBLE = re.compile(
    r"("
    r"#\{\s*r\.id\s*\}"
    r"|person\s+\$\{"
    r"|person\s+\$\{\s*r\.right_person_id"
    r"|Accept review \$\{id\}"
    r")"
)
_REVIEW_NAME_SCORE_UI = re.compile(
    r"("
    r"name_score\s*[<>]=?"
    r"|nameScoreThreshold"
    r"|raise.*name_score"
    r"|lower.*name_score"
    r")",
    re.I,
)
_REVIEW_SAMPLE_EACH = re.compile(r"\{#each\s+panel\.samples\b")
_REVIEW_SECOND_BODY = re.compile(
    r"\{#each\s+(?!panel\.samples\b)[^}]*\b(?:samples|bodies|body_lines|body_text)\b"
)
_REVIEW_LINK_EVENTS = re.compile(r"\blinkEvents\b")
_REVIEW_UNDO_USE = re.compile(r"(?:\bapi\s*\.\s*)?\bundo\s*\(")
_REVIEW_AWAIT_ONCONFIRM = re.compile(r"await\s+onconfirm\s*\(")
_REVIEW_OPEN_FALSE = re.compile(r"\bopen\s*=\s*false\b")
_REVIEW_AWAIT_CHANGED = re.compile(r"await\s+onChanged\s*\(")
_REVIEW_ONERROR_PROP = re.compile(r"\b(?:onerror|onError)\b")
_REVIEW_APP_CONFIRM_ERR = re.compile(r"\b(?:onerror|onError|showErr)\b")
_REVIEW_INFLIGHT_TOKEN = re.compile(
    r"\b(?:resolving|undoing|busy|accepting|rejecting|"
    r"inFlight|inflight|isBusy|working|pending|acting)\b"
)
_REVIEW_BOOL_STATE = re.compile(
    r"\b(?:let|const|var)\s+(\w+)\s*=\s*\$state\(\s*(?:false|true)\s*\)"
)
_REVIEW_ONERROR_SKIP = frozenset(
    {
        "reload",
        "onChanged",
        "ask",
        "canAccept",
        "api",
        "requestUndo",
        "runUndo",
        "void",
        "if",
        "await",
        "Promise",
        "Set",
        "Array",
        "Boolean",
        "Number",
        "String",
    }
)
_REVIEW_INFLIGHT_SKIP_FLAGS = frozenset({"confirmOpen", "loading", "selected"})
_REVIEW_DOCS_UNDO = re.compile(r"\bundo(?:able)?\b|\breversible\b", re.I)
_REVIEW_DOCS_NO_RAW = re.compile(
    r"("
    r"no raw person id"
    r"|not raw person id"
    r"|without raw person"
    r"|raw person ids?"
    r")",
    re.I,
)
_REVIEW_DOCS_IDENTS = re.compile(r"\bidentifiers?\b", re.I)


def _review_action_tag(markup: str, label: str) -> str:
    """Opening <Button>/<button> that wraps >Label<."""
    m = re.search(rf">\s*{re.escape(label)}\s*<", markup)
    if not m:
        return ""
    for tag in _ancestor_tags(markup, m.start(), limit=8):
        if re.match(r"<(?:Button|button)\b", tag):
            return tag
    return ""


def _review_docs_blob(dtxt: str) -> str:
    """Copy window starting at the Review heading / mention (not Merge/unlink/undo)."""
    m = re.search(r"\*\*Review\*\*.{0,1200}", dtxt, re.S | re.I)
    if m:
        return m.group(0)
    m = re.search(r"\bReview\b.{0,1200}", dtxt, re.S)
    return m.group(0) if m else ""


def _review_undo_action_blob(src: str) -> str:
    """Undo action script: named helpers + callees + api.undo windows."""
    parts: list[str] = []
    for name in ("runUndo", "requestUndo", "undoLast", "undoLink", "doUndo"):
        body = _ts_fn_body(src, name) or _function_body(src, name)
        if body:
            parts.append(_expand_fn_calls(src, body, depth=2))
    for m in _REVIEW_UNDO_USE.finditer(src):
        start = max(0, m.start() - 400)
        end = min(len(src), m.end() + 500)
        parts.append(src[start:end])
    return "\n".join(parts)


def _review_attr_expr(tag: str, name: str) -> str:
    """Value inside attr={...} on an opening tag."""
    m = re.search(rf"\b{re.escape(name)}\s*=\s*\{{", tag)
    if not m:
        return ""
    open_i = m.end() - 1
    close = _match_closer(tag, open_i)
    if close < 0:
        return ""
    return tag[open_i + 1 : close]


def _review_top_args(src: str, open_paren: int) -> list[str]:
    close = _match_closer(src, open_paren)
    if close < 0:
        return []
    args = src[open_paren + 1 : close]
    parts: list[str] = []
    start = 0
    depth = 0
    i = 0
    n = len(args)
    while i < n:
        nxt = _js_next(args, i)
        if nxt != i:
            i = nxt
            continue
        c = args[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append(args[start:i])
            start = i + 1
        i += 1
    parts.append(args[start:])
    return [p.strip() for p in parts if p.strip()]


def _review_expr_fn_body(src: str, expr: str) -> str:
    """Body of an inline arrow/function expr, or a named helper it calls."""
    expr = expr.strip().rstrip(";")
    m = re.search(
        r"(?:async\s*)?(?:function\s*)?\([^)]*\)\s*(?::\s*[^{=]+)?=>\s*\{",
        expr,
    )
    if not m:
        m = re.search(r"(?:async\s+)?function\s*\([^)]*\)\s*\{", expr)
    if m:
        brace = expr.find("{", m.end() - 1)
        if brace >= 0:
            close = _match_closer(expr, brace)
            if close > brace:
                return expr[brace + 1 : close]
    ident = re.fullmatch(r"([A-Za-z_]\w*)", expr)
    if ident:
        return _ts_fn_body(src, ident.group(1)) or _function_body(
            src, ident.group(1)
        )
    call = re.fullmatch(
        r"(?:async\s*)?\([^)]*\)\s*(?::\s*[^=]+)?=>\s*([A-Za-z_]\w*)\s*\(.*\)",
        expr,
        re.S,
    )
    if call:
        return _ts_fn_body(src, call.group(1)) or _function_body(
            src, call.group(1)
        )
    return expr


def _review_derived_body(src: str, name: str) -> str:
    m = re.search(
        rf"\b(?:let|const|var)\s+{re.escape(name)}\s*=\s*"
        rf"\$derived(?:\.by)?\s*\(",
        src,
    )
    if not m:
        return ""
    close = _match_closer(src, m.end() - 1)
    if close < 0:
        return ""
    return src[m.end() : close]


def _review_mentions_inflight(src: str, expr: str, tokens: set[str]) -> bool:
    if not expr or not tokens:
        return False
    blob = expr + "\n" + _expand_fn_calls(src, expr, depth=2)
    for name in re.findall(r"\b([A-Za-z_]\w*)\b", expr):
        derived = _review_derived_body(src, name)
        if derived:
            blob += "\n" + derived
    return any(re.search(rf"\b{re.escape(t)}\b", blob) for t in tokens)


def _review_fn_body(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name)


def _review_inflight_tokens(src: str) -> set[str]:
    """resolving/undoing/similar, plus $state flags set true on accept/reject."""
    tokens = set(_REVIEW_INFLIGHT_TOKEN.findall(src))
    action: list[str] = []
    for name in ("accept", "reject", "ask"):
        body = _review_fn_body(src, name)
        if body:
            action.append(body)
            for callee in re.findall(r"\b([A-Za-z_]\w*)\s*\(", body):
                if callee in _REVIEW_ONERROR_SKIP:
                    continue
                inner = _review_fn_body(src, callee)
                if inner:
                    action.append(inner)
    blob = "\n".join(action)
    for name in _REVIEW_BOOL_STATE.findall(src):
        if name in _REVIEW_INFLIGHT_SKIP_FLAGS:
            continue
        if re.search(rf"\b{re.escape(name)}\s*=\s*true\b", blob):
            tokens.add(name)
    return tokens


def _review_ask_callback_bodies(src: str, fn_body: str) -> list[str]:
    """Last arg to ask(...) and confirmRun = ... inside fn_body (+ one helper)."""
    blobs = [fn_body]
    for callee in re.findall(r"\b([A-Za-z_]\w*)\s*\(", fn_body):
        if callee in _REVIEW_ONERROR_SKIP | {"confirmRun"}:
            continue
        inner = _review_fn_body(src, callee)
        if inner:
            blobs.append(inner)
    cbs: list[str] = []
    for blob in blobs:
        for m in re.finditer(r"\bask\s*\(", blob):
            args = _review_top_args(blob, m.end() - 1)
            if args:
                body = _review_expr_fn_body(src, args[-1])
                if body:
                    cbs.append(body)
        for m in re.finditer(r"\bconfirmRun\s*=", blob):
            rest = blob[m.end() :]
            body = _review_expr_fn_body(src, rest)
            if body:
                cbs.append(body)
    return cbs

from tauri_gate.review_queue_rest import (
    _review_has_try_onerror,
    _review_onconfirm_blob,
    _confirm_refuses_open_while_busy,
    _confirm_go_catches_onconfirm,
    _review_component_tag,
    _review_undo_control_tag,
    _SIDEBAR_UNDO_EACH_SRC,
    _SIDEBAR_RAW_ID_TITLE,
    _SIDEBAR_BARE_ID_TEXT,
    _SIDEBAR_CONFIRM_RAW,
    _SIDEBAR_UNDO_FN_NAMES,
    _SIDEBAR_DOCS_UNDO,
    _SIDEBAR_DOCS_SKIP,
    _SIDEBAR_DOCS_NO_RAW,
    __all__,
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
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_ancestor_tags",
    "_APPEARANCE_MENU_LABEL",
    "_APPEARANCE_SCRIM_NAMES",
    "_contrast_dark_blob",
    "_css_var",
    "_expand_fn_calls",
    "_function_body",
    "_js_next",
    "_match_closer",
    "_open_tag_before",
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
]
