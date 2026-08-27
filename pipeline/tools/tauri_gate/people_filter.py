"""Helpers extracted from people_list.py (people_filter)."""
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



_OVERFLOW_Y_SCROLL = re.compile(
    r"("
    r"overflow-y-(?:auto|scroll)"
    r"|overflow-y\s*:\s*(?:auto|scroll)"
    r"|overflow\s*:\s*auto\b"
    r"|overflow\s*:\s*scroll\b"
    r")",
    re.I,
)
_OVERFLOW_X_VISIBLE = re.compile(
    r"("
    r"overflow-x-(?:auto|scroll|visible)"
    r"|overflow-x\s*:\s*(?:auto|scroll|visible)"
    r")",
    re.I,
)
_TRUNCATE_TOKENS = re.compile(
    r"("
    r"\btruncate\b"
    r"|text-ellipsis"
    r"|text-overflow\s*:\s*ellipsis"
    r"|line-clamp-\d+"
    r"|overflow-hidden"
    r")",
    re.I,
)
_PEOPLE_NAME = re.compile(r"\b(?:display_name|displayName|personName|name)\b")
_PEOPLE_PREVIEW = re.compile(
    r"\b(?:last_activity_at|lastActivityAt|preview|last_at|status)\b"
)
_PEOPLE_ID_VISIBLE = re.compile(
    r"\{[^}]{0,60}(?:\bp\.id\b|\bperson\.id\b|\bfiltered\b[^}]{0,20}\.id)[^}]{0,20}\}"
)
_PEOPLE_ID_FALLBACK = re.compile(
    r"(?:display_name|displayName|name)\s*\|\|\s*[^\n;]{0,60}"
    r"(?:\bp\.id\b|\bperson\.id\b|\.id\b)"
)
_SCROLL_AREA_TAG = re.compile(r"<ScrollArea\b([^>]*)>", re.I | re.S)


def _scroll_area_source(crate: Path) -> str:
    p = crate / "web" / "lib" / "components" / "ui" / "scroll-area" / "scroll-area.svelte"
    return p.read_text() if p.is_file() else ""


def _region_overflow_ok(region: str, scroll_defaults: str) -> bool:
    """True if this people pane (or shared ScrollArea defaults) hide x-scroll."""
    # Explicit overflow-x auto/scroll/visible on the people pane is a fail signal
    # unless a more specific hidden also applies on the same ScrollArea.
    for m in _SCROLL_AREA_TAG.finditer(region):
        attrs = m.group(1)
        if _OVERFLOW_X_VISIBLE.search(attrs) and not _OVERFLOW_X_HIDDEN.search(attrs):
            return False
        if _OVERFLOW_X_HIDDEN.search(attrs) and _OVERFLOW_Y_SCROLL.search(attrs):
            return True
        if _OVERFLOW_X_HIDDEN.search(attrs) and _OVERFLOW_Y_SCROLL.search(scroll_defaults):
            return True
        # ScrollArea with people sidebar + defaults that clip x / allow y.
        if (
            _DATA_PEOPLE_SIDEBAR.search(attrs)
            or "border-r" in attrs
            or "min-w-0" in attrs
        ) and _OVERFLOW_X_HIDDEN.search(scroll_defaults) and _OVERFLOW_Y_SCROLL.search(
            scroll_defaults
        ):
            return True
    if _OVERFLOW_X_HIDDEN.search(region) and _OVERFLOW_Y_SCROLL.search(region):
        return True
    if _OVERFLOW_X_HIDDEN.search(scroll_defaults) and _OVERFLOW_Y_SCROLL.search(
        scroll_defaults
    ):
        # Shared ScrollArea defaults apply when the people pane uses ScrollArea.
        if _SCROLL_AREA_TAG.search(region) or "ScrollArea" in region:
            return True
    return False


def _row_clips_long_text(block: str) -> bool:
    """Names / previews must truncate or otherwise not expand the column."""
    if not block:
        return False
    has_name = bool(_PEOPLE_NAME.search(block))
    has_preview = bool(_PEOPLE_PREVIEW.search(block))
    if not has_name:
        return False
    tokens = _TRUNCATE_TOKENS.findall(block)
    if not tokens:
        return False
    # Name + activity preview both shown → both must clip (two truncate sites,
    # or one shared overflow-hidden/line-clamp wrapper plus another clip).
    if has_preview and len(tokens) < 2:
        return False
    return True


# #138 — people `/` filter: identity values on the loaded list, not display_name only.
_PEOPLE_FILTER_IDENTITY_TOKENS = re.compile(
    r"\b(?:"
    r"identity_values|identityValues|"
    r"filter_haystack|filterHaystack|"
    r"value_normalized|valueNormalized"
    r")\b"
)
# `identities` alone is too broad (person detail chrome). Require a person-field
# access (p.identities / person.identities) or the tokens above.
_PEOPLE_FILTER_IDENTITIES_FIELD = re.compile(
    r"(?:\bp|person|row)\s*\??\.\s*identities\b"
    r"|\bidentities\s*\?\?|\bidentities\s*\|\|"
    r"|\b\.\.\.\s*(?:\bp|person)\s*\??\.\s*identities\b"
)
_PEOPLE_FILTER_SKIP_CALLS = frozenset(
    {
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "function",
        "return",
        "typeof",
        "new",
        "await",
        "void",
        "toLowerCase",
        "toUpperCase",
        "trim",
        "includes",
        "filter",
        "map",
        "join",
        "concat",
        "some",
        "every",
        "find",
        "String",
        "Boolean",
        "Number",
        "Array",
        "Math",
        "parseInt",
        "console",
    }
)


def _people_filter_window(src: str) -> str:
    """Logic for the people sidebar filter (`filtered` derived + named helpers)."""
    m = re.search(
        r"(?:const|let)\s+filtered\s*=\s*\$derived\s*\(",
        src,
    )
    if not m:
        m = re.search(r"(?:const|let)\s+filtered\s*=", src)
    if not m:
        return ""
    window = src[m.start() : m.start() + 1600]
    # Expand small named helpers referenced from the filter expression.
    for call in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", window):
        name = call.group(1)
        if name in _PEOPLE_FILTER_SKIP_CALLS:
            continue
        body = _function_body(src, name)
        if body and len(body) < 4000:
            window += "\n" + body
    return window


# #265 — people list must not hold the archive mutex for the whole heavy scan.
_PEOPLE_LIST_HEAVY = re.compile(
    r"\bperson_list(?:_with_groups|_on|_on_conn|_from_conn|_snapshot)?\s*\("
)
_PEOPLE_WITH_ARCH = re.compile(r"\bwith_arch(?:_mut)?\s*\(")
_PEOPLE_TAKE_ARCH = re.compile(r"\.take\s*\(")
_PEOPLE_AWAIT_API_PEOPLE = re.compile(r"await\s+api\s*\.\s*people\s*\(")
_PEOPLE_AWAIT_ONCHANGED = re.compile(r"await\s+onChanged\s*\(")
_PEOPLE_PAGE_API = re.compile(r"api\s*\.\s*people(?:Page|Roster|Chunk|More)\s*\(")
_PEOPLE_VOID_API = re.compile(r"void\s+api\s*\.\s*people\s*\(")
_PEOPLE_THEN_API = re.compile(r"api\s*\.\s*people\s*\([^)]*\)\s*\.then\s*\(")
_PEOPLE_FIRST_PAINT_ASSIGN = re.compile(
    r"\bpeople\s*=\s*await\s+api\s*\.\s*people(?:Page|Roster|Chunk|More)\s*\("
)
_PEOPLE_FIRST_PAINT_PUSH = re.compile(r"\bpeople\s*\.(?:push|unshift|splice|concat)\s*\(")
_PEOPLE_REVIEW_DISABLED_LOADING = re.compile(
    r"disabled\s*=\s*\{[^}]*peopleLoading",
    re.I,
)
_PEOPLE_ASSIGN_AWAIT = re.compile(
    r"\bpeople\s*=\s*await\s+api\s*\.\s*people\s*\("
)
_PEOPLE_LOADING_FALSE = re.compile(r"\bpeopleLoading\s*=\s*false\b")
_PEOPLE_BARE_OPEN = re.compile(r"(?:rusqlite::)?Connection::open\s*\(")
_PEOPLE_OPEN_READONLY = re.compile(r"\bSQLITE_OPEN_READ_ONLY\b")
_PEOPLE_OPEN_FLAGS = re.compile(r"\bOpenFlags\b")
_PEOPLE_READ_ONLY = re.compile(r"\bREAD_ONLY\b")
_PEOPLE_QUERY_ONLY = re.compile(r"\bquery_only\b", re.I)
_PEOPLE_SNAPSHOT_TX = re.compile(r"unchecked_transaction|\bBEGIN\b", re.I)
_PEOPLE_COMMENT_ISSUE = re.compile(r"#265")
_PEOPLE_COMMENT_FLOCK = re.compile(r"Exclusive flock stays", re.I)
_PEOPLE_COMMENT_TAKE = re.compile(
    r"Do not take\s*\(\s*\)\s*the Archive|import pattern", re.I
)


def _people_rust_cmd_body(rust: str) -> str:
    return _rust_function_body(rust, "people") or _rust_fn_body(rust, "people")


def _people_expand_rust_calls(rust: str, blob: str, depth: int = 2) -> str:
    parts = [blob]
    seen = {"people", "with_arch", "with_arch_mut"}
    skip = {
        "Ok",
        "Err",
        "Some",
        "None",
        "vec",
        "format",
        "serde_json",
        "to_value",
        "json",
        "map_err",
        "clone",
        "lock",
        "as_ref",
        "as_mut",
        "expect",
        "unwrap",
        "from",
        "join",
        "open",
        "if",
        "for",
        "while",
        "match",
        "return",
        "person_list",
        "person_list_with_groups",
        "person_list_on",
    }

    def walk(src: str, left: int) -> None:
        if left <= 0:
            return
        for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", src):
            name = m.group(1)
            if name in seen or name in skip:
                continue
            seen.add(name)
            inner = _rust_function_body(rust, name) or _rust_fn_body(rust, name)
            if not inner:
                continue
            parts.append(inner)
            walk(inner, left - 1)

    walk(blob, depth)
    return "\n".join(parts)

from tauri_gate.people_filter_rest import (
    _people_with_arch_wraps_heavy,
    _people_cmd_takes_archive,
    _refresh_first_paints_before_full_people,
    _apply_status_releases_before_people,
    _people_load_incremental,
    _review_nav_disabled_while_people_loading,
    _people_refresh_body,
    _people_cmd_comment,
    _people_list_on_blob,
    _SELECT_PERSON_CALL,
    _HUMAN_TIME_CALL,
    _DATE_PICKER,
    _interp_dumps_iso_activity,
    _attr_brace_values,
    __all__,
)

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
]
