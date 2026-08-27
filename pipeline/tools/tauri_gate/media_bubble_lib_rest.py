"""Continuation of media_bubble_lib."""
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
from tauri_gate.media_bubble_lib import (
    _BUBBLE_SEARCH_Q_BODY,
    _BUBBLE_SEARCH_SELECTION,
    _search_props_blob,
    _search_seed_effects,
)


def _bubble_search_seed_src(app: str, search: str, handler: str) -> str:
    mount = _windows_around(app, re.compile(r"<SearchPane\b"), before=0, after=700)
    effects = _search_seed_effects(search)
    props = _search_props_blob(search)
    surface = "\n".join([handler, mount, props, effects])
    parts = [surface]
    # Only expand helpers the jump / seed path actually calls (do not
    # treat today's unused pickPerson body as a prefill).
    for name in (
        "pickPerson",
        "seedPerson",
        "prefillPerson",
        "applySeed",
        "searchFromBubble",
        "openFromBubble",
    ):
        if not re.search(rf"\b{re.escape(name)}\b", surface):
            continue
        fn = _ts_fn_body(search, name) or _function_body(search, name)
        if fn:
            parts.append(fn)
    return "\n".join(parts)


def _bubble_search_q_body_is_default(seed: str) -> bool:
    """True when #q default is body_text / displayBody, not a selected span."""
    if not _BUBBLE_SEARCH_Q_BODY.search(seed):
        return False
    for m in _BUBBLE_SEARCH_Q_BODY.finditer(seed):
        win = seed[max(0, m.start() - 160) : m.end() + 80]
        if _BUBBLE_SEARCH_SELECTION.search(win):
            continue
        # `body || name` still dumps the full body as the default.
        return True
    return False


# #135 — copy message text / reveal CAS file in Finder (hash only; file open).
_CONTEXTMENU = re.compile(
    r"("
    r"on:contextmenu"
    r"|oncontextmenu"
    r"|addEventListener\s*\(\s*[\"']contextmenu[\"']"
    r"|ContextMenu(?:\.\w+)?"
    r"|data-context-menu"
    r"|contextMenu"
    r")",
    re.I,
)
_COPY_TEXT_LABEL = re.compile(r"Copy text")
_REVEAL_LABEL = re.compile(r"Reveal in Finder")
_REVEAL_CMD_NAMES = (
    "reveal_cas",
    "revealCas",
    "reveal_in_finder",
    "revealInFinder",
)
_REVEAL_CMD = re.compile(
    r"\b(?:" + "|".join(re.escape(n) for n in _REVEAL_CMD_NAMES) + r")\b"
)
_REVEAL_INVOKE = re.compile(
    r"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"'](?:"
    + "|".join(re.escape(n) for n in _REVEAL_CMD_NAMES)
    + r")[\"']"
)
_SHARE_AIRDROP = re.compile(
    r"("
    r"AirDrop"
    r"|Share sheet"
    r"|share sheet"
    r"|NSSharingService"
    r"|showShareSheet"
    r"|ShareLink\b"
    r"|share-sheet"
    r")",
    re.I,
)
_SHARE_ITEM = re.compile(
    r"("
    r">\s*Share\s*<"
    r"|[\"']Share[\"']"
    r"|label\s*:\s*[\"']Share[\"']"
    r")"
)
_COPY_FN_NAMES = (
    "copyText",
    "copyMessage",
    "copyBubble",
    "copyBubbleText",
    "onCopyText",
    "handleCopy",
    "handleCopyText",
)
_BUBBLE_MENU_SKIP = frozenset(
    {
        "App.svelte",
        "CasAttach.svelte",
        "SearchPane.svelte",
        "ReviewPane.svelte",
        "ImportPane.svelte",
        "DoctorPane.svelte",
        "ConfirmDialog.svelte",
        "EmptyState.svelte",
    }
)


def _bubble_and_attach_surface(crate: Path) -> str:
    """Person-timeline bubbles + CasAttach + components they reference."""
    parts = [_timeline_block(crate)]
    app_path = crate / "web" / "App.svelte"
    if app_path.is_file():
        parts.append(app_path.read_text())
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if cas_path.is_file():
        parts.append(cas_path.read_text())
    used = "\n".join(parts)
    web = crate / "web"
    if web.is_dir():
        for p in sorted(web.rglob("*.svelte")):
            if "node_modules" in p.parts or p.name in _BUBBLE_MENU_SKIP:
                continue
            if re.search(rf"\b{re.escape(p.stem)}\b", used):
                parts.append(p.read_text())
    return "\n".join(parts)


def _copy_handler_surface(web: str) -> str:
    chunks = [_windows_around(web, _WRITE_TEXT, before=500, after=160)]
    for name in _COPY_FN_NAMES:
        body = _ts_function_body(web, name) or _function_body(web, name)
        if body:
            chunks.append(body)
        chunks.append(
            _windows_around(web, re.compile(rf"\b{re.escape(name)}\s*\("), before=220, after=80)
        )
    return "\n".join(chunks)


def _copy_logs_body(surf: str) -> bool:
    """True if the copy path logs the message body (console / eprintln)."""
    for m in re.finditer(r"console\.(?:log|debug|info|dir|trace)\s*\(", surf):
        arg = _call_arg(surf, m.end() - 1)
        if re.search(
            r"body_text|displayBody|copiedText|\bbody\b|\btext\b|\bmsg\b|\bmessage\b",
            arg,
            re.I,
        ):
            return True
    for m in re.finditer(r"(?:eprintln|println|dbg)\s*!", surf):
        window = surf[m.start() : m.end() + 200]
        if re.search(r"body_text|displayBody|\bbody\b", window, re.I):
            return True
    return False


def _reveal_cmd_name(rust: str, web: str) -> str:
    blob = rust + "\n" + web
    m = _REVEAL_CMD.search(blob)
    return m.group(0) if m else ""

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
    "re",
    "Path",
    "fail",
    "repo_root",
    "_ARBITRARY_SHELL",
    "_expand_fn_calls",
    "_rust_body_with_callees",
    "_rust_call_arg",
    "_rust_fn_signature",
    "_search_pane_blob",
    "_svelte_markup",
    "_tauri_rust_blob",
    "_VIEW_SEARCH_ASSIGN",
    "_web_logic",
    "_without_comments",
    "_app_keydown_body",
    "_PLUGIN_SHELL",
    "_SHELL_CAP",
    "_CHROME_SEARCH_HOOK",
    "_FOCUS_SEARCH_Q",
    "_KEY_F",
    "_WRITE_TEXT",
    "_invoke_payloads",
    "_payload_has_path_or_url",
    "_windows_around",
    "annotations",
    "_call_arg",
    "_function_body",
    "_timeline_block",
    "_ts_fn_body",
    "_ts_function_body",
    "_hook_element_blocks",
]

__all__ = [
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
    "__all__",
]
