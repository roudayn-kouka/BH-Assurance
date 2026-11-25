import json

import pytest

from mlops.common import manifest as mf
from mlops.common.schemas import DecisionEvent, PolicyActRequest, RagManifest, RlManifest


def _rl(version, approved=True):
    return RlManifest(version=version, model_uri=f"models/{version}", algorithm="linucb",
                      approved=approved)


def test_latest_only_points_to_approved(tmp_path):
    mf.write_manifest(_rl("cand", approved=False), tmp_path)
    with pytest.raises(mf.ManifestError):
        mf.promote("rl", "cand", "ci", tmp_path)
    assert not mf.latest_path("rl", tmp_path).exists()


def test_manifest_is_immutable(tmp_path):
    mf.write_manifest(_rl("v1"), tmp_path)
    mf.write_manifest(_rl("v1"), tmp_path)  # identical rewrite is a no-op
    changed = _rl("v1").model_copy(update={"model_uri": "elsewhere"})
    with pytest.raises(mf.ManifestError):
        mf.write_manifest(changed, tmp_path)


def test_promote_then_rollback(tmp_path):
    for v in ("v1", "v2"):
        mf.write_manifest(_rl(v), tmp_path)
    mf.promote("rl", "v1", "alice", tmp_path)
    mf.promote("rl", "v2", "alice", tmp_path)
    assert mf.load_latest(mf.latest_path("rl", tmp_path), "rl")["version"] == "v2"

    mf.rollback("rl", "bob", root=tmp_path)
    latest = mf.load_latest(mf.latest_path("rl", tmp_path), "rl")
    assert latest["version"] == "v1"
    history = (tmp_path / "rl" / "history.jsonl").read_text().splitlines()
    assert [json.loads(h)["action"] for h in history] == ["promote", "promote", "rollback"]


def test_load_latest_rejects_bad_pointer(tmp_path):
    path = tmp_path / "latest.json"
    assert mf.load_latest(path, "rl") is None
    path.write_text("{not json")
    assert mf.load_latest(path, "rl") is None
    path.write_text(json.dumps(_rl("v1", approved=False).model_dump()))
    assert mf.load_latest(path, "rl") is None
    rag = RagManifest(version="r1", artifact_uri="x", collection_name="c", embedding_model="m",
                      source_hash="h", chunk_count=1, approved=True)
    path.write_text(json.dumps(rag.model_dump()))
    assert mf.load_latest(path, "rl") is None  # wrong kind
    assert mf.load_latest(path, "rag")["collection_name"] == "c"


def test_contract_defaults():
    req = PolicyActRequest(client_id="c1")
    assert req.state_version == "v1" and req.decision_id
    ev = DecisionEvent(event_type="admin_verdict", decision_id="d1", admin_verdict="edited")
    assert ev.customer_outcome is None and ev.schema_version == "v1"


def test_local_tracking_without_mlflow(tmp_path, monkeypatch):
    from mlops.common import mlflow_tracking

    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    monkeypatch.setenv("ARTIFACT_ROOT", str(tmp_path))
    with mlflow_tracking.start_run("rl", "test", {"seed": "0"}) as run:
        run.log_params({"alpha": 0.5})
        run.log_metrics({"mean_return": 1.25})
    record = json.loads((tmp_path / "runs" / run.run_id / "run.json").read_text())
    assert record["status"] == "FINISHED" and record["metrics"]["mean_return"] == 1.25
