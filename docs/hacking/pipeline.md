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
python3 pipeline/tools/gate_schema.py
python3 pipeline/tools/gate_api.py
python3 pipeline/tools/gate_fixtures.py
python3 pipeline/tools/gate_impl.py --stage 05a --must CAS1,CAS2,CAS3
python3 pipeline/tools/gate_impl.py --stage 05b --must W1,W2,W3,W4
python3 pipeline/tools/gate_impl.py --stage 05c --must M1,M2,M3,C1
python3 pipeline/tools/gate_impl.py --stage 05d --must I1,I2,I3,I4,I5,I6,I6b
python3 pipeline/tools/gate_impl.py --stage 05e --must S1,S2,S3
python3 pipeline/tools/gate_cli.py
python3 pipeline/tools/gate_bench.py   # 10k only; do not set INTERLACE_BENCH in PR
bash pipeline/selftest/run.sh
bash pipeline/run.sh
```

Nightly (not PR): `INTERLACE_BENCH=1M|10M cargo bench -p interlace-core --bench search`
then `python3 pipeline/tools/bench_gate.py pipeline/stages/07-bench/OUT.json`.

## Blindness

Test-author jail may read `api/*.rs` signatures only.
`assert_blind.py` fails on `crates/interlace-core/src/**` impl paths.
