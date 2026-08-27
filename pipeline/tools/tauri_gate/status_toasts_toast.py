"""Helpers extracted from status_toasts.py (status_toasts_toast)."""
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
    _ancestor_tags,
    _call_arg,
    _CHROME_HELPER_NAMES,
    _CHROME_IMPORT_SPEC,
    _CHROME_NO_TRANSLATE_FIELDS,
    _DATA_PEOPLE_SIDEBAR,
    _function_body,
    _markup_open_tag,
    _match_closer,
    _open_tag_around,
    _PERSON_PANE_SKIP,
    _product_svelte,
    _SANDBOX_137,
    _search_pane_blob,
    _strip_html_comments,
    _ts_function_body,
    _web_logic,
    _web_sources,
    _web_ts_sources,
    _without_comments,
)

from tauri_gate.import_boot_guards import (
    _HUMAN_TIME_HELPERS,
    _if_gen_eq_contains,
    _input_guard_span,
    _owned_imported_names,
    _same_block_gen_ne_return,
    _svelte_if_true_branch,
    _svelte_open_tag_at,
)
from tauri_gate.status_toasts_chrome import (
    _HM_PART,
    _SEARCH_EFFECT,
    _UTC_FMT,
    _parse_if_chain,
    _PEOPLE_EACH,
    _windows_around,
    _MONTH_SHORT,
)


def _short_time_formatter_ok(logic: str) -> bool:
    """A helper (or inline) turns ISO into a short time like `11 Aug 14:32`."""
    for name in _HUMAN_TIME_HELPERS:
        body = _ts_function_body(logic, name) or _function_body(logic, name)
        if body and _MONTH_SHORT.search(body) and _HM_PART.search(body):
            return True
    if _MONTH_SHORT.search(logic) and _HM_PART.search(logic) and (
        _UTC_FMT.search(logic) or re.search(r"\bget(?:Hours|Minutes|Date|Month|FullYear)\s*\(", logic)
    ):
        return True
    return False


def _chrome_helper_on_body(blob: str, helpers: set[str]) -> bool:
    if not helpers:
        return False
    names = "|".join(re.escape(h) for h in sorted(helpers, key=len, reverse=True))
    fields = "|".join(_CHROME_NO_TRANSLATE_FIELDS)
    return bool(
        re.search(
            rf"\b(?:{names})\s*\(\s*(?:[^)]{{0,100}}\.)?(?:{fields})\b",
            blob,
        )
    )


def _svelte_effect_args(src: str) -> list[str]:
    """Argument blob of each `$effect(() => { … })` / `$effect.pre(…)`."""
    out: list[str] = []
    for m in _SEARCH_EFFECT.finditer(src):
        open_p = src.find("(", m.start())
        if open_p < 0:
            continue
        close = _match_closer(src, open_p)
        if close < 0:
            continue
        out.append(src[open_p + 1 : close])
    return out


def _tag_inner(markup: str, tag: str) -> list[str]:
    """Inner HTML of each <tag>…</tag> (first close; chrome strips are shallow)."""
    out: list[str] = []
    for m in re.finditer(rf"<{re.escape(tag)}\b[^>]*>", markup, re.I):
        start = m.start()
        end = markup.find(f"</{tag}>", m.end())
        if end < 0:
            end = min(len(markup), m.end() + 2400)
        else:
            end = end + len(f"</{tag}>")
        out.append(markup[start:end])
    return out


def _web_chrome_blob(crate: Path) -> str:
    parts: list[str] = []
    for p in _web_ts_sources(crate):
        parts.append(p.read_text())
    for extra in (
        crate / "web" / "app.css",
        crate / "index.html",
        crate / "web" / "index.html",
    ):
        if extra.is_file():
            parts.append(extra.read_text())
    return "\n".join(parts)


def _svelte_if_chains(src: str) -> list[list[tuple[str, str]]]:
    chains: list[list[tuple[str, str]]] = []
    i = 0
    while True:
        m = re.search(r"\{#if\s+([^}]+)\}", src[i:])
        if not m:
            break
        start = i + m.start()
        chain, end = _parse_if_chain(src, start)
        if chain:
            chains.append(chain)
        i = end if end > start else start + 1
    return chains


# #132 — keyboard map (⌘F Search #q from every view, Esc back, ⌘1–5 tabs).
# #208 rewrites Find-on-People: ⌘F no longer focuses #person-filter (`/` still does).
_KEY_F = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']f[\"']"
    r"|[\"']f[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']F[\"']"
    r"|[\"']F[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*\.\s*toLowerCase\s*\(\s*\)\s*===?\s*[\"']f[\"']"
    r"|(?:e\.)?code\s*===?\s*[\"']KeyF[\"']"
    r")",
    re.I,
)


def _person_detail_markup(app: str) -> str:
    """Person column chrome (title → text-only footer), not the people sidebar."""
    start = app.find("{personTitle}")
    if start < 0:
        start = app.find("personTitle")
    end = app.find("Bodies are text")
    if start >= 0 and end > start:
        return app[start:end]
    markup = app
    script_end = app.rfind("</script>")
    if script_end >= 0:
        markup = app[script_end:]
    return markup


def _motion_js_blob(crate: Path) -> str:
    """Svelte <script> + .ts only — CSS prefers-reduced-motion must not count."""
    web = crate / "web"
    parts: list[str] = []
    for p in sorted(web.rglob("*")):
        if "node_modules" in p.parts:
            continue
        if p.suffix == ".ts":
            parts.append(p.read_text())
        elif p.suffix == ".svelte":
            text = p.read_text()
            for m in re.finditer(r"<script\b[^>]*>(.*?)</script>", text, re.S):
                parts.append(m.group(1))
    return "\n".join(parts)


def _appearance_class_names(tag: str) -> list[str]:
    chunks: list[str] = []
    for m in re.finditer(
        r"""\bclass(?:Name)?\s*=\s*(?:["']([^"']+)["']|\{cn\(\s*["']([^"']+)["'])""",
        tag,
    ):
        chunks.append(m.group(1) or m.group(2) or "")
    names: list[str] = []
    for chunk in chunks:
        for tok in chunk.split():
            base = tok.split(":")[-1]
            if re.match(r"^[A-Za-z_][\w-]*$", base):
                names.append(base)
    return names


def _people_sidebar_regions(crate: Path) -> list[str]:
    """People column chrome: filter + list, not the conversation switcher."""
    found: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        text = p.read_text()
        if not _PEOPLE_EACH.search(text) and "person-filter" not in text:
            continue
        # Prefer an explicit people-sidebar hook when present.
        for m in _DATA_PEOPLE_SIDEBAR.finditer(text):
            found.append(text[max(0, m.start() - 120) : m.end() + 2400])
        if found:
            continue
        # Else take a window around the people list / filter.
        for m in _PEOPLE_EACH.finditer(text):
            found.append(text[max(0, m.start() - 800) : m.end() + 1200])
        if not found and "person-filter" in text:
            i = text.find("person-filter")
            found.append(text[max(0, i - 400) : i + 2000])
    return found



_ARIA_BUSY_STATIC = re.compile(
    r"""\baria-busy\s*=\s*(?:"true"|'true'|\{true\})""",
    re.I,
)
_ROLE_STATUS = re.compile(r"""\brole\s*=\s*(?:"status"|'status')""", re.I)
_SR_ONLY_CLASS = re.compile(r"\bsr-only\b")
_AUDIBLE_COPY = re.compile(r"(Loading|Searching|Busy|people|timeline)", re.I)
_SEARCHING_SUBMIT = re.compile(
    r"""searching\s*\?\s*["']Searching|(?<![\w])Searching(?:…|\.\.\.)""",
    re.I,
)


def _aria_busy_bound_to(src: str, flag: str) -> bool:
    return bool(
        re.search(
            rf"\baria-busy\s*=\s*\{{[^}}]*\b{re.escape(flag)}\b[^}}]*\}}",
            src,
        )
    )


def _strip_aria_hidden_trees(src: str) -> str:
    rx = re.compile(
        r"<([A-Za-z][\w:.-]*)\b[^>]*\baria-hidden\b[^>]*(?:/>|>.*?</\1\s*>)",
        re.I | re.S,
    )
    prev = None
    out = src
    while prev != out:
        prev = out
        out = rx.sub(" ", out)
    return out


def _has_audible_status(src: str) -> bool:
    """role=status or sr-only copy that is not aria-hidden."""
    audible = _strip_aria_hidden_trees(src)
    for m in re.finditer(r"<([A-Za-z][\w:.-]*)\b([^>]*?)>", audible):
        attrs = m.group(2)
        if not (_ROLE_STATUS.search(attrs) or _SR_ONLY_CLASS.search(attrs)):
            continue
        rest = audible[m.end() : m.end() + 280]
        text = re.sub(r"<[^>]+>", " ", rest)
        if _AUDIBLE_COPY.search(text) or _AUDIBLE_COPY.search(rest):
            return True
    return False


def _inflight_is_audible(surface: str, branch: str, flag: str) -> bool:
    if flag and _aria_busy_bound_to(surface, flag):
        return True
    if flag and _aria_busy_bound_to(branch, flag):
        return True
    if _ARIA_BUSY_STATIC.search(branch):
        return True
    if _has_audible_status(branch) or _has_audible_status(surface):
        return True
    return False


def _region_window(src: str, hook: str, span: int = 8000) -> str:
    m = re.search(hook, src, re.I | re.S)
    if not m:
        return ""
    return src[m.start() : m.start() + span]




# #204 — owned toast for non-blocking copy / Reveal failures (not the err banner).
_TOAST_HOOK = re.compile(r"\bdata-toast\b")

from tauri_gate.status_toasts_toast_rest import (
    _TOAST_SINK,
    _SHOW_ERR_CALL,
    _TOAST_BODY_INTERP,
    _TOAST_CDN,
    _ANALYTICS_REMOTE_PKG,
    _HTTP_CLIENT_PKG,
    _DOCS_204_TOAST,
    _DOCS_204_INPAGE,
    _ident_body,
    _assigns_err_banner,
    _uses_toast_sink,
    _owned_toast_paths,
    _toast_chrome_ok,
    _toast_source_blob,
    _cas_onerror_resolved,
    _reveal_fail_blob,
    __all__,
)

__all__ = [
    "_short_time_formatter_ok",
    "_chrome_helper_on_body",
    "_svelte_effect_args",
    "_tag_inner",
    "_web_chrome_blob",
    "_svelte_if_chains",
    "_KEY_F",
    "_person_detail_markup",
    "_motion_js_blob",
    "_appearance_class_names",
    "_people_sidebar_regions",
    "_ARIA_BUSY_STATIC",
    "_ROLE_STATUS",
    "_SR_ONLY_CLASS",
    "_AUDIBLE_COPY",
    "_SEARCHING_SUBMIT",
    "_aria_busy_bound_to",
    "_strip_aria_hidden_trees",
    "_has_audible_status",
    "_inflight_is_audible",
    "_region_window",
    "_TOAST_HOOK",
    "_TOAST_SINK",
    "_SHOW_ERR_CALL",
    "_TOAST_BODY_INTERP",
    "_TOAST_CDN",
    "_ANALYTICS_REMOTE_PKG",
    "_HTTP_CLIENT_PKG",
    "_DOCS_204_TOAST",
    "_DOCS_204_INPAGE",
    "_ident_body",
    "_assigns_err_banner",
    "_uses_toast_sink",
    "_owned_toast_paths",
    "_toast_chrome_ok",
    "_toast_source_blob",
    "_cas_onerror_resolved",
    "_reveal_fail_blob",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_ancestor_tags",
    "_call_arg",
    "_CHROME_HELPER_NAMES",
    "_CHROME_IMPORT_SPEC",
    "_CHROME_NO_TRANSLATE_FIELDS",
    "_DATA_PEOPLE_SIDEBAR",
    "_function_body",
    "_markup_open_tag",
    "_match_closer",
    "_open_tag_around",
    "_PERSON_PANE_SKIP",
    "_product_svelte",
    "_SANDBOX_137",
    "_search_pane_blob",
    "_strip_html_comments",
    "_ts_function_body",
    "_web_logic",
    "_web_sources",
    "_web_ts_sources",
    "_without_comments",
    "_HUMAN_TIME_HELPERS",
    "_if_gen_eq_contains",
    "_input_guard_span",
    "_owned_imported_names",
    "_same_block_gen_ne_return",
    "_svelte_if_true_branch",
    "_svelte_open_tag_at",
    "_HM_PART",
    "_SEARCH_EFFECT",
    "_UTC_FMT",
    "_parse_if_chain",
    "_PEOPLE_EACH",
    "_windows_around",
    "_MONTH_SHORT",
]
