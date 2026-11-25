"""
Reference tests capturing the legacy SalesAgent.respond() behaviour.

They must keep passing with every feature flag off: this is the regression
baseline for the orchestrator migration.
"""

import importlib
import importlib.util
import os

import config
import feature_flags


def _agent_module(monkeypatch, **flags):
    for name, value in flags.items():
        monkeypatch.setattr(feature_flags, name, value)
    import agent

    return importlib.reload(agent)


def test_respond_uses_rag_when_strategy_requires_it(monkeypatch, intent, rag_calls, user_data):
    agent_mod = _agent_module(monkeypatch, USE_ORCHESTRATOR=False)
    sales_agent = agent_mod.SalesAgent()

    response, explanation = sales_agent.respond("Je veux un devis", user_data, "historique")

    assert response == "Bonjour, voici notre proposition."
    assert rag_calls == ["rag query for: Je veux un devis"]
    _, args, kwargs = [c for c in sales_agent.llm.calls if c[0] == "query_llm"][0]
    # the reply chain (is_initial=False) is the one that reads the message and the strategy
    assert args[0] is False
    assert kwargs["user_message"] == "Je veux un devis"
    assert kwargs["conversation_history"] == "historique"
    assert kwargs["system_prompt"] == config.SALES_STRATEGIES["devis"]["system_prompt"]
    assert "Retrieved RAG info" in sales_agent.llm.calls[-1][1][2]
    assert "devis" in explanation


def test_respond_skips_rag_for_no_interest(monkeypatch, intent, rag_calls, user_data):
    intent.label = "pas d'intérêt"
    agent_mod = _agent_module(monkeypatch, USE_ORCHESTRATOR=False)
    sales_agent = agent_mod.SalesAgent()

    sales_agent.respond("Non merci", user_data, "")

    assert rag_calls == []
    _, args, _ = [c for c in sales_agent.llm.calls if c[0] == "query_llm"][0]
    assert args[2] == ""


def test_every_intent_label_has_a_strategy():
    # respond() does SALES_STRATEGIES.get(label)["use_rag"]: an unmapped label crashes it
    spec = importlib.util.spec_from_file_location(
        "intent_config", os.path.join(os.path.dirname(__file__), "..", "intent_analysis", "config.py")
    )
    intent_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(intent_config)

    for label in [*intent_config.INTENT_LABELS, *intent_config.PATTERNS]:
        assert label in config.SALES_STRATEGIES, label
