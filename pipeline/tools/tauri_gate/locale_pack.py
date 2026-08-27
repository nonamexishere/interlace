"""Helpers extracted from locale.py (locale_pack)."""
from __future__ import annotations

from __future__ import annotations
import re
from pathlib import Path
from common import fail, repo_root
from tauri_gate.scan import (_CHROME_PACK_NS, _FETCH_CALL, _SCROLL_HELPER_SKIP, _call_arg, _chrome_en_text, _chrome_lang_text, _chrome_pack_files, _function_body, _js_next, _match_closer, _stem_chrome_lang, _tauri_rust_blob, _web_logic, _web_pack_candidates, _without_comments)
from tauri_gate.import_boot_guards import (
    _empty_state_blocks,
    _markup_uses_chrome_helper,
)
from tauri_gate.status_toasts_chrome import _chrome_helper_names
from tauri_gate.status_toasts_toast import _chrome_helper_on_body
from tauri_gate.locale_menu import (
    _control_inners,
    _PANE_CHROME_FILES,
    _PANE_CHROME_PHRASES,
    _svelte_attr_raw,
)


def _split_first_arg(args: str) -> str:
    i = 0
    n = len(args)
    depth = 0
    while i < n:
        nxt = _js_next(args, i)
        if nxt != i:
            i = nxt
            continue
        c = args[i]
        if c in "({[":
            depth += 1
        elif c in ")}]":
            depth -= 1
        elif c == "," and depth == 0:
            return args[:i].strip()
        i += 1
    return args.strip()


def _call_first_args(src: str, name: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(rf"\b{re.escape(name)}\s*\(", src):
        prefix = src[max(0, m.start() - 80) : m.start()]
        if re.search(r"(?:async\s+)?function\s+$", prefix):
            continue
        if re.search(r"(?:const|let|var)\s+$", prefix):
            continue
        args = _call_arg(src, m.end() - 1)
        if args.strip():
            out.append(_split_first_arg(args))
    return out


def _chrome_pack_entries(text: str) -> dict[str, str]:
    """Parse `key: "value"` entries from a chrome pack object."""
    blob = text
    m = re.search(
        r"export\s+const\s+(?:en|tr)\s*(?::\s*\w+\s*)?=\s*\{",
        text,
    )
    if m:
        brace = text.find("{", m.start())
        end = _match_closer(text, brace)
        if end > brace:
            blob = text[brace + 1 : end]
    entries: dict[str, str] = {}
    i = 0
    n = len(blob)
    key_rx = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*:")
    while i < n:
        km = key_rx.search(blob, i)
        if not km:
            break
        j = km.end()
        while j < n and blob[j] in " \t\n\r":
            j += 1
        if j >= n or blob[j] not in "'\"`":
            i = km.end()
            continue
        end = _js_next(blob, j)
        raw = blob[j + 1 : end - 1] if end > j + 1 else ""
        entries[km.group(1)] = (
            raw.replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace('\\"', '"')
            .replace("\\'", "'")
            .replace("\\\\", "\\")
        )
        i = end
    return entries


def _keys_for_phrase(entries: dict[str, str], phrase: str) -> list[str]:
    return [k for k, v in entries.items() if phrase in v]


def _pane_chrome_phrases(panes: dict[str, str]) -> list[str]:
    leftover = [
        label for name, phrase, label in _PANE_CHROME_PHRASES if phrase in panes[name]
    ]
    if re.search(r">\s*Cancel\s*<", panes["ImportPane.svelte"]):
        leftover.append("Import Cancel")
    return leftover


def _pane_chrome_unwired(
    panes: dict[str, str], helpers: set[str]
) -> list[str]:
    """EmptyState / ask() / undo / pick / cancel still not going through t()."""
    leftover: list[str] = []
    for name in _PANE_CHROME_FILES:
        src = panes[name]
        for block in _empty_state_blocks(src):
            for attr in ("title", "body", "actionLabel"):
                val = _svelte_attr_raw(block, attr)
                if val and not _markup_uses_chrome_helper(val, helpers, src):
                    leftover.append(f"{name.split('.', 1)[0]} EmptyState {attr}")
    for name in ("ReviewPane.svelte", "DoctorPane.svelte"):
        src = panes[name]
        asks = _call_first_args(src, "ask")
        if not asks:
            leftover.append(
                f"{name.split('.', 1)[0]} ConfirmDialog titles "
                "(ask() first arg must be t())"
            )
            continue
        for arg in asks:
            if not _markup_uses_chrome_helper(arg, helpers, src):
                leftover.append(
                    f"{name.split('.', 1)[0]} ConfirmDialog title {arg[:48]}"
                )
    review = panes["ReviewPane.svelte"]
    undo_inners = _control_inners(review, re.compile(r"data-review-undo"))
    if not undo_inners and re.search(r"Undo last link|requestUndo", review):
        undo_inners = _control_inners(review, re.compile(r"requestUndo"))
    if undo_inners and not any(
        _markup_uses_chrome_helper(inner, helpers, review) for inner in undo_inners
    ):
        leftover.append("Review undo label")
    imp = panes["ImportPane.svelte"]
    pick_inners = _control_inners(imp, re.compile(r"pick\(\s*false\s*\)"))
    if pick_inners and not any(
        _markup_uses_chrome_helper(inner, helpers, imp) for inner in pick_inners
    ):
        leftover.append("Import Pick file button")
    cancel_inners = _control_inners(imp, re.compile(r"data-import-cancel"))
    if not cancel_inners:
        leftover.append("Import Cancel")
    elif not any(
        _markup_uses_chrome_helper(inner, helpers, imp) for inner in cancel_inners
    ):
        leftover.append("Import Cancel")
    seen: set[str] = set()
    out: list[str] = []
    for item in leftover:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out

__all__ = [
    "_split_first_arg",
    "_call_first_args",
    "_chrome_pack_entries",
    "_keys_for_phrase",
    "_pane_chrome_phrases",
    "_pane_chrome_unwired",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_CHROME_PACK_NS",
    "_FETCH_CALL",
    "_SCROLL_HELPER_SKIP",
    "_call_arg",
    "_chrome_en_text",
    "_chrome_lang_text",
    "_chrome_pack_files",
    "_function_body",
    "_js_next",
    "_match_closer",
    "_stem_chrome_lang",
    "_tauri_rust_blob",
    "_web_logic",
    "_web_pack_candidates",
    "_without_comments",
    "_empty_state_blocks",
    "_markup_uses_chrome_helper",
    "_chrome_helper_names",
    "_chrome_helper_on_body",
    "_control_inners",
    "_PANE_CHROME_FILES",
    "_PANE_CHROME_PHRASES",
    "_svelte_attr_raw",
]
