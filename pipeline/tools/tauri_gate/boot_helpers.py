"""Boot / first-run keep-check tokens. Imported by import_boot (not scan)."""
from __future__ import annotations

import re

from tauri_gate.scan import _CHROME_PACK_NS, _js_next

_BOOT_IF = re.compile(
    r"\{#if\s+((?:booting|opening)(?:\s*\|\|\s*(?:booting|opening))+)\s*\}",
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

_LS_CALL = re.compile(
    r"localStorage\s*\.\s*(?:getItem|setItem)\s*\(\s*"
    r"(?:"
    r"(?P<q>[\"'])(?P<lit>[^\"']+)(?P=q)"
    r"|(?P<id>[A-Za-z_][\w]*)"
    r")"
)

_CONTRAST_AT_THEME = re.compile(r"@theme\b[^{]*\{")

_CONTRAST_ROOT = re.compile(r"(?:^|[,}\s]):root(?:\s*,\s*(?:html|body|#app|:root))*\s*\{")

_HUE_BLACK80 = re.compile(r"\bblack/80\b")

_HUE_HEX_CSS = re.compile(
    r"(?:background(?:-color)?|color|border(?:-color)?|outline-color|"
    r"fill|stroke|accent-color|caret-color|text-decoration-color)\s*:\s*"
    r"#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})\b",
    re.I,
)

_HUE_HEX_TW = re.compile(
    r"(?:bg|text|border|ring|from|to|via|outline|fill|stroke|decoration|"
    r"divide|accent|caret|shadow)-\[#[0-9A-Fa-f]{3,8}"
)


def _empty_state_local_names(src: str) -> list[str]:
    names = ["EmptyState"]
    for m in re.finditer(
        r"import\s+(\w+)\s+from\s+[\"'][^\"']*EmptyState\.svelte[\"']",
        src,
    ):
        names.append(m.group(1))
    return list(dict.fromkeys(names))


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


def _owned_import_path_rx(name: str) -> str:
    return (
        r"[\"'](?:\$lib/|(?:\.\.?/)*)(?:lib/)?"
        rf"components/ui/{re.escape(name)}"
        r"(?:/[^\"']*)?[\"']"
    )
