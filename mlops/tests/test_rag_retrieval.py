import json

import pytest

from mlops.common import manifest as mf
from mlops.data_rag import evaluate, index_chroma, ingest_documents, prepare, publish

CATEGORY_MAP = {"CG-Automobile": "Assurance Automobile", "CG-Vie": "Assurance Vie"}


@pytest.fixture
def corpus(tmp_path):
    auto = tmp_path / "docs" / "1-CG-Automobile"
    vie = tmp_path / "docs" / "2-CG-Vie"
    auto.mkdir(parents=True)
    vie.mkdir(parents=True)
    (auto / "cg_auto.txt").write_text(
        "La garantie bris de glace couvre le pare-brise.\n\n" + "Responsabilité civile. " * 60,
        encoding="utf-8",
    )
    (vie / "cg_vie.md").write_text("Le capital décès est versé aux bénéficiaires.", encoding="utf-8")
    (vie / "cg_vie.md.meta.yaml").write_text("date_effet: 2024-01-01\nproduit: Vie Plus\n")
    return tmp_path


def _inventory(base):
    return prepare.build_inventory(["docs"], [".txt", ".md"], CATEGORY_MAP, base=base)


def test_inventory_and_chunks_are_deterministic(corpus):
    inv1, inv2 = _inventory(corpus), _inventory(corpus)
    assert inv1 == inv2
    assert [d["category"] for d in inv1["documents"]] == ["Assurance Automobile", "Assurance Vie"]
    vie = inv1["documents"][1]
    assert vie["product"] == "Vie Plus" and vie["date_effet"] == "2024-01-01"
    json.dumps(inv1)  # the inventory is written as JSON by the pipeline

    chunks1 = ingest_documents.ingest(inv1, 200, 20, base=corpus)
    chunks2 = ingest_documents.ingest(inv2, 200, 20, base=corpus)
    assert chunks1 == chunks2 and len(chunks1) > 2
    assert len({c["id"] for c in chunks1}) == len(chunks1)
    for c in chunks1:
        meta = c["metadata"]
        assert meta["source"].startswith("docs/") and meta["document_version"]
        assert len(c["text"]) <= 200


def test_corpus_change_changes_index_version(corpus):
    v1 = index_chroma.index_version(_inventory(corpus)["corpus_hash"], "m", 500, 50)
    (corpus / "docs" / "2-CG-Vie" / "cg_vie.md").write_text("nouvelle version", encoding="utf-8")
    v2 = index_chroma.index_version(_inventory(corpus)["corpus_hash"], "m", 500, 50)
    assert v1 != v2
    assert v1 != index_chroma.index_version(_inventory(corpus)["corpus_hash"], "other-model", 500, 50)


def test_split_text_overlap():
    chunks = ingest_documents.split_text("mot " * 300, 100, 20)
    assert all(len(c) <= 100 for c in chunks)
    assert len(chunks) > 10


def _retriever(results_by_question):
    def retrieve(query, k):
        return results_by_question[query][:k]
    return retrieve


def _doc(source, version="v1"):
    return {"document": "x", "metadata": {"source": source, "document_version": version}}


def test_recall_mrr_and_source_presence():
    questions = [
        {"question": "auto", "expected_sources": ["CG-Automobile"]},
        {"question": "vie", "expected_sources": ["CG-Vie"]},
        {"question": "sante", "expected_sources": ["CG-Santé"]},
    ]
    retrieve = _retriever({
        "auto": [_doc("docs/CG-Automobile/a.pdf"), _doc("docs/CG-Vie/b.pdf")],
        "vie": [_doc("docs/CG-Automobile/a.pdf"), _doc("docs/CG-Vie/b.pdf")],
        "sante": [{"document": "x", "metadata": {"source": "docs/CG-IARD/c.pdf"}}],
    })
    report = evaluate.evaluate_retrieval(retrieve, questions, k=2)
    assert report["recall_at_k"] == pytest.approx(2 / 3)
    assert report["mrr"] == pytest.approx((1 + 0.5 + 0) / 3)
    assert report["source_presence"] == pytest.approx(4 / 5)

    gates = evaluate.apply_gates(report, 10, {"recall_at_k": 0.8, "mrr": 0.6,
                                               "source_presence": 1.0, "min_chunks": 1})
    assert not gates["recall_at_k"]["passed"] and gates["min_chunks"]["passed"]


class FakeCollection:
    def __init__(self, name):
        self.name, self.rows = name, []

    def add(self, ids, documents, embeddings, metadatas):
        self.rows += list(zip(ids, documents, embeddings, metadatas))


class FakeClient:
    def __init__(self):
        self.collections = {}

    def list_collections(self):
        return list(self.collections.values())

    def delete_collection(self, name):
        del self.collections[name]

    def create_collection(self, name, metadata=None):
        self.collections[name] = FakeCollection(name)
        return self.collections[name]


def test_build_index_is_isolated_and_protects_active(corpus):
    chunks = ingest_documents.ingest(_inventory(corpus), 200, 20, base=corpus)
    client = FakeClient()
    embed = lambda texts: [[float(len(t))] for t in texts]  # noqa: E731
    col = index_chroma.build_index(client, chunks, "legal_docs__rag-1", embed, {"legal_docs"},
                                   batch_size=2)
    assert len(col.rows) == len(chunks)
    # rebuilding a candidate replaces it instead of duplicating chunks
    col = index_chroma.build_index(client, chunks, "legal_docs__rag-1", embed, {"legal_docs"})
    assert len(col.rows) == len(chunks)
    with pytest.raises(RuntimeError):
        index_chroma.build_index(client, chunks, "legal_docs", embed, {"legal_docs"})


def test_failed_gate_never_reaches_latest(tmp_path):
    gates = {"recall_at_k": {"value": 0.5, "threshold": 0.8, "passed": False}}
    m = publish.publish_candidate("rag-x", "c", "m", "h", 3, "chroma://c", {"recall_at_k": 0.5},
                                  gates, None, root=tmp_path)
    assert m.approved is False
    with pytest.raises(mf.ManifestError):
        mf.promote("rag", "rag-x", "ci", tmp_path)
