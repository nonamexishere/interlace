"""Helpers extracted from contrast.py (contrast_lib)."""
from __future__ import annotations

from __future__ import annotations
import re
from pathlib import Path
from common import fail, repo_root
from tauri_gate.scan import (
    _ancestor_tags,
    _APPEARANCE_FETCH,
    _APPEARANCE_MENU_LABEL,
    _APPEARANCE_SCRIM_NAMES,
    _chrome_en_text,
    _contrast_dark_blob,
    _CONTRAST_SEARCH_MARK_NAMES,
    _css_brace_body,
    _css_var,
    _css_without_comments,
    _HUE_YELLOW,
    _markup_open_tag,
    _open_tag_before,
    _product_svelte,
    _search_pane_blob,
    _STATUS_CONFETTI,
    _STATUS_GRADIENT,
    _STATUS_WARNING_NAMES,
    _web_logic,
    _without_comments,
    CSP,
)
from tauri_gate.a11y_lib import (
    _A11Y_WCAG_CERT,
    _has_focus_visible_ring2,
)
from tauri_gate.design_lib import (
    _SHADCN_TOKEN_DEFS,
    _SHADCN_TOKEN_USES,
)
from tauri_gate.import_boot_guards import (
    _contrast_light_blob,
    _hue_findings,
)
from tauri_gate.status_toasts_chrome import (
    _APPEARANCE_DOCS_ARCHIVAL,
    _APPEARANCE_DOCS_NO_THEME,
    _APPEARANCE_THEME_UI,
    _CONTRAST_COLOR_SCHEME,
    _CONTRAST_DOCS_SYSTEM,
    _HUE_AMBER,
    _THEME_CDN,
    _contrast_surface_tag,
    _hsl_tuple,
    _hue_surface,
    _status_hook_blob,
)
from tauri_gate.status_toasts_toast import _appearance_class_names

_CONTRAST_SEARCH_MARK_VAR = re.compile(
    r"var\(\s*--(?:color-)?search-mark\s*\)",
    re.I,
)
_CONTRAST_MARK_FOREGROUND = re.compile(
    r"color\s*:\s*var\(\s*--(?:color-)?foreground\s*\)",
    re.I,
)
_CONTRAST_TOKEN_CLASS = re.compile(
    r"(?<![\w-])(?:text-muted-foreground|bg-muted|bg-background|"
    r"text-foreground|border-border|"
    r"bg-warning|text-warning|text-warning-foreground|border-warning|"
    r"bg-success|text-success|text-success-foreground|border-success|"
    r"status-warning|status-success)(?![\w-])"
)
_CONTRAST_THEME_PICKER = re.compile(
    r"("
    r"\bdata-theme\b"
    r"|theme-picker"
    r"|Theme menu"
    r"|Appearance menu"
    r"|high-contrast"
    r"|highContrast"
    r")",
    re.I,
)
_CONTRAST_DOCS_NO_RELOAD = re.compile(
    r"("
    r"without (?:a |an )?(?:reload|restart|relaunch)"
    r"|no reload"
    r"|does not (?:require|need) (?:a )?(?:reload|restart|relaunch)"
    r"|updates?(?: the (?:app|chrome|window))? without (?:a )?(?:reload|restart)"
    r")",
    re.I,
)
_CONTRAST_DOCS_READABLE = re.compile(
    r"("
    r"readable.{0,80}(?:on both|in both|light and dark|both (?:light|appearances|modes))"
    r"|(?:on both|light and dark|both (?:appearances|modes)).{0,80}readable"
    r"|preview.{0,80}readable"
    r")",
    re.I | re.S,
)
_CONTRAST_DOCS_MARKS = re.compile(
    r"("
    r"(?:search[- ]?)?marks?.{0,100}"
    r"(?:still work|on both|light and dark|both (?:appearances|modes)|stay yellow|yellow-enough)"
    r"|(?:yellow|highlighted).{0,80}mark.{0,80}"
    r"(?:both|light and dark|still work|without.{0,20}reload)"
    r")",
    re.I | re.S,
)


def _search_mark_rule_bodies(css: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"\.search-mark\b[^{]*\{", css):
        body = _css_brace_body(css, css.find("{", m.start()))
        if body:
            out.append(body)
    return out


def _contrast_tag_ok(tag: str) -> bool:
    if not tag:
        return False
    surface = _hue_surface(tag)
    if _HUE_AMBER.search(surface) or _HUE_YELLOW.search(surface):
        return False
    return bool(_CONTRAST_TOKEN_CLASS.search(tag))
_STATUS_CELEBRATION = re.compile(
    r"("
    r"\bcelebrat(?:e|ion|ing|ory)\b"
    r"|\bcongratulations\b"
    r"|\bhooray\b"
    r"|\bwoo+hoo\b"
    r"|🎉"
    r")",
    re.I,
)
_APPEARANCE_SCRIM_VAR = re.compile(
    r"var\(\s*--(?:overlay|scrim|lightbox-scrim)\s*\)",
    re.I,
)
_APPEARANCE_THEME_HTTP = re.compile(
    r"("
    r"(?:theme|appearance|stylesheet)[^;\n]{0,100}https://"
    r"|https://[^;\n]{0,100}(?:theme|appearance|stylesheet)"
    r"|@import\s+(?:url\s*\(\s*)?['\"]https?://"
    r")",
    re.I,
)
_APPEARANCE_BLACK_WASH = re.compile(
    r"(?<![\w-])(?:bg-)?black/(?:50|70|80)(?![\w-])"
)
_APPEARANCE_DOCS_MATCH = re.compile(
    r"("
    r"(?:lightbox|dialogs?).{0,120}(?:lightbox|dialogs?).{0,80}"
    r"(?:match|same (?:tokens?|variables?)|follow)"
    r"|(?:lightbox|dialogs?).{0,80}"
    r"(?:match|same (?:tokens?|variables?)).{0,80}"
    r"(?:lightbox|dialogs?)"
    r")",
    re.I | re.S,
)


def _appearance_tag_uses_scrim(tag: str, css: str) -> bool:
    if _APPEARANCE_SCRIM_VAR.search(tag):
        return True
    for cls in _appearance_class_names(tag):
        for m in re.finditer(rf"\.{re.escape(cls)}\b[^{{]*\{{", css):
            body = _css_brace_body(css, css.find("{", m.start()))
            if body and _APPEARANCE_SCRIM_VAR.search(body):
                return True
    return False


def _photo_lightbox_rule_bodies(css: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"\.photo-lightbox\b[^{]*\{", css):
        body = _css_brace_body(css, css.find("{", m.start()))
        if body:
            out.append(body)
    return out


def _appearance_overlay_tag(dialog_src: str) -> str:
    m = re.search(r"Dialog(?:Primitive)?\.Overlay\b", dialog_src)
    if not m:
        return ""
    return _markup_open_tag(dialog_src, dialog_src.rfind("<", 0, m.start() + 1))
_STATUS_WARNING_FG_NAMES = ("--warning-foreground", "--color-warning-foreground")
_STATUS_SUCCESS_NAMES = ("--success", "--color-success")
_STATUS_SUCCESS_FG_NAMES = ("--success-foreground", "--color-success-foreground")
_STATUS_WARNING_USE = re.compile(
    r"("
    r"(?<![\w-])(?:bg-warning|text-warning|text-warning-foreground|"
    r"border-warning|status-warning)(?![\w-])"
    r"|var\(\s*--(?:color-)?warning(?:-foreground)?\s*\)"
    r")"
)
_STATUS_SUCCESS_USE = re.compile(
    r"("
    r"(?<![\w-])(?:bg-success|text-success|text-success-foreground|"
    r"border-success|status-success)(?![\w-])"
    r"|var\(\s*--(?:color-)?success(?:-foreground)?\s*\)"
    r")"
)
_STATUS_MUTED_USE = re.compile(
    r"(?<![\w-])(?:text-muted-foreground|bg-muted|bg-background|"
    r"text-foreground|border-border)(?![\w-])"
)
_STATUS_RAW_HUE = re.compile(r"(?<![\w-])(?:amber|yellow|emerald|green)-\d+")
_STATUS_AUDIO_CTOR = re.compile(r"\bAudio\s*\(")
_STATUS_SVELTE_TRANSITION = re.compile(r"\b(?:transition|in|out)\s*:\s*([A-Za-z_]\w*)")
_STATUS_DOCS_WARNING = re.compile(
    r"("
    r"warning token"
    r"|--(?:color-)?warning"
    r"|(?:cloud|doctor).{0,120}warning token"
    r"|warnings?.{0,80}warning token"
    r")",
    re.I | re.S,
)
_STATUS_DOCS_QUIET_DONE = re.compile(
    r"("
    r"import done.{0,100}(?:quiet|muted|success)"
    r"|(?:quiet|muted|success).{0,80}import done"
    r"|import (?:done|success).{0,80}(?:quiet|muted|success token)"
    r"|quiet import done"
    r")",
    re.I | re.S,
)
_STATUS_TOAST_FADE_180 = re.compile(
    r"transition\s*:\s*fade\s*=\s*\{\{?\s*duration\s*:\s*180\s*\}"
)


def _status_selector_bodies(css: str, hook: str) -> list[str]:
    """Rule bodies whose selector mentions a data-* hook or a .class."""
    if hook.startswith("data-"):
        sel = rf"\[{re.escape(hook)}\]"
    else:
        sel = rf"\.{re.escape(hook)}\b"
    out: list[str] = []
    for m in re.finditer(rf"{sel}[^{{]*\{{", css):
        body = _css_brace_body(css, css.find("{", m.start()))
        if body:
            out.append(body)
    return out


def _status_surface_uses(
    blob: str,
    css: str,
    use_rx: re.Pattern[str],
    names: tuple[str, ...],
    hooks: tuple[str, ...] = (),
) -> bool:
    if use_rx.search(blob):
        return True
    for hook in hooks:
        for body in _status_selector_bodies(css, hook):
            if use_rx.search(body) or _css_var(body, names):
                return True
    for cls in _appearance_class_names(blob):
        if use_rx.search(cls):
            return True
        for body in _status_selector_bodies(css, cls):
            if use_rx.search(body) or _css_var(body, names):
                return True
    return False


def _status_doctor_box(src: str) -> str:
    """Non-partial doctor issues card (App 'Doctor found' / DoctorPane list)."""
    for needle in ("Doctor found issues", "Doctor found", "{#each issues"):
        at = src.find(needle)
        if at < 0:
            continue
        for tag in _ancestor_tags(src, at, limit=8):
            if "data-partial" in tag:
                continue
            if (
                _CONTRAST_TOKEN_CLASS.search(tag)
                or _STATUS_WARNING_USE.search(tag)
                or re.search(r"\b(?:rounded-md|border|bg-)\b", tag)
            ):
                return tag
    return ""


def _status_require_pair(
    light_blob: str,
    dark_blob: str,
    names: tuple[str, ...],
    fg_names: tuple[str, ...],
    *,
    label: str,
    hue_lo: float,
    hue_hi: float,
) -> None:
    pretty = " / ".join(names)
    pretty_fg = " / ".join(fg_names)
    light = _css_var(light_blob, names)
    if not light:
        fail(
            f"#219: {pretty} required in light (@theme / non-dark :root)"
        )
    dark = _css_var(dark_blob, names)
    if not dark:
        fail(
            f"#219: {pretty} required inside "
            "@media (prefers-color-scheme: dark)"
        )
    light_fg = _css_var(light_blob, fg_names)
    if not light_fg:
        fail(
            f"#219: {pretty_fg} required in light (@theme / non-dark :root)"
        )
    dark_fg = _css_var(dark_blob, fg_names)
    if not dark_fg:
        fail(
            f"#219: {pretty_fg} required inside "
            "@media (prefers-color-scheme: dark)"
        )
    for side, val in (
        ("light", light),
        ("dark", dark),
        ("light foreground", light_fg),
        ("dark foreground", dark_fg),
    ):
        if not _hsl_tuple(val):
            fail(f"#219: {label} tokens must be HSL ({side})")
    light_hsl = _hsl_tuple(light)
    dark_hsl = _hsl_tuple(dark)
    if light_hsl is None or dark_hsl is None:
        fail(f"#219: {label} tokens must be HSL (hue {hue_lo:g}–{hue_hi:g})")
    if not (hue_lo <= light_hsl[0] <= hue_hi):
        fail(
            f"#219: light {pretty} hue must be {hue_lo:g}–{hue_hi:g}; "
            f"found H={light_hsl[0]:g}"
        )
    if not (hue_lo <= dark_hsl[0] <= hue_hi):
        fail(
            f"#219: dark {pretty} hue must be {hue_lo:g}–{hue_hi:g}; "
            f"found H={dark_hsl[0]:g}"
        )

__all__ = [
    "_CONTRAST_SEARCH_MARK_VAR",
    "_CONTRAST_MARK_FOREGROUND",
    "_CONTRAST_TOKEN_CLASS",
    "_CONTRAST_THEME_PICKER",
    "_CONTRAST_DOCS_NO_RELOAD",
    "_CONTRAST_DOCS_READABLE",
    "_CONTRAST_DOCS_MARKS",
    "_search_mark_rule_bodies",
    "_contrast_tag_ok",
    "_STATUS_CELEBRATION",
    "_APPEARANCE_SCRIM_VAR",
    "_APPEARANCE_THEME_HTTP",
    "_APPEARANCE_BLACK_WASH",
    "_APPEARANCE_DOCS_MATCH",
    "_appearance_tag_uses_scrim",
    "_photo_lightbox_rule_bodies",
    "_appearance_overlay_tag",
    "_STATUS_WARNING_FG_NAMES",
    "_STATUS_SUCCESS_NAMES",
    "_STATUS_SUCCESS_FG_NAMES",
    "_STATUS_WARNING_USE",
    "_STATUS_SUCCESS_USE",
    "_STATUS_MUTED_USE",
    "_STATUS_RAW_HUE",
    "_STATUS_AUDIO_CTOR",
    "_STATUS_SVELTE_TRANSITION",
    "_STATUS_DOCS_WARNING",
    "_STATUS_DOCS_QUIET_DONE",
    "_STATUS_TOAST_FADE_180",
    "_status_selector_bodies",
    "_status_surface_uses",
    "_status_doctor_box",
    "_status_require_pair",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_ancestor_tags",
    "_APPEARANCE_FETCH",
    "_APPEARANCE_MENU_LABEL",
    "_APPEARANCE_SCRIM_NAMES",
    "_chrome_en_text",
    "_contrast_dark_blob",
    "_CONTRAST_SEARCH_MARK_NAMES",
    "_css_var",
    "_css_without_comments",
    "_markup_open_tag",
    "_open_tag_before",
    "_product_svelte",
    "_search_pane_blob",
    "_STATUS_CONFETTI",
    "_STATUS_GRADIENT",
    "_STATUS_WARNING_NAMES",
    "_web_logic",
    "_without_comments",
    "CSP",
    "_A11Y_WCAG_CERT",
    "_has_focus_visible_ring2",
    "_SHADCN_TOKEN_DEFS",
    "_SHADCN_TOKEN_USES",
    "_contrast_light_blob",
    "_hue_findings",
    "_APPEARANCE_DOCS_ARCHIVAL",
    "_APPEARANCE_DOCS_NO_THEME",
    "_APPEARANCE_THEME_UI",
    "_CONTRAST_COLOR_SCHEME",
    "_CONTRAST_DOCS_SYSTEM",
    "_THEME_CDN",
    "_contrast_surface_tag",
    "_hsl_tuple",
    "_hue_surface",
    "_status_hook_blob",
    "annotations",
    "_css_brace_body",
    "_HUE_YELLOW",
    "_HUE_AMBER",
    "_appearance_class_names",
]
