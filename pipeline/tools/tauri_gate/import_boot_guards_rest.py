"""Continuation of import_boot_guards."""
from __future__ import annotations

from __future__ import annotations

from __future__ import annotations

import re
import html
from pathlib import Path

from common import fail, repo_root

from tauri_gate.scan import (
    _PANE_RESULT_WRITES,
    _PEOPLE_GEN_COUNTER,
    _SPIN_ANIM,
    _first_substr_pos,
    _CHROME_PACK_NS,
    _CONTRAST_DARK_MEDIA,
    _HUE_YELLOW,
    _LS_BRACKET,
    _SANDBOX_137,
    _SPLASH_VIDEO,
    _VOID_HTML,
    _chrome_en_text,
    _css_at_bodies,
    _css_brace_body,
    _expand_fn_calls,
    _function_body,
    _js_next,
    _match_closer,
    _svelte_markup,
    _ts_fn_body,
    _ts_function_body,
    _web_logic,
    _web_sources,
)
from tauri_gate.boot_helpers import (
    _BOOT_IF, _CONTRAST_AT_THEME, _CONTRAST_ROOT, _HUE_BLACK80,
    _HUE_HEX_CSS, _HUE_HEX_TW, _LS_CALL, _SPINNER_BORDER, _SPINNER_RING,
    _empty_state_local_names, _eq_stmt_rhs, _ident_assigned_from_chrome,
    _owned_import_path_rx,
)
from tauri_gate.import_boot_guards import _if_gen_eq_contains


def _assignment_gen_guarded(body: str, pos: int, local: str, counter: str) -> bool:
    return _if_gen_eq_contains(body, pos, local, counter) or _same_block_gen_ne_return(
        body, pos, local, counter
    )


def _markup_uses_chrome_helper(inner: str, helpers: set[str], logic: str = "") -> bool:
    """True if visible copy comes from t()/chrome.x / a derived chrome label."""
    if not inner.strip():
        return False
    ns = set(helpers) | set(_CHROME_PACK_NS)
    for h in helpers:
        if re.search(rf"\b{re.escape(h)}\s*\(", inner):
            return True
        if re.search(rf"\b{re.escape(h)}\.\w+", inner):
            return True
    for n in ns:
        if re.search(rf"\b{re.escape(n)}\.\w+", inner):
            return True
        if re.search(rf"\b{re.escape(n)}\.\w+\s*\(", inner):
            return True
    if re.search(r"\$_\s*\(", inner):
        return True
    for m in re.finditer(r"\{([A-Za-z_]\w*)\}", inner):
        if _ident_assigned_from_chrome(logic, m.group(1), helpers):
            return True
    return False


def _svelte_open_tag_at(src: str, start: int) -> str:
    """Open tag starting at src[start]=='<', aware of quotes and {…}."""
    n = len(src)
    j = start + 1
    q = None
    brace = 0
    while j < n:
        c = src[j]
        if q:
            if c == q:
                q = None
        elif c in "'\"":
            q = c
        elif c == "{":
            brace += 1
        elif c == "}":
            if brace:
                brace -= 1
        elif c == ">" and brace == 0:
            return src[start : j + 1]
        j += 1
    return src[start : start + 480]


def _app_keydown_body(app: str) -> str:
    """App.svelte window keydown handler (onKey or the listen callback)."""
    m = re.search(
        r"addEventListener\s*\(\s*[\"']keydown[\"']\s*,\s*([A-Za-z_][\w]*)",
        app,
    )
    name = m.group(1) if m else "onKey"
    body = _ts_fn_body(app, name) or _function_body(app, name)
    if body:
        return body
    # Anonymous listener: window.addEventListener("keydown", (e) => { ... })
    anon = re.search(
        r"addEventListener\s*\(\s*[\"']keydown[\"']\s*,\s*(?:async\s*)?\([^)]*\)\s*(?::\s*[^{=]+)?=>\s*\{",
        app,
    )
    if anon:
        open_b = app.find("{", anon.end() - 1)
        if open_b >= 0:
            close_b = _match_closer(app, open_b)
            if close_b > open_b:
                return app[open_b + 1 : close_b]
    return ""


def _review_if_return_conds(body: str) -> list[str]:
    """Conditions of `if (...) return` / `if (...) { return }`."""
    out: list[str] = []
    for m in re.finditer(r"\bif\s*\(", body):
        open_p = m.end() - 1
        close_p = _match_closer(body, open_p)
        if close_p < 0:
            continue
        cond = body[open_p + 1 : close_p]
        rest = body[close_p + 1 :].lstrip()
        if rest.startswith("return"):
            out.append(cond)
            continue
        if rest.startswith("{"):
            open_b = body.find("{", close_p)
            if open_b < 0:
                continue
            close_b = _match_closer(body, open_b)
            if close_b > open_b and re.search(
                r"\breturn\b", body[open_b + 1 : close_b]
            ):
                out.append(cond)
    return out


def _unguarded_post_ipc_writes(
    body: str,
    local: str,
    counter: str,
    writes: tuple[str, ...],
    ipc_needles: tuple[str, ...],
) -> list[str]:
    """Write idents assigned after / as the IPC without a current-gen guard."""
    ipc_at = _first_substr_pos(body, ipc_needles)
    if ipc_at < 0:
        return list(writes)
    bad: list[str] = []
    for ident in writes:
        for m in re.finditer(rf"\b{re.escape(ident)}\s*=(?!=)", body):
            pos = m.start()
            eq = body.find("=", pos)
            rhs = _eq_stmt_rhs(body, eq)
            is_post = pos >= ipc_at or bool(re.search(r"\bawait\b", rhs)) or any(
                n in rhs for n in ipc_needles
            )
            if not is_post:
                continue
            if not _assignment_gen_guarded(body, pos, local, counter):
                bad.append(ident)
                break
    return bad


def _same_block_gen_ne_return(body: str, pos: int, local: str, counter: str) -> bool:
    """True if the same block already did `if (local !== counter) return`."""
    enclosing = 0
    i = 0
    while i < pos:
        nxt = _js_next(body, i)
        if nxt != i:
            i = nxt
            continue
        if body[i] == "{":
            close = _match_closer(body, i)
            if close < 0:
                break
            if close >= pos:
                enclosing = i
                i += 1
            else:
                i = close + 1
            continue
        i += 1
    region = body[enclosing:pos]
    return bool(
        re.search(
            rf"if\s*\(\s*(?:{re.escape(local)}\s*!==?\s*{re.escape(counter)}"
            rf"|{re.escape(counter)}\s*!==?\s*{re.escape(local)})\s*\)"
            r"\s*(?:\{\s*)?return\b",
            region,
        )
    )


def _svelte_if_true_branch(src: str, cond: str) -> str:
    """True-branch of the first {#if …cond…} (stops at {:else} / {/if} depth 1)."""
    m = re.search(rf"\{{#if\s+[^}}]*\b{re.escape(cond)}\b[^}}]*\}}", src)
    if not m:
        return ""
    rest = src[m.end() :]
    depth = 1
    i = 0
    while i < len(rest):
        if rest.startswith("{#if", i) or rest.startswith("{#each", i) or rest.startswith(
            "{#await", i
        ) or rest.startswith("{#key", i):
            depth += 1
            i += 3
            continue
        if rest.startswith("{/if}", i) or rest.startswith("{/each}", i) or rest.startswith(
            "{/await}", i
        ) or rest.startswith("{/key}", i):
            depth -= 1
            if depth == 0:
                return src[m.start() : m.end() + i]
            i += 3
            continue
        if depth == 1 and (
            rest.startswith("{:else", i)
            or rest.startswith("{:then", i)
            or rest.startswith("{:catch", i)
        ):
            return src[m.start() : m.end() + i]
        i += 1
    return src[m.start() :]

__all__ = [
    "_PRE_WRAP",
    "_ident_negated",
    "_input_guard_span",
    "_HEIGHT_CACHE",
    "_hue_findings",
    "_people_list_gen",
    "_contrast_light_blob",
    "_if_gen_eq_contains",
    "_gen_increment_before_ipc",
    "_has_css_spinner",
    "_ls_pref_keys",
    "_owned_imported_names",
    "_empty_state_blocks",
    "_HUMAN_TIME_HELPERS",
    "_markup_uses_chrome_helper",
    "_svelte_open_tag_at",
    "_app_keydown_body",
    "_review_if_return_conds",
    "_unguarded_post_ipc_writes",
    "_same_block_gen_ne_return",
    "_svelte_if_true_branch",
    "re",
    "html",
    "Path",
    "fail",
    "repo_root",
    "_SPIN_ANIM",
    "_SANDBOX_137",
    "_SPLASH_VIDEO",
    "_chrome_en_text",
    "_svelte_markup",
    "_web_logic",
    "_web_sources",
    "_CDN_HINT",
    "_NET_IMG",
    "_SERVER_PROGRESS",
    "_SPINNER_NAME",
    "_chrome_helper_names",
    "annotations",
    "_PANE_RESULT_WRITES",
    "_PEOPLE_GEN_COUNTER",
    "_first_substr_pos",
    "_CHROME_PACK_NS",
    "_CONTRAST_DARK_MEDIA",
    "_HUE_YELLOW",
    "_LS_BRACKET",
    "_VOID_HTML",
    "_css_at_bodies",
    "_css_brace_body",
    "_expand_fn_calls",
    "_function_body",
    "_js_next",
    "_match_closer",
    "_ts_fn_body",
    "_ts_function_body",
    "_BOOT_IF",
    "_CONTRAST_AT_THEME",
    "_CONTRAST_ROOT",
    "_HUE_BLACK80",
    "_HUE_HEX_CSS",
    "_HUE_HEX_TW",
    "_LS_CALL",
    "_SPINNER_BORDER",
    "_SPINNER_RING",
    "_empty_state_local_names",
    "_eq_stmt_rhs",
    "_ident_assigned_from_chrome",
    "_owned_import_path_rx",
]

__all__ = [
    "_markup_uses_chrome_helper",
    "_svelte_open_tag_at",
    "_app_keydown_body",
    "_review_if_return_conds",
    "_unguarded_post_ipc_writes",
    "_same_block_gen_ne_return",
    "_svelte_if_true_branch",
    "_assignment_gen_guarded",
]
