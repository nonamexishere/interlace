# Tauri desktop shell (Phase 2)

Unpublished crate `crates/interlace-tauri` (`publish = false`).
`cargo install interlace` is still the **CLI** (D3).

## Run

Frontend is **Svelte 5 + Vite** (`web/`). Owned shadcn-svelte (New York / zinc)
primitives live in `web/lib/components/ui/` (button, input, dialog, scroll).
Merge/unlink/undo use `ConfirmDialog`, not `window.confirm`. No CDN.

Dev (HMR):

```bash
cd crates/interlace-tauri
npm install
npm run tauri:dev
```

(`npm run tauri -- dev` is the same; bare `npm run tauri` only prints CLI help.)

Release-like (static `dist/` + Rust):

```bash
cd crates/interlace-tauri && npm run build
cargo run -p interlace-tauri
```

Binary name: `interlace-app`. Not in workspace `default-members`.
Production CSP is `connect-src 'none'`. Vite `localhost` is **dev only**.

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

- CSP is the DESIGN string (`connect-src 'none'`). `img-src` / `media-src`
  allow `cas:` for the local CAS protocol only (64-hex path under `$ARCHIVE/cas/`).
- `Interlace.entitlements`: app sandbox, user-selected files, **no**
  `network.client` / `network.server`.
- Message bodies in later PRs are text nodes only (never unsanitized HTML).

## Commands (UI1)

`remembered_path`, `pick_folder` / `pick_import_path` (rfd on the main thread),
`init`, `open`, `status`, `people`, `person_show`, `person_timeline`,
`person_merge_cmd`, `person_unlink_cmd`, `person_undo_cmd`, `link_events`,
`search_cmd`, `search_body`, `review_list_cmd` / `review_show_cmd` /
`review_accept_cmd` / `review_reject_cmd`, `import_start`, `import_progress`,
`doctor_issues_cmd`, `doctor_run_cmd` (integrity / rebuild FTS / GC CAS).
`init` / `open` take a **local folder path** only. Session state holds
`Archive` with `LockMode::Exclusive`. Timeline/search bodies are text nodes.

## Issue DAG

Epic #37. UI0–UI6 done. UI7 (#44) Doctor tab + cloud-path banner. UI8 unsigned dmg.
