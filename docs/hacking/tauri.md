# Tauri desktop shell (Phase 2)

Unpublished crate `crates/interlace-tauri` (`publish = false`).
`cargo install interlace` is still the **CLI** (D3).

## Run

```bash
cargo run -p interlace-tauri
```

Binary name: `interlace-app`. Not in workspace `default-members`.

## Deny

Do **not** run the repo-root `deny.toml` against this package (it bans `tokio`).
Use `crates/interlace-tauri/deny.toml`:

- allows `tokio` **without** `net` (Tauri 2.11 on macOS uses `rt` / `fs` / `sync` only)
- still denies `reqwest`, `hyper`, `tauri-plugin-http`, `tauri-plugin-updater`
- `[graph].targets` is darwin-only so mobile/wasm optional deps do not fail the gate

```bash
python3 pipeline/tools/gate_tauri.py
```

## Security

- CSP is the DESIGN string (`connect-src 'none'`).
- `Interlace.entitlements`: app sandbox, user-selected files, **no**
  `network.client` / `network.server`.
- Message bodies in later PRs are text nodes only (never unsanitized HTML).

## Commands (UI1)

`remembered_path`, `pick_folder` (rfd on the main thread), `init`, `open`,
`status`. `init` / `open` take a **local folder path** only. Session state
holds `Archive` with `LockMode::Exclusive`.

## Issue DAG

Epic #37. UI0 (#38) → UI1 archive (#39) → UI3 timeline / UI2 search / UI4 review / UI5 import.
