from langchain.chains import LLMChain
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
import gc

from utils import *
from config import *


# -----------------------------
# LLM Setup
# -----------------------------
llm = OllamaLLM(model=LLM_MODEL)

# -----------------------------
# Prompt Setup
# -----------------------------
sales_prompt = PromptTemplate(
    input_variables=SALES_PROMPT_INPUT_VARS,
    template=SALES_PROMPT_TEMPLATE.replace("{company_name}", COMPANY_NAME)
                                   .replace("{language}", LANGUAGE)
                                   .replace("{max_sentences}", str(MAX_SENTENCES))
)
rag_prompt = PromptTemplate(
    input_variables=["conversation_history", "latest_user_message"],
    template=RAG_QUERY_PROMPT)
# -----------------------------
# Chain
# -----------------------------
sales_chain = sales_prompt | llm
rag_chain = rag_prompt | llm

def query_llm(strategy, user_data,rag_context,user_message,conversation_history):
    response = sales_chain.invoke({
                "system_prompt": strategy["system_prompt"].format(company_name=COMPANY_NAME),
                "user_data": user_data,
                "rag_context": rag_context,
                "conversation_history": "\n".join(conversation_history),
                "latest_user_message": user_message,
            })
    return response

def query_rag_llm(conversation_history, latest_user_message):
    return rag_chain.invoke({
        "conversation_history": "\n".join(conversation_history),
        "latest_user_message": latest_user_message,
    })
# -----------------------------
# Agent Orchestration
# -----------------------------
class SalesAgent:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.conversation_history = []

    def agent_initiate(self) -> str:
        """Premier message : recommandation produit ou rappel facture"""
        user_data = fetch_user_data(self.user_id)

        # Déterminer si rappel facture ou reco produit
        if user_data.get("bills_due"):
            strategy = SALES_STRATEGIES.get("remind_unpaid_bill")
        elif user_data.get("recommended_products"):
            strategy = SALES_STRATEGIES.get("recommend_product")

        # Run LLM
        response = query_llm(strategy, user_data,"","il n'y a pas de message utilisateur",self.conversation_history)

        self.conversation_history.append(f"Agent: {response}")
        return response

    def respond(self, user_message: str) -> str:
        """Répondre au client avec logique intent + infos manquantes"""
        user_data = fetch_user_data(self.user_id)
        intent = analyze_intent(user_message)
        strategy = SALES_STRATEGIES.get(intent["intention"])
        # Si infos manquantes → collect d’abord
        print(f"detected intent: {intent['intention']}")

        if strategy["use_rag"]:
            rag_query = query_rag_llm(self.conversation_history, user_message)
            rag_context = query_rag(rag_query)
        else:
            rag_context = ""

        
        response = query_llm(strategy, user_data,rag_context,user_message,self.conversation_history)


        # Historique
        self.conversation_history.append(f"User: {user_message}")
        self.conversation_history.append(f"Agent: {response}")
        return response


# -----------------------------
# Exemple d’utilisation
# -----------------------------
agent = SalesAgent(user_id="12345")

# Premier message
first_msg = agent.agent_initiate()
print(f"Agent: {first_msg}\n")

# Simulation d’échanges
user_messages = [
    "Bonjour, je suis dans le secteur agro alimentaire, j’ai bien reçu votre offre, mais je voudrais avoir plus de détails sur le plan proposé.",
    "Merci pour la réponse. Est-ce que cette couverture inclut également ma famille ou seulement moi ?",
    "Parfait, c’est exactement ce que je cherchais. Quelle est la prochaine étape pour m’inscrire ?"
]


try:
    while True:
        msg = input("donner votre message: ")
        if not msg.strip():
            print("⏭️ Message vide ignoré.")
            continue

        print("==================================================================")
        print(f"User: {msg}\n")
        reply = agent.respond(msg)
        print("==================================================================")
        print(f"Agent: {reply}\n")

except KeyboardInterrupt:
    print("\n\n🛑 Interruption clavier détectée. Sauvegarde de l’état en cours...")
    del llm
    gc.collect()


    print("✅ Historique sauvegardé dans conversation_cache.txt. Au revoir 👋")