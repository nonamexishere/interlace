# Roadmap (now → Phase 4)

Canonical in-repo copy of issue **#52**. Work top-down. One issue → one PR
(`Fixes #N`). How we work: [pipeline.md](pipeline.md) (test-author → impl →
reviewer; parent chat sequences those roles as separate agents; CI is the gate).

Do **not** start Phase 1.1 (#57–#69) or Phase 3/4 (#72–#82) until Mustafa
picks one. Phase 2.1 is **done** (epic #108 and milestone 6 closed).

## Now

| What | Notes |
| --- | --- |
| Hygiene | This pass: rewrite this table (#52); satellite READMEs (#84). Then pick the next **phase** — do not invent a 2.2 epic. |
| `app-v*` | Unsigned `.app`/`.dmg` GitHub Release. **Ask** before tagging. |
| crates.io | Published **0.1.1**. Do not `cargo publish` / `v*` without asking. |

## Leftover (not a product phase)

| # | What |
| --- | --- |
| [#84](https://github.com/nonamexishere/interlace/issues/84) | Satellite README redirect (`interlace-core` / `interlace-cli`). See [mirrors.md](mirrors.md). |

## Done (do not re-implement)

- Phase 1 epic [#1](https://github.com/nonamexishere/interlace/issues/1) — CLI 0.1.0 / 0.1.1.
- Phase 2 epic [#37](https://github.com/nonamexishere/interlace/issues/37) — UI0–UI8.
- Phase 2.1 epic [#108](https://github.com/nonamexishere/interlace/issues/108) and [milestone 6](https://github.com/nonamexishere/interlace/milestone/6) — chat-shaped archive UI (through #136 plus #170 / #184).

## Parked — Phase 1.1 CLI — epic [#17](https://github.com/nonamexishere/interlace/issues/17)

Same CLI, not a new product. Do not start until chosen.

#57 W5 · #58 W6 · #59 W7 · #60 W9 · #61 W8 · #62 M4 · #63 M4b · #64 M5 · #65 M6 · #66 C2 · #67 C3 · #68 S4 · #69 resume/spill.

## Parked — Phase 3 — epic [#55](https://github.com/nonamexishere/interlace/issues/55)

#72 export jsonl · #73 export mbox · #74 export media-zip · #75 schema_epoch · #76 Telegram · #77 iMessage spike · #78 Windows+Linux CLI.

## Parked — Phase 4 — epic [#56](https://github.com/nonamexishere/interlace/issues/56)

#79 `--preserve-raw` · #80 photo pHash · #81 behavioral echo · #82 tokenizer / Tantivy if needed.

## Intentionally not on the road

Fake JID, name auto-merge, updater, “encrypted DB” claim, HTTP client, `network.server`.

**How to look:** GitHub → Issues → Milestones: [Phase 1 CLI](https://github.com/nonamexishere/interlace/milestone/1) · [Phase 2 UI](https://github.com/nonamexishere/interlace/milestone/2) (closed) · [Phase 2.1](https://github.com/nonamexishere/interlace/milestone/6) (closed) · [Phase 1.1](https://github.com/nonamexishere/interlace/milestone/3) · [Phase 3](https://github.com/nonamexishere/interlace/milestone/4) · [Phase 4](https://github.com/nonamexishere/interlace/milestone/5).
