#!/usr/bin/env bash
# Non-LLM sequencer. Does not spawn agents. Humans/Grok invoke agents separately.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
STAGES=(01-spikes)
# later: 00-bootstrap 02-schema 02b-api …

status() { printf '%s\n' "$*"; }

for stage in "${STAGES[@]}"; do
  dir="$ROOT/pipeline/stages/$stage"
  mkdir -p "$dir/logs"
  if [[ -f "$dir/DONE" && -f "$dir/logs/gate.exit" && "$(cat "$dir/logs/gate.exit")" == "0" ]]; then
    status "skip $stage (DONE)"
    continue
  fi
  if [[ -f "$dir/OUT.json" && ! -f "$dir/logs/gate.exit" ]]; then
    mv "$dir/OUT.json" "$dir/OUT.json.partial"
    status "partial OUT.json for $stage"
  fi
  case "$stage" in
    01-spikes) gate=(python3 "$ROOT/pipeline/tools/gate_spikes.py") ;;
    00-bootstrap) gate=(python3 "$ROOT/pipeline/tools/gate_bootstrap.py") ;;
    *) status "unknown stage $stage"; exit 1 ;;
  esac
  schema="$ROOT/pipeline/contracts/spike_report.schema.json"
  if [[ "$stage" == "01-spikes" && -f "$dir/OUT.json" ]]; then
    python3 "$ROOT/pipeline/tools/check_schema.py" "$schema" "$dir/OUT.json"
  fi
  if "${gate[@]}"; then
    echo 0 > "$dir/logs/gate.exit"
    touch "$dir/DONE"
    status "ok $stage"
  else
    echo 1 > "$dir/logs/gate.exit"
    status "fail $stage"
    exit 1
  fi
done
status "run.sh finished"
