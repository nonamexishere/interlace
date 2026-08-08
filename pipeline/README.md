# Interlace agent pipeline

File-only stages. Sequencer: `./pipeline/run.sh` (does **not** spawn agents).

| Tool | When it is green |
| --- | --- |
| `gate_bootstrap.py` | workspace + published crate versions == workspace version + `cargo check -p interlace-core` + deny lock |
| `gate_deny.py` | bans+licenses ×3 pkgs, no reqwest/hyper/tokio |
| `gate_spikes.py` | stage 01 OUT.json + reports |
| `gate_schema.py` / `gate_api.py` / `gate_impl.py` / … | later PRs |

Selftest: `bash pipeline/selftest/run.sh` (F1–F6).

See `docs/hacking/pipeline.md` and DESIGN.md § Development pipeline.
