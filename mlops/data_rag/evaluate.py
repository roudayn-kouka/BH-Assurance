"""
P1.4 — Retrieval evaluation on reference questions: Recall@K, MRR and source presence.

A retrieved chunk counts as relevant when one of the question's expected_sources is a
substring of its `source` metadata. Source presence checks that every retrieved chunk
carries the provenance the compliance step relies on (source + document_version).
"""

from typing import Callable, Dict, List

Retriever = Callable[[str, int], List[Dict]]
REQUIRED_METADATA = ("source", "document_version")


def chroma_retriever(collection, embed) -> Retriever:
    def retrieve(query: str, k: int) -> List[Dict]:
        res = collection.query(
            query_embeddings=embed([query]), n_results=k, include=["documents", "metadatas"]
        )
        return [
            {"document": d, "metadata": m or {}}
            for d, m in zip(res["documents"][0], res["metadatas"][0])
        ]

    return retrieve


def evaluate_retrieval(retrieve: Retriever, questions: List[Dict], k: int) -> Dict:
    hits, reciprocal_ranks, with_sources, total_chunks = 0, [], 0, 0
    per_question = []
    for q in questions:
        results = retrieve(q["question"], k)
        sources = [r.get("metadata", {}).get("source", "") for r in results]
        rank = next(
            (i for i, s in enumerate(sources, 1)
             if any(exp in s for exp in q["expected_sources"])),
            None,
        )
        hits += rank is not None
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)
        for r in results:
            total_chunks += 1
            with_sources += all(r.get("metadata", {}).get(f) for f in REQUIRED_METADATA)
        per_question.append({"question": q["question"], "rank": rank, "sources": sources})

    n = max(len(questions), 1)
    return {
        "k": k,
        "questions": len(questions),
        "recall_at_k": hits / n,
        "mrr": sum(reciprocal_ranks) / n,
        "source_presence": with_sources / total_chunks if total_chunks else 0.0,
        "per_question": per_question,
    }


def apply_gates(report: Dict, chunk_count: int, thresholds: Dict) -> Dict[str, Dict]:
    gates = {
        name: {"value": report[name], "threshold": thresholds[name],
               "passed": report[name] >= thresholds[name]}
        for name in ("recall_at_k", "mrr", "source_presence")
    }
    gates["min_chunks"] = {"value": chunk_count, "threshold": thresholds.get("min_chunks", 1),
                           "passed": chunk_count >= thresholds.get("min_chunks", 1)}
    return gates
