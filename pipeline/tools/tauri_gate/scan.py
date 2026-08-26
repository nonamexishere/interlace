"""Shared readers and parse walkers for tauri_gate area modules."""
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


def _strip_html_comments(src: str) -> str:
    return re.sub(r"<!--.*?-->", "", src, flags=re.S)


def _css_without_comments(src: str) -> str:
    return re.sub(r"/\*.*?\*/", "", src, flags=re.S)


def _open_tag_around(src: str, hook: str) -> str:
    m = re.search(rf"<[^>]*{hook}[^>]*>", src, re.I | re.S)
    return m.group(0) if m else ""


def _web_ts_sources(crate: Path) -> list[Path]:
    web = crate / "web"
    if not web.is_dir():
        return []
    return [
        p
        for p in sorted(web.rglob("*"))
        if p.suffix in {".svelte", ".ts", ".js"} and "node_modules" not in p.parts
    ]
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


def _product_svelte(crate: Path) -> list[Path]:
    web = crate / "web"
    return [
        p
        for p in sorted(web.rglob("*.svelte"))
        if "node_modules" not in p.parts
    ]
_FETCH_CALL = re.compile(r"\bfetch\s*\(")


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


def _markup_open_tag(src: str, start: int) -> str:
    found = _open_tag_before(src, start + 1)
    return found[1] if found else ""


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
_SANDBOX_137 = re.compile(
    r"macOS blocked that folder\.\s*Use Open existing"
    r"(?:\u2026|\.\.\.|…)\s*once so Interlace can remember it\."
)


# #213 — optional right person inspector (identities + meta, not a second timeline).
_INSPECTOR_HOOK = re.compile(r"\bdata-person-inspector\b")


def _contrast_dark_blob(css: str) -> str:
    return "\n".join(_css_at_bodies(css, _CONTRAST_DARK_MEDIA))


# #218 — appearance follows OS (no Theme menu; named overlay / lightbox scrim).
_APPEARANCE_SCRIM_NAMES = ("--overlay", "--scrim", "--lightbox-scrim")


# #219 — status colors via tokens (warning / optional success; no raw amber).
_STATUS_WARNING_NAMES = ("--warning", "--color-warning")
_ARBITRARY_SHELL = re.compile(
    r"Command::new\s*\(\s*[\"'](?:/bin/sh|/bin/bash|/bin/zsh|/usr/bin/env|sh|bash|zsh|cmd)[\"']"
)
_BODY_T_CALL = re.compile(
    r"\bt\s*\(\s*(?:[\w.$]+\.)?(?:body_text|bodyText|preview|snippet|displayBody)\b"
)
_BUBBLE_ME_VARS = ("--bubble-me", "--color-bubble-me")
_BUBBLE_THEM_VARS = ("--bubble-them", "--color-bubble-them")
_PRETTY_GMAIL = re.compile(r"[\"']Gmail[\"']")
_RAW_WHATSAPP = re.compile(r"[\"']whatsapp[\"']")
_INCLUDE_GROUPS_LABEL = re.compile(r"include groups", re.I)
_DATA_PEOPLE_SIDEBAR = re.compile(r"data-people-sidebar", re.I)
_SPLASH_VIDEO = re.compile(r"<video\b", re.I)
_PEOPLE_AWAIT_REFRESH = re.compile(r"await\s+refreshPeople\s*\(")
_HTML_BODY = re.compile(r"\{@html\b")
_LINKIFY_FETCH = re.compile(r"fetch\s*\(\s*[\"']https?://", re.I)
_MOD_EITHER = re.compile(r"(?:e\.)?(?:metaKey|ctrlKey)")
_VIEW_SEARCH_ASSIGN = re.compile(r"\bview\s*=\s*[\"']search[\"']")
_A11Y_ROLE_OPTION = re.compile(r"\brole\s*=\s*[\"']option[\"']", re.I)
_A11Y_TABINDEX_NEG = re.compile(r"\btabindex\s*=\s*(?:[\"']-1[\"']|\{-1\})", re.I)
_HUE_YELLOW = re.compile(r"\byellow-\d+")
_TYPO_FONT_SANS = re.compile(r"--font-sans\s*:\s*([^;]+);")
_CMD_PALETTE_PKG = re.compile(r"[\"'](?:cmdk|svelte-command(?:-palette)?)[\"']", re.I)
_TOAST_SONNER_PKG = re.compile(r"[\"'](?:sonner|svelte-sonner)[\"']", re.I)
_LS_BRACKET = re.compile(r"localStorage\s*\[\s*[\"']([^\"']+)[\"']\s*\]")
_LAST_PATH_API = re.compile(r"\b(?:write_last_path|read_last_path)\b")
_CONFIG_TOML = re.compile(r"\bconfig\.toml\b")
_PALETTE_HOOK = re.compile(r"\bdata-command-palette\b")
_CONTRAST_SEARCH_MARK_NAMES = ("--search-mark", "--color-search-mark")
_APPEARANCE_MENU_LABEL = re.compile(r"""["'](?:Theme|Appearance)["']""")
_APPEARANCE_FETCH = re.compile(r"\bfetch\s*\(")
_STATUS_GRADIENT = re.compile(r"(?<![\w-])bg-gradient")
_STATUS_CONFETTI = re.compile(r"\bconfetti\b", re.I)

_PEOPLE_GEN_COUNTER = re.compile(r"people|roster|ppl", re.I)

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

_SPIN_ANIM = re.compile(
    r"("
    r"animate-spin\b"
    r"|@keyframes\s+[\w-]*spin[\w-]*"
    r"|animation\s*:\s*[^;\n}]*\bspin\b"
    r"|animation-name\s*:\s*[\w-]*spin[\w-]*"
    r")",
    re.I,
)

_CONTRAST_DARK_MEDIA = re.compile(
    r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)\s*\{",
    re.I,
)

