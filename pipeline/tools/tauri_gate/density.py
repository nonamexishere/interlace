"""Font-density / light-chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations
import re
from pathlib import Path
from common import fail, repo_root
from tauri_gate.scan import (
    _APPEARANCE_MENU_LABEL, _CONFIG_TOML, _CONTRAST_SEARCH_MARK_NAMES, _LAST_PATH_API,
    _LS_BRACKET, _STATUS_WARNING_NAMES, _TYPO_FONT_SANS, _ancestor_tags,
    _contrast_dark_blob, _css_brace_body, _css_var, _css_without_comments,
    _function_body, _markup_open_tag, _open_tag_before, _product_svelte,
    _rust_fn_body, _ts_fn_body, _ts_function_body, _without_comments,
)
from tauri_gate.import_boot import (
    _HEIGHT_CACHE, _contrast_light_blob, _hue_findings, _ls_pref_keys,
)
from tauri_gate.status_toasts import (
    _APPEARANCE_DOCS_ARCHIVAL, _APPEARANCE_DOCS_NO_THEME, _APPEARANCE_THEME_UI, _CONTRAST_COLOR_SCHEME,
    _CONTRAST_DOCS_SYSTEM, _DOCS_TYPO_NO_REMOTE_FONT, _MOTION_DURATION_ZERO, _MOTION_JS_REDUCE,
    _THEME_CDN, _TYPO_REMOTE_FONT, _appearance_class_names, _hsl_tuple,
    _hue_surface, _motion_js_blob, _svelte_effect_args, _toml_keys_in_fn,
    _windows_around,
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
