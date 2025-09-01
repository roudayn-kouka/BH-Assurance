from utils.llm_utils import LLM
import gc

from utils.general_utils import *
from utils.endpoint_utils import (
    get_strategy_specific_prompts, 
    get_product_name_from_endpoint_data
)
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
        """Premier message avec prompts spécialisés selon le scénario business"""

        # Display user data for debugging
        print("\n", "=" * 50)
        print(f'[agent main]: User data: {user_data["user_data_str"]}')
        print("\n", "=" * 50)
        
        # Extract product name and business strategy
        product_name = get_product_name_from_endpoint_data(user_data["data"])
        endpoint_strategy = user_data["data"].get("endpoint_strategy", "unknown")
        recommended_action = user_data["data"].get("recommended_action", "unknown")
        
        print(f"[agent main]: Extracted product name: {product_name}")
        print(f"[agent main]: Business strategy: {endpoint_strategy}")
        print(f"[agent main]: Recommended action: {recommended_action}")
        
        # Generate RAG context based on the product
        rag_query = self.llm.query_small_rag_llm(product_name)
        rag_context = query_rag(rag_query)
        
        # Use scenario-specific prompts for better targeting
        print(f"[agent main]: Using scenario-specific prompt for: {endpoint_strategy}")
        
        try:
            # Query with scenario-specific prompts
            response = self.llm.query_scenario_llm(
                scenario_type=endpoint_strategy,
                user_data=user_data["user_data_str"],
                rag_context=rag_context,
                product_name=product_name
            )
        except Exception as e:
            print(f"[agent main]: Error with scenario-specific prompt: {e}")
            print(f"[agent main]: Falling back to default prompt")
            # Fallback to original method
            response = self.llm.query_llm(
                True, 
                user_data, 
                rag_context, 
                product_name=product_name
            )
        
        # Generate appropriate explanation based on strategy
        explanation = self._generate_scenario_explanation(
            endpoint_strategy, 
            product_name, 
            user_data["data"]
        )

        # Generate contextual subject line
        subject = self.llm.generate_mail_object(
            MAIL_SUBJECT_PROMPT.replace("{mail_body}", response)
        )
        
        return response, explanation, subject
    
    def _generate_scenario_explanation(self, strategy: str, product_name: str, raw_data: dict) -> str:
        """Generate explanation text based on the business scenario."""
        
        profile = raw_data.get("profile", {})
        confidence_score = (
            profile.get("score") or 
            profile.get("recommended_score") or
            profile.get("good_buyer_score_pct") or
            0
        )
        
        strategy_explanations = {
            "product_recommendation": f"""
Explication de génération — Recommandation produit personnalisée

1. Approche utilisée :
   Analyse du profil client (secteur: {profile.get('lib_secteur_activite', 'N/A')}, 
   activité: {profile.get('lib_activite', 'N/A')}) pour recommander {product_name}.

2. Score de pertinence :
   Score de confiance: {confidence_score}% - Le produit est hautement adapté au profil.

3. Stratégie de communication :
   Mise en avant des bénéfices business spécifiques au secteur du client.
   Personnalisation basée sur l'analyse des besoins métier.
""",
            
            "payment_reminder": f"""
Explication de génération — Rappel de paiement bienveillant

1. Approche utilisée :
   Gestion respectueuse de l'impayé pour le contrat {profile.get('num_contrat', 'N/A')} 
   concernant {product_name}.

2. Statut actuel :
   Paiement: {profile.get('statut_paiement', 'N/A')} - Intervention requise pour régulariser.

3. Stratégie de communication :
   Ton ferme mais bienveillant, proposition de solutions d'aide.
   Préservation de la relation client tout en rappelant les obligations.
""",
            
            "contract_renewal": f"""
Explication de génération — Renouvellement de contrat fidélité

1. Approche utilisée :
   Valorisation de la relation existante (durée: {profile.get('age_contract', 'N/A')} ans)
   pour renouveler {product_name}.

2. Échéance proche :
   Date d'expiration: {profile.get('date_expiration_contract', profile.get('date_expiration', 'N/A'))}
   - Action requise pour assurer la continuité.

3. Stratégie de communication :
   Reconnaissance de la fidélité, proposition d'améliorations de garanties.
   Facilitation du processus de renouvellement.
"""
        }
        
        return strategy_explanations.get(strategy, f"""
Explication de génération — Stratégie générique

1. Produit ciblé: {product_name}
2. Score de confiance: {confidence_score}%
3. Approche standard de recommandation produit.
""")

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
    
    # Extract client_id from the new data structure
    client_id = user_data["data"].get("user_id", "unknown")
    
    append_message_to_conversation(
        client_id=client_id,
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
