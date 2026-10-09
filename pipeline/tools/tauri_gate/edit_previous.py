"""#464 — Edited opens the previous wordings on the same non-mail bubble.

messageEdited stays "Edited" / "Düzenlendi". The non-mail edited arm renders
that key on <button type="button" data-message-edited>, toggled by editOpen.
While open, each previous_bodies string is a plain <p data-previous-body>.
A deleted bubble stays messageDeleted only. No new locale key.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.last_read import _text, _web_file
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.scan import (
    _helper_with_callees,
    _match_closer,
    _open_tag_before,
    _svelte_markup,
    _template_stack,
    _without_comments,
)

_ISSUE = "#464"
_EDITED = re.compile(r"""edit_state\s*===\s*['"]edited['"]""")
_DELETED = re.compile(r"""edit_state\s*===\s*['"]deleted['"]""")
_T_EDITED = re.compile(r"""t\(\s*['"]messageEdited['"]\s*\)""")
_T_DELETED = re.compile(r"""t\(\s*['"]messageDeleted['"]\s*\)""")
_BLOCK = re.compile(r"\{#if\b|\{:else\b|\{/if\}")
_PREV_CLASSES = ("text-xs", "text-muted-foreground", "whitespace-pre-wrap")
_BTN_CLASSES = (
    "text-xs",
    "text-muted-foreground",
    "focus-visible:ring-2",
    "focus-visible:ring-ring",
)


def _true_arm_span(src: str, if_open: int) -> tuple[int, int]:
    head_end = _match_closer(src, if_open)
    if head_end < 0:
        return (if_open, if_open)
    depth = 1
    start = head_end + 1
    for m in _BLOCK.finditer(src, start):
        tok = m.group(0)
        if tok.startswith("{#if"):
            depth += 1
        elif tok.startswith("{:else") and depth == 1:
            return (start, m.start())
        elif tok.startswith("{/if"):
            depth -= 1
            if depth == 0:
                return (start, m.start())
    return (start, len(src))


def _if_open_matching(src: str, rx: re.Pattern[str]) -> int:
    for m in re.finditer(r"\{#if\b", src):
        end = _match_closer(src, m.start())
        if end < 0:
            continue
        if rx.search(src[m.start() : end + 1]):
            return m.start()
    return -1


def _non_mail_span(markup: str) -> tuple[int, int]:
    m = re.search(r"\{#if\s*!isMailRow\s*\(", markup)
    if m:
        return _true_arm_span(markup, m.start())
    m = re.search(r"\{#if\s+isMailRow\s*\(", markup)
    if not m:
        return (0, 0)
    head_end = _match_closer(markup, m.start())
    if head_end < 0:
        return (0, 0)
    depth = 1
    else_at = None
    for tok in _BLOCK.finditer(markup, head_end + 1):
        text = tok.group(0)
        if text.startswith("{#if"):
            depth += 1
        elif text.startswith("{:else") and depth == 1 and else_at is None:
            else_at = tok.end()
        elif text.startswith("{/if"):
            depth -= 1
            if depth == 0:
                if else_at is None:
                    return (0, 0)
                return (else_at, tok.start())
    return (0, 0)


def _tight_each_span(src: str, idx: int) -> tuple[int, int] | None:
    best: tuple[int, int] | None = None
    best_len: int | None = None
    for m in re.finditer(r"\{#each\b", src):
        span = _each_span(src, m.start())
        if span[0] <= idx < span[1]:
            length = span[1] - span[0]
            if best_len is None or length < best_len:
                best = span
                best_len = length
    return best


def _each_span(src: str, each_open: int) -> tuple[int, int]:
    depth = 0
    for m in re.finditer(r"\{#each\b|\{/each\}", src[each_open:]):
        if m.group(0).startswith("{#each"):
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return (each_open, each_open + m.end())
    return (each_open, len(src))


def _class_tokens(tag: str) -> list[str]:
    tokens: list[str] = []
    for m in re.finditer(
        r"""\bclass\s*=\s*(?:"([^"]*)"|'([^']*)'|\{`([^`]*)`\}|\{"([^"]*)"\})""",
        tag,
    ):
        raw = next(g for g in m.groups() if g is not None)
        tokens.extend(raw.split())
    return tokens


def _has_class(tag: str, token: str) -> bool:
    return token in _class_tokens(tag) or f"class:{token}" in tag


def _tag_name(tag: str) -> str:
    m = re.match(r"<\s*([A-Za-z][\w.-]*)", tag)
    return m.group(1) if m else ""


def _attr_expr(tag: str, name: str) -> str:
    m = re.search(rf"\b{re.escape(name)}\s*=\s*", tag)
    if not m:
        return ""
    rest = tag[m.end() :]
    if rest.startswith("{"):
        end = _match_closer(tag, m.end())
        return tag[m.end() : end + 1] if end >= 0 else rest
    if rest[:1] in "'\"":
        q = rest[0]
        stop = rest.find(q, 1)
        return rest[: stop + 1] if stop >= 0 else rest
    return rest.split(None, 1)[0]


def _click_blob(src: str, tag: str) -> str:
    expr = _attr_expr(tag, "onclick") or _attr_expr(tag, "on:click")
    blob = expr
    for name in re.findall(r"\b([A-Za-z_]\w*)\b", expr):
        blob += "\n" + _helper_with_callees(src, name)
    return blob


def _true_if(stack: list[tuple[str, str, str]], rx: re.Pattern[str]) -> bool:
    return any(kind == "if" and rx.search(cond) for kind, cond, _ in stack)


def _true_name(stack: list[tuple[str, str, str]], name: str) -> bool:
    return any(
        kind == "if" and re.search(rf"\b{re.escape(name)}\b", cond)
        for kind, cond, _ in stack
    )


def _in_each(stack: list[tuple[str, str, str]], needle: str) -> bool:
    return any(kind == "each" and needle in cond for kind, cond, _ in stack)


def _in_mail_true(stack: list[tuple[str, str, str]]) -> bool:
    return any(
        kind == "if" and re.search(r"(?<!!)\bisMailRow\s*\(", cond)
        for kind, cond, _ in stack
    )


def _start_tag(markup: str, idx: int) -> str:
    found = _open_tag_before(markup, idx + 1)
    if not found:
        return ""
    return found[1]


def _has_edit_open(src: str) -> bool:
    return (
        re.search(
            r"\beditOpen\b[\s\S]{0,200}?Record\s*<\s*number\s*,\s*boolean\s*>"
            r"|Record\s*<\s*number\s*,\s*boolean\s*>[\s\S]{0,200}?\beditOpen\b",
            src,
        )
        is not None
    )


def _timeline_row_block(api: str) -> str:
    m = re.search(r"export\s+type\s+TimelineRow\s*=\s*\{", api)
    if not m:
        return ""
    brace = api.find("{", m.start())
    end = _match_closer(api, brace)
    if end < 0:
        return ""
    return api[brace : end + 1]


def _quoted_clear_effects(src: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"\$effect\s*\(", src):
        close = _match_closer(src, m.end() - 1)
        if close < 0:
            continue
        call = src[m.start() : close + 1]
        if (
            "density" in call
            and "selectedId" in call
            and re.search(r"quotedOpen\s*=\s*\{\s*\}", call)
        ):
            out.append(call)
    return out


def _button_bits(src: str, markup: str, tag: str, idx: int) -> list[str]:
    bits: list[str] = []
    stack = _template_stack(markup, idx)
    if _tag_name(tag) != "button":
        bits.append("edited control must be a native <button>, not the shared Button")
    if not re.search(r"""\btype\s*=\s*['"]button['"]""", tag):
        bits.append('edited control is not <button type="button">')
    missing = [token for token in _BTN_CLASSES if not _has_class(tag, token)]
    if missing:
        bits.append("edited button is missing " + " ".join(missing))
    if any(tok == "underline" or tok.endswith(":underline") for tok in _class_tokens(tag)):
        bits.append("edited button uses an underline class")
    if re.search(r"\baria-label\s*=", tag):
        bits.append("edited button adds an aria-label; the accessible name is the visible text")
    aria = _attr_expr(tag, "aria-expanded")
    if not aria:
        bits.append("edited button does not set aria-expanded from editOpen")
    elif "editOpen" not in aria or re.search(r"\bquotedOpen\b", aria):
        bits.append("aria-expanded is not the editOpen flag")
    click = _click_blob(src, tag)
    if "stopPropagation" not in click or "preventDefault" not in click:
        bits.append("edited button click handler does not call stopPropagation and preventDefault")
    if not _true_if(stack, _EDITED) or _true_if(stack, _DELETED) or _in_mail_true(stack):
        bits.append('edited control is outside edit_state === "edited"')
    if any(
        kind == "if" and "previous_bodies" in cond for kind, cond, _ in stack
    ) or _in_each(stack, "previous_bodies"):
        bits.append("edited button is hidden when previous_bodies is empty")
    end = idx
    found = _open_tag_before(markup, idx + 1)
    if found:
        end = found[0] + len(found[1])
    close = markup.find("</button>", end)
    inner = markup[end:close] if close >= 0 else ""
    if not _T_EDITED.search(inner):
        bits.append('edited button does not render t("messageEdited")')
    elif re.search(r"<svg\b|lucide|<[A-Z]", inner):
        bits.append("edited button adds an icon")
    arm_at = _if_open_matching(markup, _EDITED)
    if arm_at >= 0 and close >= 0:
        arm_s, arm_e = _true_arm_span(markup, arm_at)
        arm = markup[arm_s:arm_e]
        without = arm.replace(markup[found[0] : close + len("</button>")] if found else "", "", 1)
        if "messageEdited" in without:
            bits.append("messageEdited is still a <p> outside the edited button")
    return bits


def _previous_bits(markup: str, idx: int) -> list[str]:
    bits: list[str] = []
    tag = _start_tag(markup, idx)
    stack = _template_stack(markup, idx)
    if _tag_name(tag) != "p" or "data-previous-body" not in tag:
        bits.append("previous wording is not a plain <p data-previous-body>")
        return bits
    missing = [token for token in _PREV_CLASSES if not _has_class(tag, token)]
    if missing:
        bits.append("data-previous-body is missing " + " ".join(missing))
    if "bubble-me" in tag or "bubble-them" in tag or "<article" in tag:
        bits.append("previous lines use bubble-me / bubble-them or a nested article")
    if not _true_name(stack, "editOpen"):
        bits.append("previous lines are not gated on the editOpen flag")
    if not _true_if(stack, _EDITED) or _true_if(stack, _DELETED) or _in_mail_true(stack):
        bits.append("previous lines render outside the edited arm")
    edited_at = _if_open_matching(markup, _EDITED)
    edited_arm = ""
    if edited_at >= 0:
        arm_s, arm_e = _true_arm_span(markup, edited_at)
        edited_arm = markup[arm_s:arm_e]
    each_span = _tight_each_span(markup, idx)
    if each_span is None or "previous_bodies" not in edited_arm:
        bits.append("previous lines are not one element per previous_bodies entry")
    else:
        block = markup[each_span[0] : each_span[1]]
        if re.search(r"\bLinkifyBody\b|\bwaView\b|<article\b|bubble-me|bubble-them", block):
            bits.append(
                "previous lines are passed to LinkifyBody or waView, or are a nested article"
            )
    return bits


def _order_bits(markup: str) -> list[str]:
    start, end = _non_mail_span(markup)
    if start >= end:
        return ["TimelineRows has no non-mail bubble"]
    region = markup[start:end]
    body_at = region.find("body_text")
    button_at = region.find("data-message-edited")
    prev_at = region.find("data-previous-body")
    react_at = -1
    for m in re.finditer(r"\{#if\b", region):
        abs_at = start + m.start()
        close = _match_closer(markup, abs_at)
        cond = markup[abs_at : close + 1] if close >= 0 else ""
        if "reactions" in cond:
            react_at = m.start()
            break
    if min(body_at, button_at, prev_at, react_at) < 0:
        return []
    if not (body_at < button_at < prev_at < react_at):
        return [
            "non-mail live arm source order must be current body, then the edited button, then previous lines, then reactions"
        ]
    return []


def assert_edit_previous(crate: Path) -> None:
    """#464: Edited is a button that reveals previous_bodies on the same bubble."""
    rows_path = _web_file(crate, "TimelineRows.svelte")
    list_path = _web_file(crate, "TimelineList.svelte")
    api_path = crate / "web" / "lib" / "api.ts"
    en_path = crate / "web" / "lib" / "locales" / "en.ts"
    tr_path = crate / "web" / "lib" / "locales" / "tr.ts"
    raw = _without_comments(_text(rows_path))
    markup = re.sub(r"<!--.*?-->", "", _svelte_markup(raw), flags=re.S)
    en = _chrome_pack_entries(_text(en_path)) if en_path.is_file() else {}
    tr = _chrome_pack_entries(_text(tr_path)) if tr_path.is_file() else {}
    api = _without_comments(_text(api_path))
    row = _timeline_row_block(api)
    bits: list[str] = []
    if en.get("messageEdited") != "Edited":
        bits.append("chrome key messageEdited is not Edited in en.ts")
    if tr.get("messageEdited") != "Düzenlendi":
        bits.append("chrome key messageEdited is not Düzenlendi in tr.ts")
    if not re.search(
        r"\bprevious_bodies\??\s*:\s*(?:string\s*\[\]|Array<\s*string\s*>)",
        row,
    ):
        bits.append("api.ts TimelineRow does not include previous_bodies")
    if not _has_edit_open(raw):
        bits.append("TimelineRows has no editOpen record")
    effects = _quoted_clear_effects(_without_comments(_text(list_path)))
    if not effects:
        bits.append(
            "TimelineList effect that clears quotedOpen on selectedId / density is missing"
        )
    elif any(re.search(r"\beditOpen\b", effect) for effect in effects):
        bits.append("the quotedOpen clear effect also clears editOpen")

    deleted_at = _if_open_matching(markup, _DELETED)
    if deleted_at < 0:
        bits.append('deleted arm (edit_state === "deleted") is missing')
    else:
        arm_s, arm_e = _true_arm_span(markup, deleted_at)
        arm = markup[arm_s:arm_e]
        if not _T_DELETED.search(arm):
            bits.append('deleted arm does not render t("messageDeleted")')
        for bad in (
            "data-message-edited",
            "data-previous-body",
            "previous_bodies",
            "messageEdited",
        ):
            if bad in arm:
                bits.append(f"deleted arm contains {bad}")
    mail_at = re.search(r"\{#if\s+isMailRow\s*\(", markup)
    if mail_at:
        mail_s, mail_e = _true_arm_span(markup, mail_at.start())
        mail = markup[mail_s:mail_e]
        if "data-message-edited" in mail or "data-previous-body" in mail or _T_EDITED.search(mail):
            bits.append("mail branch paints the edited button or previous lines")

    hits = list(re.finditer(r"data-message-edited", markup))
    if not hits:
        bits.append(
            'Edited is a <p>, not <button type="button" data-message-edited>'
        )
    else:
        for hit in hits:
            tag = _start_tag(markup, hit.start())
            if "data-message-edited" not in tag:
                bits.append(
                    'Edited is a <p>, not <button type="button" data-message-edited>'
                )
                continue
            bits.extend(_button_bits(raw, markup, tag, hit.start()))
    prev_hits = list(re.finditer(r"data-previous-body", markup))
    if not prev_hits:
        bits.append("nothing renders data-previous-body")
    else:
        bits.extend(_previous_bits(markup, prev_hits[0].start()))
    each = re.search(r"\{#each\s+group\.rows\b", markup)
    if each:
        a, b = _each_span(markup, each.start())
        block = markup[a:b]
        articles = len(re.findall(r"<article\b", block))
        if articles != 1:
            bits.append("a row is not exactly one article, or previous lines are a nested article")
        prev_at = block.find("data-previous-body")
        art = block.find("<article")
        art_end = block.find("</article>")
        if prev_at >= 0 and not (art < prev_at < art_end):
            bits.append("previous lines are outside the row article")
    bits.extend(_order_bits(markup))
    if bits:
        fail(f"{_ISSUE}: " + "; ".join(bits))
