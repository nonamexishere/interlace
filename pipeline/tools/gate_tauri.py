#!/usr/bin/env python3
"""UI0: unpublished tauri shell, macOS deny exception, CSP, no network entitlement.

#111: person timeline must be chat bubbles (from_me right / else left), not a log.
#112: calendar-day headings (2024-03-15) when sent_at's day changes.
#268: day headings + people-row short times follow the host / Mac timezone
#     (parse sent_at ISO as UTC, then local getters / Intl). Storage /
#     api.ts sent_at and last_activity_at stay ISO UTC. No TZ picker, no
#     tzdata / network TZ database. Search type=date from/to stay. Docs:
#     display follows the host timezone; storage stays UTC.
#     Follow-up: WhatsApp / omitted-platform is wall-clock export digits
#     (no Date); Gmail / zoned still new Date + local getters. Timeline /
#     Search pass platform. Docs: WhatsApp wall-clock; Gmail follows Mac
#     TZ; storage stays UTC. `_ts_function_body` sees `: string {`.
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
#265: people list must not hold the Tauri archive mutex for the whole heavy
#     person_list scan. Review / Confirm / Undo stay callable while people
#     is filling (people() does not wrap the entire person_list in with_arch,
#     or the UI first-paints without awaiting the full list). Do not take()
#     the Archive (import pattern). Exclusive flock stays (core). Keep #138
#     identity haystack. Keep #221 void onChanged / ConfirmDialog close-first.
#     Not: wall-clock “minutes”, #203 skeletons, #110 sort/preview.
#     #265 follow-up: refreshPeople increments peopleGen (tlGen only if it
#     is also the people-list gen) and does not assign people / clear
#     peopleLoading from a stale api.people() reply; snapshot open is
#     read-only + query_only (not bare Connection::open); person_list_on
#     uses unchecked_transaction / BEGIN; people() comment is not the
#     three-line #265 / flock / take() history.
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
#184: people-list last_activity_at is a short human time (e.g. 11 Aug 14:32)
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
#     conversation_id + same calendar day is one caption (time+chip) then quieter
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
#     #215 palette.
#209: SearchPane filters are secondary (`data-search-filters`); `#q` is first /
#     primary. Optional local type="date" from/to (empty = any). Invalid dates
#     (unparseable or from > to) show a calm error and do not call api.search.
#     Closed selects stay. No CDN/npm datepicker, no Gmail labels, no invented
#     platforms. Docs: filters secondary + optional date range; invalid dates
#     do not search.
#210: SearchPane hit rows show short humanTime/utcTime + person/title, then a
#     highlighted snippet (splitSnippet + <mark> text children). No raw ISO
#     sent_at dump and no five-field sent_at · platform · kind · name · title
#     log line. Keep #124 j/k+Enter jump, #126 mark path, #208 chrome search,
#     #209 filters. Not: regex HTML inject, HTML mail renderer, FTS «» rewrite.
#211: overlay / custom titlebar — Tauri 2 titleBarStyle Overlay (native
#     traffic lights stay; decorations not false), data-tauri-drag-region on
#     the top chrome (not #app / the whole window, not on nav buttons /
#     chrome-search; the drag attribute needs allow-start-dragging), drop
#     the in-app Interlace wordmark. Keep #129 setTitle and #130 File/View.
#     Not: Windows/Linux chrome, custom traffic-light buttons.
#212: collapsible people sidebar — fixed expanded width (w-72 / 18rem, not
#     only shrinking minmax(0,18rem)), data-sidebar-toggle + collapsed hook,
#     rail / icons (no raw person ids), ⌘\\ / Ctrl+\\ in onKey (AltGr-safe
#     mod, works from fields like ⌘F), localStorage persist (not
#     write_last_path / config.toml), auto-collapse at 880/800.
#     Follow-up: rail hover name (title={display_name} / owned Tooltip),
#     #person-filter stays mounted (not inside a collapse {#if}), forceOpen
#     (or eq) so Expand opens under 880 (not only narrow || userCollapsed;
#     crossing into narrow still auto-collapses), e.code Backslash /
#     IntlBackslash (INPUT guard lets the code path through). Docs: Expand
#     on a narrow window; / still filters when the rail is showing.
#     Keep #159 overflow-x, #208 chrome search, #211 overlay. Not: liquid
#     multi-column, hiding Search/Review chrome.
#213: optional right person inspector — identities and meta, not a second
#     timeline. data-person-inspector in the People shell, hidden by
#     default (flag false / {#if} / hidden; selectedId alone is not
#     enough). Display name + identities (kind + value / value_normalized
#     / display_name, not raw ident.id / person id as the label) + last
#     activity via humanTime / utcTime (not raw ISO last_activity_at).
#     Merge / include-groups / unlink live inside the inspector (one
#     place — not a second copy above #person-timeline). Esc closes when
#     the inspector or a child is focused. No second #person-timeline /
#     no http(s) avatar <img>. Docs. Keep #q, data-people-sidebar,
#     overlay titlebar, visibleRange, CSP.
#214: keyboard map — list arrows, no trap. ArrowDown/Up on a focused
#     people listbox/option call selectPerson next/prev on filtered
#     (not only timeline tlIndex). Selected option tabindex 0, others
#     -1. Tab: #person-filter → selected person → #person-timeline;
#     undo / Open other archive tabindex="-1" (stay clickable, not a
#     stop). INPUT/TEXTAREA/SELECT guard still returns before bare
#     j/k (Search #q never intercepted). Docs in docs/user/app.md.
#     Do not rewrite #132 ⌘F / ⌘1–5. Keep #q, data-people-sidebar,
#     overlay, inspector, CSP.
#215: command palette — owned web/lib/components/ui/command/ wrapping
#     bits-ui Command; ⌘K / Ctrl+K from every view (INPUT guard lets
#     the combo through); views People/Search/Review/Import/Doctor;
#     Search focuses #q; person jump from the loaded people array
#     (display_name / personLabel) via selectPerson; Esc closes;
#     no api.search / FTS / HTTP / Spotlight; data-command-palette
#     hook. People items are filtered + capped (≤32), not the full
#     {#each people}. Palette field keeps Ctrl/⌘A; chrome shortcuts
#     do not steal keys from [data-command-palette]. Palette field
#     Ctrl/⌘C / V / X via navigator.clipboard (no plugin). Keep #201
#     cmdk ban. Docs: docs/user/app.md. Do not rewrite #132 / #201 / #214.
#     Keep #q, sidebar, overlay, inspector, CSP.
#216: focus rings + ARIA on chrome/dialogs — visible focus-visible:ring-2
#     ring-ring on every interactive control (or owned Button/Input);
#     Dialog Close + Command.Input/Item; Confirm/Merge keep trapFocus;
#     voice seek aria-valuenow + name; no aria-hidden on message bodies;
#     docs (not a WCAG certificate). Keep #133 listbox/article, #q,
#     sidebar, overlay, inspector, CSP, #215 data-command-palette.
#217: contrast tokens — light + dark both readable. Light
#     --color-muted-foreground L ≤ 40; dark (prefers-color-scheme) L ≥ 62.
#     Named --search-mark / --color-search-mark (hue 40–60) on both;
#     color-scheme: light dark; no Theme menu.
#     Docs: system appearance without a reload. Keep #198 / #216.
#218: appearance follows OS — no Theme / Appearance menu / data-theme;
#     no fetch / HTTP theme; named --overlay / --scrim / --lightbox-scrim
#     (dialog + .photo-lightbox use var(...); no bg-black/50); toast
#     bg-background + text-foreground; splash + color-scheme stay.
#     Docs: OS, dark archival, lightbox/dialogs match. Keep #217.
#219: status colors via tokens — --warning / --warning-foreground (and
#     --success if import-done is not muted) in light + dark; HSL;
#     warning hue 30–55; success hue 120–160. Cloud + doctor issues
#     use warning (not muted-only / text-destructive). Import done is
#     quiet (muted or success; no celebration). Docs: warning token +
#     quiet import done. Keep #217 / #218.
#220: import progress + calm done — Cancel hook (`data-import-cancel`)
#     while running. Status running stays; done stays quiet
#     (`data-import-done`, no Dialog/confetti). No thread kill. No path
#     console.log/toast. No parallel/HTTP/GC. Docs: progress visible +
#     quiet done. Keep #219 / #218. (#266 owns enabled Cancel +
#     import_cancel; this assert no longer requires disabled Cancel,
#     forbids import_cancel, or requires “cannot be stopped” docs.)
#266: real import cancel — `data-import-cancel` enabled while running
#     (not a bare `disabled`); `import_cancel` / `importCancel` in
#     `main.rs` and `api.ts`; ImportPane click calls that API; core or
#     Tauri mentions a cancel flag (`AtomicBool` / `ImportCancel` /
#     `cancel` / `interrupted`); `tick` treats `interrupted` as
#     terminal; no JoinHandle abort / thread::kill. Docs: Cancel
#     **stops** the import (not “cannot be stopped”). Keep #220 hook /
#     quiet done / no path toast.
#     Follow-up (in-file): WhatsApp `import()` must not `self.probe(`;
#     cancel on ZIP open / list / hash (`open_zip_cancellable` /
#     `list_zip` / `hash_file`), not only `maybe_commit`; ImportPane
#     must not promise only “Stops after this file”.
#     Fold (sources upsert + Cancelled media): `upsert_source` /
#     `abort_cancelled` fall back to `origin_path` when blake3 misses
#     (or UPDATE `file_blake3` on the existing row); WhatsApp media
#     `Err` near `read_zip_entry_capped` returns `Cancelled` (not only
#     `ctx.warn` / `media_read`); `ImportCancel` docs have no `#266`.
#221: review queue chrome — owned Card + Separator (`data-review-card`);
#     Accept/Reject stay explicit and not destructive; no raw review /
#     person ids in queue or confirm copy; Undo on the Review pane
#     (`linkEvents` / `undo`, `data-review-undo`). Identifiers + sample
#     text nodes stay (#128). Docs: Review + undo / no raw person ids.
#     Keep #219 / #220 / #218. Not: name_score UI, extra body dump, #222 motion.
#     Follow-up (undo freeze): Review undo skips split_person / undo_of
#     (not events[0] blindly); ConfirmDialog go() sets open = false
#     before await onconfirm() (or never awaits); Review undo does not
#     await onChanged() (People refresh must not block confirm).
#     Follow-up (in-flight Accept/Reject): disable Accept/Reject while
#     resolving/undoing (not only !canAccept()); accept/reject/ask no-op
#     on that flag; Accept/Reject callbacks try/catch onError (as runUndo).
#     Optional: ConfirmDialog refuses open = true while busy.
#     Follow-up (onerror + undo-while-resolving): ConfirmDialog go()
#     catch + onerror/onError; App.svelte ConfirmDialog passes
#     onerror/onError/showErr; Review Undo disabled mentions resolving
#     and requestUndo returns early when resolving.
#269: people sidebar undo chrome — short human label (op + display name if
#     cheap), not #{e.id} / raw event id as the title. Same undoable set
#     as Review: user + merge_persons/link/unlink, skip split_person /
#     undo_of. Never call doUndo / api.undo on split_person. Confirm has
#     no Undo event ${id}. ConfirmDialog close-first + App onerror stay
#     (#221). Docs: sidebar undo + skip split / no raw event id.
#     Do not rewrite #221 / #265.
#270: search-as-you-type without hitching on people refresh —
#     #q / SearchPane has an input/effect/debounce path to run() /
#     api.search, not submit-only. run() does not call people /
#     refreshPeople / applyStatus. #q is not disabled by peopleLoading.
#     Keep #q, <mark> / splitSnippet, data-search-filters. No Tantivy /
#     no fetch( / remote search. Docs: type-to-search; not blocked on
#     people refresh. Do not rewrite #126 / #208 / #209 / #210 / #265.
#     Follow-up (type-to-search lag): first in-flight (searching, no
#     hits) still has the #203 skeleton; later run() must not clear
#     expanded / hitIndex / body before api.search; previous hits stay
#     until the gen-guarded assign (no hits = [] at the start of run();
#     do not paint the skeleton over existing hits). Do not rewrite
#     #203 / #205 / the rest of #270.
#     Follow-up (PR #288 review fold): run() clears the debounce timer
#     (or a named timer) before api.search; applyStatus / refreshPeople
#     fire-and-forget has .catch / showErr / onError; onHitsKey does
#     not return solely on searching when hits exist; no restating
#     “Typing in #q searches (debounce)” comment.
#     Follow-up (PR #288 peopleGen catch): refreshPeople increments
#     peopleGen and, in catch, only showErr / assigns error when
#     gen === peopleGen (a superseded people() / archive changed must
#     not paint the banner). applyStatus still does not await
#     refreshPeople(). Do not rewrite #265 / #205 / earlier #270.
#271: video / PDF / sticker CAS attachments in the timeline —
#     loadable video plays in-window (<video> or a named video surface)
#     from casDataUrl / data: / srcs; no autoplay; no http(s) src.
#     Loadable PDF opens in-window (iframe / embed / object / overlay)
#     from local casDataUrl / data:; no remote PDF host.
#     Stickers stay on the image / lightbox path (kind === "sticker"
#     in isImage). Omitted / missing stay placeholders.
#     #118 photo lightbox still has no <video>. Docs: video + PDF
#     local in-window; no autoplay; no remote stream.
#     Do not rewrite #118 / #119 / #135 / #170.
#     Follow-up (PDF iframe vs CSP): the local PDF iframe requires
#     frame-src data: (not 'none', not *, not http(s)). Keep-check +
#     assert stay in lockstep. connect-src stays IPC-only.
#     Follow-up (video full-size overlay): visible Interlace expand /
#     full-size control (not native <video controls>); in-window overlay
#     <video> from local srcs (not data-photo-lightbox); no autoplay;
#     Esc / Close / backdrop dismiss. Docs: video full-size / expand.
#272: linkify http(s) URLs in timeline bubbles —
#     data-bubble-body splits http:// / https:// into sibling <a>
#     (or a named button); surrounding words stay text nodes
#     ({seg.text}), not one HTML string of the body.
#     https://example.com/a (or https?:// detect) is in the split path.
#     No {@html / innerHTML of the bubble body.
#     Only http / https (reject javascript: / data: / file: / tauri:).
#     ConfirmDialog before OS-open. Rust command accepts http(s) only
#     — no plugin-shell, no fetch("http.
#     Keep displayBody, whitespace-pre-wrap, break-words, Gmail
#     splitQuotedBody / Show quoted, #126 search <mark>.
#     Docs: clickable http(s) in bubbles; rest stays text; confirm;
#     not HTML mail / markdown.
#     Follow-up (long URL overflow + Open link): bubble <a
#     data-bubble-link> wraps with break-all / overflow-wrap anywhere.
#     ConfirmDialog description wraps; Content / dialog-content is
#     min-w-0 and/or overflow-x-hidden so Cancel + Open link stay
#     on-screen. App URL confirm uses confirmLabel Open link. Keep
#     break-words on the body. Do not rewrite earlier #272 / #111 /
#     #117 / #126 / #135 / #207 / #120 / #224 / #271.
#273: jump from a timeline bubble to Search —
#     context menuitem on data-copy-menu / data-context-menu
#     (or a named quiet control data-bubble-search) opens Search
#     and focuses #q (whenSearchPaneReady). Person picker is
#     prefilled with the open person's display name (pickPerson /
#     personLabel) — never a raw numeric id. Hits load: #q gets
#     a short name query or existing run() / api.search (not
#     empty-q idle only). Do not dump body_text into #q by
#     default. Keep Copy text, #q, splitSnippet / <mark>,
#     person picker, #124 hit→timeline jump, ⌘F → #q.
#     Docs: bubble → Search; person name; hits; ⌘F.
#     Do not rewrite #123 / #124 / #126 / #135 / #208 / #270 / #272.
#274: Reveal archive folder in Finder from Doctor / People —
#     Doctor Backup + People near st.path have a Reveal
#     control (Reveal in Finder / Reveal archive /
#     data-reveal-archive). Rust command (not reveal_cas,
#     not open_url) reads archive_root from app state and
#     runs /usr/bin/open -R. No path from the webview.
#     Canonicalize; refuse if not the open root.
#     reveal_cas stays hash-only. No plugin-shell / opener,
#     no fetch("http, no upload, no zip-to-iCloud, no
#     encryption claim, no second CAS copy.
#     Docs: Reveal archive folder; copy after close.
#     Do not rewrite #135 / #204 / #272 / #273.
#     Follow-up (single canonicalize): reveal_archive
#     canonicalizes archive_root once. Fail if two
#     canonicalize() results are compared (!= / ==).
#     Keep /usr/bin/open -R, archive_root from app
#     state, no webview path. Do not rewrite earlier
#     #274 / #135 / #204 / #272 / #273.
#275: first-run one screen — offline / no account, required
#     phone-region, Create / Open. Owner name / emails /
#     phones are not always-visible primary fields
#     (disclosure or absent). createArchive still requires
#     region and api.init; empty optional owner fields OK.
#     FileVault / not encrypted; folder picker only; no
#     carousel / account / sample cloud archive. Keep #137
#     sandbox sentence and #156 “Opening last archive”.
#     Docs: one first-run screen; optional fields not
#     required first. Do not rewrite #137 / #156 / #274.
#276: local density control (Default / Comfortable) — persist in
#     namespaced localStorage (not config.toml / write_last_path).
#     Comfortable enlarges timeline bubble bodies without a reload
#     (data-density / CSS variable / class on html/body). Keep the
#     system font. No Theme / Appearance menu (#218). Reduced motion
#     unchanged (#222). No remote/webfont, no per-bubble font picker.
#     Docs: local density; enlarges bubble bodies without reload;
#     system font; OS appearance; no Theme menu.
#     Follow-up: density change wipes the timeline height cache
#     (clearPendingMeasures + rowHeights = {}). Keep VIRTUALIZE_AFTER,
#     data-bubble-body, no location.reload.
#     Do not rewrite #199 / #218 / #222 / #212 / #275.
#277: leftover chrome in system light — named --chrome-* vars
#     (preview / chips / inspector / review / palette / toasts);
#     the six surfaces use them; no amber/yellow; dark media keeps
#     the current --color-background / --search-mark / --color-warning
#     strings. No Theme / Appearance menu. Docs: leftover chrome
#     readable in system light; dark archival; no Theme menu.
#     Do not rewrite #198 / #217 / #218 / #219 / #276.
#278: finish en+tr chrome — Review / Import / Doctor remaining
#     chrome (empty states, ConfirmDialog titles, undo, pick file,
#     import Cancel, doctor integrity / rebuild / GC) uses t();
#     new keys in both packs and tr is not an English copy; no
#     t(body_text|snippet|display_name|preview); detectLocale stays
#     OS-first (tr* → tr); no third pack; no fetch of locale files.
#     Keep #131 Arşiv aç / Doktor. Docs: Review / Import / Doctor
#     chrome follows OS language (en/tr); bodies stay as imported.
#     Do not rewrite #131.
#279: split assert_* into package pipeline/tools/tauri_gate/ (~8–10
#     area modules + scan.py). Entry + CI stay
#     `python3 pipeline/tools/gate_tauri.py`. Same main() assert_*
#     order + bootstrap. Do not rewrite #128 / #219–#222. Docs name
#     the package and keep the command.
#222: motion — 150–250ms Svelte fade/fly/slide on palette, inspector, toast;
#     prefers-reduced-motion uses duration 0 (JS matchMedia / MediaQuery;
#     CSS 0.01ms is not enough). No spring / bounce / lottie / celebration.
#     Keep #133 CSS reduce + boot spinner. Keep #q, sidebar, overlay,
#     inspector, CSP, #219 tokens, #220 cancel, #221 data-review-card / undo.
#224: person timeline measure-and-cache variable row heights (constant 88)
#     fallback). Lists ≤250 mount fully; longer lists still window. Spacers /
#     visibleRange / ensureTlIndexVisible use prefix sums, not index * 88.
#     Keep the #120 window helpers. Not: 10M in one view, lazy-decode every
#     photo, live average fallback, #206/#207 changes.
#267: Developer ID + notarize app-v* — workflow mentions notarytool / Developer ID
#     / Tauri notarize env; job fails closed if signing/notary secrets are missing;
#     user docs drag-and-open (xattr fallback for old tags); entitlements +
#     createUpdaterArtifacts false + no Sparkle/updater/HTTP client stay;
#     release.md lists secret names + ask before first notarized tag.
#     Committed signingIdentity may stay "-". See gate_app_release.assert_app_notarize.
#     Follow-up (empty APPLE_ID shadows API-key): app-release.yml unsets empty
#     APPLE_ID / APPLE_PASSWORD / APPLE_TEAM_ID (or only exports the chosen
#     notary method) before tauri:build.
#     Follow-up (DMG notary): app-release.yml must notarytool submit the DMG
#     ($dmg / .dmg) before stapler staple of that DMG.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root, run  # noqa: E402
from gate_app_release import assert_app_notarize  # noqa: E402

from tauri_gate.scan import (  # noqa: E402
    CSP,
    _chrome_en_text,
)
from tauri_gate.timeline import (  # noqa: E402
    assert_chat_bubbles,
    assert_day_separators,
    assert_local_tz_display,
    assert_timeline_latest,
    assert_timeline_platform_chips,
    assert_timeline_kind_filter,
    assert_gmail_timeline_rows,
    assert_virtualized_timeline,
    assert_variable_height_timeline,
    assert_timeline_grouped_runs,
    assert_timeline_bubble_hierarchy,
    assert_timeline_attach_slot,
)
from tauri_gate.people import (  # noqa: E402
    assert_conversation_switcher,
    assert_people_filter_identity,
    assert_people_list_lock,
    assert_people_sidebar_no_x_scroll,
    assert_human_time_people,
    assert_people_sidebar_collapse,
    assert_person_inspector,
)
from tauri_gate.media import (  # noqa: E402
    assert_photo_lightbox,
    assert_voice_note_player,
    assert_voice_note_seek,
    assert_cas_video_pdf,
    assert_bubble_linkify,
    assert_bubble_search,
    assert_copy_reveal_cas,
)
from tauri_gate.search import (  # noqa: E402
    assert_search_platform_select,
    assert_search_conversation_kind,
    assert_search_person_picker,
    assert_search_jump_to_message,
    assert_search_attachment_filter,
    assert_search_safe_highlight,
    assert_search_filters_secondary,
    assert_search_hit_density,
    assert_chrome_search_field,
    assert_search_as_you_type,
)
from tauri_gate.import_doctor import (  # noqa: E402
    assert_boot_spinner,
    assert_reveal_archive,
    assert_first_run,
    assert_drag_drop_import,
    assert_defer_doctor_cas,
    assert_import_progress,
    assert_import_cancel,
)
from tauri_gate.review import (  # noqa: E402
    assert_review_identifiers,
    assert_review_chrome,
    assert_sidebar_undo_chrome,
)
from tauri_gate.chrome import (  # noqa: E402
    assert_window_title,
    assert_macos_menu,
    assert_chrome_locale,
    assert_keyboard_map,
    assert_custom_titlebar,
    assert_keyboard_list_arrows,
    assert_command_palette,
    assert_command_palette_people_cap,
    assert_command_palette_field_keys,
    assert_command_palette_clipboard,
    assert_font_density,
    assert_light_chrome,
    assert_chrome_locale_panes,
)
from tauri_gate.tokens import (  # noqa: E402
    assert_a11y_listbox_focus_motion,
    assert_design_tokens,
    assert_typography,
    assert_lucide_icons,
    assert_owned_primitives,
    assert_empty_next_action,
    assert_loading_skeletons,
    assert_timeline_append_skeleton_guard,
    assert_focus_aria_audit,
    assert_contrast_tokens,
    assert_appearance_os,
    assert_status_tokens,
    assert_motion,
)
from tauri_gate.status import (  # noqa: E402
    assert_inflight_audible_status,
    assert_recoverable_toasts,
    assert_partial_pane_errors,
    assert_partial_retry_generation,
)

_SPLIT_ENTRY_CMD = "python3 pipeline/tools/gate_tauri.py"
_SPLIT_MAX_LINES = 25_000
_SPLIT_DOCSTRING_MIN_LINES = 400
_SPLIT_AREA_MIN = 8
_SPLIT_SELF = "assert_gate_tauri_split"
_SPLIT_PKG = "tauri_gate"
_SPLIT_PROTECTED_HOMES = ("review.py", "tokens.py", "import_doctor.py")
_SPLIT_EXISTING_TOOL_ASSERTS = {
    "assert_blind.py",
    "assert_matrix_not_ignored.py",
    "assert_no_crate.py",
    "assert_no_test_edits.py",
    "assert_no_todo.py",
}

# main() assert_* calls on master today (including assert_app_notarize).
_SPLIT_MAIN_ASSERTS = (
    "assert_app_notarize",
    "assert_chat_bubbles",
    "assert_day_separators",
    "assert_local_tz_display",
    "assert_timeline_latest",
    "assert_conversation_switcher",
    "assert_timeline_platform_chips",
    "assert_timeline_kind_filter",
    "assert_gmail_timeline_rows",
    "assert_people_sidebar_no_x_scroll",
    "assert_people_filter_identity",
    "assert_people_list_lock",
    "assert_boot_spinner",
    "assert_photo_lightbox",
    "assert_voice_note_player",
    "assert_voice_note_seek",
    "assert_cas_video_pdf",
    "assert_bubble_linkify",
    "assert_bubble_search",
    "assert_reveal_archive",
    "assert_first_run",
    "assert_font_density",
    "assert_light_chrome",
    "assert_chrome_locale_panes",
    "assert_virtualized_timeline",
    "assert_variable_height_timeline",
    "assert_search_platform_select",
    "assert_search_conversation_kind",
    "assert_search_person_picker",
    "assert_search_jump_to_message",
    "assert_search_attachment_filter",
    "assert_search_safe_highlight",
    "assert_search_filters_secondary",
    "assert_search_hit_density",
    "assert_review_identifiers",
    "assert_window_title",
    "assert_macos_menu",
    "assert_chrome_locale",
    "assert_keyboard_map",
    "assert_chrome_search_field",
    "assert_search_as_you_type",
    "assert_custom_titlebar",
    "assert_people_sidebar_collapse",
    "assert_person_inspector",
    "assert_keyboard_list_arrows",
    "assert_command_palette",
    "assert_command_palette_people_cap",
    "assert_command_palette_field_keys",
    "assert_command_palette_clipboard",
    "assert_focus_aria_audit",
    "assert_contrast_tokens",
    "assert_appearance_os",
    "assert_status_tokens",
    "assert_import_progress",
    "assert_import_cancel",
    "assert_review_chrome",
    "assert_sidebar_undo_chrome",
    "assert_motion",
    "assert_a11y_listbox_focus_motion",
    "assert_human_time_people",
    "assert_drag_drop_import",
    "assert_copy_reveal_cas",
    "assert_defer_doctor_cas",
    "assert_design_tokens",
    "assert_typography",
    "assert_lucide_icons",
    "assert_owned_primitives",
    "assert_empty_next_action",
    "assert_loading_skeletons",
    "assert_timeline_append_skeleton_guard",
    "assert_inflight_audible_status",
    "assert_recoverable_toasts",
    "assert_partial_pane_errors",
    "assert_partial_retry_generation",
    "assert_timeline_grouped_runs",
    "assert_timeline_bubble_hierarchy",
    "assert_timeline_attach_slot",
)

_SPLIT_BOOTSTRAP_NEEDLES = (
    "publish = false",
    "tauri-plugin-http",
    "tauri-plugin-updater",
    "CSP",
    "Interlace.entitlements",
    "signingIdentity",
    "network.server",
    "network.client",
    "allow-jit",
    "assert_app_notarize",
    '["npm", "ci"]',
    '["npm", "run", "build"]',
    '"clippy"',
    '"deny"',
    '"reqwest"',
    '"hyper"',
)

# #219 keep-check that #278 folded (pane or en pack).
_SPLIT_219_FOLD_TOKENS = (
    "Loading review queue",
    "identifierLabel",
    "reviewList",
    "reviewAccept",
    "reviewReject",
)

_SPLIT_PROTECTED_PREFIXES: dict[str, tuple[str, ...]] = {
    "assert_review_identifiers": (
        "#128: ReviewPane.svelte required (review card identifier chrome lives there)",
        "#128: web/lib/api.ts required (ReviewPanel type surface)",
        "#128: api.ts must declare export type ReviewPanel = { … }",
        "#128: unclosed ReviewPanel type in api.ts",
        "#128: ReviewPanel must include identifiers[] (kind + value_normalized per entry — not only display_name / platforms)",
        "#128: ReviewPane must render panel.identifiers (kind + value_normalized under the title — not only display_name / platforms)",
        "#128: ReviewPane must show identifier kind and value_normalized as text (bindings on the panel loop, or a small formatter used there) — not only panelTitle(display_name + platforms)",
        "#128: do not use raw person_id as the primary identifier label",
        "#128: ReviewPane samples must stay text nodes — no {@html on sample body}",
        "#128: ReviewPane must still render sample body_text as text",
        "#128: sample bodies must remain text bindings of body_text (not HTML inject)",
        "#128: keep the evidence list on the review card",
        "#128: keep the score on the review card",
        "#128: keep Accept on the review card",
        "#128: keep Reject on the review card",
        "#128: keep display_name / panel title chrome; identifiers sit under it",
        "#128: keep platforms on the panel surface (identifiers are additive)",
        "#128: do not invent name_score raise/lower UI (threshold policy is #103; this issue only surfaces identifiers)",
        "#128: ReviewPanel.identifiers entries must expose kind + value_normalized (inline or named type; platform optional)",
    ),
    "assert_status_tokens": (
        "#219: crates/interlace-tauri/web/**/*.svelte required (status tokens)",
        "#219: web/app.css required (warning / success status tokens)",
        "#219: App.svelte required (cloud banner + Doctor found box)",
        "#219: DoctorPane.svelte required (issues card uses warning token)",
        "#219: data-cloud-warning required (warning token, not muted-only)",
        "#219: data-cloud-warning must not use amber-* / yellow-* / emerald-* / green-* (warning token only)",
        "#219: data-cloud-warning must use a warning token class / var(--warning) / var(--color-warning) (not muted-only, not amber-*)",
        "#219: App.svelte “Doctor found” box required (warning token, not text-destructive)",
        "#219: App.svelte “Doctor found” box must use a warning token (not text-destructive as the status color)",
        "#219: DoctorPane.svelte issues card required (warning token, not text-destructive)",
        "#219: DoctorPane.svelte issues card must use a warning token (not text-destructive as the status color)",
        "#219: data-import-done required (muted token classes or success tokens; no bg-gradient / confetti / celebration)",
        "#219: data-import-done must use muted token classes or success tokens (no bg-gradient / confetti / celebration)",
        "#219: data-import-done must not use bg-gradient / confetti / celebration",
        "#219: no amber-* / yellow-* / emerald-* / green-* on cloud / doctor / import-done surfaces. Found:\n  ",
        "#219: no confetti / Audio( / celebration copy. Found:\n  ",
        "#219: docs/user/app.md required — warning token + quiet import done",
        "#219: docs/user/app.md must say cloud / doctor warnings use the warning token",
        "#219: docs/user/app.md must say import done is quiet (muted or success)",
        "#219: not in scope — no review-queue chrome rewrite (#221)",
        '#219: keep id="q" as the canonical query field (#208)',
        "#219: keep data-people-sidebar (#159 / #212)",
        "#219: keep the overlay titlebar (#211)",
        "#219: keep data-person-inspector (#213)",
        "#219: do not soften tauri CSP",
        "#219: keep #217 light --color-muted-foreground HSL L ≤ 40 (@theme / non-dark :root)",
        "#219: keep #217 dark --color-muted-foreground HSL L ≥ 62 (inside prefers-color-scheme: dark)",
        "#219: keep #217 --search-mark / --color-search-mark on both sides",
        "#219: keep #217 .search-mark on var(--search-mark)",
        "#219: keep #218 --overlay / --scrim / --lightbox-scrim",
        "#219: keep #218 — no Theme / Appearance menu / data-theme",
    ),
    "assert_import_progress": (
        "#220: data-import-cancel required in ImportPane.svelte (Cancel while running)",
        "#220: no thread:: kill / JoinHandle:: abort as cancel (do not kill the import thread)",
        "#220: Status running must still be rendered in the import pane",
        "#220: keep data-import-done (quiet counts; no Dialog / bg-gradient / confetti)",
        "#220: data-import-done must not be wrapped in a Dialog",
        "#220: data-import-done must not use bg-gradient / confetti / celebration",
        "#220: do not console.log the import path",
        "#220: do not toast the import path",
        "#220: no parallel-import UI",
        "#220: no fetch( / HTTP import",
        "#220: no background GC button on Import",
        "#220: docs/user/app.md required — progress visible + quiet done",
        "#220: docs/user/app.md must say import progress is visible",
        "#220: docs/user/app.md must say import done stays quiet",
        '#220: keep id="q" as the canonical query field (#208)',
        "#220: keep data-people-sidebar (#159 / #212)",
        "#220: keep the overlay titlebar (#211)",
        "#220: keep data-person-inspector (#213)",
        "#220: do not soften tauri CSP",
        "#220: keep #219 --warning / --color-warning in light and dark",
        "#220: keep #219 data-import-done",
        "#220: keep #218 --overlay / --scrim / --lightbox-scrim",
        "#220: keep #218 — no Theme / Appearance menu / data-theme",
    ),
    "assert_review_chrome": (
        "#221: ReviewPane.svelte required (review queue chrome lives there)",
        "#221: ReviewPane.svelte must import Card from $lib/components/ui/card and Separator from $lib/components/ui/separator",
        "#221: data-review-card required on the open review card",
        "#221: keep Accept on the review card (explicit >Accept<)",
        "#221: keep Reject on the review card (explicit >Reject<)",
        "#221: queue/detail markup must not show #{r.id} / person ${ / person ${r.right_person_id / Accept review ${id} (found ",
        "#221: keep identifierLabel or value_normalized on the review card",
        "#221: ReviewPane samples must stay text nodes — no {@html",
        "#221: sample bodies must remain text bindings of body_text",
        "#221: ReviewPane must call linkEvents (undo lives on the pane)",
        "#221: ReviewPane must call undo (api.undo after Accept)",
        "#221: data-review-undo required on the Review pane Undo control",
        "#221: do not undo events[0] blindly — skip split_person / already-undone / system import links",
        "#221: Review undo must skip split_person and already-undone events (undo_of)",
        "#221: ConfirmDialog.svelte required (go() must close before await onconfirm())",
        "#221: ConfirmDialog.svelte go() required (set open = false before await onconfirm())",
        "#221: ReviewPane must not await onChanged() after undo (People refresh must not block the confirm callback)",
        "#221: ConfirmDialog must refuse open = true while busy (or leave Cancel enabled so a resurrected overlay is dismissable)",
        "#221: ConfirmDialog go() must catch onconfirm and have an onerror / onError prop",
        "#221: App.svelte ConfirmDialog required",
        "#221: App.svelte ConfirmDialog must pass onerror / onError / showErr",
        "#221: Review Undo disabled must mention resolving (not only undoing)",
        "#221: ReviewPane requestUndo() required",
        "#221: requestUndo() must return early when resolving",
        "#221: do not invent name_score raise/lower UI (threshold policy is not this issue)",
        "#221: sample loop must stay {#each panel.samples (do not add a second body dump)",
        "#221: do not add a second body dump — keep the existing panel.samples loop",
        "#221: docs/user/app.md required — Review + undo / reversible / no raw person id (or identifiers + undo)",
        "#221: docs/user/app.md must say Review + undo / reversible / no raw person id (or identifiers + undo)",
        '#221: keep id="q" as the canonical query field (#208)',
        "#221: keep data-people-sidebar (#159 / #212)",
        "#221: keep the overlay titlebar (#211)",
        "#221: keep data-person-inspector (#213)",
        "#221: do not soften tauri CSP",
        "#221: keep #219 --warning / --color-warning in light and dark",
        "#221: keep #220 data-import-cancel",
        "#221: keep #218 --overlay / --scrim / --lightbox-scrim",
        "#221: keep #218 — no Theme / Appearance menu / data-theme",
        "#221: ConfirmDialog go() must set open = false before await onconfirm() (or not await onconfirm)",
        "#221: Accept/Reject callbacks must try/catch and call onError (same as runUndo)",
    ),
    "assert_motion": (
        "#222: crates/interlace-tauri/web/**/*.svelte required (motion)",
        "#222: palette must import fade / fly / slide from svelte/transition (App.svelte and/or CommandPalette.svelte)",
        "#222: inspector must import fade / fly / slide from svelte/transition",
        "#222: data-command-palette (or commandOpen root) required for fade / fly / slide",
        "#222: data-command-palette (or commandOpen root) must use transition:fade / fly / slide with duration 150–250 (or 0 when reduced)",
        "#222: data-person-inspector required for fade / fly / slide",
        "#222: data-person-inspector must use transition:fade / fly / slide with duration 150–250 (or 0 when reduced)",
        "#222: toast.svelte required (keep transition:fade 150–250)",
        "#222: toast must still use transition:fade",
        "#222: toast transition:fade duration must be 150–250 (or 0 if reduced)",
        "#222: no spring / bounce / elastic / lottie / celebration / confetti in product Svelte. Found:\n  ",
        "#222: reduced-motion path must use matchMedia / MediaQuery / prefersReducedMotion in JS (CSS transition-duration: 0.01ms is not enough for Svelte transitions)",
        "#222: palette / inspector / toast Svelte transitions must use duration 0 (or skip) when reduced motion",
        "#222: keep #133 @media (prefers-reduced-motion: reduce) in CSS (or Tailwind motion-reduce)",
        "#222: keep #133 reduced-motion animation: none (boot spinner must not spin)",
        "#222: keep #133 prefers-reduced-motion CSS (transition: none / transition-duration: 0)",
        "#222: keep boot spinner reduced-motion (#133 / #156 — disable boot-spin under reduce)",
        "#222: docs/user/app.md required — fade/slide + reduced motion instant + no celebration / no auto-play",
        "#222: docs/user/app.md must say palette / inspector / toast use a short fade / slide",
        "#222: docs/user/app.md must say reduced motion makes them instant",
        "#222: docs/user/app.md must say no celebration",
        "#222: docs/user/app.md must say no auto-playing media",
        '#222: keep id="q" as the canonical query field (#208)',
        "#222: keep data-people-sidebar (#159 / #212)",
        "#222: keep the overlay titlebar (#211)",
        "#222: keep data-person-inspector (#213)",
        "#222: do not soften tauri CSP",
        "#222: keep #219 --warning / --color-warning in light and dark",
        "#222: keep #220 data-import-cancel",
        "#222: keep #221 data-review-card",
        "#222: keep #221 data-review-undo",
    ),
}


def _split_line_count(path: Path) -> int:
    return sum(1 for _ in path.open(encoding="utf-8"))


def _split_yaml_job(wf: str, name: str) -> str:
    m = re.search(rf"(?m)^  {re.escape(name)}:\n", wf)
    if not m:
        return ""
    rest = wf[m.end() :]
    nxt = re.search(r"(?m)^  [A-Za-z0-9_-]+:\n", rest)
    return wf[m.start() : m.end() + (nxt.start() if nxt else len(rest))]


def _split_job_run_lines(job: str) -> list[str]:
    lines: list[str] = []
    for m in re.finditer(r"(?m)^[ \t]+run:[ \t]*(.*)$", job):
        val = m.group(1).strip()
        if val in {"|", ">"}:
            continue
        if val:
            lines.append(val)
    return lines


def _split_const_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _split_fold_str(node: ast.AST) -> str | None:
    direct = _split_const_str(node)
    if direct is not None:
        return direct
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _split_fold_str(node.left)
        right = _split_fold_str(node.right)
        if left is not None and right is not None:
            return left + right
        return left if left is not None else right
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            chunk = _split_const_str(value)
            if chunk is None:
                break
            parts.append(chunk)
        return "".join(parts) if parts else None
    return None


def _split_fail_prefixes(fn_src: str) -> list[str]:
    try:
        tree = ast.parse(fn_src)
    except SyntaxError:
        return []
    out: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Name) or func.id != "fail" or not node.args:
            continue
        folded = _split_fold_str(node.args[0])
        if folded and folded not in out:
            out.append(folded)
    return out


def _split_fn_sources(paths: list[Path]) -> dict[str, str]:
    found: dict[str, str] = {}
    for path in paths:
        src = path.read_text()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            seg = ast.get_source_segment(src, node)
            if not seg:
                continue
            if node.name in found:
                found[node.name] = found[node.name] + "\n" + seg
            else:
                found[node.name] = seg
    return found


def _split_main_calls(main_src: str) -> list[str]:
    try:
        tree = ast.parse(main_src)
    except SyntaxError:
        return []
    fn = next(
        (
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "main"
        ),
        None,
    )
    if fn is None:
        return []
    names: list[str] = []
    for stmt in fn.body:
        if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
            continue
        func = stmt.value.func
        if isinstance(func, ast.Name) and func.id.startswith("assert_"):
            names.append(func.id)
    return names


def _split_gate_paths() -> tuple[Path, Path, Path]:
    root = repo_root()
    tools = root / "pipeline" / "tools"
    return root, tools / "gate_tauri.py", tools / _SPLIT_PKG


def assert_gate_tauri_split(crate: Path) -> None:
    """#279: split assert_* into tauri_gate/; entry + CI command unchanged.

    G1 CI one-liner. G2 main() call order + bootstrap. G3 #128 / #219–#222
    fail prefixes (and the #219 keep-check #278 folded). G5 package + size
    + docs. G4 is the existing full gate (do not re-run npm/clippy here).
    """
    root, entry, pkg = _split_gate_paths()
    if not entry.is_file():
        fail("#279: G5 — pipeline/tools/gate_tauri.py must stay the entry")
    entry_src = entry.read_text()
    try:
        entry_tree = ast.parse(entry_src)
    except SyntaxError as exc:
        fail(f"#279: G5 — pipeline/tools/gate_tauri.py must parse: {exc}")

    # G1 — CI tauri job is still exactly the one-liner.
    ci = root / ".github" / "workflows" / "ci.yml"
    if not ci.is_file():
        fail("#279: G1 — .github/workflows/ci.yml required")
    wf = ci.read_text()
    if "python3 -m tauri_gate" in wf:
        fail("#279: G1 — no python3 -m tauri_gate")
    job = _split_yaml_job(wf, "tauri")
    if not job:
        fail("#279: G1 — ci.yml tauri job required")
    gate_runs = [
        line
        for line in _split_job_run_lines(job)
        if "gate_tauri" in line or "tauri_gate" in line
    ]
    if gate_runs != [_SPLIT_ENTRY_CMD]:
        fail(
            "#279: G1 — ci.yml tauri job step must stay exactly "
            f"`{_SPLIT_ENTRY_CMD}`"
        )
    for m in re.finditer(r"(?m)^  ([A-Za-z0-9_-]+):\n", wf):
        other = m.group(1)
        if other == "tauri":
            continue
        block = _split_yaml_job(wf, other)
        if "gate_tauri.py" in block or "tauri_gate" in block:
            fail("#279: G1 — no new CI job for the tauri gate")

    # G2 — same main() assert_* calls (order) + bootstrap.
    main_node = next(
        (
            n
            for n in entry_tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "main"
        ),
        None,
    )
    if main_node is None:
        fail("#279: G2 — gate_tauri.py main() required")
    main_src = ast.get_source_segment(entry_src, main_node) or ""
    calls = [n for n in _split_main_calls(main_src) if n != _SPLIT_SELF]
    frozen = list(_SPLIT_MAIN_ASSERTS)
    idx = 0
    for name in calls:
        if idx < len(frozen) and name == frozen[idx]:
            idx += 1
    if idx != len(frozen):
        missing = [n for n in frozen if n not in calls]
        if missing:
            fail(
                "#279: G2 — main() must still call "
                + ", ".join(missing)
                + " (same order as master; a missing call is a softened gate)"
            )
        expected = frozen[idx]
        prev = frozen[idx - 1] if idx else "(start)"
        fail(
            f"#279: G2 — main() assert_* order drifted: expected {expected} "
            f"after {prev}"
        )
    for needle in _SPLIT_BOOTSTRAP_NEEDLES:
        if needle not in main_src:
            fail(f"#279: G2 — main() bootstrap must still include {needle!r}")

    scan_paths = [entry]
    if pkg.is_dir():
        scan_paths.extend(sorted(p for p in pkg.glob("*.py") if p.is_file()))
    fn_sources = _split_fn_sources(scan_paths)
    for name in frozen:
        if name == "assert_app_notarize":
            continue
        if name not in fn_sources:
            fail(
                f"#279: G2 — {name} must still exist "
                "(moved body, not dropped)"
            )

    # G3 — protected fail prefixes still live on the five functions.
    for name, prefixes in _SPLIT_PROTECTED_PREFIXES.items():
        body = fn_sources.get(name, "")
        if not body:
            fail(
                f"#279: G3 — {name} required "
                "(move #128 / #219–#222; do not drop)"
            )
        messages = _split_fail_prefixes(body)
        for prefix in prefixes:
            if not any(msg == prefix or msg.startswith(prefix) for msg in messages):
                fail(
                    f"#279: G3 — {name} must keep fail prefix {prefix!r} "
                    "(move, do not rewrite)"
                )
    status_src = fn_sources.get("assert_status_tokens", "")
    for token in _SPLIT_219_FOLD_TOKENS:
        if token not in status_src:
            fail(
                "#279: G3 — assert_status_tokens must keep #219/#278 token "
                f"{token!r}"
            )

    # G5 — package + size + entry + docs. G4 is the rest of this script.
    clash = entry.parent / "gate_tauri"
    if clash.is_dir():
        fail(
            "#279: G5 — do not name the package gate_tauri "
            "(clash with the entry script)"
        )
    entry_lines = _split_line_count(entry)
    g5_bits: list[str] = []
    if not pkg.is_dir():
        g5_bits.append(f"package pipeline/tools/{_SPLIT_PKG}/ is missing")
    if entry_lines >= _SPLIT_MAX_LINES:
        g5_bits.append(
            f"gate_tauri.py is still {entry_lines:,} lines "
            f"(≥ {_SPLIT_MAX_LINES:,})"
        )
    if g5_bits:
        fail("#279: G5 — " + "; ".join(g5_bits))

    if not (pkg / "__init__.py").is_file():
        fail("#279: G5 — pipeline/tools/tauri_gate/__init__.py required")
    if not (pkg / "scan.py").is_file():
        fail(
            "#279: G5 — pipeline/tools/tauri_gate/scan.py required "
            "(shared readers + keep-check tokens)"
        )
    missing_homes = [n for n in _SPLIT_PROTECTED_HOMES if not (pkg / n).is_file()]
    if missing_homes:
        fail(
            "#279: G5 — review.py / tokens.py / import_doctor.py required "
            "(homes for #128 / #219 / #220 / #221 / #222)"
        )
    area_py = [
        p
        for p in pkg.glob("*.py")
        if p.is_file() and p.name not in {"__init__.py", "scan.py"}
    ]
    if len(area_py) < _SPLIT_AREA_MIN:
        fail(
            "#279: G5 — ~8–10 area modules required under tauri_gate/ "
            "(not one file per assert_*)"
        )
    one_each = [p for p in area_py if p.name.startswith("assert_")]
    if len(one_each) >= 20:
        fail("#279: G5 — do not split one file per assert_* (approach B)")
    tools = entry.parent
    chrome_files = {
        f"{name}.py"
        for name in frozen
        if name != "assert_app_notarize"
    }
    flat = [
        p.name
        for p in tools.glob("assert_*.py")
        if p.is_file()
        and p.name in chrome_files
        and p.name not in _SPLIT_EXISTING_TOOL_ASSERTS
    ]
    if flat:
        fail(
            "#279: G5 — do not add flat pipeline/tools/assert_*.py "
            "siblings (approach C)"
        )
    for py in sorted(p for p in pkg.glob("*.py") if p.is_file()):
        n = _split_line_count(py)
        if n >= _SPLIT_MAX_LINES:
            fail(
                f"#279: G5 — {py.relative_to(root)} is {n:,} lines — "
                f"no tauri_gate module may be ≥ {_SPLIT_MAX_LINES:,}"
            )

    doc = ast.get_docstring(entry_tree) or ""
    if "def main(" not in entry_src or not doc:
        fail(
            "#279: G5 — gate_tauri.py must stay the entry "
            "(module docstring + def main)"
        )
    if len(doc.splitlines()) < _SPLIT_DOCSTRING_MIN_LINES:
        fail("#279: G5 — ~500-line policy docstring stays on gate_tauri.py")

    pipe_docs = root / "docs" / "hacking" / "pipeline.md"
    tauri_docs = root / "docs" / "hacking" / "tauri.md"
    for label, path in (("pipeline.md", pipe_docs), ("tauri.md", tauri_docs)):
        text = path.read_text() if path.is_file() else ""
        if _SPLIT_ENTRY_CMD not in text:
            fail(
                f"#279: G5 — docs/hacking/{label} must keep "
                f"`{_SPLIT_ENTRY_CMD}`"
            )
    named = ""
    if pipe_docs.is_file():
        named += pipe_docs.read_text()
    if tauri_docs.is_file():
        named += "\n" + tauri_docs.read_text()
    if "tauri_gate" not in named:
        fail(
            "#279: G5 — docs/hacking/pipeline.md and/or docs/hacking/tauri.md "
            "must name the tauri_gate package"
        )

    compile_paths = [entry, *sorted(p for p in pkg.glob("*.py") if p.is_file())]
    compiled = run(
        [sys.executable, "-m", "py_compile", *[str(p) for p in compile_paths]],
        check=False,
    )
    if compiled.returncode != 0:
        fail(
            "#279: G5 — py_compile failed:\n"
            + (compiled.stderr or compiled.stdout or "")
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

    assert_app_notarize(crate)

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
    assert_local_tz_display(crate)
    assert_timeline_latest(crate)
    assert_conversation_switcher(crate)
    assert_timeline_platform_chips(crate)
    assert_timeline_kind_filter(crate)
    assert_gmail_timeline_rows(crate)
    assert_people_sidebar_no_x_scroll(crate)
    assert_people_filter_identity(crate)
    assert_people_list_lock(crate)
    assert_boot_spinner(crate)
    assert_photo_lightbox(crate)
    assert_voice_note_player(crate)
    assert_voice_note_seek(crate)
    assert_cas_video_pdf(crate)
    assert_bubble_linkify(crate)
    assert_bubble_search(crate)
    assert_reveal_archive(crate)
    assert_first_run(crate)
    assert_font_density(crate)
    assert_light_chrome(crate)
    assert_chrome_locale_panes(crate)
    assert_gate_tauri_split(crate)
    assert_virtualized_timeline(crate)
    assert_variable_height_timeline(crate)
    assert_search_platform_select(crate)
    assert_search_conversation_kind(crate)
    assert_search_person_picker(crate)
    assert_search_jump_to_message(crate)
    assert_search_attachment_filter(crate)
    assert_search_safe_highlight(crate)
    assert_search_filters_secondary(crate)
    assert_search_hit_density(crate)
    assert_review_identifiers(crate)
    assert_window_title(crate)
    assert_macos_menu(crate)
    assert_chrome_locale(crate)
    assert_keyboard_map(crate)
    assert_chrome_search_field(crate)
    assert_search_as_you_type(crate)
    assert_custom_titlebar(crate)
    assert_people_sidebar_collapse(crate)
    assert_person_inspector(crate)
    assert_keyboard_list_arrows(crate)
    assert_command_palette(crate)
    assert_command_palette_people_cap(crate)
    assert_command_palette_field_keys(crate)
    assert_command_palette_clipboard(crate)
    assert_focus_aria_audit(crate)
    assert_contrast_tokens(crate)
    assert_appearance_os(crate)
    assert_status_tokens(crate)
    assert_import_progress(crate)
    assert_import_cancel(crate)
    assert_review_chrome(crate)
    assert_sidebar_undo_chrome(crate)
    assert_motion(crate)
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
