"""Helpers extracted from density.py (density_steps)."""
from __future__ import annotations

from __future__ import annotations

from __future__ import annotations
import re
from pathlib import Path
from common import fail, repo_root
from tauri_gate.scan import (
    _ancestor_tags,
    _APPEARANCE_MENU_LABEL,
    _CONFIG_TOML,
    _contrast_dark_blob,
    _CONTRAST_SEARCH_MARK_NAMES,
    _css_brace_body,
    _css_var,
    _css_without_comments,
    _function_body,
    _LAST_PATH_API,
    _LS_BRACKET,
    _markup_open_tag,
    _open_tag_before,
    _product_svelte,
    _rust_fn_body,
    _STATUS_WARNING_NAMES,
    _ts_fn_body,
    _ts_function_body,
    _TYPO_FONT_SANS,
    _web_logic,
    _without_comments,
)
from tauri_gate.import_boot_guards import (
    _HEIGHT_CACHE,
    _contrast_light_blob,
    _hue_findings,
    _ls_pref_keys,
)
from tauri_gate.status_toasts_chrome import (
    _APPEARANCE_DOCS_ARCHIVAL,
    _APPEARANCE_DOCS_NO_THEME,
    _APPEARANCE_THEME_UI,
    _CONTRAST_COLOR_SCHEME,
    _CONTRAST_DOCS_SYSTEM,
    _DOCS_TYPO_NO_REMOTE_FONT,
    _MOTION_DURATION_ZERO,
    _MOTION_JS_REDUCE,
    _THEME_CDN,
    _TYPO_REMOTE_FONT,
    _hsl_tuple,
    _hue_surface,
    _toml_keys_in_fn,
    _windows_around,
)
from tauri_gate.status_toasts_toast import (
    _appearance_class_names,
    _motion_js_blob,
    _svelte_effect_args,
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

from tauri_gate.density_steps_rest import (
    _density_fn_body,
    _density_expand_calls,
    _density_wipes_heights,
    _density_path_wipes,
    _density_persist_only_pref,
    _density_change_blobs,
    _CHROME_FAMILIES,
    _CHROME_FAMILY_EXAMPLES,
    _CHROME_GENERIC_VARS,
    _CHROME_GENERIC_REF,
    _CHROME_VAR_DEF,
    _CHROME_VAR_USE,
    _CHROME_DARK_BG,
    _CHROME_DARK_MARK,
    _CHROME_DARK_MARK_VAL,
    _CHROME_DARK_WARN,
    _CHROME_DARK_WARN_VAL,
    _CHROME_HOOKS,
    __all__,
)

__all__ = [
    "_DENSITY_HOOK",
    "_DENSITY_IDENT",
    "_DENSITY_STATE",
    "_DENSITY_VALUE",
    "_DENSITY_LABEL",
    "_DENSITY_STEP_COMFORTABLE",
    "_DENSITY_STEP_DEFAULT",
    "_DENSITY_STEP_COMPACT",
    "_DENSITY_CHROME",
    "_DENSITY_PALETTE_ITEM",
    "_DENSITY_APPLY",
    "_DENSITY_CSS_HOOK",
    "_DENSITY_SIZE_PROP",
    "_DENSITY_BODY_VAR",
    "_BUBBLE_DENSITY_CLASS",
    "_DENSITY_RELOAD",
    "_DENSITY_WORD",
    "_PER_BUBBLE_FONT",
    "_DENSITY_FONT_FACE_HTTP",
    "_DOCS_DENSITY_STEPS",
    "_DOCS_LOCAL_DENSITY",
    "_DOCS_DENSITY_BODIES",
    "_DOCS_DENSITY_NO_RELOAD",
    "_density_web_src",
    "_density_has_control",
    "_density_has_two_steps",
    "_density_key_ok",
    "_density_css_bumps_body",
    "_DENSITY_STATE_READ",
    "_DENSITY_CLEAR_PENDING",
    "_DENSITY_HEIGHT_WIPE",
    "_DENSITY_VIRTUALIZE_AFTER",
    "_DENSITY_CALL_SKIP",
    "_density_fn_body",
    "_density_expand_calls",
    "_density_wipes_heights",
    "_density_path_wipes",
    "_density_persist_only_pref",
    "_density_change_blobs",
    "_CHROME_FAMILIES",
    "_CHROME_FAMILY_EXAMPLES",
    "_CHROME_GENERIC_VARS",
    "_CHROME_GENERIC_REF",
    "_CHROME_VAR_DEF",
    "_CHROME_VAR_USE",
    "_CHROME_DARK_BG",
    "_CHROME_DARK_MARK",
    "_CHROME_DARK_MARK_VAL",
    "_CHROME_DARK_WARN",
    "_CHROME_DARK_WARN_VAL",
    "_CHROME_HOOKS",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_ancestor_tags",
    "_APPEARANCE_MENU_LABEL",
    "_CONFIG_TOML",
    "_contrast_dark_blob",
    "_CONTRAST_SEARCH_MARK_NAMES",
    "_css_brace_body",
    "_css_var",
    "_css_without_comments",
    "_function_body",
    "_LAST_PATH_API",
    "_LS_BRACKET",
    "_markup_open_tag",
    "_open_tag_before",
    "_product_svelte",
    "_rust_fn_body",
    "_STATUS_WARNING_NAMES",
    "_ts_fn_body",
    "_ts_function_body",
    "_TYPO_FONT_SANS",
    "_web_logic",
    "_without_comments",
    "_HEIGHT_CACHE",
    "_contrast_light_blob",
    "_hue_findings",
    "_ls_pref_keys",
    "_APPEARANCE_DOCS_ARCHIVAL",
    "_APPEARANCE_DOCS_NO_THEME",
    "_APPEARANCE_THEME_UI",
    "_CONTRAST_COLOR_SCHEME",
    "_CONTRAST_DOCS_SYSTEM",
    "_DOCS_TYPO_NO_REMOTE_FONT",
    "_MOTION_DURATION_ZERO",
    "_MOTION_JS_REDUCE",
    "_THEME_CDN",
    "_TYPO_REMOTE_FONT",
    "_hsl_tuple",
    "_hue_surface",
    "_toml_keys_in_fn",
    "_windows_around",
    "_appearance_class_names",
    "_motion_js_blob",
    "_svelte_effect_args",
]
