"""Orchestrator behind feature flags: legacy parity, policy modes, controlled fallback."""

import importlib

import pytest

import config
import feature_flags
from compliance import check_message
from utils import policy_client


@pytest.fixture
def agent_mod(monkeypatch):
    def load(**flags):
        for name, value in flags.items():
            monkeypatch.setattr(feature_flags, name, value)
        import agent

        return importlib.reload(agent)
    return load


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


def _service(monkeypatch, action="recommend_guarantee", fail=False):
    calls = []

    def post(url, json, headers, timeout):
        calls.append(json)
        if fail:
            raise ConnectionError("down")
        return FakeResponse({"action": action, "model_version": "rl-1", "fallback": False,
                             "reason_codes": ["model:linucb", "low_propensity"],
                             "allowed_actions": ["wait", action]})
    monkeypatch.setattr(policy_client.requests, "post", post)
    return calls


def test_orchestrator_matches_legacy_when_policy_off(agent_mod, monkeypatch, intent, rag_calls, user_data):
    legacy = agent_mod(USE_ORCHESTRATOR=False, POLICY_MODE="off").SalesAgent()
    legacy_response, _ = legacy.respond("Je veux un devis", user_data, "historique")
    legacy_llm_call = [c for c in legacy.llm.calls if c[0] == "query_llm"][0]
    legacy_rag = list(rag_calls)
    rag_calls.clear()

    graph = agent_mod(USE_ORCHESTRATOR=True, POLICY_MODE="off").SalesAgent()
    response, explanation = graph.respond("Je veux un devis", user_data, "historique")
    graph_llm_call = [c for c in graph.llm.calls if c[0] == "query_llm"][0]

    assert response == legacy_response
    assert rag_calls == legacy_rag
    assert graph_llm_call[1][2] == legacy_llm_call[1][2]  # same RAG context
    assert graph_llm_call[2] == legacy_llm_call[2]  # same system prompt and inputs
    assert graph.last_decision["mode"] == "off" and graph.last_decision["action"] == "recommend_product"
    assert "data/CG-Automobile/cg_auto.pdf (version 2024)" in explanation
    assert "decision_id=" in explanation and "features" not in graph.last_decision


def test_active_mode_applies_policy_action_directive(agent_mod, monkeypatch, intent, user_data):
    calls = _service(monkeypatch, action="recommend_guarantee")
    sales_agent = agent_mod(USE_ORCHESTRATOR=True, POLICY_MODE="active").SalesAgent()
    _, explanation = sales_agent.respond("Je veux un devis", user_data, "")

    system_prompt = [c for c in sales_agent.llm.calls if c[0] == "query_llm"][0][2]["system_prompt"]
    assert config.ACTION_DIRECTIVES["recommend_guarantee"] in system_prompt
    assert calls[0]["features"]["good_buyer_score"] == 72.0 and calls[0]["state_version"] == "v1"
    assert sales_agent.last_decision["model_version"] == "rl-1"
    assert "low_propensity" in explanation


def test_shadow_mode_logs_but_keeps_legacy(agent_mod, monkeypatch, intent, user_data):
    _service(monkeypatch, action="recommend_guarantee")
    sales_agent = agent_mod(USE_ORCHESTRATOR=True, POLICY_MODE="shadow").SalesAgent()
    _, explanation = sales_agent.respond("Je veux un devis", user_data, "")

    d = sales_agent.last_decision
    assert d["policy_action"] == "recommend_guarantee" and d["action"] == "recommend_product"
    system_prompt = [c for c in sales_agent.llm.calls if c[0] == "query_llm"][0][2]["system_prompt"]
    assert system_prompt == config.SALES_STRATEGIES["devis"]["system_prompt"]
    assert "non appliquée" in explanation


def test_service_down_falls_back_to_legacy_strategy(agent_mod, monkeypatch, intent, user_data):
    _service(monkeypatch, fail=True)
    sales_agent = agent_mod(USE_ORCHESTRATOR=True, POLICY_MODE="active").SalesAgent()
    response, _ = sales_agent.respond("Je veux un devis", user_data, "")

    assert response
    d = sales_agent.last_decision
    assert d["action"] == "recommend_product" and d["fallback"] is True
    assert d["fallback_reason"].startswith("policy_service_unavailable")


def test_initial_contact_can_be_deferred(agent_mod, monkeypatch, user_data):
    _service(monkeypatch, action="wait")
    agent = agent_mod(USE_ORCHESTRATOR=False, POLICY_MODE="active")
    sales_agent = agent.SalesAgent()
    response, explanation, subject = sales_agent.agent_initiate(user_data)
    assert response is None and subject is None and "différé" in explanation
    assert sales_agent.last_decision["action"] == "wait"


def test_compliance_flags_ungrounded_figures_and_promises():
    ok = check_message("Le tarif est de 350 DT par an.", "tarif: 350 DT", "", [{"source": "x"}], True)
    assert ok["passed"]
    bad = check_message("Garanti à 100 % pour 99 DT seulement !", "", "", [], True)
    assert not bad["passed"]
    assert "absolute_guarantee" in bad["issues"] and "no_supporting_sources" in bad["issues"]
    assert any(i.startswith("unsupported_figure") for i in bad["issues"])


def test_decision_event_only_published_when_flag_on(monkeypatch):
    from utils import event_publisher

    published = []

    class Publisher:
        def publish(self, event):
            published.append(event)
            return True

    decision = {"decision_id": "d-9", "action": "wait", "model_version": "rl-1", "trace_id": "t"}
    monkeypatch.setattr(feature_flags, "PUBLISH_EVENTS", False)
    assert not event_publisher.publish_decision(decision, "c1", "m1", Publisher())
    monkeypatch.setattr(feature_flags, "PUBLISH_EVENTS", True)
    assert event_publisher.publish_decision(decision, "c1", "m1", Publisher())
    assert published[0].event_type == "decision_made" and published[0].message_id == "m1"
    assert not event_publisher.publish_decision(None, "c1", "m1", Publisher())


def test_initial_message_records_rag_sources(agent_mod, monkeypatch, user_data):
    _service(monkeypatch, action="recommend_product")
    sales_agent = agent_mod(USE_ORCHESTRATOR=False, POLICY_MODE="active").SalesAgent()
    response, explanation, _ = sales_agent.agent_initiate(user_data)

    assert response
    assert sales_agent.last_decision["sources"][0]["source"] == "data/CG-Automobile/cg_auto.pdf"
    assert "cg_auto.pdf (version 2024)" in explanation
