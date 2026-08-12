# Agent / session handoff

**Date:** 2026-08-13. **Owner:** Mustafa. **Repo:** [nonamexishere/interlace](https://github.com/nonamexishere/interlace) (public).

Read this first in a new session, then `gh pr list` / `gh issue list` (this file rots).
Do **not** dump real chat bodies or real contact names into issues, PRs, tests, or this file.

How we work: [`docs/hacking/pipeline.md`](pipeline.md) — test-author → impl → reviewer.
The parent chat sequences; agents do not spawn agents.

## Keep this file current

Update `docs/hacking/handoff.md` in the **same session** when any of these change
(prefer one short PR or the same product PR’s docs commit):

- HEAD / last merge on `master`
- Open vs closed product issues that affect “now”
- Recommended next steps order
- Machine paths, published versions, or tags (`v*`, `app-v*`)
- Dogfood archive facts (counts only — no names, no chat text)

Do **not** leave a session that merged product work with a stale “Snapshot” or
“Recommended next steps” section. If you only touched code and skipped this
file, say so in the wrap-up so the next agent rewrites it before coding.

## What Interlace is

OSS local-first offline desktop archive. Rust workspace + Tauri 2 macOS app.
SQLite+FTS5, CAS BLAKE3 (`cas/ab/cd/<hash>`). No server, no sync, no outbound
HTTP client (cargo-deny bans `reqwest`/`hyper`/`tokio` on core+cli; Tauri may
use `tokio` without `net`). Phase 1 = CLI; Phase 2 = Svelte 5 desktop UI
(UI0–UI8 done). **Active product track: Phase 2.1** (chat-shaped archive UI).

Normative spec: [`docs/design/DESIGN.md`](../design/DESIGN.md).
Roadmap index: issue **#52** (body is stale — rewrite when hygiene time allows).
Workflow: one issue → one PR `Fixes #N` → merge when CI jobs **`check`** +
**`tauri`** are green. Small conventional commits.

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
| Repo | `~/AllTogether/interlace/interlace` (this monorepo; not `~/Desktop/…`) |
| Live archive | `~/Interlace` (mode 0700, exclusive flock) |
| Archive backups | `~/Interlace.bak-2026-08-10`, `~/Interlace.bak-2026-08-11` (may exist) |
| WhatsApp exports | `~/Downloads/WhatsApp/*.zip` (3 official iOS ZIPs; glob, do not name people) |
| Installed CLI | `~/.cargo/bin/interlace` (rebuild from workspace; crates.io 0.1.1 may lag) |
| App support | `~/Library/Application Support/Interlace/` (`config.toml`, `last-archive.bookmark`) |
| Owner | `init --phone-region TR --name Mustafa` |

App holds exclusive flock. Close `interlace-app` / `tauri:dev` before CLI
`import` / `doctor --integrity` / wipe.

## Snapshot (2026-08-13)

Published: `interlace` / `interlace-core` / `interlace-cli` **0.1.1** (`v0.1.0`,
`v0.1.1` tags). Workspace version is still **0.1.1**. App crate
`interlace-tauri` is `publish = false`. **No `app-v*` tag yet** (unsigned
`.app`/`.dmg` can be built locally; not cut as a GitHub Release).

`master` is **protected**: required checks `check` + `tauri`, strict,
enforce_admins, no force-push, no delete, 0 required reviewers.
Do not flip the repo private without asking.

HEAD when this was rewritten: branch `feat/ui-search-platform-select` for **#121**
(search platform select) after **#120** virtualize. Re-check with
`git log -1` / `gh pr list`.

Live dogfood archive (`interlace --path ~/Interlace --json status`, counts only):

| Field | Value |
| --- | --- |
| messages | ~37k |
| identities | ~1.7k |
| persons_live | ~2.2k |
| review_open | 0 |
| region / owner | `TR` / Mustafa |
| last import | 2026-08-11 (done) |

Treat counts as approximate; never paste real names or message text here.

### Done — Phase 1 / 2 foundation (do not re-implement)

| # | What |
| --- | --- |
| #1 | Phase 1 epic — closed; CLI 0.1.0 / 0.1.1 published |
| #7 | Living pipeline prompts + `test_plan.json` map |
| #37 | Phase 2 epic — closed (UI0–UI8) |
| #44 | UI7 doctor + backup banner |
| #46 / PR #106 | UI8 unsigned `.app` / `.dmg` |
| #54 | Dogfood wipe + re-import 3 iOS WA ZIPs |
| #83 | Dogfood Takeout Contacts + Gmail |
| #88 / PR #139 | `--version` / `-V` |
| #100 / PR #142 | Later WA re-export unions (not duplicate) |
| #103 / PR #104 | `name_score` token align |
| UI0–UI6 | shell, search, people, review, import, empty states, shadcn, CAS photos |

### Done — Phase 2.1 + review polish (closed on/after 2026-08-11)

| # | What |
| --- | --- |
| #109 / PR #141 | Security-scoped bookmark; `.app` reopens last archive |
| #137 | Honest empty/error when sandbox denies remembered path |
| #110 / PR #145 | People list by last activity + preview |
| #111 / PR #153 | Chat bubbles (me right / them left), text nodes |
| #112 / PR #157 | UTC day headings on person timeline |
| #113 / PR #158 | Timeline opens at latest message |
| #114 / PR #160 | Compact conversation switcher for one person |
| #159 | People sidebar: no horizontal scroll (truncate / clip) |
| #156 | Boot: centered CSS spinner (pre-JS + Opening last archive) |
| #138 | People `/` filter matches linked phone/email identity values |
| #115 | Timeline platform chips + All / platform filter |
| #116 | Timeline kind filter (DMs / email / groups) AND platform |
| #117 | Gmail rows: subject title + fold quoted tails |
| #118 | In-window photo lightbox (local CAS) |
| #119 | Voice-note player chrome (local CAS; play/pause + time) |
| #120 | Virtualize person timeline (visible + overscan rows only) |
| #121 | Search platform is a closed select (Any / WhatsApp / Gmail) |
| #127 / PR #146 | Merge by picking a person (no raw ids) |
| #147 / PR #148 | Exact folded Contacts+WA names → review, never auto-merge |
| #149 / PR #150 | Review card: both sides’ samples / counts |
| #151 / PR #152 | Accept can fold every same-name person (n-way pick) |
| #143 / PR #144 | Takeout mbox split on `\nFrom ` (not blank-line-only) |
| #154 / PR #155 | Reviewer must score scope vs the issue |

Phase 2.1 milestone (#6): verify with `gh` (counts move as issues close).

## Open — product now (Phase 2.1)

Epic **#108**. Do **not** start Phase 1.1 (#57–#69) or Phase 3/4 (#72–#82)
while 2.1 is the product focus. Prefer one issue → one PR; thin UI chrome does
not need the full three-role loop unless behavior is load-bearing.

### Suggested next (hygiene polish first, then epic order)

| # | Note |
| --- | --- |
| **#122**–**#126** | Search: conversation-kind filter, person pick, jump-to-hit, has:media, safe highlight |
| **#128** | Review card shows both sides’ identifiers (not only names) |
| **#129**–**#136** | Window title, macOS menu, en+tr chrome, keyboard map, a11y, drag-drop, copy/reveal, defer doctor CAS |

Full board: issue **#108** and milestone [Phase 2.1 product UI](https://github.com/nonamexishere/interlace/milestone/6).

### Open — hygiene / parked (not product coding)

| # | Note |
| --- | --- |
| **#52** | Roadmap “now” table still points at #109 — rewrite when convenient |
| **#17** | Phase 1.1 umbrella — parked; not blocked; do not start children |
| **#84** | Satellite mirror READMEs — leftover docs on Phase 1 CLI milestone |
| Phase 1 CLI milestone | Still open with 1 leftover (#84); close milestone when #84 is done or moved |
| Phase 1.1 / 3 / 4 | Parked. Do not start. |

## Recommended next steps

1. Next coding **#122** (search conversation-kind filter) — continue **#108** search board (#122–#126), then app chrome (#128–#136).
2. Optional hygiene PR when idle: rewrite **#52** “now” table; decide **#84**.
3. Do **not** start 1.1 / P3 / P4. Do **not** cut `app-v*` without asking.

## Commands (copy-paste)

```bash
# CLI with this tree (not crates.io 0.1.1)
cargo install --path crates/interlace --locked --force

# status / integrity (close the app first if flock busy)
interlace --path ~/Interlace --json status
interlace --path ~/Interlace doctor --integrity

# wipe + re-import only if Mustafa asks (archive is already post-#54)
# mv ~/Interlace ~/Interlace.bak-$(date +%Y-%m-%d)
# interlace init --path ~/Interlace --phone-region TR --name Mustafa
# for z in ~/Downloads/WhatsApp/*.zip; do
#   interlace --path ~/Interlace import whatsapp "$z"
# done

# desktop UI
cd ~/AllTogether/interlace/interlace/crates/interlace-tauri
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
one-letter typo still ≥ 0.40. Exact folded Contacts FN vs WA name still
**review-only** (#147). N-way Accept can fold every same-name person with a
picker (#151). Tests use placeholders only (`Cemre Yıldız` / `Berk Özdemir`).

## Stack cheatsheet

- Workspace: `interlace`, `interlace-core`, `interlace-cli`, `interlace-cli-common`,
  `interlace-fixtures`, `interlace-tauri`.
- UI: Svelte 5 + Vite 7 + Tailwind 4 + owned shadcn-svelte in
  `crates/interlace-tauri/web/`.
- Dev: `npm run tauri:dev` (Vite HMR + Tauri wrapping cargo).
- CI: `.github/workflows/ci.yml` — `check` (Ubuntu, includes `gate_tests.py`) +
  `tauri` (macOS, `gate_tauri.py`).
- Tauri deny: `crates/interlace-tauri/deny.toml` (darwin graph targets).
- Pipeline prompts: `pipeline/prompts/{orchestrator,test-author,impl,reviewer}.md`.

## What not to do next

- Do not start Phase 3 (Telegram/iMessage/export) or Phase 4 (pHash/echo/Tantivy).
- Do not put real ZIP filenames, display names, or message text in tickets.
- Do not `cargo publish` / tag without asking.
- Do not require PR reviewers (solo). Reviewer **role** is still required
  (`pipeline/prompts/reviewer.md`); GitHub review-required is not.
- Do not enable `dangerousRemoteDomainIpcAccess`, `network.server`, or an
  HTTP client. Keep `network.client`.
- Do not leave this handoff stale after merges (see **Keep this file current**).

## New session prompt (paste)

> Read `docs/hacking/handoff.md` and `docs/hacking/pipeline.md`. Sequence
> test-author → impl → reviewer when load-bearing. Do not spawn agents from a
> child. Product now is Phase 2.1 (#108): next coding **#122** (search conversation-kind filter)
> then remaining board. Do not start 1.1 / P3 / P4. Do not dump chat bodies.
> Ask before crates.io, `v*`, or `app-v*` tags. After merges, update this handoff
> in the same session.
