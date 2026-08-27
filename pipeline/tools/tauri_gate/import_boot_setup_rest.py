"""Continuation of import_boot_setup."""
from __future__ import annotations

from __future__ import annotations

from __future__ import annotations

import re
import html
from pathlib import Path

from common import fail, repo_root

from tauri_gate.scan import (
    _PANE_RESULT_WRITES,
    _PEOPLE_GEN_COUNTER,
    _SPIN_ANIM,
    _first_substr_pos,
    _CHROME_PACK_NS,
    _CONTRAST_DARK_MEDIA,
    _HUE_YELLOW,
    _LS_BRACKET,
    _SANDBOX_137,
    _SPLASH_VIDEO,
    _VOID_HTML,
    _chrome_en_text,
    _css_at_bodies,
    _css_brace_body,
    _expand_fn_calls,
    _function_body,
    _js_next,
    _match_closer,
    _svelte_markup,
    _ts_fn_body,
    _ts_function_body,
    _web_logic,
    _web_sources,
)
from tauri_gate.boot_helpers import (
    _BOOT_IF, _CONTRAST_AT_THEME, _CONTRAST_ROOT, _HUE_BLACK80,
    _HUE_HEX_CSS, _HUE_HEX_TW, _LS_CALL, _SPINNER_BORDER, _SPINNER_RING,
    _empty_state_local_names, _eq_stmt_rhs, _ident_assigned_from_chrome,
    _owned_import_path_rx,
)
from tauri_gate.import_boot_guards import (
    _has_css_spinner,
    _svelte_open_tag_at,
)


from tauri_gate.status_toasts_chrome import (
    _CDN_HINT,
    _HUE_AMBER,
    _NET_IMG,
    _SERVER_PROGRESS,
    _SPINNER_NAME,
    _assignment_gen_guarded,
    _chrome_helper_names,
    _hue_surface,
)
from tauri_gate.import_boot_setup import (
    _element_block_at,
    _SETUP_BRANCH_OPEN,
    _SETUP_OWNER_FIELDS,
    _SETUP_SKIP_TAGS,
    _SETUP_DISCLOSURE_TAG,
    _SETUP_DISCLOSURE_IF,
)
_SETUP_HIDDEN_ATTR = re.compile(
    r"("
    r"\bhidden\s*="
    r"|class:hidden\b"
    r"|aria-hidden\b"
    r"|(?<=\s)hidden(?=[\s/>])"
    r")"
)
_SETUP_CAROUSEL = re.compile(r"\b(?:carousel|swiper|onboarding)\b", re.I)
_SETUP_ACCOUNT_ACTION = re.compile(
    r"\b(?:sign[\s-]*in|sign[\s-]*up|log[\s-]*in|create account|oauth)\b",
    re.I,
)
_SETUP_SAMPLE_CLOUD = re.compile(
    r"("
    r"\b(?:sample|demo|cloud)\s+archive\b"
    r"|try a sample"
    r"|sample cloud"
    r")",
    re.I,
)
_SETUP_URL_FIELD = re.compile(
    r"<input\b[^>]*\btype\s*=\s*[\"']url[\"']|bind:value=\{[^}]*archiveUrl",
    re.I,
)
_SETUP_REQUIRE_OWNER = re.compile(
    r"("
    r"if\s*\(\s*!\s*(?:name|emails|phones)\b"
    r"|(?:name|emails|phones)\s+is required"
    r"|err\s*=\s*[\"'][^\"']*\b(?:name|emails?|phones?)\b[^\"']*required"
    r")",
    re.I,
)
_SETUP_DOC_ONE_SCREEN = re.compile(
    r"("
    r"first[- ]run.{0,80}one (?:calm )?screen"
    r"|one (?:calm )?screen.{0,80}first[- ](?:run|open)"
    r"|first[- ](?:run|open) is one"
    r")",
    re.I | re.S,
)
_SETUP_DOC_OPTIONAL = re.compile(
    r"("
    r"optional.{0,80}(?:owner|name|emails?|phones?).{0,80}"
    r"(?:not required|later|disclosure|not .{0,24}up front|not .{0,24}first)"
    r"|(?:owner )?(?:name|emails?|phones?).{0,60}"
    r"(?:not required|optional).{0,40}(?:first|up front|setup)"
    r"|optional owner.{0,40}(?:not required|disclosure|later|inspector)"
    r")",
    re.I | re.S,
)


def _svelte_closed_block_at(src: str, start: int) -> str:
    """{#if}/{#each}/{#await}/{#key} starting at start, through its close."""
    if start < 0 or start >= len(src) or not src.startswith("{#", start):
        return ""
    rest = src[start:]
    depth = 1
    i = 2
    while i < len(rest):
        if rest.startswith("{#if", i) or rest.startswith("{#each", i) or rest.startswith(
            "{#await", i
        ) or rest.startswith("{#key", i):
            depth += 1
            i += 3
            continue
        if rest.startswith("{/if}", i) or rest.startswith("{/each}", i) or rest.startswith(
            "{/await}", i
        ) or rest.startswith("{/key}", i):
            depth -= 1
            if depth == 0:
                close = 5 if rest.startswith("{/if}", i) else 7
                if rest.startswith("{/await}", i) or rest.startswith("{/key}", i):
                    close = 8 if rest.startswith("{/await}", i) else 6
                return rest[: i + close]
            i += 3
            continue
        i += 1
    return rest


def _setup_branch(app: str) -> str:
    """Markup of the setup / first-run branch ({:else if setup} or {#if setup})."""
    markup = _svelte_markup(app)
    m = _SETUP_BRANCH_OPEN.search(markup)
    src = markup
    if not m:
        return ""
    rest = src[m.end() :]
    depth = 1
    i = 0
    while i < len(rest):
        if rest.startswith("{#if", i) or rest.startswith("{#each", i) or rest.startswith(
            "{#await", i
        ) or rest.startswith("{#key", i):
            depth += 1
            i += 3
            continue
        if rest.startswith("{/if}", i) or rest.startswith("{/each}", i) or rest.startswith(
            "{/await}", i
        ) or rest.startswith("{/key}", i):
            depth -= 1
            if depth == 0:
                return rest[:i]
            i += 3
            continue
        if depth == 1 and (
            rest.startswith("{:else", i)
            or rest.startswith("{:then", i)
            or rest.startswith("{:catch", i)
        ):
            return rest[:i]
        i += 1
    return rest


def _setup_mounted_extra(crate: Path, setup: str) -> str:
    """Svelte files the setup branch actually mounts (FirstRun / SetupScreen)."""
    web = crate / "web"
    if not web.is_dir() or not setup.strip():
        return ""
    extra: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(r"<([A-Z][A-Za-z0-9]*)\b", setup):
        name = m.group(1)
        if name in _SETUP_SKIP_TAGS or name in seen:
            continue
        seen.add(name)
        for p in sorted(web.rglob(f"{name}.svelte")):
            if "node_modules" in p.parts:
                continue
            extra.append(p.read_text())
    return "\n".join(extra)


def _strip_setup_disclosures(markup: str) -> str:
    """Primary wall: drop <details> / disclosure {#if} / hidden wrappers."""
    text = markup
    changed = True
    while changed:
        changed = False
        m = _SETUP_DISCLOSURE_TAG.search(text)
        if m:
            block = _element_block_at(text, m.start())
            if block:
                text = text[: m.start()] + text[m.start() + len(block) :]
                changed = True
                continue
        m = _SETUP_DISCLOSURE_IF.search(text)
        if m:
            block = _svelte_closed_block_at(text, m.start())
            if block:
                text = text[: m.start()] + text[m.start() + len(block) :]
                changed = True
                continue
        for mm in re.finditer(r"<([A-Za-z][\w:.-]*)\b[^>]*>", text):
            tag = mm.group(0)
            if not _SETUP_HIDDEN_ATTR.search(tag):
                continue
            block = _element_block_at(text, mm.start())
            if block:
                text = text[: mm.start()] + text[mm.start() + len(block) :]
                changed = True
                break
    return text


def _setup_has_field(markup: str, field: str) -> bool:
    if re.search(rf"""\bid\s*=\s*["']{re.escape(field)}["']""", markup):
        return True
    if re.search(rf"""\bfor\s*=\s*["']{re.escape(field)}["']""", markup):
        return True
    if re.search(rf"bind:value\s*=\s*\{{\s*{re.escape(field)}\s*\}}", markup):
        return True
    return False


def _setup_visible_owner_fields(wall: str) -> list[str]:
    found: list[str] = []
    labels = {
        "name": re.compile(r"Your name|>\s*Name\s*<|Owner name", re.I),
        "emails": re.compile(r">\s*Emails?\b|owner emails", re.I),
        "phones": re.compile(r">\s*Phones?\b|owner phones", re.I),
    }
    for field in _SETUP_OWNER_FIELDS:
        if _setup_has_field(wall, field) or labels[field].search(wall):
            found.append(field)
    return found


def _setup_fn(app: str, extra: str, name: str) -> str:
    blob = app + "\n" + extra
    body = (
        _ts_function_body(blob, name)
        or _function_body(blob, name)
        or _ts_fn_body(blob, name)
    )
    if not body:
        return ""
    return body + "\n" + _expand_fn_calls(blob, body)

__all__ = [
    "_boot_opening_block",
    "_element_block_at",
    "_try_catch_blocks",
    "_VIEWPORT_FILL",
    "_CENTER_AXIS",
    "_FLEX_OR_GRID",
    "_LIGHT_DARK",
    "_is_viewport_centered",
    "_plain_corner_loading",
    "_SETUP_BRANCH_OPEN",
    "_SETUP_OWNER_FIELDS",
    "_SETUP_SKIP_TAGS",
    "_SETUP_DISCLOSURE_TAG",
    "_SETUP_DISCLOSURE_IF",
    "_SETUP_HIDDEN_ATTR",
    "_SETUP_CAROUSEL",
    "_SETUP_ACCOUNT_ACTION",
    "_SETUP_SAMPLE_CLOUD",
    "_SETUP_URL_FIELD",
    "_SETUP_REQUIRE_OWNER",
    "_SETUP_DOC_ONE_SCREEN",
    "_SETUP_DOC_OPTIONAL",
    "_svelte_closed_block_at",
    "_setup_branch",
    "_setup_mounted_extra",
    "_strip_setup_disclosures",
    "_setup_has_field",
    "_setup_visible_owner_fields",
    "_setup_fn",
    "annotations",
    "re",
    "html",
    "Path",
    "fail",
    "repo_root",
    "_PANE_RESULT_WRITES",
    "_PEOPLE_GEN_COUNTER",
    "_SPIN_ANIM",
    "_first_substr_pos",
    "_CHROME_PACK_NS",
    "_CONTRAST_DARK_MEDIA",
    "_HUE_YELLOW",
    "_LS_BRACKET",
    "_SANDBOX_137",
    "_SPLASH_VIDEO",
    "_VOID_HTML",
    "_chrome_en_text",
    "_css_at_bodies",
    "_css_brace_body",
    "_expand_fn_calls",
    "_function_body",
    "_js_next",
    "_match_closer",
    "_svelte_markup",
    "_ts_fn_body",
    "_ts_function_body",
    "_web_logic",
    "_web_sources",
    "_BOOT_IF",
    "_CONTRAST_AT_THEME",
    "_CONTRAST_ROOT",
    "_HUE_BLACK80",
    "_HUE_HEX_CSS",
    "_HUE_HEX_TW",
    "_LS_CALL",
    "_SPINNER_BORDER",
    "_SPINNER_RING",
    "_empty_state_local_names",
    "_eq_stmt_rhs",
    "_ident_assigned_from_chrome",
    "_owned_import_path_rx",
    "_has_css_spinner",
    "_svelte_open_tag_at",
    "_CDN_HINT",
    "_HUE_AMBER",
    "_NET_IMG",
    "_SERVER_PROGRESS",
    "_SPINNER_NAME",
    "_assignment_gen_guarded",
    "_chrome_helper_names",
    "_hue_surface",
]

__all__ = [
    "_SETUP_HIDDEN_ATTR",
    "_SETUP_CAROUSEL",
    "_SETUP_ACCOUNT_ACTION",
    "_SETUP_SAMPLE_CLOUD",
    "_SETUP_URL_FIELD",
    "_SETUP_REQUIRE_OWNER",
    "_SETUP_DOC_ONE_SCREEN",
    "_SETUP_DOC_OPTIONAL",
    "_svelte_closed_block_at",
    "_setup_branch",
    "_setup_mounted_extra",
    "_strip_setup_disclosures",
    "_setup_has_field",
    "_setup_visible_owner_fields",
    "_setup_fn",
    "__all__",
]
