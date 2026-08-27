"""Helpers extracted from a11y.py (a11y_lib)."""
from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _A11Y_ROLE_OPTION,
    _A11Y_TABINDEX_NEG,
    _ancestor_tags,
    _css_without_comments,
    _markup_open_tag,
    _matching_each_end,
    _open_tag_around,
    _open_tag_before,
    _PERSON_PANE_SKIP,
    _product_svelte,
    _search_pane_blob,
    _strip_html_comments,
    _svelte_markup,
    _tag_name,
    _timeline_block,
    _web_logic,
    _web_sources,
    _without_comments,
    CSP,
)

from tauri_gate.import_boot_setup import _boot_opening_block

from tauri_gate.status_toasts_chrome import _PEOPLE_EACH


_SPIN_ANIM = re.compile(
    r"("
    r"animate-spin\b"
    r"|@keyframes\s+[\w-]*spin[\w-]*"
    r"|animation\s*:\s*[^;\n}]*\bspin\b"
    r"|animation-name\s*:\s*[\w-]*spin[\w-]*"
    r")",
    re.I,
)


def _people_each_block(markup: str) -> str:
    """Innermost {#each filtered …} body for the people list (not switcher)."""
    m = _PEOPLE_EACH.search(markup)
    if not m:
        return ""
    end = _matching_each_end(markup, m.start())
    if end < 0:
        return markup[m.start() :]
    return markup[m.start() : end]


def _people_list_a11y_surfaces(crate: Path) -> tuple[str, str]:
    """Chrome around `{#each filtered}` plus the each body (not SearchPane)."""
    chromes: list[str] = []
    bodies: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        text = p.read_text()
        markup = _strip_html_comments(_svelte_markup(text))
        if not _PEOPLE_EACH.search(markup):
            markup = _strip_html_comments(text)
        for m in _PEOPLE_EACH.finditer(markup):
            end = _matching_each_end(markup, m.start())
            if end < 0:
                end = min(len(markup), m.start() + 1600)
            chromes.append(markup[max(0, m.start() - 700) : end])
            bodies.append(markup[m.start() : end])
    return "\n".join(chromes), "\n".join(bodies)



_A11Y_ROLE_LIST = re.compile(r"\brole\s*=\s*[\"']list[\"']", re.I)
_A11Y_ACTIVEDESC = re.compile(r"\baria-activedescendant\s*=", re.I)
_A11Y_SELECTED = re.compile(r"\baria-selected\s*=", re.I)
_A11Y_SELECTED_STATE = re.compile(
    r"aria-selected\s*=\s*\{[^}]{0,120}"
    r"(?:selectedId|selected_id|selectedPerson|p\.id|person\.id)",
    re.I,
)
_A11Y_ARTICLE = re.compile(r"<article\b|\brole\s*=\s*[\"']article[\"']", re.I)
_A11Y_ARIA_LABEL = re.compile(r"\baria-label(?:ledby)?\s*=", re.I)
_A11Y_FOCUS_VISIBLE = re.compile(
    r"("
    r"focus-visible:(?:ring|outline)"
    r"|:focus-visible\b"
    r")",
    re.I,
)
_A11Y_REDUCED_MOTION = re.compile(
    r"@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)",
    re.I,
)
_A11Y_MOTION_REDUCE_TW = re.compile(r"\bmotion-reduce:", re.I)
_A11Y_ANIM_NONE = re.compile(
    r"("
    r"animation\s*:\s*none\b"
    r"|animation-duration\s*:\s*0(?:s|ms|px)?\b"
    r"|animate-none\b"
    r"|motion-reduce:animate-none\b"
    r")",
    re.I,
)
_A11Y_TRANS_NONE = re.compile(
    r"("
    r"transition\s*:\s*none\b"
    r"|transition-duration\s*:\s*0(?:s|ms)?\b"
    r"|transition-none\b"
    r"|motion-reduce:transition-none\b"
    r")",
    re.I,
)
_A11Y_SCROLL_AUTO = re.compile(
    r"("
    r"scroll-behavior\s*:\s*auto\b"
    r"|scroll-auto\b"
    r"|motion-reduce:scroll-auto\b"
    r")",
    re.I,
)
_A11Y_WCAG_CERT = re.compile(
    r"("
    r"WCAG.{0,80}(?:certificate|certified|conformance\s+certificate)"
    r"|(?:full|complete|official)\s+WCAG\s+(?:2\.[0-2]\s+)?(?:audit\s+)?certificate"
    r"|WCAG\s*2\.[0-2].{0,40}(?:AAA|AA).{0,40}(?:certified|certificate)"
    r"|certified\s+WCAG"
    r")",
    re.I,
)
_A11Y_INERT = re.compile(r"(?:\s|/|\{)\binert\b", re.I)
_A11Y_PERSON_ID_LABEL = re.compile(
    r"aria-label\s*=\s*\{[^}]{0,80}"
    r"(?:person_id|personId|selectedId|\bp\.id\b|\bperson\.id\b|(?:item\.)?row\.id)"
    r"[^}]*\}",
    re.I,
)
_A11Y_NAME_IN_LABEL = re.compile(
    r"aria-label\s*=\s*\{[^}]{0,160}"
    r"(?:display_name|displayName|sent_at|body_text|displayBody|utcTime|subject|preview)"
    r"[^}]*\}",
    re.I,
)


def _css_prefers_reduced_blocks(blob: str) -> list[str]:
    """Bodies of `@media (prefers-reduced-motion: reduce) { … }` (nested braces)."""
    out: list[str] = []
    for m in _A11Y_REDUCED_MOTION.finditer(blob):
        brace = blob.find("{", m.end() - 1)
        if brace < 0:
            continue
        depth = 0
        j = brace
        while j < len(blob):
            c = blob[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    out.append(blob[brace + 1 : j])
                    break
            j += 1
    return out


def _css_focus_visible_for(css: str, tokens: tuple[str, ...]) -> bool:
    """True when a :focus-visible rule's selector mentions one of tokens."""
    for m in re.finditer(r"([^{}@][^{]*)\{([^{}]*)\}", css):
        sel, body = m.group(1), m.group(2)
        if ":focus-visible" not in sel and "focus-visible" not in body:
            continue
        low = sel.lower()
        if any(tok.lower() in low for tok in tokens):
            return True
    return False


# #133 — a11y: people listbox, timeline article/label, focus-visible, reduced motion.
_A11Y_ROLE_LISTBOX = re.compile(r"\brole\s*=\s*[\"']listbox[\"']", re.I)


# #216 — focus rings + ARIA on chrome/dialogs (builds on #133; do not rewrite it).
_OWNED_RING_PRIMITIVES = (
    "web/lib/components/ui/button/button.svelte",
    "web/lib/components/ui/input/input.svelte",
)
_RAW_FOCUS_TAG = re.compile(r"<(button|input|textarea|select|summary)\b")
_HIDDEN_INPUT_TYPE = re.compile(
    r"""type\s*=\s*(?:["']hidden["']|\{\s*["']hidden["']\s*\})""",
    re.I,
)
_DIALOG_CLOSE_OPEN = re.compile(r"<(?:DialogPrimitive\.Close|Dialog\.Close)\b")
_COMMAND_INPUT_OPEN = re.compile(r"<(?:CommandPrimitive\.Input|Command\.Input)\b")
_COMMAND_ITEM_OPEN = re.compile(r"<(?:CommandPrimitive\.Item|Command\.Item)\b")
_TRAP_FOCUS_FALSE = re.compile(r"\btrapFocus\s*=\s*\{\s*false\s*\}")
_DOCS_FOCUS_RING = re.compile(r"focus[- ]?(?:visible[- ]?)?rings?", re.I)
_DOCS_KB_MERGE = re.compile(
    r"keyboard.{0,400}Merge|Merge.{0,400}keyboard",
    re.I | re.S,
)
_DOCS_KB_CONFIRM = re.compile(
    r"keyboard.{0,400}\bconfirm\b|\bconfirm\b.{0,400}keyboard",
    re.I | re.S,
)
_DOCS_KB_DISMISS = re.compile(
    r"keyboard.{0,400}\bdismiss\b|\bdismiss\b.{0,400}keyboard",
    re.I | re.S,
)
_DOCS_VOICE_SEEK_ANN = re.compile(
    r"(?:voice.{0,80}(?:seek|scrub)|(?:seek|scrub).{0,40}voice)"
    r".{0,200}announc"
    r"|announc.{0,200}"
    r"(?:voice.{0,80}(?:seek|scrub)|(?:seek|scrub).{0,40}voice)",
    re.I | re.S,
)


def _has_focus_visible_ring2(src: str) -> bool:
    """True when src has focus-visible:ring-2 and ring-ring (#216)."""
    return (
        bool(_A11Y_FOCUS_VISIBLE.search(src))
        and "focus-visible:ring-2" in src
        and "ring-ring" in src
    )


def _iter_raw_focus_tags(markup: str) -> list[str]:
    """Native <button>/<input>/<textarea>/<select>/<summary> opening tags."""
    out: list[str] = []
    for m in _RAW_FOCUS_TAG.finditer(markup):
        tag = _markup_open_tag(markup, m.start())
        if tag:
            out.append(tag)
    return out


def _iter_component_open_tags(markup: str, rx: re.Pattern[str]) -> list[str]:
    out: list[str] = []
    for m in rx.finditer(markup):
        tag = _markup_open_tag(markup, m.start())
        if tag:
            out.append(tag)
    return out


def _person_title_is_button(markup: str) -> bool:
    for m in re.finditer(r"\{personTitle\}", markup):
        tags = _ancestor_tags(markup, m.start(), limit=6)
        if any(_tag_name(t) == "button" for t in tags):
            return True
    return False


def _merge_ellipsis_is_button(src: str) -> bool:
    m = re.search(r">\s*Merge(?:…|\.\.\.)\s*<", src)
    if not m:
        return False
    found = _open_tag_before(src, m.start())
    if found and found[1].startswith("<Button"):
        return True
    for tag in _ancestor_tags(src, m.start(), limit=6):
        if tag.startswith("<Button"):
            return True
    return False

__all__ = [
    "_SPIN_ANIM",
    "_people_each_block",
    "_people_list_a11y_surfaces",
    "_A11Y_ROLE_LIST",
    "_A11Y_ACTIVEDESC",
    "_A11Y_SELECTED",
    "_A11Y_SELECTED_STATE",
    "_A11Y_ARTICLE",
    "_A11Y_ARIA_LABEL",
    "_A11Y_FOCUS_VISIBLE",
    "_A11Y_REDUCED_MOTION",
    "_A11Y_MOTION_REDUCE_TW",
    "_A11Y_ANIM_NONE",
    "_A11Y_TRANS_NONE",
    "_A11Y_SCROLL_AUTO",
    "_A11Y_WCAG_CERT",
    "_A11Y_INERT",
    "_A11Y_PERSON_ID_LABEL",
    "_A11Y_NAME_IN_LABEL",
    "_css_prefers_reduced_blocks",
    "_css_focus_visible_for",
    "_A11Y_ROLE_LISTBOX",
    "_OWNED_RING_PRIMITIVES",
    "_RAW_FOCUS_TAG",
    "_HIDDEN_INPUT_TYPE",
    "_DIALOG_CLOSE_OPEN",
    "_COMMAND_INPUT_OPEN",
    "_COMMAND_ITEM_OPEN",
    "_TRAP_FOCUS_FALSE",
    "_DOCS_FOCUS_RING",
    "_DOCS_KB_MERGE",
    "_DOCS_KB_CONFIRM",
    "_DOCS_KB_DISMISS",
    "_DOCS_VOICE_SEEK_ANN",
    "_has_focus_visible_ring2",
    "_iter_raw_focus_tags",
    "_iter_component_open_tags",
    "_person_title_is_button",
    "_merge_ellipsis_is_button",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_A11Y_ROLE_OPTION",
    "_A11Y_TABINDEX_NEG",
    "_css_without_comments",
    "_markup_open_tag",
    "_open_tag_around",
    "_product_svelte",
    "_search_pane_blob",
    "_strip_html_comments",
    "_svelte_markup",
    "_tag_name",
    "_timeline_block",
    "_web_logic",
    "_web_sources",
    "_without_comments",
    "CSP",
    "_boot_opening_block",
    "_PEOPLE_EACH",
    "annotations",
    "_ancestor_tags",
    "_matching_each_end",
    "_open_tag_before",
    "_PERSON_PANE_SKIP",
]
