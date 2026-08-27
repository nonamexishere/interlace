"""Parse walkers extracted from scan.py (scan_parse)."""
from __future__ import annotations

from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
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
    """Markup after each </script> so concatenated .svelte sources keep every pane."""
    parts, i = [], 0
    while True:
        end = text.find("</script>", i)
        if end < 0:
            return "\n".join(parts) or text
        nxt = text.find("<script", end + 9)
        parts.append(text[end:] if nxt < 0 else text[end:nxt])
        if nxt < 0:
            return "\n".join(parts)
        i = nxt


def _search_pane_blob(crate: Path) -> str:
    """SearchPane plus SearchHits (hit list may live in the sibling)."""
    lib = crate / "web" / "lib"
    return "\n".join(p.read_text() for n in ("SearchPane.svelte", "SearchHits.svelte") if (p := lib / n).is_file())


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

from tauri_gate.scan_parse_rest import (
    _cond_uses_flag,
    _open_tag_before,
    _ancestor_tags,
    _ts_function_body,
    _helper_with_callees,
    _tauri_rust_sources,
    _tauri_rust_blob,
    _CHROME_PACK_SUFFIXES,
    _CHROME_PACK_DIR_HINTS,
    _CHROME_PACK_FILE_HINTS,
    _CHROME_HELPER_NAMES,
    _CHROME_PACK_NS,
    _CHROME_NO_TRANSLATE_FIELDS,
    _CHROME_IMPORT_SPEC,
    _LANG_STEM,
    _looks_like_wa_pack,
    __all__,
)

__all__ = [
    "_SCROLL_HELPER_SKIP",
    "_TMPL_TOKEN",
    "_PERSON_PANE_SKIP",
    "_VOID_HTML",
    "_matching_each_end",
    "_js_next",
    "_without_comments",
    "_match_closer",
    "_call_arg",
    "_function_body",
    "_svelte_markup",
    "_search_pane_blob",
    "_template_stack",
    "_assigned_idents",
    "_cond_uses_flag",
    "_open_tag_before",
    "_ancestor_tags",
    "_ts_function_body",
    "_helper_with_callees",
    "_tauri_rust_sources",
    "_tauri_rust_blob",
    "_CHROME_PACK_SUFFIXES",
    "_CHROME_PACK_DIR_HINTS",
    "_CHROME_PACK_FILE_HINTS",
    "_CHROME_HELPER_NAMES",
    "_CHROME_PACK_NS",
    "_CHROME_NO_TRANSLATE_FIELDS",
    "_CHROME_IMPORT_SPEC",
    "_LANG_STEM",
    "_looks_like_wa_pack",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
]
