# Tauri desktop shell (Phase 2)

Unpublished crate `crates/interlace-tauri` (`publish = false`).
`cargo install interlace` is still the **CLI** (D3).

## Run

Frontend is **Svelte 5 + Vite** (`web/`). Owned shadcn-svelte (New York / zinc)
primitives live in `web/lib/components/ui/` (button, input, dialog, scroll,
tooltip, separator, badge, card).
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

Unsigned `.app` / `.dmg` (UI8):

```bash
cd crates/interlace-tauri
npm run tauri:build
# → ../../target/release/bundle/macos/Interlace.app
# → ../../target/release/bundle/dmg/*.dmg
python3 ../../pipeline/tools/gate_app_bundle.py
```

Tags `app-v*` (not `v*`) upload those artifacts. First ship: **`app-v0.1.1`**.
See [release.md](release.md).

Binary name: `interlace-app`. Not in workspace `default-members`.
Production CSP allows **only** Tauri IPC (`ipc:` / `ipc.localhost`), not the
network. `connect-src 'none'` blanks the `.app`. Vite `base: './'` so bundled
JS is relative. Dev URL `localhost:1420` is **dev only**.
`bundle.createUpdaterArtifacts` stays false.

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

- CSP is the DESIGN string (IPC-only `connect-src`, no general `http`/`https`).
  `img-src` / `media-src` allow `cas:` for the local CAS protocol only.
- `Interlace.entitlements`: sandbox, `allow-jit`, user-selected files,
  **`bookmarks.app-scope`**, **`network.client`** (WKWebView will not paint
  `tauri://localhost` without it — measured blank `.app`). **No
  `network.server`.** Still no `reqwest` / http plugin; CSP cannot connect to
  the internet.
- Last folder: after a successful rfd `init` / `open`, Tauri writes
  `last_archive_path` in `config.toml` **and** an opaque security-scoped
  bookmark in `last-archive.bookmark` (same `INTERLACE_CONFIG_DIR`). CLI
  `init` / `open --path` write only the path pointer — that is not enough
  inside the sandbox. `remembered_path` resolves the bookmark with
  `NSURLBookmarkResolutionWithSecurityScope` and
  `startAccessingSecurityScopedResource`. Stale / failed resolve returns no
  path (picker). No bookmark + leftover path → try the path; sandboxed
  `.app` gets EPERM and the #137 sentence alone (no raw errno).
- Message bodies in later PRs are text nodes only (never unsanitized HTML).

## Commands (UI1)

Native macOS menu (`MenuBuilder` in `main.rs`): Interlace About + Quit, File
Open archive + Import, View (People / Search / Review / Doctor). About copy is
offline / not encrypted at rest / FileVault. No updater / Check for Updates.

`remembered_path` (bookmark first, else last-path pointer), `pick_folder` /
`pick_import_path` (rfd on the main thread), `init`, `open`, `status`,
`people`, `person_show`, `person_timeline`, `person_merge_cmd`,
`person_unlink_cmd`, `person_undo_cmd`, `link_events`, `search_cmd`,
`search_body`, `review_list_cmd` / `review_show_cmd` / `review_accept_cmd` /
`review_reject_cmd`, `import_start`, `import_progress`, `doctor_issues_cmd`,
`doctor_run_cmd` (integrity / rebuild FTS / GC CAS). `init` / `open` take a
**local folder path** only. Session state holds `Archive` with
`LockMode::Exclusive`. Timeline/search bodies are text nodes.

## Issue DAG

Epic #37. UI0–UI7 done. UI8 (#46) unsigned `.app`/`.dmg` on `app-v*` tags.
