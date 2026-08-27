"""Helpers extracted from media_linkify.py (media_linkify_lib)."""
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


_MIN_W0 = re.compile(
    r"("
    r"\bmin-w-0\b"
    r"|min-width\s*:\s*0"
    r"|minmax\s*\(\s*0\s*,"
    r")",
    re.I,
)
_OVERFLOW_X_HIDDEN = re.compile(
    r"("
    r"overflow-x-hidden"
    r"|overflow-x\s*:\s*hidden"
    r"|overflow\s*:\s*hidden\b"
    r")",
    re.I,
)
_SHELL_CAP = re.compile(
    r"("
    r"shell:allow-execute"
    r"|shell:allow-open"
    r"|shell:default"
    r"|opener:allow-open"
    r"|opener:allow-reveal"
    r"|opener:default"
    r")"
)
_PLUGIN_SHELL = re.compile(
    r"("
    r"tauri-plugin-shell"
    r"|tauri-plugin-opener"
    r"|@tauri-apps/plugin-shell"
    r"|@tauri-apps/plugin-opener"
    r"|plugin-shell"
    r"|plugin-opener"
    r"|plugin_shell"
    r"|plugin_opener"
    r")",
    re.I,
)


_SHOW_QUOTED = re.compile(
    r"("
    r"Show quoted"
    r"|Show quote"
    r"|Show quotes"
    r"|Expand quoted"
    r"|Expand quote"
    r"|Quoted text"
    r"|showQuoted"
    r"|showQuote"
    r"|quotedExpanded"
    r"|expandQuoted"
    r"|data-show-quoted"
    r")",
    re.I,
)


def _hook_element_blocks(src: str, hook: str) -> list[str]:
    """Each element that carries `hook` (e.g. data-partial) including children."""
    out: list[str] = []
    for m in re.finditer(rf"\b{re.escape(hook)}\b", src):
        i = m.start()
        while i > 0 and src[i] != "<":
            i -= 1
        if src[i] != "<":
            continue
        block = _element_block_at(src, i)
        if block and hook in block:
            out.append(block)
    # Dedup overlapping / identical slices.
    seen: set[str] = set()
    uniq: list[str] = []
    for b in out:
        if b not in seen:
            seen.add(b)
            uniq.append(b)
    return uniq



# #272 — linkify http(s) URLs in timeline bubbles (text nodes / <a> siblings).
_LINKIFY_UNSPLIT_BODY = re.compile(
    r"(?<![=])\{displayBody\s*\(\s*"
    r"(?:"
    r"(?:(?:item\.)?row\.)?body_text"
    r"|parts\.(?:main|quoted)"
    r")"
)
_LINKIFY_EACH = re.compile(
    r"\{#each\s+(?:"
    r"[^}]*\b(?:seg(?:ment)?s?|parts|chunks|links|tokens|urls)\b"
    r"|[^}]{0,100}(?:splitUrl|splitLink|splitHttp|linkify|urlSeg|"
    r"bodySeg|segmentUrl|parseUrl)"
    r")",
    re.I,
)
_LINKIFY_SEG_TEXT = re.compile(
    r"\{(?:seg|s|part|chunk|token|link|item)\.text\}"
)
_LINKIFY_ANCHOR = re.compile(r"<a\b", re.I)
_LINKIFY_NAMED_BTN = re.compile(
    r"("
    r"data-(?:bubble-link|body-link|url-link|open-url|linkify|url-button)"
    r"|<button\b[^>]{0,260}(?:openUrl|openURL|openLink|openBubbleUrl|"
    r"openHttp|onBubbleLink|onUrlClick|confirmOpenUrl)"
    r")",
    re.I,
)
_LINKIFY_HELPER_FN = re.compile(
    r"\b(?:"
    r"splitUrls|splitUrl|splitLinks|splitLink|splitBodyUrls|splitBodyLinks|"
    r"linkifyBody|linkifySegments|urlSegments|splitHttpUrls|splitHttp|"
    r"bodySegments|segmentUrls|parseUrls|extractUrls|linkify"
    r")\b"
)
_LINKIFY_KIND_URL = re.compile(
    r"kind\s*:\s*[\"']url[\"']|kind\s*===?\s*[\"']url[\"']"
)
_LINKIFY_HTTP_DETECT = re.compile(
    r"("
    r"https://example\.com/a"
    r"|https\?:\\?/\\?/"
    r"|https\?://"
    r"|[\"']https?://[\"']"
    r"|startsWith\s*\(\s*[\"']https?://"
    r"|starts_with\s*\(\s*[\"']https?://"
    r"|[\"']https://[\"'][\s\S]{0,120}[\"']http://"
    r"|[\"']http://[\"'][\s\S]{0,120}[\"']https://"
    r")",
    re.I,
)
_LINKIFY_BROAD_SCHEME = re.compile(
    r"("
    r"\[a-zA-Z\]\[a-zA-Z0-9+.\-\]\*:/"
    r"|\\\\w\+:/"
    r"|\[a-zA-Z\]\[a-zA-Z0-9+.\-\]\*:"
    r")"
)
_LINKIFY_BAD_SCHEME_ALLOW = re.compile(
    r"("
    r"(?:scheme|protocol)s?\s*=\s*\[[^\]]*(?:javascript:|data:|file:|tauri:)"
    r"|[\"'](?:javascript|data|file|tauri)://?[\"'][^;]{0,160}"
    r"[\"']https?://"
    r"|[\"']https?://[\"'][^;]{0,160}"
    r"[\"'](?:javascript|data|file|tauri):"
    r")",
    re.I,
)
_LINKIFY_UNSAFE_HTML = re.compile(
    r"("
    r"\{@html\b"
    r"|\.innerHTML\s*="
    r"|insertAdjacentHTML\s*\("
    r"|dangerouslySetInnerHTML"
    r")"
)
_LINKIFY_HTML_STRING = re.compile(
    r"("
    r"\.replace\s*\([^)]{0,200},\s*[`'\"][^`'\"]*<a\b"
    r"|return\s+[`'\"][^`'\"]*<a\b"
    r")",
    re.I,
)
_LINKIFY_NAVIGATE = re.compile(
    r"("
    r"window\.open\s*\("
    r"|location\.href\s*="
    r"|location\.assign\s*\("
    r")"
)
_LINKIFY_OPEN_FN = re.compile(
    r"\b(?:"
    r"openUrl|openURL|openLink|openBubbleUrl|openHttp|openHttps|"
    r"openExternal|openExternalUrl|confirmOpenUrl|confirmUrl|"
    r"onBubbleLink|onUrlClick|askOpenUrl"
    r")\b"
)
_LINKIFY_CMD_SNAKE = (
    "open_url",
    "open_http",
    "open_https",
    "open_http_url",
    "open_https_url",
    "open_external_url",
    "open_external",
    "open_bubble_url",
    "open_link",
    "open_os_url",
)
_LINKIFY_SKIP_EXTRA = frozenset(
    {
        "App.svelte",
        "SearchPane.svelte",
        "snippetHighlight.ts",
        "ConfirmDialog.svelte",
        "CasAttach.svelte",
        "CasVideo.svelte",
        "CasPdf.svelte",
        "ReviewPane.svelte",
        "ImportPane.svelte",
        "DoctorPane.svelte",
        "EmptyState.svelte",
        "api.ts",
    }
)


def _bubble_body_blocks(src: str) -> list[str]:
    """data-bubble-body element(s), including WA + Gmail branches."""
    return _hook_element_blocks(src, "data-bubble-body")


def _bubble_linkify_extra(crate: Path, host: str) -> str:
    """Helpers / child chrome App actually mounts for bubble URL split.

    Unwired drafts do not count. snippetHighlight / SearchPane stay #126.
    """
    web = crate / "web"
    if not web.is_dir():
        return ""
    extra: list[str] = []
    for p in sorted(web.rglob("*")):
        if "node_modules" in p.parts:
            continue
        if p.suffix not in {".svelte", ".ts"}:
            continue
        if p.name in _LINKIFY_SKIP_EXTRA:
            continue
        name_hit = bool(
            re.search(
                r"linkify|splitUrl|urlSeg|bodyLink|bubbleLink|bodyUrl|httpUrl",
                p.name,
                re.I,
            )
        )
        text = p.read_text()
        hook = bool(
            _LINKIFY_KIND_URL.search(text)
            or _LINKIFY_NAMED_BTN.search(text)
            or _LINKIFY_HELPER_FN.search(text)
        )
        if not name_hit and not hook:
            continue
        stem = p.stem
        if stem in host or re.search(
            rf"\b{re.escape(stem)}\b|{re.escape(p.name)}", host
        ):
            extra.append(text)
    return "\n".join(extra)

from tauri_gate.media_linkify_lib_rest import (
    _strip_anchor_tags,
    _has_url_split_render,
    _has_text_node_segments,
    _linkify_split_src,
    _linkify_open_handler,
    _find_open_url_cmd,
    _rust_http_only,
    _LINKIFY_WRAP_ANY,
    _LINKIFY_OPEN_LINK_LABEL,
    _LINKIFY_CONFIRM_LABEL_PROP,
    _linkify_anchor_surface,
    _linkify_confirm_desc_blob,
    _linkify_dialog_content_blob,
    _linkify_width_capped,
    __all__,
)

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
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_function_body",
    "_HTML_BODY",
    "_LINKIFY_FETCH",
    "_rust_body_with_callees",
    "_rust_fn_signature",
    "_rust_function_body",
    "_search_pane_blob",
    "_svelte_markup",
    "_tauri_rust_blob",
    "_ts_function_body",
    "_web_logic",
    "_without_comments",
    "_element_block_at",
    "_windows_around",
]
