"""Helpers extracted from timeline_hierarchy.py (timeline_attach)."""
from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _HTML_BODY,
    _function_body,
    _match_closer,
    _svelte_markup,
    _tag_name,
    _template_stack,
    _timeline_block,
    _web_logic,
    _without_comments,
)

from tauri_gate.import_boot_guards import _PRE_WRAP

from tauri_gate.media_linkify_lib import _SHOW_QUOTED


from tauri_gate.timeline_latest import (
    _JK_KEY,
    _derived_body,
)
from tauri_gate.timeline_grouping import (
    _tag_at,
    _BUBBLE_META,
    _BUBBLE_BODY,
    _BUBBLE_ATTACH,
    _ODD_STACK_SPACE,
    _FRAC_STACK_SPACE,
    _STACK_FLEX_COL,
    _STACK_GAP_48,
    _STACK_PAD_48,
    _CAS_ITEMS_LEN_COND,
    _UL_MT2_STATIC,
    _UL_MT2_LIT,
    _MT2_TOKEN,
    _NOMARGIN_PROP,
    _BUBBLE_HTML_TOKEN,
    _BUBBLE_VOID,
    _article_open_tag,
    _hook_pos,
    _casattach_pos,
)


def _stack_class_blobs(article: str) -> list[str]:
    """Article open tag + any flex-col wrapper (not caption chip rows)."""
    blobs: list[str] = []
    open_tag = _article_open_tag(article)
    if open_tag:
        blobs.append(open_tag)
    for m in re.finditer(r"<([a-zA-Z][\w:-]*)\b[^>]*>", article):
        tag = m.group(0)
        if _STACK_FLEX_COL.search(tag) and tag not in blobs:
            blobs.append(tag)
    return blobs


def _odd_stack_token(blobs: list[str]) -> str | None:
    """First off-scale arbitrary / fractional spacing token on the stack."""
    for blob in blobs:
        for m in _ODD_STACK_SPACE.finditer(blob):
            px = int(m.group(1))
            if px % 4 != 0:
                return m.group(0)
        for m in _FRAC_STACK_SPACE.finditer(blob):
            # gap-1.5 is tokenized as gap-1 only by the integer class; catch gap-[n]/[d]
            return m.group(0)
        if re.search(r"(?<![\w-])(?:[mp](?:[trblxy])?|gap(?:-[xy])?)-\d+\.\d+\b", blob):
            frac = re.search(
                r"(?<![\w-])(?:[mp](?:[trblxy])?|gap(?:-[xy])?)-\d+\.\d+\b",
                blob,
            )
            if frac:
                return frac.group(0)
    return None


def _stack_uses_48(blobs: list[str]) -> bool:
    """flex-col + gap-2/gap-3 and/or p-2/p-3 (or px/py-2/3) on the stack."""
    text = "\n".join(blobs)
    has_col_gap = bool(_STACK_FLEX_COL.search(text) and _STACK_GAP_48.search(text))
    has_pad = bool(_STACK_PAD_48.search(text))
    return has_col_gap or has_pad


def _docs_207_ok(dtxt: str) -> bool:
    """Every bubble stacks identity/time, then body/subject, then attachments."""
    stacked = re.search(
        r"identity\s*/\s*time.{0,120}body\s*/\s*subject.{0,120}attachment",
        dtxt,
        re.I | re.S,
    )
    same = re.search(
        r"("
        r"whatsapp.{0,80}gmail.{0,40}(?:same|stack|order)"
        r"|gmail.{0,80}whatsapp.{0,40}(?:same|stack|order)"
        r"|WA and Gmail"
        r"|the same"
        r")",
        dtxt,
        re.I | re.S,
    )
    if stacked and same:
        # "the same" must sit near the stack sentence, not an unrelated line.
        win = dtxt[max(0, stacked.start() - 80) : stacked.end() + 160]
        if re.search(
            r"("
            r"whatsapp"
            r"|gmail"
            r"|WA and Gmail"
            r"|the same"
            r")",
            win,
            re.I,
        ):
            return True
    for m in re.finditer(r"stack", dtxt, re.I):
        win = dtxt[max(0, m.start() - 100) : m.end() + 220]
        if not re.search(r"identity\s*/\s*time", win, re.I):
            continue
        if not re.search(r"body\s*/\s*subject", win, re.I):
            continue
        if not re.search(r"attachment", win, re.I):
            continue
        if not re.search(r"whatsapp|gmail|\bWA\b|the same", win, re.I):
            continue
        return True
    return False


def _casattach_open(blob: str) -> str:
    m = re.search(r"<CasAttach\b[^>]*>", blob)
    return m.group(0) if m else ""


def _path_has_body_then_attach(blob: str) -> bool:
    """A WA or Gmail branch (or shared tail) keeps body before attach."""
    body = _hook_pos(blob, _BUBBLE_BODY)
    attach = _hook_pos(blob, _BUBBLE_ATTACH)
    cas = _casattach_pos(blob)
    if body >= 0 and attach >= 0 and attach < body:
        return False
    if body >= 0 and cas >= 0 and cas < body:
        return False
    if attach >= 0 and cas >= 0 and attach > cas:
        if _BUBBLE_ATTACH not in _casattach_open(blob):
            return False
    return True


def _cond_is_attach_len(cond: str) -> bool:
    """{#if} that mounts only when attachments.length is truthy."""
    if re.search(r"attachments\s*\??\s*\.\s*length", cond):
        return True
    return bool(re.search(r"\battachments\b", cond) and re.search(r"\blength\b", cond))


def _attach_len_gated(markup: str, pos: int) -> bool:
    for kind, cond, _extra in _template_stack(markup, pos):
        if kind == "if" and _cond_is_attach_len(cond):
            return True
    return False


def _html_open_stack(markup: str, pos: int) -> list[tuple[int, str, str]]:
    """(start, name, attrs) for unclosed HTML/component tags at pos."""
    stack: list[tuple[int, str, str]] = []
    for m in _BUBBLE_HTML_TOKEN.finditer(markup):
        if m.start() >= pos:
            break
        raw = m.group(0)
        if raw.startswith("<!--"):
            continue
        if m.group(1):
            name = m.group(1)
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][1].lower() == name.lower():
                    del stack[i:]
                    break
            continue
        name = m.group(2) or ""
        attrs = m.group(3) or ""
        self_close = raw.rstrip().endswith("/>") or name.lower() in _BUBBLE_VOID
        if self_close:
            continue
        stack.append((m.start(), name, attrs))
    return stack


def _empty_attach_wrapper_name(article: str) -> str | None:
    """Tag name of an always-on attach flex sibling, if any."""
    for m in re.finditer(re.escape(_BUBBLE_ATTACH), article):
        host = _tag_at(article, m.start())
        name = _tag_name(host)
        if name.lower() == "casattach":
            continue
        if name.lower() in {"div", "span"} and not _attach_len_gated(article, m.start()):
            return name
    cas = _casattach_pos(article)
    if cas < 0:
        return None
    for start, name, attrs in reversed(_html_open_stack(article, cas)):
        if name.lower() == "article":
            break
        if _BUBBLE_BODY in attrs or _BUBBLE_META in attrs:
            break
        if name.lower() in {"div", "span"}:
            if not _attach_len_gated(article, start):
                return name
            break
    return None


def _cas_items_ul_open(cas: str) -> str:
    markup = _svelte_markup(cas)
    for m in re.finditer(r"\{#if\s+([^}]+)\}", markup):
        if _CAS_ITEMS_LEN_COND.search(m.group(1)):
            um = re.search(r"<ul\b[^>]*>", markup[m.end() : m.end() + 600])
            if um:
                return um.group(0)
    um = re.search(r"<ul\b[^>]*>", markup)
    return um.group(0) if um else ""


def _ul_mt2_unconditional(ul_open: str) -> bool:
    if _UL_MT2_STATIC.search(ul_open):
        return True
    if _UL_MT2_LIT.search(ul_open) and not re.search(r"\?|&&|\|\|", ul_open):
        return True
    return False


def _cas_default_class_has_mt2(cas: str) -> bool:
    return bool(
        re.search(
            r"""(?:class(?:Name)?\s*:\s*\w+\s*=\s*|class(?:Name)?\s*=\s*)["'][^"']*\bmt-2\b""",
            cas,
        )
    )


def _timeline_cas_drops_mt2(cas: str, article: str, ul_open: str) -> bool:
    """True when the timeline CasAttach instance does not apply ul.mt-2."""
    if _ul_mt2_unconditional(ul_open):
        return False
    cas_open = _casattach_open(article)
    if not _MT2_TOKEN.search(ul_open) and not _cas_default_class_has_mt2(cas):
        return True
    if re.search(r"\b(?:class|className|ulClass|listClass)\b", ul_open + cas):
        cm = re.search(r"""\bclass\s*=\s*["']([^"']*)["']""", cas_open)
        if cm is not None and not _MT2_TOKEN.search(cm.group(1)):
            return True
        dyn = re.search(r"\bclass\s*=\s*\{([^}]+)\}", cas_open)
        if dyn and not _MT2_TOKEN.search(dyn.group(1)):
            return True
    for prop in _NOMARGIN_PROP.findall(cas):
        if not re.search(rf"\b{re.escape(prop)}\b", ul_open + cas_open):
            continue
        if re.search(
            rf"\b{re.escape(prop)}(?:\s*(?:/|>)|\s*=\s*\{{\s*true\s*\}})",
            cas_open,
        ):
            return True
    return False


def _article_has_col_gap23(article: str) -> bool:
    text = "\n".join(_stack_class_blobs(article))
    return bool(_STACK_FLEX_COL.search(text) and _STACK_GAP_48.search(text))

__all__ = [
    "_stack_class_blobs",
    "_odd_stack_token",
    "_stack_uses_48",
    "_docs_207_ok",
    "_casattach_open",
    "_path_has_body_then_attach",
    "_cond_is_attach_len",
    "_attach_len_gated",
    "_html_open_stack",
    "_empty_attach_wrapper_name",
    "_cas_items_ul_open",
    "_ul_mt2_unconditional",
    "_cas_default_class_has_mt2",
    "_timeline_cas_drops_mt2",
    "_article_has_col_gap23",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_HTML_BODY",
    "_function_body",
    "_match_closer",
    "_svelte_markup",
    "_tag_name",
    "_template_stack",
    "_timeline_block",
    "_web_logic",
    "_without_comments",
    "_PRE_WRAP",
    "_SHOW_QUOTED",
    "_JK_KEY",
    "_derived_body",
    "_tag_at",
    "_BUBBLE_META",
    "_BUBBLE_BODY",
    "_BUBBLE_ATTACH",
    "_ODD_STACK_SPACE",
    "_FRAC_STACK_SPACE",
    "_STACK_FLEX_COL",
    "_STACK_GAP_48",
    "_STACK_PAD_48",
    "_CAS_ITEMS_LEN_COND",
    "_UL_MT2_STATIC",
    "_UL_MT2_LIT",
    "_MT2_TOKEN",
    "_NOMARGIN_PROP",
    "_BUBBLE_HTML_TOKEN",
    "_BUBBLE_VOID",
    "_article_open_tag",
    "_hook_pos",
    "_casattach_pos",
]
