from typing import Dict, Any
from rag_model import rag
from intent_analysis import analyse_message
from utils.user_profile_conn import *
import random
from typing import Dict


def format_user_for_llm(user_data: Dict) -> str:
    """
    Transform user data into a structured prompt-friendly format for an LLM.
    Scores are omitted. A random placeholder name is added.
    """
    # Random placeholder name
    placeholder_names = ["Alice Dupont", "Jean Martin", "Sophie Bernard", "Luc Durand"]
    nom_utilisateur = random.choice(placeholder_names)

    type_user = user_data.get("type", "Inconnu")

    profil = user_data.get("profil", {})
    situation = profil.get("situation_familiale", "Non renseigné")
    secteur = profil.get("secteur", "Non renseigné")
    profession = profil.get("profession", "Non renseigné")
    age = profil.get("age", "Non renseigné")

    produits_possedes = user_data.get("produits_possedes", [])
    produits_recommandes = user_data.get("produits_recommandes", [])

    # Format owned products
    produits_possedes_str = (
        ", ".join(produits_possedes) if produits_possedes else "Aucun"
    )

    # Format recommended products without scores
    produits_recommandes_str = (
        "\n".join([f"- {p['nom']}" for p in produits_recommandes])
        if produits_recommandes
        else "Aucun"
    )

    llm_text = f"""
Nom: {nom_utilisateur}
Type d'utilisateur: {type_user}
Profil:
  - Situation familiale: {situation}
  - Secteur: {secteur}
  - Profession: {profession}
  - Age: {age}
Produits possédés: {produits_possedes_str}
Produits recommandés:
{produits_recommandes_str}
"""
    return llm_text.strip()


def fetch_new_user_data() -> Dict[str, Any]:
    raw_user_data = fetch_new_user()
    clean_user_data = format_user_for_llm(raw_user_data)
    return {"data": raw_user_data, "user_data_str": clean_user_data}


def fetch_existing_user_data(user_id: int) -> Dict[str, Any]:
    raw_user_data = fetch_existing_user(user_id)
    clean_user_data = format_user_for_llm(raw_user_data)
    return clean_user_data


def query_rag(query: str) -> str:
    response = rag.retrieve_context(query, 3)
    return f"Retrieved RAG info: {response}"


def analyze_intent(user_message: str) -> Dict[str, Any]:
    msg = user_message.lower()
    return analyse_message(msg)


TEMPLATE_INITIAL_PITCH = """Explication de génération — Pitch initial

1. Données utilisées :
   Le message s’appuie sur les données disponibles relatives au client.

2. Choix du produit :
   Le produit mis en avant est {products}, retenu parce qu’il correspond aux besoins types identifiés à partir des données disponibles avec un score de confience de {confidence_score}.

3. Ton et angle :
   {system_prompt}

"""

TEMPLATE_RESPONDING = """Explication de génération — Réponse au message client

1. Intention détectée :
   L’agent a identifié : {intention} {intention_score}, ce qui oriente le niveau de détail et l’angle de réponse.

2. Éléments pris en compte :
   Produits/points évoqués dans la conversation : {products}.

3. Ton et angle :
   {system_prompt}

"""


def generate_explanation(
    msg_type: str, products, system_prompt, intention="", confidence_score=0
):
    if msg_type == "initial pitch":
        return (
            TEMPLATE_INITIAL_PITCH.replace("{products}", str(products))
            .replace("{system_prompt}", system_prompt)
            .replace("{confidence_score}", str(confidence_score))
        )
    elif msg_type == "respond":
        return (
            TEMPLATE_RESPONDING.replace("{intention}", intention)
            .replace("{products}", str(products))
            .replace("{system_prompt}", system_prompt)
            .replace("{intention_score}", confidence_score)
        )
