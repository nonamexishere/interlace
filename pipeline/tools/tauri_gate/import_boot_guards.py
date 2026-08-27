"""Helpers extracted from import_boot.py (import_boot_guards)."""
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
from tauri_gate.status_toasts_hues import _HUE_AMBER, _SPINNER_NAME, _hue_surface

_PRE_WRAP = re.compile(
    r"<([a-zA-Z][\w:-]*)([^>]*\bwhitespace-pre-wrap\b[^>]*)>(.*?)</\1>",
    re.S,
)


def _ident_negated(cond: str, ident: str) -> bool:
    if re.search(rf"!\s*{re.escape(ident)}\b", cond):
        return True
    if re.search(
        rf"\b{re.escape(ident)}\s*(?:===?|!==?)\s*(?:false|0|null|undefined)",
        cond,
    ):
        return True
    if re.search(
        rf"(?:false|0|null|undefined)\s*(?:===?|!==?)\s*{re.escape(ident)}\b",
        cond,
    ):
        return True
    return False


def _input_guard_span(body: str) -> tuple[int, int] | None:
    """Span of the INPUT/TEXTAREA/SELECT early-exit (Esc blur lives here)."""
    m = re.search(r"tagName\s*===?\s*[\"']INPUT[\"']", body)
    if not m:
        return None
    start = body.rfind("if", 0, m.start())
    if start < 0:
        start = m.start()
    brace = body.find("{", m.start())
    if brace < 0:
        ret = body.find("return", m.start())
        return (start, ret + 6 if ret >= 0 else m.end())
    end = _match_closer(body, brace)
    return (start, end if end >= 0 else brace)


# #224 — measure-and-cache variable row heights; constant 88 fallback; prefix-sum spacers.
_HEIGHT_CACHE = re.compile(
    r"\b("
    r"rowHeights"
    r"|tlRowHeights"
    r"|measuredHeights"
    r"|heightCache"
    r"|rowHeightCache"
    r"|cachedHeights"
    r"|cachedRowHeights"
    r"|heightsByIndex"
    r"|tlHeights"
    r")\b"
)


def _hue_findings(text: str) -> list[str]:
    """Banned raw hues (issue #198). Token defs may live in app.css only."""
    surface = _hue_surface(text)
    found: list[str] = []
    amber = sorted(set(_HUE_AMBER.findall(surface)))
    if amber:
        found.append("amber-* (" + ", ".join(amber) + ")")
    yellow = sorted(set(_HUE_YELLOW.findall(surface)))
    if yellow:
        found.append("yellow-* (" + ", ".join(yellow) + ")")
    if _HUE_BLACK80.search(surface):
        found.append("black/80")
    hexes = _HUE_HEX_TW.findall(surface) + _HUE_HEX_CSS.findall(surface)
    if hexes:
        found.append("hex (" + ", ".join(sorted(set(hexes))) + ")")
    return found


def _people_list_gen(refresh: str) -> tuple[str, str] | None:
    """`(local, counter)` if refreshPeople increments a people-list gen.

    `peopleGen` / roster / ppl names count. `tlGen` only if refreshPeople
    itself increments it (then it is also the people-list gen).
    """
    ipc_at = _first_substr_pos(refresh, ("api.people",))
    tok = _gen_increment_before_ipc(refresh, ipc_at)
    if not tok:
        return None
    local, counter = tok
    if _PEOPLE_GEN_COUNTER.search(counter) or _PEOPLE_GEN_COUNTER.search(local):
        return tok
    if counter == "tlGen":
        return tok
    return None


def _contrast_light_blob(css: str) -> str:
    """@theme plus :root that is not inside prefers-color-scheme: dark."""
    chunks = list(_css_at_bodies(css, _CONTRAST_AT_THEME))
    dark_spans: list[tuple[int, int]] = []
    for m in _CONTRAST_DARK_MEDIA.finditer(css):
        brace = css.find("{", m.start())
        body = _css_brace_body(css, brace)
        if body:
            dark_spans.append((brace, brace + 1 + len(body)))
    for m in _CONTRAST_ROOT.finditer(css):
        brace = css.find("{", m.start())
        if any(start <= brace <= end for start, end in dark_spans):
            continue
        body = _css_brace_body(css, brace)
        if body:
            chunks.append(body)
    return "\n".join(chunks)


def _if_gen_eq_contains(body: str, pos: int, local: str, counter: str) -> bool:
    """True if `pos` sits in `if (local === counter) { … }` or its then-stmt."""
    pat = re.compile(
        rf"if\s*\(\s*(?:{re.escape(local)}\s*===?\s*{re.escape(counter)}"
        rf"|{re.escape(counter)}\s*===?\s*{re.escape(local)})\s*\)"
    )
    for m in pat.finditer(body[:pos]):
        i = m.end()
        while i < len(body) and body[i] in " \t\n\r":
            i += 1
        if i < len(body) and body[i] == "{":
            close = _match_closer(body, i)
            if close >= pos > i:
                return True
        elif i == pos:
            return True
    return False


def _gen_increment_before_ipc(body: str, ipc_at: int) -> tuple[str, str] | None:
    """`(local, counter)` for `const gen = ++searchGen` before the first IPC."""
    if ipc_at < 0:
        return None
    prefix = body[:ipc_at]
    for m in re.finditer(
        r"(?:const|let|var)\s+(\w+)\s*=\s*(?:\+\+\s*(\w+)|(\w+)\s*\+\+)",
        prefix,
    ):
        local = m.group(1)
        counter = m.group(2) or m.group(3)
        if local in _PANE_RESULT_WRITES or counter in _PANE_RESULT_WRITES:
            continue
        if local.lower() != "gen" and not re.search(r"gen", counter, re.I):
            continue
        return local, counter
    return None


def _has_css_spinner(blob: str) -> bool:
    """True when blob has a CSS-only rotating spinner (no network image required)."""
    if not blob:
        return False
    if _SPIN_ANIM.search(blob) and (
        _SPINNER_NAME.search(blob) or (_SPINNER_RING.search(blob) and _SPINNER_BORDER.search(blob))
    ):
        return True
    # Tailwind animate-spin on a ring element is enough by itself.
    if re.search(r"animate-spin", blob) and (
        _SPINNER_RING.search(blob) or _SPINNER_BORDER.search(blob) or _SPINNER_NAME.search(blob)
    ):
        return True
    # Named spinner class with an inline/keyframes animation nearby.
    if _SPINNER_NAME.search(blob) and _SPIN_ANIM.search(blob):
        return True
    return False


def _ls_pref_keys(src: str) -> list[str]:
    """Literal / resolved localStorage keys (sidebar persist)."""
    keys: list[str] = []
    for m in _LS_CALL.finditer(src):
        lit = m.group("lit")
        if lit:
            keys.append(lit)
            continue
        name = m.group("id")
        if not name:
            continue
        cm = re.search(
            rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*[\"'`]([^\"'`]+)[\"'`]",
            src,
        )
        keys.append(cm.group(1) if cm else name)
    keys.extend(_LS_BRACKET.findall(src))
    return keys


def _owned_imported_names(src: str, name: str) -> list[str]:
    """Local identifiers imported from `$lib/components/ui/{name}` (or relative)."""
    path = _owned_import_path_rx(name)
    out: list[str] = []
    for m in re.finditer(rf"import\s+\{{([^}}]+)\}}\s+from\s+{path}", src):
        for part in m.group(1).split(","):
            part = part.strip()
            if not part:
                continue
            bits = re.split(r"\s+as\s+", part)
            local = bits[-1].strip()
            if local:
                out.append(local)
    for m in re.finditer(rf"import\s+\*\s+as\s+(\w+)\s+from\s+{path}", src):
        out.append(m.group(1))
    for m in re.finditer(rf"import\s+(\w+)\s+from\s+{path}", src):
        out.append(m.group(1))
    return out


def _empty_state_blocks(src: str) -> list[str]:
    """Each <EmptyState …> usage (local import alias OK), incl. children."""
    out: list[str] = []
    for name in _empty_state_local_names(src):
        for m in re.finditer(rf"<{re.escape(name)}\b", src):
            open_tag = _svelte_open_tag_at(src, m.start())
            if open_tag.rstrip().endswith("/>"):
                out.append(open_tag)
                continue
            close = re.search(
                rf"</{re.escape(name)}\s*>",
                src[m.start() + len(open_tag) :],
                re.I,
            )
            if not close:
                out.append(open_tag)
            else:
                out.append(src[m.start() : m.start() + len(open_tag) + close.end()])
    return out


# #184 — people list / VoiceOver: short human time, not raw ISO last_activity_at.
_HUMAN_TIME_HELPERS = (
    "humanTime",
    "shortTime",
    "formatLastActivity",
    "utcHumanTime",
    "activityTime",
    "lastActivityLabel",
    "formatActivityAt",
    "shortActivity",
    "humanLastActivity",
    "utcShortTime",
    "formatUtcShort",
    "shortHumanTime",
    "formatHumanTime",
    "humanActivity",
    "utcActivity",
    "formatUtcActivity",
)

from tauri_gate.import_boot_guards_rest import (
    _markup_uses_chrome_helper,
    _svelte_open_tag_at,
    _app_keydown_body,
    _review_if_return_conds,
    _unguarded_post_ipc_writes,
    _same_block_gen_ne_return,
    _svelte_if_true_branch,
    _assignment_gen_guarded,
)

__all__ = [
    "_PRE_WRAP",
    "_ident_negated",
    "_input_guard_span",
    "_HEIGHT_CACHE",
    "_hue_findings",
    "_people_list_gen",
    "_contrast_light_blob",
    "_if_gen_eq_contains",
    "_gen_increment_before_ipc",
    "_has_css_spinner",
    "_ls_pref_keys",
    "_owned_imported_names",
    "_empty_state_blocks",
    "_HUMAN_TIME_HELPERS",
    "_markup_uses_chrome_helper",
    "_svelte_open_tag_at",
    "_app_keydown_body",
    "_review_if_return_conds",
    "_unguarded_post_ipc_writes",
    "_same_block_gen_ne_return",
    "_svelte_if_true_branch",
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
    "_HUE_AMBER",
    "_SPINNER_NAME",
    "_hue_surface",
]
