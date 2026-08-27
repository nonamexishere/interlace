"""Helpers extracted from import_doctor.py (import_doctor_cancel)."""
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
_IMPORT_CANCEL_FLAG = re.compile(
    r"("
    r"\bAtomicBool\b"
    r"|\bImportCancel\b"
    r"|\bcancel\s*:"
    r"|\bis_cancelled\b"
    r"|\bis_canceled\b"
    r")"
)
_IMPORT_TICK_INTERRUPTED = re.compile(
    r"("
    r"""status\s*===\s*["']interrupted["']"""
    r"""|["']interrupted["']\s*===\s*[\w.]*status"""
    r"""|\.includes\s*\(\s*["']interrupted["']"""
    r"""|["']interrupted["']"""
    r")",
)
_IMPORT_DOCS_STOPS = re.compile(
    r"cancel.{0,120}stop",
    re.I | re.S,
)
_IMPORT_SELF_PROBE = re.compile(r"self\s*\.\s*probe\s*\(")
_IMPORT_CANCEL_WORD = re.compile(r"\b(?:Cancelled|is_cancelled|is_canceled)\b")
_IMPORT_STOPS_AFTER_FILE = re.compile(r"Stops after this file")
_IMPORT_AFTER_THIS_FILE = re.compile(r"after this file", re.I)
_IMPORT_CANCEL_OPEN = re.compile(r"\bopen\b", re.I)


def _import_fn_checks_cancel(src: str, name: str) -> bool:
    """`fn name(..., cancel...)` body mentions Cancelled / is_cancelled."""
    if not re.search(rf"fn\s+{re.escape(name)}\s*\([^)]*\bcancel\b", src, re.S):
        return False
    body = _rust_fn_body(src, name)
    return bool(body and _IMPORT_CANCEL_WORD.search(body))


_UPSERT_UPDATE_BLAKE3 = re.compile(
    r"UPDATE\s+sources\b[\s\S]{0,500}\bfile_blake3\b",
    re.I,
)
_UPSERT_SELECT_BLAKE3 = re.compile(r"SELECT\b[^;]{0,200}file_blake3", re.I)
_UPSERT_SELECT_ORIGIN = re.compile(r"SELECT\b[^;]{0,200}origin_path", re.I)


def _upsert_origin_fallback_or_hash_update(upsert: str, abort: str) -> bool:
    """Reuse a hashless sources row: UPDATE file_blake3, or origin_path after a blake3 miss."""
    blob = f"{upsert}\n{abort}"
    if _UPSERT_UPDATE_BLAKE3.search(blob):
        return True
    blake3_sel = _UPSERT_SELECT_BLAKE3.search(upsert)
    if not blake3_sel:
        return False
    for origin_sel in _UPSERT_SELECT_ORIGIN.finditer(upsert):
        if origin_sel.start() <= blake3_sel.start():
            continue
        between = upsert[blake3_sel.end() : origin_sel.start()]
        if "else" not in between:
            return True
    return False


def _wa_media_zip_match_body(wa: str) -> str:
    """`match read_zip_entry_capped(...) { ... }` body (media read, not fn def)."""
    m = re.search(r"match\s+read_zip_entry_capped\s*\(", wa)
    if not m:
        return ""
    paren = wa.find("(", m.start())
    if paren < 0:
        return ""
    close_paren = _match_closer(wa, paren)
    if close_paren < 0:
        return ""
    brace = wa.find("{", close_paren)
    if brace < 0:
        return ""
    close_b = _match_closer(wa, brace)
    if close_b < 0:
        return wa[brace + 1 :]
    return wa[brace + 1 : close_b]


def _whatsapp_blob(root: Path) -> str:
    """whatsapp.rs facade plus import/whatsapp/*.rs siblings."""
    wa = root / "crates" / "interlace-core" / "src" / "import" / "whatsapp.rs"
    parts = [wa.read_text()] if wa.is_file() else []
    sib = wa.parent / "whatsapp"
    if sib.is_dir():
        parts.extend(p.read_text() for p in sorted(sib.glob("*.rs")))
    return "\n".join(parts)


def _import_cancel_struct_docs(model: str) -> str:
    """Rustdoc / attributes immediately above `pub struct ImportCancel`."""
    m = re.search(r"pub struct ImportCancel\b", model)
    if not m:
        return ""
    docs: list[str] = []
    for line in reversed(model[: m.start()].splitlines()):
        s = line.strip()
        if (
            s.startswith("///")
            or s.startswith("//!")
            or s.startswith("//")
            or s.startswith("#[")
            or not s
        ):
            docs.append(line)
            continue
        break
    docs.reverse()
    return "\n".join(docs)

__all__ = [
    "_IMPORT_CANCEL_FLAG",
    "_IMPORT_TICK_INTERRUPTED",
    "_IMPORT_DOCS_STOPS",
    "_IMPORT_SELF_PROBE",
    "_IMPORT_CANCEL_WORD",
    "_IMPORT_STOPS_AFTER_FILE",
    "_IMPORT_AFTER_THIS_FILE",
    "_IMPORT_CANCEL_OPEN",
    "_import_fn_checks_cancel",
    "_UPSERT_UPDATE_BLAKE3",
    "_UPSERT_SELECT_BLAKE3",
    "_UPSERT_SELECT_ORIGIN",
    "_upsert_origin_fallback_or_hash_update",
    "_wa_media_zip_match_body",
    "_whatsapp_blob",
    "_import_cancel_struct_docs",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_ancestor_tags",
    "_APPEARANCE_FETCH",
    "_APPEARANCE_MENU_LABEL",
    "_APPEARANCE_SCRIM_NAMES",
    "_call_arg",
    "_contrast_dark_blob",
    "_css_var",
    "_FETCH_CALL",
    "_function_body",
    "_match_closer",
    "_product_svelte",
    "_rust_fn_body",
    "_search_pane_blob",
    "_STATUS_CONFETTI",
    "_STATUS_GRADIENT",
    "_STATUS_WARNING_NAMES",
    "_tauri_rust_blob",
    "_tauri_rust_sources",
    "_ts_fn_body",
    "_web_logic",
    "_web_ts_sources",
    "_without_comments",
    "CSP",
    "_STATUS_CELEBRATION",
    "_contrast_light_blob",
    "_APPEARANCE_THEME_UI",
    "_contrast_surface_tag",
    "_hue_surface",
    "_status_hook_blob",
    "_windows_around",
]
