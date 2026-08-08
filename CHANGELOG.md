# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Virtual Cargo workspace (`interlace-core`, `interlace`, `interlace-cli`).
- `deny.toml`, CI, and deterministic pipeline gates (`pipeline/tools`).
- SQLite archive open/migrate/`0001_init.sql` + exclusive flock.
- Frozen `interlace-core` public API (types + `unimplemented!` import/search/identity).
- Unpublished `interlace-fixtures` locale packs + synthetic generators.
- CAS put/get/gc + zip-slip checks (CAS1–CAS3).
- WhatsApp Android/iOS ZIP importer (W1–W4), `ImportContext` persist, `resolve_run` no-op until PR8.
- `docs/user/import-whatsapp.md`.
- Gmail mboxrd + Takeout + Contacts importers (M1–M3, C1) and `docs/user/import-takeout.md`.
- Identity `resolve_run` auto-link/merge + undo/review (I1–I6, I6b) and `docs/user/identity-and-review.md`.
- FTS5 search + person timeline with dual Turkish/ASCII fold (S1–S3) and `docs/user/search.md`.
- CLI `init/open/import/search/person/review/doctor/log` (silent `interlace-cli` twin) plus `docs/user/doctor.md` and `docs/user/backup.md`.
- Doctor smoke (exit 3, stale heartbeat → interrupted) and 10k search bench in PR CI (S4 proxy).

## [0.0.1] - 2026-08-08

### Added

- Name-squat / hello-world packages on crates.io.
