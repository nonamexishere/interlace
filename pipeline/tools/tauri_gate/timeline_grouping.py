"""Helpers extracted from timeline_hierarchy.py (timeline_grouping)."""
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


def _standalone_subject_bindings(block: str) -> list[str]:
    """{…row.subject…} expressions that are titles, not body_text||subject."""
    out: list[str] = []
    for m in re.finditer(
        r"\{([^{}]{0,160}(?:item\.)?row\.subject[^{}]{0,80})\}",
        block,
    ):
        expr = m.group(1)
        if "body_text" in expr and "||" in expr:
            continue
        if re.search(r"body_text\s*\|\|", expr):
            continue
        if re.search(r"displayBody\s*\(", expr) and "||" in expr:
            continue
        out.append(expr)
    return out
# Standalone subject title binding — not body_text || subject body fallback.
_SUBJECT_TITLE_HELPER = re.compile(
    r"("
    r"\{[^}]{0,80}(?:subjectTitle|mailSubject|emailSubject|"
    r"rowSubject|displaySubject)[^}]{0,40}\}"
    r"|data-mail-subject"
    r"|class=[\"'][^\"']*\b(?:mail-)?subject\b"
    r"|class:(?:mail-)?subject\b"
    r")",
    re.I,
)


# #117 — Gmail / email_thread timeline rows: subject title + fold quoted tails.
_MAIL_ROW_GATE = re.compile(
    r"("
    r"(?:platform|row\.platform|\.platform)\s*===?\s*[\"']gmail[\"']"
    r"|[\"']gmail[\"']\s*===?\s*(?:platform|row\.platform|\.platform)"
    r"|(?:conversation_kind|row\.conversation_kind|\.conversation_kind)"
    r"\s*===?\s*[\"']email_thread[\"']"
    r"|[\"']email_thread[\"']\s*===?\s*"
    r"(?:conversation_kind|row\.conversation_kind|\.conversation_kind)"
    r"|\bisMail(?:Row|Bubble|Message)?\b"
    r"|\bisEmail(?:Row|Bubble|Message|Thread)?\b"
    r"|\bisGmail(?:Row|Bubble|Message)?\b"
    r"|\bmailRow\b"
    r"|\bemailRow\b"
    # Subject present ⇒ mail-ish title branch (WA subjects are null).
    r"|\{#if\s+[^}]{0,120}(?:item\.)?row\.subject\b"
    r"|(?:item\.)?row\.subject\s*(?:\?\.|\.)?trim\s*\([^)]*\)\s*(?:&&|\?)"
    r"|(?:item\.)?row\.subject\s*&&"
    r")",
    re.I,
)


# #111 — person timeline is a chat (me right / them left), not a metadata log.
_FROM_ME_LAYOUT = re.compile(
    r"(data-from-me\s*=\s*\{(?:\w+\.)?row\.from_me\}"
    r"|class:[A-Za-z0-9_-]+\s*=\s*\{!?(?:\w+\.)?row\.from_me\}"
    r"|class=\{[^}]*row\.from_me[^}]*\})",
)

# #112 — day heading when the calendar day of sent_at changes.
_DAY_HEADING = re.compile(
    r"(<h[2-4]\b"
    r"|role\s*=\s*[\"']heading[\"']"
    r"|day-heading"
    r"|day-separator"
    r"|day-sep\b"
    r"|data-day-heading)",
    re.I,
)
_CID_IMG = re.compile(
    r"("
    r"cid:"
    r"|src\s*=\s*[\"']cid:"
    r"|src\s*=\s*\{[^}]*cid:"
    r")",
    re.I,
)




# #206 — group consecutive same-side / same-conversation / same-calendar-day bubbles.
# Static: followers omit the run caption; grouping keys off filteredTimeline[i-1].
_GROUPING_COND = re.compile(
    r"("
    r"\bgrouped\b"
    r"|\bisGrouped(?:Follower|Row)?"
    r"|\brunStart\b|\bisRunStart\b"
    r"|\bfirstOfRun\b|\bisFirst(?:InRun|OfRun)\b"
    r"|\bshowCaption\b|\bhideCaption\b|\bcaptionVisible\b"
    r"|\bisFollower\b"
    r"|\bsameRun\b|\binSameRun\b|\bisSameRun\b|\bsameCaptionRun\b"
    r"|\bgroupStart\b|\bisGroupStart\b|\bfirstInGroup\b"
    r"|\brunHead\b|\bisRunHead\b"
    r")",
    re.I,
)
_CAPTION_MARK = re.compile(
    r"("
    r"class\s*=\s*[\"'][^\"']*\bcaption\b"
    r"|data-platform-chip"
    r"|<time\b"
    r")",
    re.I,
)
_CAPTION_OMIT_ATTR = re.compile(
    r"("
    r"class:hidden\s*=\s*\{[^}]{0,80}"
    r"(?:grouped|isFollower|isGrouped|!?\s*(?:runStart|showCaption|firstOfRun))"
    r"|hidden\s*=\s*\{[^}]{0,80}"
    r"(?:grouped|isFollower|isGrouped|!?\s*(?:runStart|showCaption|firstOfRun))"
    r"|class:opacity-0\s*=\s*\{[^}]{0,80}(?:grouped|isFollower|isGrouped)"
    r")",
    re.I,
)
_HOVER_ONLY_TIME = re.compile(
    r"("
    r"hover:opacity"
    r"|focus(?:-visible)?:opacity"
    r"|hover:visible"
    r"|focus(?:-visible)?:visible"
    r"|group-hover:"
    r"|group-focus:"
    r")",
    re.I,
)
_FILTERED_PREV = re.compile(
    r"filteredTimeline\s*(?:"
    r"\[[^\]]{0,80}-\s*1\s*\]"
    r"|\.at\s*\(\s*[^)]{0,60}-\s*1\s*\)"
    r")",
    re.I,
)
_PREV_INDEX = re.compile(
    r"("
    r"\[[^\]]{0,60}-\s*1\s*\]"
    r"|\.at\s*\(\s*[^)]{0,40}-\s*1\s*\)"
    r"|\bprev(?:ious)?(?:Row|Item|Msg|Filtered)?\b"
    r")",
    re.I,
)
_GROUP_DAY_KEY = re.compile(
    r"\butcDay\b|\butc_day\b|\blocalDay\b|\blocal_day\b|\bhostDay\b|"
    r"\bcalendarDay\b|\bdayKey\b|\bisoDay\b"
)
_NET_AVATAR = re.compile(
    r"("
    r"<img\b[^>]{0,400}src\s*=\s*[\"']https?://"
    r"|src\s*=\s*\{[^}]{0,160}https?://"
    r"|slack[-_]?avatar"
    r"|gravatar"
    r"|cdn\.slack"
    r"|face[-_]?pile"
    r")",
    re.I | re.S,
)
_GROUP_HELPER_NAMES = (
    "sameCaptionRun",
    "isGroupedFollower",
    "isRunFollower",
    "sameRun",
    "inSameRun",
    "isSameRun",
    "isCaptionGrouped",
    "groupedWithPrev",
    "isFollower",
    "isGrouped",
    "runStart",
    "isRunStart",
    "firstOfRun",
    "showCaption",
    "sameSenderRun",
)


def _grouping_if_at(markup: str, pos: int) -> bool:
    for kind, cond, _extra in _template_stack(markup, pos):
        if kind in {"if", "if-else"} and _GROUPING_COND.search(cond):
            return True
    return False


def _tag_at(markup: str, pos: int) -> str:
    start = markup.rfind("<", 0, pos + 1)
    if start < 0:
        return ""
    end = markup.find(">", start)
    if end < 0:
        return ""
    return markup[start : end + 1]


def _caption_el_omitted(markup: str, pos: int) -> bool:
    tag = _tag_at(markup, pos)
    if tag and _CAPTION_OMIT_ATTR.search(tag):
        return True
    # Chip / <time> may sit inside <p class="caption" hidden={grouped}>.
    start = markup.rfind("<", 0, pos + 1)
    if start <= 0:
        return False
    parent = _tag_at(markup, start - 1)
    return bool(parent and _CAPTION_OMIT_ATTR.search(parent))


def _hover_only_time(markup: str, pos: int) -> bool:
    tag = _tag_at(markup, pos)
    if tag and _HOVER_ONLY_TIME.search(tag):
        return True
    start = markup.rfind("<", 0, pos + 1)
    if start <= 0:
        return False
    parent = _tag_at(markup, start - 1)
    return bool(parent and _HOVER_ONLY_TIME.search(parent))


def _followers_omit_caption(markup: str) -> bool:
    """True when run-start can show time+chip and followers can skip that caption."""
    has_gated_caption = False
    for m in _CAPTION_MARK.finditer(markup):
        token = m.group(0)
        gated = _grouping_if_at(markup, m.start()) or _caption_el_omitted(markup, m.start())
        if gated:
            has_gated_caption = True
            continue
        is_time = token.lower().startswith("<time")
        if is_time and _hover_only_time(markup, m.start()):
            continue
        # Ungated .caption / chip / always-visible <time> — every bubble still
        # paints the run caption.
        return False
    return has_gated_caption or bool(re.search(r"\bdata-grouped\b", markup, re.I))


def _grouping_logic_src(cleaned: str) -> str:
    parts: list[str] = []
    for name in _GROUP_HELPER_NAMES:
        body = _function_body(cleaned, name)
        if body:
            parts.append(body)
        derived = _derived_body(cleaned, name)
        if derived:
            parts.append(derived)
    w = _derived_body(cleaned, "windowedDayGroups")
    if w and re.search(r"from_me|grouped|conversation_id", w):
        parts.append(w)
    return "\n".join(parts)


def _has_three_key_run(src: str) -> bool:
    """from_me + conversation_id + calendar day compared against a previous row."""
    for m in re.finditer(r"conversation_id", src):
        win = src[max(0, m.start() - 500) : m.end() + 500]
        if not re.search(r"\bfrom_me\b", win):
            continue
        if not _GROUP_DAY_KEY.search(win):
            continue
        if not _PREV_INDEX.search(win):
            continue
        return True
    return False

from tauri_gate.timeline_grouping_rest import (
    _grouping_uses_filtered_prev,
    _docs_206_ok,
    _casattach_stripped_from_followers,
    _BUBBLE_META,
    _BUBBLE_BODY,
    _BUBBLE_ATTACH,
    _ODD_STACK_SPACE,
    _FRAC_STACK_SPACE,
    _STACK_FLEX_COL,
    _STACK_GAP_48,
    _STACK_PAD_48,
    _REACTIONS_UI,
    _NEW_PLATFORM_ON_BUBBLE,
    _SENDER_NAME_ON_BUBBLE,
    _CAS_ITEMS_LEN_COND,
    _UL_MT2_STATIC,
    _UL_MT2_LIT,
    _MT2_TOKEN,
    _NOMARGIN_PROP,
    _BUBBLE_HTML_TOKEN,
    _BUBBLE_VOID,
    _timeline_articles,
    _article_open_tag,
    _split_mail_else,
    _hook_pos,
    _casattach_pos,
    _attach_wraps_cas,
    __all__,
)

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
]
