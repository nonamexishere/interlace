"""Timeline grouping / hierarchy chrome asserts. Imported by gate_tauri.py."""
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

from tauri_gate.import_boot import _PRE_WRAP

from tauri_gate.media_linkify import _SHOW_QUOTED


from tauri_gate.timeline_scroll import (
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


def assert_timeline_grouped_runs(crate: Path) -> None:
    """#206: consecutive same from_me + conversation + calendar day share one caption.

    Acceptance: a 5-message run shows one caption then four quieter bubbles.
    Grouping keys off the filtered list (previous index), not only the previous
    windowed row. Day headings stay. Each message stays its own row (j/k).
    Bodies stay text nodes. CasAttach stays on followers. No network avatars.
    Do not soften #111/#112/#113/#115/#120/#205.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#206: App.svelte required (person-timeline caption grouping)")
    app = app_path.read_text()
    logic = _web_logic(crate)
    cleaned = _without_comments(app + "\n" + logic)
    block = _timeline_block(crate)
    markup = _svelte_markup(app)
    pt = markup.find("person-timeline")
    timeline_markup = markup[pt:] if pt >= 0 else markup
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) Followers omit the run caption (or time on hover/focus only).
    #    Grep hook: data-grouped, or {#if} / hidden that skips .caption / chip.
    if not _followers_omit_caption(timeline_markup) and not _followers_omit_caption(block):
        fail(
            "#206: consecutive filtered rows with the same from_me, same "
            "conversation_id, and same calendar day must form a run — run-start "
            "keeps the caption (time + platform chip); followers omit it "
            "(data-grouped, or {#if} that skips .caption / data-platform-chip). "
            "Do not paint a caption on every bubble"
        )

    # 2) Grouping must key off the filtered list, not only the windowed row.
    if not _grouping_uses_filtered_prev(cleaned):
        fail(
            "#206: grouping must key off the filtered list "
            "(filteredTimeline[i-1] / previous filtered index), not only the "
            "previous windowed row — otherwise scrolling mid-run would re-show "
            "captions"
        )

    # 3) Break the run when from_me, conversation_id, or calendar day changes.
    group_src = _grouping_logic_src(cleaned)
    if not _has_three_key_run(group_src) and not _has_three_key_run(cleaned):
        fail(
            "#206: grouping key is from_me + conversation_id + calendar day "
            "(break the run when any of those change). Do not group across "
            "different conversation_id or a different calendar day"
        )
    identity_src = group_src or cleaned
    for m in re.finditer(r"sender_identity_id", identity_src):
        win = identity_src[max(0, m.start() - 280) : m.end() + 280]
        if _GROUPING_COND.search(win) or re.search(r"\bfrom_me\b", win):
            fail(
                "#206: grouping key is from_me + conversation_id + calendar day — "
                "do not invent sender_identity_id (that is #207)"
            )

    # 4) Each message stays its own row; j/k still walks every data-tl-index.
    if not re.search(r"data-tl-index", block):
        fail(
            "#206: each message stays its own row (data-tl-index); "
            "do not collapse a run into one DOM node"
        )
    if not re.search(r"<article\b", block, re.I):
        fail(
            "#206: each message stays its own article row; "
            "do not collapse five messages into one DOM node"
        )
    if not _JK_KEY.search(cleaned):
        fail(
            "#206: do not soften #120 — j/k must still walk every "
            "data-tl-index row"
        )

    # 5) Day headings stay (#112). Run-start still has caption/time/platform (#111/#115).
    if not _DAY_HEADING.search(block):
        fail(
            "#206: do not soften #112 — day headings (day-heading) stay when "
            "the calendar day changes"
        )
    if "caption" not in block.lower() and "<time" not in block.lower():
        fail(
            "#206: do not soften #111 — run-start keeps the caption / <time>"
        )
    if (
        "row.platform" not in block
        and "platformLabel" not in block
        and "data-platform-chip" not in block
    ):
        fail(
            "#206: do not soften #111/#115 — run-start keeps the platform chip"
        )
    if not re.search(r"ESTIMATED_ROW_HEIGHT\s*=\s*88", cleaned):
        fail(
            "#206: do not soften #120/#224 — keep ESTIMATED_ROW_HEIGHT = 88"
        )
    if not re.search(r"\bOVERSCAN\s*=\s*15\b", cleaned):
        fail("#206: do not soften #120/#224 — keep OVERSCAN = 15")
    if "data-partial" not in app and "data-partial" not in logic:
        fail("#206: do not soften #205 — pane Error+Retry (data-partial) stays")

    # 6) Bodies stay text nodes; CasAttach stays on followers.
    if not _PRE_WRAP.search(block):
        fail("#206: bodies stay whitespace-pre-wrap text nodes")
    if _HTML_BODY.search(block) or _HTML_BODY.search(timeline_markup):
        fail("#206: bodies stay text nodes — no {@html}")
    if "displayBody" not in block and "body_text" not in block:
        fail("#206: bodies stay text nodes (displayBody / body_text)")
    if _casattach_stripped_from_followers(timeline_markup):
        fail(
            "#206: do not strip attachments / CasAttach from follower bubbles"
        )

    # 7) No network avatars / Slack-style face pile.
    if _NET_AVATAR.search(timeline_markup) or _NET_AVATAR.search(block):
        fail(
            "#206: no network avatars (no http(s) <img> / slack avatar / "
            "CDN face pile)"
        )

    # 8) D24: consecutive same-side / same-conversation / same calendar day share one caption.
    if not dtxt.strip():
        fail(
            "#206: docs/user/app.md required — consecutive same-side / "
            "same-conversation / same-calendar-day bubbles share one caption "
            "(keep the existing hour:minute + platform chip sentence)"
        )
    if not _docs_206_ok(dtxt):
        fail(
            "#206: docs/user/app.md must say consecutive same-side / "
            "same-conversation / same-calendar-day bubbles share one caption "
            "(keep the existing hour:minute + platform chip sentence for "
            "the run-start)"
        )


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


def assert_timeline_bubble_hierarchy(crate: Path) -> None:
    """#207: identity/time → body/subject → attachments on every bubble.

    WA and Gmail share that stack. Attachments never sit above the body.
    4/8 spacing on the stack. Followers may omit data-bubble-meta (#206).
    Do not soften #111/#117/#206/#120/#205. Not HTML mail / reactions /
    new platforms / sender_identity_id.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#207: App.svelte required (person-timeline bubble stack)")
    app = app_path.read_text()
    logic = _web_logic(crate)
    cleaned = _without_comments(app + "\n" + logic)
    block = _timeline_block(crate)
    markup = _svelte_markup(app)
    pt = markup.find("person-timeline")
    timeline_markup = markup[pt:] if pt >= 0 else markup
    articles = _timeline_articles(timeline_markup) or _timeline_articles(block)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    if not articles:
        fail("#207: person-timeline must render each message as an <article>")
    article = articles[0]

    # 1) Named stack hooks so the gate can see the order.
    have = {
        _BUBBLE_META: _hook_pos(article, _BUBBLE_META) >= 0,
        _BUBBLE_BODY: _hook_pos(article, _BUBBLE_BODY) >= 0,
        _BUBBLE_ATTACH: _hook_pos(article, _BUBBLE_ATTACH) >= 0,
    }
    missing = [name for name, ok in have.items() if not ok]
    if missing:
        fail(
            "#207: person-timeline <article> must name one stack with "
            "data-bubble-meta (identity/time), data-bubble-body (body/subject), "
            "and data-bubble-attach (CasAttach) — missing "
            + ", ".join(missing)
            + ". Source order on the article must be meta, then body, then "
            "attach. WA (isMailRow false) and Gmail (isMailRow true) share "
            "that order. Followers may omit data-bubble-meta (#206)"
        )

    meta_at = _hook_pos(article, _BUBBLE_META)
    body_at = _hook_pos(article, _BUBBLE_BODY)
    attach_at = _hook_pos(article, _BUBBLE_ATTACH)
    cas_at = _casattach_pos(article)

    # 2) Source order: meta → body → attach (meta may be gated for #206).
    if not (meta_at < body_at < attach_at):
        fail(
            "#207: source order on the person-timeline <article> must be "
            "data-bubble-meta, then data-bubble-body, then data-bubble-attach "
            "(identity/time → body/subject → attachments)"
        )

    # 3) CasAttach / attachments must not sit above the body wrapper.
    if cas_at >= 0 and cas_at < body_at:
        fail(
            "#207: CasAttach / attachments must not appear above the "
            "data-bubble-body wrapper in the person-timeline <article>"
        )
    if not _attach_wraps_cas(article):
        fail(
            "#207: data-bubble-attach must wrap CasAttach "
            "(attribute on CasAttach or on a wrapper that precedes it)"
        )

    # 4) WA and Gmail share that order (mail if / else both keep body before attach).
    branches = _split_mail_else(article)
    if branches:
        mail_br, wa_br = branches
        # Shared hooks wrapping both branches sit outside; each branch
        # must not reverse body/attach if it names them or mounts CasAttach.
        if mail_br and not _path_has_body_then_attach(mail_br):
            fail(
                "#207: Gmail (isMailRow true) path must keep data-bubble-body "
                "before data-bubble-attach / CasAttach — same stack as WA"
            )
        if wa_br and not _path_has_body_then_attach(wa_br):
            fail(
                "#207: WA (isMailRow false) path must keep data-bubble-body "
                "before data-bubble-attach / CasAttach — same stack as Gmail"
            )
        # Shared wrapper sits outside both branches; otherwise each branch
        # must name data-bubble-body (subject+quoted vs WA plain).
        mail_has = _BUBBLE_BODY in mail_br
        wa_has = _BUBBLE_BODY in wa_br
        body_wraps_both = (not mail_has) and (not wa_has) and body_at >= 0
        if not body_wraps_both and not (mail_has and wa_has):
            fail(
                "#207: WA and Gmail must share the same stack — put "
                "data-bubble-body around subject+body+quoted and the WA "
                "plain body (one wrapper, or the hook on both branches)"
            )
    elif _MAIL_ROW_GATE.search(article) is None and _MAIL_ROW_GATE.search(block):
        # Mail gate lives in script; both platforms still share one article stack.
        pass
    else:
        # No isMail split: one body path is fine if hooks are ordered.
        pass

    # 5) 4/8 spacing on the bubble stack — no odd arbitrary padding.
    stack_blobs = _stack_class_blobs(article)
    odd = _odd_stack_token(stack_blobs)
    if odd:
        fail(
            f"#207: bubble stack spacing must stay on the 4/8 scale "
            f"(gap-2 / gap-3, p-2 / p-3) — not {odd}"
        )
    if not _stack_uses_48(stack_blobs):
        fail(
            "#207: bubble stack must use 4/8 spacing "
            "(flex-col + gap-2/gap-3 and/or p-2/p-3 on the <article> or a "
            "flex-col wrapper). Do not change ESTIMATED_ROW_HEIGHT"
        )

    # 6) #111 stays: from_me left/right, run-start caption/<time>+platform,
    #    whitespace-pre-wrap, long URLs wrap.
    if not _FROM_ME_LAYOUT.search(block):
        fail(
            "#207: do not soften #111 — from_me must still choose a "
            "right/left bubble"
        )
    if "caption" not in block.lower() and "<time" not in block.lower():
        fail(
            "#207: do not soften #111 — run-start keeps the caption / <time>"
        )
    if (
        "row.platform" not in block
        and "platformLabel" not in block
        and "data-platform-chip" not in block
    ):
        fail(
            "#207: do not soften #111 — run-start keeps the platform chip"
        )
    if not _PRE_WRAP.search(block):
        fail("#207: do not soften #111 — bodies stay whitespace-pre-wrap")
    if not (
        "break-words" in block
        or "overflow-wrap" in block
        or "break-all" in block
    ):
        fail("#207: do not soften #111 — long URLs still wrap (break-words)")

    # 7) #117 stays: mail subject title, Show quoted, no {@html}, no cid:.
    if not (
        _standalone_subject_bindings(block)
        or _SUBJECT_TITLE_HELPER.search(block)
        or re.search(r"mail-subject|data-mail-subject", block, re.I)
    ):
        fail("#207: do not soften #117 — mail subject title stays")
    if not _SHOW_QUOTED.search(block) and not _SHOW_QUOTED.search(timeline_markup):
        fail("#207: do not soften #117 — Show quoted stays")
    if _HTML_BODY.search(block) or _HTML_BODY.search(article):
        fail("#207: do not soften #117 — no {@html} for bodies (not HTML mail)")
    if _CID_IMG.search(block) or _CID_IMG.search(article):
        fail("#207: do not soften #117 — no cid: images")

    # 8) #206 stays: followers may omit data-bubble-meta / caption.
    if not _followers_omit_caption(timeline_markup) and not _followers_omit_caption(block):
        fail(
            "#207: do not soften #206 — followers may omit data-bubble-meta / "
            "the caption; do not paint identity/time on every bubble"
        )

    # 9) #120 88/15 and #205 data-partial stay. Do not require a new height.
    if not re.search(r"ESTIMATED_ROW_HEIGHT\s*=\s*88", cleaned):
        fail("#207: do not soften #120 — keep ESTIMATED_ROW_HEIGHT = 88")
    if not re.search(r"\bOVERSCAN\s*=\s*15\b", cleaned):
        fail("#207: do not soften #120 — keep OVERSCAN = 15")
    if "data-partial" not in app and "data-partial" not in logic:
        fail("#207: do not soften #205 — pane Error+Retry (data-partial) stays")

    # 10) Not in scope.
    if re.search(r"\bsender_identity_id\b", article):
        fail(
            "#207: not in scope — do not add sender_identity_id on the bubble "
            "(no new IPC / sender display-name)"
        )
    if _SENDER_NAME_ON_BUBBLE.search(article):
        fail(
            "#207: not in scope — do not invent a sender display-name on the "
            "bubble (identity is from_me + the caption row)"
        )
    if _REACTIONS_UI.search(article) or _REACTIONS_UI.search(timeline_markup):
        fail("#207: not in scope — no reactions UI")
    if _NEW_PLATFORM_ON_BUBBLE.search(article):
        fail("#207: not in scope — no new platforms on the bubble")

    # 11) D24: keep #111/#117/#206 sentences; add the shared stack line.
    if not dtxt.strip():
        fail(
            "#207: docs/user/app.md required — every bubble stacks "
            "identity/time, then body/subject, then attachments "
            "(WA and Gmail the same)"
        )
    if not re.search(r"Long URLs wrap", dtxt):
        fail("#207: do not drop the #111 wrap sentence in docs/user/app.md")
    if not re.search(r"whitespace-pre-wrap", dtxt):
        fail(
            "#207: do not drop the #111 whitespace-pre-wrap sentence in "
            "docs/user/app.md"
        )
    if not re.search(r"hour:minute", dtxt, re.I):
        fail(
            "#207: do not drop the #111 hour:minute caption sentence in "
            "docs/user/app.md"
        )
    if not re.search(r"Show quoted", dtxt):
        fail("#207: do not drop the #117 fold sentence in docs/user/app.md")
    if not _docs_206_ok(dtxt):
        fail(
            "#207: do not drop the #206 consecutive-caption sentence in "
            "docs/user/app.md"
        )
    if not _docs_207_ok(dtxt):
        fail(
            "#207: docs/user/app.md must say every bubble stacks "
            "identity/time, then body/subject, then attachments "
            "(WA and Gmail the same)"
        )


def assert_timeline_attach_slot(crate: Path) -> None:
    """#207 follow-up: no empty attach flex sibling; no gap-2 + ul.mt-2.

    Person-timeline must not keep an always-on empty attach wrapper. Hook
    on <CasAttach> (empty component is not a flex item) or wrap it in
    {#if item.row.attachments?.length}. Timeline body-to-attach spacing
    is only the article gap-2/gap-3 — CasAttach ul.mt-2 must not stack
    on the timeline call. SearchPane may keep mt-2. Do not soften the
    #207 stack-order hooks or #111/#117/#206/#120/#205.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#207: App.svelte required (person-timeline attach slot)")
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail("#207: CasAttach.svelte required (timeline attach slot / gap)")
    app = app_path.read_text()
    cas = cas_path.read_text()
    markup = _svelte_markup(app)
    pt = markup.find("person-timeline")
    timeline_markup = markup[pt:] if pt >= 0 else markup
    block = _timeline_block(crate)
    articles = _timeline_articles(timeline_markup) or _timeline_articles(block)
    if not articles:
        fail("#207: person-timeline must render each message as an <article>")

    empty_name: str | None = None
    double_gap = False
    ul_open = _cas_items_ul_open(cas)
    for article in articles:
        if empty_name is None:
            empty_name = _empty_attach_wrapper_name(article)
        if _article_has_col_gap23(article) and not _timeline_cas_drops_mt2(
            cas, article, ul_open
        ):
            double_gap = True

    problems: list[str] = []
    if empty_name:
        problems.append(
            "person-timeline must not keep an always-on empty attach flex "
            f"sibling — data-bubble-attach is on a wrapper <{empty_name}> "
            "that is not gated by attachments length and is not <CasAttach> "
            "itself (put the hook on <CasAttach>, or wrap it in "
            "{#if item.row.attachments?.length})"
        )
    if double_gap:
        problems.append(
            "timeline body-to-attach must not stack article gap-2/gap-3 "
            "plus CasAttach inner mt-2 (drop ul.mt-2 on the timeline "
            "CasAttach via a no-margin prop/class; SearchPane may keep mt-2)"
        )
    if problems:
        fail("#207: " + "; ".join(problems))
