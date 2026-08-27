"""Parse walkers extracted from scan.py (scan_tokens)."""
from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)
from tauri_gate.scan_parse import (
    _match_closer,
    _open_tag_before,
)


def _matched_inner(markup: str, open_pos: int) -> str:
    m = re.match(r"<([A-Za-z][\w-]*)\b", markup[open_pos:])
    if not m:
        return ""
    name = m.group(1)
    gt = markup.find(">", open_pos)
    if gt < 0:
        return ""
    if markup[gt - 1] == "/":
        return ""
    depth = 1
    rx = re.compile(rf"</?{re.escape(name)}\b", re.I)
    for mm in rx.finditer(markup, gt + 1):
        if mm.group(0).startswith("</"):
            depth -= 1
            if depth == 0:
                return markup[gt + 1 : mm.start()]
        else:
            depth += 1
    return markup[gt + 1 : min(len(markup), gt + 1 + 8000)]


def _rust_fn_body(src: str, name: str) -> str:
    m = re.search(rf"(?:pub\s+)?(?:async\s+)?fn\s+{re.escape(name)}\s*\(", src)
    if not m:
        return ""
    close_paren = _match_closer(src, m.end() - 1)
    if close_paren < 0:
        return ""
    brace = src.find("{", close_paren)
    if brace < 0:
        return ""
    close_b = _match_closer(src, brace)
    if close_b < 0:
        return src[brace + 1 :]
    return src[brace + 1 : close_b]


def _markup_open_tag(src: str, start: int) -> str:
    found = _open_tag_before(src, start + 1)
    return found[1] if found else ""


def _css_brace_body(src: str, open_idx: int) -> str:
    if open_idx < 0 or open_idx >= len(src) or src[open_idx] != "{":
        return ""
    depth = 0
    j = open_idx
    while j < len(src):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[open_idx + 1 : j]
        j += 1
    return ""


def _css_at_bodies(css: str, head: re.Pattern[str]) -> list[str]:
    out: list[str] = []
    for m in head.finditer(css):
        brace = css.find("{", m.start())
        body = _css_brace_body(css, brace)
        if body:
            out.append(body)
    return out
_SANDBOX_137 = re.compile(
    r"macOS blocked that folder\.\s*Use Open existing"
    r"(?:\u2026|\.\.\.|…)\s*once so Interlace can remember it\."
)


# #213 — optional right person inspector (identities + meta, not a second timeline).
_INSPECTOR_HOOK = re.compile(r"\bdata-person-inspector\b")


def _contrast_dark_blob(css: str) -> str:
    return "\n".join(_css_at_bodies(css, _CONTRAST_DARK_MEDIA))


# #218 — appearance follows OS (no Theme menu; named overlay / lightbox scrim).
_APPEARANCE_SCRIM_NAMES = ("--overlay", "--scrim", "--lightbox-scrim")


# #219 — status colors via tokens (warning / optional success; no raw amber).
_STATUS_WARNING_NAMES = ("--warning", "--color-warning")
_ARBITRARY_SHELL = re.compile(
    r"Command::new\s*\(\s*[\"'](?:/bin/sh|/bin/bash|/bin/zsh|/usr/bin/env|sh|bash|zsh|cmd)[\"']"
)
_BODY_T_CALL = re.compile(
    r"\bt\s*\(\s*(?:[\w.$]+\.)?(?:body_text|bodyText|preview|snippet|displayBody)\b"
)
_BUBBLE_ME_VARS = ("--bubble-me", "--color-bubble-me")
_BUBBLE_THEM_VARS = ("--bubble-them", "--color-bubble-them")
_PRETTY_GMAIL = re.compile(r"[\"']Gmail[\"']")
_RAW_WHATSAPP = re.compile(r"[\"']whatsapp[\"']")
_INCLUDE_GROUPS_LABEL = re.compile(r"include groups", re.I)
_DATA_PEOPLE_SIDEBAR = re.compile(r"data-people-sidebar", re.I)
_SPLASH_VIDEO = re.compile(r"<video\b", re.I)
_PEOPLE_AWAIT_REFRESH = re.compile(r"await\s+refreshPeople\s*\(")
_HTML_BODY = re.compile(r"\{@html\b")
_LINKIFY_FETCH = re.compile(r"fetch\s*\(\s*[\"']https?://", re.I)
_MOD_EITHER = re.compile(r"(?:e\.)?(?:metaKey|ctrlKey)")
_VIEW_SEARCH_ASSIGN = re.compile(r"\bview\s*=\s*[\"']search[\"']")
_A11Y_ROLE_OPTION = re.compile(r"\brole\s*=\s*[\"']option[\"']", re.I)
_A11Y_TABINDEX_NEG = re.compile(r"\btabindex\s*=\s*(?:[\"']-1[\"']|\{-1\})", re.I)
_HUE_YELLOW = re.compile(r"\byellow-\d+")
_TYPO_FONT_SANS = re.compile(r"--font-sans\s*:\s*([^;]+);")
_CMD_PALETTE_PKG = re.compile(r"[\"'](?:cmdk|svelte-command(?:-palette)?)[\"']", re.I)
_TOAST_SONNER_PKG = re.compile(r"[\"'](?:sonner|svelte-sonner)[\"']", re.I)
_LS_BRACKET = re.compile(r"localStorage\s*\[\s*[\"']([^\"']+)[\"']\s*\]")
_LAST_PATH_API = re.compile(r"\b(?:write_last_path|read_last_path)\b")
_CONFIG_TOML = re.compile(r"\bconfig\.toml\b")
_PALETTE_HOOK = re.compile(r"\bdata-command-palette\b")
_CONTRAST_SEARCH_MARK_NAMES = ("--search-mark", "--color-search-mark")
_APPEARANCE_MENU_LABEL = re.compile(r"""["'](?:Theme|Appearance)["']""")
_APPEARANCE_FETCH = re.compile(r"\bfetch\s*\(")
_STATUS_GRADIENT = re.compile(r"(?<![\w-])bg-gradient")
_STATUS_CONFETTI = re.compile(r"\bconfetti\b", re.I)

_PEOPLE_GEN_COUNTER = re.compile(r"people|roster|ppl", re.I)

_PANE_RESULT_WRITES = frozenset(
    {
        "searchError",
        "hits",
        "searching",
        "empty",
        "scanError",
        "scanning",
        "issues",
    }
)

def _first_substr_pos(body: str, needles: tuple[str, ...]) -> int:
    found = [body.find(n) for n in needles]
    found = [i for i in found if i >= 0]
    return min(found) if found else -1

_SPIN_ANIM = re.compile(
    r"("
    r"animate-spin\b"
    r"|@keyframes\s+[\w-]*spin[\w-]*"
    r"|animation\s*:\s*[^;\n}]*\bspin\b"
    r"|animation-name\s*:\s*[\w-]*spin[\w-]*"
    r")",
    re.I,
)

_CONTRAST_DARK_MEDIA = re.compile(
    r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)\s*\{",
    re.I,
)

__all__ = [
    "_matched_inner",
    "_rust_fn_body",
    "_markup_open_tag",
    "_css_brace_body",
    "_css_at_bodies",
    "_SANDBOX_137",
    "_INSPECTOR_HOOK",
    "_contrast_dark_blob",
    "_APPEARANCE_SCRIM_NAMES",
    "_STATUS_WARNING_NAMES",
    "_ARBITRARY_SHELL",
    "_BODY_T_CALL",
    "_BUBBLE_ME_VARS",
    "_BUBBLE_THEM_VARS",
    "_PRETTY_GMAIL",
    "_RAW_WHATSAPP",
    "_INCLUDE_GROUPS_LABEL",
    "_DATA_PEOPLE_SIDEBAR",
    "_SPLASH_VIDEO",
    "_PEOPLE_AWAIT_REFRESH",
    "_HTML_BODY",
    "_LINKIFY_FETCH",
    "_MOD_EITHER",
    "_VIEW_SEARCH_ASSIGN",
    "_A11Y_ROLE_OPTION",
    "_A11Y_TABINDEX_NEG",
    "_HUE_YELLOW",
    "_TYPO_FONT_SANS",
    "_CMD_PALETTE_PKG",
    "_TOAST_SONNER_PKG",
    "_LS_BRACKET",
    "_LAST_PATH_API",
    "_CONFIG_TOML",
    "_PALETTE_HOOK",
    "_CONTRAST_SEARCH_MARK_NAMES",
    "_APPEARANCE_MENU_LABEL",
    "_APPEARANCE_FETCH",
    "_STATUS_GRADIENT",
    "_STATUS_CONFETTI",
    "_PEOPLE_GEN_COUNTER",
    "_PANE_RESULT_WRITES",
    "_first_substr_pos",
    "_SPIN_ANIM",
    "_CONTRAST_DARK_MEDIA",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_match_closer",
    "_open_tag_before",
]
