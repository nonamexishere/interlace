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

## Today (UI0)

Placeholder window only. Init, import, search, and timelines are the next
issues (UI1–UI5). Until then use the CLI:

```bash
interlace init --path ~/Interlace --phone-region TR --name "Your Name"
interlace import whatsapp ./chat.zip
```

## Encryption

Not encrypted at rest. The folder is the backup unit. Use FileVault. See
[backup.md](backup.md).
