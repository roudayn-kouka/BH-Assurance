# Synthetic draft review checks

Use Git, Python 3.12, and Docker. Run the commands from the root of a fresh checkout containing these checks. Docker starts a disposable MongoDB container accessible only on localhost. The walkthrough uses the [recommendation demo](RECOMMENDATION_DEMO.md) to generate a synthetic draft and exercises both outcomes against that database.

```sh
python3.12 -m venv ../.next-bh-review-venv
review_python=../.next-bh-review-venv/bin/python
"$review_python" -m pip install -r scripts/smoke-requirements.txt -r scripts/agent-smoke-requirements.txt -r scripts/draft-review-requirements.txt
"$review_python" -m pip check
env -i PATH="$PATH" "$review_python" -B scripts/demo_recommendation.py

(
  set -eu
  review_mongo=$(docker run --rm -d -p 127.0.0.1::27017 mongo:7.0@sha256:884c055bff8b7144ca44830d01826facd3083b33c4dea44b94a1476c62de3c32)
  trap 'docker stop "$review_mongo" >/dev/null' EXIT
  for attempt in $(seq 1 30); do
    if docker exec "$review_mongo" mongosh --quiet --eval 'db.adminCommand({ping: 1}).ok' >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  review_port=$(docker port "$review_mongo" 27017/tcp | cut -d: -f2)
  env -i PATH="$PATH" "$review_python" -B scripts/check_draft_decisions.py --port "$review_port"
  env -i PATH="$PATH" "$review_python" -B scripts/demo_draft_review.py --port "$review_port"
)
```

The recommendation demo should select `Synthetic Fleet Cover` and show `pending`. The review demo then prints `validated` for `synthetic-approver` and `rejected` for `synthetic-rejecter`, each with the recorded UTC timestamp. For each draft it tries a second decision, rereads the record to confirm the original fields, and reports `Outbound requests: 0`. The decision checks also verify that two competing reviewers have exactly one winner.

The review demo allows connections only to the disposable database. It uses synthetic fixtures and the agent demo's model and storage substitutes. GitHub Actions runs the same checks with a temporary MongoDB service.

The [historical dashboard pilot](../web/review-pilot/README.md) documents the browser walkthrough. The dashboard CI job signs in, opens both synthetic drafts, checks the recorded decisions after reload, and verifies that the API returns a conflict on a second decision. It also checks that the email endpoint is unavailable and records any browser request outside the pilot origin. [BH-10 integration](https://maiteai.atlassian.net/browse/BH-10)
