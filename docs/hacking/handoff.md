# Agent / session handoff

**Date:** 2026-08-11. **Owner:** Mustafa. **Repo:** [nonamexishere/interlace](https://github.com/nonamexishere/interlace) (public).

Read this first in a new session, then `gh pr list` / `gh issue list` (this file rots).
Do **not** dump real chat bodies or real contact names into issues, PRs, tests, or this file.

How we work: [`docs/hacking/pipeline.md`](pipeline.md) — test-author → impl → reviewer.
The parent chat sequences; agents do not spawn agents.

## What Interlace is

OSS local-first offline desktop archive. Rust workspace + Tauri 2 macOS app.
SQLite+FTS5, CAS BLAKE3 (`cas/ab/cd/<hash>`). No server, no sync, no outbound
HTTP client (cargo-deny bans `reqwest`/`hyper`/`tokio` on core+cli; Tauri may
use `tokio` without `net`). Phase 1 = CLI; Phase 2 = Svelte 5 desktop UI
(UI0–UI8 done).

Normative spec: [`docs/design/DESIGN.md`](../design/DESIGN.md).
Roadmap index: issue **#52**. Workflow: one issue → one PR `Fixes #N` → merge
when CI jobs **`check`** + **`tauri`** are green. Small conventional commits.

## Non-negotiables

- No fake WhatsApp JID. Name-only identities **never auto-merge** (I2).
- `--phone-region` required at init (D20). D18: group vs DM; D18-C owner-name 1:1 → DM.
- D25 Gmail fold only on gmail/googlemail. No SQLCipher; do not claim encryption.
- CSP `connect-src` is IPC-only (`ipc:` / `ipc.localhost`), not `'none'`
  (that blanked the `.app`). No `protocol-asset` if it opens remote/http-range.
- Sandbox **keeps `network.client`** (WKWebView / `tauri://` will not paint
  without it) and **omits `network.server`**. No HTTP client crate, no updater.
- Tests use `interlace-fixtures` + **placeholder names** only.
- Confirm with Mustafa before another crates.io tag / `v*` / `app-v*` publish.
- Do not kill other projects’ Metro/Docker. Do not force-push `master`.

## Machine paths (this Mac)

| What | Path |
| --- | --- |
| Repo | `~/Desktop/interlace/interlace` |
| Live archive | `~/Interlace` (mode 0700, exclusive flock) |
| Previous archive backup | `~/Interlace.bak-2026-08-10` (may exist if he already wiped) |
| WhatsApp exports | `~/Downloads/WhatsApp/*.zip` (3 official iOS ZIPs; glob, do not name people) |
| Installed CLI | `~/.cargo/bin/interlace` (rebuild from workspace; crates.io 0.1.1 may lag) |
| Last-archive pointer | `~/Library/Application Support/Interlace/last-archive-path` |
| Owner | `init --phone-region TR --name Mustafa` |

App holds exclusive flock. Close `interlace-app` / `tauri:dev` before CLI
`import` / `doctor --integrity` / wipe.

## Snapshot (2026-08-11)

Published: `interlace` / `interlace-core` / `interlace-cli` **0.1.1** (`v0.1.0`, `v0.1.1` tags).
App crate `interlace-tauri` is `publish = false`. **No `app-v*` tag yet.**

`master` is **protected**: required checks `check` + `tauri`, strict,
enforce_admins, no force-push, no delete, 0 required reviewers.
Do not flip the repo private without asking.

HEAD when this was rewritten: `e700f5e` (merge #139 `--version`). In sync
with `origin/master`. CI green. **Zero open PRs.**

### Done (do not re-implement)

| # | What |
| --- | --- |
| #37 | Phase 2 epic — closed |
| #44 | UI7 doctor + backup banner |
| #46 / PR #106 | UI8 unsigned `.app` / `.dmg` |
| #103 / PR #104 | `name_score` token align |
| #88 / PR #139 | `--version` / `-V` (#89 closed unmerged) |
| UI0–UI6 | shell, search, people, review, import, empty states, shadcn, CAS photos |

Phase 2 milestone should be **closed** (0 open / 17 closed). Do not re-close #37.

### Open — hygiene then product

Phase 2.1 epic **#108** (31 children). Do **not** start Phase 1.1 (#57–#69) or
Phase 3/4 (#72–#82) while dogfood + a thin 2.1 are open.

| # | Note |
| --- | --- |
| **#7** | This PR (`Fixes #7`): `test_plan.json` + living prompts. Close with a comment that 1.1 IDs stay on #57–#69 and the plan is a map, not proof of blindness. |
| **#1** | Phase 1 epic — close after #7; 0.1.0/0.1.1 already published |
| **#17** | Unstick (`Blocked by #16` is false); move to Phase 1.1 milestone |
| **#52** | Rewrite “now” table after hygiene |
| **#54** | Wipe + re-import 3 iOS WA ZIPs (dirty archive; counts only) |
| **#83** | Takeout Contacts + Gmail dogfood |
| **#84** | Satellite README redirect — leftover docs on Phase 1 CLI milestone |
| **#100** | Later re-export of the same chat must union — **first issue that must use the three-role loop** |
| **#109** | Security-scoped bookmark so `.app` reopens last archive |

## Recommended next steps

1. Land `Fixes #7` (this branch). Comment + close #7.
2. GitHub hygiene: close #1; close Phase 2 milestone only; unstick/move #17; rewrite #52; decide #84.
3. Optional dogfood **#54** (commented commands below). Ask before wiping.
4. Product: **#109** bookmark, **#83** Takeout, then **#100** via test-author → impl → reviewer.
5. One chat-surface PR after that — not eleven Phase 2.1 atoms. Do not start 1.1 / P3 / P4.

## Commands (copy-paste)

```bash
# CLI with this tree (not crates.io 0.1.1)
cargo install --path crates/interlace --locked --force

# optional wipe + re-import (#54). Close the app first. Ask Mustafa.
# mv ~/Interlace ~/Interlace.bak-2026-08-11
# interlace init --path ~/Interlace --phone-region TR --name Mustafa
# for z in ~/Downloads/WhatsApp/*.zip; do
#   interlace --path ~/Interlace import whatsapp "$z"
# done
# interlace --path ~/Interlace --json status
# interlace --path ~/Interlace doctor --integrity

# desktop UI
cd ~/Desktop/interlace/interlace/crates/interlace-tauri
npm install
npm run tauri:dev    # NOT bare `npm run tauri` (prints help only)
```

Folder of WA ZIPs: CLI is **one file per** `import whatsapp <FILE>`. The app
Import picker accepts the folder (UI5 fix).

Do **not** `gh pr merge` old PRs. Do **not** `cargo publish` / tag `v*` or
`app-v*` without asking. `app-v0.1.1` is still untagged.

## Review tab

Not a chat view. Queue of “are these two identities the same person?”
Phone/email exact → auto. **Name never auto-merges.** Accept links identity →
person (`review_accepted`); Reject suppresses the pair. Sample lines are
evidence, not the timeline.

`name_score` (PR #104) aligns tokens: leftover tokens on both sides → 0.0;
one-letter typo still ≥ 0.40. Tests in `identity.rs` use placeholders only
(`Cemre Yıldız` / `Berk Özdemir`).

## Dogfood notes (counts only)

- Init region `TR`, owner display `Mustafa`.
- 3 iOS WA ZIPs. After 0.1.0: many `kind=unknown` (unpadded day) + 1:1 as
  `group` — wipe is the honest fix (#54). 0.1.1 has locale + D18-C.
- Last `status` seen ~16k messages / 6 identities; treat as possibly dirty
  until #54.
- `#100`: same chat re-exported later must union, not duplicate messages.

## Stack cheatsheet

- Workspace: `interlace`, `interlace-core`, `interlace-cli`, `interlace-cli-common`,
  `interlace-fixtures`, `interlace-tauri`.
- UI: Svelte 5 + Vite 7 + Tailwind 4 + owned shadcn-svelte in
  `crates/interlace-tauri/web/`.
- Dev: `npm run tauri:dev` (Vite HMR + Tauri wrapping cargo).
- CI: `.github/workflows/ci.yml` — `check` (Ubuntu, includes `gate_tests.py`) +
  `tauri` (macOS, `gate_tauri.py`).
- Tauri deny: `crates/interlace-tauri/deny.toml` (darwin graph targets).

## What not to do next

- Do not start Phase 3 (Telegram/iMessage/export) or Phase 4 (pHash/echo/Tantivy).
- Do not put real ZIP filenames, display names, or message text in tickets.
- Do not `cargo publish` / tag without asking.
- Do not require PR reviewers (solo). Reviewer **role** is still required
  (`pipeline/prompts/reviewer.md`); GitHub review-required is not.
- Do not enable `dangerousRemoteDomainIpcAccess`, `network.server`, or an
  HTTP client. Keep `network.client`.

## New session prompt (paste)

> Read `docs/hacking/handoff.md` and `docs/hacking/pipeline.md`. Sequence
> test-author → impl → reviewer. Do not spawn agents from a child. Stay on
> issue order after hygiene: #54 (ask before wipe), #109, #83, then #100.
> Do not dump chat bodies. Ask before crates.io, `v*`, or `app-v*` tags.
