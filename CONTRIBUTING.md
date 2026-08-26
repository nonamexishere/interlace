# Contributing to Interlace

## Before you write code

1. Read `docs/design/DESIGN.md` (normative). Key Decisions are not reopened in drive-by PRs.
2. Read `docs/hacking/add-a-source.md` if you are adding a parser (file lands with later PRs).
3. Do not send real personal exports. Tests use `interlace-fixtures` only.

## Dev setup (macOS)

```bash
git clone https://github.com/nonamexishere/interlace
cd interlace
rustup show   # rust-toolchain.toml pins stable
cargo test --workspace --exclude interlace-tauri
python3 pipeline/tools/gate_bootstrap.py
python3 pipeline/tools/gate_deny.py
python3 pipeline/tools/gate_tauri.py   # Phase 2 shell; needs cargo-deny
```

Phase 1 target is macOS. Other OSes may compile; they are unsupported.

## PR rules

- One concern per PR. Follow the PR plan in DESIGN.md when possible.
- **Docs in the same PR** as the behavior (D24).
- Phase 1 must-pass IDs cannot be `#[ignore]`.
- No `reqwest`, `hyper`, `tokio` in `interlace-core` / `interlace` / `interlace-cli`.
  `interlace-tauri` may use `tokio` without `net`; still no HTTP client plugins.
- Open Questions 1–10 are decided in DESIGN.md; do not re-open them.
- `cargo fmt`, `clippy -D warnings`, `cargo deny check bans` + `licenses` must pass.
- Reference the GitHub issue: `Fixes #N`.

## Agent / pipeline contributors

Product work uses **researcher → test-author → impl → reviewer**.
Skip researcher only when the issue already names helpers, files, and must-IDs.
The human (or the parent chat) sequences them. See
`docs/hacking/pipeline.md` and `pipeline/prompts/`. Subagents communicate via
files and those prompts only. Do not give agents a spawn-agent tool.
Humans may still run `pipeline/run.sh` (it only re-checks finished spike
stage 01).

## Commit messages

Conventional, present tense: `feat(core): whatsapp locale voter`, `docs(user): resume flock`.

## Code of conduct

[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
