"""Continuation of people_filter."""
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
    _PEOPLE_LIST_HEAVY,
    _PEOPLE_WITH_ARCH,
    _PEOPLE_TAKE_ARCH,
    _PEOPLE_AWAIT_API_PEOPLE,
    _PEOPLE_PAGE_API,
    _PEOPLE_VOID_API,
    _PEOPLE_THEN_API,
    _PEOPLE_FIRST_PAINT_ASSIGN,
    _PEOPLE_FIRST_PAINT_PUSH,
    _PEOPLE_REVIEW_DISABLED_LOADING,
    _people_rust_cmd_body,
    _people_expand_rust_calls,
)


def _people_with_arch_wraps_heavy(rust: str, body: str) -> bool:
    """True if a with_arch / with_arch_mut closure (or its callees) runs person_list."""
    for m in _PEOPLE_WITH_ARCH.finditer(body):
        args = _call_arg(body, m.end() - 1)
        if not args:
            continue
        expanded = _people_expand_rust_calls(rust, args)
        if _PEOPLE_LIST_HEAVY.search(expanded):
            return True
    return False


def _people_cmd_takes_archive(rust: str, body: str) -> bool:
    expanded = _people_expand_rust_calls(rust, body)
    return bool(_PEOPLE_TAKE_ARCH.search(expanded))


def _refresh_first_paints_before_full_people(refresh: str) -> bool:
    """True if refreshPeople paints a page / fires-and-forgets before the full list."""
    full = _PEOPLE_AWAIT_API_PEOPLE.search(refresh)
    if not full:
        if _PEOPLE_VOID_API.search(refresh) or _PEOPLE_THEN_API.search(refresh):
            return True
        if _PEOPLE_PAGE_API.search(refresh):
            return True
        return False
    before = refresh[: full.start()]
    if _PEOPLE_FIRST_PAINT_ASSIGN.search(before):
        return True
    if _PEOPLE_FIRST_PAINT_PUSH.search(before):
        return True
    return False


def _apply_status_releases_before_people(apply_st: str) -> bool:
    if _PEOPLE_AWAIT_REFRESH.search(apply_st):
        return False
    return bool(re.search(r"(?:void\s+)?refreshPeople\s*\(", apply_st))


def _people_load_incremental(app: str, logic: str) -> bool:
    src = _without_comments(app + "\n" + logic)
    refresh = _function_body(src, "refreshPeople") or _ts_fn_body(src, "refreshPeople")
    apply_st = _function_body(src, "applyStatus") or _ts_fn_body(src, "applyStatus")
    if refresh and _refresh_first_paints_before_full_people(refresh):
        return True
    if apply_st and _apply_status_releases_before_people(apply_st):
        return True
    return False


def _review_nav_disabled_while_people_loading(app: str) -> bool:
    for m in re.finditer(r"<Button\b[^>]*>", app, re.S):
        tag = m.group(0)
        if "review" not in tag.lower():
            continue
        if _PEOPLE_REVIEW_DISABLED_LOADING.search(tag):
            return True
    return False


def _people_refresh_body(src: str) -> str:
    return _function_body(src, "refreshPeople") or _ts_fn_body(src, "refreshPeople")


def _people_cmd_comment(rust: str) -> str:
    """Comments on `fn people` (leading body + immediately above the fn)."""
    m = re.search(r"(?:pub\s+)?(?:async\s+)?fn\s+people\s*\(", rust)
    if not m:
        return ""
    kept: list[str] = []
    for line in reversed(rust[: m.start()].splitlines()):
        s = line.strip()
        if s == "":
            if kept:
                break
            continue
        if s.startswith("#["):
            continue
        if s.startswith("//") or s.startswith("///") or s.startswith("/*") or s.startswith("*"):
            kept.append(s)
            continue
        break
    header = list(reversed(kept))
    lead: list[str] = []
    for line in _people_rust_cmd_body(rust).splitlines():
        s = line.strip()
        if s == "":
            if lead:
                break
            continue
        if s.startswith("//") or s.startswith("/*") or s.startswith("*"):
            lead.append(s)
            continue
        break
    return "\n".join(header + lead)


def _people_list_on_blob(core: str) -> str:
    """person_list_on / person_list_on_with_groups (+ one hop, not attach)."""
    parts: list[str] = []
    skip = {"attach_identity_values"}
    seen: set[str] = set()
    for name in ("person_list_on", "person_list_on_with_groups"):
        body = _rust_function_body(core, name) or _rust_fn_body(core, name)
        if not body:
            continue
        parts.append(body)
        seen.add(name)
        for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", body):
            callee = m.group(1)
            if callee in seen or callee in skip:
                continue
            seen.add(callee)
            inner = _rust_function_body(core, callee) or _rust_fn_body(core, callee)
            if inner:
                parts.append(inner)
    return "\n".join(parts)
# Selecting / opening a person (existing selectPerson or jump-specific open).
_SELECT_PERSON_CALL = re.compile(
    r"\b(?:"
    r"selectPerson|openPerson|pickPerson|showPerson|loadPerson|"
    r"openPersonAtMessage|selectPersonAtMessage|jumpToPersonMessage"
    r")\s*\(",
    re.I,
)
_HUMAN_TIME_CALL = re.compile(
    r"\b(?:" + "|".join(_HUMAN_TIME_HELPERS) + r")\s*\("
)
_DATE_PICKER = re.compile(
    r"("
    r"\bDatePicker\b"
    r"|date-picker"
    r"|datepicker"
    r"|flatpickr"
    r"|litepicker"
    r"|air-datepicker"
    r"|type\s*=\s*[\"']date[\"']"
    r"|type\s*=\s*[\"']datetime-local[\"']"
    r")",
    re.I,
)


def _interp_dumps_iso_activity(expr: str) -> bool:
    """True if last_activity_at is stringified (raw T…Z), not passed to a formatter."""
    if not re.search(r"\blast_activity_at\b", expr):
        return False
    if re.search(r"[A-Za-z_]\w*\s*\([^)]*\blast_activity_at\b", expr):
        return False
    # Truthiness for a separator (`p.last_activity_at && p.preview ? " · " : ""`).
    if re.search(r"last_activity_at\s*&&", expr) and not re.search(
        r"last_activity_at\s*(?:\?\?|\|\|)", expr
    ):
        return False
    return True


def _attr_brace_values(src: str, attr: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(rf"{re.escape(attr)}\s*=\s*\{{", src, re.I):
        start = m.end() - 1
        end = _match_closer(src, start)
        if end > start:
            out.append(src[start + 1 : end])
    return out

__all__ = [
    "_OVERFLOW_Y_SCROLL",
    "_OVERFLOW_X_VISIBLE",
    "_TRUNCATE_TOKENS",
    "_PEOPLE_NAME",
    "_PEOPLE_PREVIEW",
    "_PEOPLE_ID_VISIBLE",
    "_PEOPLE_ID_FALLBACK",
    "_SCROLL_AREA_TAG",
    "_scroll_area_source",
    "_region_overflow_ok",
    "_row_clips_long_text",
    "_PEOPLE_FILTER_IDENTITY_TOKENS",
    "_PEOPLE_FILTER_IDENTITIES_FIELD",
    "_PEOPLE_FILTER_SKIP_CALLS",
    "_people_filter_window",
    "_PEOPLE_LIST_HEAVY",
    "_PEOPLE_WITH_ARCH",
    "_PEOPLE_TAKE_ARCH",
    "_PEOPLE_AWAIT_API_PEOPLE",
    "_PEOPLE_AWAIT_ONCHANGED",
    "_PEOPLE_PAGE_API",
    "_PEOPLE_VOID_API",
    "_PEOPLE_THEN_API",
    "_PEOPLE_FIRST_PAINT_ASSIGN",
    "_PEOPLE_FIRST_PAINT_PUSH",
    "_PEOPLE_REVIEW_DISABLED_LOADING",
    "_PEOPLE_ASSIGN_AWAIT",
    "_PEOPLE_LOADING_FALSE",
    "_PEOPLE_BARE_OPEN",
    "_PEOPLE_OPEN_READONLY",
    "_PEOPLE_OPEN_FLAGS",
    "_PEOPLE_READ_ONLY",
    "_PEOPLE_QUERY_ONLY",
    "_PEOPLE_SNAPSHOT_TX",
    "_PEOPLE_COMMENT_ISSUE",
    "_PEOPLE_COMMENT_FLOCK",
    "_PEOPLE_COMMENT_TAKE",
    "_people_rust_cmd_body",
    "_people_expand_rust_calls",
    "_people_with_arch_wraps_heavy",
    "_people_cmd_takes_archive",
    "_refresh_first_paints_before_full_people",
    "_apply_status_releases_before_people",
    "_people_load_incremental",
    "_review_nav_disabled_while_people_loading",
    "_people_refresh_body",
    "_people_cmd_comment",
    "_people_list_on_blob",
    "_SELECT_PERSON_CALL",
    "_HUMAN_TIME_CALL",
    "_DATE_PICKER",
    "_interp_dumps_iso_activity",
    "_attr_brace_values",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_BODY_T_CALL",
    "_PERSON_PANE_SKIP",
    "_function_body",
    "_strip_html_comments",
    "_svelte_interpolations",
    "_svelte_markup",
    "_ts_fn_body",
    "_web_logic",
    "_web_sources",
    "_without_comments",
    "_people_each_block",
    "_people_list_a11y_surfaces",
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
    "annotations",
    "_DATA_PEOPLE_SIDEBAR",
    "_PEOPLE_AWAIT_REFRESH",
    "_call_arg",
    "_match_closer",
    "_rust_fn_body",
    "_rust_function_body",
    "_HUMAN_TIME_HELPERS",
]

__all__ = [
    "_people_with_arch_wraps_heavy",
    "_people_cmd_takes_archive",
    "_refresh_first_paints_before_full_people",
    "_apply_status_releases_before_people",
    "_people_load_incremental",
    "_review_nav_disabled_while_people_loading",
    "_people_refresh_body",
    "_people_cmd_comment",
    "_people_list_on_blob",
    "_SELECT_PERSON_CALL",
    "_HUMAN_TIME_CALL",
    "_DATE_PICKER",
    "_interp_dumps_iso_activity",
    "_attr_brace_values",
    "__all__",
]
