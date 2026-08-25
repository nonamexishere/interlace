# Backup and move

The **archive folder is the backup unit**. Phase 1 has no `interlace backup`
command. `init` prints this on purpose.

Doctor and People can **Reveal archive** folder in Finder so you do not hunt
`~/Interlace` by hand. Backup is still copy that folder after closing the app.

```bash
cp -a ~/Interlace /Volumes/SSD/Interlace
interlace open --path /Volumes/SSD/Interlace
```

## Copy these

- `INTERLACE.toml`
- `archive.sqlite`, `archive.sqlite-wal`, `archive.sqlite-shm` (checkpoint
  first if possible: close all writers)
- `cas/`
- `logs/`

Skip `tmp/`. After a successful import, skip `imports/*/spill`.

The pointer file `~/Library/Application Support/Interlace/config.toml` is
**not** the data. Update `last_archive_path` with `open --path`. Moving
mid-import is unsupported.

## Time Machine / iCloud

Do **not** put the live archive in iCloud Drive, Dropbox, or Google Drive.
`open` warns if the path looks like those folders. Time Machine of the whole
folder is fine if writers are closed.

## Encryption

Phase 1 and Phase 2 are **not** encrypted at rest (OQ4). Use FileVault or
other disk encryption. There is no SQLCipher in this product yet.
