"""#471 — a wa_near card shows the older wording and the newer wording.

Both locale packs have the four exact strings. The card renders the two
label keys and the two wording texts, older then newer, as text nodes.
For that kind the raw reason JSON is not the wording display. Other kinds
still show their reason. data-review-card stays. No new CSS color token
and no new palette. Reject still uses stopSuggesting.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.scan import (
    _function_body,
    _match_closer,
    _svelte_markup,
    _without_comments,
)

_ISSUE = "WA471-CARD"

# (key, english, turkish) — exact.
_STRINGS = (
    ("reviewOlderWording", "Older wording", "Eski metin"),
    ("reviewNewerWording", "Newer wording", "Yeni metin"),
    ("joinTheseMessages", "Keep one message?", "Tek mesaj kalsın mı?"),
    (
        "joinTheseMessagesDesc",
        "The newer wording stays on the message. The older wording stays under Edited. People stay separate.",
        "Yeni metin mesajda kalır. Eski metin Düzenlendi altında kalır. Kişiler ayrı kalır.",
    ),
)

_LABELS = (
    ("reviewOlderWording", "older_wording"),
    ("reviewNewerWording", "newer_wording"),
)

# Every custom property in web/app.css at the start of #471.
_KNOWN_TOKENS = frozenset(
    {
        "--font-sans",
        "--color-background",
        "--color-foreground",
        "--color-muted",
        "--color-muted-foreground",
        "--color-border",
        "--color-input",
        "--color-primary",
        "--color-primary-foreground",
        "--color-secondary",
        "--color-secondary-foreground",
        "--color-accent",
        "--color-accent-foreground",
        "--color-destructive",
        "--color-warning",
        "--color-warning-foreground",
        "--color-success",
        "--color-success-foreground",
        "--color-ring",
        "--color-card",
        "--color-card-foreground",
        "--radius-sm",
        "--radius-md",
        "--radius-lg",
        "--bubble-me",
        "--bubble-them",
        "--bubble-body-size",
        "--search-mark",
        "--overlay",
        "--lightbox-scrim",
        "--lightbox-chrome-fg",
        "--chrome-preview-fg",
        "--chrome-chip-bg",
        "--chrome-chip-fg",
        "--chrome-inspector-fg",
        "--chrome-review-card",
        "--chrome-palette",
        "--chrome-toast",
    }
)

_TOKEN_DEF = re.compile(r"(--[A-Za-z0-9-]+)\s*:\s*([^;]+);")
_COLOR_VALUE = re.compile(
    r"hsl\(|hsla\(|rgb\(|rgba\(|oklch\(|oklab\(|#[0-9A-Fa-f]{3,8}\b"
)
_COLOR_NAME = re.compile(
    r"^--(?:color|chrome|bubble|search|overlay|lightbox|palette|review|wording)-"
)
_PALETTE_CLASS = re.compile(
    r"\b(?:text|bg|border|fill|stroke|from|to|via|ring|outline|decoration|shadow)-"
    r"(?:amber|yellow|orange|red|rose|pink|fuchsia|purple|violet|indigo|blue|sky|"
    r"cyan|teal|emerald|green|lime|slate|gray|zinc|neutral|stone|black|white)"
    r"(?:-\d{2,3})?\b"
)
_INCLUDES_NEAR = re.compile(r"""includes\(\s*['"]wa_near['"]\s*\)""")
_REASON_RENDER = re.compile(r"\{(?![#:/@])([^{}]*)\}")


def _negated_wa_near(cond: str) -> bool:
    if re.search(r"!\s*waNear\b", cond):
        return True
    for match in _INCLUDES_NEAR.finditer(cond):
        window = cond[max(0, match.start() - 80) : match.start()]
        if re.search(r"!\s*[\w.?]+\s*$", window):
            return True
    return False


def _positive_wa_near(cond: str, flags: set[str]) -> bool:
    if _INCLUDES_NEAR.search(cond) and not _negated_wa_near(cond):
        return True
    if re.search(r"(?<![\w!])waNear\b", cond) and not re.search(r"!\s*waNear\b", cond):
        return True
    for name in flags:
        if re.search(rf"(?<![\w!]){re.escape(name)}\b", cond) and not re.search(
            rf"!\s*{re.escape(name)}\b", cond
        ):
            return True
    if re.search(r"\b(?:older_wording|newer_wording)\b", cond):
        return True
    return False


def _wa_near_flags(script: str) -> set[str]:
    flags: set[str] = set()
    for match in re.finditer(
        r"(?:const|let|var)\s+([A-Za-z_]\w*)\s*=\s*([^;\n]+)",
        script,
    ):
        expr = match.group(2)
        if "wa_near" in expr and not _negated_wa_near(expr):
            flags.add(match.group(1))
    return flags


def _branch_shows_wa_near(cond: str, in_else: bool, flags: set[str]) -> bool:
    pos = _positive_wa_near(cond, flags)
    neg = _negated_wa_near(cond)
    if pos and neg:
        return False
    if pos and not in_else:
        return True
    if neg and in_else:
        return True
    return False


def _branch_hides_wa_near(cond: str, in_else: bool, flags: set[str]) -> bool:
    pos = _positive_wa_near(cond, flags)
    neg = _negated_wa_near(cond)
    if pos and neg:
        return False
    if pos and in_else:
        return True
    if neg and not in_else:
        return True
    return False


def _if_arms(src: str) -> list[tuple[str, str, bool, int, int]]:
    """(condition, body, in_else, body_start, body_end) for every if / else-if / else."""
    arms: list[tuple[str, str, bool, int, int]] = []

    def skip_each(i: int) -> int:
        i = _match_closer(src, i) + 1
        depth = 1
        while i < len(src) and depth:
            if src.startswith("{#each", i) or src.startswith("{#if", i):
                depth += 1
                end = _match_closer(src, i)
                i = end + 1 if end >= 0 else i + 1
                continue
            if src.startswith("{/each}", i) or src.startswith("{/if}", i):
                depth -= 1
                i += len("{/each}") if src.startswith("{/each}", i) else len("{/if}")
                continue
            i += 1
        return i

    def parse_if(i: int) -> int:
        tag_end = _match_closer(src, i)
        if tag_end < 0:
            return i + 1
        cond = src[i:tag_end]
        i = tag_end + 1
        body_start = i
        else_next = False
        while i < len(src):
            if src.startswith("{#if", i):
                i = parse_if(i)
                continue
            if src.startswith("{#each", i):
                i = skip_each(i)
                continue
            if src.startswith("{:else if", i):
                arms.append((cond, src[body_start:i], else_next, body_start, i))
                tag_end = _match_closer(src, i)
                if tag_end < 0:
                    return len(src)
                cond = src[i:tag_end]
                else_next = False
                i = tag_end + 1
                body_start = i
                continue
            if src.startswith("{:else}", i):
                arms.append((cond, src[body_start:i], else_next, body_start, i))
                else_next = True
                i += len("{:else}")
                body_start = i
                continue
            if src.startswith("{/if}", i):
                arms.append((cond, src[body_start:i], else_next, body_start, i))
                return i + len("{/if}")
            i += 1
        arms.append((cond, src[body_start:], else_next, body_start, len(src)))
        return len(src)

    i = 0
    while i < len(src):
        if src.startswith("{#if", i):
            i = parse_if(i)
            continue
        i += 1
    return arms


def _label_end(body: str, key: str, start: int) -> int | None:
    match = re.search(
        rf"""\bt\(\s*['"]{re.escape(key)}['"]\s*\)""",
        body[start:],
    )
    if not match:
        return None
    return start + match.end()


def _text_end(body: str, field: str, start: int) -> int | str | None:
    for match in re.finditer(r"\{([^{}]*)\}", body[start:]):
        expr = match.group(1).strip()
        if expr.startswith(("#", ":", "/", "@")):
            continue
        if field not in expr:
            continue
        if re.search(r"\bt\s*\(", expr):
            return "t"
        if "@html" in expr:
            return "html"
        return start + match.end()
    return None


def _wording_order_problem(body: str) -> str | None:
    pos = 0
    for key, field in _LABELS:
        label = _label_end(body, key, pos)
        if label is None:
            return f'missing label t("{key}")'
        text = _text_end(body, field, label)
        if text == "t":
            return f"{field} is passed through t()"
        if text == "html":
            return f"{field} is not plain text"
        if text is None:
            return f"missing text node {field} under t(\"{key}\")"
        pos = text
    return None


def _renders_raw_reason(body: str) -> bool:
    for match in _REASON_RENDER.finditer(body):
        expr = match.group(1)
        if "review.reason" not in expr:
            continue
        if "includes" in expr or re.search(r"\bt\s*\(", expr):
            continue
        return True
    return False


def _palette_problem(body: str) -> str | None:
    literal = _COLOR_VALUE.search(body)
    if literal:
        return f"wording block uses a CSS color literal {literal.group(0)!r}"
    palette = _PALETTE_CLASS.search(body)
    if palette:
        return f"wording block uses a new palette class {palette.group(0)!r}"
    for name in re.findall(r"var\(\s*(--[A-Za-z0-9-]+)", body):
        if name not in _KNOWN_TOKENS:
            return f"wording block uses a new CSS token {name}"
    if re.search(r"\b(?:command-palette|CommandPalette|data-command-palette)\b", body):
        return "wording block adds a palette"
    return None


def _new_color_tokens(css: str) -> list[str]:
    found: list[str] = []
    for name, value in _TOKEN_DEF.findall(css):
        if name in _KNOWN_TOKENS:
            continue
        if _COLOR_NAME.match(name) or _COLOR_VALUE.search(value):
            found.append(name)
    return found


def _locale_bits(crate: Path) -> list[str]:
    bits: list[str] = []
    packs = {
        "en.ts": crate / "web" / "lib" / "locales" / "en.ts",
        "tr.ts": crate / "web" / "lib" / "locales" / "tr.ts",
    }
    parsed: dict[str, dict[str, str]] = {}
    for name, path in packs.items():
        if not path.is_file():
            bits.append(f"{name} is missing")
            parsed[name] = {}
            continue
        parsed[name] = _chrome_pack_entries(path.read_text())
    for key, en, tr in _STRINGS:
        got_en = parsed["en.ts"].get(key)
        got_tr = parsed["tr.ts"].get(key)
        if got_en is None:
            bits.append(f"en.ts missing {key}")
        elif got_en != en:
            bits.append(f"en.ts {key} is {got_en!r}, expected {en!r}")
        if got_tr is None:
            bits.append(f"tr.ts missing {key}")
        elif got_tr != tr:
            bits.append(f"tr.ts {key} is {got_tr!r}, expected {tr!r}")
    return bits


def _reason_bits(markup: str, arms: list[tuple[str, str, bool, int, int]], flags: set[str]) -> list[str]:
    renders = []
    for match in _REASON_RENDER.finditer(markup):
        expr = match.group(1)
        if "review.reason" not in expr or "includes" in expr:
            continue
        if re.search(r"\bt\s*\(", expr):
            continue
        renders.append(match.start())
    if not renders:
        return ["other review kinds must still show their reason string"]
    bits: list[str] = []
    for idx in renders:
        hidden = False
        for cond, _body, in_else, start, end in arms:
            if start <= idx < end and _branch_hides_wa_near(cond, in_else, flags):
                hidden = True
                break
        if not hidden:
            bits.append(
                "raw reason JSON is still the wording display for a wa_near card"
            )
            break
    return bits


def assert_review_wording(crate: Path) -> None:
    """WA471-CARD: older/newer wording on the wa_near card, exact en/tr strings."""
    bits = _locale_bits(crate)
    pane_path = crate / "web" / "lib" / "ReviewPane.svelte"
    if not pane_path.is_file():
        bits.append("ReviewPane.svelte is missing")
        fail(f"{_ISSUE}:\n- " + "\n- ".join(bits))
    src = _without_comments(pane_path.read_text())
    markup = re.sub(r"<!--.*?-->", "", _svelte_markup(src), flags=re.S)
    if "data-review-card" not in src:
        bits.append("ReviewPane.svelte missing data-review-card")
    reject = _function_body(src, "reject")
    if "stopSuggesting" not in reject or "stopSuggestingDesc" not in reject:
        bits.append("Reject must still use stopSuggesting / stopSuggestingDesc")

    script_end = src.find("</script>")
    script = src[:script_end] if script_end >= 0 else ""
    flags = _wa_near_flags(script)
    arms = _if_arms(markup)
    good = False
    saw_wording = False
    for cond, body, in_else, _start, _end in arms:
        if not _branch_shows_wa_near(cond, in_else, flags):
            continue
        if not re.search(
            r"older_wording|newer_wording|reviewOlderWording|reviewNewerWording",
            body,
        ):
            continue
        saw_wording = True
        problem = _wording_order_problem(body)
        if problem:
            bits.append(f"ReviewPane.svelte wa_near card: {problem}")
            continue
        if _renders_raw_reason(body):
            bits.append(
                "ReviewPane.svelte wa_near wording block still renders the raw reason JSON"
            )
            continue
        palette = _palette_problem(body)
        if palette:
            bits.append(f"ReviewPane.svelte {palette}")
            continue
        good = True
    if not good and not saw_wording:
        bits.append(
            "ReviewPane.svelte missing wa_near wording hook: render "
            't("reviewOlderWording"), older_wording, t("reviewNewerWording"), '
            "newer_wording as text, older then newer"
        )
    bits.extend(_reason_bits(markup, arms, flags))

    for style in re.findall(r"<style\b[^>]*>(.*?)</style>", src, flags=re.S):
        for name in _new_color_tokens(style):
            bits.append(f"ReviewPane.svelte style adds CSS color token {name}")
        literal = _COLOR_VALUE.search(style)
        if literal:
            bits.append(
                f"ReviewPane.svelte style uses a CSS color literal {literal.group(0)!r}"
            )
    css_path = crate / "web" / "app.css"
    if css_path.is_file():
        for name in _new_color_tokens(css_path.read_text()):
            bits.append(f"app.css new CSS color token {name}")

    if bits:
        fail(f"{_ISSUE}:\n- " + "\n- ".join(bits))
