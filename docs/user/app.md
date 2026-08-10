# Interlace app (macOS)

Phase 2 desktop window. **Offline.** No account. No sync. No updater.

The archive is still a folder you own (same `~/Interlace` as the CLI). This
app does not phone home and contains no HTTP **client**. A Tauri build may
contain the `http` and `url` **type** crates; that is not a network client.

Phase 1 CLI remains:

```bash
cargo install interlace --locked
```

The app binary is **not** published on crates.io (`interlace-tauri` is
`publish = false`). Unsigned `.app` / `.dmg` is UI8.

Dev: `cd crates/interlace-tauri && npm run tauri:dev`. That is the same loop as
other Tauri apps (`npm` drives Vite + the Tauri CLI, which still calls Cargo).

## Today (UI1 + UI3)

You can **create or open** an archive from the window (folder picker, no URLs).
`--phone-region` is still required (no silent TR/US default). Status shows
message / identity / person / review counts.

The app holds an **exclusive flock** on the archive for the session. A second
Interlace window or a CLI writer (`import`, `doctor --gc-cas`) fails with the
holder pid — close this window first.

After open: **people list + timeline** (groups hidden unless you tick include
groups). `j`/`k` move messages; `/` filters people. Merge/unlink/undo do not
rewrite `messages.sender_identity_id`.

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
