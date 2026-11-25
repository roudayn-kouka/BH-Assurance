"""Check the agent's initial recommendation draft without live services."""

import sys
from contextlib import redirect_stdout
from importlib import import_module
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


AGENT_DIRECTORY = Path(__file__).resolve().parents[1] / "agent"
SUBJECT = "Synthetic insurance recommendation"


def check_recommendation_draft(payload, expected_product):
    body = f"Consider {expected_product} for your synthetic company."
    model = SimpleNamespace(
        query_small_rag_llm=Mock(return_value=expected_product),
        query_scenario_llm=Mock(return_value=body),
        generate_mail_object=Mock(return_value=SUBJECT),
    )
    storage = SimpleNamespace(
        create_or_get_client=Mock(return_value="synthetic-client"),
        append_message_to_conversation=Mock(return_value=("synthetic-message", "synthetic-conversation")),
        get_first_open_conversation=Mock(side_effect=AssertionError("Unexpected storage read")),
        get_first_open_status_conversation=Mock(side_effect=AssertionError("Unexpected storage read")),
        get_conversations_with_open_status=Mock(side_effect=AssertionError("Unexpected storage read")),
        update_conversation_status=Mock(side_effect=AssertionError("Unexpected status update")),
    )
    rag = SimpleNamespace(retrieve_context=Mock(return_value="Synthetic product context"))
    substitutes = {
        "utils.llm_utils": SimpleNamespace(LLM=lambda: model),
        "utils.mongodb_conn": storage,
        "rag_model": SimpleNamespace(rag=rag),
        "intent_analysis": SimpleNamespace(
            analyse_message=Mock(side_effect=AssertionError("Unexpected intent analysis")),
        ),
    }
    with patch.dict(sys.modules, substitutes), patch.object(
        sys, "path", [str(AGENT_DIRECTORY), *sys.path]
    ):
        agent = import_module("agent")
        utils = import_module("utils.general_utils")
        with patch.object(utils, "fetch_new_user", return_value=payload), redirect_stdout(StringIO()):
            user_data = utils.fetch_new_user_data()
            agent.generate_initial_message(agent.SalesAgent(), user_data)

    model.query_small_rag_llm.assert_called_once_with(expected_product)
    model.query_scenario_llm.assert_called_once()
    prompt = model.query_scenario_llm.call_args.kwargs
    if prompt["product_name"] != expected_product or prompt["scenario_type"] != "product_recommendation":
        raise RuntimeError("The agent did not use the expected product recommendation")

    storage.create_or_get_client.assert_called_once_with(user_data)
    storage.append_message_to_conversation.assert_called_once()
    draft = storage.append_message_to_conversation.call_args.kwargs
    if (draft["subject"], draft["corps"], draft["statut"]) != (SUBJECT, body, "pending"):
        raise RuntimeError("The agent did not save the expected pending draft")
    return draft


if __name__ == "__main__":
    product = "Synthetic Fleet Cover"
    recommendation = {
        "user_id": "REF_pm_DRAFT",
        "user_type": "personne_morale",
        "endpoint_key": "pm_recommendation",
        "endpoint_strategy": "product_recommendation",
        "recommended_action": "recommend_produit",
        "profile": {"candidate_produit": product, "raison_sociale": "Synthetic Company"},
    }
    draft = check_recommendation_draft(recommendation, product)
    print(f"Draft subject: {draft['subject']}")
    print(f"Draft status: {draft['statut']}")
