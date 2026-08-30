"""Keyboard-map chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.keyboard_lib import *


def assert_keyboard_map(crate: Path) -> None:
    """#132: Find map, Esc back to People, ⌘1–5 tabs. #310 Find-on-People.

    Find (⌘F / ctrl+F) on People with a person selected stays on People
    (#310). Search-tab / no person / Review / Import / Doctor still focus
    Search #q. `/` still focuses #person-filter. Static: App key handler
    must accept metaKey or ctrlKey. Do not steal letters from
    INPUT/TEXTAREA/SELECT.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#132: App.svelte required (global keyboard map)")
    app = _web_logic(crate)
    cleaned = _without_comments(app)
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = _search_pane_blob(crate) if search_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    raw_body = _app_keydown_body(cleaned) or _app_keydown_body(app)
    if not raw_body.strip():
        fail(
            "#132: App.svelte must handle window keydown "
            "(onKey / addEventListener(\"keydown\")) for the keyboard map"
        )
    body = _expand_fn_calls(cleaned, raw_body)
    if body == raw_body:
        body = _expand_fn_calls(app, raw_body)
    prefix, tail = _split_people_only(raw_body)
    prefix_x = _expand_fn_calls(cleaned, prefix) if prefix.strip() else body
    if prefix_x == prefix:
        prefix_x = _expand_fn_calls(app, prefix) if prefix.strip() else body

    # 1) ⌘F / ctrl+F: People + open person stays (#310). Search-tab / no
    #    person / Review / Import / Doctor still archive Search #q.
    #    Must run off People (not after `if (view !== "people") return`).
    #    Do not send Find to #person-filter — that stays `/` only (#208).
    f_surface = _windows_around(prefix_x, _KEY_F)
    if not f_surface.strip():
        f_surface = _windows_around(body, _KEY_F)
        if f_surface.strip() and tail and _KEY_F.search(tail) and not _KEY_F.search(prefix_x):
            fail(
                "#132: ⌘F / ctrl+F must run off People "
                "(it is after `if (view !== \"people\") return` and never fires on Search)"
            )
        fail(
            "#132: App key handler must treat metaKey/ctrlKey + f/F as Find "
            "(Search-tab / other views still #q; People + person stays — #310)"
        )
    if not _has_mod_combo(f_surface) and not _has_mod_combo(prefix_x):
        fail(
            "#132: Find must accept metaKey or ctrlKey "
            "(⌘F on macOS; ctrl+F so gates/tests see the fallback)"
        )
    if not _MOD_EITHER.search(f_surface) and not _MOD_EITHER.search(prefix_x):
        fail("#132: f/F Find must be a metaKey/ctrlKey combo, not a bare letter")
    if _FOCUS_PERSON_FILTER.search(f_surface):
        fail(
            "#132: ⌘F / ctrl+F must not go to #person-filter "
            "(`/` still focuses the people filter; People + person is pane find)"
        )
    q_focus = bool(_FOCUS_SEARCH_Q.search(f_surface) or _FOCUS_SEARCH_Q.search(prefix_x))
    if not q_focus:
        fail(
            "#132: Search-tab / no person / Review / Import / Doctor ⌘F "
            "must still focus the Search query (getElementById(\"q\") / #q)"
        )
    if not _VIEW_SEARCH_ASSIGN.search(f_surface) and not _VIEW_SEARCH_ASSIGN.search(prefix_x):
        fail(
            "#132: Search-tab / no person / Review / Import / Doctor ⌘F "
            "must still switch to Search (view = \"search\") then focus #q"
        )
    if not re.search(
        r"("
        r"if\s*\([^)]{0,240}\bselectedId\b"
        r"|view\s*===?\s*[\"']people[\"'][\s\S]{0,160}\bselectedId\b"
        r"|\bselectedId\b[\s\S]{0,160}view\s*===?\s*[\"']people[\"']"
        r"|(?:ctx\.)?selectedId\s*(?:&&|!=|!==)"
        r"|(?:&&\s*(?:ctx\.)?selectedId\b)"
        r")",
        f_surface,
    ):
        fail(
            "#310: ⌘F / Ctrl+F on People with a person selected must stay "
            "on People (branch on view === \"people\" && selectedId; "
            "do not always whenSearchPaneReady → Search #q)"
        )
    if not _PREVENT_DEFAULT.search(f_surface) and not _PREVENT_DEFAULT.search(prefix_x):
        fail(
            "#132: ⌘F / ctrl+F must preventDefault "
            "(webview/browser must not take Find)"
        )
    if search and not re.search(r"id=[\"']q[\"']", search):
        fail("#132: SearchPane must keep id=\"q\" so Search-tab ⌘F can focus the query")

    # 2) `/` still focuses the people filter on People (existing).
    slash_src = tail if tail and _KEY_SLASH.search(tail) else body
    if not _KEY_SLASH.search(slash_src) or not _FOCUS_PERSON_FILTER.search(
        _windows_around(slash_src, _KEY_SLASH) or slash_src
    ):
        fail(
            "#132: `/` on People must still focus #person-filter "
            "(do not drop the existing slash filter)"
        )

    # 3) Escape: inputs blur; from other views view = "people"; do not quit.
    if not _INPUT_TAG_GUARD.search(raw_body) and not _INPUT_TAG_GUARD.search(body):
        fail(
            "#132: key handler must still ignore INPUT/TEXTAREA/SELECT "
            "(do not steal letters from a typing field; Esc may blur)"
        )
    if not _KEY_ESC.search(raw_body) and not _KEY_ESC.search(body):
        fail("#132: Escape must be handled (blur inputs; from other views back to People)")
    if not _INPUT_BLUR.search(raw_body) and not _INPUT_BLUR.search(body):
        fail("#132: Escape in an INPUT/TEXTAREA/SELECT must blur the field")
    # ⌘1 also assigns view = "people" — require Escape itself, outside the blur guard.
    outside_prefix, _ = _split_people_only(_without_input_guard(raw_body))
    if not _esc_sets_view_people(outside_prefix, cleaned) and not _esc_sets_view_people(
        outside_prefix, app
    ):
        fail(
            "#132: Escape when not in a typing field must go back to People "
            "(view = \"people\" from Search/Review/Import/Doctor — do not close the app)"
        )
    esc_surface = _windows_around(outside_prefix, _KEY_ESC) or _windows_around(prefix_x, _KEY_ESC)
    if esc_surface and _ESC_CLOSE_APP.search(esc_surface):
        fail("#132: Escape must not close the app (back to People only)")

    # 4) ⌘/ctrl 1–5 → people / search / review / import / doctor.
    digit_surface = _windows_around(prefix_x, _DIGIT_KEY, before=200, after=800)
    if not digit_surface.strip():
        digit_surface = prefix_x
    if not _has_mod_combo(digit_surface) and not _has_mod_combo(prefix_x):
        fail(
            "#132: tab digits must accept metaKey or ctrlKey "
            "(⌘1…5 on macOS; ctrl+1…5 fallback)"
        )
    if not _digit_view_map_ok(digit_surface) and not _digit_view_map_ok(prefix_x):
        if tail and _digit_view_map_ok(tail):
            fail(
                "#132: ⌘/ctrl 1…5 must run off People "
                "(they are after `if (view !== \"people\") return`)"
            )
        fail(
            "#132: metaKey/ctrlKey + Digit1…5 (or keys \"1\"…\"5\") must set "
            "view people / search / review / import / doctor"
        )
    for tok in _VIEW_TAB_ORDER:
        if not re.search(rf"[\"']{tok}[\"']", prefix_x) and not re.search(
            rf"[\"']{tok}[\"']", digit_surface
        ):
            fail(
                f"#132: ⌘/ctrl tab map must include view \"{tok}\" "
                "(1 People, 2 Search, 3 Review, 4 Import, 5 Doctor)"
            )

    # 5) Timeline j/k stay on People (visible indices). Search hits keep their j/k.
    jk_src = tail if tail else body
    if not _KEY_J.search(jk_src) or not _KEY_K.search(jk_src):
        fail("#132: keep timeline j/k (and arrows) on People")
    if tail:
        if (_KEY_J.search(prefix) or _KEY_K.search(prefix)) and re.search(r"\btlIndex\b", prefix):
            if not re.search(r"view\s*===?\s*[\"']people[\"']", prefix):
                fail("#132: timeline j/k must stay People-only (do not steal Search hit j/k)")
    elif not re.search(r"view\s*===?\s*[\"']people[\"']", body) and not re.search(
        r"view\s*!==?\s*[\"']people[\"']", body
    ):
        fail("#132: timeline j/k must stay gated to the People view")
    if not re.search(r"visibleTlIndices|nearestVisibleTlIndex|visibleIndices", jk_src + "\n" + body):
        fail("#132: timeline j/k must still walk visibleTlIndices (do not regress #116)")
    if not _KEY_J.search(search) or not _KEY_K.search(search):
        fail("#132: keep Search hit-list j/k (SearchPane onHitsKey)")

    # 6) Letter shortcuts stay behind the input guard (Esc blur is the exception).
    guard = re.search(
        r"tagName\s*===?\s*[\"']INPUT[\"']",
        raw_body,
    )
    if guard:
        # First return after the INPUT check is the "do not steal" exit.
        ret = raw_body.find("return", guard.start())
        pre_guard = raw_body[: guard.start()] if ret >= 0 else ""
        stolen = False
        for rx in (_KEY_J, _KEY_K, _KEY_SLASH):
            for m in rx.finditer(pre_guard):
                window = pre_guard[max(0, m.start() - 80) : m.end() + 40]
                if _MOD_EITHER.search(window):
                    continue
                stolen = True
                break
            if stolen:
                break
        if stolen:
            fail(
                "#132: do not apply letter shortcuts (j/k, /) before the "
                "INPUT/TEXTAREA/SELECT guard — only Esc may act on a typing field"
            )

    # 7) Not in scope: vim mode, custom keybindings file.
    # Stay in owned sources — do not walk node_modules / target / dist.
    bind_roots = [crate, crate / "web", crate / "web" / "lib", crate / "src"]
    for root in bind_roots:
        if not root.is_dir():
            continue
        for p in root.iterdir():
            if not p.is_file():
                continue
            low = p.name.lower()
            if low in _KEYBIND_NAMES or (
                "keybind" in low and p.suffix in {".json", ".toml"}
            ):
                fail(
                    "#132: no custom keybindings file "
                    f"({p.relative_to(crate)} — out of scope; not vim remaps)"
                )
    web = crate / "web"
    if web.is_dir():
        for p in web.rglob("*"):
            if not p.is_file():
                continue
            low = p.name.lower()
            if low in _KEYBIND_NAMES or (
                "keybind" in low and p.suffix in {".json", ".toml"}
            ):
                fail(
                    "#132: no custom keybindings file "
                    f"({p.relative_to(crate)} — out of scope; not vim remaps)"
                )
    vim_src = body + "\n" + raw_body
    if _VIM_COLON.search(vim_src) or _VIM_COMMAND.search(vim_src):
        fail(
            "#132: no vim mode "
            "(no `:` command map, no :w/:q, no keybindings.json / vimMode)"
        )

    # 8) D24: docs/user/app.md documents the map.
    if not dtxt.strip():
        fail("#132: docs/user/app.md required (document the keyboard map)")
    if not re.search(
        r"("
        r"⌘\s*F"
        r"|Cmd(?:-|\s*|\+)\s*F"
        r"|Command(?:-|\s*|\+)\s*F"
        r"|Ctrl(?:-|\s*|\+)\s*F"
        r"|ctrl(?:-|\s*|\+)\s*F"
        r"|meta(?:-|\s*|\+)\s*f"
        r")",
        dtxt,
        re.I,
    ):
        fail("#132: docs/user/app.md must document ⌘F / Ctrl+F")
    if re.search(
        r"("
        r"⌘\s*F.{0,100}people filter"
        r"|⌘\s*F.{0,80}#person-filter"
        r"|focuses that people filter on People"
        r"|(?:⌘\s*F|Ctrl\+F|Ctrl-F).{0,60}on People.{0,40}filter"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#132: docs/user/app.md must not send ⌘F / Ctrl+F to the people "
            "filter (`/` still focuses #person-filter)"
        )
    if not re.search(
        r"("
        r"(?:⌘\s*F|Ctrl\+F|Ctrl-F|find).{0,180}"
        r"(?:People|timeline|thread|conversation).{0,140}"
        r"(?:stay|stays|staying|does not leave|without leaving|on the thread|on People)"
        r"|(?:People|timeline|thread|conversation).{0,100}"
        r"(?:find|⌘\s*F|Ctrl\+F).{0,140}"
        r"(?:stay|stays|on the thread|on People|does not (?:switch|leave))"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#310: docs/user/app.md must say People timeline find stays "
            "on the thread"
        )
    if not re.search(
        r"("
        r"(?:Search tab|Search view|from Search|on Search).{0,100}"
        r"(?:⌘\s*F|Ctrl\+F|Ctrl-F).{0,80}(?:#q|query)"
        r"|(?:⌘\s*F|Ctrl\+F|Ctrl-F).{0,100}"
        r"(?:Search tab|Search view|from Search).{0,80}(?:#q|query)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#310: docs/user/app.md must say Search-tab ⌘F still focuses #q"
        )
    if not re.search(
        r"("
        r"(?:Esc(?:ape)?).{0,80}(?:People|people|back)"
        r"|(?:back|return).{0,40}(?:People|people).{0,40}Esc"
        r"|Esc(?:ape)?\s+(?:clears?|back)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#132: docs/user/app.md must document Escape "
            "(clear / back to People)"
        )
    if not re.search(
        r"("
        r"⌘\s*1"
        r"|Cmd(?:-|\s*|\+)\s*1"
        r"|Command(?:-|\s*|\+)\s*1"
        r"|Ctrl(?:-|\s*|\+)\s*1"
        r"|⌘\s*1\s*[–—\-]\s*5"
        r"|Cmd(?:-|\s*|\+)\s*1\s*[–—\-]\s*5"
        r")",
        dtxt,
        re.I,
    ):
        fail(
            "#132: docs/user/app.md must document ⌘1…5 / Ctrl+1…5 "
            "(People / Search / Review / Import / Doctor)"
        )
    missing_tabs = [
        name
        for name in ("People", "Search", "Review", "Import", "Doctor")
        if not re.search(rf"\b{name}\b", dtxt)
    ]
    if missing_tabs:
        fail(
            "#132: docs/user/app.md keyboard map must name "
            + ", ".join(missing_tabs)
            + " (⌘1…5 tabs)"
        )
    if not re.search(r"\bj\b.{0,20}\bk\b|\bj`/`k\b|`j`/`k`", dtxt, re.I):
        fail("#132: docs/user/app.md must keep j/k on the timeline")

from tauri_gate.keyboard_more import assert_keyboard_list_arrows
