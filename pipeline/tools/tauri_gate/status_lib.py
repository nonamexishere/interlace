"""Helpers extracted from status.py (status_lib)."""
from __future__ import annotations

from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import fail

from tauri_gate.scan import (
    _assigned_idents,
    _call_arg,
    _chrome_en_text,
    _cond_uses_flag,
    _match_closer,
    _product_svelte,
    _search_pane_blob,
    _svelte_markup,
    _template_stack,
    _TOAST_SONNER_PKG,
    _web_logic,
    _without_comments,
)

from tauri_gate.import_boot_guards import (
    _gen_increment_before_ipc,
    _svelte_if_true_branch,
    _unguarded_post_ipc_writes,
)
from tauri_gate.import_boot_setup import _try_catch_blocks

from tauri_gate.media_linkify_lib import _hook_element_blocks

from tauri_gate.status_toasts_toast import (
    _HTTP_CLIENT_PKG,
    _TOAST_CDN,
    _assigns_err_banner,
    _ident_body,
    _svelte_if_chains,
    _web_chrome_blob,
)
from tauri_gate.status_toasts_chrome import (
    _first_substr_pos,
    _typo_docs_blob,
)




# #205 — one pane can fail without blanking the shell (Error + Retry).
# Grep hook: data-partial on each of the three Error+Retry surfaces
# (person timeline, search results, doctor scan). Equivalent hook is
# not accepted unless documented here — prefer data-partial as IN.md.
_PARTIAL_HOOK = re.compile(r"\bdata-partial\b")
_RETRY_COPY = re.compile(
    r"("
    r">\s*Retry\s*<"
    r"|[\"']Retry[\"']"
    r"|\bt\s*\(\s*[\"']retry[\"']\s*\)"
    r")",
    re.I,
)
_ERROR_COPY = re.compile(
    r"("
    r"\bError\b"
    r"|\bt\s*\(\s*[\"']error[\"']\s*\)"
    r")",
)
_ONERROR_CALL = re.compile(r"\bonError\s*\(")
_PARTIAL_MASCOT = re.compile(r"\bmascot\b|\billustration\b|<img\b", re.I)
_PARTIAL_CDN = re.compile(
    r"("
    r"https?://[^\"'\s)]+"
    r"|(?:unpkg(?:\.com)?|jsdelivr(?:\.net)?|esm\.sh|cdnjs|cdn\.)"
    r")",
    re.I,
)
_DOCTOR_HEAVY = re.compile(
    r"("
    r"\bdoctorRun\b"
    r"|\bgcCas\b"
    r"|\bgc_cas\b"
    r"|\brebuildFts\b"
    r"|\brebuild_fts\b"
    r"|\bintegrity\s*:\s*true\b"
    r")",
)
_AUTO_RETRY_TIMER = re.compile(r"\bsetInterval\b")
_RECURSIVE_RETRY = re.compile(
    r"\.catch\s*\(\s*(?:async\s*)?(?:function\b|[A-Za-z_]\w*|\([^)]*\)\s*=>)",
)
_SEARCH_FILTER_IDENTS = ("q", "platform", "conversationKind", "from", "to", "personId")
_PANE_CATCH_NOISE = frozenset(
    {
        "tlLoading",
        "tlAppending",
        "tlIndex",
        "tlScrollTop",
        "tlViewportHeight",
        "tlGen",
        "gen",
        "searchGen",
        "scanGen",
        "runGen",
        "loadGen",
        "scanning",
        "searching",
        "busy",
        "empty",
        "searched",
        "expanded",
        "body",
        "hitIndex",
        "hits",
        "timeline",
        "conversations",
        "identities",
        "personTitle",
        "quotedOpen",
        "platformFilter",
        "kindFilter",
        "showPersonChrome",
        "selectedConversationId",
        "selectedId",
        "issues",
        "lastOk",
        "confirmOpen",
        "confirmTitle",
        "confirmDesc",
        "confirmLabel",
        "pending",
        "err",
        "view",
        "setup",
        "people",
        "filter",
        "includeGroups",
        "before",
        "page",
        "chrono",
        "show",
        "pane",
        "prevHeight",
        "sc",
        "estTotal",
    }
)
_BANNER_SINKS = frozenset(
    {
        "showErr",
        "onError",
        "friendly",
        "String",
        "Error",
        "console",
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "function",
        "return",
        "typeof",
        "new",
        "await",
        "void",
        "Promise",
    }
)
_DOCS_205_RETRY = re.compile(r"error.{0,40}retry|retry.{0,40}error", re.I | re.S)


def _ipc_catch_bodies(src: str, fn_name: str, ipc_needles: tuple[str, ...]) -> list[str]:
    """Catch bodies whose try (or a callee try) mentions one of the IPC names."""
    body = _ident_body(src, fn_name)
    if not body:
        return []
    found: list[str] = []
    for try_body, catch_body in _try_catch_blocks(body):
        if any(needle in try_body for needle in ipc_needles):
            found.append(catch_body)
    if found:
        return found
    # One level of helpers (loadTimeline / runSearch / …).
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", body):
        callee = m.group(1)
        if callee in _BANNER_SINKS or callee == fn_name:
            continue
        nested = _ident_body(src, callee)
        if not nested:
            continue
        for try_body, catch_body in _try_catch_blocks(nested):
            if any(needle in try_body for needle in ipc_needles):
                found.append(catch_body)
    return found


def _pane_catch_dumps_banner(catch: str) -> bool:
    """True if the catch writes the App banner (showErr / onError / err =)."""
    if _assigns_err_banner(catch):
        return True
    return bool(_ONERROR_CALL.search(catch))


def _catch_error_flags(src: str, catch: str, seen: set[str] | None = None) -> set[str]:
    """Idents assigned in catch that can gate an in-pane Error+Retry."""
    found = seen if seen is not None else set()
    flags: set[str] = set()
    for ident in _assigned_idents(catch):
        if ident not in _PANE_CATCH_NOISE:
            flags.add(ident)
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", catch):
        name = m.group(1)
        if name in _BANNER_SINKS or name in found:
            continue
        found.add(name)
        nested = _ident_body(src, name)
        if nested:
            flags |= _catch_error_flags(src, nested, found)
    return flags


def _cond_negates_flag(cond: str, flags: set[str]) -> bool:
    for f in flags:
        if re.search(rf"!\s*(?:[\w$]+(?:\?\.|\.))*{re.escape(f)}\b", cond):
            return True
        if re.search(
            rf"\b(?:[\w$]+(?:\?\.|\.))*{re.escape(f)}\s*"
            r"(?:===?|==)\s*(?:null|undefined|false|[\"']{2})",
            cond,
        ):
            return True
    return False


def _attr_brace_expr(block: str, names: tuple[str, ...]) -> str:
    for name in names:
        m = re.search(rf"\b{re.escape(name)}\s*=\s*\{{", block)
        if not m:
            continue
        open_i = m.end() - 1
        close = _match_closer(block, open_i)
        if close >= 0:
            return block[open_i + 1 : close].strip()
    return ""


def _retry_click_expr(block: str) -> str:
    return _attr_brace_expr(
        block, ("onclick", "on:click", "onAction", "onaction", "onRetry", "onretry")
    )


def _resolve_handler_blob(src: str, expr: str) -> str:
    if not expr:
        return ""
    ident = re.fullmatch(r"(?:async\s+)?([A-Za-z_]\w*)", expr)
    if ident:
        return _ident_body(src, ident.group(1)) or expr
    call = re.fullmatch(r"(?:async\s+)?([A-Za-z_]\w*)\s*\([^)]*\)", expr)
    if call:
        body = _ident_body(src, call.group(1))
        return (body + "\n" + expr) if body else expr
    arrow = re.match(r"(?:async\s*)?(?:\([^)]*\)|[A-Za-z_]\w*)\s*=>\s*\{?", expr)
    if arrow:
        rest = expr[arrow.end() :]
        ident2 = re.match(r"([A-Za-z_]\w*)\s*\(", rest)
        if ident2:
            body = _ident_body(src, ident2.group(1))
            return (body + "\n" + expr) if body else expr
    return expr


def _block_has_retry_copy(block: str, en: str) -> bool:
    if _RETRY_COPY.search(block):
        return True
    for m in re.finditer(r"\bt\s*\(\s*[\"']([^\"']+)[\"']\s*\)", block):
        key = m.group(1)
        if re.search(rf"\b{re.escape(key)}\s*:\s*[\"']Retry[\"']", en):
            return True
    return False

from tauri_gate.status_lib_rest import (
    _block_has_error_copy,
    _partial_bound_to_flags,
    _empty_exclusive_of_partial,
    _interval_retries,
    _catch_auto_retries,
    _effect_auto_retries,
    _docs_205_ok,
    _en_has_retry,
    _early_busy_ipc_status,
    __all__,
)

__all__ = [
    "_PARTIAL_HOOK",
    "_RETRY_COPY",
    "_ERROR_COPY",
    "_ONERROR_CALL",
    "_PARTIAL_MASCOT",
    "_PARTIAL_CDN",
    "_DOCTOR_HEAVY",
    "_AUTO_RETRY_TIMER",
    "_RECURSIVE_RETRY",
    "_SEARCH_FILTER_IDENTS",
    "_PANE_CATCH_NOISE",
    "_BANNER_SINKS",
    "_DOCS_205_RETRY",
    "_ipc_catch_bodies",
    "_pane_catch_dumps_banner",
    "_catch_error_flags",
    "_cond_negates_flag",
    "_attr_brace_expr",
    "_retry_click_expr",
    "_resolve_handler_blob",
    "_block_has_retry_copy",
    "_block_has_error_copy",
    "_partial_bound_to_flags",
    "_empty_exclusive_of_partial",
    "_interval_retries",
    "_catch_auto_retries",
    "_effect_auto_retries",
    "_docs_205_ok",
    "_en_has_retry",
    "_early_busy_ipc_status",
    "annotations",
    "re",
    "Path",
    "fail",
    "_assigned_idents",
    "_call_arg",
    "_chrome_en_text",
    "_cond_uses_flag",
    "_match_closer",
    "_product_svelte",
    "_search_pane_blob",
    "_svelte_markup",
    "_template_stack",
    "_TOAST_SONNER_PKG",
    "_web_logic",
    "_without_comments",
    "_gen_increment_before_ipc",
    "_svelte_if_true_branch",
    "_unguarded_post_ipc_writes",
    "_try_catch_blocks",
    "_hook_element_blocks",
    "_HTTP_CLIENT_PKG",
    "_TOAST_CDN",
    "_assigns_err_banner",
    "_ident_body",
    "_svelte_if_chains",
    "_web_chrome_blob",
    "_first_substr_pos",
    "_typo_docs_blob",
]
