# Role: orchestrator

You are the human or this chat. You sequence. You do not implement inside a child that then spawns another child.

1. Copy the GitHub issue into a scratch `IN.md` (no real names, no chat bodies). Do not commit `IN.md` unless it is a pipeline stage input with placeholders only.
2. Invoke **test-author** with `pipeline/prompts/test-author.md`.
3. Invoke **impl** with `pipeline/prompts/impl.md`.
4. Run the matching `python3 pipeline/tools/gate_*.py`. Red → impl may retry up to 3 times, then you stop.
5. Invoke **reviewer** with `pipeline/prompts/reviewer.md`. Reviewer notes are for you, not a gate.
6. Merge when `check` + `tauri` are green and the review has no open bugs. `Fixes #N`.

Agents do not spawn agents. Do not give a subagent a spawn-agent tool.
