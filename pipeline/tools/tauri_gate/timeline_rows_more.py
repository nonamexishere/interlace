"""Additional timeline_rows asserts."""
from __future__ import annotations

from tauri_gate.timeline_rows_lib import *


def assert_gmail_timeline_rows(crate: Path) -> None:
    """#117: Gmail/email_thread rows — subject title, fold quotes; WA plain.

    Acceptance: long reply chains stay one screen until “Show quoted” expands.
    Subject is a title on mail rows (not only body_text||subject fallback).
    Body stays text nodes (whitespace-pre-wrap / plain); no {@html}, no cid:
    images, no send/compose chrome. WhatsApp / non-mail rows keep a plain body
    path and are not forced through the mail layout.
    """
    app = _web_logic(crate)
    logic = _web_logic(crate)
    block = _timeline_block(crate)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    whole = app + "\n" + logic
    cleaned = _without_comments(whole)
    detail = _person_detail_markup(app)
    timeline_chrome = block + "\n" + detail

    # 1) Mail-aware path: gmail platform and/or email_thread kind.
    if not _MAIL_ROW_GATE.search(cleaned) and not _MAIL_ROW_GATE.search(block):
        fail(
            "#117: email_thread / gmail timeline rows need a mail-aware path "
            "(platform === \"gmail\" and/or conversation_kind === \"email_thread\", "
            "isMail/isEmail helper, or {#if row.subject} title branch) — "
            "subject title + quote fold only apply there"
        )

    # 2) Subject shown as a title on mail rows — not only body_text || subject.
    standalone_subjects = _standalone_subject_bindings(block)
    has_subject_title = bool(standalone_subjects) or bool(
        _SUBJECT_TITLE_HELPER.search(block)
    )
    if not has_subject_title:
        has_subject_title = bool(
            re.search(
                r"(?:subjectTitle|mailSubject|emailSubject|rowSubject|displaySubject|"
                r"mail-subject|data-mail-subject)"
                r"[\s\S]{0,200}"
                r"(?:\.subject\b|row\.subject)"
                r"|(?:function|const|let)\s+(?:subjectTitle|mailSubject|emailSubject|"
                r"displaySubject)\b",
                cleaned,
                re.I,
            )
        )
    # Title may live in a small child component used from the row.
    if not has_subject_title:
        has_subject_title = bool(
            re.search(
                r"<(?:MailBubble|EmailBubble|GmailRow|MailRow|MailBody)\b[^>]{0,200}"
                r"subject",
                block + "\n" + blob,
                re.I,
            )
        )
    if not has_subject_title:
        fail(
            "#117: for email_thread / gmail, show subject as a title on the bubble "
            "(bind row.subject / mailSubject as its own text node), not only as "
            "displayBody(body_text || subject) fallback"
        )

    # If the only subject use in the row is still the body fallback, fail even
    # when a helper name exists elsewhere (Search hits subject).
    if _SUBJECT_BODY_FALLBACK_ONLY.search(block) and not standalone_subjects:
        if not _SUBJECT_TITLE_HELPER.search(block) and not re.search(
            r"subjectTitle|mailSubject|emailSubject|displaySubject|data-mail-subject",
            block,
            re.I,
        ):
            fail(
                "#117: subject must be a title on mail rows — "
                "body_text || subject alone is the body fallback, not a title"
            )

    # Subject title must be reachable from the mail gate (not a global force that
    # rewrites WhatsApp). Prefer an isMail / gmail / email_thread condition near
    # the subject surface, or a helper that only returns subject for mail rows.
    mail_subject_ok = bool(
        re.search(
            r"(?:isMail|isEmail|isGmail|mailRow|emailRow|"
            r"platform\s*===?\s*[\"']gmail[\"']|"
            r"conversation_kind\s*===?\s*[\"']email_thread[\"'])"
            r"[\s\S]{0,500}"
            r"(?:\.subject\b|subjectTitle|mailSubject|emailSubject|displaySubject|"
            r"data-mail-subject|mail-subject)"
            r"|(?:\.subject\b|subjectTitle|mailSubject|emailSubject|displaySubject|"
            r"data-mail-subject|mail-subject)"
            r"[\s\S]{0,500}"
            r"(?:isMail|isEmail|isGmail|mailRow|emailRow|"
            r"platform\s*===?\s*[\"']gmail[\"']|"
            r"conversation_kind\s*===?\s*[\"']email_thread[\"'])",
            cleaned,
            re.I,
        )
    ) or bool(
        re.search(
            r"(?:subjectTitle|mailSubject|displaySubject|emailSubject)\s*=\s*"
            r"(?:function|\([^)]*\)\s*=>|\$derived)",
            cleaned,
            re.I,
        )
    )
    if not mail_subject_ok:
        # Markup {#if isMail} … {row.subject} is enough when both tokens are in block.
        if not (
            _MAIL_ROW_GATE.search(block + "\n" + cleaned)
            and (
                standalone_subjects
                or _SUBJECT_TITLE_HELPER.search(block)
                or re.search(
                    r"subjectTitle|mailSubject|emailSubject|data-mail-subject",
                    block,
                    re.I,
                )
            )
        ):
            fail(
                "#117: subject-as-title must be gated to email_thread / gmail "
                "(do not force a mail subject title onto every WhatsApp bubble)"
            )

    # 3) Quoted tails collapsed behind “Show quoted” (or similar expand control).
    if not _SHOW_QUOTED.search(blob) and not _SHOW_QUOTED.search(cleaned):
        fail(
            "#117: fold quoted reply tails behind an expand control "
            "(“Show quoted” / showQuoted / data-show-quoted) so a long chain "
            "is one screen until expanded"
        )
    if not _QUOTE_SPLIT.search(cleaned):
        fail(
            "#117: split mail body on common quote markers "
            "(“On … wrote:”, lines starting with “>”) — pure text split / "
            "quoteTail / splitQuoted helper is fine; still text nodes, not HTML"
        )
    # Expand control must sit on the timeline / person detail, not only Search.
    if not _SHOW_QUOTED.search(timeline_chrome) and not _SHOW_QUOTED.search(block):
        # Allow control label only in script if data-show-quoted / toggle is in row.
        if not re.search(
            r"(?:showQuoted|quotedExpanded|expandQuoted|data-show-quoted|"
            r"quotedTail|quoteTail|splitQuoted)",
            block + "\n" + timeline_chrome,
            re.I,
        ):
            fail(
                "#117: “Show quoted” (or the quote expand toggle) must be on the "
                "person timeline bubble for mail rows, not only in Search/Review"
            )

    # 4) Body remains text nodes — no {@html} for mail body; pre-wrap / plain ok.
    if _HTML_BODY.search(block) or _HTML_BODY.search(timeline_chrome):
        fail(
            "#117: mail body must stay text nodes (whitespace-pre-wrap or plain) — "
            "no {@html} for the message body (not HTML MIME layout)"
        )
    # Timeline body still needs a readable text surface (#111 pre-wrap or plain).
    if not re.search(r"whitespace-pre-wrap|whitespace-pre\b", block) and not re.search(
        r"\{(?:displayBody|mainBody|visibleBody|unquotedBody|bodyWithoutQuote|"
        r"(?:item\.)?row\.body_text)[^}]*\}",
        block,
    ):
        fail(
            "#117: timeline body must remain a text binding "
            "(whitespace-pre-wrap / plain text node), including after quote fold"
        )

    # 5) No cid: remote images; no send/compose chrome on the person timeline.
    if _CID_IMG.search(timeline_chrome) or _CID_IMG.search(block):
        fail("#117: no cid: images in the person timeline (not HTML MIME / inline cid)")
    if re.search(
        r"<img\b[^>]{0,200}src\s*=\s*[\"'](?:cid:|https?://)",
        timeline_chrome + "\n" + block,
        re.I | re.S,
    ):
        fail("#117: timeline must not render remote or cid: <img> for mail bodies")
    if _SEND_MAIL_UI.search(timeline_chrome) or _SEND_MAIL_UI.search(block):
        fail(
            "#117: no send / compose mail UI on the person timeline "
            "(read-only archive — fold quotes only, do not add reply chrome)"
        )

    # 6) WhatsApp / non-mail path stays plain body — not forced through mail layout.
    # Require either an explicit {:else} / !isMail branch, or that mail-only helpers
    # do not wrap every row (subject title + show-quoted only under mail gate).
    wa_plain = bool(_WA_PLAIN_BODY.search(block + "\n" + cleaned))
    # Plain body_text for non-mail: displayBody(body_text) without requiring subject title.
    plain_body_binding = bool(
        re.search(
            r"(?:displayBody\s*\(\s*(?:(?:item\.)?row\.)?body_text"
            r"|\{(?:(?:item\.)?row\.)?body_text\s*\}\s*)",
            block,
        )
    )
    if not (wa_plain and plain_body_binding) and not (
        _MAIL_ROW_GATE.search(cleaned)
        and plain_body_binding
        and re.search(r"\{:else\b", block)
    ):
        # Soften: if quote fold / subject title are clearly mail-gated, WA inherits
        # the existing pre-wrap body_text path from #111.
        if not (
            _MAIL_ROW_GATE.search(cleaned)
            and (
                re.search(r"body_text", block)
                or re.search(r"displayBody", block)
            )
            and not re.search(
                r"(?:showQuoted|Show quoted|subjectTitle|mailSubject)"
                r"[^;]{0,120}(?:whatsapp|for\s+each|every\s+row)",
                cleaned,
                re.I,
            )
        ):
            fail(
                "#117: WhatsApp / non-mail rows must keep a plain body path "
                "(body_text / displayBody) and must not be forced through the "
                "mail subject-title + quote-fold layout"
            )
