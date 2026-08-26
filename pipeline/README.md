# Interlace agent pipeline

Living loop: **researcher → test-author → impl → reviewer**. Prompts in `pipeline/prompts/`. Skip researcher only when the issue already names helpers, files, and must-IDs.
The human / parent chat sequences. Do not spawn agents.

`./pipeline/run.sh` only re-checks finished spike stage 01 (does **not** spawn).

| Tool | When it is green |
| --- | --- |
| `gate_bootstrap.py` | workspace + published crate versions == workspace version + `cargo check -p interlace-core` + deny lock |
| `gate_deny.py` | bans+licenses ×3 pkgs, no reqwest/hyper/tokio |
| `gate_spikes.py` | stage 01 OUT.json + reports |
| `gate_tests.py` | `03-test-author/test_plan.json` has CAS1–S3; tests have no `todo!` |
| `gate_schema.py` / `gate_api.py` / `gate_impl.py` / … | schema, API freeze, must-ID impl gates |

Selftest: `bash pipeline/selftest/run.sh` (F1–F6).

See `docs/hacking/pipeline.md` and DESIGN.md § Development pipeline.
