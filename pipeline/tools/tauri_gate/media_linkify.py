"""Bubble linkify chrome assert. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.media_linkify_lib import *


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
    app = _web_logic(crate)
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
    search = _search_pane_blob(crate) if search_path.is_file() else ""

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
