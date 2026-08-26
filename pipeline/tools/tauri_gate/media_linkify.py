"""Bubble linkify chrome assert. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _HTML_BODY,
    _LINKIFY_FETCH,
    _function_body,
    _rust_body_with_callees,
    _rust_fn_signature,
    _rust_function_body,
    _svelte_markup,
    _tauri_rust_blob,
    _ts_function_body,
    _web_logic,
    _without_comments,
)

from tauri_gate.import_boot import _element_block_at

from tauri_gate.status_toasts import _windows_around


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


def assert_bubble_linkify(crate: Path) -> None:
    """#272: http(s) URLs in timeline bubbles are sibling <a> / button.

    Acceptance: a bubble with https://example.com/a is clickable; the rest
    of the sentence stays a text node; no {@html of the body. Confirm
    before OS-open. Rust command accepts only http/https. Keep displayBody,
    whitespace-pre-wrap, break-words, Gmail quote fold, #126 <mark>.
    Not: HTML mail, markdown, tracking redirects.
    Do not rewrite #111 / #117 / #126 / #135 / #207 / #120 / #224 / #271.
    Follow-up: long http(s) URL wraps on <a data-bubble-link> (break-all /
    overflow-wrap anywhere) and in the ConfirmDialog description; Content /
    dialog-content is min-w-0 and/or overflow-x-hidden; App URL confirm
    uses confirmLabel Open link. Keep break-words on the body.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#272: App.svelte required (timeline data-bubble-body linkify)")
    app = app_path.read_text()
    markup = _svelte_markup(app)
    pt = markup.find("person-timeline")
    timeline_markup = markup[pt:] if pt >= 0 else markup
    blocks = _bubble_body_blocks(timeline_markup) or _bubble_body_blocks(app)
    body = "\n".join(blocks)
    extra = _bubble_linkify_extra(crate, app + "\n" + body)
    surface = body if not extra else body + "\n" + extra
    cleaned_surface = _without_comments(surface)
    split_src = _linkify_split_src(app, extra, body)
    cleaned_split = _without_comments(split_src)
    web = _web_logic(crate)
    rust = _tauri_rust_blob(crate)
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    pkg = (crate / "package.json").read_text() if (crate / "package.json").is_file() else ""
    caps_path = crate / "capabilities" / "default.json"
    caps = caps_path.read_text() if caps_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""

    # 1) Primary red: WA / mail body is still one unsplit {displayBody(...)}.
    unsplit = bool(_LINKIFY_UNSPLIT_BODY.search(body))
    if (
        unsplit
        or not _has_url_split_render(surface)
        or not _has_text_node_segments(surface)
    ):
        fail(
            "#272: timeline data-bubble-body must split http(s) URLs into "
            "sibling <a> (or a named link button); surrounding words stay "
            "text nodes ({seg.text}) — do not leave the WA / mail body as "
            "one unsplit {displayBody(...)}"
        )

    # 2) https://example.com/a (or https?:// detect) is in the split path.
    if not _LINKIFY_HTTP_DETECT.search(cleaned_split) and not _LINKIFY_HTTP_DETECT.search(
        split_src
    ):
        fail(
            "#272: https://example.com/a (or equivalent https?:// detect) "
            "must be in the URL-split path — not only the drop-URL rejector"
        )

    # 3) No {@html / innerHTML / insertAdjacentHTML of the bubble body.
    if (
        _LINKIFY_UNSAFE_HTML.search(cleaned_surface)
        or _LINKIFY_UNSAFE_HTML.search(body)
        or _HTML_BODY.search(body)
        or _HTML_BODY.search(surface)
    ):
        fail(
            "#272: no {@html / innerHTML / insertAdjacentHTML of body_text / "
            "displayBody / the bubble body (a body containing <script> or "
            "<a href=…> as text stays text)"
        )
    if _LINKIFY_HTML_STRING.search(cleaned_split) or _LINKIFY_HTML_STRING.search(
        split_src
    ):
        fail(
            "#272: surrounding words stay Svelte text nodes ({seg.text}) — "
            "do not build one HTML string of the body"
        )

    # 4) Only http / https become clickable.
    if _LINKIFY_BROAD_SCHEME.search(cleaned_split) and not _LINKIFY_HTTP_DETECT.search(
        cleaned_split
    ):
        fail(
            "#272: only http / https become clickable — a generic scheme "
            "matcher would treat javascript: / data: / file: / tauri: as links"
        )
    if re.search(r"\bisDroppedUrl\b", split_src):
        fail(
            "#272: only http / https become clickable — do not reuse "
            "isDroppedUrl (it matches every scheme) as the split"
        )
    if _LINKIFY_BAD_SCHEME_ALLOW.search(cleaned_split):
        fail(
            "#272: javascript: / data: / file: / tauri: must not become "
            "clickable — only http / https"
        )

    # 5) ConfirmDialog (or the existing confirm chrome) before OS-open.
    confirm_path = crate / "web" / "lib" / "ConfirmDialog.svelte"
    if not confirm_path.is_file() or "ConfirmDialog" not in app:
        fail(
            "#272: reuse ConfirmDialog (title + the URL in the description) "
            "before OS-open"
        )
    handler = _linkify_open_handler(app, extra)
    if not re.search(r"\bask\s*\(|confirmOpen\s*=\s*true|ConfirmDialog", handler):
        fail(
            "#272: ConfirmDialog (or the existing ask / confirm chrome) "
            "must run before OS-open — Cancel does nothing; Confirm hands "
            "the URL to the OS"
        )
    if not re.search(r"\b(?:url|href|link)\b", handler, re.I):
        fail(
            "#272: ConfirmDialog description must include the URL "
            "(title + the URL; Cancel does nothing)"
        )
    if _LINKIFY_NAVIGATE.search(_without_comments(surface + "\n" + handler)):
        fail(
            "#272: do not navigate the webview — confirm, then OS-open "
            "the http(s) string as written"
        )

    # 6) OS-open is a Rust command that only accepts http/https.
    cmd = _find_open_url_cmd(rust, web)
    if not cmd:
        fail(
            "#272: OS-open must be a Rust command (e.g. open_url) that only "
            "accepts http/https — no tauri-plugin-shell / opener"
        )
    sig = _rust_fn_signature(rust, cmd)
    cmd_body = _rust_body_with_callees(rust, cmd)
    if not re.search(r"\burl\b", sig, re.I):
        fail(
            f"#272: {cmd} must take the URL string "
            "(not a CAS hash — reveal_cas stays file-only)"
        )
    if not _rust_http_only(cmd_body):
        fail(
            f"#272: {cmd} must only accept http/https "
            "(reject javascript: / data: / file: / tauri:)"
        )
    if "/usr/bin/open" not in cmd_body:
        fail(
            f"#272: {cmd} must OS-open via /usr/bin/open on the validated "
            "http(s) URL (same spirit as reveal_cas; do not add a plugin)"
        )
    if not re.search(r"std::process|Command::new", cmd_body):
        fail(
            f"#272: {cmd} must use std::process::Command "
            "(/usr/bin/open) — not tauri-plugin-shell / opener"
        )
    if not re.search(
        r"generate_handler!\s*\[[^\]]*\b" + re.escape(cmd) + r"\b", rust, re.S
    ):
        fail(f"#272: register {cmd} in generate_handler")
    if _PLUGIN_SHELL.search(toml) or _PLUGIN_SHELL.search(pkg):
        fail(
            "#272: do not add tauri-plugin-shell / opener "
            "(Rust command, not a plugin)"
        )
    if _PLUGIN_SHELL.search(rust) or _PLUGIN_SHELL.search(web):
        fail(
            "#272: do not add tauri-plugin-shell / opener "
            "(Rust command, not a plugin)"
        )
    if _SHELL_CAP.search(caps):
        fail(
            "#272: capabilities must not add shell:allow-execute / "
            "shell:allow-open / opener — OS-open is a Rust command"
        )
    if (
        _LINKIFY_FETCH.search(cleaned_surface)
        or _LINKIFY_FETCH.search(handler)
        or _LINKIFY_FETCH.search(_without_comments(web))
    ):
        fail(
            '#272: do not fetch("http the bubble URL — open the string '
            "as written (no tracking redirects)"
        )
    if re.search(r"\b(?:reqwest|ureq|hyper::Client)\b", cmd_body):
        fail(
            "#272: do not fetch / follow redirects — "
            "/usr/bin/open the http(s) string as written"
        )

    # 7) Keep displayBody, wrap, Gmail fold, #126 search <mark>.
    if "displayBody" not in app:
        fail("#272: keep displayBody in the pipeline (do not soften #111 / #117 / #207)")
    if "displayBody" not in body and "displayBody" not in extra:
        fail(
            "#272: keep displayBody on the timeline bubble body "
            "(split after displayBody so #111 / #117 / #207 stay green)"
        )
    if "whitespace-pre-wrap" not in body:
        fail("#272: keep whitespace-pre-wrap on the bubble body")
    if "break-words" not in body:
        fail("#272: keep break-words so long URLs still wrap")
    if not re.search(r"\bsplitQuotedBody\b", app) and not re.search(
        r"\bsplitQuotedBody\b", extra
    ):
        fail("#272: keep Gmail splitQuotedBody / quote fold (#117)")
    if not _SHOW_QUOTED.search(body) and not _SHOW_QUOTED.search(app):
        fail("#272: keep Gmail Show quoted (#117)")
    if not search.strip() or not re.search(r"<mark\b", search, re.I):
        fail(
            "#272: keep #126 search <mark> "
            "(do not require search hits to linkify)"
        )
    if "splitSnippet" not in search:
        fail(
            "#272: keep #126 splitSnippet "
            "(do not require search hits to linkify)"
        )

    # 8) Docs: clickable http(s) in bubbles; rest stays text; confirm; not HTML mail.
    if not dtxt.strip():
        fail(
            "#272: docs/user/app.md required — http(s) URLs in a timeline "
            "bubble are clickable; the rest of the sentence stays a text "
            "node; confirm before the OS browser opens; still not HTML "
            "mail / markdown"
        )
    url_doc = ""
    for m in re.finditer(
        r".{0,180}(?:"
        r"\bURLs?\b"
        r"|http\(s\)"
        r"|https?"
        r"|linkify"
        r"|timeline bubble"
        r"|text node"
        r"|HTML mail"
        r"|markdown"
        r").{0,180}",
        dtxt,
        re.I | re.S,
    ):
        url_doc += m.group(0) + "\n"
    if not re.search(r"clickable", url_doc, re.I):
        fail(
            "#272: docs/user/app.md must say http(s) URLs in a timeline "
            "bubble are clickable"
        )
    if not re.search(r"text node", url_doc, re.I):
        fail(
            "#272: docs/user/app.md must say the rest of the sentence "
            "stays a text node"
        )
    if not re.search(r"confirm", url_doc, re.I):
        fail(
            "#272: docs/user/app.md must say confirm before the OS browser opens"
        )
    if not re.search(r"(?:OS\s+)?browser", url_doc, re.I):
        fail(
            "#272: docs/user/app.md must say confirm before the OS browser opens"
        )
    if not re.search(r"HTML mail", url_doc, re.I):
        fail("#272: docs/user/app.md must say this is still not HTML mail")
    if not re.search(r"markdown", url_doc, re.I):
        fail("#272: docs/user/app.md must say this is still not markdown")

    # 9) Follow-up: long URL wraps on the link + confirm; Open link label.
    #    Keep-checks 1–8 already cover only-http/https, no {@html, no
    #    plugin-shell, displayBody / break-words / #126 search <mark>.
    link_el = _linkify_anchor_surface(surface)
    if not _LINKIFY_WRAP_ANY.search(link_el):
        fail(
            "#272: timeline bubble <a data-bubble-link> (or the link surface) "
            "must wrap a long http(s) URL with break-all or overflow-wrap "
            "anywhere — keep break-words on the bubble body"
        )
    confirm_src = confirm_path.read_text()
    desc_path = (
        crate / "web" / "lib" / "components" / "ui" / "dialog" / "dialog-description.svelte"
    )
    desc_src = desc_path.read_text() if desc_path.is_file() else ""
    desc_blob = _linkify_confirm_desc_blob(confirm_src, desc_src)
    if not _LINKIFY_WRAP_ANY.search(desc_blob):
        fail(
            "#272: ConfirmDialog description must wrap a long http(s) URL "
            "(break-all or overflow-wrap anywhere) so Cancel + confirm stay "
            "on-screen"
        )
    content_path = (
        crate / "web" / "lib" / "components" / "ui" / "dialog" / "dialog-content.svelte"
    )
    content_src = content_path.read_text() if content_path.is_file() else ""
    content_blob = _linkify_dialog_content_blob(confirm_src, content_src)
    if not _linkify_width_capped(content_blob):
        fail(
            "#272: ConfirmDialog Content and/or shared dialog-content must "
            "be width-capped (min-w-0 and/or overflow-x-hidden) so a long "
            "URL cannot grow the dialog with min-content and push Cancel / "
            "confirm off-screen"
        )
    app_clean = _without_comments(app)
    handler_clean = _without_comments(handler)
    has_open_link = bool(_LINKIFY_OPEN_LINK_LABEL.search(app_clean))
    has_confirm_prop = bool(_LINKIFY_CONFIRM_LABEL_PROP.search(app_clean))
    tied = bool(
        _LINKIFY_OPEN_LINK_LABEL.search(handler_clean)
        or _LINKIFY_CONFIRM_LABEL_PROP.search(handler_clean)
        or (
            has_open_link
            and has_confirm_prop
            and re.search(
                r"<ConfirmDialog\b[\s\S]{0,400}\bconfirmLabel\b", app_clean
            )
        )
    )
    if not (has_open_link and has_confirm_prop and tied):
        fail(
            "#272: App URL confirm must use the existing confirmLabel "
            "Open link (Cancel still dismisses; do not leave the default "
            "Confirm)"
        )
    if not re.search(r">\s*Cancel\s*<", confirm_src):
        fail("#272: ConfirmDialog Cancel must still dismiss")
