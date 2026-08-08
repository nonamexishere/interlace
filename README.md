# Interlace

Local archive of your digital life.

Interlace is an **offline**, single-user, single-machine archive. You feed official
platform exports into one searchable store that survives account deletion, unifies
the same human across channels, and searches millions of messages locally.

**Phase 1 (macOS CLI):** WhatsApp Android/iOS ZIP (with or without media) +
Google Takeout Contacts + Gmail mbox.

The app does not phone home. There is no account, no sync, no updater.
CI denies HTTP *clients* (`reqwest`, `hyper`, `tokio` in Phase 1). A future
Tauri build may contain the `http`/`url` *type* crates; that is not a network client.

## Install

```bash
# after 0.1.0; until then build from this repo
cargo install --path crates/interlace --locked
# silent twin:
cargo install --path crates/interlace-cli --locked
```

macOS only in Phase 1.

## Quick start

```bash
interlace init --path ~/Interlace --phone-region TR --name "Your Name"
interlace import whatsapp ~/Downloads/WhatsApp\ Chat\ with\ Alice.zip
interlace import takeout ~/Downloads/Takeout
interlace search "fatura"
interlace doctor --integrity
```

`--phone-region` is required (ISO 3166-1 alpha-2; no silent default). Back up
the entire archive directory.

## Crate layout

Development is **this monorepo**. Satellite GitHub repos
(`interlace-core`, `interlace-cli`) are name/publish mirrors, not live trees.

| crates.io name | Path | Role |
| --- | --- | --- |
| `interlace-core` | `crates/interlace-core` | library |
| `interlace` | `crates/interlace` | primary CLI |
| `interlace-cli` | `crates/interlace-cli` | silent alias binary |

`interlace-cli-common` is unpublished shared CLI code (`publish = false`).
It is **not** a fourth crates.io name.

## Docs

- Architecture: [docs/design/DESIGN.md](docs/design/DESIGN.md)
- Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)
- Security: [SECURITY.md](SECURITY.md)
- Pipeline: [docs/hacking/pipeline.md](docs/hacking/pipeline.md)
- Import WhatsApp: [docs/user/import-whatsapp.md](docs/user/import-whatsapp.md)
- Import Takeout / Gmail / Contacts: [docs/user/import-takeout.md](docs/user/import-takeout.md)
- People / review / undo: [docs/user/identity-and-review.md](docs/user/identity-and-review.md)
- Search: [docs/user/search.md](docs/user/search.md)
- Doctor / locks / resume: [docs/user/doctor.md](docs/user/doctor.md)
- Backup / move: [docs/user/backup.md](docs/user/backup.md)

## License

MIT OR Apache-2.0
