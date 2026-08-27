"""Helpers extracted from people_switcher_label.py (people_switcher_label_extra2)."""
from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import fail

from tauri_gate.scan import (
    _PERSON_PANE_SKIP,
    _PRETTY_GMAIL,
    _RAW_WHATSAPP,
    _SCROLL_HELPER_SKIP,
    _VOID_HTML,
    _ancestor_tags,
    _assigned_idents,
    _call_arg,
    _cond_uses_flag,
    _function_body,
    _helper_with_callees,
    _js_next,
    _match_closer,
    _matching_each_end,
    _open_tag_before,
    _svelte_markup,
    _tag_name,
    _template_stack,
    _web_sources,
)

from tauri_gate.status_toasts_toast import _person_detail_markup


def _label_helper_falls_back_to_id(blob: str) -> bool:
    return bool(
        re.search(
            r"("
            r"return\s+[^;\n]{0,80}(?:conversation_id|\.id|person_id|personId)\b"
            r"|(?:title|\|\|)\s*[^\n;]{0,80}(?:conversation_id|\.id|person_id|personId)\b"
            r")",
            blob,
        )
    )
_PRETTY_WHATSAPP = re.compile(r"[\"']WhatsApp[\"']")

__all__ = [
    "_label_helper_falls_back_to_id",
    "_PRETTY_WHATSAPP",
    "annotations",
    "re",
    "Path",
    "fail",
    "_PERSON_PANE_SKIP",
    "_PRETTY_GMAIL",
    "_RAW_WHATSAPP",
    "_SCROLL_HELPER_SKIP",
    "_VOID_HTML",
    "_ancestor_tags",
    "_assigned_idents",
    "_call_arg",
    "_cond_uses_flag",
    "_function_body",
    "_helper_with_callees",
    "_js_next",
    "_match_closer",
    "_matching_each_end",
    "_open_tag_before",
    "_svelte_markup",
    "_tag_name",
    "_template_stack",
    "_web_sources",
    "_person_detail_markup",
]
