"""
Client of the RL policy-service with a controlled fallback.

off    → policy-service not called, legacy action applied
shadow → policy-service called and journaled, legacy action applied
active → policy action applied; on any failure the legacy action is applied and
         fallback_reason is recorded
"""

import os
import sys
import time
import uuid
from typing import Dict, List, Optional

import requests

import feature_flags

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from mlops.rl.actions import ACTIONS_V1, legacy_action  # noqa: E402
from mlops.rl.features import FEATURE_SCHEMA, profile_to_features  # noqa: E402

LEGACY_VERSION = "legacy-strategy"


def build_features(user_data: Dict, context: Optional[Dict] = None) -> Dict:
    data = (user_data or {}).get("data") or {}
    ctx = {"user_type": data.get("user_type"), **(context or {})}
    return profile_to_features(data.get("profile") or {}, ctx)


def legacy_decision(user_data: Dict) -> str:
    data = (user_data or {}).get("data") or {}
    return legacy_action(data.get("endpoint_strategy"), data.get("recommended_action"))


def decide(
    client_id: str,
    features: Dict,
    fallback_action: str,
    allowed_actions: Optional[List[str]] = None,
    trace_id: Optional[str] = None,
    mode: Optional[str] = None,
) -> Dict:
    mode = mode or feature_flags.POLICY_MODE
    decision = {
        "decision_id": str(uuid.uuid4()),
        "trace_id": trace_id or uuid.uuid4().hex,
        "mode": mode,
        "legacy_action": fallback_action,
        "policy_action": None,
        "action": fallback_action,
        "model_version": LEGACY_VERSION,
        "fallback": True,
        "fallback_reason": "policy_mode_off" if mode == "off" else None,
        "reason_codes": [],
        "allowed_actions": allowed_actions or ACTIONS_V1,
        "state_version": FEATURE_SCHEMA,
        "features": features,
    }
    if mode == "off":
        return decision

    start = time.perf_counter()
    try:
        r = requests.post(
            f"{feature_flags.POLICY_SERVICE_URL}/policy/act",
            json={"decision_id": decision["decision_id"], "client_id": str(client_id),
                  "state_version": FEATURE_SCHEMA, "features": features,
                  "allowed_actions": allowed_actions, "trace_id": decision["trace_id"]},
            headers={"X-Trace-Id": decision["trace_id"]},
            timeout=feature_flags.POLICY_TIMEOUT_S,
        )
        r.raise_for_status()
        body = r.json()
    except Exception as e:
        decision["fallback_reason"] = f"policy_service_unavailable:{type(e).__name__}"
        print(f"[policy] fallback to legacy action {fallback_action}: {e}")
        return decision

    decision.update(
        policy_action=body["action"],
        model_version=body["model_version"],
        reason_codes=body.get("reason_codes", []),
        allowed_actions=body.get("allowed_actions", decision["allowed_actions"]),
        latency_ms=round((time.perf_counter() - start) * 1000, 1),
    )
    if mode == "active":
        decision["action"] = body["action"]
        decision["fallback"] = bool(body.get("fallback"))
        decision["fallback_reason"] = body.get("fallback_reason")
    else:
        decision["fallback_reason"] = "shadow_mode"
    print(f"[policy] mode={mode} policy={body['action']} applied={decision['action']} "
          f"model={body['model_version']} trace={decision['trace_id']}")
    return decision


def public_decision(decision: Dict) -> Dict:
    """Decision fields persisted on the message and published in events (no raw features)."""
    return {k: v for k, v in decision.items() if k != "features"}
