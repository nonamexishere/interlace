# Interlace app (macOS)

Phase 2 desktop window. **Offline.** No account. No sync. No updater.

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

After open: **people list + timeline** (groups hidden unless you tick include
groups). The people list is **recent-first** by last D18 activity (you sent
the message, or you share a DM / email thread). Each row shows that time and
a one-line **plain-text** preview (the last message’s subject if it has one,
otherwise a truncated body — never HTML). Contacts with no matching messages
stay listed at the bottom. The person timeline is a **chat**, not a log:
messages you sent sit on the right, the other person on the left. Each
bubble caption is **hour:minute** (UTC) and platform — not the calendar
date again. Opening a person shows the **latest messages** (the loading line
clears first, then the list waits for wrap and the pane is pinned
to the bottom while heights settle, so the newest bubble is fully
visible above the text-only footer even on a narrow pane or a long
UTC day). Older rows sit above; newest at
the bottom. **Load older**
is at the top of the list and prepends earlier pages without jumping
the viewport. A **day heading** (`15/03/2024` UTC, day/month/year) is
inserted when the UTC calendar day of `sent_at` changes and **sticks**
to the top of the message list until the next day replaces it. Days are
UTC (not the host timezone). A row with no `sent_at` gets no heading. Bodies stay visible plain-text
nodes (`whitespace-pre-wrap`) so a screen reader still hears them — never
HTML. Long URLs wrap inside the bubble; they do not widen the pane. `/` still filters by name only. `j`/`k` move
messages. Merge by picking a name: select a person, **Merge…**, search the
list (display name only — typing an id matches nobody), then confirm. Targets
show the same last-activity preview as the sidebar so same-name cards differ.
Self is hidden unless you tick **Allow absorbing self into this person** (that
absorbs self into the selected person; it does not copy `is_self`). Confirm
names are taken from the people list at Merge… time, not the header. Confirm
shows display names, not ids. Names never auto-merge. Unlink stays on each
identity row.
Merge/unlink/undo do not rewrite `messages.sender_identity_id`.

Tabs: **Search** (same FTS as CLI; expand a hit for the full body), **Review**
(accept/reject name-only pairs), **Import** (ZIP/mbox/vcf/Takeout via the
folder picker; progress in-window), **Doctor** (integrity / rebuild FTS /
GC CAS with a confirm dialog — same as the CLI, no extra window).

Empty lists, loading, lock conflicts, and doctor findings are shown as copy
in the window (not only in the terminal).

Photos and voice notes stored in the archive `cas/` folder open in the
timeline (and search). Exports that omitted media show a placeholder — nothing
is fetched from the network.

If the archive path looks like iCloud Drive, Dropbox, or Google Drive, a
banner stays up on every tab. Time Machine of the whole folder is fine after
you close the window. See [backup.md](backup.md).

## Encryption

Not encrypted at rest. The folder is the backup unit. Use FileVault. See
[backup.md](backup.md). The Doctor tab repeats this; it never claims the
database is encrypted.
