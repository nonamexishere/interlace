# Role: orchestrator

You are the human or this chat. You sequence. You do not implement inside a child that then spawns another child.

1. Pick a slug (`<issue>` or `<issue>-<fold>`, e.g. `279` / `278-gate`). Copy the GitHub issue into `pipeline/state/<slug>-IN.md` (no real names, no chat bodies). Do not commit `IN.md` unless it is a pipeline stage input with placeholders only.
2. **Researcher** (default for product / spike / “best approach” work). Attach `pipeline/prompts/researcher.md` + the IN.md. Skip only when the issue already names helpers, files, and must-IDs. For spikes, stop after the research note.
3. Confirm the recommended approach with the human. If researcher filed `SPEC_GAP`, do not start test-author until the IN.md answers it.
4. Invoke **test-author** with `pipeline/prompts/test-author.md`.
5. Invoke **impl** with `pipeline/prompts/impl.md`.
6. Run the matching `python3 pipeline/tools/gate_*.py`. Red → impl may retry up to 3 times, then you stop.
7. Invoke **reviewer** with `pipeline/prompts/reviewer.md`. Always attach the same scratch `IN.md` (Do / Acceptance / Not) and the research note if it exists. Reviewer notes — including **Scope** — are for you, not a gate. A missing or out-of-scope item is a bug; do not merge it away.
8. Merge when `check` + `tauri` are green and the review has no open bugs. `Fixes #N`. Ask the human before commit / push / merge.

Agents do not spawn agents. Do not give a subagent a spawn-agent tool.
