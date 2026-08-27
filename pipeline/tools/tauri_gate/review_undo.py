"""Helpers extracted from review.py (review_undo)."""
from __future__ import annotations

from __future__ import annotations
import re
from pathlib import Path
from common import fail, repo_root
from tauri_gate.scan import (
    _ancestor_tags,
    _APPEARANCE_MENU_LABEL,
    _APPEARANCE_SCRIM_NAMES,
    _contrast_dark_blob,
    _css_var,
    _expand_fn_calls,
    _function_body,
    _js_next,
    _match_closer,
    _open_tag_before,
    _product_svelte,
    _search_pane_blob,
    _STATUS_WARNING_NAMES,
    _svelte_markup,
    _ts_fn_body,
    _web_logic,
    _without_comments,
    CSP,
)
from tauri_gate.import_boot_guards import (
    _contrast_light_blob,
    _review_if_return_conds,
)
from tauri_gate.status_toasts_chrome import (
    _APPEARANCE_THEME_UI,
    _hue_surface,
)
from tauri_gate.review_queue import (
    _SIDEBAR_UNDO_FN_NAMES,
)


def _svelte_each_blocks(text: str) -> list[tuple[str, str]]:
    """`(source as alias …, inner)` for each `{#each}` in markup (nested-aware)."""
    out: list[tuple[str, str]] = []
    i = 0
    n = len(text)
    while i < n:
        m = re.search(r"\{#each\s+([^}]+)\}", text[i:])
        if not m:
            break
        inner_start = i + m.end()
        depth = 1
        j = inner_start
        while j < n and depth:
            nxt = re.search(r"\{#each\b|\{/each\}", text[j:])
            if not nxt:
                j = n
                break
            tok = nxt.group(0)
            j = j + nxt.end()
            if tok.startswith("{#each"):
                depth += 1
            else:
                depth -= 1
        inner_end = j - len("{/each}") if depth == 0 else n
        out.append((m.group(1).strip(), text[inner_start:inner_end]))
        i = inner_start
    return out


def _markup_text_nodes(block: str) -> str:
    """Drop attribute values so `{e.id}` in onclick / bind does not count."""
    out = re.sub(r"\b[\w:.-]+\s*=\s*\{(?:[^{}]|\{[^{}]*\})*\}", " ", block)
    out = re.sub(r"\b[\w:.-]+\s*=\s*\"[^\"]*\"", " ", out)
    out = re.sub(r"\b[\w:.-]+\s*=\s*'[^']*'", " ", out)
    return out


def _people_sidebar_region(markup: str) -> str:
    """People sidebar slice (data-people-sidebar → timeline / inspector)."""
    m = re.search(r"\bdata-people-sidebar\b", markup)
    if not m:
        return ""
    start = m.start()
    rest = markup[start + 20 :]
    end_m = re.search(
        r"("
        r"id\s*=\s*[\"']person-timeline[\"']"
        r"|data-person-inspector"
        r"|data-conversation-switcher"
        r")",
        rest,
    )
    end = start + 20 + end_m.start() if end_m else min(len(markup), start + 16000)
    return markup[start:end]


def _sidebar_undo_fn_blob(cleaned: str) -> str:
    chunks: list[str] = []
    for name in _SIDEBAR_UNDO_FN_NAMES:
        body = _ts_fn_body(cleaned, name) or _function_body(cleaned, name)
        if body:
            chunks.append(body)
    return "\n".join(chunks)


def _sidebar_each_guard_blob(cleaned: str, inner: str) -> str:
    """Each-block plus named helpers it calls (isUndoable / lastUndoable)."""
    parts = [inner]
    for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", inner):
        if name in {"doUndo", "undo", "api"}:
            continue
        body = _ts_fn_body(cleaned, name) or _function_body(cleaned, name)
        if body:
            parts.append(body)
    return "\n".join(parts)

__all__ = [
    "_svelte_each_blocks",
    "_markup_text_nodes",
    "_people_sidebar_region",
    "_sidebar_undo_fn_blob",
    "_sidebar_each_guard_blob",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_ancestor_tags",
    "_APPEARANCE_MENU_LABEL",
    "_APPEARANCE_SCRIM_NAMES",
    "_contrast_dark_blob",
    "_css_var",
    "_expand_fn_calls",
    "_function_body",
    "_js_next",
    "_match_closer",
    "_open_tag_before",
    "_product_svelte",
    "_search_pane_blob",
    "_STATUS_WARNING_NAMES",
    "_svelte_markup",
    "_ts_fn_body",
    "_web_logic",
    "_without_comments",
    "CSP",
    "_contrast_light_blob",
    "_review_if_return_conds",
    "_APPEARANCE_THEME_UI",
    "_hue_surface",
    "_SIDEBAR_UNDO_FN_NAMES",
]
