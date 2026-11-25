"""Check the company recommendation route with a disposable dataset."""

import sys
from contextlib import chdir
from runpy import run_path
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient


API_DIRECTORY = Path(__file__).resolve().parents[1] / "api_datasets"
EXPECTED_CUSTOMER = "REF_pm_SMOKE_HIGH"
EXPECTED_PRODUCT = "Synthetic Fleet Cover"


def check_recommendation_api():
    with TemporaryDirectory(prefix="next-bh-recommendation-") as directory:
        with chdir(directory), patch.object(sys, "path", [str(API_DIRECTORY), *sys.path]):
            api = run_path(str(API_DIRECTORY / "app.py"))
            Path(api["PM_FILE"]).write_text(
                "REF_pm,Candidate_Produit,goodBuyer_score_pourcent\n"
                "REF_pm_SMOKE_LOW,Synthetic Office Cover,25\n"
                f"{EXPECTED_CUSTOMER},{EXPECTED_PRODUCT},90\n",
                encoding="utf-8",
            )

            with TestClient(api["app"]) as client:
                health = client.get("/")
                health.raise_for_status()
                if health.json() != {"status": "ok"}:
                    raise RuntimeError("The API health check did not return status ok")

                response = client.get("/recommend_pm/")
                response.raise_for_status()
                payload = response.json()

    actual = (
        payload["user_id"],
        payload["endpoint_key"],
        payload["endpoint_strategy"],
        payload["recommended_action"],
        payload["profile"]["candidate_produit"],
    )
    expected = (
        EXPECTED_CUSTOMER,
        "pm_recommendation",
        "product_recommendation",
        "recommend_produit",
        EXPECTED_PRODUCT,
    )
    if actual != expected:
        raise RuntimeError(f"Unexpected recommendation contract: {actual!r}")
    return payload


if __name__ == "__main__":
    result = check_recommendation_api()
    print('GET / -> 200 {"status":"ok"}')
    print(f"GET /recommend_pm/ -> {result['user_id']}, {EXPECTED_PRODUCT}")
