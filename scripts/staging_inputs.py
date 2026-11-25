"""Local opportunity and product-evidence inputs for the isolated sales pilot."""

import csv
import hashlib
import math
import re
import sys
import unicodedata
from contextlib import chdir, contextmanager
from pathlib import Path
from runpy import run_path
from tempfile import TemporaryDirectory
from typing import Annotated
from urllib.parse import urlsplit
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

ROOT = Path(__file__).resolve().parents[1]
Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$")]
CaseId = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9-]{0,23}$")]


class Opportunity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: CaseId
    sector: Label
    activity: Label
    candidate: Label
    needs: list[Identifier] = Field(max_length=12)


class CatalogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Identifier
    product: Label
    document: Label
    locator: Label
    supports: list[Identifier] = Field(min_length=1, max_length=12)
    excerpt: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1800)]


class Catalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: Identifier
    entries: list[CatalogEntry] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def unique_source_ids(self):
        if len({entry.id for entry in self.entries}) != len(self.entries):
            raise ValueError("Catalog source IDs must be unique")
        return self


def load_catalog(path, approved_sha256):
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != approved_sha256:
        raise ValueError(f"The catalog SHA-256 does not match the approved digest ({digest})")
    return Catalog.model_validate_json(raw)


@contextmanager
def opportunity_api():
    """Use the real GET route in process, with all CSV and result I/O disposable."""
    with TemporaryDirectory(prefix="next-bh-stage-api-") as directory, chdir(directory):
        with patch.object(sys, "path", [str(ROOT / "api_datasets"), *sys.path]):
            api = run_path(str(ROOT / "api_datasets" / "app.py"))
        with TestClient(api["app"]) as client:
            yield client, Path(api["PM_FILE"])


def fetch_opportunity(api, opportunity):
    client, dataset = api
    candidate = {
        "REF_pm": f"REF_pm_STAGE_{opportunity.case_id}",
        "Candidate_Produit": opportunity.candidate,
        "goodBuyer_score_pourcent": 90,
        "Lib_Secteur_Activite": opportunity.sector,
        "Lib_Activite": opportunity.activity,
    }
    with dataset.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=candidate)
        writer.writeheader()
        writer.writerow({**candidate, "REF_pm": "REF_pm_STAGE_CONTROL", "goodBuyer_score_pourcent": 25})
        writer.writerow(candidate)
    response = client.get("/recommend_pm/")
    response.raise_for_status()
    payload = response.json()
    if (
        payload["user_id"] != candidate["REF_pm"]
        or payload["user_type"] != "personne_morale"
        or payload["endpoint_strategy"] != "product_recommendation"
        or payload["recommended_action"] != "recommend_produit"
        or payload["profile"]["candidate_produit"] != opportunity.candidate
    ):
        raise RuntimeError("Unexpected company recommendation API response")

    # Retain the opportunity fields. Use non-routable contact data in the pilot.
    profile = payload["profile"]
    payload["profile"] = {
        "candidate_produit": profile["candidate_produit"],
        "lib_secteur_activite": profile["lib_secteur_activite"],
        "lib_activite": profile["lib_activite"],
        "raison_sociale": f"Entreprise synthétique {opportunity.case_id}",
        "email": f"{opportunity.case_id.lower()}@example.invalid",
    }
    return payload


class CatalogIndex:
    """Index a single catalog in process and return evidence for the API candidate."""

    def __init__(self, catalog):
        import chromadb
        from chromadb.config import Settings

        self.revision = catalog.revision
        client = chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False))
        catalog_key = hashlib.sha256(catalog.model_dump_json().encode()).hexdigest()[:24]
        self.collection = client.get_or_create_collection(
            f"pilot-{catalog_key}", embedding_function=None
        )
        texts = [
            f"{entry.product}\n{entry.excerpt}\n{' '.join(entry.supports)}"
            for entry in catalog.entries
        ]
        self.collection.upsert(
            ids=[entry.id for entry in catalog.entries],
            documents=[entry.excerpt for entry in catalog.entries],
            metadatas=[
                {
                    "product": entry.product,
                    "document": entry.document,
                    "locator": entry.locator,
                    "supports": " ".join(entry.supports),
                }
                for entry in catalog.entries
            ],
            embeddings=[catalog_vector(text) for text in texts],
        )

    def search(self, product, activity, needs):
        results = self.collection.query(
            query_embeddings=[catalog_vector(f"{product}\n{activity}\n{' '.join(needs)}")],
            where={"product": product},
            n_results=8,
            include=["documents", "metadatas"],
        )
        return [
            {
                "id": source_id,
                "product": meta["product"],
                "document": meta["document"],
                "locator": meta["locator"],
                "supports": meta["supports"].split(),
                "excerpt": excerpt,
                "revision": self.revision,
            }
            for source_id, excerpt, meta in zip(
                results["ids"][0], results["documents"][0], results["metadatas"][0], strict=True
            )
        ]


def catalog_vector(text):
    """Embed the small product catalog with normalized lexical features."""
    normalized = unicodedata.normalize("NFKD", text.casefold())
    folded = "".join(character for character in normalized if not unicodedata.combining(character))
    vector = [0.0] * 512
    for term in set(re.findall(r"[^\W_]+", folded)):
        digest = hashlib.blake2b(term.encode(), digest_size=4).digest()
        position = int.from_bytes(digest, "big") % len(vector)
        vector[position] += 1.0
    length = math.sqrt(sum(weight * weight for weight in vector))
    return [weight / length for weight in vector] if length else vector


def local_gemma(base_url, expected_digest):
    from config import LLM_MODEL
    from langchain_ollama import OllamaLLM

    location = urlsplit(base_url)
    if (
        location.scheme != "http" or location.hostname != "127.0.0.1"
        or not location.port or location.username is not None
        or location.path or location.query or location.fragment
    ):
        raise ValueError("Ollama must use a dedicated http://127.0.0.1:PORT origin")
    with httpx.Client(base_url=base_url, timeout=5, trust_env=False) as client:
        tags = client.get("/api/tags")
        tags.raise_for_status()
        model = next((entry for entry in tags.json()["models"] if entry["name"] == LLM_MODEL), None)
        if model is None or model["digest"] != expected_digest:
            raise RuntimeError(f"Provision the configured {LLM_MODEL} model with the pinned digest")
        version = client.get("/api/version")
        version.raise_for_status()
    llm = OllamaLLM(
        model=LLM_MODEL, base_url=base_url, temperature=0, seed=42, format="json",
        num_ctx=4096, num_predict=180, client_kwargs={"trust_env": False, "timeout": 120},
    )
    return llm, {"name": LLM_MODEL, "digest": model["digest"], "ollama": version.json()["version"]}
