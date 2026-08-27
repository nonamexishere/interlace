"""Continuation of scan_rust."""
from __future__ import annotations

from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)
from tauri_gate.scan_parse import (
    _SCROLL_HELPER_SKIP,
    _match_closer,
    _function_body,
    _CHROME_PACK_SUFFIXES,
    _CHROME_PACK_DIR_HINTS,
    _CHROME_PACK_FILE_HINTS,
    _LANG_STEM,
    _looks_like_wa_pack,
)
from tauri_gate.scan_rust import (
    _RUST_CALL_SKIP,
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

__all__ = [
    "_web_pack_candidates",
    "_stem_chrome_lang",
    "_chrome_file_hinted",
    "_is_combined_chrome_pack",
    "_chrome_pack_files",
    "_extract_lang_object",
    "_chrome_lang_text",
    "_KEYMAP_CALL_SKIP",
    "_ts_fn_body",
    "_expand_fn_calls",
    "_strip_html_comments",
    "_css_without_comments",
    "_open_tag_around",
    "_web_ts_sources",
    "_RUST_CALL_SKIP",
    "_rust_next",
    "_rust_match_delim",
    "_rust_function_body",
    "_rust_fn_signature",
    "_rust_call_arg",
    "_rust_body_with_callees",
    "_svelte_interpolations",
    "_product_svelte",
    "_FETCH_CALL",
    "_opening_tag",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_SCROLL_HELPER_SKIP",
    "_match_closer",
    "_function_body",
    "_CHROME_PACK_SUFFIXES",
    "_CHROME_PACK_DIR_HINTS",
    "_CHROME_PACK_FILE_HINTS",
    "_LANG_STEM",
    "_looks_like_wa_pack",
]

__all__ = [
    "_rust_next",
    "_rust_match_delim",
    "_rust_function_body",
    "_rust_fn_signature",
    "_rust_call_arg",
    "_rust_body_with_callees",
    "_svelte_interpolations",
    "_product_svelte",
    "_FETCH_CALL",
    "_opening_tag",
    "__all__",
]
