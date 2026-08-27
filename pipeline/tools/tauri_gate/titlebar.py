"""Window title / custom titlebar chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.titlebar_lib import *


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
    app = _web_logic(crate)
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

from tauri_gate.titlebar_more import assert_custom_titlebar
