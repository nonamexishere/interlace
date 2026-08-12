# Agent pipeline

Agents talk **only through files and prompts**. The sequencer is a human or
this chat — never a child agent spawning another child. Gates are
`python3 pipeline/tools/gate_*.py` (exit 0 pass, 1 fail). An LLM approving
another LLM is not a gate.

How we work on a product issue:

```
orchestrator  →  test-author  →  impl  →  gates  →  reviewer  →  human merge
```

Prompts live in `pipeline/prompts/`. Read `orchestrator.md` first.

## Roles

| Role | Prompt | Does | Must not |
| --- | --- | --- | --- |
| orchestrator | `prompts/orchestrator.md` | Sequence the loop; copy issue → scratch `IN.md` | Implement; give a child a spawn tool |
| test-author | `prompts/test-author.md` | Write tests from the issue + public API | Open parser/identity/search impl bodies; invent policy |
| impl | `prompts/impl.md` | Make those tests and the matching gate green | Edit tests; ignore must-IDs; add HTTP clients |
| reviewer | `prompts/reviewer.md` | Structured notes: **scope vs issue** (Do/Acceptance/Not) plus correctness | Merge; patch source; count as a gate; invent a ticket |
| human + CI | `gate_*.py` | The actual gate | — |

Producer ≠ verifier. The agent that writes tests is not the one that writes the impl.

### How to run a product issue

1. Copy the GitHub issue into a scratch `IN.md`. No real chat bodies, no real contact names.
2. Run **test-author** with `pipeline/prompts/test-author.md`.
3. Confirm new tests exist. For new behavior they should fail for the right reason (not compile errors).
4. Run **impl** with `pipeline/prompts/impl.md`.
5. Run the matching `gate_*.py` (see CI block below). Red → impl retries, max 3, then stop.
6. Run **reviewer** with `pipeline/prompts/reviewer.md` and the same `IN.md`. It must fill **Scope** (in / out / extra).
7. Merge when jobs **`check`** + **`tauri`** are green and the review has no open bugs (including scope: missing / out). `Fixes #N`. Ask before commit / push / merge.

### When blindness applies

- **Yes** — WhatsApp / Gmail / Contacts parsers, identity, search. Test-author may read `model.rs` and `lib.rs` signatures, not those impl files. `assert_blind.py` fails on `crates/interlace-core/src/**` impl paths in a test-author `IN.md`.
- **No (Tauri chrome)** — test-author still writes acceptance from the issue only; impl still must not edit those tests.

### Done vs parked

Phase 1 product stages already shipped. `pipeline/run.sh` only sequences `01-spikes`; that is intentional, not a missing bootstrap. Do not recreate empty 00/02/05* stage dirs.

`pipeline/stages/03-test-author/test_plan.json` is a **map of tests that exist** (CAS1–S3). It is not proof those tests were authored blind. New CAS/W/M/C/I/S cases must update that file.

Phase 1.1 (`#57`–`#69`), Phase 3/4, and dogfood wipes are not this page’s job to start. First issue that must use the loop: **#100** (later WA export unions).

## Layout

```
pipeline/prompts/{orchestrator,test-author,impl,reviewer}.md
pipeline/stages/<id>/{IN.md,OUT.json,DONE,logs/}
pipeline/stages/03-test-author/test_plan.json
pipeline/tools/*.py
pipeline/contracts/*.schema.json
pipeline/selftest/run.sh
```

Skip rule: `DONE` exists **and** `logs/gate.exit` is `0`.

Fix loop: max 3 per impl attempt, then a human. Do not invoke test-author to soften tests.

## Commands used in CI today

```bash
python3 pipeline/tools/gate_bootstrap.py
python3 pipeline/tools/gate_deny.py
python3 pipeline/tools/gate_spikes.py
python3 pipeline/tools/gate_schema.py
python3 pipeline/tools/gate_api.py
python3 pipeline/tools/gate_tests.py
python3 pipeline/tools/gate_fixtures.py
python3 pipeline/tools/gate_impl.py --stage 05a --must CAS1,CAS2,CAS3
python3 pipeline/tools/gate_impl.py --stage 05b --must W1,W2,W3,W4
python3 pipeline/tools/gate_impl.py --stage 05c --must M1,M2,M3,C1
python3 pipeline/tools/gate_impl.py --stage 05d --must I1,I2,I3,I4,I5,I6,I6b
python3 pipeline/tools/gate_impl.py --stage 05e --must S1,S2,S3
python3 pipeline/tools/gate_cli.py
python3 pipeline/tools/gate_bench.py   # 10k only; do not set INTERLACE_BENCH in PR
python3 pipeline/tools/gate_tauri.py   # Phase 2 shell; separate CI job
bash pipeline/selftest/run.sh
bash pipeline/run.sh
```

Nightly (not PR): `INTERLACE_BENCH=1M|10M cargo bench -p interlace-core --bench search`
then `python3 pipeline/tools/bench_gate.py pipeline/stages/07-bench/OUT.json`.
