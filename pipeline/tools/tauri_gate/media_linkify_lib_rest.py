"""Continuation of media_linkify_lib."""
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
    _function_body,
    _HTML_BODY,
    _LINKIFY_FETCH,
    _rust_body_with_callees,
    _rust_fn_signature,
    _rust_function_body,
    _search_pane_blob,
    _svelte_markup,
    _tauri_rust_blob,
    _ts_function_body,
    _web_logic,
    _without_comments,
)

from tauri_gate.import_boot_setup import _element_block_at

from tauri_gate.status_toasts_chrome import _windows_around
from tauri_gate.media_linkify_lib import (
    _MIN_W0,
    _OVERFLOW_X_HIDDEN,
    _hook_element_blocks,
    _LINKIFY_EACH,
    _LINKIFY_SEG_TEXT,
    _LINKIFY_ANCHOR,
    _LINKIFY_NAMED_BTN,
    _LINKIFY_HELPER_FN,
    _LINKIFY_BAD_SCHEME_ALLOW,
    _LINKIFY_OPEN_FN,
    _LINKIFY_CMD_SNAKE,
)


def _strip_anchor_tags(src: str) -> str:
    return re.sub(r"<a\b[^>]*>[\s\S]*?</a>", " ", src, flags=re.I)


def _has_url_split_render(src: str) -> bool:
    """Sibling <a> or named button plus a segment each — not one HTML string."""
    clickable = bool(_LINKIFY_ANCHOR.search(src) or _LINKIFY_NAMED_BTN.search(src))
    split = bool(_LINKIFY_EACH.search(src) or _LINKIFY_HELPER_FN.search(src))
    segs = bool(_LINKIFY_SEG_TEXT.search(src))
    return clickable and split and segs


def _has_text_node_segments(src: str) -> bool:
    """Surrounding words are `{seg.text}` (or equivalent), not only inside <a>."""
    if re.search(
        r"\{:else(?:\s+if\s+[^}]*)?\}[\s\S]{0,240}" + _LINKIFY_SEG_TEXT.pattern,
        src,
    ):
        return True
    if re.search(
        r"kind\s*===?\s*[\"']text[\"'][\s\S]{0,240}" + _LINKIFY_SEG_TEXT.pattern,
        src,
    ):
        return True
    return bool(_LINKIFY_SEG_TEXT.search(_strip_anchor_tags(src)))


def _linkify_split_src(app: str, extra: str, body: str) -> str:
    """Bodies of the URL-split helper(s) actually used on the bubble."""
    parts = [extra, body]
    names = set(_LINKIFY_HELPER_FN.findall(body + "\n" + extra))
    for m in re.finditer(r"\{#each\s+([^}]+)\}", body + "\n" + extra):
        for ident in re.findall(r"\b([A-Za-z_]\w*)\s*\(", m.group(1)):
            names.add(ident)
    for m in re.finditer(
        r"\b([A-Za-z_]\w*)\s*\(\s*displayBody\s*\(", body + "\n" + extra
    ):
        names.add(m.group(1))
    blob = app + "\n" + extra
    for name in names:
        fn = _ts_function_body(blob, name) or _function_body(blob, name)
        if fn:
            parts.append(fn)
    return "\n".join(parts)


def _linkify_open_handler(app: str, extra: str) -> str:
    blob = app + "\n" + extra
    chunks: list[str] = []
    for m in _LINKIFY_OPEN_FN.finditer(blob):
        name = m.group(0)
        fn = _ts_function_body(blob, name) or _function_body(blob, name)
        if fn:
            chunks.append(fn)
    if not chunks:
        # onclick / ask() around a url argument on the bubble surface.
        chunks.append(
            _windows_around(
                blob,
                re.compile(
                    r"\bask\s*\([\s\S]{0,200}\b(?:url|href|link)\b"
                    r"|\b(?:url|href|link)\b[\s\S]{0,200}\bask\s*\("
                    r"|confirmDesc\s*=\s*[^\n]{0,80}\burl\b",
                    re.I,
                ),
                before=80,
                after=240,
            )
        )
    return "\n".join(chunks)


def _find_open_url_cmd(rust: str, web: str) -> str:
    """Rust command that OS-opens a URL (not reveal_cas)."""
    blob = rust + "\n" + web
    for name in _LINKIFY_CMD_SNAKE:
        if re.search(rf"\bfn\s+{re.escape(name)}\b", rust) or re.search(
            rf"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']{re.escape(name)}[\"']",
            web,
        ):
            return name
    camel = re.search(
        r"\bopen(?:Url|URL|Http|Https|ExternalUrl|BubbleUrl|Link)\s*[:=]",
        web,
    )
    if camel:
        for name in _LINKIFY_CMD_SNAKE:
            if name.replace("_", "") in camel.group(0).lower():
                if re.search(rf"\bfn\s+{re.escape(name)}\b", rust):
                    return name
    gh = re.search(r"generate_handler!\s*\[([^\]]*)\]", rust, re.S)
    if not gh:
        return ""
    for name in re.findall(r"\b([a-z][a-z0-9_]*)\b", gh.group(1)):
        if name == "reveal_cas":
            continue
        sig = _rust_fn_signature(rust, name)
        body = _rust_function_body(rust, name)
        if "/usr/bin/open" in body and re.search(r"\burl\b", sig, re.I):
            return name
    if "open_url" in blob or "openUrl" in web:
        if re.search(r"\bfn\s+open_url\b", rust):
            return "open_url"
    return ""


def _rust_http_only(body: str) -> bool:
    """True when the command allows http/https and not javascript/data/file/tauri."""
    http = bool(
        re.search(
            r"("
            r"starts_with\s*\(\s*[\"']https?://"
            r"|starts_with\s*\(\s*[\"']http://"
            r"[\s\S]{0,160}starts_with\s*\(\s*[\"']https://"
            r"|starts_with\s*\(\s*[\"']https://"
            r"[\s\S]{0,160}starts_with\s*\(\s*[\"']http://"
            r"|https\?://"
            r"|(?:scheme|protocol)\s*==\s*[\"']https?[\"']"
            r")",
            body,
        )
    )
    if not http:
        return False
    if _LINKIFY_BAD_SCHEME_ALLOW.search(body):
        return False
    # file:/javascript: OR'd into the same allow as http.
    if re.search(
        r"starts_with\s*\(\s*[\"'](?:http://|https://)[\"'][\s\S]{0,200}"
        r"starts_with\s*\(\s*[\"'](?:javascript|data|file|tauri):",
        body,
    ):
        return False
    return True


# #272 follow-up — long URL overflow + visible Open link.
# break-words (overflow-wrap: break-word) is not enough for a no-space URL.
_LINKIFY_WRAP_ANY = re.compile(
    r"("
    r"\bbreak-all\b"
    r"|overflow-wrap\s*:\s*anywhere"
    r"|overflow-wrap-anywhere"
    r"|\[overflow-wrap:anywhere\]"
    r"|wrap-anywhere"
    r"|break-anywhere"
    r")",
    re.I,
)
_LINKIFY_OPEN_LINK_LABEL = re.compile(r"Open link")
_LINKIFY_CONFIRM_LABEL_PROP = re.compile(r"\bconfirmLabel\b")


def _linkify_anchor_surface(surface: str) -> str:
    """The bubble <a data-bubble-link> / named link button — not the body <p>."""
    for hook in (
        "data-bubble-link",
        "data-body-link",
        "data-url-link",
        "data-open-url",
        "data-linkify",
        "data-url-button",
    ):
        blocks = _hook_element_blocks(surface, hook)
        if blocks:
            return "\n".join(blocks)
    return _windows_around(surface, re.compile(r"<a\b", re.I), before=0, after=240)


def _linkify_confirm_desc_blob(confirm_src: str, desc_src: str) -> str:
    """ConfirmDialog description chrome — not the whole dialog / title."""
    parts = [
        _windows_around(
            confirm_src, re.compile(r"\{description\}"), before=160, after=40
        ),
        "\n".join(_hook_element_blocks(confirm_src, "Dialog.Description")),
        desc_src,
    ]
    return "\n".join(parts)


def _linkify_dialog_content_blob(confirm_src: str, content_src: str) -> str:
    """ConfirmDialog Content open-tag classes and/or shared dialog-content."""
    opens = re.findall(r"<Dialog\.Content\b[^>]*>", confirm_src)
    return "\n".join(opens) + "\n" + content_src


def _linkify_width_capped(blob: str) -> bool:
    """min-w-0 and/or overflow-x-hidden — max-w-md alone still grows min-content."""
    return bool(_MIN_W0.search(blob) or _OVERFLOW_X_HIDDEN.search(blob))

__all__ = [
    "_MIN_W0",
    "_OVERFLOW_X_HIDDEN",
    "_SHELL_CAP",
    "_PLUGIN_SHELL",
    "_SHOW_QUOTED",
    "_hook_element_blocks",
    "_LINKIFY_UNSPLIT_BODY",
    "_LINKIFY_EACH",
    "_LINKIFY_SEG_TEXT",
    "_LINKIFY_ANCHOR",
    "_LINKIFY_NAMED_BTN",
    "_LINKIFY_HELPER_FN",
    "_LINKIFY_KIND_URL",
    "_LINKIFY_HTTP_DETECT",
    "_LINKIFY_BROAD_SCHEME",
    "_LINKIFY_BAD_SCHEME_ALLOW",
    "_LINKIFY_UNSAFE_HTML",
    "_LINKIFY_HTML_STRING",
    "_LINKIFY_NAVIGATE",
    "_LINKIFY_OPEN_FN",
    "_LINKIFY_CMD_SNAKE",
    "_LINKIFY_SKIP_EXTRA",
    "_bubble_body_blocks",
    "_bubble_linkify_extra",
    "_strip_anchor_tags",
    "_has_url_split_render",
    "_has_text_node_segments",
    "_linkify_split_src",
    "_linkify_open_handler",
    "_find_open_url_cmd",
    "_rust_http_only",
    "_LINKIFY_WRAP_ANY",
    "_LINKIFY_OPEN_LINK_LABEL",
    "_LINKIFY_CONFIRM_LABEL_PROP",
    "_linkify_anchor_surface",
    "_linkify_confirm_desc_blob",
    "_linkify_dialog_content_blob",
    "_linkify_width_capped",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_HTML_BODY",
    "_LINKIFY_FETCH",
    "_rust_body_with_callees",
    "_rust_fn_signature",
    "_search_pane_blob",
    "_svelte_markup",
    "_tauri_rust_blob",
    "_web_logic",
    "_without_comments",
    "annotations",
    "_function_body",
    "_rust_function_body",
    "_ts_function_body",
    "_element_block_at",
    "_windows_around",
]

__all__ = [
    "_strip_anchor_tags",
    "_has_url_split_render",
    "_has_text_node_segments",
    "_linkify_split_src",
    "_linkify_open_handler",
    "_find_open_url_cmd",
    "_rust_http_only",
    "_LINKIFY_WRAP_ANY",
    "_LINKIFY_OPEN_LINK_LABEL",
    "_LINKIFY_CONFIRM_LABEL_PROP",
    "_linkify_anchor_surface",
    "_linkify_confirm_desc_blob",
    "_linkify_dialog_content_blob",
    "_linkify_width_capped",
    "__all__",
]
