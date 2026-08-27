"""Continuation of status_lib."""
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
from tauri_gate.status_lib import (
    _PARTIAL_HOOK,
    _RETRY_COPY,
    _ERROR_COPY,
    _AUTO_RETRY_TIMER,
    _RECURSIVE_RETRY,
    _DOCS_205_RETRY,
    _cond_negates_flag,
)


def _block_has_error_copy(block: str, en: str) -> bool:
    if _ERROR_COPY.search(block):
        return True
    for m in re.finditer(r"\bt\s*\(\s*[\"']([^\"']+)[\"']\s*\)", block):
        key = m.group(1)
        if re.search(rf"\b{re.escape(key)}\s*:\s*[\"'][^\"']*Error[^\"']*[\"']", en):
            return True
    return False


def _partial_bound_to_flags(src: str, block: str, flags: set[str]) -> bool:
    if not flags:
        return False
    if _cond_uses_flag(block, flags):
        return True
    pos = src.find(block[: min(80, len(block))]) if block else -1
    if pos < 0:
        return False
    for kind, cond, _attrs in _template_stack(src, pos):
        if kind == "if" and _cond_uses_flag(cond, flags) and not _cond_negates_flag(
            cond, flags
        ):
            return True
        if kind == "if-else" and _cond_negates_flag(cond, flags):
            return True
    return False


def _empty_exclusive_of_partial(
    src: str, empty_title: str, flags: set[str]
) -> bool:
    """True if EmptyState `empty_title` cannot render with data-partial / fail flag."""
    if empty_title not in src:
        return True
    for chain in _svelte_if_chains(src):
        partial_branches = [b for _c, b in chain if _PARTIAL_HOOK.search(b)]
        empty_branches = [b for _c, b in chain if empty_title in b]
        if empty_branches and partial_branches:
            # Same branch would paint both — not exclusive.
            if any(empty_title in b and _PARTIAL_HOOK.search(b) for _c, b in chain):
                return False
            return True
        if empty_branches:
            for cond, body in chain:
                if empty_title not in body:
                    continue
                if flags and (
                    _cond_negates_flag(cond, flags)
                    or (cond == ":else" and any(_cond_uses_flag(c, flags) for c, _b in chain))
                ):
                    return True
    # Separate {#if}: EmptyState stack must negate the fail flag.
    markup = _svelte_markup(src)
    idx = src.find(empty_title)
    if idx < 0:
        idx = markup.find(empty_title)
        use = markup
    else:
        use = src
    if idx < 0:
        return False
    stack = _template_stack(use, idx)
    if flags and any(
        kind in {"if", "if-else"} and _cond_negates_flag(cond, flags)
        for kind, cond, _a in stack
    ):
        return True
    return False


def _interval_retries(src: str, load_names: tuple[str, ...]) -> bool:
    for m in re.finditer(r"\bsetInterval\s*\(", src):
        arg = _call_arg(src, m.end() - 1)
        if any(re.search(rf"\b{re.escape(n)}\b", arg) for n in load_names):
            return True
    return False


def _catch_auto_retries(catch: str, load_names: tuple[str, ...]) -> bool:
    if _AUTO_RETRY_TIMER.search(catch):
        return True
    if re.search(r"\bsetTimeout\s*\(", catch):
        for m in re.finditer(r"\bsetTimeout\s*\(", catch):
            arg = _call_arg(catch, m.end() - 1)
            if any(re.search(rf"\b{re.escape(n)}\b", arg) for n in load_names):
                return True
    if any(re.search(rf"\b{re.escape(n)}\s*\(", catch) for n in load_names):
        return True
    if _RECURSIVE_RETRY.search(catch):
        return True
    return False


def _effect_auto_retries(src: str, flags: set[str], load_names: tuple[str, ...]) -> bool:
    if not flags:
        return False
    for m in re.finditer(r"\$effect\s*\(", src):
        arg = _call_arg(src, m.end() - 1)
        if _cond_uses_flag(arg, flags) and any(
            re.search(rf"\b{re.escape(n)}\s*\(", arg) for n in load_names
        ):
            return True
    return False


def _docs_205_ok(dtxt: str) -> bool:
    """Failed timeline / search / doctor scan → Error + Retry on that pane; shell stays."""
    if not dtxt.strip():
        return False
    for m in _DOCS_205_RETRY.finditer(dtxt):
        win = dtxt[max(0, m.start() - 280) : m.end() + 280]
        if not re.search(r"\btimeline\b", win, re.I):
            continue
        if not re.search(r"\bsearch\b", win, re.I):
            continue
        if not re.search(r"\bdoctor\b", win, re.I):
            continue
        if not re.search(r"\b(?:pane|shell)\b", win, re.I):
            continue
        if not re.search(r"\b(?:stay|stays|rest)\b", win, re.I):
            continue
        return True
    return False


def _en_has_retry(en: str) -> bool:
    return bool(re.search(r"\bRetry\b", en)) or bool(_RETRY_COPY.search(en))


def _early_busy_ipc_status(body: str, busy: str, ipc_needles: tuple[str, ...]) -> str:
    """Whether `if (busy) return` actually prevents a second IPC.

    ok: return is before the IPC, busy is set true after that if and
    before the IPC, no await between the if and the set.
    incomplete: an `if (busy)` exists before the IPC but does not prove
    a second call cannot start.
    absent: no such if before the IPC.
    """
    ipc_at = _first_substr_pos(body, ipc_needles)
    if ipc_at < 0:
        return "absent"
    prefix = body[:ipc_at]
    m = re.search(
        rf"if\s*\(\s*{re.escape(busy)}(?:\s*===?\s*true)?\s*\)",
        prefix,
    )
    if not m:
        return "absent"
    i = m.end()
    n = len(body)
    while i < n and body[i] in " \t\n\r":
        i += 1
    if i < n and body[i] == "{":
        close = _match_closer(body, i)
        if close < 0 or close > ipc_at:
            return "incomplete"
        block = body[i + 1 : close]
        if not re.search(r"\breturn\b", block):
            return "incomplete"
        if any(needle in block for needle in ipc_needles):
            return "incomplete"
        if_end = close + 1
    elif body.startswith("return", i):
        if_end = i + len("return")
    else:
        return "incomplete"
    after_if = body[if_end:ipc_at]
    set_m = re.search(rf"\b{re.escape(busy)}\s*=\s*true\b", after_if)
    if not set_m:
        return "incomplete"
    if re.search(r"\bawait\b", after_if[: set_m.start()]):
        return "incomplete"
    return "ok"

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
    "re",
    "Path",
    "fail",
    "_chrome_en_text",
    "_product_svelte",
    "_search_pane_blob",
    "_TOAST_SONNER_PKG",
    "_web_logic",
    "_without_comments",
    "_gen_increment_before_ipc",
    "_svelte_if_true_branch",
    "_unguarded_post_ipc_writes",
    "_hook_element_blocks",
    "_HTTP_CLIENT_PKG",
    "_TOAST_CDN",
    "_first_substr_pos",
    "_ident_body",
    "_typo_docs_blob",
    "_web_chrome_blob",
    "annotations",
    "_assigned_idents",
    "_call_arg",
    "_cond_uses_flag",
    "_match_closer",
    "_svelte_markup",
    "_template_stack",
    "_try_catch_blocks",
    "_assigns_err_banner",
    "_svelte_if_chains",
]

__all__ = [
    "_block_has_error_copy",
    "_partial_bound_to_flags",
    "_empty_exclusive_of_partial",
    "_interval_retries",
    "_catch_auto_retries",
    "_effect_auto_retries",
    "_docs_205_ok",
    "_en_has_retry",
    "_early_busy_ipc_status",
    "__all__",
]
