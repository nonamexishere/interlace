# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Unpublished `interlace-tauri` macOS placeholder window (UI0): CSP, sandbox
  entitlements without network, darwin-only deny exception (`tokio` without
  `net`; still no `reqwest` / `hyper` / updater).
- App init / open / status (UI1): rfd folder picker, required phone-region,
  exclusive session lock, same status JSON as the CLI.
- Person list + D18 timeline in the app (UI3): groups off by default,
  merge/unlink/undo, j/k navigation.
- Desktop UI is Svelte 5 + Vite + Tailwind (`npm run tauri:dev`); vanilla `ui/`
  removed. Production still ships static files, no CDN.
- Owned shadcn-svelte (New York / zinc) primitives under
  `web/lib/components/ui/`; merge/unlink/undo use Dialog, not `confirm()`.
- App search (UI2), review queue (UI4), and import-with-progress (UI5).
  Snippets/bodies stay text nodes. CI `check` job runs on Ubuntu (1× minutes);
  `tauri` stays macOS.

### Fixed

- Import “Pick folder” on a directory of WhatsApp ZIPs imports each zip
  (auto-detect no longer assumes Takeout).

### Fixed

- WhatsApp name-only identities become their own people after import (not
  merged onto Contacts). Group-title identities stay unlinked. Re-import the
  same ZIP to backfill an existing archive (`skipped_dupes`).
- WhatsApp locale probe: datetime ties (`tr-TR`/`de-DE`) break on unique
  language tokens across all sample lines, then archive `phone-region`
  (`TR`→`tr-TR`). `--locale` still overrides.

## [0.1.1] - 2026-08-09

Dogfood patch for the published CLI. If you imported WhatsApp under 0.1.0,
wipe the archive and re-import (unknown rows + sticky `group`). The desktop
app is unpublished and not in this crate release.

### Fixed

- Global `--path` no longer collides with `import` positionals; a WhatsApp ZIP
  is not treated as the archive root.
- iOS WhatsApp 1:1 chats whose senders are address-book names (no `You`/`Siz`)
  classify as `dm` when one name matches `init --name` and the ZIP title looks
  like a DM (D18-C).
- WhatsApp locale packs accept unpadded day/month (`3.08.2025, 02:31:13`);
  datetime ties between `tr-TR` and `de-DE` break on native language tokens.

## [0.1.0] - 2026-08-08

First usable Phase 1 macOS CLI. crates.io names `interlace`, `interlace-core`,
and `interlace-cli` leave the 0.0.1 name-squat.

### Added

- Virtual Cargo workspace (`interlace-core`, `interlace`, `interlace-cli`).
- `deny.toml`, CI, and deterministic pipeline gates (`pipeline/tools`).
- SQLite archive open/migrate/`0001_init.sql` + exclusive flock.
- Frozen `interlace-core` public API.
- Unpublished `interlace-fixtures` locale packs + synthetic generators.
- CAS put/get/gc + zip-slip checks (CAS1–CAS3).
- WhatsApp Android/iOS ZIP importer (W1–W4).
- Gmail mboxrd + Takeout + Contacts importers (M1–M3, C1).
- Identity `resolve_run` auto-link/merge + undo/review (I1–I6, I6b).
- FTS5 search + person timeline with dual Turkish/ASCII fold (S1–S3).
- CLI `init/open/import/search/person/review/doctor/log` (silent `interlace-cli` twin).
- Doctor smoke (exit 3, stale heartbeat → interrupted) and 10k search bench in PR CI.
- User docs: import-whatsapp, import-takeout, identity-and-review, search, doctor, backup.
- `publish.yml` from annotated `v*` tags; satellite mirror README instructions.

## [0.0.1] - 2026-08-08

### Added

- Name-squat / hello-world packages on crates.io.
