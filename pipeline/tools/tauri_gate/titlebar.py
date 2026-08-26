"""Window title / custom titlebar chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    CSP,
    _call_arg,
    _function_body,
    _matched_inner,
    _opening_tag,
    _strip_html_comments,
    _svelte_markup,
    _tag_name,
    _tauri_rust_blob,
    _template_stack,
    _web_logic,
    _web_sources,
    _without_comments,
)

from tauri_gate.locale import (
    _FILE_SUBMENU,
    _TAURI_MENU_API,
    _VIEW_SUBMENU,
)

from tauri_gate.status_toasts import (
    _claim_without_negation,
    _tag_inner,
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
