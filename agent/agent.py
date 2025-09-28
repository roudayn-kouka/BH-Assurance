from utils.llm_utils import LLM
import gc

from utils.general_utils import *
from utils.endpoint_utils import (
    get_strategy_specific_prompts,
    get_product_name_from_endpoint_data,
)
from config import *
from utils.mongodb_conn import (
    append_message_to_conversation,
    get_first_open_conversation,
    get_first_open_status_conversation,
    get_conversations_with_open_status,
    update_conversation_status,
    create_or_get_client,
)
from utils.user_type_classifier import (
    classify_user_type,
    get_user_display_name,
    extract_personne_physique_data,
    extract_personne_morale_data,
    UserType,
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
        data = user_data.get("data", {})
        product_name = get_product_name_from_endpoint_data(data)
        endpoint_strategy = data.get("endpoint_strategy", "unknown")
        recommended_action = data.get("recommended_action", "unknown")

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
                product_name=product_name,
            )
        except Exception as e:
            print(f"[agent main]: Error with scenario-specific prompt: {e}")
            print(f"[agent main]: Falling back to default prompt")
            # Fallback to original method
            response = self.llm.query_llm(
                True, user_data, rag_context, product_name=product_name
            )

        # Generate appropriate explanation based on strategy
        explanation = self._generate_scenario_explanation(
            endpoint_strategy, product_name, user_data["data"]
        )

        # Generate contextual subject line
        subject = self.llm.generate_mail_object(
            MAIL_SUBJECT_PROMPT.replace("{mail_body}", response)
        )

        return response, explanation, subject

    def _generate_scenario_explanation(
        self, strategy: str, product_name: str, raw_data: dict
    ) -> str:
        """Generate explanation text based on the business scenario."""

        profile = raw_data.get("profile", {})
        confidence_score = (
            profile.get("score")
            or profile.get("recommended_score")
            or profile.get("good_buyer_score_pct")
            or 0
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
""",
        }

        return strategy_explanations.get(
            strategy,
            f"""
Explication de génération — Stratégie générique

1. Produit ciblé: {product_name}
2. Score de confiance: {confidence_score}%
3. Approche standard de recommandation produit.
""",
        )

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
            intent["intention"]["label"],
            confidence_score=intent["intention"]["score"],
        )
        return response, explanation


def generate_initial_message(agent: "SalesAgent", user_data) -> str:
    """
    Generate the first message from the AI agent and log it to the DB.
    This function now:
    1. Classifies user type (personne_physique vs personne_morale)
    2. Creates or gets the client from MongoDB using backend-compatible schema
    3. Creates a new conversation for this client
    4. Adds the AI agent's initial message with proper 'ai' sender marking
    """
    print("\n" + "=" * 60)
    print("[generate_initial_message] Starting AI agent initiation process...")
    print("=" * 60)

    # Step 0: Classify user type and display information
    print("\n[generate_initial_message] Classifying user type...")
    user_type, confidence = classify_user_type(user_data)
    print(f"🏷️  User Type: {user_type.value.upper()} (Confidence: {confidence:.1%})")

    # Extract structured data for display
    if user_type == UserType.PERSONNE_PHYSIQUE:
        structured_data = extract_personne_physique_data(user_data)
        display_name = get_user_display_name(structured_data)
        print(f"👤 Individual: {display_name}")
    elif user_type == UserType.PERSONNE_MORALE:
        structured_data = extract_personne_morale_data(user_data)
        display_name = get_user_display_name(structured_data)
        print(f"🏢 Company: {display_name}")
    else:
        structured_data = extract_personne_physique_data(user_data)  # Fallback
        display_name = get_user_display_name(structured_data)
        print(f"❓ Unknown Type: {display_name} (treating as individual)")

    # Step 1: Generate AI agent response
    response, explanation, subject = agent.agent_initiate(user_data)

    # Step 2: Create or get client from database
    print("\n[generate_initial_message] Creating/getting client from database...")
    client_id = create_or_get_client(user_data)

    if not client_id:
        print("❌ [generate_initial_message] Failed to create/get client")
        return response, explanation, subject

    print(f"✅ [generate_initial_message] Using client_id: {client_id}")

    # Step 3: Determine conversation type and status based on strategy
    endpoint_strategy = user_data.get("data", {}).get("endpoint_strategy", "unknown")

    # Map AI strategies to backend conversation statuses
    strategy_to_status = {
        "product_recommendation": "nouvelle_opportunite",
        "contract_renewal": "renouvellement",
        "payment_reminder": "payment_facture",
        "upsell_cross_sell": "upsell_cross_sell",
        "unknown": "nouvelle_opportunite",
    }

    conversation_status = strategy_to_status.get(
        endpoint_strategy, "nouvelle_opportunite"
    )
    print(f"✅ [generate_initial_message] Conversation status: {conversation_status}")

    # Step 4: Add AI agent message to conversation
    print("\n[generate_initial_message] Adding AI agent message to database...")
    message_id, conversation_id = append_message_to_conversation(
        client_id=client_id,
        corps=response,  # AI generated response
        expediteur="ai",  # Mark as coming from AI agent
        statut="pending",  # Backend status enum
        msg_type="email",
        subject=subject,  # Generated subject
        conversation_status=conversation_status,
        argumentation=explanation,  # AI explanation for the response
    )

    if message_id and conversation_id:
        print(f"✅ [generate_initial_message] Successfully created:")
        print(f"   Message ID: {message_id}")
        print(f"   Conversation ID: {conversation_id}")
        print(f"   Sender: ai (AI Agent)")
        print(f"   Status: pending (awaiting validation)")
    else:
        print("❌ [generate_initial_message] Failed to create message")

    print("=" * 60)
    print("[generate_initial_message] Process completed!")
    print("=" * 60 + "\n")

    return response, explanation, subject


def generate_response(agent: "SalesAgent") -> str:
    """
    Generate a response from the agent for conversations with 'open' status.
    This function:
    1. Finds conversations with conversation_status='open'
    2. Generates appropriate responses using the AI agent
    3. Appends the agent's response to the conversation
    4. Updates the conversation_status from 'open' to 'pending'
    """
    print("\n" + "=" * 60)
    print("[generate_response] Looking for conversations with 'open' status...")
    print("=" * 60)

    # Step 1: Find conversations with 'open' status
    conversation = get_first_open_status_conversation()

    if not conversation:
        print("⚠️  [generate_response] No conversations with 'open' status found")
        return None, "No open conversations found"

    print(
        f"✅ [generate_response] Found conversation: {conversation['conversation_id']}"
    )
    print(
        f"   Client: {conversation['client']['first_name']} {conversation['client']['last_name']}"
    )
    print(
        f"   Latest message: {conversation['latest_client_message'][:100]}..."
        if conversation["latest_client_message"]
        else "   No client message found"
    )

    # Step 2: Get user data for this client (reconstruct from conversation data)
    client_data = conversation["client"]
    user_data = {
        "user_data_str": f"{client_data['first_name']} {client_data['last_name']} - Responding to client inquiry",
        "data": {
            "user_id": client_data["id"],
            "email": client_data["email"],
            "endpoint_strategy": "product_recommendation",  # Default strategy for responses
            "profile": {
                "first_name": client_data.get("first_name", "Unknown"),
                "last_name": client_data.get("last_name", "Unknown"),
                "email": client_data.get("email", ""),
                "telephone": client_data.get("phone", ""),
            },
            "produits_recommandes": [
                {"nom": "AUTOMOBILE", "score": 0.8, "category": "Auto Insurance"}
            ],
        },
    }

    # Step 3: Generate agent response
    print("\n[generate_response] Generating AI agent response...")
    try:
        response, explanation = agent.respond(
            user_message=conversation["latest_client_message"],
            user_data=user_data,
            conversation_history=conversation["conversation_history"],
        )
        print(f"✅ [generate_response] Generated response ({len(response)} chars)")
    except Exception as e:
        print(f"❌ [generate_response] Failed to generate response: {e}")
        return None, f"Error generating response: {e}"

    # Step 4: Generate subject for the response
    subject = f"Re: Votre demande d'information"

    # Step 5: Append agent response to conversation
    print("\n[generate_response] Adding agent response to database...")
    message_id, conversation_id = append_message_to_conversation(
        client_id=conversation["client"]["id"],
        corps=response,
        expediteur="ai",  # Mark as AI agent response
        statut="pending",  # Requires validation
        msg_type="email",
        conversation_id=conversation["conversation_id"],
        subject=subject,
        argumentation=explanation,  # AI explanation for the response
    )

    if not message_id:
        print("❌ [generate_response] Failed to save agent response")
        return None, "Failed to save response"

    print(f"✅ [generate_response] Agent response saved: {message_id}")

    # Step 6: Update conversation status from 'open' to 'pending'
    print(
        "\n[generate_response] Updating conversation status from 'open' to 'pending'..."
    )
    status_updated = update_conversation_status(
        conversation["conversation_id"], "pending"
    )

    if status_updated:
        print(f"✅ [generate_response] Conversation status updated to 'pending'")
    else:
        print(f"❌ [generate_response] Failed to update conversation status")

    print("=" * 60)
    print("[generate_response] Response process completed!")
    print("=" * 60 + "\n")

    return response, explanation
