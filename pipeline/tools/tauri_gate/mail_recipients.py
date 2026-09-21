"""#374 — To/Cc/Bcc on mail bubbles (People timeline + inspector).

Confirmed mix (2026-09-21): identity display_name then value; To-role only
on the bubble; 3 +k; hide empty To; attach_recipients on TimelineRow JSON
(names-only to / cc / bcc string arrays); inspector from timeline[tlIndex]
when open; People only; include Self; To line after data-mail-labels.
Keep #364 / #373 / #372 / #317 / #322.

Not persons.display_name. Not extra IPC. Not Search preview. Not omit Self.

Placeholders Ada / Berk / Self. Same ChromeKey on en.ts + tr.ts.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.last_read import _text, _web_file
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.media_linkify_lib import _hook_element_blocks
from tauri_gate.people_inspector_lib import _inspector_ident_each
from tauri_gate.scan import (
    _function_body,
    _match_closer,
    _rust_fn_signature,
    _rust_function_body,
    _svelte_markup,
    _tauri_rust_blob,
    _ts_fn_body,
    _without_comments,
)
from tauri_gate.timeline_gmail_labels import (
    _BUBBLE_BODY,
    _BUBBLE_META,
    _CHIP_HOOK,
    _EST88,
    _INVOKE,
    _IS_MAIL,
    _MAIL_SUBJECT,
    _caption_block,
    _mail_else_blocks,
    _people_core_blob,
    _rust_struct_body,
    _svelte_if_else,
    _ts_type_body,
)

_ISSUE = "#374"

_TO_HOOK = re.compile(r"\bdata-mail-to\b")
_RECIP_HOOK = re.compile(r"\bdata-mail-recipients\b")
_GROUP_HOOK = re.compile(r"\bdata-group-participants\b")
_MAIL_TO_T = re.compile(r"""t\s*\(\s*["']mailTo["']\s*\)""")
_MAIL_CC_T = re.compile(r"""t\s*\(\s*["']mailCc["']\s*\)""")
_MAIL_BCC_T = re.compile(r"""t\s*\(\s*["']mailBcc["']\s*\)""")
_SEARCH_TO_T = re.compile(r"""t\s*\(\s*["']searchTo["']\s*\)""")
_OPEN_ORIG_T = re.compile(r"""t\s*\(\s*["']openOriginal["']\s*\)""")
_SEARCH_THIS_T = re.compile(r"""t\s*\(\s*["']searchThisConversation["']\s*\)""")
_SEARCH_T = re.compile(r"""t\s*\(\s*["']search["']\s*\)""")
_T_OPEN = re.compile(r"""\bt\s*\(\s*["']open["']\s*\)""")
_INNERHTML = re.compile(r"\binnerHTML\b|\{@html\b")
_LINKIFY = re.compile(r"\bLinkifyBody\b")
_BADGE = re.compile(r"<Badge\b")
_T_NAME = re.compile(
    r"""\bt\s*\(\s*(?:name|n|toName|recipient)\b"""
    r"""|\bt\s*\(\s*["'](?:Ada|Berk|Self)["']"""
)
_TO_FIELD = re.compile(
    r"\brecipients\s*\??\s*\.\s*to\b"
    r"|\b(?:row\.)?to\s*\??\s*(?:\.length|\.\s*slice|\.\s*join)"
    r"|\b(?:toNames|mailToNames|toList|visibleTo)\b"
)
_CC_ON_BUBBLE = re.compile(
    r"\brecipients\s*\??\s*\.\s*cc\b"
    r"|\brecipients\s*\??\s*\.\s*bcc\b"
    r"|role\s*===?\s*['\"]cc['\"]"
    r"|role\s*===?\s*['\"]bcc['\"]"
)
_VISIBLE_3 = re.compile(
    r"\.slice\s*\(\s*0\s*,\s*3\s*\)"
    r"|slice\s*\(\s*0\s*,\s*3\s*\)"
    r"|\b(?:visibleCount|VISIBLE|TO_VISIBLE|maxVisible)\s*=\s*3\b"
)
_PLUS_K = re.compile(
    r"""\+\s*\{|\+\s*`|`\+|'\s*\+\s*'|"\s*\+\s*"|`\$\{[^}]*\}\s*`"""
    r"""|\+\s*\$\{|\{\s*`\+|plusK\b"""
    r"""|\+\{[^}]*(?:length|toNames|names)"""
)
_NOWRAP = re.compile(r"\bflex-nowrap\b|\bnowrap\b|\bwhitespace-nowrap\b")
_MIN_W0 = re.compile(r"\bmin-w-0\b")
_OVERFLOW_HID = re.compile(r"\boverflow-hidden\b")
_TRUNCATE = re.compile(r"\btruncate\b")
_MUTED = re.compile(r"text-muted-foreground|muted-foreground|text-muted")
_TEXT_XS = re.compile(r"\btext-xs\b")
_LENGTH_IF = re.compile(
    r"\{#if\s+[^}]*\b(?:to|toNames|mailToNames|toList|visibleTo|recipients)"
    r"[^}]*\.length"
    r"|\{#if\s+[^}]*\.length\s*>\s*0"
)
_EMPTY_DASH = re.compile(r"To\s*[—–-]\s*(?:['\"`]|$)|mailTo[^\n]{0,40}[—–-]")
_OMIT_SELF = re.compile(
    r"("
    r"omitSelf|excludeSelf|skipSelf|hideSelf"
    r"|filter\s*\([^)]{0,80}(?:from_me|is_self|isSelf|personTitle|selectedPerson)"
    r"|self_identities"
    r"|is_self\s*="
    r")",
    re.I,
)
_TL_INDEX = re.compile(r"\btimeline\s*\[\s*tlIndex\s*\]")
_SELECTED_SET = re.compile(
    r"\b(?:selectedIds|selectedMessageIds|copySelection|selectedSet)\b"
)
_NEW_CMD = re.compile(
    r"\b(?:message_recipients(?:_for|_cmd)?"
    r"|mail_recipients"
    r"|recipients_for"
    r"|messageRecipients"
    r"|mailRecipients"
    r"|getMessageRecipients)\b"
)
_HANDLER = re.compile(r"generate_handler!\s*\[(.*?)\]", re.S)
_PERSONS_JOIN = re.compile(
    r"("
    r"JOIN\s+persons\b"
    r"|JOIN\s+person_identities\b"
    r"|persons\.display_name"
    r"|\bp\.display_name\b"
    r")",
    re.I,
)
_MAIN_JOIN_RECIP = re.compile(
    r"FROM\s+messages[\s\S]{0,2500}JOIN\s+message_recipients",
    re.I,
)
_ID_KEYS = re.compile(
    r"\b(?:identity_id|person_id|identityId|personId|conversation_id)\s*\??\s*:"
)
_RAW_ID_INTERP = re.compile(
    r"\{[^}]{0,100}(?:"
    r"\bident(?:ity)?\.id\b"
    r"|\bidentity_id\b"
    r"|\bperson_id\b"
    r"|\bpersonId\b"
    r"|\bmessage_id\b"
    r")[^}]{0,40}\}"
)
_JID = re.compile(r"\bwhatsapp_jid\b|\bwa_jid\b|\bjid\b", re.I)
_INPUT = re.compile(r"<Input\b")
_SEND = re.compile(r"\b(?:sendMail|send_mail|composeMail|addRecipient|removeRecipient)\b")
_HTTP = re.compile(r"https?://", re.I)
_LUCIDE = re.compile(r"\blucide\b", re.I)
_BOUNCE = re.compile(r"animate-bounce|@keyframes")
_SHOW_QUOTED = re.compile(r"data-show-quoted|Show quoted|splitQuotedBody")
_CAS = re.compile(r"\bCasAttach\b")
_COPY_N = re.compile(r"""t\s*\(\s*["']copyN["']\s*\)""")
_AUTO_OPEN = re.compile(r"\bshowPersonChrome\s*=\s*true\b")
_PLACEHOLDERS = re.compile(r"\bAda\b|\bBerk\b|\bSelf\b")
_VEC_STR = re.compile(
    r"\bto\s*:\s*Vec\s*<\s*String\s*>"
    r"|\bcc\s*:\s*Vec\s*<\s*String\s*>"
    r"|\bbcc\s*:\s*Vec\s*<\s*String\s*>"
)
_TS_STR_ARR = re.compile(
    r"\bto\s*\??\s*:\s*string\s*\[\s*\]"
    r"|\bcc\s*\??\s*:\s*string\s*\[\s*\]"
    r"|\bbcc\s*\??\s*:\s*string\s*\[\s*\]"
)
_SKIP_SER = re.compile(r"skip_serializing_if")
_DOCS_TO_LINE = re.compile(r"muted To(?: line)?|\bTo line\b", re.I)
_DOCS_INSPECTOR = re.compile(
    r"(?:inspector|highlighted mail).{0,160}(?:To\s*/\s*Cc\s*/\s*Bcc|To.{0,20}Cc.{0,20}Bcc)"
    r"|(?:To\s*/\s*Cc\s*/\s*Bcc|To.{0,12}Cc.{0,12}Bcc).{0,160}(?:inspector|highlighted)",
    re.I | re.S,
)
_DOCS_WA = re.compile(
    r"WhatsApp.{0,140}(?:no |not |does not|never|without).{0,80}To line"
    r"|To line.{0,140}WhatsApp.{0,80}(?:no |not |never|does not|without)",
    re.I | re.S,
)
_DOCS_OVERFLOW = re.compile(r"\+\s*k\b|\+k\b")
_DOCS_CHIPS = re.compile(
    r"(?:chip|label).{0,80}(?:under|below).{0,40}subject"
    r"|subject.{0,80}(?:chip|label)",
    re.I | re.S,
)
_DOCS_OPEN_ORIG = re.compile(r"Open original", re.I)
_DOCS_NAMES = re.compile(
    r"names? (?:are|is) text.{0,40}not.{0,20}ids?"
    r"|text, not.{0,20}ids?",
    re.I | re.S,
)
_DOCS_SEARCH_THIS = re.compile(r"Search this conversation", re.I)
_DOCS_ATTACH_OPEN = re.compile(
    r"(?:right-click|context menu).{0,200}(?:stored )?(?:attachment|CAS).{0,200}Open"
    r"|Open.{0,160}default app",
    re.I | re.S,
)


def _around(src: str, rx: re.Pattern[str], before: int = 420, after: int = 420) -> str:
    bits: list[str] = []
    for m in rx.finditer(src):
        bits.append(src[max(0, m.start() - before) : m.end() + after])
    return "\n".join(bits)


def _hook_block(src: str, hook: str) -> str:
    return "\n".join(_hook_element_blocks(src, hook))


def _ts_type_flexible(src: str, name: str) -> str:
    body = _ts_type_body(src, name)
    if body:
        return body
    m = re.search(
        rf"(?:export\s+)?(?:type|interface)\s+{re.escape(name)}\s*=?\s*\{{",
        src,
    )
    if not m:
        return ""
    start = src.find("{", m.start())
    if start < 0:
        return ""
    end = _match_closer(src, start)
    if end < 0:
        return src[start:]
    return src[start : end + 1]


def _field_payload(src: str, row_body: str, field: str) -> str:
    m = re.search(rf"\b{re.escape(field)}\s*\??\s*:", row_body)
    if not m:
        return ""
    rest = row_body[m.end() :].lstrip()
    if rest.startswith("{"):
        end = _match_closer(rest, 0)
        return rest[: end + 1] if end > 0 else rest[:800]
    ident = re.match(r"([A-Za-z_][\w]*)", rest)
    if not ident:
        return rest[:400]
    name = ident.group(1)
    if name in {"Vec", "Option", "string", "Array"}:
        return rest[:400]
    return (
        _rust_struct_body(src, name)
        or _ts_type_flexible(src, name)
        or rest[:400]
    )


def _has_role_arrays(payload: str, rust: bool) -> bool:
    if rust:
        return bool(
            re.search(r"\bto\s*:\s*Vec\s*<\s*String\s*>", payload)
            and re.search(r"\bcc\s*:\s*Vec\s*<\s*String\s*>", payload)
            and re.search(r"\bbcc\s*:\s*Vec\s*<\s*String\s*>", payload)
        )
    return bool(
        re.search(r"\bto\s*\??\s*:\s*string\s*\[\s*\]", payload)
        and re.search(r"\bcc\s*\??\s*:\s*string\s*\[\s*\]", payload)
        and re.search(r"\bbcc\s*\??\s*:\s*string\s*\[\s*\]", payload)
    )


def _to_window(mail_then: str) -> str:
    if not _TO_HOOK.search(mail_then):
        return ""
    block = _hook_block(mail_then, "data-mail-to")
    win = _around(mail_then, _TO_HOOK, 520, 520)
    return block + "\n" + win


def assert_mail_recipients(crate: Path) -> None:
    """#374: muted To line on mail bubbles; inspector To/Cc/Bcc from the row."""
    root = repo_root()
    rows_path = _web_file(crate, "TimelineRows.svelte")
    mail_path = _web_file(crate, "TimelineMail.ts")
    insp_path = _web_file(crate, "PeopleInspector.svelte")
    shell_path = _web_file(crate, "PeopleShell.svelte")
    pane_path = _web_file(crate, "TimelinePane.svelte")
    list_path = _web_file(crate, "TimelineList.svelte")
    hits_path = _web_file(crate, "SearchHits.svelte")
    menu_path = _web_file(crate, "TimelineCopyMenu.svelte")
    cas_path = _web_file(crate, "CasAttach.svelte")
    api_path = _web_file(crate, "api.ts")
    find_path = _web_file(crate, "findHighlight.ts")
    virt_path = _web_file(crate, "TimelineVirtual.ts")
    en_path = crate / "web" / "lib" / "locales" / "en.ts"
    tr_path = crate / "web" / "lib" / "locales" / "tr.ts"
    docs_path = root / "docs" / "user" / "app.md"
    cmd_path = crate / "src" / "people_cmd.rs"

    rows_raw = _text(rows_path)
    mail_raw = _text(mail_path)
    insp_raw = _text(insp_path)
    shell_raw = _text(shell_path)
    pane_raw = _text(pane_path)
    lst_raw = _text(list_path)
    hits_raw = _text(hits_path)
    menu_raw = _text(menu_path)
    cas_raw = _text(cas_path)
    api_raw = _text(api_path)
    find_raw = _text(find_path)
    virt_raw = _text(virt_path)
    docs_raw = _text(docs_path)
    cmd_raw = _text(cmd_path)
    core = _people_core_blob(root)
    rust = _tauri_rust_blob(crate)

    rows = _without_comments(rows_raw)
    mail = _without_comments(mail_raw)
    insp = _without_comments(insp_raw)
    hits = _without_comments(hits_raw)
    menu = _without_comments(menu_raw)
    api = _without_comments(api_raw)
    rows_m = _svelte_markup(rows_raw)
    insp_m = _svelte_markup(insp_raw)
    hits_m = _svelte_markup(hits_raw)
    menu_m = _svelte_markup(menu_raw)
    mail_then, mail_else = _mail_else_blocks(rows_raw)
    mail_then_c = _without_comments(mail_then)
    mail_else_c = _without_comments(mail_else)

    # 1) mail-to-line — primary red today.
    if not rows_path.is_file() or not _TO_HOOK.search(mail_then or rows_m or rows):
        fail(
            f"{_ISSUE}: mail bubble must show a muted To line "
            "(data-mail-to) after data-mail-labels"
        )
    if not _TO_HOOK.search(mail_then):
        fail(
            f"{_ISSUE}: mail bubble must show a muted To line "
            "(data-mail-to) after data-mail-labels"
        )
    labels_at = mail_then.find("data-mail-labels")
    to_at = mail_then.find("data-mail-to")
    if labels_at < 0:
        fail(
            f"{_ISSUE}: keep #364 data-mail-labels under the subject "
            "(To line comes after the chips)"
        )
    if to_at < labels_at:
        fail(
            f"{_ISSUE}: To line (data-mail-to) must sit after data-mail-labels "
            "(chips stay under the subject)"
        )
    quoted_at = mail_then.find("splitQuotedBody")
    if quoted_at < 0:
        quoted_at = mail_then.find("data-show-quoted")
    if quoted_at >= 0 and to_at > quoted_at:
        fail(
            f"{_ISSUE}: To line sits after data-mail-labels and before the "
            "quoted body (not after Show quoted)"
        )
    if not _BUBBLE_BODY.search(rows):
        fail(f"{_ISSUE}: To line lives inside data-bubble-body")
    caption = _caption_block(rows_raw)
    if _TO_HOOK.search(caption):
        fail(
            f"{_ISSUE}: To line is inside data-bubble-body, not data-bubble-meta "
            "(#206 grouped followers hide the caption)"
        )
    if _BUBBLE_META.search(_hook_block(rows_m or rows, "data-mail-to")):
        fail(
            f"{_ISSUE}: To line is inside data-bubble-body, not data-bubble-meta"
        )

    to_win = _to_window(mail_then)
    to_win_c = _without_comments(to_win)

    # 2) chrome — t("mailTo") prefix; names are text; muted; not a Badge.
    if not _MAIL_TO_T.search(to_win) and not _MAIL_TO_T.search(mail_then_c):
        fail(
            f'{_ISSUE}: To line prefix is t("mailTo") '
            "(do not reuse t(\"searchTo\") — that is the Search date To)"
        )
    if _SEARCH_TO_T.search(mail_then_c) or _SEARCH_TO_T.search(to_win_c):
        fail(
            f'{_ISSUE}: do not reuse t("searchTo") for the mail To line '
            "(new ChromeKey mailTo)"
        )
    if _INNERHTML.search(to_win) or _INNERHTML.search(to_win_c):
        fail(f"{_ISSUE}: To names are text nodes (not {{@html}})")
    if _LINKIFY.search(to_win):
        fail(
            f"{_ISSUE}: To names are text nodes, not LinkifyBody "
            "(names are not a body)"
        )
    if _BADGE.search(to_win):
        fail(
            f"{_ISSUE}: To line is muted text, not a Badge chip row "
            "(#364 chips stay the Badge row)"
        )
    if _T_NAME.search(to_win_c) or _T_NAME.search(mail_then_c):
        fail(
            f"{_ISSUE}: names are archive data (Ada / Berk / Self), not t(name) "
            "/ t(\"Ada\")"
        )
    if not _MUTED.search(to_win) and not _MUTED.search(mail_then):
        fail(
            f"{_ISSUE}: To line uses text-muted-foreground "
            "(muted meta, not a loud heading)"
        )
    if not _TEXT_XS.search(to_win) and not _TEXT_XS.search(mail_then):
        fail(f"{_ISSUE}: To line is text-xs muted meta (UI-DESIGN secondary)")
    if _LUCIDE.search(to_win) or _LUCIDE.search(mail_then):
        fail(f"{_ISSUE}: no Lucide on the To line (match #322 group names — none)")
    if _BOUNCE.search(to_win):
        fail(f"{_ISSUE}: reduced motion — no bounce on the To line")
    if _MAIL_TO_T.search(menu_m or menu):
        fail(
            f"{_ISSUE}: To/Cc/Bcc is not a bubble menuitem "
            "(keep #373 Open original on TimelineCopyMenu)"
        )

    # 3) mail-only — isMailRow; WhatsApp {:else} mounts nothing.
    if not _IS_MAIL.search(rows):
        fail(
            f"{_ISSUE}: To line gate is isMailRow ∧ To-role names "
            "(keep #117 isMailRow)"
        )
    if not re.search(r"""platform\s*===?\s*["']gmail["']""", mail) or not re.search(
        r"""["']email_thread["']""", mail
    ):
        fail(
            f"{_ISSUE}: keep isMailRow as platform === \"gmail\" or "
            "conversation_kind === \"email_thread\" (#117)"
        )
    mail_fn = _function_body(mail_raw, "isMailRow") or _ts_fn_body(
        mail_raw, "isMailRow"
    )
    if re.search(r"\brecipients\b|\.to\b", mail_fn):
        fail(
            f"{_ISSUE}: do not rewrite isMailRow to mean has recipients "
            "(gmail or email_thread — WA stays To-line-less even if JSON had names)"
        )
    if (
        _TO_HOOK.search(mail_else_c)
        or _MAIL_TO_T.search(mail_else_c)
        or re.search(r"\brecipients\b", mail_else_c)
    ):
        fail(
            f"{_ISSUE}: WhatsApp / non-mail path must mount no To line "
            "even if recipients.to is non-empty"
        )

    # 4) To-role only — Cc / Bcc inspector-only.
    if not _TO_FIELD.search(to_win_c) and not _TO_FIELD.search(mail_then_c):
        fail(
            f"{_ISSUE}: bubble To line reads recipients.to "
            "(To-role names only — not a mixed To+Cc line)"
        )
    if _CC_ON_BUBBLE.search(to_win_c):
        fail(
            f"{_ISSUE}: a Cc-only recipient is not on the bubble To line "
            "(Cc / Bcc are inspector-only)"
        )

    # 5) truncate — first 3 then ASCII +k; nowrap / min-w-0 / overflow-hidden.
    if not _VISIBLE_3.search(to_win_c) and not _VISIBLE_3.search(mail_then_c):
        fail(f"{_ISSUE}: To line shows 3 names then ASCII +k (same N as #364 chips)")
    if not _PLUS_K.search(to_win_c) and not _PLUS_K.search(mail_then_c):
        fail(
            f"{_ISSUE}: To overflow remainder is ASCII +k "
            "(muted text, not a Badge, not a new ChromeKey)"
        )
    if re.search(r"<Badge\b[^>]*>[\s\S]{0,60}\+", to_win):
        fail(f"{_ISSUE}: +k is muted text, not a Badge")
    if not _NOWRAP.search(to_win) and not _NOWRAP.search(mail_then):
        fail(f"{_ISSUE}: To line is nowrap (a long name must not wrap-widen the pane)")
    if not _MIN_W0.search(to_win) and not _MIN_W0.search(mail_then):
        fail(f"{_ISSUE}: To line is min-w-0")
    if not _OVERFLOW_HID.search(to_win) and not _OVERFLOW_HID.search(mail_then):
        fail(f"{_ISSUE}: To line is overflow-hidden")
    if not _TRUNCATE.search(to_win) and not _TRUNCATE.search(mail_then):
        fail(f"{_ISSUE}: a single long To name truncates")

    # 6) empty-to — no To rows → mount nothing (Cc-only mail has no To line).
    if not _LENGTH_IF.search(to_win) and not _LENGTH_IF.search(mail_then):
        fail(
            f"{_ISSUE}: no To rows → mount nothing "
            "({#if to.length} — no “To —”, no zero-height wrapper)"
        )
    if _EMPTY_DASH.search(to_win) or _EMPTY_DASH.search(mail_then_c):
        fail(f"{_ISSUE}: hide the To line when there are no To rows (no “To —”)")
    subj_then, _ = _svelte_if_else(
        mail_then, re.compile(r"\{#if\s+[^}]*\bsubject\b")
    )
    if subj_then and _TO_HOOK.search(subj_then):
        rest = mail_then.replace(subj_then, "", 1)
        if not _TO_HOOK.search(rest):
            fail(
                f"{_ISSUE}: no-subject mail may still show a To line when "
                "To names exist (do not nest data-mail-to only inside the subject if)"
            )

    # 7) include Self / the open person.
    if _OMIT_SELF.search(to_win_c) or _OMIT_SELF.search(mail_then_c):
        fail(
            f"{_ISSUE}: include Self / the open person if they are a To recipient "
            "(Gmail to Ada and Berk names both — do not omit from-me)"
        )
    if _PLACEHOLDERS.search(to_win_c) or _PLACEHOLDERS.search(mail_then_c):
        fail(
            f"{_ISSUE}: placeholders Ada / Berk / Self stay out of chrome "
            "(names come from the row JSON)"
        )

    # 8) JSON — names-only to / cc / bcc string arrays on TimelineRow.
    rust_row = _rust_struct_body(core, "TimelineRow")
    if not re.search(r"\brecipients\b", rust_row):
        fail(
            f"{_ISSUE}: person_timeline TimelineRow JSON must expose recipients "
            "(names-only to / cc / bcc string arrays — no extra IPC)"
        )
    rust_payload = _field_payload(core, rust_row, "recipients")
    if not _has_role_arrays(rust_payload + "\n" + rust_row, rust=True):
        fail(
            f"{_ISSUE}: TimelineRow.recipients is names-only to / cc / bcc "
            "(Vec<String> arrays — not role+name objects, not ids)"
        )
    if _ID_KEYS.search(rust_payload):
        fail(
            f"{_ISSUE}: recipients JSON has no identity_id / person_id "
            "(unlike ConversationParticipantName)"
        )
    if _SKIP_SER.search(rust_payload) or re.search(
        r"skip_serializing_if[^\n]{0,80}\n\s*(?:pub\s+)?recipients",
        rust_row,
    ):
        fail(
            f"{_ISSUE}: recipients serializes empty arrays like labels: [] "
            "(do not skip_serializing_if)"
        )
    api_row = _ts_type_body(api, "TimelineRow") or _ts_type_flexible(api, "TimelineRow")
    if not re.search(r"\brecipients\b", api_row):
        fail(
            f"{_ISSUE}: api.ts TimelineRow must include recipients "
            "(to / cc / bcc: string[])"
        )
    api_payload = _field_payload(api, api_row, "recipients")
    if not _has_role_arrays(api_payload + "\n" + api_row, rust=False):
        fail(
            f"{_ISSUE}: api.ts recipients is names-only to / cc / bcc string[]"
        )
    if _ID_KEYS.search(api_payload):
        fail(
            f"{_ISSUE}: api.ts recipients has no identity_id / person_id "
            "(names only)"
        )
    hit_type = _ts_type_body(api, "SearchHit") or _ts_type_flexible(api, "SearchHit")
    if re.search(r"\brecipients\b", hit_type):
        fail(
            f"{_ISSUE}: SearchHit stays without recipients "
            "(People timeline + inspector only — not Search preview)"
        )

    # 9) attach_recipients after attach_labels; one IN join; identities.
    tl_fn = _rust_function_body(core, "person_timeline_rows_for")
    att = tl_fn.find("attach_attachments")
    lab = tl_fn.find("attach_labels")
    rec = tl_fn.find("attach_recipients")
    if rec < 0:
        fail(
            f"{_ISSUE}: attach_recipients on the person_timeline page "
            "(after attach_labels — same family as labels)"
        )
    if att < 0 or lab < 0 or rec < lab:
        fail(
            f"{_ISSUE}: attach_recipients after attach_labels "
            "(do not JOIN message_recipients into the main timeline SELECT)"
        )
    if _MAIN_JOIN_RECIP.search(tl_fn):
        fail(
            f"{_ISSUE}: do not JOIN message_recipients into the main timeline "
            "SELECT (cartesian LIMIT — page-batch attach_recipients instead)"
        )
    rec_fn = _rust_function_body(core, "attach_recipients")
    if not rec_fn or not re.search(r"\bmessage_recipients\b", rec_fn):
        fail(
            f"{_ISSUE}: attach_recipients reads message_recipients ⨝ identities "
            "for the page's message_id s"
        )
    if not re.search(r"JOIN\s+identities\b", rec_fn, re.I):
        fail(
            f"{_ISSUE}: attach_recipients joins identities "
            "(display_name then value — not persons.display_name)"
        )
    if not re.search(r"IN\s*\(", rec_fn):
        fail(
            f"{_ISSUE}: attach_recipients is one IN join for the page "
            "(not N SQLite per row, not a JOIN in the main SELECT)"
        )
    if _PERSONS_JOIN.search(rec_fn):
        fail(
            f"{_ISSUE}: name-source is identity display_name then value — "
            "do not join persons.display_name"
        )
    if re.search(r"\bconversation_participants\b", rec_fn):
        fail(
            f"{_ISSUE}: do not reuse conversation_participants for mail To/Cc/Bcc "
            "(#322 group roster stays that table)"
        )
    if re.search(r"\bpayload_json\b", rec_fn):
        fail(f"{_ISSUE}: names from message_recipients ⨝ identities, not payload_json")
    if not re.search(r"\bdisplay_name\b", rec_fn):
        fail(
            f"{_ISSUE}: resolved name is identity display_name then identity value"
        )
    if not re.search(r"value_normalized|value_raw", rec_fn):
        fail(
            f"{_ISSUE}: fallback is identity value (value_normalized / value_raw), "
            "not an id, not persons.display_name"
        )
    if not (
        re.search(r"\bto\b", rec_fn)
        and re.search(r"\bcc\b", rec_fn)
        and re.search(r"\bbcc\b", rec_fn)
    ):
        fail(
            f"{_ISSUE}: attach_recipients fills to / cc / bcc "
            "(UI slices To for the bubble; inspector lists all three)"
        )
    if _OMIT_SELF.search(rec_fn) or re.search(
        r"self_identities|is_self", rec_fn
    ):
        fail(
            f"{_ISSUE}: include Self on the To/Cc/Bcc arrays "
            "(do not drop the open person / from-me)"
        )
    sig = _rust_fn_signature(core, "person_timeline_rows_for")
    if re.search(r"\brecipients\b", sig):
        fail(
            f"{_ISSUE}: person_timeline_rows_for signature stays "
            "(no new recipients arg — attach fills the row)"
        )

    # 10) no extra IPC — recipients ride person_timeline JSON.
    if _INVOKE.search(rows) or _INVOKE.search(_without_comments(rows_raw)):
        fail(f"{_ISSUE}: no invoke / api. in TimelineRows (no per-row IPC)")
    if _NEW_CMD.search(cmd_raw) or _NEW_CMD.search(api) or _NEW_CMD.search(rust):
        fail(
            f"{_ISSUE}: no new message_recipients / per-id command "
            "(names ride person_timeline JSON; inspector reads timeline[tlIndex])"
        )
    h = _HANDLER.search(rust)
    if h and re.search(r"\bmessage_recipients\b|\bmail_recipients\b", h.group(1)):
        fail(
            f"{_ISSUE}: do not add a message_recipients command to generate_handler"
        )
    if re.search(r"""invoke\s*[<(][^)]*message_recipients""", api):
        fail(f"{_ISSUE}: no message_recipients invoke in api.ts")

    # 11) inspector — To/Cc/Bcc from timeline[tlIndex] when open.
    if not insp_path.is_file() or not _RECIP_HOOK.search(insp_m or insp):
        fail(
            f"{_ISSUE}: open inspector + highlighted mail lists To / Cc / Bcc "
            "(data-mail-recipients from timeline[tlIndex])"
        )
    recip_block = _hook_block(insp_m or insp_raw, "data-mail-recipients")
    recip_win = recip_block + "\n" + _around(insp_raw, _RECIP_HOOK, 700, 900)
    recip_c = _without_comments(recip_win)
    if not _MAIL_TO_T.search(recip_c) or not _MAIL_CC_T.search(
        recip_c
    ) or not _MAIL_BCC_T.search(recip_c):
        fail(
            f'{_ISSUE}: inspector headings are t("mailTo") / t("mailCc") / '
            't("mailBcc") (empty role unmounts that heading)'
        )
    if _SEARCH_TO_T.search(recip_c):
        fail(
            f'{_ISSUE}: inspector must not reuse t("searchTo") for mail To'
        )
    if not _TL_INDEX.search(insp) and not _TL_INDEX.search(recip_c):
        fail(
            f"{_ISSUE}: inspector recipients follow timeline[tlIndex] "
            "(highlight another mail → list updates; no extra fetch)"
        )
    if _SELECTED_SET.search(recip_c):
        fail(
            f"{_ISSUE}: inspector recipients follow tlIndex, not the #370 "
            "selected-id set"
        )
    if not _IS_MAIL.search(recip_c) and not _IS_MAIL.search(insp):
        fail(
            f"{_ISSUE}: highlight WhatsApp / non-mail → hide the recipient block "
            "(gate data-mail-recipients with isMailRow)"
        )
    if not re.search(r"\brecipients\s*\??\s*\.\s*cc\b|\.cc\b", recip_c):
        fail(
            f"{_ISSUE}: a Cc-only recipient shows under inspector Cc, not as To"
        )
    ident_each = _inspector_ident_each(insp_m or insp)
    if _RECIP_HOOK.search(ident_each) or _MAIL_CC_T.search(ident_each):
        fail(
            f"{_ISSUE}: do not mix mail To/Cc/Bcc into {{#each identities}} "
            "(#213 identities stay kind + value)"
        )
    group_block = _hook_block(insp_m or insp_raw, "data-group-participants")
    if _RECIP_HOOK.search(group_block) or _MAIL_TO_T.search(group_block):
        fail(
            f"{_ISSUE}: do not mix mail To/Cc/Bcc into data-group-participants "
            "(#322 group names stay that list)"
        )
    if not _GROUP_HOOK.search(insp_m or insp):
        fail(
            f"{_ISSUE}: keep #322 data-group-participants "
            "(identity display_name || value; separate from mail recipients)"
        )
    if _NEW_CMD.search(insp) or re.search(
        r"""invoke\s*[<(][^)]*message_recipients""", insp
    ):
        fail(
            f"{_ISSUE}: inspector must not fetch recipients "
            "(derive from timeline[tlIndex]; no extra IPC)"
        )
    if _INNERHTML.search(recip_c) or _RAW_ID_INTERP.search(recip_win):
        fail(
            f"{_ISSUE}: inspector recipient labels are text names "
            "(never identity_id / person_id / message_id)"
        )
    if _JID.search(recip_c):
        fail(f"{_ISSUE}: never show a JID on the inspector recipient lists")
    if _INPUT.search(recip_block) or _SEND.search(recip_c):
        fail(
            f"{_ISSUE}: no recipient Input / add/remove / send "
            "(read-only lists)"
        )
    if re.search(r"\.slice\s*\(\s*0\s*,\s*3\s*\)", recip_c):
        fail(
            f"{_ISSUE}: inspector lists every To/Cc/Bcc name "
            "(no +k cap — existing inspector scroll)"
        )
    if not re.search(r"scrollTo\s*\(\s*0\s*,\s*0\s*\)", insp):
        fail(
            f"{_ISSUE}: inspector must scroll to top when the highlighted mail "
            "changes (a long To list then a short one must not leave an empty pane)"
        )
    if not re.search(
        r"bind:this=\{[^}]+\}", _hook_block(insp_m or insp_raw, "data-person-inspector")
    ) and not re.search(r"bind:this=\{", insp_m or insp):
        fail(
            f"{_ISSUE}: bind the inspector scroller (data-person-inspector) "
            "so highlight can reset overflow-y-auto"
        )
    if _PLACEHOLDERS.search(recip_c):
        fail(
            f"{_ISSUE}: placeholders Ada / Berk / Self stay out of inspector "
            "chrome (names come from the row JSON)"
        )
    if _LENGTH_IF.search(recip_c) is None and not re.search(
        r"\{#if\s+[^}]*\.(?:to|cc|bcc)[^}]*\.length", recip_c
    ):
        fail(
            f"{_ISSUE}: empty inspector role unmounts that heading "
            "(no “Cc —”)"
        )

    # 12) inspector-off — still #213 default-off; highlighting mail does not open it.
    if not re.search(r"\{#if\s+showPersonChrome\s*\}", shell_raw):
        fail(
            f"{_ISSUE}: keep PeopleShell {{#if showPersonChrome}} unmount "
            "(#213 off by default — recipient list is not a reason to open it)"
        )
    if "PeopleInspector" not in shell_raw:
        fail(f"{_ISSUE}: keep PeopleInspector mounted only while the inspector is open")
    auto_src = pane_raw + "\n" + shell_raw + "\n" + lst_raw + "\n" + rows_raw
    for m in _AUTO_OPEN.finditer(auto_src):
        win = auto_src[max(0, m.start() - 180) : m.end() + 180]
        if re.search(r"isMailRow|recipients|data-mail-to|mailTo", win):
            fail(
                f"{_ISSUE}: highlighting a mail must not set showPersonChrome = true "
                "(inspector stays off by default)"
            )

    # 13) People only — Search preview does not grow a To line.
    if _TO_HOOK.search(hits_m or hits) or _MAIL_TO_T.search(hits):
        fail(
            f"{_ISSUE}: Search preview does not grow a To line "
            "(People timeline + inspector only)"
        )
    if _RECIP_HOOK.search(hits_m or hits):
        fail(f"{_ISSUE}: SearchHits must not grow inspector recipient lists")
    if "TimelineCopyMenu" in hits_raw:
        fail(
            f"{_ISSUE}: SearchHits must not mount TimelineCopyMenu "
            "(#371 preview is not a bubble timeline)"
        )
    if "CasAttach" not in hits_raw:
        fail(
            f"{_ISSUE}: SearchHits must keep mounting CasAttach "
            "(attachment Open only — #317)"
        )

    # 14) keep #364 / #373 / #372 / #317 / #322 / #117 / #224 / find haystack.
    if not _CHIP_HOOK.search(mail_then) and not _CHIP_HOOK.search(rows):
        fail(
            f"{_ISSUE}: keep #364 data-mail-labels chips under the subject "
            "(To line does not replace them)"
        )
    if not _MAIL_SUBJECT.search(rows) or not _SHOW_QUOTED.search(rows_raw):
        fail(f"{_ISSUE}: keep #117 mail-subject + Show quoted")
    if not _CAS.search(rows):
        fail(f"{_ISSUE}: keep #207 / #317 CasAttach on the bubble stack")
    if not _EST88.search(virt_raw):
        fail(f"{_ISSUE}: keep #224 ESTIMATED_ROW_HEIGHT = 88")
    vis = _function_body(find_raw, "visibleFindFields") or _ts_fn_body(
        find_raw, "visibleFindFields"
    )
    if re.search(r"\brecipients\b|\bmailTo\b|\.to\b", vis):
        fail(
            f"{_ISSUE}: find haystack stays subject + body "
            "(do not add To names — same as #364 chips)"
        )
    if not _SEARCH_THIS_T.search(menu_m or menu):
        fail(
            f'{_ISSUE}: keep t("searchThisConversation") on the bubble menu (#372)'
        )
    if not _OPEN_ORIG_T.search(menu_m or menu):
        fail(
            f'{_ISSUE}: keep t("openOriginal") after t("searchThisConversation") (#373)'
        )
    this_t = _SEARCH_THIS_T.search(menu_m or menu)
    orig_t = _OPEN_ORIG_T.search(menu_m or menu)
    if this_t and orig_t and orig_t.start() < this_t.start():
        fail(
            f'{_ISSUE}: keep t("openOriginal") after t("searchThisConversation") (#373)'
        )
    if not _SEARCH_T.search(menu_m or menu):
        fail(f'{_ISSUE}: keep t("search") on the bubble menu (#273 / #372)')
    if not _COPY_N.search(menu_m or menu):
        fail(f'{_ISSUE}: keep t("copyN") when n > 1 (#370)')
    if not _T_OPEN.search(_svelte_markup(cas_raw) or cas_raw):
        fail(f'{_ISSUE}: keep CasAttach t("open") (#317 attachment Open)')
    if re.search(r"stopPropagation", rows_raw) is None:
        fail(
            f"{_ISSUE}: keep CasAttach stopPropagation so attachment Open/Reveal "
            "do not become Copy N (#370)"
        )

    # 15) locale — same ChromeKey on en.ts + tr.ts; tr is not an English copy.
    en = _chrome_pack_entries(_text(en_path))
    tr = _chrome_pack_entries(_text(tr_path))
    extra_en = set(en) - set(tr)
    extra_tr = set(tr) - set(en)
    if extra_en or extra_tr:
        bits: list[str] = []
        if extra_en:
            bits.append("in en only: " + ", ".join(sorted(extra_en)))
        if extra_tr:
            bits.append("in tr only: " + ", ".join(sorted(extra_tr)))
        fail(f"{_ISSUE}: same ChromeKey on both en and tr packs — " + "; ".join(bits))
    for key in ("mailTo", "mailCc", "mailBcc"):
        if key not in en or key not in tr:
            fail(f"{_ISSUE}: {key} ChromeKey on both en.ts and tr.ts (#278)")
    if not re.search(r"\bTo\b", en.get("mailTo") or ""):
        fail(f'{_ISSUE}: en mailTo is the To-line prefix (not t("searchTo"))')
    if not re.search(r"\bCc\b", en.get("mailCc") or "", re.I):
        fail(f"{_ISSUE}: en mailCc must say Cc")
    if not re.search(r"\bBcc\b", en.get("mailBcc") or "", re.I):
        fail(f"{_ISSUE}: en mailBcc must say Bcc")
    if (en.get("mailTo") or "").strip() == (tr.get("mailTo") or "").strip():
        fail(f"{_ISSUE}: tr mailTo is not an English copy")
    if (en.get("mailCc") or "").strip() == (tr.get("mailCc") or "").strip():
        fail(f"{_ISSUE}: tr mailCc is not an English copy")
    if (en.get("mailBcc") or "").strip() == (tr.get("mailBcc") or "").strip():
        fail(f"{_ISSUE}: tr mailBcc is not an English copy")
    if (tr.get("mailTo") or "").strip() == (tr.get("searchTo") or "").strip():
        fail(
            f"{_ISSUE}: do not reuse searchTo for mail To "
            "(tr searchTo is the date-filter Bitiş)"
        )
    for pack in (en, tr):
        for _key, val in pack.items():
            if re.search(r"\bAda\b|\bBerk\b", val):
                fail(
                    f"{_ISSUE}: locale packs stay chrome only — no placeholder "
                    "names in t() values"
                )
            if re.search(r"\+\s*k\b|\+k\b", val):
                fail(f"{_ISSUE}: +k stays ASCII, not a ChromeKey")

    # 16) no edit / send / HTTP on this surface.
    if _SEND.search(rows) or _SEND.search(insp):
        fail(f"{_ISSUE}: no send / compose / add-recipient widgets")
    if _HTTP.search(to_win_c) or _HTTP.search(recip_c):
        fail(f"{_ISSUE}: To/Cc/Bcc names are local archive text — no http(s)")

    # 17) D24 — docs/user/app.md (handoff / roadmap land with impl).
    if not docs_raw.strip():
        fail(
            f"{_ISSUE}: docs/user/app.md required — mail To line; inspector "
            "To/Cc/Bcc; WhatsApp has no To line"
        )
    if not _DOCS_TO_LINE.search(docs_raw):
        fail(
            f"{_ISSUE}: docs/user/app.md must describe the muted mail To line "
            "(To-role names; overflow +k)"
        )
    if not _DOCS_INSPECTOR.search(docs_raw):
        fail(
            f"{_ISSUE}: docs/user/app.md must say the inspector lists To/Cc/Bcc "
            "for the highlighted mail"
        )
    if not _DOCS_WA.search(docs_raw):
        fail(f"{_ISSUE}: docs/user/app.md must say a WhatsApp bubble has no To line")
    if not _DOCS_OVERFLOW.search(docs_raw):
        fail(f"{_ISSUE}: docs/user/app.md must keep overflow +k")
    if not _DOCS_CHIPS.search(docs_raw):
        fail(
            f"{_ISSUE}: keep docs for Gmail chips under the subject (#364)"
        )
    if not _DOCS_OPEN_ORIG.search(docs_raw):
        fail(f"{_ISSUE}: keep docs for Open original (#373)")
    if not _DOCS_SEARCH_THIS.search(docs_raw):
        fail(f"{_ISSUE}: keep docs for Search this conversation (#372)")
    if not _DOCS_ATTACH_OPEN.search(docs_raw):
        fail(f"{_ISSUE}: keep docs for attachment Open (#317)")
    if not _DOCS_NAMES.search(docs_raw):
        fail(f"{_ISSUE}: docs must keep names are text, not ids")
