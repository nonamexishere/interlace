"""Helpers extracted from status_toasts.py (status_toasts_extra2)."""
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
    _call_arg,
    _CHROME_HELPER_NAMES,
    _CHROME_IMPORT_SPEC,
    _CHROME_NO_TRANSLATE_FIELDS,
    _DATA_PEOPLE_SIDEBAR,
    _function_body,
    _markup_open_tag,
    _match_closer,
    _open_tag_around,
    _PERSON_PANE_SKIP,
    _product_svelte,
    _SANDBOX_137,
    _search_pane_blob,
    _strip_html_comments,
    _ts_function_body,
    _web_logic,
    _web_sources,
    _web_ts_sources,
    _without_comments,
)

from tauri_gate.import_boot_guards import (
    _HUMAN_TIME_HELPERS,
    _if_gen_eq_contains,
    _input_guard_span,
    _owned_imported_names,
    _same_block_gen_ne_return,
    _svelte_if_true_branch,
    _svelte_open_tag_at,
)
from tauri_gate.status_toasts_chrome import (
    _WRITE_TEXT,
    _windows_around,
)
from tauri_gate.status_toasts_toast import (
    _ident_body,
)


def _copy_fail_blob(crate: Path) -> str:
    app_path = crate / "web" / "App.svelte"
    app = _web_logic(crate) if app_path.is_file() else ""
    web = _web_logic(crate)
    parts: list[str] = []
    for src in (app, web):
        body = _ident_body(src, "copyText")
        if body:
            parts.append(body)
            break
    parts.append(_windows_around(web, _WRITE_TEXT, before=80, after=200))
    hop = "\n".join(parts)
    if re.search(r"\bonCopyFail\b", hop):
        parts.append(
            _windows_around(web, re.compile(r"\bonCopyFail\b"), before=20, after=80)
        )
        for src in (app, web):
            body = _ident_body(src, "onCopyFail")
            if body:
                parts.append(body)
    if re.search(r"\bshowErr\b", "\n".join(parts)):
        parts.append(_ident_body(app, "showErr"))
    return "\n".join(parts)


def _toast_args_include_body(blob: str) -> bool:
    for m in re.finditer(
        r"\b(?:toast|showToast|pushToast|addToast|notifyToast|toastError|toastFail)\s*\(",
        blob,
    ):
        arg = _call_arg(blob, m.end() - 1)
        if re.search(r"body_text|copyMenu\.body_text|copyMenu\.text\b|displayBody\s*\(", arg):
            return True
    return False

__all__ = [
    "_copy_fail_blob",
    "_toast_args_include_body",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_ancestor_tags",
    "_call_arg",
    "_CHROME_HELPER_NAMES",
    "_CHROME_IMPORT_SPEC",
    "_CHROME_NO_TRANSLATE_FIELDS",
    "_DATA_PEOPLE_SIDEBAR",
    "_function_body",
    "_markup_open_tag",
    "_match_closer",
    "_open_tag_around",
    "_PERSON_PANE_SKIP",
    "_product_svelte",
    "_SANDBOX_137",
    "_search_pane_blob",
    "_strip_html_comments",
    "_ts_function_body",
    "_web_logic",
    "_web_sources",
    "_web_ts_sources",
    "_without_comments",
    "_HUMAN_TIME_HELPERS",
    "_if_gen_eq_contains",
    "_input_guard_span",
    "_owned_imported_names",
    "_same_block_gen_ne_return",
    "_svelte_if_true_branch",
    "_svelte_open_tag_at",
    "_WRITE_TEXT",
    "_windows_around",
    "_ident_body",
]
