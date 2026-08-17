# Interlace app (macOS)

Phase 2 desktop window. **Offline.** No account. No sync. No updater.
Visual language: [`docs/design/UI-DESIGN.md`](../design/UI-DESIGN.md)
(Phase 2.2, epic [#197](https://github.com/nonamexishere/interlace/issues/197)).
Chrome colors come from design tokens / CSS variables, not raw Tailwind hues.
Timeline and search message bodies are 14–15px (line-height 1.5). People-row
and bubble-caption meta is 12–13px. System UI font only — no remote font.

The archive is still a folder you own (same `~/Interlace` as the CLI). This
app does not phone home and contains no HTTP **client**. A Tauri build may
contain the `http` and `url` **type** crates; that is not a network client.
The sandboxed `.app` includes macOS `network.client` because WKWebView will
not load the local `tauri://` UI without it (otherwise a blank window). It
still cannot listen (`network.server` omitted) and CSP cannot reach the
public internet.

Phase 1 CLI remains:

```bash
cargo install interlace --locked
```

The app binary is **not** published on crates.io (`interlace-tauri` is
`publish = false`). `cargo install interlace` stays the CLI (D3).

## Install the .app (unsigned)

GitHub Releases for tags `app-v*` (example `app-v0.1.1`) attach:

- `Interlace.app.zip`
- `Interlace_<version>_<arch>.dmg`

No Sparkle, no updater, no network entitlement. Ad-hoc signed only — not
notarized. After you put `Interlace.app` in `/Applications` (or anywhere):

```bash
xattr -dr com.apple.quarantine /Applications/Interlace.app
```

Then open it, pick or create `~/Interlace`, import a WhatsApp ZIP. You do
**not** need a Rust toolchain.

Ship a new build:

```bash
git checkout master && git pull
git tag -a app-v0.1.1 -m "Interlace.app 0.1.1"
git push origin app-v0.1.1
```

That runs `.github/workflows/app-release.yml` only. It does **not** publish
crates.io (`v*` tags still do that).

Dev: `cd crates/interlace-tauri && npm run tauri:dev`. Release-like local
bundle: `npm run tauri:build` (writes `target/release/bundle/`).

## Today (UI1 + UI3)

You can **create or open** an archive from the window (folder picker, no URLs).
`--phone-region` is still required (no silent TR/US default). Status shows
message / identity / person / review counts.

After you pick a folder once (**Open existing…** or **Create archive…**), the
sandboxed `.app` stores a **local security-scoped bookmark** in Application
Support (`last-archive.bookmark`, next to `config.toml`). Quit and reopen:
that folder opens again — no picker. The CLI-only `last_archive_path` string
is **not** enough under the sandbox. If you first used the CLI, then open
Interlace.app, macOS blocks the folder and the window shows the setup form
with: “macOS blocked that folder. Use Open existing… once so Interlace can
remember it.” Pick the folder once in the app. The bookmark is local only
(not iCloud, not synced). `tauri:dev` still works from the path pointer if
bookmark create fails outside the sandbox.

The app holds an **exclusive flock** on the archive for the session. A second
Interlace window or a CLI writer (`import`, `doctor --gc-cas`) fails with the
holder pid — close this window first.

The native **window title** (Cmd-tab) follows the open view or person — e.g.
`Ada — Interlace`, `Search — Interlace`; setup / People with no selection stays
bare `Interlace`. Message text never appears in the title.

The native macOS **menu bar** has **File → Open archive** (same folder picker as
**Open existing…**) and **File → Import**; **View** switches People, Search,
Review, and Doctor. About states the app is offline and not encrypted at rest
(FileVault). There is no Check for Updates item.

UI chrome (buttons, nav, empty states, Doctor) follows the OS language
(`en` / `tr`, first supported preference). A later `tr` fallback does not
override an earlier `en`. Message bodies stay as imported.

Opening an archive is **not blocked on hashing `cas/`**. People (status and
the people list) appear as soon as SQLite is open. The Doctor nav badge and
People banner stay empty until you open the **Doctor** tab. That tab still
walks every referenced CAS hash and finds a missing blob (same as CLI
`interlace doctor`). Switching archives clears the previous folder’s
findings so a remounted Doctor tab does not flash the old list.

After open: **people list + timeline** (groups hidden unless you tick include
groups). The people list is **recent-first** by last D18 activity (you sent
the message, or you share a DM / email thread). Each row shows that last
activity as a **short UTC time** (`11 Aug 14:32`), not the raw ISO, and a
one-line **plain-text** preview (the last message’s subject if it has one,
otherwise a truncated body — never HTML). The merge-target picker uses the
same short time. Archive JSON still stores ISO. Contacts with no matching messages
stay listed at the bottom. After you open a person, a **compact conversation switcher** in the header
(not a second list above the bubbles) lists their chats (WhatsApp / Gmail
when the title is empty or the person’s name; otherwise the group name or
mail subject; platform and last activity). **All** is the default (the merged D18 stream). Picking a
conversation filters the timeline to that chat. Groups still need **include
groups** to appear in the conversation list and in All. A **platform filter**
toolbar (All | WhatsApp | Gmail | …) lists only sources present for that
person; **All** is the default and switching people resets it. A **kind filter**
(All | DMs | Email threads | Groups) ANDs with the platform filter on
`conversation_kind`; groups still need **include groups** to load at all.
Switching people resets both filters. Each bubble
shows a small text **platform chip** (not a brand logo). **Identity chrome**
(Merge, include groups, unlink) is hidden until you click the person name at
the top of the conversation. The person timeline is a **chat**, not a log:
messages you sent sit on the right, the other person on the left. Each
bubble caption is **hour:minute** (UTC) plus the platform chip — not the
calendar date again. Opening a person shows the **latest messages** (the loading line
clears first, then the list waits for wrap and the pane is pinned
to the bottom while heights settle, so the newest bubble is fully
visible above the text-only footer even on a narrow pane or a long
UTC day). Older rows sit above; newest at
the bottom. **Load older**
is at the top of the list and prepends earlier pages without jumping
the viewport. Large threads **virtualize**: only the rows in (and near)
the viewport are in the DOM, so a long DM stays scrollable. A **day heading** (`15/03/2024` UTC, day/month/year) is
inserted when the UTC calendar day of `sent_at` changes and **sticks**
to the top of the message list until the next day replaces it. Days are
UTC (not the host timezone). A row with no `sent_at` gets no heading. Bodies stay visible plain-text
nodes (`whitespace-pre-wrap`) so a screen reader still hears them — never
HTML. **Gmail / email-thread** bubbles show the subject as a title when present
and fold quoted reply tails (`On … wrote:`, lines starting with `>`) behind
**Show quoted** / **Hide quoted** — still plain text, not HTML layout. WhatsApp
and other non-mail rows stay a single body paragraph. Long URLs wrap inside the bubble; they do not widen the pane. `/` filters the loaded people list client-side by display name and linked identity values (phone digits / E.164, email local part or full address). VoiceOver can move through people and hear the selected name plus that short time, not the raw ISO (`2024-08-11T14:32:00Z`). `j`/`k` move
messages. **⌘F** (Ctrl+F) focuses that people filter on People, or switches to Search and focuses the query (`#q`). **Esc** blurs a typing field, or goes back to People from Search / Review / Import / Doctor (it does not quit). **⌘1…5** (Ctrl+1…5) open People, Search, Review, Import, and Doctor. Letter shortcuts are ignored while a field is focused. Merge by picking a name: select a person, **Merge…**, search the
list (display name only — typing an id matches nobody), then confirm. Targets
show the same last-activity preview as the sidebar so same-name cards differ.
Self is hidden unless you tick **Allow absorbing self into this person** (that
absorbs self into the selected person; it does not copy `is_self`). Confirm
names are taken from the people list at Merge… time, not the header. Confirm
shows display names, not ids. Names never auto-merge. Unlink stays on each
identity row.
Merge/unlink/undo do not rewrite `messages.sender_identity_id`.

Tabs: **Search** (same FTS as CLI). **Person** is
a name-facing combobox over the same people list as the sidebar: type to filter
by display name (case-insensitive substring; self gets a “(self)” label), Enter
or click to pick — the archive stores `person_id` under the hood for the search
filter (Clear / empty = no person filter). You can search “messages with Ada”
without knowing her numeric id (single person only; no multi-person OR). After
hits load, **j**/**k** or arrow keys move the highlight; **Enter** or click
opens a hit that has a linked person on the **People** timeline at that message
(scroll + highlight once; seeks near the hit’s `sent_at` when present). If the
message cannot be placed after a bounded load, the window shows an error instead
of highlighting an unrelated row. Group hits turn **include groups** on when
needed so the row can appear. A hit with no `person_id` stays on Search and
expands the body as before. Snippet hits highlight matched tokens with a yellow
`<mark>` (split on core FTS markers) — never by injecting the body as HTML, so
markup such as `<script>` in a message stays plain text. Platform is a closed **select** — **Any** (default, empty value),
**WhatsApp**, **Gmail**, and **Contacts** — not a free-text box; values are the
core tokens (`whatsapp` / `gmail` / `contacts`). Empty means any platform.
**Kind** is another closed select — **Any** (default), **DM**, **Group**,
**Email thread** (`dm` / `group` / `email_thread`). Choosing DM never returns
group hits; Group still needs **include groups** ticked. CLI:
`interlace search --kind dm|group|email_thread`. **Attachment** is a closed
select — **Any** (default), **Has file**, **Omitted**, **Missing**
(`has_file` / `omitted` / `missing`). Has file keeps only messages with a
stored CAS blob; Omitted / Missing match the corresponding attachment flags.
CLI: `interlace search --attachment has_file|omitted|missing`. **Review**
(accept/reject name-only pairs; each side shows linked identifier
kind + normalized value — phone/email/display_name — under the title so a
name-similarity card is decidable without the CLI), **Import** (ZIP/mbox/vcf/Takeout via the
folder picker; progress in-window), **Doctor** (integrity / rebuild FTS / GC
CAS with a confirm dialog — same as the CLI, no extra window).
Drop a local ZIP or mbox onto the window (any tab) to start import — no URLs.

Empty lists, loading, lock conflicts, and doctor findings are shown as copy
in the window (not only in the terminal). Chrome icons (play/pause, lightbox
close, empty states) are Lucide, not emoji glyphs.

Photos and voice notes stored in the archive `cas/` folder open in the
timeline (and search). Click a photo thumbnail for a full-size in-window
lightbox (Esc or backdrop to close; arrow keys when a message has several
images). Voice notes play in-app with play/pause, elapsed/duration, and a
progress track you can scrub; audio is loaded only from local CAS bytes
(`data:`), never a remote stream.
Nothing is fetched from the network. Exports that omitted media show a
placeholder. Right-click a timeline bubble to **Copy text** to the clipboard.
Right-click a stored attachment to **Reveal in Finder** (local CAS file).
There is no Share sheet or AirDrop.

If the archive path looks like iCloud Drive, Dropbox, or Google Drive, a
banner stays up on every tab. Time Machine of the whole folder is fine after
you close the window. See [backup.md](backup.md).

## Encryption

Not encrypted at rest. The folder is the backup unit. Use FileVault. See
[backup.md](backup.md). The Doctor tab repeats this; it never claims the
database is encrypted.
