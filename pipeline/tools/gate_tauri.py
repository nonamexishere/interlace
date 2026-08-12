#!/usr/bin/env python3
"""UI0: unpublished tauri shell, macOS deny exception, CSP, no network entitlement.

#111: person timeline must be chat bubbles (from_me right / else left), not a log.
#112: UTC calendar-day headings (2024-03-15) when sent_at's day changes.
#113: open at latest (scroll after layout); older above; Load older at the top; prepend without jump;
#     last bubble sits above the “Bodies are text only” chrome (list bottom pad);
#     clear tlLoading before the open-person scroll; nested rAF so wrap has happened.
#114: after selecting a person, list conversations (dm / group / email_thread) with
#     title + platform + last_at; default All (D18 merged); pick one to filter the
#     timeline; groups still need include-groups in the list and in All; no raw ids.
#     Identity chrome (Merge, include groups, unlink) is hidden until the person
#     name is clicked. Conversation switcher is a compact header control, not a
#     second always-expanded list above the bubbles. People sidebar stays.
#     All / the open panel must stack above sticky .day-heading (higher z-index
#     than the heading, plus a background so the date cannot show through).
#     Switcher label (summary + each row): empty title or title === personTitle
#     → pretty platform (WhatsApp, Gmail — not raw whatsapp); distinct titles
#     (groups, mail subjects) stay as the title. Subtitle may still show
#     platform + last_at. No raw ids.
#159: people sidebar must not scroll sideways — overflow-x hidden on the people
#     pane (or ScrollArea defaults); vertical scroll stays; long names / activity
#     previews truncate (or min-w-0 / minmax(0, …)) so they do not widen the
#     column; people list still visible when a chat is open; no raw person ids
#     in list labels. Not the conversation switcher (#114).
#156: boot screen — centered CSS spinner (pre-JS splash + Opening-last-archive),
#     not a blank page with a corner Loading line; keep “Opening last archive”;
#     light/dark; no network images / CDN / splash video / server progress %.
#138: people `/` filter matches linked identity values (phone/email haystack on the
#     loaded list), not only display_name. Still client-side; no country-code UI.
#115: timeline bubble platform chip (text badge, not CDN img) + toolbar filter
#     All + platforms present for this person (data-derived from conversations /
#     timeline — dynamic {#each} OK; not a forever-visible full platform matrix).
#     WhatsApp only hides Gmail (client filter on row.platform or core/API arg).
#116: timeline kind filter All + kinds present for this person (data-derived from
#     conversation_kind on conversations / timeline — dynamic {#each} OK; not a
#     forever-visible All|DMs|Email|Groups matrix). Client filter on
#     row.conversation_kind (AND with platform filter). Groups still need
#     include-groups; empty state when the combined filter yields no rows;
#     Load older must not sit under that empty filtered view; j/k walks the
#     visible (combined-filtered) indices only.
#117: email_thread / gmail bubbles: subject as a title (not only body_text||subject
#     fallback); fold quoted tails (On … wrote: / leading >) behind “Show quoted”
#     (or similar); still text nodes (whitespace-pre-wrap / plain), never {@html}
#     for the mail body; no cid: remote images; no send/compose chrome. WhatsApp
#     / non-mail rows keep a plain body path (not forced through the mail layout).
#118: in-window photo lightbox from local CAS — click timeline/search thumbnail →
#     full-size overlay from casDataUrl / data: URL; Esc and/or backdrop close;
#     no remote http(s) in the viewer; optional prev/next among same-message
#     attachments. HEIC stays placeholder unless already decoded (no transcode).
#     Not: system Preview, video player chrome, HEIC convert.
#119: voice/audio CAS attachments — in-app player (play/pause + time/duration),
#     local casDataUrl / data: only (no streaming http(s)); omitted/missing stay
#     placeholders. Not: waveform-from-CDN, transcription.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root, run  # noqa: E402

# IPC-only connect-src (no general http/https). 'none' blanks the .app (#107).
CSP = (
    "default-src 'self'; img-src 'self' asset: data: cas:; media-src 'self' cas: data:; "
    "style-src 'self' 'unsafe-inline'; "
    "connect-src ipc: http://ipc.localhost https://ipc.localhost; "
    "frame-src 'none'; font-src 'self'"
)

# #111 — person timeline is a chat (me right / them left), not a metadata log.
_FROM_ME_LAYOUT = re.compile(
    r"(data-from-me\s*=\s*\{(?:\w+\.)?row\.from_me\}"
    r"|class:[A-Za-z0-9_-]+\s*=\s*\{!?(?:\w+\.)?row\.from_me\}"
    r"|class=\{[^}]*row\.from_me[^}]*\})",
)
_ALIGN_RIGHT = (
    "ml-auto",
    "justify-end",
    "self-end",
    "items-end",
    "margin-left: auto",
    "margin-inline-start: auto",
    "justify-content: flex-end",
    "justify-content: end",
    "align-self: flex-end",
    "align-self: end",
)
_ALIGN_LEFT = (
    "mr-auto",
    "justify-start",
    "self-start",
    "items-start",
    "margin-right: auto",
    "margin-inline-end: auto",
    "justify-content: flex-start",
    "justify-content: start",
    "align-self: flex-start",
    "align-self: start",
)
_BUBBLE_ME_VARS = ("--bubble-me", "--color-bubble-me")
_BUBBLE_THEM_VARS = ("--bubble-them", "--color-bubble-them")
_BUBBLE_ME_USE = ("var(--bubble-me)", "var(--color-bubble-me)", "bg-bubble-me", "bubble-me")
_BUBBLE_THEM_USE = (
    "var(--bubble-them)",
    "var(--color-bubble-them)",
    "bg-bubble-them",
    "bubble-them",
)
_PRE_WRAP = re.compile(
    r"<([a-zA-Z][\w:-]*)([^>]*\bwhitespace-pre-wrap\b[^>]*)>(.*?)</\1>",
    re.S,
)

# #112 — day heading when the UTC calendar day of sent_at changes.
_DAY_HEADING = re.compile(
    r"(<h[2-4]\b"
    r"|role\s*=\s*[\"']heading[\"']"
    r"|day-heading"
    r"|day-separator"
    r"|day-sep\b"
    r"|data-day-heading)",
    re.I,
)
_PREV_DAY = re.compile(
    r"("
    r"timeline\s*\[\s*i\s*-\s*1\s*\]"
    r"|prev(?:ious)?Day"
    r"|lastDay"
    r"|dayChanged"
    r"|isNewDay"
    r")",
    re.I,
)
# RFC3339 UTC `2024-03-15T…Z` → calendar day is the `YYYY-MM-DD` prefix (or UTC getters).
_ISO_DAY = re.compile(
    r"("
    r"\.slice\s*\(\s*0\s*,\s*10\s*\)"
    r"|\.substring\s*\(\s*0\s*,\s*10\s*\)"
    r"|toISOString\s*\(\s*\)\s*\.\s*slice\s*\(\s*0\s*,\s*10\s*\)"
    r"|getUTCFullYear"
    r")",
)
_LOCAL_DAY = re.compile(
    r"("
    r"toLocaleDateString"
    r"|\.getFullYear\s*\("
    r"|\.getMonth\s*\("
    r"|\.getDate\s*\("
    r")",
)
_YESTERDAY = re.compile(r"\byesterday\b", re.I)
_TZ_PICKER = re.compile(
    r"(<select\b[^>]{0,120}(timezone|timeZone|tz)\b"
    r"|bind:value=\{[^}]*timeZone"
    r"|name=[\"']timezone[\"'])",
    re.I,
)
_HEADING_IF = re.compile(r"\{#if\s+([^}]+)\}")
_SENT_AT_GUARD = re.compile(
    r"("
    r"sent_at\s*\?\.|"
    r"sent_at\s*&&|"
    r"!\s*(?:row\.)?sent_at|"
    r"if\s*\(\s*!\s*(?:iso|day)\b"
    r")",
)

# #113 — newest page visible at the bottom; Load older at the top; prepend without jump.
# Dogfood: pad the list so the last bubble clears the text-only chrome; scroll after layout.
# Narrow pane: tlLoading = false before the open scroll; nested rAF so wrap has happened.
_LOAD_OLDER = re.compile(r"Load older")
_EACH_TIMELINE = re.compile(r"\{#each\s+(?:timeline|dayGroups)\b")
_CONCAT_BOTTOM = re.compile(r"timeline\.concat\s*\(\s*rows\s*\)")
_PREPEND = re.compile(
    r"("
    r"(?:rows|older|page|reversed|chrono)\s*\.concat\s*\(\s*timeline\s*\)"
    r"|\[\s*\.\.\.[^,\]]+\s*,\s*\.\.\.timeline\s*\]"
    r"|\.unshift\s*\("
    r"|timeline\s*=\s*append\s*\?\s*[^;\n]*\.concat\s*\(\s*timeline\s*\)"
    r")",
)
# Newest-first API page flipped for chat order (older above, newest at the bottom).
_OLDEST_FIRST = re.compile(
    r"("
    r"\.toReversed\s*\("
    r"|\.reverse\s*\("
    r"|oldestFirst"
    r"|\.sort\s*\([^)]*sent_at"
    r")",
    re.I,
)
# Whole newest-first store shown oldest-first (concat-then-reverse is ok).
_FULL_REVERSE = re.compile(
    r"("
    r"timeline\.toReversed\s*\("
    r"|timeline\.slice\s*\(\s*\)\s*\.reverse\s*\("
    r"|\[\s*\.\.\.timeline\s*\]\s*\.reverse\s*\("
    r"|\{#each\s+timeline\.toReversed"
    r")",
)
_SCROLL_TO_BOTTOM = re.compile(
    r"("
    r"scrollTop\s*=\s*[^;\n]*scrollHeight"
    r"|scrollTo\s*\(\s*\{[^}]*scrollHeight"
    r"|scrollIntoView\s*\("
    r")",
    re.I,
)
_SCROLL_PRESERVE = re.compile(
    r"("
    r"scrollTop\s*\+="
    r"|scrollHeight\s*-"
    r"|(?:prev(?:ious)?|old|saved|was)(?:Scroll)?(?:Height|Top)"
    r")",
    re.I,
)
# Enough pad that the last bubble is not under the text-only chrome (not .day-heading 0.25rem).
_TL_PAD_UTIL = re.compile(r"\bpb-(?:8|10|12)\b")
_TL_SPACER = re.compile(
    r"("
    r"\bpb-(?:8|10|12)\b"
    r"|padding-bottom\s*:"
    r"|\bh-(?:8|10|12)\b"
    r"|spacer"
    r")",
    re.I,
)
_SCROLL_AFTER_LAYOUT = re.compile(r"requestAnimationFrame\s*\(|scrollIntoView\s*\(")
_TL_LOADING_FALSE = re.compile(r"\btlLoading\s*=\s*false\b")
_RAF_CALL = re.compile(r"\b(?:window\.)?requestAnimationFrame\s*\(")
_SCROLL_HELPER_SKIP = frozenset(
    {
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "function",
        "return",
        "typeof",
        "new",
        "await",
        "void",
        "requestAnimationFrame",
        "setTimeout",
        "setInterval",
        "queueMicrotask",
        "tick",
        "Promise",
        "Math",
        "Number",
        "String",
        "Boolean",
        "parseInt",
        "document",
        "getElementById",
        "querySelector",
        "querySelectorAll",
        "scrollTo",
        "scrollIntoView",
        "showErr",
        "personShow",
        "personTimeline",
        "toReversed",
        "concat",
    }
)
_LAST_ROW = re.compile(
    r"("
    r"lastElementChild"
    r"|lastChild"
    r"|\.at\s*\(\s*-1\s*\)"
    r"|\[\s*length\s*-\s*1\s*\]"
    r"|length\s*-\s*1"
    r"|:last-child"
    r"|last(?:Row|Bubble|Msg|Message|Item)"
    r")",
    re.I,
)

# #114 — conversation switcher (title + platform + last_at); default All; no raw ids.
_CONV_EACH = re.compile(
    r"\{#each\s+"
    r"(?:(?:[\w.$]+)?conversations|convos|personConversations|"
    r"conversationList|convList|visibleConversations|filteredConversations)\b"
)
_CONV_SWITCHER_HOOK = re.compile(
    r"(data-conversation-switcher|id=[\"']conversation-switcher[\"'])",
    re.I,
)
_CONV_SELECT = re.compile(
    r"<select\b[^>]{0,400}(conversation|convo)",
    re.I | re.S,
)
_CONV_STATE_DEFAULT_ALL = re.compile(
    r"(?:selectedConversation(?:Id)?|conversationId|conversationFilter|"
    r"selectedConvo|activeConversation|pickedConversation)"
    r"\s*=\s*\$state\s*(?:<[^>]*>)?\s*\(\s*(?:null|undefined|[\"']all[\"'])",
    re.I,
)
_CONV_RESET_ALL = re.compile(
    r"(?:selectedConversation(?:Id)?|conversationId|conversationFilter|"
    r"selectedConvo|activeConversation|pickedConversation)"
    r"\s*=\s*(?:null|undefined|[\"']all[\"'])",
    re.I,
)
_CONV_ALL_LABEL = re.compile(r">\s*All\s*<|[\"']All[\"']")
_CONV_TITLE = re.compile(r"(conversation_title|\.title\b|\{[^}]{0,80}\btitle\b[^}]{0,40}\})")
# #114 dogfood — label helper (pretty platform when title is empty / the person).
_CONV_LABEL_HELPER_NAMES = (
    "conversationLabel",
    "switcherLabel",
    "platformLabel",
    "convLabel",
    "conversationHeading",
    "switcherHeading",
)
_PRETTY_WHATSAPP = re.compile(r"[\"']WhatsApp[\"']")
_PRETTY_GMAIL = re.compile(r"[\"']Gmail[\"']")
_RAW_WHATSAPP = re.compile(r"[\"']whatsapp[\"']")
_RAW_GMAIL = re.compile(r"[\"']gmail[\"']")
_TITLE_EQ_PERSON = re.compile(
    r"("
    r"(?:[\w$]+(?:\?\.|\.))*title\b[^;\n]{0,48}(?:===?|!==?)[^;\n]{0,48}"
    r"(?:personTitle|personName|displayName|display_name)\b"
    r"|(?:personTitle|personName|displayName|display_name)\b[^;\n]{0,48}"
    r"(?:===?|!==?)[^;\n]{0,48}(?:[\w$]+(?:\?\.|\.))*title\b"
    r")"
)
_EMPTY_TITLE = re.compile(
    r"("
    r"!\s*(?:[\w$]+(?:\?\.|\.))*title\b"
    r"|(?:[\w$]+(?:\?\.|\.))*title\b[^;\n]{0,40}(?:===?|!==?)\s*[\"']{2}"
    r"|(?:[\w$]+(?:\?\.|\.))*title\b\s*\?\?"
    r"|(?:[\w$]+(?:\?\.|\.))*title\b\s*\|\|"
    r"|(?:[\w$]+(?:\?\.|\.))*title\b[^;\n]{0,24}\.trim\s*\("
    r")"
)
_DISTINCT_TITLE = re.compile(
    r"("
    r"return\s+(?:[\w$]+(?:\?\.|\.))*title\b"
    r"|:\s*(?:[\w$]+(?:\?\.|\.))*title\b"
    r")"
)
_RAW_TITLE_HEADING = re.compile(
    r"^(?:[\w$]+(?:\?\.|\.))*title(?:\s*\?\?\s*[\"']{2})?(?:\s*\|\|\s*[\"']{2})?$"
)
_SUBTITLE_EL = re.compile(
    r"<(span|div|p|small|time)\b[^>]*>"
    r"(?:(?!</\1>).)*\b(?:last_at|lastAt|last_activity_at)\b"
    r"(?:(?!</\1>).)*</\1>",
    re.I | re.S,
)
_CONV_PLATFORM = re.compile(r"\bplatform\b")
_CONV_LAST_AT = re.compile(r"\b(?:last_at|lastAt|last_activity_at)\b")
_CONV_ID_TEXT = re.compile(
    r"\{[^}]{0,80}(?:conversation_id|\.id|person_id|personId|selectedId)[^}]{0,40}\}"
)
_CONV_ID_FALLBACK = re.compile(
    r"(?:conversation_title|\.title|title)\s*\|\|\s*[^\n;]{0,80}"
    r"(?:conversation_id|\.id|person_id|personId)\b"
)
_CONV_PICK = re.compile(
    r"("
    r"(?:onclick|onchange|on:click|on:change)\s*=\s*\{[^}]{0,200}"
    r"(?:conversation|convo|Conversation|Convo)"
    r"|bind:value=\{[^}]{0,80}(?:conversation|convo|Conversation|Convo)"
    r")",
    re.I,
)
_CONV_CREATE = re.compile(r"Create conversation|New conversation", re.I)
_CONV_MUTE = re.compile(r">\s*Mute\s*<")
_CONV_PIN = re.compile(r">\s*(?:Un)?[Pp]in\s*<")
_PERSON_TIMELINE_CALL = re.compile(r"\bpersonTimeline\s*\(")
_INCLUDE_GROUPS_LABEL = re.compile(r"include groups", re.I)

# #114 dogfood — identity chrome + compact switcher (chat must not sit under admin).
# All / the open panel stack above sticky .day-heading (z-index + background).
_MERGE_CTRL = re.compile(r">\s*Merge(?:…|\.{3})?\s*<")
_UNLINK_CTRL = re.compile(r">\s*unlink\s*<", re.I)
_GROUPS_BIND = re.compile(r"bind:checked=\{includeGroups\}")
_GROUPS_LABEL_CTRL = re.compile(
    r"<label\b[^>]*>[\s\S]{0,240}include groups[\s\S]{0,80}</label>",
    re.I,
)
_CLICK_ATTR = re.compile(r"(?:on:click|onclick)(?:\|\w+)*\s*=\s*\{", re.I)
_TMPL_TOKEN = re.compile(
    r"\{#if\s+([^}]+)\}"
    r"|\{:else\s+if\s+([^}]+)\}"
    r"|\{:else\}"
    r"|\{/if\}"
    r"|\{#each\s+([^}]+)\}"
    r"|\{/each\}"
    r"|\{#await\b[^}]*\}"
    r"|\{/await\}"
    r"|\{#key\b[^}]*\}"
    r"|\{/key\}"
    r"|<((?:[A-Za-z][\w]*\.)?(?:Select|Popover|DropdownMenu|Dropdown|Combobox|Menu)"
    r"(?:\.\w+)?|details|select)\b([^>]*)>"
    r"|</((?:[A-Za-z][\w]*\.)?(?:Select|Popover|DropdownMenu|Dropdown|Combobox|Menu)"
    r"(?:\.\w+)?|details|select)\s*>",
    re.I,
)
_HIDDEN_BIND = re.compile(
    r"(?:\bhidden|class:hidden|aria-hidden)\s*=\s*\{",
    re.I,
)
_TITLE_SKIP_ASSIGN = frozenset(
    {
        "selectedId",
        "selectedConversationId",
        "view",
        "err",
        "mergeOpen",
        "mergeQuery",
        "mergeKeepId",
        "mergeKeepName",
        "allowSelf",
        "filter",
        "tlIndex",
        "tlLoading",
        "setup",
        "booting",
        "opening",
    }
)
_PERSON_PANE_SKIP = frozenset(
    {
        "SearchPane.svelte",
        "ReviewPane.svelte",
        "ImportPane.svelte",
        "DoctorPane.svelte",
        "ConfirmDialog.svelte",
        "EmptyState.svelte",
        "CasAttach.svelte",
    }
)
# Sticky .day-heading is z-index 10; All / the open panel must sit above it.
_TW_Z_INDEX = re.compile(r"(?<![\w-])z-(?:\[(\d+)\]|(\d+))(?![\w-])")
_CSS_Z_INDEX = re.compile(r"z-index\s*:\s*(\d+)", re.I)
_CLASS_Z_DIR = re.compile(r"\bclass:z-(\d+)\b")
_TW_STACK_BG = re.compile(
    r"(?<![\w-])((?:(?:group-)?(?:hover|focus|active|focus-visible):)*)"
    r"(bg-(?:background|card|popover|muted|white|black|primary|secondary|accent)"
    r"|bg-\[var\(--color-(?:background|card|popover|muted)\)\])"
    r"(?:/(\d+))?(?![\w-])",
    re.I,
)
_CSS_STACK_BG = re.compile(
    r"background(?:-color)?\s*:\s*(?!none\b|transparent\b)(\S)",
    re.I,
)
_VOID_HTML = frozenset(
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
_TIMELINE_INNER = re.compile(
    r"(id=[\"']person-timeline[\"']|day-heading|\{#each\s+(?:timeline|dayGroups)\b)",
    re.I,
)
_DAY_HEADING_CSS = re.compile(
    r"(?:\.day-heading\b|\.day-separator\b|\.day-sep\b|\[data-day-heading\])[^{]*\{([^}]+)\}",
    re.I,
)


def _web_sources(crate: Path) -> list[Path]:
    web = crate / "web"
    return [
        p
        for p in sorted(web.rglob("*"))
        if p.suffix in {".svelte", ".css"} and "node_modules" not in p.parts
    ]


def _web_logic(crate: Path) -> str:
    """Svelte + TS sources (helpers may live next to App.svelte)."""
    web = crate / "web"
    parts: list[str] = []
    for p in sorted(web.rglob("*")):
        if p.suffix in {".svelte", ".ts"} and "node_modules" not in p.parts:
            parts.append(p.read_text())
    return "\n".join(parts)


def _timeline_block(crate: Path) -> str:
    found: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte":
            continue
        text = p.read_text()
        i = 0
        while True:
            start = text.find("{#each timeline", i)
            if start < 0:
                start = text.find("{#each dayGroups", i)
            if start < 0:
                break
            end = text.find("{/each}", start)
            if end < 0:
                fail(f"#111: unclosed {{#each timeline}} in {p.relative_to(crate)}")
            found.append(text[start:end])
            i = end + len("{/each}")
    if not found:
        fail("#111: person timeline must {#each timeline} or {#each dayGroups} as chat rows")
    return "\n".join(found)


def _css_var(blob: str, names: tuple[str, ...]) -> str | None:
    for name in names:
        m = re.search(rf"{re.escape(name)}\s*:\s*([^;]+);", blob)
        if m:
            return m.group(1).strip()
    return None


def assert_chat_bubbles(crate: Path) -> None:
    """#111: from_me → right bubble; else left. Caption, not a log dump."""
    block = _timeline_block(crate)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))

    if not _FROM_ME_LAYOUT.search(block):
        fail(
            "#111: from_me must choose a right/left bubble "
            "(class or data-from-me), not a you/them log label"
        )
    # Utility classes must be on the timeline row. Colon tokens live in CSS.
    # "Else left" may be default flow; do not require a left utility. Do forbid
    # forcing the not-from_me branch to the right.
    css_right = tuple(t for t in _ALIGN_RIGHT if ":" in t)
    util_right = tuple(t for t in _ALIGN_RIGHT if ":" not in t)
    util_left = tuple(t for t in _ALIGN_LEFT if ":" not in t)
    me_right = any(t in block for t in util_right) or (
        ("bubble-me" in block or "data-from-me" in block) and any(t in blob for t in css_right)
    )
    if not me_right:
        fail("#111: from_me rows must sit on the right (bubble, not a log)")
    tern = re.search(
        r"row\.from_me\s*\?\s*['\"]([^'\"]*)['\"]\s*:\s*['\"]([^'\"]*)['\"]",
        block,
    )
    if tern:
        them_cls = tern.group(2)
        if any(t in them_cls for t in util_right) and not any(t in them_cls for t in util_left):
            fail("#111: rows that are not from_me must sit on the left")

    if re.search(r"\.join\(\s*[\"'] · [\"']\s*\)", block):
        fail("#111: date/platform must be a caption, not a dumped · field list")
    if "caption" not in block.lower() and "<time" not in block.lower():
        fail("#111: date/platform must be a caption (caption class or <time>), not a dump")
    if "row.platform" not in block:
        fail("#111: caption must still show platform")
    if not re.search(
        r"(utcTime|hh:?mm|slice\s*\(\s*11\s*,\s*16\s*\))",
        block + "\n" + blob,
        re.I,
    ):
        fail("#111: caption must show hour:minute, not the full ISO date again")
    if re.search(r"\{row\.sent_at\s*\|\|", block):
        fail("#111: do not dump the full sent_at ISO string in the bubble caption")

    pre = _PRE_WRAP.search(block)
    if not pre:
        fail("#111: timeline body must stay a whitespace-pre-wrap text node")
    attrs, inner = pre.group(2), pre.group(3)
    if re.search(r"\baria-hidden\b", attrs) or re.search(r"\bsr-only\b", attrs):
        fail("#111: screen reader must still get the visible message text")
    if "displayBody" not in inner and "body_text" not in inner:
        fail("#111: screen reader must still get the message text")
    if not (
        "overflow-wrap" in blob
        or "break-words" in block
        or "break-all" in block
        or "overflow-wrap" in block
    ):
        fail("#111: long tokens (URLs) must wrap inside the bubble")

    me = _css_var(blob, _BUBBLE_ME_VARS)
    them = _css_var(blob, _BUBBLE_THEM_VARS)
    if not me or not them:
        fail(
            "#111: distinct bubble colors via CSS variables "
            "(--bubble-me / --bubble-them or --color-bubble-*)"
        )
    if me == them:
        fail("#111: --bubble-me and --bubble-them must be distinct colors")
    if re.search(r"https?://", me) or re.search(r"https?://", them):
        fail("#111: bubble colors must not load images from the network")
    if not any(tok in blob for tok in _BUBBLE_ME_USE):
        fail("#111: --bubble-me must be applied to the me bubble")
    if not any(tok in blob for tok in _BUBBLE_THEM_USE):
        fail("#111: --bubble-them must be applied to the them bubble")
    if re.search(r"url\(\s*['\"]?https?://", blob, re.I):
        fail("#111: no network images in the person timeline chrome")


def assert_day_separators(crate: Path) -> None:
    """#112: UTC day heading (DD/MM/YYYY) when sent_at's day changes; sticky."""
    block = _timeline_block(crate)
    app = (crate / "web" / "App.svelte").read_text()
    logic = _web_logic(crate)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    if not _DAY_HEADING.search(block):
        fail(
            "#112: person timeline must insert a day heading "
            "(h2–h4, role=heading, or day-heading) when the UTC calendar day changes"
        )
    # Heading is a timeline separator, not a label inside the #111 bubble.
    outside_bubbles = block
    for btn in re.findall(r"<button\b.*?</button>", block, re.S):
        outside_bubbles = outside_bubbles.replace(btn, "", 1)
    if not _DAY_HEADING.search(outside_bubbles):
        fail(
            "#112: day heading must sit on the timeline when the UTC day changes, "
            "not inside a chat bubble"
        )

    if_conds = _HEADING_IF.findall(block)
    if not if_conds:
        fail(
            "#112: day heading must be conditional "
            "(when sent_at's UTC calendar day changes; no heading if sent_at is missing)"
        )
    if not any(re.search(r"sent_at|utcDay|dayKey|calendarDay|isoDay|\bday\b", c, re.I) for c in if_conds):
        fail(
            "#112: day heading {#if} must key off the UTC calendar day of sent_at "
            "(do not invent a heading for a row with no date)"
        )

    if not _PREV_DAY.search(block) and not _PREV_DAY.search(app):
        fail(
            "#112: must compare the current row's UTC calendar day to the previous "
            "row (timeline[i - 1]) so a multi-year DM gets day/month/year separators"
        )

    if not _ISO_DAY.search(app) and not _ISO_DAY.search(block) and not _ISO_DAY.search(logic):
        fail(
            "#112: compare days on the UTC ISO date prefix of sent_at "
            "(slice(0, 10) or UTC getters / toISOString)"
        )
    if not re.search(
        r"("
        r"utcDayLabel"
        r"|split\s*\(\s*[\"']-[\"']\s*\)"
        r"|/\$\{"
        r"|day\s*/\s*month"
        r"|padStart"
        r")",
        app + "\n" + logic,
        re.I,
    ):
        fail("#112: day headings must display day/month/year (15/03/2024), not YYYY-MM-DD")

    chrome = app + "\n" + block
    if _LOCAL_DAY.search(chrome) and not re.search(r"getUTC(?:FullYear|Month|Date)", chrome):
        fail("#112: days are UTC; do not format archive-local or the host timezone")

    if _YESTERDAY.search(block) or _YESTERDAY.search(app):
        fail("#112: day headings must be day/month/year, not relative “yesterday”")

    if _TZ_PICKER.search(app) or _TZ_PICKER.search(block):
        fail("#112: no timezone picker")

    # Caption may use `row.sent_at || "no date"` — that is not a day heading.
    if re.search(r"<h[2-4]\b[^>]*>[^<{]*no date", block, re.I):
        fail("#112: do not invent a day heading for a row with no date")

    if not _SENT_AT_GUARD.search(block) and not _SENT_AT_GUARD.search(app):
        fail(
            "#112: missing sent_at must not crash; guard before reading a calendar day "
            "(do not invent a heading for a row with no date)"
        )
    day_src = app + "\n" + block
    if re.search(r"(?:row\.)?sent_at\.slice\s*\(", day_src) and not re.search(
        r"sent_at\s*\?\.", day_src
    ):
        if not re.search(r"if\s*\(\s*!\s*(?:row\.)?sent_at", day_src):
            fail("#112: missing sent_at must not crash; guard before slicing")

    markup = app
    script_end = app.rfind("</script>")
    if script_end >= 0:
        markup = app[script_end:]
    if "UTC" not in markup and "UTC" not in block:
        fail("#112: say UTC in the UI copy (timeline days are UTC)")

    if "UTC" not in dtxt:
        fail("#112: docs/user/app.md must say timeline days are UTC")
    if not re.search(r"(day heading|day separator)", dtxt, re.I):
        fail("#112: docs/user/app.md must describe UTC day headings")
    if not re.search(r"(day/month/year|DD/MM/YYYY|15/03/2024)", dtxt, re.I):
        fail("#112: docs/user/app.md must say day headings are day/month/year")

    sticky_src = "\n".join(p.read_text() for p in _web_sources(crate))
    if not re.search(r"(position\s*:\s*sticky|\bsticky\b)", sticky_src, re.I):
        fail("#112: day heading must stick to the top of the message list while scrolling")


def _matching_each_end(markup: str, each_start: int) -> int:
    depth = 0
    for m in re.finditer(r"\{#each\b|\{/each\}", markup[each_start:]):
        if m.group(0).startswith("{#each"):
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return each_start + m.end()
    return -1


def _person_timeline_open_tag(src: str) -> str:
    m = re.search(
        r"<[^>]*\bid=(?:[\"']person-timeline[\"']|\{[\"']person-timeline[\"']\})[^>]*>",
        src,
        re.I | re.S,
    )
    return m.group(0) if m else ""


def _has_nonzero_padding_bottom(blob: str) -> bool:
    for m in re.finditer(r"padding-bottom\s*:\s*([^;}\n]+)", blob, re.I):
        val = m.group(1).strip().lower()
        if val not in {"0", "0px", "0rem", "0em", "0%", "none"}:
            return True
    return False


def _timeline_css_pad_blocks(blob: str) -> list[str]:
    blocks: list[str] = []
    for rx in (
        r"#person-timeline(?:\s+(?:ol|ul))?\s*\{([^}]+)\}",
        r"\[id=[\"']person-timeline[\"']\](?:\s+(?:ol|ul))?\s*\{([^}]+)\}",
    ):
        blocks.extend(m.group(1) for m in re.finditer(rx, blob, re.I))
    return blocks


def _timeline_has_bottom_pad(crate: Path, app: str) -> bool:
    """True if #person-timeline / the message list pads above the text-only chrome."""
    tag = _person_timeline_open_tag(app)
    if tag and (_TL_PAD_UTIL.search(tag) or _has_nonzero_padding_bottom(tag)):
        return True
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    for block in _timeline_css_pad_blocks(blob):
        if _TL_PAD_UTIL.search(block) or _has_nonzero_padding_bottom(block):
            return True
    for p in _web_sources(crate):
        if p.suffix != ".svelte":
            continue
        text = p.read_text()
        script_end = text.rfind("</script>")
        markup = text[script_end:] if script_end >= 0 else text
        for each in _EACH_TIMELINE.finditer(markup):
            before = markup[: each.start()]
            ol = None
            for m in re.finditer(r"<ol\b[^>]*>", before, re.I | re.S):
                ol = m
            if ol and (
                _TL_PAD_UTIL.search(ol.group(0)) or _has_nonzero_padding_bottom(ol.group(0))
            ):
                return True
            end = _matching_each_end(markup, each.start())
            if end < 0:
                continue
            after = markup[end : end + 900]
            cut = after.lower().find("</scrollarea>")
            if cut < 0:
                cut = after.find("Bodies are text")
            if cut >= 0:
                after = after[:cut]
            if _TL_SPACER.search(after):
                return True
    return False


def _scrolls_after_layout(app: str, logic: str) -> bool:
    """True if open-person scroll waits for layout (rAF and/or last-row scrollIntoView)."""
    src = app + "\n" + logic
    for m in _SCROLL_AFTER_LAYOUT.finditer(src):
        window = src[max(0, m.start() - 500) : m.end() + 500]
        if m.group(0).startswith("requestAnimationFrame"):
            if re.search(r"scrollTop|scrollTo\s*\(|scrollIntoView", window):
                return True
        elif _LAST_ROW.search(window):
            return True
    return False


def _js_next(src: str, i: int) -> int:
    """Advance past a JS comment or string starting at i; else return i."""
    n = len(src)
    if i >= n:
        return i
    if src.startswith("//", i):
        nl = src.find("\n", i)
        return n if nl < 0 else nl + 1
    if src.startswith("/*", i):
        end = src.find("*/", i + 2)
        return n if end < 0 else end + 2
    q = src[i]
    if q in "'\"`":
        j = i + 1
        while j < n:
            if src[j] == "\\":
                j += 2
                continue
            if src[j] == q:
                return j + 1
            j += 1
        return n
    return i


def _without_comments(src: str) -> str:
    out: list[str] = []
    i = 0
    n = len(src)
    while i < n:
        if src.startswith("//", i) or src.startswith("/*", i):
            i = _js_next(src, i)
            continue
        nxt = _js_next(src, i)
        if nxt != i:
            out.append(src[i:nxt])
            i = nxt
            continue
        out.append(src[i])
        i += 1
    return "".join(out)


def _match_closer(src: str, open_idx: int) -> int:
    opener = src[open_idx]
    closer = ")" if opener == "(" else "}"
    depth = 0
    i = open_idx
    n = len(src)
    while i < n:
        nxt = _js_next(src, i)
        if nxt != i:
            i = nxt
            continue
        c = src[i]
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _call_arg(src: str, open_paren: int) -> str:
    close = _match_closer(src, open_paren)
    if close < 0:
        return ""
    return src[open_paren + 1 : close]


def _function_body(src: str, name: str) -> str:
    rx = re.compile(
        rf"(?:async\s+)?function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{"
        rf"|(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?:async\s*)?"
        rf"(?:function\s*)?\([^)]*\)\s*(?:=>\s*)?\{{"
    )
    m = rx.search(src)
    if not m:
        return ""
    open_b = m.end() - 1
    close_b = _match_closer(src, open_b)
    if close_b < 0:
        return src[open_b + 1 :]
    return src[open_b + 1 : close_b]


def _contains_open_latest_scroll(blob: str, whole: str, seen: set[str] | None = None) -> bool:
    """True if blob (or a named rAF callback it references) scrolls to latest."""
    if _SCROLL_TO_BOTTOM.search(blob):
        return True
    found = seen if seen is not None else set()
    for m in _RAF_CALL.finditer(blob):
        arg = _call_arg(blob, m.end() - 1)
        if _SCROLL_TO_BOTTOM.search(arg):
            return True
        ident = re.fullmatch(r"\s*([A-Za-z_]\w*)\s*", arg)
        if ident and ident.group(1) not in found:
            found.add(ident.group(1))
            body = _function_body(whole, ident.group(1))
            if body and _contains_open_latest_scroll(body, whole, found):
                return True
    return False


def _open_person_scroll_anchor(src: str, whole: str) -> int | None:
    """Index of the outer open-person rAF / scrollTop / scrollIntoView (not append +=)."""
    for m in _RAF_CALL.finditer(src):
        arg = _call_arg(src, m.end() - 1)
        if arg and _contains_open_latest_scroll(arg, whole):
            return m.start()
    m = _SCROLL_TO_BOTTOM.search(src)
    return m.start() if m else None


def _clears_loading_before_open_scroll(app: str, logic: str) -> bool:
    """tlLoading = false must appear before the open-person rAF/scroll, not only in finally after."""
    whole = app + "\n" + logic
    fn = _function_body(whole, "selectPerson") or whole
    cleaned = _without_comments(fn)
    whole_c = _without_comments(whole)
    anchor = _open_person_scroll_anchor(cleaned, whole_c)
    if anchor is not None:
        return bool(_TL_LOADING_FALSE.search(cleaned[:anchor]))
    m = _TL_LOADING_FALSE.search(cleaned)
    if not m:
        return False
    after = cleaned[m.end() :]
    for call in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", after):
        name = call.group(1)
        if name in _SCROLL_HELPER_SKIP:
            continue
        body = _function_body(whole_c, name)
        if body and _open_person_scroll_anchor(_without_comments(body), whole_c) is not None:
            return True
    return False


def _nested_raf_around_open_scroll(app: str, logic: str) -> bool:
    """True if a requestAnimationFrame callback itself schedules another rAF that scrolls to latest."""
    whole = _without_comments(app + "\n" + logic)
    for m in _RAF_CALL.finditer(whole):
        arg = _call_arg(whole, m.end() - 1)
        if not arg or not _RAF_CALL.search(arg):
            continue
        if _contains_open_latest_scroll(arg, whole):
            return True
    return False


def assert_timeline_latest(crate: Path) -> None:
    """#113: newest at bottom; Load older at top; prepend without jump; pad / scroll after layout.

    Narrow-pane dogfood: clear tlLoading before the open-person scroll; nested rAF for wrap.
    """
    app = (crate / "web" / "App.svelte").read_text()
    logic = _web_logic(crate)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    found_each = False
    found_load = False
    for p in _web_sources(crate):
        if p.suffix != ".svelte":
            continue
        text = p.read_text()
        script_end = text.rfind("</script>")
        markup = text[script_end:] if script_end >= 0 else text
        if _LOAD_OLDER.search(markup):
            found_load = True
        each = _EACH_TIMELINE.search(markup)
        if not each:
            continue
        found_each = True
        if not _LOAD_OLDER.search(markup):
            fail("#113: Load older button is required (intersection observer is optional)")
        if markup.find("Load older") > each.start():
            fail("#113: Load older must sit at the top of the message list, not under it")
        # A leftover control under the list is the current bug even if one also sits above.
        after_each = markup.find("{/each}", each.start())
        if after_each >= 0 and "Load older" in markup[after_each:]:
            fail("#113: Load older must sit at the top of the message list, not under it")
    if not found_each:
        fail("#113: person timeline must still {#each timeline} or {#each dayGroups}")
    if not found_load:
        fail("#113: Load older button is required (intersection observer is optional)")

    concat_bottom = bool(_CONCAT_BOTTOM.search(logic))
    prepended = bool(_PREPEND.search(logic))
    full_reverse = bool(_FULL_REVERSE.search(logic))
    oldest_first = bool(_OLDEST_FIRST.search(logic))
    if concat_bottom and not full_reverse:
        fail("#113: older pages must be prepended, not concatenated at the bottom")
    if not (prepended or full_reverse or oldest_first):
        fail(
            "#113: visual order is a chat — older above, newest at the bottom "
            "(reverse or sort the newest-first page; prepend older rows)"
        )

    # Initial fetch is already the newest page (`before` unset). Latest must be visible.
    if not _SCROLL_TO_BOTTOM.search(logic) and not _SCROLL_TO_BOTTOM.search(app):
        fail(
            "#113: opening a person must scroll to the bottom "
            "so the latest messages are visible"
        )

    if not _SCROLL_PRESERVE.search(logic) and not _SCROLL_PRESERVE.search(app):
        fail(
            "#113: preserve scroll position when prepending older rows "
            "(do not jump the viewport to 0)"
        )

    # Last bubble must sit above the “Bodies are text only” chrome, not under it.
    if not _timeline_has_bottom_pad(crate, app):
        fail(
            "#113: last bubble must sit above the “Bodies are text only” chrome — "
            "pad the bottom of the message list / #person-timeline "
            "(pb-8, pb-10, pb-12, padding-bottom, or a spacer after {/each})"
        )

    # tick then scrollTop = scrollHeight runs before day groups / images settle.
    if not _scrolls_after_layout(app, logic):
        fail(
            "#113: opening a person must scroll to the newest message after layout "
            "(requestAnimationFrame and/or scrollIntoView on the last row), "
            "not only await tick() then scrollTop = scrollHeight"
        )

    # Loading line still in the pane (tlLoading true) makes one rAF land short on a wrap.
    if not _clears_loading_before_open_scroll(app, logic):
        fail(
            "#113: clear tlLoading before the open-person scroll to latest "
            "(tlLoading = false must run before that scrollTop / scrollIntoView / "
            "requestAnimationFrame, not only in finally after it — "
            "the loading line must leave the pane first)"
        )
    if not _nested_raf_around_open_scroll(app, logic):
        fail(
            "#113: opening a person must wait for wrap on a short pane "
            "(nested requestAnimationFrame around the open-person scroll to latest; "
            "a single rAF while tlLoading is still true is not enough)"
        )

    if not re.search(
        r"("
        r"opens? at (the )?(latest|newest)"
        r"|(latest|newest) messages"
        r"|scroll(?:s|ed)? to the bottom"
        r")",
        dtxt,
        re.I,
    ):
        fail("#113: docs/user/app.md must say the person timeline opens at the latest messages")
    if not re.search(
        r"Load older.{0,80}(top|above)|(top|above).{0,80}Load older",
        dtxt,
        re.I | re.S,
    ):
        fail("#113: docs/user/app.md must say Load older is at the top")
    if not re.search(
        r"("
        r"does not jump"
        r"|don.?t jump"
        r"|without jump"
        r"|keep(?:s|ing)? (the )?(scroll|viewport|place)"
        r"|preserve(?:s|d)? scroll"
        r"|scroll position"
        r")",
        dtxt,
        re.I,
    ):
        fail("#113: docs/user/app.md must say loading older does not jump the viewport")


def _without_calls(src: str, rx: re.Pattern[str]) -> str:
    """Blank out `name(` … matching `)` so a later search ignores those args."""
    out: list[str] = []
    i = 0
    for m in rx.finditer(src):
        out.append(src[i : m.start()])
        close = _match_closer(src, m.end() - 1)
        i = (close + 1) if close >= 0 else m.end()
    out.append(src[i:])
    return "".join(out)


def _strip_tag_attrs(block: str) -> str:
    """Leave element text / mustaches; drop attributes (data-id={c.id} is not visible)."""
    no_mustache_attr = re.sub(
        r"\s+[A-Za-z_:][\w:.-]*\s*=\s*\{(?:[^{}]|\{[^{}]*\})*\}",
        "",
        block,
    )
    no_quoted_attr = re.sub(
        r"\s+[A-Za-z_:][\w:.-]*\s*=\s*(?:\"[^\"]*\"|'[^']*')",
        "",
        no_mustache_attr,
    )
    return no_quoted_attr


def _visible_switcher_text(block: str) -> str:
    """User-visible switcher text. Each keys and {#if} tests are not shown."""
    no_attrs = _strip_tag_attrs(block)
    return re.sub(r"\{[#/:@].*?\}", "", no_attrs, flags=re.S)


def _person_detail_markup(app: str) -> str:
    """Person column chrome (title → text-only footer), not the people sidebar."""
    start = app.find("{personTitle}")
    if start < 0:
        start = app.find("personTitle")
    end = app.find("Bodies are text")
    if start >= 0 and end > start:
        return app[start:end]
    markup = app
    script_end = app.rfind("</script>")
    if script_end >= 0:
        markup = app[script_end:]
    return markup


def _conversation_switcher_blocks(crate: Path) -> list[str]:
    """Conversation list/select chrome — not the people sidebar, not chat bubbles."""
    found: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte":
            continue
        text = p.read_text()
        for m in _CONV_SWITCHER_HOOK.finditer(text):
            found.append(text[max(0, m.start() - 200) : m.end() + 900])
        i = 0
        while True:
            m = _CONV_EACH.search(text, i)
            if not m:
                break
            end = _matching_each_end(text, m.start())
            if end < 0:
                fail(f"#114: unclosed conversation {{#each}} in {p.relative_to(crate)}")
            found.append(text[m.start() : end])
            i = end
        for m in re.finditer(r"<select\b[^>]*>.*?</select>", text, re.I | re.S):
            chunk = m.group(0)
            if re.search(r"conversation|convo", chunk, re.I):
                found.append(chunk)
    return found


def _svelte_markup(text: str) -> str:
    end = text.rfind("</script>")
    return text[end:] if end >= 0 else text


def _template_stack(markup: str, pos: int) -> list[tuple[str, str, str]]:
    """Open {#if}/{#each}/compact tags at pos. {:else} is if-else (not a closed gate)."""
    stack: list[tuple[str, str, str]] = []
    for m in _TMPL_TOKEN.finditer(markup):
        if m.start() >= pos:
            break
        tok = m.group(0)
        if tok.startswith("{#if"):
            stack.append(("if", (m.group(1) or "").strip(), ""))
        elif tok.startswith("{:else if"):
            if stack and stack[-1][0] in {"if", "if-else"}:
                stack[-1] = ("if", (m.group(2) or "").strip(), "")
        elif tok.startswith("{:else}"):
            if stack and stack[-1][0] == "if":
                stack[-1] = ("if-else", stack[-1][1], "")
        elif tok.startswith("{/if}"):
            while stack and stack[-1][0] not in {"if", "if-else"}:
                stack.pop()
            if stack:
                stack.pop()
        elif tok.startswith("{#each"):
            stack.append(("each", (m.group(3) or "").strip(), ""))
        elif tok.startswith("{/each}"):
            while stack and stack[-1][0] != "each":
                stack.pop()
            if stack:
                stack.pop()
        elif tok.startswith("{#await") or tok.startswith("{#key"):
            stack.append(("block", tok[:6], ""))
        elif tok.startswith("{/await}") or tok.startswith("{/key}"):
            if stack and stack[-1][0] == "block":
                stack.pop()
        elif tok.startswith("</"):
            name = (m.group(6) or "").lower()
            if stack and stack[-1][0] == "tag" and stack[-1][1].lower() == name:
                stack.pop()
        else:
            stack.append(("tag", (m.group(4) or "").lower(), m.group(5) or ""))
    return stack


def _is_vacuous_chrome_cond(cond: str) -> bool:
    """selectedId / personTitle / true is not 'user opened identity chrome'."""
    parts = re.split(r"&&|\|\|", cond)
    if not parts:
        return True
    for raw in parts:
        p = raw.strip().strip("()")
        p = re.sub(r"^\s*!!?", "", p).strip()
        if re.fullmatch(r"true|1", p, re.I):
            continue
        if re.fullmatch(r"personTitle", p):
            continue
        if re.fullmatch(
            r"(?:selectedId|selectedPerson|identities\.length(?:\s*[><!=]=?\s*0)?"
            r"|personById\s*\([^)]*\)|st|setup|booting|opening"
            r"|view\s*===\s*[\"']\w+[\"'])",
            p,
        ):
            continue
        if re.fullmatch(r"selectedId\s*(?:!=|!==|==|===)\s*(?:null|undefined)", p):
            continue
        return False
    return True


def _details_always_open(attrs: str) -> bool:
    if re.search(r"\bbind:open\b|\bopen\s*=\s*\{", attrs):
        return False
    return bool(re.search(r"\bopen\b", attrs))


def _assigned_idents(expr: str) -> set[str]:
    return set(re.findall(r"\b([A-Za-z_]\w*)\s*=(?!=)", expr))


def _cond_uses_flag(cond: str, flags: set[str]) -> bool:
    return any(re.search(rf"\b{re.escape(f)}\b", cond) for f in flags)


def _title_flags(expr: str, whole: str, seen: set[str] | None = None) -> set[str]:
    found = seen if seen is not None else set()
    flags = {a for a in _assigned_idents(expr) if a not in _TITLE_SKIP_ASSIGN}
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", expr):
        name = m.group(1)
        if name in found or name in _SCROLL_HELPER_SKIP or name in _TITLE_SKIP_ASSIGN:
            continue
        found.add(name)
        body = _function_body(whole, name)
        if body:
            flags |= _title_flags(body, whole, found)
    return flags


def _open_tag_before(markup: str, pos: int) -> tuple[int, str] | None:
    n = len(markup)
    i = pos
    while i > 0:
        lt = markup.rfind("<", 0, i)
        if lt < 0:
            return None
        if markup.startswith("</", lt) or markup.startswith("<!--", lt):
            i = lt
            continue
        j = lt + 1
        q = None
        brace = 0
        while j < n:
            c = markup[j]
            if q:
                if c == q:
                    q = None
            elif c in "'\"":
                q = c
            elif c == "{":
                brace += 1
            elif c == "}":
                if brace:
                    brace -= 1
            elif c == ">" and brace == 0:
                return lt, markup[lt : j + 1]
            j += 1
        return None
    return None


def _is_title_wrapper(tag: str) -> bool:
    name_m = re.match(r"<([\w.]+)", tag)
    if not name_m:
        return False
    name = name_m.group(1).lower()
    if name in {"button", "summary", "h1", "a"}:
        return True
    return bool(re.search(r"personTitle|person-title|data-person-title", tag))


def _ancestor_tags(markup: str, pos: int, limit: int = 4) -> list[str]:
    tags: list[str] = []
    cur = pos
    for _ in range(limit):
        found = _open_tag_before(markup, cur)
        if not found:
            break
        lt, tag = found
        tags.append(tag)
        cur = lt
    return tags


def _click_expr(tag: str) -> str:
    m = _CLICK_ATTR.search(tag)
    if not m:
        return ""
    open_i = m.end() - 1
    close = _match_closer(tag, open_i)
    if close < 0:
        return ""
    return tag[open_i + 1 : close]


def _person_title_pos(markup: str) -> int:
    for pat in (
        "{personTitle}",
        'id="personTitle"',
        "id='personTitle'",
        'class="personTitle"',
        "data-person-title",
        "person-title",
    ):
        i = markup.find(pat)
        if i >= 0:
            return i
    return markup.find("personTitle")


def _identity_title_toggle(markup: str, whole: str) -> tuple[set[str], bool]:
    """Flags assigned by clicking the person title, and whether the title is a <summary>."""
    pos = _person_title_pos(markup)
    if pos < 0:
        return set(), False
    tags = _ancestor_tags(markup, pos)
    candidates: list[str] = []
    if tags:
        candidates.append(tags[0])
        for tag in tags[1:]:
            if _is_title_wrapper(tag):
                candidates.append(tag)
    title_in_summary = any(re.match(r"<summary\b", t, re.I) for t in candidates)
    flags: set[str] = set()
    for tag in candidates:
        expr = _click_expr(tag)
        if expr:
            flags |= _title_flags(expr, whole)
            break
    return flags, title_in_summary


def _hidden_flags_before(markup: str, pos: int) -> set[str]:
    window = markup[max(0, pos - 500) : pos]
    flags: set[str] = set()
    skip = _TITLE_SKIP_ASSIGN | {
        "hidden",
        "true",
        "false",
        "null",
        "undefined",
        "class",
        "aria",
    }
    exprs: list[str] = []
    for m in _HIDDEN_BIND.finditer(window):
        close = _match_closer(window, m.end() - 1)
        if close >= 0:
            exprs.append(window[m.end() : close])
    for m in re.finditer(r"\bclass\s*=\s*\{", window, re.I):
        close = _match_closer(window, m.end() - 1)
        if close < 0:
            continue
        expr = window[m.end() : close]
        if "hidden" in expr.lower():
            exprs.append(expr)
    for expr in exprs:
        for ident in re.findall(r"\b([A-Za-z_]\w*)\b", expr):
            if ident not in skip:
                flags.add(ident)
    return flags


def _chrome_hidden_by_default(markup: str, pos: int) -> bool:
    for kind, a, b in _template_stack(markup, pos):
        if kind == "if" and not _is_vacuous_chrome_cond(a):
            return True
        if kind == "tag" and a.lower() == "details" and not _details_always_open(b):
            return True
    return bool(_hidden_flags_before(markup, pos))


def _chrome_toggled_by_title(
    markup: str, pos: int, flags: set[str], title_in_summary: bool
) -> bool:
    for kind, a, b in _template_stack(markup, pos):
        if kind == "if" and flags and _cond_uses_flag(a, flags):
            return True
        if kind == "tag" and a.lower() == "details" and not _details_always_open(b):
            if title_in_summary:
                return True
            if flags and _cond_uses_flag(b, flags):
                return True
    hidden_fs = _hidden_flags_before(markup, pos)
    return bool(flags and hidden_fs & flags)


def _flag_default_open(logic: str, name: str) -> bool:
    m = re.search(
        rf"\b(?:let|const|var)\s+{re.escape(name)}\s*=\s*"
        rf"(?:\$state\s*(?:<[^>]*>)?\s*\(\s*)?([^\n;)]+)",
        logic,
    )
    if not m:
        return False
    val = m.group(1).strip().rstrip(")").strip()
    return val in {"true", "1", '"open"', "'open'"} or val.startswith("true")


def _person_chrome_markup(text: str) -> str:
    """Person column, including the title open tag (h1 / button / summary onclick)."""
    idx = text.find("{personTitle}")
    if idx < 0:
        idx = text.find("data-conversation-switcher")
    if idx < 0:
        return _person_detail_markup(text)
    # Look back far enough for a wrapping <button>/<summary>/<details>, not to {#if st}.
    start = max(0, idx - 600)
    end = text.find("Bodies are text", idx)
    if end > start:
        return text[start:end]
    return text[start:]


def _person_pane_markups(crate: Path) -> list[str]:
    found: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        text = p.read_text()
        if not (
            "{personTitle}" in text
            or "data-conversation-switcher" in text
            or "openMerge" in text
        ):
            continue
        found.append(_person_chrome_markup(text))
    return found


def _groups_ctrl_pos(detail: str) -> int:
    m = _GROUPS_BIND.search(detail)
    if m:
        return m.start()
    m = _GROUPS_LABEL_CTRL.search(detail)
    if m and re.search(r"<input\b", m.group(0), re.I):
        return m.start()
    return -1


def _is_compact_enclosure(stack: list[tuple[str, str, str]], logic: str = "") -> bool:
    compact_parts = {
        "select",
        "details",
        "popover",
        "dropdownmenu",
        "dropdown",
        "combobox",
        "menu",
    }
    for kind, a, b in stack:
        if kind == "tag":
            parts = a.lower().split(".")
            if any(p in compact_parts for p in parts):
                if "details" in parts and _details_always_open(b):
                    continue
                return True
        if kind == "if" and not _is_vacuous_chrome_cond(a):
            ident = a.strip()
            if ident.isidentifier() and _flag_default_open(logic, ident):
                continue
            return True
    return False


def _always_expanded_conversation_list(crate: Path, logic: str = "") -> bool:
    """True if {#each conversations} is a second always-visible list, not a compact control."""
    for pane in _person_pane_markups(crate):
        for m in _CONV_EACH.finditer(pane):
            if _is_compact_enclosure(_template_stack(pane, m.start()), logic):
                continue
            return True
    return False


def _people_list_hidden_on_select(crate: Path) -> bool:
    for p in _web_sources(crate):
        if p.suffix != ".svelte":
            continue
        markup = _svelte_markup(p.read_text())
        for m in re.finditer(r"\{#each\s+filtered\b", markup):
            for kind, a, _b in _template_stack(markup, m.start()):
                if kind == "if" and re.search(
                    r"!\s*selectedId|selectedId\s*===\s*null|selectedId\s*==\s*null",
                    a,
                ):
                    return True
    return False


def _z_from_text(blob: str) -> int | None:
    """Highest explicit numeric z-index in classes / CSS (z-auto does not count)."""
    best: int | None = None
    for m in _TW_Z_INDEX.finditer(blob):
        n = int(m.group(1) or m.group(2))
        best = n if best is None else max(best, n)
    for m in _CSS_Z_INDEX.finditer(blob):
        n = int(m.group(1))
        best = n if best is None else max(best, n)
    for m in _CLASS_Z_DIR.finditer(blob):
        n = int(m.group(1))
        best = n if best is None else max(best, n)
    return best


def _has_stacking_bg(blob: str) -> bool:
    """Opaque background so a sticky date cannot show through the control."""
    if _CSS_STACK_BG.search(blob):
        return True
    for m in _TW_STACK_BG.finditer(blob):
        if m.group(1):
            continue
        if m.group(3) == "0":
            continue
        return True
    return False


def _tag_name(tag: str) -> str:
    m = re.match(r"</?([A-Za-z][\w:.-]*)", tag)
    return (m.group(1) if m else "").lower()


def _class_list(tag: str) -> list[str]:
    m = re.search(r"\bclass(?:Name)?\s*=\s*[\"']([^\"']*)[\"']", tag, re.I)
    if not m:
        m = re.search(
            r"\bclass(?:Name)?\s*=\s*\{[`'\"]([^`'\"]*)[`'\"]\}",
            tag,
            re.I,
        )
    if not m:
        return []
    return m.group(1).split()


def _id_of(tag: str) -> str | None:
    m = re.search(r"\bid\s*=\s*[\"']([^\"']+)[\"']", tag, re.I)
    return m.group(1) if m else None


def _style_attr(tag: str) -> str:
    m = re.search(r"\bstyle\s*=\s*[\"']([^\"']*)[\"']", tag, re.I)
    return m.group(1) if m else ""


def _css_rules_for(css: str, tag: str) -> str:
    chunks: list[str] = []
    for cls in _class_list(tag):
        esc = re.escape(cls)
        chunks.extend(m.group(1) for m in re.finditer(rf"\.{esc}\b[^{{]*\{{([^}}]+)\}}", css))
    el_id = _id_of(tag)
    if el_id:
        esc = re.escape(el_id)
        chunks.extend(m.group(1) for m in re.finditer(rf"#{esc}\b[^{{]*\{{([^}}]+)\}}", css))
    return "\n".join(chunks)


def _layer_blob(tag: str, css: str) -> str:
    return "\n".join((tag, _style_attr(tag), _css_rules_for(css, tag)))


def _layer_stacks(blob: str, day_z: int) -> tuple[bool, int | None, bool]:
    z = _z_from_text(blob)
    bg = _has_stacking_bg(blob)
    return bool(z is not None and z > day_z and bg), z, bg


def _element_span(markup: str, pos: int) -> tuple[int, str, str] | None:
    """Open tag at/before pos and its inner HTML (not descendants' close)."""
    found = _open_tag_before(markup, pos + 1)
    if not found:
        return None
    lt, tag = found
    name = _tag_name(tag)
    if not name or tag.rstrip().endswith("/>") or name in _VOID_HTML:
        return lt, tag, ""
    start = lt + len(tag)
    depth = 1
    rx = re.compile(rf"<{re.escape(name)}\b|</{re.escape(name)}\s*>", re.I)
    for m in rx.finditer(markup, start):
        if markup.startswith("</", m.start()):
            depth -= 1
            if depth == 0:
                return lt, tag, markup[start : m.start()]
        else:
            depth += 1
    return lt, tag, markup[start:]


def _day_heading_z_index(crate: Path) -> int:
    """Sticky day-heading z-index. Missing still stacks as 10 (current .day-heading)."""
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    found: list[int] = []
    for m in _DAY_HEADING_CSS.finditer(blob):
        z = _z_from_text(m.group(1))
        if z is not None:
            found.append(z)
    for m in re.finditer(r"<[^>]+>", blob):
        tag = m.group(0)
        if not re.search(r"day-heading|day-separator|day-sep\b|data-day-heading", tag, re.I):
            continue
        z = _z_from_text(tag)
        if z is not None:
            found.append(z)
    return max(found) if found else 10


def _switcher_hook_positions(markup: str) -> list[int]:
    pos = [m.start() for m in _CONV_SWITCHER_HOOK.finditer(markup)]
    if pos:
        return pos
    pos = [m.start() for m in _CONV_SELECT.finditer(markup)]
    if pos:
        return pos
    return [m.start() for m in _CONV_EACH.finditer(markup)]


def _is_switcher_tag(tag: str) -> bool:
    if _CONV_SWITCHER_HOOK.search(tag) or _CONV_SELECT.search(tag):
        return True
    return _tag_name(tag) in {"details", "select"}


def _child_open_tag(inner: str, rx: re.Pattern[str]) -> str | None:
    m = rx.search(inner)
    if not m:
        return None
    found = _open_tag_before(inner, m.start() + 1)
    return found[1] if found else m.group(0)


def _switcher_summary_and_panel(tag: str, inner: str) -> tuple[str | None, str | None]:
    """Closed control (summary / select) and the open list, if they are separate."""
    if _tag_name(tag) == "select" or _CONV_SELECT.search(tag):
        return tag, None
    summary = _child_open_tag(inner, re.compile(r"<summary\b", re.I))
    panel = _child_open_tag(
        inner,
        re.compile(
            r"<[^>]*\babsolute\b|<[^>]*role\s*=\s*[\"'](?:listbox|menu)[\"']",
            re.I,
        ),
    )
    if panel is None:
        panel = _child_open_tag(inner, re.compile(r"<(?:ul|ol|menu)\b", re.I))
    return summary, panel


def _switcher_above_day_heading(crate: Path) -> tuple[bool, int, int | None, bool]:
    """Whether All / the open panel stack above .day-heading.

    A z-index on the person-pane header or the switcher element covers both
    the closed label and the dropdown (one stacking context). z-index only on
    the panel leaves All under the sticky date; only on the summary leaves
    the open list under it. People-sidebar overflow (#159) is not in scope.
    """
    day_z = _day_heading_z_index(crate)
    css = "\n".join(p.read_text() for p in _web_sources(crate))
    best_z: int | None = None
    saw_bg = False
    saw_switcher = False
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        markup = p.read_text()
        for pos in _switcher_hook_positions(markup):
            saw_switcher = True
            switcher: tuple[int, str, str] | None = None
            headers: list[str] = []
            cur = pos + 1
            for _ in range(12):
                found = _open_tag_before(markup, cur)
                if not found:
                    break
                lt, _open = found
                el = _element_span(markup, lt)
                if not el:
                    break
                _lt, tag, inner = el
                if switcher is None and _is_switcher_tag(tag):
                    switcher = el
                elif switcher is not None and not _TIMELINE_INNER.search(inner):
                    headers.append(tag)
                cur = lt
            if switcher is None:
                switcher = _element_span(markup, pos)
            if switcher is None:
                continue
            _lt, sw_tag, sw_inner = switcher
            summary, panel = _switcher_summary_and_panel(sw_tag, sw_inner)
            sw_blob = _layer_blob(sw_tag, css)
            hd_blobs = [_layer_blob(h, css) for h in headers]
            su_blob = _layer_blob(summary, css) if summary else ""
            pa_blob = _layer_blob(panel, css) if panel else ""
            sw_ok, sw_z, sw_bg = _layer_stacks(sw_blob, day_z)
            hd_hits = [_layer_stacks(b, day_z) for b in hd_blobs]
            hd_ok = any(ok for ok, _z, _bg in hd_hits)
            su_ok, su_z, su_bg = _layer_stacks(su_blob, day_z) if summary else (False, None, False)
            pa_ok, _pa_z, _pa_bg = _layer_stacks(pa_blob, day_z) if panel else (True, None, True)
            for z in (sw_z, su_z, *(z for _ok, z, _bg in hd_hits)):
                if z is None:
                    continue
                best_z = z if best_z is None else max(best_z, z)
            saw_bg = saw_bg or sw_bg or su_bg or any(bg for _ok, _z, bg in hd_hits)
            # Panel-only stacking does not cover the word All.
            if sw_ok or hd_ok or (su_ok and pa_ok):
                return True, day_z, best_z, True
    if not saw_switcher:
        return False, day_z, best_z, saw_bg
    return False, day_z, best_z, saw_bg


def _ts_function_body(src: str, name: str) -> str:
    """Body or arrow expression of `name`, including a TS `: ReturnType`."""
    body = _function_body(src, name)
    if body:
        return body
    pats = (
        rf"(?:async\s+)?function\s+{re.escape(name)}\s*\(",
        rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?:async\s+)?function\s*\(",
        rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?:async\s*)?\(",
    )
    for pat in pats:
        m = re.search(pat, src)
        if not m:
            continue
        open_p = m.end() - 1
        if open_p < 0 or src[open_p] != "(":
            continue
        close_p = _match_closer(src, open_p)
        if close_p < 0:
            continue
        i = close_p + 1
        n = len(src)
        while i < n and src[i] in " \t\n":
            i += 1
        if i < n and src[i] == ":":
            i += 1
            depth = 0
            while i < n:
                c = src[i]
                if c in "<({[":
                    depth += 1
                elif c in ">)}]":
                    depth -= 1
                elif depth <= 0 and (src.startswith("=>", i) or c == "{"):
                    break
                i += 1
        while i < n and src[i] in " \t\n":
            i += 1
        if src.startswith("=>", i):
            i += 2
            while i < n and src[i] in " \t\n":
                i += 1
        if i < n and src[i] == "{":
            close_b = _match_closer(src, i)
            return src[i + 1 : close_b] if close_b >= 0 else src[i + 1 :]
        j = i
        depth = 0
        while j < n:
            nxt = _js_next(src, j)
            if nxt != j:
                j = nxt
                continue
            c = src[j]
            if c in "({[":
                depth += 1
            elif c in ")}]":
                if depth == 0:
                    break
                depth -= 1
            elif c in ";,\n" and depth == 0:
                break
            j += 1
        return src[i:j]
    return ""


def _helper_with_callees(src: str, name: str, seen: set[str] | None = None) -> str:
    found = seen if seen is not None else set()
    if name in found:
        return ""
    found.add(name)
    body = _ts_function_body(src, name)
    if not body:
        return ""
    parts = [body]
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", body):
        callee = m.group(1)
        if callee in found or callee in _SCROLL_HELPER_SKIP:
            continue
        nested = _helper_with_callees(src, callee, found)
        if nested:
            parts.append(nested)
    return "\n".join(parts)


def _assignment_rhs(src: str, name: str) -> str:
    m = re.search(
        rf"\b(?:const|let|var)\s+{re.escape(name)}\s*=\s*",
        src,
    )
    if not m:
        return ""
    rest = src[m.end() :]
    dm = re.match(r"\$derived(?:\.by)?\s*\(", rest)
    if dm:
        return _call_arg(rest, dm.end() - 1).strip().rstrip(",")
    depth = 0
    j = 0
    while j < len(rest):
        nxt = _js_next(rest, j)
        if nxt != j:
            j = nxt
            continue
        c = rest[j]
        if c in "({[":
            depth += 1
        elif c in ")}]":
            depth -= 1
        elif c == ";" and depth <= 0:
            break
        j += 1
    return rest[:j].strip()


def _is_pretty_platform_blob(blob: str) -> bool:
    """Maps raw slugs to WhatsApp / Gmail (not a raw `whatsapp` fallback)."""
    if not (_PRETTY_WHATSAPP.search(blob) and _PRETTY_GMAIL.search(blob)):
        return False
    return bool(_RAW_WHATSAPP.search(blob) and _RAW_GMAIL.search(blob))


def _pretty_platform_helpers(logic: str) -> set[str]:
    names: set[str] = set()
    for name in _CONV_LABEL_HELPER_NAMES:
        blob = _helper_with_callees(logic, name)
        if blob and _is_pretty_platform_blob(blob):
            names.add(name)
    return names


def _compares_title_to_person(blob: str) -> bool:
    if not re.search(r"\bpersonTitle\b", blob):
        return False
    if _TITLE_EQ_PERSON.search(blob):
        return True
    # `person = personTitle` then `title === person`
    return bool(
        re.search(
            r"(?:[\w$]+(?:\?\.|\.))*title\b[^;\n]{0,48}(?:===?|!==?)",
            blob,
        )
    )


def _blob_chooses_pretty_platform(blob: str, pretty_names: set[str]) -> bool:
    """Empty title or title === personTitle → pretty platform; else title."""
    if not _compares_title_to_person(blob):
        return False
    if not _EMPTY_TITLE.search(blob):
        return False
    if not _DISTINCT_TITLE.search(blob):
        return False
    uses_pretty = any(re.search(rf"\b{re.escape(n)}\s*\(", blob) for n in pretty_names)
    if uses_pretty or _is_pretty_platform_blob(blob):
        return True
    return bool(_PRETTY_WHATSAPP.search(blob) and _PRETTY_GMAIL.search(blob))


def _conversation_chooser_helpers(logic: str) -> dict[str, str]:
    """Named helpers that pick pretty platform vs a distinct title."""
    pretty = _pretty_platform_helpers(logic)
    found: dict[str, str] = {}
    for name in _CONV_LABEL_HELPER_NAMES:
        blob = _helper_with_callees(logic, name)
        if blob and _blob_chooses_pretty_platform(blob, pretty | {name}):
            found[name] = blob
    return found


def _closed_switcher_label_markup(tag: str, inner: str) -> str:
    if _tag_name(tag) == "select" or _CONV_SELECT.search(tag):
        return inner
    sm = re.search(r"<summary\b[^>]*>([\s\S]*?)</summary>", inner, re.I)
    if sm:
        return sm.group(1)
    each = _CONV_EACH.search(inner)
    if each:
        return inner[: each.start()]
    bm = re.search(r"<button\b[^>]*>([\s\S]*?)</button>", inner, re.I)
    if bm:
        return bm.group(1)
    return inner


def _switcher_summary_markup(crate: Path) -> str:
    parts: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        text = p.read_text()
        for m in _CONV_SWITCHER_HOOK.finditer(text):
            el = _element_span(text, m.start())
            if not el:
                window = text[max(0, m.start() - 80) : m.end() + 900]
                sm = re.search(r"<summary\b[^>]*>([\s\S]*?)</summary>", window, re.I)
                if sm:
                    parts.append(sm.group(1))
                continue
            _lt, tag, inner = el
            parts.append(_closed_switcher_label_markup(tag, inner))
        if not parts:
            for m in _CONV_SELECT.finditer(text):
                el = _element_span(text, m.start())
                if el:
                    parts.append(el[2])
    return "\n".join(parts)


def _switcher_row_markup(crate: Path) -> str:
    parts: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        text = p.read_text()
        i = 0
        while True:
            m = _CONV_EACH.search(text, i)
            if not m:
                break
            end = _matching_each_end(text, m.start())
            if end < 0:
                break
            parts.append(text[m.start() : end])
            i = end
    return "\n".join(parts)


def _strip_switcher_subtitles(block: str) -> str:
    prev = None
    out = block
    while prev != out:
        prev = out
        out = _SUBTITLE_EL.sub("", out)
    return out


def _heading_exprs(markup: str) -> list[str]:
    """Visible heading mustaches (not {#if}, not All, not last_at subtitle)."""
    cleaned = _strip_switcher_subtitles(markup)
    cleaned = _strip_tag_attrs(cleaned)
    cleaned = re.sub(r"\{[#/:@].*?\}", "", cleaned, flags=re.S)
    cleaned = re.sub(r">\s*All\s*<|[\"']All[\"']", "", cleaned)
    return [m.group(1).strip() for m in re.finditer(r"\{([^{}]+)\}", cleaned)]


def _expr_with_defs(expr: str, logic: str, depth: int = 0) -> str:
    if depth > 4:
        return expr
    parts = [expr]
    skip = _SCROLL_HELPER_SKIP | {
        "conv",
        "c",
        "title",
        "platform",
        "personTitle",
        "null",
        "undefined",
        "true",
        "false",
    }
    for ident in re.findall(r"\b([A-Za-z_]\w*)\b", expr):
        if ident in skip:
            continue
        rhs = _assignment_rhs(logic, ident)
        if rhs:
            parts.append(rhs)
            parts.append(_expr_with_defs(rhs, logic, depth + 1))
    return "\n".join(parts)


def _uses_named_helper(blob: str, names: set[str] | dict[str, str]) -> bool:
    return any(re.search(rf"\b{re.escape(n)}\s*\(", blob) for n in names)


def _is_raw_title_heading(expr: str, logic: str, choosers: dict[str, str]) -> bool:
    s = expr.strip()
    s = re.sub(r"\s*\?\?\s*[\"']{2}\s*$", "", s).strip()
    s = re.sub(r"\s*\|\|\s*[\"']{2}\s*$", "", s).strip()
    if _RAW_TITLE_HEADING.match(s):
        return True
    if re.fullmatch(r"selectedConversationTitle|conversation_title", s):
        rhs = _assignment_rhs(logic, s)
        if rhs and _uses_named_helper(rhs, choosers):
            return False
        if rhs and _blob_chooses_pretty_platform(rhs, _pretty_platform_helpers(logic)):
            return False
        return True
    return False


def _headings_use_label_helper(
    exprs: list[str],
    logic: str,
    choosers: dict[str, str],
    pretty: set[str],
) -> bool:
    """True if the heading calls the chooser (or inlines empty/name → pretty)."""
    if not exprs:
        return False
    if all(_is_raw_title_heading(e, logic, choosers) for e in exprs):
        return False
    blobs = [_expr_with_defs(e, logic) for e in exprs]
    combined = "\n".join(blobs)
    if choosers and _uses_named_helper(combined, choosers):
        return True
    return _blob_chooses_pretty_platform(combined, pretty)


def _label_helper_falls_back_to_id(blob: str) -> bool:
    return bool(
        re.search(
            r"("
            r"return\s+[^;\n]{0,80}(?:conversation_id|\.id|person_id|personId)\b"
            r"|(?:title|\|\|)\s*[^\n;]{0,80}(?:conversation_id|\.id|person_id|personId)\b"
            r")",
            blob,
        )
    )


def assert_conversation_switcher(crate: Path) -> None:
    """#114: after a person is selected, switch conversations; default All; no raw ids.

    Groups still need include-groups to appear in the list and in All.
    Identity chrome (Merge, include groups, unlink) stays hidden until the
    person name is clicked. Conversation switcher is a compact header control,
    not a second always-expanded list above the bubbles. People sidebar stays.
    All / the open panel must stack above sticky .day-heading (higher z-index
    + background). Switcher label: empty title or title === personTitle shows
    the pretty platform (WhatsApp, Gmail), not the repeated person name;
    distinct titles stay. Not in scope: create / mute / pin. Keep #111–#113.
    """
    app = (crate / "web" / "App.svelte").read_text()
    logic = _web_logic(crate)
    api_src = (crate / "web" / "lib" / "api.ts").read_text()
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    whole = app + "\n" + logic

    blocks = _conversation_switcher_blocks(crate)
    if not blocks:
        fail(
            "#114: after selecting a person, list their conversations "
            "({#each conversations / convos / personConversations / conversationList, "
            "a conversation <select>, or data-conversation-switcher) "
            "with title + platform + last_at"
        )
    switcher = "\n".join(blocks)

    # People sidebar and chat bubbles are not the switcher.
    if _CONV_EACH.search(switcher) is None and not _CONV_SWITCHER_HOOK.search(switcher):
        if not _CONV_SELECT.search(switcher):
            fail(
                "#114: conversation switcher must be a list or select of conversations, "
                "not the people sidebar and not a caption inside a chat bubble"
            )
    tl = _timeline_block(crate)
    if switcher.strip() and switcher.strip() in tl:
        fail(
            "#114: conversation switcher must sit outside the message bubbles "
            "(list conversations, then filter the timeline)"
        )

    detail = _person_detail_markup(app)
    if not _CONV_ALL_LABEL.search(switcher) and not _CONV_ALL_LABEL.search(detail):
        fail("#114: conversation switcher must offer All (default = current D18 merged stream)")
    if not _CONV_STATE_DEFAULT_ALL.search(logic) and not _CONV_STATE_DEFAULT_ALL.search(app):
        fail(
            "#114: default conversation must be All "
            "(selected conversation state starts null / undefined / \"all\")"
        )

    sel = _function_body(whole, "selectPerson")
    if not sel:
        fail("#114: selectPerson must still open a person (default conversation = All)")
    opened_all = bool(_CONV_RESET_ALL.search(sel)) or bool(
        re.search(
            r"conversation(?:Id|_id)\s*:\s*(?:null|undefined|(?:append\s*\?))",
            sel,
        )
    )
    if not opened_all:
        fail(
            "#114: opening a person must default to All (merged D18 stream), "
            "not leave a previously picked conversation_id selected"
        )

    choosers = _conversation_chooser_helpers(logic)
    pretty_helpers = _pretty_platform_helpers(logic)
    # Distinct titles still show; do not require interpolating conv.title when
    # that title is the open person's name (helper may show WhatsApp / Gmail).
    if not _CONV_TITLE.search(switcher):
        title_in_helper = any(
            re.search(r"(?:conversation_title|\.title\b|\btitle\b)", blob)
            for blob in choosers.values()
        )
        if not title_in_helper:
            fail("#114: each conversation in the list must show its title")

    summary_exprs = _heading_exprs(_switcher_summary_markup(crate))
    row_exprs = _heading_exprs(_switcher_row_markup(crate))
    summary_ok = _headings_use_label_helper(summary_exprs, logic, choosers, pretty_helpers)
    rows_ok = _headings_use_label_helper(row_exprs, logic, choosers, pretty_helpers)
    if not choosers and not (summary_ok and rows_ok):
        fail(
            "#114: conversation switcher label must use a helper "
            "(conversationLabel / switcherLabel / platformLabel) that shows "
            "the pretty platform (WhatsApp, Gmail — not raw whatsapp) when "
            "the title is empty or equals personTitle; distinct titles "
            "(groups, mail subjects) still use title"
        )
    if not summary_ok:
        fail(
            "#114: compact switcher summary must call that label helper "
            "(not raw selectedConversationTitle / conv.title as the only heading)"
        )
    if not rows_ok:
        fail(
            "#114: each switcher row heading must call that label helper "
            "(not raw conv.title; subtitle may still show platform + last_at)"
        )
    for blob in choosers.values():
        if _label_helper_falls_back_to_id(blob):
            fail("#114: do not fall back a missing conversation title to a raw id")

    if not _CONV_PLATFORM.search(switcher):
        fail("#114: each conversation in the list must show its platform")
    if not _CONV_LAST_AT.search(switcher):
        fail(
            "#114: each conversation in the list must show last_at "
            "(last activity time of that conversation for this person)"
        )

    if not _CONV_PICK.search(switcher) and not _CONV_PICK.search(detail):
        fail("#114: picking a conversation must select it (click / change / bind)")

    tl_filtered = False
    for m in _PERSON_TIMELINE_CALL.finditer(whole):
        arg = _call_arg(whole, m.end() - 1)
        if re.search(r"conversation(?:Id|_id)\s*:", arg):
            tl_filtered = True
            if not re.search(r"includeGroups", arg):
                fail(
                    "#114: personTimeline must still pass includeGroups "
                    "(All is the current D18 merged stream; groups stay gated)"
                )
            break
    if not tl_filtered:
        fail(
            "#114: picking one conversation must filter the timeline "
            "(personTimeline must pass conversationId / conversation_id; "
            "All passes null so the stream stays D18 merged)"
        )

    api_args = re.search(r"personTimeline\s*:\s*\(\s*args\s*:\s*\{([^}]*)\}", api_src, re.S)
    if not api_args or not re.search(r"conversation(?:Id|_id)\b", api_args.group(1)):
        fail(
            "#114: personTimeline args must include optional conversationId / conversation_id "
            "(All = omitted/null; pick one = that conversation)"
        )

    if not _INCLUDE_GROUPS_LABEL.search(app):
        fail("#114: include groups toggle must remain (groups still require it)")

    list_src = _without_calls(whole, _PERSON_TIMELINE_CALL) + "\n" + switcher
    group_in_list = re.search(
        r"includeGroups[\s\S]{0,400}[\"']group[\"']|[\"']group[\"'][\s\S]{0,400}includeGroups",
        list_src,
    )
    fetched_with_toggle = re.search(
        r"(?:conversations|convos|personConversations|conversationList|convList"
        r"|visibleConversations|filteredConversations)"
        r"\s*=\s*(?:await\s+)?[^=;\n]{0,200}includeGroups",
        list_src,
        re.I,
    )
    if not group_in_list and not fetched_with_toggle:
        fail(
            "#114: groups must require the include-groups toggle to appear in the "
            "conversation list (and in All) — filter kind === \"group\" with includeGroups, "
            "or load the list with includeGroups"
        )
    if re.search(r"kind\s*===?\s*[\"']dm[\"']", list_src) and not re.search(
        r"[\"']group[\"']|email_thread", list_src
    ):
        fail("#114: list dm / group / email_thread, not only DMs")

    visible = _visible_switcher_text(switcher)
    if _CONV_ID_TEXT.search(visible):
        fail(
            "#114: no raw conversation ids or person ids in the conversation switcher "
            "(show title + platform + last_at; data-conversation-id attributes are fine)"
        )
    if (
        _CONV_ID_FALLBACK.search(switcher)
        or _CONV_ID_FALLBACK.search(sel)
        or _CONV_ID_FALLBACK.search(detail)
    ):
        fail("#114: do not fall back a missing conversation title to a raw id")

    markup = app
    script_end = app.rfind("</script>")
    if script_end >= 0:
        markup = app[script_end:]
    if _CONV_CREATE.search(markup) or _CONV_CREATE.search(switcher):
        fail("#114: not in scope — do not add create-conversation chrome")
    if _CONV_MUTE.search(markup) or _CONV_MUTE.search(switcher):
        fail("#114: not in scope — do not add mute-conversation chrome")
    if _CONV_PIN.search(markup) or _CONV_PIN.search(switcher):
        fail("#114: not in scope — do not add pin-conversation chrome")

    if not re.search(
        r"("
        r"conversation switcher"
        r"|list(?:s|ing)? (?:their |the )?conversations"
        r"|conversations? (?:list|switcher|filter)"
        r")",
        dtxt,
        re.I,
    ):
        fail("#114: docs/user/app.md must describe the conversation switcher")
    if not re.search(
        r"("
        r"\bAll\b.{0,100}(default|merged|D18)"
        r"|(default|merged|D18).{0,100}\bAll\b"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail("#114: docs/user/app.md must say All is the default (merged D18 stream)")
    if not re.search(
        r"("
        r"filter(?:s|ed|ing)? (?:the )?timeline"
        r"|timeline.{0,60}filter"
        r"|picking (?:a |one )?conversation"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail("#114: docs/user/app.md must say picking a conversation filters the timeline")
    if not re.search(
        r"("
        r"include groups?.{0,160}conversation"
        r"|conversation.{0,160}include groups?"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#114: docs/user/app.md must say groups still need include-groups "
            "to appear in the conversation list (and in All)"
        )

    # Dogfood: reading a chat must not be buried under identity admin + a second list.
    panes = _person_pane_markups(crate)
    pane = "\n".join(panes) if panes else detail
    merge_at = _MERGE_CTRL.search(pane)
    unlink_at = _UNLINK_CTRL.search(pane)
    groups_at = _groups_ctrl_pos(pane)
    if not merge_at:
        fail(
            "#114: Merge must remain in the person chrome "
            "(hidden until the person name is clicked; do not remove it)"
        )
    if groups_at < 0:
        fail(
            "#114: include groups toggle must remain in the person chrome "
            "(hidden until the person name is clicked; groups still need it)"
        )
    if not unlink_at:
        fail(
            "#114: unlink must remain in the person chrome "
            "(hidden until the person name is clicked; do not remove it)"
        )

    chrome_sites = (
        ("Merge", merge_at.start()),
        ("include groups", groups_at),
        ("unlink", unlink_at.start()),
    )
    for label, pos in chrome_sites:
        if not _chrome_hidden_by_default(pane, pos):
            fail(
                f"#114: {label} must not show until the user opens identity chrome "
                "(default: behind {{#if …}} / hidden / <details> closed — "
                "not sitting above the timeline after selecting a person; "
                "{{#if selectedId}} alone is not a click-to-open gate)"
            )

    flags, title_in_summary = _identity_title_toggle(pane, whole)
    if not flags and not title_in_summary:
        fail(
            "#114: clicking the person title (h1 / personTitle / a button wrapping "
            "the name) must toggle identity chrome (Merge, include groups, unlink)"
        )
    if flags and any(_flag_default_open(logic, name) for name in flags):
        fail(
            "#114: identity chrome must start closed "
            "(toggle state must default false / closed, not true)"
        )
    for label, pos in chrome_sites:
        if not _chrome_toggled_by_title(pane, pos, flags, title_in_summary):
            fail(
                f"#114: clicking the person title must toggle {label} "
                "(same {{#if}} flag, <details> summary, or hidden binding — "
                "not a separate always-visible control)"
            )

    if flags:
        buried = False
        for rx in (_CONV_SWITCHER_HOOK, _CONV_SELECT, _CONV_EACH):
            hit = rx.search(pane)
            if not hit:
                continue
            stack = _template_stack(pane, hit.start())
            if any(kind == "if" and _cond_uses_flag(a, flags) for kind, a, _b in stack):
                buried = True
                break
        if buried:
            fail(
                "#114: conversation switcher must stay in the header next to the "
                "person name (not inside the identity chrome that opens on click)"
            )

    if _always_expanded_conversation_list(crate, logic):
        fail(
            "#114: conversation switcher must be compact in the header "
            "(a <select>, <details>, or a single closed control) — "
            "not a second always-expanded full-width {#each conversations} "
            "list sitting above the bubbles (data-conversation-switcher can stay; "
            "title + platform + last_at still belong inside the compact control)"
        )

    people_src = "\n".join(
        p.read_text() for p in _web_sources(crate) if p.suffix == ".svelte"
    )
    if not re.search(r"\{#each\s+filtered\b", people_src) and not re.search(
        r"id=[\"']person-filter[\"']", people_src
    ):
        fail("#114: people sidebar must stay (do not hide the people list)")
    if _people_list_hidden_on_select(crate):
        fail(
            "#114: people sidebar must stay — do not hide the people list when a "
            "person is selected (no Back-that-hides-the-list in this issue)"
        )

    if not re.search(
        r"("
        r"compact (conversation )?(switcher|control)"
        r"|(conversation )?(switcher|control).{0,80}compact"
        r"|not a second .{0,60}(list|switcher)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#114: docs/user/app.md must say the conversation switcher is a "
            "compact header control (not a second list above the bubbles)"
        )
    if not re.search(
        r"("
        r"(click(?:s|ing)?|tap(?:s|ping)?) (the )?(person )?(name|title)"
        r".{0,160}(Merge|include groups|unlink|identity)"
        r"|(Merge|include groups|unlink|identity chrome)"
        r".{0,160}(click(?:s|ing)?|hidden until|until you click)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#114: docs/user/app.md must say identity chrome "
            "(Merge, include groups, unlink) is hidden until the person name is clicked"
        )

    # Dogfood: sticky .day-heading must not cover All or the open panel.
    stacked, day_z, chrome_z, chrome_bg = _switcher_above_day_heading(crate)
    if not stacked:
        if chrome_z is None or chrome_z <= day_z:
            fail(
                "#114: conversation switcher (data-conversation-switcher / its "
                "summary or panel) or the person-pane header that contains it "
                f"must stack above .day-heading (higher z-index than {day_z}, "
                "and a background so the date cannot show through) — "
                "fail if the switcher/header z-index is missing or "
                f"≤ the day-heading z-index ({day_z})"
            )
        if not chrome_bg:
            fail(
                "#114: conversation switcher / person-pane header must have a "
                "background so the sticky .day-heading date cannot show through "
                "All or the open panel"
            )
        fail(
            "#114: conversation switcher / person-pane header must stack above "
            f".day-heading (z-index > {day_z} and a background; the date must "
            "not cover All or the dropdown)"
        )


# #159 — people sidebar: vertical scroll only; long names/previews do not pan sideways.
_PEOPLE_EACH = re.compile(r"\{#each\s+filtered\b")
_OVERFLOW_X_HIDDEN = re.compile(
    r"("
    r"overflow-x-hidden"
    r"|overflow-x\s*:\s*hidden"
    r"|overflow\s*:\s*hidden\b"
    r")",
    re.I,
)
_OVERFLOW_Y_SCROLL = re.compile(
    r"("
    r"overflow-y-(?:auto|scroll)"
    r"|overflow-y\s*:\s*(?:auto|scroll)"
    r"|overflow\s*:\s*auto\b"
    r"|overflow\s*:\s*scroll\b"
    r")",
    re.I,
)
_OVERFLOW_X_VISIBLE = re.compile(
    r"("
    r"overflow-x-(?:auto|scroll|visible)"
    r"|overflow-x\s*:\s*(?:auto|scroll|visible)"
    r")",
    re.I,
)
_TRUNCATE_TOKENS = re.compile(
    r"("
    r"\btruncate\b"
    r"|text-ellipsis"
    r"|text-overflow\s*:\s*ellipsis"
    r"|line-clamp-\d+"
    r"|overflow-hidden"
    r")",
    re.I,
)
_MIN_W0 = re.compile(
    r"("
    r"\bmin-w-0\b"
    r"|min-width\s*:\s*0"
    r"|minmax\s*\(\s*0\s*,"
    r")",
    re.I,
)
_PEOPLE_NAME = re.compile(r"\b(?:display_name|displayName|personName|name)\b")
_PEOPLE_PREVIEW = re.compile(
    r"\b(?:last_activity_at|lastActivityAt|preview|last_at|status)\b"
)
_PEOPLE_ID_VISIBLE = re.compile(
    r"\{[^}]{0,60}(?:\bp\.id\b|\bperson\.id\b|\bfiltered\b[^}]{0,20}\.id)[^}]{0,20}\}"
)
_PEOPLE_ID_FALLBACK = re.compile(
    r"(?:display_name|displayName|name)\s*\|\|\s*[^\n;]{0,60}"
    r"(?:\bp\.id\b|\bperson\.id\b|\.id\b)"
)
_DATA_PEOPLE_SIDEBAR = re.compile(r"data-people-sidebar", re.I)
_SCROLL_AREA_TAG = re.compile(r"<ScrollArea\b([^>]*)>", re.I | re.S)


def _people_each_block(markup: str) -> str:
    """Innermost {#each filtered …} body for the people list (not switcher)."""
    m = _PEOPLE_EACH.search(markup)
    if not m:
        return ""
    end = _matching_each_end(markup, m.start())
    if end < 0:
        return markup[m.start() :]
    return markup[m.start() : end]


def _people_sidebar_regions(crate: Path) -> list[str]:
    """People column chrome: filter + list, not the conversation switcher."""
    found: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        text = p.read_text()
        if not _PEOPLE_EACH.search(text) and "person-filter" not in text:
            continue
        # Prefer an explicit people-sidebar hook when present.
        for m in _DATA_PEOPLE_SIDEBAR.finditer(text):
            found.append(text[max(0, m.start() - 120) : m.end() + 2400])
        if found:
            continue
        # Else take a window around the people list / filter.
        for m in _PEOPLE_EACH.finditer(text):
            found.append(text[max(0, m.start() - 800) : m.end() + 1200])
        if not found and "person-filter" in text:
            i = text.find("person-filter")
            found.append(text[max(0, i - 400) : i + 2000])
    return found


def _scroll_area_source(crate: Path) -> str:
    p = crate / "web" / "lib" / "components" / "ui" / "scroll-area" / "scroll-area.svelte"
    return p.read_text() if p.is_file() else ""


def _region_overflow_ok(region: str, scroll_defaults: str) -> bool:
    """True if this people pane (or shared ScrollArea defaults) hide x-scroll."""
    # Explicit overflow-x auto/scroll/visible on the people pane is a fail signal
    # unless a more specific hidden also applies on the same ScrollArea.
    for m in _SCROLL_AREA_TAG.finditer(region):
        attrs = m.group(1)
        if _OVERFLOW_X_VISIBLE.search(attrs) and not _OVERFLOW_X_HIDDEN.search(attrs):
            return False
        if _OVERFLOW_X_HIDDEN.search(attrs) and _OVERFLOW_Y_SCROLL.search(attrs):
            return True
        if _OVERFLOW_X_HIDDEN.search(attrs) and _OVERFLOW_Y_SCROLL.search(scroll_defaults):
            return True
        # ScrollArea with people sidebar + defaults that clip x / allow y.
        if (
            _DATA_PEOPLE_SIDEBAR.search(attrs)
            or "border-r" in attrs
            or "min-w-0" in attrs
        ) and _OVERFLOW_X_HIDDEN.search(scroll_defaults) and _OVERFLOW_Y_SCROLL.search(
            scroll_defaults
        ):
            return True
    if _OVERFLOW_X_HIDDEN.search(region) and _OVERFLOW_Y_SCROLL.search(region):
        return True
    if _OVERFLOW_X_HIDDEN.search(scroll_defaults) and _OVERFLOW_Y_SCROLL.search(
        scroll_defaults
    ):
        # Shared ScrollArea defaults apply when the people pane uses ScrollArea.
        if _SCROLL_AREA_TAG.search(region) or "ScrollArea" in region:
            return True
    return False


def _row_clips_long_text(block: str) -> bool:
    """Names / previews must truncate or otherwise not expand the column."""
    if not block:
        return False
    has_name = bool(_PEOPLE_NAME.search(block))
    has_preview = bool(_PEOPLE_PREVIEW.search(block))
    if not has_name:
        return False
    tokens = _TRUNCATE_TOKENS.findall(block)
    if not tokens:
        return False
    # Name + activity preview both shown → both must clip (two truncate sites,
    # or one shared overflow-hidden/line-clamp wrapper plus another clip).
    if has_preview and len(tokens) < 2:
        return False
    return True


# #156 — cold launch: centered CSS spinner, not a corner Loading line.
_BOOT_IF = re.compile(
    r"\{#if\s+((?:booting|opening)(?:\s*\|\|\s*(?:booting|opening))+)\s*\}",
)
_SPIN_ANIM = re.compile(
    r"("
    r"animate-spin\b"
    r"|@keyframes\s+[\w-]*spin[\w-]*"
    r"|animation\s*:\s*[^;\n}]*\bspin\b"
    r"|animation-name\s*:\s*[\w-]*spin[\w-]*"
    r")",
    re.I,
)
_SPINNER_NAME = re.compile(
    r"("
    r"\bspinner\b"
    r"|boot-spinner"
    r"|loading-spinner"
    r"|data-boot-spinner"
    r"|data-spinner"
    r")",
    re.I,
)
_SPINNER_RING = re.compile(
    r"("
    r"rounded-full"
    r"|border-radius\s*:\s*(?:50%|9999px|999px)"
    r")",
    re.I,
)
_SPINNER_BORDER = re.compile(
    r"("
    r"\bborder(?:-[trblxy])?(?:-\d)?\b"
    r"|border(?:-top|-right|-bottom|-left)?\s*:"
    r")",
    re.I,
)
_VIEWPORT_FILL = re.compile(
    r"("
    r"min-h-(?:screen|dvh|svh|full)"
    r"|h-(?:screen|dvh|svh|full)"
    r"|min-height\s*:\s*100(?:vh|dvh|svh|%)"
    r"|height\s*:\s*100(?:vh|dvh|svh|%)"
    r"|(?:fixed|absolute)\s+inset-0"
    r"|inset\s*:\s*0"
    r")",
    re.I,
)
_CENTER_AXIS = re.compile(
    r"("
    r"items-center"
    r"|justify-center"
    r"|place-items-center"
    r"|place-content-center"
    r"|align-items\s*:\s*center"
    r"|justify-content\s*:\s*center"
    r"|place-items\s*:\s*center"
    r"|place-content\s*:\s*center"
    r")",
    re.I,
)
_FLEX_OR_GRID = re.compile(
    r"("
    r"\bflex\b"
    r"|\bgrid\b"
    r"|display\s*:\s*(?:flex|grid|inline-flex)"
    r")",
    re.I,
)
_LIGHT_DARK = re.compile(
    r"("
    r"\bdark:"
    r"|prefers-color-scheme"
    r"|--color-(?:background|foreground|muted)"
    r"|color-scheme\s*:"
    r")",
    re.I,
)
_NET_IMG = re.compile(
    r"("
    r"""(?:src|href)\s*=\s*["']https?://"""
    r"""|url\(\s*['"]?https?://"""
    r"""|<img\b[^>]+https?://"""
    r")",
    re.I,
)
_CDN_HINT = re.compile(
    r"("
    r"cdn\.|unpkg\.com|jsdelivr|googleapis|gstatic|cloudflare"
    r"|fonts\.google"
    r")",
    re.I,
)
_SPLASH_VIDEO = re.compile(r"<video\b", re.I)
_SERVER_PROGRESS = re.compile(
    r"("
    r"progress\s*%"
    r"|percent(?:age)?\s*(?:from|via|of)\s*(?:server|network|http)"
    r"|fetch(?:Progress|Percent)"
    r")",
    re.I,
)


def _boot_opening_block(app: str) -> str:
    """Markup of the booting || opening branch (until {:else…} or {/if})."""
    m = _BOOT_IF.search(app)
    if not m:
        return ""
    rest = app[m.end() :]
    # Branch ends at the first sibling {:else / {:else if / {/if} at depth 0.
    depth = 1
    i = 0
    while i < len(rest):
        if rest.startswith("{#if", i) or rest.startswith("{#each", i) or rest.startswith(
            "{#await", i
        ) or rest.startswith("{#key", i):
            depth += 1
            i += 3
            continue
        if rest.startswith("{/if}", i) or rest.startswith("{/each}", i) or rest.startswith(
            "{/await}", i
        ) or rest.startswith("{/key}", i):
            depth -= 1
            if depth == 0:
                return app[m.start() : m.end() + i]
            i += 3
            continue
        if depth == 1 and (
            rest.startswith("{:else", i) or rest.startswith("{:then", i) or rest.startswith(
                "{:catch", i
            )
        ):
            return app[m.start() : m.end() + i]
        i += 1
    return app[m.start() :]


def _has_css_spinner(blob: str) -> bool:
    """True when blob has a CSS-only rotating spinner (no network image required)."""
    if not blob:
        return False
    if _SPIN_ANIM.search(blob) and (
        _SPINNER_NAME.search(blob) or (_SPINNER_RING.search(blob) and _SPINNER_BORDER.search(blob))
    ):
        return True
    # Tailwind animate-spin on a ring element is enough by itself.
    if re.search(r"animate-spin", blob) and (
        _SPINNER_RING.search(blob) or _SPINNER_BORDER.search(blob) or _SPINNER_NAME.search(blob)
    ):
        return True
    # Named spinner class with an inline/keyframes animation nearby.
    if _SPINNER_NAME.search(blob) and _SPIN_ANIM.search(blob):
        return True
    return False


def _is_viewport_centered(blob: str) -> bool:
    """True when layout fills the viewport and centers content (not corner text)."""
    if not blob:
        return False
    if re.search(r"place-items-center|place-content-center", blob) and _VIEWPORT_FILL.search(
        blob
    ):
        return True
    return bool(
        _VIEWPORT_FILL.search(blob)
        and _CENTER_AXIS.search(blob)
        and _FLEX_OR_GRID.search(blob)
    )


def _plain_corner_loading(html: str) -> bool:
    """True when splash is only plain Loading text with no spinner chrome."""
    body = re.search(r"<body\b[^>]*>(.*)</body>", html, re.I | re.S)
    blob = body.group(1) if body else html
    # Strip scripts — they are not the visible splash.
    blob = re.sub(r"<script\b[^>]*>.*?</script>", "", blob, flags=re.I | re.S)
    if _has_css_spinner(html):
        return False
    if re.search(r"Loading Interlace", blob, re.I) and not _is_viewport_centered(html):
        return True
    # Bare #app text node, no spinner markup.
    if re.search(
        r"""id=["']app["'][^>]*>\s*Loading\b[^<]*\s*</""",
        blob,
        re.I,
    ) and not _has_css_spinner(html):
        return True
    return False


def assert_boot_spinner(crate: Path) -> None:
    """#156: centered CSS spinner on pre-JS splash and Opening-last-archive.

    Cold launch must not be a blank page with a corner Loading line. Spinner is
    CSS-only (no network images / CDN). Keep exact copy “Opening last archive”.
    Light/dark aware. Not: splash video, server progress %, people skeleton.
    """
    index = crate / "index.html"
    if not index.is_file():
        fail("#156: crates/interlace-tauri/index.html missing (pre-JS splash)")
    html = index.read_text()
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#156: App.svelte missing (Opening-last-archive boot state)")
    app = app_path.read_text()
    css_blob = "\n".join(
        p.read_text() for p in _web_sources(crate) if p.suffix == ".css"
    )
    boot = _boot_opening_block(app)

    # 1) Pre-JS splash: centered CSS spinner in index.html (inline — Vite CSS
    # loads with JS, so corner text-only “Loading Interlace…” is not enough).
    if _plain_corner_loading(html):
        fail(
            "#156: pre-JS splash must not be a plain corner Loading line — "
            "index.html needs a centered CSS spinner (inline <style> / classes) "
            "plus short status, not only “Loading Interlace…”"
        )
    # Spinner styles for pre-JS must live in index.html itself (not only app.css).
    if not _has_css_spinner(html):
        fail(
            "#156: pre-JS splash (index.html) must include a CSS-only rotating "
            "spinner (@keyframes / animate-spin / border ring) — no network image"
        )
    if not _is_viewport_centered(html):
        fail(
            "#156: pre-JS splash must center the spinner in the viewport "
            "(flex/grid + items/justify center + min-h-screen/full), "
            "not leave status text in the corner"
        )
    if _NET_IMG.search(html) or _CDN_HINT.search(html):
        fail(
            "#156: pre-JS spinner must be CSS-only — no http(s) image URLs or CDN"
        )
    if _SPLASH_VIDEO.search(html):
        fail("#156: no branded splash <video> (out of scope)")

    # 2) Post-mount boot: booting || opening UI — centered spinner + copy.
    if not boot:
        fail(
            "#156: App.svelte must keep a {#if booting || opening} (or opening || booting) "
            "branch for the Opening-last-archive state"
        )
    if "Opening last archive" not in boot and "Opening last archive" not in app:
        fail(
            "#156: boot screen must keep the exact copy substring "
            "“Opening last archive” (existing gate string)"
        )
    if "Opening last archive" not in boot:
        fail(
            "#156: “Opening last archive” must appear in the booting/opening branch, "
            "not only elsewhere in App.svelte"
        )
    # Spinner may use Tailwind utilities in the branch and/or shared CSS.
    boot_with_css = boot + "\n" + css_blob
    if not _has_css_spinner(boot) and not (
        _has_css_spinner(boot_with_css) and _SPINNER_NAME.search(boot)
    ):
        # Accept spinner markup in branch that relies on global .spinner / animate-spin CSS.
        if not (
            (_SPINNER_NAME.search(boot) or re.search(r"animate-spin", boot))
            and _SPIN_ANIM.search(boot_with_css)
        ):
            fail(
                "#156: Opening-last-archive state must show a CSS rotating spinner "
                "(animate-spin / @keyframes spin / spinner class), not status text only"
            )
    if not _is_viewport_centered(boot):
        fail(
            "#156: Opening-last-archive state must be viewport-centered "
            "(flex/grid + center + full height), not a left-aligned loading line"
        )
    if _NET_IMG.search(boot) or _CDN_HINT.search(boot):
        fail(
            "#156: boot spinner must not load network images or CDN assets"
        )
    if _SPLASH_VIDEO.search(boot):
        fail("#156: no splash <video> on the Opening-last-archive state")
    if _SERVER_PROGRESS.search(boot):
        fail(
            "#156: boot status must not show server/network progress percent "
            "(out of scope)"
        )

    # 3) Light/dark aware — soft: dark: utilities, prefers-color-scheme, or theme vars.
    theme_blob = html + "\n" + app + "\n" + css_blob
    if not _LIGHT_DARK.search(theme_blob):
        fail(
            "#156: boot chrome must follow light/dark "
            "(dark: classes, prefers-color-scheme, or --color-background/foreground)"
        )


# #138 — people `/` filter: identity values on the loaded list, not display_name only.
_PEOPLE_FILTER_IDENTITY_TOKENS = re.compile(
    r"\b(?:"
    r"identity_values|identityValues|"
    r"filter_haystack|filterHaystack|"
    r"value_normalized|valueNormalized"
    r")\b"
)
# `identities` alone is too broad (person detail chrome). Require a person-field
# access (p.identities / person.identities) or the tokens above.
_PEOPLE_FILTER_IDENTITIES_FIELD = re.compile(
    r"(?:\bp|person|row)\s*\??\.\s*identities\b"
    r"|\bidentities\s*\?\?|\bidentities\s*\|\|"
    r"|\b\.\.\.\s*(?:\bp|person)\s*\??\.\s*identities\b"
)
_PEOPLE_FILTER_SKIP_CALLS = frozenset(
    {
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "function",
        "return",
        "typeof",
        "new",
        "await",
        "void",
        "toLowerCase",
        "toUpperCase",
        "trim",
        "includes",
        "filter",
        "map",
        "join",
        "concat",
        "some",
        "every",
        "find",
        "String",
        "Boolean",
        "Number",
        "Array",
        "Math",
        "parseInt",
        "console",
    }
)


def _people_filter_window(src: str) -> str:
    """Logic for the people sidebar filter (`filtered` derived + named helpers)."""
    m = re.search(
        r"(?:const|let)\s+filtered\s*=\s*\$derived\s*\(",
        src,
    )
    if not m:
        m = re.search(r"(?:const|let)\s+filtered\s*=", src)
    if not m:
        return ""
    window = src[m.start() : m.start() + 1600]
    # Expand small named helpers referenced from the filter expression.
    for call in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", window):
        name = call.group(1)
        if name in _PEOPLE_FILTER_SKIP_CALLS:
            continue
        body = _function_body(src, name)
        if body and len(body) < 4000:
            window += "\n" + body
    return window


# #115 — platform chip on timeline bubbles + All | platform toolbar filter.
_PLATFORM_CHIP = re.compile(
    r"("
    r"data-platform-chip"
    r"|platform-chip"
    r"|platformChip"
    r"|class:[A-Za-z0-9_-]*chip\b"
    r"|class=[\"'][^\"']*\b(?:platform-)?chip\b"
    r"|class=[\"'][^\"']*\bbadge\b"
    r"|class:badge\b"
    r"|class=\{[^}]*(?:chip|badge)[^}]*\}"
    r")",
    re.I,
)
_PLATFORM_CHIP_NEAR = re.compile(
    r"("
    r"data-platform-chip"
    r"|platform-chip"
    r"|platformChip"
    r"|\bchip\b[^;{]{0,160}(?:\.platform\b|platformLabel|platform)"
    r"|(?:\.platform\b|platformLabel|platform)[^;{]{0,160}\bchip\b"
    r"|\bbadge\b[^;{]{0,160}(?:\.platform\b|platformLabel|platform)"
    r"|(?:\.platform\b|platformLabel|platform)[^;{]{0,160}\bbadge\b"
    r")",
    re.I | re.S,
)
_REMOTE_PLATFORM_IMG = re.compile(
    r"<img\b[^>]{0,400}https?://[^>]{0,200}"
    r"(?:logo|brand|whatsapp|gmail|favicon|cdn)",
    re.I | re.S,
)
_REMOTE_PLATFORM_URL = re.compile(
    r"url\(\s*['\"]?https?://[^)]*(?:logo|brand|whatsapp|gmail|cdn)",
    re.I,
)
_PLATFORM_FILTER_STATE = re.compile(
    r"\b(?:"
    r"selectedPlatform|platformFilter|timelinePlatform|tlPlatform|"
    r"platformTab|activePlatform|pickedPlatform|filterPlatform|"
    r"platformOnly|timelinePlatformFilter"
    r")\b"
)
_PLATFORM_FILTER_HOOK = re.compile(
    r"(data-platform-filter|id=[\"']platform-filter[\"']|"
    r"data-timeline-platform|class=[\"'][^\"']*platform-filter)",
    re.I,
)
_PLATFORM_TOOLBAR_ALL = re.compile(
    r"("
    r">\s*All\s*<"
    r"|[\"']All[\"']"
    r"|platformFilter\s*===\s*[\"']all[\"']"
    r"|selectedPlatform\s*(?:===?|==)\s*(?:null|undefined|[\"']all[\"'])"
    r")",
    re.I,
)
_PRETTY_PLATFORM_MAP = re.compile(
    r"("
    r"[\"']whatsapp[\"']\s*[:=]\s*[\"']WhatsApp[\"']"
    r"|[\"']gmail[\"']\s*[:=]\s*[\"']Gmail[\"']"
    r"|case\s+[\"']whatsapp[\"']\s*:[^;]{0,40}WhatsApp"
    r"|case\s+[\"']gmail[\"']\s*:[^;]{0,40}Gmail"
    r"|platform\s*===\s*[\"']whatsapp[\"'][^?]{0,40}\?\s*[\"']WhatsApp[\"']"
    r"|platform\s*===\s*[\"']gmail[\"'][^?]{0,40}\?\s*[\"']Gmail[\"']"
    r")",
    re.I,
)
# Client-side: keep row when All or row.platform matches the selection.
_CLIENT_PLATFORM_FILTER = re.compile(
    r"("
    r"\.filter\s*\(\s*(?:\(?)(?:row|r|item|m|msg|t|tl)[^)]{0,80}"
    r"\.platform\b"
    r"|(?:row|r|item|m)\.platform\s*===?\s*(?:selectedPlatform|platformFilter|"
    r"timelinePlatform|tlPlatform|activePlatform|pickedPlatform|filterPlatform|"
    r"platformOnly|p|plat)\b"
    r"|(?:selectedPlatform|platformFilter|timelinePlatform|tlPlatform|"
    r"activePlatform|pickedPlatform|filterPlatform|platformOnly)"
    r"\s*===?\s*(?:row|r|item|m)\.platform\b"
    r"|(?:selectedPlatform|platformFilter|timelinePlatform|tlPlatform|"
    r"activePlatform|filterPlatform)\s*(?:===?|==)\s*[\"']all[\"']"
    r"[^|]{0,80}\|\|"
    r")",
    re.I | re.S,
)
# API / core: personTimeline({ … platform: … }) or person_timeline platform arg.
_API_PLATFORM_FILTER = re.compile(
    r"("
    r"personTimeline\s*\(\s*\{[^}]{0,400}\bplatform\s*:"
    r"|\bplatform\s*:\s*(?:selectedPlatform|platformFilter|timelinePlatform|"
    r"tlPlatform|activePlatform|filterPlatform|null)"
    r")",
    re.I | re.S,
)
# Toolbar options come from this person's conversations / timeline platforms.
_PLATFORM_OPTIONS_FROM_DATA = re.compile(
    r"("
    r"(?:conversations|convos|timeline|personConversations|conversationList)"
    r"\s*(?:\?\.|\.)\s*(?:map|flatMap|reduce|forEach|filter)\s*\([^)]{0,120}"
    r"\.platform\b"
    r"|\.platform\b[\s\S]{0,100}(?:Set|unique|uniq|platformsFor|personPlatforms|"
    r"availablePlatforms|timelinePlatforms|presentPlatforms)"
    r"|(?:Set|unique|uniq|platformsFor|personPlatforms|availablePlatforms|"
    r"timelinePlatforms|presentPlatforms|platformOptions)"
    r"[\s\S]{0,180}\.platform\b"
    r"|new\s+Set\s*\([^)]{0,200}\.platform\b"
    r"|for\s*\(\s*(?:const|let)\s+\w+\s+of\s+"
    r"(?:conversations|convos|timeline|personConversations)\b[^)]{0,80}\)"
    r"[\s\S]{0,220}\.platform\b"
    r"|(?:conversations|convos|timeline|personConversations)"
    r"[\s\S]{0,220}\.platform\b[\s\S]{0,80}(?:add|push|Set)"
    r"|\{#each\s+(?:availablePlatforms|platformOptions|presentPlatforms|"
    r"personPlatforms|timelinePlatforms)\b"
    r")",
    re.I | re.S,
)
# Hard-coded forever list of invented platforms (slack/discord/telegram/signal…)
# used as the toolbar source without deriving from the person.
_INVENTED_PLATFORM_LIST = re.compile(
    r"\[\s*[\"'](?:whatsapp|gmail|contacts)[\"']\s*,\s*"
    r"[\"'](?:whatsapp|gmail|contacts|telegram|signal|slack|discord|imessage|"
    r"sms|messenger|instagram|twitter)[\"']"
    r"[^\]]{0,200}\]",
    re.I,
)

# #116 — conversation kind filter (All | dm | email_thread | group).
_KIND_FILTER_STATE = re.compile(
    r"\b(?:"
    r"kindFilter|conversationKindFilter|timelineKind|tlKind|"
    r"selectedKind|activeKind|pickedKind|filterKind|"
    r"kindOnly|timelineKindFilter|conversationKind|"
    r"kindTab|selectedConversationKind"
    r")\b"
)
_KIND_FILTER_HOOK = re.compile(
    r"(data-kind-filter|id=[\"']kind-filter[\"']|"
    r"data-timeline-kind|class=[\"'][^\"']*kind-filter|"
    r"aria-label=[\"'][^\"']*[Kk]ind)",
    re.I,
)
_KIND_TOOLBAR_ALL = re.compile(
    r"("
    r">\s*All\s*<"
    r"|[\"']All[\"']"
    r"|kindFilter\s*===\s*[\"']all[\"']"
    r"|conversationKindFilter\s*===\s*[\"']all[\"']"
    r"|selectedKind\s*(?:===?|==)\s*(?:null|undefined|[\"']all[\"'])"
    r"|timelineKind\s*(?:===?|==)\s*(?:null|undefined|[\"']all[\"'])"
    r")",
    re.I,
)
# Pretty labels or raw archive kinds in helpers / options (not required all-at-once).
_KIND_OPT_DM = re.compile(
    r"("
    r">\s*DMs?\s*<"
    r"|[\"']DMs?[\"']"
    r"|[\"']dm[\"']"
    r")",
    re.I,
)
_KIND_OPT_EMAIL = re.compile(
    r"("
    r">\s*Email(?:\s+threads?)?\s*<"
    r"|[\"']Email(?:\s+threads?)?[\"']"
    r"|[\"']email_thread[\"']"
    r"|[\"']email[\"']"
    r")",
    re.I,
)
_KIND_OPT_GROUP = re.compile(
    r"("
    r">\s*Groups?\s*<"
    r"|[\"']Groups?[\"']"
    r"|[\"']group[\"']"
    r")",
    re.I,
)
# Kind toolbar options come from this person's conversations / timeline kinds.
# Dynamic {#each availableKinds} is OK for chrome, but the list itself must be
# harvested from data (not a hard-coded forever All|DMs|Email|Groups matrix).
# PersonConversation uses `.kind`; TimelineRow uses `.conversation_kind`.
# Require collecting into a Set/array (add/push) so the filteredTimeline row
# filter alone is not mistaken for option derivation.
_KIND_OPTIONS_FROM_DATA = re.compile(
    r"("
    r"for\s*\(\s*(?:const|let)\s+\w+\s+of\s+"
    r"(?:conversations|convos|timeline|personConversations)\b[^)]{0,80}\)"
    r"[\s\S]{0,220}\.(?:conversation_kind|kind)\b[\s\S]{0,80}(?:\.add\b|push\s*\()"
    r"|(?:availableKinds|kindOptions|presentKinds|personKinds|timelineKinds|"
    r"kindsPresent)\b[\s\S]{0,500}"
    r"(?:for\s*\(\s*(?:const|let)\s+\w+\s+of\s+"
    r"(?:conversations|convos|timeline|personConversations)\b"
    r"|(?:conversations|convos|timeline|personConversations)\s*"
    r"(?:\?\.|\.)\s*(?:map|flatMap|reduce|forEach)\b)"
    r"[\s\S]{0,240}\.(?:conversation_kind|kind)\b"
    r"|(?:conversations|convos|timeline|personConversations)\s*"
    r"(?:\?\.|\.)\s*(?:map|flatMap)\s*\(\s*\w+\s*=>\s*\w+\.(?:conversation_kind|kind)\b"
    r"|new\s+Set\s*\(\s*(?:conversations|convos|timeline|personConversations)"
    r"\s*(?:\?\.|\.)\s*map\s*\([^)]{0,80}\.(?:conversation_kind|kind)\b"
    r")",
    re.I | re.S,
)
# Forever-hard-coded kind toolbar: static onclick targets for dm + email_thread +
# group without a data-derived options list (WhatsApp path must not force Email).
_STATIC_KIND_MATRIX = re.compile(
    r"(?:kindFilter|conversationKindFilter|timelineKind|selectedKind|filterKind)"
    r"\s*=\s*[\"']dm[\"']"
    r"[\s\S]{0,500}"
    r"(?:kindFilter|conversationKindFilter|timelineKind|selectedKind|filterKind)"
    r"\s*=\s*[\"']email_thread[\"']"
    r"[\s\S]{0,500}"
    r"(?:kindFilter|conversationKindFilter|timelineKind|selectedKind|filterKind)"
    r"\s*=\s*[\"']group[\"']",
    re.I,
)
# Client-side: keep row when All or row.conversation_kind matches.
_CLIENT_KIND_FILTER = re.compile(
    r"("
    r"\.filter\s*\(\s*(?:\(?)(?:row|r|item|m|msg|t|tl|x)[^)]{0,100}"
    r"\.conversation_kind\b"
    r"|(?:row|r|item|m|x)\.conversation_kind\s*===?\s*"
    r"(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
    r"selectedKind|activeKind|pickedKind|filterKind|kindOnly|k|kind)\b"
    r"|(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
    r"selectedKind|activeKind|pickedKind|filterKind|kindOnly)"
    r"\s*===?\s*(?:row|r|item|m|x)\.conversation_kind\b"
    r"|(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
    r"selectedKind|filterKind|kindOnly)"
    r"\s*(?:===?|==)\s*[\"']all[\"']"
    r"[^|]{0,100}\|\|"
    r"|conversation_kind\s*===?\s*[\"'](?:dm|email_thread|group)[\"']"
    r")",
    re.I | re.S,
)
# Derived list that reads conversation_kind (filteredTimeline / visibleTimeline…).
_DERIVED_KIND_FILTER = re.compile(
    r"("
    r"(?:filteredTimeline|visibleTimeline|timelineRows|kindRows|"
    r"shownTimeline|displayTimeline|tlRows|visibleRows)"
    r"[^;]{0,400}\.conversation_kind\b"
    r"|\.conversation_kind\b[^;]{0,300}"
    r"(?:filteredTimeline|visibleTimeline|kindRows|displayTimeline|"
    r"shownTimeline|tlRows)"
    r")",
    re.I | re.S,
)
# API / core: personTimeline({ … kind: … }) — optional; client-side is enough.
_API_KIND_FILTER = re.compile(
    r"("
    r"personTimeline\s*\(\s*\{[^}]{0,400}\b(?:kind|conversation_kind)\s*:"
    r"|\b(?:kind|conversationKind)\s*:\s*(?:kindFilter|conversationKindFilter|"
    r"timelineKind|tlKind|selectedKind|activeKind|filterKind|null)"
    r")",
    re.I | re.S,
)
# Platform and kind both participate in the same filter path (AND).
_COMBINED_FILTER_PATH = re.compile(
    r"("
    # Single filter callback / expression that mentions both fields.
    r"\.filter\s*\([^)]{0,200}\.platform\b[^)]{0,200}\.conversation_kind\b"
    r"|\.filter\s*\([^)]{0,200}\.conversation_kind\b[^)]{0,200}\.platform\b"
    # Derived list that chains / includes both predicates nearby.
    r"|(?:filteredTimeline|visibleTimeline|timelineRows|shownTimeline|"
    r"displayTimeline|tlRows)"
    r"[^;]{0,500}\.platform\b[^;]{0,500}\.conversation_kind\b"
    r"|(?:filteredTimeline|visibleTimeline|timelineRows|shownTimeline|"
    r"displayTimeline|tlRows)"
    r"[^;]{0,500}\.conversation_kind\b[^;]{0,500}\.platform\b"
    # Both filter states referenced near the same derived / filter site.
    r"|(?:platformFilter|selectedPlatform|timelinePlatform|tlPlatform|"
    r"activePlatform|filterPlatform)"
    r"[^;]{0,400}"
    r"(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
    r"selectedKind|filterKind|kindOnly)"
    r"|(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
    r"selectedKind|filterKind|kindOnly)"
    r"[^;]{0,400}"
    r"(?:platformFilter|selectedPlatform|timelinePlatform|tlPlatform|"
    r"activePlatform|filterPlatform)"
    r")",
    re.I | re.S,
)
# j/k / highlight use indices from the filtered (visible) list.
_VISIBLE_KIND_JK = re.compile(
    r"("
    r"visibleTlIndices|visibleIndices|visibleTimeline|filteredTimeline"
    r"|nearestVisibleTlIndex"
    r")",
    re.I,
)
# Empty when the *filtered* timeline is empty (not only the raw unfiltered list).
_FILTERED_EMPTY = re.compile(
    r"("
    r"(?:filteredTimeline|visibleTimeline|timelineRows|kindRows|"
    r"shownTimeline|displayTimeline|tlRows|visibleRows)"
    r"\s*(?:\?\.|\.)?\s*length\s*===?\s*0"
    r"|!\s*(?:filteredTimeline|visibleTimeline|timelineRows|kindRows|"
    r"shownTimeline|displayTimeline|tlRows|visibleRows)"
    r"\s*(?:\?\.|\.)?\s*length"
    r"|(?:filteredTimeline|visibleTimeline|timelineRows|kindRows|"
    r"shownTimeline|displayTimeline|tlRows|visibleRows)"
    r"\s*\.length\s*(?:===?|==)\s*0"
    r"|(?:filteredTimeline|visibleTimeline)\s*\.length\s*===\s*0"
    r")",
    re.I,
)
# Kind=group must not force includeGroups on / bypass the D18 groups gate.
_KIND_BYPASS_GROUPS = re.compile(
    r"("
    r"(?:kindFilter|conversationKindFilter|timelineKind|selectedKind|filterKind)"
    r"[^;]{0,120}===?\s*[\"']group[\"'][^;]{0,160}"
    r"includeGroups\s*=\s*true"
    r"|includeGroups\s*=\s*true[^;]{0,160}"
    r"(?:kindFilter|conversationKindFilter|timelineKind|selectedKind|filterKind)"
    r"[^;]{0,80}===?\s*[\"']group[\"']"
    r"|(?:kindFilter|conversationKindFilter|selectedKind)\s*===?\s*[\"']group[\"']"
    r"[^;]{0,200}personTimeline\s*\([^)]{0,200}includeGroups\s*:\s*true"
    r")",
    re.I | re.S,
)


def assert_timeline_platform_chips(crate: Path) -> None:
    """#115: platform chip on each bubble + All + data-derived platform toolbar.

    Acceptance: “WhatsApp only” hides Gmail for that person. Chip is text/badge,
    not a remote CDN brand image. Toolbar offers All plus only platforms present
    for this person (from conversations / timeline) — dynamic {#each} is OK;
    a forever-visible WhatsApp+Gmail button matrix is not required. Client filter
    on row.platform is OK; API/core platform arg also OK when paging.
    """
    app = (crate / "web" / "App.svelte").read_text()
    logic = _web_logic(crate)
    api_src = (crate / "web" / "lib" / "api.ts").read_text()
    whole = app + "\n" + logic
    cleaned = _without_comments(whole)
    block = _timeline_block(crate)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    detail = _person_detail_markup(app)

    # 1) Bubble/row shows platform as a chip/badge — not only bare caption text.
    chip_in_row = bool(_PLATFORM_CHIP.search(block)) and (
        "platform" in block or "platformLabel" in block or "PlatformChip" in block
    )
    if not chip_in_row:
        chip_in_row = bool(_PLATFORM_CHIP_NEAR.search(block))
    if not chip_in_row:
        # Dedicated chip component used from the row (markup may live next door).
        chip_component = bool(
            re.search(
                r"<(?:PlatformChip|platform-chip)\b|data-platform-chip",
                block,
                re.I,
            )
        ) or (
            bool(re.search(r"data-platform-chip|PlatformChip|platform-chip", blob, re.I))
            and bool(
                re.search(
                    r"<(?:PlatformChip|platform-chip)\b|data-platform-chip",
                    block + "\n" + cleaned,
                    re.I,
                )
            )
        )
        if not chip_component:
            fail(
                "#115: each timeline bubble/row must show platform as a chip "
                "(text chip / badge / data-platform-chip), not only bare caption "
                "text like {row.platform}"
            )
    if not re.search(r"\.platform\b|platformLabel|row\.platform", block + "\n" + cleaned):
        fail("#115: chip must still come from the row/conversation platform field")

    # 2) Chip is not a remote image / CDN brand logo.
    timeline_chrome = block + "\n" + detail
    if _REMOTE_PLATFORM_IMG.search(timeline_chrome) or _REMOTE_PLATFORM_IMG.search(blob):
        fail("#115: platform chip must not be a remote <img> / CDN brand logo")
    if _REMOTE_PLATFORM_URL.search(blob):
        fail("#115: platform chip must not load brand logos via url(https://…)")
    if re.search(
        r"<img\b[^>]{0,200}(?:platform|whatsapp|gmail)[^>]{0,200}"
        r"src\s*=\s*[\"']https?://",
        blob,
        re.I | re.S,
    ):
        fail("#115: platform chip must not be an http(s) image (text chip only)")

    # Pretty labels (WhatsApp / Gmail) are OK; raw whatsapp/gmail also OK on chip.
    has_pretty = bool(_PRETTY_WHATSAPP.search(cleaned) and _PRETTY_GMAIL.search(cleaned))
    has_map = bool(_PRETTY_PLATFORM_MAP.search(cleaned))
    if not (has_pretty or has_map or _RAW_WHATSAPP.search(block)):
        # Still require some platform surface on the row.
        if "row.platform" not in block and ".platform" not in block:
            fail(
                "#115: chip may use pretty labels (WhatsApp / Gmail) or raw "
                "platform; must still bind the row platform"
            )

    # 3) Platform filter toolbar: All + data-derived options (not conversation switcher alone).
    # Dynamic {#each availablePlatforms} is OK — do not require WhatsApp and Gmail
    # as always-rendered static buttons for every person.
    has_filter_state = bool(_PLATFORM_FILTER_STATE.search(cleaned))
    has_filter_hook = bool(_PLATFORM_FILTER_HOOK.search(blob))
    toolbar_blob = detail if detail.strip() else app
    # Exclude the message {#each} body so conversation switcher / caption is not enough.
    toolbar_only = toolbar_blob
    for m in _EACH_TIMELINE.finditer(toolbar_blob):
        end = _matching_each_end(toolbar_blob, m.start())
        if end > m.start():
            toolbar_only = toolbar_only.replace(toolbar_blob[m.start() : end], "", 1)
    has_toolbar_all = bool(_PLATFORM_TOOLBAR_ALL.search(toolbar_only)) or bool(
        _PLATFORM_TOOLBAR_ALL.search(cleaned)
    )
    has_dynamic_each = bool(
        re.search(
            r"\{#each\s+(?:availablePlatforms|platformOptions|presentPlatforms|"
            r"personPlatforms|timelinePlatforms|platformsFor)\b",
            toolbar_only + "\n" + app,
            re.I,
        )
    )
    options_from_data = bool(_PLATFORM_OPTIONS_FROM_DATA.search(cleaned))
    if not (has_filter_state or has_filter_hook):
        fail(
            "#115: person timeline must have a platform filter toolbar state "
            "(selectedPlatform / platformFilter / data-platform-filter) — "
            "All + platforms present for this person"
        )
    if not has_toolbar_all:
        fail(
            "#115: platform filter toolbar must offer All when the platform "
            "dimension is active (default = every platform)"
        )
    if not options_from_data:
        fail(
            "#115: platform toolbar options must come from platforms present for "
            "this person (unique platform values from conversations / timeline "
            "via map/Set/for…of), not a hard-coded forever list"
        )
    # Labels / raw values may live only in a helper; dynamic each is enough chrome.
    if not (
        has_dynamic_each
        or has_pretty
        or has_map
        or re.search(
            r"(?:platformFilter|selectedPlatform|timelinePlatform|tlPlatform|"
            r"activePlatform|filterPlatform|platformOnly)[^;]{0,200}"
            r"[\"'](?:whatsapp|gmail)[\"']",
            cleaned,
            re.I | re.S,
        )
        or re.search(r">\s*(?:WhatsApp|Gmail)\s*<|[\"'](?:WhatsApp|Gmail)[\"']", cleaned)
    ):
        fail(
            "#115: platform filter must surface platform options "
            "(data-derived {#each}, pretty labels, or raw platform values)"
        )

    # Default selection is All (null / undefined / "all").
    if not re.search(
        r"(?:selectedPlatform|platformFilter|timelinePlatform|tlPlatform|"
        r"activePlatform|pickedPlatform|filterPlatform|platformOnly|"
        r"timelinePlatformFilter)"
        r"\s*=\s*\$state\s*(?:<[^>]*>)?\s*\(\s*(?:null|undefined|[\"']all[\"'])",
        cleaned,
        re.I,
    ) and not re.search(
        r"(?:selectedPlatform|platformFilter|timelinePlatform|tlPlatform|"
        r"activePlatform|filterPlatform|platformOnly)"
        r"\s*=\s*(?:null|undefined|[\"']all[\"'])",
        cleaned,
        re.I,
    ):
        fail(
            "#115: platform filter must default to All "
            "(selected platform state starts null / undefined / \"all\")"
        )

    # 4) Filtering WhatsApp excludes other platforms (client row.platform or API arg).
    client_ok = bool(_CLIENT_PLATFORM_FILTER.search(cleaned))
    api_ok = bool(_API_PLATFORM_FILTER.search(cleaned))
    # Also accept derived list filtered by platform before {#each}.
    derived_ok = bool(
        re.search(
            r"(?:filteredTimeline|visibleTimeline|timelineRows|platformRows|"
            r"shownTimeline|displayTimeline|tlRows)"
            r"[^;]{0,300}\.platform\b"
            r"|\.platform\b[^;]{0,200}"
            r"(?:filteredTimeline|visibleTimeline|platformRows|displayTimeline)",
            cleaned,
            re.I | re.S,
        )
    )
    if not (client_ok or api_ok or derived_ok):
        fail(
            "#115: “WhatsApp only” must hide other platforms for that person "
            "(filter timeline rows by row.platform client-side, or pass platform "
            "into personTimeline / the core query so Load older stays consistent)"
        )

    # If filter is pushed into the API, personTimeline args must accept platform.
    if api_ok:
        api_args = re.search(
            r"personTimeline\s*:\s*\(\s*args\s*:\s*\{([^}]*)\}",
            api_src,
            re.S,
        )
        if not api_args or not re.search(r"\bplatform\b", api_args.group(1)):
            fail(
                "#115: personTimeline args must include optional platform when "
                "the UI passes a platform filter into the timeline query"
            )

    # 5) Only platforms present for this person — not a hard-coded invented forever-list.
    # (options_from_data already required in §3; still reject invented-only lists.)
    for m in _INVENTED_PLATFORM_LIST.finditer(cleaned):
        window = cleaned[max(0, m.start() - 80) : m.end() + 80]
        if re.search(
            r"platformFilter|selectedPlatform|platformOptions|toolbar|platforms\s*=",
            window,
            re.I,
        ) and not _PLATFORM_OPTIONS_FROM_DATA.search(
            cleaned[max(0, m.start() - 400) : m.end() + 400]
        ):
            fail(
                "#115: do not invent toolbar platforms (slack/discord/…) — "
                "only offer platforms that exist for this person"
            )


def assert_timeline_kind_filter(crate: Path) -> None:
    """#116: All + data-derived kind filter, AND with platform filter.

    Acceptance: Email-only shows conversation_kind === email_thread only.
    Kind toolbar options come from kinds present for this person (conversations /
    timeline) — dynamic {#each} is OK; a forever-visible All|DMs|Email|Groups
    button matrix is not required (WhatsApp path must not force Email threads
    buttons into the markup). Empty state when the combined filter yields no rows.
    Load older must not be required / shown under that empty filtered view.
    Groups still need include-groups (kind=Groups must not invent group rows).
    j/k walks visible (combined-filtered) indices. Client-side like #115 is OK.
    """
    app = (crate / "web" / "App.svelte").read_text()
    logic = _web_logic(crate)
    api_src = (crate / "web" / "lib" / "api.ts").read_text()
    whole = app + "\n" + logic
    cleaned = _without_comments(whole)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    detail = _person_detail_markup(app)

    # 1) Kind filter toolbar state / hook (distinct from the #114 conversation switcher).
    has_filter_state = bool(_KIND_FILTER_STATE.search(cleaned))
    has_filter_hook = bool(_KIND_FILTER_HOOK.search(blob))
    if not (has_filter_state or has_filter_hook):
        fail(
            "#116: person timeline must have a conversation-kind filter "
            "(kindFilter / conversationKindFilter / data-kind-filter) — "
            "All + kinds present for this person"
        )

    # Toolbar chrome: All for the active kind dimension. Kind chips themselves
    # must be data-derived (not a forever-hard-coded full matrix always in DOM).
    toolbar_blob = detail if detail.strip() else app
    toolbar_only = toolbar_blob
    for m in _EACH_TIMELINE.finditer(toolbar_blob):
        end = _matching_each_end(toolbar_blob, m.start())
        if end > m.start():
            toolbar_only = toolbar_only.replace(toolbar_blob[m.start() : end], "", 1)
    has_toolbar_all = bool(_KIND_TOOLBAR_ALL.search(toolbar_only)) or bool(
        _KIND_TOOLBAR_ALL.search(cleaned)
    )
    options_from_data = bool(_KIND_OPTIONS_FROM_DATA.search(cleaned))
    has_dynamic_each = bool(
        re.search(
            r"\{#each\s+(?:availableKinds|kindOptions|presentKinds|personKinds|"
            r"timelineKinds|kindsPresent)\b",
            toolbar_only + "\n" + app,
            re.I,
        )
    )
    if not has_toolbar_all:
        fail(
            "#116: kind filter must offer All when the kind dimension is active "
            "(default = every kind / D18 merged)"
        )
    if not options_from_data:
        fail(
            "#116: kind toolbar options must come from kind / conversation_kind "
            "values present for this person (conversations / timeline via "
            "map/Set/for…of into availableKinds), not a hard-coded forever "
            "All|DMs|Email|Groups matrix always rendered for every person"
        )
    # Static onclick matrix for dm + email_thread + group always in the toolbar
    # forces Email threads under a WhatsApp-only person — reject that.
    if _STATIC_KIND_MATRIX.search(toolbar_only):
        fail(
            "#116: do not hard-code always-rendered DMs + Email threads + Groups "
            "buttons — derive kind chips from this person's conversation_kind "
            "values (dynamic {#each} is OK; WhatsApp must not force Email threads)"
        )
    # Pretty labels / raw archive kinds may live in a helper map; not all required
    # to be visible at once. At least one known kind token should exist for UX.
    has_kind_token = bool(
        _KIND_OPT_DM.search(cleaned)
        or _KIND_OPT_EMAIL.search(cleaned)
        or _KIND_OPT_GROUP.search(cleaned)
        or re.search(r"[\"'](?:dm|email_thread|group)[\"']", cleaned)
    )
    if not (has_kind_token or has_dynamic_each):
        fail(
            "#116: kind filter must be able to select archive kinds "
            "(dm / email_thread / group labels or values, or {#each} over them)"
        )

    # Default selection is All (null / undefined / "all").
    if not re.search(
        r"(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
        r"selectedKind|activeKind|pickedKind|filterKind|kindOnly|"
        r"timelineKindFilter|selectedConversationKind)"
        r"\s*=\s*\$state\s*(?:<[^>]*>)?\s*\(\s*(?:null|undefined|[\"']all[\"'])",
        cleaned,
        re.I,
    ) and not re.search(
        r"(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
        r"selectedKind|activeKind|filterKind|kindOnly)"
        r"\s*=\s*(?:null|undefined|[\"']all[\"'])",
        cleaned,
        re.I,
    ):
        fail(
            "#116: kind filter must default to All "
            "(kind state starts null / undefined / \"all\")"
        )

    # 2) Filtering by kind keeps only matching conversation_kind rows.
    client_ok = bool(_CLIENT_KIND_FILTER.search(cleaned))
    derived_ok = bool(_DERIVED_KIND_FILTER.search(cleaned))
    api_ok = bool(_API_KIND_FILTER.search(cleaned))
    if not (client_ok or derived_ok or api_ok):
        fail(
            "#116: Email-only must show email_thread rows only "
            "(filter timeline rows by row.conversation_kind client-side, "
            "or pass kind into personTimeline / the core query)"
        )
    # Prefer conversation_kind field (archive / TimelineRow), not invented labels alone.
    if not re.search(r"\bconversation_kind\b", cleaned):
        fail(
            "#116: kind filter must key off conversation_kind on timeline rows "
            "(dm / group / email_thread)"
        )

    if api_ok:
        api_args = re.search(
            r"personTimeline\s*:\s*\(\s*args\s*:\s*\{([^}]*)\}",
            api_src,
            re.S,
        )
        if not api_args or not re.search(
            r"\b(?:kind|conversation_kind)\b", api_args.group(1)
        ):
            fail(
                "#116: personTimeline args must include optional kind / "
                "conversation_kind when the UI passes a kind filter into the query"
            )

    # 3) AND with the platform filter — both present on the filter path.
    has_platform = bool(_PLATFORM_FILTER_STATE.search(cleaned)) or bool(
        _PLATFORM_FILTER_HOOK.search(blob)
    )
    if not has_platform:
        fail(
            "#116: platform filter (#115) must remain; kind filter ANDs with it "
            "(Email + WhatsApp keeps only matching rows)"
        )
    if not _COMBINED_FILTER_PATH.search(cleaned):
        fail(
            "#116: kind filter must AND with the platform filter "
            "(same filter path / derived list must consider both "
            "conversation_kind and platform — not replace the platform toolbar)"
        )

    # 4) Groups still require include-groups; kind=Groups must not invent group rows.
    if not _INCLUDE_GROUPS_LABEL.search(app) and not _INCLUDE_GROUPS_LABEL.search(blob):
        fail("#116: include groups toggle must remain (groups still require it)")
    if _KIND_BYPASS_GROUPS.search(cleaned):
        fail(
            "#116: kind=Groups must not force includeGroups=true or bypass the "
            "include-groups gate — groups stay out of the stream when groups are off"
        )
    # Selecting Groups must not be the only way groups appear; includeGroups still gates load.
    if re.search(
        r"(?:kindFilter|conversationKindFilter|selectedKind)\s*===?\s*[\"']group[\"']"
        r"[^;{]{0,200}includeGroups\s*=\s*(?:true|!0|1)\b",
        cleaned,
        re.I | re.S,
    ):
        fail(
            "#116: do not auto-enable include groups when the kind filter is Groups"
        )

    # 5) Empty state when the combined filtered list is empty (email-only, no mail).
    # Raw timeline.length === 0 alone is not enough once filters hide every row.
    # Require EmptyState (or data-empty) in a branch that keys off the *filtered* list,
    # not merely filteredTimeline.length used for day-grouping loops.
    empty_src = app + "\n" + blob
    markup = app
    script_end = app.rfind("</script>")
    if script_end >= 0:
        markup = app[script_end:]
    filtered_empty_cond = re.compile(
        r"("
        r"\{#if\s+[^}]{0,200}"
        r"(?:filteredTimeline|visibleTimeline|timelineRows|displayTimeline|"
        r"shownTimeline|tlRows|visibleRows)"
        r"[^}]{0,80}(?:length|===?\s*0)"
        r"|\{:else\s+if\s+[^}]{0,200}"
        r"(?:filteredTimeline|visibleTimeline|timelineRows|displayTimeline|"
        r"shownTimeline|tlRows|visibleRows)"
        r"[^}]{0,80}(?:length|===?\s*0)"
        r"|(?:filteredTimeline|visibleTimeline|timelineRows|displayTimeline|"
        r"shownTimeline|tlRows|visibleRows)"
        r"\s*(?:\?\.|\.)?\s*length\s*===?\s*0"
        r"|!\s*(?:filteredTimeline|visibleTimeline|timelineRows|displayTimeline|"
        r"shownTimeline|tlRows|visibleRows)"
        r"\s*(?:\?\.|\.)?\s*length"
        r")",
        re.I,
    )
    # Walk markup: filtered-empty condition must sit near EmptyState / data-empty.
    empty_ok = False
    for m in filtered_empty_cond.finditer(markup + "\n" + cleaned):
        window = (markup + "\n" + cleaned)[m.start() : m.end() + 280]
        if re.search(r"EmptyState|data-empty", window, re.I):
            empty_ok = True
            break
    # Script-side flag that drives EmptyState is also OK.
    if not empty_ok and re.search(
        r"(?:filteredEmpty|isFilterEmpty|noVisibleRows|filterEmpty|tlEmpty)\s*=",
        cleaned,
        re.I,
    ):
        if re.search(
            r"(?:filteredEmpty|isFilterEmpty|noVisibleRows|filterEmpty|tlEmpty)"
            r"[\s\S]{0,400}(?:EmptyState|data-empty)"
            r"|(?:EmptyState|data-empty)[\s\S]{0,400}"
            r"(?:filteredEmpty|isFilterEmpty|noVisibleRows|filterEmpty|tlEmpty)",
            empty_src,
            re.I,
        ):
            empty_ok = True
    if not empty_ok:
        fail(
            "#116: when the kind/platform filter yields no rows "
            "(e.g. Email-only and the person has no mail), show an empty state "
            "on the filtered list — not only when the unfiltered timeline is empty"
        )
    # Empty copy should be reachable in the person timeline pane (static presence).
    if not re.search(r"EmptyState|data-empty", detail if detail.strip() else app, re.I):
        fail("#116: person timeline must keep an EmptyState path for the empty filter case")

    # 5b) Load older must not show under the empty filtered view.
    # #113 still requires the control to exist in markup; it must not be required
    # (or left visible) when filteredTimeline is empty next to "No messages…".
    if re.search(r"Load older", markup, re.I):
        load_guarded = False
        for m in re.finditer(r"\{#if\s+([^}]+)\}", markup):
            cond = m.group(1)
            block_start = m.end()
            # End at matching {/if} at depth 1 from this {#if}, approx via next Load older.
            next_load = markup.find("Load older", block_start)
            if next_load < 0:
                continue
            between = markup[block_start:next_load]
            # Skip if another {#if} opens first without this cond applying directly —
            # require Load older appears before any nested {#if} or only simple content.
            if re.search(r"\{#if\b", between):
                continue
            if re.search(
                r"(?:filteredTimeline|visibleTimeline|timelineRows|displayTimeline|"
                r"shownTimeline|tlRows|visibleRows)",
                cond,
                re.I,
            ):
                load_guarded = True
                break
        # Also accept: Load older only after an {:else} of a filtered-empty branch
        # (empty filtered → EmptyState; else → Load older path).
        if not load_guarded and re.search(
            r"(?:filteredTimeline|visibleTimeline|timelineRows|displayTimeline|"
            r"shownTimeline|tlRows|visibleRows)"
            r"[^}]{0,80}(?:length\s*===?\s*0|!\s*\w+\.length)"
            r"[\s\S]{0,400}\{:else\b[\s\S]{0,400}Load older",
            markup,
            re.I,
        ):
            load_guarded = True
        if not load_guarded:
            fail(
                "#116: Load older must not show under the empty filtered view "
                "(gate it on filteredTimeline.length / visible rows — do not "
                "require Load older when the kind/platform filter hides every row)"
            )

    # 6) j/k / highlight walk visible indices from the combined-filtered list.
    if not _VISIBLE_KIND_JK.search(cleaned):
        fail(
            "#116: j/k must walk only visible (combined-filtered) timeline rows "
            "(visibleTlIndices / filteredTimeline), not the full unfiltered list"
        )
    # visible indices derivation should hang off the same filtered list that applies kind.
    if not re.search(
        r"(?:visibleTlIndices|visibleIndices)\s*=\s*\$derived\s*\("
        r"[^)]{0,200}(?:filteredTimeline|visibleTimeline|timelineRows)",
        cleaned,
        re.I | re.S,
    ) and not re.search(
        r"(?:filteredTimeline|visibleTimeline)[^;]{0,200}"
        r"(?:visibleTlIndices|visibleIndices|\.map\s*\([^)]*index)",
        cleaned,
        re.I | re.S,
    ):
        # Softer: onKey / j/k references filtered or visible indices at all.
        if not re.search(
            r"(?:key\s*===?\s*[\"']j[\"']|[\"']j[\"']\s*\|\||ArrowDown)"
            r"[\s\S]{0,400}"
            r"(?:visibleTlIndices|visibleIndices|filteredTimeline|visibleTimeline)",
            cleaned,
            re.I,
        ) and not re.search(
            r"(?:visibleTlIndices|visibleIndices|filteredTimeline)"
            r"[\s\S]{0,400}"
            r"(?:key\s*===?\s*[\"']j[\"']|[\"']j[\"']|ArrowDown)",
            cleaned,
            re.I,
        ):
            fail(
                "#116: j/k (and the selection ring) must use the combined-filtered "
                "visible indices so hidden kind/platform rows are skipped"
            )


def assert_people_filter_identity(crate: Path) -> None:
    """#138: people `/` filter matches linked identity values, not only display_name.

    Static: filter expression (or its helpers) must read identity material from
    the loaded person row (identity_values / filter_haystack / p.identities).
    Display-name-only matching is a fail. Still client-side on the list.
    """
    app = (crate / "web" / "App.svelte").read_text()
    logic = _web_logic(crate)
    src = _without_comments(app + "\n" + logic)

    if "person-filter" not in src:
        fail("#138: people sidebar must keep id=person-filter")
    if not _PEOPLE_EACH.search(app):
        fail("#138: people list must still {#each filtered …} as person rows")

    window = _people_filter_window(src)
    if not window.strip():
        fail("#138: people sidebar `filtered` list derivation missing")

    has_identity = bool(_PEOPLE_FILTER_IDENTITY_TOKENS.search(window)) or bool(
        _PEOPLE_FILTER_IDENTITIES_FIELD.search(window)
    )
    if not has_identity:
        fail(
            "#138: people `/` filter must match linked identity values "
            "(identity_values / filter_haystack / p.identities on the loaded list), "
            "not only display_name"
        )
    if "display_name" not in window and "displayName" not in window:
        fail("#138: people filter must still match display_name")


def assert_people_sidebar_no_x_scroll(crate: Path) -> None:
    """#159: people sidebar must not pan sideways; vertical scroll only.

    Long names and activity previews stay readable via truncate / min-w-0 /
    minmax(0, …) — they must not push the left column wider. People list stays
    when a chat is open. No raw person ids in list labels. Not #114 switcher.
    """
    app = (crate / "web" / "App.svelte").read_text()
    people_src = "\n".join(
        p.read_text() for p in _web_sources(crate) if p.suffix == ".svelte"
    )
    regions = _people_sidebar_regions(crate)
    region_blob = "\n".join(regions) if regions else ""
    scroll_defaults = _scroll_area_source(crate)

    # 1) People list still exists and is not hidden when a person is selected.
    if not _PEOPLE_EACH.search(people_src) and not re.search(
        r"id=[\"']person-filter[\"']", people_src
    ):
        fail(
            "#159: people sidebar must still list people "
            "({#each filtered …} and/or person-filter) — do not remove the left column"
        )
    if _people_list_hidden_on_select(crate):
        fail(
            "#159: people sidebar must stay visible when a person is selected "
            "(do not hide the people list when a chat is open — that is not this issue)"
        )

    # 2) Scroll container: overflow-x hidden; overflow-y auto/scroll.
    if not regions and not (
        _OVERFLOW_X_HIDDEN.search(scroll_defaults)
        and _OVERFLOW_Y_SCROLL.search(scroll_defaults)
        and _SCROLL_AREA_TAG.search(app)
    ):
        fail(
            "#159: people sidebar scroll region not found "
            "({#each filtered}, person-filter, or data-people-sidebar)"
        )

    overflow_ok = False
    if regions:
        overflow_ok = any(_region_overflow_ok(r, scroll_defaults) for r in regions)
    if not overflow_ok:
        # Shared ScrollArea defaults alone are enough when people pane uses it.
        if (
            _SCROLL_AREA_TAG.search(app)
            and _OVERFLOW_X_HIDDEN.search(scroll_defaults)
            and _OVERFLOW_Y_SCROLL.search(scroll_defaults)
            and not _OVERFLOW_X_VISIBLE.search(region_blob)
        ):
            overflow_ok = True
    if not overflow_ok:
        fail(
            "#159: people pane must hide horizontal overflow "
            "(overflow-x: hidden / overflow-x-hidden on the people ScrollArea "
            "or shared ScrollArea defaults) while still allowing vertical scroll "
            "(overflow-y: auto|scroll)"
        )
    if _OVERFLOW_X_VISIBLE.search(region_blob) and not _OVERFLOW_X_HIDDEN.search(
        region_blob + "\n" + scroll_defaults
    ):
        fail(
            "#159: people pane must not enable horizontal pan "
            "(overflow-x auto/scroll/visible without overflow-x hidden)"
        )

    # 3) Long names / previews do not expand the column indefinitely.
    each_blocks = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        text = p.read_text()
        markup = _svelte_markup(text)
        block = _people_each_block(markup)
        if block:
            each_blocks.append(block)
    if not each_blocks:
        fail("#159: people list must still {#each filtered …} as person rows")
    people_rows = "\n".join(each_blocks)
    if not _row_clips_long_text(people_rows):
        fail(
            "#159: long person names and activity previews must truncate "
            "(or ellipsis / line-clamp / overflow-hidden) so they stay readable "
            "without pushing the people column wider"
        )
    # Column track or row ancestors must be able to shrink (min-w-0 / minmax(0, …)).
    column_blob = region_blob + "\n" + app
    if not _MIN_W0.search(column_blob) and not _MIN_W0.search(people_rows):
        fail(
            "#159: people column / row content must allow shrink "
            "(min-w-0 or grid minmax(0, …)) so truncate can take effect"
        )

    # 4) No raw person-id copy in people list labels (undo event ids elsewhere ok).
    visible_rows = _strip_tag_attrs(people_rows)
    visible_rows = re.sub(r"\{[#/:@].*?\}", "", visible_rows, flags=re.S)
    if _PEOPLE_ID_VISIBLE.search(visible_rows):
        fail(
            "#159: no raw person ids in the people list labels "
            "(show display name / preview; data-id attributes are fine)"
        )
    if _PEOPLE_ID_FALLBACK.search(people_rows):
        fail("#159: do not fall back a missing person name to a raw id")


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
# Sole body fallback that treats subject as body when body is empty — not a title.
_SUBJECT_BODY_FALLBACK_ONLY = re.compile(
    r"(?:body_text\s*\|\|\s*(?:(?:item\.)?row\.)?subject"
    r"|(?:displayBody|bodyText)\s*\(\s*(?:(?:item\.)?row\.)?body_text\s*\|\|"
    r"\s*(?:(?:item\.)?row\.)?subject)",
    re.I,
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


_SHOW_QUOTED = re.compile(
    r"("
    r"Show quoted"
    r"|Show quote"
    r"|Show quotes"
    r"|Expand quoted"
    r"|Expand quote"
    r"|Quoted text"
    r"|showQuoted"
    r"|showQuote"
    r"|quotedExpanded"
    r"|expandQuoted"
    r"|data-show-quoted"
    r")",
    re.I,
)
_QUOTE_SPLIT = re.compile(
    r"("
    # “On … wrote:” marker (literal, regex, or template).
    r"On\s+.{0,60}wrote\s*:"
    r"|On\s+\\?\$\{[^}]{0,40}\}\s+wrote"
    r"|/On\s+.+?wrote\s*:/"
    r"|[\"']On [\"'][^;]{0,80}wrote"
    r"|[\"']wrote:[\"']"
    r"|wrote:"
    # Named pure split / fold helpers (synthetic placeholders only in tests).
    r"|splitQuoted(?:Body|Tail|Text)?"
    r"|splitQuote(?:d)?(?:Body|Tail)?"
    r"|quoteTail"
    r"|quotedTail"
    r"|quotedBody"
    r"|foldQuoted"
    r"|quoteSplit"
    r"|mailQuote"
    r"|extractQuoted"
    r"|stripQuoted"
    r"|unquotedBody"
    r"|bodyWithoutQuote"
    r"|mainBody(?:Text)?"
    # Leading “>” quote lines.
    r"|startsWith\s*\(\s*[\"']>[\"']"
    r"|lines?\s*\.?\s*(?:filter|map|find|some|every|startsWith)"
    r"[^;]{0,80}[\"']>[\"']"
    r"|[\"']>[\"']\s*===?\s*.{0,20}(?:trim|charAt|\[0\])"
    r")",
    re.I | re.S,
)
_HTML_BODY = re.compile(r"\{@html\b")
_CID_IMG = re.compile(
    r"("
    r"cid:"
    r"|src\s*=\s*[\"']cid:"
    r"|src\s*=\s*\{[^}]*cid:"
    r")",
    re.I,
)
_SEND_MAIL_UI = re.compile(
    r"("
    r">\s*Send\s+(?:mail|email|message)\s*<"
    r"|[\"']Send (?:mail|email|message)[\"']"
    r"|compose(?:Mail|Email|Message)"
    r"|data-compose-mail"
    r"|reply-all"
    r"|Reply all"
    r"|mailto:"
    r"|type=[\"']email[\"'][^>]{0,80}compose"
    r"|placeholder=[\"'][^\"']*(?:Write a (?:mail|reply)|Compose)"
    r")",
    re.I,
)
_WA_PLAIN_BODY = re.compile(
    r"("
    r"(?:platform|row\.platform)\s*===?\s*[\"']whatsapp[\"']"
    r"|[\"']whatsapp[\"']\s*===?\s*(?:platform|row\.platform)"
    r"|\bisWhats?App\b"
    r"|!\s*(?:isMail|isEmail|isGmail|mailRow|emailRow)\b"
    r"|\{:else\b"
    r")",
    re.I,
)


def assert_gmail_timeline_rows(crate: Path) -> None:
    """#117: Gmail/email_thread rows — subject title, fold quotes; WA plain.

    Acceptance: long reply chains stay one screen until “Show quoted” expands.
    Subject is a title on mail rows (not only body_text||subject fallback).
    Body stays text nodes (whitespace-pre-wrap / plain); no {@html}, no cid:
    images, no send/compose chrome. WhatsApp / non-mail rows keep a plain body
    path and are not forced through the mail layout.
    """
    app = (crate / "web" / "App.svelte").read_text()
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


# #118 — in-window photo lightbox from local CAS (timeline / search thumbnails).
_LIGHTBOX_TOKEN = re.compile(
    r"("
    r"\blightbox\b"
    r"|photoLightbox"
    r"|photo-lightbox"
    r"|data-photo-lightbox"
    r"|data-lightbox"
    r"|imageLightbox"
    r"|image-lightbox"
    r"|casLightbox"
    r"|cas-lightbox"
    r"|openLightbox"
    r"|closeLightbox"
    r"|lightboxOpen"
    r"|lightboxSrc"
    r"|lightboxIndex"
    r"|viewerOpen"
    r"|photoViewer"
    r"|photo-viewer"
    r"|data-photo-viewer"
    r"|fullsizeOpen"
    r"|fullSizeOpen"
    r"|fullscreenPhoto"
    r"|mediaLightbox"
    r")",
    re.I,
)
_LIGHTBOX_OPEN_CLICK = re.compile(
    r"("
    r"(?:on:click|onclick)(?:\|\w+)*\s*=\s*\{[^}]{0,240}"
    r"(?:openLightbox|openPhoto|openImage|showLightbox|showPhoto|showImage|"
    r"lightboxOpen|setLightbox|openViewer|openCas|viewPhoto|viewImage|"
    r"lightbox|photoViewer)"
    r"|(?:openLightbox|openPhoto|openImage|showLightbox|showPhoto|showImage|"
    r"setLightbox|openViewer|viewPhoto|viewImage)\s*\("
    r")",
    re.I | re.S,
)
_LIGHTBOX_IMG_CLICK = re.compile(
    r"<img\b[^>]{0,400}(?:on:click|onclick)(?:\|\w+)*\s*=\s*\{",
    re.I | re.S,
)
_LIGHTBOX_BUTTON_AROUND_IMG = re.compile(
    r"<button\b[^>]{0,300}(?:on:click|onclick)(?:\|\w+)*\s*=\s*\{[^}]{0,200}"
    r"(?:lightbox|openPhoto|openImage|openLightbox|showLightbox|photoViewer|"
    r"viewPhoto|viewImage)"
    r"[^}]{0,80}\}[^>]{0,200}>[\s\S]{0,400}<img\b",
    re.I,
)
_LIGHTBOX_OVERLAY = re.compile(
    r"("
    r"data-photo-lightbox"
    r"|data-lightbox"
    r"|data-photo-viewer"
    r"|role\s*=\s*[\"']dialog[\"'][^>]{0,200}"
    r"(?:lightbox|photo|image|viewer|cas)"
    r"|(?:lightbox|photo-lightbox|photo-viewer|image-lightbox|cas-lightbox)"
    r"[^;{]{0,120}(?:fixed|inset-0|z-\[?5)"
    r"|(?:fixed\s+inset-0|fixed inset-0|inset-0\s+fixed)[^;{]{0,200}"
    r"(?:lightbox|photo-viewer|photoLightbox|data-photo)"
    r"|class=[\"'][^\"']*\b(?:lightbox|photo-lightbox|photo-viewer)\b"
    r"|Dialog\.(?:Root|Content)\b[\s\S]{0,400}"
    r"(?:lightbox|photoLightbox|photo-viewer|casDataUrl|data:)"
    r")",
    re.I | re.S,
)
_LIGHTBOX_FULL_IMG = re.compile(
    r"("
    r"<img\b[^>]{0,500}"
    r"(?:lightbox|photoLightbox|lightboxSrc|viewerSrc|fullSrc|fullsize|"
    r"fullSize|data-photo-lightbox|data-lightbox)"
    r"|(?:lightbox|photoLightbox|lightboxSrc|viewerSrc|fullSrc|"
    r"lightboxUrl|viewerUrl)"
    r"[^;]{0,120}"
    r"(?:casDataUrl|srcs\[|data:|src\s*=)"
    r"|(?:src\s*=\s*\{[^}]{0,120}"
    r"(?:lightbox|photoLightbox|lightboxSrc|viewerSrc|fullSrc|srcs\[)"
    r")"
    r")",
    re.I | re.S,
)
_LIGHTBOX_LOCAL_SRC = re.compile(
    r"("
    r"casDataUrl"
    r"|srcs\s*\[|"
    r"data:"
    r"|lightboxSrc"
    r"|viewerSrc"
    r"|fullSrc"
    r")",
    re.I,
)
_LIGHTBOX_REMOTE_SRC = re.compile(
    r"("
    r"src\s*=\s*[\"']https?://"
    r"|src\s*=\s*\{[^}]{0,160}https?://"
    r"|lightboxSrc\s*=\s*[\"']https?://"
    r"|viewerSrc\s*=\s*[\"']https?://"
    r")",
    re.I,
)
_LIGHTBOX_ESC = re.compile(
    r"("
    r"(?:key|code)\s*===?\s*[\"']Escape[\"']"
    r"|[\"']Escape[\"']\s*===?\s*(?:e\.)?(?:key|code)"
    r"|e\.key\s*===?\s*[\"']Esc[\"']"
    r"|keydown[^;]{0,200}Escape"
    r"|on(?:keydown|keyup)(?:\|\w+)*\s*=\s*\{[^}]{0,200}Escape"
    r")",
    re.I | re.S,
)
_LIGHTBOX_CLOSE = re.compile(
    r"("
    r"closeLightbox"
    r"|closePhoto"
    r"|closeViewer"
    r"|lightboxOpen\s*=\s*(?:false|null|undefined|0)"
    r"|setLightbox(?:Open)?\s*\(\s*(?:false|null|undefined)"
    r"|open\s*=\s*false"
    r"|lightbox\s*=\s*null"
    r"|data-lightbox-close"
    r"|aria-label\s*=\s*[\"'][^\"']*[Cc]lose[^\"']*[\"']"
    r")",
    re.I,
)
_LIGHTBOX_BACKDROP = re.compile(
    r"("
    r"backdrop"
    r"|overlay"
    r"|fixed\s+inset-0"
    r"|inset-0[^;{]{0,80}bg-black"
    r"|bg-black/50"
    r"|bg-black\/\d+"
    r"|on(?:click)(?:\|\w+)*\s*=\s*\{[^}]{0,160}"
    r"(?:closeLightbox|closePhoto|closeViewer|lightboxOpen\s*=\s*false|"
    r"setLightbox|onOpenChange)"
    r")",
    re.I | re.S,
)
_LIGHTBOX_PREV_NEXT = re.compile(
    r"("
    r"\b(?:prev|next)(?:Photo|Image|Lightbox|Attach|Attachment)?\b"
    r"|lightboxIndex\s*[+\-]="
    r"|lightboxIndex\s*\+\s*1"
    r"|lightboxIndex\s*-\s*1"
    r"|ArrowLeft|ArrowRight"
    r"|data-lightbox-(?:prev|next)"
    r"|goTo(?:Prev|Next)"
    r"|show(?:Prev|Next)"
    r")",
    re.I,
)
_SYSTEM_PREVIEW = re.compile(
    r"("
    r"Preview\.app"
    r"|open\s+.*Preview"
    r"|NSWorkspace"
    r"|shell\.open"
    r"|plugin-shell"
    r"|@tauri-apps/plugin-shell"
    r"|revealItemInDir"
    r"|openPath\s*\([^)]*(?:\.jpe?g|\.png|\.gif|\.webp|\.heic|cas_hash|casHash)"
    r"|open\s*\(\s*[\"']file:"
    r")",
    re.I | re.S,
)
_LIGHTBOX_VIDEO_CHROME = re.compile(
    r"("
    r"<video\b[^>]{0,200}(?:lightbox|photo-lightbox|photo-viewer)"
    r"|(?:lightbox|photoLightbox|photo-viewer)[\s\S]{0,300}<video\b"
    r"|lightbox[\s\S]{0,200}\.play\s*\("
    r")",
    re.I | re.S,
)
_HEIC_TRANSCODE = re.compile(
    r"("
    r"heic2any"
    r"|heif-convert"
    r"|libheif"
    r"|transcodeHeic"
    r"|heicToJpeg"
    r"|heicToPng"
    r"|convertHeic"
    r"|decodeHeic"
    r"|heic-decode"
    r")",
    re.I,
)


def _lightbox_name_hit(name: str) -> bool:
    n = name.lower()
    return any(
        tok in n
        for tok in (
            "lightbox",
            "photoviewer",
            "photo-viewer",
            "imageviewer",
            "image-viewer",
            "casviewer",
            "cas-viewer",
        )
    )


def _cas_attach_and_lightbox_sources(crate: Path) -> tuple[str, str, str]:
    """Return (cas_attach, lightbox-ish components only, full web logic).

    Lightbox surface is deliberately narrow: CasAttach + files named/content-
    matched as photo lightbox. Full app logic is only used for HEIC/transcode
    bans and CasAttach wiring checks — not Esc/backdrop (those would false-
    pass on merge Dialog / people-filter Escape).
    """
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    cas = cas_path.read_text() if cas_path.is_file() else ""
    logic = _web_logic(crate)
    extra: list[str] = []
    web = crate / "web"
    for p in sorted(web.rglob("*.svelte")):
        if "node_modules" in p.parts:
            continue
        if p.name == "CasAttach.svelte":
            continue
        text = p.read_text()
        if _lightbox_name_hit(p.name) or _LIGHTBOX_TOKEN.search(text):
            extra.append(text)
    # Also pull .ts helpers that only exist for the lightbox.
    for p in sorted(web.rglob("*.ts")):
        if "node_modules" in p.parts:
            continue
        if _lightbox_name_hit(p.name):
            extra.append(p.read_text())
            continue
        text = p.read_text()
        if _LIGHTBOX_TOKEN.search(text) and re.search(
            r"casDataUrl|lightbox|photoViewer|photoLightbox", text, re.I
        ):
            extra.append(text)
    return cas, "\n".join(extra), logic


def _lightbox_esc_near_close(src: str) -> bool:
    """Escape handler that actually closes the lightbox (not people-filter blur)."""
    if not _LIGHTBOX_ESC.search(src):
        return False
    # Require close-ish action within a window of Escape, or lightbox state.
    for m in _LIGHTBOX_ESC.finditer(src):
        window = src[max(0, m.start() - 240) : m.end() + 240]
        if _LIGHTBOX_CLOSE.search(window) or _LIGHTBOX_TOKEN.search(window):
            return True
        if re.search(
            r"lightboxOpen\s*=\s*false|closeLightbox|setLightbox|viewerOpen\s*=\s*false",
            window,
            re.I,
        ):
            return True
    return False


def assert_photo_lightbox(crate: Path) -> None:
    """#118: click CAS thumbnail → in-window full-size overlay (local data only).

    Acceptance: dogfood JPEG opens large from casDataUrl / data:; still no
    http(s) in the viewer. Esc and/or backdrop closes. Optional left/right among
    attachments on the same message. HEIC stays placeholder unless already
    decoded — no HEIC transcode. Not: system Preview, video player chrome.
    Timeline and/or search CAS images (CasAttach is shared) must open the viewer;
    decorative non-CAS imgs alone are not enough.
    """
    cas, lightbox_extra, logic = _cas_attach_and_lightbox_sources(crate)
    if not cas:
        fail("#118: CasAttach.svelte required (CAS thumbnails already use casDataUrl)")
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    app = (crate / "web" / "App.svelte").read_text()
    search = ""
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if search_path.is_file():
        search = search_path.read_text()
    # Surfaces for the photo viewer only (not merge Dialog / whole App).
    surface = cas + "\n" + lightbox_extra
    cleaned = _without_comments(surface)
    cleaned_cas = _without_comments(cas)

    # 0) Baseline: still load via local casDataUrl, never remote in CasAttach.
    if "casDataUrl" not in cas:
        fail(
            "#118: CAS thumbnails must load via casDataUrl (local data: URL) — "
            "lightbox reuses the same bytes, not a remote host"
        )
    if re.search(r"[\"']https?://", cleaned_cas) or re.search(
        r"src\s*=\s*[\"']https?://", cas, re.I
    ):
        fail("#118: CasAttach must not use remote http(s) URLs for attachments")

    # 1) Open path: click on a CAS image thumbnail (not only decorative img).
    has_img = bool(re.search(r"<img\b", cas, re.I))
    if not has_img:
        fail(
            "#118: CasAttach must render a CAS <img> thumbnail that can open "
            "the lightbox (JPEG/PNG/… already decoded via casDataUrl)"
        )
    open_click = bool(_LIGHTBOX_OPEN_CLICK.search(surface)) or bool(
        _LIGHTBOX_OPEN_CLICK.search(cleaned)
    )
    img_click = bool(_LIGHTBOX_IMG_CLICK.search(surface))
    btn_img = bool(_LIGHTBOX_BUTTON_AROUND_IMG.search(surface))
    # cursor-pointer + click handler on the CAS image surface.
    pointer_click = bool(
        re.search(
            r"(?:cursor-pointer|role\s*=\s*[\"']button[\"'])[\s\S]{0,200}<img\b"
            r"|<img\b[\s\S]{0,200}(?:cursor-pointer|role\s*=\s*[\"']button[\"'])",
            surface,
            re.I,
        )
    ) and bool(
        re.search(
            r"(?:on:click|onclick)(?:\|\w+)*\s*=\s*\{",
            surface,
            re.I,
        )
    )
    if not (open_click or img_click or btn_img or pointer_click):
        fail(
            "#118: CAS photo thumbnail must be clickable to open an in-window "
            "lightbox (onclick / openLightbox / button wrapping <img>) — "
            "passive decorative <img> only is not enough"
        )

    # Timeline and/or search must surface CasAttach (shared component covers both).
    timeline_has_cas = "CasAttach" in app or bool(
        re.search(r"casDataUrl|CasAttach", _timeline_block(crate) + "\n" + app)
    )
    search_has_cas = "CasAttach" in search or bool(
        re.search(r"casDataUrl|CasAttach", search)
    )
    if not (timeline_has_cas or search_has_cas):
        fail(
            "#118: lightbox open path must be reachable from timeline and/or "
            "search CAS images (CasAttach on person timeline / SearchPane)"
        )
    if timeline_has_cas and search_path.is_file() and not search_has_cas:
        if re.search(r"attachments|cas_hash|casHash", search) and re.search(
            r"<img\b", search, re.I
        ):
            fail(
                "#118: SearchPane CAS images must share the lightbox open path "
                "(CasAttach or the same click → overlay handler)"
            )

    # 2) Overlay / lightbox / modal with a full-size image.
    has_token = bool(_LIGHTBOX_TOKEN.search(surface)) or bool(
        _LIGHTBOX_TOKEN.search(cleaned)
    )
    has_overlay = bool(_LIGHTBOX_OVERLAY.search(surface)) or bool(
        _LIGHTBOX_OVERLAY.search(cleaned)
    )
    dialog_lightbox = bool(
        re.search(
            r"Dialog\.(?:Root|Content)\b[\s\S]{0,500}"
            r"(?:lightbox|photoLightbox|photoViewer|viewerOpen|lightboxOpen)"
            r"|(?:lightbox|photoLightbox|photoViewer|viewerOpen|lightboxOpen)"
            r"[\s\S]{0,500}Dialog\.(?:Root|Content)\b",
            surface + "\n" + cleaned,
            re.I,
        )
    )
    if not (has_token and (has_overlay or dialog_lightbox)):
        if not has_overlay and not dialog_lightbox:
            fail(
                "#118: need an in-window photo overlay / lightbox / modal "
                "(fixed inset overlay, data-photo-lightbox, or Dialog bound to "
                "lightbox state) — not only the thumbnail"
            )
        fail(
            "#118: photo lightbox needs a named open state / surface "
            "(lightbox / photoLightbox / data-photo-lightbox / openLightbox)"
        )

    has_full_img = bool(_LIGHTBOX_FULL_IMG.search(surface)) or bool(
        _LIGHTBOX_FULL_IMG.search(cleaned)
    )
    if not has_full_img:
        overlay_img = bool(
            re.search(
                r"(?:lightbox|photoLightbox|photo-viewer|data-photo-lightbox|"
                r"data-lightbox|viewerOpen|lightboxOpen)"
                r"[\s\S]{0,800}<img\b",
                surface + "\n" + cleaned,
                re.I,
            )
        ) and bool(_LIGHTBOX_LOCAL_SRC.search(surface + "\n" + cleaned))
        if not overlay_img:
            fail(
                "#118: lightbox must show a full-size <img> from local "
                "casDataUrl / data: / srcs (same CAS bytes as the thumbnail)"
            )

    # 3) Viewer src stays local — no http(s) remote host.
    if _LIGHTBOX_REMOTE_SRC.search(surface) or _LIGHTBOX_REMOTE_SRC.search(cleaned):
        fail(
            "#118: photo lightbox viewer must not use http(s) src — "
            "only local casDataUrl / data: URLs"
        )
    if re.search(
        r"(?:fetch\s*\(\s*[\"']https?://|axios\.|new\s+Image\s*\([^)]*https?://)",
        cleaned,
        re.I,
    ):
        fail("#118: lightbox must not fetch remote image hosts")

    # 4) Close via Esc and/or backdrop click (scoped to lightbox surface).
    has_esc = _lightbox_esc_near_close(surface) or _lightbox_esc_near_close(cleaned)
    dialog_escape_ok = dialog_lightbox
    # Narrow close: named closeLightbox / lightboxOpen=false — not bare open=false
    # (merge Dialog uses open=false and would false-pass if we scanned App).
    has_close = bool(
        re.search(
            r"("
            r"closeLightbox"
            r"|closePhoto"
            r"|closeViewer"
            r"|lightboxOpen\s*=\s*(?:false|null|undefined|0)"
            r"|setLightbox(?:Open)?\s*\(\s*(?:false|null|undefined)"
            r"|viewerOpen\s*=\s*(?:false|null|undefined)"
            r"|photoLightbox\s*=\s*null"
            r"|data-lightbox-close"
            r")",
            surface + "\n" + cleaned,
            re.I,
        )
    )
    has_backdrop = bool(
        re.search(
            r"("
            r"(?:on:click|onclick)(?:\|\w+)*\s*=\s*\{[^}]{0,200}"
            r"(?:closeLightbox|closePhoto|closeViewer|lightboxOpen\s*=\s*false|"
            r"setLightbox|viewerOpen\s*=\s*false)"
            r"|(?:lightbox|photo-lightbox|data-photo-lightbox|data-lightbox)"
            r"[^;{]{0,200}(?:fixed\s+inset-0|inset-0|bg-black)"
            r"|(?:fixed\s+inset-0|inset-0)[^;{]{0,200}"
            r"(?:lightbox|photo-lightbox|data-photo-lightbox|closeLightbox)"
            r"|backdrop[^;]{0,80}(?:closeLightbox|lightboxOpen)"
            r")",
            surface + "\n" + cleaned,
            re.I | re.S,
        )
    )
    if not (has_esc or dialog_escape_ok):
        fail(
            "#118: lightbox must close on Escape "
            "(keydown Escape → closeLightbox / lightboxOpen=false, "
            "or Dialog.Root bound to lightbox state)"
        )
    if not (has_backdrop or has_close or dialog_lightbox):
        fail(
            "#118: lightbox must close via backdrop click and/or an explicit "
            "close control (closeLightbox / lightboxOpen = false)"
        )
    if not dialog_escape_ok and has_esc and not (has_backdrop or has_close):
        fail(
            "#118: custom lightbox overlay needs backdrop click or close control "
            "in addition to Escape"
        )

    # 5) Optional prev/next among same-message attachments — if present, must
    # stay on the message's attachment list (not a global gallery).
    if _LIGHTBOX_PREV_NEXT.search(surface) or _LIGHTBOX_PREV_NEXT.search(cleaned):
        same_message = bool(
            re.search(
                r"("
                r"items\s*\[|"
                r"attachments\s*\[|"
                r"messageAttachments|"
                r"sameMessage|"
                r"filter\s*\(\s*(?:a|att|item)\s*=>[\s\S]{0,120}isImage|"
                r"lightboxIndex|"
                r"attach(?:ment)?Index|"
                r"imageItems|"
                r"imageAttachments"
                r")",
                surface + "\n" + cleaned,
                re.I,
            )
        )
        if not same_message:
            fail(
                "#118: lightbox prev/next must walk attachments on the same "
                "message (items / attachments / lightboxIndex), not a global "
                "gallery across the archive"
            )

    # 6) HEIC: not required to open; no HEIC transcode code (whole UI).
    if _HEIC_TRANSCODE.search(blob) or _HEIC_TRANSCODE.search(logic):
        fail(
            "#118: do not add HEIC transcode (heic2any / libheif / heicToJpeg) — "
            "HEIC stays placeholder unless already decoded"
        )
    # Explicitly do not require heic in the open path (no fail if absent).

    # 7) No system Preview / external open for the photo viewer.
    if _SYSTEM_PREVIEW.search(surface) or _SYSTEM_PREVIEW.search(cleaned):
        fail(
            "#118: photo lightbox must stay in-window — no system Preview, "
            "shell.open, or revealItemInDir for CAS images"
        )
    if re.search(
        r"(?:openPath|open\s*\()\s*[\s\S]{0,120}"
        r"(?:cas_hash|casHash|filename|\.jpe?g|\.png|\.heic|lightbox)",
        surface,
        re.I,
    ):
        fail(
            "#118: do not shell-open attachment paths from the lightbox "
            "(in-window overlay only; not macOS Preview)"
        )

    # 8) No video player chrome in the photo lightbox (voice-note is #119).
    if _LIGHTBOX_VIDEO_CHROME.search(surface) or _LIGHTBOX_VIDEO_CHROME.search(cleaned):
        fail(
            "#118: photo lightbox must not embed a <video> player "
            "(images only; voice-note chrome is a separate issue)"
        )


# #119 — voice-note / audio CAS player (local only; play/pause + time).
_VOICE_KIND = re.compile(
    r"("
    r"kind\s*===\s*[\"']voice[\"']"
    r"|kind\s*==\s*[\"']voice[\"']"
    r"|startsWith\s*\(\s*[\"']audio/"
    r"|audio/\*"
    r"|\.opus|\.ogg|\.mp3|\.m4a|\.aac|\.wav"
    r"|isAudio\s*\("
    r"|isVoice\s*\("
    r")",
    re.I,
)
_VOICE_AUDIO_EL = re.compile(r"<audio\b", re.I)
_VOICE_NATIVE_CONTROLS = re.compile(
    r"<audio\b[^>]*\bcontrols\b|\bcontrols\b[^>]*<audio\b",
    re.I | re.S,
)
_VOICE_LOCAL_SRC = re.compile(
    r"("
    r"src\s*=\s*\{[^}]{0,120}(?:srcs|casDataUrl|data:)"
    r"|src\s*=\s*\{[^}]{0,80}(?:url|src|audioSrc|voiceSrc)"
    r"|src\s*=\s*[\"']data:"
    r")",
    re.I,
)
_VOICE_REMOTE_SRC = re.compile(
    r"("
    r"src\s*=\s*[\"']https?://"
    r"|src\s*=\s*\{[^}]{0,160}https?://"
    r"|new\s+Audio\s*\(\s*[\"']https?://"
    r"|audio(?:Src|Url|URL)?\s*=\s*[\"']https?://"
    r")",
    re.I,
)
_VOICE_PLAY_PAUSE = re.compile(
    r"("
    r"\.play\s*\(|\.pause\s*\("
    r"|togglePlay|playPause|isPlaying|playing\s*="
    r"|aria-label\s*=\s*[\"'][^\"']*(?:[Pp]lay|[Pp]ause)[^\"']*[\"']"
    r"|data-voice-(?:play|pause)"
    r")",
    re.I,
)
_VOICE_TIME_CHROME = re.compile(
    r"("
    r"currentTime|\.duration\b"
    r"|formatTime|formatDuration|audioTime|elapsed"
    r"|data-voice-(?:time|duration|elapsed)"
    r"|aria-valuenow"
    r"|timeupdate"
    r")",
    re.I,
)
_VOICE_OMITTED = re.compile(
    r"("
    r"\.omitted\b"
    r"|a\.omitted"
    r"|omitted\s*\?"
    r"|Media omitted"
    r"|omitted in this export"
    r")",
    re.I,
)
_VOICE_MISSING = re.compile(
    r"("
    r"\.missing\b"
    r"|a\.missing"
    r"|not stored"
    r"|Photo/file not stored"
    r"|file not stored"
    r")",
    re.I,
)
_VOICE_WAVEFORM_CDN = re.compile(
    r"("
    r"wavesurfer"
    r"|waveform\.js"
    r"|cdn\.jsdelivr.*wave"
    r"|unpkg\.com.*wave"
    r"|https?://[^\"'\s)]+(?:waveform|wavesurfer)"
    r"|url\s*\(\s*[\"']https?://[^\"']*wave"
    r"|src\s*=\s*[\"']https?://[^\"']*(?:waveform|wave\.png|spectrogram)"
    r")",
    re.I,
)
_VOICE_TRANSCRIPTION = re.compile(
    r"("
    r"\btranscri(?:be|ption|pt)\b"
    r"|speech[-_]?to[-_]?text"
    r"|whisper\.|openai\.audio"
    r"|data-voice-transcript"
    r"|showTranscript|voiceTranscript"
    r")",
    re.I,
)


def assert_voice_note_player(crate: Path) -> None:
    """#119: voice/audio CAS attachments play in-app (local only).

    Acceptance: opus/mp3 (and other audio/* / kind===voice) play via an in-app
    player with play/pause and time/duration chrome. Native <audio controls> is
    enough; custom chrome must expose both. Source is casDataUrl / data: (same
    path as other CAS) — no remote streaming URL. Omitted/missing stay
    placeholders (no fake player). Not: waveform-from-CDN, transcription.
    """
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail("#119: CasAttach.svelte required for voice/audio CAS attachments")
    cas = cas_path.read_text()
    cleaned = _without_comments(cas)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    logic = _web_logic(crate)
    surface = cas + "\n" + logic

    # 0) Local CAS path only — same casDataUrl / data: as photos.
    if "casDataUrl" not in cas:
        fail(
            "#119: voice notes must load via casDataUrl (local data: URL), "
            "not a remote stream"
        )
    if re.search(r"[\"']https?://", cleaned) or re.search(
        r"src\s*=\s*[\"']https?://", cas, re.I
    ):
        fail("#119: CasAttach must not use remote http(s) URLs for voice/audio")
    if _VOICE_REMOTE_SRC.search(cas) or _VOICE_REMOTE_SRC.search(cleaned):
        fail(
            "#119: audio player must not use http(s) src — only local "
            "casDataUrl / data: (no streaming CDN)"
        )

    # 1) Classify voice/audio (kind, mime, or extension).
    if not _VOICE_KIND.search(cas):
        fail(
            "#119: CasAttach must detect voice/audio attachments "
            "(kind === \"voice\", audio/* mime, or .opus/.ogg/.mp3/.m4a/.aac/.wav)"
        )

    # 2) In-app player: native <audio controls> OR custom play/pause + time.
    has_audio = bool(_VOICE_AUDIO_EL.search(cas))
    if not has_audio:
        fail(
            "#119: voice/audio CAS attachments need an in-app <audio> player "
            "(play opus/mp3 in-window; not shell-open only)"
        )
    native = bool(_VOICE_NATIVE_CONTROLS.search(cas))
    custom_play = bool(_VOICE_PLAY_PAUSE.search(cas) or _VOICE_PLAY_PAUSE.search(cleaned))
    custom_time = bool(_VOICE_TIME_CHROME.search(cas) or _VOICE_TIME_CHROME.search(cleaned))
    if not (native or (custom_play and custom_time)):
        fail(
            "#119: audio player needs play/pause and time/duration chrome "
            "(native <audio controls>, or custom play/pause + currentTime/duration)"
        )
    if not _VOICE_LOCAL_SRC.search(cas):
        fail(
            "#119: <audio> src must be local casDataUrl / data: / srcs "
            "(same CAS bytes path as images)"
        )

    # 3) Omitted / missing stay placeholders — no player on those branches.
    if not _VOICE_OMITTED.search(cas):
        fail(
            "#119: omitted attachments must stay placeholders "
            "(branch on .omitted — no fake voice player)"
        )
    if not _VOICE_MISSING.search(cas):
        fail(
            "#119: missing attachments must stay placeholders "
            "(branch on .missing / not stored — no fake voice player)"
        )
    # Audio must not render on the omitted path: require loadable guards
    # (srcs / !broken / !omitted) near <audio>, not a bare always-on player.
    audio_m = _VOICE_AUDIO_EL.search(cas)
    if audio_m:
        window = cas[max(0, audio_m.start() - 400) : audio_m.end() + 200]
        guarded = bool(
            re.search(
                r"("
                r"srcs\s*\[|srcs\s*\.|!broken|broken\s*\[|"
                r"!a\.omitted|!omitted|!a\.missing|!missing|"
                r"hashOf\s*\(|cas_hash|casHash"
                r")",
                window,
                re.I,
            )
        )
        if not guarded:
            fail(
                "#119: <audio> must only render for loadable voice/audio "
                "(srcs / hash present, not omitted/missing) — placeholders otherwise"
            )
        # If audio sits inside the omitted branch, reject.
        before = cas[: audio_m.start()]
        # Last relevant branch marker before <audio>.
        last_omitted = max(before.rfind("omitted"), before.rfind("Media omitted"))
        last_missing = max(
            before.rfind(".missing"),
            before.rfind("not stored"),
            before.rfind("a.missing"),
        )
        last_audio_guard = max(
            before.rfind("isAudio"),
            before.rfind("isVoice"),
            before.rfind("audio/"),
            before.rfind("kind === \"voice\""),
            before.rfind("kind === 'voice'"),
        )
        if last_omitted > last_audio_guard and last_omitted > 0:
            # Only fail if no {:else if isAudio} sits after omitted closer to audio.
            if last_audio_guard < last_omitted:
                fail(
                    "#119: do not put the voice player on the omitted branch — "
                    "omitted stays a placeholder"
                )
        if last_missing > last_audio_guard and last_missing > 0:
            if last_audio_guard < last_missing:
                fail(
                    "#119: do not put the voice player on the missing branch — "
                    "missing stays a placeholder"
                )

    # 4) Reachable from timeline and/or search (shared CasAttach).
    app = (crate / "web" / "App.svelte").read_text()
    search = ""
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if search_path.is_file():
        search = search_path.read_text()
    timeline_has_cas = "CasAttach" in app or bool(
        re.search(r"casDataUrl|CasAttach", _timeline_block(crate) + "\n" + app)
    )
    search_has_cas = "CasAttach" in search
    if not (timeline_has_cas or search_has_cas):
        fail(
            "#119: voice player must be reachable from timeline and/or search "
            "CAS attachments (CasAttach)"
        )

    # 5) Not in scope: waveform-from-CDN, transcription UI.
    if _VOICE_WAVEFORM_CDN.search(surface) or _VOICE_WAVEFORM_CDN.search(blob):
        fail(
            "#119: not in scope — no waveform visualization from a CDN "
            "(wavesurfer / remote wave assets)"
        )
    if _VOICE_TRANSCRIPTION.search(cleaned) or _VOICE_TRANSCRIPTION.search(
        _without_comments(blob)
    ):
        fail(
            "#119: not in scope — no transcription UI "
            "(transcribe / speech-to-text / transcript pane)"
        )


def main() -> None:
    root = repo_root()
    crate = root / "crates" / "interlace-tauri"
    toml = (crate / "Cargo.toml").read_text()
    if "publish = false" not in toml:
        fail("interlace-tauri must set publish = false")
    for plug in ("tauri-plugin-http", "tauri-plugin-updater"):
        if plug in toml:
            fail(f"{plug} must not be a dependency")

    ws = (root / "Cargo.toml").read_text()
    if '"crates/interlace-tauri"' not in ws:
        fail("interlace-tauri must be a workspace member")
    dm = ws[ws.find("default-members") : ws.find("[workspace.package]")]
    if "interlace-tauri" in dm:
        fail("interlace-tauri must not be a default-member")

    conf = (crate / "tauri.conf.json").read_text()
    if CSP not in conf:
        fail(f"tauri.conf.json missing exact CSP:\n{CSP}")
    import json

    cfg = json.loads(conf)
    bundle = cfg.get("bundle") or {}
    if bundle.get("active") is not True:
        fail("bundle.active must be true (UI8 unsigned .app/.dmg)")
    targets = bundle.get("targets") or []
    if "app" not in targets or "dmg" not in targets:
        fail("bundle.targets must include app and dmg")
    if bundle.get("createUpdaterArtifacts"):
        fail("createUpdaterArtifacts must stay false (no updater)")
    mac = bundle.get("macOS") or {}
    if mac.get("entitlements") != "Interlace.entitlements":
        fail("bundle.macOS.entitlements must be Interlace.entitlements")
    if mac.get("signingIdentity") != "-":
        fail('signingIdentity must be "-" (ad-hoc / unsigned)')
    icons = bundle.get("icon") or []
    if "icons/icon.icns" not in icons:
        fail("bundle.icon must include icons/icon.icns")
    if not (crate / "icons" / "icon.icns").is_file():
        fail("icons/icon.icns missing")

    ent = (crate / "Interlace.entitlements").read_text()
    if "com.apple.security.app-sandbox" not in ent:
        fail("sandbox entitlement required")
    if "network.server" in ent:
        fail("entitlements must omit network.server")
    # WKWebView will not paint tauri://localhost in a sandbox without this.
    # Measured 2026-08-10: sandbox-only and sandbox+JIT = blank .app;
    # sandbox+network.client shows the UI. Still no HTTP client crate.
    if "network.client" not in ent:
        fail("entitlements must include network.client (WKWebView local UI)")
    if "allow-jit" not in ent:
        fail("entitlements must include cs.allow-jit for WKWebView")

    app = (crate / "web" / "App.svelte").read_text()
    if "phones home" not in app or "HTTP" not in app:
        fail("Svelte UI must state no phone-home and no HTTP client")
    if "confirm(" in app:
        fail("App.svelte must not use window.confirm after UI primitives")
    for rel in (
        "web/lib/components/ui/button/button.svelte",
        "web/lib/components/ui/input/input.svelte",
        "web/lib/components/ui/dialog/dialog.svelte",
        "web/lib/components/ui/scroll-area/scroll-area.svelte",
    ):
        if not (crate / rel).is_file():
            fail(f"missing owned primitive {rel}")
    empty = crate / "web" / "lib" / "EmptyState.svelte"
    if not empty.is_file():
        fail("EmptyState.svelte required for UI empty/loading copy")
    if "Opening last archive" not in app:
        fail("boot screen must say Opening last archive (no blank flash)")
    doctor = crate / "web" / "lib" / "DoctorPane.svelte"
    if not doctor.is_file():
        fail("DoctorPane.svelte required for UI7")
    dtxt = doctor.read_text()
    if "Not encrypted at rest" not in dtxt or "FileVault" not in dtxt:
        fail("Doctor pane must say not encrypted at rest; FileVault is encryption")
    if "database is encrypted" in dtxt or "your data is encrypted" in dtxt.lower():
        fail("UI must not claim the DB is encrypted at rest")
    if "doctorRun" not in dtxt:
        fail("Doctor pane must call doctorRun (not only CLI copy)")
    if "data-cloud-warning" not in app:
        fail("App.svelte must show a persistent cloud-path banner")
    if "UI7 will run doctor" in app:
        fail("placeholder UI7 CLI-only copy must be gone")
    assert_chat_bubbles(crate)
    assert_day_separators(crate)
    assert_timeline_latest(crate)
    assert_conversation_switcher(crate)
    assert_timeline_platform_chips(crate)
    assert_timeline_kind_filter(crate)
    assert_gmail_timeline_rows(crate)
    assert_people_sidebar_no_x_scroll(crate)
    assert_people_filter_identity(crate)
    assert_boot_spinner(crate)
    assert_photo_lightbox(crate)
    assert_voice_note_player(crate)
    cas = (crate / "web" / "lib" / "CasAttach.svelte").read_text()
    if "casDataUrl" not in cas:
        fail("CAS viewer must load bytes via casDataUrl (data: URL; Vite cannot fetch cas://)")
    if "http://" in cas or "https://" in cas:
        fail("CAS viewer must not use remote URLs")
    if "protocol-asset" in toml or "dangerousRemoteDomainIpcAccess" in conf:
        fail("must not enable remote asset IPC")
    if (crate / "ui" / "app.js").is_file():
        fail("vanilla ui/app.js must be gone after UI-FE")
    if not (crate / "package-lock.json").is_file():
        fail("package-lock.json must be committed")
    pkg = (crate / "package.json").read_text()
    if "bits-ui" not in pkg:
        fail("bits-ui must be a local dependency (no CDN theme)")
    vite = (crate / "vite.config.ts").read_text()
    if 'base: "./"' not in vite and "base: './'" not in vite:
        fail("vite.config.ts must set base: './' so the .app loads JS")
    if "tauri:build" not in pkg:
        fail("package.json must expose tauri:build")

    wf = root / ".github" / "workflows" / "app-release.yml"
    if not wf.is_file():
        fail("app-release.yml missing (UI8 app-v* tags)")
    wtxt = wf.read_text()
    if "app-v*" not in wtxt:
        fail("app-release.yml must trigger on app-v* tags only")
    if "cargo publish" in wtxt or "CARGO_REGISTRY_TOKEN" in wtxt:
        fail("app-release.yml must not publish crates (D3)")
    if "tauri-plugin-updater" in wtxt or "plugin-updater" in wtxt:
        fail("app-release.yml must not install an updater")
    pub = (root / ".github" / "workflows" / "publish.yml").read_text()
    if "tauri:build" in pub or "bundle/dmg" in pub or "Interlace.app" in pub:
        fail("publish.yml is crates.io v* only; do not attach the .dmg there")

    npm = run(
        ["npm", "ci"],
        cwd=crate,
        check=False,
    )
    if npm.returncode != 0:
        fail(npm.stderr or npm.stdout)
    built = run(["npm", "run", "build"], cwd=crate, check=False)
    if built.returncode != 0:
        fail(built.stderr or built.stdout)
    dist = (crate / "dist" / "index.html").read_text()
    if "cdn." in dist or "unpkg.com" in dist:
        fail("production bundle must not load a CDN")
    if 'src="/assets/' in dist or "href=\"/assets/" in dist:
        fail("dist/index.html must use relative asset URLs (vite base ./); absolute /assets blanks the .app")
    if "connect-src 'none'" in conf:
        fail("connect-src 'none' blocks Tauri IPC and blanks the bundled .app")

    chk = run(["cargo", "check", "-p", "interlace-tauri"], cwd=root, check=False)
    if chk.returncode != 0:
        fail(chk.stderr or chk.stdout)

    clip = run(
        ["cargo", "clippy", "-p", "interlace-tauri", "--", "-D", "warnings"],
        cwd=root,
        check=False,
    )
    if clip.returncode != 0:
        fail(clip.stderr or clip.stdout)

    for kind in ("bans", "licenses"):
        d = run(
            [
                "cargo",
                "deny",
                "--manifest-path",
                str(crate / "Cargo.toml"),
                "check",
                kind,
            ],
            cwd=root,
            check=False,
        )
        if d.returncode != 0:
            fail(f"cargo deny check {kind} interlace-tauri failed\n{d.stdout}\n{d.stderr}")

    for name in ("reqwest", "hyper"):
        t = run(
            [
                "cargo",
                "tree",
                "-p",
                "interlace-tauri",
                "-i",
                name,
                "--target",
                "aarch64-apple-darwin",
            ],
            cwd=root,
            check=False,
        )
        out = (t.stdout or "") + (t.stderr or "")
        if "warning: nothing to print" not in out and f"{name} v" in out:
            fail(f"{name} is in the macOS tauri graph\n{out}")

    print("gate_tauri ok")


if __name__ == "__main__":
    main()
