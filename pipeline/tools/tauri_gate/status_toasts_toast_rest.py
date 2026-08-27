"""Continuation of status_toasts_toast."""
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
from tauri_gate.status_toasts_toast import (
    _TOAST_HOOK,
)
_TOAST_SINK = re.compile(
    r"("
    r"\b(?:toast|showToast|pushToast|addToast|notifyToast|toastError|"
    r"toastFail|toastInfo|toastWarning)\s*(?:\.|\()"
    r"|<(?:Toast|Toaster)\b"
    r"|\$lib/components/ui/toast"
    r"|\bdata-toast\b"
    r"|\btoasts\s*=\s*\["
    r"|\btoasts\.push\s*\("
    r")",
    re.I,
)
_SHOW_ERR_CALL = re.compile(r"\bshowErr\s*\(")
_TOAST_BODY_INTERP = re.compile(
    r"\{body_text\}|copyMenu\.body_text|\{copyMenu\.body_text\}|\{copyMenu\.text\}"
)
_TOAST_CDN = re.compile(
    r"("
    r"(?:unpkg(?:\.com)?|jsdelivr(?:\.net)?|esm\.sh|cdn\.)[^\"'\s)]*"
    r"(?:sonner|toastify|hot-toast|notistack|react-toast|svelte-toast)"
    r"|https?://[^\"'\s)]*(?:sonner|toastify|hot-toast|notistack)"
    r")",
    re.I,
)
_ANALYTICS_REMOTE_PKG = re.compile(
    r"[\"'](?:"
    r"@sentry(?:/[^\"']*)?"
    r"|sentry(?:-svelte)?"
    r"|posthog(?:-js)?"
    r"|mixpanel(?:-browser)?"
    r"|amplitude-js"
    r"|@amplitude(?:/[^\"']*)?"
    r"|@segment/analytics(?:-next)?"
    r"|@vercel/analytics"
    r"|plausible-tracker"
    r"|@openreplay(?:/[^\"']*)?"
    r"|bugsnag"
    r"|rollbar"
    r"|logrocket"
    r"|@datadog/browser-rum"
    r"|google-analytics"
    r")[\"']",
    re.I,
)
_HTTP_CLIENT_PKG = re.compile(
    r"[\"'](?:"
    r"axios"
    r"|ky(?:-universal)?"
    r"|got"
    r"|node-fetch"
    r"|whatwg-fetch"
    r"|superagent"
    r"|@tauri-apps/plugin-http"
    r"|tauri-plugin-http"
    r")[\"']",
    re.I,
)
_DOCS_204_TOAST = re.compile(
    r"("
    r"(?:copy|clipboard|reveal).{0,120}toast"
    r"|toast.{0,120}(?:copy|clipboard|reveal)"
    r")",
    re.I | re.S,
)
_DOCS_204_INPAGE = re.compile(
    r"("
    r"(?:sandbox|lock|not[- ]an[- ]archive).{0,160}(?:in-page|banner|setup)"
    r"|(?:in-page|banner).{0,160}(?:sandbox|lock|not[- ]an[- ]archive)"
    r")",
    re.I | re.S,
)


def _ident_body(src: str, name: str) -> str:
    return _ts_function_body(src, name) or _function_body(src, name)


def _assigns_err_banner(blob: str) -> bool:
    """True if the blob writes the full-width err banner (showErr / err = …)."""
    if _SHOW_ERR_CALL.search(blob):
        return True
    for m in re.finditer(r"\berr\s*=\s*", blob):
        rest = blob[m.end() :].lstrip()
        if rest.startswith('""') or rest.startswith("''"):
            continue
        if re.match(r"['\"]\s*['\"]", rest):
            continue
        return True
    return False


def _uses_toast_sink(blob: str) -> bool:
    return bool(_TOAST_SINK.search(blob))


def _owned_toast_paths(crate: Path) -> list[Path]:
    """Owned toast primitive and equivalent Toaster files (no node_modules)."""
    found: list[Path] = []
    ui = crate / "web" / "lib" / "components" / "ui"
    for name in ("toast", "toaster"):
        d = ui / name
        if d.is_dir():
            found.extend(
                p
                for p in d.rglob("*")
                if p.suffix in {".svelte", ".ts", ".js", ".css"}
                and "node_modules" not in p.parts
            )
    web = crate / "web"
    if web.is_dir():
        for p in web.rglob("*.svelte"):
            if "node_modules" in p.parts:
                continue
            if p.stem.lower() in {"toast", "toaster", "toasts"}:
                found.append(p)
    seen: set[Path] = set()
    out: list[Path] = []
    for p in found:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _toast_chrome_ok(crate: Path, svelte_blob: str) -> bool:
    if _TOAST_HOOK.search(svelte_blob):
        return True
    return bool(_owned_toast_paths(crate))


def _toast_source_blob(crate: Path) -> str:
    parts: list[str] = []
    for p in _owned_toast_paths(crate):
        parts.append(p.read_text())
    for p in _product_svelte(crate):
        text = p.read_text()
        if _TOAST_HOOK.search(text) or re.search(
            r"components/ui/toast|\$lib/components/ui/toast", text
        ):
            parts.append(text)
    for p in _web_ts_sources(crate):
        if p.suffix not in {".ts", ".js"}:
            continue
        text = p.read_text()
        if _TOAST_HOOK.search(text) or re.search(
            r"components/ui/toast|\$lib/components/ui/toast", text
        ):
            parts.append(text)
    return "\n".join(parts)


def _cas_onerror_resolved(crate: Path) -> str:
    """Bodies bound to CasAttach onError if a future tag still binds it."""
    chunks: list[str] = []
    app_path = crate / "web" / "App.svelte"
    app = _web_logic(crate) if app_path.is_file() else ""
    for p in _product_svelte(crate):
        text = p.read_text()
        for m in re.finditer(r"<CasAttach\b", text):
            tag = _svelte_open_tag_at(text, m.start())
            bind = re.search(r"\bonError\s*=\s*\{([^}]+)\}", tag)
            shorthand = "{onError}" in tag
            expr = bind.group(1).strip() if bind else ("onError" if shorthand else "")
            if not expr:
                continue
            chunks.append(expr)
            ident = expr if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expr) else ""
            if not ident:
                continue
            body = _ident_body(text, ident)
            if not body:
                body = _ident_body(app, ident)
            if body:
                chunks.append(body)
            elif ident == "onError":
                chunks.append(_ident_body(app, "showErr"))
    return "\n".join(c for c in chunks if c)


def _reveal_fail_blob(crate: Path) -> str:
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    cas = cas_path.read_text() if cas_path.is_file() else ""
    body = _ident_body(cas, "revealInFinder")
    parts = [body]
    parts.append(
        _windows_around(
            cas,
            re.compile(r"\b(?:revealCas|revealInFinder|reveal_cas)\b"),
            before=80,
            after=200,
        )
    )
    joined = "\n".join(parts)
    if re.search(r"\bonError\b", body or joined):
        parts.append(_cas_onerror_resolved(crate))
    if re.search(r"\bshowErr\b", "\n".join(parts)):
        app_path = crate / "web" / "App.svelte"
        if app_path.is_file():
            parts.append(_ident_body(app_path.read_text(), "showErr"))
    return "\n".join(parts)

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

__all__ = [
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
    "__all__",
]
