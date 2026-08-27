"""Continuation of density_steps."""
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
from tauri_gate.density_steps import (
    _DENSITY_STATE_READ,
    _DENSITY_CLEAR_PENDING,
    _DENSITY_HEIGHT_WIPE,
    _DENSITY_CALL_SKIP,
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
    "re",
    "Path",
    "fail",
    "repo_root",
    "_APPEARANCE_MENU_LABEL",
    "_CONFIG_TOML",
    "_contrast_dark_blob",
    "_CONTRAST_SEARCH_MARK_NAMES",
    "_css_var",
    "_css_without_comments",
    "_LAST_PATH_API",
    "_LS_BRACKET",
    "_product_svelte",
    "_rust_fn_body",
    "_STATUS_WARNING_NAMES",
    "_TYPO_FONT_SANS",
    "_web_logic",
    "_without_comments",
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
    "_motion_js_blob",
    "_toml_keys_in_fn",
    "_windows_around",
    "annotations",
    "_ancestor_tags",
    "_css_brace_body",
    "_function_body",
    "_markup_open_tag",
    "_open_tag_before",
    "_ts_fn_body",
    "_ts_function_body",
    "_HEIGHT_CACHE",
    "_appearance_class_names",
    "_svelte_effect_args",
]

__all__ = [
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
    "__all__",
]
