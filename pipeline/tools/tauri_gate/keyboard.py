"""Keyboard-map chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    CSP,
    _A11Y_ROLE_OPTION,
    _A11Y_TABINDEX_NEG,
    _KEYMAP_CALL_SKIP,
    _MOD_EITHER,
    _VIEW_SEARCH_ASSIGN,
    _expand_fn_calls,
    _function_body,
    _strip_html_comments,
    _svelte_markup,
    _ts_fn_body,
    _without_comments,
)

from tauri_gate.a11y import (
    _A11Y_ROLE_LISTBOX,
    _people_each_block,
    _people_list_a11y_surfaces,
)

from tauri_gate.import_boot import (
    _app_keydown_body,
    _input_guard_span,
)

from tauri_gate.status_toasts import (
    _FOCUS_SEARCH_Q,
    _KEY_ESC,
    _KEY_F,
    _has_mod_combo,
    _split_people_only,
    _windows_around,
    _without_input_guard,
)



_KEY_SLASH = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']/[\"']"
    r"|[\"']/[\"']\s*===?\s*(?:e\.)?key"
    r")",
)
_KEY_J = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']j[\"']|[\"']j[\"']\s*===?\s*(?:e\.)?key"
)
_KEY_K = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']k[\"']|[\"']k[\"']\s*===?\s*(?:e\.)?key"
)
_FOCUS_PERSON_FILTER = re.compile(
    r"("
    r"getElementById\s*\(\s*[\"']person-filter[\"']"
    r"|querySelector\s*\(\s*[\"']#person-filter[\"']"
    r"|#person-filter"
    r")",
)
_VIEW_PEOPLE_ASSIGN = re.compile(r"\bview\s*=\s*[\"']people[\"']")
_INPUT_TAG_GUARD = re.compile(
    r"tagName\s*===?\s*[\"']INPUT[\"']"
    r".{0,160}tagName\s*===?\s*[\"']TEXTAREA[\"']"
    r".{0,160}tagName\s*===?\s*[\"']SELECT[\"']"
    r"|tagName\s*===?\s*[\"']INPUT[\"']"
    r".{0,80}[\"']TEXTAREA[\"']"
    r".{0,80}[\"']SELECT[\"']",
    re.S,
)
_INPUT_BLUR = re.compile(r"\.blur\s*\(\s*\)")
_PREVENT_DEFAULT = re.compile(r"preventDefault\s*\(")
_DIGIT_KEY = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"'][1-5][\"']"
    r"|(?:e\.)?code\s*===?\s*[\"']Digit[1-5][\"']"
    r"|(?:e\.)?key\s*>=\s*[\"']1[\"']"
    r"|(?:e\.)?key\s*<=\s*[\"']5[\"']"
    r"|Number\s*\(\s*(?:e\.)?key"
    r"|parseInt\s*\(\s*(?:e\.)?key"
    r")"
)
_VIEW_TAB_ORDER = ("people", "search", "review", "import", "doctor")
_VIM_COLON = re.compile(r"(?:e\.)?key\s*===?\s*[\"']:[\"']|[\"']:[\"']\s*===?\s*(?:e\.)?key")
_VIM_COMMAND = re.compile(
    r"("
    r"[\"']:w[\"']"
    r"|[\"']:q[\"']"
    r"|[\"']:wq[\"']"
    r"|\bvimMode\b"
    r"|\bvim-mode\b"
    r"|\bcustomKeybindings\b"
    r")",
    re.I,
)
_ESC_CLOSE_APP = re.compile(
    r"("
    r"getCurrentWindow\s*\(\s*\)\s*\.\s*close\s*\("
    r"|window\s*\.\s*close\s*\("
    r"|app(?:Window)?\s*\.\s*close\s*\("
    r"|app\.exit\s*\("
    r"|process\.exit\s*\("
    r")"
)
_KEYBIND_NAMES = frozenset(
    {
        "keybindings.json",
        "keybindings.toml",
        "key-bindings.json",
        "keymaps.json",
    }
)


def _esc_sets_view_people(src: str, whole: str) -> bool:
    """True if an Escape check outside the input guard assigns view = \"people\"."""
    for m in _KEY_ESC.finditer(src):
        window = src[m.start() : m.end() + 400]
        if _VIEW_PEOPLE_ASSIGN.search(window):
            return True
        for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", window):
            if name in _KEYMAP_CALL_SKIP:
                continue
            inner = _ts_fn_body(whole, name) or _function_body(whole, name)
            if inner and _VIEW_PEOPLE_ASSIGN.search(inner):
                return True
    return False


def _digit_view_map_ok(surface: str) -> bool:
    """True if digit 1..5 map to people/search/review/import/doctor."""
    if not _DIGIT_KEY.search(surface):
        return False
    # Ordered array / tuple used as the tab list.
    joined = r"[\"']people[\"']\s*,\s*[\"']search[\"']\s*,\s*[\"']review[\"']\s*,\s*[\"']import[\"']\s*,\s*[\"']doctor[\"']"
    if re.search(joined, surface):
        return True
    # Object / switch / per-key assigns.
    pairs = (
        (r"[\"']1[\"']|Digit1", "people"),
        (r"[\"']2[\"']|Digit2", "search"),
        (r"[\"']3[\"']|Digit3", "review"),
        (r"[\"']4[\"']|Digit4", "import"),
        (r"[\"']5[\"']|Digit5", "doctor"),
    )
    for digit_rx, view in pairs:
        if not re.search(
            rf"(?:{digit_rx})[\s\S]{{0,220}}[\"']{view}[\"']"
            rf"|[\"']{view}[\"'][\s\S]{{0,220}}(?:{digit_rx})",
            surface,
        ):
            return False
    return True


def assert_keyboard_map(crate: Path) -> None:
    """#132: ⌘F Search #q from every view, Esc back to People, ⌘1–5 tabs.

    Find (⌘F / ctrl+F) switches to Search and focuses #q — including from
    People (#208). `/` still focuses #person-filter. Keyboard-only can open
    Ada, search, return. Static: App key handler must accept metaKey or
    ctrlKey. Do not steal letters from INPUT/TEXTAREA/SELECT.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#132: App.svelte required (global keyboard map)")
    app = app_path.read_text()
    cleaned = _without_comments(app)
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
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

    # 1) ⌘F / ctrl+F from every view including People → Search + #q.
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
            "(from every view including People, switch to Search and focus #q)"
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
            "#132: ⌘F / ctrl+F from People must switch to Search and focus #q "
            "(do not send Find to #person-filter — `/` still focuses the people filter)"
        )
    q_focus = bool(_FOCUS_SEARCH_Q.search(f_surface) or _FOCUS_SEARCH_Q.search(prefix_x))
    if not q_focus:
        fail(
            "#132: ⌘F / ctrl+F from every view including People must focus "
            "the Search query (getElementById(\"q\") / #q)"
        )
    if not _VIEW_SEARCH_ASSIGN.search(f_surface) and not _VIEW_SEARCH_ASSIGN.search(prefix_x):
        fail(
            "#132: ⌘F / ctrl+F from every view including People must switch "
            "to Search (view = \"search\") then focus #q"
        )
    if not _PREVENT_DEFAULT.search(f_surface) and not _PREVENT_DEFAULT.search(prefix_x):
        fail(
            "#132: ⌘F / ctrl+F must preventDefault "
            "(webview/browser must not take Find)"
        )
    if search and not re.search(r"id=[\"']q[\"']", search):
        fail("#132: SearchPane must keep id=\"q\" so ⌘F can focus the query")

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
        fail(
            "#132: docs/user/app.md must document ⌘F / Ctrl+F "
            "(from every view including People, switch to Search and focus #q)"
        )
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
            "#132: docs/user/app.md must say ⌘F / Ctrl+F from every view "
            "including People switches to Search and focuses #q "
            "(not the people filter — `/` still focuses #person-filter)"
        )
    if not re.search(
        r"("
        r"(?:⌘\s*F|Ctrl\+F|Ctrl-F).{0,160}(?:every view|including People|from People)"
        r".{0,80}(?:#q|Search)"
        r"|(?:every view|including People).{0,80}(?:⌘\s*F|Ctrl\+F|Ctrl-F)"
        r".{0,80}(?:#q|Search)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#132: docs/user/app.md must say ⌘F / Ctrl+F from every view "
            "including People focuses Search #q"
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


# #214 — keyboard map: list arrows, roving tabindex, tab path, no trap.
_KEY_ARROW_DOWN = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']ArrowDown[\"']"
    r"|[\"']ArrowDown[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?code\s*===?\s*[\"']ArrowDown[\"']"
    r")"
)
_KEY_ARROW_UP = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']ArrowUp[\"']"
    r"|[\"']ArrowUp[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?code\s*===?\s*[\"']ArrowUp[\"']"
    r")"
)
_KEY_ARROW_EITHER = re.compile(
    r"("
    + _KEY_ARROW_DOWN.pattern
    + r"|"
    + _KEY_ARROW_UP.pattern
    + r")"
)
_LIST_FOCUS = re.compile(
    r"("
    r"(?:closest|matches|querySelector)[\s?.]*\(\s*[^)]{0,120}(?:option|listbox)"
    r"|getAttribute\s*\(\s*[\"']role[\"']\s*\)\s*===?\s*[\"'](?:option|listbox)[\"']"
    r"|\.role\s*===?\s*[\"'](?:option|listbox)[\"']"
    r"|\[role\s*=\s*[\\'\"]?(?:option|listbox)"
    r"|data-people-(?:listbox|option)"
    r")",
    re.I,
)
_LIST_SELECT_PERSON = re.compile(r"\bselectPerson\s*\(")
_FILTERED_LIST = re.compile(r"\bfiltered\b")
_LIST_NEXT_PREV = re.compile(
    r"("
    r"findIndex"
    r"|indexOf"
    r"|\+\s*1"
    r"|-\s*1"
    r"|nextPerson"
    r"|prevPerson"
    r"|nextIndex"
    r"|prevIndex"
    r")"
)
_TABINDEX_ATTR = re.compile(r"\btab(?:[Ii]ndex)\s*=", re.I)
_TABINDEX_DYNAMIC = re.compile(r"\btab(?:[Ii]ndex)\s*=\s*\{", re.I)
_TABINDEX_ZERO = re.compile(
    r"\btab(?:[Ii]ndex)\s*=\s*(?:[\"']0[\"']|\{0\}|\{[^}]{0,240}(?:\b0\b|[\"']0[\"']))",
    re.I,
)
_TABINDEX_NEG1 = re.compile(
    r"\btab(?:[Ii]ndex)\s*=\s*(?:[\"']-1[\"']|\{-1\}|\{[^}]{0,240}(?:-1|[\"']-1[\"']))",
    re.I,
)
_OPEN_OTHER_ARCHIVE = re.compile(r"Open other archive", re.I)
_DOCS_LIST_ARROWS = re.compile(
    r"("
    r"(?:arrow\s*keys?|arrows|ArrowDown|ArrowUp).{0,120}"
    r"(?:people|listbox|person)"
    r"|(?:people|listbox|person).{0,100}"
    r"(?:arrow\s*keys?|arrows)"
    r"|arrows?.{0,80}change.{0,60}person"
    r")",
    re.I | re.S,
)
_DOCS_TAB_PATH = re.compile(
    r"("
    r"Tab.{0,140}(?:filter|#person-filter).{0,100}(?:selected )?person.{0,80}timeline"
    r"|(?:filter|#person-filter).{0,80}(?:selected )?person.{0,80}timeline"
    r"|filter\s*→\s*(?:the\s+)?(?:selected\s+)?person\s*→\s*timeline"
    r"|filter\s*->\s*(?:the\s+)?(?:selected\s+)?person\s*->\s*timeline"
    r")",
    re.I | re.S,
)
_DOCS_JK_MESSAGES = re.compile(
    r"("
    r"[`']?j[`']?\s*/\s*[`']?k[`']?.{0,50}(?:message|timeline)"
    r"|[`']?j[`']?.{0,10}[`']?k[`']?.{0,50}(?:message|timeline)"
    r")",
    re.I | re.S,
)
_DOCS_Q_SAFE = re.compile(
    r"("
    r"(?:#q|Search).{0,120}(?:never intercept|not intercept|is never intercepted)"
    r"|typing.{0,60}(?:Search|#q).{0,80}(?:never|not)\s+intercept"
    r"|letter shortcuts.{0,80}(?:ignored|not applied).{0,60}field"
    r")",
    re.I | re.S,
)
_LIST_ARROW_EXPAND_SKIP = _KEYMAP_CALL_SKIP | frozenset(
    {
        "selectPerson",
        "ensureTlIndexVisible",
        "nearestVisibleTlIndex",
    }
)


def _expand_list_arrow_calls(src: str, body: str, depth: int = 2) -> str:
    """Include named callees, but not selectPerson (its body walks tlIndex)."""
    chunks = [body]
    seen: set[str] = set()

    def walk(blob: str, left: int) -> None:
        for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob):
            if name in seen or name in _LIST_ARROW_EXPAND_SKIP:
                continue
            seen.add(name)
            inner = _ts_fn_body(src, name) or _function_body(src, name)
            if not inner:
                continue
            chunks.append(inner)
            if left > 0:
                walk(inner, left - 1)

    walk(body, depth)
    return "\n".join(chunks)


def _arrow_key_windows(src: str, rx: re.Pattern[str]) -> list[str]:
    return [
        src[max(0, m.start() - 360) : m.end() + 860] for m in rx.finditer(src)
    ]


def _list_arrow_selects_person(body: str, whole: str, rx: re.Pattern[str]) -> bool:
    """True when this arrow key on a listbox/option calls selectPerson on filtered."""
    expanded = _expand_list_arrow_calls(whole, body)
    windows = _arrow_key_windows(expanded, rx) or _arrow_key_windows(body, rx)
    if not windows:
        return False
    has_list = bool(_LIST_FOCUS.search(expanded) or _LIST_FOCUS.search(body))
    if not has_list:
        return False
    for w in windows:
        w_x = _expand_list_arrow_calls(whole, w)
        if (
            _LIST_FOCUS.search(w_x)
            and _LIST_SELECT_PERSON.search(w_x)
            and _FILTERED_LIST.search(w_x)
            and _LIST_NEXT_PREV.search(w_x)
        ):
            return True
        # List-focus may sit just outside the per-key window (shared inList flag).
        if (
            has_list
            and _LIST_SELECT_PERSON.search(w_x)
            and _FILTERED_LIST.search(w_x)
            and _LIST_NEXT_PREV.search(w_x)
        ):
            return True
    return False


def _people_option_tags(people_each: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"<([A-Za-z][\w:-]*)\b", people_each):
        gt = people_each.find(">", m.start())
        if gt < 0:
            continue
        tag = people_each[m.start() : gt + 1]
        if re.search(r"role\s*=\s*[\"']option[\"']", tag, re.I):
            out.append(tag)
    return out


def _option_roving_tabindex_ok(people_each: str) -> bool:
    """Selected option tabindex 0 / {0}; others -1 / {-1}."""
    tags = _people_option_tags(people_each)
    blob = "\n".join(tags) if tags else people_each
    if not _TABINDEX_DYNAMIC.search(blob) and not (
        _TABINDEX_ZERO.search(blob) and _TABINDEX_NEG1.search(blob)
    ):
        return False
    if not _TABINDEX_ZERO.search(blob) or not _TABINDEX_NEG1.search(blob):
        return False
    if not re.search(
        r"selectedId|selected_id|selectedPerson|p\.id|person\.id|aria-selected",
        blob,
    ):
        return False
    return True


def _nearest_open_tag(src: str, pos: int) -> str:
    """Open tag immediately before pos (text-node label → its element)."""
    lt = src.rfind("<", 0, pos)
    if lt < 0:
        return ""
    gt = src.find(">", lt)
    if gt < 0:
        return ""
    return src[lt : gt + 1]


def _sidebar_chrome_untabbable(markup: str) -> bool:
    """Undo / Open other archive are not default-tabbable between filter and timeline."""
    fm = re.search(r"id\s*=\s*[\"']person-filter[\"']", markup)
    tl = re.search(r"id\s*=\s*[\"']person-timeline[\"']", markup)
    if not fm or not tl or tl.start() <= fm.start():
        return False
    mid = markup[fm.start() : tl.start()]
    needed: list[tuple[str, re.Pattern[str]]] = [
        ("undo", re.compile(r">\s*undo\s*<", re.I)),
        ("Open other archive", _OPEN_OTHER_ARCHIVE),
    ]
    for _label, rx in needed:
        hits = list(rx.finditer(mid))
        if not hits:
            # Control not between filter and timeline — tab path is already clear.
            continue
        for m in hits:
            tag = _nearest_open_tag(mid, m.start())
            if not tag or not re.search(r"<Button\b|<button\b", tag, re.I):
                # Walk back to the nearest Button/button.
                search = mid[: m.start()]
                bm = None
                for cand in re.finditer(r"<(?:Button|button)\b[^>]*>", search, re.I | re.S):
                    bm = cand
                if not bm:
                    return False
                tag = bm.group(0)
            if not _TABINDEX_NEG1.search(tag) and not _A11Y_TABINDEX_NEG.search(tag):
                return False
    return True


def _bare_letter_before_guard(pre: str, rx: re.Pattern[str]) -> bool:
    for m in rx.finditer(pre):
        window = pre[max(0, m.start() - 80) : m.end() + 40]
        if _MOD_EITHER.search(window):
            continue
        return True
    return False


def assert_keyboard_list_arrows(crate: Path) -> None:
    """#214: list arrows selectPerson, roving tabindex, tab path, no trap.

    ArrowDown/Up on a focused people listbox/option change the selected
    person (selectPerson next/prev on filtered), not only timeline tlIndex.
    Selected option tabindex 0, others -1. Tab: #person-filter → people →
    #person-timeline; undo / Open other archive are not a stop. INPUT
    guard still returns before bare j/k. Docs. Do not rewrite #132.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#214: App.svelte required (people listbox arrows + tab path)")
    app = app_path.read_text()
    app_clean = _without_comments(app)
    markup = _strip_html_comments(_svelte_markup(app))
    chrome, people_each = _people_list_a11y_surfaces(crate)
    if not people_each.strip():
        people_each = _people_each_block(markup)
    if not chrome.strip():
        chrome = markup
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    conf_path = crate / "tauri.conf.json"
    conf = conf_path.read_text() if conf_path.is_file() else ""

    raw_body = _app_keydown_body(app_clean) or _app_keydown_body(app)
    if not raw_body.strip():
        fail(
            "#214: App.svelte must handle window keydown "
            "(onKey) so listbox arrows can selectPerson"
        )
    body = _expand_list_arrow_calls(app_clean, raw_body)
    if body == raw_body:
        body = _expand_list_arrow_calls(app, raw_body)

    # 1) When a people listbox/option is focused, ArrowDown/Up selectPerson
    #    next/prev on filtered — not only timeline tlIndex.
    if not _KEY_ARROW_DOWN.search(raw_body) and not _KEY_ARROW_DOWN.search(body):
        fail(
            "#214: onKey must handle ArrowDown "
            "(people listbox when focused; timeline otherwise)"
        )
    if not _KEY_ARROW_UP.search(raw_body) and not _KEY_ARROW_UP.search(body):
        fail(
            "#214: onKey must handle ArrowUp "
            "(people listbox when focused; timeline otherwise)"
        )
    if not _list_arrow_selects_person(
        raw_body, app_clean, _KEY_ARROW_DOWN
    ) and not _list_arrow_selects_person(raw_body, app, _KEY_ARROW_DOWN):
        fail(
            "#214: ArrowDown/Up when a people listbox/option is focused "
            "must selectPerson next/prev on filtered (not only timeline tlIndex)"
        )
    if not _list_arrow_selects_person(
        raw_body, app_clean, _KEY_ARROW_UP
    ) and not _list_arrow_selects_person(raw_body, app, _KEY_ARROW_UP):
        fail(
            "#214: ArrowUp when a people listbox/option is focused "
            "must selectPerson prev on filtered (not only timeline tlIndex)"
        )
    # Timeline arrows stay when the listbox is not focused (do not drop j/k).
    if not re.search(r"\btlIndex\b", raw_body) and not re.search(r"\btlIndex\b", body):
        fail(
            "#214: timeline j/k + arrows must stay when focus is not "
            "in the people listbox (keep tlIndex walk)"
        )

    # 2) Selected option tabindex="0" / {0}; other options tabindex="-1" / {-1}.
    if not people_each.strip():
        fail("#214: people list {{#each filtered}} required (roving tabindex on options)")
    if not _A11Y_ROLE_OPTION.search(people_each) and not _A11Y_ROLE_OPTION.search(chrome):
        fail('#214: people rows must stay role="option" (listbox arrows + roving tabindex)')
    option_blob = "\n".join(_people_option_tags(people_each)) or people_each
    if not _TABINDEX_ATTR.search(option_blob):
        fail(
            "#214: people listbox options must use roving tabindex "
            '(selected tabindex="0" / {0}, others tabindex="-1" / {-1}) — '
            "do not leave every person button default-tabbable"
        )
    if not _option_roving_tabindex_ok(people_each):
        fail(
            "#214: selected people option must be tabindex=\"0\" (or {0}); "
            "other options tabindex=\"-1\" (or {-1})"
        )

    # 3) Tab path: #person-filter → people list → #person-timeline.
    #    Undo / Open other archive must not remain default-tabbable between them.
    filter_m = re.search(r"id\s*=\s*[\"']person-filter[\"']", markup)
    list_m = _A11Y_ROLE_LISTBOX.search(markup) or _A11Y_ROLE_OPTION.search(markup)
    tl_m = re.search(r"id\s*=\s*[\"']person-timeline[\"']", markup)
    if not filter_m:
        fail("#214: keep #person-filter in the People shell (Tab starts there)")
    if not list_m:
        fail('#214: keep the people role="listbox" / option list in the People shell')
    if not tl_m:
        fail("#214: keep #person-timeline (Tab ends at the timeline after the selected person)")
    if not (filter_m.start() < list_m.start() < tl_m.start()):
        fail(
            "#214: Tab path must be #person-filter then people list then "
            "#person-timeline (filter → selected person → timeline)"
        )
    filter_win = markup[max(0, filter_m.start() - 160) : filter_m.end() + 160]
    if _A11Y_TABINDEX_NEG.search(filter_win):
        fail(
            "#214: #person-filter must stay in tab order "
            "(do not tabindex=\"-1\" the people filter)"
        )
    if not _sidebar_chrome_untabbable(markup):
        fail(
            "#214: undo / \"Open other archive\" must not stay default-tabbable "
            "between #person-filter and #person-timeline "
            '(tabindex="-1"; they stay clickable)'
        )

    # 4) INPUT/TEXTAREA/SELECT guard still returns before bare j/k (#q).
    if not _INPUT_TAG_GUARD.search(raw_body) and not _INPUT_TAG_GUARD.search(body):
        fail(
            "#214: keep the INPUT/TEXTAREA/SELECT guard "
            "(Search #q must never see bare j/k)"
        )
    guard_span = _input_guard_span(raw_body)
    if not guard_span:
        fail(
            "#214: INPUT/TEXTAREA/SELECT guard must still wrap the early return "
            "(Search #q never intercepted)"
        )
    guard = raw_body[guard_span[0] : guard_span[1] + 1]
    if not re.search(r"\breturn\b", guard):
        fail(
            "#214: INPUT/TEXTAREA/SELECT guard must return before bare j/k "
            "(Search #q never intercepted)"
        )
    pre = raw_body[: guard_span[0]]
    if _bare_letter_before_guard(pre, _KEY_J) or _bare_letter_before_guard(pre, _KEY_K):
        fail(
            "#214: do not handle bare j/k before the INPUT/TEXTAREA/SELECT guard "
            "— Search #q must not be intercepted"
        )
    if _bare_letter_before_guard(pre, _KEY_ARROW_EITHER):
        fail(
            "#214: do not handle bare ArrowDown/Up before the INPUT guard "
            "(#q / #person-filter must keep their caret)"
        )
    if not _KEY_J.search(raw_body) or not _KEY_K.search(raw_body):
        fail("#214: keep timeline j/k (letters still move messages; arrows may move the list)")

    # 5) Docs: arrows in people list; Tab filter → person → timeline;
    #    j/k still messages; Search #q not intercepted.
    if not dtxt.strip():
        fail(
            "#214: docs/user/app.md required — people-list arrows, Tab order, "
            "j/k on messages, Search #q not intercepted"
        )
    if not _DOCS_LIST_ARROWS.search(dtxt):
        fail(
            "#214: docs/user/app.md must say arrow keys in the people list "
            "change the selected person"
        )
    if not _DOCS_TAB_PATH.search(dtxt):
        fail(
            "#214: docs/user/app.md must document Tab order "
            "(filter → selected person → timeline)"
        )
    if not _DOCS_JK_MESSAGES.search(dtxt):
        fail("#214: docs/user/app.md must keep j/k on messages / the timeline")
    if not _DOCS_Q_SAFE.search(dtxt):
        fail(
            "#214: docs/user/app.md must say typing in Search #q is never intercepted"
        )

    # 6) Do not soften ⌘F, ⌘1–5, #q, sidebar, overlay, inspector, CSP.
    prefix, _tail = _split_people_only(raw_body)
    prefix_x = _expand_fn_calls(app_clean, prefix) if prefix.strip() else body
    if prefix_x == prefix:
        prefix_x = _expand_fn_calls(app, prefix) if prefix.strip() else body
    if not _KEY_F.search(prefix_x) and not _KEY_F.search(raw_body):
        fail("#214: keep ⌘F / ctrl+F Find (do not rewrite #132)")
    if not _has_mod_combo(prefix_x) and not _has_mod_combo(raw_body):
        fail(
            "#214: keep metaKey or ctrlKey on Find / tab digits "
            "(do not rewrite #132 ⌘F / ⌘1–5)"
        )
    for tok in _VIEW_TAB_ORDER:
        if not re.search(rf"[\"']{tok}[\"']", prefix_x) and not re.search(
            rf"[\"']{tok}[\"']", raw_body
        ):
            fail(
                f'#214: keep ⌘1–5 view "{tok}" '
                "(1 People … 5 Doctor — do not rewrite #132)"
            )
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#214: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#214: keep data-people-sidebar (#159 / #212)")
    if not re.search(r"\bdata-person-inspector\b", app):
        fail("#214: keep data-person-inspector (#213)")
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#214: keep the overlay titlebar (#211)")
    if CSP not in conf:
        fail("#214: do not soften tauri CSP")
