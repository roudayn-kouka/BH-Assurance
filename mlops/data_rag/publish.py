"""
P1.5 — Publish the candidate index manifest and its validation record.

The manifest is approved only when every gate passes. Pointing rag/latest.json at it is a
separate, explicit step (`python -m mlops.promote rag promote <version> --by <name>`),
so a candidate is never served implicitly.
"""

from pathlib import Path
from typing import Dict, Optional

from mlops.common.manifest import write_manifest, write_validation
from mlops.common.schemas import GateResult, RagManifest, ValidationRecord, utc_now


def publish_candidate(
    version: str, collection: str, embedding_model: str, corpus_hash: str, chunk_count: int,
    artifact_uri: str, report: Dict, gates: Dict[str, Dict], run_id: Optional[str],
    root: Optional[Path] = None,
) -> RagManifest:
    approved = all(g["passed"] for g in gates.values())
    manifest = RagManifest(
        version=version, artifact_uri=artifact_uri, collection_name=collection,
        embedding_model=embedding_model, source_hash=corpus_hash, chunk_count=chunk_count,
        evaluation_run_id=run_id,
        test_report={k: v for k, v in report.items() if k != "per_question"},
        approved=approved,
    )
    write_manifest(manifest, root)
    write_validation(
        ValidationRecord(
            kind="rag", version=version,
            gates={k: GateResult(**g) for k, g in gates.items()},
            approved=approved, approved_by="gates" if approved else None,
            approved_at=utc_now() if approved else None,
            reasons=[f"{k} failed" for k, g in gates.items() if not g["passed"]],
        ),
        root,
    )
    return manifest
