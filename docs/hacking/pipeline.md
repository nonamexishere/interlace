# Agent pipeline

Agents talk **only through files**. The sequencer is `pipeline/run.sh` (no spawn).
Gates are `python3 pipeline/tools/gate_*.py` — exit 0 pass, 1 fail. An LLM
approving another LLM is not a gate.

## Layout

```
pipeline/stages/<id>/{IN.md,OUT.json,DONE,logs/}
pipeline/tools/*.py
pipeline/contracts/*.schema.json
pipeline/selftest/run.sh
```

Skip rule: `DONE` exists **and** `logs/gate.exit` is `0`.

Fix loop: max 3 per stage (`pipeline/state/FIX_TURN_<stage>`), then
`pipeline/stages/10-human-gate/` and a human `APPROVED` file.

## Commands used in CI today

```bash
python3 pipeline/tools/gate_bootstrap.py
python3 pipeline/tools/gate_deny.py
python3 pipeline/tools/gate_spikes.py
bash pipeline/selftest/run.sh
bash pipeline/run.sh
```

Later stages (`gate_schema`, `gate_api`, `gate_impl`, …) turn green as those PRs land.

## Blindness

Test-author jail may read `api/*.rs` signatures only.
`assert_blind.py` fails on `crates/interlace-core/src/**` impl paths.
