# Roadmap (now → Phase 4)

Canonical in-repo copy of issue **#52**. Work top-down. One issue → one PR
(`Fixes #N`). How we work: [pipeline.md](pipeline.md) (test-author → impl →
reviewer; parent chat sequences those roles as separate agents; CI is the gate).

Do **not** start Phase 1.1 (#57–#69) or Phase 3/4 (#72–#82) unprompted.
Phase 2.1 is **done**. Phase 2.2 polish is **done**.

## Now

| What | Notes |
| --- | --- |
| Phase 2.3 | Epic [#264](https://github.com/nonamexishere/interlace/issues/264). **#265** / [PR #282](https://github.com/nonamexishere/interlace/pull/282), **#266** / [PR #283](https://github.com/nonamexishere/interlace/pull/283), **#267** / [PR #285](https://github.com/nonamexishere/interlace/pull/285), **#268** / [PR #286](https://github.com/nonamexishere/interlace/pull/286), **#269** / [PR #287](https://github.com/nonamexishere/interlace/pull/287), **#270** / [PR #288](https://github.com/nonamexishere/interlace/pull/288), **#271** / [PR #289](https://github.com/nonamexishere/interlace/pull/289), **#272** / [PR #290](https://github.com/nonamexishere/interlace/pull/290), **#273** / [PR #291](https://github.com/nonamexishere/interlace/pull/291), and **#274** / [PR #292](https://github.com/nonamexishere/interlace/pull/292) done. **#275** in flight; next coding **#276**. Do not start 1.1 / P3 / P4. Ask before the first notarized `app-v*`. |
| Phase 2.2 | Epic [#197](https://github.com/nonamexishere/interlace/issues/197) / [milestone 7](https://github.com/nonamexishere/interlace/milestone/7). Normative [`UI-DESIGN.md`](../design/UI-DESIGN.md). **Done** (#198–#222 / PRs #225–#262). |
| Desktop app | **`app-v0.1.2` shipped** ([release](https://github.com/nonamexishere/interlace/releases/tag/app-v0.1.2)). Ask before another `app-v*`. |
| crates.io | Published **0.1.1**. Do not `cargo publish` / `v*` without asking. |

## Done (do not re-implement)

- Phase 1 epic [#1](https://github.com/nonamexishere/interlace/issues/1) — CLI 0.1.0 / 0.1.1. Phase 1 CLI milestone closed.
- Phase 2 epic [#37](https://github.com/nonamexishere/interlace/issues/37) — UI0–UI8.
- Phase 2.1 epic [#108](https://github.com/nonamexishere/interlace/issues/108) and [milestone 6](https://github.com/nonamexishere/interlace/milestone/6) — chat-shaped archive UI (through #136 plus #170 / #184).
- Hygiene [#52](https://github.com/nonamexishere/interlace/issues/52) / [#84](https://github.com/nonamexishere/interlace/issues/84) — this roadmap + satellite README redirects ([mirrors.md](mirrors.md)).
- First unsigned app tag **`app-v0.1.1`**.

## Parked — Phase 1.1 CLI — epic [#17](https://github.com/nonamexishere/interlace/issues/17)

Same CLI, not a new product. Do not start until chosen.

#57 W5 · #58 W6 · #59 W7 · #60 W9 · #61 W8 · #62 M4 · #63 M4b · #64 M5 · #65 M6 · #66 C2 · #67 C3 · #68 S4 · #69 resume/spill.

## Parked — Phase 3 — epic [#55](https://github.com/nonamexishere/interlace/issues/55)

#72 export jsonl · #73 export mbox · #74 export media-zip · #75 schema_epoch · #76 Telegram · #77 iMessage spike · #78 Windows+Linux CLI.

## Parked — Phase 4 — epic [#56](https://github.com/nonamexishere/interlace/issues/56)

#79 `--preserve-raw` · #80 photo pHash · #81 behavioral echo · #82 tokenizer / Tantivy if needed.

## Intentionally not on the road

Fake JID, name auto-merge, updater, “encrypted DB” claim, HTTP client, `network.server`.

**How to look:** GitHub → Issues → Milestones: [Phase 1 CLI](https://github.com/nonamexishere/interlace/milestone/1) (closed) · [Phase 2 UI](https://github.com/nonamexishere/interlace/milestone/2) (closed) · [Phase 2.1](https://github.com/nonamexishere/interlace/milestone/6) (closed) · [Phase 2.2 UI/UX](https://github.com/nonamexishere/interlace/milestone/7) · [Phase 1.1](https://github.com/nonamexishere/interlace/milestone/3) · [Phase 3](https://github.com/nonamexishere/interlace/milestone/4) · [Phase 4](https://github.com/nonamexishere/interlace/milestone/5).
