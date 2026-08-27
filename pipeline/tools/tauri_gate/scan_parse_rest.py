"""Continuation of scan_parse."""
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
    _js_next,
    _match_closer,
    _function_body,
)


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

__all__ = [
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
    "__all__",
]
