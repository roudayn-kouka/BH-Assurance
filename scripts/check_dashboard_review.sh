#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 && !( $# -eq 2 && $2 == --staging-ci ) ]]; then
  echo 'Usage: bash scripts/check_dashboard_review.sh PYTHON [--staging-ci]' >&2
  exit 2
fi
pilot_args=("$1")
if [[ ${2:-} == --staging-ci ]]; then
  pilot_args+=(--staging reviewer@example.invalid --ci)
fi

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
review_work=$(mktemp -d)
bash "$repo_root/scripts/run_dashboard_review_pilot.sh" "${pilot_args[@]}" > "$review_work/runner.log" 2>&1 &
review_runner=$!

cleanup() {
  kill "$review_runner" 2>/dev/null || true
  wait "$review_runner" || true
  rm -rf -- "$review_work"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

for attempt in $(seq 1 120); do
  if ! kill -0 "$review_runner" 2>/dev/null; then break; fi
  awk '/^\{"url"/ { print; exit }' "$review_work/runner.log" > "$review_work/session.json"
  if [[ -s "$review_work/session.json" ]]; then
    if [[ ${2:-} == --staging-ci ]]; then
      "$1" -B - "$review_work/runner.log" <<'PYTHON'
import json
from pathlib import Path
import sys

summary, = (
    json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()
    if line.startswith('{"mode": "ci"')
)
assert summary["case_count"] == summary["expected_outcome_matches"] == 24, summary
assert summary["outcomes"] == {
    "recommended": 8, "clarification_required": 8, "insufficient_evidence": 8,
}, summary
assert summary["outbound_customer_messages"] == 0, summary
print(json.dumps(summary))
PYTHON
    fi
    node "$repo_root/scripts/check_dashboard_review.cjs" "$review_work/session.json" "${2:-}"
    exit
  fi
  sleep 1
done

awk '!/^\{"url"/' "$review_work/runner.log" >&2
echo 'The dashboard pilot did not start.' >&2
exit 1
