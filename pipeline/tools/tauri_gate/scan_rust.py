"""Parse walkers extracted from scan.py (scan_rust)."""
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

from tauri_gate.scan_rust_rest import (
    _rust_next,
    _rust_match_delim,
    _rust_function_body,
    _rust_fn_signature,
    _rust_call_arg,
    _rust_body_with_callees,
    _svelte_interpolations,
    _product_svelte,
    _FETCH_CALL,
    _opening_tag,
    __all__,
)

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
