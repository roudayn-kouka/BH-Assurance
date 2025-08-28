from typing import Dict, Any, List
from rag_model import rag
from intent_analysis import analyse_message
import user_profile_conn
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
    produits_possedes_str = ", ".join(produits_possedes) if produits_possedes else "Aucun"
    
    # Format recommended products without scores
    produits_recommandes_str = "\n".join(
        [f"- {p['nom']}" for p in produits_recommandes]
    ) if produits_recommandes else "Aucun"
    
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
    raw_user_data = user_profile_conn.fetch_new_user()
    clean_user_data = format_user_for_llm(raw_user_data)
    return clean_user_data

def fetch_existing_user_data(user_id:int) -> Dict[str, Any]:
    raw_user_data = user_profile_conn.fetch_existing_user(user_id)
    clean_user_data = format_user_for_llm(raw_user_data)
    return clean_user_data


def query_rag(query: str) -> str:
    response = rag.retrieve_context(query,3)
    return f"Retrieved RAG info: {response}"

def analyze_intent(user_message: str) -> Dict[str, Any]:
    msg = user_message.lower()
    return analyse_message(msg)

import json
import re
import textwrap

def _extract_json_substring(s: str):
    """
    Try to extract a JSON object substring from a string.
    Returns the substring or None.
    """
    if not isinstance(s, str):
        return None
    # find first '{' and last '}' and try parse
    start = s.find('{')
    end = s.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = s[start:end+1]
    # try load directly
    try:
        json.loads(candidate)
        return candidate
    except Exception:
        # try to fix common issues: replace single quotes with double quotes (best-effort)
        fixed = candidate.replace("'", '"')
        try:
            json.loads(fixed)
            return fixed
        except Exception:
            return None

def pretty_print_agent_reply(reply):
    """
    Print the agent reply in a nice, structured way.
    - If reply is JSON or contains a JSON object, parse and pretty-print fields.
    - Otherwise, print the raw reply.
    """
    # If the agent already returned a dict
    if isinstance(reply, dict):
        resp = reply
    else:
        # If it's not a str, convert to str
        text = reply if isinstance(reply, str) else str(reply)

        # Try direct JSON parse
        try:
            resp = json.loads(text)
        except Exception:
            # Try to extract JSON substring
            substring = _extract_json_substring(text)
            if substring:
                try:
                    resp = json.loads(substring)
                except Exception:
                    resp = None
            else:
                resp = None

    sep = "-" * 60
    if resp and isinstance(resp, dict):
        intent = resp.get("intent", "unknown")
        message = resp.get("message", "")
        follow_ups = resp.get("follow_up_questions", []) or []

        print(sep)
        print(f"Intention détectée : {intent}")
        print()
        print("Message généré :")
        print(textwrap.fill(message, width=100))
        print()
        if follow_ups:
            print("Questions de relance suggérées :")
            for i, q in enumerate(follow_ups, 1):
                print(f"  {i}. {q}")
        else:
            print("Questions de relance suggérées : aucune")
        print(sep)
    else:
        # Fallback: print raw reply (truncated if very long)
        print(sep)
        print("Réponse (raw) :")
        print(textwrap.fill(str(reply), width=100))
        print(sep)
