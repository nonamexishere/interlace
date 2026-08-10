# Interlace

Local archive of your digital life.

Interlace is an **offline**, single-user, single-machine archive. You feed official
platform exports into one searchable store that survives account deletion, unifies
the same human across channels, and searches millions of messages locally.

**Phase 1 (macOS CLI):** WhatsApp Android/iOS ZIP (with or without media) +
Google Takeout Contacts + Gmail mbox.

The app does not phone home. There is no account, no sync, no updater.
CI denies HTTP *clients* (`reqwest`, `hyper`, `tokio` on core+cli). The
unpublished Tauri shell (`npm run tauri:dev` in `crates/interlace-tauri`) may contain the
`http`/`url` *type* crates and `tokio` **without** `net`; that is not a
network client.

## Install

**Desktop app (macOS, unsigned):** GitHub Releases on `app-v*` tags
(`Interlace_*.dmg` or `Interlace.app.zip`). Not notarized.

```bash
# after you copy Interlace.app out of the DMG / zip:
xattr -dr com.apple.quarantine /Applications/Interlace.app
```

Gatekeeper will complain once; that is expected until codesign. The app
never phones home. **`cargo install interlace` is still the CLI** — the
`.dmg` does not replace that crates.io name.

```bash
cargo install interlace --locked
# silent twin (same binary surface):
cargo install interlace-cli --locked
# or from this repo:
cargo install --path crates/interlace --locked
```

macOS only in Phase 1. Dev UI: `cd crates/interlace-tauri && npm run tauri:dev`.

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
It is **not** a fourth crates.io name. `interlace-tauri` is the unpublished
macOS window (also `publish = false`; not `cargo install interlace`).

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
- Desktop app (Phase 2): [docs/user/app.md](docs/user/app.md)
- Tauri hacking: [docs/hacking/tauri.md](docs/hacking/tauri.md)
- Release / publish: [docs/hacking/release.md](docs/hacking/release.md)

## License

MIT OR Apache-2.0
