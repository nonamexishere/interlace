"""Continuation of status_toasts_chrome."""
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
)
from tauri_gate.import_boot_guards_rest import (
    _same_block_gen_ne_return,
    _svelte_if_true_branch,
    _svelte_open_tag_at,
)
from tauri_gate.status_toasts_hues import _SPINNER_NAME
from tauri_gate.status_toasts_chrome import (
    _NEGATED_SCOPE,
    _chrome_import_names,
    _SKELETON_HOOK,
)
_NET_IMG = re.compile(
    r"("
    r"""(?:src|href)\s*=\s*["']https?://"""
    r"""|url\(\s*['"]?https?://"""
    r"""|<img\b[^>]+https?://"""
    r")",
    re.I,
)
_APPEARANCE_DOCS_NO_THEME = re.compile(
    r"("
    r"no(?: in-app)? Theme(?: / Appearance)? menu"
    r"|without (?:a |an )?Theme menu"
    r"|no Theme / Appearance"
    r"|not (?:a |an )?Theme menu"
    r")",
    re.I,
)


def _claim_without_negation(blob: str, rx: re.Pattern[str]) -> bool:
    for m in rx.finditer(blob):
        window = blob[max(0, m.start() - 48) : m.end() + 48]
        if _NEGATED_SCOPE.search(window):
            continue
        return True
    return False


def _people_inflight_branch(src: str) -> tuple[str, str]:
    """Return (flag, {#if flag} true-branch) for the people-list in-flight window."""
    for flag in ("peopleLoading", "loadingPeople", "peopleBusy"):
        block = _svelte_if_true_branch(src, flag)
        if block:
            return flag, block
    return "", ""


def _status_hook_blob(src: str, hook: str) -> str:
    """Opening-tag ancestors plus a short window around a data-* / text hook."""
    at = src.find(hook)
    if at < 0:
        return ""
    tags = _ancestor_tags(src, at, limit=8)
    window = src[max(0, at - 160) : at + 280]
    return "\n".join(tags) + "\n" + window
_APPEARANCE_DOCS_ARCHIVAL = re.compile(
    r"("
    r"dark.{0,100}(?:intended|archival).{0,60}(?:look|aesthetic)"
    r"|(?:intended|archival).{0,40}(?:look|aesthetic).{0,60}dark"
    r"|dark is the intended"
    r"|intended archival"
    r"|archival look"
    r")",
    re.I | re.S,
)
_CONTRAST_DOCS_SYSTEM = re.compile(
    r"("
    r"system (?:light(?:/| and | / )dark|appearance)"
    r"|follows? system (?:light|dark|appearance)"
    r"|macOS appearance"
    r"|prefers-color-scheme"
    r"|light(?:/| and )dark.{0,80}system"
    r")",
    re.I | re.S,
)


def _skeleton_hook_positions(block: str, owned_names: list[str]) -> list[int]:
    pos: list[int] = []
    for m in _SKELETON_HOOK.finditer(block):
        pos.append(m.start())
    for n in owned_names:
        for m in re.finditer(rf"<{re.escape(n)}(?:\.\w+)?\b", block):
            pos.append(m.start())
    return sorted(set(pos))
_DOCS_TYPO_NO_REMOTE_FONT = re.compile(
    r"("
    r"no remote fonts?"
    r"|not (?:a |an )?remote fonts?"
    r"|system(?:-ui| UI)? fonts?"
    r"|no Google Fonts"
    r"|not.{0,48}(?:Google Fonts|fonts\.googleapis|CDN fonts?|remote fonts?)"
    r")",
    re.I,
)


def _payload_has_path_or_url(payload: str) -> bool:
    return bool(
        re.search(
            r"\b(?:path|url|file|href|uri)\s*:|\b(?:path|url|file|href|uri)\b\s*[,}]",
            payload,
            re.I,
        )
    )
_APPEARANCE_THEME_UI = re.compile(
    r"("
    r"\bdata-theme\b"
    r"|theme-picker"
    r"|themePicker"
    r"|ThemePicker"
    r"|Theme menu"
    r"|Appearance menu"
    r")",
    re.I,
)


def _typo_docs_blob() -> str:
    user_docs = repo_root() / "docs" / "user" / "app.md"
    hack_docs = repo_root() / "docs" / "hacking" / "tauri.md"
    dtxt = ""
    if user_docs.is_file():
        dtxt += user_docs.read_text()
    if hack_docs.is_file():
        dtxt += "\n" + hack_docs.read_text()
    return dtxt
_TYPO_REMOTE_FONT = re.compile(
    r"("
    r"fonts\.googleapis"
    r"|fonts\.gstatic"
    r"|use\.typekit\.net"
    r"|fonts\.adobe"
    r"|@import\s+(?:url\s*\(\s*)?['\"]https?://"
    r"|url\s*\(\s*['\"]?https?://[^)]*(?:font|\.woff2?|\.ttf|\.otf)"
    r")",
    re.I,
)
_THEME_CDN = re.compile(
    r"("
    r"fonts\.googleapis"
    r"|fonts\.gstatic"
    r"|cdn\."
    r"|unpkg\.com"
    r"|jsdelivr"
    r"|@import\s+(?:url\s*\(\s*)?['\"]https?://"
    r")",
    re.I,
)


def _invoke_payloads(web: str, rx: re.Pattern[str]) -> list[str]:
    found: list[str] = []
    for m in rx.finditer(web):
        open_p = web.find("(", m.start())
        if open_p < 0:
            continue
        arg = _call_arg(web, open_p)
        if arg:
            found.append(arg)
    return found


def _chrome_helper_names(logic: str) -> set[str]:
    names = _chrome_import_names(logic)
    for name in _CHROME_HELPER_NAMES:
        if re.search(
            rf"(?:function\s+{re.escape(name)}\s*\("
            rf"|(?:const|let)\s+{re.escape(name)}\s*=\s*(?:async\s*)?(?:function\b|\())",
            logic,
        ):
            names.add(name)
    return names
_SECOND_UI_KIT = re.compile(
    r"[\"']("
    r"@radix-ui(?:/[^\"']*)?"
    r"|shadcn(?:-svelte)?"
    r"|@shadcn(?:/[^\"']*)?"
    r"|@skeletonlabs(?:/[^\"']*)?"
    r"|daisyui"
    r"|flowbite(?:-[a-z]+)?"
    r"|@ark-ui(?:/[^\"']*)?"
    r"|melt-ui"
    r")[\"']",
    re.I,
)

__all__ = [
    "_CONTRAST_HSL",
    "_HM_PART",
    "_MOD_CTRL",
    "_MOD_META",
    "_NEGATED_SCOPE",
    "_PEOPLE_ONLY_RETURN",
    "_SEARCH_EFFECT",
    "_UTC_FMT",
    "_chrome_import_names",
    "_parse_if_chain",
    "_owned_skeleton_names",
    "_SKELETON_HOOK",
    "_hue_surface",
    "_HUE_AMBER",
    "_has_mod_combo",
    "_PEOPLE_EACH",
    "_CONTRAST_COLOR_SCHEME",
    "_cond_code",
    "_assignment_gen_guarded",
    "_first_substr_pos",
    "_WRITE_TEXT",
    "_windows_around",
    "_FOCUS_SEARCH_Q",
    "_KEY_ESC",
    "_MOTION_DURATION_ZERO",
    "_contrast_surface_tag",
    "_hsl_tuple",
    "_toml_keys_in_fn",
    "_MONTH_SHORT",
    "_without_input_guard",
    "_CDN_HINT",
    "_MOTION_JS_REDUCE",
    "_split_people_only",
    "_SERVER_PROGRESS",
    "_NET_IMG",
    "_APPEARANCE_DOCS_NO_THEME",
    "_claim_without_negation",
    "_people_inflight_branch",
    "_status_hook_blob",
    "_APPEARANCE_DOCS_ARCHIVAL",
    "_CONTRAST_DOCS_SYSTEM",
    "_skeleton_hook_positions",
    "_DOCS_TYPO_NO_REMOTE_FONT",
    "_payload_has_path_or_url",
    "_SPINNER_NAME",
    "_APPEARANCE_THEME_UI",
    "_typo_docs_blob",
    "_TYPO_REMOTE_FONT",
    "_THEME_CDN",
    "_invoke_payloads",
    "_chrome_helper_names",
    "_SECOND_UI_KIT",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_open_tag_around",
    "_product_svelte",
    "_SANDBOX_137",
    "_search_pane_blob",
    "_web_logic",
    "_svelte_if_true_branch",
    "annotations",
    "_ancestor_tags",
    "_call_arg",
    "_CHROME_HELPER_NAMES",
    "_CHROME_IMPORT_SPEC",
    "_CHROME_NO_TRANSLATE_FIELDS",
    "_DATA_PEOPLE_SIDEBAR",
    "_function_body",
    "_markup_open_tag",
    "_match_closer",
    "_PERSON_PANE_SKIP",
    "_strip_html_comments",
    "_ts_function_body",
    "_web_sources",
    "_web_ts_sources",
    "_without_comments",
    "_HUMAN_TIME_HELPERS",
    "_if_gen_eq_contains",
    "_input_guard_span",
    "_owned_imported_names",
    "_same_block_gen_ne_return",
    "_svelte_open_tag_at",
]

__all__ = [
    "_NET_IMG",
    "_APPEARANCE_DOCS_NO_THEME",
    "_claim_without_negation",
    "_people_inflight_branch",
    "_status_hook_blob",
    "_APPEARANCE_DOCS_ARCHIVAL",
    "_CONTRAST_DOCS_SYSTEM",
    "_skeleton_hook_positions",
    "_DOCS_TYPO_NO_REMOTE_FONT",
    "_payload_has_path_or_url",
    "_SPINNER_NAME",
    "_APPEARANCE_THEME_UI",
    "_typo_docs_blob",
    "_TYPO_REMOTE_FONT",
    "_THEME_CDN",
    "_invoke_payloads",
    "_chrome_helper_names",
    "_SECOND_UI_KIT",
    "__all__",
]
