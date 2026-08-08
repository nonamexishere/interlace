# Spike 3 — deny tree of MIME/zip/sqlite

**Date:** 2026-08-08  
**Host:** macOS, rustc via local cargo, `cargo-deny 0.18.2`  
**Throwaway crate:** `/tmp/il-spike3/spike` (not in repo)

## Question

Do Phase 1 crates (`rusqlite` bundled, `zip`, `blake3`, `mailparse`, `encoding_rs`, `clap`, `serde`, `serde_json`, `thiserror`, `chrono`) pull `reqwest` / `hyper` / `h2` / `tokio`?

## Method

Created a dummy lib with those deps and the DESIGN.md `deny.toml`. Ran:

```
cargo fetch
cargo tree -i reqwest|hyper|hyper-util|h2|tokio
cargo deny check bans
cargo deny check licenses   # after setting dummy crate license = MIT OR Apache-2.0
```

Separate probe crate with only `phonenumber = "0.3"`.

Did **not** add `image` (Phase 4) or `tokio`.

## Results

| Check | Result |
| --- | --- |
| `reqwest` / `hyper` / `h2` / `tokio` in Phase 1 tree | **absent** (`cargo tree -i` no match) |
| `cargo deny check bans` | **ok** (duplicate `syn` warn only) |
| `cargo deny check licenses` | **ok** once dummy has a license field |
| `mailparse` 0.16.1 | license **0BSD**; deps `charset`, `data-encoding`, `quoted_printable`, `encoding_rs` — no HTTP |
| `phonenumber` 0.3.10 | **no** reqwest/hyper/tokio; safe to use in Phase 1 if wanted |
| `image` | not tested (out of Phase 1) |

`chrono` pulled `wasm-bindgen` via `iana-time-zone` (types, not a client). Not banned.

## Verdict

**pass = true.** `blocked = false`.

Phase 1 dependency set is compatible with the literal client ban. Keep 0BSD on the license allowlist for `mailparse`. `phonenumber` is optional and clean.

## Caveats

- Dummy crate must declare `license` or `cargo deny check licenses` fails on the workspace package itself.
- `zip` 2.x pulled `arbitrary`/`syn` duplicates (`multiple-versions = warn`). Fine.
- Re-run deny after every new dependency in PR1+.
