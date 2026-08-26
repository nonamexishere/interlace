"""Boot spinner / first-run chrome asserts. Imported by gate_tauri.py."""
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


def _markup_uses_chrome_helper(inner: str, helpers: set[str], logic: str = "") -> bool:
    """True if visible copy comes from t()/chrome.x / a derived chrome label."""
    if not inner.strip():
        return False
    ns = set(helpers) | set(_CHROME_PACK_NS)
    for h in helpers:
        if re.search(rf"\b{re.escape(h)}\s*\(", inner):
            return True
        if re.search(rf"\b{re.escape(h)}\.\w+", inner):
            return True
    for n in ns:
        if re.search(rf"\b{re.escape(n)}\.\w+", inner):
            return True
        if re.search(rf"\b{re.escape(n)}\.\w+\s*\(", inner):
            return True
    if re.search(r"\$_\s*\(", inner):
        return True
    for m in re.finditer(r"\{([A-Za-z_]\w*)\}", inner):
        if _ident_assigned_from_chrome(logic, m.group(1), helpers):
            return True
    return False


def _svelte_open_tag_at(src: str, start: int) -> str:
    """Open tag starting at src[start]=='<', aware of quotes and {…}."""
    n = len(src)
    j = start + 1
    q = None
    brace = 0
    while j < n:
        c = src[j]
        if q:
            if c == q:
                q = None
        elif c in "'\"":
            q = c
        elif c == "{":
            brace += 1
        elif c == "}":
            if brace:
                brace -= 1
        elif c == ">" and brace == 0:
            return src[start : j + 1]
        j += 1
    return src[start : start + 480]


def _app_keydown_body(app: str) -> str:
    """App.svelte window keydown handler (onKey or the listen callback)."""
    m = re.search(
        r"addEventListener\s*\(\s*[\"']keydown[\"']\s*,\s*([A-Za-z_][\w]*)",
        app,
    )
    name = m.group(1) if m else "onKey"
    body = _ts_fn_body(app, name) or _function_body(app, name)
    if body:
        return body
    # Anonymous listener: window.addEventListener("keydown", (e) => { ... })
    anon = re.search(
        r"addEventListener\s*\(\s*[\"']keydown[\"']\s*,\s*(?:async\s*)?\([^)]*\)\s*(?::\s*[^{=]+)?=>\s*\{",
        app,
    )
    if anon:
        open_b = app.find("{", anon.end() - 1)
        if open_b >= 0:
            close_b = _match_closer(app, open_b)
            if close_b > open_b:
                return app[open_b + 1 : close_b]
    return ""


def _review_if_return_conds(body: str) -> list[str]:
    """Conditions of `if (...) return` / `if (...) { return }`."""
    out: list[str] = []
    for m in re.finditer(r"\bif\s*\(", body):
        open_p = m.end() - 1
        close_p = _match_closer(body, open_p)
        if close_p < 0:
            continue
        cond = body[open_p + 1 : close_p]
        rest = body[close_p + 1 :].lstrip()
        if rest.startswith("return"):
            out.append(cond)
            continue
        if rest.startswith("{"):
            open_b = body.find("{", close_p)
            if open_b < 0:
                continue
            close_b = _match_closer(body, open_b)
            if close_b > open_b and re.search(
                r"\breturn\b", body[open_b + 1 : close_b]
            ):
                out.append(cond)
    return out


def _unguarded_post_ipc_writes(
    body: str,
    local: str,
    counter: str,
    writes: tuple[str, ...],
    ipc_needles: tuple[str, ...],
) -> list[str]:
    """Write idents assigned after / as the IPC without a current-gen guard."""
    ipc_at = _first_substr_pos(body, ipc_needles)
    if ipc_at < 0:
        return list(writes)
    bad: list[str] = []
    for ident in writes:
        for m in re.finditer(rf"\b{re.escape(ident)}\s*=(?!=)", body):
            pos = m.start()
            eq = body.find("=", pos)
            rhs = _eq_stmt_rhs(body, eq)
            is_post = pos >= ipc_at or bool(re.search(r"\bawait\b", rhs)) or any(
                n in rhs for n in ipc_needles
            )
            if not is_post:
                continue
            if not _assignment_gen_guarded(body, pos, local, counter):
                bad.append(ident)
                break
    return bad


def _same_block_gen_ne_return(body: str, pos: int, local: str, counter: str) -> bool:
    """True if the same block already did `if (local !== counter) return`."""
    enclosing = 0
    i = 0
    while i < pos:
        nxt = _js_next(body, i)
        if nxt != i:
            i = nxt
            continue
        if body[i] == "{":
            close = _match_closer(body, i)
            if close < 0:
                break
            if close >= pos:
                enclosing = i
                i += 1
            else:
                i = close + 1
            continue
        i += 1
    region = body[enclosing:pos]
    return bool(
        re.search(
            rf"if\s*\(\s*(?:{re.escape(local)}\s*!==?\s*{re.escape(counter)}"
            rf"|{re.escape(counter)}\s*!==?\s*{re.escape(local)})\s*\)"
            r"\s*(?:\{\s*)?return\b",
            region,
        )
    )


def _svelte_if_true_branch(src: str, cond: str) -> str:
    """True-branch of the first {#if …cond…} (stops at {:else} / {/if} depth 1)."""
    m = re.search(rf"\{{#if\s+[^}}]*\b{re.escape(cond)}\b[^}}]*\}}", src)
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
                return src[m.start() : m.end() + i]
            i += 3
            continue
        if depth == 1 and (
            rest.startswith("{:else", i)
            or rest.startswith("{:then", i)
            or rest.startswith("{:catch", i)
        ):
            return src[m.start() : m.end() + i]
        i += 1
    return src[m.start() :]


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


def assert_boot_spinner(crate: Path) -> None:
    """#156: centered CSS spinner on pre-JS splash and Opening-last-archive.

    Cold launch must not be a blank page with a corner Loading line. Spinner is
    CSS-only (no network images / CDN). Keep exact copy “Opening last archive”.
    Light/dark aware. Not: splash video, server progress %, people skeleton.
    """
    index = crate / "index.html"
    if not index.is_file():
        fail("#156: crates/interlace-tauri/index.html missing (pre-JS splash)")
    html = index.read_text()
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#156: App.svelte missing (Opening-last-archive boot state)")
    app = app_path.read_text()
    css_blob = "\n".join(
        p.read_text() for p in _web_sources(crate) if p.suffix == ".css"
    )
    boot = _boot_opening_block(app)

    # 1) Pre-JS splash: centered CSS spinner in index.html (inline — Vite CSS
    # loads with JS, so corner text-only “Loading Interlace…” is not enough).
    if _plain_corner_loading(html):
        fail(
            "#156: pre-JS splash must not be a plain corner Loading line — "
            "index.html needs a centered CSS spinner (inline <style> / classes) "
            "plus short status, not only “Loading Interlace…”"
        )
    # Spinner styles for pre-JS must live in index.html itself (not only app.css).
    if not _has_css_spinner(html):
        fail(
            "#156: pre-JS splash (index.html) must include a CSS-only rotating "
            "spinner (@keyframes / animate-spin / border ring) — no network image"
        )
    if not _is_viewport_centered(html):
        fail(
            "#156: pre-JS splash must center the spinner in the viewport "
            "(flex/grid + items/justify center + min-h-screen/full), "
            "not leave status text in the corner"
        )
    if _NET_IMG.search(html) or _CDN_HINT.search(html):
        fail(
            "#156: pre-JS spinner must be CSS-only — no http(s) image URLs or CDN"
        )
    if _SPLASH_VIDEO.search(html):
        fail("#156: no branded splash <video> (out of scope)")

    # 2) Post-mount boot: booting || opening UI — centered spinner + copy.
    if not boot:
        fail(
            "#156: App.svelte must keep a {#if booting || opening} (or opening || booting) "
            "branch for the Opening-last-archive state"
        )
    en_pack = _chrome_en_text(crate)
    boot_has_copy = "Opening last archive" in boot
    pack_has_copy = "Opening last archive" in en_pack
    boot_uses_chrome = _markup_uses_chrome_helper(boot, _chrome_helper_names(_web_logic(crate)))
    if not boot_has_copy and "Opening last archive" not in app:
        if not (pack_has_copy and boot_uses_chrome):
            fail(
                "#156: boot screen must keep the exact copy substring "
                "“Opening last archive” (existing gate string; English default / en pack)"
            )
    if not boot_has_copy:
        if not (pack_has_copy and boot_uses_chrome):
            fail(
                "#156: “Opening last archive” must appear in the booting/opening branch "
                "(literal English, or chrome helper + en pack — default stays English)"
            )
    # Spinner may use Tailwind utilities in the branch and/or shared CSS.
    boot_with_css = boot + "\n" + css_blob
    if not _has_css_spinner(boot) and not (
        _has_css_spinner(boot_with_css) and _SPINNER_NAME.search(boot)
    ):
        # Accept spinner markup in branch that relies on global .spinner / animate-spin CSS.
        if not (
            (_SPINNER_NAME.search(boot) or re.search(r"animate-spin", boot))
            and _SPIN_ANIM.search(boot_with_css)
        ):
            fail(
                "#156: Opening-last-archive state must show a CSS rotating spinner "
                "(animate-spin / @keyframes spin / spinner class), not status text only"
            )
    if not _is_viewport_centered(boot):
        fail(
            "#156: Opening-last-archive state must be viewport-centered "
            "(flex/grid + center + full height), not a left-aligned loading line"
        )
    if _NET_IMG.search(boot) or _CDN_HINT.search(boot):
        fail(
            "#156: boot spinner must not load network images or CDN assets"
        )
    if _SPLASH_VIDEO.search(boot):
        fail("#156: no splash <video> on the Opening-last-archive state")
    if _SERVER_PROGRESS.search(boot):
        fail(
            "#156: boot status must not show server/network progress percent "
            "(out of scope)"
        )

    # 3) Light/dark aware — soft: dark: utilities, prefers-color-scheme, or theme vars.
    theme_blob = html + "\n" + app + "\n" + css_blob
    if not _LIGHT_DARK.search(theme_blob):
        fail(
            "#156: boot chrome must follow light/dark "
            "(dark: classes, prefers-color-scheme, or --color-background/foreground)"
        )


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


def assert_first_run(crate: Path) -> None:
    """#275: first-run is one calm screen, not a form wall.

    Setup: offline / no account, required #region, Create + Open.
    Owner name / emails / phones are not always-visible primary
    fields (disclosure or absent). createArchive still requires
    region and calls api.init; empty optional owner fields OK.
    FileVault / not encrypted; folder picker only; no carousel /
    account / sample cloud archive. Keep #137 sandbox sentence
    and #156 “Opening last archive”. Docs: one first-run screen;
    optional owner fields not required first.
    Do not rewrite #137 / #156 / #274.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#275: App.svelte required (setup / first-run screen)")
    app = app_path.read_text()
    setup = _setup_branch(app)
    if not setup.strip():
        fail(
            "#275: App.svelte must have a setup / first-run branch "
            "({:else if setup} or {#if setup})"
        )
    extra = _setup_mounted_extra(crate, setup)
    extra_m = _svelte_markup(extra) if extra else extra
    surface = setup + ("\n" + extra_m if extra_m else "")
    wall = _strip_setup_disclosures(surface)

    # 1) Form wall — name / emails / phones must not be always-visible
    #    siblings of #region. Disclosure or absent is OK.
    visible = _setup_visible_owner_fields(wall)
    if visible:
        listed = " / ".join(visible)
        fail(
            "#275: setup must not be a form wall — owner "
            f"{listed} "
            "are still always-visible primary fields next to #region; "
            "put them behind a disclosure (`<details>` / More) or leave "
            "them for the inspector"
        )

    # 2) Offline / no account copy on the setup screen.
    if not re.search(r"\boffline\b", surface, re.I):
        fail("#275: setup screen must say this is an offline archive")
    if not re.search(r"\bno account\b", surface, re.I):
        fail("#275: setup screen must say no account")

    # 3) Required phone-region field (#region).
    if not _setup_has_field(surface, "region"):
        fail(
            "#275: setup must have a required phone-region field (#region)"
        )
    if not re.search(r"required|phone-region|ISO", surface, re.I):
        fail(
            "#275: #region must be marked required "
            "(ISO-2 phone-region, no silent default)"
        )

    # 4) Create + Open actions.
    if not re.search(r"\bcreateArchive\b", surface):
        fail("#275: setup must have a Create action (createArchive)")
    if not re.search(r"\bopenPicker\b", surface):
        fail("#275: setup must have an Open action (openPicker)")

    # 5) createArchive still requires region and calls api.init.
    create = _setup_fn(app, extra, "createArchive")
    if not create.strip():
        fail("#275: createArchive required (init still needs a region)")
    if not re.search(r"\bapi\.init\s*\(", create):
        fail("#275: createArchive must call api.init")
    region_required = bool(
        re.search(r"phone-region is required", create, re.I)
        or (
            re.search(r"\bregion\b", create)
            and re.search(r"if\s*\(\s*!", create)
            and re.search(r"\breturn\b", create)
        )
    )
    if not region_required:
        fail(
            "#275: createArchive must require phone-region "
            "(no silent default; empty region errors)"
        )
    if _SETUP_REQUIRE_OWNER.search(create):
        fail(
            "#275: createArchive must not require owner name / emails / "
            "phones — empty or null optional owner fields are OK"
        )
    if not re.search(r"\bapplyStatus\s*\(", create):
        fail("#275: createArchive must applyStatus after api.init (land on People)")

    # 6) FileVault / not encrypted; folder picker only; no carousel /
    #    account / sample cloud archive.
    if not re.search(r"\bFileVault\b", surface):
        fail("#275: setup must keep FileVault (not encrypted at rest)")
    if not re.search(r"not encrypted", surface, re.I):
        fail("#275: setup must keep “not encrypted at rest”")
    open_p = _setup_fn(app, extra, "openPicker")
    pick_src = create + "\n" + open_p + "\n" + surface
    if not re.search(r"\bpickFolder\b|\bpick_folder\b", pick_src):
        fail(
            "#275: Create / Open must use the folder picker "
            "(pickFolder / pick_folder) — no URLs"
        )
    if not re.search(r"folder picker|no URLs", surface, re.I):
        fail("#275: setup must say folder picker only — no URLs")
    if _SETUP_URL_FIELD.search(surface):
        fail("#275: setup must not take an archive URL (folder picker only)")
    if _SETUP_CAROUSEL.search(surface):
        fail("#275: no onboarding carousel (one first-run screen)")
    if _SETUP_ACCOUNT_ACTION.search(surface):
        fail("#275: no account / sign-in on first-run")
    if _SETUP_SAMPLE_CLOUD.search(surface):
        fail("#275: no sample / cloud archive on first-run")

    # 7) Keep #137 sandbox-denied sentence on setup / err.
    #    Keep #156 “Opening last archive”.
    if not _SANDBOX_137.search(app) and "SANDBOX_DENIED" not in app:
        fail(
            "#275: keep the #137 sandbox-denied sentence on setup / err: "
            "macOS blocked that folder. Use Open existing… once so Interlace "
            "can remember it."
        )
    err_branch = _svelte_if_true_branch(app, "err")
    if not err_branch or not re.search(r"\{err\}", err_branch):
        fail(
            "#275: keep the in-page {#if err} banner so the #137 sandbox "
            "sentence can show on setup"
        )
    if "Opening last archive" not in app:
        fail('#275: keep #156 “Opening last archive”')

    # 8) docs/user/app.md — one first-run screen; optional fields not first.
    docs_path = repo_root() / "docs" / "user" / "app.md"
    if not docs_path.is_file():
        fail("#275: docs/user/app.md required (first-run is one screen)")
    docs = docs_path.read_text()
    if not _SETUP_DOC_ONE_SCREEN.search(docs):
        fail(
            "#275: docs/user/app.md must say first-run is one screen "
            "(offline / no account, required region, Create / Open)"
        )
    if not re.search(r"\boffline\b", docs, re.I) or not re.search(
        r"\bno account\b", docs, re.I
    ):
        fail("#275: docs/user/app.md must say offline / no account")
    if not re.search(r"phone-region|required.{0,40}region|region.{0,40}required", docs, re.I):
        fail("#275: docs/user/app.md must say phone-region is required")
    if not re.search(r"create.{0,40}open|open.{0,40}create", docs, re.I):
        fail("#275: docs/user/app.md must say Create / Open")
    if not _SETUP_DOC_OPTIONAL.search(docs):
        fail(
            "#275: docs/user/app.md must say optional owner fields "
            "(name / emails / phones) are not required first"
        )

from tauri_gate.status_toasts import (
    _CDN_HINT,
    _HUE_AMBER,
    _NET_IMG,
    _SERVER_PROGRESS,
    _SPINNER_NAME,
    _assignment_gen_guarded,
    _chrome_helper_names,
    _hue_surface,
)
