"""Continuation of primitives_lib."""
from __future__ import annotations

from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import fail

from tauri_gate.scan import (
    _BODY_T_CALL,
    _chrome_en_text,
    _CMD_PALETTE_PKG,
    _function_body,
    _HUE_YELLOW,
    _product_svelte,
    _search_pane_blob,
    _SPLASH_VIDEO,
    _svelte_markup,
    _template_stack,
    _timeline_block,
    _TOAST_SONNER_PKG,
    _web_logic,
    _web_sources,
)

from tauri_gate.a11y_lib import (
    _SPIN_ANIM,
    _css_prefers_reduced_blocks,
)

from tauri_gate.design_lib import (
    _EMPTY_MASCOT,
    _lucide_attr_block,
    _lucide_surface,
)

from tauri_gate.import_boot_setup import _boot_opening_block
from tauri_gate.import_boot_guards import (
    _empty_state_blocks,
    _has_css_spinner,
    _ident_negated,
    _owned_imported_names,
    _svelte_if_true_branch,
)

from tauri_gate.status_toasts_chrome import (
    _CDN_HINT,
    _HUE_AMBER,
    _NET_IMG,
    _SECOND_UI_KIT,
    _SERVER_PROGRESS,
    _SKELETON_HOOK,
    _SPINNER_NAME,
    _cond_code,
    _owned_skeleton_names,
    _people_inflight_branch,
    _skeleton_hook_positions,
    _typo_docs_blob,
)
from tauri_gate.status_toasts_toast import (
    _people_sidebar_regions,
    _web_chrome_blob,
)


def _docs_203_surfaces(dtxt: str) -> bool:
    for m in re.finditer(r"\bskeleton\b", dtxt, re.I):
        win = dtxt[max(0, m.start() - 220) : m.end() + 220]
        if (
            re.search(r"\bpeople\b", win, re.I)
            and re.search(r"\btimeline\b", win, re.I)
            and re.search(r"\bsearch\b", win, re.I)
        ):
            return True
    return False


# #203 follow-up — Load older must not mount the timeline skeleton; in-flight audible.
_APPEND_IDENT = re.compile(
    r"\b(tlAppending|isAppending|appending|tlAppend|appendFlag|appendMode|"
    r"loadingOlder|loadOlder|tlLoadOlder|olderLoading|isAppend|append)\b"
)
_REPLACE_IDENT = re.compile(
    r"\b(tlReplacing|isReplacing|replacing|tlReplace|fullReplace|isReplace)\b"
)
_LOAD_OLDER_SELECT_APPEND = re.compile(
    r"selectPerson\s*\(\s*[^,)]+\s*,\s*true\s*[,)]"
)


def _cond_hides_skeleton_on_append(cond: str) -> bool:
    """True if this {#if} is false while Load older / append is in flight."""
    code = _cond_code(cond)
    for ident in _APPEND_IDENT.findall(code):
        if _ident_negated(code, ident):
            return True
    for ident in _REPLACE_IDENT.findall(code):
        if not _ident_negated(code, ident):
            return True
    return False


def _cond_shows_skeleton_on_append(cond: str) -> bool:
    code = _cond_code(cond)
    for ident in _APPEND_IDENT.findall(code):
        if not _ident_negated(code, ident):
            return True
    for ident in _REPLACE_IDENT.findall(code):
        if _ident_negated(code, ident):
            return True
    return False


def _stack_hides_on_append(stack: list[tuple[str, str, str]]) -> bool:
    for kind, cond, _extra in stack:
        if kind == "if" and _cond_hides_skeleton_on_append(cond):
            return True
        if kind == "if-else" and _cond_shows_skeleton_on_append(cond):
            return True
    return False


def _guard_flags(stack: list[tuple[str, str, str]]) -> tuple[list[str], list[str]]:
    append_flags: list[str] = []
    replace_flags: list[str] = []
    for kind, cond, _extra in stack:
        code = _cond_code(cond)
        if kind == "if" and _cond_hides_skeleton_on_append(cond):
            for ident in _APPEND_IDENT.findall(code):
                if _ident_negated(code, ident):
                    append_flags.append(ident)
            for ident in _REPLACE_IDENT.findall(code):
                if not _ident_negated(code, ident):
                    replace_flags.append(ident)
        elif kind == "if-else" and _cond_shows_skeleton_on_append(cond):
            for ident in _APPEND_IDENT.findall(code):
                if not _ident_negated(code, ident):
                    append_flags.append(ident)
            for ident in _REPLACE_IDENT.findall(code):
                if _ident_negated(code, ident):
                    replace_flags.append(ident)
    return append_flags, replace_flags


def _svelte_if_true_branches(src: str, cond: str) -> list[str]:
    found: list[str] = []
    for m in re.finditer(rf"\{{#if\s+[^}}]*\b{re.escape(cond)}\b[^}}]*\}}", src):
        block = _svelte_if_true_branch(src[m.start() :], cond)
        if block:
            found.append(block)
    return found


def _select_person_append_param(src: str) -> str:
    m = re.search(r"(?:async\s+)?function\s+selectPerson\s*\(([^)]*)\)", src)
    if not m:
        return "append"
    params = [p.strip() for p in m.group(1).split(",") if p.strip()]
    if len(params) < 2:
        return "append"
    raw = re.sub(r":[^=]+", "", params[1])
    name = raw.split("=")[0].strip()
    return name or "append"


def _flag_assigned_from_append(fn: str, flag: str, append_param: str) -> bool:
    if re.search(
        rf"\b{re.escape(flag)}\s*=\s*(?:!!|Boolean\s*\(\s*)?{re.escape(append_param)}\b",
        fn,
    ):
        return True
    if re.search(
        rf"if\s*\(\s*{re.escape(append_param)}\s*\)\s*\{{[^}}]{{0,400}}"
        rf"\b{re.escape(flag)}\s*=\s*true",
        fn,
    ):
        return True
    if re.search(
        rf"if\s*\(\s*{re.escape(append_param)}\s*\)\s*{re.escape(flag)}\s*=\s*true",
        fn,
    ):
        return True
    return False


def _flag_cleared_on_append(fn: str, flag: str, append_param: str) -> bool:
    if re.search(rf"\b{re.escape(flag)}\s*=\s*!\s*{re.escape(append_param)}\b", fn):
        return True
    if re.search(
        rf"if\s*\(\s*{re.escape(append_param)}\s*\)[\s\S]{{0,200}}"
        rf"\b{re.escape(flag)}\s*=\s*(?:false|0|null)",
        fn,
    ):
        return True
    return False


def _flag_set_true_in(src: str, flag: str) -> bool:
    return bool(re.search(rf"\b{re.escape(flag)}\s*=\s*true\b", src))


def _open_person_clears_append_flag(src: str, flag: str) -> bool:
    body = _function_body(src, "openPersonAtMessage")
    if not body:
        return True
    if re.search(rf"\b{re.escape(flag)}\s*=\s*(?:false|0|null)", body):
        return True
    if re.search(r"\bselectPerson\s*\(", body):
        return True
    return False

__all__ = [
    "_OWNED_PRIMITIVES_201",
    "_BITS_KIT_CDN",
    "_NETWORK_AVATAR_IMG",
    "_DOCS_OWNED_CHIPS_BANNERS",
    "_DOCS_NOT_ONE_OFF_CHROME",
    "_DIALOG_FOOTER_BLOCK",
    "_owned_tag_match",
    "_owned_used_in",
    "_hook_tag_name",
    "_chip_hook_files",
    "_EMPTY_TITLES_202",
    "_EMPTY_TITLES_202_OPTIONAL_IF_ABSENT",
    "_EMPTY_NEXT_ACTION",
    "_EMPTY_OPTIONAL_ACTION",
    "_EMPTY_GRADIENT",
    "_SKELETON_PKG_202",
    "_DOCS_EMPTY_NEXT_ACTION",
    "_DOCS_EMPTY_NO_MASCOT",
    "_empty_block_title",
    "_empty_usage_has_action",
    "_empty_file",
    "_SKELETON_MUTED_BAR",
    "_SKELETON_ANIM",
    "_SKELETON_JS_SHIMMER",
    "_SKELETON_PKG_203",
    "_SKELETON_SVG_ANIM",
    "_DOCS_203_SKELETON",
    "_DOCS_203_BOOT_STAYS",
    "_DOCS_203_REDUCE_STATIC",
    "_SKELETON_REDUCE_STATIC",
    "_has_skeleton_hook",
    "_skeleton_owned_files",
    "_docs_203_surfaces",
    "_APPEND_IDENT",
    "_REPLACE_IDENT",
    "_LOAD_OLDER_SELECT_APPEND",
    "_cond_hides_skeleton_on_append",
    "_cond_shows_skeleton_on_append",
    "_stack_hides_on_append",
    "_guard_flags",
    "_svelte_if_true_branches",
    "_select_person_append_param",
    "_flag_assigned_from_append",
    "_flag_cleared_on_append",
    "_flag_set_true_in",
    "_open_person_clears_append_flag",
    "re",
    "Path",
    "fail",
    "_BODY_T_CALL",
    "_chrome_en_text",
    "_CMD_PALETTE_PKG",
    "_function_body",
    "_HUE_YELLOW",
    "_product_svelte",
    "_search_pane_blob",
    "_SPLASH_VIDEO",
    "_svelte_markup",
    "_template_stack",
    "_timeline_block",
    "_TOAST_SONNER_PKG",
    "_web_logic",
    "_web_sources",
    "_SPIN_ANIM",
    "_css_prefers_reduced_blocks",
    "_EMPTY_MASCOT",
    "_lucide_attr_block",
    "_lucide_surface",
    "_boot_opening_block",
    "_empty_state_blocks",
    "_has_css_spinner",
    "_owned_imported_names",
    "_svelte_if_true_branch",
    "_CDN_HINT",
    "_HUE_AMBER",
    "_NET_IMG",
    "_SECOND_UI_KIT",
    "_SERVER_PROGRESS",
    "_SKELETON_HOOK",
    "_SPINNER_NAME",
    "_owned_skeleton_names",
    "_people_inflight_branch",
    "_people_sidebar_regions",
    "_skeleton_hook_positions",
    "_typo_docs_blob",
    "_web_chrome_blob",
    "annotations",
    "_ident_negated",
    "_cond_code",
]

__all__ = [
    "_docs_203_surfaces",
    "_APPEND_IDENT",
    "_REPLACE_IDENT",
    "_LOAD_OLDER_SELECT_APPEND",
    "_cond_hides_skeleton_on_append",
    "_cond_shows_skeleton_on_append",
    "_stack_hides_on_append",
    "_guard_flags",
    "_svelte_if_true_branches",
    "_select_person_append_param",
    "_flag_assigned_from_append",
    "_flag_cleared_on_append",
    "_flag_set_true_in",
    "_open_person_clears_append_flag",
    "__all__",
]
