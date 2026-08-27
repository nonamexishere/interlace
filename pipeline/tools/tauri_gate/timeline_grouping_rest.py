"""Continuation of timeline_grouping."""
from __future__ import annotations

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
    _GROUPING_COND,
    _FILTERED_PREV,
    _PREV_INDEX,
    _GROUP_HELPER_NAMES,
    _grouping_if_at,
)


def _grouping_uses_filtered_prev(cleaned: str) -> bool:
    if _FILTERED_PREV.search(cleaned):
        return True
    for m in re.finditer(r"filteredTimeline\s*\.\s*map\s*\(", cleaned):
        open_p = m.end() - 1
        close = _match_closer(cleaned, open_p)
        blob = cleaned[open_p : close] if close >= 0 else cleaned[m.end() : m.end() + 800]
        if _PREV_INDEX.search(blob):
            return True
    for name in _GROUP_HELPER_NAMES:
        body = _function_body(cleaned, name)
        if not body:
            continue
        if not _PREV_INDEX.search(body):
            continue
        if re.search(rf"{re.escape(name)}\s*\(\s*filteredTimeline", cleaned):
            return True
        if re.search(r"filteredTimeline", body):
            return True
    return False


def _docs_206_ok(dtxt: str) -> bool:
    """Consecutive same-side / same-conversation / same calendar day share one caption."""
    if not re.search(r"hour:minute", dtxt, re.I):
        return False
    if not re.search(r"platform chip", dtxt, re.I):
        return False
    for m in re.finditer(r"consecutive", dtxt, re.I):
        win = dtxt[max(0, m.start() - 80) : m.end() + 240]
        if not re.search(r"same[- ]side|same[- ]sender|from[_ ]me", win, re.I):
            continue
        if not re.search(r"same[- ]conversation", win, re.I):
            continue
        if not re.search(
            r"same[- ](?:UTC[- ]|calendar[- ])day|same (?:UTC |calendar )?day",
            win,
            re.I,
        ):
            continue
        if not re.search(r"share one|one caption|quieter", win, re.I):
            continue
        return True
    return False


def _casattach_stripped_from_followers(markup: str) -> bool:
    """True if CasAttach only mounts on the run-start branch."""
    hits = list(re.finditer(r"<CasAttach\b", markup))
    if not hits:
        return True
    ungated = [m for m in hits if not _grouping_if_at(markup, m.start())]
    if ungated:
        return False
    kinds = set()
    for m in hits:
        for kind, cond, _extra in _template_stack(markup, m.start()):
            if kind in {"if", "if-else"} and _GROUPING_COND.search(cond):
                kinds.add(kind)
    return not ({"if", "if-else"} <= kinds)


# #207 — one bubble stack: identity/time → body/subject → attachments.
_BUBBLE_META = "data-bubble-meta"
_BUBBLE_BODY = "data-bubble-body"
_BUBBLE_ATTACH = "data-bubble-attach"
_ODD_STACK_SPACE = re.compile(
    r"(?<![\w-])(?:[mp](?:[trblxy])?|gap(?:-[xy])?)-\[(\d+)(?:px)?\]"
)
_FRAC_STACK_SPACE = re.compile(
    r"(?<![\w-])(?:[mp](?:[trblxy])?|gap(?:-[xy])?)-(\d+)-(\d+)\b"
)
_STACK_FLEX_COL = re.compile(r"(?<![\w-])flex-col\b")
_STACK_GAP_48 = re.compile(r"(?<![\w-])gap-[23]\b")
_STACK_PAD_48 = re.compile(r"(?<![\w-])(?:p|px|py|pt|pb|pl|pr)-[23]\b")
_REACTIONS_UI = re.compile(
    r"("
    r">\s*Add reaction\s*<"
    r"|data-reaction(?:s)?\b"
    r"|reaction-bar"
    r"|emoji-picker"
    r")",
    re.I,
)
_NEW_PLATFORM_ON_BUBBLE = re.compile(
    r"""platform\s*===?\s*['\"](?:twitter|slack|discord|telegram|imessage|signal)['\"]""",
    re.I,
)
_SENDER_NAME_ON_BUBBLE = re.compile(
    r"\{[^{}]{0,80}(?:sender_identity_id|senderName|sender_name|senderDisplayName)[^{}]{0,40}\}"
)
_CAS_ITEMS_LEN_COND = re.compile(r"items\s*\??\s*\.\s*length|(?=.*\bitems\b)(?=.*\blength\b).*")
_UL_MT2_STATIC = re.compile(r"""class\s*=\s*["'][^"']*\bmt-2\b""")
_UL_MT2_LIT = re.compile(r"class\s*=\s*\{\s*[`'\"][^`'\"]*\bmt-2\b")
_MT2_TOKEN = re.compile(r"(?<![\w-])mt-2\b")
_NOMARGIN_PROP = re.compile(
    r"\b(?:flush|noMargin|nomargin|compact|tight|dense|bare|plain|noMt|unspaced)\b"
)
_BUBBLE_HTML_TOKEN = re.compile(
    r"<!--.*?-->"
    r"|</([A-Za-z][\w:.-]*)\s*>"
    r"|<([A-Za-z][\w:.-]*)\b([^>]*?)>",
    re.S,
)
_BUBBLE_VOID = frozenset(
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


def _timeline_articles(markup: str) -> list[str]:
    """Person-timeline <article>…</article> blobs (not nested)."""
    out: list[str] = []
    i = 0
    while True:
        m = re.search(r"<article\b", markup[i:], re.I)
        if not m:
            break
        start = i + m.start()
        end = re.search(r"</article\s*>", markup[start:], re.I)
        if not end:
            out.append(markup[start:])
            break
        out.append(markup[start : start + end.end()])
        i = start + end.end()
    return out


def _article_open_tag(article: str) -> str:
    m = re.match(r"<article\b[^>]*>", article, re.I | re.S)
    return m.group(0) if m else ""


def _split_mail_else(article: str) -> tuple[str, str] | None:
    """Mail {#if isMailRow…}{:else} split (skip the caption-only You {#if})."""
    for head in re.finditer(r"\{#if\s+([^}]*isMail[^}]*)\}", article, re.I):
        depth = 0
        then_start = head.end()
        else_start: int | None = None
        then_body = ""
        i = head.start()
        for m in re.finditer(r"\{#if\b|\{:else\s+if\b|\{:else\}|\{/if\}", article[i:]):
            tok = m.group(0)
            abs_at = i + m.start()
            if tok.startswith("{#if"):
                depth += 1
            elif tok.startswith("{:else if"):
                continue
            elif tok.startswith("{:else}"):
                if depth == 1 and else_start is None:
                    else_start = i + m.end()
                    then_body = article[then_start:abs_at]
            else:
                depth -= 1
                if depth == 0:
                    if else_start is None:
                        break
                    return then_body, article[else_start:abs_at]
    return None


def _hook_pos(blob: str, name: str) -> int:
    return blob.find(name)


def _casattach_pos(blob: str) -> int:
    m = re.search(r"<CasAttach\b", blob)
    return m.start() if m else -1


def _attach_wraps_cas(article: str) -> bool:
    """data-bubble-attach is on CasAttach or on a wrapper that precedes it."""
    for m in re.finditer(r"<CasAttach\b[^>]*>", article):
        if _BUBBLE_ATTACH in m.group(0):
            return True
    a = _hook_pos(article, _BUBBLE_ATTACH)
    c = _casattach_pos(article)
    return a >= 0 and c >= 0 and a < c

__all__ = [
    "_standalone_subject_bindings",
    "_SUBJECT_TITLE_HELPER",
    "_MAIL_ROW_GATE",
    "_FROM_ME_LAYOUT",
    "_DAY_HEADING",
    "_CID_IMG",
    "_GROUPING_COND",
    "_CAPTION_MARK",
    "_CAPTION_OMIT_ATTR",
    "_HOVER_ONLY_TIME",
    "_FILTERED_PREV",
    "_PREV_INDEX",
    "_GROUP_DAY_KEY",
    "_NET_AVATAR",
    "_GROUP_HELPER_NAMES",
    "_grouping_if_at",
    "_tag_at",
    "_caption_el_omitted",
    "_hover_only_time",
    "_followers_omit_caption",
    "_grouping_logic_src",
    "_has_three_key_run",
    "_grouping_uses_filtered_prev",
    "_docs_206_ok",
    "_casattach_stripped_from_followers",
    "_BUBBLE_META",
    "_BUBBLE_BODY",
    "_BUBBLE_ATTACH",
    "_ODD_STACK_SPACE",
    "_FRAC_STACK_SPACE",
    "_STACK_FLEX_COL",
    "_STACK_GAP_48",
    "_STACK_PAD_48",
    "_REACTIONS_UI",
    "_NEW_PLATFORM_ON_BUBBLE",
    "_SENDER_NAME_ON_BUBBLE",
    "_CAS_ITEMS_LEN_COND",
    "_UL_MT2_STATIC",
    "_UL_MT2_LIT",
    "_MT2_TOKEN",
    "_NOMARGIN_PROP",
    "_BUBBLE_HTML_TOKEN",
    "_BUBBLE_VOID",
    "_timeline_articles",
    "_article_open_tag",
    "_split_mail_else",
    "_hook_pos",
    "_casattach_pos",
    "_attach_wraps_cas",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_HTML_BODY",
    "_svelte_markup",
    "_timeline_block",
    "_web_logic",
    "_without_comments",
    "_PRE_WRAP",
    "_SHOW_QUOTED",
    "_JK_KEY",
    "annotations",
    "_function_body",
    "_match_closer",
    "_tag_name",
    "_template_stack",
    "_derived_body",
]

__all__ = [
    "_grouping_uses_filtered_prev",
    "_docs_206_ok",
    "_casattach_stripped_from_followers",
    "_BUBBLE_META",
    "_BUBBLE_BODY",
    "_BUBBLE_ATTACH",
    "_ODD_STACK_SPACE",
    "_FRAC_STACK_SPACE",
    "_STACK_FLEX_COL",
    "_STACK_GAP_48",
    "_STACK_PAD_48",
    "_REACTIONS_UI",
    "_NEW_PLATFORM_ON_BUBBLE",
    "_SENDER_NAME_ON_BUBBLE",
    "_CAS_ITEMS_LEN_COND",
    "_UL_MT2_STATIC",
    "_UL_MT2_LIT",
    "_MT2_TOKEN",
    "_NOMARGIN_PROP",
    "_BUBBLE_HTML_TOKEN",
    "_BUBBLE_VOID",
    "_timeline_articles",
    "_article_open_tag",
    "_split_mail_else",
    "_hook_pos",
    "_casattach_pos",
    "_attach_wraps_cas",
    "__all__",
]
