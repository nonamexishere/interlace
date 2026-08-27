"""Helpers extracted from density.py (density_chrome)."""
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
    _CHROME_FAMILIES,
    _CHROME_GENERIC_VARS,
    _CHROME_GENERIC_REF,
    _CHROME_VAR_DEF,
    _CHROME_VAR_USE,
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

__all__ = [
    "_DOCS_LEFTOVER_CHROME",
    "_DOCS_LEFTOVER_SURFACES",
    "_DOCS_LIGHT_READABLE",
    "_chrome_leftover_family",
    "_chrome_token_stem",
    "_chrome_light_defs",
    "_chrome_by_family",
    "_chrome_value_is_generic",
    "_chrome_hook_blob",
    "_chrome_preview_blob",
    "_chrome_attr_rule_bodies",
    "_chrome_class_rule_bodies",
    "_chrome_blob_uses_vars",
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
    "_CHROME_FAMILIES",
    "_CHROME_GENERIC_VARS",
    "_CHROME_GENERIC_REF",
    "_CHROME_VAR_DEF",
    "_CHROME_VAR_USE",
]
