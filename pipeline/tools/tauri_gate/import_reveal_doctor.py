"""Helpers extracted from import_reveal.py (import_reveal_doctor)."""
from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _ARBITRARY_SHELL,
    _FETCH_CALL,
    _LINKIFY_FETCH,
    _SCROLL_HELPER_SKIP,
    _expand_fn_calls,
    _function_body,
    _js_next,
    _rust_body_with_callees,
    _rust_call_arg,
    _rust_fn_signature,
    _rust_function_body,
    _svelte_markup,
    _tauri_rust_blob,
    _ts_fn_body,
    _ts_function_body,
    _web_logic,
    _without_comments,
)

from tauri_gate.import_boot_setup import (
    _boot_opening_block,
    _element_block_at,
)

from tauri_gate.media_linkify_lib import (
    _PLUGIN_SHELL,
    _SHELL_CAP,
    _hook_element_blocks,
)

from tauri_gate.status_toasts_chrome import (
    _claim_without_negation,
    _invoke_payloads,
    _payload_has_path_or_url,
    _windows_around,
)
from tauri_gate.import_reveal_cmd import (
    _DOCTOR_ISSUE_API,
    _QUICK_DOCTOR,
    _OPEN_AWAIT_SKIP,
    _await_expression,
)


def _doctor_expr_is_quick(expr: str) -> bool:
    return bool(_QUICK_DOCTOR.search(expr))


def _doctor_expr_is_full_scan(expr: str) -> bool:
    if not _DOCTOR_ISSUE_API.search(expr):
        return False
    return not _doctor_expr_is_quick(expr)


def _open_awaited_surface(web: str, roots: tuple[str, ...]) -> str:
    """Bodies of `roots` plus only functions they `await` (not fire-and-forget)."""
    parts: list[str] = []
    seen: set[str] = set()

    def walk(name: str) -> None:
        if name in seen or name in _OPEN_AWAIT_SKIP:
            return
        seen.add(name)
        body = _ts_function_body(web, name) or _function_body(web, name)
        if not body:
            return
        parts.append(body)
        for m in re.finditer(r"\bawait\s+", body):
            expr = _await_expression(body, m.end())
            ident = re.match(r"(?:api\.)?([A-Za-z_]\w*)", expr)
            if ident:
                walk(ident.group(1))

    for root_name in roots:
        walk(root_name)
    return "\n".join(parts)


def _awaited_exprs(src: str) -> list[str]:
    return [_await_expression(src, m.end()) for m in re.finditer(r"\bawait\s+", src)]


def _core_rust_blob(root: Path) -> str:
    src = root / "crates" / "interlace-core" / "src"
    if not src.is_dir():
        return ""
    return "\n".join(p.read_text() for p in sorted(src.rglob("*.rs")) if p.is_file())


def _full_doctor_scan_body(core_src: str, rust: str) -> str:
    """Archive::doctor_issues (full) plus callees — not the quick path."""
    blob = core_src + "\n" + rust
    body = _rust_body_with_callees(blob, "doctor_issues")
    if body.strip():
        return body
    return _rust_function_body(blob, "doctor_issues")

__all__ = [
    "_doctor_expr_is_quick",
    "_doctor_expr_is_full_scan",
    "_open_awaited_surface",
    "_awaited_exprs",
    "_core_rust_blob",
    "_full_doctor_scan_body",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_ARBITRARY_SHELL",
    "_FETCH_CALL",
    "_LINKIFY_FETCH",
    "_SCROLL_HELPER_SKIP",
    "_expand_fn_calls",
    "_function_body",
    "_js_next",
    "_rust_body_with_callees",
    "_rust_call_arg",
    "_rust_fn_signature",
    "_rust_function_body",
    "_svelte_markup",
    "_tauri_rust_blob",
    "_ts_fn_body",
    "_ts_function_body",
    "_web_logic",
    "_without_comments",
    "_boot_opening_block",
    "_element_block_at",
    "_PLUGIN_SHELL",
    "_SHELL_CAP",
    "_hook_element_blocks",
    "_claim_without_negation",
    "_invoke_payloads",
    "_payload_has_path_or_url",
    "_windows_around",
    "_DOCTOR_ISSUE_API",
    "_QUICK_DOCTOR",
    "_OPEN_AWAIT_SKIP",
    "_await_expression",
]
