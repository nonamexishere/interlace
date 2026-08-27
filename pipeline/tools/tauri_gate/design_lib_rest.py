"""Continuation of design_lib."""
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


# #200 — Lucide chrome icons: play/pause, lightbox close, empty-state.
# Conservative emoji-as-icon ban on those surfaces only (not message bodies).
_ICON_EMOJI_GLYPH = re.compile(r"[▶❚✓✕✖❌✨]")
_LUCIDE_DEFAULT = re.compile(
    r"import\s+(\w+)\s+from\s+[\"']@lucide/svelte/icons/([\w-]+)[\"']"
)
_LUCIDE_NAMED = re.compile(
    r"import\s+\{([^}]+)\}\s+from\s+[\"']@lucide/svelte[\"']"
)
_LUCIDE_BARE = re.compile(
    r"import\s+(\w+)\s+from\s+[\"']@lucide/svelte[\"']"
)
_ICON_SIZE_16 = re.compile(
    r"("
    r"(?<![\w-])(?:size-4|w-4|h-4)(?![\w-])"
    r"|size\s*=\s*(?:\{\s*16\s*\}|[\"']16[\"'])"
    r"|(?:width|height)\s*=\s*(?:\{\s*16\s*\}|[\"']16(?:px)?[\"'])"
    r"|(?:width|height)\s*:\s*16px"
    r")"
)
_ICON_SIZE_20 = re.compile(
    r"("
    r"(?<![\w-])(?:size-5|w-5|h-5)(?![\w-])"
    r"|size\s*=\s*(?:\{\s*20\s*\}|[\"']20[\"'])"
    r"|(?:width|height)\s*=\s*(?:\{\s*20\s*\}|[\"']20(?:px)?[\"'])"
    r"|(?:width|height)\s*:\s*20px"
    r")"
)
_OTHER_ICON_PKG = re.compile(
    r"[\"']("
    r"react-icons(?:/[^\"']+)?"
    r"|@heroicons/[^\"']+"
    r"|heroicons"
    r"|@fortawesome/[^\"']+"
    r"|font-?awesome(?:/[^\"']+)?"
    r"|@tabler/[^\"']+"
    r"|@iconify(?:-[a-z]+)?/[^\"']+"
    r"|@iconify-json/[^\"']+"
    r"|iconify(?:-[a-z]+)?"
    r")[\"']",
    re.I,
)
_OTHER_ICON_IMPORT = re.compile(
    r"from\s+[\"']("
    r"react-icons"
    r"|@heroicons/"
    r"|heroicons"
    r"|@fortawesome/"
    r"|font-?awesome"
    r"|@tabler/"
    r"|@iconify"
    r"|iconify"
    r")",
    re.I,
)
_ICON_CDN = re.compile(
    r"("
    r"fonts\.googleapis"
    r"|cdn\."
    r"|unpkg(?:\.com)?"
    r"|jsdelivr"
    r"|api\.iconify"
    r"|iconify\.design"
    r")",
    re.I,
)
_EMPTY_MASCOT = re.compile(
    r"("
    r"\billustration\b"
    r"|\bmascot\b"
    r"|<svg\b"
    r"|<img\b"
    r")",
    re.I,
)
_BRAND_LOGO_IMG = re.compile(
    r"("
    r"<img\b[^>]*(?:whatsapp|gmail|gstatic|googleusercontent)[^>]*>"
    r"|src\s*=\s*[\"']https?://[^\"']*(?:whatsapp|gmail|gstatic)"
    r")",
    re.I,
)
_DOCS_LUCIDE_CHROME = re.compile(
    r"("
    r"lucide.{0,280}(?:play|pause|lightbox|empty)"
    r"|(?:play|pause|lightbox|empty|chrome icons?).{0,280}lucide"
    r")",
    re.I | re.S,
)
_DOCS_LUCIDE_NOT_EMOJI = re.compile(
    r"("
    r"not emoji(?:[- ]as[- ]icon)?(?: glyphs?)?"
    r"|not.{0,80}emoji glyphs?"
    r"|lucide.{0,80}not emoji"
    r"|chrome icons?.{0,80}not emoji"
    r"|not.{0,48}(?:▶|❚❚|text glyphs?)"
    r")",
    re.I,
)
_NAV_LABEL_KEYS = ("people", "search", "review", "import", "doctor")


def _lucide_surface(text: str) -> str:
    return _without_comments(_strip_html_comments(text))


def _lucide_bindings(src: str) -> list[tuple[str, str]]:
    """Local name + lucide icon id from `@lucide/svelte` imports."""
    out: list[tuple[str, str]] = []
    for m in _LUCIDE_DEFAULT.finditer(src):
        out.append((m.group(1), m.group(2).lower()))
    for m in _LUCIDE_NAMED.finditer(src):
        for part in m.group(1).split(","):
            part = part.strip()
            if not part:
                continue
            bits = re.split(r"\s+as\s+", part)
            export = bits[0].strip()
            local = bits[-1].strip()
            if export and local:
                out.append((local, export.lower()))
    for m in _LUCIDE_BARE.finditer(src):
        out.append((m.group(1), m.group(1).lower()))
    return out


def _lucide_ids(bindings: list[tuple[str, str]]) -> set[str]:
    return {path for _, path in bindings}


def _lucide_open_tags(block: str, names: set[str]) -> list[str]:
    if not names:
        return []
    alt = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    return re.findall(rf"<(?:{alt})\b([^>]*?)/?>", block, re.S)


def _lucide_used(block: str, names: set[str]) -> set[str]:
    return {n for n in names if re.search(rf"<{re.escape(n)}\b", block)}


def _lucide_attr_block(src: str, attr: str) -> str:
    m = re.search(
        rf"<([A-Za-z][\w:.-]*)\b([^>]*\b{re.escape(attr)}\b[^>]*)>",
        src,
        re.S,
    )
    if not m:
        return ""
    open_tag = m.group(0)
    name = m.group(1)
    if open_tag.rstrip().endswith("/>") or name.lower() in _VOID_HTML:
        return open_tag
    close = re.search(rf"</{re.escape(name)}\s*>", src[m.end() :], re.I)
    if not close:
        return src[m.start() : m.end() + 480]
    return src[m.start() : m.end() + close.end()]


def _lucide_files_with(crate: Path, needle: str) -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    for p in _product_svelte(crate):
        text = p.read_text()
        if needle in text:
            found.append((p, text))
    return found

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
    "_web_logic",
    "_people_each_block",
    "_people_list_a11y_surfaces",
    "_hue_findings",
    "_DOCS_TYPO_NO_REMOTE_FONT",
    "_THEME_CDN",
    "_TYPO_REMOTE_FONT",
    "_chrome_helper_names",
    "_chrome_helper_on_body",
    "_typo_docs_blob",
    "annotations",
    "_VOID_HTML",
    "_without_comments",
    "_PRE_WRAP",
    "_hue_surface",
]

__all__ = [
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
    "__all__",
]
