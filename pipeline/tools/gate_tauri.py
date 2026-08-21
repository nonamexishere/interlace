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
#170: voice-note seek bar — click/drag progress track (range / progress / seek)
#     writes currentTime on the local <audio>; same casDataUrl / data: source
#     (no http(s) stream); keep play/pause + elapsed/duration (#119);
#     omitted/missing stay placeholders (no seek bar). Not: CDN waveform,
#     transcription, video scrubber. Docs: docs/user/app.md — scrub a local
#     voice note; still no remote stream.
#120: virtualize person timeline — only visible + overscan rows in the DOM for
#     large lists (10k fixture stays scrollable). Keep j/k and Load older (#113).
#     Bodies still text nodes (no {@html}/innerHTML of message body).
#     Not: 10M in one view, lazy-decode every photo.
#121: SearchPane platform is a closed <select> (Any | whatsapp | gmail), not a
#     free-text Input — invalid tokens cannot be typed. Empty value = any
#     (null/empty to api.search from select state). Only core tokens Tauri
#     parse_platform accepts (contacts OK; no owner option unless IPC accepts it;
#     no invented twitter/slack/…). Not: new platforms, regex.
#122: SearchPane conversation kind is a closed <select> (Any | dm | group |
#     email_thread), not free text. Empty value = any. Wire conversationKind /
#     conversation_kind into api.search. Groups still respect include-groups.
#     Not: Gmail label filter, invented kinds beyond dm/group/email_thread.
#123: SearchPane person is a name-facing combobox / filtered list (same people
#     source as the sidebar), not free-text “Person id” + datalist of numeric
#     ids. Selecting stores person_id for api.search({ personId }). Keyboard:
#     type to filter display names, Enter to pick (first match or highlighted).
#     Clear = no person filter. Not: multi-person OR, fuzzy beyond list filter.
#124: search hit with person_id jumps to that message on the person timeline —
#     switch to People, select person, load a window around message_id, scroll
#     into view, highlight once (tlIndex ring). No person_id → stay on Search
#     and expand body (toggle / searchBody) as today. Not: FTS rewrite.
#     Miss after bounded load: surface showErr (or equivalent); never set tlIndex
#     to last-loaded (idx >= 0 ? idx : length-1) as a successful hit ring.
#125: SearchPane attachment presence is a closed <select> (Any | has_file |
#     omitted | missing), not free text. Empty value = any. Wire
#     attachmentFilter / attachment_filter into api.search. Not: MIME taxonomy.
#126: Search snippets highlight match tokens via <mark> siblings (split on core
#     FTS «…» markers or matched query terms), never innerHTML / {@html} of the
#     full snippet or expanded body. Yellow mark styling. A body containing
#     <script> stays text. Not: regex HTML inject, HTML mail renderer.
#128: ReviewPane shows each side’s identifiers (kind + value_normalized, not only
#     display_name / platforms) so a name_similarity card is decidable without
#     CLI `review show`. Samples stay text nodes (no {@html on sample body).
#     Keep score + evidence list + Accept/Reject. Not: dump extra body lines,
#     raise/lower name_score UI.
#129: native window title via Tauri setTitle — Interlace | Ada — Interlace |
#     Search — Interlace (and Review/Import/Doctor — Interlace). React to view +
#     selected person name. No message body/snippet in the title. Not dock badges.
#130: native macOS menu — Interlace (About + Quit), File (open archive + import),
#     View (people/search/review/doctor). About: offline, not encrypted at rest,
#     FileVault. Open uses pick_folder / openPicker. No Check for Updates,
#     no updater, no Preferences window, no iCloud menu.
#131: UI chrome locale packs (en + tr) under web/ — not WA fixture toml.
#     Resolve from OS locale (navigator.language / Intl / Tauri); tr* → tr, else en.
#     tr pack has “Arşiv aç” / “Doktor”; App setup/nav uses the chrome helper
#     (not only hardcoded English). Never t(body_text)/snippet. English remains
#     the default so existing doctor / empty / backup English gates still pass.
#132: keyboard map — ⌘F/ctrl+F from every view (including People) switches to
#     Search and focuses `#q`; `/` still focuses `#person-filter` on People;
#     Esc blurs inputs and from other views sets view=people; ⌘/ctrl 1–5
#     People/Search/Review/Import/Doctor; keep timeline + search-hit j/k;
#     do not steal letters from inputs; no vim mode / keybindings.json.
#     Document in docs/user/app.md. (#208 changed the Find-on-People rule.)
#133: people list is listbox/option (or list + aria-activedescendant) with
#     aria-selected; timeline rows are article/label (not raw person id);
#     focus-visible rings on people options + timeline rows; honor
#     prefers-reduced-motion (no spin / sticky-date animation); keep SearchPane
#     listbox; no WCAG certificate claim; tab order is not a trap.
#134: drop a local ZIP/mbox on the window (any tab) → same path as the Import
#     picker: Tauri onDragDropEvent / DragDropEvent / file-drop (not HTML
#     ondrop of remote URLs, not fetch). Reject http(s) / URL-scheme drops
#     (error, do not import). First local path into existing importStart
#     (auto-detect) and switch view to Import so importProgress / Status
#     running→done still shows. No new folder-of-folders walker (UI5
#     folder-of-zips via existing import is OK). Docs: drop local ZIP/mbox,
#     no URLs.
#135: context menu on a person-timeline bubble — Copy text (clipboard);
#     attachment with cas_hash — Reveal in Finder; reveal command takes hash
#     only (cas/ab/cd/<hash> via cas_blob_path); file-only open (std::process
#     /usr/bin/open -R or file://), not http; copy does not log the body;
#     no plugin-shell / shell:allow-execute / arbitrary Command; no Share /
#     AirDrop; docs line in docs/user/app.md.
#136: defer doctor CAS scan so large archives open fast — Open / applyStatus
#     shows People without awaiting a full cas_get / attachments.cas_hash walk
#     before opening clears. Doctor badge may load async or stay empty until
#     the Doctor tab. Doctor tab (DoctorPane load / Refresh / doctorIssues)
#     still runs the full scan; a missing blob is still an issue. No
#     background GC on open (gc_cas / GC thread not started from
#     applyStatus/open). Docs: open is not blocked on hashing cas/; Doctor
#     tab still finds missing blobs.
#184: people-list last_activity_at is a short human time (e.g. 11 Aug 14:32 UTC)
#     for display and VoiceOver / aria-label (name + short time), not raw
#     2024-08-11T14:32:00Z. Keep ISO on archive / API JSON types. Do not
#     t() message bodies. Not a date-picker locale pack. Do not put
#     “yesterday” in App.svelte (#112 greps the file). Docs: docs/user/app.md
#     — people list / VoiceOver use a short time, not the raw ISO.
#198: product Svelte chrome uses existing design tokens (shadcn background /
#     foreground / muted-foreground / border / destructive + --bubble-me /
#     --bubble-them). No hex / amber-* / yellow-* / black/80 in
#     web/**/*.svelte (token defs may stay in app.css). Bubbles stay
#     distinct. No new brand palette, gradients, CDN theme, or stored-data
#     rewrite. Docs: chrome colors from tokens / CSS variables, not raw hues.
#199: typography — timeline + search bodies share one 14–15px size with
#     line-height 1.5–1.6; people-row + bubble-caption meta share one
#     12–13px muted-foreground size; headings stay restrained (no
#     text-3xl+); --font-sans stays system UI; no remote font load.
#     Do not t() bodies. Docs: 14–15px bodies, 12–13px meta, no remote font.
#200: Lucide icons only — voice play/pause, lightbox close, empty-state
#     use @lucide/svelte (16px default, 20px empty); no ▶/❚❚ glyphs,
#     no emoji-as-icon on those surfaces, no CDN icon kit / second
#     icon package. Nav icons optional (keep text labels). Docs: Lucide
#     chrome icons, not emoji glyphs.
#201: own Tooltip, Separator, Badge, Card under web/lib/components/ui/
#     (at least one .svelte + index.ts each). Platform chip
#     (data-platform-chip / platform-chip) is the Badge primitive.
#     At least one banner (data-cloud-warning) or dialog footer uses
#     Card or Separator. No second npm UI kit; bits-ui stays a local
#     dep (not CDN). No network avatars; Command is #215; Toast/sonner
#     is #204. Docs: owned Badge/Card (or owned shadcn primitives) for
#     chips/banners, not one-off chrome.
#202: EmptyState optional primary action via owned Button; every major
#     empty view has a next action — People (none / no filter match),
#     Search (no query / no hits), Review empty, Timeline no messages,
#     Import idle, Doctor healthy. Keep data-empty. No SVG mascot /
#     illustration / bg-gradient. Docs: empty views have a next action,
#     no mascot. Not: skeletons (#203), toasts (#204), t() of imported
#     bodies, command palette (#215), timeline stutter (#224).
#203: quiet muted skeleton (data-skeleton / owned Skeleton) while people
#     list, person timeline, and search hits load; keep #156 boot CSS
#     spinner + “Opening last archive”; search in-flight is not “No hits”;
#     prefers-reduced-motion → static bars; no CDN shimmer / skeleton
#     package / video splash / server %. Load older / append must not
#     mount those bars (append / tlAppending guard); people + timeline
#     in-flight stay audible (aria-busy or role=status / sr-only, not
#     aria-hidden-only). Docs: quiet muted skeleton; boot spinner stays;
#     reduced-motion is static.
#204: recoverable errors — owned toast (data-toast / $lib/components/ui/toast)
#     for copy / Reveal-in-Finder failures, not the full-width err banner;
#     sandbox #137 sentence, lock, and not-an-archive stay in-page via
#     friendly / banner; toasts never interpolate body_text; ConfirmDialog
#     stays; no analytics / remote reporter / HTTP client. Do not add
#     sonner unless #201/#202 package bans are narrowed (they are not).
#205: partial states — failed person timeline / search / doctor scan show
#     Error + Retry on that pane (data-partial); nav + people stay;
#     do not paint EmptyState “No messages…” / “No hits” / “No doctor
#     issues” on the fail path; pane fails are not only showErr / the
#     full-width err banner (sandbox #137 / lock / not-an-archive stay
#     in-page). Retry is user-clicked once; no setInterval / auto-retry;
#     doctor Retry is not GC CAS / integrity / rebuild. Owned Button
#     OK. No CDN / HTTP client / updater / network.server / sonner.
#     Keep #202/#203/#204/#137/#156/#113/#120. Docs: failed pane shows
#     Error + Retry; the rest of the shell stays.
#206: group consecutive person-timeline bubbles — same from_me + same
#     conversation_id + same UTC day is one caption (time+chip) then quieter
#     followers (data-grouped, or skip .caption / data-platform-chip). Key off
#     the filtered list (previous index), not only the previous windowed row.
#     Day headings stay; each message stays its own row (data-tl-index / j/k).
#     Bodies stay text nodes; CasAttach stays on followers. No network avatars.
#     Do not soften #111/#112/#113/#115/#120/#205. Docs: consecutive same-side
#     / same-conversation / same-UTC-day bubbles share one caption (keep the
#     existing hour:minute + chip sentence).
#207: one person-timeline bubble stack — identity/time (data-bubble-meta),
#     then body/subject (data-bubble-body), then attachments (data-bubble-attach
#     wrapping CasAttach). WA (isMailRow false) and Gmail (isMailRow true) share
#     that source order; CasAttach must not sit above the body wrapper. 4/8
#     spacing on the stack (flex-col + gap-2/gap-3 and/or p-2/p-3; no mt-[7px]
#     / p-[5px]). Do not keep an always-on empty attach flex sibling (hook on
#     CasAttach, or {#if attachments.length}); do not stack article gap-2/3
#     plus CasAttach ul.mt-2 (SearchPane may keep mt-2). Followers may omit
#     data-bubble-meta (#206). Do not soften #111/#117/#206/#120/#205. Not:
#     HTML mail, reactions, new platforms, sender_identity_id. Docs: every
#     bubble stacks identity/time, then body/subject, then attachments
#     (WA and Gmail the same).
#208: always-available chrome search field (`data-chrome-search` in App nav /
#     header, not only the Search tab). Routes to Search + `#q` (canonical);
#     SearchPane `run()` stays the only `api.search` caller. ⌘F from People
#     also lands on `#q` (rewrites the #132 Find-on-People branch). `/` still
#     people filter. No Spotlight, no multi-archive, no remote search, no
#     second FTS. Not #209 filters / #210 hit density / #211 titlebar /
#     #215 palette / #224 virtualizer.
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
# Timeline row loop — full list names or windowed variants (#120).
_EACH_TIMELINE = re.compile(
    r"\{#each\s+(?:"
    r"timeline|dayGroups|"
    r"windowed(?:Day)?Groups|visible(?:Day)?Groups|virtual(?:Day)?Groups|"
    r"rendered(?:Day)?Groups|windowedRows|visibleRows|virtualRows|renderedRows|"
    r"windowedTimeline|visibleTimeline|virtualTimeline|renderedTimeline|"
    r"windowedItems|visibleItems|virtualItems"
    r")\b"
)
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
    r"(id=[\"']person-timeline[\"']|day-heading|"
    r"\{#each\s+(?:timeline|dayGroups|windowed(?:Day)?Groups|visible(?:Day)?Groups|"
    r"virtual(?:Day)?Groups|rendered(?:Day)?Groups|windowedRows|visibleRows|"
    r"virtualRows|renderedRows|windowedTimeline|visibleTimeline)\b)",
    re.I,
)
# Names accepted as the person-timeline {#each} source (#111–#113 / #120).
_TIMELINE_EACH_NAMES = (
    "timeline",
    "dayGroups",
    "windowedDayGroups",
    "windowedGroups",
    "visibleDayGroups",
    "visibleGroups",
    "virtualDayGroups",
    "virtualGroups",
    "renderedDayGroups",
    "renderedGroups",
    "windowedRows",
    "visibleRows",
    "virtualRows",
    "renderedRows",
    "windowedTimeline",
    "visibleTimeline",
    "virtualTimeline",
    "renderedTimeline",
    "windowedItems",
    "visibleItems",
    "virtualItems",
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
            start = -1
            for name in _TIMELINE_EACH_NAMES:
                idx = text.find(f"{{#each {name}", i)
                if idx >= 0 and (start < 0 or idx < start):
                    start = idx
            if start < 0:
                break
            end = text.find("{/each}", start)
            if end < 0:
                fail(f"#111: unclosed {{#each timeline}} in {p.relative_to(crate)}")
            found.append(text[start:end])
            i = end + len("{/each}")
    if not found:
        fail(
            "#111: person timeline must {#each timeline}, {#each dayGroups}, "
            "or a windowed row list as chat rows"
        )
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


def _svelte_snippet_body(src: str, name: str) -> str:
    """Body of `{#snippet name …}…{/snippet}` (no nested snippet support)."""
    head = re.search(rf"\{{#snippet\s+{re.escape(name)}\b[^}}]*\}}", src)
    if not head:
        return ""
    end = src.find("{/snippet}", head.end())
    if end < 0:
        return src[head.end() :]
    return src[head.end() : end]


def _person_detail_with_renders(app: str) -> str:
    """Person-column markup plus any `{@render snippet()}` bodies it invokes."""
    detail = _person_detail_markup(app)
    extra: list[str] = []
    for m in re.finditer(r"\{@render\s+([A-Za-z_]\w*)\s*\(", detail):
        extra.append(_svelte_snippet_body(app, m.group(1)))
    return detail + ("\n" + "\n".join(extra) if extra else "")


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
    en_pack = _chrome_en_text(crate)
    boot_has_copy = "Opening last archive" in boot
    pack_has_copy = "Opening last archive" in en_pack
    boot_uses_chrome = _markup_uses_chrome_helper(boot, _chrome_helper_names(_web_logic(crate)))
    if not boot_has_copy and "Opening last archive" not in app:
        if not (pack_has_copy and boot_uses_chrome):
            fail(
                "#156: boot screen must keep the exact copy substring "
                "“Opening last archive” (existing gate string; English default / en pack)"
            )
    if not boot_has_copy:
        if not (pack_has_copy and boot_uses_chrome):
            fail(
                "#156: “Opening last archive” must appear in the booting/opening branch "
                "(literal English, or chrome helper + en pack — default stays English)"
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
    # `{@render timelinePaneState()}` hosts EmptyState in a snippet above this
    # window; expand renders so we do not require a fake data-empty on the list.
    pane_empty = _person_detail_with_renders(app)
    if not re.search(
        r"EmptyState|data-empty", pane_empty if pane_empty.strip() else app, re.I
    ):
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
# Pin local CAS only: srcs map / casDataUrl / data: — not a generic url/src binding.
_VOICE_LOCAL_SRC = re.compile(
    r"("
    r"src\s*=\s*\{[^}]{0,120}(?:srcs|casDataUrl|data:)"
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


# #170 — voice-note seek bar (scrub to time, local only). Follow-up to #119.
_VOICE_SEEK_TRACK = re.compile(
    r"("
    r"<input\b[^>]{0,240}type\s*=\s*[\"']range[\"']"
    r"|type\s*=\s*[\"']range[\"']"
    r"|<progress\b"
    r"|data-voice-(?:seek|scrub|progress)"
    r"|role\s*=\s*[\"']slider[\"']"
    r")",
    re.I | re.S,
)
# Write currentTime on the <audio> from a seek — not the onended reset to 0,
# and not currentTimes state used only for elapsed labels.
_VOICE_SEEK_WRITE = re.compile(
    r"("
    r"\.currentTime\s*=\s*(?!0\b)"
    r"|bind:currentTime"
    r")"
)
_VOICE_VIDEO_SCRUBBER = re.compile(
    r"("
    r"<video\b[^>]{0,400}(?:\bcontrols\b|currentTime|type\s*=\s*[\"']range[\"'])"
    r"|data-video-(?:seek|scrub)"
    r"|video\.currentTime\s*="
    r")",
    re.I | re.S,
)


def assert_voice_note_seek(crate: Path) -> None:
    """#170: voice-note player has a local-only seek / progress track.

    Acceptance: user can click or drag a progress track to jump mid-note.
    Seeking writes currentTime (or equivalent) on the local <audio>.
    Source stays casDataUrl / data: — no http(s) stream. Play/pause and
    elapsed/duration remain (#119). Omitted/missing stay placeholders
    (no seek bar). Not: CDN waveform, transcription, video scrubber.
    Docs: docs/user/app.md — scrub a local voice note; still no remote stream.
    """
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail("#170: CasAttach.svelte required for the voice-note seek bar")
    cas = cas_path.read_text()
    cleaned = _without_comments(cas)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    logic = _web_logic(crate)
    surface = cas + "\n" + logic
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 0) Local CAS path only — same casDataUrl / data: as #119. No http(s) stream.
    if "casDataUrl" not in cas:
        fail(
            "#170: voice notes must stay on casDataUrl (local data: URL), "
            "not a remote stream"
        )
    if re.search(r"[\"']https?://", cleaned) or re.search(
        r"src\s*=\s*[\"']https?://", cas, re.I
    ):
        fail("#170: CasAttach must not use remote http(s) URLs for voice/audio")
    if _VOICE_REMOTE_SRC.search(cas) or _VOICE_REMOTE_SRC.search(cleaned):
        fail(
            "#170: seek must not stream http(s) — only local "
            "casDataUrl / data:"
        )
    if not _VOICE_LOCAL_SRC.search(cas):
        fail(
            "#170: <audio> src must stay local casDataUrl / data: / srcs "
            "(no http(s) stream)"
        )

    # 1) Progress track the user can click or drag.
    if not _VOICE_SEEK_TRACK.search(cas):
        fail(
            "#170: voice-note player must have a progress track "
            "(range / progress / seek) the user can click or drag"
        )

    # 2) Seeking writes currentTime on the local <audio>.
    if not _VOICE_SEEK_WRITE.search(cas) and not _VOICE_SEEK_WRITE.search(cleaned):
        fail(
            "#170: seeking must write currentTime (or equivalent) "
            "on the local <audio>"
        )

    # 3) Play/pause + elapsed/duration remain (#119).
    has_audio = bool(_VOICE_AUDIO_EL.search(cas))
    if not has_audio:
        fail(
            "#170: voice-note seek bar is on the in-app <audio> player "
            "(keep play/pause + time from #119)"
        )
    native = bool(_VOICE_NATIVE_CONTROLS.search(cas))
    custom_play = bool(_VOICE_PLAY_PAUSE.search(cas) or _VOICE_PLAY_PAUSE.search(cleaned))
    custom_time = bool(_VOICE_TIME_CHROME.search(cas) or _VOICE_TIME_CHROME.search(cleaned))
    if not (native or (custom_play and custom_time)):
        fail(
            "#170: play/pause and elapsed/duration must remain "
            "(#119 chrome stays; seek bar is in addition)"
        )

    # 4) Omitted / missing stay placeholders — no seek bar on those branches.
    if not _VOICE_OMITTED.search(cas):
        fail(
            "#170: omitted attachments must stay placeholders "
            "(no seek bar on omitted)"
        )
    if not _VOICE_MISSING.search(cas):
        fail(
            "#170: missing attachments must stay placeholders "
            "(no seek bar on missing)"
        )
    track_m = _VOICE_SEEK_TRACK.search(cas)
    if track_m:
        before = cas[: track_m.start()]
        last_omitted = max(before.rfind("omitted"), before.rfind("Media omitted"))
        last_missing = max(
            before.rfind(".missing"),
            before.rfind("not stored"),
            before.rfind("a.missing"),
        )
        last_audio_guard = max(
            before.rfind("isAudio"),
            before.rfind("isVoice"),
            before.rfind("data-voice-note"),
            before.rfind("audio/"),
            before.rfind('kind === "voice"'),
            before.rfind("kind === 'voice'"),
        )
        if last_omitted > last_audio_guard and last_omitted > 0:
            fail(
                "#170: do not put the seek bar on the omitted branch — "
                "omitted stays a placeholder"
            )
        if last_missing > last_audio_guard and last_missing > 0:
            fail(
                "#170: do not put the seek bar on the missing branch — "
                "missing stays a placeholder"
            )

    # 5) Not in scope: waveform-from-CDN, transcription, video scrubber.
    if _VOICE_WAVEFORM_CDN.search(surface) or _VOICE_WAVEFORM_CDN.search(blob):
        fail(
            "#170: not in scope — no waveform visualization from a CDN "
            "(wavesurfer / remote wave assets)"
        )
    if _VOICE_TRANSCRIPTION.search(cleaned) or _VOICE_TRANSCRIPTION.search(
        _without_comments(blob)
    ):
        fail(
            "#170: not in scope — no transcription UI "
            "(transcribe / speech-to-text / transcript pane)"
        )
    if _VOICE_VIDEO_SCRUBBER.search(cas) or _VOICE_VIDEO_SCRUBBER.search(cleaned):
        fail("#170: not in scope — no video scrubber")

    # 6) Docs: scrub a local voice note; still no remote stream.
    # Window on voice/audio lines so Search “seeks near sent_at” is not a hit.
    if not dtxt.strip():
        fail("#170: docs/user/app.md required (scrub a local voice note)")
    voice_doc = ""
    for m in re.finditer(
        r".{0,160}(?:voice notes?|audio).{0,160}",
        dtxt,
        re.I | re.S,
    ):
        voice_doc += m.group(0) + "\n"
    if not re.search(r"\b(?:scrub|seek)\w*\b", voice_doc, re.I):
        fail("#170: docs/user/app.md must say you can scrub a local voice note")
    if not re.search(
        r"("
        r"never a remote stream"
        r"|no remote stream"
        r"|not a remote stream"
        r"|remote stream"
        r")",
        voice_doc,
        re.I,
    ):
        fail(
            "#170: docs/user/app.md must still say voice notes are not a remote stream"
        )


# #120 — virtualize person timeline (visible + overscan only in the DOM).
# Static analysis: fail naive full {#each dayGroups}→{#each group.rows} without a window.
# No FPS/perf assertions in CI; dogfood measures 10k scroll.
_VIRT_SIGNAL = re.compile(
    r"("
    r"\boverscan\b"
    r"|\bvirtual(?:ize|ized|izing|isation|ization)?\b"
    r"|\bVirtualList\b"
    r"|\bvirtual(?:List|Rows?|Window|Scroll|Range|Items?)\b"
    r"|\bwindow(?:ed|ing)(?:Rows?|Items?|Groups?|Range|Start|End|Slice|Timeline|DayGroups?)?\b"
    r"|\bvisible(?:Range|Start|End|Count|Window|Slice|Rows?|Items?|Groups?|DayGroups?|"
    r"Indices|Index)\b"
    r"|\b(?:start|end)(?:Index|Row|Offset)\b"
    r"|\b(?:first|last)Visible(?:Index|Row|Item)?\b"
    r"|\brender(?:ed)?(?:Rows?|Items?|Range|Window|Slice|Groups?)\b"
    r"|\bviewport(?:Rows?|Range|Height|Top)\b"
    r"|\b(?:row|item)(?:Height|Size)\b"
    r"|\bestimated(?:Row|Item)?(?:Height|Size)\b"
    r"|\btotalHeight\b"
    r"|\bspacer(?:Height|Top|Bottom)?\b"
    r"|\bscrollMargin\b"
    r"|\bsvelte-virtual(?:-list)?\b"
    r"|@tanstack/(?:svelte-)?virtual\b"
    r"|\bcreateVirtualizer\b"
    r"|\buseVirtualizer\b"
    r"|\bVirtualizer\b"
    r")",
    re.I,
)
# Classic anti-pattern: full dayGroups then every group.rows (no window).
_NAIVE_DAYGROUPS_ROWS = re.compile(
    r"\{#each\s+dayGroups\b[^}]*\}[\s\S]{0,1200}?\{#each\s+group\.rows\b",
    re.I,
)
# Full unwindowed list each (flat timeline / filtered list of every row).
_NAIVE_FULL_ROW_EACH = re.compile(
    r"\{#each\s+(?:timeline|filteredTimeline)\b",
    re.I,
)
_BODY_INNER_HTML = re.compile(
    r"("
    r"\{@html\b"
    r"|\.innerHTML\s*="
    r"|insertAdjacentHTML\s*\("
    r")",
)
_SCOPE_10M = re.compile(
    r"("
    r"10\s*[Mm](?:illion)?\b[^.\n]{0,80}"
    r"(?:one view|single view|in (?:the )?DOM|all (?:at )?once|in one (?:list|view))"
    r"|(?:render|mount|load)\s+(?:all\s+)?10\s*[Mm]"
    r")",
    re.I,
)
_SCOPE_LAZY_EVERY_PHOTO = re.compile(
    r"("
    r"lazy[- ]decode\s+every\s+(?:photo|image|cas|attachment)"
    r"|decode\s+every\s+(?:photo|image)\s+laz"
    r"|lazyDecodeEvery"
    r")",
    re.I,
)
_JK_KEY = re.compile(
    r"("
    r"key\s*===?\s*[\"']j[\"']"
    r"|[\"']j[\"']\s*===?\s*key"
    r"|key\s*===?\s*[\"']k[\"']"
    r"|[\"']k[\"']\s*===?\s*key"
    r"|visibleTlIndices"
    r"|nearestVisibleTlIndex"
    r")",
    re.I,
)


def _derived_body(cleaned: str, name: str) -> str | None:
    """Return the body of `const name = $derived...` / `$derived.by` if present."""
    m = re.search(
        rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*\$derived(?:\.by)?\s*\(",
        cleaned,
    )
    if not m:
        return None
    open_idx = m.end() - 1
    close = _match_closer(cleaned, open_idx)
    if close < 0:
        return cleaned[m.end() : m.end() + 2500]
    return cleaned[open_idx + 1 : close]


def _body_has_row_window(body: str) -> bool:
    """True if a derived-list body actually bounds rows (not only ISO day slice)."""
    if re.search(
        r"\boverscan\b|\bvirtual|\bwindow(?:ed|ing|Start|End|Range)|"
        r"\bvisible(?:Range|Start|End|Window|Slice|Rows?|Groups?)|"
        r"\b(?:start|end)(?:Index|Row)\b|"
        r"\b(?:first|last)Visible\b|"
        r"createVirtualizer|useVirtualizer",
        body,
        re.I,
    ):
        return True
    # .slice(a, b) row window — exclude the common day-prefix .slice(0, 10).
    for sm in re.finditer(r"\.slice\s*\(\s*([^)]*)\)", body):
        args = sm.group(1)
        if re.match(r"\s*0\s*,\s*10\s*$", args):
            continue
        if "," in args:
            return True
    return False


def _list_source_is_windowed(cleaned: str, name: str) -> bool:
    """True if `name` is derived/assigned with a real row window (not a rename alone)."""
    body = _derived_body(cleaned, name)
    if body and _body_has_row_window(body):
        return True
    # Non-$derived assignment / helper: name = windowRows(...) / slice(...)
    m = re.search(
        rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?!\$derived)([^;]{{0,400}})",
        cleaned,
    )
    if m and _body_has_row_window(m.group(1)):
        return True
    if re.search(
        rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*"
        r"(?:\$derived(?:\.by)?\s*\()?"
        r"[\s\S]{0,240}"
        r"(?:window(?:ed|ing)\w*|virtual(?:ize|Rows|List|Items?)?|"
        r"visible(?:Range|Rows|Groups?|Window)|"
        r"overscan|createVirtualizer|useVirtualizer)",
        cleaned,
        re.I,
    ):
        return True
    return False


def _timeline_each_names_in_markup(markup: str) -> list[str]:
    """Names used in {#each ...} that look like timeline row sources."""
    names: list[str] = []
    for m in re.finditer(r"\{#each\s+([A-Za-z_]\w*)\b", markup):
        name = m.group(1)
        if name in _TIMELINE_EACH_NAMES or re.match(
            r"^(?:windowed|visible|virtual|rendered)",
            name,
            re.I,
        ):
            names.append(name)
        elif name in {"timeline", "filteredTimeline", "dayGroups"}:
            names.append(name)
    return names


def _naive_full_timeline_mount(markup: str, cleaned: str) -> bool:
    """True if the person timeline always mounts every filtered row (no window)."""
    # 1) {#each dayGroups} → {#each group.rows} with unwindowed dayGroups.
    if _NAIVE_DAYGROUPS_ROWS.search(markup):
        if not _list_source_is_windowed(cleaned, "dayGroups"):
            return True
    # 2) Flat {#each timeline|filteredTimeline} without windowing that source.
    for m in _NAIVE_FULL_ROW_EACH.finditer(markup):
        mm = re.search(r"\{#each\s+(\w+)", m.group(0))
        name = mm.group(1) if mm else "timeline"
        if not _list_source_is_windowed(cleaned, name):
            return True
    # 3) Any timeline-ish each whose source is not windowed (rename without window).
    for name in _timeline_each_names_in_markup(markup):
        if name in {"dayGroups", "timeline", "filteredTimeline"}:
            continue  # already covered; dayGroups alone without rows is headings-only
        # Nested group.rows is not a top-level list name.
        if not _list_source_is_windowed(cleaned, name):
            # Only treat as naive if the each body looks like message rows.
            for em in re.finditer(rf"\{{#each\s+{re.escape(name)}\b[^}}]*\}}", markup):
                end = _matching_each_end(markup, em.start())
                chunk = markup[em.start() : end if end > 0 else em.start() + 800]
                if re.search(
                    r"from_me|body_text|data-from-me|bubble-me|group\.rows",
                    chunk,
                    re.I,
                ):
                    return True
    return False


def _has_windowed_render_path(markup: str, cleaned: str) -> bool:
    """True if some timeline {#each} iterates a really windowed list (or VirtualList)."""
    for name in _timeline_each_names_in_markup(markup):
        if _list_source_is_windowed(cleaned, name):
            return True
    # Virtual list component / helper owns the window even without a named slice.
    if re.search(
        r"<Virtual(?:List|Scroll|izer)?\b|createVirtualizer\s*\(|useVirtualizer\s*\(",
        markup + "\n" + cleaned,
        re.I,
    ):
        return True
    # dayGroups itself windowed (still named dayGroups) + nested group.rows.
    if re.search(r"\{#each\s+dayGroups\b", markup) and _list_source_is_windowed(
        cleaned, "dayGroups"
    ):
        return True
    return False


# #121 — SearchPane platform select (closed control; core tokens only).
# Tokens Tauri parse_platform accepts for search (not CLI Platform::Owner).
_CORE_SEARCH_PLATFORM_TOKENS = frozenset({"whatsapp", "gmail", "contacts"})
_INVENTED_SEARCH_PLATFORM_TOKENS = frozenset(
    {
        "twitter",
        "x",
        "slack",
        "discord",
        "telegram",
        "signal",
        "imessage",
        "sms",
        "messenger",
        "instagram",
        "facebook",
        "linkedin",
        "reddit",
        "mastodon",
        "matrix",
        "irc",
    }
)
# Free-text textbox bound to search platform state (invalid tokens typable).
_SEARCH_PLATFORM_FREE_TEXT = re.compile(
    r"<Input\b[^>]{0,400}\bbind:value=\{platform\}"
    r"|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio|submit|button)[\"'])"
    r"[^>]{0,400}\bbind:value=\{platform\}"
    r"|<Input\b[^>]{0,200}\bid\s*=\s*[\"']plat[\"'][^>]{0,200}>"
    r"|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio|submit|button)[\"'])"
    r"[^>]{0,200}\bid\s*=\s*[\"']plat[\"'][^>]{0,200}>",
    re.I,
)
# Closed platform control: native <select> or bits-ui / Select root.
_SEARCH_PLATFORM_SELECT = re.compile(
    r"<select\b[^>]{0,400}(?:\bbind:value=\{platform\}|\bid\s*=\s*[\"']plat[\"'])"
    r"|(?:\bbind:value=\{platform\}|\bid\s*=\s*[\"']plat[\"'])[^>]{0,400}>"
    r"|<(?:[A-Za-z][\w]*\.)?Select(?:\.Root)?\b[^>]{0,400}\bplatform\b",
    re.I,
)
_SEARCH_OPTION_VALUE = re.compile(
    r"<option\b([^>]*)>",
    re.I,
)
_SEARCH_OPTION_VALUE_ATTR = re.compile(
    r"\bvalue\s*=\s*(?:\{\s*([\"'])(.*?)\1\s*\}|([\"'])(.*?)\3|\{([^}]*)\})",
    re.I | re.S,
)
# bits-ui / custom Select.Item value="…"
_SEARCH_SELECT_ITEM_VALUE = re.compile(
    r"<(?:[A-Za-z][\w]*\.)?(?:Select\.Item|SelectItem|Option)\b([^>]*)>",
    re.I,
)
_SEARCH_API_PLATFORM_ARG = re.compile(
    r"api\.search\s*\(\s*\{([\s\S]{0,800}?)\}",
    re.I,
)
_SEARCH_PLATFORM_ARG = re.compile(
    r"\bplatform\s*:\s*([^,\n}]+)",
    re.I,
)
# Empty select value must mean any → null/empty from select *state* (not bare null).
_SEARCH_PLATFORM_EMPTY_AS_ANY = re.compile(
    r"platform\s*:\s*(?:"
    r"platform\s*\|\|\s*(?:null|undefined)"
    r"|platform\s*\?\?\s*(?:null|undefined)"
    r"|platform\s*\?\s*platform\s*:\s*(?:null|undefined)"
    r"|platform\s*===\s*[\"'][\"']\s*\?\s*(?:null|undefined)"
    r"|!platform\s*\?\s*(?:null|undefined)\s*:\s*platform"
    r"|platform\b"
    r")",
    re.I,
)
# api.search platform arg must read the select binding (not a decorative control).
_SEARCH_PLATFORM_STATE_FLOW = re.compile(
    r"platform\s*:\s*platform\b",
    re.I,
)


def _search_platform_option_values(markup: str) -> list[str]:
    """Collect value= attributes from <option> / Select.Item near platform control."""
    values: list[str] = []
    for tag_re in (_SEARCH_OPTION_VALUE, _SEARCH_SELECT_ITEM_VALUE):
        for m in tag_re.finditer(markup):
            attrs = m.group(1) or ""
            am = _SEARCH_OPTION_VALUE_ATTR.search(attrs)
            if not am:
                # <option>any</option> with no value attr → empty string in HTML
                if tag_re is _SEARCH_OPTION_VALUE and "value" not in attrs.lower():
                    values.append("")
                continue
            if am.group(2) is not None:
                values.append(am.group(2))
            elif am.group(4) is not None:
                values.append(am.group(4))
            else:
                # value={expr} — only accept string literals inside
                expr = (am.group(5) or "").strip()
                lit = re.fullmatch(r"([\"'])(.*)\1", expr)
                if lit:
                    values.append(lit.group(2))
                elif expr in {"\"\"", "''"}:
                    values.append("")
    return values


def assert_search_platform_select(crate: Path) -> None:
    """#121: Search platform is a closed <select>, not free-text.

    Options: empty/any + whatsapp + gmail (core tokens). Empty value means any
    and is sent as null/empty to api.search from select state. Invalid tokens
    cannot be typed. contacts may appear (existing core + Tauri parse); do not
    invent twitter/slack/… or offer owner unless parse_platform accepts it.
    Not: new platforms, regex platform matching.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#121: SearchPane.svelte required (search platform control lives there)")
    src = search_path.read_text()
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    # Prefer markup; fall back to whole file for script-only option lists.
    surface = markup if markup.strip() else src
    whole = cleaned

    # 1) Must still call api.search with a platform arg (filter reaches core).
    api_m = _SEARCH_API_PLATFORM_ARG.search(whole)
    if not api_m:
        # Multiline / nested — looser fallback.
        if not re.search(r"api\.search\s*\(", whole):
            fail("#121: SearchPane must call api.search")
        if not re.search(r"\bplatform\s*:", whole):
            fail(
                "#121: api.search must receive platform from the select "
                "(platform: … in the search args)"
            )
        api_args = whole
    else:
        api_args = api_m.group(1)
        if not re.search(r"\bplatform\s*:", api_args):
            fail(
                "#121: api.search must receive platform from the select "
                "(platform: … in the search args)"
            )

    plat_arg_m = _SEARCH_PLATFORM_ARG.search(api_args)
    plat_arg = (plat_arg_m.group(1).strip() if plat_arg_m else "") or ""
    if plat_arg and re.fullmatch(
        r"[\"'](?:" + "|".join(sorted(_INVENTED_SEARCH_PLATFORM_TOKENS)) + r")[\"']",
        plat_arg,
        re.I,
    ):
        fail(
            "#121: api.search platform must come from the select state, "
            "not a hard-coded invented token"
        )
    if plat_arg and re.fullmatch(r"[\"'](?:whatsapp|gmail|contacts|owner)[\"']", plat_arg, re.I):
        fail(
            "#121: api.search platform must be user-selected from the control, "
            "not hard-coded to a single platform"
        )
    # Must flow from select state (platform: platform …), not bare null only.
    if not _SEARCH_PLATFORM_STATE_FLOW.search(api_args) and not _SEARCH_PLATFORM_STATE_FLOW.search(
        whole
    ):
        fail(
            "#121: api.search platform must read the select state "
            "(e.g. platform: platform || null) — not a bare null / ignored control"
        )

    # 2) Fail free-text Input/textbox for platform (invalid tokens typable).
    if _SEARCH_PLATFORM_FREE_TEXT.search(surface) or _SEARCH_PLATFORM_FREE_TEXT.search(src):
        fail(
            "#121: search platform must not be a free-text Input/textbox "
            "(invalid tokens cannot be typed — use a closed <select>)"
        )
    # Platform label + Input nearby without a select is also free-text.
    if re.search(r"Platform", surface, re.I) and re.search(
        r"<Input\b|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio)[\"'])",
        surface,
        re.I,
    ):
        # Only fail when the free-text sits in the platform field region.
        for m in re.finditer(r"Platform", surface, re.I):
            window = surface[m.start() : m.start() + 400]
            if re.search(
                r"<Input\b[^>]{0,200}(?:platform|plat)|"
                r"<input\b[^>]{0,200}(?:platform|plat)|"
                r"bind:value=\{platform\}",
                window,
                re.I,
            ) and not re.search(r"<select\b|Select\.Root|SelectItem", window, re.I):
                fail(
                    "#121: search platform must not be a free-text Input/textbox "
                    "(invalid tokens cannot be typed — use a closed <select>)"
                )

    # 3) Closed control: <select> (or equivalent) bound to platform.
    has_select = bool(_SEARCH_PLATFORM_SELECT.search(surface)) or bool(
        _SEARCH_PLATFORM_SELECT.search(src)
    )
    # Also accept a plain <select> whose options carry core tokens next to Platform.
    if not has_select:
        plat_label = re.search(
            r"(?:for\s*=\s*[\"']plat[\"']|>\s*Platform\s*<|id\s*=\s*[\"']plat[\"'])",
            surface,
            re.I,
        )
        if plat_label:
            window = surface[plat_label.start() : plat_label.start() + 800]
            has_select = bool(re.search(r"<select\b", window, re.I)) or bool(
                re.search(r"<(?:[A-Za-z][\w]*\.)?Select(?:\.Root)?\b", window, re.I)
            )
    if not has_select:
        fail(
            "#121: search platform must be a closed <select> "
            "(or equivalent Select control) with fixed options — not free text"
        )

    # 4) Options: empty/any + whatsapp + gmail; only core tokens.
    # Narrow to the platform <select>…</select> when present.
    option_region = surface
    sel = re.search(
        r"<select\b[^>]{0,400}(?:\bbind:value=\{platform\}|\bid\s*=\s*[\"']plat[\"'])"
        r"[^>]*>[\s\S]{0,2000}?</select>",
        surface,
        re.I,
    )
    if not sel:
        sel = re.search(
            r"(?:for\s*=\s*[\"']plat[\"']|>\s*Platform\s*<)[\s\S]{0,200}"
            r"<select\b[^>]*>[\s\S]{0,2000}?</select>",
            surface,
            re.I,
        )
    if sel:
        option_region = sel.group(0)

    values = _search_platform_option_values(option_region)
    # Fallback: any option values in SearchPane markup if region parse missed.
    if not values:
        values = _search_platform_option_values(surface)

    norm = [v.strip() for v in values]
    lower = [v.lower() for v in norm]

    if "" not in norm:
        # Empty value required for “any”. value="any"/"all" alone is not enough.
        fail(
            "#121: platform <select> must include an empty-value option for Any "
            '(value="" — empty means any; do not send a literal "any" token)'
        )

    if "whatsapp" not in lower:
        fail(
            "#121: platform <select> must offer whatsapp "
            "(core token; issue: Any | whatsapp | gmail)"
        )
    if "gmail" not in lower:
        fail(
            "#121: platform <select> must offer gmail "
            "(core token; issue: Any | whatsapp | gmail)"
        )

    for v in lower:
        if v == "":
            continue
        if v in _INVENTED_SEARCH_PLATFORM_TOKENS:
            fail(
                f"#121: do not invent search platform option {v!r} "
                "(only core tokens: whatsapp, gmail, and optionally contacts)"
            )
        if v not in _CORE_SEARCH_PLATFORM_TOKENS:
            # Labels like "Any" must not appear as non-empty values.
            if v in {"any", "all"}:
                fail(
                    "#121: Any/all must use empty value=\"\" (core has no \"any\" platform "
                    "token — empty means any)"
                )
            fail(
                f"#121: platform option value {v!r} is not accepted by search "
                "(allowed: whatsapp, gmail, contacts; empty = any; no owner unless IPC accepts it)"
            )

    # 5) Empty value means any → null/empty from select state to api.search.
    if not _SEARCH_PLATFORM_EMPTY_AS_ANY.search(whole):
        fail(
            "#121: empty platform must mean any "
            "(send null/empty from select state — e.g. platform: platform || null)"
        )

    # Default state should be empty/any, not a forced platform.
    if re.search(
        r"\b(?:let|const|var)\s+platform\s*=\s*\$state\s*\(\s*[\"']"
        r"(?:whatsapp|gmail|contacts|owner|"
        + "|".join(sorted(_INVENTED_SEARCH_PLATFORM_TOKENS))
        + r")[\"']\s*\)",
        whole,
        re.I,
    ) or re.search(
        r"\bplatform\s*=\s*\$state\s*\(\s*[\"']"
        r"(?:whatsapp|gmail|contacts|owner)[\"']\s*\)",
        whole,
        re.I,
    ):
        fail(
            "#121: platform state must default to empty/any "
            "(not pre-selected to a single platform)"
        )


# #122 — SearchPane conversation-kind select (closed control; dm|group|email_thread).
_CORE_SEARCH_KIND_TOKENS = frozenset({"dm", "group", "email_thread"})
_INVENTED_SEARCH_KIND_TOKENS = frozenset(
    {
        "channel",
        "room",
        "broadcast",
        "community",
        "thread",
        "space",
        "channel_thread",
        "mailing_list",
        "list",
        "forum",
        "chat",
        "private",
        "public",
        "supergroup",
    }
)
# State bindings accepted for the kind select (camel/snake + short names).
_SEARCH_KIND_STATE = (
    r"(?:conversationKind|conversation_kind|searchKind|kindFilter|kind)"
)
# Free-text textbox bound to search kind state (invalid tokens typable).
_SEARCH_KIND_FREE_TEXT = re.compile(
    rf"<Input\b[^>]{{0,400}}\bbind:value=\{{{_SEARCH_KIND_STATE}\}}"
    rf"|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio|submit|button)[\"'])"
    rf"[^>]{{0,400}}\bbind:value=\{{{_SEARCH_KIND_STATE}\}}"
    rf"|<Input\b[^>]{{0,200}}\bid\s*=\s*[\"'](?:skind|kind|conv-kind|conversation-kind)[\"']"
    rf"[^>]{{0,200}}>"
    rf"|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio|submit|button)[\"'])"
    rf"[^>]{{0,200}}\bid\s*=\s*[\"'](?:skind|kind|conv-kind|conversation-kind)[\"']"
    rf"[^>]{{0,200}}>",
    re.I,
)
# Closed kind control: native <select> or bits-ui Select.
_SEARCH_KIND_SELECT = re.compile(
    rf"<select\b[^>]{{0,400}}(?:\bbind:value=\{{{_SEARCH_KIND_STATE}\}}"
    rf"|\bid\s*=\s*[\"'](?:skind|kind|conv-kind|conversation-kind)[\"'])"
    rf"|(?:\bbind:value=\{{{_SEARCH_KIND_STATE}\}}"
    rf"|\bid\s*=\s*[\"'](?:skind|kind|conv-kind|conversation-kind)[\"'])[^>]{{0,400}}>"
    rf"|<(?:[A-Za-z][\w]*\.)?Select(?:\.Root)?\b[^>]{{0,400}}"
    rf"\b(?:conversationKind|conversation_kind|searchKind|kindFilter)\b",
    re.I,
)
_SEARCH_API_KIND_ARG = re.compile(
    r"\b(?:conversationKind|conversation_kind)\s*:\s*([^,\n}]+)",
    re.I,
)
# Empty select value must mean any → null/empty from select *state*.
_SEARCH_KIND_EMPTY_AS_ANY = re.compile(
    r"(?:conversationKind|conversation_kind)\s*:\s*(?:"
    rf"{_SEARCH_KIND_STATE}\s*\|\|\s*(?:null|undefined)"
    rf"|{_SEARCH_KIND_STATE}\s*\?\?\s*(?:null|undefined)"
    rf"|{_SEARCH_KIND_STATE}\s*\?\s*{_SEARCH_KIND_STATE}\s*:\s*(?:null|undefined)"
    rf"|{_SEARCH_KIND_STATE}\s*===\s*[\"'][\"']\s*\?\s*(?:null|undefined)"
    rf"|!{_SEARCH_KIND_STATE}\s*\?\s*(?:null|undefined)\s*:\s*{_SEARCH_KIND_STATE}"
    rf"|{_SEARCH_KIND_STATE}\b"
    r")",
    re.I,
)
# api.search kind arg must read the select binding (not a decorative control).
_SEARCH_KIND_STATE_FLOW = re.compile(
    rf"(?:conversationKind|conversation_kind)\s*:\s*{_SEARCH_KIND_STATE}\b",
    re.I,
)


def assert_search_conversation_kind(crate: Path) -> None:
    """#122: Search conversation kind is a closed <select>, not free-text.

    Options: empty/any + dm + group + email_thread. Empty value means any and is
    sent as null/empty to api.search (conversationKind / conversation_kind).
    Groups still respect include-groups (checkbox must remain). Do not invent
    kinds beyond those three. Not: Gmail label filter.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#122: SearchPane.svelte required (search conversation-kind control lives there)")
    src = search_path.read_text()
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    whole = cleaned

    # 1) api.search must receive conversationKind / conversation_kind from select state.
    api_m = _SEARCH_API_PLATFORM_ARG.search(whole)
    if not api_m:
        if not re.search(r"api\.search\s*\(", whole):
            fail("#122: SearchPane must call api.search")
        if not re.search(r"\b(?:conversationKind|conversation_kind)\s*:", whole):
            fail(
                "#122: api.search must receive conversationKind / conversation_kind "
                "from the select (conversationKind: … in the search args)"
            )
        api_args = whole
    else:
        api_args = api_m.group(1)
        if not re.search(r"\b(?:conversationKind|conversation_kind)\s*:", api_args):
            fail(
                "#122: api.search must receive conversationKind / conversation_kind "
                "from the select (conversationKind: … in the search args)"
            )

    kind_arg_m = _SEARCH_API_KIND_ARG.search(api_args)
    kind_arg = (kind_arg_m.group(1).strip() if kind_arg_m else "") or ""
    if kind_arg and re.fullmatch(
        r"[\"'](?:" + "|".join(sorted(_INVENTED_SEARCH_KIND_TOKENS)) + r")[\"']",
        kind_arg,
        re.I,
    ):
        fail(
            "#122: api.search conversation kind must come from the select state, "
            "not a hard-coded invented token"
        )
    if kind_arg and re.fullmatch(r"[\"'](?:dm|group|email_thread)[\"']", kind_arg, re.I):
        fail(
            "#122: api.search conversation kind must be user-selected from the control, "
            "not hard-coded to a single kind"
        )
    if not _SEARCH_KIND_STATE_FLOW.search(api_args) and not _SEARCH_KIND_STATE_FLOW.search(whole):
        fail(
            "#122: api.search conversation kind must read the select state "
            "(e.g. conversationKind: conversationKind || null) — not a bare null / ignored control"
        )

    # 2) Fail free-text Input/textbox for kind (invalid tokens typable).
    if _SEARCH_KIND_FREE_TEXT.search(surface) or _SEARCH_KIND_FREE_TEXT.search(src):
        fail(
            "#122: search conversation kind must not be a free-text Input/textbox "
            "(invalid tokens cannot be typed — use a closed <select>)"
        )
    # Label "Kind" only — do not match the "kind" suffix inside id="skind".
    if re.search(
        r"(?:Conversation\s+kind|>\s*Kind\s*<|for\s*=\s*[\"'](?:skind|kind)[\"'])",
        surface,
        re.I,
    ) and re.search(
        r"<Input\b|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio)[\"'])",
        surface,
        re.I,
    ):
        for m in re.finditer(
            r"(?:Conversation\s+kind|>\s*Kind\s*<|for\s*=\s*[\"'](?:skind|kind)[\"'])",
            surface,
            re.I,
        ):
            window = surface[m.start() : m.start() + 400]
            if re.search(
                rf"<Input\b[^>]{{0,200}}(?:kind|skind)|"
                rf"<input\b[^>]{{0,200}}(?:kind|skind)|"
                rf"bind:value=\{{{_SEARCH_KIND_STATE}\}}",
                window,
                re.I,
            ) and not re.search(r"<select\b|Select\.Root|SelectItem", window, re.I):
                fail(
                    "#122: search conversation kind must not be a free-text Input/textbox "
                    "(invalid tokens cannot be typed — use a closed <select>)"
                )

    # 3) Closed control: <select> (or equivalent) bound to kind state.
    has_select = bool(_SEARCH_KIND_SELECT.search(surface)) or bool(
        _SEARCH_KIND_SELECT.search(src)
    )
    if not has_select:
        kind_label = re.search(
            r"(?:for\s*=\s*[\"'](?:skind|kind|conv-kind|conversation-kind)[\"']"
            r"|>\s*(?:Conversation\s*kind|Kind)\s*<"
            r"|id\s*=\s*[\"'](?:skind|kind|conv-kind|conversation-kind)[\"'])",
            surface,
            re.I,
        )
        if kind_label:
            window = surface[kind_label.start() : kind_label.start() + 800]
            has_select = bool(re.search(r"<select\b", window, re.I)) or bool(
                re.search(r"<(?:[A-Za-z][\w]*\.)?Select(?:\.Root)?\b", window, re.I)
            )
    if not has_select:
        fail(
            "#122: search conversation kind must be a closed <select> "
            "(or equivalent Select control) with fixed options — not free text"
        )

    # 4) Options: empty/any + dm + group + email_thread; only those tokens.
    option_region = surface
    sel = re.search(
        rf"<select\b[^>]{{0,400}}(?:\bbind:value=\{{{_SEARCH_KIND_STATE}\}}"
        rf"|\bid\s*=\s*[\"'](?:skind|kind|conv-kind|conversation-kind)[\"'])"
        rf"[^>]*>[\s\S]{{0,2000}}?</select>",
        surface,
        re.I,
    )
    if not sel:
        sel = re.search(
            r"(?:for\s*=\s*[\"'](?:skind|kind|conv-kind|conversation-kind)[\"']"
            r"|>\s*(?:Conversation\s*kind|Kind)\s*<)[\s\S]{0,200}"
            r"<select\b[^>]*>[\s\S]{0,2000}?</select>",
            surface,
            re.I,
        )
    if sel:
        option_region = sel.group(0)

    values = _search_platform_option_values(option_region)
    if not values:
        # Fallback only if a dedicated kind select region was found; do not
        # swallow platform <option> values from the rest of SearchPane.
        if sel:
            values = _search_platform_option_values(surface)

    norm = [v.strip() for v in values]
    lower = [v.lower() for v in norm]

    if "" not in norm:
        fail(
            "#122: conversation-kind <select> must include an empty-value option for Any "
            '(value="" — empty means any; do not send a literal "any" token)'
        )
    if "dm" not in lower:
        fail("#122: conversation-kind <select> must offer dm")
    if "group" not in lower:
        fail("#122: conversation-kind <select> must offer group")
    if "email_thread" not in lower:
        fail("#122: conversation-kind <select> must offer email_thread")

    for v in lower:
        if v == "":
            continue
        if v in _INVENTED_SEARCH_KIND_TOKENS:
            fail(
                f"#122: do not invent search conversation-kind option {v!r} "
                "(only: dm, group, email_thread)"
            )
        if v not in _CORE_SEARCH_KIND_TOKENS:
            if v in {"any", "all"}:
                fail(
                    "#122: Any/all must use empty value=\"\" "
                    "(core has no \"any\" conversation_kind token — empty means any)"
                )
            fail(
                f"#122: conversation-kind option value {v!r} is not accepted "
                "(allowed: dm, group, email_thread; empty = any)"
            )

    # 5) Empty value means any → null/empty from select state to api.search.
    if not _SEARCH_KIND_EMPTY_AS_ANY.search(whole):
        fail(
            "#122: empty conversation kind must mean any "
            "(send null/empty from select state — e.g. conversationKind: conversationKind || null)"
        )

    # Default state should be empty/any, not a forced kind.
    if re.search(
        rf"\b(?:let|const|var)\s+{_SEARCH_KIND_STATE}\s*=\s*\$state\s*\(\s*[\"']"
        r"(?:dm|group|email_thread|"
        + "|".join(sorted(_INVENTED_SEARCH_KIND_TOKENS))
        + r")[\"']\s*\)",
        whole,
        re.I,
    ) or re.search(
        rf"\b{_SEARCH_KIND_STATE}\s*=\s*\$state\s*\(\s*[\"']"
        r"(?:dm|group|email_thread)[\"']\s*\)",
        whole,
        re.I,
    ):
        fail(
            "#122: conversation-kind state must default to empty/any "
            "(not pre-selected to a single kind)"
        )

    # Groups still respect include-groups — checkbox must remain on SearchPane.
    if not re.search(r"include groups", src, re.I) and not re.search(
        r"includeGroups", whole
    ):
        fail(
            "#122: keep include-groups on Search (kind=group still respects include_groups)"
        )


# #123 — SearchPane person picker by display name (not free-text numeric id).
# State names accepted for the chosen person id (numeric under the hood).
_SEARCH_PERSON_ID_STATE = (
    r"(?:personId|person_id|selectedPersonId|pickedPersonId|searchPersonId)"
)
# Free-text filter / query over display names (not the stored id).
_SEARCH_PERSON_FILTER_STATE = (
    r"(?:personFilter|personQuery|personSearch|searchPersonFilter|personNameFilter|"
    r"personPickQuery|personPickerQuery|personText|nameFilter)"
)
# Label that treats the control as a raw id field (pre-impl UX).
_SEARCH_PERSON_ID_LABEL = re.compile(
    r">\s*Person\s*id\s*<"
    r"|for\s*=\s*[\"']sp[\"'][^>]*>\s*Person\s*id\s*<"
    r"|placeholder\s*=\s*[\"'][^\"']*\bperson\s*id\b[^\"']*[\"']",
    re.I,
)
# Free-text Input bound to the stored person id (user types a number).
# id="sp" alone is fine for a name-filter field; fail only when bound to id state
# or when the id field uses list= datalist of people ids.
_SEARCH_PERSON_ID_FREE_TEXT = re.compile(
    rf"<Input\b[^>]{{0,400}}\bbind:value=\{{{_SEARCH_PERSON_ID_STATE}\}}"
    rf"|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio|submit|button)[\"'])"
    rf"[^>]{{0,400}}\bbind:value=\{{{_SEARCH_PERSON_ID_STATE}\}}"
    rf"|<Input\b[^>]{{0,200}}(?:\bid\s*=\s*[\"']sp[\"'][^>]{{0,200}}\blist\s*="
    rf"|\blist\s*=\s*[\"']people-ids[\"'][^>]{{0,200}}\bbind:value=\{{{_SEARCH_PERSON_ID_STATE}\}})"
    rf"|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio|submit|button)[\"'])"
    rf"[^>]{{0,200}}(?:\bid\s*=\s*[\"']sp[\"'][^>]{{0,200}}\blist\s*="
    rf"|\blist\s*=\s*[\"']people-ids[\"'])",
    re.I,
)
# datalist whose option values are numeric person ids (primary pre-impl UX).
_SEARCH_PERSON_DATALIST_ID_VALUE = re.compile(
    r"<datalist\b[^>]{0,200}(?:people-ids|person-ids|people_ids)[^>]*>[\s\S]{0,1200}?"
    r"<option\b[^>]*\bvalue\s*=\s*\{[^}]{0,40}\b(?:p\.id|person\.id|String\s*\(\s*p\.id)",
    re.I,
)
_SEARCH_PERSON_DATALIST_ID_VALUE_LOOSE = re.compile(
    r"<datalist\b[^>]*>[\s\S]{0,1200}?"
    r"<option\b[^>]*\bvalue\s*=\s*\{\s*(?:String\s*\(\s*)?(?:p|person)\.id",
    re.I,
)
# Visible each of people (or a filtered people list) for the name picker.
_SEARCH_PERSON_EACH = re.compile(
    r"\{#each\s+(?:"
    r"people|filteredPeople|personOptions|searchPeople|filteredSearchPeople|"
    r"personMatches|personList|pickerPeople|visiblePeople|nameMatches|"
    r"filteredPerson(?:s|Options)?|personPicker(?:People|List|Options)?"
    r")\b",
    re.I,
)
# Name-facing control chrome (combobox / listbox / select / filtered list).
_SEARCH_PERSON_NAME_CONTROL = re.compile(
    r"("
    r"<(?:[A-Za-z][\w]*\.)?Combobox(?:\.Root)?\b"
    r"|role\s*=\s*[\"'](?:combobox|listbox)[\"']"
    r"|aria-autocomplete\s*="
    r"|data-person-picker"
    r"|id\s*=\s*[\"'](?:person-picker|sp-person|search-person)[\"']"
    r"|<select\b[^>]{0,400}(?:"
    rf"\bbind:value=\{{{_SEARCH_PERSON_ID_STATE}\}}"
    r"|\bid\s*=\s*[\"'](?:sp|person|search-person|person-picker)[\"']"
    r")"
    r")",
    re.I,
)
# Type-to-filter path over people display names (plain includes / fold OK).
_SEARCH_PERSON_TYPE_FILTER = re.compile(
    r"("
    r"people\.filter\s*\("
    r"|(?:filteredPeople|personOptions|searchPeople|personMatches|pickerPeople|"
    r"visiblePeople|nameMatches|filteredPerson(?:s|Options)?|"
    r"personPicker(?:People|List|Options)?)\s*="
    r"|display_name[^;\n]{0,100}\.toLowerCase"
    r"|display_name[^;\n]{0,100}\.includes"
    r"|(?:toLowerCase\s*\(\s*\)[^;\n]{0,60}includes|"
    r"includes\s*\([^)]{0,60}toLowerCase)"
    rf"|{_SEARCH_PERSON_FILTER_STATE}"
    r"|Combobox\.(?:Input|Root)|cmdk|command-input"
    r")",
    re.I,
)
# Enter to pick (first match or highlighted row).
_SEARCH_PERSON_ENTER = re.compile(
    r"("
    r"(?:key|code)\s*===?\s*[\"']Enter[\"']"
    r"|(?:on:keydown|onkeydown)(?:\|\w+)*\s*=\s*\{[^}]{0,300}Enter"
    r"|keydown[^;\n]{0,160}Enter"
    r"|case\s*[\"']Enter[\"']"
    r")",
    re.I,
)
# Enter handler must actually choose a person (not only submit Search).
_SEARCH_PERSON_ENTER_PICK = re.compile(
    rf"("
    rf"(?:key|code)\s*===?\s*[\"']Enter[\"'][\s\S]{{0,400}}"
    rf"(?:{_SEARCH_PERSON_ID_STATE}\s*="
    r"|pickPerson|selectPerson|choosePerson|setPerson|onPickPerson"
    r"|\.id\b)"
    rf"|(?:pickPerson|selectPerson|choosePerson)\s*\("
    rf"|{_SEARCH_PERSON_ID_STATE}\s*=\s*(?:p|person|match|first|hit|row|selected)\.id"
    r")",
    re.I,
)
# api.search personId flows from picker state (empty → null).
_SEARCH_API_PERSON_ARG = re.compile(
    rf"\b(?:personId|person_id)\s*:\s*([^,\n}}]+)",
    re.I,
)
_SEARCH_PERSON_STATE_FLOW = re.compile(
    rf"(?:personId|person_id)\s*:\s*(?:"
    rf"{_SEARCH_PERSON_ID_STATE}\s*\?\s*Number\s*\(\s*{_SEARCH_PERSON_ID_STATE}\s*\)"
    rf"|{_SEARCH_PERSON_ID_STATE}\s*\?\s*{_SEARCH_PERSON_ID_STATE}"
    rf"|Number\s*\(\s*{_SEARCH_PERSON_ID_STATE}\s*\)"
    rf"|{_SEARCH_PERSON_ID_STATE}\s*\|\|"
    rf"|{_SEARCH_PERSON_ID_STATE}\s*\?\?"
    rf"|{_SEARCH_PERSON_ID_STATE}\b"
    r")",
    re.I,
)
# Multi-person OR scope creep (single personId only).
_SEARCH_MULTI_PERSON_OR = re.compile(
    r"("
    r"\bpersonIds\s*:"
    r"|\bperson_ids\s*:"
    r"|\bselectedPersonIds\b"
    r"|\bpickedPersonIds\b"
    r"|\bsearchPersonIds\b"
    r"|multi(?:ple)?[-\s]?person"
    r"|person\s*OR\s*person"
    r"|any\s+of\s+(?:these\s+)?people"
    r"|multiple\s+people"
    r"|bind:value=\{[^}]{0,40}personIds"
    r"|type\s*=\s*[\"']checkbox[\"'][^>]{0,200}person"
    r")",
    re.I,
)
# Fuzzy-beyond-filter product claims (plain includes is fine; fuse.js etc. not).
_SEARCH_PERSON_FUZZY_CREEP = re.compile(
    r"("
    r"\bfuse\.js\b"
    r"|\bfuzzysort\b"
    r"|\bfuseSearch\b"
    r"|\bfuzzy(?:Match|Search|Filter)?\b"
    r"|levenshtein"
    r"|string-similarity"
    r")",
    re.I,
)


def assert_search_person_picker(crate: Path) -> None:
    """#123: search person is a name-facing combobox/list, not free-text Person id.

    Same people source as the sidebar (people prop). Selecting stores person_id
    for api.search({ personId }). Keyboard required: type-to-filter display names
    AND Enter to pick (first match or highlighted). Clear = no person filter.
    Fail free-text “Person id” + datalist of numeric ids as primary UX.
    Not: multi-person OR, fuzzy name search beyond plain list filter.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#123: SearchPane.svelte required (search person picker lives there)")
    src = search_path.read_text()
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    whole = cleaned

    # 1) Reject free-text id-only UX (current pre-impl SearchPane). Prefer this
    # as the red gate so the fix target is obvious before positive checks.
    if _SEARCH_PERSON_ID_LABEL.search(surface) or _SEARCH_PERSON_ID_LABEL.search(src):
        fail(
            "#123: search person must not be labeled “Person id” — "
            "use a name-facing picker (combobox / filtered list of display names); "
            "store person_id underneath for api.search"
        )
    if _SEARCH_PERSON_DATALIST_ID_VALUE.search(surface) or _SEARCH_PERSON_DATALIST_ID_VALUE.search(
        src
    ) or _SEARCH_PERSON_DATALIST_ID_VALUE_LOOSE.search(surface) or _SEARCH_PERSON_DATALIST_ID_VALUE_LOOSE.search(
        src
    ):
        fail(
            "#123: datalist of numeric person ids is not a name picker "
            "(option value = p.id / String(p.id) forces users to know the id). "
            "Show display names; keep person_id only as the stored value"
        )
    if _SEARCH_PERSON_ID_FREE_TEXT.search(surface) or _SEARCH_PERSON_ID_FREE_TEXT.search(src):
        # Allow type=hidden storage of the id next to a name-facing control.
        hidden_only = True
        for m in _SEARCH_PERSON_ID_FREE_TEXT.finditer(surface + "\n" + src):
            tag = m.group(0)
            if not re.search(r"type\s*=\s*[\"']hidden[\"']", tag, re.I):
                hidden_only = False
                break
        if not hidden_only:
            fail(
                "#123: search person must not be a free-text Input bound to personId "
                "(users must not type a numeric id). Use a name-facing combobox / "
                "filtered list; personId stays under the hood"
            )

    # 2) api.search must still receive personId from picker state when chosen.
    api_m = _SEARCH_API_PLATFORM_ARG.search(whole)
    if not api_m:
        if not re.search(r"api\.search\s*\(", whole):
            fail("#123: SearchPane must call api.search")
        if not re.search(r"\b(?:personId|person_id)\s*:", whole):
            fail(
                "#123: api.search must receive personId when a person is chosen "
                "(personId: … in the search args; null/empty when cleared)"
            )
        api_args = whole
    else:
        api_args = api_m.group(1)
        if not re.search(r"\b(?:personId|person_id)\s*:", api_args):
            fail(
                "#123: api.search must receive personId when a person is chosen "
                "(personId: … in the search args; null/empty when cleared)"
            )

    person_arg_m = _SEARCH_API_PERSON_ARG.search(api_args)
    person_arg = (person_arg_m.group(1).strip() if person_arg_m else "") or ""
    if person_arg and re.fullmatch(r"\d+", person_arg):
        fail(
            "#123: api.search personId must come from the picker state, "
            "not a hard-coded numeric id"
        )
    if person_arg and re.fullmatch(r"null|undefined", person_arg, re.I):
        # Bare null with no state read means the picker is ignored.
        if not _SEARCH_PERSON_STATE_FLOW.search(api_args) and not _SEARCH_PERSON_STATE_FLOW.search(
            whole
        ):
            fail(
                "#123: api.search personId must read picker state "
                "(e.g. personId: personId ? Number(personId) : null) — "
                "not a bare null / ignored control"
            )
    if not _SEARCH_PERSON_STATE_FLOW.search(api_args) and not _SEARCH_PERSON_STATE_FLOW.search(
        whole
    ):
        fail(
            "#123: api.search personId must read picker state "
            "(e.g. personId: personId ? Number(personId) : null) — "
            "not a decorative control"
        )

    # 3) Name-facing picker: list/combobox of display names from people prop.
    has_people_prop = bool(
        re.search(r"\bpeople\b", whole)
        and re.search(r"people\s*:\s*Person\[\]|\{[^}]*\bpeople\b[^}]*\}", whole)
    ) or bool(re.search(r"\bpeople\b", src))
    if not has_people_prop:
        fail(
            "#123: SearchPane must take the same people list as the sidebar "
            "(people prop) for the name picker"
        )

    has_each = bool(_SEARCH_PERSON_EACH.search(surface) or _SEARCH_PERSON_EACH.search(src))
    # {#each people as p} is the minimum source loop.
    if not has_each and not re.search(r"\{#each\s+people\b", surface):
        fail(
            "#123: person picker must iterate people (or a filtered people list) "
            "so display names can be chosen — same source as the sidebar"
        )

    # display_name must appear as the visible label (not only as datalist text
    # beside value=id — already rejected above).
    picker_region = surface
    each_m = _SEARCH_PERSON_EACH.search(surface) or re.search(r"\{#each\s+people\b", surface)
    if each_m:
        end = _matching_each_end(surface, each_m.start())
        picker_region = surface[each_m.start() : end if end > 0 else each_m.start() + 800]
    if not re.search(r"\bdisplay_name\b", picker_region) and not re.search(
        r"\bdisplay_name\b", surface
    ):
        fail(
            "#123: person picker must show display_name (name-facing), "
            "not raw person ids as the primary label"
        )
    # Visible text node / binding of the name in the each body.
    if each_m and not re.search(
        r"\{[^}]{0,80}display_name[^}]{0,40}\}|display_name\s*\}",
        picker_region,
    ):
        # Allow personLabel(p) / format helpers that read display_name in script.
        if not re.search(
            r"(?:personLabel|displayName|formatPerson|personName)\s*\(",
            surface + "\n" + whole,
        ):
            fail(
                "#123: person picker list/options must present display_name to the user "
                "(search “messages with Ada” without knowing her id)"
            )

    has_name_control = bool(
        _SEARCH_PERSON_NAME_CONTROL.search(surface)
        or _SEARCH_PERSON_NAME_CONTROL.search(src)
        or re.search(
            rf"bind:value=\{{{_SEARCH_PERSON_FILTER_STATE}\}}",
            surface,
        )
        or re.search(
            r"<(?:ul|ol|div|menu)\b[^>]{0,200}(?:person-picker|person-options|people-picker)",
            surface,
            re.I,
        )
    )
    # Filtered list with clickable name rows counts even without combobox role.
    has_pick_action = bool(
        re.search(
            r"(?:onclick|on:click)(?:\|\w+)*\s*=\s*\{[^}]{0,200}"
            rf"(?:{_SEARCH_PERSON_ID_STATE}\s*="
            r"|pickPerson|selectPerson|choosePerson|onPickPerson)",
            surface,
            re.I,
        )
        or re.search(
            rf"{_SEARCH_PERSON_ID_STATE}\s*=\s*(?:p|person|match|row)\.id",
            whole,
        )
    )
    if not has_name_control and not has_pick_action:
        fail(
            "#123: require a name-facing person control "
            "(combobox / select / filtered list of display names with pick action) — "
            "not free-text id entry"
        )

    # 4) Keyboard: type-to-filter display names AND Enter to pick.
    # Required (issue): type to filter, Enter to pick first/highlighted.
    # bits-ui / role=combobox may supply both without an explicit key===Enter
    # handler in app code — accept that as the keyboard path.
    has_combobox_widget = bool(
        re.search(
            r"<(?:[A-Za-z][\w]*\.)?Combobox(?:\.Root|\.Input)?\b"
            r"|role\s*=\s*[\"']combobox[\"']"
            r"|aria-autocomplete\s*=",
            surface,
            re.I,
        )
        or re.search(
            r"<(?:[A-Za-z][\w]*\.)?Combobox(?:\.Root|\.Input)?\b",
            whole,
            re.I,
        )
    )
    has_type_filter = bool(
        _SEARCH_PERSON_TYPE_FILTER.search(whole) or _SEARCH_PERSON_TYPE_FILTER.search(surface)
    )
    if not has_type_filter and not has_combobox_widget:
        fail(
            "#123: keyboard path requires type-to-filter on display names "
            "(people.filter / includes / personFilter — plain case-insensitive "
            "substring is fine; same spirit as the sidebar filter). "
            "A Combobox widget also counts"
        )
    has_enter = bool(
        _SEARCH_PERSON_ENTER.search(whole) or _SEARCH_PERSON_ENTER.search(surface)
    )
    has_enter_pick = bool(
        _SEARCH_PERSON_ENTER_PICK.search(whole) or _SEARCH_PERSON_ENTER_PICK.search(surface)
    )
    if not has_combobox_widget:
        if not has_enter:
            fail(
                "#123: keyboard path requires Enter to pick "
                "(first match or highlighted row — key === \"Enter\" / onkeydown Enter). "
                "A Combobox widget’s built-in Enter also counts"
            )
        if not has_enter_pick:
            # Enter might only submit the Search form — require a pick path.
            fail(
                "#123: Enter on the person control must pick a person "
                "(set personId / pickPerson from the filtered list), "
                "not only submit the search form"
            )

    # 5) Forbid multi-person OR and fuzzy-beyond-list-filter scope creep.
    if _SEARCH_MULTI_PERSON_OR.search(whole) or _SEARCH_MULTI_PERSON_OR.search(surface):
        # type=checkbox for include groups is fine; only fail person multi-select.
        multi = _SEARCH_MULTI_PERSON_OR.search(whole) or _SEARCH_MULTI_PERSON_OR.search(surface)
        snippet = multi.group(0) if multi else ""
        if re.search(r"includeGroups|include groups", snippet, re.I):
            pass
        else:
            fail(
                "#123: not in scope — multi-person OR / personIds multi-select "
                f"(found {snippet!r}). Single person_id filter only"
            )
    if _SEARCH_PERSON_FUZZY_CREEP.search(whole) or _SEARCH_PERSON_FUZZY_CREEP.search(src):
        fail(
            "#123: not in scope — fuzzy name search beyond the existing list filter "
            "(plain case-insensitive includes / fold is enough)"
        )

    # 6) Keep platform (#121) and kind (#122) selects present.
    if not re.search(r"\bplatform\b", whole) or not re.search(r"<select\b", surface, re.I):
        fail("#123: keep the search platform <select> (#121) when adding the person picker")
    if not re.search(r"conversationKind|conversation_kind", whole):
        fail(
            "#123: keep the search conversation-kind <select> (#122) when adding the person picker"
        )


# #124 — search hit jumps to that message on the person timeline (not a dead end).
# Jump / open-at-message handlers (App callback or local + parent wire).
_SEARCH_JUMP_FN = re.compile(
    r"\b(?:"
    r"jumpToMessage|jumpToHit|jumpToSearchHit|openSearchHit|openHit|goToMessage|"
    r"openPersonAtMessage|selectPersonAtMessage|openAtMessage|jumpToPersonMessage|"
    r"onJumpToMessage|onOpenHit|onOpenSearchHit|onJumpHit|onSearchHit|"
    r"handleSearchHit|activateSearchHit|openHitOnTimeline"
    r")\b",
    re.I,
)
# Props / callbacks SearchPane may receive from App for the jump path.
_SEARCH_JUMP_PROP = re.compile(
    r"\b(?:"
    r"onJumpToMessage|onOpenHit|onOpenSearchHit|onJumpHit|onSearchHit|"
    r"jumpToMessage|openSearchHit|openHit|onJump"
    r")\b",
    re.I,
)
# Switching to the People view (leave Search).
_VIEW_PEOPLE = re.compile(
    r"view\s*=\s*[\"']people[\"']"
    r"|view\s*=\s*\{?\s*[\"']people[\"']"
    r"|\bsetView\s*\(\s*[\"']people[\"']\s*\)"
    r"|\bnavigate\s*\(\s*[\"']people[\"']\s*\)",
    re.I,
)
# Selecting / opening a person (existing selectPerson or jump-specific open).
_SELECT_PERSON_CALL = re.compile(
    r"\b(?:"
    r"selectPerson|openPerson|pickPerson|showPerson|loadPerson|"
    r"openPersonAtMessage|selectPersonAtMessage|jumpToPersonMessage"
    r")\s*\(",
    re.I,
)
# Hit activation must read person_id from the hit (not the search filter state).
_HIT_PERSON_ID_READ = re.compile(
    r"(?:h|hit|row|item|searchHit)\s*\.\s*(?:person_id|personId)\b"
    r"|\b(?:h|hit|row|item|searchHit)\s*\?\s*\.\s*(?:person_id|personId)\b"
    r"|(?:person_id|personId)\s*:\s*(?:h|hit|row|item|searchHit)\s*\.\s*(?:person_id|personId)",
    re.I,
)
# Message id from the hit carried into the jump / scroll path (not only toggle expand).
_HIT_MESSAGE_ID_READ = re.compile(
    r"(?:h|hit|row|item|searchHit)\s*\.\s*(?:message_id|messageId)\b"
    r"|(?:message_id|messageId)\s*:\s*(?:h|hit|row|item|searchHit)\s*\.\s*(?:message_id|messageId)",
    re.I,
)
# Expand-body path (no person_id / stay on Search) — current toggle + searchBody.
_SEARCH_EXPAND_BODY = re.compile(
    r"\b(?:api\.)?searchBody\s*\("
    r"|\bexpanded\s*="
    r"|\btoggle\s*\(\s*(?:h|hit|id|message_id|messageId)",
    re.I,
)
# Scroll / highlight once the target row is known.
_SEARCH_JUMP_SCROLL_HL = re.compile(
    r"("
    r"\bensureTlIndexVisible\s*\("
    r"|\bscrollIntoView\s*\("
    r"|\btlIndex\s*="
    r"|data-message-id"
    r"|data-tl-index"
    r"|data-message="
    r"|\bfindIndex\s*\([^)]{0,80}(?:message_id|messageId)"
    r"|\.findIndex\s*\("
    r"|\bscrollToMessage\s*\("
    r"|\bscrollMessageIntoView\s*\("
    r"|\bhighlightMessage\s*\("
    r"|ring-2\s+ring-ring"
    r")",
    re.I,
)
# Loading a timeline window that can include the target message (around / after /
# before cursor, or messageId arg). Repeated Load older is OK if bounded — we
# only require some load path that can place message_id in the loaded set.
_SEARCH_JUMP_LOAD_WINDOW = re.compile(
    r"("
    r"\bpersonTimeline\s*\("
    r"|\bapi\.personTimeline\s*\("
    r"|\baround\s*:"
    r"|\bafter\s*:"
    r"|\bbefore\s*:"
    r"|\bmessageId\s*:"
    r"|\bmessage_id\s*:"
    r"|\baroundMessage\b"
    r"|\bloadAround\b"
    r"|\bopenAround\b"
    r"|\bjumpLoad\b"
    r"|\bselectPerson\s*\("
    r")",
    re.I,
)
# Names accepted for the open-hit / jump entry point (click + Enter call this).
# Plain string (adjacent literals) so it embeds cleanly in larger patterns.
_SEARCH_JUMP_CALL_RE = (
    r"jumpToMessage|jumpToHit|jumpToSearchHit|openSearchHit|openHit|goToMessage|"
    r"openPersonAtMessage|selectPersonAtMessage|openAtMessage|jumpToPersonMessage|"
    r"onJumpToMessage|onOpenHit|onOpenSearchHit|onJumpHit|onSearchHit|"
    r"handleSearchHit|activateSearchHit|openHitOnTimeline|activateHit|openHitRow"
)
# Hit click / Enter invokes a jump or activate entry (not only toggle).
_HIT_ACTIVATES_JUMP = re.compile(
    rf"("
    rf"(?:onclick|on:click)(?:\|\w+)*\s*=\s*\{{[\s\S]{{0,400}}\b(?:"
    rf"{_SEARCH_JUMP_CALL_RE}"
    rf")\s*\("
    rf"|(?:onclick|on:click)(?:\|\w+)*\s*=\s*\{{[\s\S]{{0,400}}"
    rf"(?:h|hit)\s*\.\s*(?:person_id|personId)"
    rf"|(?:key|code)\s*===?\s*[\"']Enter[\"'][\s\S]{{0,400}}\b(?:"
    rf"{_SEARCH_JUMP_CALL_RE}"
    rf")\s*\("
    rf"|(?:key|code)\s*===?\s*[\"']Enter[\"'][\s\S]{{0,400}}"
    rf"(?:h|hit)\s*\.\s*(?:person_id|personId)"
    rf")",
    re.I,
)
# Jump handler body must select person + carry message id (not a no-op name).
_JUMP_BODY_SELECTS_PERSON = re.compile(
    r"("
    r"\bselectPerson\s*\("
    r"|\bopenPerson\s*\("
    r"|\bopenPersonAtMessage\s*\("
    r"|\bselectPersonAtMessage\s*\("
    r"|view\s*=\s*[\"']people[\"']"
    r")",
    re.I,
)
_JUMP_BODY_USES_MESSAGE = re.compile(
    r"("
    r"\b(?:message_id|messageId)\b"
    r"|\bensureTlIndexVisible\s*\("
    r"|\btlIndex\s*="
    r"|data-message-id"
    r"|\bfindIndex\s*\("
    r"|\bscrollIntoView\s*\("
    r")",
    re.I,
)
# person_id presence guard on the hit (not the Search filter personId state alone).
_HIT_PERSON_GUARD = re.compile(
    r"("
    r"(?:h|hit|row|item|searchHit)\s*\.\s*(?:person_id|personId)\s*"
    r"(?:\?\?|\|\||&&|!=|!==|==|===|\?)"
    r"|(?:h|hit|row|item|searchHit)\s*\?\s*\.\s*(?:person_id|personId)"
    r"|\bif\s*\([^)]{0,100}(?:h|hit|row|item|searchHit)\s*\.\s*(?:person_id|personId)"
    r"|\b(?:person_id|personId)\s*(?:!=|!==|==|===)\s*(?:null|undefined)[\s\S]{0,120}"
    r"(?:jumpTo|openHit|openSearch|onJump|goToMessage|selectPerson|view\s*=)"
    r")",
    re.I,
)
# #124 miss path — do not treat last loaded row as the hit when findIndex misses.
_IDX_NAME = r"(?:idx|index|foundIdx|foundIndex|tlIdx|pos|foundAt|messageIdx|messageIndex)"
_LOADED_NAME = r"(?:loaded|timeline|rows|chrono|batch|msgs|messages|page|window)"
# tlIndex = idx >= 0 ? idx : Math.max(0, loaded.length - 1)  (and close variants)
_SEARCH_JUMP_LAST_ROW_FALLBACK = re.compile(
    rf"("
    rf"tlIndex\s*=\s*{_IDX_NAME}\s*>=?\s*0\s*\?\s*{_IDX_NAME}\s*:\s*"
    rf"(?:Math\.max\s*\(\s*0\s*,\s*)?{_LOADED_NAME}\s*\.length\s*-\s*1"
    rf"|{_IDX_NAME}\s*>=?\s*0\s*\?\s*{_IDX_NAME}\s*:\s*"
    rf"(?:Math\.max\s*\(\s*0\s*,\s*)?{_LOADED_NAME}\s*\.length\s*-\s*1"
    rf"|{_IDX_NAME}\s*(?:<\s*0|===?\s*-1)\s*\?\s*"
    rf"(?:Math\.max\s*\(\s*0\s*,\s*)?{_LOADED_NAME}\s*\.length\s*-\s*1"
    rf"|findIndex\s*\([\s\S]{{0,160}}(?:message_id|messageId)[\s\S]{{0,280}}"
    rf"tlIndex\s*=\s*[^;\n]{{0,120}}{_LOADED_NAME}\s*\.length\s*-\s*1"
    rf"|tlIndex\s*=\s*{_IDX_NAME}\s*>=?\s*0\s*\?\s*{_IDX_NAME}\s*:"
    rf")",
    re.I,
)
# Any ternary that sets tlIndex from findIndex-style idx with a non-idx false branch
# (wrong-row success) — pairs with the last-row ban above.
_SEARCH_JUMP_TLINDEX_MISS_TERNARY = re.compile(
    rf"tlIndex\s*=\s*{_IDX_NAME}\s*(?:>=?\s*0|<\s*0|===?\s*-1)\s*\?",
    re.I,
)
# Miss branch must surface showErr / onError / throw (not only catch).
_SEARCH_JUMP_MISS_ERROR = re.compile(
    rf"("
    rf"if\s*\(\s*{_IDX_NAME}\s*(?:<\s*0|===?\s*-1)\s*\)\s*\{{[\s\S]{{0,280}}"
    rf"(?:showErr|onError)\s*\("
    rf"|if\s*\(\s*{_IDX_NAME}\s*(?:<\s*0|===?\s*-1)\s*\)[\s\S]{{0,120}}"
    rf"(?:showErr|onError)\s*\("
    rf"|if\s*\(\s*{_IDX_NAME}\s*(?:<\s*0|===?\s*-1)\s*\)\s*\{{[\s\S]{{0,200}}\bthrow\b"
    rf"|if\s*\(\s*{_IDX_NAME}\s*>=?\s*0\s*\)[\s\S]{{0,400}}"
    rf"else\s*\{{[\s\S]{{0,200}}(?:showErr|onError)\s*\("
    rf"|if\s*\(\s*!(?:found|row|hit|target|match|located)\b[\s\S]{{0,160}}"
    rf"(?:showErr|onError)\s*\("
    rf"|if\s*\(\s*!{_LOADED_NAME}\.some\s*\([\s\S]{{0,200}}"
    rf"(?:message_id|messageId)[\s\S]{{0,100}}\)\s*\)\s*\{{[\s\S]{{0,240}}"
    rf"(?:showErr|onError)\s*\("
    rf"|if\s*\(\s*{_LOADED_NAME}\.findIndex\s*\([\s\S]{{0,200}}"
    rf"(?:message_id|messageId)[\s\S]{{0,80}}\)\s*(?:<\s*0|===?\s*-1)"
    rf"[\s\S]{{0,200}}(?:showErr|onError)\s*\("
    rf")",
    re.I,
)


def _search_jump_handler_bodies(blob: str) -> list[str]:
    """Bodies of jump/open-hit functions (placeholder names from the gate list)."""
    names = (
        "jumpToMessage",
        "jumpToHit",
        "jumpToSearchHit",
        "openSearchHit",
        "openHit",
        "goToMessage",
        "openPersonAtMessage",
        "selectPersonAtMessage",
        "openAtMessage",
        "jumpToPersonMessage",
        "handleSearchHit",
        "activateSearchHit",
        "openHitOnTimeline",
        "activateHit",
        "openHitRow",
        "onJumpToMessage",
        "onOpenHit",
        "onOpenSearchHit",
    )
    bodies: list[str] = []
    for name in names:
        body = _function_body(blob, name)
        if body.strip():
            bodies.append(body)
    return bodies


def _assert_search_jump_miss_path(web_blob: str, jump_bodies: list[str]) -> None:
    """#124 miss: error on unfound message_id; never ring last loaded as the hit."""
    path = "\n".join(jump_bodies) if jump_bodies else web_blob
    path_clean = _without_comments(path)
    blob_clean = _without_comments(web_blob)

    # 1) Forbid last-row (or any idx-ternary) fallback as a successful hit ring.
    if _SEARCH_JUMP_LAST_ROW_FALLBACK.search(path_clean) or (
        _SEARCH_JUMP_LAST_ROW_FALLBACK.search(blob_clean)
        and re.search(
            r"findIndex\s*\([\s\S]{0,120}(?:message_id|messageId)",
            blob_clean,
            re.I,
        )
    ):
        fail(
            "#124: when message_id is not in the loaded timeline after the jump walk, "
            "do not set tlIndex to the last loaded row "
            "(tlIndex = idx >= 0 ? idx : Math.max(0, loaded.length - 1)). "
            "That rings an unrelated message with no error. Surface showErr instead"
        )
    if _SEARCH_JUMP_TLINDEX_MISS_TERNARY.search(path_clean):
        fail(
            "#124: do not assign tlIndex via idx-miss ternary "
            "(tlIndex = idx >= 0 ? idx : <fallback>). "
            "On miss: showErr (or equivalent) and return — only set tlIndex when "
            "the hit row is actually found"
        )

    # 2) Require an explicit miss → error path (catch-only showErr is not enough).
    has_miss_err = bool(
        _SEARCH_JUMP_MISS_ERROR.search(path_clean)
        or _SEARCH_JUMP_MISS_ERROR.search(blob_clean)
    )
    if not has_miss_err:
        fail(
            "#124: when the jump path cannot place message_id in the loaded set "
            "(miss after bounded walk / cap), surface an error "
            "(if (idx < 0) { showErr(...); return } / else showErr / "
            "!loaded.some(...message_id) showErr). "
            "Do not treat a wrong row as a successful hit highlight"
        )

    # Prefer (not hard-gated): pass hit.sent_at into onJumpToMessage /
    # openPersonAtMessage when present so the walk can seek near the hit.


def assert_search_jump_to_message(crate: Path) -> None:
    """#124: search hit with person_id jumps to that message on the person timeline.

    With person_id: switch to People, select that person, load a window around
    message_id, scroll the row into view, highlight once (tlIndex / ring as j/k).
    Without person_id: stay on Search and expand body (toggle / searchBody).
    Miss after bounded load: showErr (or equivalent); never ring last-loaded as hit.
    Virtualized timeline (#120): ensure target index enters the window
    (ensureTlIndexVisible / scroll estimate) when that path exists.
    Not: FTS rewrite, inventing a person when person_id is missing.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    app_path = crate / "web" / "App.svelte"
    if not search_path.is_file():
        fail("#124: SearchPane.svelte required (search hit jump lives there)")
    if not app_path.is_file():
        fail("#124: App.svelte required (People view / selectPerson / timeline scroll)")

    search_src = search_path.read_text()
    app_src = app_path.read_text()
    logic = _web_logic(crate)
    search_clean = _without_comments(search_src)
    app_clean = _without_comments(app_src)
    logic_clean = _without_comments(logic)
    search_markup = _svelte_markup(search_src)
    surface = search_markup if search_markup.strip() else search_src
    # Jump path may live in SearchPane, App, or a small helper under web/.
    web_blob = search_clean + "\n" + app_clean + "\n" + logic_clean

    # 1) Hits must still be listed and activatable (click and/or keyboard Enter).
    if not re.search(r"\{#each\s+hits\b", surface) and not re.search(
        r"\{#each\s+hits\b", search_src
    ):
        fail("#124: SearchPane must list hits ({#each hits}) so a hit can be opened")
    has_hit_click = bool(
        re.search(r"(?:onclick|on:click)(?:\|\w+)*\s*=\s*\{", surface)
        and re.search(
            r"message_id|messageId|toggle|jump|openHit|openSearch|activate",
            surface + "\n" + search_clean,
            re.I,
        )
    )
    has_hit_enter = bool(
        re.search(r"(?:key|code)\s*===?\s*[\"']Enter[\"']", search_clean)
    )
    if not has_hit_click and not has_hit_enter:
        fail(
            "#124: search hits must be activatable (click and/or Enter) — "
            "a hit is not a dead end"
        )

    # 2) Without person_id: keep expand-body on Search (toggle / searchBody).
    if not _SEARCH_EXPAND_BODY.search(search_clean) and not _SEARCH_EXPAND_BODY.search(
        search_src
    ):
        fail(
            "#124: without person_id, stay on Search and expand body as today "
            "(toggle / api.searchBody / expanded = message_id) — do not invent a person"
        )

    # 3) Hit activation must invoke a jump/activate path (primary pre-impl red).
    #    Current SearchPane only toggle(h.message_id) / Enter → toggle — fail that.
    hit_activates_jump = bool(
        _HIT_ACTIVATES_JUMP.search(search_src)
        or _HIT_ACTIVATES_JUMP.search(search_clean)
        or _HIT_ACTIVATES_JUMP.search(surface)
    )
    if not hit_activates_jump:
        fail(
            "#124: search hit with person_id must not only expand the body on Search — "
            "click/Enter must call a jump handler (jumpToMessage / openSearchHit / "
            "activateHit / onJumpToMessage…) or branch on hit.person_id. "
            "Without person_id, expand body stays"
        )

    # 4) Jump handler must exist and do real work: People + person + message.
    jump_bodies = _search_jump_handler_bodies(web_blob)
    # Inline arrow assigned to prop: onJumpToMessage={async (pid, mid) => { ... }}
    inline_jump = re.findall(
        r"(?:onJumpToMessage|onOpenHit|onOpenSearchHit|onJumpHit|onSearchHit|onJump)\s*="
        r"\s*\{([\s\S]{0,1500}?)\}(?=\s|/?>)",
        app_src + "\n" + search_src,
        re.I,
    )
    jump_bodies.extend(inline_jump)

    has_jump_symbol = bool(
        _SEARCH_JUMP_FN.search(web_blob) or _SEARCH_JUMP_PROP.search(web_blob)
    )
    if not has_jump_symbol and not jump_bodies:
        fail(
            "#124: require a jump handler (jumpToMessage / openSearchHit / "
            "onJumpToMessage / activateHit / …) that opens the hit on the person timeline"
        )

    # App wires SearchPane callback, or SearchPane jumps itself (view/selectPerson).
    app_wires_jump = bool(
        re.search(
            r"<SearchPane\b[^>]{0,500}(?:"
            r"onJumpToMessage|onOpenHit|onOpenSearchHit|onJumpHit|onSearchHit|"
            r"jumpToMessage|openSearchHit|onJump|activateHit"
            r")",
            app_src,
            re.I,
        )
        or re.search(
            r"SearchPane[\s\S]{0,500}(?:"
            r"onJumpToMessage|onOpenHit|onOpenSearchHit|onJumpHit|onSearchHit|"
            r"jumpToMessage|openSearchHit|onJump|activateHit"
            r")",
            app_clean,
            re.I,
        )
    )
    search_jumps_inline = bool(
        _HIT_PERSON_ID_READ.search(search_clean)
        and (
            _VIEW_PEOPLE.search(search_clean)
            or re.search(r"\bselectPerson\s*\(|\bopenPerson\s*\(", search_clean)
        )
    )
    if not app_wires_jump and not search_jumps_inline and not jump_bodies:
        fail(
            "#124: wire SearchPane → App jump (onJumpToMessage={…} / jumpToMessage) "
            "or jump from SearchPane into People + selectPerson"
        )

    # Real work inside a jump handler (reject no-op name-only stubs).
    body_selects = any(_JUMP_BODY_SELECTS_PERSON.search(b) for b in jump_bodies)
    body_message = any(_JUMP_BODY_USES_MESSAGE.search(b) for b in jump_bodies)
    # selectPerson / view=people near a jump call site also counts (thin wrapper).
    jump_call_near_select = bool(
        re.search(
            rf"(?:{_SEARCH_JUMP_CALL_RE})\s*\([\s\S]{{0,600}}"
            r"(?:selectPerson\s*\(|openPerson\s*\(|view\s*=\s*[\"']people[\"'])"
            rf"|(?:selectPerson\s*\(|view\s*=\s*[\"']people[\"'])[\s\S]{{0,600}}"
            rf"(?:{_SEARCH_JUMP_CALL_RE})\s*\(",
            web_blob,
            re.I,
        )
    )
    # Combined handler in SearchPane: if (h.person_id) { onJump… } else toggle
    search_branches_to_jump = bool(
        re.search(
            r"(?:h|hit)\s*\.\s*(?:person_id|personId)[\s\S]{0,200}"
            rf"(?:{_SEARCH_JUMP_CALL_RE})\s*\(",
            search_clean,
            re.I,
        )
    )

    if not (body_selects or jump_call_near_select or search_jumps_inline):
        fail(
            "#124: jump path must switch to People and select the hit's person "
            "(view = \"people\" + selectPerson / openPerson / openPersonAtMessage — "
            "not a no-op jump name)"
        )
    if not (body_message or search_branches_to_jump or _HIT_MESSAGE_ID_READ.search(
        "\n".join(jump_bodies) if jump_bodies else ""
    )):
        # Message id must reach the open/scroll path.
        if not re.search(
            rf"(?:{_SEARCH_JUMP_CALL_RE})\s*\([^)]{{0,120}}"
            r"(?:message_id|messageId|h\.message|hit\.message)",
            web_blob,
            re.I,
        ) and not re.search(
            r"(?:h|hit)\s*\.\s*(?:message_id|messageId)[\s\S]{0,200}"
            rf"(?:{_SEARCH_JUMP_CALL_RE}|selectPerson|tlIndex|ensureTlIndexVisible)",
            web_blob,
            re.I,
        ):
            fail(
                "#124: jump path must carry hit.message_id "
                "(open around that message, set tlIndex / scroll to that row)"
            )

    # 5) Only jump when person_id is present (no inventing a person).
    if not _HIT_PERSON_GUARD.search(web_blob) and not _HIT_PERSON_ID_READ.search(
        search_clean
    ):
        fail(
            "#124: only jump when hit.person_id is present — without it stay on Search "
            "and expand body (do not invent a person from the hit)"
        )
    # Prefer an explicit guard near jump (hit.person_id ? jump : toggle).
    if not _HIT_PERSON_GUARD.search(web_blob):
        fail(
            "#124: branch on hit.person_id before jumping "
            "(if present → People timeline; else → expand body on Search)"
        )

    # 6) Load a window that can contain message_id.
    # Require load signal inside jump bodies or within a jump-related window —
    # not only the ordinary selectPerson used for sidebar clicks.
    load_in_jump = any(_SEARCH_JUMP_LOAD_WINDOW.search(b) for b in jump_bodies)
    load_near_jump = bool(
        re.search(
            rf"(?:{_SEARCH_JUMP_CALL_RE})[\s\S]{{0,800}}"
            r"(?:personTimeline|around\s*:|after\s*:|before\s*:|aroundMessage|"
            r"loadAround|openAround|selectPerson\s*\()"
            rf"|(?:personTimeline|aroundMessage|loadAround)[\s\S]{{0,400}}"
            rf"(?:{_SEARCH_JUMP_CALL_RE}|message_id|messageId)",
            web_blob,
            re.I,
        )
    )
    if not load_in_jump and not load_near_jump and not body_selects:
        fail(
            "#124: jump path must load a timeline window around message_id "
            "(personTimeline before/after/around, or selectPerson load that can "
            "place the hit in the loaded set — bounded Load older OK for dogfood)"
        )

    # 7) Scroll into view + highlight once — must appear in jump path, not only j/k.
    # Require coupling to a jump handler name (bare tlIndex/message_id elsewhere is j/k / mail fold).
    scroll_in_jump = any(_SEARCH_JUMP_SCROLL_HL.search(b) for b in jump_bodies)
    scroll_near_jump = bool(
        re.search(
            rf"(?:{_SEARCH_JUMP_CALL_RE})[\s\S]{{0,900}}"
            r"(?:ensureTlIndexVisible\s*\(|tlIndex\s*=|scrollIntoView\s*\(|"
            r"data-message-id|scrollToMessage|scrollMessageIntoView|findIndex\s*\()"
            rf"|(?:ensureTlIndexVisible\s*\(|scrollToMessage\s*\(|scrollMessageIntoView\s*\()"
            rf"[\s\S]{{0,400}}(?:{_SEARCH_JUMP_CALL_RE}|message_id|messageId)",
            web_blob,
            re.I,
        )
    )
    if not scroll_in_jump and not scroll_near_jump:
        fail(
            "#124: after jump, scroll the target message into view and highlight once "
            "(tlIndex = … / ensureTlIndexVisible / scrollIntoView / data-message-id — "
            "same ring as j/k selection; must be on the jump path, not only j/k)"
        )
    # Virtualized timeline: ensureTlIndexVisible (or scroll) must exist in App.
    if not re.search(r"\bensureTlIndexVisible\s*\(", app_clean) and not re.search(
        r"scrollIntoView|data-message-id", app_clean
    ):
        fail(
            "#124: timeline must be able to bring the jumped-to index into view "
            "(ensureTlIndexVisible or scrollIntoView / data-message-id; "
            "virtualized lists must open the virtual window on that index)"
        )

    # 8) Keep #121–#123 search chrome.
    if not re.search(r"\bplatform\b", search_clean) or not re.search(
        r"<select\b", surface, re.I
    ):
        fail("#124: keep the search platform <select> (#121) when adding jump-to-hit")
    if not re.search(r"conversationKind|conversation_kind", search_clean):
        fail(
            "#124: keep the search conversation-kind <select> (#122) when adding jump-to-hit"
        )
    if not re.search(
        r"personId|person_id|personFilter|data-person-picker", search_clean
    ):
        fail("#124: keep the search person picker (#123) when adding jump-to-hit")

    # 9) Keep api.search (do not rewrite FTS as part of jump-to-hit).
    if not re.search(r"api\.search\s*\(", search_clean):
        fail("#124: keep api.search (do not rewrite FTS as part of jump-to-hit)")

    # 10) Miss path: error when message_id not in loaded set; never ring last row.
    _assert_search_jump_miss_path(web_blob, jump_bodies)


# #125 — SearchPane attachment presence select (closed; has_file|omitted|missing).
_CORE_SEARCH_ATTACHMENT_TOKENS = frozenset({"has_file", "omitted", "missing"})
_INVENTED_SEARCH_ATTACHMENT_TOKENS = frozenset(
    {
        "video",
        "video_only",
        "image",
        "image_only",
        "audio",
        "audio_only",
        "mime",
        "media",
        "has_media",
        "has:media",
        "hasmedia",
        "sticker",
        "voice",
        "pdf",
        "document",
        "photo",
        "file_type",
        "filetype",
        "mimetype",
        "mime_type",
    }
)
# State bindings accepted for the attachment select (camel/snake + short names).
_SEARCH_ATTACHMENT_STATE = (
    r"(?:attachmentFilter|attachment_filter|attFilter|attachFilter|searchAttachment)"
)
# Free-text textbox bound to attachment filter state (invalid tokens typable).
_SEARCH_ATTACHMENT_FREE_TEXT = re.compile(
    rf"<Input\b[^>]{{0,400}}\bbind:value=\{{{_SEARCH_ATTACHMENT_STATE}\}}"
    rf"|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio|submit|button)[\"'])"
    rf"[^>]{{0,400}}\bbind:value=\{{{_SEARCH_ATTACHMENT_STATE}\}}"
    rf"|<Input\b[^>]{{0,200}}\bid\s*=\s*[\"'](?:satt|att|attachment|attachment-filter)[\"']"
    rf"[^>]{{0,200}}>"
    rf"|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio|submit|button)[\"'])"
    rf"[^>]{{0,200}}\bid\s*=\s*[\"'](?:satt|att|attachment|attachment-filter)[\"']"
    rf"[^>]{{0,200}}>",
    re.I,
)
# Closed attachment control: native <select> or bits-ui Select.
_SEARCH_ATTACHMENT_SELECT = re.compile(
    rf"<select\b[^>]{{0,400}}(?:\bbind:value=\{{{_SEARCH_ATTACHMENT_STATE}\}}"
    rf"|\bid\s*=\s*[\"'](?:satt|att|attachment|attachment-filter)[\"'])"
    rf"|(?:\bbind:value=\{{{_SEARCH_ATTACHMENT_STATE}\}}"
    rf"|\bid\s*=\s*[\"'](?:satt|att|attachment|attachment-filter)[\"'])[^>]{{0,400}}>"
    rf"|<(?:[A-Za-z][\w]*\.)?Select(?:\.Root)?\b[^>]{{0,400}}"
    rf"\b(?:attachmentFilter|attachment_filter|attFilter|attachFilter)\b",
    re.I,
)
_SEARCH_API_ATTACHMENT_ARG = re.compile(
    r"\b(?:attachmentFilter|attachment_filter)\s*:\s*([^,\n}]+)",
    re.I,
)
# Empty select value must mean any → null/empty from select *state*.
_SEARCH_ATTACHMENT_EMPTY_AS_ANY = re.compile(
    r"(?:attachmentFilter|attachment_filter)\s*:\s*(?:"
    rf"{_SEARCH_ATTACHMENT_STATE}\s*\|\|\s*(?:null|undefined)"
    rf"|{_SEARCH_ATTACHMENT_STATE}\s*\?\?\s*(?:null|undefined)"
    rf"|{_SEARCH_ATTACHMENT_STATE}\s*\?\s*{_SEARCH_ATTACHMENT_STATE}\s*:\s*(?:null|undefined)"
    rf"|{_SEARCH_ATTACHMENT_STATE}\s*===\s*[\"'][\"']\s*\?\s*(?:null|undefined)"
    rf"|!{_SEARCH_ATTACHMENT_STATE}\s*\?\s*(?:null|undefined)\s*:\s*{_SEARCH_ATTACHMENT_STATE}"
    rf"|{_SEARCH_ATTACHMENT_STATE}\b"
    r")",
    re.I,
)
# api.search attachment arg must read the select binding (not a decorative control).
_SEARCH_ATTACHMENT_STATE_FLOW = re.compile(
    rf"(?:attachmentFilter|attachment_filter)\s*:\s*{_SEARCH_ATTACHMENT_STATE}\b",
    re.I,
)


def assert_search_attachment_filter(crate: Path) -> None:
    """#125: Search attachment presence is a closed <select>, not free-text.

    Options: empty/any + has_file + omitted + missing. Empty value means any and
    is sent as null/empty to api.search (attachmentFilter / attachment_filter).
    Labels: Any | Has file | Omitted | Missing. Not: MIME taxonomy, video-only.
    Keep #121–#124 search chrome.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#125: SearchPane.svelte required (search attachment control lives there)")
    src = search_path.read_text()
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    whole = cleaned

    # 1) api.search must receive attachmentFilter / attachment_filter from select state.
    api_m = _SEARCH_API_PLATFORM_ARG.search(whole)
    if not api_m:
        if not re.search(r"api\.search\s*\(", whole):
            fail("#125: SearchPane must call api.search")
        if not re.search(r"\b(?:attachmentFilter|attachment_filter)\s*:", whole):
            fail(
                "#125: api.search must receive attachmentFilter / attachment_filter "
                "from the select (attachmentFilter: … in the search args)"
            )
        api_args = whole
    else:
        api_args = api_m.group(1)
        if not re.search(r"\b(?:attachmentFilter|attachment_filter)\s*:", api_args):
            fail(
                "#125: api.search must receive attachmentFilter / attachment_filter "
                "from the select (attachmentFilter: … in the search args)"
            )

    att_arg_m = _SEARCH_API_ATTACHMENT_ARG.search(api_args)
    att_arg = (att_arg_m.group(1).strip() if att_arg_m else "") or ""
    if att_arg and re.fullmatch(
        r"[\"'](?:" + "|".join(sorted(_INVENTED_SEARCH_ATTACHMENT_TOKENS)) + r")[\"']",
        att_arg,
        re.I,
    ):
        fail(
            "#125: api.search attachment filter must come from the select state, "
            "not a hard-coded invented token"
        )
    if att_arg and re.fullmatch(r"[\"'](?:has_file|omitted|missing)[\"']", att_arg, re.I):
        fail(
            "#125: api.search attachment filter must be user-selected from the control, "
            "not hard-coded to a single value"
        )
    if not _SEARCH_ATTACHMENT_STATE_FLOW.search(api_args) and not _SEARCH_ATTACHMENT_STATE_FLOW.search(
        whole
    ):
        fail(
            "#125: api.search attachment filter must read the select state "
            "(e.g. attachmentFilter: attachmentFilter || null) — not a bare null / ignored control"
        )

    # 2) Fail free-text Input/textbox for attachment (invalid tokens typable).
    if _SEARCH_ATTACHMENT_FREE_TEXT.search(surface) or _SEARCH_ATTACHMENT_FREE_TEXT.search(src):
        fail(
            "#125: search attachment filter must not be a free-text Input/textbox "
            "(invalid tokens cannot be typed — use a closed <select>)"
        )
    if re.search(
        r"(?:Attachment|>\s*Has\s*file\s*<|for\s*=\s*[\"'](?:satt|att|attachment)[\"'])",
        surface,
        re.I,
    ) and re.search(
        r"<Input\b|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio)[\"'])",
        surface,
        re.I,
    ):
        for m in re.finditer(
            r"(?:Attachment|>\s*Has\s*file\s*<|for\s*=\s*[\"'](?:satt|att|attachment)[\"'])",
            surface,
            re.I,
        ):
            window = surface[m.start() : m.start() + 400]
            if re.search(
                rf"<Input\b[^>]{{0,200}}(?:att|attachment)|"
                rf"<input\b[^>]{{0,200}}(?:att|attachment)|"
                rf"bind:value=\{{{_SEARCH_ATTACHMENT_STATE}\}}",
                window,
                re.I,
            ) and not re.search(r"<select\b|Select\.Root|SelectItem", window, re.I):
                fail(
                    "#125: search attachment filter must not be a free-text Input/textbox "
                    "(invalid tokens cannot be typed — use a closed <select>)"
                )

    # 3) Closed control: <select> (or equivalent) bound to attachment state.
    has_select = bool(_SEARCH_ATTACHMENT_SELECT.search(surface)) or bool(
        _SEARCH_ATTACHMENT_SELECT.search(src)
    )
    if not has_select:
        att_label = re.search(
            r"(?:for\s*=\s*[\"'](?:satt|att|attachment|attachment-filter)[\"']"
            r"|>\s*Attachment\s*<"
            r"|id\s*=\s*[\"'](?:satt|att|attachment|attachment-filter)[\"'])",
            surface,
            re.I,
        )
        if att_label:
            window = surface[att_label.start() : att_label.start() + 800]
            has_select = bool(re.search(r"<select\b", window, re.I)) or bool(
                re.search(r"<(?:[A-Za-z][\w]*\.)?Select(?:\.Root)?\b", window, re.I)
            )
    if not has_select:
        fail(
            "#125: search attachment filter must be a closed <select> "
            "(or equivalent Select control) with fixed options — not free text"
        )

    # 4) Options: empty/any + has_file + omitted + missing; only those tokens.
    option_region = surface
    sel = re.search(
        rf"<select\b[^>]{{0,400}}(?:\bbind:value=\{{{_SEARCH_ATTACHMENT_STATE}\}}"
        rf"|\bid\s*=\s*[\"'](?:satt|att|attachment|attachment-filter)[\"'])"
        rf"[^>]*>[\s\S]{{0,2000}}?</select>",
        surface,
        re.I,
    )
    if not sel:
        sel = re.search(
            r"(?:for\s*=\s*[\"'](?:satt|att|attachment|attachment-filter)[\"']"
            r"|>\s*Attachment\s*<)[\s\S]{0,200}"
            r"<select\b[^>]*>[\s\S]{0,2000}?</select>",
            surface,
            re.I,
        )
    if sel:
        option_region = sel.group(0)

    values = _search_platform_option_values(option_region)
    if not values:
        if sel:
            values = _search_platform_option_values(surface)

    norm = [v.strip() for v in values]
    lower = [v.lower() for v in norm]

    if "" not in norm:
        fail(
            "#125: attachment <select> must include an empty-value option for Any "
            '(value="" — empty means any; do not send a literal "any" token)'
        )
    if "has_file" not in lower:
        fail("#125: attachment <select> must offer has_file (label: Has file)")
    if "omitted" not in lower:
        fail("#125: attachment <select> must offer omitted")
    if "missing" not in lower:
        fail("#125: attachment <select> must offer missing")

    for v in lower:
        if v == "":
            continue
        if v in _INVENTED_SEARCH_ATTACHMENT_TOKENS:
            fail(
                f"#125: do not invent search attachment option {v!r} "
                "(only: has_file, omitted, missing — no MIME/video-only taxonomy)"
            )
        if v not in _CORE_SEARCH_ATTACHMENT_TOKENS:
            if v in {"any", "all"}:
                fail(
                    "#125: Any/all must use empty value=\"\" "
                    "(core has no \"any\" attachment_filter token — empty means any)"
                )
            fail(
                f"#125: attachment option value {v!r} is not accepted "
                "(allowed: has_file, omitted, missing; empty = any; no MIME/video-only)"
            )

    # 5) Empty value means any → null/empty from select state to api.search.
    if not _SEARCH_ATTACHMENT_EMPTY_AS_ANY.search(whole):
        fail(
            "#125: empty attachment filter must mean any "
            "(send null/empty from select state — e.g. attachmentFilter: attachmentFilter || null)"
        )

    # Default state should be empty/any, not a forced filter.
    if re.search(
        rf"\b(?:let|const|var)\s+{_SEARCH_ATTACHMENT_STATE}\s*=\s*\$state\s*\(\s*[\"']"
        r"(?:has_file|omitted|missing|"
        + "|".join(re.escape(t) for t in sorted(_INVENTED_SEARCH_ATTACHMENT_TOKENS))
        + r")[\"']\s*\)",
        whole,
        re.I,
    ) or re.search(
        rf"\b{_SEARCH_ATTACHMENT_STATE}\s*=\s*\$state\s*\(\s*[\"']"
        r"(?:has_file|omitted|missing)[\"']\s*\)",
        whole,
        re.I,
    ):
        fail(
            "#125: attachment filter state must default to empty/any "
            "(not pre-selected to a single value)"
        )

    # 6) No MIME / video-only option tokens anywhere in SearchPane surface for this control.
    banned_opt = re.search(
        r"<option\b[^>]*\bvalue\s*=\s*[\"'](?:video(?:_only)?|image(?:_only)?|mime|media|"
        r"has[_:]?media|audio(?:_only)?|sticker|voice|pdf)[\"']",
        surface,
        re.I,
    )
    if banned_opt:
        fail(
            f"#125: not in scope — MIME/video-only attachment options "
            f"(found {banned_opt.group(0)!r}); only has_file / omitted / missing"
        )

    # 7) Keep #121–#124 search chrome.
    if not re.search(r"\bplatform\b", whole) or not re.search(r"<select\b", surface, re.I):
        fail("#125: keep the search platform <select> (#121) when adding attachment filter")
    if not re.search(r"conversationKind|conversation_kind", whole):
        fail(
            "#125: keep the search conversation-kind <select> (#122) when adding attachment filter"
        )
    if not re.search(r"personId|person_id|personFilter|data-person-picker", whole):
        fail("#125: keep the search person picker (#123) when adding attachment filter")
    # Jump path may live in App; SearchPane must still list activatable hits.
    if not re.search(r"\{#each\s+hits\b", surface) and not re.search(
        r"\{#each\s+hits\b", src
    ):
        fail("#125: keep search hits list (#124 jump chrome) when adding attachment filter")


# #126 — safe search snippet highlight: <mark> siblings, never innerHTML of body.
# Core FTS snippets already wrap hits with «…» (see docs/user/search.md).
_SEARCH_HIGHLIGHT_HELPER = re.compile(
    r"\b(?:"
    r"splitSnippet|snippetSegments|snippetParts|highlightSnippet|highlightSegments|"
    r"markSegments|markSnippet|segmentSnippet|parseSnippet|snippetMarks|"
    r"highlightSearch|searchHighlight|ftsSnippet|splitFtsSnippet|"
    r"splitMarkers|markerSegments|wrapMarks"
    r")\b",
    re.I,
)
# Split evidence: FTS guillemet markers or a snippet-aware split / segment helper.
_SEARCH_SNIPPET_SPLIT = re.compile(
    r"("
    r"[«»]"  # core FTS snippet markers
    r"|\\u00ab|\\u00bb"  # unicode escapes
    r"|\bsplit\s*\([^)]*(?:snippet|«|»|marker)"
    r"|\.split\s*\(\s*(?:/[«»]|[\"']«|new\s+RegExp\s*\(\s*[\"']«)"
    r"|\b(?:snippetSegments|snippetParts|markSegments|highlightSegments|"
    r"segmentSnippet|splitSnippet|splitMarkers|markerSegments)\b"
    r"|\b(?:segments?|parts)\s*(?:=|:)\s*(?:splitSnippet|highlightSnippet|"
    r"snippetSegments|markSegments|segmentSnippet)\b"
    r")",
    re.I,
)
# <mark> with yellow / highlight / mark class, or bare <mark> used as the hit wrap.
_SEARCH_MARK_TAG = re.compile(r"<mark\b", re.I)
_SEARCH_MARK_STYLE = re.compile(
    r"("
    r"<mark\b[^>]{0,200}\bclass\s*=\s*[\"'][^\"']*"
    r"(?:yellow|highlight|mark|bg-yellow|bg-amber|bg-\[|search-hit|hit-mark)"
    r"|<mark\b"  # intentional <mark> (UA default is yellow-ish; class optional)
    r"|\b(?:bg-yellow-\d+|bg-amber-\d+|text-yellow|highlight|hit-mark|search-mark)\b"
    r")",
    re.I,
)
# Dangerous HTML injection on search snippet/body path.
_SEARCH_UNSAFE_HTML = re.compile(
    r"("
    r"\{@html\b"
    r"|\.innerHTML\s*="
    r"|insertAdjacentHTML\s*\("
    r"|dangerouslySetInnerHTML"
    r")",
    re.I,
)
# Building an HTML string of <mark> via replace (regex highlight → inject path).
_SEARCH_REGEX_HTML_MARK = re.compile(
    r"("
    r"\.replace\s*\([^)]{0,200},\s*[`'\"][^`'\"]*<mark\b"
    r"|replace\s*\(\s*(?:new\s+)?RegExp\b[\s\S]{0,200}<mark\b"
    r"|return\s+[`'\"][^`'\"]*<mark\b[^`'\"]*[`'\"]"  # helper returns HTML string
    r")",
    re.I,
)
# HTML mail renderer (out of scope for #126).
_SEARCH_HTML_MAIL = re.compile(
    r"("
    r"\bDOMParser\b"
    r"|\bsrcdoc\s*="
    r"|\brenderHtmlMail\b|\bhtmlMail\b|\bMimeHtml\b|\brenderMime\b"
    r"|iframe[^>]{0,80}(?:body|snippet|mail|message)"
    r")",
    re.I,
)


def _search_highlight_surface(crate: Path) -> tuple[str, str, list[Path]]:
    """SearchPane + relative snippet/highlight helpers (not CasAttach / general UI)."""
    web = crate / "web"
    lib = web / "lib"
    search_path = lib / "SearchPane.svelte"
    paths: list[Path] = []
    seen: set[Path] = set()
    if search_path.is_file():
        paths.append(search_path)
        seen.add(search_path.resolve())
        text = search_path.read_text()
        for m in re.finditer(r"""from\s+["'](\.[^"']+)["']""", text):
            rel = m.group(1)
            base = (search_path.parent / rel).resolve()
            candidates = [base]
            if not base.suffix:
                candidates.extend(
                    [
                        Path(str(base) + ".ts"),
                        Path(str(base) + ".js"),
                        Path(str(base) + ".svelte"),
                        base / "index.ts",
                        base / "index.js",
                    ]
                )
            for c in candidates:
                if not c.is_file() or c.resolve() in seen:
                    continue
                try:
                    c.relative_to(web.resolve())
                except ValueError:
                    continue
                name = c.name.lower()
                body = c.read_text()
                # Only pull helpers involved in snippet split / mark render.
                if re.search(
                    r"snippet|highlight|mark.?segment|fts.?marker|split.?marker",
                    name + "\n" + body[:4000],
                    re.I,
                ) and not re.search(
                    r"CasAttach|EmptyState|DoctorPane|ImportPane|ReviewPane",
                    c.name,
                ):
                    # Skip pure API types modules unless they define a split helper.
                    if c.name in {"api.ts", "api.js"} and not _SEARCH_HIGHLIGHT_HELPER.search(
                        body
                    ):
                        continue
                    paths.append(c)
                    seen.add(c.resolve())
    blob = "\n".join(p.read_text() for p in paths)
    cleaned = _without_comments(blob)
    return blob, cleaned, paths


def assert_search_safe_highlight(crate: Path) -> None:
    """#126: highlight search tokens with <mark> siblings; never innerHTML the body.

    Split the snippet on core FTS markers («…») or matched query terms; render
    plain text + <mark> Svelte elements (text children only). Yellow / mark
    styling so query e.g. fatura shows a visible mark. Expanded search body
    (api.searchBody → body_text) stays text — a body containing <script> must
    not execute. Not: regex HTML inject, HTML mail. Keep #121–#125 chrome.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#126: SearchPane.svelte required (search snippet highlight lives there)")
    src = search_path.read_text()
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    _blob, blob_clean, helper_paths = _search_highlight_surface(crate)
    # Hits list region is the snippet path; expanded body is the other surface.
    hits_m = re.search(
        r"\{#each\s+hits\b[\s\S]{0,8000}?\{/each\}",
        surface,
        re.I,
    )
    hits_region = hits_m.group(0) if hits_m else surface

    # 1) Primary red: snippet path must render <mark> for hit highlights.
    #    Not a single raw string of h.snippet alone.
    has_mark = bool(_SEARCH_MARK_TAG.search(hits_region)) or bool(
        _SEARCH_MARK_TAG.search(surface)
    )
    # Allow a small child component used only for the snippet line (e.g. SnippetHighlight).
    if not has_mark:
        for p in helper_paths:
            if p.suffix == ".svelte" and p.name != "SearchPane.svelte":
                htxt = p.read_text()
                if _SEARCH_MARK_TAG.search(htxt) and re.search(
                    r"snippet|highlight|mark|segment",
                    htxt,
                    re.I,
                ):
                    has_mark = True
                    break
    if not has_mark:
        fail(
            "#126: search snippet path must render <mark> for hit highlights "
            "(text + <mark> Svelte element siblings — not a single raw snippet string). "
            "Split on core FTS markers «…» or matched query terms"
        )

    # 2) Must actually split into segments (siblings), not wrap the whole snippet
    #    once without a split path. Evidence: FTS markers, segment helper, or
    #    {#each} over parts next to <mark>.
    has_split = bool(_SEARCH_SNIPPET_SPLIT.search(blob_clean)) or bool(
        _SEARCH_HIGHLIGHT_HELPER.search(blob_clean)
    )
    has_each_segments = bool(
        re.search(
            r"\{#each\s+(?:[^}]*\b(?:seg(?:ment)?s?|parts|tokens|chunks|marks|"
            r"highlighted|snippetParts|snippetSegments)\b|"
            r"[^}]{0,80}(?:splitSnippet|highlightSnippet|snippetSegments|"
            r"markSegments|segmentSnippet)\s*\()",
            hits_region + "\n" + surface,
            re.I,
        )
    )
    # <mark> text content must be a segment field, not the full raw snippet alone.
    mark_wraps_full_snippet = bool(
        re.search(
            r"<mark\b[^>]*>\s*\{(?:\(?\s*)?(?:h\.)?snippet\b[^}]{0,120}\}\s*</mark>",
            hits_region,
            re.I,
        )
    )
    if not has_split and not has_each_segments:
        fail(
            "#126: split the snippet into plain-text + <mark> siblings "
            "(core FTS markers «…», or a pure segment helper / {#each} over parts) — "
            "do not leave the hit as one unsplit string"
        )
    if mark_wraps_full_snippet and not has_each_segments and not has_split:
        fail(
            "#126: do not wrap the entire raw snippet in one <mark> — "
            "split on matched terms / FTS «…» markers into text + <mark> siblings"
        )

    # 3) Yellow / highlight styling on the mark (class or intentional <mark>).
    style_blob = hits_region + "\n" + surface
    for p in helper_paths:
        if p.suffix in {".svelte", ".css"}:
            style_blob += "\n" + p.read_text()
    if not _SEARCH_MARK_STYLE.search(style_blob):
        fail(
            "#126: <mark> must be visibly highlighted "
            "(yellow/amber/highlight class e.g. bg-yellow-200, or intentional <mark> styling) "
            "so a query match is obvious"
        )

    # 4) Ban innerHTML / {@html on search snippet and expanded body path.
    if _SEARCH_UNSAFE_HTML.search(blob_clean) or _SEARCH_UNSAFE_HTML.search(cleaned):
        # Narrow: only fail if it touches snippet/body/search surfaces (not unrelated).
        unsafe = re.search(
            r"(?:snippet|body_text|searchBody|\bbody\b|highlight|mark)[\s\S]{0,160}"
            r"(?:\{@html\b|\.innerHTML\s*=|insertAdjacentHTML\s*\()"
            r"|(?:\{@html\b|\.innerHTML\s*=|insertAdjacentHTML\s*\()[\s\S]{0,160}"
            r"(?:snippet|body_text|searchBody|\bbody\b|highlight)",
            blob_clean,
            re.I,
        )
        bare_html = _HTML_BODY.search(blob_clean) or re.search(
            r"\.innerHTML\s*=", blob_clean
        )
        if unsafe or bare_html:
            fail(
                "#126: never assign innerHTML / {@html on the search snippet or body path "
                "(render text + <mark> Svelte elements with text children only — "
                "a body containing <script> must stay text)"
            )

    # Expanded body path specifically: {body} / body_text must stay text bindings.
    expanded_region = ""
    exp = re.search(
        r"\{#if\s+expanded\b[\s\S]{0,800}?\{/if\}",
        surface,
        re.I,
    )
    if exp:
        expanded_region = exp.group(0)
    if expanded_region and (
        _HTML_BODY.search(expanded_region)
        or re.search(r"\.innerHTML\s*=", expanded_region)
        or re.search(r"\{@html\s+body\b", expanded_region)
    ):
        fail(
            "#126: expanded search body must stay text-safe "
            "(no {@html body} / innerHTML of full body — <script> in body stays text)"
        )
    # Global SearchPane ban on {@html body} even outside the if-region.
    if re.search(r"\{@html\s+(?:body|body_text|snippet)\b", blob_clean):
        fail(
            "#126: expanded search body / snippet must stay text-safe — "
            "no {@html body} / {@html snippet}"
        )

    # 5) Not: regex highlight that builds HTML strings to inject.
    if _SEARCH_REGEX_HTML_MARK.search(blob_clean):
        fail(
            "#126: not in scope — regex highlight that builds HTML mark strings "
            "(no .replace(…, '<mark>…') inject path; use text + <mark> element siblings)"
        )

    # 6) Not: HTML mail renderer.
    if _SEARCH_HTML_MAIL.search(blob_clean):
        # Ignore false positives in comments already stripped; still scope to search.
        fail(
            "#126: not in scope — HTML mail renderer "
            "(DOMParser / srcdoc / htmlMail on search path); snippets and body stay text"
        )

    # 7) Keep #121–#125 search chrome.
    if not re.search(r"\bplatform\b", cleaned) or not re.search(
        r"<select\b", surface, re.I
    ):
        fail("#126: keep the search platform <select> (#121) when adding safe highlight")
    if not re.search(r"conversationKind|conversation_kind", cleaned):
        fail(
            "#126: keep the search conversation-kind <select> (#122) when adding safe highlight"
        )
    if not re.search(r"personId|person_id|personFilter|data-person-picker", cleaned):
        fail("#126: keep the search person picker (#123) when adding safe highlight")
    if not re.search(r"\{#each\s+hits\b", surface) and not re.search(
        r"\{#each\s+hits\b", src
    ):
        fail("#126: keep search hits list (#124 jump chrome) when adding safe highlight")
    if not re.search(r"attachmentFilter|attachment_filter", cleaned):
        fail(
            "#126: keep the search attachment filter (#125) when adding safe highlight"
        )


def assert_review_identifiers(crate: Path) -> None:
    """#128: ReviewPane shows identifier kind+value_normalized on each side panel.

    A name_similarity card must be decidable without CLI `review show`: under
    the title, render identifiers (kind + value_normalized; platform optional),
    not only display_name / platforms. Samples stay text nodes (body_text;
    no {@html on sample body). Keep score, evidence list, Accept/Reject.
    Not: dump extra body lines, invent name_score UI changes.
    """
    review_path = crate / "web" / "lib" / "ReviewPane.svelte"
    api_path = crate / "web" / "lib" / "api.ts"
    if not review_path.is_file():
        fail("#128: ReviewPane.svelte required (review card identifier chrome lives there)")
    if not api_path.is_file():
        fail("#128: web/lib/api.ts required (ReviewPanel type surface)")

    src = review_path.read_text()
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    api_src = api_path.read_text()

    # 1) Type surface: ReviewPanel carries identifiers with kind + value_normalized.
    # Nested braces inside ReviewPanel (inline object types) are allowed.
    panel_start = re.search(r"(?:export\s+)?type\s+ReviewPanel\s*=\s*\{", api_src)
    if not panel_start:
        fail("#128: api.ts must declare export type ReviewPanel = { … }")
    brace_i = panel_start.end() - 1
    depth = 0
    end_i = -1
    for j in range(brace_i, len(api_src)):
        c = api_src[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end_i = j
                break
    if end_i < 0:
        fail("#128: unclosed ReviewPanel type in api.ts")
    panel_body = api_src[brace_i + 1 : end_i]
    if not re.search(r"\bidentifiers\b", panel_body):
        fail(
            "#128: ReviewPanel must include identifiers[] "
            "(kind + value_normalized per entry — not only display_name / platforms)"
        )
    # Inline object type, field pair on ReviewPanel, or a named element type.
    ident_shape = (
        re.search(
            r"identifiers\s*[?]?\s*:\s*\{[^}]*\bkind\b[^}]*\bvalue_normalized\b",
            panel_body,
            re.I | re.S,
        )
        or re.search(
            r"identifiers\s*[?]?\s*:\s*\{[^}]*\bvalue_normalized\b[^}]*\bkind\b",
            panel_body,
            re.I | re.S,
        )
        or (
            re.search(r"\bidentifiers\b", panel_body)
            and re.search(r"\bkind\b", panel_body)
            and re.search(r"\bvalue_normalized\b", panel_body)
        )
        or re.search(
            r"(?:export\s+)?type\s+Review(?:Panel)?Ident(?:ifier)?\s*=\s*\{[^}]*\bkind\b[^}]*\bvalue_normalized\b",
            api_src,
            re.I | re.S,
        )
        or re.search(
            r"(?:export\s+)?type\s+Review(?:Panel)?Ident(?:ifier)?\s*=\s*\{[^}]*\bvalue_normalized\b[^}]*\bkind\b",
            api_src,
            re.I | re.S,
        )
    )
    if not ident_shape:
        named = re.search(
            r"identifiers\s*[?]?\s*:\s*([A-Za-z_]\w*)\s*\[\]",
            panel_body,
        )
        named_ok = False
        if named:
            tname = named.group(1)
            m = re.search(
                rf"(?:export\s+)?type\s+{re.escape(tname)}\s*=\s*\{{([^}}]*)\}}",
                api_src,
                re.S,
            )
            if m and re.search(r"\bkind\b", m.group(1)) and re.search(
                r"\bvalue_normalized\b", m.group(1)
            ):
                named_ok = True
        if not named_ok:
            fail(
                "#128: ReviewPanel.identifiers entries must expose kind + value_normalized "
                "(inline or named type; platform optional)"
            )

    # 2) Pane renders identifiers under the panel title — not only panelTitle / platforms.
    panel_each = re.search(
        r"\{#each\s+[^}]*panelsOf\([^)]*\)[^}]*\}[\s\S]{0,4000}?\{/each\}"
        r"|\{#each\s+(?:panel|panels|sides)\b[^}]*\}[\s\S]{0,4000}?\{/each\}",
        surface,
        re.I,
    )
    panel_region = panel_each.group(0) if panel_each else surface
    renders_idents = bool(
        re.search(
            r"("
            r"\{#each\s+[^}]*\bidentifiers\b"
            r"|\.identifiers\b"
            r"|panel\.identifiers"
            r"|identifiers\s*\?\."
            r")",
            panel_region + "\n" + cleaned,
            re.I,
        )
    )
    if not renders_idents:
        fail(
            "#128: ReviewPane must render panel.identifiers "
            "(kind + value_normalized under the title — not only display_name / platforms)"
        )
    has_kind_bind = bool(
        re.search(
            r"("
            r"\{[^}]{0,80}\.kind\b[^}]{0,40}\}"
            r"|\.kind\b"
            r"|ident(?:ifier)?\.kind"
            r"|id\.kind"
            r")",
            panel_region,
            re.I,
        )
    )
    has_norm_bind = bool(
        re.search(
            r"("
            r"\{[^}]{0,80}\.value_normalized\b[^}]{0,40}\}"
            r"|\.value_normalized\b"
            r"|valueNormalized"
            r"|ident(?:ifier)?\.value_normalized"
            r")",
            panel_region + "\n" + cleaned,
            re.I,
        )
    )
    helper_fmt = bool(
        re.search(
            r"("
            r"ident(?:ifier)?Label"
            r"|formatIdent"
            r"|idLabel"
            r"|kind\s*\+\s*"
            r"|value_normalized"
            r")",
            cleaned,
            re.I,
        )
    ) and re.search(r"\bkind\b", cleaned) and re.search(
        r"\bvalue_normalized\b|valueNormalized", cleaned
    )
    if not ((has_kind_bind and has_norm_bind) or helper_fmt):
        fail(
            "#128: ReviewPane must show identifier kind and value_normalized as text "
            "(bindings on the panel loop, or a small formatter used there) — "
            "not only panelTitle(display_name + platforms)"
        )
    if re.search(
        r"\{[^}]{0,40}panel\.person_id[^}]{0,40}\}",
        panel_region,
    ) and not renders_idents:
        fail("#128: do not use raw person_id as the primary identifier label")

    # 3) Samples remain text nodes — no {@html on sample body.
    if re.search(r"\{@html\b", surface):
        fail("#128: ReviewPane samples must stay text nodes — no {@html on sample body}")
    if not re.search(r"\bbody_text\b", surface + "\n" + cleaned):
        fail("#128: ReviewPane must still render sample body_text as text")
    if not re.search(
        r"("
        r"\{[^}]{0,40}body_text[^}]{0,40}\}"
        r"|whitespace-pre-wrap[^>]{0,80}body_text"
        r"|body_text[^;\n]{0,40}\}"
        r")",
        surface,
        re.I,
    ):
        fail("#128: sample bodies must remain text bindings of body_text (not HTML inject)")

    # 4) Keep score + evidence + Accept/Reject chrome (identifiers are additive).
    if not re.search(r"\bevidence\b", surface + "\n" + cleaned):
        fail("#128: keep the evidence list on the review card")
    if not re.search(r"\b(?:score|suggested_score)\b", surface + "\n" + cleaned):
        fail("#128: keep the score on the review card")
    if not re.search(r">\s*Accept\s*<", surface):
        fail("#128: keep Accept on the review card")
    if not re.search(r">\s*Reject\s*<", surface):
        fail("#128: keep Reject on the review card")
    if "panelTitle" not in cleaned and not re.search(r"\bdisplay_name\b", surface):
        fail("#128: keep display_name / panel title chrome; identifiers sit under it")
    if not re.search(r"\bplatforms\b", cleaned):
        fail("#128: keep platforms on the panel surface (identifiers are additive)")

    # 5) Not in scope: inventing name_score threshold UI.
    if re.search(
        r"("
        r"name_score\s*[<>]=?"
        r"|nameScoreThreshold"
        r"|raise.*name_score"
        r"|lower.*name_score"
        r")",
        cleaned,
        re.I,
    ):
        fail(
            "#128: do not invent name_score raise/lower UI "
            "(threshold policy is #103; this issue only surfaces identifiers)"
        )


# #129 — native window title follows open person / view (Cmd-tab).
# Separator: em dash (—) preferred; en dash / " - " / " --- " accepted if consistent.
_TITLE_SEP = r"(?:—|–|---| - )"
_SET_TITLE_CALL = re.compile(r"\bsetTitle\s*\(")
_WINDOW_API_IMPORT = re.compile(
    r"from\s+[\"']@tauri-apps/api/window[\"']"
    r"|import\s*\{[^}]*\b(?:getCurrentWindow|Window)\b[^}]*\}\s*from\s*[\"']@tauri-apps/api"
)
_GET_CURRENT_WINDOW = re.compile(r"\bgetCurrentWindow\s*\(")
_DOCK_BADGE_API = re.compile(
    r"("
    r"\bsetBadgeCount\b"
    r"|\bsetBadgeLabel\b"
    r"|\bsetOverlayIcon\b"
    r"|\bdock\s*\.\s*setBadge\b"
    r"|\bbadgeCount\b"
    r"|\bBadgeCount\b"
    r")",
)
# Message fields that must never flow into setTitle args / title helpers.
_TITLE_BODY_LEAK = re.compile(
    r"("
    r"\bbody_text\b"
    r"|\bsnippet\b"
    r"|\bdisplayBody\b"
    r"|\bsearchBody\b"
    r"|\blast_body\b"
    r"|\blastBody\b"
    r"|\blast_preview\b"
    r"|\bactivityPreview\b"
    r")",
)
_TITLE_HELPER_NAMES = (
    "windowTitle",
    "nativeTitle",
    "appTitle",
    "titleForView",
    "titleForWindow",
    "syncWindowTitle",
    "updateWindowTitle",
    "setWindowTitle",
    "computeWindowTitle",
    "formatWindowTitle",
)


def _title_path_sources(crate: Path) -> str:
    """Web logic that may own setTitle (App + helpers; exclude pure UI chrome)."""
    return _web_logic(crate)


def _collect_set_title_args(src: str) -> list[str]:
    args: list[str] = []
    for m in _SET_TITLE_CALL.finditer(src):
        open_paren = m.end() - 1
        if open_paren < 0 or src[open_paren] != "(":
            continue
        arg = _call_arg(src, open_paren)
        if arg is not None:
            args.append(arg)
    return args


def _title_helper_bodies(src: str) -> list[str]:
    bodies: list[str] = []
    for name in _TITLE_HELPER_NAMES:
        body = _function_body(src, name)
        if body:
            bodies.append(body)
    # $derived / const title = (...) => … / function expressions assigned to common names.
    for name in _TITLE_HELPER_NAMES:
        for m in re.finditer(
            rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?:\$derived(?:\.\w+)?\s*)?"
            rf"(?:\([^)]*\)\s*=>\s*|\([^)]*\)\s*=>\s*\{{|"
            rf"function\s*\([^)]*\)\s*\{{)?",
            src,
        ):
            # Prefer brace body via _function_body; also capture arrow expr after =.
            eq = src.find("=", m.start())
            if eq < 0:
                continue
            rest = src[eq + 1 : eq + 1 + 800].lstrip()
            if rest.startswith("$derived"):
                # $derived(expr) or $derived.by(() => …)
                dm = re.match(
                    r"\$derived(?:\.by)?\s*\(",
                    rest,
                )
                if dm:
                    arg = _call_arg(rest, dm.end() - 1)
                    if arg:
                        bodies.append(arg)
            elif rest.startswith("(") or rest.startswith("async"):
                pass  # covered by _function_body when brace form
            else:
                # Arrow/expression form: name = `…` / name = cond ? … : …
                end = rest.find("\n")
                chunk = rest if end < 0 else rest[: max(end, 200)]
                bodies.append(chunk)
    return bodies


def assert_window_title(crate: Path) -> None:
    """#129: native title Interlace | Ada — Interlace | Search — Interlace.

    Tauri window setTitle (getCurrentWindow from @tauri-apps/api/window). React
    to view + selected person display name. Setup/booting/no-archive stay
    bare Interlace. Never put message body/snippet into the title. Not dock
    badge counts.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#129: App.svelte required (window title follows view + selected person)")
    app = app_path.read_text()
    logic = _title_path_sources(crate)
    cleaned = _without_comments(app + "\n" + logic)
    conf_path = crate / "tauri.conf.json"
    conf = conf_path.read_text() if conf_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    pkg = (crate / "package.json").read_text() if (crate / "package.json").is_file() else ""

    # 1) Dependency + Tauri 2 window API import + setTitle call.
    if "@tauri-apps/api" not in pkg:
        fail("#129: @tauri-apps/api must remain a dependency (window setTitle)")
    if not _WINDOW_API_IMPORT.search(cleaned) and not re.search(
        r"@tauri-apps/api/window",
        cleaned,
    ):
        fail(
            "#129: import getCurrentWindow (or Window) from @tauri-apps/api/window "
            "— native title uses the Tauri window API, not document.title alone"
        )
    if not _GET_CURRENT_WINDOW.search(cleaned) and not re.search(
        r"\bgetCurrent\s*\(\s*\)"
        r"|\bWindow\s*\.\s*getByLabel\b"
        r"|\bappWindow\b",
        cleaned,
    ):
        fail(
            "#129: must obtain the current Tauri window "
            "(getCurrentWindow() or equivalent) before setTitle"
        )
    if not _SET_TITLE_CALL.search(cleaned):
        fail(
            "#129: App (or a small helper) must call setTitle(…) so Cmd-tab "
            "shows who you are looking at — static tauri.conf.json title is not enough"
        )

    # 2) Title format strings / builders: base Interlace; person; Search; other views.
    title_args = _collect_set_title_args(cleaned)
    helper_bodies = _title_helper_bodies(cleaned)
    title_surface = "\n".join(title_args + helper_bodies)
    if not title_surface.strip():
        title_surface = cleaned  # fall back: formats may live in open code near setTitle

    # Bare / default Interlace (setup, booting, people with no selection).
    # Scope to setTitle args / title helpers — App chrome already says "Interlace".
    title_path_blob = "\n".join(title_args + helper_bodies)
    if not title_path_blob.strip():
        # Inline setTitle regions only (not whole App header copy).
        title_path_blob = "\n".join(
            cleaned[max(0, m.start() - 500) : m.end() + 300]
            for m in _SET_TITLE_CALL.finditer(cleaned)
        )
    has_bare = bool(
        re.search(
            r"("
            r"setTitle\s*\(\s*[\"']Interlace[\"']\s*\)"
            r"|return\s+[\"']Interlace[\"']"
            r"|:\s*[\"']Interlace[\"']"
            r"|\?\s*[\"']Interlace[\"']"
            r"|\|\|\s*[\"']Interlace[\"']"
            r"|=\s*[\"']Interlace[\"']"
            r"|[\"']Interlace[\"']\s*;"
            r")",
            title_path_blob + "\n" + "\n".join(helper_bodies),
        )
    )
    # Constant used only by the title path: const APP_TITLE = "Interlace" near setTitle.
    if not has_bare:
        for m in re.finditer(
            r"(?:const|let|var)\s+\w+\s*=\s*[\"']Interlace[\"']",
            cleaned,
        ):
            window = cleaned[max(0, m.start() - 200) : m.end() + 400]
            if _SET_TITLE_CALL.search(window) or any(n in window for n in _TITLE_HELPER_NAMES):
                has_bare = True
                break
    if not has_bare:
        fail(
            "#129: default/base native title must be bare Interlace "
            "(setup, booting, no archive, People with no person selected)"
        )

    # Person selected: {name} — Interlace (placeholder names; use personTitle / display_name).
    person_name_tok = (
        r"(?:personTitle|display_name|displayName|personName|selectedName|"
        r"selectedPersonName|openPersonName)"
    )
    person_in_title = bool(
        re.search(
            rf"("
            rf"{person_name_tok}\b[^;\n]{{0,120}}{_TITLE_SEP}[^;\n]{{0,40}}Interlace"
            rf"|`\$\{{{person_name_tok}[^}}]{{0,40}}\}}\s*{_TITLE_SEP}\s*Interlace`"
            rf"|{person_name_tok}\s*\+\s*[\"']\s*{_TITLE_SEP}\s*Interlace"
            rf"|[\"']\s*{_TITLE_SEP}\s*Interlace[\"']\s*\+\s*{person_name_tok}"
            rf")",
            title_surface + "\n" + cleaned,
        )
    )
    if not person_in_title:
        fail(
            "#129: with a person selected, native title must be "
            "`{display_name} — Interlace` (em dash preferred; personTitle / display_name, "
            "not a raw person id)"
        )

    # Search tab (and other chrome tabs when present).
    def _literal_view_title(label: str) -> bool:
        """True if the fixed `{Label} — Interlace` string (or concat) appears."""
        return bool(
            re.search(
                rf"[\"'`]{re.escape(label)}\s*{_TITLE_SEP}\s*Interlace[\"'`]"
                rf"|[\"'`]{re.escape(label)}[\"'`]\s*\+\s*[\"']\s*{_TITLE_SEP}\s*Interlace"
                rf"|[\"']\s*{_TITLE_SEP}\s*Interlace[\"']\s*\+\s*[\"'`]{re.escape(label)}",
                title_surface + "\n" + cleaned,
            )
        )

    def _mapped_view_title(label: str) -> bool:
        """True if view token maps to Label and a View — Interlace builder exists."""
        view_token = label.lower()
        # Prefer title helper / setTitle args — not the whole App (platform chips
        # already use charAt().toUpperCase for WhatsApp/Gmail labels).
        map_surface = title_surface if title_surface.strip() and title_surface != cleaned else ""
        if not map_surface:
            # Narrow to regions that mention setTitle or a title helper name.
            chunks: list[str] = []
            for m in _SET_TITLE_CALL.finditer(cleaned):
                chunks.append(cleaned[max(0, m.start() - 600) : m.end() + 400])
            for name in _TITLE_HELPER_NAMES:
                body = _function_body(cleaned, name)
                if body:
                    chunks.append(body)
                for dm in re.finditer(
                    rf"(?:const|let|var)\s+{re.escape(name)}\b",
                    cleaned,
                ):
                    chunks.append(cleaned[dm.start() : dm.start() + 900])
            map_surface = "\n".join(chunks) if chunks else cleaned
        has_sep_builder = bool(
            re.search(rf"{_TITLE_SEP}\s*Interlace", map_surface + "\n" + title_surface)
        )
        # Explicit map entry: search: "Search" / case "search": return "Search" …
        explicit = bool(
            re.search(
                rf"("
                rf"(?:case\s+[\"']{view_token}[\"']|[\"']{view_token}[\"']\s*:)\s*"
                rf"[^;\n]{{0,100}}[\"']{re.escape(label)}[\"']"
                rf"|[\"']{view_token}[\"']\s*[^\n]{{0,40}}[\"']{re.escape(label)}[\"']"
                rf")",
                map_surface + "\n" + title_surface,
                re.I,
            )
        )
        # Capitalizer only counts when it appears in the title path and reads `view`.
        capitalizer = bool(
            re.search(
                r"("
                r"charAt\s*\(\s*0\s*\)\s*\.\s*toUpperCase"
                r"|\.toUpperCase\s*\(\s*\)\s*\+\s*\w+\.slice"
                r"|capitalize\s*\(\s*view"
                r"|titleCase\s*\(\s*view"
                r"|viewLabel"
                r"|VIEW_TITLE"
                r"|viewTitles"
                r")",
                map_surface,
                re.I,
            )
        ) and bool(re.search(r"\bview\b", map_surface)) and has_sep_builder
        return has_sep_builder and (explicit or bool(capitalizer))

    if not _literal_view_title("Search") and not _mapped_view_title("Search"):
        fail(
            "#129: Search tab native title must be `Search — Interlace` "
            "(Cmd-tab must show the open view)"
        )

    for label in ("Review", "Import", "Doctor"):
        # Soft: if the view enum still has the tab, title path must cover it.
        view_token = label.lower()
        if re.search(rf"[\"']{view_token}[\"']", app) or re.search(
            rf"view\s*===?\s*[\"']{view_token}[\"']",
            cleaned,
        ):
            if not _literal_view_title(label) and not _mapped_view_title(label):
                fail(
                    f"#129: {label} tab native title must be `{label} — Interlace` "
                    f"(same View — Interlace pattern as Search)"
                )

    # People with no selection stays Interlace (not forced "People — Interlace"
    # unless they also keep bare Interlace as default — issue prefers bare).
    # If they emit "People — Interlace" that is OK only alongside person + Search forms.

    # 3) React to view + selected person (Svelte 5 $effect or equivalent).
    # Require an $effect (or title-derived) path that actually calls setTitle / a
    # title helper — mere presence of unrelated $effect + view state is not enough.
    effect_ok = False
    for m in re.finditer(r"\$effect\s*\(", cleaned):
        arg = _call_arg(cleaned, m.end() - 1)
        if not arg:
            continue
        uses_helper = bool(
            any(n in arg for n in _TITLE_HELPER_NAMES)
            or re.search(r"\b(?:windowTitle|nativeTitle|appTitle|syncWindowTitle)\b", arg)
        )
        calls_set = bool(_SET_TITLE_CALL.search(arg))
        if not (calls_set or uses_helper):
            continue
        # Inline effect: must read view and person name.
        reads_view = bool(re.search(r"\bview\b", arg))
        reads_person = bool(
            re.search(r"\b(personTitle|display_name|selectedId|selectedPerson)\b", arg)
        )
        # $effect(() => setTitle(windowTitle)) — helper encodes view+person (format checks).
        if uses_helper and calls_set:
            effect_ok = True
            break
        if uses_helper and not calls_set:
            # syncWindowTitle() inside effect — helper body must call setTitle (checked via names).
            effect_ok = True
            break
        if calls_set and reads_view and reads_person:
            effect_ok = True
            break
    # $derived windowTitle that depends on view + person, applied somewhere with setTitle.
    derived_bodies = _title_helper_bodies(cleaned)
    derived_tracks = any(
        re.search(r"\bview\b", b)
        and re.search(r"\b(personTitle|display_name|selectedId)\b", b)
        for b in derived_bodies
    )
    has_derived_name = bool(
        re.search(
            r"(?:const|let)\s+(?:windowTitle|nativeTitle|appTitle)\s*=\s*\$derived",
            cleaned,
        )
    )
    if not effect_ok and not (has_derived_name and derived_tracks and _SET_TITLE_CALL.search(cleaned)):
        # Last resort: setTitle call site closed over both deps (same function / effect region).
        near_both = False
        for m in _SET_TITLE_CALL.finditer(cleaned):
            window = cleaned[max(0, m.start() - 500) : m.end() + 240]
            if re.search(r"\bview\b", window) and re.search(
                r"\b(personTitle|display_name|selectedId)\b",
                window,
            ):
                near_both = True
                break
        if not near_both:
            fail(
                "#129: setTitle must react to view + selected person name changes "
                "($effect reading view / personTitle and calling setTitle, "
                "or a $derived windowTitle applied via setTitle)"
            )

    # 4) Ban message body / snippet / query string in the title path.
    leak_surfaces = title_args + helper_bodies
    if not leak_surfaces:
        # Scan ~200 chars around each setTitle for body fields.
        for m in _SET_TITLE_CALL.finditer(cleaned):
            leak_surfaces.append(cleaned[max(0, m.start() - 120) : m.end() + 200])
    for chunk in leak_surfaces:
        if _TITLE_BODY_LEAK.search(chunk):
            fail(
                "#129: never put message body / snippet / body_text into setTitle "
                "(Cmd-tab shows person or view name only — not chat text)"
            )
    # Filter / search query must not become the window title either.
    for chunk in title_args:
        if re.search(r"\b(?:filter|query|q|searchQuery)\b", chunk) and not re.search(
            r"Search\s*(?:—|–|---| - )\s*Interlace",
            chunk,
        ):
            # Only fail if the arg interpolates the query, not the word Search.
            if re.search(
                r"(\$\{[^}]*(?:filter|query|searchQuery)|(?:filter|query|searchQuery)\s*\+)",
                chunk,
            ):
                fail(
                    "#129: do not put the search query string in the native title "
                    "(fixed `Search — Interlace`, not the typed query)"
                )

    # 5) Not in scope: dock badge counts.
    if _DOCK_BADGE_API.search(cleaned):
        fail(
            "#129: do not set dock badge counts "
            "(out of scope — native title only, not setBadgeCount / badge APIs)"
        )

    # 6) Static conf title remains a sensible default (Interlace).
    if conf and not re.search(r"[\"']title[\"']\s*:\s*[\"']Interlace[\"']", conf):
        fail(
            '#129: tauri.conf.json default window title should stay "Interlace" '
            "(runtime setTitle overrides per view/person)"
        )

    # 7) User-visible: one line in docs/user/app.md.
    if not re.search(
        r"("
        r"window title"
        r"|native title"
        r"|Cmd-?tab"
        r"|title bar"
        r"|title follows"
        r")",
        dtxt,
        re.I,
    ):
        fail(
            "#129: docs/user/app.md must mention the native window title "
            "(follows open person / view — e.g. Ada — Interlace)"
        )


def assert_virtualized_timeline(crate: Path) -> None:
    """#120: window person timeline (visible + overscan); keep j/k + Load older.

    Acceptance: synthetic 10k DM does not lock the window — only visible + overscan
    rows (and needed day headings) mount. Bodies still text nodes.
    Static gate: fail naive full {#each dayGroups}→{#each group.rows} without a
    window. No FPS assertions in CI (dogfood measures scroll).
    Not: 10M in one view, lazy-decode every photo.
    """
    app = (crate / "web" / "App.svelte").read_text()
    logic = _web_logic(crate)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    whole = app + "\n" + logic
    cleaned = _without_comments(whole)
    markup = _svelte_markup(app)
    # Prefer person-timeline pane if present.
    pt = markup.find("person-timeline")
    if pt >= 0:
        timeline_markup = markup[pt:]
    else:
        timeline_markup = markup
    block = _timeline_block(crate)

    # 1) Reject naive full double-each over dayGroups/rows (current App.svelte).
    # Prefer this message as the pre-impl red gate so the fix target is obvious.
    if _naive_full_timeline_mount(timeline_markup, cleaned):
        fail(
            "#120: do not always mount every filtered row "
            "({#each dayGroups} → {#each group.rows} over the full list, or "
            "{#each timeline|filteredTimeline} without a window). "
            "Window to visible + overscan only so a synthetic 10k DM stays scrollable"
        )

    # 2) Virtualization / windowing signal must exist (overscan, virtual list, …).
    if not _VIRT_SIGNAL.search(cleaned) and not _VIRT_SIGNAL.search(blob):
        fail(
            "#120: person timeline must window the list "
            "(only visible + overscan rows in the DOM — overscan / virtual list / "
            "visibleRange / startIndex+endIndex / windowed rows; "
            "do not always mount every filtered bubble)"
        )

    # 3) Positive: render path must each a windowed list (or VirtualList).
    if not _has_windowed_render_path(timeline_markup, cleaned):
        fail(
            "#120: person timeline render path must iterate a windowed list "
            "(windowed/visible/virtual/rendered rows or groups, or a list derived "
            "with overscan/slice/startIndex — not the full filtered set)"
        )

    # 4) Keep Load older (#113) — still at the list, not dropped by virtualization.
    if not _LOAD_OLDER.search(markup) and not _LOAD_OLDER.search(app):
        fail("#120: keep Load older when virtualizing (do not regress #113)")

    # 5) Keep j/k on visible (filtered) indices (#113 / #116).
    if not _JK_KEY.search(cleaned) and not _VISIBLE_KIND_JK.search(cleaned):
        fail(
            "#120: keep j/k walking visible timeline rows "
            "(visibleTlIndices / j|k handlers — do not regress #113/#116)"
        )

    # 6) Bodies still text nodes — no {@html} / innerHTML of message body.
    body_surface = block + "\n" + timeline_markup
    if _HTML_BODY.search(body_surface) or _BODY_INNER_HTML.search(body_surface):
        # Allow innerHTML only outside body bindings (e.g. unrelated); still forbid {@html}.
        if _HTML_BODY.search(body_surface):
            fail(
                "#120: bodies still text nodes — no {@html} of the message body "
                "(keep whitespace-pre-wrap / plain text bindings)"
            )
        # innerHTML near body_text / displayBody is the product footgun.
        if re.search(
            r"(?:body_text|displayBody|message\.body|row\.body)[\s\S]{0,120}\.innerHTML\s*="
            r"|\.innerHTML\s*=[\s\S]{0,120}(?:body_text|displayBody)",
            body_surface,
            re.I,
        ):
            fail(
                "#120: bodies still text nodes — no innerHTML of the message body"
            )

    # 7) Not in scope: 10M-in-one-view / lazy-decode-every-photo (product claims).
    scope_src = _without_comments(blob)
    # Ignore this gate file and issue notes if they ever land under web/ (they should not).
    if _SCOPE_10M.search(scope_src):
        fail(
            "#120: not in scope — do not claim or build 10M messages in one view "
            "(window the list for 10k-class DMs only)"
        )
    if _SCOPE_LAZY_EVERY_PHOTO.search(scope_src):
        fail(
            "#120: not in scope — lazy-decode every photo / CAS is a separate concern, "
            "not part of timeline windowing"
        )


# #130 — native macOS menu (About/Quit, File Open+Import, View tabs). No updater.
_TAURI_MENU_API = re.compile(
    r"("
    r"tauri::menu::"
    r"|MenuBuilder"
    r"|SubmenuBuilder"
    r"|MenuItemBuilder"
    r"|PredefinedMenuItem"
    r"|CheckMenuItemBuilder"
    r"|@tauri-apps/api/menu"
    r")",
)
_MENU_ATTACH = re.compile(
    r"("
    r"\.menu\s*\("
    r"|\.set_menu\s*\("
    r"|\bset_menu\s*\("
    r"|\bsetMenu\s*\("
    r"|\bsetAsAppMenu\s*\("
    r"|\bsetAsWindowMenu\s*\("
    r")",
)
_ABOUT_ITEM = re.compile(
    r"("
    r"PredefinedMenuItem::about"
    r"|\.about\s*\("
    r"|item\s*:\s*[\"']About[\"']"
    r"|[\"']About(?: Interlace)?[\"']"
    r")",
)
_QUIT_ITEM = re.compile(
    r"("
    r"PredefinedMenuItem::quit"
    r"|\.quit\s*\("
    r"|item\s*:\s*[\"']Quit[\"']"
    r"|[\"']Quit(?: Interlace)?[\"']"
    r")",
)
_FILE_SUBMENU = re.compile(r"[\"']File[\"']")
_VIEW_SUBMENU = re.compile(r"[\"']View[\"']")
_OPEN_ITEM = re.compile(
    r"[\"']("
    r"Open archive"
    r"|Open existing(?:…|\.\.\.)?"
    r"|Open(?:…|\.\.\.)?"
    r"|open-archive"
    r"|open_archive"
    r"|file-open"
    r"|menu-open"
    r")[\"']",
    re.I,
)
_IMPORT_ITEM = re.compile(
    r"[\"']("
    r"Import(?:…|\.\.\.)?"
    r"|file-import"
    r"|menu-import"
    r"|import-archive"
    r")[\"']",
)
_CHECK_UPDATES_ITEM = re.compile(
    r"[\"']Check for [Uu]pdates?[\"']"
    r"|PredefinedMenuItem::check_for_updates"
    r"|tauri_plugin_updater"
    r"|plugin-updater"
    r"|UpdaterExt",
)
_PREFERENCES_ITEM = re.compile(
    r"("
    r"PredefinedMenuItem::preferences"
    r"|[\"']Preferences(?:…|\.\.\.)?[\"']"
    r"|[\"']Settings(?:…|\.\.\.)?[\"']"
    r"|PreferencesWindow"
    r"|open_preferences"
    r")",
)
_ICLOUD_MENU_ITEM = re.compile(
    r"[\"'][^\"']*iCloud[^\"']*[\"']",
    re.I,
)
_ABOUT_ANCHOR = re.compile(
    r"("
    r"AboutMetadata"
    r"|PredefinedMenuItem::about"
    r"|\.about\s*\("
    r"|[\"']About(?: Interlace)?[\"']"
    r"|(?:const|static|let)\s+ABOUT\w*"
    r")",
)
_MENU_HANDLER_NAMES = (
    "on_menu_event",
    "handle_menu_event",
    "handle_menu",
    "menu_event",
    "applyMenu",
    "onMenu",
    "onMenuEvent",
    "handleMenu",
)
_LISTEN_CALL = re.compile(
    r"\b(?:listen|once|onMenuEvent)\s*\(",
)
_VIEW_MENU_TOKENS = ("people", "search", "review", "doctor")
_ABOUT_OFFLINE = re.compile(r"\boffline\b", re.I)
_ABOUT_NOT_ENCRYPTED = re.compile(r"not encrypted at rest", re.I)
_ABOUT_FILEVAULT = re.compile(r"\bFileVault\b")
_DOCS_MENU = re.compile(
    r"("
    r"native menu"
    r"|menu bar"
    r"|File menu"
    r"|macOS menu"
    r"|Open archive"
    r")",
    re.I,
)


def _tauri_rust_sources(crate: Path) -> list[Path]:
    src = crate / "src"
    if not src.is_dir():
        return []
    return [p for p in sorted(src.rglob("*.rs")) if p.is_file()]


def _tauri_rust_blob(crate: Path) -> str:
    return "\n".join(p.read_text() for p in _tauri_rust_sources(crate))


def _menu_web_blob(crate: Path) -> str:
    """Web sources that build a Tauri menu (not the in-window nav / bits-ui menus)."""
    parts: list[str] = []
    web = crate / "web"
    if not web.is_dir():
        return ""
    for p in sorted(web.rglob("*")):
        if p.suffix not in {".svelte", ".ts", ".js"} or "node_modules" in p.parts:
            continue
        text = p.read_text()
        if (
            "@tauri-apps/api/menu" in text
            or "PredefinedMenuItem" in text
            or "MenuItem.new" in text
            or "Menu.new" in text
        ):
            parts.append(text)
    return "\n".join(parts)


def _on_menu_event_bodies(src: str) -> list[str]:
    bodies: list[str] = []
    for m in re.finditer(r"\.on_menu_event\s*\(", src):
        arg = _call_arg(src, m.end() - 1)
        if arg:
            bodies.append(arg)
    for name in _MENU_HANDLER_NAMES:
        body = _function_body(src, name)
        if body:
            bodies.append(body)
    return bodies


def _listen_bodies(src: str) -> list[str]:
    bodies: list[str] = []
    for m in _LISTEN_CALL.finditer(src):
        open_paren = src.find("(", m.start())
        if open_paren < 0:
            continue
        arg = _call_arg(src, open_paren)
        if arg:
            bodies.append(arg)
    return bodies


def _menu_handler_surface(rust: str, web: str) -> str:
    """Rust on_menu_event + frontend listen / menu-handler bodies (and one callee)."""
    chunks = _on_menu_event_bodies(rust) + _listen_bodies(web)
    seen = set(_MENU_HANDLER_NAMES)
    extra: list[str] = []
    blob = "\n".join(chunks)
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", blob):
        name = m.group(1)
        if name in seen or name in _SCROLL_HELPER_SKIP:
            continue
        seen.add(name)
        body = _function_body(web, name) or _function_body(rust, name)
        if body:
            extra.append(body)
    return "\n".join(chunks + extra)


def _about_copy_surface(rust: str, web_menu: str) -> str:
    chunks: list[str] = []
    for src in (rust, web_menu):
        if not src:
            continue
        for m in _ABOUT_ANCHOR.finditer(src):
            chunks.append(src[max(0, m.start() - 200) : m.end() + 900])
    return "\n".join(chunks)


def _quoted_view_token(blob: str, token: str) -> bool:
    return bool(
        re.search(
            rf"("
            rf"view\s*=\s*[\"']{token}[\"']"
            rf"|[\"'](?:view-|menu-)?{token}[\"']"
            rf")",
            blob,
        )
    )


def assert_macos_menu(crate: Path) -> None:
    """#130: native macOS menu — About/Quit, File Open+Import, View tabs; no updater."""
    rust = _tauri_rust_blob(crate)
    web_all = _web_logic(crate)
    web_menu = _menu_web_blob(crate)
    menu_src = rust + "\n" + web_menu
    app_path = crate / "web" / "App.svelte"
    app = app_path.read_text() if app_path.is_file() else ""
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    deny_path = crate / "deny.toml"
    deny = deny_path.read_text() if deny_path.is_file() else ""
    docs_app = repo_root() / "docs" / "user" / "app.md"
    docs_tauri = repo_root() / "docs" / "hacking" / "tauri.md"
    dtxt = (docs_app.read_text() if docs_app.is_file() else "") + "\n" + (
        docs_tauri.read_text() if docs_tauri.is_file() else ""
    )
    caps_path = crate / "capabilities" / "default.json"
    caps = caps_path.read_text() if caps_path.is_file() else ""

    # 1) Native Tauri menu construction (not the default app menu, not HTML nav).
    if not _TAURI_MENU_API.search(menu_src):
        fail(
            "#130: native macOS menu must be built with Tauri Menu / MenuBuilder / "
            "PredefinedMenuItem (or @tauri-apps/api/menu), not the default app menu alone"
        )

    if not _MENU_ATTACH.search(rust) and not _MENU_ATTACH.search(web_menu):
        fail(
            "#130: the constructed menu must be attached to the app "
            "(.menu(...) / set_menu / setMenu) — building items and never installing "
            "them leaves the default macOS menu"
        )

    if "@tauri-apps/api/menu" in web_menu and "core:menu" not in caps:
        fail(
            "#130: JS @tauri-apps/api/menu needs a core:menu capability "
            "(or build the menu in Rust)"
        )

    # 2) App menu: About + Quit (predefined preferred; custom About Interlace / Quit OK).
    if not _ABOUT_ITEM.search(menu_src):
        fail(
            "#130: app menu must include About "
            "(PredefinedMenuItem::about / About Interlace)"
        )
    if not _QUIT_ITEM.search(menu_src):
        fail(
            "#130: app menu must include native Quit "
            "(PredefinedMenuItem::quit — not a custom network-y exit)"
        )

    # 3) File: Open archive + Import.
    if not _FILE_SUBMENU.search(menu_src):
        fail('#130: File submenu required (Open archive + Import)')
    if not _OPEN_ITEM.search(menu_src):
        fail(
            "#130: File menu must include Open archive "
            "(same folder picker as the in-window Open existing… button)"
        )
    if not _IMPORT_ITEM.search(menu_src):
        fail("#130: File menu must include Import")

    # 4) View: People, Search, Review, Doctor (Import may live under File only).
    if not _VIEW_SUBMENU.search(menu_src):
        fail("#130: View submenu required (People, Search, Review, Doctor)")
    for label in ("People", "Search", "Review", "Doctor"):
        if not re.search(rf"[\"']{label}[\"']", menu_src):
            fail(
                f"#130: View menu must include {label} "
                "(same view token as the in-window nav buttons)"
            )

    # 5) About copy: offline + not encrypted at rest + FileVault (About surface, not Doctor).
    about_src = _about_copy_surface(rust, web_menu)
    if not about_src.strip():
        fail(
            "#130: About copy must live on the About item / AboutMetadata "
            "(offline, not encrypted at rest, FileVault — same honesty as Doctor)"
        )
    if not _ABOUT_OFFLINE.search(about_src):
        fail("#130: About copy must say the app is offline")
    if not _ABOUT_NOT_ENCRYPTED.search(about_src):
        fail("#130: About copy must say not encrypted at rest")
    if not _ABOUT_FILEVAULT.search(about_src):
        fail("#130: About copy must mention FileVault")
    if re.search(r"https?://", about_src):
        fail(
            "#130: About must stay offline — no website / http(s) URL on the About item"
        )

    # 6) Open uses the same picker path (pick_folder / openPicker), not a remote open.
    handlers = _menu_handler_surface(rust, web_all)
    if not handlers.strip():
        fail(
            "#130: menu Open must be wired (on_menu_event and/or a frontend listen) "
            "to the existing folder picker — pick_folder / openPicker"
        )
    open_wired = bool(
        re.search(r"\bpick_folder\b", handlers)
        or re.search(r"\bopenPicker\b", handlers)
        or re.search(r"\bpickFolder\b", handlers)
    )
    if not open_wired:
        fail(
            "#130: menu Open must call the same folder picker as the UI button "
            "(openPicker / pickFolder / pick_folder), not a new remote/URL open"
        )
    if re.search(r"https?://", handlers) or re.search(
        r"\b(?:webbrowser|open::that|opener::)\b", handlers
    ):
        fail("#130: menu handlers must not open a remote URL")

    # 7) Import: same Import-tab picker, or switch to Import + existing flow.
    import_wired = bool(
        re.search(r"\bpick_import_path\b", handlers)
        or re.search(r"\bpickImportPath\b", handlers)
        or re.search(r"view\s*=\s*[\"']import[\"']", handlers)
        or re.search(r"[\"'](?:view-|menu-)?import[\"']", handlers)
    )
    if not import_wired:
        fail(
            "#130: menu Import must use pick_import_path / pickImportPath "
            "or switch view to import (existing Import tab flow)"
        )

    # 8) View items set the same `view` tokens as the nav buttons.
    if not re.search(r"\bview\s*=", handlers) and not any(
        _quoted_view_token(handlers, tok) for tok in _VIEW_MENU_TOKENS
    ):
        fail(
            "#130: View menu items must set `view` the same as the nav buttons "
            "(people / search / review / doctor) via on_menu_event emit + listen"
        )
    for tok in _VIEW_MENU_TOKENS:
        if not _quoted_view_token(handlers, tok):
            fail(
                f"#130: View menu must switch to {tok} "
                "(same view token as the in-window nav)"
            )

    # 9) Bans: Check for Updates, updater plugin, Preferences window, iCloud menu.
    if _CHECK_UPDATES_ITEM.search(menu_src) or _CHECK_UPDATES_ITEM.search(handlers):
        fail("#130: no Check for Updates menu item (and no updater plugin)")
    if "tauri-plugin-updater" in toml:
        fail("#130: tauri-plugin-updater must not be a dependency")
    if "tauri-plugin-updater" not in deny:
        fail(
            "#130: crates/interlace-tauri/deny.toml must keep banning "
            "tauri-plugin-updater"
        )
    if _PREFERENCES_ITEM.search(menu_src):
        fail("#130: no Preferences / Settings window or menu item (out of scope)")
    if _ICLOUD_MENU_ITEM.search(menu_src):
        fail("#130: no iCloud / iCloud Drive menu item (out of scope)")

    # 10) User-visible: one line in docs/user/app.md and/or docs/hacking/tauri.md.
    if not _DOCS_MENU.search(dtxt):
        fail(
            "#130: docs/user/app.md and/or docs/hacking/tauri.md must mention "
            "the native menu (File → Open archive; no Check for Updates)"
        )

    # Keep using the existing in-window picker — do not drop openPicker.
    if "openPicker" not in app and "pickFolder" not in web_all:
        fail(
            "#130: keep the in-window openPicker / pickFolder path "
            "(menu Open must share it, not replace it with a second picker)"
        )


# #131 — UI chrome locale packs (en + tr). Not WA parser packs, not message bodies.
_CHROME_PACK_SUFFIXES = {".json", ".ts", ".toml"}
_CHROME_PACK_DIR_HINTS = frozenset(
    {"locale", "locales", "i18n", "l10n", "chrome", "messages", "strings"}
)
_CHROME_PACK_FILE_HINTS = ("chrome", "i18n", "l10n", "messages", "strings", "locale")
_CHROME_HELPER_NAMES = (
    "t",
    "tt",
    "i18n",
    "i18nT",
    "chromeT",
    "chromeText",
    "chromeString",
    "uiText",
    "uiString",
    "msg",
    "translate",
    "tChrome",
    "chromeMsg",
)
_CHROME_PACK_NS = (
    "chrome",
    "i18n",
    "strings",
    "messages",
    "ui",
    "m",
    "pack",
    "packs",
    "c",
)
_WA_PARSER_KEYS = frozenset(
    {
        "id",
        "family_hints",
        "you_tokens",
        "date_time_patterns",
        "media_omitted",
        "file_attached_pattern",
        "file_attached_alt",
        "forwarded_tokens",
        "title_prefixes_dm",
        "title_prefixes_group",
        "system_created_group",
        "system_added",
        "system_subject",
        "system_encryption",
        "encryption_banner_startswith",
    }
)
_WA_UI_BAN = ("Arşiv aç", "Open existing", "Open an archive")
_CHROME_NO_TRANSLATE_FIELDS = (
    "body_text",
    "bodyText",
    "snippet",
    "displayBody",
    "searchBody",
    "display_name",
    "displayName",
    "personTitle",
    "preview",
    "sample",
    "sample_body",
    "sampleBody",
)
_EN_EMPTY_TITLES = (
    "No people yet",
    "Select a person",
    "No doctor issues",
    "Nothing to review",
    "Type a query",
    "No hits",
)
_OS_LOCALE_READ = re.compile(
    r"("
    r"navigator\.language"
    r"|navigator\.languages"
    r"|Intl\.DateTimeFormat\s*\("
    r"|resolvedOptions\s*\(\s*\)\s*\.\s*locale"
    r"|@tauri-apps/plugin-os"
    r"|\bosLocale\b"
    r"|\bgetLocale\s*\("
    r"|\blocaleIdentifier\b"
    r")",
)
_TR_STAR_PICK = re.compile(
    r"("
    r"startsWith\s*\(\s*[\"']tr"
    r"|starts_with\s*\(\s*[\"']tr"
    r"|slice\s*\(\s*0\s*,\s*2\s*\)\s*===?\s*[\"']tr[\"']"
    r"|substring\s*\(\s*0\s*,\s*2\s*\)\s*===?\s*[\"']tr[\"']"
    r"|===?\s*[\"']tr[\"']"
    r"|===?\s*[\"']tr-[A-Za-z]{2}[\"']"
    r"|/\^tr/i?"
    r"|match\s*\(\s*/\^tr"
    r")",
)
_EN_DEFAULT_PICK = re.compile(
    r"("
    r":\s*[\"']en[\"']"
    r"|\|\|\s*[\"']en[\"']"
    r"|\?\?\s*[\"']en[\"']"
    r"|else\s+[\"']en[\"']"
    r"|return\s+[\"']en[\"']"
    r"|fallback(?:Locale|Lang|Pack)?\s*[:=]\s*[\"']en[\"']"
    r"|default(?:Locale|Lang|Pack)?\s*[:=]\s*[\"']en[\"']"
    r"|\?\s*[\"']tr[\"']\s*:\s*[\"']en[\"']"
    r")",
)
_CHROME_OVERRIDE_UI = re.compile(
    r"("
    r"\bchromeLocale\b"
    r"|\buiLocale\b"
    r"|\buiLanguage\b"
    r"|\bdisplayLanguage\b"
    r"|[\"']UI language[\"']"
    r"|[\"']Display language[\"']"
    r"|[\"']App language[\"']"
    r"|[\"']Chrome language[\"']"
    r")",
    re.I,
)
_DIR_RTL = re.compile(r"\bdir\s*=\s*[\"']rtl[\"']", re.I)
_CHROME_IMPORT_SPEC = re.compile(
    r"chrome|i18n|l10n|locale|messages|strings|paraglide",
    re.I,
)
_LANG_STEM = re.compile(
    r"(?:^|[._-])(en|tr)(?:[-_][A-Za-z]+)?$",
    re.I,
)


def _looks_like_wa_pack(text: str) -> bool:
    return (
        "you_tokens" in text
        and "media_omitted" in text
        and "file_attached_pattern" in text
    )


def _web_pack_candidates(crate: Path) -> list[Path]:
    web = crate / "web"
    if not web.is_dir():
        return []
    out: list[Path] = []
    for p in sorted(web.rglob("*")):
        if not p.is_file():
            continue
        if "node_modules" in p.parts or "dist" in p.parts:
            continue
        if p.suffix not in _CHROME_PACK_SUFFIXES:
            continue
        if p.name.endswith(".d.ts"):
            continue
        out.append(p)
    return out


def _stem_chrome_lang(path: Path) -> str | None:
    m = _LANG_STEM.search(path.stem)
    if not m:
        return None
    return m.group(1).lower()


def _chrome_file_hinted(path: Path) -> bool:
    name = path.name.lower()
    parent = path.parent.name.lower()
    if parent in _CHROME_PACK_DIR_HINTS:
        return True
    return any(h in name for h in _CHROME_PACK_FILE_HINTS)


def _is_combined_chrome_pack(path: Path, text: str) -> bool:
    if not _chrome_file_hinted(path):
        return False
    if _looks_like_wa_pack(text):
        return False
    has_en = bool(re.search(r"""(?:\ben\b\s*[:=]|["']en["']\s*:)""", text))
    has_tr = bool(re.search(r"""(?:\btr\b\s*[:=]|["']tr["']\s*:)""", text))
    return has_en and has_tr


def _chrome_pack_files(crate: Path) -> tuple[list[Path], list[Path], list[Path]]:
    """Dedicated en files, dedicated tr files, combined en+tr modules under web/."""
    en: list[Path] = []
    tr: list[Path] = []
    combined: list[Path] = []
    for p in _web_pack_candidates(crate):
        text = p.read_text()
        if _looks_like_wa_pack(text):
            continue
        lang = _stem_chrome_lang(p)
        if lang == "en":
            en.append(p)
            continue
        if lang == "tr":
            tr.append(p)
            continue
        if _is_combined_chrome_pack(p, text):
            combined.append(p)
    return en, tr, combined


def _extract_lang_object(text: str, lang: str) -> str:
    for pat in (
        rf"(?:export\s+)?(?:const|let|var)\s+{re.escape(lang)}\s*=\s*\{{",
        rf"[\"']{re.escape(lang)}[\"']\s*:\s*\{{",
        rf"\b{re.escape(lang)}\s*:\s*\{{",
    ):
        m = re.search(pat, text)
        if not m:
            continue
        brace = text.find("{", m.start())
        if brace < 0:
            continue
        end = _match_closer(text, brace)
        if end > brace:
            return text[brace : end + 1]
    m = re.search(rf"^\[{re.escape(lang)}\]\s*$", text, re.M)
    if m:
        rest = text[m.end() :]
        nxt = re.search(r"^\[", rest, re.M)
        return rest[: nxt.start()] if nxt else rest
    return ""


def _chrome_lang_text(crate: Path, lang: str) -> str:
    en, tr, combined = _chrome_pack_files(crate)
    dedicated = en if lang == "en" else tr
    parts = [p.read_text() for p in dedicated]
    for p in combined:
        text = p.read_text()
        extracted = _extract_lang_object(text, lang)
        parts.append(extracted if extracted.strip() else text)
    return "\n".join(parts)


def _chrome_en_text(crate: Path) -> str:
    return _chrome_lang_text(crate, "en")


def _chrome_tr_text(crate: Path) -> str:
    return _chrome_lang_text(crate, "tr")


def _chrome_import_names(logic: str) -> set[str]:
    names: set[str] = set()
    for m in re.finditer(
        r"import\s+(?:type\s+)?(?:(\w+)\s*,\s*)?\{([^}]+)\}\s+from\s+[\"']([^\"']+)[\"']",
        logic,
    ):
        if not _CHROME_IMPORT_SPEC.search(m.group(3)):
            continue
        if m.group(1):
            names.add(m.group(1))
        for part in m.group(2).split(","):
            bit = part.strip()
            if not bit or bit.startswith("type "):
                continue
            names.add(re.split(r"\s+as\s+", bit)[-1].strip())
    for m in re.finditer(
        r"import\s+(\w+)\s+from\s+[\"']([^\"']+)[\"']",
        logic,
    ):
        if _CHROME_IMPORT_SPEC.search(m.group(2)):
            names.add(m.group(1))
    for m in re.finditer(
        r"import\s+\*\s+as\s+(\w+)\s+from\s+[\"']([^\"']+)[\"']",
        logic,
    ):
        if _CHROME_IMPORT_SPEC.search(m.group(2)):
            names.add(m.group(1))
    return {n for n in names if n}


def _chrome_helper_names(logic: str) -> set[str]:
    names = _chrome_import_names(logic)
    for name in _CHROME_HELPER_NAMES:
        if re.search(
            rf"(?:function\s+{re.escape(name)}\s*\("
            rf"|(?:const|let)\s+{re.escape(name)}\s*=\s*(?:async\s*)?(?:function\b|\())",
            logic,
        ):
            names.add(name)
    return names


def _ident_assigned_from_chrome(logic: str, ident: str, helpers: set[str]) -> bool:
    if not ident or ident in {"#if", ":else", "/if", "#each", "/each"}:
        return False
    ns = set(helpers) | set(_CHROME_PACK_NS)
    for m in re.finditer(
        rf"(?:const|let|var)\s+{re.escape(ident)}\s*=",
        logic,
    ):
        window = logic[m.start() : m.start() + 500]
        if any(re.search(rf"\b{re.escape(h)}\s*\(", window) for h in helpers):
            return True
        if any(re.search(rf"\b{re.escape(n)}\.\w+", window) for n in ns):
            return True
    return False


def _markup_uses_chrome_helper(inner: str, helpers: set[str], logic: str = "") -> bool:
    """True if visible copy comes from t()/chrome.x / a derived chrome label."""
    if not inner.strip():
        return False
    ns = set(helpers) | set(_CHROME_PACK_NS)
    for h in helpers:
        if re.search(rf"\b{re.escape(h)}\s*\(", inner):
            return True
        if re.search(rf"\b{re.escape(h)}\.\w+", inner):
            return True
    for n in ns:
        if re.search(rf"\b{re.escape(n)}\.\w+", inner):
            return True
        if re.search(rf"\b{re.escape(n)}\.\w+\s*\(", inner):
            return True
    if re.search(r"\$_\s*\(", inner):
        return True
    for m in re.finditer(r"\{([A-Za-z_]\w*)\}", inner):
        if _ident_assigned_from_chrome(logic, m.group(1), helpers):
            return True
    return False


def _control_inners(src: str, needle: re.Pattern[str], tags: tuple[str, ...] = ("Button", "button")) -> list[str]:
    """Inner HTML of a Button/button whose open tag (or nearby) matches needle.

    Closing tags may split across lines (`</Button\\n>`).
    """
    inners: list[str] = []
    for m in needle.finditer(src):
        before = src[: m.start()]
        open_idx = -1
        tag_found = ""
        for tag in tags:
            idx = before.lower().rfind("<" + tag.lower())
            if idx > open_idx:
                open_idx = idx
                tag_found = tag
        if open_idx < 0 or m.start() - open_idx > 900:
            continue
        gt = src.find(">", open_idx)
        if gt < 0:
            continue
        close_m = re.search(rf"</{re.escape(tag_found)}\s*>", src[gt:], re.I)
        if not close_m:
            continue
        inners.append(src[gt + 1 : gt + close_m.start()])
    return inners


def _nav_block(src: str) -> str:
    m = re.search(r"<nav\b[^>]*>(.*?)</nav>", src, re.S | re.I)
    return m.group(0) if m else ""


def _locale_resolver_surface(src: str) -> str:
    """Windows around OS-locale reads / named resolvers — not pack dictionaries."""
    chunks: list[str] = []
    for m in _OS_LOCALE_READ.finditer(src):
        chunks.append(src[max(0, m.start() - 400) : m.end() + 500])
    for name in (
        "resolveLocale",
        "chromeLocale",
        "pickLocale",
        "detectLocale",
        "localeFromOs",
        "osLang",
        "chromeLang",
        "resolvedLocale",
        "uiLang",
    ):
        body = _function_body(src, name)
        if body:
            chunks.append(body)
        for dm in re.finditer(rf"(?:const|let|var|function)\s+{re.escape(name)}\b", src):
            chunks.append(src[dm.start() : dm.start() + 800])
    return "\n".join(chunks)


def _heading_inners(src: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"<h1\b[^>]*>(.*?)</h1>", src, re.S | re.I)]


def _chrome_helper_on_body(blob: str, helpers: set[str]) -> bool:
    if not helpers:
        return False
    names = "|".join(re.escape(h) for h in sorted(helpers, key=len, reverse=True))
    fields = "|".join(_CHROME_NO_TRANSLATE_FIELDS)
    return bool(
        re.search(
            rf"\b(?:{names})\s*\(\s*(?:[^)]{{0,100}}\.)?(?:{fields})\b",
            blob,
        )
    )


def _toml_top_keys(text: str) -> set[str]:
    return set(re.findall(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", text, re.M))


def _assert_wa_locale_not_chrome(root: Path) -> None:
    """UI chrome must not land in WhatsApp/Gmail parser packs."""
    for rel in (
        Path("crates") / "interlace-fixtures" / "locale",
        Path("crates") / "interlace-core" / "locale",
    ):
        folder = root / rel
        if not folder.is_dir():
            continue
        for p in sorted(folder.iterdir()):
            if not p.is_file():
                continue
            loc = p.relative_to(root)
            if p.suffix != ".toml":
                fail(
                    f"#131: {loc} is not a WA parser pack — "
                    "do not add UI chrome files under interlace-fixtures/locale "
                    "(or core locale copies)"
                )
            text = p.read_text()
            extra = _toml_top_keys(text) - _WA_PARSER_KEYS
            if extra:
                fail(
                    f"#131: do not add UI chrome keys to WA locale pack {loc}: "
                    f"{sorted(extra)} — chrome lives under crates/interlace-tauri/web/"
                )
            for s in _WA_UI_BAN:
                if s in text:
                    fail(
                        f"#131: do not put UI chrome string {s!r} in WA locale pack {loc}"
                    )


def assert_chrome_locale(crate: Path) -> None:
    """#131: en+tr UI chrome packs; OS locale; not bodies; not WA packs.

    Ship chrome strings (nav, setup Open archive, doctor, empty states, backup
    banner, common buttons) as en + tr packs under web/. Resolve from the OS
    locale: tr / tr-TR → tr, everything else → en. Message bodies stay stored.
    English remains the default so existing doctor / empty / backup greps pass.
    """
    root = repo_root()
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#131: App.svelte required (setup Open archive + nav Doctor chrome)")
    app = app_path.read_text()
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    doctor = doctor_path.read_text() if doctor_path.is_file() else ""
    logic = _web_logic(crate)
    cleaned = _without_comments(logic)
    docs = root / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) en + tr chrome packs under web/ (json / ts / toml) — not WA fixture toml.
    en_files, tr_files, combined = _chrome_pack_files(crate)
    if not en_files and not combined:
        fail(
            "#131: English UI chrome pack missing under crates/interlace-tauri/web/ "
            "(en.json / en.ts / en.toml, or a combined chrome/i18n module) — "
            "not interlace-fixtures/locale/*.toml"
        )
    if not tr_files and not combined:
        fail(
            "#131: Turkish UI chrome pack missing under crates/interlace-tauri/web/ "
            "(tr.json / tr.ts / tr.toml, or a combined chrome/i18n module) — "
            "not interlace-fixtures/locale/*.toml"
        )
    en_text = _chrome_en_text(crate)
    tr_text = _chrome_tr_text(crate)
    if not en_text.strip():
        fail("#131: English chrome pack is empty")
    if not tr_text.strip():
        fail("#131: Turkish chrome pack is empty")

    # 2) Resolver follows OS locale; tr* → tr, else en (English default).
    if not _OS_LOCALE_READ.search(cleaned) and not _OS_LOCALE_READ.search(logic):
        fail(
            "#131: chrome locale must follow the OS "
            "(navigator.language / navigator.languages / Intl / Tauri locale) — "
            "not the Import pane WhatsApp/Gmail probe `locale` field"
        )
    resolver = _locale_resolver_surface(cleaned) or _locale_resolver_surface(logic)
    if not _TR_STAR_PICK.search(resolver):
        fail(
            "#131: OS locale tr / tr-TR / tr* must select the tr chrome pack "
            "(startsWith('tr') or equivalent, next to the OS locale read)"
        )
    if not _EN_DEFAULT_PICK.search(resolver):
        fail(
            "#131: every non-tr OS locale must fall back to the en chrome pack "
            "(English is the default so existing fixture/gate copy still passes)"
        )

    # 3) Acceptance strings in the tr pack.
    if "Arşiv aç" not in tr_text:
        fail('#131: tr chrome pack must contain “Arşiv aç” (Open archive / Open existing)')
    if "Doktor" not in tr_text:
        fail('#131: tr chrome pack must contain “Doktor” (Doctor nav + pane title)')

    # 4) English pack keeps the acceptance keys (default / fixtures).
    if not re.search(r"[\"']Doctor[\"']", en_text) and "Doctor" not in en_text:
        fail(
            "#131: en chrome pack must contain “Doctor” "
            "(English default — existing doctor chrome gates stay green)"
        )
    if not re.search(
        r"Open(?: an)? archive|Open existing",
        en_text,
        re.I,
    ):
        fail(
            "#131: en chrome pack must contain “Open archive” / “Open existing” "
            "(English default for setup)"
        )

    # 5) App setup/nav uses the chrome helper — not only hardcoded English.
    helpers = _chrome_helper_names(logic)
    if not helpers and not any(
        re.search(rf"\b{re.escape(n)}\.\w+", logic) for n in _CHROME_PACK_NS
    ):
        fail(
            "#131: App/setup/nav must use a chrome helper "
            "(t / chromeT / i18n / imported chrome pack) — "
            "not only hardcoded English “Open existing…” / “Doctor”"
        )

    open_inners = _control_inners(app, re.compile(r"\bopenPicker\b"))
    if not open_inners:
        open_inners = _control_inners(app, re.compile(r"\bopenPath\b|\bpickFolder\b"))
    if not open_inners:
        fail(
            "#131: setup Open archive / Open existing control missing "
            "(openPicker button must show the chrome string)"
        )
    if not any(_markup_uses_chrome_helper(inner, helpers, logic) for inner in open_inners):
        fail(
            "#131: setup Open archive / Open existing must use the chrome helper "
            "(tr-TR shows “Arşiv aç” — not only hardcoded English on openPicker)"
        )

    nav = _nav_block(app)
    nav_inners = _control_inners(nav or app, re.compile(r"view\s*=\s*[\"']doctor[\"']"))
    if not nav_inners:
        fail(
            "#131: nav Doctor button missing "
            "(in-window nav must use the chrome helper for “Doktor”)"
        )
    if not any(_markup_uses_chrome_helper(inner, helpers, logic) for inner in nav_inners):
        fail(
            "#131: nav Doctor must use the chrome helper "
            "(tr-TR shows “Doktor” — not only hardcoded English)"
        )

    # Doctor pane title (acceptance: nav + pane).
    if doctor:
        doc_headings = _heading_inners(doctor)
        if not doc_headings:
            fail("#131: Doctor pane must keep a title heading (chrome “Doktor” / “Doctor”)")
        if not any(_markup_uses_chrome_helper(inner, helpers, logic) for inner in doc_headings):
            fail(
                "#131: Doctor pane title must use the chrome helper "
                "(not only hardcoded English “Doctor”)"
            )

    # 6) Never translate stored message bodies / snippets / names via the helper.
    body_blob = logic + "\n" + app + "\n" + doctor
    if _chrome_helper_on_body(body_blob, helpers):
        fail(
            "#131: do not pass body_text / snippet / display_name / preview "
            "through the chrome helper — message bodies stay as stored"
        )

    # 7) WA parser packs must not grow UI chrome strings.
    _assert_wa_locale_not_chrome(root)

    # 8) English empty / doctor / backup copy still present (pack or svelte)
    #    so existing English gates keep passing for the default locale.
    svelte_en = app + "\n" + doctor
    for pane_name in ("EmptyState.svelte", "SearchPane.svelte", "ReviewPane.svelte"):
        p = crate / "web" / "lib" / pane_name
        if p.is_file():
            svelte_en += "\n" + p.read_text()
    en_surface = svelte_en + "\n" + en_text
    missing_empty = [s for s in _EN_EMPTY_TITLES if s not in en_surface]
    if len(missing_empty) == len(_EN_EMPTY_TITLES):
        fail(
            "#131: English empty-state copy must remain in the en pack or the panes "
            f"({_EN_EMPTY_TITLES[0]!r}, …) so existing empty-state gates stay English"
        )
    if "Not encrypted at rest" not in en_surface or "FileVault" not in en_surface:
        fail(
            "#131: English doctor / backup honesty copy must remain in the en pack "
            "or Doctor pane (“Not encrypted at rest”, FileVault)"
        )
    if "backup unit" not in en_surface and "data-cloud-warning" not in app:
        fail(
            "#131: English backup / cloud banner copy must remain "
            "(en pack or existing data-cloud-warning banner)"
        )

    # 9) Docs: chrome follows OS language (en/tr); bodies stay as imported.
    if not re.search(
        r"("
        r"OS language"
        r"|OS locale"
        r"|follows (?:the )?OS"
        r"|chrome follows"
        r"|UI chrome.{0,40}(?:language|locale)"
        r"|en(?:glish)?\s*/\s*tr"
        r")",
        dtxt,
        re.I,
    ):
        fail(
            "#131: docs/user/app.md must say chrome follows the OS language (en/tr)"
        )
    if not re.search(
        r"("
        r"message bodies? stay"
        r"|bodies stay as"
        r"|as (?:imported|stored)"
        r"|not (?:translate|translating) (?:message )?bod"
        r"|bodies? (?:are|stay|remain) (?:as )?(?:imported|stored|unchanged)"
        r")",
        dtxt,
        re.I,
    ):
        fail(
            "#131: docs/user/app.md must say message bodies stay as imported / stored"
        )

    # 10) Out of scope: chrome-language override UI, RTL layout.
    if _CHROME_OVERRIDE_UI.search(app) or _CHROME_OVERRIDE_UI.search(logic):
        fail(
            "#131: no chrome-language override / settings UI "
            "(optional later — Import pane WhatsApp locale probe is not chrome)"
        )
    if _DIR_RTL.search(app) or _DIR_RTL.search(logic):
        fail("#131: RTL layout is out of scope")


# #132 — keyboard map (⌘F Search #q from every view, Esc back, ⌘1–5 tabs).
# #208 rewrites Find-on-People: ⌘F no longer focuses #person-filter (`/` still does).
_KEY_F = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']f[\"']"
    r"|[\"']f[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']F[\"']"
    r"|[\"']F[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*\.\s*toLowerCase\s*\(\s*\)\s*===?\s*[\"']f[\"']"
    r"|(?:e\.)?code\s*===?\s*[\"']KeyF[\"']"
    r")",
    re.I,
)
_KEY_SLASH = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']/[\"']"
    r"|[\"']/[\"']\s*===?\s*(?:e\.)?key"
    r")",
)
_KEY_ESC = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']Escape[\"']"
    r"|[\"']Escape[\"']\s*===?\s*(?:e\.)?key"
    r")",
)
_KEY_J = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']j[\"']|[\"']j[\"']\s*===?\s*(?:e\.)?key"
)
_KEY_K = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']k[\"']|[\"']k[\"']\s*===?\s*(?:e\.)?key"
)
_MOD_META = re.compile(r"(?:e\.)?metaKey")
_MOD_CTRL = re.compile(r"(?:e\.)?ctrlKey")
_MOD_EITHER = re.compile(r"(?:e\.)?(?:metaKey|ctrlKey)")
_FOCUS_PERSON_FILTER = re.compile(
    r"("
    r"getElementById\s*\(\s*[\"']person-filter[\"']"
    r"|querySelector\s*\(\s*[\"']#person-filter[\"']"
    r"|#person-filter"
    r")",
)
_FOCUS_SEARCH_Q = re.compile(
    r"("
    r"getElementById\s*\(\s*[\"']q[\"']"
    r"|querySelector\s*\(\s*[\"']#q[\"']"
    r")",
)
_VIEW_PEOPLE_ASSIGN = re.compile(r"\bview\s*=\s*[\"']people[\"']")
_VIEW_SEARCH_ASSIGN = re.compile(r"\bview\s*=\s*[\"']search[\"']")
_INPUT_TAG_GUARD = re.compile(
    r"tagName\s*===?\s*[\"']INPUT[\"']"
    r".{0,160}tagName\s*===?\s*[\"']TEXTAREA[\"']"
    r".{0,160}tagName\s*===?\s*[\"']SELECT[\"']"
    r"|tagName\s*===?\s*[\"']INPUT[\"']"
    r".{0,80}[\"']TEXTAREA[\"']"
    r".{0,80}[\"']SELECT[\"']",
    re.S,
)
_INPUT_BLUR = re.compile(r"\.blur\s*\(\s*\)")
_PREVENT_DEFAULT = re.compile(r"preventDefault\s*\(")
_PEOPLE_ONLY_RETURN = re.compile(
    r"if\s*\(\s*view\s*!==?\s*[\"']people[\"']\s*\)\s*(?:\{\s*)?return\s*;"
)
_DIGIT_KEY = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"'][1-5][\"']"
    r"|(?:e\.)?code\s*===?\s*[\"']Digit[1-5][\"']"
    r"|(?:e\.)?key\s*>=\s*[\"']1[\"']"
    r"|(?:e\.)?key\s*<=\s*[\"']5[\"']"
    r"|Number\s*\(\s*(?:e\.)?key"
    r"|parseInt\s*\(\s*(?:e\.)?key"
    r")"
)
_VIEW_TAB_ORDER = ("people", "search", "review", "import", "doctor")
_VIM_COLON = re.compile(r"(?:e\.)?key\s*===?\s*[\"']:[\"']|[\"']:[\"']\s*===?\s*(?:e\.)?key")
_VIM_COMMAND = re.compile(
    r"("
    r"[\"']:w[\"']"
    r"|[\"']:q[\"']"
    r"|[\"']:wq[\"']"
    r"|\bvimMode\b"
    r"|\bvim-mode\b"
    r"|\bcustomKeybindings\b"
    r")",
    re.I,
)
_ESC_CLOSE_APP = re.compile(
    r"("
    r"getCurrentWindow\s*\(\s*\)\s*\.\s*close\s*\("
    r"|window\s*\.\s*close\s*\("
    r"|app(?:Window)?\s*\.\s*close\s*\("
    r"|app\.exit\s*\("
    r"|process\.exit\s*\("
    r")"
)
_KEYBIND_NAMES = frozenset(
    {
        "keybindings.json",
        "keybindings.toml",
        "key-bindings.json",
        "keymaps.json",
    }
)
_KEYMAP_CALL_SKIP = _SCROLL_HELPER_SKIP | frozenset(
    {
        "preventDefault",
        "stopPropagation",
        "blur",
        "focus",
        "getElementById",
        "querySelector",
        "querySelectorAll",
        "addEventListener",
        "removeEventListener",
        "toLowerCase",
        "toUpperCase",
        "includes",
        "indexOf",
        "startsWith",
        "endsWith",
        "trim",
        "slice",
        "charAt",
        "charCodeAt",
        "fromCharCode",
        "Number",
        "String",
        "Boolean",
        "parseInt",
        "parseFloat",
        "isNaN",
        "ensureTlIndexVisible",
        "nearestVisibleTlIndex",
        "console",
        "Error",
        "Map",
        "Set",
        "Array",
        "Object",
        "JSON",
        "Date",
        "RegExp",
    }
)


def _ts_fn_body(src: str, name: str) -> str:
    """Body of `function name(` / `const name = (` including a TS return type."""
    rx = re.compile(
        rf"(?:async\s+)?function\s+{re.escape(name)}\s*\("
        rf"|(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?:async\s*)?(?:function\s*)?\("
    )
    m = rx.search(src)
    if not m:
        return ""
    open_paren = m.end() - 1
    close_paren = _match_closer(src, open_paren)
    if close_paren < 0:
        return ""
    brace = src.find("{", close_paren)
    if brace < 0:
        return ""
    # Ignore a `{` that belongs to a following function if `=> expr` has no block.
    between = src[close_paren + 1 : brace]
    if "\nfunction" in between or re.search(r"\n\s*(?:const|let|var)\s+\w+", between):
        return ""
    close_b = _match_closer(src, brace)
    if close_b < 0:
        return src[brace + 1 :]
    return src[brace + 1 : close_b]


def _expand_fn_calls(src: str, body: str, depth: int = 2) -> str:
    """Include named callees so ⌘F / tab helpers still count."""
    chunks = [body]
    seen: set[str] = set()

    def walk(blob: str, left: int) -> None:
        for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob):
            if name in seen or name in _KEYMAP_CALL_SKIP:
                continue
            seen.add(name)
            inner = _ts_fn_body(src, name) or _function_body(src, name)
            if not inner:
                continue
            chunks.append(inner)
            if left > 0:
                walk(inner, left - 1)

    walk(body, depth)
    return "\n".join(chunks)


def _app_keydown_body(app: str) -> str:
    """App.svelte window keydown handler (onKey or the listen callback)."""
    m = re.search(
        r"addEventListener\s*\(\s*[\"']keydown[\"']\s*,\s*([A-Za-z_][\w]*)",
        app,
    )
    name = m.group(1) if m else "onKey"
    body = _ts_fn_body(app, name) or _function_body(app, name)
    if body:
        return body
    # Anonymous listener: window.addEventListener("keydown", (e) => { ... })
    anon = re.search(
        r"addEventListener\s*\(\s*[\"']keydown[\"']\s*,\s*(?:async\s*)?\([^)]*\)\s*(?::\s*[^{=]+)?=>\s*\{",
        app,
    )
    if anon:
        open_b = app.find("{", anon.end() - 1)
        if open_b >= 0:
            close_b = _match_closer(app, open_b)
            if close_b > open_b:
                return app[open_b + 1 : close_b]
    return ""


def _split_people_only(body: str) -> tuple[str, str]:
    """Prefix always runs; suffix only runs on People (`view !== "people" return`)."""
    m = _PEOPLE_ONLY_RETURN.search(body)
    if not m:
        return body, ""
    return body[: m.start()], body[m.end() :]


def _input_guard_span(body: str) -> tuple[int, int] | None:
    """Span of the INPUT/TEXTAREA/SELECT early-exit (Esc blur lives here)."""
    m = re.search(r"tagName\s*===?\s*[\"']INPUT[\"']", body)
    if not m:
        return None
    start = body.rfind("if", 0, m.start())
    if start < 0:
        start = m.start()
    brace = body.find("{", m.start())
    if brace < 0:
        ret = body.find("return", m.start())
        return (start, ret + 6 if ret >= 0 else m.end())
    end = _match_closer(body, brace)
    return (start, end if end >= 0 else brace)


def _without_input_guard(body: str) -> str:
    span = _input_guard_span(body)
    if not span:
        return body
    return body[: span[0]] + body[span[1] + 1 :]


def _esc_sets_view_people(src: str, whole: str) -> bool:
    """True if an Escape check outside the input guard assigns view = \"people\"."""
    for m in _KEY_ESC.finditer(src):
        window = src[m.start() : m.end() + 400]
        if _VIEW_PEOPLE_ASSIGN.search(window):
            return True
        for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", window):
            if name in _KEYMAP_CALL_SKIP:
                continue
            inner = _ts_fn_body(whole, name) or _function_body(whole, name)
            if inner and _VIEW_PEOPLE_ASSIGN.search(inner):
                return True
    return False


def _windows_around(src: str, rx: re.Pattern[str], before: int = 280, after: int = 640) -> str:
    return "\n".join(
        src[max(0, m.start() - before) : m.end() + after] for m in rx.finditer(src)
    )


def _has_mod_combo(src: str) -> bool:
    return bool(_MOD_META.search(src) and _MOD_CTRL.search(src))


def _digit_view_map_ok(surface: str) -> bool:
    """True if digit 1..5 map to people/search/review/import/doctor."""
    if not _DIGIT_KEY.search(surface):
        return False
    # Ordered array / tuple used as the tab list.
    joined = r"[\"']people[\"']\s*,\s*[\"']search[\"']\s*,\s*[\"']review[\"']\s*,\s*[\"']import[\"']\s*,\s*[\"']doctor[\"']"
    if re.search(joined, surface):
        return True
    # Object / switch / per-key assigns.
    pairs = (
        (r"[\"']1[\"']|Digit1", "people"),
        (r"[\"']2[\"']|Digit2", "search"),
        (r"[\"']3[\"']|Digit3", "review"),
        (r"[\"']4[\"']|Digit4", "import"),
        (r"[\"']5[\"']|Digit5", "doctor"),
    )
    for digit_rx, view in pairs:
        if not re.search(
            rf"(?:{digit_rx})[\s\S]{{0,220}}[\"']{view}[\"']"
            rf"|[\"']{view}[\"'][\s\S]{{0,220}}(?:{digit_rx})",
            surface,
        ):
            return False
    return True


def assert_keyboard_map(crate: Path) -> None:
    """#132: ⌘F Search #q from every view, Esc back to People, ⌘1–5 tabs.

    Find (⌘F / ctrl+F) switches to Search and focuses #q — including from
    People (#208). `/` still focuses #person-filter. Keyboard-only can open
    Ada, search, return. Static: App key handler must accept metaKey or
    ctrlKey. Do not steal letters from INPUT/TEXTAREA/SELECT.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#132: App.svelte required (global keyboard map)")
    app = app_path.read_text()
    cleaned = _without_comments(app)
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    raw_body = _app_keydown_body(cleaned) or _app_keydown_body(app)
    if not raw_body.strip():
        fail(
            "#132: App.svelte must handle window keydown "
            "(onKey / addEventListener(\"keydown\")) for the keyboard map"
        )
    body = _expand_fn_calls(cleaned, raw_body)
    if body == raw_body:
        body = _expand_fn_calls(app, raw_body)
    prefix, tail = _split_people_only(raw_body)
    prefix_x = _expand_fn_calls(cleaned, prefix) if prefix.strip() else body
    if prefix_x == prefix:
        prefix_x = _expand_fn_calls(app, prefix) if prefix.strip() else body

    # 1) ⌘F / ctrl+F from every view including People → Search + #q.
    #    Must run off People (not after `if (view !== "people") return`).
    #    Do not send Find to #person-filter — that stays `/` only (#208).
    f_surface = _windows_around(prefix_x, _KEY_F)
    if not f_surface.strip():
        f_surface = _windows_around(body, _KEY_F)
        if f_surface.strip() and tail and _KEY_F.search(tail) and not _KEY_F.search(prefix_x):
            fail(
                "#132: ⌘F / ctrl+F must run off People "
                "(it is after `if (view !== \"people\") return` and never fires on Search)"
            )
        fail(
            "#132: App key handler must treat metaKey/ctrlKey + f/F as Find "
            "(from every view including People, switch to Search and focus #q)"
        )
    if not _has_mod_combo(f_surface) and not _has_mod_combo(prefix_x):
        fail(
            "#132: Find must accept metaKey or ctrlKey "
            "(⌘F on macOS; ctrl+F so gates/tests see the fallback)"
        )
    if not _MOD_EITHER.search(f_surface) and not _MOD_EITHER.search(prefix_x):
        fail("#132: f/F Find must be a metaKey/ctrlKey combo, not a bare letter")
    if _FOCUS_PERSON_FILTER.search(f_surface):
        fail(
            "#132: ⌘F / ctrl+F from People must switch to Search and focus #q "
            "(do not send Find to #person-filter — `/` still focuses the people filter)"
        )
    q_focus = bool(_FOCUS_SEARCH_Q.search(f_surface) or _FOCUS_SEARCH_Q.search(prefix_x))
    if not q_focus:
        fail(
            "#132: ⌘F / ctrl+F from every view including People must focus "
            "the Search query (getElementById(\"q\") / #q)"
        )
    if not _VIEW_SEARCH_ASSIGN.search(f_surface) and not _VIEW_SEARCH_ASSIGN.search(prefix_x):
        fail(
            "#132: ⌘F / ctrl+F from every view including People must switch "
            "to Search (view = \"search\") then focus #q"
        )
    if not _PREVENT_DEFAULT.search(f_surface) and not _PREVENT_DEFAULT.search(prefix_x):
        fail(
            "#132: ⌘F / ctrl+F must preventDefault "
            "(webview/browser must not take Find)"
        )
    if search and not re.search(r"id=[\"']q[\"']", search):
        fail("#132: SearchPane must keep id=\"q\" so ⌘F can focus the query")

    # 2) `/` still focuses the people filter on People (existing).
    slash_src = tail if tail and _KEY_SLASH.search(tail) else body
    if not _KEY_SLASH.search(slash_src) or not _FOCUS_PERSON_FILTER.search(
        _windows_around(slash_src, _KEY_SLASH) or slash_src
    ):
        fail(
            "#132: `/` on People must still focus #person-filter "
            "(do not drop the existing slash filter)"
        )

    # 3) Escape: inputs blur; from other views view = "people"; do not quit.
    if not _INPUT_TAG_GUARD.search(raw_body) and not _INPUT_TAG_GUARD.search(body):
        fail(
            "#132: key handler must still ignore INPUT/TEXTAREA/SELECT "
            "(do not steal letters from a typing field; Esc may blur)"
        )
    if not _KEY_ESC.search(raw_body) and not _KEY_ESC.search(body):
        fail("#132: Escape must be handled (blur inputs; from other views back to People)")
    if not _INPUT_BLUR.search(raw_body) and not _INPUT_BLUR.search(body):
        fail("#132: Escape in an INPUT/TEXTAREA/SELECT must blur the field")
    # ⌘1 also assigns view = "people" — require Escape itself, outside the blur guard.
    outside_prefix, _ = _split_people_only(_without_input_guard(raw_body))
    if not _esc_sets_view_people(outside_prefix, cleaned) and not _esc_sets_view_people(
        outside_prefix, app
    ):
        fail(
            "#132: Escape when not in a typing field must go back to People "
            "(view = \"people\" from Search/Review/Import/Doctor — do not close the app)"
        )
    esc_surface = _windows_around(outside_prefix, _KEY_ESC) or _windows_around(prefix_x, _KEY_ESC)
    if esc_surface and _ESC_CLOSE_APP.search(esc_surface):
        fail("#132: Escape must not close the app (back to People only)")

    # 4) ⌘/ctrl 1–5 → people / search / review / import / doctor.
    digit_surface = _windows_around(prefix_x, _DIGIT_KEY, before=200, after=800)
    if not digit_surface.strip():
        digit_surface = prefix_x
    if not _has_mod_combo(digit_surface) and not _has_mod_combo(prefix_x):
        fail(
            "#132: tab digits must accept metaKey or ctrlKey "
            "(⌘1…5 on macOS; ctrl+1…5 fallback)"
        )
    if not _digit_view_map_ok(digit_surface) and not _digit_view_map_ok(prefix_x):
        if tail and _digit_view_map_ok(tail):
            fail(
                "#132: ⌘/ctrl 1…5 must run off People "
                "(they are after `if (view !== \"people\") return`)"
            )
        fail(
            "#132: metaKey/ctrlKey + Digit1…5 (or keys \"1\"…\"5\") must set "
            "view people / search / review / import / doctor"
        )
    for tok in _VIEW_TAB_ORDER:
        if not re.search(rf"[\"']{tok}[\"']", prefix_x) and not re.search(
            rf"[\"']{tok}[\"']", digit_surface
        ):
            fail(
                f"#132: ⌘/ctrl tab map must include view \"{tok}\" "
                "(1 People, 2 Search, 3 Review, 4 Import, 5 Doctor)"
            )

    # 5) Timeline j/k stay on People (visible indices). Search hits keep their j/k.
    jk_src = tail if tail else body
    if not _KEY_J.search(jk_src) or not _KEY_K.search(jk_src):
        fail("#132: keep timeline j/k (and arrows) on People")
    if tail:
        if (_KEY_J.search(prefix) or _KEY_K.search(prefix)) and re.search(r"\btlIndex\b", prefix):
            if not re.search(r"view\s*===?\s*[\"']people[\"']", prefix):
                fail("#132: timeline j/k must stay People-only (do not steal Search hit j/k)")
    elif not re.search(r"view\s*===?\s*[\"']people[\"']", body) and not re.search(
        r"view\s*!==?\s*[\"']people[\"']", body
    ):
        fail("#132: timeline j/k must stay gated to the People view")
    if not re.search(r"visibleTlIndices|nearestVisibleTlIndex|visibleIndices", jk_src + "\n" + body):
        fail("#132: timeline j/k must still walk visibleTlIndices (do not regress #116)")
    if not _KEY_J.search(search) or not _KEY_K.search(search):
        fail("#132: keep Search hit-list j/k (SearchPane onHitsKey)")

    # 6) Letter shortcuts stay behind the input guard (Esc blur is the exception).
    guard = re.search(
        r"tagName\s*===?\s*[\"']INPUT[\"']",
        raw_body,
    )
    if guard:
        # First return after the INPUT check is the "do not steal" exit.
        ret = raw_body.find("return", guard.start())
        pre_guard = raw_body[: guard.start()] if ret >= 0 else ""
        stolen = False
        for rx in (_KEY_J, _KEY_K, _KEY_SLASH):
            for m in rx.finditer(pre_guard):
                window = pre_guard[max(0, m.start() - 80) : m.end() + 40]
                if _MOD_EITHER.search(window):
                    continue
                stolen = True
                break
            if stolen:
                break
        if stolen:
            fail(
                "#132: do not apply letter shortcuts (j/k, /) before the "
                "INPUT/TEXTAREA/SELECT guard — only Esc may act on a typing field"
            )

    # 7) Not in scope: vim mode, custom keybindings file.
    # Stay in owned sources — do not walk node_modules / target / dist.
    bind_roots = [crate, crate / "web", crate / "web" / "lib", crate / "src"]
    for root in bind_roots:
        if not root.is_dir():
            continue
        for p in root.iterdir():
            if not p.is_file():
                continue
            low = p.name.lower()
            if low in _KEYBIND_NAMES or (
                "keybind" in low and p.suffix in {".json", ".toml"}
            ):
                fail(
                    "#132: no custom keybindings file "
                    f"({p.relative_to(crate)} — out of scope; not vim remaps)"
                )
    web = crate / "web"
    if web.is_dir():
        for p in web.rglob("*"):
            if not p.is_file():
                continue
            low = p.name.lower()
            if low in _KEYBIND_NAMES or (
                "keybind" in low and p.suffix in {".json", ".toml"}
            ):
                fail(
                    "#132: no custom keybindings file "
                    f"({p.relative_to(crate)} — out of scope; not vim remaps)"
                )
    vim_src = body + "\n" + raw_body
    if _VIM_COLON.search(vim_src) or _VIM_COMMAND.search(vim_src):
        fail(
            "#132: no vim mode "
            "(no `:` command map, no :w/:q, no keybindings.json / vimMode)"
        )

    # 8) D24: docs/user/app.md documents the map.
    if not dtxt.strip():
        fail("#132: docs/user/app.md required (document the keyboard map)")
    if not re.search(
        r"("
        r"⌘\s*F"
        r"|Cmd(?:-|\s*|\+)\s*F"
        r"|Command(?:-|\s*|\+)\s*F"
        r"|Ctrl(?:-|\s*|\+)\s*F"
        r"|ctrl(?:-|\s*|\+)\s*F"
        r"|meta(?:-|\s*|\+)\s*f"
        r")",
        dtxt,
        re.I,
    ):
        fail(
            "#132: docs/user/app.md must document ⌘F / Ctrl+F "
            "(from every view including People, switch to Search and focus #q)"
        )
    if re.search(
        r"("
        r"⌘\s*F.{0,100}people filter"
        r"|⌘\s*F.{0,80}#person-filter"
        r"|focuses that people filter on People"
        r"|(?:⌘\s*F|Ctrl\+F|Ctrl-F).{0,60}on People.{0,40}filter"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#132: docs/user/app.md must say ⌘F / Ctrl+F from every view "
            "including People switches to Search and focuses #q "
            "(not the people filter — `/` still focuses #person-filter)"
        )
    if not re.search(
        r"("
        r"(?:⌘\s*F|Ctrl\+F|Ctrl-F).{0,160}(?:every view|including People|from People)"
        r".{0,80}(?:#q|Search)"
        r"|(?:every view|including People).{0,80}(?:⌘\s*F|Ctrl\+F|Ctrl-F)"
        r".{0,80}(?:#q|Search)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#132: docs/user/app.md must say ⌘F / Ctrl+F from every view "
            "including People focuses Search #q"
        )
    if not re.search(
        r"("
        r"(?:Esc(?:ape)?).{0,80}(?:People|people|back)"
        r"|(?:back|return).{0,40}(?:People|people).{0,40}Esc"
        r"|Esc(?:ape)?\s+(?:clears?|back)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#132: docs/user/app.md must document Escape "
            "(clear / back to People)"
        )
    if not re.search(
        r"("
        r"⌘\s*1"
        r"|Cmd(?:-|\s*|\+)\s*1"
        r"|Command(?:-|\s*|\+)\s*1"
        r"|Ctrl(?:-|\s*|\+)\s*1"
        r"|⌘\s*1\s*[–—\-]\s*5"
        r"|Cmd(?:-|\s*|\+)\s*1\s*[–—\-]\s*5"
        r")",
        dtxt,
        re.I,
    ):
        fail(
            "#132: docs/user/app.md must document ⌘1…5 / Ctrl+1…5 "
            "(People / Search / Review / Import / Doctor)"
        )
    missing_tabs = [
        name
        for name in ("People", "Search", "Review", "Import", "Doctor")
        if not re.search(rf"\b{name}\b", dtxt)
    ]
    if missing_tabs:
        fail(
            "#132: docs/user/app.md keyboard map must name "
            + ", ".join(missing_tabs)
            + " (⌘1…5 tabs)"
        )
    if not re.search(r"\bj\b.{0,20}\bk\b|\bj`/`k\b|`j`/`k`", dtxt, re.I):
        fail("#132: docs/user/app.md must keep j/k on the timeline")


# #133 — a11y: people listbox, timeline article/label, focus-visible, reduced motion.
_A11Y_ROLE_LISTBOX = re.compile(r"\brole\s*=\s*[\"']listbox[\"']", re.I)
_A11Y_ROLE_OPTION = re.compile(r"\brole\s*=\s*[\"']option[\"']", re.I)
_A11Y_ROLE_LIST = re.compile(r"\brole\s*=\s*[\"']list[\"']", re.I)
_A11Y_ACTIVEDESC = re.compile(r"\baria-activedescendant\s*=", re.I)
_A11Y_SELECTED = re.compile(r"\baria-selected\s*=", re.I)
_A11Y_SELECTED_STATE = re.compile(
    r"aria-selected\s*=\s*\{[^}]{0,120}"
    r"(?:selectedId|selected_id|selectedPerson|p\.id|person\.id)",
    re.I,
)
_A11Y_ARTICLE = re.compile(r"<article\b|\brole\s*=\s*[\"']article[\"']", re.I)
_A11Y_ARIA_LABEL = re.compile(r"\baria-label(?:ledby)?\s*=", re.I)
_A11Y_FOCUS_VISIBLE = re.compile(
    r"("
    r"focus-visible:(?:ring|outline)"
    r"|:focus-visible\b"
    r")",
    re.I,
)
_A11Y_REDUCED_MOTION = re.compile(
    r"@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)",
    re.I,
)
_A11Y_MOTION_REDUCE_TW = re.compile(r"\bmotion-reduce:", re.I)
_A11Y_ANIM_NONE = re.compile(
    r"("
    r"animation\s*:\s*none\b"
    r"|animation-duration\s*:\s*0(?:s|ms|px)?\b"
    r"|animate-none\b"
    r"|motion-reduce:animate-none\b"
    r")",
    re.I,
)
_A11Y_TRANS_NONE = re.compile(
    r"("
    r"transition\s*:\s*none\b"
    r"|transition-duration\s*:\s*0(?:s|ms)?\b"
    r"|transition-none\b"
    r"|motion-reduce:transition-none\b"
    r")",
    re.I,
)
_A11Y_SCROLL_AUTO = re.compile(
    r"("
    r"scroll-behavior\s*:\s*auto\b"
    r"|scroll-auto\b"
    r"|motion-reduce:scroll-auto\b"
    r")",
    re.I,
)
_A11Y_WCAG_CERT = re.compile(
    r"("
    r"WCAG.{0,80}(?:certificate|certified|conformance\s+certificate)"
    r"|(?:full|complete|official)\s+WCAG\s+(?:2\.[0-2]\s+)?(?:audit\s+)?certificate"
    r"|WCAG\s*2\.[0-2].{0,40}(?:AAA|AA).{0,40}(?:certified|certificate)"
    r"|certified\s+WCAG"
    r")",
    re.I,
)
_A11Y_TABINDEX_NEG = re.compile(r"\btabindex\s*=\s*(?:[\"']-1[\"']|\{-1\})", re.I)
_A11Y_INERT = re.compile(r"(?:\s|/|\{)\binert\b", re.I)
_A11Y_PERSON_ID_LABEL = re.compile(
    r"aria-label\s*=\s*\{[^}]{0,80}"
    r"(?:person_id|personId|selectedId|\bp\.id\b|\bperson\.id\b|(?:item\.)?row\.id)"
    r"[^}]*\}",
    re.I,
)
_A11Y_NAME_IN_LABEL = re.compile(
    r"aria-label\s*=\s*\{[^}]{0,160}"
    r"(?:display_name|displayName|sent_at|body_text|displayBody|utcTime|subject|preview)"
    r"[^}]*\}",
    re.I,
)


def _strip_html_comments(src: str) -> str:
    return re.sub(r"<!--.*?-->", "", src, flags=re.S)


def _css_without_comments(src: str) -> str:
    return re.sub(r"/\*.*?\*/", "", src, flags=re.S)


def _css_prefers_reduced_blocks(blob: str) -> list[str]:
    """Bodies of `@media (prefers-reduced-motion: reduce) { … }` (nested braces)."""
    out: list[str] = []
    for m in _A11Y_REDUCED_MOTION.finditer(blob):
        brace = blob.find("{", m.end() - 1)
        if brace < 0:
            continue
        depth = 0
        j = brace
        while j < len(blob):
            c = blob[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    out.append(blob[brace + 1 : j])
                    break
            j += 1
    return out


def _people_list_a11y_surfaces(crate: Path) -> tuple[str, str]:
    """Chrome around `{#each filtered}` plus the each body (not SearchPane)."""
    chromes: list[str] = []
    bodies: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        text = p.read_text()
        markup = _strip_html_comments(_svelte_markup(text))
        if not _PEOPLE_EACH.search(markup):
            markup = _strip_html_comments(text)
        for m in _PEOPLE_EACH.finditer(markup):
            end = _matching_each_end(markup, m.start())
            if end < 0:
                end = min(len(markup), m.start() + 1600)
            chromes.append(markup[max(0, m.start() - 700) : end])
            bodies.append(markup[m.start() : end])
    return "\n".join(chromes), "\n".join(bodies)


def _open_tag_around(src: str, hook: str) -> str:
    m = re.search(rf"<[^>]*{hook}[^>]*>", src, re.I | re.S)
    return m.group(0) if m else ""


def _css_focus_visible_for(css: str, tokens: tuple[str, ...]) -> bool:
    """True when a :focus-visible rule's selector mentions one of tokens."""
    for m in re.finditer(r"([^{}@][^{]*)\{([^{}]*)\}", css):
        sel, body = m.group(1), m.group(2)
        if ":focus-visible" not in sel and "focus-visible" not in body:
            continue
        low = sel.lower()
        if any(tok.lower() in low for tok in tokens):
            return True
    return False


def assert_a11y_listbox_focus_motion(crate: Path) -> None:
    """#133: people listbox, timeline article/label, focus rings, reduced motion.

    VoiceOver can move through people and hear the selected name. Tab order is
    not a trap. Not a full WCAG audit / certificate.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#133: App.svelte required (people list + timeline a11y)")
    app = app_path.read_text()
    markup = _strip_html_comments(_svelte_markup(app))
    chrome, people_each = _people_list_a11y_surfaces(crate)
    if not chrome.strip():
        chrome = markup
    if not people_each.strip():
        people_each = _people_each_block(markup)
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    css_blob = _css_without_comments(
        "\n".join(p.read_text() for p in _web_sources(crate) if p.suffix == ".css")
    )
    index_html = ""
    index_path = crate / "index.html"
    if index_path.is_file():
        index_html = _css_without_comments(index_path.read_text())
    button_src = ""
    button_path = (
        crate / "web" / "lib" / "components" / "ui" / "button" / "button.svelte"
    )
    if button_path.is_file():
        button_src = button_path.read_text()
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    docs_blob = ""
    docs_root = repo_root() / "docs"
    if docs_root.is_dir():
        docs_blob = "\n".join(
            p.read_text()
            for p in sorted(docs_root.rglob("*.md"))
            if p.is_file()
        )
    readme = repo_root() / "README.md"
    if readme.is_file():
        docs_blob += "\n" + readme.read_text()
    tl_block = _timeline_block(crate)
    boot = _boot_opening_block(app)

    # 1) People list: listbox + option, or list + aria-activedescendant.
    #    Prefer this as the pre-impl red — today is <ul><li><button> with neither.
    if not _PEOPLE_EACH.search(markup) and not _PEOPLE_EACH.search(chrome):
        fail(
            "#133: people sidebar must still {#each filtered …} "
            "(listbox/option wraps that list, not SearchPane)"
        )
    has_listbox = bool(_A11Y_ROLE_LISTBOX.search(chrome))
    has_option = bool(_A11Y_ROLE_OPTION.search(people_each) or _A11Y_ROLE_OPTION.search(chrome))
    has_activedesc = bool(_A11Y_ACTIVEDESC.search(chrome))
    has_list = bool(
        _A11Y_ROLE_LIST.search(chrome)
        or re.search(r"<ul\b|<ol\b", chrome, re.I)
    )
    listbox_pattern = has_listbox and has_option
    activedesc_pattern = has_list and has_activedesc
    if not listbox_pattern and not activedesc_pattern:
        fail(
            "#133: people list must be role=\"listbox\" + role=\"option\" "
            "(or a list + aria-activedescendant). "
            "Today's <ul><li><button> is not a listbox — VoiceOver cannot "
            "move through people as options and hear the selected name"
        )
    if has_listbox and not has_option and not has_activedesc:
        fail(
            "#133: people listbox must have role=\"option\" on each person "
            "(or aria-activedescendant pointing at the active option)"
        )

    # 2) aria-selected on the selected person (VoiceOver hears selected name).
    if not _A11Y_SELECTED.search(people_each) and not _A11Y_SELECTED.search(chrome):
        fail(
            "#133: selected person must set aria-selected "
            "(VoiceOver hears the selected name — bind to selectedId === p.id)"
        )
    if not _A11Y_SELECTED_STATE.search(people_each) and not _A11Y_SELECTED_STATE.search(
        chrome
    ):
        fail(
            "#133: aria-selected must follow the selected person "
            "(selectedId === p.id / equivalent), not a constant true"
        )
    if not re.search(r"\bdisplay_name\b", people_each):
        fail(
            "#133: people options must expose display_name "
            "(VoiceOver hears the selected name; not a raw person id)"
        )
    if _A11Y_PERSON_ID_LABEL.search(people_each) and not _A11Y_NAME_IN_LABEL.search(
        people_each
    ):
        fail(
            "#133: people option accessible name must be the display name, "
            "not a raw person id"
        )

    # 3) Timeline message rows: <article> and/or aria-label — not a bare clickable div.
    #    Accessible name is time + preview/snippet, never a raw person id.
    has_article = bool(_A11Y_ARTICLE.search(tl_block))
    has_row_label = bool(_A11Y_ARIA_LABEL.search(tl_block))
    if not has_article and not has_row_label:
        fail(
            "#133: timeline message rows must be <article> (or role=\"article\") "
            "and/or have an accessible name (aria-label) — not a raw clickable <div>"
        )
    # Article must sit on the message (time / body / data-tl-index), not only .day-heading.
    if has_article:
        article_on_row = bool(
            re.search(
                r"<article\b[^>]{0,500}(?:data-tl-index|data-from-me|body_text|displayBody)",
                tl_block,
                re.I | re.S,
            )
            or re.search(
                r"(?:data-tl-index|data-from-me).{0,240}<article\b",
                tl_block,
                re.I | re.S,
            )
            or re.search(
                r"<article\b.{0,900}(?:<time\b|body_text|displayBody|whitespace-pre-wrap)",
                tl_block,
                re.I | re.S,
            )
        )
        if not article_on_row:
            fail(
                "#133: <article> must be the message row (time + body / snippet), "
                "not only a day heading"
            )
    if _A11Y_PERSON_ID_LABEL.search(tl_block) and not _A11Y_NAME_IN_LABEL.search(tl_block):
        fail(
            "#133: timeline accessible name must be time + preview/snippet, "
            "not a raw person id"
        )

    # 4) Visible focus rings on people options and timeline rows (not only j/k ring-2).
    people_surface = chrome + "\n" + people_each
    people_focus = bool(_A11Y_FOCUS_VISIBLE.search(people_surface))
    if not people_focus and re.search(r"<Button\b", people_each) and _A11Y_FOCUS_VISIBLE.search(
        button_src
    ):
        people_focus = True
    if not people_focus:
        people_focus = _css_focus_visible_for(
            css_blob,
            (
                "[role='option']",
                '[role="option"]',
                "[role=option]",
                "listbox",
                "people-option",
                "person-option",
                "data-people-sidebar",
            ),
        )
    if not people_focus:
        fail(
            "#133: people options need a visible focus-visible ring "
            "(focus-visible:ring / :focus-visible) — browser default outline "
            "on a raw <button> is not enough; j/k selection ring is not focus"
        )
    tl_focus = bool(_A11Y_FOCUS_VISIBLE.search(tl_block))
    if not tl_focus:
        tl_focus = _css_focus_visible_for(
            css_blob,
            (
                "article",
                "[role='article']",
                '[role="article"]',
                "timeline",
                "data-tl-index",
                "bubble-me",
                "bubble-them",
            ),
        )
    if not tl_focus:
        fail(
            "#133: timeline message rows need a visible focus-visible ring "
            "(focus-visible:ring on the article) — the j/k ring-2 highlight "
            "is selection, not keyboard focus"
        )
    if button_src and not _A11Y_FOCUS_VISIBLE.search(button_src):
        fail(
            "#133: nav Button primitive must keep focus-visible:ring "
            "(do not drop visible focus on chrome)"
        )

    # 5) prefers-reduced-motion: disable spin / animation / transitions; scroll auto.
    #    Sticky .day-heading has no animation today — still wrap transitions.
    reduce_css = "\n".join(_css_prefers_reduced_blocks(css_blob))
    reduce_html = "\n".join(_css_prefers_reduced_blocks(index_html))
    reduce_all = reduce_css + "\n" + reduce_html
    has_reduce_media = bool(reduce_css.strip() or reduce_html.strip())
    has_motion_tw = bool(
        _A11Y_MOTION_REDUCE_TW.search(app)
        or _A11Y_MOTION_REDUCE_TW.search(boot)
        or _A11Y_MOTION_REDUCE_TW.search(css_blob)
    )
    if not has_reduce_media and not has_motion_tw:
        fail(
            "#133: must honor prefers-reduced-motion "
            "(@media (prefers-reduced-motion: reduce) in CSS, or Tailwind "
            "motion-reduce) — disable spin / animation / sticky-date animation"
        )
    if not _A11Y_ANIM_NONE.search(reduce_all) and not _A11Y_ANIM_NONE.search(app) and not (
        has_motion_tw and re.search(r"motion-reduce:animate-none", app + "\n" + boot + "\n" + css_blob)
    ):
        fail(
            "#133: prefers-reduced-motion must disable animation "
            "(animation: none / animate-none / motion-reduce:animate-none) "
            "so the boot spinner does not spin"
        )
    if not _A11Y_TRANS_NONE.search(reduce_all) and not re.search(
        r"motion-reduce:transition-none", app + "\n" + css_blob
    ):
        fail(
            "#133: prefers-reduced-motion must disable or zero transitions "
            "(transition: none / motion-reduce:transition-none) — including "
            "any sticky-date animation"
        )
    if not _A11Y_SCROLL_AUTO.search(reduce_all) and not re.search(
        r"motion-reduce:scroll-auto", app + "\n" + css_blob
    ):
        fail(
            "#133: prefers-reduced-motion must set scroll-behavior: auto "
            "(or motion-reduce:scroll-auto)"
        )
    # Pre-JS splash spinner is inline in index.html — app.css cannot stop it.
    if _SPIN_ANIM.search(index_html) and not _A11Y_ANIM_NONE.search(reduce_html):
        fail(
            "#133: index.html boot spinner must honor prefers-reduced-motion "
            "(disable boot-spin / animation under reduce — app.css does not apply pre-JS)"
        )
    if re.search(r"animate-spin", boot) or re.search(r"animate-spin", app):
        covered = bool(
            re.search(r"motion-reduce:animate-none", boot)
            or re.search(r"motion-reduce:animate-none", app)
            or _A11Y_ANIM_NONE.search(reduce_css)
        )
        if not covered:
            fail(
                "#133: Opening-last-archive animate-spin must stop under "
                "prefers-reduced-motion (motion-reduce:animate-none or "
                "animation: none in the reduce media query)"
            )

    # 6) Keep the existing SearchPane person-picker listbox (do not steal it).
    if not search_path.is_file():
        fail("#133: SearchPane.svelte required (keep its listbox/option picker)")
    search_markup = _strip_html_comments(_svelte_markup(search))
    if not _A11Y_ROLE_LISTBOX.search(search) and not _A11Y_ROLE_LISTBOX.search(search_markup):
        fail(
            "#133: keep SearchPane's existing role=\"listbox\" "
            "(people sidebar is a second listbox; do not remove the picker)"
        )
    if not _A11Y_ROLE_OPTION.search(search) and not _A11Y_ROLE_OPTION.search(search_markup):
        fail(
            "#133: keep SearchPane's existing role=\"option\" on person picker rows"
        )

    # 7) Ban claiming a WCAG audit certificate (out of scope).
    if _A11Y_WCAG_CERT.search(docs_blob) or _A11Y_WCAG_CERT.search(dtxt):
        fail(
            "#133: do not claim a WCAG certificate / certified audit in docs "
            "(this issue is listbox + focus + reduced motion, not a full audit)"
        )

    # 8) Tab order is not a trap: filter → people options → timeline/chrome.
    #    Lightbox/dialogs may trap (already). Do not inert the people+timeline grid.
    grid_tag = _open_tag_around(
        markup,
        r"grid-cols-\[minmax\(0,18rem\)_minmax\(0,1fr\)\]",
    )
    if not grid_tag:
        grid_tag = _open_tag_around(markup, r"data-people-sidebar")
    sidebar_tag = _open_tag_around(markup, r"data-people-sidebar")
    timeline_tag = _open_tag_around(markup, r"id=[\"']person-timeline[\"']")
    for tag, where in (
        (grid_tag, "people+timeline grid"),
        (sidebar_tag, "people sidebar"),
        (timeline_tag, "person timeline"),
    ):
        if tag and _A11Y_INERT.search(tag):
            fail(
                f"#133: do not put inert on the {where} "
                "(tab order must reach people filter → people options → timeline; "
                "dialogs/lightbox may still trap)"
            )
    filter_win = ""
    fm = re.search(r"id=[\"']person-filter[\"']", markup)
    if fm:
        filter_win = markup[max(0, fm.start() - 160) : fm.end() + 160]
    if filter_win and _A11Y_TABINDEX_NEG.search(filter_win):
        fail(
            "#133: #person-filter must stay in tab order "
            "(do not tabindex=\"-1\" the people filter)"
        )
    # tabindex="-1" on every person skips the list unless the listbox uses
    # aria-activedescendant (roving focus stays on the listbox).
    if _A11Y_TABINDEX_NEG.search(people_each) and not has_activedesc:
        dynamic_tab = bool(re.search(r"tabindex\s*=\s*\{", people_each))
        if not dynamic_tab:
            fail(
                "#133: do not tabindex=\"-1\" every person "
                "(that skips the list). Use listbox + options in tab order, "
                "or roving tabindex with aria-activedescendant"
            )

    # 9) User-visible: one line in docs (keyboard + VoiceOver). Not a certificate.
    if not dtxt.strip():
        fail("#133: docs/user/app.md required (VoiceOver / people list; not a WCAG certificate)")
    if not re.search(r"VoiceOver", dtxt):
        fail(
            "#133: docs/user/app.md must mention VoiceOver on the people list "
            "(hear the selected name; keyboard tab order) — not a WCAG certificate"
        )


# #134 — drag-drop local ZIP/mbox onto the window → existing importStart + progress.
_TAURI_DRAG_DROP_API = re.compile(
    r"("
    r"\.onDragDropEvent\s*\("
    r"|\bon_drag_drop_event\s*\("
    r"|tauri://drag-drop"
    r"|tauri://file-drop"
    r")",
)
_TAURI_DRAG_DROP_TYPE = re.compile(r"\bDragDropEvent\b")
_TAURI_DRAG_DROP_PLUGIN = re.compile(
    r"("
    r"@tauri-apps/plugin-fs"
    r"|tauri-plugin-fs"
    r"|plugin-file-drop"
    r"|tauri-plugin-drag"
    r")",
)
_HTML_DROP_ATTR = re.compile(
    r"("
    r"\bon:?drop\b"
    r"|\bondrop\b"
    r"|\bon:?dragover\b"
    r"|\bondragover\b"
    r"|\bon:?dragenter\b"
    r")",
    re.I,
)
_DROP_EVENT_TYPE = re.compile(
    r"("
    r"(?:payload\.)?type\s*===?\s*[\"']drop[\"']"
    r"|[\"']drop[\"']\s*===?\s*(?:[\w$.]+\.)?type"
    r"|DragDropEvent::Drop"
    r"|DragDrop::Drop"
    r"|WindowEvent::DragDrop"
    r")",
)
_DROP_PATHS = re.compile(
    r"("
    r"(?:payload\.)?paths\b"
    r"|\.paths\s*\["
    r")"
)
_IMPORT_START_CALL = re.compile(r"\b(?:api\.)?importStart\s*\(")
_IMPORT_START_KIND_AUTO = re.compile(
    r"("
    r"kind\s*:\s*null"
    r"|kind\s*:\s*(?:undefined|kind\s*===?\s*[\"']auto[\"']\s*\?\s*null)"
    r")"
)
_VIEW_IMPORT_ASSIGN = re.compile(r"\bview\s*=\s*[\"']import[\"']")
_URL_SCHEME_REJECT = re.compile(
    r"("
    r"https?://"
    r"|/?\\^https\\?:"
    r"|\\bhttps?:"
    r"|startsWith\s*\(\s*[\"']https?"
    r"|includes\s*\(\s*[\"']https?"
    r"|protocol\s*===?\s*[\"']https?:"
    r"|[\"']https?://"
    r"|isRemote(?:Url|Path)?"
    r"|isHttps?"
    r"|isUrl\b"
    r"|looksLikeUrl"
    r"|hasUrlScheme"
    r"|urlScheme"
    r"|reject(?:Http|Url|Remote)"
    r")",
    re.I,
)
_HTTPS_TOKEN = re.compile(r"https://|[\"']https://|https\\?:|[\"']https[\"']", re.I)
_HTTP_TOKEN = re.compile(r"http://|[\"']http://|[\"']http[\"']|https\\?:", re.I)
_SHOW_ERR = re.compile(
    r"("
    r"\bonError\s*\("
    r"|\bshowErr\s*\("
    r"|\berr\s*="
    r"|progress\.error"
    r")",
)
_FETCH_CALL = re.compile(r"\bfetch\s*\(")
_XHR = re.compile(r"\bXMLHttpRequest\b|\baxios\s*\.")
_DATATRANSFER = re.compile(r"\bdataTransfer\b")
_DROP_WALK = re.compile(
    r"("
    r"\bwalkDir\b"
    r"|\bwalkSync\b"
    r"|\bfs\.walk\b"
    r"|\breadDir\s*\("
    r"|\bread_dir\s*\("
    r"|\breaddir\s*\("
    r"|recursive\s*:\s*true"
    r"|@tauri-apps/plugin-fs"
    r"|\bfolderOfFolders\b"
    r"|\bwalkImport\b"
    r"|\bimportWalk\b"
    r"|\brglob\s*\("
    r")",
)
_HTTP_CAP = re.compile(
    r"("
    r"http:default"
    r"|http:allow-fetch"
    r"|http:allow-request"
    r"|tauri-plugin-http"
    r"|allow-http"
    r")",
    re.I,
)
_IMPORT_PANE_PATH_PROP = re.compile(
    r"<ImportPane\b[^>]{0,500}(?:"
    r"bind:path"
    r"|droppedPath|dropPath|startPath|importPath|queuedPath|pendingPath"
    r"|autoStart|dropQueued"
    r")",
    re.I | re.S,
)
_DROP_CALL_SKIP = frozenset(
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
        "Error",
        "setTimeout",
        "setInterval",
        "clearInterval",
        "requestAnimationFrame",
        "getCurrentWebview",
        "getCurrentWindow",
        "onDragDropEvent",
        "listen",
        "console",
        "JSON",
        "Array",
        "Object",
        "RegExp",
        "Date",
        "Map",
        "Set",
        "unlisten",
        "onMount",
        "tick",
    }
)


def _web_ts_sources(crate: Path) -> list[Path]:
    web = crate / "web"
    if not web.is_dir():
        return []
    return [
        p
        for p in sorted(web.rglob("*"))
        if p.suffix in {".svelte", ".ts", ".js"} and "node_modules" not in p.parts
    ]


def _import_pane_conditionally_mounted(app: str) -> bool:
    """True when every ImportPane mounts only under view === \"import\"."""
    seen = False
    only_conditional = True
    for m in re.finditer(r"<ImportPane\b", app):
        seen = True
        window = app[max(0, m.start() - 400) : m.start()]
        if not re.search(r"view\s*===?\s*[\"']import[\"']", window):
            only_conditional = False
    return seen and only_conditional


def _drop_api_files(crate: Path) -> list[Path]:
    found: list[Path] = []
    for p in _web_ts_sources(crate) + _tauri_rust_sources(crate):
        text = p.read_text()
        if _TAURI_DRAG_DROP_API.search(text) or (
            _TAURI_DRAG_DROP_TYPE.search(text) and re.search(r"\.paths\b", text)
        ):
            found.append(p)
    return found


def _extract_call_callback(src: str, call_rx: re.Pattern[str]) -> list[str]:
    bodies: list[str] = []
    for m in call_rx.finditer(src):
        open_paren = src.find("(", m.start())
        if open_paren < 0:
            continue
        arg = _call_arg(src, open_paren)
        if not arg:
            continue
        bodies.append(arg)
        named = re.match(r"\s*([A-Za-z_][\w]*)\s*$", arg.strip())
        if named and named.group(1) not in _DROP_CALL_SKIP:
            inner = _ts_fn_body(src, named.group(1)) or _function_body(src, named.group(1))
            if inner:
                bodies.append(inner)
    return bodies


def _expand_drop_calls(src: str, body: str, depth: int = 3) -> str:
    chunks = [body]
    seen: set[str] = set()

    def walk(blob: str, left: int) -> None:
        for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob):
            if name in seen or name in _DROP_CALL_SKIP:
                continue
            seen.add(name)
            inner = _ts_fn_body(src, name) or _function_body(src, name)
            if not inner:
                continue
            chunks.append(inner)
            if left > 0:
                walk(inner, left - 1)

    walk(body, depth)
    return "\n".join(chunks)


def _drop_handler_surface(crate: Path) -> str:
    """Bodies that run on Tauri drag-drop (and named callees)."""
    chunks: list[str] = []
    sources: list[str] = []
    for p in _web_ts_sources(crate) + _tauri_rust_sources(crate):
        text = p.read_text()
        cleaned = _without_comments(text)
        sources.append(text)
        sources.append(cleaned)
        chunks.extend(_extract_call_callback(cleaned, re.compile(r"\.onDragDropEvent\s*\(")))
        chunks.extend(_extract_call_callback(text, re.compile(r"\.onDragDropEvent\s*\(")))
        chunks.extend(_extract_call_callback(cleaned, re.compile(r"\bon_drag_drop_event\s*\(")))
        chunks.extend(_extract_call_callback(text, re.compile(r"\bon_drag_drop_event\s*\(")))
        for src in (cleaned, text):
            for m in re.finditer(
                r"listen\s*(?:<[^>]*>)?\s*\(\s*[\"']tauri://(?:drag-drop|file-drop)[\"']",
                src,
            ):
                open_paren = src.find("(", m.start())
                arg = _call_arg(src, open_paren) if open_paren >= 0 else ""
                if arg:
                    chunks.append(arg)
    joined = "\n".join(chunks)
    if not joined.strip():
        return ""
    whole = "\n".join(sources)
    return _expand_drop_calls(whole, joined)


def _drop_rejects_url_scheme(surface: str) -> bool:
    """True if http and https (or a generic URL-scheme helper) are rejected."""
    if not _URL_SCHEME_REJECT.search(surface):
        return False
    has_http = bool(_HTTP_TOKEN.search(surface))
    has_https = bool(_HTTPS_TOKEN.search(surface))
    generic = bool(
        re.search(
            r"("
            r"urlScheme"
            r"|hasUrlScheme"
            r"|looksLikeUrl"
            r"|isUrl\b"
            r"|isRemote"
            r"|reject(?:Http|Url|Remote)"
            r"|/?\\^[a-zA-Z][a-zA-Z0-9+.\-]*:"
            r")",
            surface,
        )
    )
    return (has_http and has_https) or generic


def _drop_starts_import(crate: Path, surface: str, app: str, import_pane: str) -> bool:
    if _IMPORT_START_CALL.search(surface):
        return True
    if re.search(r"\bstart\s*\(", surface) and _IMPORT_START_CALL.search(import_pane):
        return True
    if _IMPORT_PANE_PATH_PROP.search(app) and _IMPORT_START_CALL.search(import_pane):
        if re.search(
            r"("
            r"droppedPath|dropPath|startPath|importPath|queuedPath|pendingPath"
            r"|\$effect"
            r")",
            import_pane,
        ) and _IMPORT_START_CALL.search(import_pane):
            return True
    return False


def assert_drag_drop_import(crate: Path) -> None:
    """#134: drop local ZIP/mbox → existing importStart + progress; reject URLs.

    Tauri file-drop (onDragDropEvent), not HTML ondrop of remote URLs and not
    fetch. First local path into importStart (auto-detect). Switch to Import
    so the existing progress UI shows. No new folder-of-folders walker.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#134: App.svelte required (window-level drop must reach Import)")
    app = app_path.read_text()
    import_path = crate / "web" / "lib" / "ImportPane.svelte"
    import_pane = import_path.read_text() if import_path.is_file() else ""
    web = _web_logic(crate)
    rust = _tauri_rust_blob(crate)
    blob = web + "\n" + rust
    cleaned = _without_comments(blob)
    caps_path = crate / "capabilities" / "default.json"
    caps = caps_path.read_text() if caps_path.is_file() else ""
    pkg = (crate / "package.json").read_text() if (crate / "package.json").is_file() else ""
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) Tauri drag-drop API — not a raw http fetch, not HTML ondrop alone.
    if "@tauri-apps/api" not in pkg:
        fail("#134: @tauri-apps/api must remain a dependency (onDragDropEvent)")
    if not _TAURI_DRAG_DROP_API.search(cleaned) and not _TAURI_DRAG_DROP_API.search(blob):
        fail(
            "#134: must listen for Tauri file-drop "
            "(getCurrentWebview/Window().onDragDropEvent or on_drag_drop_event), "
            "not a raw http fetch / HTML ondrop of remote URLs"
        )
    api_files = _drop_api_files(crate)
    if not api_files:
        fail(
            "#134: must listen for Tauri file-drop "
            "(getCurrentWebview/Window().onDragDropEvent or on_drag_drop_event)"
        )
    only_import_pane = api_files and all(p.name == "ImportPane.svelte" for p in api_files)
    if only_import_pane and _import_pane_conditionally_mounted(app):
        fail(
            "#134: drop listener must run on any tab "
            "(App / always-mounted helper), not only inside the Import view "
            "(ImportPane unmounts when view !== \"import\")"
        )

    surface = _drop_handler_surface(crate)
    if not surface.strip():
        surface = "\n".join(p.read_text() for p in api_files)

    # 2) Drop branch reads Tauri local paths (payload.paths), not dataTransfer URLs.
    if not _DROP_PATHS.search(surface):
        fail(
            "#134: drop handler must read Tauri local paths "
            "(event.payload.paths) — not HTML dataTransfer of a remote URL"
        )
    if _DATATRANSFER.search(surface) and not _DROP_PATHS.search(surface):
        fail(
            "#134: do not import from HTML dataTransfer URLs; "
            "use Tauri payload.paths (local filesystem only)"
        )
    if not _DROP_EVENT_TYPE.search(surface) and not re.search(
        r"\bpaths\b", surface
    ):
        fail(
            "#134: handle the drop event (payload.type === \"drop\" / "
            "DragDropEvent::Drop), not hover/enter"
        )

    # 3) First local path starts existing import (not only fills the path field).
    if not import_pane.strip():
        fail("#134: ImportPane.svelte required (existing progress UI)")
    if not _drop_starts_import(crate, surface, app, import_pane):
        fail(
            "#134: drop of a local path must call existing importStart "
            "(or ImportPane start / path prop that starts import) — "
            "filling the path field alone is not enough"
        )
    start_win = _windows_around(surface, _IMPORT_START_CALL, before=200, after=240)
    if not start_win.strip():
        start_win = surface
    if _IMPORT_START_CALL.search(surface) and re.search(
        r"kind\s*:\s*[\"']whatsapp[\"']", start_win
    ) and not _IMPORT_START_KIND_AUTO.search(start_win):
        fail(
            "#134: drop must use the picker auto-detect path "
            "(importStart({ path, kind: null })) — not a WhatsApp-only kind"
        )

    # 4) Switch to Import so importProgress / Status running→done is visible.
    if not _VIEW_IMPORT_ASSIGN.search(surface) and not _VIEW_IMPORT_ASSIGN.search(app):
        fail(
            "#134: drop on another tab must set view = \"import\" "
            "so the existing import progress UI is visible"
        )
    if not _VIEW_IMPORT_ASSIGN.search(surface):
        # Assignment exists somewhere in App (⌘4 / nav). Require it on the drop path.
        fail(
            "#134: drop handler must set view = \"import\" "
            "(progress UI is the Import tab; drop may land on People/Search/…)"
        )
    if "importProgress" not in import_pane:
        fail(
            "#134: keep ImportPane importProgress polling "
            "(drop starts the existing progress UI, not a new one)"
        )
    if not re.search(r"progress\.status|Status:", import_pane):
        fail("#134: keep the Import status / progress UI (running → done)")

    # 5) Reject http(s) / URL-scheme drops: show error, do not import.
    if not _drop_rejects_url_scheme(surface):
        fail(
            "#134: drop handler must reject http:// and https:// "
            "(and other URL schemes) — local filesystem paths only"
        )
    if not _SHOW_ERR.search(surface):
        fail(
            "#134: rejected URL drops must show an error "
            "(onError / showErr) and must not call importStart"
        )

    # 6) Bans: fetch of the dropped file, remote URL as import path, new walker.
    if _FETCH_CALL.search(surface) or _XHR.search(surface):
        fail(
            "#134: do not fetch() the dropped file "
            "(no remote URLs as the import path)"
        )
    if re.search(r"importStart\s*\(\s*\{[^}]{0,200}https?://", surface, re.I | re.S):
        fail("#134: importStart path must not be a remote http(s) URL")
    walk_src = surface
    for p in api_files:
        if p.suffix in {".svelte", ".ts", ".js", ".rs"}:
            walk_src += "\n" + p.read_text()
    if _DROP_WALK.search(walk_src) or _DROP_WALK.search(surface):
        fail(
            "#134: do not add a new folder-of-folders walker "
            "(UI5 folder-of-zips via existing importStart auto-detect is OK)"
        )
    if _TAURI_DRAG_DROP_PLUGIN.search(toml) or _TAURI_DRAG_DROP_PLUGIN.search(pkg):
        if "plugin-fs" in toml or "plugin-fs" in pkg or "@tauri-apps/plugin-fs" in web:
            fail(
                "#134: do not add @tauri-apps/plugin-fs / a recursive walk "
                "for drop — pass the local path to existing importStart"
            )
    if _HTTP_CAP.search(caps) or "tauri-plugin-http" in toml:
        fail("#134: no HTTP client capability / tauri-plugin-http (local paths only)")
    if re.search(r"network\.server", caps):
        fail("#134: capabilities must not add network.server")

    # Optional: smallest drag-drop ACL if the generated schema lists one.
    schema_blob = ""
    schemas = crate / "gen" / "schemas"
    if schemas.is_dir():
        for p in schemas.glob("*.json"):
            schema_blob += p.read_text()
    if re.search(r"allow-on-drag-drop-event", schema_blob) and not re.search(
        r"allow-on-drag-drop-event", caps
    ):
        fail(
            "#134: capabilities/default.json must include the smallest "
            "drag-drop permission (core:webview:allow-on-drag-drop-event "
            "or core:window:allow-on-drag-drop-event)"
        )

    # 7) HTML ondrop of remote URLs is not a substitute.
    if _HTML_DROP_ATTR.search(cleaned) and not _TAURI_DRAG_DROP_API.search(cleaned):
        fail(
            "#134: HTML ondrop/ondragover is not enough — "
            "use Tauri onDragDropEvent for local paths"
        )

    # 8) Docs: drop a local ZIP/mbox; no URLs.
    if not dtxt.strip():
        fail("#134: docs/user/app.md required (drop a local ZIP/mbox; no URLs)")
    drop_win = ""
    for m in re.finditer(
        r".{0,160}(?:\bdrop(?:ping|ped)?\b|drag-and-drop|drag and drop).{0,160}",
        dtxt,
        re.I | re.S,
    ):
        drop_win += m.group(0) + "\n"
    if not drop_win.strip():
        fail(
            "#134: docs/user/app.md must say you can drop a local ZIP/mbox "
            "onto the window"
        )
    if not re.search(r"\blocal\b", drop_win, re.I):
        fail("#134: docs/user/app.md must say the drop is a local path (not a URL)")
    if not re.search(r"\bZIP\b|\.zip\b", drop_win, re.I):
        fail("#134: docs/user/app.md must mention dropping a local ZIP")
    if not re.search(r"\bmbox\b", drop_win, re.I):
        fail("#134: docs/user/app.md must mention dropping a local mbox")
    if not re.search(r"URL", drop_win, re.I):
        fail(
            "#134: docs/user/app.md drop line must say no URLs "
            "(local ZIP/mbox only)"
        )
    if not re.search(
        r"("
        r"no URLs"
        r"|not a URL"
        r"|URLs not"
        r"|not URLs"
        r"|never a URL"
        r"|local.{0,40}not.{0,20}URL"
        r")",
        drop_win,
        re.I | re.S,
    ):
        fail("#134: docs/user/app.md must say drop is local ZIP/mbox, no URLs")


# #135 — copy message text / reveal CAS file in Finder (hash only; file open).
_CONTEXTMENU = re.compile(
    r"("
    r"on:contextmenu"
    r"|oncontextmenu"
    r"|addEventListener\s*\(\s*[\"']contextmenu[\"']"
    r"|ContextMenu(?:\.\w+)?"
    r"|data-context-menu"
    r"|contextMenu"
    r")",
    re.I,
)
_COPY_TEXT_LABEL = re.compile(r"Copy text")
_REVEAL_LABEL = re.compile(r"Reveal in Finder")
_WRITE_TEXT = re.compile(
    r"("
    r"navigator\.clipboard\.writeText"
    r"|clipboard\.writeText"
    r")"
)
_REVEAL_CMD_NAMES = (
    "reveal_cas",
    "revealCas",
    "reveal_in_finder",
    "revealInFinder",
)
_REVEAL_CMD = re.compile(
    r"\b(?:" + "|".join(re.escape(n) for n in _REVEAL_CMD_NAMES) + r")\b"
)
_REVEAL_INVOKE = re.compile(
    r"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"'](?:"
    + "|".join(re.escape(n) for n in _REVEAL_CMD_NAMES)
    + r")[\"']"
)
_PLUGIN_SHELL = re.compile(
    r"("
    r"tauri-plugin-shell"
    r"|tauri-plugin-opener"
    r"|@tauri-apps/plugin-shell"
    r"|@tauri-apps/plugin-opener"
    r"|plugin-shell"
    r"|plugin-opener"
    r"|plugin_shell"
    r"|plugin_opener"
    r")",
    re.I,
)
_SHELL_CAP = re.compile(
    r"("
    r"shell:allow-execute"
    r"|shell:allow-open"
    r"|shell:default"
    r"|opener:allow-open"
    r"|opener:allow-reveal"
    r"|opener:default"
    r")"
)
_SHARE_AIRDROP = re.compile(
    r"("
    r"AirDrop"
    r"|Share sheet"
    r"|share sheet"
    r"|NSSharingService"
    r"|showShareSheet"
    r"|ShareLink\b"
    r"|share-sheet"
    r")",
    re.I,
)
_SHARE_ITEM = re.compile(
    r"("
    r">\s*Share\s*<"
    r"|[\"']Share[\"']"
    r"|label\s*:\s*[\"']Share[\"']"
    r")"
)
_ARBITRARY_SHELL = re.compile(
    r"Command::new\s*\(\s*[\"'](?:/bin/sh|/bin/bash|/bin/zsh|/usr/bin/env|sh|bash|zsh|cmd)[\"']"
)
_COPY_FN_NAMES = (
    "copyText",
    "copyMessage",
    "copyBubble",
    "copyBubbleText",
    "onCopyText",
    "handleCopy",
    "handleCopyText",
)
_RUST_CALL_SKIP = frozenset(
    {
        "Ok",
        "Err",
        "Some",
        "None",
        "vec",
        "format",
        "println",
        "eprintln",
        "dbg",
        "Command",
        "Path",
        "PathBuf",
        "String",
        "Vec",
        "Result",
        "Option",
        "drop",
        "clone",
        "lock",
        "map_err",
        "ok_or",
        "ok_or_else",
        "canonicalize",
        "starts_with",
        "join",
        "spawn",
        "output",
        "status",
        "arg",
        "args",
        "new",
        "from",
        "into",
        "as_ref",
        "as_str",
        "to_string",
        "to_owned",
        "expect",
        "unwrap",
        "if",
        "for",
        "while",
        "loop",
        "match",
        "return",
        "Box",
        "Arc",
        "Mutex",
        "State",
        "fs",
        "File",
        "OpenOptions",
    }
)
_BUBBLE_MENU_SKIP = frozenset(
    {
        "App.svelte",
        "CasAttach.svelte",
        "SearchPane.svelte",
        "ReviewPane.svelte",
        "ImportPane.svelte",
        "DoctorPane.svelte",
        "ConfirmDialog.svelte",
        "EmptyState.svelte",
    }
)


def _rust_next(src: str, i: int) -> int:
    """Advance past a Rust comment or string starting at i; else return i."""
    n = len(src)
    if i >= n:
        return i
    if src.startswith("//", i):
        nl = src.find("\n", i)
        return n if nl < 0 else nl + 1
    if src.startswith("/*", i):
        end = src.find("*/", i + 2)
        return n if end < 0 else end + 2
    raw = re.match(r"(?:[bc])?r(#*)\"", src[i:])
    if raw:
        hashes = raw.group(1)
        start = i + raw.end()
        needle = '"' + hashes
        end = src.find(needle, start)
        return n if end < 0 else end + len(needle)
    if src[i] == '"' or (i + 1 < n and src[i] in "bc" and src[i + 1] == '"'):
        j = i + 1 if src[i] == '"' else i + 2
        while j < n:
            if src[j] == "\\":
                j += 2
                continue
            if src[j] == '"':
                return j + 1
            j += 1
        return n
    if src[i] == "'":
        if i + 1 < n and (src[i + 1].isalpha() or src[i + 1] == "_"):
            j = i + 2
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            if j < n and src[j] == "'" and j == i + 2:
                return j + 1
            return j
        j = i + 1
        if j < n and src[j] == "\\":
            j += 2
        elif j < n:
            j += 1
        if j < n and src[j] == "'":
            return j + 1
        return j
    return i


def _rust_match_delim(src: str, open_idx: int) -> int:
    pairs = {"(": ")", "{": "}", "[": "]", "<": ">"}
    opener = src[open_idx]
    closer = pairs.get(opener)
    if not closer:
        return -1
    depth = 0
    i = open_idx
    n = len(src)
    while i < n:
        nxt = _rust_next(src, i)
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


def _rust_function_body(src: str, name: str) -> str:
    """Body of `fn name` (Rust). Do not use the JS `_function_body` here."""
    m = re.search(
        rf"(?:pub\s+)?(?:async\s+)?fn\s+{re.escape(name)}\b",
        src,
    )
    if not m:
        return ""
    i = m.end()
    n = len(src)
    while i < n:
        nxt = _rust_next(src, i)
        if nxt != i:
            i = nxt
            continue
        if src[i] == "(":
            break
        i += 1
    else:
        return ""
    close_p = _rust_match_delim(src, i)
    if close_p < 0:
        return ""
    i = close_p + 1
    while i < n:
        nxt = _rust_next(src, i)
        if nxt != i:
            i = nxt
            continue
        if src[i] == "{":
            close_b = _rust_match_delim(src, i)
            if close_b < 0:
                return src[i + 1 :]
            return src[i + 1 : close_b]
        i += 1
    return ""


def _rust_fn_signature(src: str, name: str) -> str:
    """Parameter list of `fn name`, including the wrapping parens."""
    m = re.search(
        rf"(?:pub\s+)?(?:async\s+)?fn\s+{re.escape(name)}\b",
        src,
    )
    if not m:
        return ""
    i = m.end()
    n = len(src)
    while i < n:
        nxt = _rust_next(src, i)
        if nxt != i:
            i = nxt
            continue
        if src[i] == "(":
            close_p = _rust_match_delim(src, i)
            if close_p < 0:
                return src[i:]
            return src[i : close_p + 1]
        i += 1
    return ""


def _rust_call_arg(src: str, open_paren: int) -> str:
    close = _rust_match_delim(src, open_paren)
    if close < 0:
        return ""
    return src[open_paren + 1 : close]


def _rust_body_with_callees(src: str, name: str, depth: int = 2) -> str:
    body = _rust_function_body(src, name)
    if not body:
        return ""
    parts = [body]
    seen = {name}

    def walk(blob: str, left: int) -> None:
        if left <= 0:
            return
        for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob):
            callee = m.group(1)
            if callee in seen or callee in _RUST_CALL_SKIP:
                continue
            seen.add(callee)
            inner = _rust_function_body(src, callee)
            if not inner:
                continue
            parts.append(inner)
            walk(inner, left - 1)

    walk(body, depth)
    return "\n".join(parts)


def _bubble_and_attach_surface(crate: Path) -> str:
    """Person-timeline bubbles + CasAttach + components they reference."""
    parts = [_timeline_block(crate)]
    app_path = crate / "web" / "App.svelte"
    if app_path.is_file():
        parts.append(app_path.read_text())
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if cas_path.is_file():
        parts.append(cas_path.read_text())
    used = "\n".join(parts)
    web = crate / "web"
    if web.is_dir():
        for p in sorted(web.rglob("*.svelte")):
            if "node_modules" in p.parts or p.name in _BUBBLE_MENU_SKIP:
                continue
            if re.search(rf"\b{re.escape(p.stem)}\b", used):
                parts.append(p.read_text())
    return "\n".join(parts)


def _copy_handler_surface(web: str) -> str:
    chunks = [_windows_around(web, _WRITE_TEXT, before=500, after=160)]
    for name in _COPY_FN_NAMES:
        body = _ts_function_body(web, name) or _function_body(web, name)
        if body:
            chunks.append(body)
        chunks.append(
            _windows_around(web, re.compile(rf"\b{re.escape(name)}\s*\("), before=220, after=80)
        )
    return "\n".join(chunks)


def _copy_logs_body(surf: str) -> bool:
    """True if the copy path logs the message body (console / eprintln)."""
    for m in re.finditer(r"console\.(?:log|debug|info|dir|trace)\s*\(", surf):
        arg = _call_arg(surf, m.end() - 1)
        if re.search(
            r"body_text|displayBody|copiedText|\bbody\b|\btext\b|\bmsg\b|\bmessage\b",
            arg,
            re.I,
        ):
            return True
    for m in re.finditer(r"(?:eprintln|println|dbg)\s*!", surf):
        window = surf[m.start() : m.end() + 200]
        if re.search(r"body_text|displayBody|\bbody\b", window, re.I):
            return True
    return False


def _reveal_cmd_name(rust: str, web: str) -> str:
    blob = rust + "\n" + web
    m = _REVEAL_CMD.search(blob)
    return m.group(0) if m else ""


def _invoke_payloads(web: str, rx: re.Pattern[str]) -> list[str]:
    found: list[str] = []
    for m in rx.finditer(web):
        open_p = web.find("(", m.start())
        if open_p < 0:
            continue
        arg = _call_arg(web, open_p)
        if arg:
            found.append(arg)
    return found


def _payload_has_path_or_url(payload: str) -> bool:
    return bool(
        re.search(
            r"\b(?:path|url|file|href|uri)\s*:|\b(?:path|url|file|href|uri)\b\s*[,}]",
            payload,
            re.I,
        )
    )


def assert_copy_reveal_cas(crate: Path) -> None:
    """#135: bubble context menu Copy text; cas_hash attachment Reveal in Finder.

    Reveal command takes the hash only, resolves cas/ab/cd/<hash> via
    cas_blob_path, opens the local file (std::process /usr/bin/open -R or
    file://). Copy does not log the body. No plugin-shell / Share / AirDrop.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#135: App.svelte required (person-timeline bubble context menu)")
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail("#135: CasAttach.svelte required (Reveal in Finder on cas_hash)")
    web = _web_logic(crate)
    surface = _bubble_and_attach_surface(crate)
    rust = _tauri_rust_blob(crate)
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    pkg = (crate / "package.json").read_text() if (crate / "package.json").is_file() else ""
    caps_path = crate / "capabilities" / "default.json"
    caps = caps_path.read_text() if caps_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) Context menu on a person-timeline bubble.
    if not _CONTEXTMENU.search(surface):
        fail(
            "#135: person-timeline bubble must have a context menu "
            "(on:contextmenu / ContextMenu) for Copy text"
        )

    # 2) Custom menu: Copy text → clipboard (message text).
    if not _COPY_TEXT_LABEL.search(surface) and not _COPY_TEXT_LABEL.search(web):
        fail("#135: context menu must include Copy text")
    if not _WRITE_TEXT.search(web):
        fail(
            "#135: Copy text must write the message text to the clipboard "
            "(navigator.clipboard.writeText)"
        )
    copy_surf = _copy_handler_surface(web)
    if not re.search(r"body_text|displayBody|bodyText", copy_surf):
        fail("#135: clipboard write must be the message text (body_text / displayBody)")

    # 3) Copy does not log the body.
    if _copy_logs_body(copy_surf) or _copy_logs_body(_windows_around(web, _WRITE_TEXT)):
        fail(
            "#135: Copy must not log the message body "
            "(no console.log / eprintln of the text)"
        )

    # 4) Attachment with cas_hash → Reveal in Finder.
    if not _REVEAL_LABEL.search(surface) and not _REVEAL_LABEL.search(web):
        fail(
            "#135: attachment with cas_hash must offer Reveal in Finder "
            "(context menu on the attachment)"
        )
    reveal_win = _windows_around(surface, _REVEAL_LABEL, before=520, after=240)
    if not reveal_win.strip():
        reveal_win = _windows_around(web, _REVEAL_LABEL, before=520, after=240)
    if not re.search(r"cas_hash|casHash|hashOf", reveal_win + "\n" + surface):
        fail("#135: Reveal in Finder is only for an attachment that has cas_hash")

    # 5) Frontend sends only the hash to the reveal command.
    cmd = _reveal_cmd_name(rust, web)
    if not cmd:
        fail(
            "#135: frontend must invoke a reveal command that takes the hash only "
            "(e.g. reveal_cas) — not a path or URL"
        )
    payloads = _invoke_payloads(web, _REVEAL_INVOKE)
    if not payloads:
        # api.revealCas(hash) wrapper — still must mention hash, not path/url.
        call_win = _windows_around(web, _REVEAL_CMD, before=80, after=160)
        if not re.search(r"\bhash\b", call_win, re.I):
            fail(
                "#135: frontend must send only the hash to reveal "
                "(invoke reveal_cas with { hash })"
            )
        if _payload_has_path_or_url(call_win):
            fail(
                "#135: frontend must send only the hash to reveal "
                "(do not pass a path or URL from the webview)"
            )
    for payload in payloads:
        if not re.search(r"\bhash\b", payload, re.I):
            fail(
                "#135: frontend must send only the hash to reveal "
                "(invoke reveal_cas with { hash })"
            )
        if _payload_has_path_or_url(payload):
            fail(
                "#135: frontend must send only the hash to reveal "
                "(do not pass a path or URL from the webview)"
            )

    # 6) Rust command: hash only; cas_blob_path; under cas/; file-only open.
    sig = _rust_fn_signature(rust, cmd)
    body = _rust_body_with_callees(rust, cmd)
    if not body.strip():
        fail(
            f"#135: Rust command {cmd} must resolve cas/ab/cd/<hash> "
            "(fn reveal_cas taking the hash only)"
        )
    if not re.search(r"\bhash\b", sig, re.I):
        fail("#135: reveal command must take a hash (not a path or URL)")
    if re.search(r"\b(?:path|url|file|href|uri)\s*:", sig, re.I):
        fail(
            "#135: reveal command must take the hash only — "
            "do not take a path or URL from the webview"
        )
    if "cas_blob_path" not in body:
        fail(
            "#135: reveal must resolve cas/ab/cd/<hash> via cas_blob_path "
            "(64 hex only — reject anything else)"
        )
    if not re.search(r"\bcanonicalize\s*\(", body):
        fail("#135: reveal must canonicalize the CAS path")
    if not re.search(
        r"("
        r"starts_with"
        r"|outside cas"
        r"|join\(\s*[\"']cas[\"']"
        r"|[\"']cas/"
        r")",
        body,
    ):
        fail("#135: reveal must refuse anything outside cas/")
    if not re.search(r"generate_handler!\s*\[[^\]]*\b" + re.escape(cmd) + r"\b", rust, re.S):
        fail(f"#135: register {cmd} in generate_handler")

    if not re.search(r"std::process|\buse\s+std::process", rust):
        fail(
            "#135: open Finder with std::process "
            "(not tauri-plugin-shell / plugin-opener)"
        )
    if not re.search(r"Command::new|std::process::Command", body):
        fail(
            "#135: reveal must open the local file with std::process::Command "
            "(/usr/bin/open -R or a file:// URL)"
        )
    if "/usr/bin/open" not in body:
        fail("#135: open the local CAS file with /usr/bin/open (file only, not http)")
    if not re.search(r"[\"']-R[\"']", body) and "file://" not in body:
        fail("#135: use /usr/bin/open -R or a file:// URL to the CAS path")
    if re.search(r"[\"']https?://", body):
        fail("#135: reveal must not open http(s) — file only")
    if _ARBITRARY_SHELL.search(body) or _ARBITRARY_SHELL.search(rust):
        fail("#135: no shell of arbitrary commands — only /usr/bin/open on the CAS file")
    for m in re.finditer(r"Command::new\s*\(", body):
        arg = _rust_call_arg(body, m.end() - 1)
        if "/usr/bin/open" not in arg:
            fail(
                "#135: no shell of arbitrary commands — "
                "Command::new must be /usr/bin/open on the CAS file"
            )

    # 7) Bans: plugin-shell / opener / shell caps / Share / AirDrop.
    if _PLUGIN_SHELL.search(toml) or _PLUGIN_SHELL.search(pkg):
        fail(
            "#135: do not add tauri-plugin-shell / tauri-plugin-opener "
            "(std::process file-only open)"
        )
    if _PLUGIN_SHELL.search(rust) or _PLUGIN_SHELL.search(web):
        fail(
            "#135: do not add tauri-plugin-shell / tauri-plugin-opener "
            "(std::process file-only open)"
        )
    if _SHELL_CAP.search(caps):
        fail(
            "#135: capabilities must not add shell:allow-execute / "
            "shell:allow-open / opener (no arbitrary Command)"
        )
    if _SHARE_AIRDROP.search(web) or _SHARE_AIRDROP.search(rust) or _SHARE_ITEM.search(surface):
        fail("#135: no Share sheet / AirDrop")

    # 8) Docs: right-click copy text; reveal local CAS in Finder; no Share / AirDrop.
    if not dtxt.strip():
        fail("#135: docs/user/app.md required (right-click copy text; reveal in Finder)")
    doc_win = ""
    for m in re.finditer(
        r".{0,180}(?:right-click|context menu|Copy text|Reveal in Finder|AirDrop|Share sheet).{0,180}",
        dtxt,
        re.I | re.S,
    ):
        doc_win += m.group(0) + "\n"
    if not doc_win.strip():
        fail(
            "#135: docs/user/app.md must say right-click Copy text "
            "and reveal local CAS in Finder"
        )
    if not re.search(r"right-click|context menu", doc_win, re.I):
        fail("#135: docs/user/app.md must say right-click (or context menu) to copy text")
    if not re.search(r"copy text", doc_win, re.I):
        fail("#135: docs/user/app.md must describe Copy text")
    if not re.search(r"reveal", doc_win, re.I):
        fail("#135: docs/user/app.md must say reveal local CAS in Finder")
    if not re.search(r"Finder", doc_win):
        fail("#135: docs/user/app.md must say reveal local CAS in Finder")
    if not re.search(r"CAS|cas/", doc_win, re.I):
        fail("#135: docs/user/app.md must say the reveal target is a local CAS file")
    if not re.search(
        r"("
        r"no Share"
        r"|not Share"
        r"|Share sheet"
        r"|AirDrop"
        r")",
        doc_win,
        re.I,
    ):
        fail("#135: docs/user/app.md must say no Share / AirDrop")


# #136 — defer doctor CAS scan so large archives open fast.
_DOCTOR_ISSUE_API = re.compile(
    r"("
    r"(?:api\.)?doctorIssues\b"
    r"|(?:api\.)?doctor_issues\b"
    r"|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']doctor_issues"
    r")",
)
_DOCTOR_RUN_API = re.compile(r"(?:api\.)?doctorRun\b|doctor_run_cmd|\bdoctor_run\b")
_QUICK_DOCTOR = re.compile(
    r"("
    r"doctorIssuesQuick"
    r"|doctor_issues_quick"
    r"|quick\s*:\s*true"
    r"|mode\s*:\s*[\"']quick[\"']"
    r"|doctorIssues\s*\(\s*true\s*\)"
    r")",
    re.I,
)
_GC_ON_OPEN = re.compile(r"\bgc_cas\b|\bgcCas\s*:\s*true")
_GC_THREAD = re.compile(
    r"("
    r"thread::spawn"
    r"|std::thread"
    r"|Builder::new\s*\(\s*\)\s*\.name\s*\(\s*[\"'][^\"']*gc"
    r")",
    re.I,
)
_OPEN_AWAIT_SKIP = _SCROLL_HELPER_SKIP | {
    "api",
    "invoke",
    "doctorIssues",
    "doctorIssuesQuick",
    "doctorRun",
    "people",
    "linkEvents",
    "status",
    "open",
    "init",
    "pickFolder",
    "rememberedPath",
    "showErr",
    "csv",
    "trim",
}


def _await_expression(src: str, start: int) -> str:
    """Expression after `await` at `start`, up to `;` / newline at depth 0."""
    n = len(src)
    i = start
    while i < n and src[i] in " \t":
        i += 1
    depth = 0
    j = i
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
    return src[i:j].strip()


def _doctor_expr_is_quick(expr: str) -> bool:
    return bool(_QUICK_DOCTOR.search(expr))


def _doctor_expr_is_full_scan(expr: str) -> bool:
    if not _DOCTOR_ISSUE_API.search(expr):
        return False
    return not _doctor_expr_is_quick(expr)


def _open_awaited_surface(web: str, roots: tuple[str, ...]) -> str:
    """Bodies of `roots` plus only functions they `await` (not fire-and-forget)."""
    parts: list[str] = []
    seen: set[str] = set()

    def walk(name: str) -> None:
        if name in seen or name in _OPEN_AWAIT_SKIP:
            return
        seen.add(name)
        body = _ts_function_body(web, name) or _function_body(web, name)
        if not body:
            return
        parts.append(body)
        for m in re.finditer(r"\bawait\s+", body):
            expr = _await_expression(body, m.end())
            ident = re.match(r"(?:api\.)?([A-Za-z_]\w*)", expr)
            if ident:
                walk(ident.group(1))

    for root_name in roots:
        walk(root_name)
    return "\n".join(parts)


def _awaited_exprs(src: str) -> list[str]:
    return [_await_expression(src, m.end()) for m in re.finditer(r"\bawait\s+", src)]


def _core_rust_blob(root: Path) -> str:
    src = root / "crates" / "interlace-core" / "src"
    if not src.is_dir():
        return ""
    return "\n".join(p.read_text() for p in sorted(src.rglob("*.rs")) if p.is_file())


def _full_doctor_scan_body(core_src: str, rust: str) -> str:
    """Archive::doctor_issues (full) plus callees — not the quick path."""
    blob = core_src + "\n" + rust
    body = _rust_body_with_callees(blob, "doctor_issues")
    if body.strip():
        return body
    return _rust_function_body(blob, "doctor_issues")


def assert_defer_doctor_cas(crate: Path) -> None:
    """#136: open shows People without awaiting a full CAS walk.

    Doctor badge may load async or stay empty until the Doctor tab.
    Doctor tab (load / Refresh) still runs the full scan that walks
    referenced CAS hashes. A missing blob still surfaces. No background
    GC on open.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#136: App.svelte required (open / applyStatus must show People first)")
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    if not doctor_path.is_file():
        fail("#136: DoctorPane.svelte required (full CAS scan on the Doctor tab)")
    app = app_path.read_text()
    doctor_txt = doctor_path.read_text()
    web = _web_logic(crate)
    rust = _tauri_rust_blob(crate)
    root = repo_root()
    core_src = _core_rust_blob(root)
    docs_app = root / "docs" / "user" / "app.md"
    dtxt = docs_app.read_text() if docs_app.is_file() else ""
    docs_doc = root / "docs" / "user" / "doctor.md"
    ddoc = docs_doc.read_text() if docs_doc.is_file() else ""

    apply_body = _ts_function_body(web, "applyStatus") or _function_body(web, "applyStatus")
    if not apply_body.strip():
        fail("#136: applyStatus required (open / create / reopen last archive)")
    if not re.search(r"\b(?:api\.)?people\s*\(|\brefreshPeople\s*\(", apply_body):
        fail(
            "#136: applyStatus must still load People "
            "(people list + status) when opening clears"
        )

    open_path = _ts_function_body(web, "openPath") or _function_body(web, "openPath")
    if not open_path.strip():
        fail("#136: openPath required (opening must clear before a full CAS walk)")
    if not re.search(r"\bopening\s*=\s*true\b", open_path):
        fail("#136: openPath must set opening = true while the archive opens")
    if not re.search(r"\bopening\s*=\s*false\b", open_path):
        fail("#136: opening must clear so People can render (do not wait on CAS)")
    if not re.search(r"\bapplyStatus\s*\(", open_path):
        fail("#136: openPath must apply status / people (applyStatus) when opening")

    create_body = _ts_function_body(web, "createArchive") or _function_body(
        web, "createArchive"
    )
    if not create_body.strip():
        fail("#136: createArchive required (create must show People without a CAS walk)")
    if not re.search(r"\bapplyStatus\s*\(", create_body):
        fail("#136: createArchive must apply status / people without waiting on CAS")

    if not re.search(r"rememberedPath|openPath\s*\(", app):
        fail("#136: reopen last archive must go through openPath / applyStatus")

    # 1) Open / applyStatus does not await a full CAS walk before People / opening.
    open_surface = _open_awaited_surface(
        web, ("applyStatus", "openPath", "createArchive", "openPicker")
    )
    if not open_surface.strip():
        open_surface = apply_body + "\n" + open_path + "\n" + create_body
    open_clean = _without_comments(open_surface)
    for expr in _awaited_exprs(open_clean):
        if _DOCTOR_RUN_API.search(expr):
            fail(
                "#136: open / applyStatus must not await doctorRun "
                "(People must not wait on a doctor action / GC)"
            )
        if _doctor_expr_is_full_scan(expr):
            fail(
                "#136: open / applyStatus must show People without awaiting a full "
                "CAS walk (cas_get / every attachments.cas_hash) before opening "
                "clears — Doctor badge may be async or empty until the Doctor tab"
            )
    if re.search(r"\bcas_get\b", open_clean) and re.search(r"cas_hash", open_clean):
        fail(
            "#136: applyStatus / open must not walk every attachments.cas_hash / "
            "cas_get before People render"
        )

    # Rust open / create / status must not themselves walk CAS or start GC.
    for name in ("open", "init", "hold", "status"):
        body = _rust_body_with_callees(rust, name)
        if not body.strip():
            continue
        if _GC_ON_OPEN.search(body):
            fail(
                f"#136: no background GC on open "
                f"(gc_cas must not run from Rust {name}())"
            )
        if re.search(r"\bcas_get\b", body) and re.search(
            r"cas_hash|attachments", body
        ):
            fail(
                f"#136: Rust {name}() must not walk attachments.cas_hash / cas_get "
                "(opening must not wait on a full CAS scan)"
            )
        if re.search(r"\bdoctor_issues\s*\(", body) and not _doctor_expr_is_quick(body):
            fail(
                f"#136: Rust {name}() must not run the full doctor_issues CAS walk "
                "(People stay behind opening if open/status awaits it)"
            )

    # People render when opening clears — not inside the spinner, not gated on doctor.
    if not re.search(r"booting\s*\|\|\s*opening|opening\s*\|\|\s*booting", app):
        fail(
            "#136: opening must gate the spinner so People render when opening clears"
        )
    boot = _boot_opening_block(app)
    if re.search(r"data-people-sidebar|{#each\s+people\b", boot):
        fail(
            "#136: People list must render after opening clears, "
            "not inside the opening spinner"
        )
    if not re.search(r"data-people-sidebar|{#each\s+people\b", app):
        fail("#136: People list must still render after open (sidebar / people rows)")

    # 2) Doctor tab still runs the full scan (load / Refresh / doctorIssues).
    load_body = _ts_function_body(doctor_txt, "load") or _function_body(doctor_txt, "load")
    if not load_body.strip():
        fail("#136: DoctorPane load must run the full doctor scan")
    load_clean = _without_comments(load_body)
    if not any(_doctor_expr_is_full_scan(expr) for expr in _awaited_exprs(load_clean)):
        # Fire-and-forget still counts if load calls the full API (Refresh / tab).
        if not _DOCTOR_ISSUE_API.search(load_clean) or _doctor_expr_is_quick(load_clean):
            fail(
                "#136: Doctor tab (DoctorPane load) must run a full scan "
                "(doctorIssues / doctor_issues) that walks referenced CAS hashes "
                "— not only a quick SQLite+FTS check"
            )
        if _doctor_expr_is_quick(load_clean) and not any(
            _doctor_expr_is_full_scan(expr) for expr in _awaited_exprs(load_clean)
        ):
            fail(
                "#136: Doctor tab must invoke the full doctorIssues scan "
                "(not doctorIssuesQuick / quick: true only)"
            )
    if not re.search(r"\bRefresh\b", doctor_txt):
        fail("#136: Doctor tab must keep Refresh (full scan)")
    if not re.search(r"onclick=\{[^}]*\bload\b", doctor_txt):
        fail("#136: Refresh must call load (full doctorIssues scan)")
    if not re.search(r"onMount\s*\(\s*\(\s*\)\s*=>\s*\{[^}]*\bload\s*\(", doctor_txt, re.S):
        if "load()" not in doctor_txt:
            fail("#136: DoctorPane must load the full scan when the Doctor tab opens")

    # IPC used by the Doctor tab still calls the full Archive::doctor_issues.
    cmd_body = _rust_body_with_callees(rust, "doctor_issues_cmd")
    if not cmd_body.strip():
        fail(
            "#136: doctor_issues_cmd must still run the full doctor_issues scan "
            "(Doctor tab / Refresh)"
        )
    if not re.search(r"\bdoctor_issues\s*\(", cmd_body):
        fail(
            "#136: doctor_issues_cmd must call doctor_issues() "
            "(full scan, not only a quick flag)"
        )
    if re.search(r"doctor_issues_quick", cmd_body) and not re.search(
        r"\bdoctor_issues\s*\(", cmd_body
    ):
        fail("#136: Doctor-tab IPC must run the full doctor_issues path")

    full_body = _full_doctor_scan_body(core_src, rust)
    if not full_body.strip():
        fail("#136: Archive::doctor_issues (full) must still exist for the Doctor tab")
    if not re.search(r"\bcas_get\b", full_body):
        fail(
            "#136: full doctor scan must cas_get referenced hashes "
            "(Doctor tab still walks CAS)"
        )
    if not re.search(r"cas_hash", full_body):
        fail(
            "#136: full doctor scan must walk attachments.cas_hash "
            "(referenced CAS hashes)"
        )
    if not re.search(r"CAS blob missing", full_body):
        fail(
            "#136: a missing blob must still surface as a doctor issue "
            "on the full path (Doctor tab / doctor_issues)"
        )

    # CLI with no flag stays a full scan.
    cli = root / "crates" / "interlace-core" / "src" / "cli.rs"
    if cli.is_file():
        cli_txt = cli.read_text()
        if not re.search(r"\bdoctor_issues\s*\(\s*\)", cli_txt):
            fail(
                "#136: CLI `interlace doctor` (no flag) must keep a full "
                "doctor_issues() scan"
            )

    # 3) No background GC on open (applyStatus / open / create / boot).
    if _GC_ON_OPEN.search(open_clean):
        fail(
            "#136: no background GC on open "
            "(gc_cas / GC thread not started from applyStatus/open)"
        )
    if _GC_THREAD.search(open_clean) and _GC_ON_OPEN.search(open_clean + "\n" + rust):
        fail("#136: no background GC thread on open")
    boot_src = _without_comments(app)
    if _GC_ON_OPEN.search(boot_src) and re.search(
        r"rememberedPath|opening\s*=\s*true", boot_src
    ):
        # gcCas: true on the Doctor tab is fine; fail only if it sits on the open path.
        for name in ("applyStatus", "openPath", "createArchive", "openPicker"):
            body = _ts_function_body(web, name) or _function_body(web, name)
            if body and _GC_ON_OPEN.search(_without_comments(body)):
                fail(
                    "#136: no background GC on open "
                    f"(gc_cas must not start from {name})"
                )
    if re.search(r"thread::spawn", rust) and re.search(
        r"gc_cas", _rust_body_with_callees(rust, "open") + _rust_body_with_callees(rust, "init")
    ):
        fail("#136: no background GC thread started from open/init")

    # 4) Docs (D24): open is not blocked on hashing cas/; Doctor tab finds missing blobs.
    if not dtxt.strip():
        fail(
            "#136: docs/user/app.md required "
            "(open is not blocked on hashing cas/; Doctor tab still finds missing blobs)"
        )
    if not re.search(
        r"("
        r"not blocked on hashing"
        r"|without (?:waiting|blocking).{0,60}(?:hash|cas/|CAS)"
        r"|open(?:ing)?(?:ing an archive| of (?:an? )?archive)?.{0,80}"
        r"not.{0,40}(?:hash|walk|scan|blocked).{0,40}cas"
        r"|People.{0,60}(?:immediately|without waiting).{0,60}(?:cas|doctor|hash)"
        r"|does not wait.{0,40}(?:hash|cas/|CAS)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail("#136: docs/user/app.md must say open is not blocked on hashing cas/")
    if not re.search(
        r"("
        r"Doctor tab.{0,100}(?:missing blob|referenced.{0,20}blob|walk.{0,40}cas)"
        r"|missing blob.{0,80}Doctor"
        r"|Doctor.{0,80}(?:still )?(?:walk|find).{0,40}(?:missing|referenced|cas|blob)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#136: docs/user/app.md must say the Doctor tab still finds a missing blob "
            "(full scan of referenced CAS hashes)"
        )
    if not ddoc.strip():
        fail(
            "#136: docs/user/doctor.md required "
            "(Doctor tab still walks referenced CAS / finds missing blobs)"
        )
    if not re.search(
        r"("
        r"Doctor tab.{0,120}(?:missing|referenced|cas_hash|CAS)"
        r"|CAS file missing"
        r"|missing blob"
        r"|cas_hash"
        r"|referenced.{0,40}(?:CAS|blob|hash|attachments)"
        r")",
        ddoc,
        re.I | re.S,
    ):
        fail(
            "#136: docs/user/doctor.md must say the Doctor tab still walks "
            "referenced CAS hashes / finds a missing blob"
        )


# #184 — people list / VoiceOver: short human time, not raw ISO last_activity_at.
_HUMAN_TIME_HELPERS = (
    "humanTime",
    "shortTime",
    "formatLastActivity",
    "utcHumanTime",
    "activityTime",
    "lastActivityLabel",
    "formatActivityAt",
    "shortActivity",
    "humanLastActivity",
    "utcShortTime",
    "formatUtcShort",
    "shortHumanTime",
    "formatHumanTime",
    "humanActivity",
    "utcActivity",
    "formatUtcActivity",
)
_HUMAN_TIME_CALL = re.compile(
    r"\b(?:" + "|".join(_HUMAN_TIME_HELPERS) + r")\s*\("
)
_MONTH_SHORT = re.compile(
    r"("
    r"[\"'](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\"']"
    r"|month\s*:\s*[\"']short[\"']"
    r")",
    re.I,
)
_HM_PART = re.compile(
    r"("
    r"getUTCHours"
    r"|getUTCMinutes"
    r"|slice\s*\(\s*11\s*,\s*16\s*\)"
    r"|slice\s*\(\s*t\s*\+\s*1\s*,\s*t\s*\+\s*6\s*\)"
    r"|hour\s*:\s*[\"']2-digit[\"']"
    r"|minute\s*:\s*[\"']2-digit[\"']"
    r")",
)
_UTC_FMT = re.compile(
    r"("
    r"getUTC(?:Date|Month|Hours|Minutes|FullYear)"
    r"|timeZone\s*:\s*[\"']UTC[\"']"
    r"|split\s*\(\s*[\"']T[\"']\s*\)"
    r"|indexOf\s*\(\s*[\"']T[\"']\s*\)"
    r"|\bUTC\b"
    r")",
)
_DATE_PICKER = re.compile(
    r"("
    r"\bDatePicker\b"
    r"|date-picker"
    r"|datepicker"
    r"|flatpickr"
    r"|litepicker"
    r"|air-datepicker"
    r"|type\s*=\s*[\"']date[\"']"
    r"|type\s*=\s*[\"']datetime-local[\"']"
    r")",
    re.I,
)
_BODY_T_CALL = re.compile(
    r"\bt\s*\(\s*(?:[\w.$]+\.)?(?:body_text|bodyText|preview|snippet|displayBody)\b"
)


def _svelte_interpolations(src: str) -> list[str]:
    """Inner text of `{…}` markup interpolations (not {#if} / {:else} / {@const})."""
    out: list[str] = []
    i = 0
    n = len(src)
    while i < n:
        j = src.find("{", i)
        if j < 0:
            break
        nxt = src[j + 1 : j + 3]
        if nxt[:1] in {"#", "/", ":", "@"}:
            i = j + 1
            continue
        end = _match_closer(src, j)
        if end < 0:
            break
        out.append(src[j + 1 : end])
        i = end + 1
    return out


def _interp_dumps_iso_activity(expr: str) -> bool:
    """True if last_activity_at is stringified (raw T…Z), not passed to a formatter."""
    if not re.search(r"\blast_activity_at\b", expr):
        return False
    if re.search(r"[A-Za-z_]\w*\s*\([^)]*\blast_activity_at\b", expr):
        return False
    # Truthiness for a separator (`p.last_activity_at && p.preview ? " · " : ""`).
    if re.search(r"last_activity_at\s*&&", expr) and not re.search(
        r"last_activity_at\s*(?:\?\?|\|\|)", expr
    ):
        return False
    return True


def _attr_brace_values(src: str, attr: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(rf"{re.escape(attr)}\s*=\s*\{{", src, re.I):
        start = m.end() - 1
        end = _match_closer(src, start)
        if end > start:
            out.append(src[start + 1 : end])
    return out


def _short_time_formatter_ok(logic: str) -> bool:
    """A helper (or inline) turns ISO into a short UTC time like `11 Aug 14:32`."""
    for name in _HUMAN_TIME_HELPERS:
        body = _ts_function_body(logic, name) or _function_body(logic, name)
        if body and _MONTH_SHORT.search(body) and _HM_PART.search(body):
            return True
    if _MONTH_SHORT.search(logic) and _HM_PART.search(logic) and _UTC_FMT.search(logic):
        return True
    return False


def _people_uses_short_time(people_each: str) -> bool:
    if _HUMAN_TIME_CALL.search(people_each):
        return True
    for expr in _svelte_interpolations(people_each):
        if re.search(r"[A-Za-z_]\w*\s*\([^)]*\blast_activity_at\b", expr):
            return True
    return False


def assert_human_time_people(crate: Path) -> None:
    """#184: people list / VoiceOver show a short time, not raw ISO last_activity_at.

    Visible sidebar options and the name VoiceOver reads are name + a short
    time (e.g. 11 Aug 14:32), not 2024-08-11T14:32:00Z. Archive / api.ts JSON
    still carries ISO last_activity_at. Do not t() bodies. Not a date-picker
    locale pack. Do not require “yesterday” in App.svelte (#112).
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#184: App.svelte required (people list last_activity_at display)")
    app = app_path.read_text()
    logic = _web_logic(crate)
    chrome, people_each = _people_list_a11y_surfaces(crate)
    if not people_each.strip():
        markup = _strip_html_comments(_svelte_markup(app))
        people_each = _people_each_block(markup)
        chrome = markup
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    if not _PEOPLE_EACH.search(app) and not _PEOPLE_EACH.search(chrome):
        fail("#184: people sidebar must still {#each filtered …} as person options")
    if not people_each.strip():
        fail("#184: people list {#each filtered} body missing")

    # 1) Still show last_activity_at — as a short time, not dropped.
    if not re.search(r"\blast_activity_at\b", people_each):
        fail(
            "#184: people list must still show last_activity_at "
            "(as a short time, not drop the activity timestamp)"
        )

    # 2) Visible option text is not the raw ISO T…Z string.
    raw_dump = any(_interp_dumps_iso_activity(expr) for expr in _svelte_interpolations(people_each))
    if raw_dump:
        fail(
            "#184: people list must not display raw ISO last_activity_at "
            "(T…Z / 2024-08-11T14:32:00Z); use a short time (e.g. 11 Aug 14:32)"
        )

    # 3) A formatter exists (month + hour:minute; UTC / ISO prefix). Helper
    #    may live in another web/ file. Do not require “yesterday” in App.svelte.
    if not _short_time_formatter_ok(logic):
        fail(
            "#184: format last_activity_at as a short UTC time "
            "(e.g. 11 Aug 14:32) — month + hour:minute, not YYYY-MM-DDTHH:MM:SSZ"
        )
    if not _people_uses_short_time(people_each):
        fail(
            "#184: people options must pass last_activity_at through a short-time "
            "helper (e.g. humanTime(p.last_activity_at)), not interpolate the ISO"
        )

    # 4) VoiceOver: name + short time, not 2024-08-11T14:32:00Z.
    if not re.search(r"\b(?:display_name|displayName|personLabel|personName)\b", people_each):
        fail(
            "#184: VoiceOver on a person must hear the name plus a short time "
            "(keep display_name / personLabel on the option)"
        )
    labels = _attr_brace_values(people_each, "aria-label")
    if labels:
        for lab in labels:
            has_name = bool(
                re.search(r"display_name|displayName|personLabel|personName", lab)
            )
            wrapped = bool(
                re.search(r"[A-Za-z_]\w*\s*\([^)]*\blast_activity_at\b", lab)
                or _HUMAN_TIME_CALL.search(lab)
            )
            raw_in_label = bool(re.search(r"\blast_activity_at\b", lab)) and not wrapped
            if not has_name:
                fail(
                    "#184: VoiceOver aria-label must include the person name "
                    "plus a short time"
                )
            if raw_in_label:
                fail(
                    "#184: VoiceOver must not read raw ISO last_activity_at "
                    "(2024-08-11T14:32:00Z) — aria-label is name + short time"
                )
            if not wrapped:
                fail(
                    "#184: VoiceOver aria-label must be the name plus a short time "
                    "(not 2024-08-11T14:32:00Z)"
                )

    # 5) Archive / API JSON types still carry ISO last_activity_at.
    api_path = crate / "web" / "lib" / "api.ts"
    if not api_path.is_file():
        fail("#184: web/lib/api.ts required (Person.last_activity_at stays ISO)")
    api = api_path.read_text()
    if not re.search(
        r"export type Person\s*=\s*\{[^}]*\blast_activity_at\??\s*:\s*string",
        api,
        re.S,
    ):
        fail(
            "#184: API Person JSON must still carry ISO last_activity_at "
            "(do not strip the field from api.ts)"
        )

    # 6) Do not t() message bodies or previews.
    helpers = _chrome_helper_names(logic)
    body_blob = logic + "\n" + app
    if _chrome_helper_on_body(body_blob, helpers) or _BODY_T_CALL.search(body_blob):
        fail("#184: do not t() message bodies or previews (t(body_text) / t(preview))")

    # 7) Not a date-picker locale pack.
    if _DATE_PICKER.search(logic) or _DATE_PICKER.search(app):
        fail("#184: not a date-picker locale pack")

    # 8) Docs: people list / VoiceOver use a short time, not the raw ISO.
    if not dtxt.strip():
        fail("#184: docs/user/app.md required (people list / VoiceOver short time)")
    if not re.search(
        r"("
        r"(?:people list|VoiceOver).{0,220}short(?:er)?(?: human)? time"
        r"|short(?:er)?(?: human)? time.{0,220}(?:people list|VoiceOver)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#184: docs/user/app.md must say people list / VoiceOver use a "
            "short time, not the raw ISO"
        )
    if not re.search(
        r"("
        r"not (?:the |a )?raw ISO"
        r"|not (?:the |a )?raw.{0,24}ISO"
        r"|not .{0,40}2024-08-11T"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#184: docs/user/app.md must say people list / VoiceOver time is "
            "not the raw ISO"
        )


# #198 — design tokens: no raw hues in product Svelte; chrome uses shadcn + bubbles.
_HUE_AMBER = re.compile(r"\bamber-\d+")
_HUE_YELLOW = re.compile(r"\byellow-\d+")
_HUE_BLACK80 = re.compile(r"\bblack/80\b")
# Hex as a color: Tailwind arbitrary `bg-[#111]` or a CSS color property.
# Do not treat `{#each}`, `#person-timeline`, `#{e.id}`, or issue `#198` as hex.
_HUE_HEX_TW = re.compile(
    r"(?:bg|text|border|ring|from|to|via|outline|fill|stroke|decoration|"
    r"divide|accent|caret|shadow)-\[#[0-9A-Fa-f]{3,8}"
)
_HUE_HEX_CSS = re.compile(
    r"(?:background(?:-color)?|color|border(?:-color)?|outline-color|"
    r"fill|stroke|accent-color|caret-color|text-decoration-color)\s*:\s*"
    r"#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})\b",
    re.I,
)
_HEAVY_SHADOW = re.compile(r"(?<![\w-])shadow-(?:lg|xl|2xl)\b")
_GRADIENT = re.compile(
    r"("
    r"(?<![\w-])bg-gradient-"
    r"|(?<![\w-])(?:from|to|via)-(?:"
    r"zinc|slate|gray|neutral|stone|red|orange|amber|yellow|lime|green|"
    r"emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|"
    r"black|white|transparent|current|inherit"
    r")"
    r")",
)
_THEME_CDN = re.compile(
    r"("
    r"fonts\.googleapis"
    r"|fonts\.gstatic"
    r"|cdn\."
    r"|unpkg\.com"
    r"|jsdelivr"
    r"|@import\s+(?:url\s*\(\s*)?['\"]https?://"
    r")",
    re.I,
)
_NEW_BRAND_VAR = re.compile(r"--(?:color-)?brand\b|--palette-")
_SQL_DDL = re.compile(r"""['\"][^'\"]*\b(?:ALTER|CREATE)\s+TABLE\b""", re.I)
_DOCS_DESIGN_TOKENS = re.compile(
    r"("
    r"(?:design tokens?|CSS variables?).{0,260}(?:chrome|colou?rs?|hues?)"
    r"|(?:chrome|colou?rs?|hues?).{0,260}(?:design tokens?|CSS variables?)"
    r")",
    re.I | re.S,
)
_DOCS_NOT_RAW_HUES = re.compile(
    r"("
    r"not raw (?:Tailwind )?hues?"
    r"|not (?:a |the )?raw Tailwind hues?"
    r"|not raw Tailwind"
    r"|CSS variables?, not raw"
    r"|design tokens?, not raw"
    r")",
    re.I,
)
_SHADCN_TOKEN_DEFS = (
    "--color-background",
    "--color-foreground",
    "--color-muted-foreground",
    "--color-border",
    "--color-destructive",
)
_SHADCN_TOKEN_USES = (
    "bg-background",
    "text-foreground",
    "text-muted-foreground",
    "border-border",
)


def _product_svelte(crate: Path) -> list[Path]:
    web = crate / "web"
    return [
        p
        for p in sorted(web.rglob("*.svelte"))
        if "node_modules" not in p.parts
    ]


def _hue_surface(text: str) -> str:
    return _without_comments(_strip_html_comments(text))


def _token_hits(crate: Path, files: list[Path], rx: re.Pattern[str]) -> list[str]:
    hits: list[str] = []
    for p in files:
        found = sorted({m.group(0) for m in rx.finditer(_hue_surface(p.read_text()))})
        if found:
            hits.append(f"{p.relative_to(crate)}: {', '.join(found)}")
    return hits


def _hue_findings(text: str) -> list[str]:
    """Banned raw hues (issue #198). Token defs may live in app.css only."""
    surface = _hue_surface(text)
    found: list[str] = []
    amber = sorted(set(_HUE_AMBER.findall(surface)))
    if amber:
        found.append("amber-* (" + ", ".join(amber) + ")")
    yellow = sorted(set(_HUE_YELLOW.findall(surface)))
    if yellow:
        found.append("yellow-* (" + ", ".join(yellow) + ")")
    if _HUE_BLACK80.search(surface):
        found.append("black/80")
    hexes = _HUE_HEX_TW.findall(surface) + _HUE_HEX_CSS.findall(surface)
    if hexes:
        found.append("hex (" + ", ".join(sorted(set(hexes))) + ")")
    return found


def assert_design_tokens(crate: Path) -> None:
    """#198: product Svelte chrome uses existing tokens, not raw hues.

    No hex / amber-* / yellow-* / black/80 in web/**/*.svelte (defs may stay
    in app.css). Map chrome onto existing shadcn names (background, foreground,
    muted-foreground, border, destructive) plus --bubble-me / --bubble-them.
    Bubbles stay distinct. No new brand palette, gradients, CDN theme, or
    stored-data rewrite. Do not require --warning / --success (#219). Keep
    <mark> highlight chrome (#126). Docs: tokens / CSS variables, not raw hues.
    """
    svelte_files = _product_svelte(crate)
    if not svelte_files:
        fail("#198: crates/interlace-tauri/web/**/*.svelte required (token chrome)")

    # 1) Hard acceptance: no raw hues in product Svelte (first fail on master).
    offenders: list[str] = []
    for p in svelte_files:
        hits = _hue_findings(p.read_text())
        if hits:
            offenders.append(f"{p.relative_to(crate)}: {'; '.join(hits)}")
    if offenders:
        fail(
            "#198: product Svelte must not contain hex / amber-* / yellow-* / "
            "black/80 (token definitions may live in app.css only). Found:\n  "
            + "\n  ".join(offenders)
        )

    css_path = crate / "web" / "app.css"
    if not css_path.is_file():
        fail("#198: web/app.css required (shadcn + bubble token definitions)")
    css = css_path.read_text()

    # 2) Existing shadcn token names still defined in app.css.
    missing_defs = [name for name in _SHADCN_TOKEN_DEFS if name not in css]
    if missing_defs:
        fail(
            "#198: app.css must keep existing shadcn tokens "
            f"({', '.join(missing_defs)} missing) — do not invent a new brand palette"
        )

    # 3) Bubbles stay distinct via existing --bubble-me / --bubble-them
    #    (or --color-bubble-*). Do not soften #111.
    me = _css_var(css, _BUBBLE_ME_VARS)
    them = _css_var(css, _BUBBLE_THEM_VARS)
    if not me or not them:
        fail(
            "#198: keep distinct bubble tokens --bubble-me / --bubble-them "
            "(or --color-bubble-*) in app.css"
        )
    if me == them:
        fail("#198: --bubble-me and --bubble-them must stay distinct colors")

    svelte_blob = "\n".join(p.read_text() for p in svelte_files)

    # 4) Product Svelte uses token / variable classes, not raw hues.
    missing_uses = [tok for tok in _SHADCN_TOKEN_USES if tok not in svelte_blob]
    if missing_uses:
        fail(
            "#198: product Svelte must use existing token/variable classes "
            f"({', '.join(missing_uses)} missing) rather than raw hues"
        )

    # 5) Targeted shadow language (not a full Tailwind linter; p-1 leftovers OK).
    shadow_hits = _token_hits(crate, svelte_files, _HEAVY_SHADOW)
    if shadow_hits:
        fail(
            "#198: product Svelte shadows must be shadow-sm / shadow-md only "
            "(no shadow-lg / shadow-xl / shadow-2xl). Found:\n  "
            + "\n  ".join(shadow_hits)
        )

    # 6) Not: gradients / new brand palette / CDN theme.
    gradient_hits = _token_hits(crate, svelte_files, _GRADIENT)
    if gradient_hits:
        fail(
            "#198: not in scope — no gradients (bg-gradient-* / from-* / to-* "
            "hero) in product Svelte. Found:\n  " + "\n  ".join(gradient_hits)
        )
    if _NEW_BRAND_VAR.search(css) or _NEW_BRAND_VAR.search(svelte_blob):
        fail(
            "#198: not in scope — no new brand palette "
            "(keep existing shadcn + bubble vars; do not add --brand)"
        )
    cdn_blob = svelte_blob + "\n" + css
    splash = crate / "index.html"
    if splash.is_file():
        cdn_blob += "\n" + splash.read_text()
    if _THEME_CDN.search(cdn_blob):
        fail(
            "#198: not in scope — no CDN theme "
            "(fonts.googleapis / cdn. / remote @import of a theme)"
        )

    # 7) Not: changing stored data (no SQLite migration / timestamp rewrite).
    rust_blob = ""
    src_dir = crate / "src"
    if src_dir.is_dir():
        rust_blob = "\n".join(p.read_text() for p in sorted(src_dir.rglob("*.rs")))
    api_path = crate / "web" / "lib" / "api.ts"
    api = api_path.read_text() if api_path.is_file() else ""
    if _SQL_DDL.search(rust_blob) or _SQL_DDL.search(svelte_blob) or _SQL_DDL.search(api):
        fail(
            "#198: not in scope — no SQLite migration / stored-data change "
            "(do not ALTER/CREATE TABLE from Tauri chrome)"
        )
    if api and not re.search(
        r"export type Person\s*=\s*\{[^}]*\blast_activity_at\??\s*:\s*string",
        api,
        re.S,
    ):
        fail(
            "#198: not in scope — do not rewrite last_activity_at / message "
            "timestamps (Person.last_activity_at stays ISO string on the API)"
        )

    # 8) D24: chrome colors come from design tokens / CSS variables, not raw hues.
    user_docs = repo_root() / "docs" / "user" / "app.md"
    hack_docs = repo_root() / "docs" / "hacking" / "tauri.md"
    dtxt = ""
    if user_docs.is_file():
        dtxt += user_docs.read_text()
    if hack_docs.is_file():
        dtxt += "\n" + hack_docs.read_text()
    if not dtxt.strip():
        fail(
            "#198: docs/user/app.md (and/or docs/hacking/tauri.md) required "
            "(chrome colors from design tokens / CSS variables)"
        )
    if not _DOCS_DESIGN_TOKENS.search(dtxt):
        fail(
            "#198: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "chrome colors come from design tokens / CSS variables"
        )
    if not _DOCS_NOT_RAW_HUES.search(dtxt):
        fail(
            "#198: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "chrome colors are not raw Tailwind hues"
        )


# #199 — typography: 14–15px bodies, 12–13px meta, system font, no remote font.
_TYPO_BODY_TW = re.compile(
    r"(?<![\w-])(text-sm|text-base|text-\[(?:14|15)(?:\.\d+)?px\])(?![\w-])"
)
_TYPO_META_TW = re.compile(
    r"(?<![\w-])(text-xs|text-\[(?:12|13)(?:\.\d+)?px\])(?![\w-])"
)
_TYPO_LEADING_NAMED = re.compile(
    r"(?<![\w-])(?:leading-normal|leading-relaxed)(?![\w-])"
)
_TYPO_LEADING_ARB = re.compile(r"(?<![\w-])leading-\[([^\]]+)\]")
_TYPO_LINE_HEIGHT = re.compile(r"line-height\s*:\s*([^;}]+)", re.I)
_TYPO_FONT_SIZE = re.compile(r"font-size\s*:\s*([^;}]+)", re.I)
_TYPO_GIANT = re.compile(
    r"(?<![\w-])text-(?:3xl|4xl|5xl|6xl|7xl|8xl|9xl)(?![\w-])"
)
_TYPO_REMOTE_FONT = re.compile(
    r"("
    r"fonts\.googleapis"
    r"|fonts\.gstatic"
    r"|use\.typekit\.net"
    r"|fonts\.adobe"
    r"|@import\s+(?:url\s*\(\s*)?['\"]https?://"
    r"|url\s*\(\s*['\"]?https?://[^)]*(?:font|\.woff2?|\.ttf|\.otf)"
    r")",
    re.I,
)
_TYPO_MUTED = re.compile(
    r"("
    r"text-muted-foreground"
    r"|text-\[var\(--(?:color-)?muted-foreground\)\]"
    r"|var\(--(?:color-)?muted-foreground\)"
    r")"
)
_TYPO_FONT_SANS = re.compile(r"--font-sans\s*:\s*([^;]+);")
_DOCS_TYPO_BODY = re.compile(
    r"("
    r"14\s*[–\-]\s*15\s*px"
    r"|(?:message )?bod(?:y|ies).{0,80}\bsizes?\b"
    r")",
    re.I,
)
_DOCS_TYPO_META = re.compile(
    r"("
    r"12\s*[–\-]\s*13\s*px"
    r"|\bmeta\b.{0,80}\bsizes?\b"
    r")",
    re.I,
)
_DOCS_TYPO_NO_REMOTE_FONT = re.compile(
    r"("
    r"no remote fonts?"
    r"|not (?:a |an )?remote fonts?"
    r"|system(?:-ui| UI)? fonts?"
    r"|no Google Fonts"
    r"|not.{0,48}(?:Google Fonts|fonts\.googleapis|CDN fonts?|remote fonts?)"
    r")",
    re.I,
)


def _typo_tag_class(attrs: str) -> str:
    m = re.search(r"\bclass\s*=\s*\"([^\"]*)\"", attrs)
    if m:
        return m.group(1)
    m = re.search(r"\bclass\s*=\s*'([^']*)'", attrs)
    if m:
        return m.group(1)
    m = re.search(r"\bclass\s*=\s*\{([^}]*)\}", attrs)
    if not m:
        return ""
    inner = m.group(1).strip()
    if len(inner) >= 2 and inner[0] == inner[-1] and inner[0] in "'\"`":
        return inner[1:-1]
    return "{" + inner + "}"


def _typo_tag_style(attrs: str) -> str:
    m = re.search(r"\bstyle\s*=\s*\"([^\"]*)\"", attrs)
    if m:
        return m.group(1)
    m = re.search(r"\bstyle\s*=\s*'([^']*)'", attrs)
    return m.group(1) if m else ""


def _typo_resolve_class(class_str: str, logic: str) -> str:
    parts = [class_str]
    for m in re.finditer(r"\{([A-Za-z_]\w*)\}", class_str):
        name = m.group(1)
        am = re.search(
            rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*[\"']([^\"']+)[\"']",
            logic,
        )
        if am:
            parts.append(am.group(1))
        am = re.search(
            rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*`([^`]+)`",
            logic,
        )
        if am:
            parts.append(am.group(1))
    return " ".join(parts)


def _typo_classes(class_str: str) -> list[str]:
    out: list[str] = []
    for tok in class_str.split():
        if tok and not tok.startswith("{") and not tok.startswith(":"):
            out.append(tok)
    return out


def _typo_css_blocks(css: str, classname: str) -> list[str]:
    return [
        m.group(1)
        for m in re.finditer(
            rf"\.{re.escape(classname)}\b[^{{]*\{{([^}}]*)\}}",
            css,
        )
    ]


def _typo_unitless_lh(raw: str) -> float | None:
    val = raw.strip().lower().rstrip(";")
    if val.endswith("%"):
        try:
            return float(val[:-1]) / 100.0
        except ValueError:
            return None
    if re.fullmatch(r"1\.\d+", val):
        return float(val)
    return None


def _typo_lh_in_range(raw: str) -> bool:
    n = _typo_unitless_lh(raw)
    return n is not None and 1.5 <= n <= 1.625


def _typo_px(raw: str) -> float | None:
    val = raw.strip().lower()
    m = re.fullmatch(r"([\d.]+)\s*px", val)
    if m:
        return float(m.group(1))
    m = re.fullmatch(r"([\d.]+)\s*rem", val)
    if m:
        return float(m.group(1)) * 16.0
    return None


def _typo_size_token(class_str: str, css: str, kind: str) -> str | None:
    rx = _TYPO_BODY_TW if kind == "body" else _TYPO_META_TW
    m = rx.search(class_str)
    if m:
        return m.group(1)
    lo, hi = (14.0, 15.0) if kind == "body" else (12.0, 13.0)
    for cls in _typo_classes(class_str):
        for block in _typo_css_blocks(css, cls):
            fm = _TYPO_FONT_SIZE.search(block)
            if not fm:
                continue
            px = _typo_px(fm.group(1).strip())
            if px is not None and lo <= px <= hi:
                return f".{cls}"
    return None


def _typo_theme_lh_ok(css: str, tw_token: str) -> bool:
    key = {"text-sm": "sm", "text-base": "base", "text-xs": "xs"}.get(tw_token)
    if not key:
        return False
    m = re.search(
        rf"--text-{re.escape(key)}--line-height\s*:\s*([^;]+);",
        css,
    )
    return bool(m) and _typo_lh_in_range(m.group(1))


def _typo_leading_ok(class_str: str, style: str, css: str) -> bool:
    if _TYPO_LEADING_NAMED.search(class_str):
        return True
    for m in _TYPO_LEADING_ARB.finditer(class_str):
        if _typo_lh_in_range(m.group(1)):
            return True
    if style:
        hm = _TYPO_LINE_HEIGHT.search(style)
        if hm and _typo_lh_in_range(hm.group(1)):
            return True
    tw = _TYPO_BODY_TW.search(class_str)
    if tw and _typo_theme_lh_ok(css, tw.group(1)):
        return True
    for cls in _typo_classes(class_str):
        for block in _typo_css_blocks(css, cls):
            hm = _TYPO_LINE_HEIGHT.search(block)
            if hm and _typo_lh_in_range(hm.group(1)):
                return True
    return False


def _typo_muted_ok(class_str: str, css: str) -> bool:
    if _TYPO_MUTED.search(class_str):
        return True
    for cls in _typo_classes(class_str):
        for block in _typo_css_blocks(css, cls):
            if _TYPO_MUTED.search(block) or re.search(
                r"color\s*:\s*var\(--(?:color-)?muted-foreground\)",
                block,
                re.I,
            ):
                return True
    return False


def _typo_prewrap_attrs(src: str, inner_rx: re.Pattern[str]) -> list[str]:
    found: list[str] = []
    for m in _PRE_WRAP.finditer(src):
        if inner_rx.search(m.group(3)):
            found.append(m.group(2))
    return found


def _typo_docs_blob() -> str:
    user_docs = repo_root() / "docs" / "user" / "app.md"
    hack_docs = repo_root() / "docs" / "hacking" / "tauri.md"
    dtxt = ""
    if user_docs.is_file():
        dtxt += user_docs.read_text()
    if hack_docs.is_file():
        dtxt += "\n" + hack_docs.read_text()
    return dtxt


def assert_typography(crate: Path) -> None:
    """#199: 14–15px bodies with line-height 1.5–1.6; 12–13px meta.

    Timeline bodies and search snippets share one body size. People-row
    time/preview and bubble captions share one meta size + muted-foreground.
    Headings stay restrained (no text-3xl+). --font-sans stays system UI.
    No remote font. Do not t() bodies. Docs: 14–15px bodies, 12–13px meta,
    no remote font.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#199: App.svelte required (timeline body / people-row typography)")
    css_path = crate / "web" / "app.css"
    if not css_path.is_file():
        fail("#199: web/app.css required (--font-sans system UI stack)")
    css = css_path.read_text()
    logic = _web_logic(crate)
    timeline = _timeline_block(crate)
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#199: SearchPane.svelte required (search snippet typography)")
    search = search_path.read_text()

    # 1) Timeline + search bodies exist and share one 14–15px size.
    tl_attrs = _typo_prewrap_attrs(
        timeline,
        re.compile(r"displayBody|body_text|bodyText"),
    )
    if not tl_attrs:
        fail(
            "#199: timeline message bodies must stay whitespace-pre-wrap "
            "text nodes (14–15px body size)"
        )
    search_attrs = _typo_prewrap_attrs(
        search,
        re.compile(r"splitSnippet|\.snippet\b|\{body\}"),
    )
    if not search_attrs:
        fail(
            "#199: search snippets / expanded hits must stay "
            "whitespace-pre-wrap text nodes (14–15px body size)"
        )

    body_tokens: list[str] = []
    body_surfaces: list[tuple[str, str, str]] = []
    for label, attrs in (
        *[("timeline", a) for a in tl_attrs],
        *[("search snippet / expanded hit", a) for a in search_attrs],
    ):
        class_str = _typo_resolve_class(_typo_tag_class(attrs), logic)
        tok = _typo_size_token(class_str, css, "body")
        if not tok:
            fail(
                "#199: timeline message bodies and search snippets must use "
                "one body size in the 14–15px range (text-sm / text-base / "
                "text-[14px] / text-[15px])"
            )
        body_tokens.append(tok)
        body_surfaces.append((label, class_str, _typo_tag_style(attrs)))
    if len(set(body_tokens)) != 1:
        fail(
            "#199: timeline bodies and search snippets must share one body "
            "size class (14–15px: text-sm / text-base / text-[14px] / "
            "text-[15px]). Found: " + ", ".join(sorted(set(body_tokens)))
        )

    # 2) Those bodies use line-height 1.5–1.6 (the gap on current master).
    missing_lh = []
    for label, class_str, style in body_surfaces:
        if not _typo_leading_ok(class_str, style, css):
            if label not in missing_lh:
                missing_lh.append(label)
    if missing_lh:
        fail(
            "#199: timeline + search snippet bodies must use line-height "
            "1.5–1.6 (leading-normal / leading-relaxed / leading-[1.5] / "
            "leading-[1.6] / CSS line-height: 1.5–1.6)"
        )

    # 3) People-row time/preview + bubble caption share one 12–13px meta.
    _, people_each = _people_list_a11y_surfaces(crate)
    if not people_each.strip():
        markup = _strip_html_comments(_svelte_markup(app_path.read_text()))
        people_each = _people_each_block(markup)
    if not people_each.strip():
        fail("#199: people list {#each filtered} required (time / preview meta)")
    people_meta: list[str] = []
    for m in re.finditer(r"<span\b([^>]*)>(.*?)</span>", people_each, re.S):
        attrs, inner = m.group(1), m.group(2)
        if re.search(r"last_activity_at|humanTime|\.preview\b", inner):
            people_meta.append(attrs)
    if not people_meta:
        fail(
            "#199: people-list rows must show time / preview as 12–13px meta "
            "(text-xs / text-[12px] / text-[13px])"
        )
    caption_meta: list[str] = []
    for m in re.finditer(
        r"<([a-zA-Z][\w:-]*)\b([^>]*\bclass\s*=\s*[\"'][^\"']*\bcaption\b[^\"']*[\"'][^>]*)>",
        timeline,
    ):
        caption_meta.append(m.group(2))
    if not caption_meta:
        fail(
            "#199: bubble captions (time + platform chip) must keep a caption "
            "element with 12–13px meta"
        )

    meta_tokens: list[str] = []
    for attrs in (*people_meta, *caption_meta):
        class_str = _typo_resolve_class(_typo_tag_class(attrs), logic)
        tok = _typo_size_token(class_str, css, "meta")
        if not tok:
            fail(
                "#199: people-list rows (time / preview) and bubble captions "
                "must use one meta size in the 12–13px range (text-xs / "
                "text-[12px] / text-[13px])"
            )
        if not _typo_muted_ok(class_str, css):
            fail(
                "#199: people-list rows (time / preview) and bubble captions "
                "must use muted-foreground for meta"
            )
        meta_tokens.append(tok)
    if len(set(meta_tokens)) != 1:
        fail(
            "#199: people-list rows and bubble captions must share one meta "
            "size class (12–13px: text-xs / text-[12px] / text-[13px]). "
            "Found: " + ", ".join(sorted(set(meta_tokens)))
        )

    # 4) Headings stay restrained — no display type in product Svelte.
    svelte_files = _product_svelte(crate)
    giant = _token_hits(crate, svelte_files, _TYPO_GIANT)
    if giant:
        fail(
            "#199: headings stay restrained — no text-3xl / text-4xl / "
            "text-5xl / text-6xl / text-7xl / text-8xl / text-9xl in product "
            "Svelte (text-xl / text-2xl on setup is OK). Found:\n  "
            + "\n  ".join(giant)
        )

    # 5) --font-sans stays system UI; no remote font load.
    fm = _TYPO_FONT_SANS.search(css)
    if not fm:
        fail("#199: app.css must keep --font-sans as the system UI stack")
    stack = fm.group(1)
    if "ui-sans-serif" not in stack or "-apple-system" not in stack:
        fail(
            "#199: --font-sans must stay system UI "
            "(ui-sans-serif and -apple-system still present)"
        )
    font_blob = css + "\n" + "\n".join(p.read_text() for p in svelte_files)
    splash = crate / "index.html"
    if splash.is_file():
        font_blob += "\n" + splash.read_text()
    if _TYPO_REMOTE_FONT.search(font_blob) or _THEME_CDN.search(font_blob):
        fail(
            "#199: no Google Fonts / CDN / remote @import of a font "
            "(fonts.googleapis / fonts.gstatic / remote url())"
        )

    # 6) Not: t() of message bodies / previews.
    helpers = _chrome_helper_names(logic)
    body_blob = logic + "\n" + app_path.read_text() + "\n" + search
    if _chrome_helper_on_body(body_blob, helpers) or _BODY_T_CALL.search(body_blob):
        fail("#199: do not t() message bodies or previews (t(body_text) / t(preview))")

    # 7) D24: 14–15px bodies, 12–13px meta, no remote font.
    dtxt = _typo_docs_blob()
    if not dtxt.strip():
        fail(
            "#199: docs/user/app.md (and/or docs/hacking/tauri.md) required "
            "(14–15px bodies, 12–13px meta, no remote font)"
        )
    if not _DOCS_TYPO_BODY.search(dtxt):
        fail(
            "#199: docs/user/app.md (and/or docs/hacking/tauri.md) must mention "
            "14–15px bodies (or body size)"
        )
    if not _DOCS_TYPO_META.search(dtxt):
        fail(
            "#199: docs/user/app.md (and/or docs/hacking/tauri.md) must mention "
            "12–13px meta (or meta size)"
        )
    if not _DOCS_TYPO_NO_REMOTE_FONT.search(dtxt):
        fail(
            "#199: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "system font / no remote font"
        )


# #200 — Lucide chrome icons: play/pause, lightbox close, empty-state.
# Conservative emoji-as-icon ban on those surfaces only (not message bodies).
_ICON_EMOJI_GLYPH = re.compile(r"[▶❚✓✕✖❌✨]")
_LUCIDE_DEFAULT = re.compile(
    r"import\s+(\w+)\s+from\s+[\"']@lucide/svelte/icons/([\w-]+)[\"']"
)
_LUCIDE_NAMED = re.compile(
    r"import\s+\{([^}]+)\}\s+from\s+[\"']@lucide/svelte[\"']"
)
_LUCIDE_BARE = re.compile(
    r"import\s+(\w+)\s+from\s+[\"']@lucide/svelte[\"']"
)
_ICON_SIZE_16 = re.compile(
    r"("
    r"(?<![\w-])(?:size-4|w-4|h-4)(?![\w-])"
    r"|size\s*=\s*(?:\{\s*16\s*\}|[\"']16[\"'])"
    r"|(?:width|height)\s*=\s*(?:\{\s*16\s*\}|[\"']16(?:px)?[\"'])"
    r"|(?:width|height)\s*:\s*16px"
    r")"
)
_ICON_SIZE_20 = re.compile(
    r"("
    r"(?<![\w-])(?:size-5|w-5|h-5)(?![\w-])"
    r"|size\s*=\s*(?:\{\s*20\s*\}|[\"']20[\"'])"
    r"|(?:width|height)\s*=\s*(?:\{\s*20\s*\}|[\"']20(?:px)?[\"'])"
    r"|(?:width|height)\s*:\s*20px"
    r")"
)
_OTHER_ICON_PKG = re.compile(
    r"[\"']("
    r"react-icons(?:/[^\"']+)?"
    r"|@heroicons/[^\"']+"
    r"|heroicons"
    r"|@fortawesome/[^\"']+"
    r"|font-?awesome(?:/[^\"']+)?"
    r"|@tabler/[^\"']+"
    r"|@iconify(?:-[a-z]+)?/[^\"']+"
    r"|@iconify-json/[^\"']+"
    r"|iconify(?:-[a-z]+)?"
    r")[\"']",
    re.I,
)
_OTHER_ICON_IMPORT = re.compile(
    r"from\s+[\"']("
    r"react-icons"
    r"|@heroicons/"
    r"|heroicons"
    r"|@fortawesome/"
    r"|font-?awesome"
    r"|@tabler/"
    r"|@iconify"
    r"|iconify"
    r")",
    re.I,
)
_ICON_CDN = re.compile(
    r"("
    r"fonts\.googleapis"
    r"|cdn\."
    r"|unpkg(?:\.com)?"
    r"|jsdelivr"
    r"|api\.iconify"
    r"|iconify\.design"
    r")",
    re.I,
)
_EMPTY_MASCOT = re.compile(
    r"("
    r"\billustration\b"
    r"|\bmascot\b"
    r"|<svg\b"
    r"|<img\b"
    r")",
    re.I,
)
_BRAND_LOGO_IMG = re.compile(
    r"("
    r"<img\b[^>]*(?:whatsapp|gmail|gstatic|googleusercontent)[^>]*>"
    r"|src\s*=\s*[\"']https?://[^\"']*(?:whatsapp|gmail|gstatic)"
    r")",
    re.I,
)
_DOCS_LUCIDE_CHROME = re.compile(
    r"("
    r"lucide.{0,280}(?:play|pause|lightbox|empty)"
    r"|(?:play|pause|lightbox|empty|chrome icons?).{0,280}lucide"
    r")",
    re.I | re.S,
)
_DOCS_LUCIDE_NOT_EMOJI = re.compile(
    r"("
    r"not emoji(?:[- ]as[- ]icon)?(?: glyphs?)?"
    r"|not.{0,80}emoji glyphs?"
    r"|lucide.{0,80}not emoji"
    r"|chrome icons?.{0,80}not emoji"
    r"|not.{0,48}(?:▶|❚❚|text glyphs?)"
    r")",
    re.I,
)
_NAV_LABEL_KEYS = ("people", "search", "review", "import", "doctor")


def _lucide_surface(text: str) -> str:
    return _without_comments(_strip_html_comments(text))


def _lucide_bindings(src: str) -> list[tuple[str, str]]:
    """Local name + lucide icon id from `@lucide/svelte` imports."""
    out: list[tuple[str, str]] = []
    for m in _LUCIDE_DEFAULT.finditer(src):
        out.append((m.group(1), m.group(2).lower()))
    for m in _LUCIDE_NAMED.finditer(src):
        for part in m.group(1).split(","):
            part = part.strip()
            if not part:
                continue
            bits = re.split(r"\s+as\s+", part)
            export = bits[0].strip()
            local = bits[-1].strip()
            if export and local:
                out.append((local, export.lower()))
    for m in _LUCIDE_BARE.finditer(src):
        out.append((m.group(1), m.group(1).lower()))
    return out


def _lucide_ids(bindings: list[tuple[str, str]]) -> set[str]:
    return {path for _, path in bindings}


def _lucide_open_tags(block: str, names: set[str]) -> list[str]:
    if not names:
        return []
    alt = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    return re.findall(rf"<(?:{alt})\b([^>]*?)/?>", block, re.S)


def _lucide_used(block: str, names: set[str]) -> set[str]:
    return {n for n in names if re.search(rf"<{re.escape(n)}\b", block)}


def _lucide_attr_block(src: str, attr: str) -> str:
    m = re.search(
        rf"<([A-Za-z][\w:.-]*)\b([^>]*\b{re.escape(attr)}\b[^>]*)>",
        src,
        re.S,
    )
    if not m:
        return ""
    open_tag = m.group(0)
    name = m.group(1)
    if open_tag.rstrip().endswith("/>") or name.lower() in _VOID_HTML:
        return open_tag
    close = re.search(rf"</{re.escape(name)}\s*>", src[m.end() :], re.I)
    if not close:
        return src[m.start() : m.end() + 480]
    return src[m.start() : m.end() + close.end()]


def _lucide_files_with(crate: Path, needle: str) -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    for p in _product_svelte(crate):
        text = p.read_text()
        if needle in text:
            found.append((p, text))
    return found


def assert_lucide_icons(crate: Path) -> None:
    """#200: chrome icons are Lucide (@lucide/svelte), not glyphs / CDN.

    Voice play/pause and lightbox close are 16px Lucide. EmptyState shows a
    20px Lucide. Keep data-voice-play / data-lightbox-close / data-empty and
    play-pause behavior. No emoji-as-icon on those surfaces. No second icon
    package or CDN icon kit. Nav icons optional — text labels stay. Not:
    mascots, brand-logo images, #201/#202/#224. Docs: Lucide chrome icons,
    not emoji glyphs.
    """
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail("#200: CasAttach.svelte required (voice play/pause + lightbox close)")
    empty_path = crate / "web" / "lib" / "EmptyState.svelte"
    if not empty_path.is_file():
        fail("#200: EmptyState.svelte required (20px Lucide on data-empty)")
    pkg_path = crate / "package.json"
    if not pkg_path.is_file():
        fail("#200: crates/interlace-tauri/package.json required (@lucide/svelte)")

    # 1) Keep voice play/pause behavior; replace ▶ / ❚❚ with Lucide 16px.
    voice_files = _lucide_files_with(crate, "data-voice-play")
    if not voice_files:
        fail("#200: keep data-voice-play on the voice play/pause control")
    voice_blob = "\n".join(text for _, text in voice_files)
    if not re.search(
        r"("
        r"togglePlay"
        r"|\.play\s*\("
        r"|\.pause\s*\("
        r"|aria-label\s*=\s*\{[^}]*(?:[Pp]lay|[Pp]ause)"
        r")",
        voice_blob,
    ):
        fail(
            "#200: keep voice play/pause behavior "
            "(togglePlay / .play()/.pause() / aria-label Play or Pause)"
        )
    if _ICON_EMOJI_GLYPH.search(_lucide_surface(voice_blob)):
        fail(
            "#200: voice play/pause must be Lucide, not ▶ / ❚❚ text glyphs "
            "(keep data-voice-play)"
        )
    voice_bindings = _lucide_bindings(voice_blob)
    voice_ids = _lucide_ids(voice_bindings)
    if "play" not in voice_ids or "pause" not in voice_ids:
        fail(
            "#200: voice play/pause must import Lucide Play / Pause "
            "from @lucide/svelte (keep data-voice-play)"
        )
    voice_names = {local for local, path in voice_bindings if path in {"play", "pause"}}
    voice_blocks = [
        _lucide_attr_block(text, "data-voice-play") or text for _, text in voice_files
    ]
    voice_used = set()
    for block in voice_blocks:
        voice_used |= _lucide_used(block, voice_names)
    if voice_used != voice_names:
        fail(
            "#200: data-voice-play must render Lucide Play / Pause "
            "(not ▶ / ❚❚ text glyphs)"
        )
    voice_tags = []
    for block in voice_blocks:
        voice_tags.extend(_lucide_open_tags(block, voice_used))
    if not voice_tags or any(not _ICON_SIZE_16.search(tag) for tag in voice_tags):
        fail(
            "#200: voice play/pause Lucide icons must be 16px default "
            "(size-4 / w-4 h-4 / size={16})"
        )

    # 2) Lightbox close is Lucide (dialog X is the pattern) at 16px.
    close_files = _lucide_files_with(crate, "data-lightbox-close")
    if not close_files:
        fail("#200: keep data-lightbox-close on the lightbox close control")
    close_blob = "\n".join(text for _, text in close_files)
    if not re.search(
        r"aria-label\s*=\s*[\"'][^\"']*[Cc]lose[^\"']*[\"']",
        close_blob,
    ):
        fail(
            "#200: lightbox close must keep an accessible name "
            "(aria-label \"Close photo\")"
        )
    close_bindings = _lucide_bindings(close_blob)
    close_names = {local for local, _ in close_bindings}
    if not close_names:
        fail(
            "#200: lightbox close (data-lightbox-close) must use a Lucide icon "
            "imported from @lucide/svelte (dialog X is the pattern)"
        )
    close_blocks = [
        _lucide_attr_block(text, "data-lightbox-close") or text
        for _, text in close_files
    ]
    close_used: set[str] = set()
    for block in close_blocks:
        close_used |= _lucide_used(block, close_names)
    if not close_used:
        fail(
            "#200: data-lightbox-close must render a Lucide icon "
            "(import from @lucide/svelte; dialog X is the pattern)"
        )
    close_tags: list[str] = []
    for block in close_blocks:
        close_tags.extend(_lucide_open_tags(block, close_used))
    if not close_tags or any(not _ICON_SIZE_16.search(tag) for tag in close_tags):
        fail(
            "#200: lightbox close Lucide icon must be 16px "
            "(size-4 / w-4 h-4 / size={16})"
        )

    # 3) EmptyState: 20px Lucide; keep title/body; not a mascot / network img.
    empty = empty_path.read_text()
    if "data-empty" not in empty:
        fail("#200: EmptyState must keep data-empty")
    if not re.search(r"\{title\}", empty) or not re.search(r"\{body\}", empty):
        fail("#200: EmptyState must keep title / body text")
    empty_bindings = _lucide_bindings(empty)
    empty_names = {local for local, _ in empty_bindings}
    if not empty_names:
        fail(
            "#200: EmptyState (data-empty) must import a Lucide icon "
            "from @lucide/svelte at 20px (size-5 / w-5 h-5 / 20)"
        )
    empty_block = _lucide_attr_block(empty, "data-empty") or empty
    empty_used = _lucide_used(empty_block, empty_names) or _lucide_used(
        empty, empty_names
    )
    if not empty_used:
        fail(
            "#200: EmptyState (data-empty) must render a Lucide icon "
            "at 20px (size-5 / w-5 h-5 / 20)"
        )
    empty_tags = _lucide_open_tags(empty, empty_used)
    if not empty_tags or any(not _ICON_SIZE_20.search(tag) for tag in empty_tags):
        fail(
            "#200: EmptyState Lucide icon must be 20px "
            "(size-5 / w-5 h-5 / size={20}) — not a mascot / illustration"
        )
    # Ban illustrated mascots / network <img> in EmptyState. Lucide is a
    # component import, not a raw <svg> scene or remote <img>.
    if _EMPTY_MASCOT.search(_lucide_surface(empty)):
        fail(
            "#200: EmptyState must not use a mascot / illustration / <svg> "
            "scene / <img> (20px Lucide only; no network image)"
        )

    # 4) No emoji-as-icon on play/pause / close / empty (not message bodies).
    surface_blob = "\n".join(
        [
            *[block for block in voice_blocks if block],
            *[block for block in close_blocks if block],
            empty_block,
        ]
    )
    if _ICON_EMOJI_GLYPH.search(_lucide_surface(surface_blob)):
        fail(
            "#200: no emoji-as-icon on play/pause / lightbox close / empty "
            "(▶ ❚ ✓ ✕ ✖ ❌ ✨) — message bodies are not this check"
        )

    # 5) @lucide/svelte stays; no second icon pack.
    pkg = pkg_path.read_text()
    if '"@lucide/svelte"' not in pkg:
        fail(
            "#200: package.json must keep @lucide/svelte "
            "(do not add a second icon package)"
        )
    if _OTHER_ICON_PKG.search(pkg):
        fail(
            "#200: do not add a second icon package "
            "(react-icons / heroicons / fontawesome / @tabler / iconify) — "
            "use @lucide/svelte already in the crate"
        )
    svelte_blob = "\n".join(p.read_text() for p in _product_svelte(crate))
    if _OTHER_ICON_IMPORT.search(svelte_blob):
        fail(
            "#200: product Svelte must import icons from @lucide/svelte only "
            "(no react-icons / heroicons / fontawesome / @tabler / iconify)"
        )

    # 6) No CDN icon kit; no WhatsApp/Gmail CDN brand logos as icons.
    cdn_blob = svelte_blob
    css_path = crate / "web" / "app.css"
    if css_path.is_file():
        cdn_blob += "\n" + css_path.read_text()
    splash = crate / "index.html"
    if splash.is_file():
        cdn_blob += "\n" + splash.read_text()
    if _ICON_CDN.search(_lucide_surface(cdn_blob)):
        fail(
            "#200: no CDN icon kit "
            "(fonts.googleapis / cdn. / unpkg / jsdelivr / iconify API)"
        )
    if _BRAND_LOGO_IMG.search(_lucide_surface(svelte_blob)):
        fail(
            "#200: not in scope — no WhatsApp / Gmail CDN brand logos as icons"
        )

    # 7) Nav icons are optional; text labels must stay.
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#200: App.svelte required (nav text labels stay; icons optional)")
    app = app_path.read_text()
    nav_m = re.search(r"<nav\b[^>]*>[\s\S]*?</nav>", app, re.I)
    if not nav_m:
        fail("#200: App.svelte nav required (keep text labels; icons optional)")
    nav = nav_m.group(0)
    for key in _NAV_LABEL_KEYS:
        if not re.search(rf"""t\(\s*["']{key}["']\s*\)""", nav):
            fail(
                f"#200: nav must keep the {key} text label "
                "(icons are optional; do not replace labels with icon-only chrome)"
            )

    # 8) D24: Lucide chrome icons (play/pause / lightbox / empty), not emoji.
    dtxt = _typo_docs_blob()
    if not dtxt.strip():
        fail(
            "#200: docs/user/app.md (and/or docs/hacking/tauri.md) required "
            "(Lucide chrome icons, not emoji glyphs)"
        )
    if not _DOCS_LUCIDE_CHROME.search(dtxt):
        fail(
            "#200: docs/user/app.md (and/or docs/hacking/tauri.md) must mention "
            "Lucide chrome icons (play/pause, lightbox, empty)"
        )
    if not _DOCS_LUCIDE_NOT_EMOJI.search(dtxt):
        fail(
            "#200: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "chrome icons are Lucide, not emoji glyphs"
        )


# #201 — owned Tooltip, Separator, Badge, Card (no one-off chrome).
_OWNED_PRIMITIVES_201 = ("tooltip", "separator", "badge", "card")
_SECOND_UI_KIT = re.compile(
    r"[\"']("
    r"@radix-ui(?:/[^\"']*)?"
    r"|shadcn(?:-svelte)?"
    r"|@shadcn(?:/[^\"']*)?"
    r"|@skeletonlabs(?:/[^\"']*)?"
    r"|daisyui"
    r"|flowbite(?:-[a-z]+)?"
    r"|@ark-ui(?:/[^\"']*)?"
    r"|melt-ui"
    r")[\"']",
    re.I,
)
_CMD_PALETTE_PKG = re.compile(r"[\"'](?:cmdk|svelte-command(?:-palette)?)[\"']", re.I)
_TOAST_SONNER_PKG = re.compile(r"[\"'](?:sonner|svelte-sonner)[\"']", re.I)
_BITS_KIT_CDN = re.compile(
    r"("
    r"(?:unpkg(?:\.com)?|jsdelivr(?:\.net)?|esm\.sh|cdn\.)[^\"'\s)]*bits-ui"
    r"|bits-ui[^\"'\s)]*(?:unpkg|jsdelivr|esm\.sh)"
    r"|https?://[^\"'\s)]*(?:unpkg|jsdelivr|esm\.sh|cdn\.)[^\"'\s)]*"
    r"(?:bits-ui|@radix-ui|shadcn|daisyui|flowbite|melt-ui|skeletonlabs|ark-ui)"
    r")",
    re.I,
)
_NETWORK_AVATAR_IMG = re.compile(
    r"<img\b[^>]{0,400}\bsrc\s*=\s*[\"']https?://",
    re.I | re.S,
)
_DOCS_OWNED_CHIPS_BANNERS = re.compile(
    r"("
    r"(?:platform[- ]?chips?|banners?).{0,200}"
    r"(?:owned.{0,60})?(?:badge|card|shadcn[- ]?(?:svelte )?primitives?)"
    r"|(?:owned.{0,60})?(?:badge|card|shadcn[- ]?(?:svelte )?primitives?).{0,200}"
    r"(?:platform[- ]?chips?|banners?)"
    r")",
    re.I | re.S,
)
_DOCS_NOT_ONE_OFF_CHROME = re.compile(
    r"("
    r"not one-off(?: chrome)?"
    r"|not.{0,48}one-off chrome"
    r"|rather than one-off"
    r"|instead of one-off"
    r"|not hand-?rolled chrome"
    r")",
    re.I,
)
_DIALOG_FOOTER_BLOCK = re.compile(
    r"<Dialog\.Footer\b[^>]*>[\s\S]*?</Dialog\.Footer>",
    re.I,
)


def _owned_import_path_rx(name: str) -> str:
    return (
        r"[\"'](?:\$lib/|(?:\.\.?/)*)(?:lib/)?"
        rf"components/ui/{re.escape(name)}"
        r"(?:/[^\"']*)?[\"']"
    )


def _owned_imported_names(src: str, name: str) -> list[str]:
    """Local identifiers imported from `$lib/components/ui/{name}` (or relative)."""
    path = _owned_import_path_rx(name)
    out: list[str] = []
    for m in re.finditer(rf"import\s+\{{([^}}]+)\}}\s+from\s+{path}", src):
        for part in m.group(1).split(","):
            part = part.strip()
            if not part:
                continue
            bits = re.split(r"\s+as\s+", part)
            local = bits[-1].strip()
            if local:
                out.append(local)
    for m in re.finditer(rf"import\s+\*\s+as\s+(\w+)\s+from\s+{path}", src):
        out.append(m.group(1))
    for m in re.finditer(rf"import\s+(\w+)\s+from\s+{path}", src):
        out.append(m.group(1))
    return out


def _owned_tag_match(tag: str, names: list[str]) -> bool:
    tag_l = tag.lower()
    for n in names:
        nl = n.lower()
        if tag_l == nl or tag_l.startswith(nl + "."):
            return True
    return False


def _owned_used_in(block: str, names: list[str]) -> bool:
    for n in names:
        if re.search(rf"<{re.escape(n)}(?:\.\w+)?\b", block):
            return True
    return False


def _hook_tag_name(src: str, hook: str) -> str:
    m = re.search(
        rf"<([A-Za-z][\w:.-]*)\b[^>]*\b{re.escape(hook)}\b",
        src,
        re.S,
    )
    return m.group(1) if m else ""


def _chip_hook_files(crate: Path) -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    for p in _product_svelte(crate):
        text = p.read_text()
        if re.search(r"\bdata-platform-chip\b|\bplatform-chip\b", text):
            found.append((p, text))
    return found


def _web_chrome_blob(crate: Path) -> str:
    parts: list[str] = []
    for p in _web_ts_sources(crate):
        parts.append(p.read_text())
    for extra in (
        crate / "web" / "app.css",
        crate / "index.html",
        crate / "web" / "index.html",
    ):
        if extra.is_file():
            parts.append(extra.read_text())
    return "\n".join(parts)


def assert_owned_primitives(crate: Path) -> None:
    """#201: own Tooltip, Separator, Badge, Card — no one-off chrome.

    Four primitive dirs under web/lib/components/ui/ (svelte + index.ts).
    Platform chip is Badge. A banner or dialog footer uses Card/Separator.
    bits-ui stays the local kit (no second library, no CDN). Not: network
    avatars, Command (#215), Toast (#204). Docs: owned Badge/Card for
    chips/banners, not one-off chrome.
    """
    ui = crate / "web" / "lib" / "components" / "ui"
    if not ui.is_dir():
        fail("#201: web/lib/components/ui/ required for owned primitives")

    # 1) Owned tooltip / separator / badge / card files exist.
    missing: list[str] = []
    for name in _OWNED_PRIMITIVES_201:
        d = ui / name
        if not d.is_dir():
            missing.append(f"{name}/")
            continue
        if not any(d.glob("*.svelte")):
            missing.append(f"{name}/*.svelte")
        if not (d / "index.ts").is_file():
            missing.append(f"{name}/index.ts")
    if missing:
        fail(
            "#201: missing owned primitives under web/lib/components/ui/ "
            "(tooltip, separator, badge, card — each needs at least one "
            ".svelte and index.ts). Missing: " + ", ".join(missing)
        )

    # 2) Platform chip is the Badge primitive (keep existing hooks).
    chip_files = _chip_hook_files(crate)
    if not chip_files:
        fail(
            "#201: keep data-platform-chip / platform-chip on the platform "
            "chip (implemented with the Badge primitive)"
        )
    badge_ok = False
    for _p, text in chip_files:
        names = _owned_imported_names(text, "badge")
        if not names:
            continue
        tag = _hook_tag_name(text, "data-platform-chip") or _hook_tag_name(
            text, "platform-chip"
        )
        if tag and _owned_tag_match(tag, names):
            badge_ok = True
            break
    if not badge_ok:
        fail(
            "#201: platform chip (data-platform-chip / platform-chip) must "
            "be the Badge primitive (import from $lib/components/ui/badge "
            "or relative components/ui/badge) — not a hand-rolled span"
        )

    # 3) At least one banner or dialog footer uses Card or Separator.
    chrome_ok = False
    for p in _product_svelte(crate):
        text = p.read_text()
        names = _owned_imported_names(text, "card") + _owned_imported_names(
            text, "separator"
        )
        if not names:
            continue
        if "data-cloud-warning" in text:
            block = _lucide_attr_block(text, "data-cloud-warning") or ""
            tag = _hook_tag_name(text, "data-cloud-warning")
            if _owned_tag_match(tag, names) or _owned_used_in(block, names):
                chrome_ok = True
                break
        for footer in _DIALOG_FOOTER_BLOCK.findall(text):
            if _owned_used_in(footer, names):
                chrome_ok = True
                break
        if chrome_ok:
            break
        footer_hook = _lucide_attr_block(text, "data-dialog-footer")
        if footer_hook and _owned_used_in(footer_hook, names):
            chrome_ok = True
            break
    if not chrome_ok:
        fail(
            "#201: at least one banner (data-cloud-warning) or dialog footer "
            "must use owned Card or Separator from "
            "$lib/components/ui/{card,separator}"
        )

    # 4) No second component library; bits-ui stays a local dep.
    pkg_path = crate / "package.json"
    if not pkg_path.is_file():
        fail("#201: crates/interlace-tauri/package.json required (bits-ui local)")
    pkg = pkg_path.read_text()
    if '"bits-ui"' not in pkg:
        fail(
            "#201: package.json must keep bits-ui as a local dependency "
            "(do not load bits-ui from a CDN)"
        )
    if _SECOND_UI_KIT.search(pkg):
        fail(
            "#201: package.json must not add a second component library "
            "(@radix-ui / shadcn / @skeletonlabs / daisyui / flowbite / "
            "@ark-ui / melt-ui) — extend owned primitives; bits-ui stays"
        )

    # 5) No bits-ui / component kit from CDN.
    if _BITS_KIT_CDN.search(_web_chrome_blob(crate)):
        fail(
            "#201: no bits-ui / component kit from CDN "
            "(unpkg / jsdelivr / cdn. / esm.sh)"
        )

    # 6) Not: network avatars, Command palette (#215), Toast (#204).
    svelte_blob = "\n".join(p.read_text() for p in _product_svelte(crate))
    if _NETWORK_AVATAR_IMG.search(svelte_blob):
        fail(
            "#201: not in scope — no network avatar <img src=\"http…\"> "
            "on people / chrome"
        )
    if _CMD_PALETTE_PKG.search(pkg):
        fail(
            "#201: not in scope — Command palette is #215 "
            "(do not add cmdk / svelte-command)"
        )
    if _TOAST_SONNER_PKG.search(pkg):
        fail(
            "#201: not in scope — Toast / sonner is #204 "
            "(do not add sonner / svelte-sonner)"
        )

    # 7) D24: owned Badge/Card (or owned shadcn primitives) for chips/banners.
    dtxt = _typo_docs_blob()
    if not dtxt.strip():
        fail(
            "#201: docs/user/app.md (and/or docs/hacking/tauri.md) required "
            "(owned Badge/Card for chips/banners, not one-off chrome)"
        )
    if not _DOCS_OWNED_CHIPS_BANNERS.search(dtxt):
        fail(
            "#201: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "platform chips / banners use owned Badge / Card "
            "(or owned shadcn primitives)"
        )
    if not _DOCS_NOT_ONE_OFF_CHROME.search(dtxt):
        fail(
            "#201: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "chips / banners are owned primitives, not one-off chrome"
        )


# #202 — EmptyState next action on every major empty view (no mascot).
# Titles stay English-grepable (#131). Action may be a label + handler,
# onclick, snippet, or Button/button child. Import idle may use data-empty
# instead of <EmptyState> if that hook still carries a next action.
_EMPTY_TITLES_202 = (
    ("App.svelte", "No people yet", "People: no people yet"),
    ("App.svelte", "No match", "People: no filter match"),
    ("SearchPane.svelte", "Type a query", "Search: no query"),
    ("SearchPane.svelte", "No hits", "Search: no hits"),
    ("ReviewPane.svelte", "Nothing to review", "Review: nothing to review"),
    ("App.svelte", "No messages in this view", "Timeline: no messages"),
    ("DoctorPane.svelte", "No doctor issues", "Doctor healthy"),
)
# IN.md: Select a person still needs a next action if that EmptyState stays.
_EMPTY_TITLES_202_OPTIONAL_IF_ABSENT = (
    ("App.svelte", "Select a person", "Timeline: select a person"),
)
_EMPTY_NEXT_ACTION = re.compile(
    r"("
    r"\baction(?:Label|Text|Click|Handler)?\s*="
    r"|\bprimaryAction\s*="
    r"|\bnextAction\s*="
    r"|\bcta(?:Label)?\s*="
    r"|\bonAction\s*="
    r"|\bonaction\s*="
    r"|\bonclick\s*="
    r"|\bon:click\s*="
    r"|\{#snippet\s+(?:action|children|cta)\b"
    r"|\{@render\s+(?:action|children|cta)\b"
    r"|<(?:Button|button)\b"
    r"|Pick file"
    r"|Clear filter"
    r")",
    re.I,
)
_EMPTY_OPTIONAL_ACTION = re.compile(
    r"("
    r"\baction(?:Label|Text|Click|Handler)?\s*\??\s*:"
    r"|\bprimaryAction\s*\??\s*:"
    r"|\bnextAction\s*\??\s*:"
    r"|\bcta(?:Label)?\s*\??\s*:"
    r"|\bonAction\s*\??\s*:"
    r"|\bonclick\s*\??\s*:"
    r"|children\s*\??\s*:"
    r"|\{#if\s+[^}]{0,120}(?:action|onclick|onAction|cta|children)\b"
    r"|\{@render\s+(?:action|children|cta)\b"
    r"|\{#snippet\s+(?:action|children|cta)\b"
    r")",
    re.I,
)
_EMPTY_GRADIENT = re.compile(r"\bbg-gradient(?:-|to-|\b)", re.I)
_SKELETON_PKG_202 = re.compile(
    r"[\"'](?:svelte-skeleton|skeleton-svelte|@skeletonlabs(?:/[^\"']*)?)[\"']",
    re.I,
)
_DOCS_EMPTY_NEXT_ACTION = re.compile(
    r"("
    r"empty(?:[- ]states?| views?)?.{0,120}(?:next action|helpful action)"
    r"|(?:next action|helpful action).{0,120}empty(?:[- ]states?| views?)?"
    r"|empty(?:[- ]states?| views?)?.{0,80}(?:import|clear filter|pick file)"
    r")",
    re.I | re.S,
)
_DOCS_EMPTY_NO_MASCOT = re.compile(
    r"("
    r"(?:empty(?:[- ]states?| views?)?).{0,80}(?:no |not |without ).{0,40}mascot"
    r"|no mascot.{0,80}empty"
    r"|not.{0,40}(?:a )?mascot"
    r")",
    re.I | re.S,
)


def _svelte_open_tag_at(src: str, start: int) -> str:
    """Open tag starting at src[start]=='<', aware of quotes and {…}."""
    n = len(src)
    j = start + 1
    q = None
    brace = 0
    while j < n:
        c = src[j]
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
            return src[start : j + 1]
        j += 1
    return src[start : start + 480]


def _empty_state_local_names(src: str) -> list[str]:
    names = ["EmptyState"]
    for m in re.finditer(
        r"import\s+(\w+)\s+from\s+[\"'][^\"']*EmptyState\.svelte[\"']",
        src,
    ):
        names.append(m.group(1))
    return list(dict.fromkeys(names))


def _empty_state_blocks(src: str) -> list[str]:
    """Each <EmptyState …> usage (local import alias OK), incl. children."""
    out: list[str] = []
    for name in _empty_state_local_names(src):
        for m in re.finditer(rf"<{re.escape(name)}\b", src):
            open_tag = _svelte_open_tag_at(src, m.start())
            if open_tag.rstrip().endswith("/>"):
                out.append(open_tag)
                continue
            close = re.search(
                rf"</{re.escape(name)}\s*>",
                src[m.start() + len(open_tag) :],
                re.I,
            )
            if not close:
                out.append(open_tag)
            else:
                out.append(src[m.start() : m.start() + len(open_tag) + close.end()])
    return out


def _empty_block_title(block: str) -> str:
    m = re.search(r"\btitle\s*=\s*[\"']([^\"']+)[\"']", block)
    if m:
        return m.group(1)
    m = re.search(r"\btitle\s*=\s*\{[\"']([^\"']+)[\"']\}", block)
    if m:
        return m.group(1)
    return ""


def _empty_usage_has_action(block: str) -> bool:
    return bool(_EMPTY_NEXT_ACTION.search(block))


def _empty_file(crate: Path, name: str) -> Path:
    if name == "App.svelte":
        return crate / "web" / "App.svelte"
    return crate / "web" / "lib" / name


def assert_empty_next_action(crate: Path) -> None:
    """#202: EmptyState next action on every major empty view, no mascot.

    Optional primary action uses owned Button. People / Search / Review /
    Timeline / Import idle / Doctor healthy wire a next action. Keep
    data-empty. No illustration / bg-gradient. Merge-picker EmptyState
    also needs an action if present. Not: skeletons (#203), toasts (#204),
    t() of imported bodies, command palette (#215). Docs: empty views
    have a next action, no mascot.
    """
    empty_path = crate / "web" / "lib" / "EmptyState.svelte"
    if not empty_path.is_file():
        fail("#202: EmptyState.svelte required (data-empty + optional Button action)")
    empty = empty_path.read_text()

    # 1) Keep data-empty / title / body (gates grep data-empty).
    if "data-empty" not in empty:
        fail("#202: EmptyState must keep data-empty")
    if not re.search(r"\{title\}", empty) or not re.search(r"\{body\}", empty):
        fail("#202: EmptyState must keep title / body text")

    # 2) Optional primary action rendered with owned Button.
    button_names = _owned_imported_names(empty, "button")
    if not button_names:
        fail(
            "#202: EmptyState must render an optional primary action with "
            "owned Button (import from $lib/components/ui/button or "
            "relative components/ui/button)"
        )
    empty_markup = _svelte_markup(empty)
    if not _owned_used_in(empty_markup, button_names) and not _owned_used_in(
        empty, button_names
    ):
        fail(
            "#202: EmptyState must render the optional primary action with "
            "owned Button (import from $lib/components/ui/button or "
            "relative components/ui/button)"
        )
    if not _EMPTY_OPTIONAL_ACTION.search(empty):
        fail(
            "#202: EmptyState primary action must be optional "
            "(label + handler, onclick, or snippet — not a required mascot CTA)"
        )

    # 3) No SVG mascot / illustration / gradient card on EmptyState.
    if _EMPTY_GRADIENT.search(empty):
        fail("#202: EmptyState must not use a gradient card (no bg-gradient)")
    if _EMPTY_MASCOT.search(_lucide_surface(empty)):
        fail(
            "#202: EmptyState must not use a mascot / illustration / <svg> "
            "scene / <img> (20px Lucide + next action; no marketing card)"
        )

    # 4) Listed views keep their empty copy and wire a next action.
    en_chrome = _chrome_en_text(crate)
    required_files = {fname for fname, _title, _why in _EMPTY_TITLES_202}
    file_text: dict[str, str] = {}
    for fname in required_files | {"ImportPane.svelte"} | {
        f for f, _t, _w in _EMPTY_TITLES_202_OPTIONAL_IF_ABSENT
    }:
        path = _empty_file(crate, fname)
        if not path.is_file():
            fail(f"#202: {fname} required (empty view with a next action)")
        file_text[fname] = path.read_text()

    for fname, title, why in _EMPTY_TITLES_202:
        blob = file_text[fname] + "\n" + en_chrome
        if title not in blob:
            fail(f"#202: keep {title!r} empty copy ({why})")
        all_blocks = _empty_state_blocks(file_text[fname])
        titled = [b for b in all_blocks if title in b]
        if not titled:
            # Title may live in the en pack; the file still needs EmptyState.
            if not all_blocks:
                fail(
                    f"#202: {why} must use EmptyState with a next action "
                    f"(keep {title!r}; keep data-empty grep-able)"
                )
            titled = all_blocks
        missing = [b for b in titled if not _empty_usage_has_action(b)]
        if missing:
            shown = _empty_block_title(missing[0]) or title
            fail(
                f"#202: {why} EmptyState ({shown!r}) must include a next action "
                "(action label / onclick / Button child)"
            )

    for fname, title, why in _EMPTY_TITLES_202_OPTIONAL_IF_ABSENT:
        titled = [b for b in _empty_state_blocks(file_text[fname]) if title in b]
        if not titled:
            continue
        missing = [b for b in titled if not _empty_usage_has_action(b)]
        if missing:
            fail(
                f"#202: {why} EmptyState ({title!r}) must include a next action "
                "(action label / onclick / Button child)"
            )

    # Every remaining EmptyState usage (merge-picker No match, …) needs an action.
    for p in _product_svelte(crate):
        if p.name == "EmptyState.svelte":
            continue
        text = p.read_text()
        for block in _empty_state_blocks(text):
            if _empty_usage_has_action(block):
                continue
            shown = _empty_block_title(block) or p.name
            fail(
                f"#202: EmptyState {shown!r} in {p.relative_to(crate)} must "
                "include a next action (action label / onclick / Button child)"
            )

    # 5) Import idle must gain EmptyState or data-empty with a next action.
    imp = file_text["ImportPane.svelte"]
    if "EmptyState" not in imp and "data-empty" not in imp:
        fail(
            "#202: Import idle must use EmptyState (or data-empty) with a "
            "next action (Pick file)"
        )
    import_ok = False
    for block in _empty_state_blocks(imp):
        if _empty_usage_has_action(block):
            import_ok = True
            break
    if not import_ok and "data-empty" in imp:
        hook = _lucide_attr_block(imp, "data-empty") or imp
        if _empty_usage_has_action(hook):
            import_ok = True
    if not import_ok:
        fail(
            "#202: Import idle EmptyState (or data-empty) must include a "
            "next action (Pick file)"
        )

    # 6) Not: skeletons (#203), toasts (#204), command palette (#215), t(bodies).
    pkg_path = crate / "package.json"
    pkg = pkg_path.read_text() if pkg_path.is_file() else ""
    if _SKELETON_PKG_202.search(pkg):
        fail("#202: not in scope — loading skeletons are #203")
    for p in _product_svelte(crate):
        stem = p.stem.lower()
        if stem.startswith("skeleton") or stem in {"skeleton", "skeletons"}:
            fail(
                "#202: not in scope — loading skeleton components are #203 "
                f"(found {p.relative_to(crate)})"
            )
    if _TOAST_SONNER_PKG.search(pkg):
        fail("#202: not in scope — toasts / sonner are #204")
    if _CMD_PALETTE_PKG.search(pkg):
        fail("#202: not in scope — command palette is #215")
    svelte_blob = "\n".join(p.read_text() for p in _product_svelte(crate))
    if _BODY_T_CALL.search(svelte_blob):
        fail(
            "#202: not in scope — do not t() imported bodies "
            "(body_text / preview / snippet)"
        )

    # 7) D24: empty views have a next action, no mascot.
    dtxt = _typo_docs_blob()
    if not dtxt.strip():
        fail(
            "#202: docs/user/app.md (and/or docs/hacking/tauri.md) required "
            "(empty views have a next action, no mascot)"
        )
    if not _DOCS_EMPTY_NEXT_ACTION.search(dtxt):
        fail(
            "#202: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "empty views have a next action (Import / clear filter / Pick file)"
        )
    if not _DOCS_EMPTY_NO_MASCOT.search(dtxt):
        fail(
            "#202: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "empty views have no mascot"
        )


# #203 — quiet muted skeleton on people / timeline / search in-flight.
_SKELETON_HOOK = re.compile(r"\bdata-skeleton\b")
_SKELETON_MUTED_BAR = re.compile(
    r"("
    r"\bbg-muted\b"
    r"|var\(--(?:color-)?muted\)"
    r")"
)
_SKELETON_ANIM = re.compile(
    r"("
    r"\banimate-(?:pulse|shimmer|skeleton)\b"
    r"|@keyframes\s+[\w-]*(?:shimmer|pulse|skeleton)[\w-]*"
    r"|animation\s*:\s*[^;\n}]*(?:shimmer|pulse|skeleton)"
    r")",
    re.I,
)
_SKELETON_JS_SHIMMER = re.compile(
    r"("
    r"requestAnimationFrame\s*\([^)]{0,80}(?:shimmer|skeleton|pulse)"
    r"|setInterval\s*\([^)]{0,80}(?:shimmer|skeleton|pulse)"
    r")",
    re.I,
)
_SKELETON_PKG_203 = re.compile(
    r"[\"'](?:svelte-skeleton|skeleton-svelte|@skeletonlabs(?:/[^\"']*)?"
    r"|react-loading-skeleton|react-content-loader)[\"']",
    re.I,
)
_SKELETON_SVG_ANIM = re.compile(r"<animate(?:Transform|Motion)?\b", re.I)
_DOCS_203_SKELETON = re.compile(
    r"("
    r"(?:quiet\s+)?(?:muted\s+)?skeleton.{0,240}(?:people|timeline|search)"
    r"|(?:people|timeline|search).{0,240}(?:quiet\s+)?(?:muted\s+)?skeleton"
    r")",
    re.I | re.S,
)
_DOCS_203_BOOT_STAYS = re.compile(
    r"("
    r"boot(?:\s*/\s*opening)?\s+spinner.{0,48}stay"
    r"|spinner stay"
    r"|boot spinner stays"
    r"|keep.{0,48}(?:boot|opening).{0,24}spinner"
    r")",
    re.I | re.S,
)
_DOCS_203_REDUCE_STATIC = re.compile(
    r"("
    r"reduced[- ]motion.{0,80}static"
    r"|static.{0,48}(?:bars|skeleton)"
    r")",
    re.I | re.S,
)
_SKELETON_REDUCE_STATIC = re.compile(
    r"("
    r"animation\s*:\s*none\b"
    r"|animation-duration\s*:\s*0(?:\.\d+)?(?:s|ms)?\b"
    r"|animation-iteration-count\s*:\s*1\b"
    r"|animate-none\b"
    r"|motion-reduce:animate-none\b"
    r")",
    re.I,
)


def _svelte_if_true_branch(src: str, cond: str) -> str:
    """True-branch of the first {#if …cond…} (stops at {:else} / {/if} depth 1)."""
    m = re.search(rf"\{{#if\s+[^}}]*\b{re.escape(cond)}\b[^}}]*\}}", src)
    if not m:
        return ""
    rest = src[m.end() :]
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
                return src[m.start() : m.end() + i]
            i += 3
            continue
        if depth == 1 and (
            rest.startswith("{:else", i)
            or rest.startswith("{:then", i)
            or rest.startswith("{:catch", i)
        ):
            return src[m.start() : m.end() + i]
        i += 1
    return src[m.start() :]


def _people_inflight_branch(src: str) -> tuple[str, str]:
    """Return (flag, {#if flag} true-branch) for the people-list in-flight window."""
    for flag in ("peopleLoading", "loadingPeople", "peopleBusy"):
        block = _svelte_if_true_branch(src, flag)
        if block:
            return flag, block
    return "", ""


def _owned_skeleton_names(src: str) -> list[str]:
    return _owned_imported_names(src, "skeleton")


def _has_skeleton_hook(block: str, owned_names: list[str]) -> bool:
    if not block:
        return False
    if _SKELETON_HOOK.search(block):
        return True
    return bool(owned_names) and _owned_used_in(block, owned_names)


def _skeleton_owned_files(crate: Path) -> list[Path]:
    ui = crate / "web" / "lib" / "components" / "ui" / "skeleton"
    if not ui.is_dir():
        return []
    return [p for p in ui.rglob("*") if p.suffix in {".svelte", ".ts", ".css"}]


def _docs_203_surfaces(dtxt: str) -> bool:
    for m in re.finditer(r"\bskeleton\b", dtxt, re.I):
        win = dtxt[max(0, m.start() - 220) : m.end() + 220]
        if (
            re.search(r"\bpeople\b", win, re.I)
            and re.search(r"\btimeline\b", win, re.I)
            and re.search(r"\bsearch\b", win, re.I)
        ):
            return True
    return False


def assert_loading_skeletons(crate: Path) -> None:
    """#203: quiet muted skeleton on people / timeline / search in-flight.

    Token bars (bg-muted / muted), data-skeleton and/or owned Skeleton.
    Keep #156 boot CSS spinner + “Opening last archive”. Search in-flight
    is not EmptyState “No hits” / “Type a query”. Reduced-motion: static
    bars (existing app.css reduce may count). Not: server %, every
    virtualized row, video splash, skeleton npm/CDN. Docs: quiet muted
    skeleton; boot spinner stays; reduced-motion is static.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#203: App.svelte required (people list + person timeline in-flight)")
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#203: SearchPane.svelte required (search hits in-flight)")
    app = app_path.read_text()
    search = search_path.read_text()
    css_path = crate / "web" / "app.css"
    css = css_path.read_text() if css_path.is_file() else ""
    pkg_path = crate / "package.json"
    pkg = pkg_path.read_text() if pkg_path.is_file() else ""

    people_flag, people_branch = _people_inflight_branch(app)
    if not people_branch:
        for region in _people_sidebar_regions(crate):
            flag, block = _people_inflight_branch(region)
            if block:
                people_flag, people_branch = flag, block
                break
    tl_branch = _svelte_if_true_branch(app, "tlLoading")
    search_branch = _svelte_if_true_branch(search, "searching")

    people_names = _owned_skeleton_names(app)
    search_names = _owned_skeleton_names(search)
    # 1) Three surfaces show a muted skeleton while in-flight.
    missing: list[str] = []
    if not _has_skeleton_hook(people_branch, people_names):
        missing.append("people list")
    if not _has_skeleton_hook(tl_branch, people_names):
        missing.append("person timeline")
    if not _has_skeleton_hook(search_branch, search_names):
        missing.append("search hits")
    if missing:
        fail(
            "#203: "
            + ", ".join(missing)
            + " must show a quiet muted skeleton while in-flight "
            "(data-skeleton and/or owned $lib/components/ui/skeleton)"
        )

    owned_files = _skeleton_owned_files(crate)
    skel_chrome = people_branch + "\n" + tl_branch + "\n" + search_branch
    for p in owned_files:
        skel_chrome += "\n" + p.read_text()

    # 2) Token bars — muted, not a raw amber/yellow shimmer.
    if not _SKELETON_MUTED_BAR.search(skel_chrome):
        fail(
            "#203: skeleton bars must use the muted token "
            "(bg-muted / var(--muted)), not a raw hue"
        )
    if _HUE_AMBER.search(skel_chrome) or _HUE_YELLOW.search(skel_chrome):
        fail("#203: skeleton must not use a raw amber/yellow shimmer")
    if _NET_IMG.search(skel_chrome) or _CDN_HINT.search(skel_chrome):
        fail("#203: skeleton must not load a CDN / network shimmer")

    # 3) Keep #156 boot / opening CSS spinner + exact copy. Do not require a skeleton.
    boot = _boot_opening_block(app)
    en_pack = _chrome_en_text(crate)
    if "Opening last archive" not in boot and "Opening last archive" not in app:
        if "Opening last archive" not in en_pack:
            fail(
                "#203: keep the #156 copy substring “Opening last archive” "
                "(do not replace the boot spinner with a skeleton)"
            )
    css_blob = "\n".join(p.read_text() for p in _web_sources(crate) if p.suffix == ".css")
    boot_with_css = boot + "\n" + css_blob
    if boot and not _has_css_spinner(boot) and not (
        (_SPINNER_NAME.search(boot) or re.search(r"animate-spin", boot))
        and _SPIN_ANIM.search(boot_with_css)
    ):
        fail(
            "#203: keep the #156 boot / opening CSS spinner — "
            "do not replace it with a skeleton"
        )

    # 4) Search in-flight is not EmptyState “No hits” / “Type a query”.
    if re.search(r"\bNo hits\b", search_branch):
        fail("#203: search in-flight must not be the EmptyState “No hits”")
    if re.search(r"\bType a query\b", search_branch):
        fail("#203: search in-flight must not be “Type a query” while searching")
    if "No hits" not in search and "No hits" not in en_pack:
        fail("#203: keep EmptyState “No hits” for the empty (not searching) branch")

    # People in-flight is not the #202 empty copy.
    if re.search(r"\bNo people yet\b", people_branch) or re.search(
        r"\bNo match\b", people_branch
    ):
        fail(
            "#203: people list must not show “No people yet” / “No match” while in-flight"
        )
    refresh = _function_body(app, "refreshPeople")
    if people_flag and refresh and not re.search(
        rf"\b{re.escape(people_flag)}\s*=\s*true\b", refresh
    ):
        fail(
            f"#203: refreshPeople must set {people_flag} = true while "
            "api.people() is in flight so the people skeleton can show"
        )

    # 5) prefers-reduced-motion → static bars. Existing app.css reduce may count.
    reduce_css = "\n".join(_css_prefers_reduced_blocks(css + "\n" + css_blob))
    has_skel_anim = bool(
        _SKELETON_ANIM.search(skel_chrome) or re.search(r"animate-pulse", skel_chrome)
    )
    if _SKELETON_JS_SHIMMER.search(skel_chrome) or _SKELETON_SVG_ANIM.search(skel_chrome):
        fail(
            "#203: prefers-reduced-motion: reduce → no animated shimmer on the "
            "skeletons (static bars; no JS / SVG shimmer that bypasses CSS)"
        )
    if has_skel_anim and not _SKELETON_REDUCE_STATIC.search(reduce_css):
        fail(
            "#203: prefers-reduced-motion: reduce → no animated shimmer on the "
            "skeletons (static bars; existing app.css reduce may count if it "
            "kills the CSS animation)"
        )

    # 6) Not in scope: server %, every virtualized row, video splash, npm/CDN kit.
    if _SERVER_PROGRESS.search(skel_chrome):
        fail("#203: not in scope — no percent progress from a server")
    if _SPLASH_VIDEO.search(skel_chrome) or _SPLASH_VIDEO.search(boot):
        fail("#203: not in scope — no video splash")
    if _SKELETON_PKG_203.search(pkg) or _SKELETON_PKG_202.search(pkg):
        fail("#203: not in scope — do not add a skeleton npm package / CDN shimmer kit")
    tl_rows = _timeline_block(crate)
    tl_owned = people_names
    if _SKELETON_HOOK.search(tl_rows) or _owned_used_in(tl_rows, tl_owned):
        fail(
            "#203: not in scope — do not skeleton every virtualized timeline row at once"
        )

    # 7) D24: quiet muted skeleton on people / timeline / search; boot spinner
    # stays; reduced-motion is static.
    dtxt = _typo_docs_blob()
    if not dtxt.strip():
        fail(
            "#203: docs/user/app.md (and/or docs/hacking/tauri.md) required "
            "(quiet muted skeleton on people / timeline / search)"
        )
    if not _docs_203_surfaces(dtxt) or not _DOCS_203_SKELETON.search(dtxt):
        fail(
            "#203: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "people / timeline / search show a quiet muted skeleton while loading "
            "(boot spinner stays; reduced-motion is static)"
        )
    if not _DOCS_203_BOOT_STAYS.search(dtxt):
        fail(
            "#203: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "the boot spinner stays"
        )
    if not _DOCS_203_REDUCE_STATIC.search(dtxt):
        fail(
            "#203: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "reduced-motion is static"
        )


# #203 follow-up — Load older must not mount the timeline skeleton; in-flight audible.
_APPEND_IDENT = re.compile(
    r"\b(tlAppending|isAppending|appending|tlAppend|appendFlag|appendMode|"
    r"loadingOlder|loadOlder|tlLoadOlder|olderLoading|isAppend|append)\b"
)
_REPLACE_IDENT = re.compile(
    r"\b(tlReplacing|isReplacing|replacing|tlReplace|fullReplace|isReplace)\b"
)
_ARIA_BUSY_STATIC = re.compile(
    r"""\baria-busy\s*=\s*(?:"true"|'true'|\{true\})""",
    re.I,
)
_ROLE_STATUS = re.compile(r"""\brole\s*=\s*(?:"status"|'status')""", re.I)
_SR_ONLY_CLASS = re.compile(r"\bsr-only\b")
_AUDIBLE_COPY = re.compile(r"(Loading|Searching|Busy|people|timeline)", re.I)
_SEARCHING_SUBMIT = re.compile(
    r"""searching\s*\?\s*["']Searching|(?<![\w])Searching(?:…|\.\.\.)""",
    re.I,
)
_LOAD_OLDER_SELECT_APPEND = re.compile(
    r"selectPerson\s*\(\s*[^,)]+\s*,\s*true\s*[,)]"
)


def _cond_code(cond: str) -> str:
    """Drop quoted strings so 'append' inside \"append\" is not a flag."""
    return re.sub(r"""(['\"])(?:\\.|(?!\1).)*\1""", '""', cond)


def _ident_negated(cond: str, ident: str) -> bool:
    if re.search(rf"!\s*{re.escape(ident)}\b", cond):
        return True
    if re.search(
        rf"\b{re.escape(ident)}\s*(?:===?|!==?)\s*(?:false|0|null|undefined)",
        cond,
    ):
        return True
    if re.search(
        rf"(?:false|0|null|undefined)\s*(?:===?|!==?)\s*{re.escape(ident)}\b",
        cond,
    ):
        return True
    return False


def _cond_hides_skeleton_on_append(cond: str) -> bool:
    """True if this {#if} is false while Load older / append is in flight."""
    code = _cond_code(cond)
    for ident in _APPEND_IDENT.findall(code):
        if _ident_negated(code, ident):
            return True
    for ident in _REPLACE_IDENT.findall(code):
        if not _ident_negated(code, ident):
            return True
    return False


def _cond_shows_skeleton_on_append(cond: str) -> bool:
    code = _cond_code(cond)
    for ident in _APPEND_IDENT.findall(code):
        if not _ident_negated(code, ident):
            return True
    for ident in _REPLACE_IDENT.findall(code):
        if _ident_negated(code, ident):
            return True
    return False


def _stack_hides_on_append(stack: list[tuple[str, str, str]]) -> bool:
    for kind, cond, _extra in stack:
        if kind == "if" and _cond_hides_skeleton_on_append(cond):
            return True
        if kind == "if-else" and _cond_shows_skeleton_on_append(cond):
            return True
    return False


def _guard_flags(stack: list[tuple[str, str, str]]) -> tuple[list[str], list[str]]:
    append_flags: list[str] = []
    replace_flags: list[str] = []
    for kind, cond, _extra in stack:
        code = _cond_code(cond)
        if kind == "if" and _cond_hides_skeleton_on_append(cond):
            for ident in _APPEND_IDENT.findall(code):
                if _ident_negated(code, ident):
                    append_flags.append(ident)
            for ident in _REPLACE_IDENT.findall(code):
                if not _ident_negated(code, ident):
                    replace_flags.append(ident)
        elif kind == "if-else" and _cond_shows_skeleton_on_append(cond):
            for ident in _APPEND_IDENT.findall(code):
                if not _ident_negated(code, ident):
                    append_flags.append(ident)
            for ident in _REPLACE_IDENT.findall(code):
                if _ident_negated(code, ident):
                    replace_flags.append(ident)
    return append_flags, replace_flags


def _svelte_if_true_branches(src: str, cond: str) -> list[str]:
    found: list[str] = []
    for m in re.finditer(rf"\{{#if\s+[^}}]*\b{re.escape(cond)}\b[^}}]*\}}", src):
        block = _svelte_if_true_branch(src[m.start() :], cond)
        if block:
            found.append(block)
    return found


def _skeleton_hook_positions(block: str, owned_names: list[str]) -> list[int]:
    pos: list[int] = []
    for m in _SKELETON_HOOK.finditer(block):
        pos.append(m.start())
    for n in owned_names:
        for m in re.finditer(rf"<{re.escape(n)}(?:\.\w+)?\b", block):
            pos.append(m.start())
    return sorted(set(pos))


def _select_person_append_param(src: str) -> str:
    m = re.search(r"(?:async\s+)?function\s+selectPerson\s*\(([^)]*)\)", src)
    if not m:
        return "append"
    params = [p.strip() for p in m.group(1).split(",") if p.strip()]
    if len(params) < 2:
        return "append"
    raw = re.sub(r":[^=]+", "", params[1])
    name = raw.split("=")[0].strip()
    return name or "append"


def _flag_assigned_from_append(fn: str, flag: str, append_param: str) -> bool:
    if re.search(
        rf"\b{re.escape(flag)}\s*=\s*(?:!!|Boolean\s*\(\s*)?{re.escape(append_param)}\b",
        fn,
    ):
        return True
    if re.search(
        rf"if\s*\(\s*{re.escape(append_param)}\s*\)\s*\{{[^}}]{{0,400}}"
        rf"\b{re.escape(flag)}\s*=\s*true",
        fn,
    ):
        return True
    if re.search(
        rf"if\s*\(\s*{re.escape(append_param)}\s*\)\s*{re.escape(flag)}\s*=\s*true",
        fn,
    ):
        return True
    return False


def _flag_cleared_on_append(fn: str, flag: str, append_param: str) -> bool:
    if re.search(rf"\b{re.escape(flag)}\s*=\s*!\s*{re.escape(append_param)}\b", fn):
        return True
    if re.search(
        rf"if\s*\(\s*{re.escape(append_param)}\s*\)[\s\S]{{0,200}}"
        rf"\b{re.escape(flag)}\s*=\s*(?:false|0|null)",
        fn,
    ):
        return True
    return False


def _flag_set_true_in(src: str, flag: str) -> bool:
    return bool(re.search(rf"\b{re.escape(flag)}\s*=\s*true\b", src))


def _open_person_clears_append_flag(src: str, flag: str) -> bool:
    body = _function_body(src, "openPersonAtMessage")
    if not body:
        return True
    if re.search(rf"\b{re.escape(flag)}\s*=\s*(?:false|0|null)", body):
        return True
    if re.search(r"\bselectPerson\s*\(", body):
        return True
    return False


def _aria_busy_bound_to(src: str, flag: str) -> bool:
    return bool(
        re.search(
            rf"\baria-busy\s*=\s*\{{[^}}]*\b{re.escape(flag)}\b[^}}]*\}}",
            src,
        )
    )


def _strip_aria_hidden_trees(src: str) -> str:
    rx = re.compile(
        r"<([A-Za-z][\w:.-]*)\b[^>]*\baria-hidden\b[^>]*(?:/>|>.*?</\1\s*>)",
        re.I | re.S,
    )
    prev = None
    out = src
    while prev != out:
        prev = out
        out = rx.sub(" ", out)
    return out


def _has_audible_status(src: str) -> bool:
    """role=status or sr-only copy that is not aria-hidden."""
    audible = _strip_aria_hidden_trees(src)
    for m in re.finditer(r"<([A-Za-z][\w:.-]*)\b([^>]*?)>", audible):
        attrs = m.group(2)
        if not (_ROLE_STATUS.search(attrs) or _SR_ONLY_CLASS.search(attrs)):
            continue
        rest = audible[m.end() : m.end() + 280]
        text = re.sub(r"<[^>]+>", " ", rest)
        if _AUDIBLE_COPY.search(text) or _AUDIBLE_COPY.search(rest):
            return True
    return False


def _inflight_is_audible(surface: str, branch: str, flag: str) -> bool:
    if flag and _aria_busy_bound_to(surface, flag):
        return True
    if flag and _aria_busy_bound_to(branch, flag):
        return True
    if _ARIA_BUSY_STATIC.search(branch):
        return True
    if _has_audible_status(branch) or _has_audible_status(surface):
        return True
    return False


def _region_window(src: str, hook: str, span: int = 8000) -> str:
    m = re.search(hook, src, re.I | re.S)
    if not m:
        return ""
    return src[m.start() : m.start() + span]


def assert_timeline_append_skeleton_guard(crate: Path) -> None:
    """#203 follow-up: timeline skeleton only on replace, never Load older.

    {#if tlLoading} may stay true so Load older stays disabled. Bars
    (data-skeleton / owned Skeleton) must sit behind an append /
    tlAppending (or equivalent) guard. selectPerson(..., true) must
    actually set that flag. openPersonAtMessage is a full replace.
    Do not require bars on Load older. Existing people / search hooks
    stay in assert_loading_skeletons.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#203: App.svelte required (timeline append must not mount the skeleton)")
    app = app_path.read_text()
    markup = _svelte_markup(app)
    names = _owned_skeleton_names(app)
    branches = _svelte_if_true_branches(markup, "tlLoading")
    if not branches:
        branches = _svelte_if_true_branches(app, "tlLoading")

    hooked = [(b, _skeleton_hook_positions(b, names)) for b in branches]
    hooked = [(b, pos) for b, pos in hooked if pos]
    if not hooked:
        # Replace path still needs a skeleton hook — existing #203 assert.
        return

    append_flags: list[str] = []
    replace_flags: list[str] = []
    unguarded = False
    for block, positions in hooked:
        for pos in positions:
            stack = _template_stack(block, pos)
            if _stack_hides_on_append(stack):
                af, rf = _guard_flags(stack)
                append_flags.extend(af)
                replace_flags.extend(rf)
                continue
            unguarded = True

    if unguarded:
        fail(
            "#203: {#if tlLoading} must not mount data-skeleton / <Skeleton> "
            "on Load older — guard with !append / !tlAppending (or equivalent)"
        )

    select_fn = _function_body(app, "selectPerson")
    append_param = _select_person_append_param(app)
    load_win = ""
    i = app.find("Load older")
    if i >= 0:
        load_win = app[max(0, i - 500) : i + 80]
    load_calls_append = bool(_LOAD_OLDER_SELECT_APPEND.search(load_win) or _LOAD_OLDER_SELECT_APPEND.search(app))

    wired = False
    for flag in dict.fromkeys(append_flags):
        if _flag_assigned_from_append(select_fn, flag, append_param):
            wired = True
        elif _flag_set_true_in(select_fn, flag) or _flag_set_true_in(load_win, flag):
            wired = True
        if not _open_person_clears_append_flag(app, flag):
            fail(
                "#203: openPersonAtMessage is a full replace — do not inherit "
                "a stale append / hide-bars flag (clear tlAppending or equivalent)"
            )
    for flag in dict.fromkeys(replace_flags):
        if _flag_cleared_on_append(select_fn, flag, append_param):
            wired = True
        if re.search(
            rf"\b{re.escape(flag)}\s*=\s*(?:true|!\s*{re.escape(append_param)})",
            select_fn,
        ):
            wired = True

    if load_calls_append and not wired:
        fail(
            "#203: Load older / selectPerson(..., true) must not show the "
            "timeline skeleton bars (set the append / tlAppending guard)"
        )


def assert_inflight_audible_status(crate: Path) -> None:
    """#203 follow-up: people / timeline in-flight must stay audible.

    aria-busy on the region and/or role=status / sr-only text that is
    not aria-hidden. Decorative bars may stay aria-hidden. Search may
    keep the submit label “Searching…”.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#203: App.svelte required (people / timeline in-flight a11y)")
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#203: SearchPane.svelte required (search in-flight a11y)")
    app = app_path.read_text()
    search = search_path.read_text()

    people_flag, people_branch = _people_inflight_branch(app)
    if not people_branch:
        for region in _people_sidebar_regions(crate):
            flag, block = _people_inflight_branch(region)
            if block:
                people_flag, people_branch = flag, block
                break
    people_surface = (
        _region_window(app, r"data-people-sidebar")
        + "\n"
        + _open_tag_around(app, r"""role=["']listbox["']""")
        + "\n"
        + people_branch
    )
    if not _inflight_is_audible(people_surface, people_branch, people_flag):
        fail(
            "#203: people list in-flight must expose aria-busy on the region "
            "or a role=\"status\" / sr-only line that is not aria-hidden"
        )

    tl_branch = _svelte_if_true_branch(app, "tlLoading")
    tl_surface = (
        _region_window(app, r"""id=["']person-timeline["']""")
        + "\n"
        + _open_tag_around(app, r"""id=["']person-timeline["']""")
        + "\n"
        + tl_branch
    )
    if not _inflight_is_audible(tl_surface, tl_branch, "tlLoading"):
        fail(
            "#203: person timeline in-flight must expose aria-busy on the region "
            "or a role=\"status\" / sr-only line that is not aria-hidden"
        )

    search_branch = _svelte_if_true_branch(search, "searching")
    if _SEARCHING_SUBMIT.search(search):
        return
    search_surface = search_branch + "\n" + search
    if not _inflight_is_audible(search_surface, search_branch, "searching"):
        fail(
            "#203: search in-flight must keep “Searching…” or expose aria-busy "
            "/ a role=\"status\" / sr-only line that is not aria-hidden"
        )




# #204 — owned toast for non-blocking copy / Reveal failures (not the err banner).
_TOAST_HOOK = re.compile(r"\bdata-toast\b")
_TOAST_SINK = re.compile(
    r"("
    r"\b(?:toast|showToast|pushToast|addToast|notifyToast|toastError|"
    r"toastFail|toastInfo|toastWarning)\s*(?:\.|\()"
    r"|<(?:Toast|Toaster)\b"
    r"|\$lib/components/ui/toast"
    r"|\bdata-toast\b"
    r"|\btoasts\s*=\s*\["
    r"|\btoasts\.push\s*\("
    r")",
    re.I,
)
_SHOW_ERR_CALL = re.compile(r"\bshowErr\s*\(")
_SANDBOX_137 = re.compile(
    r"macOS blocked that folder\.\s*Use Open existing"
    r"(?:\u2026|\.\.\.|…)\s*once so Interlace can remember it\."
)
_TOAST_BODY_INTERP = re.compile(
    r"\{body_text\}|copyMenu\.body_text|\{copyMenu\.body_text\}|\{copyMenu\.text\}"
)
_TOAST_CDN = re.compile(
    r"("
    r"(?:unpkg(?:\.com)?|jsdelivr(?:\.net)?|esm\.sh|cdn\.)[^\"'\s)]*"
    r"(?:sonner|toastify|hot-toast|notistack|react-toast|svelte-toast)"
    r"|https?://[^\"'\s)]*(?:sonner|toastify|hot-toast|notistack)"
    r")",
    re.I,
)
_ANALYTICS_REMOTE_PKG = re.compile(
    r"[\"'](?:"
    r"@sentry(?:/[^\"']*)?"
    r"|sentry(?:-svelte)?"
    r"|posthog(?:-js)?"
    r"|mixpanel(?:-browser)?"
    r"|amplitude-js"
    r"|@amplitude(?:/[^\"']*)?"
    r"|@segment/analytics(?:-next)?"
    r"|@vercel/analytics"
    r"|plausible-tracker"
    r"|@openreplay(?:/[^\"']*)?"
    r"|bugsnag"
    r"|rollbar"
    r"|logrocket"
    r"|@datadog/browser-rum"
    r"|google-analytics"
    r")[\"']",
    re.I,
)
_HTTP_CLIENT_PKG = re.compile(
    r"[\"'](?:"
    r"axios"
    r"|ky(?:-universal)?"
    r"|got"
    r"|node-fetch"
    r"|whatwg-fetch"
    r"|superagent"
    r"|@tauri-apps/plugin-http"
    r"|tauri-plugin-http"
    r")[\"']",
    re.I,
)
_DOCS_204_TOAST = re.compile(
    r"("
    r"(?:copy|clipboard|reveal).{0,120}toast"
    r"|toast.{0,120}(?:copy|clipboard|reveal)"
    r")",
    re.I | re.S,
)
_DOCS_204_INPAGE = re.compile(
    r"("
    r"(?:sandbox|lock|not[- ]an[- ]archive).{0,160}(?:in-page|banner|setup)"
    r"|(?:in-page|banner).{0,160}(?:sandbox|lock|not[- ]an[- ]archive)"
    r")",
    re.I | re.S,
)


def _ident_body(src: str, name: str) -> str:
    return _ts_function_body(src, name) or _function_body(src, name)


def _assigns_err_banner(blob: str) -> bool:
    """True if the blob writes the full-width err banner (showErr / err = …)."""
    if _SHOW_ERR_CALL.search(blob):
        return True
    for m in re.finditer(r"\berr\s*=\s*", blob):
        rest = blob[m.end() :].lstrip()
        if rest.startswith('""') or rest.startswith("''"):
            continue
        if re.match(r"['\"]\s*['\"]", rest):
            continue
        return True
    return False


def _uses_toast_sink(blob: str) -> bool:
    return bool(_TOAST_SINK.search(blob))


def _owned_toast_paths(crate: Path) -> list[Path]:
    """Owned toast primitive and equivalent Toaster files (no node_modules)."""
    found: list[Path] = []
    ui = crate / "web" / "lib" / "components" / "ui"
    for name in ("toast", "toaster"):
        d = ui / name
        if d.is_dir():
            found.extend(
                p
                for p in d.rglob("*")
                if p.suffix in {".svelte", ".ts", ".js", ".css"}
                and "node_modules" not in p.parts
            )
    web = crate / "web"
    if web.is_dir():
        for p in web.rglob("*.svelte"):
            if "node_modules" in p.parts:
                continue
            if p.stem.lower() in {"toast", "toaster", "toasts"}:
                found.append(p)
    seen: set[Path] = set()
    out: list[Path] = []
    for p in found:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _toast_chrome_ok(crate: Path, svelte_blob: str) -> bool:
    if _TOAST_HOOK.search(svelte_blob):
        return True
    return bool(_owned_toast_paths(crate))


def _toast_source_blob(crate: Path) -> str:
    parts: list[str] = []
    for p in _owned_toast_paths(crate):
        parts.append(p.read_text())
    for p in _product_svelte(crate):
        text = p.read_text()
        if _TOAST_HOOK.search(text) or re.search(
            r"components/ui/toast|\$lib/components/ui/toast", text
        ):
            parts.append(text)
    for p in _web_ts_sources(crate):
        if p.suffix not in {".ts", ".js"}:
            continue
        text = p.read_text()
        if _TOAST_HOOK.search(text) or re.search(
            r"components/ui/toast|\$lib/components/ui/toast", text
        ):
            parts.append(text)
    return "\n".join(parts)


def _cas_onerror_resolved(crate: Path) -> str:
    """Bodies bound to CasAttach onError if a future tag still binds it."""
    chunks: list[str] = []
    app_path = crate / "web" / "App.svelte"
    app = app_path.read_text() if app_path.is_file() else ""
    for p in _product_svelte(crate):
        text = p.read_text()
        for m in re.finditer(r"<CasAttach\b", text):
            tag = _svelte_open_tag_at(text, m.start())
            bind = re.search(r"\bonError\s*=\s*\{([^}]+)\}", tag)
            shorthand = "{onError}" in tag
            expr = bind.group(1).strip() if bind else ("onError" if shorthand else "")
            if not expr:
                continue
            chunks.append(expr)
            ident = expr if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expr) else ""
            if not ident:
                continue
            body = _ident_body(text, ident)
            if not body:
                body = _ident_body(app, ident)
            if body:
                chunks.append(body)
            elif ident == "onError":
                chunks.append(_ident_body(app, "showErr"))
    return "\n".join(c for c in chunks if c)


def _reveal_fail_blob(crate: Path) -> str:
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    cas = cas_path.read_text() if cas_path.is_file() else ""
    body = _ident_body(cas, "revealInFinder")
    parts = [body]
    parts.append(
        _windows_around(
            cas,
            re.compile(r"\b(?:revealCas|revealInFinder|reveal_cas)\b"),
            before=80,
            after=200,
        )
    )
    joined = "\n".join(parts)
    if re.search(r"\bonError\b", body or joined):
        parts.append(_cas_onerror_resolved(crate))
    if re.search(r"\bshowErr\b", "\n".join(parts)):
        app_path = crate / "web" / "App.svelte"
        if app_path.is_file():
            parts.append(_ident_body(app_path.read_text(), "showErr"))
    return "\n".join(parts)


def _copy_fail_blob(crate: Path) -> str:
    app_path = crate / "web" / "App.svelte"
    app = app_path.read_text() if app_path.is_file() else ""
    web = _web_logic(crate)
    parts: list[str] = []
    for src in (app, web):
        body = _ident_body(src, "copyText")
        if body:
            parts.append(body)
            break
    parts.append(_windows_around(web, _WRITE_TEXT, before=80, after=200))
    if re.search(r"\bshowErr\b", "\n".join(parts)):
        parts.append(_ident_body(app, "showErr"))
    return "\n".join(parts)


def _toast_args_include_body(blob: str) -> bool:
    for m in re.finditer(
        r"\b(?:toast|showToast|pushToast|addToast|notifyToast|toastError|toastFail)\s*\(",
        blob,
    ):
        arg = _call_arg(blob, m.end() - 1)
        if re.search(r"body_text|copyMenu\.body_text|copyMenu\.text\b|displayBody\s*\(", arg):
            return True
    return False


def assert_recoverable_toasts(crate: Path) -> None:
    """#204: owned toast for copy / Reveal failures; blocking errors stay in-page.

    data-toast and/or $lib/components/ui/toast (or Toaster). Reveal-fail and
    copy-fail go through the toast, not only err = / the full-width banner.
    Sandbox #137 sentence, lock, and not-an-archive stay in-page via
    friendly / banner. Toasts never interpolate body_text. ConfirmDialog
    stays. No analytics / Sentry / HTTP client / CDN toast kit. Do not
    add sonner here — #201/#202 package bans stay.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#204: App.svelte required (err banner + copy / sandbox copy)")
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail("#204: CasAttach.svelte required (Reveal in Finder failure path)")
    app = app_path.read_text()
    svelte_blob = "\n".join(p.read_text() for p in _product_svelte(crate))
    pkg_path = crate / "package.json"
    pkg = pkg_path.read_text() if pkg_path.is_file() else ""

    # 1) Toast chrome exists (owned primitive and/or data-toast). No CDN kit.
    if not _toast_chrome_ok(crate, svelte_blob):
        fail(
            "#204: toast chrome required (data-toast and/or owned "
            "$lib/components/ui/toast) — copy / Reveal failures must not "
            "be only the full-width err banner"
        )
    if _TOAST_CDN.search(_web_chrome_blob(crate)):
        fail("#204: toast chrome must be owned — no CDN / network toast kit")

    # 2) Reveal-fail and copy-fail use the toast, not only showErr / err =.
    reveal_blob = _reveal_fail_blob(crate)
    if not _uses_toast_sink(reveal_blob) or _assigns_err_banner(reveal_blob):
        fail(
            "#204: Reveal in Finder failure must show a toast, not only "
            "the full-width err banner (do not showErr / err = on that path)"
        )
    copy_blob = _copy_fail_blob(crate)
    if not _uses_toast_sink(copy_blob) or _assigns_err_banner(copy_blob):
        fail(
            "#204: Copy text / clipboard failure must show a toast, not only "
            "the full-width err banner (do not showErr / err = on that path)"
        )

    # 3) Toast markup / helper must not interpolate body_text.
    toast_src = _toast_source_blob(crate)
    if _TOAST_BODY_INTERP.search(toast_src) or _toast_args_include_body(
        toast_src + "\n" + reveal_blob + "\n" + copy_blob
    ):
        fail(
            "#204: toast markup / helper must not interpolate body_text "
            "(no {body_text} / copyMenu.body_text / copyMenu.text — chrome copy only)"
        )

    # 4) Sandbox #137 sentence, lock, and not-an-archive stay in-page.
    friendly = _ident_body(app, "friendly")
    toast_only = _owned_toast_paths(crate)
    toast_files = "\n".join(p.read_text() for p in toast_only)
    in_page_sandbox = bool(
        _SANDBOX_137.search(app)
        or "SANDBOX_DENIED" in app
        or _SANDBOX_137.search(friendly)
        or "SANDBOX_DENIED" in friendly
    )
    if not in_page_sandbox:
        fail(
            "#204: sandbox-denied must keep the exact #137 sentence in-page "
            "(setup / err banner / friendly / SANDBOX_DENIED), not toast-only: "
            "macOS blocked that folder. Use Open existing… once so Interlace "
            "can remember it."
        )
    if _SANDBOX_137.search(toast_files) and not (
        _SANDBOX_137.search(app) or "SANDBOX_DENIED" in friendly
    ):
        fail(
            "#204: sandbox-denied #137 sentence must stay in-page "
            "(friendly / SANDBOX_DENIED / err banner), not toast-only"
        )
    if "SANDBOX_DENIED" not in friendly and not _SANDBOX_137.search(friendly):
        fail(
            "#204: friendly() must still surface the #137 sandbox sentence "
            "in-page (not toast-only)"
        )
    if "archive in use" not in friendly:
        fail(
            "#204: lock (archive in use) must stay in-page via friendly / "
            "err banner, not toast-only"
        )
    if "not an Interlace archive" not in friendly:
        fail(
            "#204: not-an-archive must stay in-page via friendly / err banner, "
            "not toast-only"
        )
    err_branch = _svelte_if_true_branch(app, "err")
    if not err_branch or not re.search(r"\{err\}", err_branch):
        fail(
            "#204: keep the in-page {#if err} banner for sandbox / lock / "
            "not-an-archive (do not move those to toast-only)"
        )

    # 5) ConfirmDialog stays. No analytics / remote reporter / HTTP client.
    confirm = crate / "web" / "lib" / "ConfirmDialog.svelte"
    if not confirm.is_file():
        fail(
            "#204: ConfirmDialog must stay "
            "(do not replace merge/unlink/undo/doctor confirm with a toast)"
        )
    if not any(
        p.name != "ConfirmDialog.svelte" and "ConfirmDialog" in p.read_text()
        for p in _product_svelte(crate)
    ):
        fail(
            "#204: ConfirmDialog must stay mounted "
            "(App / Review / Doctor — not replaced by a toast)"
        )
    logic = _web_logic(crate)
    if _ANALYTICS_REMOTE_PKG.search(pkg) or _ANALYTICS_REMOTE_PKG.search(logic):
        fail("#204: not in scope — no analytics / Sentry / remote reporter")
    if _HTTP_CLIENT_PKG.search(pkg):
        fail("#204: not in scope — no HTTP client")

    # 6) D24: copy / Reveal failures toast; sandbox / lock stay in-page.
    docs_path = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs_path.read_text() if docs_path.is_file() else ""
    if not dtxt.strip():
        fail(
            "#204: docs/user/app.md required (copy / Reveal failures toast; "
            "sandbox / lock / not-an-archive stay in-page)"
        )
    if not _SANDBOX_137.search(dtxt):
        fail(
            "#204: docs/user/app.md must keep the #137 sandbox sentence "
            "(macOS blocked that folder. Use Open existing… once so "
            "Interlace can remember it.)"
        )
    docs_blob = _typo_docs_blob()
    if not _DOCS_204_TOAST.search(docs_blob):
        fail(
            "#204: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "copy / Reveal failures toast"
        )
    if not _DOCS_204_INPAGE.search(docs_blob):
        fail(
            "#204: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "sandbox / lock / not-an-archive stay in-page"
        )


# #205 — one pane can fail without blanking the shell (Error + Retry).
# Grep hook: data-partial on each of the three Error+Retry surfaces
# (person timeline, search results, doctor scan). Equivalent hook is
# not accepted unless documented here — prefer data-partial as IN.md.
_PARTIAL_HOOK = re.compile(r"\bdata-partial\b")
_RETRY_COPY = re.compile(
    r"("
    r">\s*Retry\s*<"
    r"|[\"']Retry[\"']"
    r"|\bt\s*\(\s*[\"']retry[\"']\s*\)"
    r")",
    re.I,
)
_ERROR_COPY = re.compile(
    r"("
    r"\bError\b"
    r"|\bt\s*\(\s*[\"']error[\"']\s*\)"
    r")",
)
_ONERROR_CALL = re.compile(r"\bonError\s*\(")
_PARTIAL_MASCOT = re.compile(r"\bmascot\b|\billustration\b|<img\b", re.I)
_PARTIAL_CDN = re.compile(
    r"("
    r"https?://[^\"'\s)]+"
    r"|(?:unpkg(?:\.com)?|jsdelivr(?:\.net)?|esm\.sh|cdnjs|cdn\.)"
    r")",
    re.I,
)
_DOCTOR_HEAVY = re.compile(
    r"("
    r"\bdoctorRun\b"
    r"|\bgcCas\b"
    r"|\bgc_cas\b"
    r"|\brebuildFts\b"
    r"|\brebuild_fts\b"
    r"|\bintegrity\s*:\s*true\b"
    r")",
)
_AUTO_RETRY_TIMER = re.compile(r"\bsetInterval\b")
_RECURSIVE_RETRY = re.compile(
    r"\.catch\s*\(\s*(?:async\s*)?(?:function\b|[A-Za-z_]\w*|\([^)]*\)\s*=>)",
)
_SEARCH_FILTER_IDENTS = ("q", "platform", "conversationKind", "from", "to", "personId")
_PANE_CATCH_NOISE = frozenset(
    {
        "tlLoading",
        "tlAppending",
        "tlIndex",
        "tlScrollTop",
        "tlViewportHeight",
        "tlGen",
        "gen",
        "searchGen",
        "scanGen",
        "runGen",
        "loadGen",
        "scanning",
        "searching",
        "busy",
        "empty",
        "searched",
        "expanded",
        "body",
        "hitIndex",
        "hits",
        "timeline",
        "conversations",
        "identities",
        "personTitle",
        "quotedOpen",
        "platformFilter",
        "kindFilter",
        "showPersonChrome",
        "selectedConversationId",
        "selectedId",
        "issues",
        "lastOk",
        "confirmOpen",
        "confirmTitle",
        "confirmDesc",
        "confirmLabel",
        "pending",
        "err",
        "view",
        "setup",
        "people",
        "filter",
        "includeGroups",
        "before",
        "page",
        "chrono",
        "show",
        "pane",
        "prevHeight",
        "sc",
        "estTotal",
    }
)
_BANNER_SINKS = frozenset(
    {
        "showErr",
        "onError",
        "friendly",
        "String",
        "Error",
        "console",
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
        "Promise",
    }
)
_DOCS_205_RETRY = re.compile(r"error.{0,40}retry|retry.{0,40}error", re.I | re.S)


def _try_catch_blocks(src: str) -> list[tuple[str, str]]:
    """(try_body, catch_body) pairs via brace matching."""
    out: list[tuple[str, str]] = []
    i = 0
    n = len(src)
    while i < n:
        m = re.search(r"\btry\s*\{", src[i:])
        if not m:
            break
        try_open = i + m.end() - 1
        try_close = _match_closer(src, try_open)
        if try_close < 0:
            break
        j = try_close + 1
        while j < n and src[j] in " \t\n\r":
            j += 1
        if not src.startswith("catch", j):
            i = try_close + 1
            continue
        j += 5
        while j < n and src[j] in " \t\n\r":
            j += 1
        if j < n and src[j] == "(":
            close_p = _match_closer(src, j)
            j = close_p + 1 if close_p >= 0 else j
            while j < n and src[j] in " \t\n\r":
                j += 1
        if j >= n or src[j] != "{":
            i = try_close + 1
            continue
        catch_close = _match_closer(src, j)
        if catch_close < 0:
            catch_body = src[j + 1 :]
            out.append((src[try_open + 1 : try_close], catch_body))
            break
        out.append((src[try_open + 1 : try_close], src[j + 1 : catch_close]))
        i = catch_close + 1
    return out


def _ipc_catch_bodies(src: str, fn_name: str, ipc_needles: tuple[str, ...]) -> list[str]:
    """Catch bodies whose try (or a callee try) mentions one of the IPC names."""
    body = _ident_body(src, fn_name)
    if not body:
        return []
    found: list[str] = []
    for try_body, catch_body in _try_catch_blocks(body):
        if any(needle in try_body for needle in ipc_needles):
            found.append(catch_body)
    if found:
        return found
    # One level of helpers (loadTimeline / runSearch / …).
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", body):
        callee = m.group(1)
        if callee in _BANNER_SINKS or callee == fn_name:
            continue
        nested = _ident_body(src, callee)
        if not nested:
            continue
        for try_body, catch_body in _try_catch_blocks(nested):
            if any(needle in try_body for needle in ipc_needles):
                found.append(catch_body)
    return found


def _pane_catch_dumps_banner(catch: str) -> bool:
    """True if the catch writes the App banner (showErr / onError / err =)."""
    if _assigns_err_banner(catch):
        return True
    return bool(_ONERROR_CALL.search(catch))


def _catch_error_flags(src: str, catch: str, seen: set[str] | None = None) -> set[str]:
    """Idents assigned in catch that can gate an in-pane Error+Retry."""
    found = seen if seen is not None else set()
    flags: set[str] = set()
    for ident in _assigned_idents(catch):
        if ident not in _PANE_CATCH_NOISE:
            flags.add(ident)
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", catch):
        name = m.group(1)
        if name in _BANNER_SINKS or name in found:
            continue
        found.add(name)
        nested = _ident_body(src, name)
        if nested:
            flags |= _catch_error_flags(src, nested, found)
    return flags


def _cond_negates_flag(cond: str, flags: set[str]) -> bool:
    for f in flags:
        if re.search(rf"!\s*(?:[\w$]+(?:\?\.|\.))*{re.escape(f)}\b", cond):
            return True
        if re.search(
            rf"\b(?:[\w$]+(?:\?\.|\.))*{re.escape(f)}\s*"
            r"(?:===?|==)\s*(?:null|undefined|false|[\"']{2})",
            cond,
        ):
            return True
    return False


def _element_block_at(src: str, start: int) -> str:
    """Element starting at src[start]=='<', including matched children."""
    if start < 0 or start >= len(src) or src[start] != "<":
        return ""
    open_tag = _svelte_open_tag_at(src, start)
    name_m = re.match(r"<([A-Za-z][\w:.-]*)", open_tag)
    if not name_m:
        return open_tag
    name = name_m.group(1)
    if open_tag.rstrip().endswith("/>") or name.lower() in _VOID_HTML:
        return open_tag
    depth = 1
    i = start + len(open_tag)
    n = len(src)
    name_l = name.lower()
    while i < n:
        nxt = src.find("<", i)
        if nxt < 0:
            return src[start:]
        close_m = re.match(r"</([A-Za-z][\w:.-]*)\s*>", src[nxt:])
        if close_m and close_m.group(1).lower() == name_l:
            depth -= 1
            if depth == 0:
                return src[start : nxt + close_m.end()]
            i = nxt + close_m.end()
            continue
        open_m = re.match(r"<([A-Za-z][\w:.-]*)\b", src[nxt:])
        if open_m and open_m.group(1).lower() == name_l:
            inner = _svelte_open_tag_at(src, nxt)
            if not inner.rstrip().endswith("/") and not inner.rstrip().endswith("/>"):
                if open_m.group(1).lower() not in _VOID_HTML:
                    depth += 1
            i = nxt + max(len(inner), 1)
            continue
        i = nxt + 1
    return src[start:]


def _hook_element_blocks(src: str, hook: str) -> list[str]:
    """Each element that carries `hook` (e.g. data-partial) including children."""
    out: list[str] = []
    for m in re.finditer(rf"\b{re.escape(hook)}\b", src):
        i = m.start()
        while i > 0 and src[i] != "<":
            i -= 1
        if src[i] != "<":
            continue
        block = _element_block_at(src, i)
        if block and hook in block:
            out.append(block)
    # Dedup overlapping / identical slices.
    seen: set[str] = set()
    uniq: list[str] = []
    for b in out:
        if b not in seen:
            seen.add(b)
            uniq.append(b)
    return uniq


def _parse_if_chain(src: str, if_start: int) -> tuple[list[tuple[str, str]], int]:
    """Sibling branches of one {#if}…{/if}. Nested ifs stay inside bodies."""
    head = re.match(r"\{#if\s+([^}]+)\}", src[if_start:])
    if not head:
        return [], if_start
    cond = head.group(1).strip()
    i = if_start + head.end()
    body_start = i
    depth = 1
    branches: list[tuple[str, str]] = []
    n = len(src)
    while i < n:
        if src.startswith("{#if", i) or src.startswith("{#each", i) or src.startswith(
            "{#await", i
        ) or src.startswith("{#key", i):
            depth += 1
            i += 3
            continue
        if src.startswith("{/if}", i):
            depth -= 1
            if depth == 0:
                branches.append((cond, src[body_start:i]))
                return branches, i + 5
            i += 5
            continue
        if src.startswith("{/each}", i) or src.startswith("{/await}", i) or src.startswith(
            "{/key}", i
        ):
            depth -= 1
            i += 3
            continue
        if depth == 1 and src.startswith("{:else if", i):
            branches.append((cond, src[body_start:i]))
            em = re.match(r"\{:else\s+if\s+([^}]+)\}", src[i:])
            if not em:
                i += 1
                continue
            cond = em.group(1).strip()
            i += em.end()
            body_start = i
            continue
        if depth == 1 and src.startswith("{:else}", i):
            branches.append((cond, src[body_start:i]))
            cond = ":else"
            i += len("{:else}")
            body_start = i
            continue
        i += 1
    return branches, i


def _svelte_if_chains(src: str) -> list[list[tuple[str, str]]]:
    chains: list[list[tuple[str, str]]] = []
    i = 0
    while True:
        m = re.search(r"\{#if\s+([^}]+)\}", src[i:])
        if not m:
            break
        start = i + m.start()
        chain, end = _parse_if_chain(src, start)
        if chain:
            chains.append(chain)
        i = end if end > start else start + 1
    return chains


def _attr_brace_expr(block: str, names: tuple[str, ...]) -> str:
    for name in names:
        m = re.search(rf"\b{re.escape(name)}\s*=\s*\{{", block)
        if not m:
            continue
        open_i = m.end() - 1
        close = _match_closer(block, open_i)
        if close >= 0:
            return block[open_i + 1 : close].strip()
    return ""


def _retry_click_expr(block: str) -> str:
    return _attr_brace_expr(
        block, ("onclick", "on:click", "onAction", "onaction", "onRetry", "onretry")
    )


def _resolve_handler_blob(src: str, expr: str) -> str:
    if not expr:
        return ""
    ident = re.fullmatch(r"(?:async\s+)?([A-Za-z_]\w*)", expr)
    if ident:
        return _ident_body(src, ident.group(1)) or expr
    call = re.fullmatch(r"(?:async\s+)?([A-Za-z_]\w*)\s*\([^)]*\)", expr)
    if call:
        body = _ident_body(src, call.group(1))
        return (body + "\n" + expr) if body else expr
    arrow = re.match(r"(?:async\s*)?(?:\([^)]*\)|[A-Za-z_]\w*)\s*=>\s*\{?", expr)
    if arrow:
        rest = expr[arrow.end() :]
        ident2 = re.match(r"([A-Za-z_]\w*)\s*\(", rest)
        if ident2:
            body = _ident_body(src, ident2.group(1))
            return (body + "\n" + expr) if body else expr
    return expr


def _block_has_retry_copy(block: str, en: str) -> bool:
    if _RETRY_COPY.search(block):
        return True
    for m in re.finditer(r"\bt\s*\(\s*[\"']([^\"']+)[\"']\s*\)", block):
        key = m.group(1)
        if re.search(rf"\b{re.escape(key)}\s*:\s*[\"']Retry[\"']", en):
            return True
    return False


def _block_has_error_copy(block: str, en: str) -> bool:
    if _ERROR_COPY.search(block):
        return True
    for m in re.finditer(r"\bt\s*\(\s*[\"']([^\"']+)[\"']\s*\)", block):
        key = m.group(1)
        if re.search(rf"\b{re.escape(key)}\s*:\s*[\"'][^\"']*Error[^\"']*[\"']", en):
            return True
    return False


def _partial_bound_to_flags(src: str, block: str, flags: set[str]) -> bool:
    if not flags:
        return False
    if _cond_uses_flag(block, flags):
        return True
    pos = src.find(block[: min(80, len(block))]) if block else -1
    if pos < 0:
        return False
    for kind, cond, _attrs in _template_stack(src, pos):
        if kind == "if" and _cond_uses_flag(cond, flags) and not _cond_negates_flag(
            cond, flags
        ):
            return True
        if kind == "if-else" and _cond_negates_flag(cond, flags):
            return True
    return False


def _empty_exclusive_of_partial(
    src: str, empty_title: str, flags: set[str]
) -> bool:
    """True if EmptyState `empty_title` cannot render with data-partial / fail flag."""
    if empty_title not in src:
        return True
    for chain in _svelte_if_chains(src):
        partial_branches = [b for _c, b in chain if _PARTIAL_HOOK.search(b)]
        empty_branches = [b for _c, b in chain if empty_title in b]
        if empty_branches and partial_branches:
            # Same branch would paint both — not exclusive.
            if any(empty_title in b and _PARTIAL_HOOK.search(b) for _c, b in chain):
                return False
            return True
        if empty_branches:
            for cond, body in chain:
                if empty_title not in body:
                    continue
                if flags and (
                    _cond_negates_flag(cond, flags)
                    or (cond == ":else" and any(_cond_uses_flag(c, flags) for c, _b in chain))
                ):
                    return True
    # Separate {#if}: EmptyState stack must negate the fail flag.
    markup = _svelte_markup(src)
    idx = src.find(empty_title)
    if idx < 0:
        idx = markup.find(empty_title)
        use = markup
    else:
        use = src
    if idx < 0:
        return False
    stack = _template_stack(use, idx)
    if flags and any(
        kind in {"if", "if-else"} and _cond_negates_flag(cond, flags)
        for kind, cond, _a in stack
    ):
        return True
    return False


def _interval_retries(src: str, load_names: tuple[str, ...]) -> bool:
    for m in re.finditer(r"\bsetInterval\s*\(", src):
        arg = _call_arg(src, m.end() - 1)
        if any(re.search(rf"\b{re.escape(n)}\b", arg) for n in load_names):
            return True
    return False


def _catch_auto_retries(catch: str, load_names: tuple[str, ...]) -> bool:
    if _AUTO_RETRY_TIMER.search(catch):
        return True
    if re.search(r"\bsetTimeout\s*\(", catch):
        for m in re.finditer(r"\bsetTimeout\s*\(", catch):
            arg = _call_arg(catch, m.end() - 1)
            if any(re.search(rf"\b{re.escape(n)}\b", arg) for n in load_names):
                return True
    if any(re.search(rf"\b{re.escape(n)}\s*\(", catch) for n in load_names):
        return True
    if _RECURSIVE_RETRY.search(catch):
        return True
    return False


def _effect_auto_retries(src: str, flags: set[str], load_names: tuple[str, ...]) -> bool:
    if not flags:
        return False
    for m in re.finditer(r"\$effect\s*\(", src):
        arg = _call_arg(src, m.end() - 1)
        if _cond_uses_flag(arg, flags) and any(
            re.search(rf"\b{re.escape(n)}\s*\(", arg) for n in load_names
        ):
            return True
    return False


def _docs_205_ok(dtxt: str) -> bool:
    """Failed timeline / search / doctor scan → Error + Retry on that pane; shell stays."""
    if not dtxt.strip():
        return False
    for m in _DOCS_205_RETRY.finditer(dtxt):
        win = dtxt[max(0, m.start() - 280) : m.end() + 280]
        if not re.search(r"\btimeline\b", win, re.I):
            continue
        if not re.search(r"\bsearch\b", win, re.I):
            continue
        if not re.search(r"\bdoctor\b", win, re.I):
            continue
        if not re.search(r"\b(?:pane|shell)\b", win, re.I):
            continue
        if not re.search(r"\b(?:stay|stays|rest)\b", win, re.I):
            continue
        return True
    return False


def _en_has_retry(en: str) -> bool:
    return bool(re.search(r"\bRetry\b", en)) or bool(_RETRY_COPY.search(en))


def assert_partial_pane_errors(crate: Path) -> None:
    """#205: one pane can fail without blanking the shell.

    Person timeline, search results, and doctor scan each expose Error +
    Retry on a `data-partial` surface. Timeline IPC fail (selectPerson /
    personShow / personConversations / personTimeline) must not paint
    EmptyState “No messages in this view” / “No people yet” / “Select a
    person”, and must not only dump to showErr / the full-width err
    banner. Search api.search fail must not paint “No hits” / “Type a
    query” and must keep q / platform / kind / dates. Doctor doctorIssues
    fail must not paint “No doctor issues” and must stay in-pane (not
    only onError → App banner). Retry is user-clicked, once per click —
    no setInterval / auto-retry / recursive retry; doctor Retry is not
    GC CAS / integrity / rebuild (doctorRun / gcCas). Owned Button for
    Retry is fine. No CDN / HTTP client / updater / network.server /
    sonner (#201/#202 bans stay). Blocking setup errors still use
    showErr / {#if err}. Docs (D24): failed timeline / search / doctor
    scan shows Error + Retry on that pane; the rest of the shell stays.
    Keep #202 EmptyState titles, #203 skeletons, #204 toasts, #137
    sentence, #156 boot spinner, #113 tlLoading-before-pin, #120
    windowing. Search-jump miss (#124) stays showErr — not this issue.
    """
    app_path = crate / "web" / "App.svelte"
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    if not app_path.is_file():
        fail("#205: App.svelte required (person timeline partial Error+Retry)")
    if not search_path.is_file():
        fail("#205: SearchPane.svelte required (search results partial Error+Retry)")
    if not doctor_path.is_file():
        fail("#205: DoctorPane.svelte required (doctor scan partial Error+Retry)")

    app = app_path.read_text()
    search = search_path.read_text()
    doctor = doctor_path.read_text()
    en = _chrome_en_text(crate)
    pkg_path = crate / "package.json"
    pkg = pkg_path.read_text() if pkg_path.is_file() else ""
    svelte_blob = "\n".join(p.read_text() for p in _product_svelte(crate))

    # 1) Three surfaces expose Error + Retry. Grep hook: data-partial.
    app_partials = _hook_element_blocks(app, "data-partial")
    search_partials = _hook_element_blocks(search, "data-partial")
    doctor_partials = _hook_element_blocks(doctor, "data-partial")
    missing: list[str] = []
    if not app_partials:
        missing.append("person timeline")
    if not search_partials:
        missing.append("search results")
    if not doctor_partials:
        missing.append("doctor scan")
    if missing:
        fail(
            "#205: missing data-partial Error+Retry on "
            + ", ".join(missing)
            + " (person timeline / search results / doctor scan each need "
            "data-partial on the Error+Retry surface)"
        )

    surfaces = (
        ("person timeline", app, app_partials, ("selectPerson", "personTimeline")),
        ("search results", search, search_partials, ("run", "search")),
        ("doctor scan", doctor, doctor_partials, ("load", "doctorIssues")),
    )
    for label, src, blocks, _loads in surfaces:
        joined = "\n".join(blocks)
        has_retry = _block_has_retry_copy(joined, en)
        has_error = _block_has_error_copy(joined, en)
        if not has_error or not has_retry:
            fail(
                f"#205: {label} data-partial must show Error + Retry "
                "(user-clicked Retry on that pane)"
            )
        if not any(_retry_click_expr(b) or re.search(r"<(?:Button|button)\b", b) for b in blocks):
            fail(
                f"#205: {label} Retry must be a user-clicked Button / button "
                "(owned Button is fine), not an auto-retry"
            )
        if _PARTIAL_MASCOT.search(joined):
            fail(
                f"#205: {label} data-partial must not use a mascot / "
                "illustration / <img>"
            )

    # 2) Timeline IPC fail — in-pane, not EmptyState, not only showErr.
    tl_catches = _ipc_catch_bodies(
        app,
        "selectPerson",
        ("personShow", "personConversations", "personTimeline"),
    )
    if not tl_catches:
        fail(
            "#205: selectPerson must catch personShow / personConversations / "
            "personTimeline so a fail can show in-pane Error+Retry"
        )
    tl_catch = "\n".join(tl_catches)
    tl_flags = _catch_error_flags(app, tl_catch)
    if _pane_catch_dumps_banner(tl_catch) and not (
        tl_flags and any(_partial_bound_to_flags(app, b, tl_flags) for b in app_partials)
    ):
        fail(
            "#205: selectPerson / personShow / personConversations / "
            "personTimeline fail must not only dump to showErr / the "
            "full-width {#if err} banner"
        )
    if _pane_catch_dumps_banner(tl_catch):
        fail(
            "#205: selectPerson / personShow / personConversations / "
            "personTimeline fail must not write showErr / the full-width "
            "err banner (in-pane Error+Retry only; sandbox / lock stay "
            "on the banner)"
        )
    if not tl_flags:
        fail(
            "#205: selectPerson catch must set an in-pane fail flag for "
            "data-partial Error+Retry (not only showErr)"
        )
    if not any(_partial_bound_to_flags(app, b, tl_flags) for b in app_partials):
        fail(
            "#205: person timeline data-partial must show on selectPerson / "
            "personTimeline fail (bind it to the catch flag)"
        )
    for title in (
        "No messages in this view",
        "No people yet",
        "Select a person",
    ):
        # Sidebar “No people yet” may stay for true empty; the timeline
        # fail surface / exclusive chain must not paint it on this fail.
        if title == "No people yet":
            if any(title in b for b in app_partials):
                fail(
                    "#205: timeline IPC fail must not paint EmptyState "
                    "“No people yet” on the broken pane"
                )
            continue
        if not _empty_exclusive_of_partial(app, title, tl_flags):
            fail(
                "#205: timeline IPC fail must not paint EmptyState "
                f"“{title}” (show data-partial Error+Retry on that fail, "
                "not the true-empty EmptyState)"
            )
    if re.search(r"\bsetup\s*=\s*true\b", tl_catch) or re.search(
        r"\bpeople\s*=\s*\[\s*\]", tl_catch
    ):
        fail(
            "#205: timeline IPC fail must keep nav + people sidebar "
            "(do not set setup = true or clear people)"
        )

    # 3) Search api.search fail — in-pane, keep filters, not EmptyState.
    search_catches = _ipc_catch_bodies(search, "run", ("api.search", ".search("))
    if not search_catches:
        fail(
            "#205: SearchPane run() must catch api.search so a fail can "
            "show in-pane Error+Retry"
        )
    search_catch = "\n".join(search_catches)
    search_flags = _catch_error_flags(search, search_catch)
    if _pane_catch_dumps_banner(search_catch):
        fail(
            "#205: SearchPane api.search fail must not only dump to "
            "onError / showErr / the full-width err banner"
        )
    if not search_flags:
        fail(
            "#205: SearchPane run() catch must set an in-pane fail flag "
            "for data-partial Error+Retry (not only onError)"
        )
    if not any(_partial_bound_to_flags(search, b, search_flags) for b in search_partials):
        fail(
            "#205: search results data-partial must show on api.search fail "
            "(bind it to the catch flag)"
        )
    for title in ("No hits", "Type a query"):
        if not _empty_exclusive_of_partial(search, title, search_flags):
            fail(
                "#205: search api.search fail must not paint EmptyState "
                f"“{title}”"
            )
    if re.search(r"\bempty\s*=\s*true\b", search_catch):
        fail("#205: search api.search fail must not paint EmptyState “No hits”")
    if re.search(r"\bsearched\s*=\s*false\b", search_catch):
        fail("#205: search api.search fail must not paint EmptyState “Type a query”")
    for ident in _SEARCH_FILTER_IDENTS:
        if re.search(
            rf"\b{re.escape(ident)}\s*=\s*(?:[\"']{{2}}|null|undefined)",
            search_catch,
        ):
            fail(
                "#205: search api.search fail must keep q / platform / kind / "
                "dates (do not clear filters on that fail path)"
            )
    if not re.search(r"\bbind:value=\{q\}", search):
        fail("#205: search form must keep q (query) after an api.search fail")
    if not re.search(r"\bbind:value=\{platform\}", search):
        fail("#205: search form must keep platform after an api.search fail")
    if not re.search(r"\bbind:value=\{conversationKind\}", search):
        fail("#205: search form must keep kind after an api.search fail")
    if not re.search(r"\bbind:value=\{from\}", search) or not re.search(
        r"\bbind:value=\{to\}", search
    ):
        fail("#205: search form must keep dates after an api.search fail")

    # 4) Doctor doctorIssues fail — in-pane, not healthy empty, not banner-only.
    doctor_catches = _ipc_catch_bodies(doctor, "load", ("doctorIssues",))
    if not doctor_catches:
        fail(
            "#205: DoctorPane load() must catch doctorIssues so a scan fail "
            "can show in-pane Error+Retry"
        )
    doctor_catch = "\n".join(doctor_catches)
    doctor_flags = _catch_error_flags(doctor, doctor_catch)
    if _pane_catch_dumps_banner(doctor_catch):
        fail(
            "#205: doctorIssues scan fail must not only dump to onError / "
            "App showErr / the full-width err banner"
        )
    if not doctor_flags:
        fail(
            "#205: DoctorPane load() catch must set an in-pane fail flag "
            "for data-partial Error+Retry (not only onError)"
        )
    if not any(_partial_bound_to_flags(doctor, b, doctor_flags) for b in doctor_partials):
        fail(
            "#205: doctor scan data-partial must show on doctorIssues fail "
            "(bind it to the catch flag; failure stays on the Doctor pane)"
        )
    if not _empty_exclusive_of_partial(doctor, "No doctor issues", doctor_flags):
        fail(
            "#205: doctorIssues scan fail must not paint EmptyState "
            "“No doctor issues”"
        )

    # 5) Retry is user-clicked, once per click. Doctor Retry is not GC.
    tl_retry = "\n".join(
        _resolve_handler_blob(app, _retry_click_expr(b)) for b in app_partials
    )
    search_retry = "\n".join(
        _resolve_handler_blob(search, _retry_click_expr(b)) for b in search_partials
    )
    doctor_retry = "\n".join(
        _resolve_handler_blob(doctor, _retry_click_expr(b)) for b in doctor_partials
    )
    if _DOCTOR_HEAVY.search(doctor_retry) or (
        _DOCTOR_HEAVY.search("\n".join(doctor_partials))
        and re.search(r"Retry", "\n".join(doctor_partials), re.I)
    ):
        fail(
            "#205: Doctor Retry must re-call load / doctorIssues once — "
            "not doctorRun / gcCas / integrity / rebuild"
        )
    if not re.search(r"\b(?:load|doctorIssues)\b", doctor_retry + "\n" + "\n".join(doctor_partials)):
        fail(
            "#205: Doctor Retry must re-call load / doctorIssues once "
            "(not GC CAS / integrity / rebuild)"
        )
    if _catch_auto_retries(tl_catch, ("selectPerson", "personShow", "personTimeline")):
        fail(
            "#205: Retry must be user-clicked, once per click "
            "(no setInterval / auto-retry / recursive retry that hammers "
            "a locked archive)"
        )
    if _catch_auto_retries(search_catch, ("run", "search")):
        fail(
            "#205: Retry must be user-clicked, once per click "
            "(no setInterval / auto-retry / recursive retry that hammers "
            "a locked archive)"
        )
    if _catch_auto_retries(doctor_catch, ("load", "doctorIssues", "doctorRun")):
        fail(
            "#205: Retry must be user-clicked, once per click "
            "(no setInterval / auto-retry / recursive retry that hammers "
            "a locked archive)"
        )
    if (
        _interval_retries(app, ("selectPerson", "personTimeline", "personShow"))
        or _interval_retries(search, ("run", "search"))
        or _interval_retries(doctor, ("load", "doctorIssues", "doctorRun"))
    ):
        fail(
            "#205: Retry must be user-clicked, once per click "
            "(no setInterval / auto-retry loop that hammers a locked archive)"
        )
    if (
        _effect_auto_retries(app, tl_flags, ("selectPerson", "personTimeline"))
        or _effect_auto_retries(search, search_flags, ("run",))
        or _effect_auto_retries(doctor, doctor_flags, ("load", "doctorIssues"))
    ):
        fail(
            "#205: Retry must be user-clicked, once per click "
            "(no $effect auto-retry that hammers a locked archive)"
        )
    for label, blob in (
        ("person timeline", tl_retry),
        ("search results", search_retry),
        ("doctor scan", doctor_retry),
    ):
        if _AUTO_RETRY_TIMER.search(blob):
            fail(
                f"#205: {label} Retry must be once per click "
                "(no setInterval in the Retry handler)"
            )

    # 6) Shell stays. Blocking setup errors still use the banner.
    if not re.search(r"<nav\b", app):
        fail("#205: nav must stay (timeline / search / doctor pane fail is in-pane)")
    if "data-people-sidebar" not in app:
        fail(
            "#205: people sidebar must stay on a timeline IPC fail "
            "(do not require the people list to unmount)"
        )
    if not re.search(r"\bfunction\s+showErr\b|\bshowErr\s*=", app):
        fail(
            "#205: keep showErr / {#if err} for sandbox #137, lock, and "
            "not-an-archive (do not ban showErr globally)"
        )
    err_branch = _svelte_if_true_branch(app, "err")
    if not err_branch or not re.search(r"\{err\}", err_branch):
        fail(
            "#205: keep the in-page {#if err} banner for sandbox #137 / lock / "
            "not-an-archive (pane fails are in-pane; blocking setup stays here)"
        )
    # Search-jump miss (#124) stays showErr — not this issue (IN.md).
    jump = _ident_body(app, "openPersonAtMessage")
    if jump and "showErr" not in jump:
        fail(
            "#205: openPersonAtMessage must still contain showErr "
            "(#124 miss path)"
        )

    # 7) No CDN / HTTP client / updater / network.server / sonner.
    #    Do not weaken #201/#202 package bans.
    if _TOAST_SONNER_PKG.search(pkg):
        fail("#205: do not add sonner — #201/#202 package bans stay")
    if _HTTP_CLIENT_PKG.search(pkg):
        fail("#205: not in scope — no HTTP client")
    chrome = _web_chrome_blob(crate)
    if _PARTIAL_CDN.search("\n".join(app_partials + search_partials + doctor_partials)):
        fail("#205: data-partial Error+Retry must not load a CDN / network client")
    if _TOAST_CDN.search(chrome) or _TOAST_CDN.search(svelte_blob):
        fail("#205: no CDN toast / HTTP client kit on the partial surfaces")
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    if "tauri-plugin-http" in toml or "tauri-plugin-updater" in toml:
        fail("#205: not in scope — no HTTP client / updater")
    ent_path = crate / "Interlace.entitlements"
    if ent_path.is_file() and "network.server" in ent_path.read_text():
        fail("#205: entitlements must omit network.server")

    # 8) D24: failed timeline / search / doctor scan → Error + Retry; shell stays.
    #    Do not require dropping the #137 sentence or #204 toast lines.
    dtxt = _typo_docs_blob()
    if not dtxt.strip():
        fail(
            "#205: docs/user/app.md (and/or docs/hacking/tauri.md) required "
            "(failed timeline / search / doctor scan shows Error + Retry "
            "on that pane; the rest of the shell stays)"
        )
    if not _docs_205_ok(dtxt):
        fail(
            "#205: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "a failed timeline / search / doctor scan shows Error + Retry "
            "on that pane and the rest of the shell stays"
        )


_PANE_RESULT_WRITES = frozenset(
    {
        "searchError",
        "hits",
        "searching",
        "empty",
        "scanError",
        "scanning",
        "issues",
    }
)


def _first_substr_pos(body: str, needles: tuple[str, ...]) -> int:
    found = [body.find(n) for n in needles]
    found = [i for i in found if i >= 0]
    return min(found) if found else -1


def _eq_stmt_rhs(body: str, eq_idx: int) -> str:
    """RHS of `ident = …` starting at the `=`."""
    if eq_idx < 0 or eq_idx >= len(body) or body[eq_idx] != "=":
        return ""
    i = eq_idx + 1
    if i < len(body) and body[i] == "=":
        return ""
    n = len(body)
    depth = 0
    j = i
    while j < n:
        nxt = _js_next(body, j)
        if nxt != j:
            j = nxt
            continue
        c = body[j]
        if c in "({[":
            depth += 1
        elif c in ")}]":
            if depth == 0:
                break
            depth -= 1
        elif c in ";," and depth == 0:
            break
        elif c == "\n" and depth == 0:
            break
        j += 1
    return body[i:j]


def _early_busy_ipc_status(body: str, busy: str, ipc_needles: tuple[str, ...]) -> str:
    """Whether `if (busy) return` actually prevents a second IPC.

    ok: return is before the IPC, busy is set true after that if and
    before the IPC, no await between the if and the set.
    incomplete: an `if (busy)` exists before the IPC but does not prove
    a second call cannot start.
    absent: no such if before the IPC.
    """
    ipc_at = _first_substr_pos(body, ipc_needles)
    if ipc_at < 0:
        return "absent"
    prefix = body[:ipc_at]
    m = re.search(
        rf"if\s*\(\s*{re.escape(busy)}(?:\s*===?\s*true)?\s*\)",
        prefix,
    )
    if not m:
        return "absent"
    i = m.end()
    n = len(body)
    while i < n and body[i] in " \t\n\r":
        i += 1
    if i < n and body[i] == "{":
        close = _match_closer(body, i)
        if close < 0 or close > ipc_at:
            return "incomplete"
        block = body[i + 1 : close]
        if not re.search(r"\breturn\b", block):
            return "incomplete"
        if any(needle in block for needle in ipc_needles):
            return "incomplete"
        if_end = close + 1
    elif body.startswith("return", i):
        if_end = i + len("return")
    else:
        return "incomplete"
    after_if = body[if_end:ipc_at]
    set_m = re.search(rf"\b{re.escape(busy)}\s*=\s*true\b", after_if)
    if not set_m:
        return "incomplete"
    if re.search(r"\bawait\b", after_if[: set_m.start()]):
        return "incomplete"
    return "ok"


def _gen_increment_before_ipc(body: str, ipc_at: int) -> tuple[str, str] | None:
    """`(local, counter)` for `const gen = ++searchGen` before the first IPC."""
    if ipc_at < 0:
        return None
    prefix = body[:ipc_at]
    for m in re.finditer(
        r"(?:const|let|var)\s+(\w+)\s*=\s*(?:\+\+\s*(\w+)|(\w+)\s*\+\+)",
        prefix,
    ):
        local = m.group(1)
        counter = m.group(2) or m.group(3)
        if local in _PANE_RESULT_WRITES or counter in _PANE_RESULT_WRITES:
            continue
        if local.lower() != "gen" and not re.search(r"gen", counter, re.I):
            continue
        return local, counter
    return None


def _if_gen_eq_contains(body: str, pos: int, local: str, counter: str) -> bool:
    """True if `pos` sits in `if (local === counter) { … }` or its then-stmt."""
    pat = re.compile(
        rf"if\s*\(\s*(?:{re.escape(local)}\s*===?\s*{re.escape(counter)}"
        rf"|{re.escape(counter)}\s*===?\s*{re.escape(local)})\s*\)"
    )
    for m in pat.finditer(body[:pos]):
        i = m.end()
        while i < len(body) and body[i] in " \t\n\r":
            i += 1
        if i < len(body) and body[i] == "{":
            close = _match_closer(body, i)
            if close >= pos > i:
                return True
        elif i == pos:
            return True
    return False


def _same_block_gen_ne_return(body: str, pos: int, local: str, counter: str) -> bool:
    """True if the same block already did `if (local !== counter) return`."""
    enclosing = 0
    i = 0
    while i < pos:
        nxt = _js_next(body, i)
        if nxt != i:
            i = nxt
            continue
        if body[i] == "{":
            close = _match_closer(body, i)
            if close < 0:
                break
            if close >= pos:
                enclosing = i
                i += 1
            else:
                i = close + 1
            continue
        i += 1
    region = body[enclosing:pos]
    return bool(
        re.search(
            rf"if\s*\(\s*(?:{re.escape(local)}\s*!==?\s*{re.escape(counter)}"
            rf"|{re.escape(counter)}\s*!==?\s*{re.escape(local)})\s*\)"
            r"\s*(?:\{\s*)?return\b",
            region,
        )
    )


def _assignment_gen_guarded(body: str, pos: int, local: str, counter: str) -> bool:
    return _if_gen_eq_contains(body, pos, local, counter) or _same_block_gen_ne_return(
        body, pos, local, counter
    )


def _unguarded_post_ipc_writes(
    body: str,
    local: str,
    counter: str,
    writes: tuple[str, ...],
    ipc_needles: tuple[str, ...],
) -> list[str]:
    """Write idents assigned after / as the IPC without a current-gen guard."""
    ipc_at = _first_substr_pos(body, ipc_needles)
    if ipc_at < 0:
        return list(writes)
    bad: list[str] = []
    for ident in writes:
        for m in re.finditer(rf"\b{re.escape(ident)}\s*=(?!=)", body):
            pos = m.start()
            eq = body.find("=", pos)
            rhs = _eq_stmt_rhs(body, eq)
            is_post = pos >= ipc_at or bool(re.search(r"\bawait\b", rhs)) or any(
                n in rhs for n in ipc_needles
            )
            if not is_post:
                continue
            if not _assignment_gen_guarded(body, pos, local, counter):
                bad.append(ident)
                break
    return bad


def assert_partial_retry_generation(crate: Path) -> None:
    """#205 follow-up: Search run() / Doctor load() must drop stale responses.

    Timeline already sequences personShow / personTimeline with tlGen so a
    stale catch cannot write tlError after a newer success. run() and
    load() must do the same (searchGen / scanGen or equivalent): increment
    at start; catch / success / finally writes to searchError / hits /
    searching / empty and scanError / scanning / issues only apply when
    that gen is current. An early `if (searching) return` /
    `if (scanning) return` is enough only when it actually prevents a
    second IPC (busy set true after the return and before the IPC, no
    await in between). Do not change selectPerson / tlGen. Doctor Retry
    stays load / doctorIssues (existing #205). #124 showErr on
    openPersonAtMessage stays in assert_partial_pane_errors.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    if not search_path.is_file():
        fail(
            "#205: SearchPane.svelte required "
            "(run() must ignore stale search responses)"
        )
    if not doctor_path.is_file():
        fail(
            "#205: DoctorPane.svelte required "
            "(load() must ignore stale doctorIssues responses)"
        )

    search = search_path.read_text()
    doctor = doctor_path.read_text()
    run_body = _without_comments(_ident_body(search, "run"))
    load_body = _without_comments(_ident_body(doctor, "load"))
    if not run_body:
        fail("#205: SearchPane run() required (must ignore stale api.search)")
    if not load_body:
        fail("#205: DoctorPane load() required (must ignore stale doctorIssues)")

    search_ipc = ("api.search",)
    doctor_ipc = ("doctorIssues",)
    search_writes = ("searchError", "hits", "searching", "empty")
    doctor_writes = ("scanError", "scanning", "issues")

    search_early = _early_busy_ipc_status(run_body, "searching", search_ipc)
    if search_early != "ok":
        search_tok = _gen_increment_before_ipc(
            run_body, _first_substr_pos(run_body, search_ipc)
        )
        if search_tok:
            bad = _unguarded_post_ipc_writes(
                run_body, search_tok[0], search_tok[1], search_writes, search_ipc
            )
            if bad:
                fail(
                    "#205: SearchPane run() must not apply a stale catch — "
                    "write searchError / hits / searching only when the "
                    "run() generation is still current"
                )
        elif search_early == "incomplete":
            fail(
                "#205: SearchPane run() if (searching) return does not "
                "prevent a second api.search (set searching = true after "
                "the return and before the IPC, with no await in between "
                "— or use a gen token like tlGen)"
            )
        else:
            fail(
                "#205: SearchPane run() must increment a generation token "
                "(like App tlGen) and only write searchError / hits / "
                "searching when that gen is current (a second overlapping "
                "run() must not let a stale catch win)"
            )

    doctor_early = _early_busy_ipc_status(load_body, "scanning", doctor_ipc)
    if doctor_early != "ok":
        doctor_tok = _gen_increment_before_ipc(
            load_body, _first_substr_pos(load_body, doctor_ipc)
        )
        if doctor_tok:
            bad = _unguarded_post_ipc_writes(
                load_body, doctor_tok[0], doctor_tok[1], doctor_writes, doctor_ipc
            )
            if bad:
                fail(
                    "#205: DoctorPane load() must not apply a stale catch — "
                    "write scanError / scanning / issues only when the "
                    "load() generation is still current"
                )
        elif doctor_early == "incomplete":
            fail(
                "#205: DoctorPane load() if (scanning) return does not "
                "prevent a second doctorIssues (set scanning = true after "
                "the return and before the IPC, with no await in between "
                "— or use a gen token like tlGen)"
            )
        else:
            fail(
                "#205: DoctorPane load() must increment a generation token "
                "(like App tlGen / scanGen) and only write scanError / "
                "scanning / issues when that gen is current (overlapping "
                "Retry / Refresh must not apply a stale catch)"
            )


# #206 — group consecutive same-side / same-conversation / same-UTC-day bubbles.
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
_GROUP_DAY_KEY = re.compile(r"\butcDay\b|\butc_day\b|\bdayKey\b|\bisoDay\b")
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
    """from_me + conversation_id + UTC day compared against a previous row."""
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
    """Consecutive same-side / same-conversation / same-UTC-day share one caption."""
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
        if not re.search(r"same[- ]UTC[- ]day|same UTC day", win, re.I):
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
    """#206: consecutive same from_me + conversation + UTC day share one caption.

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
            "conversation_id, and same UTC day must form a run — run-start "
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

    # 3) Break the run when from_me, conversation_id, or UTC day changes.
    group_src = _grouping_logic_src(cleaned)
    if not _has_three_key_run(group_src) and not _has_three_key_run(cleaned):
        fail(
            "#206: grouping key is from_me + conversation_id + UTC day "
            "(break the run when any of those change). Do not group across "
            "different conversation_id or a different UTC day"
        )
    identity_src = group_src or cleaned
    for m in re.finditer(r"sender_identity_id", identity_src):
        win = identity_src[max(0, m.start() - 280) : m.end() + 280]
        if _GROUPING_COND.search(win) or re.search(r"\bfrom_me\b", win):
            fail(
                "#206: grouping key is from_me + conversation_id + UTC day — "
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
            "the UTC day changes"
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

    # 8) D24: consecutive same-side / same-conversation / same-UTC-day share one caption.
    if not dtxt.strip():
        fail(
            "#206: docs/user/app.md required — consecutive same-side / "
            "same-conversation / same-UTC-day bubbles share one caption "
            "(keep the existing hour:minute + platform chip sentence)"
        )
    if not _docs_206_ok(dtxt):
        fail(
            "#206: docs/user/app.md must say consecutive same-side / "
            "same-conversation / same-UTC-day bubbles share one caption "
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


def _tag_name(tag: str) -> str:
    m = re.match(r"</?([A-Za-z][\w:.-]*)", tag)
    return m.group(1) if m else ""


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


# #208 — always-available chrome search field (not only the Search tab).
_CHROME_SEARCH_HOOK = re.compile(r"\bdata-chrome-search\b", re.I)
_API_SEARCH_CALL = re.compile(r"\bapi\.search\s*\(")
_INVOKE_SEARCH_CMD = re.compile(
    r"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']search(?:_cmd)?[\"']",
    re.I,
)
_CHROME_TO_Q = re.compile(
    r"("
    r"getElementById\s*\(\s*[\"']q[\"']"
    r"|querySelector\s*\(\s*[\"']#q[\"']"
    r"|bind:value=\{[^}]*\bq\b[^}]*\}"
    r"|\bq\s*=\s*"
    r")"
)
_CHROME_FIELD_EL = re.compile(r"<Input\b|<input\b|<form\b", re.I)
_SPOTLIGHT_WORD = re.compile(r"\bspotlight\b", re.I)
_MULTI_ARCHIVE_WORD = re.compile(r"\bmulti[- ]archive\b", re.I)
_REMOTE_SEARCH_WORD = re.compile(
    r"("
    r"\bremote\s+search\b"
    r"|search\s+(?:the\s+)?(?:web|cloud|network)\b"
    r"|https?://[^\s\"']+/search"
    r")",
    re.I,
)
_NEGATED_SCOPE = re.compile(
    r"\b(?:not|no|never|out of scope|isn't|is not|don't|do not)\b",
    re.I,
)


def _tag_inner(markup: str, tag: str) -> list[str]:
    """Inner HTML of each <tag>…</tag> (first close; chrome strips are shallow)."""
    out: list[str] = []
    for m in re.finditer(rf"<{re.escape(tag)}\b[^>]*>", markup, re.I):
        start = m.start()
        end = markup.find(f"</{tag}>", m.end())
        if end < 0:
            end = min(len(markup), m.end() + 2400)
        else:
            end = end + len(f"</{tag}>")
        out.append(markup[start:end])
    return out


def _claim_without_negation(blob: str, rx: re.Pattern[str]) -> bool:
    for m in rx.finditer(blob):
        window = blob[max(0, m.start() - 48) : m.end() + 48]
        if _NEGATED_SCOPE.search(window):
            continue
        return True
    return False


def _chrome_search_handler_surface(app: str, chrome_chunk: str) -> str:
    """Markup around the hook plus named submit/focus/key handlers."""
    parts = [chrome_chunk]
    names = re.findall(
        r"(?:on:submit|onsubmit|on:focus|onfocus|on:keydown|onkeydown|"
        r"on:input|oninput|on:change|onchange|on:click|onclick|on:blur|onblur)"
        r"\s*=\s*\{[^}]{0,160}?\b([A-Za-z_][\w]*)\s*\(",
        chrome_chunk,
    )
    names += re.findall(
        r"(?:on:submit|onsubmit|on:focus|onfocus|on:keydown|onkeydown|"
        r"on:input|oninput|on:change|onchange|on:click|onclick)"
        r"\s*=\s*\{([A-Za-z_][\w]*)\}",
        chrome_chunk,
    )
    for extra in (
        "onChromeSearch",
        "chromeSearch",
        "submitChromeSearch",
        "focusChromeSearch",
        "openChromeSearch",
        "goSearch",
        "routeChromeSearch",
    ):
        names.append(extra)
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        inner = _ts_fn_body(app, name) or _function_body(app, name)
        if inner:
            parts.append(_expand_fn_calls(app, inner))
    return "\n".join(parts)


def assert_chrome_search_field(crate: Path) -> None:
    """#208: always-available chrome search field; #q stays canonical.

    data-chrome-search lives in App.svelte chrome (nav/header), not only
    SearchPane. Using it routes to Search and focuses / copies into #q.
    SearchPane run() remains the only api.search caller. No Spotlight,
    no multi-archive, no remote search, no second FTS.
    Not #209 filters, #210 hit density, #211 titlebar, #215 palette,
    #224 virtualizer.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#208: App.svelte required (chrome search field lives in nav/header)")
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#208: SearchPane.svelte required (#q stays the canonical query)")
    app = app_path.read_text()
    search = search_path.read_text()
    markup = _svelte_markup(app)
    app_clean = _without_comments(app)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) Chrome hook in App.svelte nav/header — not only SearchPane.
    if not _CHROME_SEARCH_HOOK.search(app):
        if _CHROME_SEARCH_HOOK.search(search):
            fail(
                "#208: data-chrome-search must be in App.svelte chrome "
                "(nav/header), not only inside SearchPane"
            )
        fail(
            "#208: App.svelte chrome (nav/header) must include a search field "
            "/ wrapper with data-chrome-search (visible when the archive is "
            "open, not only on the Search tab)"
        )
    if not _CHROME_SEARCH_HOOK.search(markup):
        fail(
            "#208: data-chrome-search must be in App.svelte chrome markup "
            "(nav/header), not only a script string"
        )

    chrome_chunks = [
        chunk
        for tag in ("nav", "header")
        for chunk in _tag_inner(markup, tag)
        if _CHROME_SEARCH_HOOK.search(chunk)
    ]
    if not chrome_chunks:
        fail(
            "#208: data-chrome-search must sit in App.svelte <nav> or <header> "
            "chrome, not only inside a pane"
        )
    chrome_chunk = chrome_chunks[0]
    hook = _CHROME_SEARCH_HOOK.search(markup)
    if hook:
        for kind, cond, _extra in _template_stack(markup, hook.start()):
            if kind in {"if", "if-else"} and re.search(
                r"view\s*===?\s*[\"']search[\"']", cond
            ):
                fail(
                    "#208: chrome search (data-chrome-search) must be available "
                    "whenever the archive is open, not only when view === \"search\""
                )
            if (
                kind == "if"
                and re.search(r"\bsetup\b", cond)
                and not re.search(r"!\s*setup", cond)
            ):
                fail(
                    "#208: chrome search must be visible when the archive is "
                    "open (st && !setup), not only on the setup screen"
                )

    # 2) #q stays the canonical field in SearchPane (do not steal the id).
    if not re.search(r"id=[\"']q[\"']", search):
        fail("#208: SearchPane must keep id=\"q\" as the canonical query field")
    if re.search(r"id=[\"']q[\"']", markup):
        fail(
            "#208: #q stays the canonical field in SearchPane — do not give "
            "the chrome field id=\"q\""
        )

    # 3) Chrome field is an input / form (or wraps one).
    around = markup[
        max(0, (hook.start() if hook else 0) - 220) : (hook.end() if hook else 0) + 700
    ]
    if not _CHROME_FIELD_EL.search(chrome_chunk) and not _CHROME_FIELD_EL.search(around):
        fail(
            "#208: data-chrome-search must be a search field or wrap one "
            "(Input / input / form) in App chrome"
        )

    # 4) Chrome path routes to Search and focuses / copies into #q.
    chrome_surface = _chrome_search_handler_surface(app, chrome_chunk + "\n" + around)
    if not _VIEW_SEARCH_ASSIGN.search(chrome_surface):
        fail(
            "#208: chrome search field must route to Search "
            "(view = \"search\") and then focus #q (or copy into #q)"
        )
    if not _CHROME_TO_Q.search(chrome_surface) and not _FOCUS_SEARCH_Q.search(
        chrome_surface
    ):
        fail(
            "#208: chrome search field must focus #q or copy the typed text "
            "into #q (SearchPane query stays canonical)"
        )

    # 5) SearchPane run() remains the only api.search caller.
    run_body = _ts_fn_body(search, "run") or _function_body(search, "run")
    if not run_body or not _API_SEARCH_CALL.search(run_body):
        fail(
            "#208: SearchPane run() must remain the only api.search caller "
            "(do not add a second FTS path)"
        )
    if _API_SEARCH_CALL.search(app_clean):
        fail(
            "#208: App.svelte must not call api.search — SearchPane run() is "
            "the only search IPC"
        )
    if _INVOKE_SEARCH_CMD.search(app_clean):
        fail(
            "#208: App.svelte must not invoke search / search_cmd — SearchPane "
            "run() remains the only api.search caller"
        )
    for p in _product_svelte(crate):
        if p.name == "SearchPane.svelte":
            continue
        other = _without_comments(p.read_text())
        if _API_SEARCH_CALL.search(other):
            fail(
                f"#208: {p.relative_to(crate)} must not call api.search — "
                "SearchPane run() is the only caller"
            )
        if _INVOKE_SEARCH_CMD.search(other):
            fail(
                f"#208: {p.relative_to(crate)} must not invoke search — "
                "SearchPane run() remains the only api.search caller"
            )

    # 6) D24: chrome always available; ⌘F from every view including People → #q;
    #    `/` still people filter.
    if not dtxt.strip():
        fail(
            "#208: docs/user/app.md required — chrome search is always available"
        )
    if not re.search(
        r"("
        r"chrome.{0,48}search.{0,48}(?:always|every|nav|header)"
        r"|search.{0,48}(?:always available|in (?:the )?chrome|in (?:the )?nav)"
        r"|always[- ]available.{0,24}search"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail("#208: docs/user/app.md must say chrome search is always available")
    if not re.search(
        r"("
        r"(?:⌘\s*F|Ctrl\+F|Ctrl-F).{0,160}"
        r"(?:every view|including People|from People).{0,80}(?:#q|Search)"
        r"|(?:every view|including People).{0,80}(?:⌘\s*F|Ctrl\+F|Ctrl-F)"
        r".{0,80}(?:#q|Search)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#208: docs/user/app.md must say ⌘F from every view including "
            "People focuses #q"
        )
    if not re.search(
        r"("
        r"`/`"
        r"|slash"
        r")"
        r".{0,120}"
        r"("
        r"people filter"
        r"|#person-filter"
        r"|person-filter"
        r"|filters? (?:the )?(?:loaded )?people"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#208: docs/user/app.md must keep `/` focusing the people filter"
        )

    # 7) Not: Spotlight, multi-archive, remote search / rewritten FTS.
    #    Do not require #209 filters, #210 hit density, #211 titlebar,
    #    #215 palette, or #224 virtualizer.
    web_claim = "\n".join(p.read_text() for p in _web_sources(crate)) + "\n" + dtxt
    if _claim_without_negation(web_claim, _SPOTLIGHT_WORD):
        fail("#208: not in scope — no Spotlight / OS-wide search")
    if _claim_without_negation(web_claim, _MULTI_ARCHIVE_WORD):
        fail("#208: not in scope — no multi-archive search")
    if _claim_without_negation(web_claim, _REMOTE_SEARCH_WORD):
        fail("#208: not in scope — no remote search")


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
    en_chrome = app + "\n" + _chrome_en_text(crate)
    if "Opening last archive" not in en_chrome:
        fail("boot screen must say Opening last archive (no blank flash)")
    doctor = crate / "web" / "lib" / "DoctorPane.svelte"
    if not doctor.is_file():
        fail("DoctorPane.svelte required for UI7")
    dtxt = doctor.read_text()
    doctor_en = dtxt + "\n" + _chrome_en_text(crate)
    if "Not encrypted at rest" not in doctor_en or "FileVault" not in doctor_en:
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
    assert_voice_note_seek(crate)
    assert_virtualized_timeline(crate)
    assert_search_platform_select(crate)
    assert_search_conversation_kind(crate)
    assert_search_person_picker(crate)
    assert_search_jump_to_message(crate)
    assert_search_attachment_filter(crate)
    assert_search_safe_highlight(crate)
    assert_review_identifiers(crate)
    assert_window_title(crate)
    assert_macos_menu(crate)
    assert_chrome_locale(crate)
    assert_keyboard_map(crate)
    assert_chrome_search_field(crate)
    assert_a11y_listbox_focus_motion(crate)
    assert_human_time_people(crate)
    assert_drag_drop_import(crate)
    assert_copy_reveal_cas(crate)
    assert_defer_doctor_cas(crate)
    assert_design_tokens(crate)
    assert_typography(crate)
    assert_lucide_icons(crate)
    assert_owned_primitives(crate)
    assert_empty_next_action(crate)
    assert_loading_skeletons(crate)
    assert_timeline_append_skeleton_guard(crate)
    assert_inflight_audible_status(crate)
    assert_recoverable_toasts(crate)
    assert_partial_pane_errors(crate)
    assert_partial_retry_generation(crate)
    assert_timeline_grouped_runs(crate)
    assert_timeline_bubble_hierarchy(crate)
    assert_timeline_attach_slot(crate)
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
