"""Helpers extracted from search_hits.py (search_hits_mark)."""
from __future__ import annotations

from __future__ import annotations
import re
from pathlib import Path
from common import fail, repo_root
from tauri_gate.scan import (
    _function_body,
    _HTML_BODY,
    _matching_each_end,
    _search_pane_blob,
    _svelte_interpolations,
    _svelte_markup,
    _ts_function_body,
    _web_logic,
    _without_comments,
)
from tauri_gate.import_boot_guards import _HUMAN_TIME_HELPERS
from tauri_gate.status_toasts_toast import _short_time_formatter_ok
from tauri_gate.search_hits_jump import (
    _HIT_LOG_JOIN,
)


def _hits_meta_is_five_field_log(hits_each: str) -> bool:
    """True if one interpolation still joins sent_at + platform + kind."""
    for expr in _svelte_interpolations(hits_each):
        has_sent = bool(re.search(r"\bsent_at\b", expr))
        has_plat = bool(re.search(r"\bplatform\b", expr))
        has_kind = bool(re.search(r"\bconversation_kind\b", expr))
        if has_sent and has_plat and has_kind:
            return True
        if _HIT_LOG_JOIN.search(expr) and has_plat and has_kind:
            return True
    if re.search(
        r"sent_at[\s\S]{0,240}platform[\s\S]{0,240}conversation_kind"
        r"[\s\S]{0,120}\.join\s*\(\s*[\"']\s*·",
        hits_each,
    ):
        return True
    return False

__all__ = [
    "_hits_meta_is_five_field_log",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_function_body",
    "_HTML_BODY",
    "_matching_each_end",
    "_search_pane_blob",
    "_svelte_interpolations",
    "_svelte_markup",
    "_ts_function_body",
    "_web_logic",
    "_without_comments",
    "_HUMAN_TIME_HELPERS",
    "_short_time_formatter_ok",
    "_HIT_LOG_JOIN",
]
