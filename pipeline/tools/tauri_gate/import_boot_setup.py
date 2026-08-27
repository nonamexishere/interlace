"""Helpers extracted from import_boot.py (import_boot_setup)."""
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


def _boot_opening_block(app: str) -> str:
    """Markup of the booting || opening branch (until {:else…} or {/if})."""
    m = _BOOT_IF.search(app)
    if not m:
        return ""
    rest = app[m.end() :]
    # Branch ends at the first sibling {:else / {:else if / {/if} at depth 0.
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
                return app[m.start() : m.end() + i]
            i += 3
            continue
        if depth == 1 and (
            rest.startswith("{:else", i) or rest.startswith("{:then", i) or rest.startswith(
                "{:catch", i
            )
        ):
            return app[m.start() : m.end() + i]
        i += 1
    return app[m.start() :]


def _element_block_at(src: str, start: int) -> str:
    """Element starting at src[start]=='<', including matched children."""
    if start < 0 or start >= len(src) or src[start] != "<":
        return ""
    open_tag = _svelte_open_tag_at(src, start)
    name_m = re.match(r"<([A-Za-z][\w:.-]*)", open_tag)
    if not name_m:
        return open_tag
    name = name_m.group(1)
    if open_tag.rstrip().endswith("/>") or name.lower() in _VOID_HTML:
        return open_tag
    depth = 1
    i = start + len(open_tag)
    n = len(src)
    name_l = name.lower()
    while i < n:
        nxt = src.find("<", i)
        if nxt < 0:
            return src[start:]
        close_m = re.match(r"</([A-Za-z][\w:.-]*)\s*>", src[nxt:])
        if close_m and close_m.group(1).lower() == name_l:
            depth -= 1
            if depth == 0:
                return src[start : nxt + close_m.end()]
            i = nxt + close_m.end()
            continue
        open_m = re.match(r"<([A-Za-z][\w:.-]*)\b", src[nxt:])
        if open_m and open_m.group(1).lower() == name_l:
            inner = _svelte_open_tag_at(src, nxt)
            if not inner.rstrip().endswith("/") and not inner.rstrip().endswith("/>"):
                if open_m.group(1).lower() not in _VOID_HTML:
                    depth += 1
            i = nxt + max(len(inner), 1)
            continue
        i = nxt + 1
    return src[start:]


def _try_catch_blocks(src: str) -> list[tuple[str, str]]:
    """(try_body, catch_body) pairs via brace matching."""
    out: list[tuple[str, str]] = []
    i = 0
    n = len(src)
    while i < n:
        m = re.search(r"\btry\s*\{", src[i:])
        if not m:
            break
        try_open = i + m.end() - 1
        try_close = _match_closer(src, try_open)
        if try_close < 0:
            break
        j = try_close + 1
        while j < n and src[j] in " \t\n\r":
            j += 1
        if not src.startswith("catch", j):
            i = try_close + 1
            continue
        j += 5
        while j < n and src[j] in " \t\n\r":
            j += 1
        if j < n and src[j] == "(":
            close_p = _match_closer(src, j)
            j = close_p + 1 if close_p >= 0 else j
            while j < n and src[j] in " \t\n\r":
                j += 1
        if j >= n or src[j] != "{":
            i = try_close + 1
            continue
        catch_close = _match_closer(src, j)
        if catch_close < 0:
            catch_body = src[j + 1 :]
            out.append((src[try_open + 1 : try_close], catch_body))
            break
        out.append((src[try_open + 1 : try_close], src[j + 1 : catch_close]))
        i = catch_close + 1
    return out



_VIEWPORT_FILL = re.compile(
    r"("
    r"min-h-(?:screen|dvh|svh|full)"
    r"|h-(?:screen|dvh|svh|full)"
    r"|min-height\s*:\s*100(?:vh|dvh|svh|%)"
    r"|height\s*:\s*100(?:vh|dvh|svh|%)"
    r"|(?:fixed|absolute)\s+inset-0"
    r"|inset\s*:\s*0"
    r")",
    re.I,
)
_CENTER_AXIS = re.compile(
    r"("
    r"items-center"
    r"|justify-center"
    r"|place-items-center"
    r"|place-content-center"
    r"|align-items\s*:\s*center"
    r"|justify-content\s*:\s*center"
    r"|place-items\s*:\s*center"
    r"|place-content\s*:\s*center"
    r")",
    re.I,
)
_FLEX_OR_GRID = re.compile(
    r"("
    r"\bflex\b"
    r"|\bgrid\b"
    r"|display\s*:\s*(?:flex|grid|inline-flex)"
    r")",
    re.I,
)
_LIGHT_DARK = re.compile(
    r"("
    r"\bdark:"
    r"|prefers-color-scheme"
    r"|--color-(?:background|foreground|muted)"
    r"|color-scheme\s*:"
    r")",
    re.I,
)


def _is_viewport_centered(blob: str) -> bool:
    """True when layout fills the viewport and centers content (not corner text)."""
    if not blob:
        return False
    if re.search(r"place-items-center|place-content-center", blob) and _VIEWPORT_FILL.search(
        blob
    ):
        return True
    return bool(
        _VIEWPORT_FILL.search(blob)
        and _CENTER_AXIS.search(blob)
        and _FLEX_OR_GRID.search(blob)
    )


def _plain_corner_loading(html: str) -> bool:
    """True when splash is only plain Loading text with no spinner chrome."""
    body = re.search(r"<body\b[^>]*>(.*)</body>", html, re.I | re.S)
    blob = body.group(1) if body else html
    # Strip scripts — they are not the visible splash.
    blob = re.sub(r"<script\b[^>]*>.*?</script>", "", blob, flags=re.I | re.S)
    if _has_css_spinner(html):
        return False
    if re.search(r"Loading Interlace", blob, re.I) and not _is_viewport_centered(html):
        return True
    # Bare #app text node, no spinner markup.
    if re.search(
        r"""id=["']app["'][^>]*>\s*Loading\b[^<]*\s*</""",
        blob,
        re.I,
    ) and not _has_css_spinner(html):
        return True
    return False


# #275 — first-run is one calm screen, not a four-field form wall.
_SETUP_BRANCH_OPEN = re.compile(
    r"\{:else\s+if\s+setup\b|\{#if\s+setup\b"
)
_SETUP_OWNER_FIELDS = ("name", "emails", "phones")
_SETUP_SKIP_TAGS = frozenset(
    {
        "Button",
        "Input",
        "Label",
        "Card",
        "Separator",
        "Badge",
        "ScrollArea",
        "Skeleton",
        "Toast",
        "Dialog",
        "ConfirmDialog",
        "EmptyState",
        "CommandPalette",
        "SearchPane",
        "ReviewPane",
        "ImportPane",
        "DoctorPane",
        "CasAttach",
        "LinkifyBody",
        "main",
        "div",
        "p",
        "h1",
        "h2",
        "h3",
        "span",
        "form",
        "section",
        "header",
        "footer",
    }
)
_SETUP_DISCLOSURE_TAG = re.compile(
    r"<(details|Disclosure|Collapsible|Accordion)(?:\.\w+)?\b",
    re.I,
)
_SETUP_DISCLOSURE_IF = re.compile(
    r"\{#if\s+([^}]*\b(?:showMore|moreOpen|ownerOpen|showOwner|"
    r"ownerFields|showDetails|advanced|optionalOwner|extraFields|"
    r"moreFields|ownerMore|disclose|disclosure|showExtra|"
    r"ownerDetails|more)\b[^}]*)\}",
    re.I,
)

from tauri_gate.import_boot_setup_rest import (
    _SETUP_HIDDEN_ATTR,
    _SETUP_CAROUSEL,
    _SETUP_ACCOUNT_ACTION,
    _SETUP_SAMPLE_CLOUD,
    _SETUP_URL_FIELD,
    _SETUP_REQUIRE_OWNER,
    _SETUP_DOC_ONE_SCREEN,
    _SETUP_DOC_OPTIONAL,
    _svelte_closed_block_at,
    _setup_branch,
    _setup_mounted_extra,
    _strip_setup_disclosures,
    _setup_has_field,
    _setup_visible_owner_fields,
    _setup_fn,
    __all__,
)

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
