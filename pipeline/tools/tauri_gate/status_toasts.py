"""In-flight / recoverable-toast chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _CHROME_HELPER_NAMES,
    _CHROME_IMPORT_SPEC,
    _CHROME_NO_TRANSLATE_FIELDS,
    _DATA_PEOPLE_SIDEBAR,
    _PERSON_PANE_SKIP,
    _SANDBOX_137,
    _ancestor_tags,
    _call_arg,
    _function_body,
    _markup_open_tag,
    _match_closer,
    _open_tag_around,
    _product_svelte,
    _strip_html_comments,
    _ts_function_body,
    _web_logic,
    _web_sources,
    _web_ts_sources,
    _without_comments,
)

from tauri_gate.import_boot import (
    _HUMAN_TIME_HELPERS,
    _if_gen_eq_contains,
    _input_guard_span,
    _owned_imported_names,
    _same_block_gen_ne_return,
    _svelte_if_true_branch,
    _svelte_open_tag_at,
)

_CONTRAST_HSL = re.compile(
    r"hsla?\(\s*(-?[\d.]+)\s*(?:deg)?\s*[,/\s]\s*"
    r"(-?[\d.]+)%\s*[,/\s]\s*(-?[\d.]+)%",
    re.I,
)
_HM_PART = re.compile(
    r"("
    r"getUTCHours"
    r"|getUTCMinutes"
    r"|getHours"
    r"|getMinutes"
    r"|getDate"
    r"|slice\s*\(\s*11\s*,\s*16\s*\)"
    r"|slice\s*\(\s*t\s*\+\s*1\s*,\s*t\s*\+\s*6\s*\)"
    r"|hour\s*:\s*[\"']2-digit[\"']"
    r"|minute\s*:\s*[\"']2-digit[\"']"
    r")",
)
_MOD_CTRL = re.compile(r"(?:e\.)?ctrlKey")
_MOD_META = re.compile(r"(?:e\.)?metaKey")
_NEGATED_SCOPE = re.compile(
    r"\b(?:not|no|never|out of scope|isn't|is not|don't|do not)\b",
    re.I,
)
_PEOPLE_ONLY_RETURN = re.compile(
    r"if\s*\(\s*view\s*!==?\s*[\"']people[\"']\s*\)\s*(?:\{\s*)?return\s*;"
)
_SEARCH_EFFECT = re.compile(r"\$effect(?:\.pre)?\s*\(")
_UTC_FMT = re.compile(
    r"("
    r"getUTC(?:Date|Month|Hours|Minutes|FullYear)"
    r"|timeZone\s*:\s*[\"']UTC[\"']"
    r"|slice\s*\(\s*[\"']T[\"']\s*\)"
    r"|indexOf\s*\(\s*[\"']T[\"']\s*\)"
    r"|\bUTC\b"
    r")",
)


def _chrome_import_names(logic: str) -> set[str]:
    names: set[str] = set()
    for m in re.finditer(
        r"import\s+(?:type\s+)?(?:(\w+)\s*,\s*)?\{([^}]+)\}\s+from\s+[\"']([^\"']+)[\"']",
        logic,
    ):
        if not _CHROME_IMPORT_SPEC.search(m.group(3)):
            continue
        if m.group(1):
            names.add(m.group(1))
        for part in m.group(2).split(","):
            bit = part.strip()
            if not bit or bit.startswith("type "):
                continue
            names.add(re.split(r"\s+as\s+", bit)[-1].strip())
    for m in re.finditer(
        r"import\s+(\w+)\s+from\s+[\"']([^\"']+)[\"']",
        logic,
    ):
        if _CHROME_IMPORT_SPEC.search(m.group(2)):
            names.add(m.group(1))
    for m in re.finditer(
        r"import\s+\*\s+as\s+(\w+)\s+from\s+[\"']([^\"']+)[\"']",
        logic,
    ):
        if _CHROME_IMPORT_SPEC.search(m.group(2)):
            names.add(m.group(1))
    return {n for n in names if n}


def _parse_if_chain(src: str, if_start: int) -> tuple[list[tuple[str, str]], int]:
    """Sibling branches of one {#if}…{/if}. Nested ifs stay inside bodies."""
    head = re.match(r"\{#if\s+([^}]+)\}", src[if_start:])
    if not head:
        return [], if_start
    cond = head.group(1).strip()
    i = if_start + head.end()
    body_start = i
    depth = 1
    branches: list[tuple[str, str]] = []
    n = len(src)
    while i < n:
        if src.startswith("{#if", i) or src.startswith("{#each", i) or src.startswith(
            "{#await", i
        ) or src.startswith("{#key", i):
            depth += 1
            i += 3
            continue
        if src.startswith("{/if}", i):
            depth -= 1
            if depth == 0:
                branches.append((cond, src[body_start:i]))
                return branches, i + 5
            i += 5
            continue
        if src.startswith("{/each}", i) or src.startswith("{/await}", i) or src.startswith(
            "{/key}", i
        ):
            depth -= 1
            i += 3
            continue
        if depth == 1 and src.startswith("{:else if", i):
            branches.append((cond, src[body_start:i]))
            em = re.match(r"\{:else\s+if\s+([^}]+)\}", src[i:])
            if not em:
                i += 1
                continue
            cond = em.group(1).strip()
            i += em.end()
            body_start = i
            continue
        if depth == 1 and src.startswith("{:else}", i):
            branches.append((cond, src[body_start:i]))
            cond = ":else"
            i += len("{:else}")
            body_start = i
            continue
        i += 1
    return branches, i


def _owned_skeleton_names(src: str) -> list[str]:
    return _owned_imported_names(src, "skeleton")


# #203 — quiet muted skeleton on people / timeline / search in-flight.
_SKELETON_HOOK = re.compile(r"\bdata-skeleton\b")


def _hue_surface(text: str) -> str:
    return _without_comments(_strip_html_comments(text))


# #198 — design tokens: no raw hues in product Svelte; chrome uses shadcn + bubbles.
_HUE_AMBER = re.compile(r"\bamber-\d+")


def _has_mod_combo(src: str) -> bool:
    return bool(_MOD_META.search(src) and _MOD_CTRL.search(src))


# #159 — people sidebar: vertical scroll only; long names/previews do not pan sideways.
_PEOPLE_EACH = re.compile(r"\{#each\s+filtered\b")
_CONTRAST_COLOR_SCHEME = re.compile(
    r"(?:^|[,}\s])(?::root|html)(?:\s*,\s*(?:html|body|#app|:root))*\s*\{"
    r"[^}]*color-scheme\s*:\s*light\s+dark\b",
    re.I | re.S,
)


def _cond_code(cond: str) -> str:
    """Drop quoted strings so 'append' inside \"append\" is not a flag."""
    return re.sub(r"""(['\"])(?:\\.|(?!\1).)*\1""", '""', cond)


def _assignment_gen_guarded(body: str, pos: int, local: str, counter: str) -> bool:
    return _if_gen_eq_contains(body, pos, local, counter) or _same_block_gen_ne_return(
        body, pos, local, counter
    )


def _first_substr_pos(body: str, needles: tuple[str, ...]) -> int:
    found = [body.find(n) for n in needles]
    found = [i for i in found if i >= 0]
    return min(found) if found else -1
_WRITE_TEXT = re.compile(
    r"("
    r"navigator\.clipboard\.writeText"
    r"|clipboard\.writeText"
    r")"
)


def _windows_around(src: str, rx: re.Pattern[str], before: int = 280, after: int = 640) -> str:
    return "\n".join(
        src[max(0, m.start() - before) : m.end() + after] for m in rx.finditer(src)
    )
_FOCUS_SEARCH_Q = re.compile(
    r"("
    r"getElementById\s*\(\s*[\"']q[\"']"
    r"|querySelector\s*\(\s*[\"']#q[\"']"
    r")",
)
_KEY_ESC = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']Escape[\"']"
    r"|[\"']Escape[\"']\s*===?\s*(?:e\.)?key"
    r")",
)
_MOTION_DURATION_ZERO = re.compile(
    r"("
    r"\bduration\s*:\s*0\b"
    r"|\bduration\s*=\s*0\b"
    r"|\?\s*0\s*:"
    r")"
)


def _contrast_surface_tag(src: str, hook: str) -> str:
    at = src.find(hook)
    if at < 0:
        return ""
    return _markup_open_tag(src, src.rfind("<", 0, at + 1))


def _hsl_tuple(value: str) -> tuple[float, float, float] | None:
    m = _CONTRAST_HSL.search(value)
    if not m:
        return None
    return float(m.group(1)), float(m.group(2)), float(m.group(3))


def _toml_keys_in_fn(body: str) -> list[str]:
    keys: list[str] = []
    for s in re.findall(r'"(?:[^"\\]|\\.)*"', body):
        keys.extend(re.findall(r"([A-Za-z_][\w]*)\s*=", s))
    return keys
_MONTH_SHORT = re.compile(
    r"("
    r"[\"'](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\"']"
    r"|month\s*:\s*[\"']short[\"']"
    r")",
    re.I,
)


def _without_input_guard(body: str) -> str:
    span = _input_guard_span(body)
    if not span:
        return body
    return body[: span[0]] + body[span[1] + 1 :]
_CDN_HINT = re.compile(
    r"("
    r"cdn\.|unpkg\.com|jsdelivr|googleapis|gstatic|cloudflare"
    r"|fonts\.google"
    r")",
    re.I,
)
_MOTION_JS_REDUCE = re.compile(
    r"("
    r"\bmatchMedia\s*\("
    r"|\bMediaQuery\b"
    r"|\bprefersReducedMotion\b"
    r"|prefers-reduced-motion"
    r")"
)


def _split_people_only(body: str) -> tuple[str, str]:
    """Prefix always runs; suffix only runs on People (`view !== "people" return`)."""
    m = _PEOPLE_ONLY_RETURN.search(body)
    if not m:
        return body, ""
    return body[: m.start()], body[m.end() :]
_SERVER_PROGRESS = re.compile(
    r"("
    r"progress\s*%"
    r"|percent(?:age)?\s*(?:from|via|of)\s*(?:server|network|http)"
    r"|fetch(?:Progress|Percent)"
    r")",
    re.I,
)
_NET_IMG = re.compile(
    r"("
    r"""(?:src|href)\s*=\s*["']https?://"""
    r"""|url\(\s*['"]?https?://"""
    r"""|<img\b[^>]+https?://"""
    r")",
    re.I,
)
_APPEARANCE_DOCS_NO_THEME = re.compile(
    r"("
    r"no(?: in-app)? Theme(?: / Appearance)? menu"
    r"|without (?:a |an )?Theme menu"
    r"|no Theme / Appearance"
    r"|not (?:a |an )?Theme menu"
    r")",
    re.I,
)


def _claim_without_negation(blob: str, rx: re.Pattern[str]) -> bool:
    for m in rx.finditer(blob):
        window = blob[max(0, m.start() - 48) : m.end() + 48]
        if _NEGATED_SCOPE.search(window):
            continue
        return True
    return False


def _people_inflight_branch(src: str) -> tuple[str, str]:
    """Return (flag, {#if flag} true-branch) for the people-list in-flight window."""
    for flag in ("peopleLoading", "loadingPeople", "peopleBusy"):
        block = _svelte_if_true_branch(src, flag)
        if block:
            return flag, block
    return "", ""


def _status_hook_blob(src: str, hook: str) -> str:
    """Opening-tag ancestors plus a short window around a data-* / text hook."""
    at = src.find(hook)
    if at < 0:
        return ""
    tags = _ancestor_tags(src, at, limit=8)
    window = src[max(0, at - 160) : at + 280]
    return "\n".join(tags) + "\n" + window
_APPEARANCE_DOCS_ARCHIVAL = re.compile(
    r"("
    r"dark.{0,100}(?:intended|archival).{0,60}(?:look|aesthetic)"
    r"|(?:intended|archival).{0,40}(?:look|aesthetic).{0,60}dark"
    r"|dark is the intended"
    r"|intended archival"
    r"|archival look"
    r")",
    re.I | re.S,
)
_CONTRAST_DOCS_SYSTEM = re.compile(
    r"("
    r"system (?:light(?:/| and | / )dark|appearance)"
    r"|follows? system (?:light|dark|appearance)"
    r"|macOS appearance"
    r"|prefers-color-scheme"
    r"|light(?:/| and )dark.{0,80}system"
    r")",
    re.I | re.S,
)


def _skeleton_hook_positions(block: str, owned_names: list[str]) -> list[int]:
    pos: list[int] = []
    for m in _SKELETON_HOOK.finditer(block):
        pos.append(m.start())
    for n in owned_names:
        for m in re.finditer(rf"<{re.escape(n)}(?:\.\w+)?\b", block):
            pos.append(m.start())
    return sorted(set(pos))
_DOCS_TYPO_NO_REMOTE_FONT = re.compile(
    r"("
    r"no remote fonts?"
    r"|not (?:a |an )?remote fonts?"
    r"|system(?:-ui| UI)? fonts?"
    r"|no Google Fonts"
    r"|not.{0,48}(?:Google Fonts|fonts\.googleapis|CDN fonts?|remote fonts?)"
    r")",
    re.I,
)


def _payload_has_path_or_url(payload: str) -> bool:
    return bool(
        re.search(
            r"\b(?:path|url|file|href|uri)\s*:|\b(?:path|url|file|href|uri)\b\s*[,}]",
            payload,
            re.I,
        )
    )
_SPINNER_NAME = re.compile(
    r"("
    r"\bspinner\b"
    r"|boot-spinner"
    r"|loading-spinner"
    r"|data-boot-spinner"
    r"|data-spinner"
    r")",
    re.I,
)
_APPEARANCE_THEME_UI = re.compile(
    r"("
    r"\bdata-theme\b"
    r"|theme-picker"
    r"|themePicker"
    r"|ThemePicker"
    r"|Theme menu"
    r"|Appearance menu"
    r")",
    re.I,
)


def _typo_docs_blob() -> str:
    user_docs = repo_root() / "docs" / "user" / "app.md"
    hack_docs = repo_root() / "docs" / "hacking" / "tauri.md"
    dtxt = ""
    if user_docs.is_file():
        dtxt += user_docs.read_text()
    if hack_docs.is_file():
        dtxt += "\n" + hack_docs.read_text()
    return dtxt
_TYPO_REMOTE_FONT = re.compile(
    r"("
    r"fonts\.googleapis"
    r"|fonts\.gstatic"
    r"|use\.typekit\.net"
    r"|fonts\.adobe"
    r"|@import\s+(?:url\s*\(\s*)?['\"]https?://"
    r"|url\s*\(\s*['\"]?https?://[^)]*(?:font|\.woff2?|\.ttf|\.otf)"
    r")",
    re.I,
)
_THEME_CDN = re.compile(
    r"("
    r"fonts\.googleapis"
    r"|fonts\.gstatic"
    r"|cdn\."
    r"|unpkg\.com"
    r"|jsdelivr"
    r"|@import\s+(?:url\s*\(\s*)?['\"]https?://"
    r")",
    re.I,
)


def _invoke_payloads(web: str, rx: re.Pattern[str]) -> list[str]:
    found: list[str] = []
    for m in rx.finditer(web):
        open_p = web.find("(", m.start())
        if open_p < 0:
            continue
        arg = _call_arg(web, open_p)
        if arg:
            found.append(arg)
    return found


def _chrome_helper_names(logic: str) -> set[str]:
    names = _chrome_import_names(logic)
    for name in _CHROME_HELPER_NAMES:
        if re.search(
            rf"(?:function\s+{re.escape(name)}\s*\("
            rf"|(?:const|let)\s+{re.escape(name)}\s*=\s*(?:async\s*)?(?:function\b|\())",
            logic,
        ):
            names.add(name)
    return names
_SECOND_UI_KIT = re.compile(
    r"[\"']("
    r"@radix-ui(?:/[^\"']*)?"
    r"|shadcn(?:-svelte)?"
    r"|@shadcn(?:/[^\"']*)?"
    r"|@skeletonlabs(?:/[^\"']*)?"
    r"|daisyui"
    r"|flowbite(?:-[a-z]+)?"
    r"|@ark-ui(?:/[^\"']*)?"
    r"|melt-ui"
    r")[\"']",
    re.I,
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
