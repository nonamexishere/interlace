"""Continuation of import_doctor_drop."""
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
    _ancestor_tags,
    _APPEARANCE_FETCH,
    _APPEARANCE_MENU_LABEL,
    _APPEARANCE_SCRIM_NAMES,
    _call_arg,
    _contrast_dark_blob,
    _css_var,
    _FETCH_CALL,
    _function_body,
    _match_closer,
    _product_svelte,
    _rust_fn_body,
    _search_pane_blob,
    _STATUS_CONFETTI,
    _STATUS_GRADIENT,
    _STATUS_WARNING_NAMES,
    _tauri_rust_blob,
    _tauri_rust_sources,
    _ts_fn_body,
    _web_logic,
    _web_ts_sources,
    _without_comments,
    CSP,
)

from tauri_gate.contrast_lib import _STATUS_CELEBRATION

from tauri_gate.import_boot_guards import _contrast_light_blob

from tauri_gate.status_toasts_chrome import (
    _APPEARANCE_THEME_UI,
    _contrast_surface_tag,
    _hue_surface,
    _status_hook_blob,
    _windows_around,
)
from tauri_gate.import_doctor_drop import (
    _IMPORT_START_CALL,
    _IMPORT_PANE_PATH_PROP,
)


def _drop_starts_import(crate: Path, surface: str, app: str, import_pane: str) -> bool:
    if _IMPORT_START_CALL.search(surface):
        return True
    if re.search(r"\bstart\s*\(", surface) and _IMPORT_START_CALL.search(import_pane):
        return True
    if _IMPORT_PANE_PATH_PROP.search(app) and _IMPORT_START_CALL.search(import_pane):
        if re.search(
            r"("
            r"droppedPath|dropPath|startPath|importPath|queuedPath|pendingPath"
            r"|\$effect"
            r")",
            import_pane,
        ) and _IMPORT_START_CALL.search(import_pane):
            return True
    return False


# #220 — import progress: Cancel hook + calm done (no thread kill).
# #266 owns enabled Cancel + import_cancel (surgical: this block no
# longer requires disabled / forbids the command / “cannot be stopped”).
_IMPORT_HONEST_COPY = re.compile(
    r"("
    r"cannot stop"
    r"|cannot be stopped"
    r"|no stop"
    r"|cannot be cancelled"
    r"|cannot be canceled"
    r"|not implemented"
    r")",
    re.I,
)
_IMPORT_FAKE_CMD = re.compile(r"\b(?:import_cancel|cancelImport|importCancel)\b")
_IMPORT_THREAD_KILL = re.compile(
    r"("
    r"thread::[^\n]{0,60}\b(?:kill|terminate)\b"
    r"|JoinHandle::[^\n]{0,60}\babort\b"
    r"|\b(?:JoinHandle|join_handle|import_handle)\b[^\n]{0,80}\.abort\s*\("
    r"|\bpthread_kill\b"
    r")"
)
_IMPORT_STATUS_RUNNING = re.compile(
    r"Status[\s\S]{0,160}(?:progress\.status|\brunning\b)",
    re.I,
)
_IMPORT_CONSOLE_PATH = re.compile(
    r"console\.log\s*\((?:[^)]|\n){0,240}(?:\bpath\b|progress\.path|\bprogress\b)",
    re.I,
)
_IMPORT_TOAST_PATH = re.compile(
    r"(?:onToast|toast)\s*\??\s*\((?:[^)]|\n){0,240}(?:\bpath\b|progress\.path)",
    re.I,
)
_IMPORT_PARALLEL = re.compile(
    r"("
    r"parallel[\s_-]*import"
    r"|import[\s_-]*in[\s_-]*parallel"
    r"|concurrent[\s_-]*import"
    r"|data-parallel-import"
    r")",
    re.I,
)
_IMPORT_GC_BTN = re.compile(
    r"("
    r">\s*(?:GC(?:\s+CAS)?|gc_cas|Run GC)\s*<"
    r"|\bgcCas\b"
    r"|\bgc_cas\b"
    r"|background\s+GC"
    r")",
    re.I,
)
_IMPORT_DOCS_PROGRESS = re.compile(
    r"("
    r"progress.{0,40}visible"
    r"|visible.{0,40}progress"
    r"|progress in-window"
    r"|import progress"
    r")",
    re.I | re.S,
)
_IMPORT_DOCS_NO_STOP = re.compile(
    r"("
    r"cannot stop"
    r"|cannot be stopped"
    r"|no stop"
    r"|cannot be cancelled"
    r"|cannot be canceled"
    r"|disabled cancel"
    r"|cancel.{0,80}disabled"
    r"|disabled.{0,80}cancel"
    r")",
    re.I | re.S,
)
_IMPORT_DOCS_QUIET = re.compile(
    r"("
    r"quiet done"
    r"|import done.{0,100}(?:quiet|muted|success)"
    r"|(?:quiet|muted|success).{0,80}import done"
    r")",
    re.I | re.S,
)
_IMPORT_DISABLED = re.compile(
    r"("
    r"(?<![\w-])disabled(?:=\{[^}]*\}|=[\"'][^\"']*[\"'])?(?=[\s/>])"
    r"|aria-disabled\s*=\s*(?:\{true\}|[\"']true[\"'])"
    r")"
)
_IMPORT_DIALOG = re.compile(r"^<(?:Dialog|AlertDialog)\b")
_IMPORT_DESCRIBEDBY = re.compile(
    r"aria-describedby\s*=\s*(?:[\"']([^\"']+)[\"']|\{\s*[\"']([^\"']+)[\"']\s*\})",
    re.I,
)


def _import_describedby_blob(src: str, tag: str) -> str:
    """Text of the element referenced by aria-describedby on the cancel control."""
    m = _IMPORT_DESCRIBEDBY.search(tag)
    if not m:
        return ""
    ident = m.group(1) or m.group(2)
    if not ident:
        return ""
    found = re.search(
        rf"""\bid\s*=\s*(?:["']{re.escape(ident)}["']"""
        rf"""|\{{\s*["']{re.escape(ident)}["']\s*\}})""",
        src,
    )
    if not found:
        return ""
    start = src.rfind("<", 0, found.start() + 1)
    if start < 0:
        start = found.start()
    return src[start : found.end() + 360]


def _import_honest_blob(src: str, tag: str) -> str:
    """Cancel tag + nearby window + described-by target (honest no-stop copy)."""
    return "\n".join(
        (
            tag,
            _status_hook_blob(src, "data-import-cancel"),
            _import_describedby_blob(src, tag),
        )
    )


# #266 — real import cancel (cooperative flag; Cancel enabled while running).
_IMPORT_CANCEL_CMD = _IMPORT_FAKE_CMD
_IMPORT_CANCEL_UNCOND_DISABLED = re.compile(
    r"("
    r"(?<![\w-])disabled(?:=\{true\}|=[\"']true[\"'])?(?=[\s/>])"
    r"|aria-disabled\s*=\s*(?:\{true\}|[\"']true[\"'])"
    r")"
)
_IMPORT_CANCEL_CLICK = re.compile(r"\b(?:onclick|on:click)\s*=")
_IMPORT_CANCEL_API_CALL = re.compile(
    r"("
    r"\bapi\s*\.\s*importCancel\s*\("
    r"|\bapi\s*\.\s*import_cancel\s*\("
    r"|\bapi\s*\.\s*cancelImport\s*\("
    r"|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']import_cancel[\"']"
    r")"
)

__all__ = [
    "_TAURI_DRAG_DROP_API",
    "_TAURI_DRAG_DROP_TYPE",
    "_TAURI_DRAG_DROP_PLUGIN",
    "_HTML_DROP_ATTR",
    "_DROP_EVENT_TYPE",
    "_DROP_PATHS",
    "_IMPORT_START_CALL",
    "_IMPORT_START_KIND_AUTO",
    "_VIEW_IMPORT_ASSIGN",
    "_URL_SCHEME_REJECT",
    "_HTTPS_TOKEN",
    "_HTTP_TOKEN",
    "_SHOW_ERR",
    "_XHR",
    "_DATATRANSFER",
    "_DROP_WALK",
    "_HTTP_CAP",
    "_IMPORT_PANE_PATH_PROP",
    "_DROP_CALL_SKIP",
    "_import_pane_conditionally_mounted",
    "_drop_api_files",
    "_extract_call_callback",
    "_expand_drop_calls",
    "_drop_handler_surface",
    "_drop_rejects_url_scheme",
    "_drop_starts_import",
    "_IMPORT_HONEST_COPY",
    "_IMPORT_FAKE_CMD",
    "_IMPORT_THREAD_KILL",
    "_IMPORT_STATUS_RUNNING",
    "_IMPORT_CONSOLE_PATH",
    "_IMPORT_TOAST_PATH",
    "_IMPORT_PARALLEL",
    "_IMPORT_GC_BTN",
    "_IMPORT_DOCS_PROGRESS",
    "_IMPORT_DOCS_NO_STOP",
    "_IMPORT_DOCS_QUIET",
    "_IMPORT_DISABLED",
    "_IMPORT_DIALOG",
    "_IMPORT_DESCRIBEDBY",
    "_import_describedby_blob",
    "_import_honest_blob",
    "_IMPORT_CANCEL_CMD",
    "_IMPORT_CANCEL_UNCOND_DISABLED",
    "_IMPORT_CANCEL_CLICK",
    "_IMPORT_CANCEL_API_CALL",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_ancestor_tags",
    "_APPEARANCE_FETCH",
    "_APPEARANCE_MENU_LABEL",
    "_APPEARANCE_SCRIM_NAMES",
    "_contrast_dark_blob",
    "_css_var",
    "_FETCH_CALL",
    "_function_body",
    "_product_svelte",
    "_rust_fn_body",
    "_search_pane_blob",
    "_STATUS_CONFETTI",
    "_STATUS_GRADIENT",
    "_STATUS_WARNING_NAMES",
    "_tauri_rust_blob",
    "_ts_fn_body",
    "_web_logic",
    "_without_comments",
    "CSP",
    "_STATUS_CELEBRATION",
    "_contrast_light_blob",
    "_APPEARANCE_THEME_UI",
    "_contrast_surface_tag",
    "_hue_surface",
    "_status_hook_blob",
    "_windows_around",
    "annotations",
    "_call_arg",
    "_match_closer",
    "_tauri_rust_sources",
    "_web_ts_sources",
]

__all__ = [
    "_drop_starts_import",
    "_IMPORT_HONEST_COPY",
    "_IMPORT_FAKE_CMD",
    "_IMPORT_THREAD_KILL",
    "_IMPORT_STATUS_RUNNING",
    "_IMPORT_CONSOLE_PATH",
    "_IMPORT_TOAST_PATH",
    "_IMPORT_PARALLEL",
    "_IMPORT_GC_BTN",
    "_IMPORT_DOCS_PROGRESS",
    "_IMPORT_DOCS_NO_STOP",
    "_IMPORT_DOCS_QUIET",
    "_IMPORT_DISABLED",
    "_IMPORT_DIALOG",
    "_IMPORT_DESCRIBEDBY",
    "_import_describedby_blob",
    "_import_honest_blob",
    "_IMPORT_CANCEL_CMD",
    "_IMPORT_CANCEL_UNCOND_DISABLED",
    "_IMPORT_CANCEL_CLICK",
    "_IMPORT_CANCEL_API_CALL",
    "__all__",
]
