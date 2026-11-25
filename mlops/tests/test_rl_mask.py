import json
from datetime import date

import numpy as np
import pytest

from mlops.common.settings import load_config
from mlops.rl import actions, evaluate, export_events, features, policies, train
from mlops.rl.actions import ACTION_INDEX, ACTIONS_V1
from mlops.rl.env import make_env

CFG = load_config("rl")


def _f(**kw):
    base = {"age": 40.0, "good_buyer_score": 70.0, "recommended_score": 60.0, "nb_products": 1.0,
            "has_active_contract": 1.0, "days_to_expiry": 200.0, "unpaid_invoice": 0.0,
            "nb_claims": 0.0, "contacts_30d": 0.0, "days_since_last_contact": 365.0,
            "is_company": 0.0, "contract_age": 2.0}
    base.update(kw)
    return base


def _allowed(mask):
    return {ACTIONS_V1[i] for i in np.flatnonzero(mask)}


def test_business_mask_rules():
    assert _allowed(actions.business_mask(_f())) == {"wait", "recommend_product", "recommend_guarantee"}
    assert "contract_renewal" in _allowed(actions.business_mask(_f(days_to_expiry=30)))
    unpaid = _allowed(actions.business_mask(_f(unpaid_invoice=1.0)))
    assert "payment_reminder" in unpaid and "recommend_product" not in unpaid
    assert _allowed(actions.business_mask(_f(contacts_30d=3))) == {"wait"}
    no_contract = _f(has_active_contract=0.0, days_to_expiry=None, good_buyer_score=None,
                     recommended_score=None)
    assert _allowed(actions.business_mask(no_contract)) == {"wait"}


def test_restrict_keeps_wait():
    mask = actions.restrict(actions.business_mask(_f()), ["recommend_product"])
    assert _allowed(mask) == {"wait", "recommend_product"}


def test_rules_baseline_matches_legacy_threshold():
    low = _f(good_buyer_score=40.0)
    assert ACTIONS_V1[actions.rules_action(low, actions.business_mask(low))[0]] == "recommend_guarantee"
    high = _f(good_buyer_score=80.0)
    assert ACTIONS_V1[actions.rules_action(high, actions.business_mask(high))[0]] == "recommend_product"
    unpaid = _f(unpaid_invoice=1.0)
    assert ACTIONS_V1[actions.rules_action(unpaid, actions.business_mask(unpaid))[0]] == "payment_reminder"
    assert actions.legacy_action("product_recommendation", "recommend_garantie") == "recommend_guarantee"
    assert actions.legacy_action("contract_renewal", "renouvellement_contrat") == "contract_renewal"


def test_profile_to_features_from_api_payload():
    profile = {"age": 0, "age_contract": 1.0, "statut_paiement": "Non payé",
               "date_expiration": "2026-11-29", "num_contrat": 2024301072579.0,
               "good_buyer_pct": 0.72, "nb_sinistres_2025": 54.0, "client_type": "company"}
    f = features.profile_to_features(profile, {"contacts_30d": 1}, today=date(2026, 10, 30))
    assert f["age"] is None and f["good_buyer_score"] == pytest.approx(72.0)
    assert f["unpaid_invoice"] == 1.0 and f["days_to_expiry"] == 30.0 and f["is_company"] == 1.0
    vec = features.vectorize(f)
    assert vec.shape == (features.OBS_DIM,) and vec.dtype == np.float32
    assert np.all(vec >= -1) and np.all(vec <= 1)
    assert features.vectorize(features.profile_to_features({})).shape == (features.OBS_DIM,)


def test_masked_policies_never_take_forbidden_actions():
    for policy in (policies.RandomPolicy(seed=1), policies.RulesPolicy(), policies.LinUCBPolicy()):
        result = evaluate.run_episodes(policy, CFG, seed=0, episodes=60, multiplier=1.0)
        assert result["invalid_actions"] == 0, policy.algorithm


def test_invalid_action_is_penalised():
    env = make_env(CFG)
    env.reset(seed=3)
    env.f.update(unpaid_invoice=0.0)
    _, reward, _, _, info = env.step(ACTION_INDEX["payment_reminder"])
    assert info["invalid_action"] and reward <= -CFG["simulator"]["invalid_action_penalty"] + 1e-9


def test_env_is_seed_deterministic():
    def rollout():
        env = make_env(CFG)
        obs, _ = env.reset(seed=42)
        trace = [obs.tolist()]
        for _ in range(12):
            a = policies.RulesPolicy().act(dict(env.f), obs, env.action_masks())
            obs, r, term, trunc, _ = env.step(a)
            trace.append((obs.tolist(), r))
            if term or trunc:
                break
        return trace
    assert rollout() == rollout()


def test_gymnasium_api():
    from gymnasium.utils.env_checker import check_env

    check_env(make_env(CFG), skip_render_check=True)


def test_linucb_bundle_roundtrip_and_schema_guard(tmp_path):
    cfg = json.loads(json.dumps(CFG))
    cfg["training"]["linucb"]["train_episodes"] = 50
    policy = train.train("linucb", cfg, seed=0)
    policies.save_bundle(policy, tmp_path)
    loaded, spec = policies.load_bundle(tmp_path)
    obs = features.vectorize(_f())
    mask = actions.business_mask(_f())
    assert loaded.act({}, obs, mask) == policy.act({}, obs, mask)
    assert spec["feature_schema"] == "v1"

    spec["action_schema"] = "v2"
    (tmp_path / "policy.json").write_text(json.dumps(spec))
    with pytest.raises(policies.SchemaMismatch):
        policies.load_bundle(tmp_path)


def test_compare_gates():
    def res(returns, contacts=2.0, invalid=0):
        per_seed = [{"mean_return": r} for r in returns]
        r = {"per_seed": per_seed, "mean_return": float(np.mean(returns)),
             "contacts_per_episode": contacts, "invalid_actions": invalid}
        return {"0.8": r, "1.0": r, "1.2": r}
    th = load_config("validation")["rl"]
    ok = evaluate.compare(res([1.2] * 5), res([1.0] * 5), th)
    assert all(g["passed"] for g in ok.values())
    bad = evaluate.compare(res([1.2] * 5, invalid=1), res([1.0] * 5), th)
    assert not bad["invalid_actions"]["passed"]


def test_export_dedupes_and_keeps_outcome_separate(tmp_path):
    events = [
        {"event_id": "e1", "event_type": "decision_made", "decision_id": "d1", "action": "recommend_product",
         "timestamp": "2026-10-01T00:00:00"},
        {"event_id": "e1", "event_type": "decision_made", "decision_id": "d1", "action": "recommend_product",
         "timestamp": "2026-10-01T00:00:00"},
        {"event_id": "e2", "event_type": "admin_verdict", "decision_id": "d1", "admin_verdict": "rejected",
         "timestamp": "2026-10-02T00:00:00"},
        {"event_id": "e3", "event_type": "decision_made", "decision_id": "d2", "action": "wait",
         "timestamp": "2026-10-03T00:00:00"},
        {"event_id": "e4", "event_type": "customer_outcome", "decision_id": "d2", "customer_outcome": "purchase",
         "timestamp": "2026-10-20T00:00:00"},
        {"bad": "event"},
    ]
    report = export_events.export(events, tmp_path, watermark="2026-10-10T00:00:00")
    assert report["events"] == 3 and report["decisions"] == 2
    rows = {r["decision_id"]: r for r in map(json.loads, next(tmp_path.glob("decisions-*.jsonl")).read_text().splitlines())}
    assert rows["d1"]["admin_verdict"] == "rejected" and rows["d1"]["customer_outcome"] is None
    assert rows["d1"]["reward_status"] == "provisional"
    assert rows["d2"]["reward_status"] == "none"  # outcome is after the watermark
    again = export_events.export(events, tmp_path, watermark="2026-10-10T00:00:00")
    assert again["data_hash"] == report["data_hash"]
