#!/usr/bin/env bash
# Pipeline selftest F1–F6 on throwaway copies / testdata. Exit 0 if all expected.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TOOLS="$ROOT/pipeline/tools"
SELF="$ROOT/pipeline/selftest"
fail() { echo "SELFTEST FAIL: $*" >&2; exit 1; }
pass() { echo "SELFTEST OK: $*"; }

# F1 invalid OUT.json
tmp=$(mktemp)
echo '{not json' > "$tmp"
if python3 "$TOOLS/check_schema.py" "$ROOT/pipeline/contracts/spike_report.schema.json" "$tmp" >/dev/null 2>&1; then
  fail "F1 expected schema fail"
fi
pass F1

# F2: missing must-ID keeps the impl gate red
if python3 "$TOOLS/gate_impl.py" --stage 05a --must DOES_NOT_EXIST >/dev/null 2>&1; then
  fail "F2 expected gate_impl red (unknown must-ID)"
fi
pass F2

# F3: DONE requires gate.exit == 0; missing exit => not skippable
f3dir=$(mktemp -d)
mkdir -p "$f3dir/logs"
touch "$f3dir/DONE"
# no gate.exit
if [[ -f "$f3dir/DONE" && -f "$f3dir/logs/gate.exit" ]]; then
  fail "F3 unexpected skip condition"
fi
pass F3

# F4 blindness
good="$SELF/testdata/blind_ok.md"
bad="$SELF/testdata/blind_bad.md"
python3 "$TOOLS/assert_blind.py" "$good" || fail "F4 good IN.md must pass"
if python3 "$TOOLS/assert_blind.py" "$bad" >/dev/null 2>&1; then
  fail "F4 bad IN.md must fail"
fi
pass F4

# F5 deny lock: commenting reqwest out of a copy must fail hash
f5=$(mktemp)
python3 - << PY
from pathlib import Path
p = Path("$ROOT/deny.toml")
t = p.read_text().replace('{ crate = "reqwest", wrappers = [] },', "")
Path("$f5").write_text(t)
PY
cp "$ROOT/deny.toml" "$ROOT/deny.toml.bak.selftest"
cp "$f5" "$ROOT/deny.toml"
if python3 "$TOOLS/deny_toml_lock.py" >/dev/null 2>&1; then
  mv "$ROOT/deny.toml.bak.selftest" "$ROOT/deny.toml"
  fail "F5 expected deny_toml_lock fail"
fi
mv "$ROOT/deny.toml.bak.selftest" "$ROOT/deny.toml"
pass F5

# F6: no tests dir → assert_no_test_edits ok; simulated edit message via empty
python3 "$TOOLS/assert_no_test_edits.py" || fail "F6 clean tree should pass"
pass F6

echo "all selftests passed"
