# Doctor, locks, and resume

`interlace doctor` checks archive health. **Exit 3** means a problem was found
(exit codes do not change with `--json`). The desktop **Doctor** tab runs the
same integrity / rebuild-FTS / GC-CAS actions (confirm first). Close the app
before running the CLI against the same folder (exclusive flock).

```bash
interlace doctor                 # integrity implied if no flags
interlace doctor --integrity
interlace doctor --rebuild-fts
interlace doctor --gc-cas
```

Any write flag or `--integrity` takes an exclusive flock. Do not run doctor in
parallel with import.

## Checks

| Check | Fail symptom | Human fix |
| --- | --- | --- |
| Missing `INTERLACE.toml` | open exit 1 | wrong directory; `init` or pass `--path` |
| `archive_id` mismatch toml vs db | exit 2 | restored sqlite from a different folder; restore matching pair |
| `PRAGMA integrity_check` ≠ ok | exit 2/3 | restore from backup copy of the folder |
| FTS `integrity-check` fail | exit 3 | `interlace doctor --rebuild-fts` |
| Missing `search_doc_ai` trigger | exit 3 | `doctor --rebuild-fts` recreates triggers |
| `running` + heartbeat > 15m | exit 3 | `--resume <run_id>` or mark failed and re-import |
| CAS file missing for hash referenced by attachments | exit 3 | re-import source with media; or accept `missing=1` |
| Unreferenced CAS files | warn | `doctor --gc-cas` |
| Mode > 0700 | warn on open | `chmod 700 "$ARCHIVE"` |
| Path under iCloud/Dropbox | warn | move archive (see backup.md) |

Stale `status=running` rows with heartbeat older than 15 minutes are marked
`interrupted` during doctor.

## Exit 3

Doctor prints each problem to stderr and exits **3**. Fix the row in the table,
then re-run. `status` uses the same codes if it hits a doctor-equivalent
invariant (Phase 1: mostly lock / missing archive).

## Stuck flock

`INTERLACE.lock` flock is released on process death. If a second command says
`archive in use by pid 12345 (import)` and `ps -p 12345` is empty:

1. Confirm no other `interlace` process: `pgrep -lf interlace`.
2. Stale pid line in the lock file is not authoritative; **do not** delete the
   lock file while a live process exists.
3. If flock is truly held by a zombie (should not happen on macOS after exit),
   reboot or `lsof INTERLACE.lock`. Never `rm INTERLACE.lock` as first step —
   creating a second lock file does not break an existing flock on the inode if
   a process still holds it; if no process holds it, the next open re-flocks.

If `open` loops on `busy_timeout` without the “in use” message: another writer
holds SQLite WAL; wait or find the process.

## Interrupted import

- Spill lives in `$ARCHIVE/imports/<run>/spill/*.mbox`.
- Success (`status=done`): wipe `spill/`.
- Interrupt: keep spill; `--resume` uses it; do not delete.
- Failed probe: no spill.
- Human abort forever: `rm -rf imports/<run>/spill` only after setting the run
  to `failed`.

```bash
interlace import gmail ~/Mail/All.mbox --resume 4
```

## Rebuild FTS

`doctor --rebuild-fts` runs `CREATE TRIGGER IF NOT EXISTS` on open and
`INSERT INTO messages_fts(messages_fts) VALUES('rebuild')`. Triggers are **never
DROPped** (D17).

## GC CAS

`doctor --gc-cas` deletes blobs not referenced by `attachments.cas_hash` or
`contacts_raw.photo_cas_hash`. Do not GC from `refcount==0` alone.
