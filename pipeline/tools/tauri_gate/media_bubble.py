"""Bubble search / copy-reveal CAS chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.media_bubble_lib import *


def assert_bubble_search(crate: Path) -> None:
    """#273: from a timeline bubble, open Search with that person.

    Context menuitem on data-copy-menu / data-context-menu, or a named
    quiet control (data-bubble-search), opens Search and focuses #q.
    Person picker is the open person's display name (pickPerson /
    personLabel) — never a raw numeric id. Hits load: short name query
    in #q or existing run() / api.search (not empty-q idle only).
    Do not assign body_text / displayBody to #q by default.
    Keep Copy text, #q, splitSnippet / <mark>, person picker, #124
    hit→timeline, ⌘F → #q. Docs: bubble → Search; name; hits; ⌘F.
    Do not rewrite #123 / #124 / #126 / #135 / #208 / #270 / #272.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#273: App.svelte required (timeline bubble → Search)")
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#273: SearchPane.svelte required (reuse #q / pickPerson / run)")
    app = _web_logic(crate)
    search = _search_pane_blob(crate)
    markup = _svelte_markup(app)
    extra = _bubble_search_extra(crate, app)
    extra_markup = _svelte_markup(extra) if extra else ""
    surface = markup if not extra_markup else markup + "\n" + extra_markup
    control = _bubble_search_control_src(surface)
    app_clean = _without_comments(app)
    search_clean = _without_comments(search)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) Primary red: no timeline → Search control.
    if not control.strip():
        fail(
            "#273: timeline bubble must have a Search control "
            "(context menuitem on data-copy-menu / data-context-menu, "
            "or a named quiet control data-bubble-search) that opens Search"
        )

    handler = _bubble_search_handler_src(app + "\n" + extra, extra, control)
    seed = _bubble_search_seed_src(app, search, handler)

    # 2) That path sets Search view and focuses #q.
    opens = bool(
        re.search(r"\bwhenSearchPaneReady\b", handler)
        or _VIEW_SEARCH_ASSIGN.search(handler)
    )
    focuses = bool(
        re.search(r"\bwhenSearchPaneReady\b", handler)
        or _FOCUS_SEARCH_Q.search(handler)
    )
    if not opens or not focuses:
        fail(
            "#273: bubble Search path must set Search view and focus #q "
            "(whenSearchPaneReady or getElementById(\"q\") — same path as ⌘F)"
        )

    # 3) Person picker prefilled with the open person's display name.
    mount = _windows_around(app, re.compile(r"<SearchPane\b"), before=0, after=700)
    props = _search_props_blob(search)
    wired = bool(
        _BUBBLE_SEARCH_SEED_PROP.search(props)
        or _BUBBLE_SEARCH_SEED_PROP.search(mount)
        or _BUBBLE_SEARCH_SEED_PROP.search(seed)
        or re.search(
            r"\b(?:seedPerson|selectedPerson|openPerson|searchSeed|fromBubble|"
            r"selectedId)\b",
            mount,
        )
    )
    has_name = bool(_BUBBLE_SEARCH_NAME_PREFILL.search(seed))
    has_raw = bool(_BUBBLE_SEARCH_RAW_ID_LABEL.search(seed))
    if not wired or not has_name:
        fail(
            "#273: person picker must be prefilled with the open person's "
            "display name (pickPerson / personLabel / display_name) — "
            "never a raw numeric person id"
        )
    if has_raw:
        fail(
            "#273: person picker visible label must be the display name "
            "(Ada / Ada (self) via pickPerson / personLabel) — "
            "not a raw numeric person id"
        )

    # 4) Hits load: short name query in #q, or existing run() / api.search.
    has_name_q = bool(_BUBBLE_SEARCH_Q_NAME.search(seed))
    has_run = bool(_BUBBLE_SEARCH_RUN.search(seed))
    if not has_name_q and not has_run:
        fail(
            "#273: hits must load — #q gets a short name query "
            "(display name) or existing run() / api.search is invoked "
            "on this jump (not empty-q idle / clearHitsIdle only)"
        )

    # 5) #q is not assigned body_text / displayBody as the default query.
    if _bubble_search_q_body_is_default(seed):
        fail(
            "#273: #q must not be assigned body_text / displayBody(...) "
            "as the default query — prefer the person name "
            "(a selected span is optional, not the default)"
        )

    # 6) ⌘F / chrome search / whenSearchPaneReady still focuses #q.
    key_body = _app_keydown_body(app_clean) or _app_keydown_body(app)
    key_x = _expand_fn_calls(app_clean, key_body) if key_body else ""
    f_surface = _windows_around(key_x, _KEY_F) if key_x else ""
    if not (
        re.search(r"\bwhenSearchPaneReady\b", f_surface)
        or _FOCUS_SEARCH_Q.search(f_surface)
    ):
        fail(
            "#273: ⌘F must still switch to Search and focus #q "
            "(whenSearchPaneReady / getElementById(\"q\") — "
            "do not require the new bubble menu)"
        )
    if not re.search(r"\bwhenSearchPaneReady\b", app_clean) and not re.search(
        r"\bwhenSearchPaneReady\b", app
    ):
        fail(
            "#273: keep whenSearchPaneReady so chrome search / ⌘F "
            "still focus #q"
        )
    if not _CHROME_SEARCH_HOOK.search(markup) and not _CHROME_SEARCH_HOOK.search(app):
        fail("#273: keep data-chrome-search (#208) — chrome search still focuses #q")

    # 7) Keep Copy text, #q, splitSnippet / <mark>, person picker, #124 jump.
    if not _COPY_TEXT_LABEL.search(app) and not re.search(r"\bcopyText\b", app):
        fail("#273: keep Copy text on the bubble context menu (#135)")
    if not re.search(r"id=[\"']q[\"']", search):
        fail('#273: keep id="q" as the canonical query field (#208 / #270)')
    if not re.search(r"<mark\b", search, re.I):
        fail("#273: keep #126 search <mark> siblings")
    if "splitSnippet" not in search:
        fail("#273: keep #126 splitSnippet")
    if not re.search(r"\bpickPerson\b", search_clean) and not re.search(
        r"\bpersonLabel\b", search_clean
    ):
        fail("#273: keep the #123 person picker (pickPerson / personLabel)")
    if "data-person-picker" not in search and "data-person-picker" not in search_clean:
        fail("#273: keep the #123 person picker (data-person-picker)")
    if not re.search(
        r"\b(?:onJumpToMessage|jumpToMessage|activateHit)\b",
        app_clean + "\n" + search_clean,
    ):
        fail(
            "#273: keep #124 hit→timeline jump "
            "(activateHit / onJumpToMessage / jumpToMessage)"
        )

    # 8) Docs: bubble → Search; person name (not id); hits; ⌘F still #q.
    if not dtxt.strip():
        fail(
            "#273: docs/user/app.md required — from a timeline bubble you "
            "can open Search with that person (name, not id); hits load; "
            "⌘F still focuses #q"
        )
    doc_win = ""
    for m in _BUBBLE_SEARCH_DOC.finditer(dtxt):
        i = m.start()
        doc_win += dtxt[max(0, i - 80) : m.end() + 200] + "\n"
    if not doc_win.strip() or not re.search(
        r"("
        r"(?:timeline )?bubble.{0,120}Search"
        r"|Search.{0,120}(?:from a )?(?:timeline )?bubble"
        r"|right-click.{0,80}Search"
        r"|context menu.{0,80}Search"
        r")",
        doc_win,
        re.I | re.S,
    ):
        fail(
            "#273: docs/user/app.md must say from a timeline bubble you "
            "can open Search with that person"
        )
    if not re.search(
        r"("
        r"name,?\s+not\s+(?:an? )?(?:raw )?(?:numeric )?id"
        r"|display name"
        r"|person(?:'s)? name"
        r"|\bAda\b"
        r")",
        doc_win,
        re.I,
    ):
        fail(
            "#273: docs/user/app.md must say the bubble → Search person "
            "is a name, not a raw id"
        )
    if not re.search(r"\bhits?\b", doc_win, re.I):
        fail("#273: docs/user/app.md must say hits load on the bubble → Search jump")
    if not re.search(
        r"(?:⌘\s*F|Ctrl\+F|Ctrl-F).{0,80}#q|#q.{0,80}(?:⌘\s*F|Ctrl\+F|Ctrl-F)",
        doc_win,
        re.I | re.S,
    ):
        fail(
            "#273: docs/user/app.md must say ⌘F still focuses #q "
            "(bubble → Search does not replace Find)"
        )


def assert_copy_reveal_cas(crate: Path) -> None:
    """#135: bubble context menu Copy text; cas_hash attachment Reveal in Finder.

    Reveal command takes the hash only, resolves cas/ab/cd/<hash> via
    cas_blob_path, opens the local file (std::process /usr/bin/open -R or
    file://). Copy does not log the body. No plugin-shell / Share / AirDrop.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#135: App.svelte required (person-timeline bubble context menu)")
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail("#135: CasAttach.svelte required (Reveal in Finder on cas_hash)")
    web = _web_logic(crate)
    surface = _bubble_and_attach_surface(crate)
    rust = _tauri_rust_blob(crate)
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    pkg = (crate / "package.json").read_text() if (crate / "package.json").is_file() else ""
    caps_path = crate / "capabilities" / "default.json"
    caps = caps_path.read_text() if caps_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) Context menu on a person-timeline bubble.
    if not _CONTEXTMENU.search(surface):
        fail(
            "#135: person-timeline bubble must have a context menu "
            "(on:contextmenu / ContextMenu) for Copy text"
        )

    # 2) Custom menu: Copy text → clipboard (message text).
    if not _COPY_TEXT_LABEL.search(surface) and not _COPY_TEXT_LABEL.search(web):
        fail("#135: context menu must include Copy text")
    if not _WRITE_TEXT.search(web):
        fail(
            "#135: Copy text must write the message text to the clipboard "
            "(navigator.clipboard.writeText)"
        )
    copy_surf = _copy_handler_surface(web)
    if not re.search(r"body_text|displayBody|bodyText", copy_surf):
        fail("#135: clipboard write must be the message text (body_text / displayBody)")

    # 3) Copy does not log the body.
    if _copy_logs_body(copy_surf) or _copy_logs_body(_windows_around(web, _WRITE_TEXT)):
        fail(
            "#135: Copy must not log the message body "
            "(no console.log / eprintln of the text)"
        )

    # 4) Attachment with cas_hash → Reveal in Finder.
    if not _REVEAL_LABEL.search(surface) and not _REVEAL_LABEL.search(web):
        fail(
            "#135: attachment with cas_hash must offer Reveal in Finder "
            "(context menu on the attachment)"
        )
    reveal_win = _windows_around(surface, _REVEAL_LABEL, before=520, after=240)
    if not reveal_win.strip():
        reveal_win = _windows_around(web, _REVEAL_LABEL, before=520, after=240)
    if not re.search(r"cas_hash|casHash|hashOf", reveal_win + "\n" + surface):
        fail("#135: Reveal in Finder is only for an attachment that has cas_hash")

    # 5) Frontend sends only the hash to the reveal command.
    cmd = _reveal_cmd_name(rust, web)
    if not cmd:
        fail(
            "#135: frontend must invoke a reveal command that takes the hash only "
            "(e.g. reveal_cas) — not a path or URL"
        )
    payloads = _invoke_payloads(web, _REVEAL_INVOKE)
    if not payloads:
        # api.revealCas(hash) wrapper — still must mention hash, not path/url.
        call_win = _windows_around(web, _REVEAL_CMD, before=80, after=160)
        if not re.search(r"\bhash\b", call_win, re.I):
            fail(
                "#135: frontend must send only the hash to reveal "
                "(invoke reveal_cas with { hash })"
            )
        if _payload_has_path_or_url(call_win):
            fail(
                "#135: frontend must send only the hash to reveal "
                "(do not pass a path or URL from the webview)"
            )
    for payload in payloads:
        if not re.search(r"\bhash\b", payload, re.I):
            fail(
                "#135: frontend must send only the hash to reveal "
                "(invoke reveal_cas with { hash })"
            )
        if _payload_has_path_or_url(payload):
            fail(
                "#135: frontend must send only the hash to reveal "
                "(do not pass a path or URL from the webview)"
            )

    # 6) Rust command: hash only; cas_blob_path; under cas/; file-only open.
    sig = _rust_fn_signature(rust, cmd)
    body = _rust_body_with_callees(rust, cmd)
    if not body.strip():
        fail(
            f"#135: Rust command {cmd} must resolve cas/ab/cd/<hash> "
            "(fn reveal_cas taking the hash only)"
        )
    if not re.search(r"\bhash\b", sig, re.I):
        fail("#135: reveal command must take a hash (not a path or URL)")
    if re.search(r"\b(?:path|url|file|href|uri)\s*:", sig, re.I):
        fail(
            "#135: reveal command must take the hash only — "
            "do not take a path or URL from the webview"
        )
    if "cas_blob_path" not in body:
        fail(
            "#135: reveal must resolve cas/ab/cd/<hash> via cas_blob_path "
            "(64 hex only — reject anything else)"
        )
    if not re.search(r"\bcanonicalize\s*\(", body):
        fail("#135: reveal must canonicalize the CAS path")
    if not re.search(
        r"("
        r"starts_with"
        r"|outside cas"
        r"|join\(\s*[\"']cas[\"']"
        r"|[\"']cas/"
        r")",
        body,
    ):
        fail("#135: reveal must refuse anything outside cas/")
    if not re.search(r"generate_handler!\s*\[[^\]]*\b" + re.escape(cmd) + r"\b", rust, re.S):
        fail(f"#135: register {cmd} in generate_handler")

    if not re.search(r"std::process|\buse\s+std::process", rust):
        fail(
            "#135: open Finder with std::process "
            "(not tauri-plugin-shell / plugin-opener)"
        )
    if not re.search(r"Command::new|std::process::Command", body):
        fail(
            "#135: reveal must open the local file with std::process::Command "
            "(/usr/bin/open -R or a file:// URL)"
        )
    if "/usr/bin/open" not in body:
        fail("#135: open the local CAS file with /usr/bin/open (file only, not http)")
    if not re.search(r"[\"']-R[\"']", body) and "file://" not in body:
        fail("#135: use /usr/bin/open -R or a file:// URL to the CAS path")
    if re.search(r"[\"']https?://", body):
        fail("#135: reveal must not open http(s) — file only")
    if _ARBITRARY_SHELL.search(body) or _ARBITRARY_SHELL.search(rust):
        fail("#135: no shell of arbitrary commands — only /usr/bin/open on the CAS file")
    for m in re.finditer(r"Command::new\s*\(", body):
        arg = _rust_call_arg(body, m.end() - 1)
        if "/usr/bin/open" not in arg:
            fail(
                "#135: no shell of arbitrary commands — "
                "Command::new must be /usr/bin/open on the CAS file"
            )

    # 7) Bans: plugin-shell / opener / shell caps / Share / AirDrop.
    if _PLUGIN_SHELL.search(toml) or _PLUGIN_SHELL.search(pkg):
        fail(
            "#135: do not add tauri-plugin-shell / tauri-plugin-opener "
            "(std::process file-only open)"
        )
    if _PLUGIN_SHELL.search(rust) or _PLUGIN_SHELL.search(web):
        fail(
            "#135: do not add tauri-plugin-shell / tauri-plugin-opener "
            "(std::process file-only open)"
        )
    if _SHELL_CAP.search(caps):
        fail(
            "#135: capabilities must not add shell:allow-execute / "
            "shell:allow-open / opener (no arbitrary Command)"
        )
    if _SHARE_AIRDROP.search(web) or _SHARE_AIRDROP.search(rust) or _SHARE_ITEM.search(surface):
        fail("#135: no Share sheet / AirDrop")

    # 8) Docs: right-click copy text; reveal local CAS in Finder; no Share / AirDrop.
    if not dtxt.strip():
        fail("#135: docs/user/app.md required (right-click copy text; reveal in Finder)")
    doc_win = ""
    for m in re.finditer(
        r".{0,180}(?:right-click|context menu|Copy text|Reveal in Finder|AirDrop|Share sheet).{0,180}",
        dtxt,
        re.I | re.S,
    ):
        doc_win += m.group(0) + "\n"
    if not doc_win.strip():
        fail(
            "#135: docs/user/app.md must say right-click Copy text "
            "and reveal local CAS in Finder"
        )
    if not re.search(r"right-click|context menu", doc_win, re.I):
        fail("#135: docs/user/app.md must say right-click (or context menu) to copy text")
    if not re.search(r"copy text", doc_win, re.I):
        fail("#135: docs/user/app.md must describe Copy text")
    if not re.search(r"reveal", doc_win, re.I):
        fail("#135: docs/user/app.md must say reveal local CAS in Finder")
    if not re.search(r"Finder", doc_win):
        fail("#135: docs/user/app.md must say reveal local CAS in Finder")
    if not re.search(r"CAS|cas/", doc_win, re.I):
        fail("#135: docs/user/app.md must say the reveal target is a local CAS file")
    if not re.search(
        r"("
        r"no Share"
        r"|not Share"
        r"|Share sheet"
        r"|AirDrop"
        r")",
        doc_win,
        re.I,
    ):
        fail("#135: docs/user/app.md must say no Share / AirDrop")
