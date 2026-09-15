"""#364 — Gmail label chips on mail bubbles (A + under-subject).

Wired immediately after assert_gmail_timeline_rows (#117 mail-bubble family).

Confirmed mix: page-batch attach_labels on TimelineRow after attach_attachments
(same family; one IN join; do not JOIN labels into the main timeline SELECT).
Names-only Vec<String> / string[] from labels ⨝ message_labels. No new IPC.
No payload_json copy. No per-row invoke from TimelineRows. Existing
person_timeline_rows_for signature stays (no new arg).

Chrome: muted outline owned Badge chips under the subject, inside
data-bubble-body. Gate: isMailRow AND names.length > 0. WhatsApp / non-mail
path mounts no chip row even if JSON has names. Empty → mount nothing.
Overflow: show 3 then muted-text ASCII +k (not another Badge; no new en+tr
keys). Row: nowrap + min-w-0 + overflow-hidden. A single long name truncates.
Sort: stable as attached. Hide: show every stored name. No-subject mail:
chips still first child of data-bubble-body. Find haystack stays subject +
body. SearchPane may host the #365 Filters select; SearchHits / inspector
stay chip-less. Timeline chips stay unclickable.

Placeholders only (Ada / Berk). Plant strings Inbox / Sent / Family.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.locale_pack import _chrome_pack_entries
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

_ISSUE = "#364"

_LABELS_FIELD = re.compile(r"\b(?:row\.)?labels\b")
_LABEL_HELPER = re.compile(
    r"\b(?:visibleLabels|labelNames|mailLabels|labelChips|mailLabelNames|"
    r"visibleMailLabels|labelOverflow)\b"
)
_CHIP_HOOK = re.compile(
    r"\bdata-(?:mail-label|label-chip|gmail-labels|mail-labels)\b"
    r"|\b(?:mail-labels|label-chips|mail-label-row)\b"
)
_IS_MAIL = re.compile(r"\bisMailRow\b")
_MAIL_SUBJECT = re.compile(r"\bmail-subject\b")
_BUBBLE_BODY = re.compile(r"\bdata-bubble-body\b")
_BUBBLE_META = re.compile(r"\bdata-bubble-meta\b")
_BADGE = re.compile(r"<Badge\b")
_INNERHTML = re.compile(r"\binnerHTML\b|\{@html\b")
_T_INBOX = re.compile(
    r"""\bt\s*\(\s*["'](?:Inbox|Sent|Family)["']"""
    r"""|\bt\s*\(\s*(?:name|lab(?:el)?|n)\b"""
)
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][\w]*)["']\s*\)""")
_PLUS_K = re.compile(
    r"""\+\s*\{|\+\s*`|`\+|'\s*\+\s*'|"\s*\+\s*"|`\$\{[^}]*\}\s*`"""
    r"""|\+\s*\$\{|\{\s*`\+|plusK\b"""
)
_VISIBLE_3 = re.compile(
    r"\.slice\s*\(\s*0\s*,\s*3\s*\)"
    r"|slice\s*\(\s*0\s*,\s*3\s*\)"
    r"|\b(?:visibleCount|VISIBLE|LABEL_VISIBLE|maxVisible)\s*=\s*3\b"
)
_NOWRAP = re.compile(r"\bflex-nowrap\b|\bnowrap\b|\bwhitespace-nowrap\b")
_MIN_W0 = re.compile(r"\bmin-w-0\b")
_OVERFLOW_HID = re.compile(r"\boverflow-hidden\b")
_TRUNCATE = re.compile(r"\btruncate\b")
_LENGTH_IF = re.compile(
    r"\{#if\s+[^}]*\b(?:names|labels|labelNames|visibleLabels|mailLabels)"
    r"[^}]*\.length"
    r"|\{#if\s+[^}]*\.length\s*>\s*0"
)
_ALWAYS_WRAP = re.compile(
    r"<div[^>]*(?:mail-label|label-chip|label-chips|mail-labels)[^>]*>"
)
_RAW_COLOR = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|\bbg-yellow|\bbg-green|\bbg-red|\bamber-"
)
_MUTED = re.compile(r"muted-foreground|--chrome-chip-|text-muted")
_INVOKE = re.compile(r"\binvoke\s*[<(]|\bapi\.")
_NEW_CMD = re.compile(
    r"\b(?:person_message_labels|message_labels_for|messageLabels|"
    r"personMessageLabels)\b"
)
_PAYLOAD = re.compile(r"\bpayload_json\b")
_JOIN_MAIN = re.compile(r"\bJOIN\s+(?:labels|message_labels)\b", re.I)
_SEARCH_LABEL = re.compile(r"\bdata-gmail-label\b")
_EST88 = re.compile(r"\bESTIMATED_ROW_HEIGHT\s*=\s*88\b")
_SHOW_QUOTED = re.compile(r"data-show-quoted|Show quoted|splitQuotedBody")
_PLATFORM_CHIP = re.compile(r"\bdata-platform-chip\b")
_GROUPED = re.compile(r"\bisGroupedFollower\b")
_FROM_ME = re.compile(r"\bdata-from-me-filter\b|\bfromMeFilter\b")
_ATTACH_KIND = re.compile(r"\bdata-attach-kind-filter\b|\battachKindFilter\b")
_GALLERY = re.compile(r"\bdata-person-gallery")
_CAS = re.compile(r"\bCasAttach\b")
_NEW_LOCALE = re.compile(
    r"inbox|sent|family|gmailLabel|labelChip|plusK|mailLabel|overflowLabel",
    re.I,
)
_DOCS_CHIPS = re.compile(
    r"(?:chip|label).{0,80}(?:under|below).{0,40}subject"
    r"|subject.{0,80}(?:chip|label)",
    re.I | re.S,
)
_DOCS_WA = re.compile(
    r"WhatsApp.{0,80}(?:chip-less|chipless|no chips|without chips|stay)"
    r"|(?:chip-less|chipless|no chips).{0,80}WhatsApp",
    re.I | re.S,
)
_DOCS_OVERFLOW = re.compile(r"\+\s*k\b|\+k\b", re.I)
_BADGE_VARIANTS = re.compile(r"badgeVariants\s*=\s*tv\s*\(")
_HANDLER = re.compile(r"generate_handler!\s*\[(.*?)\]", re.S)


def _text(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _people_core_blob(root: Path) -> str:
    """people.rs + people/*.rs only (do not open import / identity / search)."""
    parts: list[str] = []
    src = root / "crates" / "interlace-core" / "src" / "people.rs"
    if src.is_file():
        parts.append(src.read_text())
    d = root / "crates" / "interlace-core" / "src" / "people"
    if d.is_dir():
        for p in sorted(d.glob("*.rs")):
            parts.append(p.read_text())
    return "\n".join(parts)


def _ts_type_body(src: str, name: str) -> str:
    m = re.search(rf"export\s+type\s+{re.escape(name)}\s*=\s*\{{", src)
    if not m:
        return ""
    start = src.find("{", m.start())
    if start < 0:
        return ""
    end = _match_closer(src, start)
    if end < 0:
        return src[start:]
    return src[start : end + 1]


def _rust_struct_body(src: str, name: str) -> str:
    m = re.search(rf"(?:pub\s+)?struct\s+{re.escape(name)}\s*\{{", src)
    if not m:
        return ""
    start = src.find("{", m.start())
    if start < 0:
        return ""
    end = _match_closer(src, start)
    if end < 0:
        return src[start:]
    return src[start : end + 1]


def _svelte_if_else(src: str, open_rx: re.Pattern[str]) -> tuple[str, str]:
    m = open_rx.search(src)
    if not m:
        return "", ""
    i = m.end()
    depth = 1
    else_at = -1
    then_start = i
    n = len(src)
    while i < n and depth > 0:
        a = src.find("{#if", i)
        b = src.find("{:else", i)
        c = src.find("{/if}", i)
        cands = [x for x in (a, b, c) if x >= 0]
        if not cands:
            break
        nxt = min(cands)
        if nxt == c:
            depth -= 1
            if depth == 0:
                then = src[then_start:else_at] if else_at >= 0 else src[then_start:c]
                els = src[else_at:c] if else_at >= 0 else ""
                if els.startswith("{:else"):
                    close = els.find("}")
                    if close >= 0:
                        els = els[close + 1 :]
                return then, els
            i = c + 5
        elif nxt == b:
            is_else_if = src.startswith("{:else if", b)
            if depth == 1 and not is_else_if and else_at < 0:
                else_at = b
            i = b + 6
        else:
            depth += 1
            i = a + 4
    return "", ""


def _mail_else_blocks(rows: str) -> tuple[str, str]:
    rx = re.compile(r"\{#if\s+isMailRow\b")
    start = 0
    while True:
        m = rx.search(rows, start)
        if not m:
            return "", ""
        then, els = _svelte_if_else(rows[m.start() :], rx)
        if _MAIL_SUBJECT.search(then) or re.search(r"\bsplitQuotedBody\b", then):
            return then, els
        start = m.end()


def _has_chip_surface(rows: str, mail: str) -> bool:
    if _LABELS_FIELD.search(rows) or _LABEL_HELPER.search(rows):
        return True
    if _CHIP_HOOK.search(rows):
        return True
    if _LABEL_HELPER.search(mail) and _LABEL_HELPER.search(rows):
        return True
    return False


def _caption_block(rows: str) -> str:
    m = _BUBBLE_META.search(rows)
    if not m:
        return ""
    start = rows.rfind("<", 0, m.start())
    if start < 0:
        start = m.start()
    return rows[start : m.end() + 700]


def assert_timeline_gmail_labels(crate: Path) -> None:
    """#364: under-subject muted Badge chips on mail rows (mix A)."""
    rows_path = crate / "web" / "lib" / "TimelineRows.svelte"
    if not rows_path.is_file():
        fail(f"{_ISSUE}: chips missing")

    rows_raw = rows_path.read_text()
    rows = _without_comments(rows_raw)
    markup = _svelte_markup(rows_raw)
    mail_raw = _text(crate / "web" / "lib" / "TimelineMail.ts")
    mail = _without_comments(mail_raw)
    mail_then, mail_else = _mail_else_blocks(rows_raw)
    mail_then_c = _without_comments(mail_then)
    mail_else_c = _without_comments(mail_else)

    # 1) chips under subject — primary red today.
    if not _has_chip_surface(rows, mail):
        fail(f"{_ISSUE}: chips missing")
    if not _IS_MAIL.search(rows):
        fail(f"{_ISSUE}: chip gate is isMailRow ∧ names (keep #117 isMailRow)")
    if not _BUBBLE_BODY.search(rows):
        fail(f"{_ISSUE}: chips live inside data-bubble-body")
    if not _MAIL_SUBJECT.search(rows):
        fail(f"{_ISSUE}: chips sit under .mail-subject (keep the #117 title)")
    if not mail_then.strip():
        fail(
            f"{_ISSUE}: chips must sit under .mail-subject inside "
            "data-bubble-body (mail branch)"
        )
    chip_in_mail = (
        _LABELS_FIELD.search(mail_then_c)
        or _LABEL_HELPER.search(mail_then_c)
        or _CHIP_HOOK.search(mail_then_c)
    )
    if not chip_in_mail:
        fail(
            f"{_ISSUE}: chips must sit under .mail-subject inside "
            "data-bubble-body (mail branch)"
        )
    caption = _caption_block(rows_raw)
    if (
        _LABELS_FIELD.search(caption) or _CHIP_HOOK.search(caption)
    ) and not chip_in_mail:
        fail(f"{_ISSUE}: chips under the subject, not in the caption")
    if not _BADGE.search(mail_then):
        fail(f"{_ISSUE}: label chips must be owned Badge")
    if _INNERHTML.search(mail_then) or _INNERHTML.search(mail_then_c):
        fail(f"{_ISSUE}: label names are text nodes (not {{@html}})")
    if _T_INBOX.search(mail_then_c) or _T_INBOX.search(rows):
        fail(
            f"{_ISSUE}: names are archive data ({{name}}), not t(\"Inbox\") / t(name)"
        )
    if not re.search(r"\{(?:name|lab(?:el)?|n)\}", mail_then):
        fail(f"{_ISSUE}: names are Svelte text nodes ({{name}}), not chrome keys")

    # No-subject: chips must not live only inside the subject {#if}.
    subj_then, _ = _svelte_if_else(
        mail_then, re.compile(r"\{#if\s+[^}]*\bsubject\b")
    )
    if subj_then and (
        _LABELS_FIELD.search(subj_then) or _CHIP_HOOK.search(subj_then)
    ):
        rest = mail_then.replace(subj_then, "")
        if not (
            _LABELS_FIELD.search(rest)
            or _LABEL_HELPER.search(rest)
            or _CHIP_HOOK.search(rest)
        ):
            fail(
                f"{_ISSUE}: no-subject mail must still show chips as first "
                "child of data-bubble-body"
            )

    # 2) WA chip-less — {:else} mounts no label-chip hook.
    if (
        _LABELS_FIELD.search(mail_else_c)
        or _LABEL_HELPER.search(mail_else_c)
        or _CHIP_HOOK.search(mail_else_c)
        or _BADGE.search(mail_else)
    ):
        fail(
            f"{_ISSUE}: WhatsApp / non-mail path must mount no label chips "
            "even if labels is non-empty"
        )
    # Gate is isMailRow ∧ names, not labels.length alone at article scope.
    for m in re.finditer(
        r"\{#if\s+([^}]+)\}",
        markup,
    ):
        cond = m.group(1)
        if re.search(r"\blabels\b|\blabelNames\b|\bvisibleLabels\b", cond) and not (
            re.search(r"\bisMailRow\b", cond) or mail_then
        ):
            # Only fail when this if is outside the mail branch.
            pos = m.start()
            if mail_then and mail_then in rows_raw:
                mail_at = rows_raw.find(mail_then)
                if mail_at >= 0 and mail_at <= pos <= mail_at + len(mail_then):
                    continue
            if re.search(r"\.length", cond) and not re.search(r"\bisMailRow\b", cond):
                fail(
                    f"{_ISSUE}: chip gate is isMailRow ∧ names, "
                    "not labels.length alone"
                )

    # 3) empty unmount — no labels → no chip-row / no always-on wrapper.
    chip_src = mail_then + "\n" + mail
    if not _LENGTH_IF.search(chip_src) and not _LENGTH_IF.search(rows):
        fail(
            f"{_ISSUE}: no labels → mount nothing "
            "({#if names.length} — no always-on wrapper)"
        )
    if _ALWAYS_WRAP.search(mail_then) and not _LENGTH_IF.search(mail_then):
        fail(
            f"{_ISSUE}: empty labels must not leave a zero-height wrapper "
            "that still eats gap-2"
        )

    # 4) overflow — 3 then +k muted text; nowrap + min-w-0 + overflow-hidden.
    if not _VISIBLE_3.search(chip_src) and not _VISIBLE_3.search(rows):
        fail(f"{_ISSUE}: overflow shows 3 then +k")
    if not _PLUS_K.search(chip_src) and not _PLUS_K.search(rows):
        fail(f"{_ISSUE}: overflow remainder is ASCII +k (muted text)")
    if re.search(
        r"<Badge\b[^>]*>[\s\S]{0,60}\+",
        mail_then,
    ):
        fail(f"{_ISSUE}: +k is muted text, not a Badge")
    if not _NOWRAP.search(mail_then) and not _NOWRAP.search(chip_src):
        fail(f"{_ISSUE}: chip row is nowrap (do not wrap-widen the pane)")
    if not _MIN_W0.search(mail_then) and not _MIN_W0.search(chip_src):
        fail(f"{_ISSUE}: chip row is min-w-0")
    if not _OVERFLOW_HID.search(mail_then) and not _OVERFLOW_HID.search(chip_src):
        fail(f"{_ISSUE}: chip row is overflow-hidden")
    if not _TRUNCATE.search(mail_then) and not _TRUNCATE.search(chip_src):
        fail(f"{_ISSUE}: a single long name truncates")

    # 5) tokens — muted / --chrome-chip-*; no Gmail category colors.
    if not _MUTED.search(mail_then) and not _MUTED.search(chip_src):
        fail(
            f"{_ISSUE}: chips use muted tokens / muted-foreground / "
            "--chrome-chip-* (outline Badge)"
        )
    if _RAW_COLOR.search(mail_then) or _RAW_COLOR.search(mail_then_c):
        fail(
            f"{_ISSUE}: no raw Gmail category colors "
            "(#, bg-yellow, bg-green, bg-red, amber-)"
        )
    badge_src = _text(crate / "web" / "lib" / "components" / "ui" / "badge" / "badge.svelte")
    if _BADGE_VARIANTS.search(badge_src):
        variants = _function_body(badge_src, "badgeVariants") or badge_src
        extra = re.findall(
            r"\b(success|warning|destructive|yellow|green|red|amber|gmail)\b",
            variants,
            re.I,
        )
        if extra:
            fail(f"{_ISSUE}: do not add a colored badgeVariants entry ({extra[0]})")

    # 6) no row IPC — labels ride person_timeline JSON.
    if _INVOKE.search(rows) or _INVOKE.search(_without_comments(rows_raw)):
        fail(f"{_ISSUE}: no invoke / api. in TimelineRows (no per-row IPC)")
    rust = _tauri_rust_blob(crate)
    api = _text(crate / "web" / "lib" / "api.ts")
    cmd = _text(crate / "src" / "people_cmd.rs")
    if _NEW_CMD.search(cmd) or _NEW_CMD.search(api) or _NEW_CMD.search(rust):
        fail(
            f"{_ISSUE}: no new message_labels / per-id command "
            "(names ride person_timeline JSON)"
        )
    if re.search(r"""invoke\s*[<(][^)]*message_labels""", api):
        fail(f"{_ISSUE}: no message_labels invoke in api.ts")
    h = _HANDLER.search(rust)
    if h and re.search(r"\b(?:person_)?message_labels\b", h.group(1)):
        fail(f"{_ISSUE}: do not add a message_labels command to generate_handler")

    # 7) json field — TimelineRow.labels names-only; page-batch attach_labels.
    row_type = _ts_type_body(api, "TimelineRow")
    if not re.search(r"\blabels\s*\??\s*:\s*string\s*\[\s*\]", row_type):
        fail(f"{_ISSUE}: api.ts TimelineRow must have labels?: string[] (or labels: string[])")
    root = repo_root()
    core = _people_core_blob(root)
    rust_row = _rust_struct_body(core, "TimelineRow")
    if not re.search(r"\blabels\s*:", rust_row):
        fail(f"{_ISSUE}: Rust TimelineRow must have labels: Vec<String>")
    tl_fn = _rust_function_body(core, "person_timeline_rows_for")
    att = tl_fn.find("attach_attachments")
    lab = tl_fn.find("attach_labels")
    if att < 0 or lab < 0 or lab < att:
        fail(
            f"{_ISSUE}: attach_labels after attach_attachments "
            "(do not JOIN labels into the main timeline SELECT)"
        )
    if _JOIN_MAIN.search(tl_fn):
        fail(f"{_ISSUE}: do not JOIN labels into the main timeline SELECT")
    lab_fn = _rust_function_body(core, "attach_labels")
    if not lab_fn or not re.search(r"\bmessage_labels\b", lab_fn):
        fail(
            f"{_ISSUE}: attach_labels reads labels ⨝ message_labels "
            "for the page's message_id s"
        )
    if _PAYLOAD.search(lab_fn) or (
        _PAYLOAD.search(tl_fn) and re.search(r"\blabels\b", tl_fn)
    ):
        fail(f"{_ISSUE}: names from labels ⨝ message_labels, not payload_json")
    sig = _rust_fn_signature(rust + "\n" + core, "person_timeline_rows_for")
    if re.search(r"\blabels\b", sig):
        fail(
            f"{_ISSUE}: person_timeline_rows_for signature stays "
            "(no new labels arg)"
        )

    # 8) keep #117 / #206 / #207 / #201 / #217 / #224 / #363 / #362 / #361.
    if not _MAIL_SUBJECT.search(rows) or not _SHOW_QUOTED.search(rows_raw):
        fail(f"{_ISSUE}: keep #117 mail-subject + Show quoted")
    if not _IS_MAIL.search(rows) or not _IS_MAIL.search(mail):
        fail(f"{_ISSUE}: keep #117 isMailRow (gmail or email_thread)")
    if not _GROUPED.search(rows):
        fail(f"{_ISSUE}: keep #206 isGroupedFollower / caption omit")
    if not _BUBBLE_BODY.search(rows) or not _CAS.search(rows):
        fail(f"{_ISSUE}: keep #207 data-bubble-body + CasAttach stack")
    if not _PLATFORM_CHIP.search(rows) or not _BADGE.search(rows_raw):
        fail(f"{_ISSUE}: keep #201 / #217 data-platform-chip Badge")
    virt = _text(crate / "web" / "lib" / "TimelineVirtual.ts")
    if not _EST88.search(virt):
        fail(f"{_ISSUE}: keep #224 ESTIMATED_ROW_HEIGHT = 88")
    pane = _text(crate / "web" / "lib" / "TimelinePane.svelte")
    filters = _text(crate / "web" / "lib" / "TimelineFilters.svelte")
    if not _FROM_ME.search(pane) and not _FROM_ME.search(filters):
        fail(f"{_ISSUE}: keep #363 from-me filter")
    if not _ATTACH_KIND.search(pane) and not _ATTACH_KIND.search(filters):
        fail(f"{_ISSUE}: keep #362 attach-kind filter")
    if not _GALLERY.search(pane):
        fail(f"{_ISSUE}: keep #361 gallery")
    find = _text(crate / "web" / "lib" / "findHighlight.ts")
    vis = _function_body(find, "visibleFindFields") or _ts_fn_body(
        find, "visibleFindFields"
    )
    if _LABELS_FIELD.search(vis):
        fail(
            f"{_ISSUE}: find haystack stays subject + body "
            "(do not add chip names)"
        )

    # 9) no SearchHits / inspector chips. SearchPane Filters select is #365.
    hits_src = _text(crate / "web" / "lib" / "SearchHits.svelte")
    if _SEARCH_LABEL.search(hits_src) or re.search(
        r"gmail[-_ ]?label|labelIds|label[-_ ]?filter", hits_src, re.I
    ):
        fail(f"{_ISSUE}: do not put data-gmail-label on SearchHits")
    if _CHIP_HOOK.search(hits_src) or (
        _LABELS_FIELD.search(hits_src) and _BADGE.search(hits_src)
    ):
        fail(f"{_ISSUE}: do not put label chips in SearchHits")
    insp = _text(crate / "web" / "lib" / "PeopleInspector.svelte")
    if _CHIP_HOOK.search(insp) or (
        _LABELS_FIELD.search(insp) and _BADGE.search(insp)
    ):
        fail(f"{_ISSUE}: do not put label chips in PeopleInspector")
    for m in re.finditer(
        r"<div\b[^>]*\bdata-mail-labels\b[^>]*>[\s\S]*?</div>",
        rows_raw,
    ):
        if re.search(r"\bonclick\b|\bhref\s*=|\bapi\.search", m.group(0)):
            fail(
                f"{_ISSUE}: timeline chips stay unclickable "
                "(not a Search control)"
            )

    # 10) D24 docs/user/app.md.
    dtxt = _text(root / "docs" / "user" / "app.md")
    if not dtxt.strip():
        fail(
            f"{_ISSUE}: docs/user/app.md required — Gmail chips under the "
            "subject; WhatsApp chip-less; overflow +k"
        )
    if not _DOCS_CHIPS.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say Gmail / email-thread "
            "bubbles that have labels show quiet chips under the subject"
        )
    if not _DOCS_WA.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must say WhatsApp stays chip-less")
    if not _DOCS_OVERFLOW.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must say overflow is +k")

    # 11) no new locale keys — +k is ASCII; names are not t() keys.
    en = _chrome_pack_entries(_text(crate / "web" / "lib" / "locales" / "en.ts"))
    tr = _chrome_pack_entries(_text(crate / "web" / "lib" / "locales" / "tr.ts"))
    extra_en = set(en) - set(tr)
    extra_tr = set(tr) - set(en)
    if extra_en or extra_tr:
        bits: list[str] = []
        if extra_en:
            bits.append("in en only: " + ", ".join(sorted(extra_en)))
        if extra_tr:
            bits.append("in tr only: " + ", ".join(sorted(extra_tr)))
        fail(
            f"{_ISSUE}: no new locale keys (packs must stay aligned) — "
            + "; ".join(bits)
        )
    for key in list(en) + list(tr):
        if _NEW_LOCALE.search(key):
            fail(
                f"{_ISSUE}: no new Inbox/Sent/+k chrome keys "
                f"(found {key}; +k is ASCII, names are archive data)"
            )
    for k in _T_CALL.findall(mail_then + "\n" + rows):
        if _NEW_LOCALE.search(k):
            fail(f"{_ISSUE}: do not t() Inbox/Sent/+k (found t(\"{k}\"))")
    if re.search(r"\bAda\b|\bBerk\b", " ".join(en.values()) + " ".join(tr.values())):
        fail(f"{_ISSUE}: placeholder names (Ada, Berk) stay out of the chrome pack")
