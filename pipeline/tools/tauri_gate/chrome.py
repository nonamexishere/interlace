"""Window / keyboard / locale chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    CSP,
    _A11Y_ROLE_LISTBOX,
    _A11Y_ROLE_OPTION,
    _A11Y_TABINDEX_NEG,
    _APPEARANCE_DOCS_ARCHIVAL,
    _APPEARANCE_DOCS_NO_THEME,
    _APPEARANCE_MENU_LABEL,
    _APPEARANCE_THEME_UI,
    _CHROME_PACK_NS,
    _CMD_PALETTE_PKG,
    _CONFIG_TOML,
    _CONTRAST_COLOR_SCHEME,
    _CONTRAST_DOCS_SYSTEM,
    _CONTRAST_SEARCH_MARK_NAMES,
    _DOCS_TYPO_NO_REMOTE_FONT,
    _FETCH_CALL,
    _FOCUS_SEARCH_Q,
    _HEIGHT_CACHE,
    _KEYMAP_CALL_SKIP,
    _KEY_ESC,
    _KEY_F,
    _LAST_PATH_API,
    _LS_BRACKET,
    _MOD_EITHER,
    _MOTION_DURATION_ZERO,
    _MOTION_JS_REDUCE,
    _PALETTE_HOOK,
    _SCROLL_HELPER_SKIP,
    _SECOND_UI_KIT,
    _STATUS_WARNING_NAMES,
    _THEME_CDN,
    _TYPO_FONT_SANS,
    _TYPO_REMOTE_FONT,
    _VIEW_SEARCH_ASSIGN,
    _WRITE_TEXT,
    _ancestor_tags,
    _app_keydown_body,
    _appearance_class_names,
    _call_arg,
    _chrome_en_text,
    _chrome_helper_names,
    _chrome_helper_on_body,
    _chrome_lang_text,
    _chrome_pack_files,
    _claim_without_negation,
    _contrast_dark_blob,
    _contrast_light_blob,
    _css_brace_body,
    _css_var,
    _css_without_comments,
    _empty_state_blocks,
    _expand_fn_calls,
    _function_body,
    _has_mod_combo,
    _hsl_tuple,
    _hue_findings,
    _hue_surface,
    _input_guard_span,
    _js_next,
    _ls_pref_keys,
    _markup_open_tag,
    _markup_uses_chrome_helper,
    _match_closer,
    _matched_inner,
    _motion_js_blob,
    _open_tag_before,
    _opening_tag,
    _owned_imported_names,
    _people_each_block,
    _people_list_a11y_surfaces,
    _product_svelte,
    _rust_fn_body,
    _split_people_only,
    _stem_chrome_lang,
    _strip_html_comments,
    _svelte_effect_args,
    _svelte_markup,
    _tag_inner,
    _tag_name,
    _tauri_rust_blob,
    _template_stack,
    _toml_keys_in_fn,
    _ts_fn_body,
    _ts_function_body,
    _web_logic,
    _web_pack_candidates,
    _web_sources,
    _windows_around,
    _without_comments,
    _without_input_guard,
)



# #129 — native window title follows open person / view (Cmd-tab).
# Separator: em dash (—) preferred; en dash / " - " / " --- " accepted if consistent.
_TITLE_SEP = r"(?:—|–|---| - )"
_SET_TITLE_CALL = re.compile(r"\bsetTitle\s*\(")
_WINDOW_API_IMPORT = re.compile(
    r"from\s+[\"']@tauri-apps/api/window[\"']"
    r"|import\s*\{[^}]*\b(?:getCurrentWindow|Window)\b[^}]*\}\s*from\s*[\"']@tauri-apps/api"
)
_GET_CURRENT_WINDOW = re.compile(r"\bgetCurrentWindow\s*\(")
_DOCK_BADGE_API = re.compile(
    r"("
    r"\bsetBadgeCount\b"
    r"|\bsetBadgeLabel\b"
    r"|\bsetOverlayIcon\b"
    r"|\bdock\s*\.\s*setBadge\b"
    r"|\bbadgeCount\b"
    r"|\bBadgeCount\b"
    r")",
)
# Message fields that must never flow into setTitle args / title helpers.
_TITLE_BODY_LEAK = re.compile(
    r"("
    r"\bbody_text\b"
    r"|\bsnippet\b"
    r"|\bdisplayBody\b"
    r"|\bsearchBody\b"
    r"|\blast_body\b"
    r"|\blastBody\b"
    r"|\blast_preview\b"
    r"|\bactivityPreview\b"
    r")",
)
_TITLE_HELPER_NAMES = (
    "windowTitle",
    "nativeTitle",
    "appTitle",
    "titleForView",
    "titleForWindow",
    "syncWindowTitle",
    "updateWindowTitle",
    "setWindowTitle",
    "computeWindowTitle",
    "formatWindowTitle",
)


def _title_path_sources(crate: Path) -> str:
    """Web logic that may own setTitle (App + helpers; exclude pure UI chrome)."""
    return _web_logic(crate)


def _collect_set_title_args(src: str) -> list[str]:
    args: list[str] = []
    for m in _SET_TITLE_CALL.finditer(src):
        open_paren = m.end() - 1
        if open_paren < 0 or src[open_paren] != "(":
            continue
        arg = _call_arg(src, open_paren)
        if arg is not None:
            args.append(arg)
    return args


def _title_helper_bodies(src: str) -> list[str]:
    bodies: list[str] = []
    for name in _TITLE_HELPER_NAMES:
        body = _function_body(src, name)
        if body:
            bodies.append(body)
    # $derived / const title = (...) => … / function expressions assigned to common names.
    for name in _TITLE_HELPER_NAMES:
        for m in re.finditer(
            rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?:\$derived(?:\.\w+)?\s*)?"
            rf"(?:\([^)]*\)\s*=>\s*|\([^)]*\)\s*=>\s*\{{|"
            rf"function\s*\([^)]*\)\s*\{{)?",
            src,
        ):
            # Prefer brace body via _function_body; also capture arrow expr after =.
            eq = src.find("=", m.start())
            if eq < 0:
                continue
            rest = src[eq + 1 : eq + 1 + 800].lstrip()
            if rest.startswith("$derived"):
                # $derived(expr) or $derived.by(() => …)
                dm = re.match(
                    r"\$derived(?:\.by)?\s*\(",
                    rest,
                )
                if dm:
                    arg = _call_arg(rest, dm.end() - 1)
                    if arg:
                        bodies.append(arg)
            elif rest.startswith("(") or rest.startswith("async"):
                pass  # covered by _function_body when brace form
            else:
                # Arrow/expression form: name = `…` / name = cond ? … : …
                end = rest.find("\n")
                chunk = rest if end < 0 else rest[: max(end, 200)]
                bodies.append(chunk)
    return bodies


def assert_window_title(crate: Path) -> None:
    """#129: native title Interlace | Ada — Interlace | Search — Interlace.

    Tauri window setTitle (getCurrentWindow from @tauri-apps/api/window). React
    to view + selected person display name. Setup/booting/no-archive stay
    bare Interlace. Never put message body/snippet into the title. Not dock
    badge counts.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#129: App.svelte required (window title follows view + selected person)")
    app = app_path.read_text()
    logic = _title_path_sources(crate)
    cleaned = _without_comments(app + "\n" + logic)
    conf_path = crate / "tauri.conf.json"
    conf = conf_path.read_text() if conf_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    pkg = (crate / "package.json").read_text() if (crate / "package.json").is_file() else ""

    # 1) Dependency + Tauri 2 window API import + setTitle call.
    if "@tauri-apps/api" not in pkg:
        fail("#129: @tauri-apps/api must remain a dependency (window setTitle)")
    if not _WINDOW_API_IMPORT.search(cleaned) and not re.search(
        r"@tauri-apps/api/window",
        cleaned,
    ):
        fail(
            "#129: import getCurrentWindow (or Window) from @tauri-apps/api/window "
            "— native title uses the Tauri window API, not document.title alone"
        )
    if not _GET_CURRENT_WINDOW.search(cleaned) and not re.search(
        r"\bgetCurrent\s*\(\s*\)"
        r"|\bWindow\s*\.\s*getByLabel\b"
        r"|\bappWindow\b",
        cleaned,
    ):
        fail(
            "#129: must obtain the current Tauri window "
            "(getCurrentWindow() or equivalent) before setTitle"
        )
    if not _SET_TITLE_CALL.search(cleaned):
        fail(
            "#129: App (or a small helper) must call setTitle(…) so Cmd-tab "
            "shows who you are looking at — static tauri.conf.json title is not enough"
        )

    # 2) Title format strings / builders: base Interlace; person; Search; other views.
    title_args = _collect_set_title_args(cleaned)
    helper_bodies = _title_helper_bodies(cleaned)
    title_surface = "\n".join(title_args + helper_bodies)
    if not title_surface.strip():
        title_surface = cleaned  # fall back: formats may live in open code near setTitle

    # Bare / default Interlace (setup, booting, people with no selection).
    # Scope to setTitle args / title helpers — App chrome already says "Interlace".
    title_path_blob = "\n".join(title_args + helper_bodies)
    if not title_path_blob.strip():
        # Inline setTitle regions only (not whole App header copy).
        title_path_blob = "\n".join(
            cleaned[max(0, m.start() - 500) : m.end() + 300]
            for m in _SET_TITLE_CALL.finditer(cleaned)
        )
    has_bare = bool(
        re.search(
            r"("
            r"setTitle\s*\(\s*[\"']Interlace[\"']\s*\)"
            r"|return\s+[\"']Interlace[\"']"
            r"|:\s*[\"']Interlace[\"']"
            r"|\?\s*[\"']Interlace[\"']"
            r"|\|\|\s*[\"']Interlace[\"']"
            r"|=\s*[\"']Interlace[\"']"
            r"|[\"']Interlace[\"']\s*;"
            r")",
            title_path_blob + "\n" + "\n".join(helper_bodies),
        )
    )
    # Constant used only by the title path: const APP_TITLE = "Interlace" near setTitle.
    if not has_bare:
        for m in re.finditer(
            r"(?:const|let|var)\s+\w+\s*=\s*[\"']Interlace[\"']",
            cleaned,
        ):
            window = cleaned[max(0, m.start() - 200) : m.end() + 400]
            if _SET_TITLE_CALL.search(window) or any(n in window for n in _TITLE_HELPER_NAMES):
                has_bare = True
                break
    if not has_bare:
        fail(
            "#129: default/base native title must be bare Interlace "
            "(setup, booting, no archive, People with no person selected)"
        )

    # Person selected: {name} — Interlace (placeholder names; use personTitle / display_name).
    person_name_tok = (
        r"(?:personTitle|display_name|displayName|personName|selectedName|"
        r"selectedPersonName|openPersonName)"
    )
    person_in_title = bool(
        re.search(
            rf"("
            rf"{person_name_tok}\b[^;\n]{{0,120}}{_TITLE_SEP}[^;\n]{{0,40}}Interlace"
            rf"|`\$\{{{person_name_tok}[^}}]{{0,40}}\}}\s*{_TITLE_SEP}\s*Interlace`"
            rf"|{person_name_tok}\s*\+\s*[\"']\s*{_TITLE_SEP}\s*Interlace"
            rf"|[\"']\s*{_TITLE_SEP}\s*Interlace[\"']\s*\+\s*{person_name_tok}"
            rf")",
            title_surface + "\n" + cleaned,
        )
    )
    if not person_in_title:
        fail(
            "#129: with a person selected, native title must be "
            "`{display_name} — Interlace` (em dash preferred; personTitle / display_name, "
            "not a raw person id)"
        )

    # Search tab (and other chrome tabs when present).
    def _literal_view_title(label: str) -> bool:
        """True if the fixed `{Label} — Interlace` string (or concat) appears."""
        return bool(
            re.search(
                rf"[\"'`]{re.escape(label)}\s*{_TITLE_SEP}\s*Interlace[\"'`]"
                rf"|[\"'`]{re.escape(label)}[\"'`]\s*\+\s*[\"']\s*{_TITLE_SEP}\s*Interlace"
                rf"|[\"']\s*{_TITLE_SEP}\s*Interlace[\"']\s*\+\s*[\"'`]{re.escape(label)}",
                title_surface + "\n" + cleaned,
            )
        )

    def _mapped_view_title(label: str) -> bool:
        """True if view token maps to Label and a View — Interlace builder exists."""
        view_token = label.lower()
        # Prefer title helper / setTitle args — not the whole App (platform chips
        # already use charAt().toUpperCase for WhatsApp/Gmail labels).
        map_surface = title_surface if title_surface.strip() and title_surface != cleaned else ""
        if not map_surface:
            # Narrow to regions that mention setTitle or a title helper name.
            chunks: list[str] = []
            for m in _SET_TITLE_CALL.finditer(cleaned):
                chunks.append(cleaned[max(0, m.start() - 600) : m.end() + 400])
            for name in _TITLE_HELPER_NAMES:
                body = _function_body(cleaned, name)
                if body:
                    chunks.append(body)
                for dm in re.finditer(
                    rf"(?:const|let|var)\s+{re.escape(name)}\b",
                    cleaned,
                ):
                    chunks.append(cleaned[dm.start() : dm.start() + 900])
            map_surface = "\n".join(chunks) if chunks else cleaned
        has_sep_builder = bool(
            re.search(rf"{_TITLE_SEP}\s*Interlace", map_surface + "\n" + title_surface)
        )
        # Explicit map entry: search: "Search" / case "search": return "Search" …
        explicit = bool(
            re.search(
                rf"("
                rf"(?:case\s+[\"']{view_token}[\"']|[\"']{view_token}[\"']\s*:)\s*"
                rf"[^;\n]{{0,100}}[\"']{re.escape(label)}[\"']"
                rf"|[\"']{view_token}[\"']\s*[^\n]{{0,40}}[\"']{re.escape(label)}[\"']"
                rf")",
                map_surface + "\n" + title_surface,
                re.I,
            )
        )
        # Capitalizer only counts when it appears in the title path and reads `view`.
        capitalizer = bool(
            re.search(
                r"("
                r"charAt\s*\(\s*0\s*\)\s*\.\s*toUpperCase"
                r"|\.toUpperCase\s*\(\s*\)\s*\+\s*\w+\.slice"
                r"|capitalize\s*\(\s*view"
                r"|titleCase\s*\(\s*view"
                r"|viewLabel"
                r"|VIEW_TITLE"
                r"|viewTitles"
                r")",
                map_surface,
                re.I,
            )
        ) and bool(re.search(r"\bview\b", map_surface)) and has_sep_builder
        return has_sep_builder and (explicit or bool(capitalizer))

    if not _literal_view_title("Search") and not _mapped_view_title("Search"):
        fail(
            "#129: Search tab native title must be `Search — Interlace` "
            "(Cmd-tab must show the open view)"
        )

    for label in ("Review", "Import", "Doctor"):
        # Soft: if the view enum still has the tab, title path must cover it.
        view_token = label.lower()
        if re.search(rf"[\"']{view_token}[\"']", app) or re.search(
            rf"view\s*===?\s*[\"']{view_token}[\"']",
            cleaned,
        ):
            if not _literal_view_title(label) and not _mapped_view_title(label):
                fail(
                    f"#129: {label} tab native title must be `{label} — Interlace` "
                    f"(same View — Interlace pattern as Search)"
                )

    # People with no selection stays Interlace (not forced "People — Interlace"
    # unless they also keep bare Interlace as default — issue prefers bare).
    # If they emit "People — Interlace" that is OK only alongside person + Search forms.

    # 3) React to view + selected person (Svelte 5 $effect or equivalent).
    # Require an $effect (or title-derived) path that actually calls setTitle / a
    # title helper — mere presence of unrelated $effect + view state is not enough.
    effect_ok = False
    for m in re.finditer(r"\$effect\s*\(", cleaned):
        arg = _call_arg(cleaned, m.end() - 1)
        if not arg:
            continue
        uses_helper = bool(
            any(n in arg for n in _TITLE_HELPER_NAMES)
            or re.search(r"\b(?:windowTitle|nativeTitle|appTitle|syncWindowTitle)\b", arg)
        )
        calls_set = bool(_SET_TITLE_CALL.search(arg))
        if not (calls_set or uses_helper):
            continue
        # Inline effect: must read view and person name.
        reads_view = bool(re.search(r"\bview\b", arg))
        reads_person = bool(
            re.search(r"\b(personTitle|display_name|selectedId|selectedPerson)\b", arg)
        )
        # $effect(() => setTitle(windowTitle)) — helper encodes view+person (format checks).
        if uses_helper and calls_set:
            effect_ok = True
            break
        if uses_helper and not calls_set:
            # syncWindowTitle() inside effect — helper body must call setTitle (checked via names).
            effect_ok = True
            break
        if calls_set and reads_view and reads_person:
            effect_ok = True
            break
    # $derived windowTitle that depends on view + person, applied somewhere with setTitle.
    derived_bodies = _title_helper_bodies(cleaned)
    derived_tracks = any(
        re.search(r"\bview\b", b)
        and re.search(r"\b(personTitle|display_name|selectedId)\b", b)
        for b in derived_bodies
    )
    has_derived_name = bool(
        re.search(
            r"(?:const|let)\s+(?:windowTitle|nativeTitle|appTitle)\s*=\s*\$derived",
            cleaned,
        )
    )
    if not effect_ok and not (has_derived_name and derived_tracks and _SET_TITLE_CALL.search(cleaned)):
        # Last resort: setTitle call site closed over both deps (same function / effect region).
        near_both = False
        for m in _SET_TITLE_CALL.finditer(cleaned):
            window = cleaned[max(0, m.start() - 500) : m.end() + 240]
            if re.search(r"\bview\b", window) and re.search(
                r"\b(personTitle|display_name|selectedId)\b",
                window,
            ):
                near_both = True
                break
        if not near_both:
            fail(
                "#129: setTitle must react to view + selected person name changes "
                "($effect reading view / personTitle and calling setTitle, "
                "or a $derived windowTitle applied via setTitle)"
            )

    # 4) Ban message body / snippet / query string in the title path.
    leak_surfaces = title_args + helper_bodies
    if not leak_surfaces:
        # Scan ~200 chars around each setTitle for body fields.
        for m in _SET_TITLE_CALL.finditer(cleaned):
            leak_surfaces.append(cleaned[max(0, m.start() - 120) : m.end() + 200])
    for chunk in leak_surfaces:
        if _TITLE_BODY_LEAK.search(chunk):
            fail(
                "#129: never put message body / snippet / body_text into setTitle "
                "(Cmd-tab shows person or view name only — not chat text)"
            )
    # Filter / search query must not become the window title either.
    for chunk in title_args:
        if re.search(r"\b(?:filter|query|q|searchQuery)\b", chunk) and not re.search(
            r"Search\s*(?:—|–|---| - )\s*Interlace",
            chunk,
        ):
            # Only fail if the arg interpolates the query, not the word Search.
            if re.search(
                r"(\$\{[^}]*(?:filter|query|searchQuery)|(?:filter|query|searchQuery)\s*\+)",
                chunk,
            ):
                fail(
                    "#129: do not put the search query string in the native title "
                    "(fixed `Search — Interlace`, not the typed query)"
                )

    # 5) Not in scope: dock badge counts.
    if _DOCK_BADGE_API.search(cleaned):
        fail(
            "#129: do not set dock badge counts "
            "(out of scope — native title only, not setBadgeCount / badge APIs)"
        )

    # 6) Static conf title remains a sensible default (Interlace).
    if conf and not re.search(r"[\"']title[\"']\s*:\s*[\"']Interlace[\"']", conf):
        fail(
            '#129: tauri.conf.json default window title should stay "Interlace" '
            "(runtime setTitle overrides per view/person)"
        )

    # 7) User-visible: one line in docs/user/app.md.
    if not re.search(
        r"("
        r"window title"
        r"|native title"
        r"|Cmd-?tab"
        r"|title bar"
        r"|title follows"
        r")",
        dtxt,
        re.I,
    ):
        fail(
            "#129: docs/user/app.md must mention the native window title "
            "(follows open person / view — e.g. Ada — Interlace)"
        )


# #130 — native macOS menu (About/Quit, File Open+Import, View tabs). No updater.
_TAURI_MENU_API = re.compile(
    r"("
    r"tauri::menu::"
    r"|MenuBuilder"
    r"|SubmenuBuilder"
    r"|MenuItemBuilder"
    r"|PredefinedMenuItem"
    r"|CheckMenuItemBuilder"
    r"|@tauri-apps/api/menu"
    r")",
)
_MENU_ATTACH = re.compile(
    r"("
    r"\.menu\s*\("
    r"|\.set_menu\s*\("
    r"|\bset_menu\s*\("
    r"|\bsetMenu\s*\("
    r"|\bsetAsAppMenu\s*\("
    r"|\bsetAsWindowMenu\s*\("
    r")",
)
_ABOUT_ITEM = re.compile(
    r"("
    r"PredefinedMenuItem::about"
    r"|\.about\s*\("
    r"|item\s*:\s*[\"']About[\"']"
    r"|[\"']About(?: Interlace)?[\"']"
    r")",
)
_QUIT_ITEM = re.compile(
    r"("
    r"PredefinedMenuItem::quit"
    r"|\.quit\s*\("
    r"|item\s*:\s*[\"']Quit[\"']"
    r"|[\"']Quit(?: Interlace)?[\"']"
    r")",
)
_FILE_SUBMENU = re.compile(r"[\"']File[\"']")
_VIEW_SUBMENU = re.compile(r"[\"']View[\"']")
_OPEN_ITEM = re.compile(
    r"[\"']("
    r"Open archive"
    r"|Open existing(?:…|\.\.\.)?"
    r"|Open(?:…|\.\.\.)?"
    r"|open-archive"
    r"|open_archive"
    r"|file-open"
    r"|menu-open"
    r")[\"']",
    re.I,
)
_IMPORT_ITEM = re.compile(
    r"[\"']("
    r"Import(?:…|\.\.\.)?"
    r"|file-import"
    r"|menu-import"
    r"|import-archive"
    r")[\"']",
)
_CHECK_UPDATES_ITEM = re.compile(
    r"[\"']Check for [Uu]pdates?[\"']"
    r"|PredefinedMenuItem::check_for_updates"
    r"|tauri_plugin_updater"
    r"|plugin-updater"
    r"|UpdaterExt",
)
_PREFERENCES_ITEM = re.compile(
    r"("
    r"PredefinedMenuItem::preferences"
    r"|[\"']Preferences(?:…|\.\.\.)?[\"']"
    r"|[\"']Settings(?:…|\.\.\.)?[\"']"
    r"|PreferencesWindow"
    r"|open_preferences"
    r")",
)
_ICLOUD_MENU_ITEM = re.compile(
    r"[\"'][^\"']*iCloud[^\"']*[\"']",
    re.I,
)
_ABOUT_ANCHOR = re.compile(
    r"("
    r"AboutMetadata"
    r"|PredefinedMenuItem::about"
    r"|\.about\s*\("
    r"|[\"']About(?: Interlace)?[\"']"
    r"|(?:const|static|let)\s+ABOUT\w*"
    r")",
)
_MENU_HANDLER_NAMES = (
    "on_menu_event",
    "handle_menu_event",
    "handle_menu",
    "menu_event",
    "applyMenu",
    "onMenu",
    "onMenuEvent",
    "handleMenu",
)
_LISTEN_CALL = re.compile(
    r"\b(?:listen|once|onMenuEvent)\s*\(",
)
_VIEW_MENU_TOKENS = ("people", "search", "review", "doctor")
_ABOUT_OFFLINE = re.compile(r"\boffline\b", re.I)
_ABOUT_NOT_ENCRYPTED = re.compile(r"not encrypted at rest", re.I)
_ABOUT_FILEVAULT = re.compile(r"\bFileVault\b")
_DOCS_MENU = re.compile(
    r"("
    r"native menu"
    r"|menu bar"
    r"|File menu"
    r"|macOS menu"
    r"|Open archive"
    r")",
    re.I,
)


def _menu_web_blob(crate: Path) -> str:
    """Web sources that build a Tauri menu (not the in-window nav / bits-ui menus)."""
    parts: list[str] = []
    web = crate / "web"
    if not web.is_dir():
        return ""
    for p in sorted(web.rglob("*")):
        if p.suffix not in {".svelte", ".ts", ".js"} or "node_modules" in p.parts:
            continue
        text = p.read_text()
        if (
            "@tauri-apps/api/menu" in text
            or "PredefinedMenuItem" in text
            or "MenuItem.new" in text
            or "Menu.new" in text
        ):
            parts.append(text)
    return "\n".join(parts)


def _on_menu_event_bodies(src: str) -> list[str]:
    bodies: list[str] = []
    for m in re.finditer(r"\.on_menu_event\s*\(", src):
        arg = _call_arg(src, m.end() - 1)
        if arg:
            bodies.append(arg)
    for name in _MENU_HANDLER_NAMES:
        body = _function_body(src, name)
        if body:
            bodies.append(body)
    return bodies


def _listen_bodies(src: str) -> list[str]:
    bodies: list[str] = []
    for m in _LISTEN_CALL.finditer(src):
        open_paren = src.find("(", m.start())
        if open_paren < 0:
            continue
        arg = _call_arg(src, open_paren)
        if arg:
            bodies.append(arg)
    return bodies


def _menu_handler_surface(rust: str, web: str) -> str:
    """Rust on_menu_event + frontend listen / menu-handler bodies (and one callee)."""
    chunks = _on_menu_event_bodies(rust) + _listen_bodies(web)
    seen = set(_MENU_HANDLER_NAMES)
    extra: list[str] = []
    blob = "\n".join(chunks)
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", blob):
        name = m.group(1)
        if name in seen or name in _SCROLL_HELPER_SKIP:
            continue
        seen.add(name)
        body = _function_body(web, name) or _function_body(rust, name)
        if body:
            extra.append(body)
    return "\n".join(chunks + extra)


def _about_copy_surface(rust: str, web_menu: str) -> str:
    chunks: list[str] = []
    for src in (rust, web_menu):
        if not src:
            continue
        for m in _ABOUT_ANCHOR.finditer(src):
            chunks.append(src[max(0, m.start() - 200) : m.end() + 900])
    return "\n".join(chunks)


def _quoted_view_token(blob: str, token: str) -> bool:
    return bool(
        re.search(
            rf"("
            rf"view\s*=\s*[\"']{token}[\"']"
            rf"|[\"'](?:view-|menu-)?{token}[\"']"
            rf")",
            blob,
        )
    )


def assert_macos_menu(crate: Path) -> None:
    """#130: native macOS menu — About/Quit, File Open+Import, View tabs; no updater."""
    rust = _tauri_rust_blob(crate)
    web_all = _web_logic(crate)
    web_menu = _menu_web_blob(crate)
    menu_src = rust + "\n" + web_menu
    app_path = crate / "web" / "App.svelte"
    app = app_path.read_text() if app_path.is_file() else ""
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    deny_path = crate / "deny.toml"
    deny = deny_path.read_text() if deny_path.is_file() else ""
    docs_app = repo_root() / "docs" / "user" / "app.md"
    docs_tauri = repo_root() / "docs" / "hacking" / "tauri.md"
    dtxt = (docs_app.read_text() if docs_app.is_file() else "") + "\n" + (
        docs_tauri.read_text() if docs_tauri.is_file() else ""
    )
    caps_path = crate / "capabilities" / "default.json"
    caps = caps_path.read_text() if caps_path.is_file() else ""

    # 1) Native Tauri menu construction (not the default app menu, not HTML nav).
    if not _TAURI_MENU_API.search(menu_src):
        fail(
            "#130: native macOS menu must be built with Tauri Menu / MenuBuilder / "
            "PredefinedMenuItem (or @tauri-apps/api/menu), not the default app menu alone"
        )

    if not _MENU_ATTACH.search(rust) and not _MENU_ATTACH.search(web_menu):
        fail(
            "#130: the constructed menu must be attached to the app "
            "(.menu(...) / set_menu / setMenu) — building items and never installing "
            "them leaves the default macOS menu"
        )

    if "@tauri-apps/api/menu" in web_menu and "core:menu" not in caps:
        fail(
            "#130: JS @tauri-apps/api/menu needs a core:menu capability "
            "(or build the menu in Rust)"
        )

    # 2) App menu: About + Quit (predefined preferred; custom About Interlace / Quit OK).
    if not _ABOUT_ITEM.search(menu_src):
        fail(
            "#130: app menu must include About "
            "(PredefinedMenuItem::about / About Interlace)"
        )
    if not _QUIT_ITEM.search(menu_src):
        fail(
            "#130: app menu must include native Quit "
            "(PredefinedMenuItem::quit — not a custom network-y exit)"
        )

    # 3) File: Open archive + Import.
    if not _FILE_SUBMENU.search(menu_src):
        fail('#130: File submenu required (Open archive + Import)')
    if not _OPEN_ITEM.search(menu_src):
        fail(
            "#130: File menu must include Open archive "
            "(same folder picker as the in-window Open existing… button)"
        )
    if not _IMPORT_ITEM.search(menu_src):
        fail("#130: File menu must include Import")

    # 4) View: People, Search, Review, Doctor (Import may live under File only).
    if not _VIEW_SUBMENU.search(menu_src):
        fail("#130: View submenu required (People, Search, Review, Doctor)")
    for label in ("People", "Search", "Review", "Doctor"):
        if not re.search(rf"[\"']{label}[\"']", menu_src):
            fail(
                f"#130: View menu must include {label} "
                "(same view token as the in-window nav buttons)"
            )

    # 5) About copy: offline + not encrypted at rest + FileVault (About surface, not Doctor).
    about_src = _about_copy_surface(rust, web_menu)
    if not about_src.strip():
        fail(
            "#130: About copy must live on the About item / AboutMetadata "
            "(offline, not encrypted at rest, FileVault — same honesty as Doctor)"
        )
    if not _ABOUT_OFFLINE.search(about_src):
        fail("#130: About copy must say the app is offline")
    if not _ABOUT_NOT_ENCRYPTED.search(about_src):
        fail("#130: About copy must say not encrypted at rest")
    if not _ABOUT_FILEVAULT.search(about_src):
        fail("#130: About copy must mention FileVault")
    if re.search(r"https?://", about_src):
        fail(
            "#130: About must stay offline — no website / http(s) URL on the About item"
        )

    # 6) Open uses the same picker path (pick_folder / openPicker), not a remote open.
    handlers = _menu_handler_surface(rust, web_all)
    if not handlers.strip():
        fail(
            "#130: menu Open must be wired (on_menu_event and/or a frontend listen) "
            "to the existing folder picker — pick_folder / openPicker"
        )
    open_wired = bool(
        re.search(r"\bpick_folder\b", handlers)
        or re.search(r"\bopenPicker\b", handlers)
        or re.search(r"\bpickFolder\b", handlers)
    )
    if not open_wired:
        fail(
            "#130: menu Open must call the same folder picker as the UI button "
            "(openPicker / pickFolder / pick_folder), not a new remote/URL open"
        )
    if re.search(r"https?://", handlers) or re.search(
        r"\b(?:webbrowser|open::that|opener::)\b", handlers
    ):
        fail("#130: menu handlers must not open a remote URL")

    # 7) Import: same Import-tab picker, or switch to Import + existing flow.
    import_wired = bool(
        re.search(r"\bpick_import_path\b", handlers)
        or re.search(r"\bpickImportPath\b", handlers)
        or re.search(r"view\s*=\s*[\"']import[\"']", handlers)
        or re.search(r"[\"'](?:view-|menu-)?import[\"']", handlers)
    )
    if not import_wired:
        fail(
            "#130: menu Import must use pick_import_path / pickImportPath "
            "or switch view to import (existing Import tab flow)"
        )

    # 8) View items set the same `view` tokens as the nav buttons.
    if not re.search(r"\bview\s*=", handlers) and not any(
        _quoted_view_token(handlers, tok) for tok in _VIEW_MENU_TOKENS
    ):
        fail(
            "#130: View menu items must set `view` the same as the nav buttons "
            "(people / search / review / doctor) via on_menu_event emit + listen"
        )
    for tok in _VIEW_MENU_TOKENS:
        if not _quoted_view_token(handlers, tok):
            fail(
                f"#130: View menu must switch to {tok} "
                "(same view token as the in-window nav)"
            )

    # 9) Bans: Check for Updates, updater plugin, Preferences window, iCloud menu.
    if _CHECK_UPDATES_ITEM.search(menu_src) or _CHECK_UPDATES_ITEM.search(handlers):
        fail("#130: no Check for Updates menu item (and no updater plugin)")
    if "tauri-plugin-updater" in toml:
        fail("#130: tauri-plugin-updater must not be a dependency")
    if "tauri-plugin-updater" not in deny:
        fail(
            "#130: crates/interlace-tauri/deny.toml must keep banning "
            "tauri-plugin-updater"
        )
    if _PREFERENCES_ITEM.search(menu_src):
        fail("#130: no Preferences / Settings window or menu item (out of scope)")
    if _ICLOUD_MENU_ITEM.search(menu_src):
        fail("#130: no iCloud / iCloud Drive menu item (out of scope)")

    # 10) User-visible: one line in docs/user/app.md and/or docs/hacking/tauri.md.
    if not _DOCS_MENU.search(dtxt):
        fail(
            "#130: docs/user/app.md and/or docs/hacking/tauri.md must mention "
            "the native menu (File → Open archive; no Check for Updates)"
        )

    # Keep using the existing in-window picker — do not drop openPicker.
    if "openPicker" not in app and "pickFolder" not in web_all:
        fail(
            "#130: keep the in-window openPicker / pickFolder path "
            "(menu Open must share it, not replace it with a second picker)"
        )
_WA_PARSER_KEYS = frozenset(
    {
        "id",
        "family_hints",
        "you_tokens",
        "date_time_patterns",
        "media_omitted",
        "file_attached_pattern",
        "file_attached_alt",
        "forwarded_tokens",
        "title_prefixes_dm",
        "title_prefixes_group",
        "system_created_group",
        "system_added",
        "system_subject",
        "system_encryption",
        "encryption_banner_startswith",
    }
)
_WA_UI_BAN = ("Arşiv aç", "Open existing", "Open an archive")
_EN_EMPTY_TITLES = (
    "No people yet",
    "Select a person",
    "No doctor issues",
    "Nothing to review",
    "Type a query",
    "No hits",
)
_OS_LOCALE_READ = re.compile(
    r"("
    r"navigator\.language"
    r"|navigator\.languages"
    r"|Intl\.DateTimeFormat\s*\("
    r"|resolvedOptions\s*\(\s*\)\s*\.\s*locale"
    r"|@tauri-apps/plugin-os"
    r"|\bosLocale\b"
    r"|\bgetLocale\s*\("
    r"|\blocaleIdentifier\b"
    r")",
)
_TR_STAR_PICK = re.compile(
    r"("
    r"startsWith\s*\(\s*[\"']tr"
    r"|starts_with\s*\(\s*[\"']tr"
    r"|slice\s*\(\s*0\s*,\s*2\s*\)\s*===?\s*[\"']tr[\"']"
    r"|substring\s*\(\s*0\s*,\s*2\s*\)\s*===?\s*[\"']tr[\"']"
    r"|===?\s*[\"']tr[\"']"
    r"|===?\s*[\"']tr-[A-Za-z]{2}[\"']"
    r"|/\^tr/i?"
    r"|match\s*\(\s*/\^tr"
    r")",
)
_EN_DEFAULT_PICK = re.compile(
    r"("
    r":\s*[\"']en[\"']"
    r"|\|\|\s*[\"']en[\"']"
    r"|\?\?\s*[\"']en[\"']"
    r"|else\s+[\"']en[\"']"
    r"|return\s+[\"']en[\"']"
    r"|fallback(?:Locale|Lang|Pack)?\s*[:=]\s*[\"']en[\"']"
    r"|default(?:Locale|Lang|Pack)?\s*[:=]\s*[\"']en[\"']"
    r"|\?\s*[\"']tr[\"']\s*:\s*[\"']en[\"']"
    r")",
)
_CHROME_OVERRIDE_UI = re.compile(
    r"("
    r"\bchromeLocale\b"
    r"|\buiLocale\b"
    r"|\buiLanguage\b"
    r"|\bdisplayLanguage\b"
    r"|[\"']UI language[\"']"
    r"|[\"']Display language[\"']"
    r"|[\"']App language[\"']"
    r"|[\"']Chrome language[\"']"
    r")",
    re.I,
)
_DIR_RTL = re.compile(r"\bdir\s*=\s*[\"']rtl[\"']", re.I)


def _chrome_tr_text(crate: Path) -> str:
    return _chrome_lang_text(crate, "tr")


def _control_inners(src: str, needle: re.Pattern[str], tags: tuple[str, ...] = ("Button", "button")) -> list[str]:
    """Inner HTML of a Button/button whose open tag (or nearby) matches needle.

    Closing tags may split across lines (`</Button\\n>`).
    """
    inners: list[str] = []
    for m in needle.finditer(src):
        before = src[: m.start()]
        open_idx = -1
        tag_found = ""
        for tag in tags:
            idx = before.lower().rfind("<" + tag.lower())
            if idx > open_idx:
                open_idx = idx
                tag_found = tag
        if open_idx < 0 or m.start() - open_idx > 900:
            continue
        gt = src.find(">", open_idx)
        if gt < 0:
            continue
        close_m = re.search(rf"</{re.escape(tag_found)}\s*>", src[gt:], re.I)
        if not close_m:
            continue
        inners.append(src[gt + 1 : gt + close_m.start()])
    return inners


def _nav_block(src: str) -> str:
    m = re.search(r"<nav\b[^>]*>(.*?)</nav>", src, re.S | re.I)
    return m.group(0) if m else ""


def _locale_resolver_surface(src: str) -> str:
    """Windows around OS-locale reads / named resolvers — not pack dictionaries."""
    chunks: list[str] = []
    for m in _OS_LOCALE_READ.finditer(src):
        chunks.append(src[max(0, m.start() - 400) : m.end() + 500])
    for name in (
        "resolveLocale",
        "chromeLocale",
        "pickLocale",
        "detectLocale",
        "localeFromOs",
        "osLang",
        "chromeLang",
        "resolvedLocale",
        "uiLang",
    ):
        body = _function_body(src, name)
        if body:
            chunks.append(body)
        for dm in re.finditer(rf"(?:const|let|var|function)\s+{re.escape(name)}\b", src):
            chunks.append(src[dm.start() : dm.start() + 800])
    return "\n".join(chunks)


def _heading_inners(src: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"<h1\b[^>]*>(.*?)</h1>", src, re.S | re.I)]


def _toml_top_keys(text: str) -> set[str]:
    return set(re.findall(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", text, re.M))


def _assert_wa_locale_not_chrome(root: Path) -> None:
    """UI chrome must not land in WhatsApp/Gmail parser packs."""
    for rel in (
        Path("crates") / "interlace-fixtures" / "locale",
        Path("crates") / "interlace-core" / "locale",
    ):
        folder = root / rel
        if not folder.is_dir():
            continue
        for p in sorted(folder.iterdir()):
            if not p.is_file():
                continue
            loc = p.relative_to(root)
            if p.suffix != ".toml":
                fail(
                    f"#131: {loc} is not a WA parser pack — "
                    "do not add UI chrome files under interlace-fixtures/locale "
                    "(or core locale copies)"
                )
            text = p.read_text()
            extra = _toml_top_keys(text) - _WA_PARSER_KEYS
            if extra:
                fail(
                    f"#131: do not add UI chrome keys to WA locale pack {loc}: "
                    f"{sorted(extra)} — chrome lives under crates/interlace-tauri/web/"
                )
            for s in _WA_UI_BAN:
                if s in text:
                    fail(
                        f"#131: do not put UI chrome string {s!r} in WA locale pack {loc}"
                    )


def assert_chrome_locale(crate: Path) -> None:
    """#131: en+tr UI chrome packs; OS locale; not bodies; not WA packs.

    Ship chrome strings (nav, setup Open archive, doctor, empty states, backup
    banner, common buttons) as en + tr packs under web/. Resolve from the OS
    locale: tr / tr-TR → tr, everything else → en. Message bodies stay stored.
    English remains the default so existing doctor / empty / backup greps pass.
    """
    root = repo_root()
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#131: App.svelte required (setup Open archive + nav Doctor chrome)")
    app = app_path.read_text()
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    doctor = doctor_path.read_text() if doctor_path.is_file() else ""
    logic = _web_logic(crate)
    cleaned = _without_comments(logic)
    docs = root / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) en + tr chrome packs under web/ (json / ts / toml) — not WA fixture toml.
    en_files, tr_files, combined = _chrome_pack_files(crate)
    if not en_files and not combined:
        fail(
            "#131: English UI chrome pack missing under crates/interlace-tauri/web/ "
            "(en.json / en.ts / en.toml, or a combined chrome/i18n module) — "
            "not interlace-fixtures/locale/*.toml"
        )
    if not tr_files and not combined:
        fail(
            "#131: Turkish UI chrome pack missing under crates/interlace-tauri/web/ "
            "(tr.json / tr.ts / tr.toml, or a combined chrome/i18n module) — "
            "not interlace-fixtures/locale/*.toml"
        )
    en_text = _chrome_en_text(crate)
    tr_text = _chrome_tr_text(crate)
    if not en_text.strip():
        fail("#131: English chrome pack is empty")
    if not tr_text.strip():
        fail("#131: Turkish chrome pack is empty")

    # 2) Resolver follows OS locale; tr* → tr, else en (English default).
    if not _OS_LOCALE_READ.search(cleaned) and not _OS_LOCALE_READ.search(logic):
        fail(
            "#131: chrome locale must follow the OS "
            "(navigator.language / navigator.languages / Intl / Tauri locale) — "
            "not the Import pane WhatsApp/Gmail probe `locale` field"
        )
    resolver = _locale_resolver_surface(cleaned) or _locale_resolver_surface(logic)
    if not _TR_STAR_PICK.search(resolver):
        fail(
            "#131: OS locale tr / tr-TR / tr* must select the tr chrome pack "
            "(startsWith('tr') or equivalent, next to the OS locale read)"
        )
    if not _EN_DEFAULT_PICK.search(resolver):
        fail(
            "#131: every non-tr OS locale must fall back to the en chrome pack "
            "(English is the default so existing fixture/gate copy still passes)"
        )

    # 3) Acceptance strings in the tr pack.
    if "Arşiv aç" not in tr_text:
        fail('#131: tr chrome pack must contain “Arşiv aç” (Open archive / Open existing)')
    if "Doktor" not in tr_text:
        fail('#131: tr chrome pack must contain “Doktor” (Doctor nav + pane title)')

    # 4) English pack keeps the acceptance keys (default / fixtures).
    if not re.search(r"[\"']Doctor[\"']", en_text) and "Doctor" not in en_text:
        fail(
            "#131: en chrome pack must contain “Doctor” "
            "(English default — existing doctor chrome gates stay green)"
        )
    if not re.search(
        r"Open(?: an)? archive|Open existing",
        en_text,
        re.I,
    ):
        fail(
            "#131: en chrome pack must contain “Open archive” / “Open existing” "
            "(English default for setup)"
        )

    # 5) App setup/nav uses the chrome helper — not only hardcoded English.
    helpers = _chrome_helper_names(logic)
    if not helpers and not any(
        re.search(rf"\b{re.escape(n)}\.\w+", logic) for n in _CHROME_PACK_NS
    ):
        fail(
            "#131: App/setup/nav must use a chrome helper "
            "(t / chromeT / i18n / imported chrome pack) — "
            "not only hardcoded English “Open existing…” / “Doctor”"
        )

    open_inners = _control_inners(app, re.compile(r"\bopenPicker\b"))
    if not open_inners:
        open_inners = _control_inners(app, re.compile(r"\bopenPath\b|\bpickFolder\b"))
    if not open_inners:
        fail(
            "#131: setup Open archive / Open existing control missing "
            "(openPicker button must show the chrome string)"
        )
    if not any(_markup_uses_chrome_helper(inner, helpers, logic) for inner in open_inners):
        fail(
            "#131: setup Open archive / Open existing must use the chrome helper "
            "(tr-TR shows “Arşiv aç” — not only hardcoded English on openPicker)"
        )

    nav = _nav_block(app)
    nav_inners = _control_inners(nav or app, re.compile(r"view\s*=\s*[\"']doctor[\"']"))
    if not nav_inners:
        fail(
            "#131: nav Doctor button missing "
            "(in-window nav must use the chrome helper for “Doktor”)"
        )
    if not any(_markup_uses_chrome_helper(inner, helpers, logic) for inner in nav_inners):
        fail(
            "#131: nav Doctor must use the chrome helper "
            "(tr-TR shows “Doktor” — not only hardcoded English)"
        )

    # Doctor pane title (acceptance: nav + pane).
    if doctor:
        doc_headings = _heading_inners(doctor)
        if not doc_headings:
            fail("#131: Doctor pane must keep a title heading (chrome “Doktor” / “Doctor”)")
        if not any(_markup_uses_chrome_helper(inner, helpers, logic) for inner in doc_headings):
            fail(
                "#131: Doctor pane title must use the chrome helper "
                "(not only hardcoded English “Doctor”)"
            )

    # 6) Never translate stored message bodies / snippets / names via the helper.
    body_blob = logic + "\n" + app + "\n" + doctor
    if _chrome_helper_on_body(body_blob, helpers):
        fail(
            "#131: do not pass body_text / snippet / display_name / preview "
            "through the chrome helper — message bodies stay as stored"
        )

    # 7) WA parser packs must not grow UI chrome strings.
    _assert_wa_locale_not_chrome(root)

    # 8) English empty / doctor / backup copy still present (pack or svelte)
    #    so existing English gates keep passing for the default locale.
    svelte_en = app + "\n" + doctor
    for pane_name in ("EmptyState.svelte", "SearchPane.svelte", "ReviewPane.svelte"):
        p = crate / "web" / "lib" / pane_name
        if p.is_file():
            svelte_en += "\n" + p.read_text()
    en_surface = svelte_en + "\n" + en_text
    missing_empty = [s for s in _EN_EMPTY_TITLES if s not in en_surface]
    if len(missing_empty) == len(_EN_EMPTY_TITLES):
        fail(
            "#131: English empty-state copy must remain in the en pack or the panes "
            f"({_EN_EMPTY_TITLES[0]!r}, …) so existing empty-state gates stay English"
        )
    if "Not encrypted at rest" not in en_surface or "FileVault" not in en_surface:
        fail(
            "#131: English doctor / backup honesty copy must remain in the en pack "
            "or Doctor pane (“Not encrypted at rest”, FileVault)"
        )
    if "backup unit" not in en_surface and "data-cloud-warning" not in app:
        fail(
            "#131: English backup / cloud banner copy must remain "
            "(en pack or existing data-cloud-warning banner)"
        )

    # 9) Docs: chrome follows OS language (en/tr); bodies stay as imported.
    if not re.search(
        r"("
        r"OS language"
        r"|OS locale"
        r"|follows (?:the )?OS"
        r"|chrome follows"
        r"|UI chrome.{0,40}(?:language|locale)"
        r"|en(?:glish)?\s*/\s*tr"
        r")",
        dtxt,
        re.I,
    ):
        fail(
            "#131: docs/user/app.md must say chrome follows the OS language (en/tr)"
        )
    if not re.search(
        r"("
        r"message bodies? stay"
        r"|bodies stay as"
        r"|as (?:imported|stored)"
        r"|not (?:translate|translating) (?:message )?bod"
        r"|bodies? (?:are|stay|remain) (?:as )?(?:imported|stored|unchanged)"
        r")",
        dtxt,
        re.I,
    ):
        fail(
            "#131: docs/user/app.md must say message bodies stay as imported / stored"
        )

    # 10) Out of scope: chrome-language override UI, RTL layout.
    if _CHROME_OVERRIDE_UI.search(app) or _CHROME_OVERRIDE_UI.search(logic):
        fail(
            "#131: no chrome-language override / settings UI "
            "(optional later — Import pane WhatsApp locale probe is not chrome)"
        )
    if _DIR_RTL.search(app) or _DIR_RTL.search(logic):
        fail("#131: RTL layout is out of scope")
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


# #211 — overlay titlebar: native traffic lights, drag region, no second wordmark.
_DRAG_REGION = re.compile(
    r"\bdata-tauri-drag-region(?:\s*=\s*(?:\"\"|''|true|\{(?:\"\"|'')\}))?",
    re.I,
)
_WORDMARK_BRAND = re.compile(
    r"<(?:strong|b|h1|h2|h3|em)\b[^>]*>\s*Interlace\s*</",
    re.I,
)
_WORDMARK_TEXT = re.compile(r">\s*Interlace\s*<")
_TRAFFIC_NAME = re.compile(r"\btraffic[-_ ]?lights?\b|\bwindow-controls\b", re.I)
_TRAFFIC_HEX = re.compile(
    r"#(?:ff5f57|ff5f56|ff6058|febc2e|ffbd2e|28c840|27c93f)",
    re.I,
)
_CUSTOM_WIN_CTRL = re.compile(
    r"(?:getCurrentWindow\s*\(\s*\)|\bappWindow\b)\s*"
    r"\.\s*(?:close|minimize|toggleMaximize|maximize|unmaximize)\s*\(",
)
_FOREIGN_TITLEBAR = re.compile(
    r"("
    r"(?:target_os\s*=\s*[\"'](?:windows|linux)[\"']"
    r"|cfg!\s*\(\s*windows\s*\)"
    r"|#\[cfg\s*\(\s*windows\s*\))"
    r"[\s\S]{0,400}"
    r"(?:title_?bar|TitleBarStyle|decorations\s*\(|\bgtk\b)"
    r"|(?:title_?bar|TitleBarStyle|decorations\s*\(|\bgtk\b)"
    r"[\s\S]{0,400}"
    r"(?:target_os\s*=\s*[\"'](?:windows|linux)[\"']"
    r"|cfg!\s*\(\s*windows\s*\)"
    r"|#\[cfg\s*\(\s*windows\s*\))"
    r"|\bgtk\b[\s\S]{0,80}(?:titlebar|decorations|HeaderBar)"
    r"|HeaderBar[\s\S]{0,80}gtk"
    r")"
    r"|(?:win32|linux|gtk).{0,100}(?:titleBarStyle|titlebar|decorations)",
    re.I,
)
_DOCS_OVERLAY_BAR = re.compile(
    r"("
    r"overlay(?: / custom)? title\s*bar"
    r"|custom title\s*bar"
    r"|title\s*bar.{0,60}overlay"
    r"|overlay.{0,60}title\s*bar"
    r")",
    re.I | re.S,
)
_DOCS_DRAG_BAR = re.compile(
    r"("
    r"drag.{0,48}(?:the )?(?:top|title)\s*bar"
    r"|(?:top|title)\s*bar.{0,48}drag"
    r")",
    re.I | re.S,
)
_DOCS_NATIVE_LIGHTS = re.compile(
    r"("
    r"(?:native )?(?:close|minimize|zoom|traffic.?lights?)"
    r".{0,80}(?:stay|remain|still|native)"
    r"|(?:native )?(?:close(?:/|,| and )minimize(?:/|,| and )zoom)"
    r"|traffic.?lights?.{0,40}(?:stay|remain|native|clickable)"
    r")",
    re.I | re.S,
)
_DOCS_NO_WORDMARK = re.compile(
    r"("
    r"no second.{0,48}Interlace"
    r"|not a second.{0,48}Interlace"
    r"|without (?:a )?second.{0,48}Interlace"
    r"|no (?:duplicate|in-app|second).{0,24}(?:Interlace )?wordmark"
    r"|no second Interlace wordmark"
    r")",
    re.I | re.S,
)
_INTERACTIVE_TAG = re.compile(
    r"^(?:button|input|select|textarea|a|form|label|Button|Input)$"
)
_TITLEBAR_NAME = re.compile(r"title[-_]?bar|data-titlebar|data-title-bar", re.I)
_PANE_HOOK = re.compile(
    r"<main\b|person-timeline|SearchPane|ReviewPane|DoctorPane|ImportPane",
    re.I,
)


def _main_window_conf(cfg: dict) -> dict:
    windows = (cfg.get("app") or {}).get("windows") or []
    if not isinstance(windows, list):
        return {}
    for w in windows:
        if isinstance(w, dict) and w.get("label") == "main":
            return w
    for w in windows:
        if isinstance(w, dict):
            return w
    return {}


def _looks_like_whole_window(tag: str, inner: str) -> bool:
    name = _tag_name(tag).lower()
    if name in {"html", "body"}:
        return True
    if re.search(r"""\bid\s*=\s*["']app["']""", tag):
        return True
    wraps_chrome = bool(re.search(r"<header\b|<nav\b", inner, re.I))
    wraps_panes = bool(_PANE_HOOK.search(inner))
    if wraps_chrome and wraps_panes:
        return True
    if re.search(r"\bh-full\b", tag) and wraps_panes:
        return True
    return False


def _drag_is_interactive(tag: str) -> bool:
    if _INTERACTIVE_TAG.match(_tag_name(tag)):
        return True
    if re.search(r"\bdata-chrome-search\b", tag):
        return True
    if re.search(r"\bonclick\s*=", tag, re.I) and _tag_name(tag) in {
        "Button",
        "button",
        "a",
    }:
        return True
    return False


def _drag_is_top_chrome(tag: str, inner: str) -> bool:
    if _tag_name(tag).lower() == "header":
        return True
    if _TITLEBAR_NAME.search(tag):
        return True
    if _PANE_HOOK.search(inner):
        return False
    if _looks_like_whole_window(tag, inner):
        return False
    return True


def _drag_gated_to_archive(markup: str, pos: int) -> bool:
    for kind, cond, _extra in _template_stack(markup, pos):
        if kind not in {"if", "if-else"}:
            continue
        if re.search(r"view\s*===?", cond):
            return True
        if re.search(r"!\s*setup", cond) or (
            re.search(r"\bst\b", cond) and not re.search(r"!\s*st\b", cond)
        ):
            return True
    return False


def _header_chrome_chunks(markup: str) -> list[str]:
    chunks = list(_tag_inner(markup, "header"))
    for m in re.finditer(
        r"<([A-Za-z][\w-]*)\b[^>]*(?:titlebar|title-bar|title_bar|data-titlebar)[^>]*>",
        markup,
        re.I,
    ):
        chunks.append(markup[m.start() : m.start() + 2400])
    return chunks


def _custom_traffic_lights(blob: str) -> bool:
    if _claim_without_negation(blob, _TRAFFIC_NAME):
        return True
    if _TRAFFIC_HEX.search(blob):
        return True
    if _CUSTOM_WIN_CTRL.search(blob):
        return True
    colors = 0
    if re.search(r"rounded-full[\s\S]{0,80}(?:bg-red-|bg-\[#ff)", blob, re.I):
        colors += 1
    if re.search(r"rounded-full[\s\S]{0,80}(?:bg-yellow-|bg-\[#fe)", blob, re.I):
        colors += 1
    if re.search(r"rounded-full[\s\S]{0,80}(?:bg-green-|bg-\[#28)", blob, re.I):
        colors += 1
    return colors >= 2


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
    app = app_path.read_text()
    markup = _strip_html_comments(_svelte_markup(app))
    app_clean = _without_comments(app)
    logic = _web_logic(crate)
    rust = _tauri_rust_blob(crate)
    conf_path = crate / "tauri.conf.json"
    conf = conf_path.read_text() if conf_path.is_file() else ""
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
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


# #215 — command palette (⌘K): owned bits-ui Command, local views + people.
# People items: filter + cap ≤32, not the full {#each people}.
# Palette field keeps Ctrl/⌘A; chrome shortcuts do not steal keys from
# [data-command-palette].
# _KEY_K is timeline j/k (lowercase only). Palette must accept k/K like ⌘F.
_KEY_CMD_K = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']k[\"']"
    r"|[\"']k[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']K[\"']"
    r"|[\"']K[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*\.\s*toLowerCase\s*\(\s*\)\s*===?\s*[\"']k[\"']"
    r"|(?:e\.)?code\s*===?\s*[\"']KeyK[\"']"
    r")",
    re.I,
)
_BITS_COMMAND_IMPORT = re.compile(
    r"import\s*\{[^}]*\bCommand\b[^}]*\}\s*from\s*[\"']bits-ui[\"']"
    r"|import\s+\*\s+as\s+\w+\s+from\s*[\"']bits-ui[\"']",
)
_PALETTE_VIEW_LABELS = ("People", "Search", "Review", "Import", "Doctor")
_PALETTE_OPEN_ASSIGN = re.compile(
    r"("
    r"(?:command|palette)\w*\s*=\s*true"
    r"|(?:command|palette)\w*\s*=\s*!\s*(?:command|palette)\w*"
    r"|open(?:Command|Palette)\s*\("
    r"|show(?:Command|Palette)\s*\("
    r")",
    re.I,
)
_PALETTE_CLOSE_ASSIGN = re.compile(
    r"("
    r"(?:command|palette)\w*\s*=\s*false"
    r"|close(?:Command|Palette)\s*\("
    r")",
    re.I,
)
_PALETTE_OPEN_GATE = re.compile(
    r"("
    r"(?:command|palette)\w*"
    r"|data-command-palette"
    r")",
    re.I,
)
_PALETTE_PEOPLE_SRC = re.compile(
    r"("
    r"\{#each\s+people\b"
    r"|\bpeople\s*\.\s*(?:map|filter|flatMap|forEach)\s*\("
    r"|\bfor\s*\([^)]*\bof\s+people\b"
    r")"
)
_PALETTE_BANNED = re.compile(
    r"("
    r"\bapi\s*\.\s*search\s*\("
    r"|\bfts\b"
    r"|spotlight"
    r"|NSUserActivity"
    r"|fetch\s*\("
    r"|https?://"
    r")",
    re.I,
)
_DOCS_CMD_K = re.compile(
    r"("
    r"⌘\s*K"
    r"|Cmd(?:-|\s*|\+)\s*K"
    r"|Command(?:-|\s*|\+)\s*K"
    r"|Ctrl(?:-|\s*|\+)\s*K"
    r")",
    re.I,
)
_DOCS_CMD_PALETTE = re.compile(r"command palette", re.I)
_DOCS_PERSON_JUMP = re.compile(
    r"("
    r"(?:type|jump).{0,80}person"
    r"|person.{0,60}(?:jump|name)"
    r")",
    re.I | re.S,
)
_DOCS_PALETTE_SEARCH_Q = re.compile(
    r"("
    r"(?:command palette|⌘\s*K|Ctrl(?:-|\s*|\+)\s*K).{0,280}"
    r"Search.{0,100}#q"
    r"|Search.{0,80}#q.{0,200}(?:command palette|⌘\s*K|local)"
    r")",
    re.I | re.S,
)
_DOCS_PALETTE_ESC = re.compile(
    r"("
    r"(?:[Ee]sc(?:ape)?).{0,80}(?:close[sd]?).{0,80}(?:palette|command)"
    r"|(?:palette|command).{0,80}(?:[Ee]sc(?:ape)?).{0,40}close"
    r")",
    re.I | re.S,
)
_DOCS_PALETTE_LOCAL = re.compile(
    r"("
    r"local.{0,120}(?:loaded people|people \+ views|not.{0,40}(?:full-?text|Spotlight|FTS))"
    r"|loaded people.{0,80}(?:view|not.{0,40}(?:full-?text|Spotlight|FTS))"
    r"|not.{0,60}(?:archive full-?text|full-?text|Spotlight)"
    r")",
    re.I | re.S,
)
_CMD_PALETTE_FROM = re.compile(
    r"from\s*[\"'](?:cmdk|svelte-command(?:-palette)?)[\"']",
    re.I,
)
# Raw palette {#each} of the loaded array (sidebar {#each filtered} is fine).
_PALETTE_RAW_PEOPLE_EACH = re.compile(r"\{#each\s+people\s+(?:as|\()")
_PALETTE_PEOPLE_FILTER = re.compile(r"\bpeople\s*\.\s*filter\s*\(")
_PALETTE_SLICE_0_N = re.compile(r"\.\s*slice\s*\(\s*0\s*,\s*(\d+)\s*\)")
_PALETTE_SLICE_0_NAME = re.compile(
    r"\.\s*slice\s*\(\s*0\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)"
)
_PALETTE_PEOPLE_CAP_CONST = re.compile(
    r"\b(PALETTE_PEOPLE_CAP|PEOPLE_CAP|MAX_PALETTE_PEOPLE|MAX_PEOPLE|"
    r"PALETTE_LIMIT|PEOPLE_LIMIT|palettePeopleCap|peopleCap)\s*=\s*(\d+)",
    re.I,
)
# Palette field: Ctrl/⌘A select-all + in-palette chrome skip.
_KEY_CMD_A = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']a[\"']"
    r"|[\"']a[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']A[\"']"
    r"|[\"']A[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*\.\s*toLowerCase\s*\(\s*\)\s*===?\s*[\"']a[\"']"
    r"|(?:e\.)?code\s*===?\s*[\"']KeyA[\"']"
    r")",
    re.I,
)
_PALETTE_IN_FIELD = re.compile(
    r"("
    r"closest[\s?.]*\(\s*[\"']\[data-command-palette\][\"']"
    r"|matches[\s?.]*\(\s*[\"']\[data-command-palette\][\"']"
    r"|data-command-palette"
    r")"
)
_PALETTE_FIELD_FLAG = re.compile(
    r"\b(?:command|palette)(?:Open|Shown|Visible|_open)\b"
    r"|\b(?:is|show|open)(?:Command|Palette)(?:Open)?\b",
    re.I,
)
_PALETTE_SELECT_ALL = re.compile(r"\b(?:select|setSelectionRange)\s*\(")
# Palette field: Ctrl/⌘C / V / X via navigator.clipboard (no plugin).
_KEY_CMD_C = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']c[\"']"
    r"|[\"']c[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']C[\"']"
    r"|[\"']C[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*\.\s*toLowerCase\s*\(\s*\)\s*===?\s*[\"']c[\"']"
    r"|(?:e\.)?code\s*===?\s*[\"']KeyC[\"']"
    r")",
    re.I,
)
_KEY_CMD_V = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']v[\"']"
    r"|[\"']v[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']V[\"']"
    r"|[\"']V[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*\.\s*toLowerCase\s*\(\s*\)\s*===?\s*[\"']v[\"']"
    r"|(?:e\.)?code\s*===?\s*[\"']KeyV[\"']"
    r")",
    re.I,
)
_KEY_CMD_X = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']x[\"']"
    r"|[\"']x[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']X[\"']"
    r"|[\"']X[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*\.\s*toLowerCase\s*\(\s*\)\s*===?\s*[\"']x[\"']"
    r"|(?:e\.)?code\s*===?\s*[\"']KeyX[\"']"
    r")",
    re.I,
)
_PALETTE_READ_TEXT = re.compile(
    r"("
    r"navigator\.clipboard\.readText"
    r"|clipboard\.readText"
    r")"
)
_CLIPBOARD_PLUGIN = re.compile(
    r"("
    r"tauri-plugin-clipboard"
    r"|plugin-clipboard-manager"
    r"|clipboard-manager"
    r")"
)


def _command_ui_dir(crate: Path) -> Path:
    return crate / "web" / "lib" / "components" / "ui" / "command"


def _command_dir_blob(cmd: Path) -> str:
    parts: list[str] = []
    if not cmd.is_dir():
        return ""
    for p in sorted(cmd.rglob("*")):
        if p.is_file() and p.suffix in {".svelte", ".ts", ".js"}:
            parts.append(p.read_text())
    return "\n".join(parts)


def _palette_named_fns(src: str) -> str:
    names: set[str] = set()
    for m in re.finditer(
        r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*(?:[Cc]ommand|[Pp]alette)[A-Za-z0-9_]*)",
        src,
    ):
        names.add(m.group(1))
    for m in re.finditer(
        r"(?:const|let)\s+([A-Za-z_][A-Za-z0-9_]*(?:[Cc]ommand|[Pp]alette)[A-Za-z0-9_]*)\s*=",
        src,
    ):
        names.add(m.group(1))
    chunks: list[str] = []
    for name in names:
        if name in _KEYMAP_CALL_SKIP:
            continue
        inner = _ts_fn_body(src, name) or _function_body(src, name)
        if inner:
            chunks.append(inner)
    return "\n".join(chunks)


def _palette_surface(crate: Path, app: str, cmd_blob: str) -> str:
    """command/ sources + data-command-palette windows + *command*/*palette* fns.

    Not the whole App (nav already says People/Search; ⌘F already focuses #q).
    """
    parts = [
        cmd_blob,
        _windows_around(app, _PALETTE_HOOK, before=400, after=2800),
        _palette_named_fns(app),
        _windows_around(app, re.compile(r"<Command(?:\.\w+)?\b"), before=80, after=1200),
    ]
    for p in _product_svelte(crate):
        rel = str(p).replace("\\", "/")
        if "/components/ui/command/" in rel:
            continue
        if p.name == "App.svelte":
            continue
        text = p.read_text()
        if _PALETTE_HOOK.search(text) or _owned_imported_names(text, "command"):
            parts.append(text)
            parts.append(_palette_named_fns(text))
    return "\n".join(parts)


def _mod_k_windows(src: str) -> str:
    """Windows around k/K that are a meta/ctrl (or `mod`) combo, not timeline k."""
    parts: list[str] = []
    for m in _KEY_CMD_K.finditer(src):
        w = src[max(0, m.start() - 360) : m.end() + 640]
        if _MOD_EITHER.search(w) or re.search(r"\bmod\b", w):
            parts.append(w)
    return "\n".join(parts)


def _mod_a_windows(src: str) -> str:
    """Windows around a/A that are a meta/ctrl (or `mod`) combo."""
    parts: list[str] = []
    for m in _KEY_CMD_A.finditer(src):
        w = src[max(0, m.start() - 360) : m.end() + 640]
        if _MOD_EITHER.search(w) or re.search(r"\bmod\b", w):
            parts.append(w)
    return "\n".join(parts)


def _mod_c_windows(src: str) -> str:
    """Windows around c/C that are a meta/ctrl (or `mod`) combo."""
    parts: list[str] = []
    for m in _KEY_CMD_C.finditer(src):
        w = src[max(0, m.start() - 360) : m.end() + 640]
        if _MOD_EITHER.search(w) or re.search(r"\bmod\b", w):
            parts.append(w)
    return "\n".join(parts)


def _mod_v_windows(src: str) -> str:
    """Windows around v/V that are a meta/ctrl (or `mod`) combo."""
    parts: list[str] = []
    for m in _KEY_CMD_V.finditer(src):
        w = src[max(0, m.start() - 360) : m.end() + 640]
        if _MOD_EITHER.search(w) or re.search(r"\bmod\b", w):
            parts.append(w)
    return "\n".join(parts)


def _mod_x_windows(src: str) -> str:
    """Windows around x/X that are a meta/ctrl (or `mod`) combo."""
    parts: list[str] = []
    for m in _KEY_CMD_X.finditer(src):
        w = src[max(0, m.start() - 360) : m.end() + 640]
        if _MOD_EITHER.search(w) or re.search(r"\bmod\b", w):
            parts.append(w)
    return "\n".join(parts)


def _palette_esc_close_end(body: str) -> int | None:
    """End of the open-palette Escape-close block in onKey (if any)."""
    for m in _KEY_ESC.finditer(body):
        start = body.rfind("if", 0, m.start())
        if start < 0:
            continue
        head = body[start : m.end() + 80]
        if not (
            _PALETTE_FIELD_FLAG.search(head)
            or _PALETTE_OPEN_GATE.search(head)
        ):
            continue
        brace = body.find("{", m.start())
        if brace < 0:
            ret = body.find("return", m.start())
            chunk = body[m.start() : (ret + 20 if ret >= 0 else m.end() + 80)]
            if _PALETTE_CLOSE_ASSIGN.search(chunk):
                return ret + 6 if ret >= 0 else m.end()
            continue
        end = _match_closer(body, brace)
        block = body[start : end + 1] if end >= 0 else body[start : brace + 200]
        if _PALETTE_CLOSE_ASSIGN.search(block):
            return end if end >= 0 else brace
    return None


def _palette_chrome_shortcut_at(body: str) -> int:
    """Index of ⌘K open / ⌘F Search handlers (chrome must not run in-field)."""
    spots: list[int] = []
    m = _PALETTE_OPEN_ASSIGN.search(body)
    if m:
        spots.append(m.start())
    m = re.search(r"\bwhenSearchPaneReady\b", body)
    if m:
        spots.append(m.start())
    return min(spots) if spots else len(body)


def _in_palette_skip_ok(src: str, region: str) -> bool:
    """True if src gates a return on the palette flag + [data-command-palette]."""
    for m in _PALETTE_IN_FIELD.finditer(src):
        w = src[max(0, m.start() - 240) : m.end() + 240]
        after = src[m.start() :] + "\n" + region
        if _PALETTE_FIELD_FLAG.search(w) and re.search(r"\breturn\b", after):
            return True
    return False


def assert_command_palette(crate: Path) -> None:
    """#215: ⌘K command palette — owned bits-ui Command, local views + people.

    Own web/lib/components/ui/command/ wrapping bits-ui Command. ⌘K / Ctrl+K
    opens from every view (INPUT guard lets k/K through). View items + jump
    to a loaded person. Search focuses #q. Esc closes. No api.search / FTS /
    HTTP / Spotlight. Docs. Do not rewrite #132 / #201 / #214.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#215: App.svelte required (⌘K command palette)")
    app = app_path.read_text()
    app_clean = _without_comments(app)
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    conf_path = crate / "tauri.conf.json"
    conf = conf_path.read_text() if conf_path.is_file() else ""
    pkg_path = crate / "package.json"
    pkg = pkg_path.read_text() if pkg_path.is_file() else ""

    # 1) Owned command/ (at least one .svelte + index.ts).
    cmd = _command_ui_dir(crate)
    if not cmd.is_dir():
        fail(
            "#215: missing owned Command under web/lib/components/ui/command/ "
            "(at least one .svelte + index.ts)"
        )
    if not any(cmd.glob("*.svelte")):
        fail(
            "#215: web/lib/components/ui/command/ needs at least one .svelte "
            "(owned Command wrapper)"
        )
    if not (cmd / "index.ts").is_file():
        fail("#215: web/lib/components/ui/command/index.ts required")
    cmd_blob = _command_dir_blob(cmd)

    # 2) Wraps local bits-ui Command (not cmdk / a second kit).
    if not re.search(r"from\s*[\"']bits-ui[\"']", cmd_blob):
        fail(
            "#215: web/lib/components/ui/command/ must wrap local bits-ui Command "
            '(import { Command … } from "bits-ui")'
        )
    if not re.search(r"\bCommand\b", cmd_blob):
        fail(
            "#215: web/lib/components/ui/command/ must wrap bits-ui Command "
            "(Command / Command.Root / computeCommandScore)"
        )
    if not _BITS_COMMAND_IMPORT.search(cmd_blob):
        fail(
            "#215: web/lib/components/ui/command/ must import Command from "
            "bits-ui (same wrap as Dialog / Tooltip)"
        )
    if _CMD_PALETTE_FROM.search(cmd_blob):
        fail(
            "#215: wrap local bits-ui Command — do not import cmdk / "
            "svelte-command in command/"
        )

    # 3) package.json still has bits-ui; still no cmdk / svelte-command / second kit.
    if not pkg_path.is_file():
        fail("#215: crates/interlace-tauri/package.json required (bits-ui local)")
    if '"bits-ui"' not in pkg:
        fail(
            "#215: package.json must keep bits-ui as a local dependency "
            "(wrap bits-ui Command; do not swap kits)"
        )
    if _CMD_PALETTE_PKG.search(pkg):
        fail(
            "#215: package.json must not add cmdk / svelte-command "
            "(#201 ban stays — wrap local bits-ui Command)"
        )
    if _SECOND_UI_KIT.search(pkg):
        fail(
            "#215: package.json must not add a second UI kit "
            "(@radix-ui / shadcn / daisyui / …) — wrap local bits-ui Command"
        )

    # 4) Chrome imports the owned wrapper, not bits-ui Command in App.
    used_owned = False
    for p in _product_svelte(crate):
        rel = str(p).replace("\\", "/")
        if "/components/ui/command/" in rel:
            continue
        text = p.read_text()
        if _owned_imported_names(text, "command"):
            used_owned = True
            break
    if not used_owned:
        fail(
            "#215: App / chrome must import the owned Command from "
            "$lib/components/ui/command (do not import bits-ui Command in App)"
        )
    if re.search(
        r"import\s*\{[^}]*\bCommand\b[^}]*\}\s*from\s*[\"']bits-ui[\"']",
        app,
    ):
        fail(
            "#215: wrap bits-ui Command in web/lib/components/ui/command/ — "
            "do not import Command from bits-ui in App.svelte"
        )

    raw_body = _app_keydown_body(app_clean) or _app_keydown_body(app)
    if not raw_body.strip():
        fail(
            "#215: App.svelte must handle window keydown (onKey) so ⌘K / "
            "Ctrl+K can open the command palette"
        )
    body = _expand_fn_calls(app_clean, raw_body)
    if body == raw_body:
        body = _expand_fn_calls(app, raw_body)
    prefix, tail = _split_people_only(raw_body)
    prefix_x = _expand_fn_calls(app_clean, prefix) if prefix.strip() else body
    if prefix_x == prefix:
        prefix_x = _expand_fn_calls(app, prefix) if prefix.strip() else body

    # 5) ⌘K / Ctrl+K from every view; INPUT guard lets k/K through; preventDefault.
    k_surface = _mod_k_windows(prefix_x)
    if not k_surface.strip():
        k_surface = _mod_k_windows(prefix)
    if not k_surface.strip():
        tail_k = _mod_k_windows(tail) if tail else ""
        if tail_k.strip() and not _mod_k_windows(prefix_x).strip():
            fail(
                "#215: ⌘K / Ctrl+K must run off People "
                "(it is after `if (view !== \"people\") return`)"
            )
        fail(
            "#215: App key handler must treat metaKey/ctrlKey + k/K as the "
            "command palette (from every view, including when an INPUT is focused)"
        )
    if not _has_mod_combo(k_surface) and not _has_mod_combo(prefix_x):
        fail(
            "#215: command palette must accept metaKey or ctrlKey "
            "(⌘K on macOS; ctrl+K so gates/tests see the fallback)"
        )
    if not _MOD_EITHER.search(k_surface) and not re.search(r"\bmod\b", k_surface):
        fail("#215: k/K palette must be a metaKey/ctrlKey combo, not a bare letter")
    if not re.search(r"altKey|\bmod\b", k_surface) and not re.search(
        r"altKey|\bmod\b", prefix
    ):
        fail(
            "#215: ⌘K / Ctrl+K must use the same AltGr-safe mod as #132 "
            "(metaKey or ctrlKey && !altKey)"
        )
    if not _PREVENT_DEFAULT.search(k_surface) and not _PREVENT_DEFAULT.search(prefix_x):
        fail(
            "#215: ⌘K / Ctrl+K must preventDefault "
            "(webview must not take the key)"
        )
    if not _PALETTE_OPEN_ASSIGN.search(k_surface) and not _PALETTE_OPEN_ASSIGN.search(
        prefix_x
    ):
        fail(
            "#215: ⌘K / Ctrl+K must open the command palette "
            "(set a command/palette flag or call openCommand/openPalette)"
        )
    if not _INPUT_TAG_GUARD.search(raw_body) and not _INPUT_TAG_GUARD.search(body):
        fail(
            "#215: keep the INPUT/TEXTAREA/SELECT guard "
            "(⌘K is an exception next to ⌘F; bare k still must not steal #q)"
        )
    guard_span = _input_guard_span(raw_body)
    if not guard_span:
        fail(
            "#215: INPUT/TEXTAREA/SELECT guard must still wrap the early return "
            "(add k/K next to ⌘F so the combo works from a field)"
        )
    guard = raw_body[guard_span[0] : guard_span[1] + 1]
    if not _KEY_CMD_K.search(guard) and not _KEY_K.search(guard):
        fail(
            "#215: INPUT guard must let ⌘K / Ctrl+K through "
            "(add k/K to the exception next to ⌘F)"
        )

    # 6) data-command-palette on the open palette surface.
    markup = _strip_html_comments(_svelte_markup(app))
    hook_ok = bool(_PALETTE_HOOK.search(markup) or _PALETTE_HOOK.search(app))
    if not hook_ok:
        hook_ok = bool(_PALETTE_HOOK.search(cmd_blob))
    if not hook_ok:
        for p in _product_svelte(crate):
            if _PALETTE_HOOK.search(p.read_text()):
                hook_ok = True
                break
    if not hook_ok:
        fail(
            "#215: open command palette surface must include data-command-palette"
        )

    surface = _palette_surface(crate, app, cmd_blob)
    surface_x = _expand_fn_calls(app_clean, surface) if surface.strip() else surface
    if surface_x == surface:
        surface_x = _expand_fn_calls(app, surface) if surface.strip() else surface

    # 7) View items: People, Search, Review, Import, Doctor.
    for label, tok in zip(_PALETTE_VIEW_LABELS, _VIEW_TAB_ORDER, strict=True):
        if not re.search(rf"\b{re.escape(label)}\b", surface):
            fail(
                f"#215: command palette must include a {label} view item "
                "(People / Search / Review / Import / Doctor)"
            )
        if not re.search(rf"[\"']{tok}[\"']", surface) and not re.search(
            rf"[\"']{tok}[\"']", surface_x
        ):
            fail(
                f'#215: choosing the {label} palette item must set view = "{tok}"'
            )

    # 8) Search path focuses #q (same idea as ⌘F / whenSearchPaneReady).
    if not _FOCUS_SEARCH_Q.search(surface_x) and not re.search(
        r"\bwhenSearchPaneReady\b", surface + "\n" + surface_x
    ):
        fail(
            "#215: choosing Search in the palette must focus #q "
            "(whenSearchPaneReady or getElementById(\"q\") — same path as ⌘F)"
        )

    # 9) Person items from the loaded people array; selectPerson + People view.
    if not _PALETTE_PEOPLE_SRC.search(surface) and not _PALETTE_PEOPLE_SRC.search(
        surface_x
    ):
        fail(
            "#215: palette person items must come from the loaded people array "
            "({#each people / people.map — not api.search / FTS)"
        )
    if not re.search(r"\b(?:display_name|personLabel)\b", surface) and not re.search(
        r"\b(?:display_name|personLabel)\b", surface_x
    ):
        fail(
            "#215: person item labels must use display_name / personLabel "
            "(same list as the sidebar)"
        )
    if not re.search(r"\bselectPerson\s*\(", surface) and not re.search(
        r"\bselectPerson\s*\(", surface_x
    ):
        fail(
            "#215: choosing a person in the palette must call selectPerson"
        )
    if not _VIEW_PEOPLE_ASSIGN.search(surface) and not _VIEW_PEOPLE_ASSIGN.search(
        surface_x
    ):
        fail(
            '#215: choosing a person in the palette must switch to People '
            '(view = "people")'
        )

    # 10) No api.search / FTS / HTTP / Spotlight from the palette.
    banned = _PALETTE_BANNED.search(surface) or _PALETTE_BANNED.search(cmd_blob)
    if banned:
        fail(
            "#215: command palette must stay local (loaded people + views) — "
            "no api.search / FTS / HTTP / Spotlight from the palette"
        )

    # 11) Esc closes the open palette; does not bounce the view; closed Esc stays.
    if not _KEY_ESC.search(raw_body) and not _KEY_ESC.search(body):
        fail("#215: Escape must close the open command palette")
    esc_surface = _windows_around(
        _without_input_guard(raw_body), _KEY_ESC, before=80, after=560
    )
    if not esc_surface.strip():
        esc_surface = _windows_around(raw_body, _KEY_ESC, before=80, after=560)
    esc_x = _expand_fn_calls(app_clean, esc_surface) or _expand_fn_calls(app, esc_surface)
    if not _PALETTE_OPEN_GATE.search(esc_surface) and not _PALETTE_OPEN_GATE.search(
        esc_x
    ):
        fail(
            "#215: Escape must close the open command palette "
            "(gate on the palette open flag / data-command-palette — "
            "do not steal Esc from INPUT when the palette is closed)"
        )
    if not _PALETTE_CLOSE_ASSIGN.search(esc_surface) and not _PALETTE_CLOSE_ASSIGN.search(
        esc_x
    ):
        fail(
            "#215: Escape when the palette is open must close it "
            "(command/palette flag = false) and return"
        )
    close_m = _PALETTE_CLOSE_ASSIGN.search(esc_surface) or _PALETTE_CLOSE_ASSIGN.search(
        esc_x
    )
    if close_m:
        blob = esc_surface if _PALETTE_CLOSE_ASSIGN.search(esc_surface) else esc_x
        after = blob[close_m.end() : close_m.end() + 240]
        view_m = _VIEW_PEOPLE_ASSIGN.search(after)
        if view_m and not re.search(r"\breturn\b", after[: view_m.start()]):
            fail(
                "#215: Esc must close the palette and return "
                "(do not also bounce the view to People)"
            )
    if esc_surface and _ESC_CLOSE_APP.search(esc_surface):
        fail("#215: Escape must not close the app (close the palette only)")
    if not _INPUT_BLUR.search(raw_body) and not _INPUT_BLUR.search(body):
        fail(
            "#215: keep Esc blur on INPUT when the palette is not open "
            "(do not steal Esc from #q / #person-filter)"
        )
    # Palette INPUT is an INPUT — Esc must still close when the palette is open.
    pre = raw_body[: guard_span[0]]
    if not (
        (_KEY_ESC.search(pre) and _PALETTE_CLOSE_ASSIGN.search(pre))
        or (
            _KEY_ESC.search(guard)
            and (
                _PALETTE_CLOSE_ASSIGN.search(guard) or _PALETTE_OPEN_GATE.search(guard)
            )
        )
    ):
        fail(
            "#215: Esc must close the open palette even when its INPUT is focused "
            "(handle it before the INPUT return, or let Escape through when open)"
        )

    # 12) Docs: ⌘K / Ctrl+K, person jump, Search → #q, Esc closes, local-only.
    if not dtxt.strip():
        fail(
            "#215: docs/user/app.md required — ⌘K / Ctrl+K command palette, "
            "person jump, Search → #q, Esc closes, local-only"
        )
    if not _DOCS_CMD_K.search(dtxt):
        fail(
            "#215: docs/user/app.md must document ⌘K / Ctrl+K "
            "(opens a local command palette)"
        )
    if not _DOCS_CMD_PALETTE.search(dtxt):
        fail("#215: docs/user/app.md must mention the command palette")
    if not _DOCS_PERSON_JUMP.search(dtxt):
        fail(
            "#215: docs/user/app.md must say you can type a person name to jump"
        )
    if not _DOCS_PALETTE_SEARCH_Q.search(dtxt):
        fail(
            "#215: docs/user/app.md must say Search in the palette focuses #q"
        )
    if not _DOCS_PALETTE_ESC.search(dtxt):
        fail("#215: docs/user/app.md must say Esc closes the command palette")
    if not _DOCS_PALETTE_LOCAL.search(dtxt):
        fail(
            "#215: docs/user/app.md must say the palette is local "
            "(loaded people + views), not archive full-text / Spotlight"
        )

    # 13) Do not soften ⌘F, ⌘1–5, #q, sidebar, overlay, inspector, CSP.
    if not _KEY_F.search(prefix_x) and not _KEY_F.search(raw_body):
        fail("#215: keep ⌘F / ctrl+F Find (do not rewrite #132)")
    if not _has_mod_combo(prefix_x) and not _has_mod_combo(raw_body):
        fail(
            "#215: keep metaKey or ctrlKey on Find / tab digits "
            "(do not rewrite #132 ⌘F / ⌘1–5)"
        )
    for tok in _VIEW_TAB_ORDER:
        if not re.search(rf"[\"']{tok}[\"']", prefix_x) and not re.search(
            rf"[\"']{tok}[\"']", raw_body
        ):
            fail(
                f'#215: keep ⌘1–5 view "{tok}" '
                "(1 People … 5 Doctor — do not rewrite #132)"
            )
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#215: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#215: keep data-people-sidebar (#159 / #212)")
    if not re.search(r"\bdata-person-inspector\b", app):
        fail("#215: keep data-person-inspector (#213)")
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#215: keep the overlay titlebar (#211)")
    if CSP not in conf:
        fail("#215: do not soften tauri CSP")


def _palette_people_cap_ok(src: str) -> bool:
    """True if src proves a people-item cap of ≤32 (slice or named const)."""
    if any(int(n) <= 32 for n in _PALETTE_SLICE_0_N.findall(src)):
        return True
    consts = {
        m.group(1): int(m.group(2)) for m in _PALETTE_PEOPLE_CAP_CONST.finditer(src)
    }
    if any(v <= 32 for v in consts.values()):
        return True
    lower = {name.lower(): val for name, val in consts.items()}
    for name in _PALETTE_SLICE_0_NAME.findall(src):
        val = consts.get(name, lower.get(name.lower()))
        if val is not None and val <= 32:
            return True
    return False


def assert_command_palette_people_cap(crate: Path) -> None:
    """#215: palette people items are filtered + capped (≤32), not {#each people}.

    CommandPalette / data-command-palette / command/ chrome only — not the
    sidebar {#each filtered}. Do not rewrite assert_command_palette.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#215: App.svelte required (command palette people cap)")
    app = app_path.read_text()
    cmd_blob = _command_dir_blob(_command_ui_dir(crate))
    surface = _palette_surface(crate, app, cmd_blob)
    pal_path = crate / "web" / "lib" / "CommandPalette.svelte"
    if pal_path.is_file():
        surface = surface + "\n" + pal_path.read_text()
    cleaned = _without_comments(surface)

    # 1) Do not mount the raw loaded array as Command.Item rows.
    if _PALETTE_RAW_PEOPLE_EACH.search(cleaned):
        fail(
            "#215: command palette must not mount the raw people array "
            "({#each people as / {#each people () — filter the loaded list "
            "and render at most 32"
        )

    # 2) Filter / slice the loaded people array (not sidebar filtered).
    has_people = bool(
        re.search(r"\bpeople\b", cleaned) or _PALETTE_PEOPLE_SRC.search(cleaned)
    )
    has_filter_or_slice = bool(
        _PALETTE_PEOPLE_FILTER.search(cleaned)
        or re.search(r"\.\s*(?:filter|slice)\s*\(", cleaned)
    )
    if not (_PALETTE_PEOPLE_FILTER.search(cleaned) or (has_people and has_filter_or_slice)):
        fail(
            "#215: palette people items must come from people.filter "
            "(or people + .filter( / .slice() of the loaded array) — "
            "not the full list"
        )

    # 3) Numeric cap ≤32: slice(0, N) or PALETTE_PEOPLE_CAP / similar.
    if not _palette_people_cap_ok(cleaned):
        fail(
            "#215: palette people items must be capped at ≤32 "
            "(slice(0, N) with N<=32, or PALETTE_PEOPLE_CAP / similar)"
        )

    # 4) Keep #215 person jump: labels, selectPerson, People view.
    surface_x = _expand_fn_calls(app, surface) if surface.strip() else surface
    if not re.search(r"\b(?:display_name|personLabel)\b", cleaned) and not re.search(
        r"\b(?:display_name|personLabel)\b", surface_x
    ):
        fail(
            "#215: person item labels must use display_name / personLabel "
            "(same list as the sidebar)"
        )
    if not re.search(r"\bselectPerson\s*\(", cleaned) and not re.search(
        r"\bselectPerson\s*\(", surface_x
    ):
        fail(
            "#215: choosing a person in the palette must call selectPerson"
        )
    if not _VIEW_PEOPLE_ASSIGN.search(cleaned) and not _VIEW_PEOPLE_ASSIGN.search(
        surface_x
    ):
        fail(
            '#215: choosing a person in the palette must switch to People '
            '(view = "people")'
        )

    # 5) Still local — no api.search / FTS / HTTP / Spotlight.
    banned = _PALETTE_BANNED.search(cleaned) or _PALETTE_BANNED.search(cmd_blob)
    if banned:
        fail(
            "#215: command palette must stay local (loaded people + views) — "
            "no api.search / FTS / HTTP / Spotlight from the palette"
        )


def assert_command_palette_field_keys(crate: Path) -> None:
    """#215: palette field keeps Ctrl/⌘A; chrome shortcuts do not steal keys from [data-command-palette]."""
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#215: App.svelte required (palette field keys)")
    app = app_path.read_text()
    app_clean = _without_comments(app)
    raw_body = _app_keydown_body(app_clean) or _app_keydown_body(app)
    if not raw_body.strip():
        fail(
            "#215: App.svelte must handle window keydown (onKey) so the "
            "palette field can keep Ctrl/⌘A"
        )

    # 1) After Esc-close, return when commandOpen + target in [data-command-palette]
    #    — before ⌘K commandOpen=true / ⌘F whenSearchPaneReady.
    chrome_at = _palette_chrome_shortcut_at(raw_body)
    prefix = raw_body[:chrome_at]
    prefix_x = _expand_fn_calls(app_clean, prefix) if prefix.strip() else prefix
    if prefix_x == prefix:
        prefix_x = _expand_fn_calls(app, prefix) if prefix.strip() else prefix
    esc_end = _palette_esc_close_end(raw_body)
    region = raw_body[esc_end:chrome_at] if esc_end is not None else prefix
    if not (
        _in_palette_skip_ok(prefix, region) or _in_palette_skip_ok(prefix_x, region)
    ):
        fail(
            "#215: after Esc-close, onKey must return when commandOpen and "
            "the target is inside [data-command-palette] (before ⌘K / ⌘F — "
            "chrome must not steal field keys)"
        )

    # 2) Palette surface handles meta/ctrl + a/A and select()s the field.
    cmd_blob = _command_dir_blob(_command_ui_dir(crate))
    surface = _palette_surface(crate, app, cmd_blob)
    pal_path = crate / "web" / "lib" / "CommandPalette.svelte"
    if pal_path.is_file():
        surface = surface + "\n" + pal_path.read_text()
    surface_x = _expand_fn_calls(surface, surface) if surface.strip() else surface
    a_surface = _mod_a_windows(surface) or _mod_a_windows(surface_x)
    if not a_surface.strip():
        fail(
            "#215: palette field must handle meta/ctrl + a/A "
            "(select all in [data-command-palette])"
        )
    if not _PALETTE_SELECT_ALL.search(a_surface) and not _PALETTE_SELECT_ALL.search(
        surface
    ):
        fail(
            "#215: palette field Ctrl/⌘A must select() the text "
            "(or setSelectionRange) so WKWebView Select All works"
        )

    # 3) INPUT guard still lets k/K through (⌘K from #q / #person-filter).
    if not _INPUT_TAG_GUARD.search(raw_body):
        fail(
            "#215: keep the INPUT/TEXTAREA/SELECT guard "
            "(⌘K from #q must still open the palette)"
        )
    guard_span = _input_guard_span(raw_body)
    if not guard_span:
        fail(
            "#215: INPUT/TEXTAREA/SELECT guard must still wrap the early return "
            "(k/K stays an exception so ⌘K works from #q)"
        )
    guard = raw_body[guard_span[0] : guard_span[1] + 1]
    if not _KEY_CMD_K.search(guard) and not _KEY_K.search(guard):
        fail(
            "#215: INPUT guard must still let k/K through "
            "(⌘K from #q / #person-filter must still open the palette)"
        )

    # 4) Esc still closes the open palette.
    if not _KEY_ESC.search(raw_body):
        fail("#215: Escape must still close the open command palette")
    if not _PALETTE_CLOSE_ASSIGN.search(raw_body):
        fail(
            "#215: Escape must still close the open palette "
            "(commandOpen = false / closeCommand)"
        )


def assert_command_palette_clipboard(crate: Path) -> None:
    """#215: palette field Ctrl/⌘C / V / X via navigator.clipboard (no plugin)."""
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#215: App.svelte required (palette field clipboard)")
    app = app_path.read_text()
    cmd_blob = _command_dir_blob(_command_ui_dir(crate))
    surface = _palette_surface(crate, app, cmd_blob)
    pal_path = crate / "web" / "lib" / "CommandPalette.svelte"
    if pal_path.is_file():
        surface = surface + "\n" + pal_path.read_text()
    surface_x = _expand_fn_calls(surface, surface) if surface.strip() else surface

    # 1) Palette field: meta/ctrl + c/C → clipboard.writeText (copy).
    c_surface = _mod_c_windows(surface) or _mod_c_windows(surface_x)
    if not c_surface.strip():
        fail(
            "#215: palette field must handle meta/ctrl + c/C "
            "(clipboard.writeText / navigator.clipboard.writeText)"
        )
    if not _WRITE_TEXT.search(c_surface) and not _WRITE_TEXT.search(surface):
        fail(
            "#215: palette field Ctrl/⌘C must call clipboard.writeText "
            "(or navigator.clipboard.writeText) — no clipboard plugin"
        )

    # 2) Palette field: meta/ctrl + v/V → clipboard.readText (paste).
    v_surface = _mod_v_windows(surface) or _mod_v_windows(surface_x)
    if not v_surface.strip():
        fail(
            "#215: palette field must handle meta/ctrl + v/V "
            "(clipboard.readText / navigator.clipboard.readText)"
        )
    if not _PALETTE_READ_TEXT.search(v_surface) and not _PALETTE_READ_TEXT.search(
        surface
    ):
        fail(
            "#215: palette field Ctrl/⌘V must call clipboard.readText "
            "(or navigator.clipboard.readText) — no clipboard plugin"
        )

    # 3) Palette field: meta/ctrl + x/X → clipboard.writeText (cut).
    x_surface = _mod_x_windows(surface) or _mod_x_windows(surface_x)
    if not x_surface.strip():
        fail(
            "#215: palette field must handle meta/ctrl + x/X "
            "(cut via clipboard.writeText / navigator.clipboard.writeText)"
        )
    if not _WRITE_TEXT.search(x_surface) and not _WRITE_TEXT.search(surface):
        fail(
            "#215: palette field Ctrl/⌘X must call clipboard.writeText "
            "(or navigator.clipboard.writeText) so cut copies the selection"
        )

    # 4) Still Ctrl/⌘A select() / setSelectionRange (do not drop #215-keys).
    a_surface = _mod_a_windows(surface) or _mod_a_windows(surface_x)
    if not a_surface.strip():
        fail(
            "#215: palette field must still handle meta/ctrl + a/A "
            "(do not drop #215-keys select-all)"
        )
    if not _PALETTE_SELECT_ALL.search(a_surface) and not _PALETTE_SELECT_ALL.search(
        surface
    ):
        fail(
            "#215: palette field Ctrl/⌘A must still select() the text "
            "(or setSelectionRange)"
        )

    # 5) No tauri-plugin-clipboard* / clipboard-manager in package.json / Cargo.toml.
    pkg_path = crate / "package.json"
    pkg = pkg_path.read_text() if pkg_path.is_file() else ""
    toml_path = crate / "Cargo.toml"
    toml = toml_path.read_text() if toml_path.is_file() else ""
    if _CLIPBOARD_PLUGIN.search(pkg) or _CLIPBOARD_PLUGIN.search(toml):
        fail(
            "#215: do not add tauri-plugin-clipboard / plugin-clipboard-manager "
            "/ clipboard-manager (use navigator.clipboard on the palette field)"
        )

    # 6) Still local — no api.search / FTS / HTTP / Spotlight.
    banned = _PALETTE_BANNED.search(surface) or _PALETTE_BANNED.search(cmd_blob)
    if banned:
        fail(
            "#215: command palette must stay local (loaded people + views) — "
            "no api.search / FTS / HTTP / Spotlight from the palette"
        )


# #276 — local density (Default / Comfortable); persist in localStorage.
# Comfortable enlarges bubble bodies without a reload. Not a Theme menu.
_DENSITY_HOOK = re.compile(
    r"("
    r"\bdata-density(?:-toggle|-control|-pref)?\b"
    r"|\bdata-font-density\b"
    r")",
    re.I,
)
_DENSITY_IDENT = re.compile(
    r"\b(?:fontDensity|textDensity|densityPref|DENSITY_PREF|FONT_DENSITY)\b"
)
_DENSITY_STATE = re.compile(
    r"("
    r"\b(?:let|const|var)\s+density\b"
    r"|\bdensity\s*=\s*\$state"
    r"|\bdensity\s*:\s*[\"'](?:default|comfortable|compact)[\"']"
    r")",
    re.I,
)
_DENSITY_VALUE = re.compile(r"[\"']comfortable[\"']", re.I)
_DENSITY_LABEL = re.compile(
    r"("
    r">\s*Comfortable\s*<"
    r"|[\"']Comfortable[\"']"
    r")",
)
_DENSITY_STEP_COMFORTABLE = re.compile(
    r"("
    r">\s*Comfortable\s*<"
    r"|[\"']Comfortable[\"']"
    r"|[\"']comfortable[\"']"
    r")",
    re.I,
)
# Do not treat Button variant="default" as a density step.
_DENSITY_STEP_DEFAULT = re.compile(
    r"("
    r">\s*Default\s*<"
    r"|[\"']Default[\"']"
    r"|data-density\s*=\s*\{?\s*[\"']default[\"']"
    r"|\bdensity\b[^\n]{0,60}[\"']default[\"']"
    r"|[\"']default[\"'][^\n]{0,60}\bdensity\b"
    r"|[\"']default[\"']\s*\|\s*[\"'](?:comfortable|compact)[\"']"
    r"|[\"'](?:comfortable|compact)[\"']\s*\|\s*[\"']default[\"']"
    r")",
    re.I,
)
_DENSITY_STEP_COMPACT = re.compile(
    r"("
    r">\s*Compact\s*<"
    r"|[\"']Compact[\"']"
    r"|data-density\s*=\s*\{?\s*[\"']compact[\"']"
    r"|\bdensity\b[^\n]{0,60}[\"']compact[\"']"
    r"|[\"']compact[\"'][^\n]{0,60}\bdensity\b"
    r"|[\"']compact[\"']\s*\|\s*[\"']comfortable[\"']"
    r"|[\"']comfortable[\"']\s*\|\s*[\"']compact[\"']"
    r")",
    re.I,
)
_DENSITY_CHROME = re.compile(
    r"("
    r"\bdata-density(?:-toggle|-control|-pref)?\b"
    r"|\bdata-font-density\b"
    r"|<(?:Button|button|select|label)\b[^>]{0,300}"
    r"(?:[Dd]ensity|[Cc]omfortable|[Cc]ompact)"
    r")",
    re.I,
)
_DENSITY_PALETTE_ITEM = re.compile(
    r"<Command\.Item\b[^>]{0,400}(?:[Dd]ensity|[Cc]omfortable|[Cc]ompact)",
    re.I,
)
_DENSITY_APPLY = re.compile(
    r"("
    r"\bdata-density\s*="
    r"|document\.documentElement\.dataset\.density"
    r"|document\.body\.dataset\.density"
    r"|document\.documentElement\.setAttribute\s*\(\s*[\"']data-density"
    r"|document\.body\.setAttribute\s*\(\s*[\"']data-density"
    r"|document(?:\.documentElement|\.body)\.classList"
    r"|document(?:\.documentElement|\.body)\.className"
    r"|class:density-"
    r")"
    r"|\[data-density",
    re.I,
)
_DENSITY_CSS_HOOK = re.compile(
    r"("
    r":root\[data-density"
    r"|html\[data-density"
    r"|body\[data-density"
    r"|#app\[data-density"
    r"|\[data-density"
    r"|html\.density-"
    r"|body\.density-"
    r"|#app\.density-"
    r"|\.density-comfortable"
    r"|\.density-default"
    r"|\.density-compact"
    r")",
    re.I,
)
_DENSITY_SIZE_PROP = re.compile(
    r"("
    r"font-size\s*:"
    r"|--[A-Za-z0-9-]*(?:bubble-body|body-size|density-body|font-size-body|"
    r"bubble-font|density-size)[A-Za-z0-9-]*\s*:"
    r")",
    re.I,
)
_DENSITY_BODY_VAR = re.compile(
    r"--[A-Za-z0-9-]*(?:bubble-body|body-size|density-body|font-size-body|"
    r"bubble-font|density-size)[A-Za-z0-9-]*",
    re.I,
)
_BUBBLE_DENSITY_CLASS = re.compile(
    r"("
    r"data-bubble-body[\s\S]{0,500}(?:\bdensity\b|comfortable)"
    r"|(?:\bdensity\b|comfortable)[\s\S]{0,300}data-bubble-body"
    r"|class:text-(?:base|sm|\[15px\])[^\n]{0,80}\bdensity\b"
    r"|\bdensity\b[^\n]{0,80}class:text-(?:base|sm|\[15px\])"
    r")",
    re.I,
)
_DENSITY_RELOAD = re.compile(r"\blocation\s*\.\s*reload\s*\(")
_DENSITY_WORD = re.compile(r"\bdensity\b", re.I)
_PER_BUBBLE_FONT = re.compile(
    r"("
    r"\bdata-bubble-font\b"
    r"|per[- ]bubble font"
    r"|font[- ]picker"
    r"|fontFamily\s*=\s*\{[^}]{0,80}row\."
    r"|<(?:select|Select)\b[^>]{0,160}font[- ]?(?:family|face|picker)"
    r")",
    re.I,
)
_DENSITY_FONT_FACE_HTTP = re.compile(
    r"@font-face\b[^}]*url\s*\(\s*['\"]?https?://",
    re.I | re.S,
)
_DOCS_DENSITY_STEPS = re.compile(
    r"("
    r"(?:Default|Compact).{0,120}Comfortable"
    r"|Comfortable.{0,120}(?:Default|Compact)"
    r"|(?:local.{0,40})?density.{0,80}(?:Default|Comfortable|Compact)"
    r")",
    re.I | re.S,
)
_DOCS_LOCAL_DENSITY = re.compile(
    r"("
    r"local.{0,80}(?:density|Default|Comfortable|Compact)"
    r"|(?:density|Default|Comfortable).{0,80}local"
    r")",
    re.I | re.S,
)
_DOCS_DENSITY_BODIES = re.compile(
    r"("
    r"(?:bubble )?bod(?:y|ies).{0,80}(?:enlarg|larger|bigger|grow|size)"
    r"|(?:enlarg|larger|bigger|grow).{0,80}(?:bubble )?bod(?:y|ies)"
    r")",
    re.I | re.S,
)
_DOCS_DENSITY_NO_RELOAD = re.compile(
    r"("
    r"(?:density|Comfortable|bubble bod).{0,160}"
    r"(?:without (?:a )?reload|no reload|does not reload)"
    r"|(?:without (?:a )?reload|no reload|does not reload).{0,160}"
    r"(?:density|Comfortable|bubble bod)"
    r")",
    re.I | re.S,
)


def _density_web_src(crate: Path) -> str:
    """Product Svelte + TS + CSS (not design-system docs)."""
    web = crate / "web"
    parts: list[str] = []
    for p in sorted(web.rglob("*")):
        if "node_modules" in p.parts:
            continue
        if p.suffix in {".svelte", ".ts", ".css"}:
            parts.append(p.read_text())
    return "\n".join(parts)


def _density_has_control(src: str) -> bool:
    return bool(
        _DENSITY_HOOK.search(src)
        or _DENSITY_IDENT.search(src)
        or _DENSITY_VALUE.search(src)
        or _DENSITY_LABEL.search(src)
        or _DENSITY_STATE.search(src)
    )


def _density_has_two_steps(src: str) -> bool:
    has_hi = bool(_DENSITY_STEP_COMFORTABLE.search(src))
    has_lo = bool(_DENSITY_STEP_DEFAULT.search(src) or _DENSITY_STEP_COMPACT.search(src))
    return has_hi and has_lo


def _density_key_ok(key: str) -> bool:
    low = key.lower()
    mentions = "density" in low or "comfortable" in low
    namespaced = "interlace" in low or "." in key
    return mentions and namespaced


def _density_css_bumps_body(css: str) -> bool:
    """Comfortable / density hook changes a body size (font-size or CSS var)."""
    for m in _DENSITY_CSS_HOOK.finditer(css):
        window = css[m.start() : m.start() + 520]
        if _DENSITY_SIZE_PROP.search(window):
            return True
    vars_ = _DENSITY_BODY_VAR.findall(css)
    return len(vars_) >= 2


# #276 follow-up — wipe timeline height cache when density changes.
_DENSITY_STATE_READ = re.compile(r"(?<![\w.-])density(?![\w-])")
_DENSITY_CLEAR_PENDING = re.compile(
    r"("
    r"\bclearPendingMeasures\s*\("
    r"|\bpendingMeasures\s*=\s*\{\s*\}"
    r")"
)
_DENSITY_HEIGHT_WIPE = re.compile(
    r"("
    rf"{_HEIGHT_CACHE.pattern}\s*=\s*(?:\{{\s*\}}|Object\.create\s*\(\s*null\s*\))"
    rf"|delete\s+{_HEIGHT_CACHE.pattern}\s*\["
    rf"|Object\.keys\s*\(\s*{_HEIGHT_CACHE.pattern}\s*\)"
    r")"
)
_DENSITY_VIRTUALIZE_AFTER = re.compile(r"\bVIRTUALIZE_AFTER\s*=\s*250\b")
_DENSITY_CALL_SKIP = frozenset(
    {
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "function",
        "setItem",
        "getItem",
        "removeItem",
        "setTimeout",
        "clearTimeout",
        "requestAnimationFrame",
        "cancelAnimationFrame",
        "Object",
        "Math",
        "Number",
        "String",
        "Boolean",
        "Array",
        "parseInt",
        "parseFloat",
        "isFinite",
        "isNaN",
        "void",
        "typeof",
        "document",
        "window",
        "localStorage",
        "console",
        "Error",
        "Map",
        "Set",
        "JSON",
        "Date",
        "preventDefault",
        "stopPropagation",
        "getElementById",
        "querySelector",
        "querySelectorAll",
        "setAttribute",
        "getAttribute",
        "classList",
    }
)


def _density_fn_body(src: str, name: str) -> str:
    return (
        _ts_function_body(src, name)
        or _ts_fn_body(src, name)
        or _function_body(src, name)
    )


def _density_expand_calls(src: str, body: str, depth: int = 2) -> str:
    """Include named helpers persistDensity / a density $effect call."""
    chunks = [body]
    seen: set[str] = set()

    def walk(blob: str, left: int) -> None:
        for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob):
            if name in seen or name in _DENSITY_CALL_SKIP:
                continue
            seen.add(name)
            inner = _density_fn_body(src, name)
            if not inner:
                continue
            chunks.append(inner)
            if left > 0:
                walk(inner, left - 1)

    walk(body, depth)
    return "\n".join(chunks)


def _density_wipes_heights(blob: str) -> bool:
    """True if blob assigns an empty height cache or deletes every key."""
    if _DENSITY_HEIGHT_WIPE.search(blob):
        return True
    for m in re.finditer(
        rf"{_HEIGHT_CACHE.pattern}\s*=\s*([A-Za-z_]\w*)\b",
        blob,
    ):
        ident = m.group(m.lastindex or 0)
        if not ident or _HEIGHT_CACHE.fullmatch(ident):
            continue
        if re.search(
            rf"\b(?:const|let|var)\s+{re.escape(ident)}\b[^=]*=\s*\{{\s*\}}",
            blob,
        ):
            return True
    return False


def _density_path_wipes(blob: str) -> bool:
    return bool(_DENSITY_CLEAR_PENDING.search(blob)) and _density_wipes_heights(blob)


def _density_persist_only_pref(blob: str) -> bool:
    """persistDensity only writes density / localStorage — never the cache."""
    writes_pref = bool(
        re.search(r"\bdensity\s*=", blob)
        or re.search(r"localStorage\s*\.\s*setItem", blob)
        or re.search(r"dataset\.density\s*=", blob)
    )
    touches_cache = bool(
        _HEIGHT_CACHE.search(blob) or _DENSITY_CLEAR_PENDING.search(blob)
    )
    return writes_pref and not touches_cache


def _density_change_blobs(app_src: str, web_src: str) -> tuple[str, str]:
    """Expanded persistDensity body, then persist + density-tracking $effects."""
    persist = _density_fn_body(app_src, "persistDensity")
    persist_src = app_src
    if not persist:
        persist = _density_fn_body(web_src, "persistDensity")
        persist_src = web_src
    persist_x = _density_expand_calls(persist_src, persist) if persist else ""
    effects = [
        a for a in _svelte_effect_args(app_src) if _DENSITY_STATE_READ.search(a)
    ]
    effect_src = app_src
    if not effects:
        effects = [
            a for a in _svelte_effect_args(web_src) if _DENSITY_STATE_READ.search(a)
        ]
        effect_src = web_src
    effect_x = "\n".join(_density_expand_calls(effect_src, e) for e in effects)
    return persist_x, persist_x + "\n" + effect_x


def assert_font_density(crate: Path) -> None:
    """#276: local Default / Comfortable density; persist in localStorage.

    Comfortable enlarges timeline bubble bodies without a reload
    (data-density / CSS variable / class on html/body). Keep the
    system font. No Theme / Appearance menu (#218). Reduced motion
    unchanged (#222). No remote/webfont, no per-bubble font picker.
    Docs: local density; no reload; system font; OS appearance;
    no Theme menu.
    Follow-up: density change wipes the timeline height cache
    (clearPendingMeasures + rowHeights = {}). Keep VIRTUALIZE_AFTER,
    data-bubble-body, no location.reload.
    Do not rewrite #199 / #218 / #222 / #212 / #275.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#276: App.svelte required (local density control)")
    css_path = crate / "web" / "app.css"
    if not css_path.is_file():
        fail("#276: web/app.css required (system font + density size)")
    app = app_path.read_text()
    css = css_path.read_text()
    pal_path = crate / "web" / "lib" / "CommandPalette.svelte"
    pal = pal_path.read_text() if pal_path.is_file() else ""
    web_raw = _density_web_src(crate)
    web = _without_comments(web_raw)
    app_clean = _without_comments(app)
    pal_clean = _without_comments(pal)
    css_clean = _css_without_comments(css)

    # 1) A local density control exists (Default / Comfortable or Compact /
    #    Comfortable). Quiet chrome and/or a command-palette item.
    if not _density_has_control(web):
        fail(
            "#276: a local density control is required "
            "(Default / Comfortable or Compact / Comfortable) — "
            "quiet chrome (`data-density` / `data-density-toggle`) "
            "and/or a command-palette item, not a Theme / Appearance menu"
        )

    # 2) At least two steps.
    if not _density_has_two_steps(web):
        fail(
            "#276: density control must have at least two steps "
            "(Default / Comfortable or Compact / Comfortable)"
        )

    # 3) Surface is quiet chrome and/or the command palette — not a Theme menu.
    chrome_ok = bool(
        _DENSITY_HOOK.search(app_clean)
        or _DENSITY_CHROME.search(app_clean)
        or _DENSITY_IDENT.search(app_clean)
        or _DENSITY_STATE.search(app_clean)
        or _DENSITY_VALUE.search(app_clean)
        or _DENSITY_LABEL.search(app_clean)
    )
    palette_ok = bool(
        _DENSITY_HOOK.search(pal_clean)
        or _DENSITY_PALETTE_ITEM.search(pal_clean)
        or _DENSITY_IDENT.search(pal_clean)
        or _DENSITY_VALUE.search(pal_clean)
        or _DENSITY_LABEL.search(pal_clean)
        or _DENSITY_STEP_COMFORTABLE.search(pal_clean)
    )
    if not chrome_ok and not palette_ok:
        fail(
            "#276: density control must be quiet chrome and/or a "
            "command-palette item — not a Theme / Appearance menu"
        )

    # 4) Persist in namespaced localStorage (getItem + setItem).
    ls_keys = _ls_pref_keys(web)
    density_keys = [k for k in ls_keys if _density_key_ok(k)]
    persist_bits = [
        _windows_around(web, re.compile(r"localStorage"), before=160, after=220),
        _windows_around(web, _DENSITY_WORD, before=160, after=220),
        _windows_around(web, _DENSITY_VALUE, before=160, after=220),
    ]
    persist_surface = "\n".join(persist_bits)
    if not density_keys:
        fail(
            "#276: persist density in namespaced localStorage "
            "(getItem + setItem; e.g. interlace.density) — "
            "not config.toml / write_last_path"
        )
    if not re.search(r"localStorage\s*\.\s*setItem\s*\(", persist_surface):
        fail(
            "#276: persist density with localStorage.setItem "
            "(namespaced key; not iCloud, not write_last_path)"
        )
    if not re.search(r"localStorage\s*\.\s*getItem\s*\(", persist_surface) and not _LS_BRACKET.search(
        persist_surface
    ):
        fail(
            "#276: restore density from localStorage.getItem "
            "(same namespaced key)"
        )

    # 5) Do not write density to config.toml / write_last_path.
    if _LAST_PATH_API.search(persist_surface) or _CONFIG_TOML.search(persist_surface):
        fail(
            "#276: do not persist density via write_last_path / "
            "read_last_path / config.toml (localStorage only)"
        )
    session_path = repo_root() / "crates" / "interlace-core" / "src" / "session.rs"
    rust_path = crate / "src" / "main.rs"
    session = session_path.read_text() if session_path.is_file() else ""
    rust = rust_path.read_text() if rust_path.is_file() else ""
    if session_path.is_file():
        wl = _rust_fn_body(_without_comments(session), "write_last_path")
        if _DENSITY_WORD.search(wl) or any(
            "density" in k.lower() for k in _toml_keys_in_fn(wl)
        ):
            fail(
                "#276: do not rewrite session.rs write_last_path to dump "
                "density (config.toml is the last-archive pointer, not chrome prefs)"
            )
    rust_clean = _without_comments(session + "\n" + rust)
    for m in _DENSITY_WORD.finditer(rust_clean):
        window = rust_clean[max(0, m.start() - 360) : m.end() + 360]
        if _LAST_PATH_API.search(window) or _CONFIG_TOML.search(window):
            fail(
                "#276: do not persist density via write_last_path / "
                "read_last_path / config.toml (localStorage only)"
            )

    # 6) Comfortable / larger step changes bubble body size. No reload.
    apply_src = app_clean + "\n" + pal_clean + "\n" + css_clean + "\n" + web
    if not _DENSITY_APPLY.search(apply_src):
        fail(
            "#276: Comfortable must change timeline bubble body size via "
            "`data-density` / a CSS variable / a class on html/body "
            "(or the bubble) — apply without a reload"
        )
    if not (
        _density_css_bumps_body(css_clean)
        or _BUBBLE_DENSITY_CLASS.search(web)
    ):
        fail(
            "#276: Comfortable / the larger step must change timeline "
            "bubble body size (CSS `[data-density=…]` / `--bubble-body` "
            "variable / density class on the bubble)"
        )
    if "data-bubble-body" not in web:
        fail(
            "#276: keep data-bubble-body — Comfortable enlarges timeline "
            "bubble bodies"
        )
    density_set = "\n".join(
        [
            persist_surface,
            _windows_around(web, _DENSITY_HOOK, before=160, after=240),
            _windows_around(web, _DENSITY_APPLY, before=160, after=240),
        ]
    )
    if _DENSITY_RELOAD.search(density_set) or _DENSITY_RELOAD.search(
        _windows_around(web, _DENSITY_WORD, before=200, after=240)
    ):
        fail(
            "#276: density must apply without a reload (no location.reload)"
        )

    # 7) Keep the system font. No remote / webfont.
    fm = _TYPO_FONT_SANS.search(css)
    if not fm:
        fail("#276: keep --font-sans as the system UI stack (font-sans / --font-sans)")
    stack = fm.group(1)
    if "ui-sans-serif" not in stack or "-apple-system" not in stack:
        fail(
            "#276: --font-sans must stay system UI "
            "(ui-sans-serif and -apple-system still present)"
        )
    if "font-sans" not in css_clean and "var(--font-sans)" not in css_clean:
        fail("#276: keep font-sans / var(--font-sans) as the system stack")
    svelte_files = _product_svelte(crate)
    font_blob = css_clean + "\n" + "\n".join(
        _hue_surface(p.read_text()) for p in svelte_files
    )
    splash = crate / "index.html"
    if splash.is_file():
        font_blob += "\n" + splash.read_text()
    if (
        _TYPO_REMOTE_FONT.search(font_blob)
        or _THEME_CDN.search(font_blob)
        or _DENSITY_FONT_FACE_HTTP.search(font_blob)
    ):
        fail(
            "#276: no remote/webfont "
            "(fonts.googleapis / @font-face url http) — keep the system font"
        )

    # 8) Keep #218: no Theme / Appearance menu / data-theme.
    #    Keep color-scheme: light dark.
    svelte_files = svelte_files or _product_svelte(crate)
    theme_hits: list[str] = []
    for p in svelte_files:
        surface = _hue_surface(p.read_text())
        if _APPEARANCE_THEME_UI.search(surface) or _APPEARANCE_MENU_LABEL.search(surface):
            theme_hits.append(str(p.relative_to(crate)))
    rust_surface = _without_comments(rust)
    if _APPEARANCE_THEME_UI.search(rust_surface) or _APPEARANCE_MENU_LABEL.search(
        rust_surface
    ):
        theme_hits.append("src/main.rs")
    if theme_hits:
        fail(
            "#276: keep #218 — no Theme / Appearance menu / data-theme "
            "(density is not a color theme). Found in: "
            + ", ".join(theme_hits)
        )
    if not _CONTRAST_COLOR_SCHEME.search(css):
        fail(
            "#276: keep color-scheme: light dark on :root / html "
            "(#218; OS appearance flips without a reload)"
        )

    # 9) Keep #222 reduced motion. No per-bubble font picker.
    js_blob = _motion_js_blob(crate)
    if not _MOTION_JS_REDUCE.search(js_blob):
        fail(
            "#276: keep #222 reduced motion "
            "(matchMedia / MediaQuery / prefersReducedMotion)"
        )
    if not _MOTION_DURATION_ZERO.search(js_blob):
        fail("#276: keep #222 reduced-motion duration 0")
    if _PER_BUBBLE_FONT.search(web):
        fail(
            "#276: no per-bubble font picker "
            "(one local density control, not a font per message)"
        )

    # 10) Docs: local Default / Comfortable; enlarges bubble bodies
    #     without reload; system font; OS appearance; no Theme menu.
    docs_path = repo_root() / "docs" / "user" / "app.md"
    if not docs_path.is_file():
        fail(
            "#276: docs/user/app.md required — local Default / Comfortable "
            "density; enlarges bubble bodies without reload; system font; "
            "OS appearance; no Theme menu"
        )
    dtxt = docs_path.read_text()
    if not _DOCS_DENSITY_STEPS.search(dtxt) or not _DOCS_LOCAL_DENSITY.search(dtxt):
        fail(
            "#276: docs/user/app.md must say local Default / Comfortable "
            "(or Compact / Comfortable) density"
        )
    if not _DOCS_DENSITY_BODIES.search(dtxt):
        fail(
            "#276: docs/user/app.md must say density enlarges bubble bodies"
        )
    if not _DOCS_DENSITY_NO_RELOAD.search(dtxt):
        fail(
            "#276: docs/user/app.md must say density enlarges bubble bodies "
            "without a reload"
        )
    if not _DOCS_TYPO_NO_REMOTE_FONT.search(dtxt):
        fail(
            "#276: docs/user/app.md must say system font / no remote font"
        )
    if not _CONTRAST_DOCS_SYSTEM.search(dtxt):
        fail(
            "#276: docs/user/app.md must say the app follows OS / system appearance"
        )
    if not _APPEARANCE_DOCS_NO_THEME.search(dtxt):
        fail("#276: docs/user/app.md must say there is no Theme menu")

    # 11) Density change wipes the timeline height cache.
    persist_x, density_change = _density_change_blobs(app_clean, web)
    if not _density_path_wipes(density_change):
        if persist_x and _density_persist_only_pref(persist_x):
            fail(
                "#276: persistDensity must wipe the timeline height cache "
                "(clearPendingMeasures + rowHeights = {}) — "
                "do not only write density / localStorage; Comfortable "
                "changes bubble heights and stale rowHeights jump a "
                "virtualized list"
            )
        fail(
            "#276: persistDensity (or a density $effect) must wipe the "
            "timeline height cache (clearPendingMeasures + rowHeights = {}) "
            "when density changes"
        )

    # 12) Keep VIRTUALIZE_AFTER = 250, data-bubble-body, no location.reload.
    if not _DENSITY_VIRTUALIZE_AFTER.search(app_clean):
        fail(
            "#276: keep VIRTUALIZE_AFTER = 250 — density must not turn off "
            "or retune #224 virtualize-after-250"
        )
    if "data-bubble-body" not in web:
        fail(
            "#276: keep data-bubble-body — Comfortable enlarges timeline "
            "bubble bodies (density wipe is not a reason to drop the hook)"
        )
    if _DENSITY_RELOAD.search(density_change) or _DENSITY_RELOAD.search(
        _windows_around(web, _DENSITY_WORD, before=200, after=240)
    ):
        fail(
            "#276: density must apply without a reload (no location.reload) "
            "— wipe rowHeights in-process"
        )


# #277 — leftover chrome in system light (named --chrome-* leftovers).
# Preview / chips / inspector / review / palette / toasts; dark unchanged.
_CHROME_FAMILIES = (
    "preview",
    "chip",
    "inspector",
    "review",
    "palette",
    "toast",
)
_CHROME_FAMILY_EXAMPLES = (
    "--chrome-preview-fg",
    "--chrome-chip-bg / --chrome-chip-fg",
    "--chrome-inspector-fg",
    "--chrome-review-card",
    "--chrome-palette",
    "--chrome-toast",
)
_CHROME_GENERIC_VARS = frozenset(
    {
        "--color-muted",
        "--color-muted-foreground",
        "--color-background",
        "--color-foreground",
        "--color-border",
        "--color-card",
        "--color-card-foreground",
        "--color-input",
        "--color-primary",
        "--color-primary-foreground",
        "--color-secondary",
        "--color-secondary-foreground",
        "--color-accent",
        "--color-accent-foreground",
        "--color-destructive",
        "--color-warning",
        "--color-warning-foreground",
        "--color-success",
        "--color-success-foreground",
        "--color-ring",
        "--overlay",
        "--scrim",
        "--lightbox-scrim",
        "--lightbox-chrome-fg",
        "--search-mark",
        "--color-search-mark",
        "--bubble-me",
        "--bubble-them",
        "--bubble-body-size",
        "--font-sans",
    }
)
_CHROME_GENERIC_REF = re.compile(
    r"var\(\s*--(?:color-)?(?:muted(?:-foreground)?|background|border|card)\s*\)",
    re.I,
)
_CHROME_VAR_DEF = re.compile(r"(--[A-Za-z0-9-]+)\s*:\s*([^;]+);")
_CHROME_VAR_USE = re.compile(r"var\(\s*(--[A-Za-z0-9-]+)\s*\)")
_CHROME_DARK_BG = re.compile(
    r"--color-background\s*:\s*hsl\(\s*240\s+10%\s+3\.9%\s*\)",
    re.I,
)
_CHROME_DARK_MARK = re.compile(r"--search-mark\b")
_CHROME_DARK_MARK_VAL = re.compile(
    r"--search-mark\s*:\s*hsl\(\s*45\s+93%\s+32%\s*/\s*0\.6\s*\)",
    re.I,
)
_CHROME_DARK_WARN = re.compile(r"--color-warning\b")
_CHROME_DARK_WARN_VAL = re.compile(
    r"--color-warning\s*:\s*hsl\(\s*38\s+48%\s+70%\s*\)",
    re.I,
)
_CHROME_HOOKS = (
    ("chip", "data-platform-chip"),
    ("inspector", "data-person-inspector"),
    ("review", "data-review-card"),
    ("palette", "data-command-palette"),
    ("toast", "data-toast"),
)
_DOCS_LEFTOVER_CHROME = re.compile(
    r"("
    r"leftover chrome"
    r"|remaining chrome"
    r")",
    re.I,
)
_DOCS_LEFTOVER_SURFACES = re.compile(
    r"("
    r"preview.{0,120}chips?.{0,120}inspector.{0,120}review.{0,120}"
    r"palette.{0,120}toasts?"
    r")",
    re.I | re.S,
)
_DOCS_LIGHT_READABLE = re.compile(
    r"("
    r"readable.{0,80}(?:in )?(?:system )?light"
    r"|(?:system )?light.{0,80}readable"
    r")",
    re.I | re.S,
)


def _chrome_leftover_family(name: str) -> str | None:
    """Map a CSS custom property to a leftover-chrome family, or None.

    Accepts `--chrome-preview-fg`, `--color-chrome-chip-bg`, `--leftover-toast`,
    or a dedicated `--preview-fg` / `--chip-bg`. Generic `--color-muted` is not
    a leftover family. `--lightbox-chrome-fg` is #218 lightbox, not leftover.
    """
    if name in _CHROME_GENERIC_VARS:
        return None
    n = name.lower()
    if n.startswith("--"):
        n = n[2:]
    if n.startswith("color-"):
        n = n[6:]
    if n.startswith("chrome-"):
        n = n[7:]
    elif n.startswith("leftover-"):
        n = n[9:]
    for prefix in ("people-", "platform-", "person-", "command-"):
        if n.startswith(prefix):
            n = n[len(prefix) :]
            break
    for fam in _CHROME_FAMILIES:
        if n == fam or n.startswith(fam + "-") or n.endswith("-" + fam):
            return fam
    return None


def _chrome_token_stem(name: str) -> str:
    n = name.lower()
    if n.startswith("--color-"):
        return n[len("--color-") :]
    if n.startswith("--"):
        return n[2:]
    return n


def _chrome_light_defs(css: str) -> dict[str, str]:
    """Leftover-chrome custom properties in light (@theme / non-dark :root)."""
    light = _contrast_light_blob(css)
    found: dict[str, str] = {}
    for m in _CHROME_VAR_DEF.finditer(light):
        name, value = m.group(1), m.group(2).strip()
        if _chrome_leftover_family(name):
            found[name] = value
    return found


def _chrome_by_family(defs: dict[str, str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {fam: [] for fam in _CHROME_FAMILIES}
    for name in defs:
        fam = _chrome_leftover_family(name)
        if fam:
            grouped[fam].append(name)
    return grouped


def _chrome_value_is_generic(value: str, light_blob: str) -> bool:
    if _CHROME_GENERIC_REF.search(value):
        return True
    val_hsl = _hsl_tuple(value)
    if not val_hsl:
        return False
    for generic in (
        "--color-muted-foreground",
        "--color-muted",
        "--color-background",
        "--color-border",
        "--color-card",
    ):
        g = _css_var(light_blob, (generic,))
        if not g:
            continue
        gh = _hsl_tuple(g)
        if gh and gh == val_hsl:
            return True
    return False


def _chrome_hook_blob(src: str, hook: str) -> str:
    at = src.find(hook)
    if at < 0:
        return ""
    tag = _markup_open_tag(src, src.rfind("<", 0, at + 1))
    return tag + "\n" + src[at : at + 3600]


def _chrome_preview_blob(src: str) -> str:
    m = re.search(r"\{p\.preview\b", src)
    if not m:
        return ""
    tags = _ancestor_tags(src, m.start(), limit=6)
    found = _open_tag_before(src, m.start())
    tag = found[1] if found else ""
    return "\n".join([*tags, tag, src[max(0, m.start() - 80) : m.start() + 400]])


def _chrome_attr_rule_bodies(css: str, hook: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(rf"\[{re.escape(hook)}\][^{{]*\{{", css):
        body = _css_brace_body(css, css.find("{", m.start()))
        if body:
            out.append(body)
    return out


def _chrome_class_rule_bodies(css: str, tag: str) -> list[str]:
    out: list[str] = []
    for cls in _appearance_class_names(tag):
        for m in re.finditer(rf"\.{re.escape(cls)}\b[^{{]*\{{", css):
            body = _css_brace_body(css, css.find("{", m.start()))
            if body:
                out.append(body)
    return out


def _chrome_blob_uses_vars(blob: str, css: str, hook: str, names: list[str]) -> bool:
    if not names:
        return False
    want = set(names)
    if want.intersection(_CHROME_VAR_USE.findall(blob)):
        return True
    for name in names:
        stem = _chrome_token_stem(name)
        if not stem:
            continue
        if re.search(
            rf"(?<![\w-])(?:text|bg|border|text-color|color)-{re.escape(stem)}"
            rf"(?:/\d+)?(?![\w-])",
            blob,
        ):
            return True
        if re.search(rf"(?<![\w-]){re.escape(stem)}(?![\w-])", blob):
            return True
    tag = blob.split("\n", 1)[0] if blob else ""
    rule_blobs = list(_chrome_class_rule_bodies(css, tag))
    if hook:
        rule_blobs.extend(_chrome_attr_rule_bodies(css, hook))
    rules = "\n".join(rule_blobs)
    return bool(want.intersection(_CHROME_VAR_USE.findall(rules)))


def assert_light_chrome(crate: Path) -> None:
    """#277: leftover chrome readable in system light via named --chrome-* vars.

    Six surfaces (people preview, data-platform-chip, data-person-inspector,
    data-review-card, data-command-palette, data-toast) use dedicated leftovers,
    not only generic muted. No amber/yellow. Dark media keeps the current
    --color-background / --search-mark / --color-warning strings. No Theme
    menu. Docs: leftover chrome readable in system light; dark archival.
    Do not rewrite #198 / #217 / #218 / #219 / #276.
    """
    css_path = crate / "web" / "app.css"
    if not css_path.is_file():
        fail("#277: web/app.css required (named leftover-chrome light vars)")
    css = css_path.read_text()
    css_clean = _css_without_comments(css)
    light_blob = _contrast_light_blob(css)
    dark_blob = _contrast_dark_blob(css)

    # 1) Named leftover-chrome CSS variables in light (@theme / non-dark :root).
    defs = _chrome_light_defs(css)
    by_fam = _chrome_by_family(defs)
    if not defs:
        fail(
            "#277: named leftover-chrome CSS variables required in light "
            "(@theme / non-dark :root) — `--chrome-preview-fg`, "
            "`--chrome-chip-bg` / `--chrome-chip-fg`, `--chrome-inspector-fg`, "
            "`--chrome-review-card`, `--chrome-palette`, `--chrome-toast` "
            "(names may vary; must be `--chrome-*` or equivalent dedicated "
            "leftovers, not only generic `--color-muted`)"
        )
    missing = [fam for fam in _CHROME_FAMILIES if not by_fam[fam]]
    if missing:
        examples = ", ".join(
            ex
            for fam, ex in zip(_CHROME_FAMILIES, _CHROME_FAMILY_EXAMPLES)
            if fam in missing
        )
        fail(
            "#277: light leftover-chrome vars must cover preview, chips, "
            "inspector, review, palette, and toast "
            f"(missing: {', '.join(missing)}; e.g. {examples}) — "
            "not only generic `--color-muted`"
        )
    generic_fams = [
        fam
        for fam, names in by_fam.items()
        if names and all(_chrome_value_is_generic(defs[n], light_blob) for n in names)
    ]
    if generic_fams:
        fail(
            "#277: leftover-chrome light vars must be dedicated leftovers "
            "(not only aliases of `--color-muted` / `--color-muted-foreground` "
            f"/ `--color-background`); generic-only families: "
            + ", ".join(generic_fams)
        )

    # 2) The six surfaces use those vars.
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#277: App.svelte required (people preview / chips / inspector)")
    app = app_path.read_text()
    review_path = crate / "web" / "lib" / "ReviewPane.svelte"
    review = review_path.read_text() if review_path.is_file() else ""
    pal_path = crate / "web" / "lib" / "CommandPalette.svelte"
    pal = pal_path.read_text() if pal_path.is_file() else ""
    toast_path = crate / "web" / "lib" / "components" / "ui" / "toast" / "toast.svelte"
    toast = toast_path.read_text() if toast_path.is_file() else ""
    svelte_blob = "\n".join(p.read_text() for p in _product_svelte(crate))
    hook_src = {
        "chip": svelte_blob,
        "inspector": app,
        "review": review or svelte_blob,
        "palette": pal or svelte_blob,
        "toast": toast or svelte_blob,
    }

    preview_blob = _chrome_preview_blob(app) or _chrome_preview_blob(svelte_blob)
    if not preview_blob.strip():
        fail(
            "#277: people preview / last-activity line required "
            "(wire `--chrome-preview-fg` or equivalent, not only muted)"
        )
    if not _chrome_blob_uses_vars(
        preview_blob, css_clean, "", by_fam["preview"]
    ):
        fail(
            "#277: people preview must use a named leftover-chrome var "
            "(`--chrome-preview-fg` / `var(--chrome-preview-*)` / "
            "`text-chrome-preview-fg`) — not only `text-muted-foreground`"
        )

    for fam, hook in _CHROME_HOOKS:
        blob = _chrome_hook_blob(hook_src[fam], hook)
        if not blob.strip() or hook not in blob:
            fail(
                f"#277: {hook} required (wire `--chrome-{fam}*` leftover, "
                "not only generic muted / background)"
            )
        if not _chrome_blob_uses_vars(blob, css_clean, hook, by_fam[fam]):
            fail(
                f"#277: {hook} must use a named leftover-chrome var "
                f"(`--chrome-{fam}*`) — not only generic muted / background"
            )

    # 3) No amber-* / yellow-* in product Svelte.
    svelte_files = _product_svelte(crate)
    if not svelte_files:
        fail("#277: crates/interlace-tauri/web/**/*.svelte required (light chrome)")
    offenders: list[str] = []
    for p in svelte_files:
        hits = [
            h
            for h in _hue_findings(p.read_text())
            if h.startswith("amber") or h.startswith("yellow")
        ]
        if hits:
            offenders.append(f"{p.relative_to(crate)}: {'; '.join(hits)}")
    if offenders:
        fail(
            "#277: product Svelte must not contain amber-* / yellow-* "
            "(CSS variables only). Found:\n  " + "\n  ".join(offenders)
        )

    # 4) Dark media still has the current dark strings (dark unchanged).
    if not dark_blob.strip():
        fail(
            "#277: keep @media (prefers-color-scheme: dark) — "
            "dark is unchanged (archival look)"
        )
    if not _CHROME_DARK_BG.search(dark_blob):
        fail(
            "#277: dark @media must keep the current "
            "`--color-background: hsl(240 10% 3.9%)` (dark unchanged)"
        )
    if not _CHROME_DARK_MARK.search(dark_blob):
        fail(
            "#277: dark @media must keep `--search-mark` "
            "(dark unchanged; do not drop #217)"
        )
    if not _CHROME_DARK_MARK_VAL.search(dark_blob):
        fail(
            "#277: dark @media must keep the current "
            "`--search-mark: hsl(45 93% 32% / 0.6)` (dark unchanged)"
        )
    if not _CHROME_DARK_WARN.search(dark_blob):
        fail(
            "#277: dark @media must keep `--color-warning` "
            "(dark unchanged; do not drop #219)"
        )
    if not _CHROME_DARK_WARN_VAL.search(dark_blob):
        fail(
            "#277: dark @media must keep the current "
            "`--color-warning: hsl(38 48% 70%)` (dark unchanged)"
        )

    # 5) No Theme / Appearance menu / data-theme.
    theme_hits: list[str] = []
    for p in svelte_files:
        surface = _hue_surface(p.read_text())
        if _APPEARANCE_THEME_UI.search(surface) or _APPEARANCE_MENU_LABEL.search(surface):
            theme_hits.append(str(p.relative_to(crate)))
    rust_path = crate / "src" / "main.rs"
    rust = rust_path.read_text() if rust_path.is_file() else ""
    rust_surface = _without_comments(rust)
    if _APPEARANCE_THEME_UI.search(rust_surface) or _APPEARANCE_MENU_LABEL.search(
        rust_surface
    ):
        theme_hits.append("src/main.rs")
    if theme_hits:
        fail(
            "#277: not in scope — no Theme / Appearance menu / data-theme "
            "(OS appearance only; leftover chrome is CSS variables). Found in: "
            + ", ".join(theme_hits)
        )

    # 6) Docs: leftover chrome readable in system light; dark archival;
    #    no Theme menu.
    docs_path = repo_root() / "docs" / "user" / "app.md"
    if not docs_path.is_file():
        fail(
            "#277: docs/user/app.md required — leftover chrome readable in "
            "system light; dark archival; no Theme menu"
        )
    dtxt = docs_path.read_text()
    if not _DOCS_LEFTOVER_CHROME.search(dtxt) and not _DOCS_LEFTOVER_SURFACES.search(
        dtxt
    ):
        fail(
            "#277: docs/user/app.md must say leftover chrome "
            "(preview, chips, inspector, review, palette, toasts) "
            "is readable in system light"
        )
    if not _DOCS_LIGHT_READABLE.search(dtxt):
        fail(
            "#277: docs/user/app.md must say leftover chrome is readable "
            "in system light"
        )
    if not _APPEARANCE_DOCS_ARCHIVAL.search(dtxt):
        fail("#277: docs/user/app.md must say dark stays the archival look")
    if not _APPEARANCE_DOCS_NO_THEME.search(dtxt):
        fail("#277: docs/user/app.md must say there is no Theme menu")

    # Keep #217 muted L / search-mark, #218 color-scheme, #219 warning,
    # #276 density. Do not rewrite those asserts.
    light_muted = _css_var(light_blob, ("--color-muted-foreground",))
    if not light_muted or not _hsl_tuple(light_muted):
        fail("#277: keep #217 light --color-muted-foreground (HSL)")
    if (_hsl_tuple(light_muted) or (0, 0, 99))[2] > 40:
        fail("#277: keep #217 light --color-muted-foreground HSL L ≤ 40")
    if not _css_var(light_blob, _CONTRAST_SEARCH_MARK_NAMES) or not _css_var(
        dark_blob, _CONTRAST_SEARCH_MARK_NAMES
    ):
        fail("#277: keep #217 --search-mark in light and dark")
    if not _CONTRAST_COLOR_SCHEME.search(css):
        fail("#277: keep #218 color-scheme: light dark on :root / html")
    if not _css_var(light_blob, _STATUS_WARNING_NAMES):
        fail("#277: keep #219 --warning / --color-warning in light")
    web = app + "\n" + pal + "\n" + css_clean
    if not _DENSITY_HOOK.search(web) and not _DENSITY_IDENT.search(web):
        fail("#277: keep #276 local density (`data-density` / fontDensity)")


# #278 — finish en+tr chrome (Review / Import / Doctor). Additive;
# do not rewrite #131 assert_chrome_locale.
_PANE_CHROME_FILES = (
    "ReviewPane.svelte",
    "ImportPane.svelte",
    "DoctorPane.svelte",
)
_PANE_CHROME_PHRASES = (
    ("ReviewPane.svelte", "Nothing to review", "Review empty-state title"),
    ("ReviewPane.svelte", "Name-only WhatsApp matches", "Review empty-state body"),
    ("ReviewPane.svelte", "Loading review queue", "Review loading"),
    ("ReviewPane.svelte", "Link these people", "Review confirm “Link these people”"),
    ("ReviewPane.svelte", "Stop suggesting", "Review confirm “Stop suggesting”"),
    ("ReviewPane.svelte", "Undo last link", "Review undo / confirm “Undo last link”"),
    ("ReviewPane.svelte", "Undoing", "Review “Undoing…”"),
    ("ImportPane.svelte", "No file selected", "Import empty-state title"),
    ("ImportPane.svelte", "Pick a WhatsApp ZIP", "Import empty-state body"),
    ("ImportPane.svelte", "Pick file", "Import “Pick file”"),
    ("DoctorPane.svelte", "No doctor issues", "Doctor empty-state title"),
    ("DoctorPane.svelte", "Unreferenced files still need GC", "Doctor empty-state body"),
    ("DoctorPane.svelte", "Run integrity check", "Doctor integrity confirm"),
    ("DoctorPane.svelte", "Rebuild search index", "Doctor rebuild confirm"),
    ("DoctorPane.svelte", "Garbage-collect unused CAS", "Doctor GC confirm"),
)
_PANE_EN_REQUIRED = (
    "Nothing to review",
    "Name-only WhatsApp matches",
    "Loading review queue",
    "Link these people",
    "Stop suggesting",
    "Undo last link",
    "No file selected",
    "Pick a WhatsApp ZIP",
    "Pick file",
    "No doctor issues",
    "Unreferenced files still need GC",
    "Run integrity check",
    "Rebuild search index",
    "Garbage-collect unused CAS",
)
_PANE_BACKUP_LEFTOVER = (
    "There is no separate backup command",
    "Do not keep the",
    "Time Machine",
)
_DOCS_PANE_CHROME_LOCALE = re.compile(
    r"("
    r"Review.{0,80}Import.{0,80}Doctor.{0,100}"
    r"(?:chrome.{0,60})?(?:follows.{0,40}OS|OS language|en\s*/\s*tr)"
    r"|"
    r"(?:Review|Import|Doctor).{0,24}(?:/|,).{0,24}"
    r"(?:Review|Import|Doctor).{0,24}(?:/|,).{0,24}"
    r"(?:Review|Import|Doctor).{0,100}"
    r"(?:chrome.{0,60})?(?:follows.{0,40}OS|OS language|en\s*/\s*tr)"
    r")",
    re.I | re.S,
)
_DOCS_PANE_BODIES_STAY = re.compile(
    r"("
    r"bodies stay as imported"
    r"|message bodies stay as imported"
    r"|bodies stay as (?:imported|stored)"
    r"|bodies? (?:are|stay|remain) (?:as )?(?:imported|stored|unchanged)"
    r")",
    re.I,
)
_LOCALE_FETCH = re.compile(
    r"\bfetch\s*\(\s*[`'\"`][^`'\"`]{0,160}"
    r"(?:locale|locales|i18n|l10n|en\.json|tr\.json)",
    re.I,
)
_THIRD_PACK_STEM = re.compile(
    r"(?:^|[._-])(de|fr|es|it|nl|pt|ru|ja|zh|ar|ko)(?:[-_][A-Za-z]+)?$",
    re.I,
)


def _pane_file(crate: Path, name: str) -> Path:
    return crate / "web" / "lib" / name


def _svelte_attr_raw(tag: str, name: str) -> str:
    m = re.search(
        rf"""\b{re.escape(name)}\s*=\s*(
            \{{(?:[^{{}}]|\{{[^{{}}]*\}})*\}}
            |\"[^\"]*\"
            |'[^']*'
        )""",
        tag,
        re.X | re.S,
    )
    return m.group(1) if m else ""


def _split_first_arg(args: str) -> str:
    i = 0
    n = len(args)
    depth = 0
    while i < n:
        nxt = _js_next(args, i)
        if nxt != i:
            i = nxt
            continue
        c = args[i]
        if c in "({[":
            depth += 1
        elif c in ")}]":
            depth -= 1
        elif c == "," and depth == 0:
            return args[:i].strip()
        i += 1
    return args.strip()


def _call_first_args(src: str, name: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(rf"\b{re.escape(name)}\s*\(", src):
        prefix = src[max(0, m.start() - 80) : m.start()]
        if re.search(r"(?:async\s+)?function\s+$", prefix):
            continue
        if re.search(r"(?:const|let|var)\s+$", prefix):
            continue
        args = _call_arg(src, m.end() - 1)
        if args.strip():
            out.append(_split_first_arg(args))
    return out


def _chrome_pack_entries(text: str) -> dict[str, str]:
    """Parse `key: "value"` entries from a chrome pack object."""
    blob = text
    m = re.search(
        r"export\s+const\s+(?:en|tr)\s*(?::\s*\w+\s*)?=\s*\{",
        text,
    )
    if m:
        brace = text.find("{", m.start())
        end = _match_closer(text, brace)
        if end > brace:
            blob = text[brace + 1 : end]
    entries: dict[str, str] = {}
    i = 0
    n = len(blob)
    key_rx = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*:")
    while i < n:
        km = key_rx.search(blob, i)
        if not km:
            break
        j = km.end()
        while j < n and blob[j] in " \t\n\r":
            j += 1
        if j >= n or blob[j] not in "'\"`":
            i = km.end()
            continue
        end = _js_next(blob, j)
        raw = blob[j + 1 : end - 1] if end > j + 1 else ""
        entries[km.group(1)] = (
            raw.replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace('\\"', '"')
            .replace("\\'", "'")
            .replace("\\\\", "\\")
        )
        i = end
    return entries


def _keys_for_phrase(entries: dict[str, str], phrase: str) -> list[str]:
    return [k for k, v in entries.items() if phrase in v]


def _pane_chrome_phrases(panes: dict[str, str]) -> list[str]:
    leftover = [
        label for name, phrase, label in _PANE_CHROME_PHRASES if phrase in panes[name]
    ]
    if re.search(r">\s*Cancel\s*<", panes["ImportPane.svelte"]):
        leftover.append("Import Cancel")
    return leftover


def _pane_chrome_unwired(
    panes: dict[str, str], helpers: set[str]
) -> list[str]:
    """EmptyState / ask() / undo / pick / cancel still not going through t()."""
    leftover: list[str] = []
    for name in _PANE_CHROME_FILES:
        src = panes[name]
        for block in _empty_state_blocks(src):
            for attr in ("title", "body", "actionLabel"):
                val = _svelte_attr_raw(block, attr)
                if val and not _markup_uses_chrome_helper(val, helpers, src):
                    leftover.append(f"{name.split('.', 1)[0]} EmptyState {attr}")
    for name in ("ReviewPane.svelte", "DoctorPane.svelte"):
        src = panes[name]
        asks = _call_first_args(src, "ask")
        if not asks:
            leftover.append(
                f"{name.split('.', 1)[0]} ConfirmDialog titles "
                "(ask() first arg must be t())"
            )
            continue
        for arg in asks:
            if not _markup_uses_chrome_helper(arg, helpers, src):
                leftover.append(
                    f"{name.split('.', 1)[0]} ConfirmDialog title {arg[:48]}"
                )
    review = panes["ReviewPane.svelte"]
    undo_inners = _control_inners(review, re.compile(r"data-review-undo"))
    if not undo_inners and re.search(r"Undo last link|requestUndo", review):
        undo_inners = _control_inners(review, re.compile(r"requestUndo"))
    if undo_inners and not any(
        _markup_uses_chrome_helper(inner, helpers, review) for inner in undo_inners
    ):
        leftover.append("Review undo label")
    imp = panes["ImportPane.svelte"]
    pick_inners = _control_inners(imp, re.compile(r"pick\(\s*false\s*\)"))
    if pick_inners and not any(
        _markup_uses_chrome_helper(inner, helpers, imp) for inner in pick_inners
    ):
        leftover.append("Import Pick file button")
    cancel_inners = _control_inners(imp, re.compile(r"data-import-cancel"))
    if not cancel_inners:
        leftover.append("Import Cancel")
    elif not any(
        _markup_uses_chrome_helper(inner, helpers, imp) for inner in cancel_inners
    ):
        leftover.append("Import Cancel")
    seen: set[str] = set()
    out: list[str] = []
    for item in leftover:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def assert_chrome_locale_panes(crate: Path) -> None:
    """#278: Review / Import / Doctor remaining chrome uses t().

    Empty states, ConfirmDialog titles (Link these people / Stop suggesting /
    Undo last link / doctor integrity / rebuild / GC), undo label, Pick file,
    and Import Cancel go through t(). New keys exist in both packs; tr values
    are not identical English copies. No t(body_text|snippet|display_name|
    preview). detectLocale stays OS-first (tr* → tr). No third pack. No fetch
    of locale files. Keep #131 Arşiv aç / Doktor. Docs: Review / Import /
    Doctor chrome follows OS language (en/tr); bodies stay as imported.
    Do not rewrite #131.
    """
    root = repo_root()
    panes: dict[str, str] = {}
    for name in _PANE_CHROME_FILES:
        path = _pane_file(crate, name)
        if not path.is_file():
            fail(
                f"#278: {name} required "
                "(Review / Import / Doctor remaining chrome uses t())"
            )
        panes[name] = path.read_text()
    logic = _web_logic(crate)
    cleaned = _without_comments(logic)
    helpers = _chrome_helper_names(logic)
    en_text = _chrome_en_text(crate)
    tr_text = _chrome_tr_text(crate)
    i18n_path = crate / "web" / "lib" / "i18n.ts"
    i18n = i18n_path.read_text() if i18n_path.is_file() else ""

    # 1) Remaining Review / Import / Doctor chrome uses t() — not hardcoded English.
    leftover = _pane_chrome_phrases(panes)
    if leftover:
        fail(
            "#278: Review / Import / Doctor remaining chrome must use t() — "
            "still hardcoded English: " + "; ".join(leftover)
        )
    unwired = _pane_chrome_unwired(panes, helpers)
    if unwired:
        fail(
            "#278: Review / Import / Doctor remaining chrome must use t() "
            "(empty states, ConfirmDialog titles, undo, Pick file, Import Cancel): "
            + "; ".join(unwired)
        )

    # 2) Those strings live in the en pack; same keys in tr; tr is not an English copy.
    if not en_text.strip() or not tr_text.strip():
        fail("#278: en + tr chrome packs required (do not drop #131 packs)")
    en_entries = _chrome_pack_entries(en_text)
    tr_entries = _chrome_pack_entries(tr_text)
    if not en_entries or not tr_entries:
        fail("#278: could not parse chrome pack key/value entries from en.ts / tr.ts")
    missing_en = [p for p in _PANE_EN_REQUIRED if not _keys_for_phrase(en_entries, p)]
    if "Cancel" not in en_entries.values() and not _keys_for_phrase(en_entries, "Cancel"):
        missing_en.append("Cancel")
    if missing_en:
        fail(
            "#278: new Review / Import / Doctor chrome keys must exist in the en pack "
            f"(missing values: {', '.join(missing_en)})"
        )
    extra_en = set(en_entries) - set(tr_entries)
    extra_tr = set(tr_entries) - set(en_entries)
    if extra_en or extra_tr:
        bits: list[str] = []
        if extra_en:
            bits.append("in en only: " + ", ".join(sorted(extra_en)))
        if extra_tr:
            bits.append("in tr only: " + ", ".join(sorted(extra_tr)))
        fail(
            "#278: same ChromeKey on both en and tr packs — " + "; ".join(bits)
        )
    copied: list[str] = []
    seen_keys: set[str] = set()
    for phrase in (*_PANE_EN_REQUIRED, "Cancel"):
        for key in _keys_for_phrase(en_entries, phrase):
            if key in seen_keys:
                continue
            seen_keys.add(key)
            ev = en_entries.get(key, "").strip()
            tv = tr_entries.get(key, "").strip()
            if not tv:
                copied.append(f"{key} missing in tr")
            elif tv == ev:
                copied.append(key)
    if copied:
        fail(
            "#278: for new Review / Import / Doctor keys, tr values must not be "
            "identical English copies: " + ", ".join(copied)
        )

    # 3) Never t(body_text|snippet|display_name|preview).
    body_blob = logic + "\n" + "\n".join(panes[n] for n in _PANE_CHROME_FILES)
    if _chrome_helper_on_body(body_blob, helpers):
        fail(
            "#278: do not pass body_text / snippet / display_name / preview "
            "through t() — message bodies stay as imported"
        )

    # 4) detectLocale still OS-first (tr* → tr). No third pack. No fetch of locale files.
    detect = _function_body(i18n, "detectLocale") or _function_body(cleaned, "detectLocale")
    resolver = detect or _locale_resolver_surface(cleaned) or _locale_resolver_surface(logic)
    if not _OS_LOCALE_READ.search(resolver) and not _OS_LOCALE_READ.search(i18n):
        fail(
            "#278: detectLocale must stay OS-first "
            "(navigator.language / navigator.languages / Intl / Tauri) — "
            "tr* → tr, else en"
        )
    if not _TR_STAR_PICK.search(resolver):
        fail("#278: detectLocale must still map OS locale tr* → tr")
    if not _EN_DEFAULT_PICK.search(resolver):
        fail("#278: detectLocale must still default every non-tr OS locale to en")
    third: list[str] = []
    locale_dir = crate / "web" / "lib" / "locales"
    if locale_dir.is_dir():
        for p in sorted(locale_dir.iterdir()):
            if not p.is_file() or p.name.endswith(".d.ts"):
                continue
            if p.suffix not in {".ts", ".json", ".toml"}:
                continue
            stem = p.stem.lower()
            if stem in {"en", "tr", "index"}:
                continue
            third.append(str(p.relative_to(crate)))
    for p in _web_pack_candidates(crate):
        lang = _stem_chrome_lang(p)
        if lang and lang not in {"en", "tr"}:
            rel = str(p.relative_to(crate))
            if rel not in third:
                third.append(rel)
        elif _THIRD_PACK_STEM.search(p.stem):
            rel = str(p.relative_to(crate))
            if rel not in third:
                third.append(rel)
    if third:
        fail(
            "#278: no third locale pack — en + tr only. Found: " + ", ".join(third)
        )
    fetch_hits: list[str] = []
    for label, src in (
        ("i18n.ts", i18n),
        ("en pack", en_text),
        ("tr pack", tr_text),
        ("ReviewPane", panes["ReviewPane.svelte"]),
        ("ImportPane", panes["ImportPane.svelte"]),
        ("DoctorPane", panes["DoctorPane.svelte"]),
    ):
        surface = _without_comments(src)
        if _FETCH_CALL.search(surface) and (
            label in {"i18n.ts", "en pack", "tr pack"} or _LOCALE_FETCH.search(surface)
        ):
            fetch_hits.append(label)
    if _LOCALE_FETCH.search(cleaned):
        fetch_hits.append("web logic")
    if fetch_hits:
        fail(
            "#278: no fetch( of locale files — chrome packs are bundled. Found in: "
            + ", ".join(dict.fromkeys(fetch_hits))
        )

    # 5) Keep #131 Arşiv aç / Doktor.
    if "Arşiv aç" not in tr_text:
        fail('#278: keep #131 “Arşiv aç” in the tr pack')
    if "Doktor" not in tr_text:
        fail('#278: keep #131 “Doktor” in the tr pack')

    # Leftover Doctor backup sentences (remaining chrome, after the listed panes).
    doctor = panes["DoctorPane.svelte"]
    backup_left = [p for p in _PANE_BACKUP_LEFTOVER if p in doctor]
    if backup_left:
        fail(
            "#278: leftover Doctor backup chrome must use t() — still hardcoded: "
            + ", ".join(backup_left)
        )

    # 6) Docs: Review / Import / Doctor chrome follows OS language; bodies stay imported.
    docs = root / "docs" / "user" / "app.md"
    if not docs.is_file():
        fail(
            "#278: docs/user/app.md required — Review / Import / Doctor chrome "
            "follows OS language (en/tr); bodies stay as imported"
        )
    dtxt = docs.read_text()
    if not _DOCS_PANE_CHROME_LOCALE.search(dtxt):
        fail(
            "#278: docs/user/app.md must say Review / Import / Doctor chrome "
            "follows OS language (en/tr)"
        )
    if not _DOCS_PANE_BODIES_STAY.search(dtxt):
        fail(
            "#278: docs/user/app.md must say message bodies stay as imported"
        )
