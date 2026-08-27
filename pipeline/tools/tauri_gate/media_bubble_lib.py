"""Helpers extracted from media_bubble.py (media_bubble_lib)."""
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
    _ARBITRARY_SHELL,
    _call_arg,
    _expand_fn_calls,
    _function_body,
    _rust_body_with_callees,
    _rust_call_arg,
    _rust_fn_signature,
    _search_pane_blob,
    _svelte_markup,
    _tauri_rust_blob,
    _timeline_block,
    _ts_fn_body,
    _ts_function_body,
    _VIEW_SEARCH_ASSIGN,
    _web_logic,
    _without_comments,
)

from tauri_gate.import_boot_guards import _app_keydown_body

from tauri_gate.media_linkify_lib import (
    _PLUGIN_SHELL,
    _SHELL_CAP,
    _hook_element_blocks,
)

from tauri_gate.search_field_keys import _CHROME_SEARCH_HOOK

from tauri_gate.status_toasts_chrome import (
    _FOCUS_SEARCH_Q,
    _WRITE_TEXT,
    _invoke_payloads,
    _payload_has_path_or_url,
    _windows_around,
)
from tauri_gate.status_toasts_toast import _KEY_F




# #273 — jump from a timeline bubble to Search (person name; hits load).
_BUBBLE_SEARCH_HOOK = re.compile(
    r"data-(?:bubble-search|search-from-bubble|bubble-to-search|"
    r"search-this|search-person|timeline-search)"
)
_BUBBLE_SEARCH_HOOK_NAMES = (
    "data-bubble-search",
    "data-search-from-bubble",
    "data-bubble-to-search",
    "data-search-this",
    "data-search-person",
    "data-timeline-search",
)
_BUBBLE_SEARCH_MENU_LABEL = re.compile(
    r"("
    r">\s*Search(?:\s+this(?:\s+person)?|\s+person)?\s*<"
    r"|t\(\s*[\"']search(?:FromBubble|This|Person|OpenPerson|Bubble)?[\"']\s*\)"
    r"|aria-label\s*=\s*[\"']Search(?: this(?: person)?| person)?[\"']"
    r")"
)
_BUBBLE_SEARCH_FN = re.compile(
    r"\b(?:"
    r"searchFromBubble|searchBubble|openBubbleSearch|searchThisPerson|"
    r"searchPersonFromBubble|onBubbleSearch|handleBubbleSearch|"
    r"jumpToSearch|openSearchFromBubble|searchOpenPerson|"
    r"searchFromTimeline|openSearchForPerson"
    r")\b"
)
_BUBBLE_SEARCH_SKIP_EXTRA = frozenset(
    {
        "App.svelte",
        "SearchPane.svelte",
        "CasAttach.svelte",
        "CommandPalette.svelte",
        "ConfirmDialog.svelte",
        "ReviewPane.svelte",
        "ImportPane.svelte",
        "DoctorPane.svelte",
        "EmptyState.svelte",
        "api.ts",
    }
)
_BUBBLE_SEARCH_HANDLER_SKIP = frozenset(
    {
        "t",
        "e",
        "event",
        "true",
        "false",
        "void",
        "closeCopyMenu",
        "copyText",
        "copyMenu",
        "undefined",
        "null",
        "console",
        "preventDefault",
        "stopPropagation",
    }
)
_BUBBLE_SEARCH_NAME_PREFILL = re.compile(
    r"("
    r"\bpickPerson\s*\("
    r"|personFilter\s*=\s*personLabel\s*\("
    r"|personFilter\s*=\s*[^;\n]{0,120}display_name"
    r"|personFilter\s*=\s*personTitle\b"
    r"|personFilter\s*=\s*personLabel\b"
    r"|personLabel\s*\("
    r")"
)
_BUBBLE_SEARCH_RAW_ID_LABEL = re.compile(
    r"("
    r"personFilter\s*=\s*(?:String\s*\(\s*)?(?:selectedId|personId|selected_id|"
    r"p\.id|person\.id|id)\b"
    r"|personFilter\s*=\s*`[^`]*\$\{(?:selectedId|personId|p\.id|person\.id)"
    r")"
)
_BUBBLE_SEARCH_Q_NAME = re.compile(
    r"("
    r"(?:searchQ|(?<![\w.])q)\s*=\s*personLabel\s*\("
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*[^;\n]{0,120}display_name"
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*personTitle\b"
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*personFilter\b"
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*personLabel\b"
    r")"
)
_BUBBLE_SEARCH_Q_BODY = re.compile(
    r"("
    r"(?:searchQ|(?<![\w.])q)\s*=\s*displayBody\s*\("
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*(?:copyMenu(?:\?)?\.)?text\b"
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*(?:row|item\.row|copyMenu)\s*"
    r"(?:\?)?\.\s*(?:body_text|subject|text)\b"
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*(?:row|item)\.body_text"
    r"|(?:searchQ|(?<![\w.])q)\s*=\s*body_text\b"
    r")"
)
_BUBBLE_SEARCH_SELECTION = re.compile(
    r"("
    r"\bgetSelection\s*\("
    r"|\bwindow\.getSelection\s*\("
    r"|\bselectedText\b"
    r"|\bselectedSpan\b"
    r")"
)
_BUBBLE_SEARCH_RUN = re.compile(
    r"("
    r"\brun\s*\("
    r"|requestSubmit\s*\("
    r"|api\.search\s*\("
    r")"
)
_BUBBLE_SEARCH_SEED_PROP = re.compile(
    r"("
    r"\b(?:seedPerson|selectedPerson|openPerson|searchSeed|fromBubble|"
    r"bubblePerson|initialPerson|prefillPerson)\b"
    r"|personFilter\s*=\s*\$bindable"
    r"|personId\s*=\s*\$bindable"
    r"|bind:personFilter"
    r"|bind:personId"
    r")"
)
_BUBBLE_SEARCH_DOC = re.compile(
    r"("
    r"timeline bubble"
    r"|from a (?:timeline )?bubble"
    r"|bubble.{0,80}Search"
    r"|Search.{0,80}(?:from a )?(?:timeline )?bubble"
    r"|right-click.{0,80}Search"
    r"|context menu.{0,80}Search"
    r")",
    re.I | re.S,
)


def _copy_context_menu_blocks(markup: str) -> list[str]:
    blocks: list[str] = []
    for hook in ("data-copy-menu", "data-context-menu"):
        blocks.extend(_hook_element_blocks(markup, hook))
    return blocks


def _menu_looks_like_bubble_search(block: str) -> bool:
    if _BUBBLE_SEARCH_HOOK.search(block):
        return True
    if _BUBBLE_SEARCH_FN.search(block):
        return True
    return bool(_BUBBLE_SEARCH_MENU_LABEL.search(block))


def _bubble_search_control_src(markup: str) -> str:
    """Copy/context-menu Search item and/or named quiet hook on the timeline."""
    parts: list[str] = []
    for block in _copy_context_menu_blocks(markup):
        if _menu_looks_like_bubble_search(block):
            parts.append(block)
    for hook in _BUBBLE_SEARCH_HOOK_NAMES:
        parts.extend(_hook_element_blocks(markup, hook))
    # Dedup overlapping slices (menu that is also the named hook).
    seen: set[str] = set()
    uniq: list[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return "\n".join(uniq)


def _bubble_search_extra(crate: Path, host: str) -> str:
    """Helpers App actually mounts for bubble → Search. Unwired drafts do not count."""
    web = crate / "web"
    if not web.is_dir():
        return ""
    extra: list[str] = []
    for p in sorted(web.rglob("*")):
        if "node_modules" in p.parts:
            continue
        if p.suffix not in {".svelte", ".ts"}:
            continue
        if p.name in _BUBBLE_SEARCH_SKIP_EXTRA:
            continue
        name_hit = bool(
            re.search(r"bubbleSearch|searchFromBubble|searchBubble", p.name, re.I)
        )
        text = p.read_text()
        hook = bool(_BUBBLE_SEARCH_HOOK.search(text) or _BUBBLE_SEARCH_FN.search(text))
        if not name_hit and not hook:
            continue
        stem = p.stem
        if stem in host or re.search(
            rf"\b{re.escape(stem)}\b|{re.escape(p.name)}", host
        ):
            extra.append(text)
    return "\n".join(extra)


def _bubble_search_handler_src(app: str, extra: str, control: str) -> str:
    blob = app + "\n" + extra
    names: set[str] = set(_BUBBLE_SEARCH_FN.findall(blob))
    names.update(_BUBBLE_SEARCH_FN.findall(control))
    for m in re.finditer(
        r"(?:onclick|on:click)\s*=\s*\{([^}]{0,400})\}",
        control,
    ):
        names.update(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", m.group(1)))
    chunks = [control]
    for name in sorted(names):
        if name in _BUBBLE_SEARCH_HANDLER_SKIP:
            continue
        fn = (
            _ts_function_body(blob, name)
            or _ts_fn_body(blob, name)
            or _function_body(blob, name)
        )
        if fn:
            chunks.append(fn)
            chunks.append(_expand_fn_calls(blob, fn))
    return "\n".join(chunks)


def _search_props_blob(search: str) -> str:
    m = re.search(r"=\s*\$props\s*\(\s*\)", search)
    if not m:
        return ""
    start = search.rfind("let", 0, m.start())
    if start < 0:
        start = max(0, m.start() - 900)
    return search[start : m.end()]


def _search_seed_effects(search: str) -> str:
    parts: list[str] = []
    for m in re.finditer(r"\$effect(?:\.pre)?\s*\(", search):
        arg = _call_arg(search, m.end() - 1)
        if re.search(
            r"pickPerson|personFilter|seedPerson|selectedPerson|openPerson|"
            r"fromBubble|bubbleSearch|searchFromBubble",
            arg,
        ):
            parts.append(arg)
    return "\n".join(parts)

from tauri_gate.media_bubble_lib_rest import (
    _bubble_search_seed_src,
    _bubble_search_q_body_is_default,
    _CONTEXTMENU,
    _COPY_TEXT_LABEL,
    _REVEAL_LABEL,
    _REVEAL_CMD_NAMES,
    _REVEAL_CMD,
    _REVEAL_INVOKE,
    _SHARE_AIRDROP,
    _SHARE_ITEM,
    _COPY_FN_NAMES,
    _BUBBLE_MENU_SKIP,
    _bubble_and_attach_surface,
    _copy_handler_surface,
    _copy_logs_body,
    _reveal_cmd_name,
    __all__,
)

__all__ = [
    "_BUBBLE_SEARCH_HOOK",
    "_BUBBLE_SEARCH_HOOK_NAMES",
    "_BUBBLE_SEARCH_MENU_LABEL",
    "_BUBBLE_SEARCH_FN",
    "_BUBBLE_SEARCH_SKIP_EXTRA",
    "_BUBBLE_SEARCH_HANDLER_SKIP",
    "_BUBBLE_SEARCH_NAME_PREFILL",
    "_BUBBLE_SEARCH_RAW_ID_LABEL",
    "_BUBBLE_SEARCH_Q_NAME",
    "_BUBBLE_SEARCH_Q_BODY",
    "_BUBBLE_SEARCH_SELECTION",
    "_BUBBLE_SEARCH_RUN",
    "_BUBBLE_SEARCH_SEED_PROP",
    "_BUBBLE_SEARCH_DOC",
    "_copy_context_menu_blocks",
    "_menu_looks_like_bubble_search",
    "_bubble_search_control_src",
    "_bubble_search_extra",
    "_bubble_search_handler_src",
    "_search_props_blob",
    "_search_seed_effects",
    "_bubble_search_seed_src",
    "_bubble_search_q_body_is_default",
    "_CONTEXTMENU",
    "_COPY_TEXT_LABEL",
    "_REVEAL_LABEL",
    "_REVEAL_CMD_NAMES",
    "_REVEAL_CMD",
    "_REVEAL_INVOKE",
    "_SHARE_AIRDROP",
    "_SHARE_ITEM",
    "_COPY_FN_NAMES",
    "_BUBBLE_MENU_SKIP",
    "_bubble_and_attach_surface",
    "_copy_handler_surface",
    "_copy_logs_body",
    "_reveal_cmd_name",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_ARBITRARY_SHELL",
    "_call_arg",
    "_expand_fn_calls",
    "_function_body",
    "_rust_body_with_callees",
    "_rust_call_arg",
    "_rust_fn_signature",
    "_search_pane_blob",
    "_svelte_markup",
    "_tauri_rust_blob",
    "_timeline_block",
    "_ts_fn_body",
    "_ts_function_body",
    "_VIEW_SEARCH_ASSIGN",
    "_web_logic",
    "_without_comments",
    "_app_keydown_body",
    "_PLUGIN_SHELL",
    "_SHELL_CAP",
    "_hook_element_blocks",
    "_CHROME_SEARCH_HOOK",
    "_FOCUS_SEARCH_Q",
    "_WRITE_TEXT",
    "_invoke_payloads",
    "_payload_has_path_or_url",
    "_windows_around",
    "_KEY_F",
]
