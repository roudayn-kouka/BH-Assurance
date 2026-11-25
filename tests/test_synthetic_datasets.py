"""The generated synthetic datasets must satisfy every route of api_datasets/app.py."""

import importlib.util
import sys
from contextlib import chdir
from datetime import date
from pathlib import Path
from runpy import run_path
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api_datasets"
ROUTES = {
    "recommend_pm": "recommend_produit", "recommend_pp": None,
    "facture_pm": "paiement_facture", "facture_pp": "paiement_facture",
    "renouvellement_pm": "renouvellement_contrat", "renouvellement_pp": "renouvellement_contrat",
}


def _generator():
    spec = importlib.util.spec_from_file_location(
        "generate_synthetic_datasets", ROOT / "scripts" / "generate_synthetic_datasets.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_api_route_answers_from_synthetic_csvs(tmp_path):
    _generator().generate(tmp_path, rows=10, seed=1, today=date.today())
    with chdir(tmp_path), patch.object(sys, "path", [str(API_DIR), *sys.path]):
        api = run_path(str(API_DIR / "app.py"))
        with TestClient(api["app"]) as client:
            for route, action in ROUTES.items():
                response = client.get(f"/{route}/")
                assert response.status_code == 200, (route, response.text)
                body = response.json()
                assert body["user_id"].startswith("REF_")
                if action:
                    assert body["recommended_action"] == action
            features = client.get("/features/recommend_pm/REF_pm_SYN_0003")
            assert features.status_code == 200


def test_generation_is_deterministic(tmp_path):
    gen = _generator()
    gen.generate(tmp_path / "a", rows=5, seed=3, today=date(2026, 11, 25))
    gen.generate(tmp_path / "b", rows=5, seed=3, today=date(2026, 11, 25))
    for csv in (tmp_path / "a").glob("*.csv"):
        assert csv.read_bytes() == (tmp_path / "b" / csv.name).read_bytes()


def test_rag_documents_match_reference_questions(tmp_path):
    import yaml

    _generator().generate_rag_docs(tmp_path)
    folders = {p.name for p in tmp_path.iterdir()}
    questions = yaml.safe_load(
        (ROOT / "mlops" / "data_rag" / "reference_questions.yaml").read_text(encoding="utf-8"))
    for q in questions:
        assert any(exp in f for f in folders for exp in q["expected_sources"]), q["question"]
