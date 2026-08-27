"""Helpers extracted from import_reveal.py (import_reveal_cmd)."""
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




# #274 — Reveal archive folder in Finder from Doctor / People.
_REVEAL_ARCHIVE_HOOK = re.compile(
    r"data-(?:reveal-archive|reveal-root|reveal-folder|"
    r"reveal-archive-root|archive-reveal)"
)
_REVEAL_ARCHIVE_HOOK_NAMES = (
    "data-reveal-archive",
    "data-reveal-root",
    "data-reveal-folder",
    "data-reveal-archive-root",
    "data-archive-reveal",
)
_REVEAL_ARCHIVE_LABEL = re.compile(
    r"("
    r">\s*Reveal(?:\s+in\s+Finder|\s+archive(?:\s+folder)?)?\s*<"
    r"|t\(\s*[\"']reveal(?:InFinder|Archive|Folder|Root|ArchiveFolder)[\"']\s*\)"
    r"|aria-label\s*=\s*[\"']Reveal(?: in Finder| archive(?: folder)?)?[\"']"
    r")"
)
_REVEAL_ARCHIVE_FN = re.compile(
    r"\b(?:"
    r"revealArchive|revealArchiveRoot|revealRoot|revealFolder|"
    r"revealOpenArchive|onRevealArchive|handleRevealArchive|"
    r"openArchiveInFinder|revealArchiveFolder"
    r")\b"
)
_REVEAL_ARCHIVE_COMPONENT = re.compile(
    r"<Reveal(?:Archive|Folder|Root|ArchiveRoot|ArchiveFolder)\b"
)
_REVEAL_ARCHIVE_CMD_SNAKE = (
    "reveal_archive",
    "reveal_archive_root",
    "reveal_root",
    "reveal_folder",
    "reveal_open_archive",
    "reveal_archive_folder",
)
_REVEAL_ARCHIVE_CAMEL = (
    "revealArchive",
    "revealArchiveRoot",
    "revealRoot",
    "revealFolder",
    "revealOpenArchive",
    "revealArchiveFolder",
)
_REVEAL_ARCHIVE_SKIP_EXTRA = frozenset(
    {
        "App.svelte",
        "DoctorPane.svelte",
        "CasAttach.svelte",
        "SearchPane.svelte",
        "CommandPalette.svelte",
        "ConfirmDialog.svelte",
        "ReviewPane.svelte",
        "ImportPane.svelte",
        "EmptyState.svelte",
        "api.ts",
    }
)
_REVEAL_ARCHIVE_HANDLER_SKIP = frozenset(
    {
        "t",
        "e",
        "event",
        "true",
        "false",
        "void",
        "undefined",
        "null",
        "console",
        "preventDefault",
        "stopPropagation",
        "Button",
        "ask",
    }
)
_REVEAL_ARCHIVE_DOC = re.compile(
    r"("
    r"Reveal(?: in Finder)?(?: the)? archive folder"
    r"|Reveal archive"
    r"|reveal the (?:open )?archive"
    r"|archive folder.{0,80}Finder"
    r"|Finder.{0,80}archive folder"
    r")",
    re.I | re.S,
)
_REVEAL_ARCHIVE_DOC_COPY = re.compile(
    r"("
    r"copy (?:that |the )folder"
    r"|folder is the backup unit"
    r"|copy.{0,80}after (?:you )?clos"
    r"|after (?:you )?clos(?:e|ing).{0,80}(?:app|window)"
    r")",
    re.I | re.S,
)
_REVEAL_ARCHIVE_ENCRYPT = re.compile(
    r"("
    r"database is encrypted"
    r"|your data is encrypted"
    r"|is encrypted at rest"
    r"|SQLCipher"
    r")",
    re.I,
)
_REVEAL_ARCHIVE_UPLOAD = re.compile(r"\bupload\b", re.I)
_REVEAL_ARCHIVE_ZIP_ICLOUD = re.compile(
    r"("
    r"zip[- ]to[- ]icloud"
    r"|icloud[- ](?:drive[- ])?backup"
    r"|backup[- _]zip"
    r"|zip[- _]backup"
    r")",
    re.I,
)
_REVEAL_ARCHIVE_SECOND_CAS = re.compile(
    r"("
    r"second (?:copy of )?CAS"
    r"|duplicate(?:d)? (?:the )?CAS"
    r"|backup_cas|copy_cas|cas_copy"
    r")",
    re.I,
)
_REVEAL_ARCHIVE_BACKUP_FN = re.compile(
    r"\bfn\s+(?:backup|backup_zip|zip_backup|icloud_backup|copy_cas|backup_cas)\b"
)


def _looks_like_reveal_archive(block: str) -> bool:
    if _REVEAL_ARCHIVE_HOOK.search(block):
        return True
    if _REVEAL_ARCHIVE_FN.search(block):
        return True
    if _REVEAL_ARCHIVE_COMPONENT.search(block):
        return True
    return bool(_REVEAL_ARCHIVE_LABEL.search(block))


def _doctor_backup_section(src: str) -> str:
    """Doctor Backup <section> (heading + copy + controls)."""
    markup = _svelte_markup(src)
    i = 0
    while True:
        m = re.search(r"<section\b", markup[i:], re.I)
        if not m:
            break
        start = i + m.start()
        block = _element_block_at(markup, start)
        if re.search(r">\s*Backup\s*<", block) or re.search(
            r"<h[1-6][^>]*>\s*Backup\s*</h[1-6]>", block, re.I
        ):
            return block
        i = start + max(len(block), 1)
    m = re.search(r"<h[1-6][^>]*>\s*Backup\s*</h[1-6]>", markup, re.I)
    if m:
        rest = markup[m.start() :]
        nxt = re.search(r"<h[1-6]\b|<section\b", rest[m.end() - m.start() :])
        if nxt:
            return rest[: m.end() - m.start() + nxt.start()]
        return rest[:2000]
    return _windows_around(markup, re.compile(r"\bBackup\b"), before=40, after=1600)


def _reveal_archive_extra(crate: Path, host: str) -> str:
    """Helpers Doctor / People actually mount. CasAttach Reveal-CAS does not count."""
    web = crate / "web"
    if not web.is_dir():
        return ""
    extra: list[str] = []
    for p in sorted(web.rglob("*")):
        if "node_modules" in p.parts:
            continue
        if p.suffix not in {".svelte", ".ts"}:
            continue
        if p.name in _REVEAL_ARCHIVE_SKIP_EXTRA:
            continue
        text = p.read_text()
        name_hit = bool(re.search(r"revealArchive|RevealArchive|reveal.?root", p.name, re.I))
        hook = bool(
            _REVEAL_ARCHIVE_HOOK.search(text)
            or _REVEAL_ARCHIVE_FN.search(text)
            or _REVEAL_ARCHIVE_COMPONENT.search(text)
        )
        if not name_hit and not hook:
            continue
        stem = p.stem
        if stem in host or re.search(rf"\b{re.escape(stem)}\b|{re.escape(p.name)}", host):
            extra.append(text)
    return "\n".join(extra)


def _reveal_archive_mounted_extra(surface: str, extra: str) -> str:
    """Extra sources the surface actually references (unwired drafts do not count)."""
    if not extra.strip():
        return ""
    # Split on typical Svelte file starts is unreliable; treat as one blob
    # only when the surface names a reveal-archive helper.
    if _REVEAL_ARCHIVE_COMPONENT.search(surface) or _REVEAL_ARCHIVE_FN.search(surface):
        return extra
    for hook in _REVEAL_ARCHIVE_HOOK_NAMES:
        if hook in surface:
            return extra
    return ""


def _people_path_window(app: str) -> str:
    """People sidebar around the shown archive path (st.path)."""
    markup = _svelte_markup(app)
    blocks = _hook_element_blocks(markup, "data-people-sidebar")
    sidebar = "\n".join(blocks) if blocks else markup
    return _windows_around(sidebar, re.compile(r"\{st\.path\}"), before=280, after=560)


def _people_reveal_control_src(app: str, extra: str) -> str:
    markup = _svelte_markup(app)
    extra_m = _svelte_markup(extra) if extra else extra
    blocks = _hook_element_blocks(markup, "data-people-sidebar")
    sidebar = "\n".join(blocks) if blocks else markup
    parts: list[str] = []
    path_win = _people_path_window(app)
    mounted = _reveal_archive_mounted_extra(path_win + "\n" + sidebar, extra_m)
    if _looks_like_reveal_archive(path_win) or _looks_like_reveal_archive(mounted):
        parts.append(path_win)
        if mounted.strip():
            parts.append(mounted)
    for hook in _REVEAL_ARCHIVE_HOOK_NAMES:
        parts.extend(_hook_element_blocks(sidebar, hook))
        if extra:
            parts.extend(_hook_element_blocks(extra, hook))
    if not parts and _looks_like_reveal_archive(sidebar):
        parts.append(sidebar)
    seen: set[str] = set()
    uniq: list[str] = []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            uniq.append(p)
    return "\n".join(uniq)


def _doctor_reveal_control_src(doctor: str, extra: str) -> str:
    section = _doctor_backup_section(doctor)
    extra_m = _svelte_markup(extra) if extra else extra
    mounted = _reveal_archive_mounted_extra(section, extra_m)
    parts: list[str] = []
    if _looks_like_reveal_archive(section) or _looks_like_reveal_archive(mounted):
        parts.append(section)
        if mounted.strip():
            parts.append(mounted)
    for hook in _REVEAL_ARCHIVE_HOOK_NAMES:
        parts.extend(_hook_element_blocks(section, hook))
        if mounted:
            parts.extend(_hook_element_blocks(mounted, hook))
    seen: set[str] = set()
    uniq: list[str] = []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            uniq.append(p)
    return "\n".join(uniq)

from tauri_gate.import_reveal_cmd_rest import (
    _reveal_archive_handler_src,
    _find_reveal_archive_cmd,
    _reveal_archive_cmd_invoke,
    _REVEAL_ARCHIVE_CANON_CMP,
    _REVEAL_ARCHIVE_CANON_BIND,
    _reveal_archive_canon_self_cmp,
    _DOCTOR_ISSUE_API,
    _DOCTOR_RUN_API,
    _QUICK_DOCTOR,
    _GC_ON_OPEN,
    _GC_THREAD,
    _OPEN_AWAIT_SKIP,
    _await_expression,
    __all__,
)

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
]
