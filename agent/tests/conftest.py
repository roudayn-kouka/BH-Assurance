"""
Test harness for the agent package.

The real agent modules load LLMs, transformer classifiers, ChromaDB and MongoDB at
import time. These stubs replace them so the orchestration logic can be tested
without any infrastructure.
"""

import os
import sys
import types

import pytest

AGENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO_ROOT = os.path.abspath(os.path.join(AGENT_DIR, ".."))
for path in (REPO_ROOT, AGENT_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)


class StubLLM:
    def __init__(self):
        self.calls = []

    def query_llm(self, *args, **kwargs):
        self.calls.append(("query_llm", args, kwargs))
        return "Bonjour, voici notre proposition."

    def query_rag_llm(self, conversation_history, latest_user_message):
        self.calls.append(("query_rag_llm", conversation_history, latest_user_message))
        return f"rag query for: {latest_user_message}"

    def query_small_rag_llm(self, product_name):
        self.calls.append(("query_small_rag_llm", product_name))
        return f"rag query for: {product_name}"

    def query_scenario_llm(self, **kwargs):
        self.calls.append(("query_scenario_llm", kwargs))
        return "Message initial."

    def generate_mail_object(self, prompt):
        return "Objet"


class IntentStub:
    label = "devis"
    score = 0.9

    @classmethod
    def analyse(cls, text, threshold=0.7):
        return {
            "texte": text,
            "intention": {"label": cls.label, "score": cls.score},
            "produit": {"label": "aucun", "score": 0.0},
        }


class RagStub:
    calls = []
    docs = [
        {
            "document": "La garantie bris de glace couvre le pare-brise.",
            "metadata": {"source": "data/CG-Automobile/cg_auto.pdf", "document_version": "2024"},
        }
    ]

    @classmethod
    def retrieve(cls, query, top_k=5):
        cls.calls.append(query)
        return cls.docs[:top_k]

    @classmethod
    def retrieve_context(cls, query, top_k=5):
        return cls.build_context(cls.retrieve(query, top_k))

    @staticmethod
    def build_context(docs):
        return "".join(
            f"[Doc {i} - {d['metadata']['source']}]\n{d['document']}\n\n"
            for i, d in enumerate(docs, 1)
        )


def _install_stubs():
    llm_mod = types.ModuleType("utils.llm_utils")
    llm_mod.LLM = StubLLM
    sys.modules["utils.llm_utils"] = llm_mod

    rag_pkg = types.ModuleType("rag_model")
    rag_mod = types.ModuleType("rag_model.rag")
    rag_mod.retrieve = RagStub.retrieve
    rag_mod.retrieve_context = RagStub.retrieve_context
    rag_mod.get_index_info = lambda: {"index_version": "test-index", "collection": "legal_docs"}
    rag_mod.build_context = RagStub.build_context
    rag_mod.source_of = lambda d: {
        "source_id": d["metadata"]["source"], "source": d["metadata"]["source"],
        "document_version": d["metadata"].get("document_version", "unknown"), "page": None,
    }
    rag_pkg.rag = rag_mod
    rag_pkg.retrieve_context = RagStub.retrieve_context
    sys.modules["rag_model"] = rag_pkg
    sys.modules["rag_model.rag"] = rag_mod

    intent_mod = types.ModuleType("intent_analysis")
    intent_mod.analyse_message = IntentStub.analyse
    sys.modules["intent_analysis"] = intent_mod

    mongo_mod = types.ModuleType("utils.mongodb_conn")
    mongo_mod.persisted = []

    def append_message_to_conversation(**kwargs):
        mongo_mod.persisted.append(kwargs)
        return "msg-1", kwargs.get("conversation_id") or "conv-1"

    mongo_mod.append_message_to_conversation = append_message_to_conversation
    for name in (
        "get_first_open_conversation",
        "get_first_open_status_conversation",
        "get_conversations_with_open_status",
        "update_conversation_status",
        "create_or_get_client",
    ):
        setattr(mongo_mod, name, lambda *a, **k: None)
    sys.modules["utils.mongodb_conn"] = mongo_mod

    try:
        import requests  # noqa: F401
    except ImportError:
        sys.modules["requests"] = types.ModuleType("requests")


_install_stubs()


@pytest.fixture
def intent():
    IntentStub.label, IntentStub.score = "devis", 0.9
    return IntentStub


@pytest.fixture
def rag_calls():
    RagStub.calls.clear()
    return RagStub.calls


@pytest.fixture
def user_data():
    return {
        "user_data_str": "Client test",
        "data": {
            "user_id": "REF_pp_1",
            "endpoint_strategy": "product_recommendation",
            "recommended_action": "recommend_produit",
            "profile": {"age": 40, "good_buyer_pct": 72.0, "recommended_score": 65.0},
            "produits_recommandes": [{"nom": "AUTOMOBILE", "score": 0.8}],
        },
    }
