"""Timeline grouping / hierarchy chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.timeline_grouping import *
from tauri_gate.timeline_attach import *


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
    app = _web_logic(crate)
    logic = app
    cleaned = _without_comments(app)
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
    app = _web_logic(crate)
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
    app = _web_logic(crate)
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
