"""#421 — near-message review Accept does not ask for two people."""
from __future__ import annotations

import re
from pathlib import Path

from common import fail

_ISSUE = "#421"
_HARD = "Accept links these people and can be undone."
_PERSON_CONFIRM = {"linkThesePeople", "linkThesePeopleDesc"}


def _locale_string(text: str, key: str) -> str | None:
    m = re.search(rf"\b{re.escape(key)}\s*:\s*\"((?:\\.|[^\"\\])*)\"", text)
    if m:
        return m.group(1)
    m = re.search(
        rf"\b{re.escape(key)}\s*:\s*\n\s*\"((?:\\.|[^\"\\])*)\"",
        text,
    )
    if m:
        return m.group(1)
    return None


def _function_body(src: str, name: str) -> str | None:
    m = re.search(rf"function {re.escape(name)}\s*\([^)]*\)\s*\{{", src)
    if not m:
        return None
    start = m.end() - 1
    depth = 0
    for i in range(start, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start : i + 1]
    return None


def _near_helpers(src: str) -> list[str]:
    names: list[str] = []
    for name in re.findall(r"function\s+([A-Za-z_][\w]*)\s*\(", src):
        body = _function_body(src, name) or ""
        if "wa_near" in body:
            names.append(name)
    return names


def _expanded(src: str, body: str) -> str:
    chunks = [body]
    for name in _near_helpers(src):
        helper = _function_body(src, name)
        if helper:
            chunks.append(helper)
    return "\n".join(chunks)


def _accept_enabled_for_wa_near(pane: str) -> bool:
    body = _function_body(pane, "canAccept")
    if body is None:
        return False
    text = _expanded(pane, body)
    if "wa_near" not in text:
        return False
    # A wa_near path must return true without demanding two selected people.
    for match in re.finditer(r"wa_near", text):
        window = text[match.start() : match.start() + 320]
        if "return true" not in window:
            continue
        before_return = window.split("return true", 1)[0]
        if "selected.length >= 2" in before_return or "selected.length>=2" in before_return:
            continue
        return True
    return False


def _near_confirm_keys(pane: str) -> list[str]:
    accept = _function_body(pane, "accept")
    if not accept:
        return []
    helpers = set(_near_helpers(pane))
    flags: set[str] = set()
    for match in re.finditer(
        r"(?:const|let)\s+([A-Za-z_][\w]*)\s*=\s*([^;]+);",
        accept,
    ):
        expr = match.group(2)
        if "wa_near" in expr or any(name in expr for name in helpers):
            flags.add(match.group(1))
    keys: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"[^;]{0,400}\?[^;]{0,240}:[^;]{0,240}", accept):
        chunk = match.group(0)
        if "wa_near" not in chunk and not any(name in chunk for name in helpers | flags):
            continue
        for key in re.findall(r"""\bt\(\s*["']([A-Za-z0-9_]+)["']\s*\)""", chunk):
            if key in _PERSON_CONFIRM or key in seen:
                continue
            seen.add(key)
            keys.append(key)
    if keys:
        return keys
    # if (wa_near…) { … t("key") … }
    for match in re.finditer(r"if\s*\(([^)]*)\)\s*\{", accept):
        cond = match.group(1)
        if "wa_near" not in cond and not any(name in cond for name in helpers | flags):
            continue
        start = match.end()
        depth = 1
        i = start
        while i < len(accept) and depth:
            if accept[i] == "{":
                depth += 1
            elif accept[i] == "}":
                depth -= 1
            i += 1
        block = accept[start : i - 1]
        for key in re.findall(r"""\bt\(\s*["']([A-Za-z0-9_]+)["']\s*\)""", block):
            if key in _PERSON_CONFIRM or key in seen:
                continue
            seen.add(key)
            keys.append(key)
    return keys


def _hardcoded_hidden_for_near(pane: str) -> bool:
    idx = pane.find(_HARD)
    if idx < 0:
        return True
    stack: list[list[object]] = []
    for match in re.finditer(
        r"\{(#if\b|#each\b|:else if\b|:else\b|/if\b|/each\b)([^}]*)\}",
        pane[:idx],
    ):
        kind = match.group(1)
        cond = match.group(2)
        if kind in ("#if", "#each"):
            stack.append([kind, cond, False])
        elif kind == ":else if" and stack:
            stack[-1][1] = cond
            stack[-1][2] = False
        elif kind == ":else" and stack:
            stack[-1][2] = True
        elif kind in ("/if", "/each") and stack:
            stack.pop()
    for kind, cond, in_else in stack:
        if kind != "#if" or "wa_near" not in str(cond):
            continue
        if in_else or "!" in str(cond):
            return True
    return False


def assert_wa_near_review(crate: Path) -> None:
    """Accept is enabled for a wa_near reason with no person checkboxes.

    Near-row confirm copy comes from an en/tr pair. The person-merge sentence
    is not the text shown for that row.
    """
    pane_path = crate / "web" / "lib" / "ReviewPane.svelte"
    if not pane_path.is_file():
        fail(f"{_ISSUE}: ReviewPane.svelte required")
    pane = pane_path.read_text()
    if not _accept_enabled_for_wa_near(pane):
        fail(
            f"{_ISSUE}: ReviewPane.svelte must enable Accept when the review "
            "reason has wa_near without requiring two selected people"
        )
    keys = _near_confirm_keys(pane)
    if not keys:
        fail(f"{_ISSUE}: near-row confirm needs en and tr locale keys")
    en_path = crate / "web" / "lib" / "locales" / "en.ts"
    tr_path = crate / "web" / "lib" / "locales" / "tr.ts"
    en_text = en_path.read_text() if en_path.is_file() else ""
    tr_text = tr_path.read_text() if tr_path.is_file() else ""
    for key in keys:
        en = _locale_string(en_text, key)
        tr = _locale_string(tr_text, key)
        if not en or not tr or en == tr:
            fail(f"{_ISSUE}: near-row confirm needs an en/tr locale pair (key {key})")
        if _HARD in en or _HARD in tr:
            fail(
                f"{_ISSUE}: near-row confirm must not be the sentence `{_HARD}`"
            )
    if not _hardcoded_hidden_for_near(pane):
        fail(
            f"{_ISSUE}: the near row must not show the hardcoded sentence `{_HARD}`"
        )
