"""Generate company opportunity drafts into the dashboard's disposable MongoDB."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

from bson import ObjectId
from langchain_core.runnables import RunnableLambda
from network_guard import is_socketpair_emulation
from pymongo import MongoClient, ReturnDocument

from staging_inputs import (
    CatalogIndex,
    Opportunity,
    ROOT,
    fetch_opportunity,
    load_catalog,
    local_gemma,
    opportunity_api,
)

sys.path.insert(0, str(ROOT / "agent"))
from utils.grounded_recommendation import Evidence, Outcome, grounded_recommendation

FIXTURES = ROOT / "scripts" / "fixtures"


class EvaluationCase(Opportunity):
    expected: Outcome


def ci_select_sources(prompt):
    context = prompt.to_string().split("Extraits du catalogue avec leurs identifiants et besoins couverts :\n", 1)[1]
    sources, _ = json.JSONDecoder().raw_decode(context)
    return json.dumps({"source_ids": [source["id"] for source in sources]})


def save_draft(messages, case, recommendation, model, catalog_revision):
    values = {
        "conversation_id": ObjectId(),
        "subject": f"Recommandation synthétique {case.case_id}",
        "body": recommendation.body,
        "sender": "ai",
        "direction": "sent",
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
        "staging_case_id": case.case_id,
        "recommendation_outcome": recommendation.outcome,
        "recommendation_product": recommendation.product,
        "recommendation_sources": [source.model_dump() for source in recommendation.sources],
        "catalog_revision": catalog_revision,
        "recommendation_model": model,
    }
    saved = messages.find_one_and_update(
        {"staging_case_id": case.case_id}, {"$setOnInsert": values}, upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return saved["recommendation_outcome"]


def restrict_connections(ports):
    """Allow only the local disposable services in this process."""
    blocked = []

    def check(event, args):
        if event in {"socket.connect", "socket.sendto"}:
            endpoint = args[1]
            if event == "socket.connect" and is_socketpair_emulation(endpoint):
                return
            if not isinstance(endpoint, tuple) or endpoint[:2] not in ports:
                blocked.append(event)
                raise PermissionError("Outbound recommendation connection blocked")
        if event == "socket.getaddrinfo" and args[:2] not in ports:
            blocked.append(event)
            raise PermissionError("Outbound recommendation DNS blocked")

    sys.addaudithook(check)
    return blocked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mongo-port", required=True, type=int)
    parser.add_argument("--db", required=True)
    parser.add_argument("--cases", type=Path, default=FIXTURES / "wave3-opportunities.json")
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--catalog-sha256")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--ollama-digest")
    parser.add_argument("--ci", action="store_true", help="Use deterministic model responses")
    args = parser.parse_args()
    if not 1 <= args.mongo_port <= 65535 or not re.fullmatch(r"bh_review_stage_[0-9a-f]{24}", args.db):
        parser.error("A disposable dashboard MongoDB port and database name are required")
    cases = [EvaluationCase.model_validate(row) for row in json.loads(args.cases.read_text())]
    if not cases or len({case.case_id for case in cases}) != len(cases):
        parser.error("Cases must have unique IDs")

    ports = {("127.0.0.1", args.mongo_port)}
    if args.ci:
        if args.catalog or args.catalog_sha256 or args.ollama_digest:
            parser.error("--ci uses the bundled fixture catalog and local substitutes")
        catalog_path = FIXTURES / "wave3-catalog.json"
        catalog_digest = hashlib.sha256(catalog_path.read_bytes()).hexdigest()
        model = RunnableLambda(ci_select_sources)
        model_info = {"name": "deterministic CI source selection"}
        blocked = restrict_connections(ports)
    else:
        from urllib.parse import urlsplit

        if not args.catalog or not args.catalog_sha256 or not args.ollama_digest:
            parser.error("Staging requires explicit catalog approval and a pinned Gemma digest")
        catalog_path = args.catalog
        catalog_digest = args.catalog_sha256
        ports.add(("127.0.0.1", urlsplit(args.ollama_url).port))
        blocked = restrict_connections(ports)
        model, model_info = local_gemma(args.ollama_url, args.ollama_digest)

    catalog = load_catalog(catalog_path, catalog_digest)
    index = CatalogIndex(catalog)
    outcomes = Counter()
    matches = 0
    with MongoClient(
        "127.0.0.1", args.mongo_port, directConnection=True, serverSelectionTimeoutMS=3000
    ) as connection, opportunity_api() as api:
        messages = connection[args.db].messages
        messages.create_index("staging_case_id", unique=True, sparse=True)
        for case in cases:
            payload = fetch_opportunity(api, case)
            profile = payload["profile"]
            sources = [
                Evidence.model_validate(source)
                for source in index.search(profile["candidate_produit"], profile["lib_activite"], case.needs)
            ]
            recommendation = grounded_recommendation(payload, case.needs, sources, model)
            outcome = save_draft(messages, case, recommendation, model_info, catalog.revision)
            outcomes[outcome] += 1
            matches += outcome == case.expected
            print(json.dumps({"case": case.case_id, "actual": outcome, "expected": case.expected}))
    if blocked:
        raise RuntimeError(f"{len(blocked)} unexpected network attempts were blocked")
    print(json.dumps({
        "mode": "ci" if args.ci else "staging",
        "catalog_revision": catalog.revision,
        "catalog_sha256": catalog_digest,
        "model": model_info,
        "outcomes": dict(outcomes),
        "expected_outcome_matches": matches,
        "case_count": len(cases),
        "outbound_customer_messages": 0,
    }))


if __name__ == "__main__":
    main()
