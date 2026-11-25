#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 && ${2:-} != --staging ]]; then
  echo 'Usage: bash scripts/run_dashboard_review_pilot.sh PYTHON [--staging REVIEWER_EMAIL GENERATOR_OPTIONS...]' >&2
  exit 2
fi

staging=false
if [[ ${2:-} == --staging ]]; then
  staging=true
  reviewer_email=${3:?Provide the pilot reviewer email}
fi

review_python=$(cd -- "$(dirname -- "$1")" && pwd)/$(basename -- "$1")
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
review_work=$(mktemp -d)
review_source="$review_work/dashboard"
review_mongo=''
review_server=''

cleanup() {
  if [[ -n "$review_server" ]]; then
    kill "$review_server" 2>/dev/null || true
    wait "$review_server" || true
  fi
  if [[ -n "$review_mongo" ]]; then
    docker stop "$review_mongo" >/dev/null || true
  fi
  rm -rf -- "$review_work"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# `env -i` isolates the pilot from the caller's environment. On Windows (Git Bash), Python,
# Node and npm also need the system and profile variables below to start.
clean_env=(env -i PATH="$PATH")
case "${OSTYPE:-}" in
  msys* | cygwin*)
    for var in SYSTEMROOT SYSTEMDRIVE WINDIR COMSPEC PATHEXT TEMP TMP USERPROFILE APPDATA LOCALAPPDATA PROGRAMDATA; do
      if [[ -n "${!var:-}" ]]; then clean_env+=("$var=${!var}"); fi
    done
    ;;
esac

# the reviewer's interpreter is the documented Python 3.12 environment
"$review_python" -B "$repo_root/scripts/prepare_dashboard_snapshot.py" "$review_source"
git -C "$review_source" apply "$repo_root/web/review-pilot/dashboard.patch"
if "$staging"; then
  git -C "$review_source" apply "$repo_root/web/review-pilot/staging.patch"
fi
npm --prefix "$review_source/backend" ci --ignore-scripts --no-audit --no-fund
npm --prefix "$review_source/frontend" ci --ignore-scripts --no-audit --no-fund
"$review_source/backend/node_modules/.bin/tsc" -p "$review_source/backend/tsconfig.pilot.json" --noEmitOnError
"${clean_env[@]}" VITE_DRAFT_REVIEW_PILOT=true npm --prefix "$review_source/frontend" run build

if ! "$staging"; then
"${clean_env[@]}" PYTHONPATH="$repo_root/scripts" "$review_python" -B - "$review_work/draft.json" <<'PY'
import json
import sys
from pathlib import Path

from smoke_recommendation_api import EXPECTED_PRODUCT, check_recommendation_api
from smoke_recommendation_draft import check_recommendation_draft

draft = check_recommendation_draft(check_recommendation_api(), EXPECTED_PRODUCT)
Path(sys.argv[1]).write_text(json.dumps({
    'product': EXPECTED_PRODUCT, 'status': draft['statut'],
    'subject': draft['subject'], 'body': draft['corps'],
}))
PY
fi

review_mongo=$(docker run --rm -d -p 127.0.0.1::27017 mongo:7.0@sha256:884c055bff8b7144ca44830d01826facd3083b33c4dea44b94a1476c62de3c32)
for attempt in $(seq 1 30); do
  if docker exec "$review_mongo" mongosh --quiet --eval 'db.adminCommand({ping: 1}).ok' >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
review_port=$(docker port "$review_mongo" 27017/tcp | cut -d: -f2)
launch_args=("$review_port" "$review_work/draft.json" "$review_source/frontend/dist")
if "$staging"; then
  db_name=$("$review_python" -B -c 'from secrets import token_hex; print("bh_review_stage_" + token_hex(12))')
  "${clean_env[@]}" "$review_python" -B "$repo_root/scripts/run_staging_recommendations.py" \
    --mongo-port "$review_port" --db "$db_name" "${@:4}"
  launch_args=("$review_port" --staging "$review_source/frontend/dist" "$db_name" "$reviewer_email")
fi
"${clean_env[@]}" node "$review_source/backend/dist/pilot-review.js" "${launch_args[@]}" &
review_server=$!
wait "$review_server"
