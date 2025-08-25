from typing import Dict, Any, List
from rag_model import rag
from intent_analysis import analyse_message

def fetch_user_data(user_id: str) -> Dict[str, Any]:
    """
    Simulate fetching user data from the database for BH Assurance.
    Returns structured information including decision and missing data.
    """
    # Simulation / placeholder data
    user_data = {
        "user_id": user_id,
        "name": "Entreprise Alpha",     # could be a person or company
        "type": "personne_morale",       # "personne_physique" or "personne_morale"
        "purchased_products": ["Assurance Auto"],
        "recommended_products": ["Assurance Santé Entreprise"],
        "bills_due": ["Assurance Auto – échéance 2025-09-01"],
        "contact_info": {"email": "mail@mail.com", "telephone": "12345678"},
        "sector": None,   # sector d’activité manquant => exemple: "industrie agroalimentaire"
        "age": 17,      # seulement pour personne physique
        "family_status": "divorcé",   # seulement pour personne_physique
    }

    # Determine decision logic
    if user_data["bills_due"]:
        decision = "pay_existing"
    elif None in (user_data["sector"], user_data["contact_info"].get("email")):
        decision = "collect_missing_info"
    elif user_data.get("recommended_products"):
        decision = "recommend_product"
    else:
        decision = "no_action"

    # Identify missing fields
    missing_fields: List[str] = []
    if user_data["type"] == "personne_morale":
        if not user_data["sector"]:
            missing_fields.append("secteur d'activité")
    if user_data["type"] == "personne_physique":
        if not user_data["age"]:
            missing_fields.append("âge")
        if not user_data["family_status"]:
            missing_fields.append("situation familiale")
    if not user_data["contact_info"].get("email"):
        missing_fields.append("adresse e-mail")
    if not user_data["contact_info"].get("telephone"):
        missing_fields.append("numéro de téléphone")

    # Augment with decision and missing info
    user_data["decision"] = decision
    user_data["missing_fields"] = missing_fields

    return user_data


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
