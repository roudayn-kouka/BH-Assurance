"""
Post-deployment smoke test of the policy-service.

    python scripts/smoke_policy_service.py --url http://localhost:8010 [--expect-model]

Checks health, a decision with a trace id, the business mask (fatigued customer → wait)
and the metrics endpoint. Exit code 1 on any failure.
"""

import argparse
import json
import sys
import urllib.request
import uuid


def call(url, payload=None, headers=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json",
                                                          **(headers or {})})
    with urllib.request.urlopen(req, timeout=10) as r:
        body = r.read().decode()
        return json.loads(body) if r.headers.get_content_type() == "application/json" else body


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8010")
    parser.add_argument("--expect-model", action="store_true",
                        help="fail if the service only serves the rule fallback")
    args = parser.parse_args(argv)

    failures = []
    health = call(f"{args.url}/health")
    print("health:", health)
    if args.expect_model and health["fallback_only"]:
        failures.append(f"no model served: {health['load_error']}")

    trace = uuid.uuid4().hex
    features = {"good_buyer_score": 75, "has_active_contract": 1, "days_to_expiry": 20,
                "unpaid_invoice": 0, "contacts_30d": 0}
    decision = call(f"{args.url}/policy/act", {"client_id": "smoke", "features": features},
                    {"X-Trace-Id": trace})
    print("decision:", decision)
    if decision["trace_id"] != trace:
        failures.append("trace id not propagated")
    if decision["action"] not in decision["allowed_actions"]:
        failures.append("action outside the mask")

    fatigued = call(f"{args.url}/policy/act",
                    {"client_id": "smoke", "features": {**features, "contacts_30d": 5}})
    if fatigued["action"] != "wait":
        failures.append(f"fatigued customer got {fatigued['action']}")

    if "policy_requests_total" not in call(f"{args.url}/metrics"):
        failures.append("metrics missing")

    for f in failures:
        print("FAIL:", f)
    print("smoke test", "failed" if failures else "passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
