"""
Pipeline A — Data & RAG: prepare → ingest → index → evaluate → publish.

    python -m mlops.data_rag.run [--promote --by <name>]
"""

import argparse
import json
import logging
import os
import sys

import yaml

from mlops.common.manifest import latest_path, load_latest, promote
from mlops.common.mlflow_tracking import start_run
from mlops.common.settings import load_config
from mlops.common.storage import REPO_ROOT, artifact_root, atomic_write_json

from . import evaluate, index_chroma, ingest_documents, prepare, publish

log = logging.getLogger("data_rag")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--promote", action="store_true", help="point rag/latest.json at it if approved")
    parser.add_argument("--by", default="pipeline")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    cfg = load_config("rag")
    # same variable as agent/rag_model/rag.py: the index must be built with the query model
    cfg["embedding_model"] = os.getenv("NEXTBH_EMBEDDING_MODEL", cfg["embedding_model"])
    cfg["chroma"]["host"] = os.getenv("CHROMA_HOST", cfg["chroma"]["host"])
    cfg["chroma"]["port"] = int(os.getenv("CHROMA_PORT", cfg["chroma"]["port"]))
    thresholds = load_config("validation")["rag"]

    inventory = prepare.build_inventory(cfg["source_dirs"], cfg["extensions"], cfg["category_map"])
    if not inventory["documents"]:
        log.error("No documents found under %s", cfg["source_dirs"])
        return 1
    version = index_chroma.index_version(
        inventory["corpus_hash"], cfg["embedding_model"], cfg["chunk_size"], cfg["chunk_overlap"]
    )
    work_dir = artifact_root() / "rag" / "work" / version
    atomic_write_json(work_dir / "inventory.json", inventory)

    with start_run("next-bh-rag", version, {"pipeline": "data_rag"}) as run:
        run.log_params({
            "embedding_model": cfg["embedding_model"], "chunk_size": cfg["chunk_size"],
            "chunk_overlap": cfg["chunk_overlap"], "documents": len(inventory["documents"]),
            "corpus_hash": inventory["corpus_hash"],
        })
        chunks = ingest_documents.ingest(inventory, cfg["chunk_size"], cfg["chunk_overlap"])
        log.info("%d documents -> %d chunks", len(inventory["documents"]), len(chunks))

        embed = index_chroma.sentence_transformer_embedder(
            cfg["embedding_model"], cfg.get("embedding_batch_size", 32)
        )
        client = index_chroma.chroma_client(cfg["chroma"]["host"], cfg["chroma"]["port"])
        active = load_latest(latest_path("rag"), "rag")
        protected = {"legal_docs"} | ({active["collection_name"]} if active else set())
        name = index_chroma.collection_name(cfg["chroma"]["collection_prefix"], version)
        collection = index_chroma.build_index(
            client, chunks, name, embed, protected,
            metadata={"index_version": version, "embedding_model": cfg["embedding_model"]},
        )

        questions = yaml.safe_load(
            (REPO_ROOT / cfg["evaluation"]["reference_questions"]).read_text(encoding="utf-8")
        )
        report = evaluate.evaluate_retrieval(
            evaluate.chroma_retriever(collection, embed), questions, cfg["evaluation"]["top_k"]
        )
        gates = evaluate.apply_gates(report, len(chunks), thresholds)
        run.log_metrics({k: report[k] for k in ("recall_at_k", "mrr", "source_presence")})
        run.log_dict(report, "retrieval_report.json")

        manifest = publish.publish_candidate(
            version, name, cfg["embedding_model"], inventory["corpus_hash"], len(chunks),
            f"chroma://{cfg['chroma']['host']}:{cfg['chroma']['port']}/{name}",
            report, gates, run.run_id,
        )

    summary = {"version": version, "approved": manifest.approved, "chunks": len(chunks),
               **{k: report[k] for k in ("recall_at_k", "mrr", "source_presence")}}
    atomic_write_json(artifact_root() / "rag" / "reports" / "last_run.json", summary)
    print(json.dumps(summary, indent=2))

    if args.promote and manifest.approved:
        promote("rag", version, args.by)
        log.info("rag/latest.json -> %s", version)
    return 0 if manifest.approved else 2


if __name__ == "__main__":
    sys.exit(main())
