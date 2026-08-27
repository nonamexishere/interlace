"""Additional titlebar asserts."""
from __future__ import annotations

from tauri_gate.titlebar_lib import *


def assert_custom_titlebar(crate: Path) -> None:
    """#211: overlay titlebar; drag the top bar; no second Interlace wordmark.

    Main window uses Tauri 2 titleBarStyle Overlay (decorations stay on).
    data-tauri-drag-region sits on the header / titlebar strip, not #app /
    the whole window, and not on nav buttons or data-chrome-search.
    The drag attribute needs core:window:allow-start-dragging (not in
    core:window:default). In-app <strong>Interlace</strong> (or header
    <h1>Interlace</h1>) is gone. Keep #129 setTitle formats and #130
    File/View. Not: custom traffic-light buttons, Windows/Linux titlebar
    branch.
    """
    import json

    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#211: App.svelte required (overlay titlebar / drag region live there)")
    app = _web_logic(crate)
    markup = _strip_html_comments(_svelte_markup(app))
    app_clean = _without_comments(app)
    logic = _web_logic(crate)
    rust = _tauri_rust_blob(crate)
    conf_path = crate / "tauri.conf.json"
    conf = conf_path.read_text() if conf_path.is_file() else ""
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = _search_pane_blob(crate) if search_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    index_html = ""
    for rel in ("index.html", "web/index.html"):
        p = crate / rel
        if p.is_file():
            index_html += p.read_text() + "\n"

    # 1) Overlay / native decorations (not decorations: false).
    if not conf.strip():
        fail(
            "#211: tauri.conf.json required — main window must use "
            "Tauri 2 titleBarStyle Overlay"
        )
    try:
        cfg = json.loads(conf)
    except json.JSONDecodeError:
        fail(
            "#211: tauri.conf.json must be valid JSON "
            "(main window titleBarStyle Overlay)"
        )
    main_win = _main_window_conf(cfg)
    if not main_win:
        fail(
            "#211: tauri.conf.json main window required "
            "(titleBarStyle Overlay so native traffic lights stay)"
        )
    tbs = main_win.get("titleBarStyle")
    if tbs is None:
        tbs = main_win.get("title_bar_style")
    if not isinstance(tbs, str) or tbs.casefold() != "overlay":
        fail(
            "#211: main window must use Tauri 2 titleBarStyle Overlay "
            "(native traffic lights stay clickable; no second painted titlebar)"
        )
    if main_win.get("decorations") is False:
        fail(
            "#211: decorations must not be false — keep native window chrome "
            "(Overlay titlebar, not a fully undecorated window)"
        )
    if re.search(r"\.decorations\s*\(\s*false\s*\)", rust):
        fail(
            "#211: do not call decorations(false) in Rust — "
            "native decorations stay (Overlay only)"
        )

    # 2) No custom red/yellow/green traffic-light buttons in the web UI.
    web_blob = markup + "\n" + app_clean
    css_blob = ""
    for p in _web_sources(crate):
        if p.suffix == ".css":
            css_blob += p.read_text() + "\n"
    if _custom_traffic_lights(web_blob + "\n" + css_blob):
        fail(
            "#211: do not draw custom traffic-light buttons "
            "(no themed red/yellow/green close/min/zoom circles — "
            "native lights stay)"
        )

    # 3) data-tauri-drag-region on top chrome, not #app / whole window.
    if _DRAG_REGION.search(app) and not _DRAG_REGION.search(markup):
        fail(
            "#211: data-tauri-drag-region must be in App.svelte chrome markup "
            "(header / titlebar strip), not only a comment or script string"
        )
    hits = list(_DRAG_REGION.finditer(markup))
    if not hits:
        # Present only on #app / body / index.html counts as "only the window".
        shell = _strip_html_comments(index_html)
        if _DRAG_REGION.search(shell):
            fail(
                "#211: data-tauri-drag-region must sit on the App.svelte "
                "header / titlebar strip, not only on #app / body / the "
                "whole window"
            )
        fail(
            "#211: top chrome must be a window drag region "
            "(data-tauri-drag-region on the header / titlebar strip)"
        )
    top_ok = False
    setup_ok = False
    for m in hits:
        tag_start = markup.rfind("<", 0, m.start() + 1)
        tag = _opening_tag(markup, m.start())
        inner = _matched_inner(markup, tag_start) if tag_start >= 0 else ""
        if _looks_like_whole_window(tag, inner):
            fail(
                "#211: data-tauri-drag-region must not sit on #app / body / "
                "the whole window — put it on the header / titlebar strip"
            )
        if _drag_is_interactive(tag):
            fail(
                "#211: interactive controls (data-chrome-search, nav buttons) "
                "must not themselves carry data-tauri-drag-region"
            )
        if _drag_is_top_chrome(tag, inner):
            top_ok = True
            if not _drag_gated_to_archive(markup, m.start()):
                setup_ok = True
    if not top_ok:
        fail(
            "#211: data-tauri-drag-region must sit on the header / titlebar "
            "strip (top chrome), not only on a pane"
        )
    if not setup_ok:
        fail(
            "#211: drag region must work on setup / boot "
            "(header exists before an archive is open)"
        )

    # 3b) data-tauri-drag-region needs start_dragging ACL (not in default).
    #     Schema lists core:window:allow-start-dragging; required, not optional.
    caps_path = crate / "capabilities" / "default.json"
    caps = caps_path.read_text() if caps_path.is_file() else ""
    if not re.search(r"core:window:allow-set-title", caps):
        fail(
            "#211: keep core:window:allow-set-title (#129) — "
            "do not drop it when adding allow-start-dragging"
        )
    if not re.search(r"core:window:allow-start-dragging", caps):
        fail(
            "#211: capabilities/default.json must include "
            "core:window:allow-start-dragging "
            "(data-tauri-drag-region invokes plugin:window|start_dragging; "
            "not in core:window:default)"
        )
    if re.search(r"core:window:allow-close\b", caps):
        fail(
            "#211: do not add core:window:allow-close — "
            "native traffic lights stay; no custom close command"
        )
    if re.search(r"core:window:allow-minimize\b", caps):
        fail(
            "#211: do not add core:window:allow-minimize — "
            "native traffic lights stay; no custom minimize command"
        )
    if re.search(
        r"core:window:allow-(?:toggle-maximize|maximize|unmaximize)\b",
        caps,
    ):
        fail(
            "#211: do not add custom traffic-light commands "
            "(allow-maximize / allow-toggle-maximize) — native zoom stays"
        )

    # 4) No in-app Interlace wordmark in the header. Native setTitle / conf
    #    "title": "Interlace" still allowed.
    chrome = "\n".join(_header_chrome_chunks(markup)) or markup
    if _WORDMARK_BRAND.search(markup) or _WORDMARK_BRAND.search(chrome):
        fail(
            "#211: drop the in-app Interlace wordmark "
            "(<strong>Interlace</strong> / header <h1>Interlace</h1> is gone; "
            "native setTitle stays)"
        )
    header_chunks = _header_chrome_chunks(markup)
    if any(_WORDMARK_TEXT.search(chunk) for chunk in header_chunks):
        fail(
            "#211: drop the in-app Interlace wordmark from the header "
            "(no second painted Interlace next to the native title)"
        )

    # 5) #129 still holds — do not rewrite assert_window_title.
    if not re.search(r"\bsetTitle\s*\(", app_clean):
        fail(
            "#211: keep setTitle (#129) — native title still follows "
            "view / person (Ada — Interlace / Search — Interlace)"
        )
    if not re.search(r"Search\s*(?:—|–|---| - )\s*Interlace", app_clean):
        fail(
            "#211: keep `Search — Interlace` native title format (#129)"
        )
    if not re.search(
        r"(?:personTitle|display_name).{0,120}(?:—|–|---| - ).{0,24}Interlace"
        r"|`\$\{[^}]{0,40}(?:personTitle|display_name)[^}]{0,40}\}"
        r"\s*(?:—|–|---| - )\s*Interlace`",
        app_clean,
        re.S,
    ):
        fail(
            "#211: keep `{display_name} — Interlace` native title format (#129)"
        )
    if not re.search(r"[\"']title[\"']\s*:\s*[\"']Interlace[\"']", conf):
        fail(
            '#211: tauri.conf.json default "title": "Interlace" stays (#129)'
        )

    # 6) File / View native menus stay — do not rewrite assert_macos_menu.
    if not _TAURI_MENU_API.search(rust):
        fail("#211: keep native File / View menus (#130)")
    if not _FILE_SUBMENU.search(rust):
        fail("#211: keep the native File menu (#130)")
    if not _VIEW_SUBMENU.search(rust):
        fail("#211: keep the native View menu (#130)")

    # 7) No Windows / Linux titlebar branch.
    rust_clean = _without_comments(rust)
    web_clean = _without_comments(logic)
    if _FOREIGN_TITLEBAR.search(rust_clean) or _FOREIGN_TITLEBAR.search(web_clean):
        fail(
            "#211: not in scope — no Windows / Linux titlebar branch "
            "(no gtk / per-OS decorations; macOS Overlay keys on the "
            "existing main window only)"
        )
    for rel in (
        "tauri.windows.conf.json",
        "tauri.linux.conf.json",
        "tauri.gnu.conf.json",
    ):
        extra = crate / rel
        if extra.is_file() and re.search(
            r"titleBarStyle|decorations|title_bar", extra.read_text(), re.I
        ):
            fail(
                f"#211: not in scope — no {rel} titlebar / decorations "
                "(Windows / Linux chrome stays out)"
            )
    windows = (cfg.get("app") or {}).get("windows") or []
    if isinstance(windows, list):
        for w in windows:
            if not isinstance(w, dict):
                continue
            label = str(w.get("label") or "")
            if re.search(r"windows|linux|gtk", label, re.I):
                fail(
                    "#211: not in scope — no per-OS titlebar window "
                    f"(label {label!r})"
                )

    # 8) Docs: overlay titlebar, drag the top bar, native lights, no wordmark.
    if not dtxt.strip():
        fail(
            "#211: docs/user/app.md required — overlay titlebar "
            "(drag the top bar; native close/minimize/zoom; no second wordmark)"
        )
    if not _DOCS_OVERLAY_BAR.search(dtxt):
        fail(
            "#211: docs/user/app.md must say the window uses an overlay "
            "/ custom titlebar"
        )
    if not _DOCS_DRAG_BAR.search(dtxt):
        fail(
            "#211: docs/user/app.md must say you can drag the top bar"
        )
    if not _DOCS_NATIVE_LIGHTS.search(dtxt):
        fail(
            "#211: docs/user/app.md must say native close / minimize / zoom "
            "stay (traffic lights stay clickable)"
        )
    if not _DOCS_NO_WORDMARK.search(dtxt):
        fail(
            "#211: docs/user/app.md must say there is no second Interlace "
            "wordmark"
        )

    # 9) Do not soften #q, chrome search, search hits, virtualizer, CSP, deny.
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#211: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-chrome-search\b", app):
        fail("#211: keep chrome search field data-chrome-search (#208)")
    if not re.search(r"\bdata-search-hit\b", search):
        fail("#211: keep data-search-hit (#210)")
    if not re.search(r"\bvisibleRange\b", app + "\n" + logic):
        fail(
            "#211: keep the person-timeline virtualizer visibleRange "
            "(#120 / #224)"
        )
    if CSP not in conf:
        fail("#211: do not soften tauri CSP")
    deny_path = crate / "deny.toml"
    if not deny_path.is_file():
        fail("#211: keep crates/interlace-tauri/deny.toml")
    deny = deny_path.read_text()
    if "reqwest" not in deny or "hyper" not in deny:
        fail("#211: deny.toml must keep banning reqwest / hyper")
