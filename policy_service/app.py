"""
RL policy-service: POST /policy/act returns the next-best-action for a customer state.

- Serves only the bundle referenced by an approved rl/latest.json (POLICY_MODEL_MANIFEST).
- The business mask is recomputed here on every call, outside the model, and intersected
  with the caller's allowed_actions; a model answer outside the mask is never returned.
- No approved model, schema mismatch, pinned version unavailable or model error → rule
  baseline with fallback=true and an explicit fallback_reason.
"""

import logging
import os
import threading
import time
from collections import Counter
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import PlainTextResponse

from mlops.common.manifest import load_latest
from mlops.common.schemas import (
    ACTION_SCHEMA_VERSION,
    STATE_SCHEMA_VERSION,
    PolicyActRequest,
    PolicyActResponse,
)
from mlops.common.storage import artifact_root
from mlops.rl.actions import ACTIONS_V1, business_mask, reason_codes, restrict, rules_action
from mlops.rl.features import RAW_FEATURES_V1, vectorize
from mlops.rl.policies import load_bundle

log = logging.getLogger("policy_service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

RULES_VERSION = "rules-baseline"


class PolicyState:
    def __init__(self):
        self.lock = threading.Lock()
        self.policy = None
        self.version = RULES_VERSION
        self.algorithm = "rules"
        self.load_error: Optional[str] = "not loaded"
        self.rules = {}

    def load(self) -> None:
        manifest_path = os.getenv("POLICY_MODEL_MANIFEST") or None
        latest = load_latest(manifest_path, "rl")
        with self.lock:
            self.policy, self.version, self.algorithm = None, RULES_VERSION, "rules"
            if not latest:
                self.load_error = "no_approved_model"
                log.warning("no approved rl manifest at %s: serving rule baseline", manifest_path)
                return
            root = Path(manifest_path).parent.parent if manifest_path else artifact_root()
            try:
                policy, spec = load_bundle(root / latest["model_uri"])
            except Exception as e:  # schema mismatch, missing file, missing sb3-contrib...
                self.load_error = f"model_load_failed: {e}"
                log.exception("cannot load %s", latest["version"])
                return
            self.policy, self.version, self.algorithm = policy, latest["version"], spec["algorithm"]
            self.load_error = None
            log.info("serving %s (%s)", self.version, self.algorithm)


STATE = PolicyState()
METRICS = Counter()
ACTION_COUNTS = Counter()
LATENCY_MS = []



@asynccontextmanager
async def lifespan(_app):
    STATE.load()
    yield


app = FastAPI(title="Next-BH policy-service", version="1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "model_version": STATE.version, "algorithm": STATE.algorithm,
            "fallback_only": STATE.policy is None, "load_error": STATE.load_error}


@app.post("/policy/reload")
def reload_policy():
    STATE.load()
    return health()


@app.post("/policy/act", response_model=PolicyActResponse)
def act(req: PolicyActRequest, x_trace_id: Optional[str] = Header(default=None)):
    start = time.perf_counter()
    trace_id = req.trace_id or x_trace_id
    if req.state_version != STATE_SCHEMA_VERSION:
        METRICS["requests_rejected"] += 1
        raise HTTPException(422, f"state_version {req.state_version} unsupported "
                                 f"(expected {STATE_SCHEMA_VERSION})")
    if req.allowed_actions and set(req.allowed_actions) - set(ACTIONS_V1):
        raise HTTPException(422, f"unknown actions {set(req.allowed_actions) - set(ACTIONS_V1)}")

    features = {k: req.features.get(k) for k in RAW_FEATURES_V1}
    mask = restrict(business_mask(features, STATE.rules), req.allowed_actions)

    with STATE.lock:
        policy, version = STATE.policy, STATE.version
        fallback_reason = STATE.load_error
    if req.requested_policy_version and req.requested_policy_version != version:
        policy, fallback_reason = None, f"requested_version_unavailable:{req.requested_policy_version}"

    action_idx = None
    if policy is not None:
        try:
            action_idx = policy.act(features, vectorize(features), mask)
            if not mask[action_idx]:
                METRICS["invalid_action_count"] += 1
                action_idx, fallback_reason = None, "model_returned_masked_action"
        except Exception as e:
            log.exception("policy error")
            action_idx, fallback_reason = None, f"model_error:{type(e).__name__}"

    fallback = action_idx is None
    if fallback:
        action_idx, codes = rules_action(features, mask)
        version = RULES_VERSION
        METRICS["fallbacks"] += 1
    else:
        codes = [f"model:{STATE.algorithm}"]
    action = ACTIONS_V1[action_idx]
    codes += reason_codes(features, action, STATE.rules)

    elapsed = (time.perf_counter() - start) * 1000
    METRICS["requests"] += 1
    ACTION_COUNTS[action] += 1
    LATENCY_MS.append(elapsed)
    del LATENCY_MS[:-1000]
    log.info("decision=%s trace=%s action=%s version=%s fallback=%s", req.decision_id,
             trace_id, action, version, fallback_reason if fallback else False)
    return PolicyActResponse(
        decision_id=req.decision_id, action=action, model_version=version, fallback=fallback,
        fallback_reason=fallback_reason if fallback else None, reason_codes=codes,
        allowed_actions=[a for a, ok in zip(ACTIONS_V1, mask) if ok],
        action_schema=ACTION_SCHEMA_VERSION, inference_ms=round(elapsed, 3), trace_id=trace_id,
    )


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    """Prometheus text format: requests, fallbacks, invalid actions, action mix, latency."""
    lines = [
        "# TYPE policy_requests_total counter", f"policy_requests_total {METRICS['requests']}",
        "# TYPE policy_fallbacks_total counter", f"policy_fallbacks_total {METRICS['fallbacks']}",
        "# TYPE policy_invalid_action_total counter",
        f"policy_invalid_action_total {METRICS['invalid_action_count']}",
        "# TYPE policy_actions_total counter",
        *[f'policy_actions_total{{action="{a}"}} {ACTION_COUNTS[a]}' for a in ACTIONS_V1],
        "# TYPE policy_model_info gauge",
        f'policy_model_info{{version="{STATE.version}",algorithm="{STATE.algorithm}"}} 1',
    ]
    if LATENCY_MS:
        ordered = sorted(LATENCY_MS)
        for q in (0.5, 0.95):
            lines.append(f'policy_latency_ms{{quantile="{q}"}} {ordered[int(q * (len(ordered) - 1))]:.3f}')
    return "\n".join(lines) + "\n"
