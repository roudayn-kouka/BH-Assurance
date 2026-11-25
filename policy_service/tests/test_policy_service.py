import json

import pytest
from fastapi.testclient import TestClient

from mlops.common import manifest as mf
from mlops.common.schemas import RlManifest
from mlops.common.settings import load_config
from mlops.rl import policies, train
from policy_service import app as service

FEATURES = {"good_buyer_score": 80, "recommended_score": 60, "has_active_contract": 1,
            "days_to_expiry": 200, "unpaid_invoice": 0, "contacts_30d": 0}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("POLICY_MODEL_MANIFEST", str(tmp_path / "rl" / "latest.json"))
    with TestClient(service.app) as c:
        yield c, tmp_path


def _publish_linucb(root, version="rl-test", approved=True):
    cfg = load_config("rl")
    cfg["training"]["linucb"]["train_episodes"] = 50
    policies.save_bundle(train.train("linucb", cfg, 0), root / "rl" / "models" / version)
    mf.write_manifest(RlManifest(version=version, model_uri=f"rl/models/{version}",
                                 algorithm="linucb", approved=approved), root)
    if approved:
        mf.promote("rl", version, "test", root)


def test_fallback_to_rules_without_approved_model(client):
    c, _ = client
    r = c.post("/policy/act", json={"client_id": "c1", "features": FEATURES},
               headers={"X-Trace-Id": "t-1"})
    body = r.json()
    assert r.status_code == 200
    assert body["fallback"] is True and body["fallback_reason"] == "no_approved_model"
    assert body["action"] == "recommend_product" and body["model_version"] == "rules-baseline"
    assert body["trace_id"] == "t-1" and "high_propensity" in body["reason_codes"]


def test_serves_approved_model_and_respects_mask(client):
    c, root = client
    _publish_linucb(root)
    assert c.post("/policy/reload").json()["model_version"] == "rl-test"

    body = c.post("/policy/act", json={"client_id": "c1", "features": FEATURES,
                                       "allowed_actions": ["contract_renewal"]}).json()
    # renewal isn't allowed by the business mask (expiry in 200 days): only wait remains
    assert body["allowed_actions"] == ["wait"] and body["action"] == "wait"
    assert body["fallback"] is False and body["model_version"] == "rl-test"

    fatigued = c.post("/policy/act", json={"client_id": "c1",
                                           "features": {**FEATURES, "contacts_30d": 5}}).json()
    assert fatigued["action"] == "wait"


def test_pinned_version_and_schema_errors(client):
    c, root = client
    _publish_linucb(root)
    c.post("/policy/reload")
    body = c.post("/policy/act", json={"client_id": "c1", "features": FEATURES,
                                       "requested_policy_version": "rl-old"}).json()
    assert body["fallback"] and body["fallback_reason"].startswith("requested_version_unavailable")
    assert c.post("/policy/act", json={"client_id": "c1", "state_version": "v2"}).status_code == 422
    assert c.post("/policy/act", json={"client_id": "c1", "allowed_actions": ["spam"]}).status_code == 422


def test_bad_bundle_schema_falls_back(client):
    c, root = client
    _publish_linucb(root)
    spec_path = root / "rl" / "models" / "rl-test" / "policy.json"
    spec = json.loads(spec_path.read_text())
    spec["feature_schema"] = "v9"
    spec_path.write_text(json.dumps(spec))
    health = c.post("/policy/reload").json()
    assert health["fallback_only"] and "model_load_failed" in health["load_error"]
    assert c.post("/policy/act", json={"client_id": "c1", "features": FEATURES}).json()["fallback"]


def test_metrics_exposed(client):
    c, _ = client
    c.post("/policy/act", json={"client_id": "c1", "features": FEATURES})
    text = c.get("/metrics").text
    assert "policy_requests_total" in text and 'policy_actions_total{action="recommend_product"}' in text
