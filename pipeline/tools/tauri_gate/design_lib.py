"""Helpers extracted from design.py (design_lib)."""
from __future__ import annotations

from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _BODY_T_CALL,
    _BUBBLE_ME_VARS,
    _BUBBLE_THEM_VARS,
    _css_var,
    _product_svelte,
    _search_pane_blob,
    _strip_html_comments,
    _svelte_markup,
    _timeline_block,
    _TYPO_FONT_SANS,
    _VOID_HTML,
    _web_logic,
    _without_comments,
)

from tauri_gate.a11y_lib import (
    _people_each_block,
    _people_list_a11y_surfaces,
)

from tauri_gate.import_boot_guards import (
    _PRE_WRAP,
    _hue_findings,
)

from tauri_gate.status_toasts_chrome import (
    _DOCS_TYPO_NO_REMOTE_FONT,
    _THEME_CDN,
    _TYPO_REMOTE_FONT,
    _chrome_helper_names,
    _hue_surface,
    _typo_docs_blob,
)
from tauri_gate.status_toasts_toast import _chrome_helper_on_body



_HEAVY_SHADOW = re.compile(r"(?<![\w-])shadow-(?:lg|xl|2xl)\b")
_GRADIENT = re.compile(
    r"("
    r"(?<![\w-])bg-gradient-"
    r"|(?<![\w-])(?:from|to|via)-(?:"
    r"zinc|slate|gray|neutral|stone|red|orange|amber|yellow|lime|green|"
    r"emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|"
    r"black|white|transparent|current|inherit"
    r")"
    r")",
)
_NEW_BRAND_VAR = re.compile(r"--(?:color-)?brand\b|--palette-")
_SQL_DDL = re.compile(r"""['\"][^'\"]*\b(?:ALTER|CREATE)\s+TABLE\b""", re.I)
_DOCS_DESIGN_TOKENS = re.compile(
    r"("
    r"(?:design tokens?|CSS variables?).{0,260}(?:chrome|colou?rs?|hues?)"
    r"|(?:chrome|colou?rs?|hues?).{0,260}(?:design tokens?|CSS variables?)"
    r")",
    re.I | re.S,
)
_DOCS_NOT_RAW_HUES = re.compile(
    r"("
    r"not raw (?:Tailwind )?hues?"
    r"|not (?:a |the )?raw Tailwind hues?"
    r"|not raw Tailwind"
    r"|CSS variables?, not raw"
    r"|design tokens?, not raw"
    r")",
    re.I,
)
_SHADCN_TOKEN_DEFS = (
    "--color-background",
    "--color-foreground",
    "--color-muted-foreground",
    "--color-border",
    "--color-destructive",
)
_SHADCN_TOKEN_USES = (
    "bg-background",
    "text-foreground",
    "text-muted-foreground",
    "border-border",
)


def _token_hits(crate: Path, files: list[Path], rx: re.Pattern[str]) -> list[str]:
    hits: list[str] = []
    for p in files:
        found = sorted({m.group(0) for m in rx.finditer(_hue_surface(p.read_text()))})
        if found:
            hits.append(f"{p.relative_to(crate)}: {', '.join(found)}")
    return hits


# #199 — typography: 14–15px bodies, 12–13px meta, system font, no remote font.
_TYPO_BODY_TW = re.compile(
    r"(?<![\w-])(text-sm|text-base|text-\[(?:14|15)(?:\.\d+)?px\])(?![\w-])"
)
_TYPO_META_TW = re.compile(
    r"(?<![\w-])(text-xs|text-\[(?:12|13)(?:\.\d+)?px\])(?![\w-])"
)
_TYPO_LEADING_NAMED = re.compile(
    r"(?<![\w-])(?:leading-normal|leading-relaxed)(?![\w-])"
)
_TYPO_LEADING_ARB = re.compile(r"(?<![\w-])leading-\[([^\]]+)\]")
_TYPO_LINE_HEIGHT = re.compile(r"line-height\s*:\s*([^;}]+)", re.I)
_TYPO_FONT_SIZE = re.compile(r"font-size\s*:\s*([^;}]+)", re.I)
_TYPO_GIANT = re.compile(
    r"(?<![\w-])text-(?:3xl|4xl|5xl|6xl|7xl|8xl|9xl)(?![\w-])"
)
_TYPO_MUTED = re.compile(
    r"("
    r"text-muted-foreground"
    r"|text-\[var\(--(?:color-)?muted-foreground\)\]"
    r"|var\(--(?:color-)?muted-foreground\)"
    r")"
)
_DOCS_TYPO_BODY = re.compile(
    r"("
    r"14\s*[–\-]\s*15\s*px"
    r"|(?:message )?bod(?:y|ies).{0,80}\bsizes?\b"
    r")",
    re.I,
)
_DOCS_TYPO_META = re.compile(
    r"("
    r"12\s*[–\-]\s*13\s*px"
    r"|\bmeta\b.{0,80}\bsizes?\b"
    r")",
    re.I,
)


def _typo_tag_class(attrs: str) -> str:
    m = re.search(r"\bclass\s*=\s*\"([^\"]*)\"", attrs)
    if m:
        return m.group(1)
    m = re.search(r"\bclass\s*=\s*'([^']*)'", attrs)
    if m:
        return m.group(1)
    m = re.search(r"\bclass\s*=\s*\{([^}]*)\}", attrs)
    if not m:
        return ""
    inner = m.group(1).strip()
    if len(inner) >= 2 and inner[0] == inner[-1] and inner[0] in "'\"`":
        return inner[1:-1]
    return "{" + inner + "}"


def _typo_tag_style(attrs: str) -> str:
    m = re.search(r"\bstyle\s*=\s*\"([^\"]*)\"", attrs)
    if m:
        return m.group(1)
    m = re.search(r"\bstyle\s*=\s*'([^']*)'", attrs)
    return m.group(1) if m else ""


def _typo_resolve_class(class_str: str, logic: str) -> str:
    parts = [class_str]
    for m in re.finditer(r"\{([A-Za-z_]\w*)\}", class_str):
        name = m.group(1)
        am = re.search(
            rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*[\"']([^\"']+)[\"']",
            logic,
        )
        if am:
            parts.append(am.group(1))
        am = re.search(
            rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*`([^`]+)`",
            logic,
        )
        if am:
            parts.append(am.group(1))
    return " ".join(parts)


def _typo_classes(class_str: str) -> list[str]:
    out: list[str] = []
    for tok in class_str.split():
        if tok and not tok.startswith("{") and not tok.startswith(":"):
            out.append(tok)
    return out


def _typo_css_blocks(css: str, classname: str) -> list[str]:
    return [
        m.group(1)
        for m in re.finditer(
            rf"\.{re.escape(classname)}\b[^{{]*\{{([^}}]*)\}}",
            css,
        )
    ]


def _typo_unitless_lh(raw: str) -> float | None:
    val = raw.strip().lower().rstrip(";")
    if val.endswith("%"):
        try:
            return float(val[:-1]) / 100.0
        except ValueError:
            return None
    if re.fullmatch(r"1\.\d+", val):
        return float(val)
    return None


def _typo_lh_in_range(raw: str) -> bool:
    n = _typo_unitless_lh(raw)
    return n is not None and 1.5 <= n <= 1.625


def _typo_px(raw: str) -> float | None:
    val = raw.strip().lower()
    m = re.fullmatch(r"([\d.]+)\s*px", val)
    if m:
        return float(m.group(1))
    m = re.fullmatch(r"([\d.]+)\s*rem", val)
    if m:
        return float(m.group(1)) * 16.0
    return None


def _typo_size_token(class_str: str, css: str, kind: str) -> str | None:
    rx = _TYPO_BODY_TW if kind == "body" else _TYPO_META_TW
    m = rx.search(class_str)
    if m:
        return m.group(1)
    lo, hi = (14.0, 15.0) if kind == "body" else (12.0, 13.0)
    for cls in _typo_classes(class_str):
        for block in _typo_css_blocks(css, cls):
            fm = _TYPO_FONT_SIZE.search(block)
            if not fm:
                continue
            px = _typo_px(fm.group(1).strip())
            if px is not None and lo <= px <= hi:
                return f".{cls}"
    return None


def _typo_theme_lh_ok(css: str, tw_token: str) -> bool:
    key = {"text-sm": "sm", "text-base": "base", "text-xs": "xs"}.get(tw_token)
    if not key:
        return False
    m = re.search(
        rf"--text-{re.escape(key)}--line-height\s*:\s*([^;]+);",
        css,
    )
    return bool(m) and _typo_lh_in_range(m.group(1))


def _typo_leading_ok(class_str: str, style: str, css: str) -> bool:
    if _TYPO_LEADING_NAMED.search(class_str):
        return True
    for m in _TYPO_LEADING_ARB.finditer(class_str):
        if _typo_lh_in_range(m.group(1)):
            return True
    if style:
        hm = _TYPO_LINE_HEIGHT.search(style)
        if hm and _typo_lh_in_range(hm.group(1)):
            return True
    tw = _TYPO_BODY_TW.search(class_str)
    if tw and _typo_theme_lh_ok(css, tw.group(1)):
        return True
    for cls in _typo_classes(class_str):
        for block in _typo_css_blocks(css, cls):
            hm = _TYPO_LINE_HEIGHT.search(block)
            if hm and _typo_lh_in_range(hm.group(1)):
                return True
    return False


def _typo_muted_ok(class_str: str, css: str) -> bool:
    if _TYPO_MUTED.search(class_str):
        return True
    for cls in _typo_classes(class_str):
        for block in _typo_css_blocks(css, cls):
            if _TYPO_MUTED.search(block) or re.search(
                r"color\s*:\s*var\(--(?:color-)?muted-foreground\)",
                block,
                re.I,
            ):
                return True
    return False


def _typo_prewrap_attrs(src: str, inner_rx: re.Pattern[str]) -> list[str]:
    found: list[str] = []
    for m in _PRE_WRAP.finditer(src):
        if inner_rx.search(m.group(3)):
            found.append(m.group(2))
    return found

from tauri_gate.design_lib_rest import (
    _ICON_EMOJI_GLYPH,
    _LUCIDE_DEFAULT,
    _LUCIDE_NAMED,
    _LUCIDE_BARE,
    _ICON_SIZE_16,
    _ICON_SIZE_20,
    _OTHER_ICON_PKG,
    _OTHER_ICON_IMPORT,
    _ICON_CDN,
    _EMPTY_MASCOT,
    _BRAND_LOGO_IMG,
    _DOCS_LUCIDE_CHROME,
    _DOCS_LUCIDE_NOT_EMOJI,
    _NAV_LABEL_KEYS,
    _lucide_surface,
    _lucide_bindings,
    _lucide_ids,
    _lucide_open_tags,
    _lucide_used,
    _lucide_attr_block,
    _lucide_files_with,
    __all__,
)

__all__ = [
    "_HEAVY_SHADOW",
    "_GRADIENT",
    "_NEW_BRAND_VAR",
    "_SQL_DDL",
    "_DOCS_DESIGN_TOKENS",
    "_DOCS_NOT_RAW_HUES",
    "_SHADCN_TOKEN_DEFS",
    "_SHADCN_TOKEN_USES",
    "_token_hits",
    "_TYPO_BODY_TW",
    "_TYPO_META_TW",
    "_TYPO_LEADING_NAMED",
    "_TYPO_LEADING_ARB",
    "_TYPO_LINE_HEIGHT",
    "_TYPO_FONT_SIZE",
    "_TYPO_GIANT",
    "_TYPO_MUTED",
    "_DOCS_TYPO_BODY",
    "_DOCS_TYPO_META",
    "_typo_tag_class",
    "_typo_tag_style",
    "_typo_resolve_class",
    "_typo_classes",
    "_typo_css_blocks",
    "_typo_unitless_lh",
    "_typo_lh_in_range",
    "_typo_px",
    "_typo_size_token",
    "_typo_theme_lh_ok",
    "_typo_leading_ok",
    "_typo_muted_ok",
    "_typo_prewrap_attrs",
    "_ICON_EMOJI_GLYPH",
    "_LUCIDE_DEFAULT",
    "_LUCIDE_NAMED",
    "_LUCIDE_BARE",
    "_ICON_SIZE_16",
    "_ICON_SIZE_20",
    "_OTHER_ICON_PKG",
    "_OTHER_ICON_IMPORT",
    "_ICON_CDN",
    "_EMPTY_MASCOT",
    "_BRAND_LOGO_IMG",
    "_DOCS_LUCIDE_CHROME",
    "_DOCS_LUCIDE_NOT_EMOJI",
    "_NAV_LABEL_KEYS",
    "_lucide_surface",
    "_lucide_bindings",
    "_lucide_ids",
    "_lucide_open_tags",
    "_lucide_used",
    "_lucide_attr_block",
    "_lucide_files_with",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_BODY_T_CALL",
    "_BUBBLE_ME_VARS",
    "_BUBBLE_THEM_VARS",
    "_css_var",
    "_product_svelte",
    "_search_pane_blob",
    "_strip_html_comments",
    "_svelte_markup",
    "_timeline_block",
    "_TYPO_FONT_SANS",
    "_VOID_HTML",
    "_web_logic",
    "_without_comments",
    "_people_each_block",
    "_people_list_a11y_surfaces",
    "_PRE_WRAP",
    "_hue_findings",
    "_DOCS_TYPO_NO_REMOTE_FONT",
    "_THEME_CDN",
    "_TYPO_REMOTE_FONT",
    "_chrome_helper_names",
    "_hue_surface",
    "_typo_docs_blob",
    "_chrome_helper_on_body",
]
