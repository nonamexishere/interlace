# Stage 01 — spikes (PR-S)

Read only:

- `docs/design/DESIGN.md` § "Top 3 riskiest unknowns + one-day spikes"
- Spike 4 is also P0 (half-day).

Write reports under `pipeline/stages/01-spikes/reports/spike-{1,2,3,4}.md`.
Write `pipeline/stages/01-spikes/OUT.json` matching `spike_report.schema.json`.

Rules:

- No product crate code in this stage.
- Spike 3 is fail-closed (`blocked=true` if irreplaceable hyper/reqwest/tokio).
- Spike 1 is fail-open (`pass=false` + `caveats[]` still allows the train).
- Spike 4 fail-open defaults to "extract Takeout dir only".
- Record URLs + licenses for any public sample lines (Spike 2). No real user exports.
