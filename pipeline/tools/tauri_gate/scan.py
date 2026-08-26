"""Shared readers and keep-check tokens for tauri_gate area modules."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)


# IPC-only connect-src (no general http/https). 'none' blanks the .app (#107).
# frame-src data: lets CasPdf load a local casDataUrl iframe; no http(s) frames.
CSP = (
    "default-src 'self'; img-src 'self' asset: data: cas:; media-src 'self' cas: data:; "
    "style-src 'self' 'unsafe-inline'; "
    "connect-src ipc: http://ipc.localhost https://ipc.localhost; "
    "frame-src data:; font-src 'self'"
)
_BUBBLE_ME_VARS = ("--bubble-me", "--color-bubble-me")
_BUBBLE_THEM_VARS = ("--bubble-them", "--color-bubble-them")
_PRE_WRAP = re.compile(
    r"<([a-zA-Z][\w:-]*)([^>]*\bwhitespace-pre-wrap\b[^>]*)>(.*?)</\1>",
    re.S,
)
_SCROLL_HELPER_SKIP = frozenset(
    {
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
        "requestAnimationFrame",
        "setTimeout",
        "setInterval",
        "queueMicrotask",
        "tick",
        "Promise",
        "Math",
        "Number",
        "String",
        "Boolean",
        "parseInt",
        "document",
        "getElementById",
        "querySelector",
        "querySelectorAll",
        "scrollTo",
        "scrollIntoView",
        "showErr",
        "personShow",
        "personTimeline",
        "toReversed",
        "concat",
    }
)
_PRETTY_WHATSAPP = re.compile(r"[\"']WhatsApp[\"']")
_PRETTY_GMAIL = re.compile(r"[\"']Gmail[\"']")
_RAW_WHATSAPP = re.compile(r"[\"']whatsapp[\"']")
_INCLUDE_GROUPS_LABEL = re.compile(r"include groups", re.I)
_TMPL_TOKEN = re.compile(
    r"\{#if\s+([^}]+)\}"
    r"|\{:else\s+if\s+([^}]+)\}"
    r"|\{:else\}"
    r"|\{/if\}"
    r"|\{#each\s+([^}]+)\}"
    r"|\{/each\}"
    r"|\{#await\b[^}]*\}"
    r"|\{/await\}"
    r"|\{#key\b[^}]*\}"
    r"|\{/key\}"
    r"|<((?:[A-Za-z][\w]*\.)?(?:Select|Popover|DropdownMenu|Dropdown|Combobox|Menu)"
    r"(?:\.\w+)?|details|select)\b([^>]*)>"
    r"|</((?:[A-Za-z][\w]*\.)?(?:Select|Popover|DropdownMenu|Dropdown|Combobox|Menu)"
    r"(?:\.\w+)?|details|select)\s*>",
    re.I,
)
_PERSON_PANE_SKIP = frozenset(
    {
        "SearchPane.svelte",
        "ReviewPane.svelte",
        "ImportPane.svelte",
        "DoctorPane.svelte",
        "ConfirmDialog.svelte",
        "EmptyState.svelte",
        "CasAttach.svelte",
    }
)
_VOID_HTML = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
# Names accepted as the person-timeline {#each} source (#111–#113 / #120).
_TIMELINE_EACH_NAMES = (
    "timeline",
    "dayGroups",
    "windowedDayGroups",
    "windowedGroups",
    "visibleDayGroups",
    "visibleGroups",
    "virtualDayGroups",
    "virtualGroups",
    "renderedDayGroups",
    "renderedGroups",
    "windowedRows",
    "visibleRows",
    "virtualRows",
    "renderedRows",
    "windowedTimeline",
    "visibleTimeline",
    "virtualTimeline",
    "renderedTimeline",
    "windowedItems",
    "visibleItems",
    "virtualItems",
)


def _web_sources(crate: Path) -> list[Path]:
    web = crate / "web"
    return [
        p
        for p in sorted(web.rglob("*"))
        if p.suffix in {".svelte", ".css"} and "node_modules" not in p.parts
    ]


def _web_logic(crate: Path) -> str:
    """Svelte + TS sources (helpers may live next to App.svelte)."""
    web = crate / "web"
    parts: list[str] = []
    for p in sorted(web.rglob("*")):
        if p.suffix in {".svelte", ".ts"} and "node_modules" not in p.parts:
            parts.append(p.read_text())
    return "\n".join(parts)


def _timeline_block(crate: Path) -> str:
    found: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte":
            continue
        text = p.read_text()
        i = 0
        while True:
            start = -1
            for name in _TIMELINE_EACH_NAMES:
                idx = text.find(f"{{#each {name}", i)
                if idx >= 0 and (start < 0 or idx < start):
                    start = idx
            if start < 0:
                break
            end = text.find("{/each}", start)
            if end < 0:
                fail(f"#111: unclosed {{#each timeline}} in {p.relative_to(crate)}")
            found.append(text[start:end])
            i = end + len("{/each}")
    if not found:
        fail(
            "#111: person timeline must {#each timeline}, {#each dayGroups}, "
            "or a windowed row list as chat rows"
        )
    return "\n".join(found)


def _css_var(blob: str, names: tuple[str, ...]) -> str | None:
    for name in names:
        m = re.search(rf"{re.escape(name)}\s*:\s*([^;]+);", blob)
        if m:
            return m.group(1).strip()
    return None


def _matching_each_end(markup: str, each_start: int) -> int:
    depth = 0
    for m in re.finditer(r"\{#each\b|\{/each\}", markup[each_start:]):
        if m.group(0).startswith("{#each"):
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return each_start + m.end()
    return -1


def _js_next(src: str, i: int) -> int:
    """Advance past a JS comment or string starting at i; else return i."""
    n = len(src)
    if i >= n:
        return i
    if src.startswith("//", i):
        nl = src.find("\n", i)
        return n if nl < 0 else nl + 1
    if src.startswith("/*", i):
        end = src.find("*/", i + 2)
        return n if end < 0 else end + 2
    q = src[i]
    if q in "'\"`":
        j = i + 1
        while j < n:
            if src[j] == "\\":
                j += 2
                continue
            if src[j] == q:
                return j + 1
            j += 1
        return n
    return i


def _without_comments(src: str) -> str:
    out: list[str] = []
    i = 0
    n = len(src)
    while i < n:
        if src.startswith("//", i) or src.startswith("/*", i):
            i = _js_next(src, i)
            continue
        nxt = _js_next(src, i)
        if nxt != i:
            out.append(src[i:nxt])
            i = nxt
            continue
        out.append(src[i])
        i += 1
    return "".join(out)


def _match_closer(src: str, open_idx: int) -> int:
    opener = src[open_idx]
    closer = ")" if opener == "(" else "}"
    depth = 0
    i = open_idx
    n = len(src)
    while i < n:
        nxt = _js_next(src, i)
        if nxt != i:
            i = nxt
            continue
        c = src[i]
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _call_arg(src: str, open_paren: int) -> str:
    close = _match_closer(src, open_paren)
    if close < 0:
        return ""
    return src[open_paren + 1 : close]


def _function_body(src: str, name: str) -> str:
    rx = re.compile(
        rf"(?:async\s+)?function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{"
        rf"|(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?:async\s*)?"
        rf"(?:function\s*)?\([^)]*\)\s*(?:=>\s*)?\{{"
    )
    m = rx.search(src)
    if not m:
        return ""
    open_b = m.end() - 1
    close_b = _match_closer(src, open_b)
    if close_b < 0:
        return src[open_b + 1 :]
    return src[open_b + 1 : close_b]


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


def _svelte_markup(text: str) -> str:
    end = text.rfind("</script>")
    return text[end:] if end >= 0 else text


def _template_stack(markup: str, pos: int) -> list[tuple[str, str, str]]:
    """Open {#if}/{#each}/compact tags at pos. {:else} is if-else (not a closed gate)."""
    stack: list[tuple[str, str, str]] = []
    for m in _TMPL_TOKEN.finditer(markup):
        if m.start() >= pos:
            break
        tok = m.group(0)
        if tok.startswith("{#if"):
            stack.append(("if", (m.group(1) or "").strip(), ""))
        elif tok.startswith("{:else if"):
            if stack and stack[-1][0] in {"if", "if-else"}:
                stack[-1] = ("if", (m.group(2) or "").strip(), "")
        elif tok.startswith("{:else}"):
            if stack and stack[-1][0] == "if":
                stack[-1] = ("if-else", stack[-1][1], "")
        elif tok.startswith("{/if}"):
            while stack and stack[-1][0] not in {"if", "if-else"}:
                stack.pop()
            if stack:
                stack.pop()
        elif tok.startswith("{#each"):
            stack.append(("each", (m.group(3) or "").strip(), ""))
        elif tok.startswith("{/each}"):
            while stack and stack[-1][0] != "each":
                stack.pop()
            if stack:
                stack.pop()
        elif tok.startswith("{#await") or tok.startswith("{#key"):
            stack.append(("block", tok[:6], ""))
        elif tok.startswith("{/await}") or tok.startswith("{/key}"):
            if stack and stack[-1][0] == "block":
                stack.pop()
        elif tok.startswith("</"):
            name = (m.group(6) or "").lower()
            if stack and stack[-1][0] == "tag" and stack[-1][1].lower() == name:
                stack.pop()
        else:
            stack.append(("tag", (m.group(4) or "").lower(), m.group(5) or ""))
    return stack


def _assigned_idents(expr: str) -> set[str]:
    return set(re.findall(r"\b([A-Za-z_]\w*)\s*=(?!=)", expr))


def _cond_uses_flag(cond: str, flags: set[str]) -> bool:
    return any(re.search(rf"\b{re.escape(f)}\b", cond) for f in flags)


def _open_tag_before(markup: str, pos: int) -> tuple[int, str] | None:
    n = len(markup)
    i = pos
    while i > 0:
        lt = markup.rfind("<", 0, i)
        if lt < 0:
            return None
        if markup.startswith("</", lt) or markup.startswith("<!--", lt):
            i = lt
            continue
        j = lt + 1
        q = None
        brace = 0
        while j < n:
            c = markup[j]
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
                return lt, markup[lt : j + 1]
            j += 1
        return None
    return None


def _ancestor_tags(markup: str, pos: int, limit: int = 4) -> list[str]:
    tags: list[str] = []
    cur = pos
    for _ in range(limit):
        found = _open_tag_before(markup, cur)
        if not found:
            break
        lt, tag = found
        tags.append(tag)
        cur = lt
    return tags


def _tag_name(tag: str) -> str:
    m = re.match(r"</?([A-Za-z][\w:.-]*)", tag)
    return (m.group(1) if m else "").lower()


def _ts_function_body(src: str, name: str) -> str:
    """Body or arrow expression of `name`, including a TS `: ReturnType`."""
    body = _function_body(src, name)
    if body:
        return body
    pats = (
        rf"(?:async\s+)?function\s+{re.escape(name)}\s*\(",
        rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?:async\s+)?function\s*\(",
        rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?:async\s*)?\(",
    )
    for pat in pats:
        m = re.search(pat, src)
        if not m:
            continue
        open_p = m.end() - 1
        if open_p < 0 or src[open_p] != "(":
            continue
        close_p = _match_closer(src, open_p)
        if close_p < 0:
            continue
        i = close_p + 1
        n = len(src)
        while i < n and src[i] in " \t\n":
            i += 1
        if i < n and src[i] == ":":
            i += 1
            depth = 0
            while i < n:
                c = src[i]
                # Depth-0 `{` after a return type is the function body.
                # Do not put `{` in the open-type set before that break.
                if c in "<([":
                    depth += 1
                elif c in ">)]":
                    depth -= 1
                elif depth <= 0 and (src.startswith("=>", i) or c == "{"):
                    break
                i += 1
        while i < n and src[i] in " \t\n":
            i += 1
        if src.startswith("=>", i):
            i += 2
            while i < n and src[i] in " \t\n":
                i += 1
        if i < n and src[i] == "{":
            close_b = _match_closer(src, i)
            return src[i + 1 : close_b] if close_b >= 0 else src[i + 1 :]
        j = i
        depth = 0
        while j < n:
            nxt = _js_next(src, j)
            if nxt != j:
                j = nxt
                continue
            c = src[j]
            if c in "({[":
                depth += 1
            elif c in ")}]":
                if depth == 0:
                    break
                depth -= 1
            elif c in ";,\n" and depth == 0:
                break
            j += 1
        return src[i:j]
    return ""


def _helper_with_callees(src: str, name: str, seen: set[str] | None = None) -> str:
    found = seen if seen is not None else set()
    if name in found:
        return ""
    found.add(name)
    body = _ts_function_body(src, name)
    if not body:
        return ""
    parts = [body]
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", body):
        callee = m.group(1)
        if callee in found or callee in _SCROLL_HELPER_SKIP:
            continue
        nested = _helper_with_callees(src, callee, found)
        if nested:
            parts.append(nested)
    return "\n".join(parts)


# #159 — people sidebar: vertical scroll only; long names/previews do not pan sideways.
_PEOPLE_EACH = re.compile(r"\{#each\s+filtered\b")
_OVERFLOW_X_HIDDEN = re.compile(
    r"("
    r"overflow-x-hidden"
    r"|overflow-x\s*:\s*hidden"
    r"|overflow\s*:\s*hidden\b"
    r")",
    re.I,
)
_MIN_W0 = re.compile(
    r"("
    r"\bmin-w-0\b"
    r"|min-width\s*:\s*0"
    r"|minmax\s*\(\s*0\s*,"
    r")",
    re.I,
)
_DATA_PEOPLE_SIDEBAR = re.compile(r"data-people-sidebar", re.I)


def _people_each_block(markup: str) -> str:
    """Innermost {#each filtered …} body for the people list (not switcher)."""
    m = _PEOPLE_EACH.search(markup)
    if not m:
        return ""
    end = _matching_each_end(markup, m.start())
    if end < 0:
        return markup[m.start() :]
    return markup[m.start() : end]


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


# #156 — cold launch: centered CSS spinner, not a corner Loading line.
_BOOT_IF = re.compile(
    r"\{#if\s+((?:booting|opening)(?:\s*\|\|\s*(?:booting|opening))+)\s*\}",
)
_SPIN_ANIM = re.compile(
    r"("
    r"animate-spin\b"
    r"|@keyframes\s+[\w-]*spin[\w-]*"
    r"|animation\s*:\s*[^;\n}]*\bspin\b"
    r"|animation-name\s*:\s*[\w-]*spin[\w-]*"
    r")",
    re.I,
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
_SPINNER_RING = re.compile(
    r"("
    r"rounded-full"
    r"|border-radius\s*:\s*(?:50%|9999px|999px)"
    r")",
    re.I,
)
_SPINNER_BORDER = re.compile(
    r"("
    r"\bborder(?:-[trblxy])?(?:-\d)?\b"
    r"|border(?:-top|-right|-bottom|-left)?\s*:"
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
_CDN_HINT = re.compile(
    r"("
    r"cdn\.|unpkg\.com|jsdelivr|googleapis|gstatic|cloudflare"
    r"|fonts\.google"
    r")",
    re.I,
)
_SPLASH_VIDEO = re.compile(r"<video\b", re.I)
_SERVER_PROGRESS = re.compile(
    r"("
    r"progress\s*%"
    r"|percent(?:age)?\s*(?:from|via|of)\s*(?:server|network|http)"
    r"|fetch(?:Progress|Percent)"
    r")",
    re.I,
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
_PEOPLE_AWAIT_REFRESH = re.compile(r"await\s+refreshPeople\s*\(")
_PEOPLE_GEN_COUNTER = re.compile(r"people|roster|ppl", re.I)


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


_SHOW_QUOTED = re.compile(
    r"("
    r"Show quoted"
    r"|Show quote"
    r"|Show quotes"
    r"|Expand quoted"
    r"|Expand quote"
    r"|Quoted text"
    r"|showQuoted"
    r"|showQuote"
    r"|quotedExpanded"
    r"|expandQuoted"
    r"|data-show-quoted"
    r")",
    re.I,
)
_HTML_BODY = re.compile(r"\{@html\b")
_LINKIFY_FETCH = re.compile(r"fetch\s*\(\s*[\"']https?://", re.I)


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


def _tauri_rust_sources(crate: Path) -> list[Path]:
    src = crate / "src"
    if not src.is_dir():
        return []
    return [p for p in sorted(src.rglob("*.rs")) if p.is_file()]


def _tauri_rust_blob(crate: Path) -> str:
    return "\n".join(p.read_text() for p in _tauri_rust_sources(crate))


# #131 — UI chrome locale packs (en + tr). Not WA parser packs, not message bodies.
_CHROME_PACK_SUFFIXES = {".json", ".ts", ".toml"}
_CHROME_PACK_DIR_HINTS = frozenset(
    {"locale", "locales", "i18n", "l10n", "chrome", "messages", "strings"}
)
_CHROME_PACK_FILE_HINTS = ("chrome", "i18n", "l10n", "messages", "strings", "locale")
_CHROME_HELPER_NAMES = (
    "t",
    "tt",
    "i18n",
    "i18nT",
    "chromeT",
    "chromeText",
    "chromeString",
    "uiText",
    "uiString",
    "msg",
    "translate",
    "tChrome",
    "chromeMsg",
)
_CHROME_PACK_NS = (
    "chrome",
    "i18n",
    "strings",
    "messages",
    "ui",
    "m",
    "pack",
    "packs",
    "c",
)
_CHROME_NO_TRANSLATE_FIELDS = (
    "body_text",
    "bodyText",
    "snippet",
    "displayBody",
    "searchBody",
    "display_name",
    "displayName",
    "personTitle",
    "preview",
    "sample",
    "sample_body",
    "sampleBody",
)
_CHROME_IMPORT_SPEC = re.compile(
    r"chrome|i18n|l10n|locale|messages|strings|paraglide",
    re.I,
)
_LANG_STEM = re.compile(
    r"(?:^|[._-])(en|tr)(?:[-_][A-Za-z]+)?$",
    re.I,
)


def _looks_like_wa_pack(text: str) -> bool:
    return (
        "you_tokens" in text
        and "media_omitted" in text
        and "file_attached_pattern" in text
    )


def _web_pack_candidates(crate: Path) -> list[Path]:
    web = crate / "web"
    if not web.is_dir():
        return []
    out: list[Path] = []
    for p in sorted(web.rglob("*")):
        if not p.is_file():
            continue
        if "node_modules" in p.parts or "dist" in p.parts:
            continue
        if p.suffix not in _CHROME_PACK_SUFFIXES:
            continue
        if p.name.endswith(".d.ts"):
            continue
        out.append(p)
    return out


def _stem_chrome_lang(path: Path) -> str | None:
    m = _LANG_STEM.search(path.stem)
    if not m:
        return None
    return m.group(1).lower()


def _chrome_file_hinted(path: Path) -> bool:
    name = path.name.lower()
    parent = path.parent.name.lower()
    if parent in _CHROME_PACK_DIR_HINTS:
        return True
    return any(h in name for h in _CHROME_PACK_FILE_HINTS)


def _is_combined_chrome_pack(path: Path, text: str) -> bool:
    if not _chrome_file_hinted(path):
        return False
    if _looks_like_wa_pack(text):
        return False
    has_en = bool(re.search(r"""(?:\ben\b\s*[:=]|["']en["']\s*:)""", text))
    has_tr = bool(re.search(r"""(?:\btr\b\s*[:=]|["']tr["']\s*:)""", text))
    return has_en and has_tr


def _chrome_pack_files(crate: Path) -> tuple[list[Path], list[Path], list[Path]]:
    """Dedicated en files, dedicated tr files, combined en+tr modules under web/."""
    en: list[Path] = []
    tr: list[Path] = []
    combined: list[Path] = []
    for p in _web_pack_candidates(crate):
        text = p.read_text()
        if _looks_like_wa_pack(text):
            continue
        lang = _stem_chrome_lang(p)
        if lang == "en":
            en.append(p)
            continue
        if lang == "tr":
            tr.append(p)
            continue
        if _is_combined_chrome_pack(p, text):
            combined.append(p)
    return en, tr, combined


def _extract_lang_object(text: str, lang: str) -> str:
    for pat in (
        rf"(?:export\s+)?(?:const|let|var)\s+{re.escape(lang)}\s*=\s*\{{",
        rf"[\"']{re.escape(lang)}[\"']\s*:\s*\{{",
        rf"\b{re.escape(lang)}\s*:\s*\{{",
    ):
        m = re.search(pat, text)
        if not m:
            continue
        brace = text.find("{", m.start())
        if brace < 0:
            continue
        end = _match_closer(text, brace)
        if end > brace:
            return text[brace : end + 1]
    m = re.search(rf"^\[{re.escape(lang)}\]\s*$", text, re.M)
    if m:
        rest = text[m.end() :]
        nxt = re.search(r"^\[", rest, re.M)
        return rest[: nxt.start()] if nxt else rest
    return ""


def _chrome_lang_text(crate: Path, lang: str) -> str:
    en, tr, combined = _chrome_pack_files(crate)
    dedicated = en if lang == "en" else tr
    parts = [p.read_text() for p in dedicated]
    for p in combined:
        text = p.read_text()
        extracted = _extract_lang_object(text, lang)
        parts.append(extracted if extracted.strip() else text)
    return "\n".join(parts)


def _chrome_en_text(crate: Path) -> str:
    return _chrome_lang_text(crate, "en")


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


def _ident_assigned_from_chrome(logic: str, ident: str, helpers: set[str]) -> bool:
    if not ident or ident in {"#if", ":else", "/if", "#each", "/each"}:
        return False
    ns = set(helpers) | set(_CHROME_PACK_NS)
    for m in re.finditer(
        rf"(?:const|let|var)\s+{re.escape(ident)}\s*=",
        logic,
    ):
        window = logic[m.start() : m.start() + 500]
        if any(re.search(rf"\b{re.escape(h)}\s*\(", window) for h in helpers):
            return True
        if any(re.search(rf"\b{re.escape(n)}\.\w+", window) for n in ns):
            return True
    return False


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
_KEY_ESC = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']Escape[\"']"
    r"|[\"']Escape[\"']\s*===?\s*(?:e\.)?key"
    r")",
)
_MOD_META = re.compile(r"(?:e\.)?metaKey")
_MOD_CTRL = re.compile(r"(?:e\.)?ctrlKey")
_MOD_EITHER = re.compile(r"(?:e\.)?(?:metaKey|ctrlKey)")
_FOCUS_SEARCH_Q = re.compile(
    r"("
    r"getElementById\s*\(\s*[\"']q[\"']"
    r"|querySelector\s*\(\s*[\"']#q[\"']"
    r")",
)
_VIEW_SEARCH_ASSIGN = re.compile(r"\bview\s*=\s*[\"']search[\"']")
_PEOPLE_ONLY_RETURN = re.compile(
    r"if\s*\(\s*view\s*!==?\s*[\"']people[\"']\s*\)\s*(?:\{\s*)?return\s*;"
)
_KEYMAP_CALL_SKIP = _SCROLL_HELPER_SKIP | frozenset(
    {
        "preventDefault",
        "stopPropagation",
        "blur",
        "focus",
        "getElementById",
        "querySelector",
        "querySelectorAll",
        "addEventListener",
        "removeEventListener",
        "toLowerCase",
        "toUpperCase",
        "includes",
        "indexOf",
        "startsWith",
        "endsWith",
        "trim",
        "slice",
        "charAt",
        "charCodeAt",
        "fromCharCode",
        "Number",
        "String",
        "Boolean",
        "parseInt",
        "parseFloat",
        "isNaN",
        "ensureTlIndexVisible",
        "nearestVisibleTlIndex",
        "console",
        "Error",
        "Map",
        "Set",
        "Array",
        "Object",
        "JSON",
        "Date",
        "RegExp",
    }
)


def _ts_fn_body(src: str, name: str) -> str:
    """Body of `function name(` / `const name = (` including a TS return type."""
    rx = re.compile(
        rf"(?:async\s+)?function\s+{re.escape(name)}\s*\("
        rf"|(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?:async\s*)?(?:function\s*)?\("
    )
    m = rx.search(src)
    if not m:
        return ""
    open_paren = m.end() - 1
    close_paren = _match_closer(src, open_paren)
    if close_paren < 0:
        return ""
    brace = src.find("{", close_paren)
    if brace < 0:
        return ""
    # Ignore a `{` that belongs to a following function if `=> expr` has no block.
    between = src[close_paren + 1 : brace]
    if "\nfunction" in between or re.search(r"\n\s*(?:const|let|var)\s+\w+", between):
        return ""
    close_b = _match_closer(src, brace)
    if close_b < 0:
        return src[brace + 1 :]
    return src[brace + 1 : close_b]


def _expand_fn_calls(src: str, body: str, depth: int = 2) -> str:
    """Include named callees so ⌘F / tab helpers still count."""
    chunks = [body]
    seen: set[str] = set()

    def walk(blob: str, left: int) -> None:
        for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob):
            if name in seen or name in _KEYMAP_CALL_SKIP:
                continue
            seen.add(name)
            inner = _ts_fn_body(src, name) or _function_body(src, name)
            if not inner:
                continue
            chunks.append(inner)
            if left > 0:
                walk(inner, left - 1)

    walk(body, depth)
    return "\n".join(chunks)


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


def _split_people_only(body: str) -> tuple[str, str]:
    """Prefix always runs; suffix only runs on People (`view !== "people" return`)."""
    m = _PEOPLE_ONLY_RETURN.search(body)
    if not m:
        return body, ""
    return body[: m.start()], body[m.end() :]


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


def _without_input_guard(body: str) -> str:
    span = _input_guard_span(body)
    if not span:
        return body
    return body[: span[0]] + body[span[1] + 1 :]


def _windows_around(src: str, rx: re.Pattern[str], before: int = 280, after: int = 640) -> str:
    return "\n".join(
        src[max(0, m.start() - before) : m.end() + after] for m in rx.finditer(src)
    )


def _has_mod_combo(src: str) -> bool:
    return bool(_MOD_META.search(src) and _MOD_CTRL.search(src))


# #133 — a11y: people listbox, timeline article/label, focus-visible, reduced motion.
_A11Y_ROLE_LISTBOX = re.compile(r"\brole\s*=\s*[\"']listbox[\"']", re.I)
_A11Y_ROLE_OPTION = re.compile(r"\brole\s*=\s*[\"']option[\"']", re.I)
_A11Y_TABINDEX_NEG = re.compile(r"\btabindex\s*=\s*(?:[\"']-1[\"']|\{-1\})", re.I)


def _strip_html_comments(src: str) -> str:
    return re.sub(r"<!--.*?-->", "", src, flags=re.S)


def _css_without_comments(src: str) -> str:
    return re.sub(r"/\*.*?\*/", "", src, flags=re.S)


def _people_list_a11y_surfaces(crate: Path) -> tuple[str, str]:
    """Chrome around `{#each filtered}` plus the each body (not SearchPane)."""
    chromes: list[str] = []
    bodies: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        text = p.read_text()
        markup = _strip_html_comments(_svelte_markup(text))
        if not _PEOPLE_EACH.search(markup):
            markup = _strip_html_comments(text)
        for m in _PEOPLE_EACH.finditer(markup):
            end = _matching_each_end(markup, m.start())
            if end < 0:
                end = min(len(markup), m.start() + 1600)
            chromes.append(markup[max(0, m.start() - 700) : end])
            bodies.append(markup[m.start() : end])
    return "\n".join(chromes), "\n".join(bodies)


def _open_tag_around(src: str, hook: str) -> str:
    m = re.search(rf"<[^>]*{hook}[^>]*>", src, re.I | re.S)
    return m.group(0) if m else ""
_FETCH_CALL = re.compile(r"\bfetch\s*\(")


def _web_ts_sources(crate: Path) -> list[Path]:
    web = crate / "web"
    if not web.is_dir():
        return []
    return [
        p
        for p in sorted(web.rglob("*"))
        if p.suffix in {".svelte", ".ts", ".js"} and "node_modules" not in p.parts
    ]
_WRITE_TEXT = re.compile(
    r"("
    r"navigator\.clipboard\.writeText"
    r"|clipboard\.writeText"
    r")"
)
_PLUGIN_SHELL = re.compile(
    r"("
    r"tauri-plugin-shell"
    r"|tauri-plugin-opener"
    r"|@tauri-apps/plugin-shell"
    r"|@tauri-apps/plugin-opener"
    r"|plugin-shell"
    r"|plugin-opener"
    r"|plugin_shell"
    r"|plugin_opener"
    r")",
    re.I,
)
_SHELL_CAP = re.compile(
    r"("
    r"shell:allow-execute"
    r"|shell:allow-open"
    r"|shell:default"
    r"|opener:allow-open"
    r"|opener:allow-reveal"
    r"|opener:default"
    r")"
)
_ARBITRARY_SHELL = re.compile(
    r"Command::new\s*\(\s*[\"'](?:/bin/sh|/bin/bash|/bin/zsh|/usr/bin/env|sh|bash|zsh|cmd)[\"']"
)
_RUST_CALL_SKIP = frozenset(
    {
        "Ok",
        "Err",
        "Some",
        "None",
        "vec",
        "format",
        "println",
        "eprintln",
        "dbg",
        "Command",
        "Path",
        "PathBuf",
        "String",
        "Vec",
        "Result",
        "Option",
        "drop",
        "clone",
        "lock",
        "map_err",
        "ok_or",
        "ok_or_else",
        "canonicalize",
        "starts_with",
        "join",
        "spawn",
        "output",
        "status",
        "arg",
        "args",
        "new",
        "from",
        "into",
        "as_ref",
        "as_str",
        "to_string",
        "to_owned",
        "expect",
        "unwrap",
        "if",
        "for",
        "while",
        "loop",
        "match",
        "return",
        "Box",
        "Arc",
        "Mutex",
        "State",
        "fs",
        "File",
        "OpenOptions",
    }
)


def _rust_next(src: str, i: int) -> int:
    """Advance past a Rust comment or string starting at i; else return i."""
    n = len(src)
    if i >= n:
        return i
    if src.startswith("//", i):
        nl = src.find("\n", i)
        return n if nl < 0 else nl + 1
    if src.startswith("/*", i):
        end = src.find("*/", i + 2)
        return n if end < 0 else end + 2
    raw = re.match(r"(?:[bc])?r(#*)\"", src[i:])
    if raw:
        hashes = raw.group(1)
        start = i + raw.end()
        needle = '"' + hashes
        end = src.find(needle, start)
        return n if end < 0 else end + len(needle)
    if src[i] == '"' or (i + 1 < n and src[i] in "bc" and src[i + 1] == '"'):
        j = i + 1 if src[i] == '"' else i + 2
        while j < n:
            if src[j] == "\\":
                j += 2
                continue
            if src[j] == '"':
                return j + 1
            j += 1
        return n
    if src[i] == "'":
        if i + 1 < n and (src[i + 1].isalpha() or src[i + 1] == "_"):
            j = i + 2
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            if j < n and src[j] == "'" and j == i + 2:
                return j + 1
            return j
        j = i + 1
        if j < n and src[j] == "\\":
            j += 2
        elif j < n:
            j += 1
        if j < n and src[j] == "'":
            return j + 1
        return j
    return i


def _rust_match_delim(src: str, open_idx: int) -> int:
    pairs = {"(": ")", "{": "}", "[": "]", "<": ">"}
    opener = src[open_idx]
    closer = pairs.get(opener)
    if not closer:
        return -1
    depth = 0
    i = open_idx
    n = len(src)
    while i < n:
        nxt = _rust_next(src, i)
        if nxt != i:
            i = nxt
            continue
        c = src[i]
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _rust_function_body(src: str, name: str) -> str:
    """Body of `fn name` (Rust). Do not use the JS `_function_body` here."""
    m = re.search(
        rf"(?:pub\s+)?(?:async\s+)?fn\s+{re.escape(name)}\b",
        src,
    )
    if not m:
        return ""
    i = m.end()
    n = len(src)
    while i < n:
        nxt = _rust_next(src, i)
        if nxt != i:
            i = nxt
            continue
        if src[i] == "(":
            break
        i += 1
    else:
        return ""
    close_p = _rust_match_delim(src, i)
    if close_p < 0:
        return ""
    i = close_p + 1
    while i < n:
        nxt = _rust_next(src, i)
        if nxt != i:
            i = nxt
            continue
        if src[i] == "{":
            close_b = _rust_match_delim(src, i)
            if close_b < 0:
                return src[i + 1 :]
            return src[i + 1 : close_b]
        i += 1
    return ""


def _rust_fn_signature(src: str, name: str) -> str:
    """Parameter list of `fn name`, including the wrapping parens."""
    m = re.search(
        rf"(?:pub\s+)?(?:async\s+)?fn\s+{re.escape(name)}\b",
        src,
    )
    if not m:
        return ""
    i = m.end()
    n = len(src)
    while i < n:
        nxt = _rust_next(src, i)
        if nxt != i:
            i = nxt
            continue
        if src[i] == "(":
            close_p = _rust_match_delim(src, i)
            if close_p < 0:
                return src[i:]
            return src[i : close_p + 1]
        i += 1
    return ""


def _rust_call_arg(src: str, open_paren: int) -> str:
    close = _rust_match_delim(src, open_paren)
    if close < 0:
        return ""
    return src[open_paren + 1 : close]


def _rust_body_with_callees(src: str, name: str, depth: int = 2) -> str:
    body = _rust_function_body(src, name)
    if not body:
        return ""
    parts = [body]
    seen = {name}

    def walk(blob: str, left: int) -> None:
        if left <= 0:
            return
        for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob):
            callee = m.group(1)
            if callee in seen or callee in _RUST_CALL_SKIP:
                continue
            seen.add(callee)
            inner = _rust_function_body(src, callee)
            if not inner:
                continue
            parts.append(inner)
            walk(inner, left - 1)

    walk(body, depth)
    return "\n".join(parts)


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


def _payload_has_path_or_url(payload: str) -> bool:
    return bool(
        re.search(
            r"\b(?:path|url|file|href|uri)\s*:|\b(?:path|url|file|href|uri)\b\s*[,}]",
            payload,
            re.I,
        )
    )


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
_MONTH_SHORT = re.compile(
    r"("
    r"[\"'](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\"']"
    r"|month\s*:\s*[\"']short[\"']"
    r")",
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
_UTC_FMT = re.compile(
    r"("
    r"getUTC(?:Date|Month|Hours|Minutes|FullYear)"
    r"|timeZone\s*:\s*[\"']UTC[\"']"
    r"|split\s*\(\s*[\"']T[\"']\s*\)"
    r"|indexOf\s*\(\s*[\"']T[\"']\s*\)"
    r"|\bUTC\b"
    r")",
)
_BODY_T_CALL = re.compile(
    r"\bt\s*\(\s*(?:[\w.$]+\.)?(?:body_text|bodyText|preview|snippet|displayBody)\b"
)


def _svelte_interpolations(src: str) -> list[str]:
    """Inner text of `{…}` markup interpolations (not {#if} / {:else} / {@const})."""
    out: list[str] = []
    i = 0
    n = len(src)
    while i < n:
        j = src.find("{", i)
        if j < 0:
            break
        nxt = src[j + 1 : j + 3]
        if nxt[:1] in {"#", "/", ":", "@"}:
            i = j + 1
            continue
        end = _match_closer(src, j)
        if end < 0:
            break
        out.append(src[j + 1 : end])
        i = end + 1
    return out


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


# #198 — design tokens: no raw hues in product Svelte; chrome uses shadcn + bubbles.
_HUE_AMBER = re.compile(r"\bamber-\d+")
_HUE_YELLOW = re.compile(r"\byellow-\d+")
_HUE_BLACK80 = re.compile(r"\bblack/80\b")
# Hex as a color: Tailwind arbitrary `bg-[#111]` or a CSS color property.
# Do not treat `{#each}`, `#person-timeline`, `#{e.id}`, or issue `#198` as hex.
_HUE_HEX_TW = re.compile(
    r"(?:bg|text|border|ring|from|to|via|outline|fill|stroke|decoration|"
    r"divide|accent|caret|shadow)-\[#[0-9A-Fa-f]{3,8}"
)
_HUE_HEX_CSS = re.compile(
    r"(?:background(?:-color)?|color|border(?:-color)?|outline-color|"
    r"fill|stroke|accent-color|caret-color|text-decoration-color)\s*:\s*"
    r"#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})\b",
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


def _product_svelte(crate: Path) -> list[Path]:
    web = crate / "web"
    return [
        p
        for p in sorted(web.rglob("*.svelte"))
        if "node_modules" not in p.parts
    ]


def _hue_surface(text: str) -> str:
    return _without_comments(_strip_html_comments(text))


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
_TYPO_FONT_SANS = re.compile(r"--font-sans\s*:\s*([^;]+);")
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


def _typo_docs_blob() -> str:
    user_docs = repo_root() / "docs" / "user" / "app.md"
    hack_docs = repo_root() / "docs" / "hacking" / "tauri.md"
    dtxt = ""
    if user_docs.is_file():
        dtxt += user_docs.read_text()
    if hack_docs.is_file():
        dtxt += "\n" + hack_docs.read_text()
    return dtxt
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
_CMD_PALETTE_PKG = re.compile(r"[\"'](?:cmdk|svelte-command(?:-palette)?)[\"']", re.I)
_TOAST_SONNER_PKG = re.compile(r"[\"'](?:sonner|svelte-sonner)[\"']", re.I)


def _owned_import_path_rx(name: str) -> str:
    return (
        r"[\"'](?:\$lib/|(?:\.\.?/)*)(?:lib/)?"
        rf"components/ui/{re.escape(name)}"
        r"(?:/[^\"']*)?[\"']"
    )


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


def _empty_state_local_names(src: str) -> list[str]:
    names = ["EmptyState"]
    for m in re.finditer(
        r"import\s+(\w+)\s+from\s+[\"'][^\"']*EmptyState\.svelte[\"']",
        src,
    ):
        names.append(m.group(1))
    return list(dict.fromkeys(names))


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


# #203 — quiet muted skeleton on people / timeline / search in-flight.
_SKELETON_HOOK = re.compile(r"\bdata-skeleton\b")


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


def _people_inflight_branch(src: str) -> tuple[str, str]:
    """Return (flag, {#if flag} true-branch) for the people-list in-flight window."""
    for flag in ("peopleLoading", "loadingPeople", "peopleBusy"):
        block = _svelte_if_true_branch(src, flag)
        if block:
            return flag, block
    return "", ""


def _owned_skeleton_names(src: str) -> list[str]:
    return _owned_imported_names(src, "skeleton")


def _cond_code(cond: str) -> str:
    """Drop quoted strings so 'append' inside \"append\" is not a flag."""
    return re.sub(r"""(['\"])(?:\\.|(?!\1).)*\1""", '""', cond)


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


def _skeleton_hook_positions(block: str, owned_names: list[str]) -> list[int]:
    pos: list[int] = []
    for m in _SKELETON_HOOK.finditer(block):
        pos.append(m.start())
    for n in owned_names:
        for m in re.finditer(rf"<{re.escape(n)}(?:\.\w+)?\b", block):
            pos.append(m.start())
    return sorted(set(pos))
_SANDBOX_137 = re.compile(
    r"macOS blocked that folder\.\s*Use Open existing"
    r"(?:\u2026|\.\.\.|…)\s*once so Interlace can remember it\."
)


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


def _hook_element_blocks(src: str, hook: str) -> list[str]:
    """Each element that carries `hook` (e.g. data-partial) including children."""
    out: list[str] = []
    for m in re.finditer(rf"\b{re.escape(hook)}\b", src):
        i = m.start()
        while i > 0 and src[i] != "<":
            i -= 1
        if src[i] != "<":
            continue
        block = _element_block_at(src, i)
        if block and hook in block:
            out.append(block)
    # Dedup overlapping / identical slices.
    seen: set[str] = set()
    uniq: list[str] = []
    for b in out:
        if b not in seen:
            seen.add(b)
            uniq.append(b)
    return uniq


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


_PANE_RESULT_WRITES = frozenset(
    {
        "searchError",
        "hits",
        "searching",
        "empty",
        "scanError",
        "scanning",
        "issues",
    }
)


def _first_substr_pos(body: str, needles: tuple[str, ...]) -> int:
    found = [body.find(n) for n in needles]
    found = [i for i in found if i >= 0]
    return min(found) if found else -1


def _eq_stmt_rhs(body: str, eq_idx: int) -> str:
    """RHS of `ident = …` starting at the `=`."""
    if eq_idx < 0 or eq_idx >= len(body) or body[eq_idx] != "=":
        return ""
    i = eq_idx + 1
    if i < len(body) and body[i] == "=":
        return ""
    n = len(body)
    depth = 0
    j = i
    while j < n:
        nxt = _js_next(body, j)
        if nxt != j:
            j = nxt
            continue
        c = body[j]
        if c in "({[":
            depth += 1
        elif c in ")}]":
            if depth == 0:
                break
            depth -= 1
        elif c in ";," and depth == 0:
            break
        elif c == "\n" and depth == 0:
            break
        j += 1
    return body[i:j]


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


def _assignment_gen_guarded(body: str, pos: int, local: str, counter: str) -> bool:
    return _if_gen_eq_contains(body, pos, local, counter) or _same_block_gen_ne_return(
        body, pos, local, counter
    )


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


def _tag_name(tag: str) -> str:
    m = re.match(r"</?([A-Za-z][\w:.-]*)", tag)
    return m.group(1) if m else ""


# #208 — always-available chrome search field (not only the Search tab).
_CHROME_SEARCH_HOOK = re.compile(r"\bdata-chrome-search\b", re.I)
_NEGATED_SCOPE = re.compile(
    r"\b(?:not|no|never|out of scope|isn't|is not|don't|do not)\b",
    re.I,
)


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


def _claim_without_negation(blob: str, rx: re.Pattern[str]) -> bool:
    for m in rx.finditer(blob):
        window = blob[max(0, m.start() - 48) : m.end() + 48]
        if _NEGATED_SCOPE.search(window):
            continue
        return True
    return False


# #270 — search-as-you-type without hitching on people refresh.
_SEARCH_EFFECT = re.compile(r"\$effect(?:\.pre)?\s*\(")
_FETCH_CALL = re.compile(r"\bfetch\s*\(")


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


def _opening_tag(markup: str, pos: int) -> str:
    start = markup.rfind("<", 0, pos + 1)
    if start < 0:
        return ""
    end = markup.find(">", start)
    if end < 0:
        return markup[start:]
    return markup[start : end + 1]


def _tag_name(tag: str) -> str:
    m = re.match(r"</?([A-Za-z][\w-]*)", tag)
    return m.group(1) if m else ""


def _matched_inner(markup: str, open_pos: int) -> str:
    m = re.match(r"<([A-Za-z][\w-]*)\b", markup[open_pos:])
    if not m:
        return ""
    name = m.group(1)
    gt = markup.find(">", open_pos)
    if gt < 0:
        return ""
    if markup[gt - 1] == "/":
        return ""
    depth = 1
    rx = re.compile(rf"</?{re.escape(name)}\b", re.I)
    for mm in rx.finditer(markup, gt + 1):
        if mm.group(0).startswith("</"):
            depth -= 1
            if depth == 0:
                return markup[gt + 1 : mm.start()]
        else:
            depth += 1
    return markup[gt + 1 : min(len(markup), gt + 1 + 8000)]
_LS_CALL = re.compile(
    r"localStorage\s*\.\s*(?:getItem|setItem)\s*\(\s*"
    r"(?:"
    r"(?P<q>[\"'])(?P<lit>[^\"']+)(?P=q)"
    r"|(?P<id>[A-Za-z_][\w]*)"
    r")"
)
_LS_BRACKET = re.compile(r"localStorage\s*\[\s*[\"']([^\"']+)[\"']\s*\]")
_LAST_PATH_API = re.compile(r"\b(?:write_last_path|read_last_path)\b")
_CONFIG_TOML = re.compile(r"\bconfig\.toml\b")


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


def _rust_fn_body(src: str, name: str) -> str:
    m = re.search(rf"(?:pub\s+)?(?:async\s+)?fn\s+{re.escape(name)}\s*\(", src)
    if not m:
        return ""
    close_paren = _match_closer(src, m.end() - 1)
    if close_paren < 0:
        return ""
    brace = src.find("{", close_paren)
    if brace < 0:
        return ""
    close_b = _match_closer(src, brace)
    if close_b < 0:
        return src[brace + 1 :]
    return src[brace + 1 : close_b]


def _toml_keys_in_fn(body: str) -> list[str]:
    keys: list[str] = []
    for s in re.findall(r'"(?:[^"\\]|\\.)*"', body):
        keys.extend(re.findall(r"([A-Za-z_][\w]*)\s*=", s))
    return keys


# #213 — optional right person inspector (identities + meta, not a second timeline).
_INSPECTOR_HOOK = re.compile(r"\bdata-person-inspector\b")
_PALETTE_HOOK = re.compile(r"\bdata-command-palette\b")


def _markup_open_tag(src: str, start: int) -> str:
    found = _open_tag_before(src, start + 1)
    return found[1] if found else ""


# #217 — contrast tokens: light + dark both readable (CSS variables only).
_CONTRAST_HSL = re.compile(
    r"hsla?\(\s*(-?[\d.]+)\s*(?:deg)?\s*[,/\s]\s*"
    r"(-?[\d.]+)%\s*[,/\s]\s*(-?[\d.]+)%",
    re.I,
)
_CONTRAST_COLOR_SCHEME = re.compile(
    r"(?:^|[,}\s])(?::root|html)(?:\s*,\s*(?:html|body|#app|:root))*\s*\{"
    r"[^}]*color-scheme\s*:\s*light\s+dark\b",
    re.I | re.S,
)
_CONTRAST_DARK_MEDIA = re.compile(
    r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)\s*\{",
    re.I,
)
_CONTRAST_AT_THEME = re.compile(r"@theme\b[^{]*\{")
_CONTRAST_ROOT = re.compile(r"(?:^|[,}\s]):root(?:\s*,\s*(?:html|body|#app|:root))*\s*\{")
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
_CONTRAST_SEARCH_MARK_NAMES = ("--search-mark", "--color-search-mark")


def _css_brace_body(src: str, open_idx: int) -> str:
    if open_idx < 0 or open_idx >= len(src) or src[open_idx] != "{":
        return ""
    depth = 0
    j = open_idx
    while j < len(src):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[open_idx + 1 : j]
        j += 1
    return ""


def _css_at_bodies(css: str, head: re.Pattern[str]) -> list[str]:
    out: list[str] = []
    for m in head.finditer(css):
        brace = css.find("{", m.start())
        body = _css_brace_body(css, brace)
        if body:
            out.append(body)
    return out


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


def _contrast_dark_blob(css: str) -> str:
    return "\n".join(_css_at_bodies(css, _CONTRAST_DARK_MEDIA))


def _hsl_tuple(value: str) -> tuple[float, float, float] | None:
    m = _CONTRAST_HSL.search(value)
    if not m:
        return None
    return float(m.group(1)), float(m.group(2)), float(m.group(3))


def _contrast_surface_tag(src: str, hook: str) -> str:
    at = src.find(hook)
    if at < 0:
        return ""
    return _markup_open_tag(src, src.rfind("<", 0, at + 1))


# #218 — appearance follows OS (no Theme menu; named overlay / lightbox scrim).
_APPEARANCE_SCRIM_NAMES = ("--overlay", "--scrim", "--lightbox-scrim")
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
_APPEARANCE_MENU_LABEL = re.compile(r"""["'](?:Theme|Appearance)["']""")
_APPEARANCE_FETCH = re.compile(r"\bfetch\s*\(")
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
_APPEARANCE_DOCS_NO_THEME = re.compile(
    r"("
    r"no(?: in-app)? Theme(?: / Appearance)? menu"
    r"|without (?:a |an )?Theme menu"
    r"|no Theme / Appearance"
    r"|not (?:a |an )?Theme menu"
    r")",
    re.I,
)


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


# #219 — status colors via tokens (warning / optional success; no raw amber).
_STATUS_WARNING_NAMES = ("--warning", "--color-warning")
_STATUS_GRADIENT = re.compile(r"(?<![\w-])bg-gradient")
_STATUS_CONFETTI = re.compile(r"\bconfetti\b", re.I)
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


def _status_hook_blob(src: str, hook: str) -> str:
    """Opening-tag ancestors plus a short window around a data-* / text hook."""
    at = src.find(hook)
    if at < 0:
        return ""
    tags = _ancestor_tags(src, at, limit=8)
    window = src[max(0, at - 160) : at + 280]
    return "\n".join(tags) + "\n" + window


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
_MOTION_JS_REDUCE = re.compile(
    r"("
    r"\bmatchMedia\s*\("
    r"|\bMediaQuery\b"
    r"|\bprefersReducedMotion\b"
    r"|prefers-reduced-motion"
    r")"
)
_MOTION_DURATION_ZERO = re.compile(
    r"("
    r"\bduration\s*:\s*0\b"
    r"|\bduration\s*=\s*0\b"
    r"|\?\s*0\s*:"
    r")"
)


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
