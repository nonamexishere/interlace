"""In-flight / toast / partial-error chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _SANDBOX_137,
    _TOAST_SONNER_PKG,
    _WRITE_TEXT,
    _assigned_idents,
    _call_arg,
    _chrome_en_text,
    _cond_uses_flag,
    _first_substr_pos,
    _function_body,
    _gen_increment_before_ipc,
    _hook_element_blocks,
    _match_closer,
    _open_tag_around,
    _people_inflight_branch,
    _people_sidebar_regions,
    _product_svelte,
    _svelte_if_chains,
    _svelte_if_true_branch,
    _svelte_markup,
    _svelte_open_tag_at,
    _template_stack,
    _try_catch_blocks,
    _ts_function_body,
    _typo_docs_blob,
    _unguarded_post_ipc_writes,
    _web_chrome_blob,
    _web_logic,
    _web_ts_sources,
    _windows_around,
    _without_comments,
)


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


def assert_inflight_audible_status(crate: Path) -> None:
    """#203 follow-up: people / timeline in-flight must stay audible.

    aria-busy on the region and/or role=status / sr-only text that is
    not aria-hidden. Decorative bars may stay aria-hidden. Search may
    keep the submit label “Searching…”.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#203: App.svelte required (people / timeline in-flight a11y)")
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#203: SearchPane.svelte required (search in-flight a11y)")
    app = app_path.read_text()
    search = search_path.read_text()

    people_flag, people_branch = _people_inflight_branch(app)
    if not people_branch:
        for region in _people_sidebar_regions(crate):
            flag, block = _people_inflight_branch(region)
            if block:
                people_flag, people_branch = flag, block
                break
    people_surface = (
        _region_window(app, r"data-people-sidebar")
        + "\n"
        + _open_tag_around(app, r"""role=["']listbox["']""")
        + "\n"
        + people_branch
    )
    if not _inflight_is_audible(people_surface, people_branch, people_flag):
        fail(
            "#203: people list in-flight must expose aria-busy on the region "
            "or a role=\"status\" / sr-only line that is not aria-hidden"
        )

    tl_branch = _svelte_if_true_branch(app, "tlLoading")
    tl_surface = (
        _region_window(app, r"""id=["']person-timeline["']""")
        + "\n"
        + _open_tag_around(app, r"""id=["']person-timeline["']""")
        + "\n"
        + tl_branch
    )
    if not _inflight_is_audible(tl_surface, tl_branch, "tlLoading"):
        fail(
            "#203: person timeline in-flight must expose aria-busy on the region "
            "or a role=\"status\" / sr-only line that is not aria-hidden"
        )

    search_branch = _svelte_if_true_branch(search, "searching")
    if _SEARCHING_SUBMIT.search(search):
        return
    search_surface = search_branch + "\n" + search
    if not _inflight_is_audible(search_surface, search_branch, "searching"):
        fail(
            "#203: search in-flight must keep “Searching…” or expose aria-busy "
            "/ a role=\"status\" / sr-only line that is not aria-hidden"
        )




# #204 — owned toast for non-blocking copy / Reveal failures (not the err banner).
_TOAST_HOOK = re.compile(r"\bdata-toast\b")
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
    app = app_path.read_text() if app_path.is_file() else ""
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


def _copy_fail_blob(crate: Path) -> str:
    app_path = crate / "web" / "App.svelte"
    app = app_path.read_text() if app_path.is_file() else ""
    web = _web_logic(crate)
    parts: list[str] = []
    for src in (app, web):
        body = _ident_body(src, "copyText")
        if body:
            parts.append(body)
            break
    parts.append(_windows_around(web, _WRITE_TEXT, before=80, after=200))
    if re.search(r"\bshowErr\b", "\n".join(parts)):
        parts.append(_ident_body(app, "showErr"))
    return "\n".join(parts)


def _toast_args_include_body(blob: str) -> bool:
    for m in re.finditer(
        r"\b(?:toast|showToast|pushToast|addToast|notifyToast|toastError|toastFail)\s*\(",
        blob,
    ):
        arg = _call_arg(blob, m.end() - 1)
        if re.search(r"body_text|copyMenu\.body_text|copyMenu\.text\b|displayBody\s*\(", arg):
            return True
    return False


def assert_recoverable_toasts(crate: Path) -> None:
    """#204: owned toast for copy / Reveal failures; blocking errors stay in-page.

    data-toast and/or $lib/components/ui/toast (or Toaster). Reveal-fail and
    copy-fail go through the toast, not only err = / the full-width banner.
    Sandbox #137 sentence, lock, and not-an-archive stay in-page via
    friendly / banner. Toasts never interpolate body_text. ConfirmDialog
    stays. No analytics / Sentry / HTTP client / CDN toast kit. Do not
    add sonner here — #201/#202 package bans stay.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#204: App.svelte required (err banner + copy / sandbox copy)")
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail("#204: CasAttach.svelte required (Reveal in Finder failure path)")
    app = app_path.read_text()
    svelte_blob = "\n".join(p.read_text() for p in _product_svelte(crate))
    pkg_path = crate / "package.json"
    pkg = pkg_path.read_text() if pkg_path.is_file() else ""

    # 1) Toast chrome exists (owned primitive and/or data-toast). No CDN kit.
    if not _toast_chrome_ok(crate, svelte_blob):
        fail(
            "#204: toast chrome required (data-toast and/or owned "
            "$lib/components/ui/toast) — copy / Reveal failures must not "
            "be only the full-width err banner"
        )
    if _TOAST_CDN.search(_web_chrome_blob(crate)):
        fail("#204: toast chrome must be owned — no CDN / network toast kit")

    # 2) Reveal-fail and copy-fail use the toast, not only showErr / err =.
    reveal_blob = _reveal_fail_blob(crate)
    if not _uses_toast_sink(reveal_blob) or _assigns_err_banner(reveal_blob):
        fail(
            "#204: Reveal in Finder failure must show a toast, not only "
            "the full-width err banner (do not showErr / err = on that path)"
        )
    copy_blob = _copy_fail_blob(crate)
    if not _uses_toast_sink(copy_blob) or _assigns_err_banner(copy_blob):
        fail(
            "#204: Copy text / clipboard failure must show a toast, not only "
            "the full-width err banner (do not showErr / err = on that path)"
        )

    # 3) Toast markup / helper must not interpolate body_text.
    toast_src = _toast_source_blob(crate)
    if _TOAST_BODY_INTERP.search(toast_src) or _toast_args_include_body(
        toast_src + "\n" + reveal_blob + "\n" + copy_blob
    ):
        fail(
            "#204: toast markup / helper must not interpolate body_text "
            "(no {body_text} / copyMenu.body_text / copyMenu.text — chrome copy only)"
        )

    # 4) Sandbox #137 sentence, lock, and not-an-archive stay in-page.
    friendly = _ident_body(app, "friendly")
    toast_only = _owned_toast_paths(crate)
    toast_files = "\n".join(p.read_text() for p in toast_only)
    in_page_sandbox = bool(
        _SANDBOX_137.search(app)
        or "SANDBOX_DENIED" in app
        or _SANDBOX_137.search(friendly)
        or "SANDBOX_DENIED" in friendly
    )
    if not in_page_sandbox:
        fail(
            "#204: sandbox-denied must keep the exact #137 sentence in-page "
            "(setup / err banner / friendly / SANDBOX_DENIED), not toast-only: "
            "macOS blocked that folder. Use Open existing… once so Interlace "
            "can remember it."
        )
    if _SANDBOX_137.search(toast_files) and not (
        _SANDBOX_137.search(app) or "SANDBOX_DENIED" in friendly
    ):
        fail(
            "#204: sandbox-denied #137 sentence must stay in-page "
            "(friendly / SANDBOX_DENIED / err banner), not toast-only"
        )
    if "SANDBOX_DENIED" not in friendly and not _SANDBOX_137.search(friendly):
        fail(
            "#204: friendly() must still surface the #137 sandbox sentence "
            "in-page (not toast-only)"
        )
    if "archive in use" not in friendly:
        fail(
            "#204: lock (archive in use) must stay in-page via friendly / "
            "err banner, not toast-only"
        )
    if "not an Interlace archive" not in friendly:
        fail(
            "#204: not-an-archive must stay in-page via friendly / err banner, "
            "not toast-only"
        )
    err_branch = _svelte_if_true_branch(app, "err")
    if not err_branch or not re.search(r"\{err\}", err_branch):
        fail(
            "#204: keep the in-page {#if err} banner for sandbox / lock / "
            "not-an-archive (do not move those to toast-only)"
        )

    # 5) ConfirmDialog stays. No analytics / remote reporter / HTTP client.
    confirm = crate / "web" / "lib" / "ConfirmDialog.svelte"
    if not confirm.is_file():
        fail(
            "#204: ConfirmDialog must stay "
            "(do not replace merge/unlink/undo/doctor confirm with a toast)"
        )
    if not any(
        p.name != "ConfirmDialog.svelte" and "ConfirmDialog" in p.read_text()
        for p in _product_svelte(crate)
    ):
        fail(
            "#204: ConfirmDialog must stay mounted "
            "(App / Review / Doctor — not replaced by a toast)"
        )
    logic = _web_logic(crate)
    if _ANALYTICS_REMOTE_PKG.search(pkg) or _ANALYTICS_REMOTE_PKG.search(logic):
        fail("#204: not in scope — no analytics / Sentry / remote reporter")
    if _HTTP_CLIENT_PKG.search(pkg):
        fail("#204: not in scope — no HTTP client")

    # 6) D24: copy / Reveal failures toast; sandbox / lock stay in-page.
    docs_path = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs_path.read_text() if docs_path.is_file() else ""
    if not dtxt.strip():
        fail(
            "#204: docs/user/app.md required (copy / Reveal failures toast; "
            "sandbox / lock / not-an-archive stay in-page)"
        )
    if not _SANDBOX_137.search(dtxt):
        fail(
            "#204: docs/user/app.md must keep the #137 sandbox sentence "
            "(macOS blocked that folder. Use Open existing… once so "
            "Interlace can remember it.)"
        )
    docs_blob = _typo_docs_blob()
    if not _DOCS_204_TOAST.search(docs_blob):
        fail(
            "#204: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "copy / Reveal failures toast"
        )
    if not _DOCS_204_INPAGE.search(docs_blob):
        fail(
            "#204: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "sandbox / lock / not-an-archive stay in-page"
        )


# #205 — one pane can fail without blanking the shell (Error + Retry).
# Grep hook: data-partial on each of the three Error+Retry surfaces
# (person timeline, search results, doctor scan). Equivalent hook is
# not accepted unless documented here — prefer data-partial as IN.md.
_PARTIAL_HOOK = re.compile(r"\bdata-partial\b")
_RETRY_COPY = re.compile(
    r"("
    r">\s*Retry\s*<"
    r"|[\"']Retry[\"']"
    r"|\bt\s*\(\s*[\"']retry[\"']\s*\)"
    r")",
    re.I,
)
_ERROR_COPY = re.compile(
    r"("
    r"\bError\b"
    r"|\bt\s*\(\s*[\"']error[\"']\s*\)"
    r")",
)
_ONERROR_CALL = re.compile(r"\bonError\s*\(")
_PARTIAL_MASCOT = re.compile(r"\bmascot\b|\billustration\b|<img\b", re.I)
_PARTIAL_CDN = re.compile(
    r"("
    r"https?://[^\"'\s)]+"
    r"|(?:unpkg(?:\.com)?|jsdelivr(?:\.net)?|esm\.sh|cdnjs|cdn\.)"
    r")",
    re.I,
)
_DOCTOR_HEAVY = re.compile(
    r"("
    r"\bdoctorRun\b"
    r"|\bgcCas\b"
    r"|\bgc_cas\b"
    r"|\brebuildFts\b"
    r"|\brebuild_fts\b"
    r"|\bintegrity\s*:\s*true\b"
    r")",
)
_AUTO_RETRY_TIMER = re.compile(r"\bsetInterval\b")
_RECURSIVE_RETRY = re.compile(
    r"\.catch\s*\(\s*(?:async\s*)?(?:function\b|[A-Za-z_]\w*|\([^)]*\)\s*=>)",
)
_SEARCH_FILTER_IDENTS = ("q", "platform", "conversationKind", "from", "to", "personId")
_PANE_CATCH_NOISE = frozenset(
    {
        "tlLoading",
        "tlAppending",
        "tlIndex",
        "tlScrollTop",
        "tlViewportHeight",
        "tlGen",
        "gen",
        "searchGen",
        "scanGen",
        "runGen",
        "loadGen",
        "scanning",
        "searching",
        "busy",
        "empty",
        "searched",
        "expanded",
        "body",
        "hitIndex",
        "hits",
        "timeline",
        "conversations",
        "identities",
        "personTitle",
        "quotedOpen",
        "platformFilter",
        "kindFilter",
        "showPersonChrome",
        "selectedConversationId",
        "selectedId",
        "issues",
        "lastOk",
        "confirmOpen",
        "confirmTitle",
        "confirmDesc",
        "confirmLabel",
        "pending",
        "err",
        "view",
        "setup",
        "people",
        "filter",
        "includeGroups",
        "before",
        "page",
        "chrono",
        "show",
        "pane",
        "prevHeight",
        "sc",
        "estTotal",
    }
)
_BANNER_SINKS = frozenset(
    {
        "showErr",
        "onError",
        "friendly",
        "String",
        "Error",
        "console",
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "function",
        "return",
        "typeof",
        "new",
        "await",
        "void",
        "Promise",
    }
)
_DOCS_205_RETRY = re.compile(r"error.{0,40}retry|retry.{0,40}error", re.I | re.S)


def _ipc_catch_bodies(src: str, fn_name: str, ipc_needles: tuple[str, ...]) -> list[str]:
    """Catch bodies whose try (or a callee try) mentions one of the IPC names."""
    body = _ident_body(src, fn_name)
    if not body:
        return []
    found: list[str] = []
    for try_body, catch_body in _try_catch_blocks(body):
        if any(needle in try_body for needle in ipc_needles):
            found.append(catch_body)
    if found:
        return found
    # One level of helpers (loadTimeline / runSearch / …).
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", body):
        callee = m.group(1)
        if callee in _BANNER_SINKS or callee == fn_name:
            continue
        nested = _ident_body(src, callee)
        if not nested:
            continue
        for try_body, catch_body in _try_catch_blocks(nested):
            if any(needle in try_body for needle in ipc_needles):
                found.append(catch_body)
    return found


def _pane_catch_dumps_banner(catch: str) -> bool:
    """True if the catch writes the App banner (showErr / onError / err =)."""
    if _assigns_err_banner(catch):
        return True
    return bool(_ONERROR_CALL.search(catch))


def _catch_error_flags(src: str, catch: str, seen: set[str] | None = None) -> set[str]:
    """Idents assigned in catch that can gate an in-pane Error+Retry."""
    found = seen if seen is not None else set()
    flags: set[str] = set()
    for ident in _assigned_idents(catch):
        if ident not in _PANE_CATCH_NOISE:
            flags.add(ident)
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", catch):
        name = m.group(1)
        if name in _BANNER_SINKS or name in found:
            continue
        found.add(name)
        nested = _ident_body(src, name)
        if nested:
            flags |= _catch_error_flags(src, nested, found)
    return flags


def _cond_negates_flag(cond: str, flags: set[str]) -> bool:
    for f in flags:
        if re.search(rf"!\s*(?:[\w$]+(?:\?\.|\.))*{re.escape(f)}\b", cond):
            return True
        if re.search(
            rf"\b(?:[\w$]+(?:\?\.|\.))*{re.escape(f)}\s*"
            r"(?:===?|==)\s*(?:null|undefined|false|[\"']{2})",
            cond,
        ):
            return True
    return False


def _attr_brace_expr(block: str, names: tuple[str, ...]) -> str:
    for name in names:
        m = re.search(rf"\b{re.escape(name)}\s*=\s*\{{", block)
        if not m:
            continue
        open_i = m.end() - 1
        close = _match_closer(block, open_i)
        if close >= 0:
            return block[open_i + 1 : close].strip()
    return ""


def _retry_click_expr(block: str) -> str:
    return _attr_brace_expr(
        block, ("onclick", "on:click", "onAction", "onaction", "onRetry", "onretry")
    )


def _resolve_handler_blob(src: str, expr: str) -> str:
    if not expr:
        return ""
    ident = re.fullmatch(r"(?:async\s+)?([A-Za-z_]\w*)", expr)
    if ident:
        return _ident_body(src, ident.group(1)) or expr
    call = re.fullmatch(r"(?:async\s+)?([A-Za-z_]\w*)\s*\([^)]*\)", expr)
    if call:
        body = _ident_body(src, call.group(1))
        return (body + "\n" + expr) if body else expr
    arrow = re.match(r"(?:async\s*)?(?:\([^)]*\)|[A-Za-z_]\w*)\s*=>\s*\{?", expr)
    if arrow:
        rest = expr[arrow.end() :]
        ident2 = re.match(r"([A-Za-z_]\w*)\s*\(", rest)
        if ident2:
            body = _ident_body(src, ident2.group(1))
            return (body + "\n" + expr) if body else expr
    return expr


def _block_has_retry_copy(block: str, en: str) -> bool:
    if _RETRY_COPY.search(block):
        return True
    for m in re.finditer(r"\bt\s*\(\s*[\"']([^\"']+)[\"']\s*\)", block):
        key = m.group(1)
        if re.search(rf"\b{re.escape(key)}\s*:\s*[\"']Retry[\"']", en):
            return True
    return False


def _block_has_error_copy(block: str, en: str) -> bool:
    if _ERROR_COPY.search(block):
        return True
    for m in re.finditer(r"\bt\s*\(\s*[\"']([^\"']+)[\"']\s*\)", block):
        key = m.group(1)
        if re.search(rf"\b{re.escape(key)}\s*:\s*[\"'][^\"']*Error[^\"']*[\"']", en):
            return True
    return False


def _partial_bound_to_flags(src: str, block: str, flags: set[str]) -> bool:
    if not flags:
        return False
    if _cond_uses_flag(block, flags):
        return True
    pos = src.find(block[: min(80, len(block))]) if block else -1
    if pos < 0:
        return False
    for kind, cond, _attrs in _template_stack(src, pos):
        if kind == "if" and _cond_uses_flag(cond, flags) and not _cond_negates_flag(
            cond, flags
        ):
            return True
        if kind == "if-else" and _cond_negates_flag(cond, flags):
            return True
    return False


def _empty_exclusive_of_partial(
    src: str, empty_title: str, flags: set[str]
) -> bool:
    """True if EmptyState `empty_title` cannot render with data-partial / fail flag."""
    if empty_title not in src:
        return True
    for chain in _svelte_if_chains(src):
        partial_branches = [b for _c, b in chain if _PARTIAL_HOOK.search(b)]
        empty_branches = [b for _c, b in chain if empty_title in b]
        if empty_branches and partial_branches:
            # Same branch would paint both — not exclusive.
            if any(empty_title in b and _PARTIAL_HOOK.search(b) for _c, b in chain):
                return False
            return True
        if empty_branches:
            for cond, body in chain:
                if empty_title not in body:
                    continue
                if flags and (
                    _cond_negates_flag(cond, flags)
                    or (cond == ":else" and any(_cond_uses_flag(c, flags) for c, _b in chain))
                ):
                    return True
    # Separate {#if}: EmptyState stack must negate the fail flag.
    markup = _svelte_markup(src)
    idx = src.find(empty_title)
    if idx < 0:
        idx = markup.find(empty_title)
        use = markup
    else:
        use = src
    if idx < 0:
        return False
    stack = _template_stack(use, idx)
    if flags and any(
        kind in {"if", "if-else"} and _cond_negates_flag(cond, flags)
        for kind, cond, _a in stack
    ):
        return True
    return False


def _interval_retries(src: str, load_names: tuple[str, ...]) -> bool:
    for m in re.finditer(r"\bsetInterval\s*\(", src):
        arg = _call_arg(src, m.end() - 1)
        if any(re.search(rf"\b{re.escape(n)}\b", arg) for n in load_names):
            return True
    return False


def _catch_auto_retries(catch: str, load_names: tuple[str, ...]) -> bool:
    if _AUTO_RETRY_TIMER.search(catch):
        return True
    if re.search(r"\bsetTimeout\s*\(", catch):
        for m in re.finditer(r"\bsetTimeout\s*\(", catch):
            arg = _call_arg(catch, m.end() - 1)
            if any(re.search(rf"\b{re.escape(n)}\b", arg) for n in load_names):
                return True
    if any(re.search(rf"\b{re.escape(n)}\s*\(", catch) for n in load_names):
        return True
    if _RECURSIVE_RETRY.search(catch):
        return True
    return False


def _effect_auto_retries(src: str, flags: set[str], load_names: tuple[str, ...]) -> bool:
    if not flags:
        return False
    for m in re.finditer(r"\$effect\s*\(", src):
        arg = _call_arg(src, m.end() - 1)
        if _cond_uses_flag(arg, flags) and any(
            re.search(rf"\b{re.escape(n)}\s*\(", arg) for n in load_names
        ):
            return True
    return False


def _docs_205_ok(dtxt: str) -> bool:
    """Failed timeline / search / doctor scan → Error + Retry on that pane; shell stays."""
    if not dtxt.strip():
        return False
    for m in _DOCS_205_RETRY.finditer(dtxt):
        win = dtxt[max(0, m.start() - 280) : m.end() + 280]
        if not re.search(r"\btimeline\b", win, re.I):
            continue
        if not re.search(r"\bsearch\b", win, re.I):
            continue
        if not re.search(r"\bdoctor\b", win, re.I):
            continue
        if not re.search(r"\b(?:pane|shell)\b", win, re.I):
            continue
        if not re.search(r"\b(?:stay|stays|rest)\b", win, re.I):
            continue
        return True
    return False


def _en_has_retry(en: str) -> bool:
    return bool(re.search(r"\bRetry\b", en)) or bool(_RETRY_COPY.search(en))


def assert_partial_pane_errors(crate: Path) -> None:
    """#205: one pane can fail without blanking the shell.

    Person timeline, search results, and doctor scan each expose Error +
    Retry on a `data-partial` surface. Timeline IPC fail (selectPerson /
    personShow / personConversations / personTimeline) must not paint
    EmptyState “No messages in this view” / “No people yet” / “Select a
    person”, and must not only dump to showErr / the full-width err
    banner. Search api.search fail must not paint “No hits” / “Type a
    query” and must keep q / platform / kind / dates. Doctor doctorIssues
    fail must not paint “No doctor issues” and must stay in-pane (not
    only onError → App banner). Retry is user-clicked, once per click —
    no setInterval / auto-retry / recursive retry; doctor Retry is not
    GC CAS / integrity / rebuild (doctorRun / gcCas). Owned Button for
    Retry is fine. No CDN / HTTP client / updater / network.server /
    sonner (#201/#202 bans stay). Blocking setup errors still use
    showErr / {#if err}. Docs (D24): failed timeline / search / doctor
    scan shows Error + Retry on that pane; the rest of the shell stays.
    Keep #202 EmptyState titles, #203 skeletons, #204 toasts, #137
    sentence, #156 boot spinner, #113 tlLoading-before-pin, #120
    windowing. Search-jump miss (#124) stays showErr — not this issue.
    """
    app_path = crate / "web" / "App.svelte"
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    if not app_path.is_file():
        fail("#205: App.svelte required (person timeline partial Error+Retry)")
    if not search_path.is_file():
        fail("#205: SearchPane.svelte required (search results partial Error+Retry)")
    if not doctor_path.is_file():
        fail("#205: DoctorPane.svelte required (doctor scan partial Error+Retry)")

    app = app_path.read_text()
    search = search_path.read_text()
    doctor = doctor_path.read_text()
    en = _chrome_en_text(crate)
    pkg_path = crate / "package.json"
    pkg = pkg_path.read_text() if pkg_path.is_file() else ""
    svelte_blob = "\n".join(p.read_text() for p in _product_svelte(crate))

    # 1) Three surfaces expose Error + Retry. Grep hook: data-partial.
    app_partials = _hook_element_blocks(app, "data-partial")
    search_partials = _hook_element_blocks(search, "data-partial")
    doctor_partials = _hook_element_blocks(doctor, "data-partial")
    missing: list[str] = []
    if not app_partials:
        missing.append("person timeline")
    if not search_partials:
        missing.append("search results")
    if not doctor_partials:
        missing.append("doctor scan")
    if missing:
        fail(
            "#205: missing data-partial Error+Retry on "
            + ", ".join(missing)
            + " (person timeline / search results / doctor scan each need "
            "data-partial on the Error+Retry surface)"
        )

    surfaces = (
        ("person timeline", app, app_partials, ("selectPerson", "personTimeline")),
        ("search results", search, search_partials, ("run", "search")),
        ("doctor scan", doctor, doctor_partials, ("load", "doctorIssues")),
    )
    for label, src, blocks, _loads in surfaces:
        joined = "\n".join(blocks)
        has_retry = _block_has_retry_copy(joined, en)
        has_error = _block_has_error_copy(joined, en)
        if not has_error or not has_retry:
            fail(
                f"#205: {label} data-partial must show Error + Retry "
                "(user-clicked Retry on that pane)"
            )
        if not any(_retry_click_expr(b) or re.search(r"<(?:Button|button)\b", b) for b in blocks):
            fail(
                f"#205: {label} Retry must be a user-clicked Button / button "
                "(owned Button is fine), not an auto-retry"
            )
        if _PARTIAL_MASCOT.search(joined):
            fail(
                f"#205: {label} data-partial must not use a mascot / "
                "illustration / <img>"
            )

    # 2) Timeline IPC fail — in-pane, not EmptyState, not only showErr.
    tl_catches = _ipc_catch_bodies(
        app,
        "selectPerson",
        ("personShow", "personConversations", "personTimeline"),
    )
    if not tl_catches:
        fail(
            "#205: selectPerson must catch personShow / personConversations / "
            "personTimeline so a fail can show in-pane Error+Retry"
        )
    tl_catch = "\n".join(tl_catches)
    tl_flags = _catch_error_flags(app, tl_catch)
    if _pane_catch_dumps_banner(tl_catch) and not (
        tl_flags and any(_partial_bound_to_flags(app, b, tl_flags) for b in app_partials)
    ):
        fail(
            "#205: selectPerson / personShow / personConversations / "
            "personTimeline fail must not only dump to showErr / the "
            "full-width {#if err} banner"
        )
    if _pane_catch_dumps_banner(tl_catch):
        fail(
            "#205: selectPerson / personShow / personConversations / "
            "personTimeline fail must not write showErr / the full-width "
            "err banner (in-pane Error+Retry only; sandbox / lock stay "
            "on the banner)"
        )
    if not tl_flags:
        fail(
            "#205: selectPerson catch must set an in-pane fail flag for "
            "data-partial Error+Retry (not only showErr)"
        )
    if not any(_partial_bound_to_flags(app, b, tl_flags) for b in app_partials):
        fail(
            "#205: person timeline data-partial must show on selectPerson / "
            "personTimeline fail (bind it to the catch flag)"
        )
    for title in (
        "No messages in this view",
        "No people yet",
        "Select a person",
    ):
        # Sidebar “No people yet” may stay for true empty; the timeline
        # fail surface / exclusive chain must not paint it on this fail.
        if title == "No people yet":
            if any(title in b for b in app_partials):
                fail(
                    "#205: timeline IPC fail must not paint EmptyState "
                    "“No people yet” on the broken pane"
                )
            continue
        if not _empty_exclusive_of_partial(app, title, tl_flags):
            fail(
                "#205: timeline IPC fail must not paint EmptyState "
                f"“{title}” (show data-partial Error+Retry on that fail, "
                "not the true-empty EmptyState)"
            )
    if re.search(r"\bsetup\s*=\s*true\b", tl_catch) or re.search(
        r"\bpeople\s*=\s*\[\s*\]", tl_catch
    ):
        fail(
            "#205: timeline IPC fail must keep nav + people sidebar "
            "(do not set setup = true or clear people)"
        )

    # 3) Search api.search fail — in-pane, keep filters, not EmptyState.
    search_catches = _ipc_catch_bodies(search, "run", ("api.search", ".search("))
    if not search_catches:
        fail(
            "#205: SearchPane run() must catch api.search so a fail can "
            "show in-pane Error+Retry"
        )
    search_catch = "\n".join(search_catches)
    search_flags = _catch_error_flags(search, search_catch)
    if _pane_catch_dumps_banner(search_catch):
        fail(
            "#205: SearchPane api.search fail must not only dump to "
            "onError / showErr / the full-width err banner"
        )
    if not search_flags:
        fail(
            "#205: SearchPane run() catch must set an in-pane fail flag "
            "for data-partial Error+Retry (not only onError)"
        )
    if not any(_partial_bound_to_flags(search, b, search_flags) for b in search_partials):
        fail(
            "#205: search results data-partial must show on api.search fail "
            "(bind it to the catch flag)"
        )
    for title in ("No hits", "Type a query"):
        if not _empty_exclusive_of_partial(search, title, search_flags):
            fail(
                "#205: search api.search fail must not paint EmptyState "
                f"“{title}”"
            )
    if re.search(r"\bempty\s*=\s*true\b", search_catch):
        fail("#205: search api.search fail must not paint EmptyState “No hits”")
    if re.search(r"\bsearched\s*=\s*false\b", search_catch):
        fail("#205: search api.search fail must not paint EmptyState “Type a query”")
    for ident in _SEARCH_FILTER_IDENTS:
        if re.search(
            rf"\b{re.escape(ident)}\s*=\s*(?:[\"']{{2}}|null|undefined)",
            search_catch,
        ):
            fail(
                "#205: search api.search fail must keep q / platform / kind / "
                "dates (do not clear filters on that fail path)"
            )
    if not re.search(r"\bbind:value=\{q\}", search):
        fail("#205: search form must keep q (query) after an api.search fail")
    if not re.search(r"\bbind:value=\{platform\}", search):
        fail("#205: search form must keep platform after an api.search fail")
    if not re.search(r"\bbind:value=\{conversationKind\}", search):
        fail("#205: search form must keep kind after an api.search fail")
    if not re.search(r"\bbind:value=\{from\}", search) or not re.search(
        r"\bbind:value=\{to\}", search
    ):
        fail("#205: search form must keep dates after an api.search fail")

    # 4) Doctor doctorIssues fail — in-pane, not healthy empty, not banner-only.
    doctor_catches = _ipc_catch_bodies(doctor, "load", ("doctorIssues",))
    if not doctor_catches:
        fail(
            "#205: DoctorPane load() must catch doctorIssues so a scan fail "
            "can show in-pane Error+Retry"
        )
    doctor_catch = "\n".join(doctor_catches)
    doctor_flags = _catch_error_flags(doctor, doctor_catch)
    if _pane_catch_dumps_banner(doctor_catch):
        fail(
            "#205: doctorIssues scan fail must not only dump to onError / "
            "App showErr / the full-width err banner"
        )
    if not doctor_flags:
        fail(
            "#205: DoctorPane load() catch must set an in-pane fail flag "
            "for data-partial Error+Retry (not only onError)"
        )
    if not any(_partial_bound_to_flags(doctor, b, doctor_flags) for b in doctor_partials):
        fail(
            "#205: doctor scan data-partial must show on doctorIssues fail "
            "(bind it to the catch flag; failure stays on the Doctor pane)"
        )
    if not _empty_exclusive_of_partial(doctor, "No doctor issues", doctor_flags):
        fail(
            "#205: doctorIssues scan fail must not paint EmptyState "
            "“No doctor issues”"
        )

    # 5) Retry is user-clicked, once per click. Doctor Retry is not GC.
    tl_retry = "\n".join(
        _resolve_handler_blob(app, _retry_click_expr(b)) for b in app_partials
    )
    search_retry = "\n".join(
        _resolve_handler_blob(search, _retry_click_expr(b)) for b in search_partials
    )
    doctor_retry = "\n".join(
        _resolve_handler_blob(doctor, _retry_click_expr(b)) for b in doctor_partials
    )
    if _DOCTOR_HEAVY.search(doctor_retry) or (
        _DOCTOR_HEAVY.search("\n".join(doctor_partials))
        and re.search(r"Retry", "\n".join(doctor_partials), re.I)
    ):
        fail(
            "#205: Doctor Retry must re-call load / doctorIssues once — "
            "not doctorRun / gcCas / integrity / rebuild"
        )
    if not re.search(r"\b(?:load|doctorIssues)\b", doctor_retry + "\n" + "\n".join(doctor_partials)):
        fail(
            "#205: Doctor Retry must re-call load / doctorIssues once "
            "(not GC CAS / integrity / rebuild)"
        )
    if _catch_auto_retries(tl_catch, ("selectPerson", "personShow", "personTimeline")):
        fail(
            "#205: Retry must be user-clicked, once per click "
            "(no setInterval / auto-retry / recursive retry that hammers "
            "a locked archive)"
        )
    if _catch_auto_retries(search_catch, ("run", "search")):
        fail(
            "#205: Retry must be user-clicked, once per click "
            "(no setInterval / auto-retry / recursive retry that hammers "
            "a locked archive)"
        )
    if _catch_auto_retries(doctor_catch, ("load", "doctorIssues", "doctorRun")):
        fail(
            "#205: Retry must be user-clicked, once per click "
            "(no setInterval / auto-retry / recursive retry that hammers "
            "a locked archive)"
        )
    if (
        _interval_retries(app, ("selectPerson", "personTimeline", "personShow"))
        or _interval_retries(search, ("run", "search"))
        or _interval_retries(doctor, ("load", "doctorIssues", "doctorRun"))
    ):
        fail(
            "#205: Retry must be user-clicked, once per click "
            "(no setInterval / auto-retry loop that hammers a locked archive)"
        )
    if (
        _effect_auto_retries(app, tl_flags, ("selectPerson", "personTimeline"))
        or _effect_auto_retries(search, search_flags, ("run",))
        or _effect_auto_retries(doctor, doctor_flags, ("load", "doctorIssues"))
    ):
        fail(
            "#205: Retry must be user-clicked, once per click "
            "(no $effect auto-retry that hammers a locked archive)"
        )
    for label, blob in (
        ("person timeline", tl_retry),
        ("search results", search_retry),
        ("doctor scan", doctor_retry),
    ):
        if _AUTO_RETRY_TIMER.search(blob):
            fail(
                f"#205: {label} Retry must be once per click "
                "(no setInterval in the Retry handler)"
            )

    # 6) Shell stays. Blocking setup errors still use the banner.
    if not re.search(r"<nav\b", app):
        fail("#205: nav must stay (timeline / search / doctor pane fail is in-pane)")
    if "data-people-sidebar" not in app:
        fail(
            "#205: people sidebar must stay on a timeline IPC fail "
            "(do not require the people list to unmount)"
        )
    if not re.search(r"\bfunction\s+showErr\b|\bshowErr\s*=", app):
        fail(
            "#205: keep showErr / {#if err} for sandbox #137, lock, and "
            "not-an-archive (do not ban showErr globally)"
        )
    err_branch = _svelte_if_true_branch(app, "err")
    if not err_branch or not re.search(r"\{err\}", err_branch):
        fail(
            "#205: keep the in-page {#if err} banner for sandbox #137 / lock / "
            "not-an-archive (pane fails are in-pane; blocking setup stays here)"
        )
    # Search-jump miss (#124) stays showErr — not this issue (IN.md).
    jump = _ident_body(app, "openPersonAtMessage")
    if jump and "showErr" not in jump:
        fail(
            "#205: openPersonAtMessage must still contain showErr "
            "(#124 miss path)"
        )

    # 7) No CDN / HTTP client / updater / network.server / sonner.
    #    Do not weaken #201/#202 package bans.
    if _TOAST_SONNER_PKG.search(pkg):
        fail("#205: do not add sonner — #201/#202 package bans stay")
    if _HTTP_CLIENT_PKG.search(pkg):
        fail("#205: not in scope — no HTTP client")
    chrome = _web_chrome_blob(crate)
    if _PARTIAL_CDN.search("\n".join(app_partials + search_partials + doctor_partials)):
        fail("#205: data-partial Error+Retry must not load a CDN / network client")
    if _TOAST_CDN.search(chrome) or _TOAST_CDN.search(svelte_blob):
        fail("#205: no CDN toast / HTTP client kit on the partial surfaces")
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    if "tauri-plugin-http" in toml or "tauri-plugin-updater" in toml:
        fail("#205: not in scope — no HTTP client / updater")
    ent_path = crate / "Interlace.entitlements"
    if ent_path.is_file() and "network.server" in ent_path.read_text():
        fail("#205: entitlements must omit network.server")

    # 8) D24: failed timeline / search / doctor scan → Error + Retry; shell stays.
    #    Do not require dropping the #137 sentence or #204 toast lines.
    dtxt = _typo_docs_blob()
    if not dtxt.strip():
        fail(
            "#205: docs/user/app.md (and/or docs/hacking/tauri.md) required "
            "(failed timeline / search / doctor scan shows Error + Retry "
            "on that pane; the rest of the shell stays)"
        )
    if not _docs_205_ok(dtxt):
        fail(
            "#205: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "a failed timeline / search / doctor scan shows Error + Retry "
            "on that pane and the rest of the shell stays"
        )


def _early_busy_ipc_status(body: str, busy: str, ipc_needles: tuple[str, ...]) -> str:
    """Whether `if (busy) return` actually prevents a second IPC.

    ok: return is before the IPC, busy is set true after that if and
    before the IPC, no await between the if and the set.
    incomplete: an `if (busy)` exists before the IPC but does not prove
    a second call cannot start.
    absent: no such if before the IPC.
    """
    ipc_at = _first_substr_pos(body, ipc_needles)
    if ipc_at < 0:
        return "absent"
    prefix = body[:ipc_at]
    m = re.search(
        rf"if\s*\(\s*{re.escape(busy)}(?:\s*===?\s*true)?\s*\)",
        prefix,
    )
    if not m:
        return "absent"
    i = m.end()
    n = len(body)
    while i < n and body[i] in " \t\n\r":
        i += 1
    if i < n and body[i] == "{":
        close = _match_closer(body, i)
        if close < 0 or close > ipc_at:
            return "incomplete"
        block = body[i + 1 : close]
        if not re.search(r"\breturn\b", block):
            return "incomplete"
        if any(needle in block for needle in ipc_needles):
            return "incomplete"
        if_end = close + 1
    elif body.startswith("return", i):
        if_end = i + len("return")
    else:
        return "incomplete"
    after_if = body[if_end:ipc_at]
    set_m = re.search(rf"\b{re.escape(busy)}\s*=\s*true\b", after_if)
    if not set_m:
        return "incomplete"
    if re.search(r"\bawait\b", after_if[: set_m.start()]):
        return "incomplete"
    return "ok"


def assert_partial_retry_generation(crate: Path) -> None:
    """#205 follow-up: Search run() / Doctor load() must drop stale responses.

    Timeline already sequences personShow / personTimeline with tlGen so a
    stale catch cannot write tlError after a newer success. run() and
    load() must do the same (searchGen / scanGen or equivalent): increment
    at start; catch / success / finally writes to searchError / hits /
    searching / empty and scanError / scanning / issues only apply when
    that gen is current. An early `if (searching) return` /
    `if (scanning) return` is enough only when it actually prevents a
    second IPC (busy set true after the return and before the IPC, no
    await in between). Do not change selectPerson / tlGen. Doctor Retry
    stays load / doctorIssues (existing #205). #124 showErr on
    openPersonAtMessage stays in assert_partial_pane_errors.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    if not search_path.is_file():
        fail(
            "#205: SearchPane.svelte required "
            "(run() must ignore stale search responses)"
        )
    if not doctor_path.is_file():
        fail(
            "#205: DoctorPane.svelte required "
            "(load() must ignore stale doctorIssues responses)"
        )

    search = search_path.read_text()
    doctor = doctor_path.read_text()
    run_body = _without_comments(_ident_body(search, "run"))
    load_body = _without_comments(_ident_body(doctor, "load"))
    if not run_body:
        fail("#205: SearchPane run() required (must ignore stale api.search)")
    if not load_body:
        fail("#205: DoctorPane load() required (must ignore stale doctorIssues)")

    search_ipc = ("api.search",)
    doctor_ipc = ("doctorIssues",)
    search_writes = ("searchError", "hits", "searching", "empty")
    doctor_writes = ("scanError", "scanning", "issues")

    search_early = _early_busy_ipc_status(run_body, "searching", search_ipc)
    if search_early != "ok":
        search_tok = _gen_increment_before_ipc(
            run_body, _first_substr_pos(run_body, search_ipc)
        )
        if search_tok:
            bad = _unguarded_post_ipc_writes(
                run_body, search_tok[0], search_tok[1], search_writes, search_ipc
            )
            if bad:
                fail(
                    "#205: SearchPane run() must not apply a stale catch — "
                    "write searchError / hits / searching only when the "
                    "run() generation is still current"
                )
        elif search_early == "incomplete":
            fail(
                "#205: SearchPane run() if (searching) return does not "
                "prevent a second api.search (set searching = true after "
                "the return and before the IPC, with no await in between "
                "— or use a gen token like tlGen)"
            )
        else:
            fail(
                "#205: SearchPane run() must increment a generation token "
                "(like App tlGen) and only write searchError / hits / "
                "searching when that gen is current (a second overlapping "
                "run() must not let a stale catch win)"
            )

    doctor_early = _early_busy_ipc_status(load_body, "scanning", doctor_ipc)
    if doctor_early != "ok":
        doctor_tok = _gen_increment_before_ipc(
            load_body, _first_substr_pos(load_body, doctor_ipc)
        )
        if doctor_tok:
            bad = _unguarded_post_ipc_writes(
                load_body, doctor_tok[0], doctor_tok[1], doctor_writes, doctor_ipc
            )
            if bad:
                fail(
                    "#205: DoctorPane load() must not apply a stale catch — "
                    "write scanError / scanning / issues only when the "
                    "load() generation is still current"
                )
        elif doctor_early == "incomplete":
            fail(
                "#205: DoctorPane load() if (scanning) return does not "
                "prevent a second doctorIssues (set scanning = true after "
                "the return and before the IPC, with no await in between "
                "— or use a gen token like tlGen)"
            )
        else:
            fail(
                "#205: DoctorPane load() must increment a generation token "
                "(like App tlGen / scanGen) and only write scanError / "
                "scanning / issues when that gen is current (overlapping "
                "Retry / Refresh must not apply a stale catch)"
            )
