# Backup and move

The **archive folder is the backup unit**. Phase 1 has no `interlace backup`
command. `init` prints this on purpose.

Doctor and People can **Reveal archive** folder in Finder so you do not hunt
`~/Interlace` by hand.

Doctor and File can **Copy archive to…** while this app is the only writer
(exclusive flock stays). Pick an empty local folder — that dest folder Opens
as an archive. In-app Copy drops dest `archive.sqlite-shm` after the file copy
so dest Open rebuilds a fresh WAL-index. Import running refuses calmly. After
you close the app, `cp -a` still works.

```bash
cp -a ~/Interlace /Volumes/SSD/Interlace
interlace open --path /Volumes/SSD/Interlace
```

## Snapshots

Doctor can take a local snapshot and restore one. Each snapshot is a directory
`snapshots/<id>/` with `INTERLACE.toml`, a backup `archive.sqlite`, `cas/`,
and a BLAKE3 manifest. A snapshot is not an account and not a cloud copy.
It is not an `interlace backup` command. **Copy archive to…** stays.

A hash failure is not applied. Messages added after the snapshot are removed
when restore succeeds. A failed restore leaves the open archive as it was,
but if the archive still cannot be reopened, the window leaves the archive.
Restore refuses while this process still has the database or the content
store open. Restore does not run while Copy archive to… is copying, and a
failed reopen puts the open archive back.

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
