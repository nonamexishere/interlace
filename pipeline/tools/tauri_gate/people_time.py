"""Helpers extracted from people_list.py (people_time)."""
from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _BODY_T_CALL,
    _DATA_PEOPLE_SIDEBAR,
    _PEOPLE_AWAIT_REFRESH,
    _PERSON_PANE_SKIP,
    _call_arg,
    _function_body,
    _match_closer,
    _rust_fn_body,
    _rust_function_body,
    _strip_html_comments,
    _svelte_interpolations,
    _svelte_markup,
    _ts_fn_body,
    _web_logic,
    _web_sources,
    _without_comments,
)

from tauri_gate.a11y_lib import (
    _people_each_block,
    _people_list_a11y_surfaces,
)

from tauri_gate.import_boot_guards import (
    _HUMAN_TIME_HELPERS,
    _people_list_gen,
    _unguarded_post_ipc_writes,
)

from tauri_gate.media_linkify_lib import (
    _MIN_W0,
    _OVERFLOW_X_HIDDEN,
)

from tauri_gate.people_switcher_markup import _people_list_hidden_on_select
from tauri_gate.people_switcher_pretty import _strip_tag_attrs

from tauri_gate.status_toasts_chrome import (
    _PEOPLE_EACH,
    _assignment_gen_guarded,
    _chrome_helper_names,
)
from tauri_gate.status_toasts_toast import (
    _chrome_helper_on_body,
    _people_sidebar_regions,
    _short_time_formatter_ok,
)
from tauri_gate.people_filter import (
    _HUMAN_TIME_CALL,
)


def _people_uses_short_time(people_each: str) -> bool:
    if _HUMAN_TIME_CALL.search(people_each):
        return True
    for expr in _svelte_interpolations(people_each):
        if re.search(r"[A-Za-z_]\w*\s*\([^)]*\blast_activity_at\b", expr):
            return True
    return False

__all__ = [
    "_people_uses_short_time",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_BODY_T_CALL",
    "_DATA_PEOPLE_SIDEBAR",
    "_PEOPLE_AWAIT_REFRESH",
    "_PERSON_PANE_SKIP",
    "_call_arg",
    "_function_body",
    "_match_closer",
    "_rust_fn_body",
    "_rust_function_body",
    "_strip_html_comments",
    "_svelte_interpolations",
    "_svelte_markup",
    "_ts_fn_body",
    "_web_logic",
    "_web_sources",
    "_without_comments",
    "_people_each_block",
    "_people_list_a11y_surfaces",
    "_HUMAN_TIME_HELPERS",
    "_people_list_gen",
    "_unguarded_post_ipc_writes",
    "_MIN_W0",
    "_OVERFLOW_X_HIDDEN",
    "_people_list_hidden_on_select",
    "_strip_tag_attrs",
    "_PEOPLE_EACH",
    "_assignment_gen_guarded",
    "_chrome_helper_names",
    "_chrome_helper_on_body",
    "_people_sidebar_regions",
    "_short_time_formatter_ok",
    "_HUMAN_TIME_CALL",
]
