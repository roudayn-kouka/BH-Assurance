from utils.llm_utils import LLM
import gc

from utils.general_utils import *
from config import *
from utils.mongodb_conn import (
    append_message_to_conversation,
    get_first_open_conversation,
)


# -----------------------------
# Agent Orchestration
# -----------------------------


class SalesAgent:
    def __init__(self):

        self.llm = LLM()

    def agent_initiate(self, user_data) -> str:
        """Premier message : recommandation produit ou rappel facture"""

        # Déterminer si rappel facture ou reco produit
        print("\n", "=" * 50)
        print(f'[agent main]: User data: {user_data["user_data_str"]}')
        print("\n", "=" * 50)
        product_name = user_data["data"]["produits_recommandes"][0]["nom"]
        rag_query = self.llm.query_small_rag_llm(product_name)
        rag_context = query_rag(rag_query)
        # Run LLM
        response = self.llm.query_llm(
            True, user_data, rag_context, product_name=product_name
        )
        explanation = generate_explanation(
            "initial pitch",
            product_name,
            INITIAL_SALES_PROMPT_TEMPLATE,
            confidence_score=user_data["data"]["produits_recommandes"][0]["score"],
        )

        subject = self.llm.generate_mail_object(
            MAIL_SUBJECT_PROMPT.replace("{mail_body}", response)
        )
        return response, explanation, subject

    def respond(self, user_message: str, user_data, conversation_history: str) -> str:
        """Répondre au client avec logique intent + infos manquantes"""

        intent = analyze_intent(user_message)
        strategy = SALES_STRATEGIES.get(intent["intention"]["label"])
        # Si infos manquantes → collect d’abord
        print(f"detected intent: {intent['intention']}")

        if strategy["use_rag"]:
            rag_query = self.llm.query_rag_llm(conversation_history, user_message)
            rag_context = query_rag(rag_query)
        else:
            rag_context = ""

        print(f"RAG Context: {rag_context}")
        response = self.llm.query_llm(
            True,
            user_data,
            rag_context,
            system_prompt=strategy["system_prompt"],
            user_message=user_message,
            conversation_history=conversation_history,
        )
        explanation = generate_explanation(
            "respond",
            user_data["data"]["produits_recommandes"],
            strategy["system_prompt"],
            intent,
            confidence_score=intent,
        )
        return response, explanation


def generate_initial_message(agent: "SalesAgent", user_data) -> str:
    """
    Generate the first message from the sales agent and log it to the DB.
    """

    response, explanation, subject = agent.agent_initiate(user_data)
    append_message_to_conversation(
        client_id=user_data["data"]["client_id"],
        corps=response,
        expediteur="agent",
        statut="non validé",
        msg_type="email",
    )
    return response, explanation, subject


def generate_response(agent: "SalesAgent") -> str:
    """
    Generate a response from the agent given the user's message and log it.
    """
    conversation = get_first_open_conversation()
    user_data = fetch_existing_user_data(conversation["client"]["id"])
    response, explanation = agent.respond(
        user_data=user_data,
        user_message=conversation["latest_user_message"],
        conversation_history=conversation["conversation_history"],
    )

    append_message_to_conversation(
        client_id=conversation["client"]["id"],
        corps=response,
        expediteur="agent",
        statut="non validé",
        msg_type="email",
        conversation_id=conversation["conversationId"],
    )
    return response, explanation


from datetime import datetime


# -----------------------------
# Dummy test function
# -----------------------------
def test_sales_agent_initiation():
    # Dummy user data (simulating something from your dataset)
    user_data = {
        "client_id": "101372",  # existing REF_pm
        "user_data": {
            "nom": "Test User",
            "email": "test.user@email.com",
            "telephone": "+33 6 12 34 56 78",
            "statut": "actif",
            "LIB_SECTEUR_ACTIVITE": "Commerce",
            "LIB_PRODUIT": "AUTOMOBILE",
            "age_contract": 0.0,
            "category": "Commerce & Services",
            "candidate_product": "MULTIRISQUES PROFESSIONNELLES CENTRALISE",
            "Bought": 0,
            "score": 0.87,
        },
    }

    # Init agent
    agent = SalesAgent()

    # Step 1: Agent initiates
    first_message = generate_initial_message(agent, user_data)
    print("\n[TEST] Agent first message:\n", first_message)

    # Step 2: Simulate a user reply
    dummy_user_message = "Je veux savoir le prix de cette assurance automobile."
    conversation_history = [
        {"sender": "agent", "text": first_message, "timestamp": datetime.utcnow()},
        {"sender": "user", "text": dummy_user_message, "timestamp": datetime.utcnow()},
    ]

    # Step 3: Agent responds
    agent_reply = agent.respond(
        user_message=dummy_user_message,
        user_data=user_data["user_data"],
        conversation_history=str(conversation_history),  # simplified for test
    )
    print("\n[TEST] Agent response:\n", agent_reply)

    return first_message, agent_reply


# Run directly for manual test
if __name__ == "__main__":
    first, reply = test_sales_agent_initiation()
    print("\n✅ Test completed. Messages exchanged:")
    print("Agent (init):", first)
    print("Agent (reply):", reply)
