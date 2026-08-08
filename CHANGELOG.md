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

## [0.0.1] - 2026-08-08

### Added

- Name-squat / hello-world packages on crates.io.
