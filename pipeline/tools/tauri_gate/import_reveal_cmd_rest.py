"""Continuation of import_reveal_cmd."""
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
    _REVEAL_ARCHIVE_FN,
    _REVEAL_ARCHIVE_CMD_SNAKE,
    _REVEAL_ARCHIVE_CAMEL,
    _REVEAL_ARCHIVE_HANDLER_SKIP,
)


def _reveal_archive_handler_src(host: str, control: str) -> str:
    names: set[str] = set(_REVEAL_ARCHIVE_FN.findall(host))
    names.update(_REVEAL_ARCHIVE_FN.findall(control))
    for m in re.finditer(r"(?:onclick|on:click)\s*=\s*\{([^}]{0,400})\}", control):
        names.update(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", m.group(1)))
    chunks = [control]
    for name in sorted(names):
        if name in _REVEAL_ARCHIVE_HANDLER_SKIP:
            continue
        fn = (
            _ts_function_body(host, name)
            or _ts_fn_body(host, name)
            or _function_body(host, name)
        )
        if fn:
            chunks.append(fn)
            chunks.append(_expand_fn_calls(host, fn))
    return "\n".join(chunks)


def _find_reveal_archive_cmd(rust: str, web: str) -> str:
    """Rust command that reveals the open archive root (not reveal_cas / open_url)."""
    for name in _REVEAL_ARCHIVE_CMD_SNAKE:
        if re.search(rf"\bfn\s+{re.escape(name)}\b", rust):
            return name
    for camel, snake in zip(_REVEAL_ARCHIVE_CAMEL, _REVEAL_ARCHIVE_CMD_SNAKE, strict=True):
        if re.search(rf"\b{re.escape(camel)}\b", web) and re.search(
            rf"\bfn\s+{re.escape(snake)}\b", rust
        ):
            return snake
    for name in _REVEAL_ARCHIVE_CMD_SNAKE:
        if re.search(
            rf"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']{re.escape(name)}[\"']",
            web,
        ) and re.search(rf"\bfn\s+{re.escape(name)}\b", rust):
            return name
    gh = re.search(r"generate_handler!\s*\[([^\]]*)\]", rust, re.S)
    if not gh:
        return ""
    for name in re.findall(r"\b([a-z][a-z0-9_]*)\b", gh.group(1)):
        if name in {"reveal_cas", "open_url", "cas_data_url"}:
            continue
        body = _rust_function_body(rust, name)
        if not body:
            continue
        if "cas_blob_path" in body:
            continue
        if (
            "/usr/bin/open" in body
            and re.search(r"[\"']-R[\"']", body)
            and re.search(r"\barchive_root\b", body)
        ):
            return name
    return ""


def _reveal_archive_cmd_invoke(cmd: str) -> re.Pattern[str]:
    names = {cmd, _REVEAL_ARCHIVE_CAMEL[_REVEAL_ARCHIVE_CMD_SNAKE.index(cmd)]} if cmd in _REVEAL_ARCHIVE_CMD_SNAKE else {cmd}
    # camelCase of an unknown snake name
    if cmd not in _REVEAL_ARCHIVE_CMD_SNAKE:
        parts = cmd.split("_")
        names.add(parts[0] + "".join(p.title() for p in parts[1:]))
    alt = "|".join(re.escape(n) for n in sorted(names))
    return re.compile(
        r"(?:"
        r"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']" + re.escape(cmd) + r"[\"']"
        r"|api\.(?:" + alt + r")\s*\("
        r")"
    )


_REVEAL_ARCHIVE_CANON_CMP = re.compile(
    r"("
    r"\bcanon\b.{0,40}(?:!=|==).{0,40}\bexpected\b"
    r"|\bexpected\b.{0,40}(?:!=|==).{0,40}\bcanon\b"
    r")"
)
_REVEAL_ARCHIVE_CANON_BIND = re.compile(
    r"\blet\s+(?:mut\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=;]+)?="
    r"\s*[^;]*\bcanonicalize\s*\("
)


def _reveal_archive_canon_self_cmp(body: str) -> bool:
    """True if two canonicalize() results are compared with != / ==."""
    if _REVEAL_ARCHIVE_CANON_CMP.search(body):
        return True
    names: list[str] = []
    seen: set[str] = set()
    for name in _REVEAL_ARCHIVE_CANON_BIND.findall(body):
        if name not in seen:
            seen.add(name)
            names.append(name)
    if len(names) < 2:
        return False
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            if re.search(
                rf"\b{re.escape(a)}\b.{{0,40}}(?:!=|==).{{0,40}}\b{re.escape(b)}\b"
                rf"|\b{re.escape(b)}\b.{{0,40}}(?:!=|==).{{0,40}}\b{re.escape(a)}\b",
                body,
            ):
                return True
    return False


# #136 — defer doctor CAS scan so large archives open fast.
_DOCTOR_ISSUE_API = re.compile(
    r"("
    r"(?:api\.)?doctorIssues\b"
    r"|(?:api\.)?doctor_issues\b"
    r"|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']doctor_issues"
    r")",
)
_DOCTOR_RUN_API = re.compile(r"(?:api\.)?doctorRun\b|doctor_run_cmd|\bdoctor_run\b")
_QUICK_DOCTOR = re.compile(
    r"("
    r"doctorIssuesQuick"
    r"|doctor_issues_quick"
    r"|quick\s*:\s*true"
    r"|mode\s*:\s*[\"']quick[\"']"
    r"|doctorIssues\s*\(\s*true\s*\)"
    r")",
    re.I,
)
_GC_ON_OPEN = re.compile(r"\bgc_cas\b|\bgcCas\s*:\s*true")
_GC_THREAD = re.compile(
    r"("
    r"thread::spawn"
    r"|std::thread"
    r"|Builder::new\s*\(\s*\)\s*\.name\s*\(\s*[\"'][^\"']*gc"
    r")",
    re.I,
)
_OPEN_AWAIT_SKIP = _SCROLL_HELPER_SKIP | {
    "api",
    "invoke",
    "doctorIssues",
    "doctorIssuesQuick",
    "doctorRun",
    "people",
    "linkEvents",
    "status",
    "open",
    "init",
    "pickFolder",
    "rememberedPath",
    "showErr",
    "csv",
    "trim",
}


def _await_expression(src: str, start: int) -> str:
    """Expression after `await` at `start`, up to `;` / newline at depth 0."""
    n = len(src)
    i = start
    while i < n and src[i] in " \t":
        i += 1
    depth = 0
    j = i
    while j < n:
        nxt = _js_next(src, j)
        if nxt != j:
            j = nxt
            continue
        c = src[j]
        if c in "({[":
            depth += 1
        elif c in ")}]":
            if depth == 0:
                break
            depth -= 1
        elif c in ";,\n" and depth == 0:
            break
        j += 1
    return src[i:j].strip()

__all__ = [
    "_REVEAL_ARCHIVE_HOOK",
    "_REVEAL_ARCHIVE_HOOK_NAMES",
    "_REVEAL_ARCHIVE_LABEL",
    "_REVEAL_ARCHIVE_FN",
    "_REVEAL_ARCHIVE_COMPONENT",
    "_REVEAL_ARCHIVE_CMD_SNAKE",
    "_REVEAL_ARCHIVE_CAMEL",
    "_REVEAL_ARCHIVE_SKIP_EXTRA",
    "_REVEAL_ARCHIVE_HANDLER_SKIP",
    "_REVEAL_ARCHIVE_DOC",
    "_REVEAL_ARCHIVE_DOC_COPY",
    "_REVEAL_ARCHIVE_ENCRYPT",
    "_REVEAL_ARCHIVE_UPLOAD",
    "_REVEAL_ARCHIVE_ZIP_ICLOUD",
    "_REVEAL_ARCHIVE_SECOND_CAS",
    "_REVEAL_ARCHIVE_BACKUP_FN",
    "_looks_like_reveal_archive",
    "_doctor_backup_section",
    "_reveal_archive_extra",
    "_reveal_archive_mounted_extra",
    "_people_path_window",
    "_people_reveal_control_src",
    "_doctor_reveal_control_src",
    "_reveal_archive_handler_src",
    "_find_reveal_archive_cmd",
    "_reveal_archive_cmd_invoke",
    "_REVEAL_ARCHIVE_CANON_CMP",
    "_REVEAL_ARCHIVE_CANON_BIND",
    "_reveal_archive_canon_self_cmp",
    "_DOCTOR_ISSUE_API",
    "_DOCTOR_RUN_API",
    "_QUICK_DOCTOR",
    "_GC_ON_OPEN",
    "_GC_THREAD",
    "_OPEN_AWAIT_SKIP",
    "_await_expression",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_ARBITRARY_SHELL",
    "_FETCH_CALL",
    "_LINKIFY_FETCH",
    "_function_body",
    "_rust_body_with_callees",
    "_rust_call_arg",
    "_rust_fn_signature",
    "_rust_function_body",
    "_tauri_rust_blob",
    "_ts_function_body",
    "_web_logic",
    "_without_comments",
    "_boot_opening_block",
    "_PLUGIN_SHELL",
    "_SHELL_CAP",
    "_claim_without_negation",
    "_invoke_payloads",
    "_payload_has_path_or_url",
    "annotations",
    "_SCROLL_HELPER_SKIP",
    "_expand_fn_calls",
    "_js_next",
    "_svelte_markup",
    "_ts_fn_body",
    "_element_block_at",
    "_hook_element_blocks",
    "_windows_around",
]

__all__ = [
    "_reveal_archive_handler_src",
    "_find_reveal_archive_cmd",
    "_reveal_archive_cmd_invoke",
    "_REVEAL_ARCHIVE_CANON_CMP",
    "_REVEAL_ARCHIVE_CANON_BIND",
    "_reveal_archive_canon_self_cmp",
    "_DOCTOR_ISSUE_API",
    "_DOCTOR_RUN_API",
    "_QUICK_DOCTOR",
    "_GC_ON_OPEN",
    "_GC_THREAD",
    "_OPEN_AWAIT_SKIP",
    "_await_expression",
    "__all__",
]
