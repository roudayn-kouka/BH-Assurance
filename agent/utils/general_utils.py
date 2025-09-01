from rag_model import rag
from intent_analysis import analyse_message
from utils.user_profile_conn import *
from utils.endpoint_utils import convert_endpoint_data_to_string, get_product_name_from_endpoint_data
import random

import re
import json
from typing import Any, Dict, List, Optional


def to_snake(s: str) -> str:
    """Convert camelCase / PascalCase / mixed to snake_case."""
    if not isinstance(s, str):
        return s
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", s)
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
    s3 = s2.replace("-", "_").replace(" ", "_")
    return re.sub(r"__+", "_", s3).lower()


def _to_list(value) -> List[str]:
    """Normalize a value to a list of non-empty strings."""
    if value is None:
        return []
    if isinstance(value, list):
        out = []
        for v in value:
            if isinstance(v, dict):
                # try common name keys inside dict
                s = (
                    v.get("nom")
                    or v.get("name")
                    or v.get("product_name")
                    or v.get("nom_produit")
                )
                if s:
                    out.append(str(s).strip())
            else:
                if v is not None:
                    s = str(v).strip()
                    if s:
                        out.append(s)
        return out
    if isinstance(value, (int, float)):
        return [str(value)]
    s = str(value).strip()
    if not s:
        return []
    parts = re.split(r"\s*[;,/\n]\s*", s)
    return [p for p in (p.strip() for p in parts) if p]


def normalize_score_raw(score_raw: Any) -> Optional[float]:
    """
    Normalize score to percentage [0..100].
    If score is in 0..1 range assume fraction and multiply by 100.
    If it's already >1 assume percentage.
    Return None on failure.
    """
    if score_raw is None:
        return None
    try:
        s = float(score_raw)
    except Exception:
        return None
    if 0 <= s <= 1:
        return round(s * 100, 2)
    return round(s, 2)


def _pick_first(d: Dict[str, Any], *keys, default=None):
    for k in keys:
        if k in d and d[k] not in (None, "", []):
            return d[k]
    return default


def format_user_for_llm(user_data: Dict[str, Any]) -> str:
    """
    Build a prompt-friendly French text block from user_data.
    - Accepts camelCase and snake_case.
    - Includes a friendly summary and then a complete dump of all profile fields and other top-level fields.
    - Normalizes keys to snake_case for the detailed sections.
    """
    # placeholder name
    placeholder_names = ["Alice Dupont", "Jean Martin", "Sophie Bernard", "Luc Durand"]
    nom_utilisateur = random.choice(placeholder_names)

    # Gather primary top-level identifiers (supporting camel/snake and legacy keys)
    user_id = _pick_first(
        user_data, "user_id", "userId", "REF", "ref", default="Unknown"
    )
    recommended_action = _pick_first(
        user_data,
        "recommended_action",
        "recommendedAction",
        "recommendedAction",
        "decision",
        "action",
        default="N/A",
    )
    type_user = _pick_first(
        user_data, "type", "user_type", "type_user", "userType", default="Inconnu"
    )

    # Profile object may be under 'profile' (new), 'profil' (fr), or missing (then consider top-level keys)
    profile_raw = _pick_first(user_data, "profile", "profil", default={}) or {}
    # if profile_raw is not a dict, keep it empty
    if not isinstance(profile_raw, dict):
        profile_raw = {}

    # Friendly picks (try multiple possible keys)
    def pick_profile_friendly(*variants, default="Non renseigné"):
        for k in variants:
            # check both in profile and top-level (some payloads may put fields at top)
            if k in profile_raw and profile_raw[k] not in (None, "", []):
                return profile_raw[k]
            if k in user_data and user_data[k] not in (None, "", []):
                return user_data[k]
        return default

    situation = pick_profile_friendly(
        "situation_familiale",
        "marital_status",
        "family_status",
        default="Non renseigné",
    )
    secteur = pick_profile_friendly(
        "secteur", "sector", "industry", default="Non renseigné"
    )
    profession = pick_profile_friendly(
        "profession", "job", "occupation", default="Non renseigné"
    )

    # age — check several keys in profile then top-level
    age = None
    for k in ("age", "age_contract", "age_contrat", "ageContract", "ageContract"):
        if k in profile_raw and profile_raw[k] not in (None, ""):
            age = profile_raw[k]
            break
        if k in user_data and user_data[k] not in (None, ""):
            age = user_data[k]
            break
    age = age if age not in (None, "") else "Non renseigné"

    # Owned products (many variants)
    owned_candidates = []
    for key in (
        "produits_possedes",
        "produits_possedés",
        "owned_products",
        "products_owned",
        "produits",
        "products",
        "ownedProducts",
        "produitsPossedes",
    ):
        if key in user_data and user_data[key]:
            owned_candidates = _to_list(user_data[key])
            break
    if not owned_candidates:
        for key in (
            "produits_possedes",
            "produits",
            "owned_products",
            "products",
            "ownedProducts",
        ):
            if key in profile_raw and profile_raw[key]:
                owned_candidates = _to_list(profile_raw[key])
                break
    produits_possedes_str = ", ".join(owned_candidates) if owned_candidates else "Aucun"

    # Recommended products/details: collect list of dicts or strings and include scores when present
    recommended_items: List[Dict[str, Any]] = []

    # helper to append items from various shapes
    def append_recommended_from(val):
        if val is None:
            return
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    # normalize keys inside dict to snake
                    normalized = {to_snake(str(k)): v for k, v in item.items()}
                    # derive name possibilities
                    name = (
                        normalized.get("nom")
                        or normalized.get("name")
                        or normalized.get("product_name")
                        or normalized.get("recommended_product")
                        or normalized.get("title")
                    )
                    score = (
                        normalized.get("recommended_score")
                        or normalized.get("score")
                        or normalized.get("good_buyer_score_pct")
                        or normalized.get("good_buyer_pct")
                    )
                    recommended_items.append(
                        {
                            "name": name or str(item),
                            "meta": normalized,
                            "score": normalize_score_raw(score),
                        }
                    )
                else:
                    # string or primitive
                    recommended_items.append(
                        {"name": str(item), "meta": {}, "score": None}
                    )
        elif isinstance(val, dict):
            normalized = {to_snake(str(k)): v for k, v in val.items()}
            name = (
                normalized.get("nom")
                or normalized.get("name")
                or normalized.get("product_name")
                or normalized.get("recommended_product")
                or normalized.get("title")
            )
            score = (
                normalized.get("recommended_score")
                or normalized.get("score")
                or normalized.get("good_buyer_score_pct")
                or normalized.get("good_buyer_pct")
            )
            recommended_items.append(
                {
                    "name": name or json.dumps(val, ensure_ascii=False),
                    "meta": normalized,
                    "score": normalize_score_raw(score),
                }
            )
        else:
            # primitive string
            recommended_items.append({"name": str(val), "meta": {}, "score": None})

    # Try various candidate locations
    # 1. profile fields
    for key in (
        "recommended_product",
        "recommended_products",
        "produits_recommandes",
        "produits_recommandés",
    ):
        if key in profile_raw and profile_raw[key]:
            append_recommended_from(profile_raw[key])
    # 2. top-level fields
    for key in (
        "recommended_products",
        "recommendedProduct",
        "produits_recommandes",
        "produits_recommandés",
    ):
        if key in user_data and user_data[key]:
            append_recommended_from(user_data[key])
    # 3. candidate_garanties in profile (semicolon-separated or list)
    for key in ("candidate_garanties", "candidateGaranties", "candidate_garanties"):
        if key in profile_raw and profile_raw[key]:
            append_recommended_from(profile_raw[key])
    # 4. fallback: any field that looks like candidate / recommended keys
    for k, v in profile_raw.items():
        if (
            any(
                tok in k.lower()
                for tok in ("candidate", "recommend", "produit", "garantie")
            )
            and v
        ):
            append_recommended_from(v)

    # Deduplicate recommended items by name preserving order
    seen = set()
    rec_clean: List[Dict[str, Any]] = []
    for it in recommended_items:
        name = it.get("name")
        if not name:
            continue
        if name not in seen:
            seen.add(name)
            rec_clean.append(it)

    # Build recommended products string with scores/meta
    if rec_clean:
        rec_lines = []
        for it in rec_clean:
            line = f"- {it['name']}"
            if it.get("score") is not None:
                line += f" (score: {it['score']}%)"
            # include important meta keys (excluding very large nested objects)
            meta = {
                k: v
                for k, v in it.get("meta", {}).items()
                if k not in ("description", "extra", "additionalProp1")
            }
            if meta:
                meta_str = ", ".join(f"{k}={v}" for k, v in meta.items())
                line += f" [{meta_str}]"
            rec_lines.append(line)
        produits_recommandes_str = "\n".join(rec_lines)
    else:
        produits_recommandes_str = "Aucun"

    # Build a full normalized profile dict (snake_case keys)
    normalized_profile = {}
    for k, v in profile_raw.items():
        nk = to_snake(k)
        # normalize nested dicts/lists for readability
        if isinstance(v, dict):
            # flatten first-level dict to json string (short)
            try:
                normalized_profile[nk] = json.dumps(v, ensure_ascii=False)
            except Exception:
                normalized_profile[nk] = str(v)
        elif isinstance(v, list):
            normalized_profile[nk] = _to_list(v)
        else:
            # if key looks like a score, normalize numeric
            lowk = nk.lower()
            if any(
                tok in lowk
                for tok in ("score", "pct", "percent", "pourcent", "good_buyer")
            ):
                normalized_profile[nk] = normalize_score_raw(v)
            else:
                normalized_profile[nk] = v

    # Collect any top-level fields that are not 'profile' or already used
    other_top_level = {}
    for k, v in user_data.items():
        if k in ("profile", "profil"):
            continue
        if k in (
            "user_id",
            "userId",
            "userId".lower(),
            "recommended_action",
            "recommendedAction",
            "decision",
            "action",
            "type",
            "user_type",
            "type_user",
        ):
            continue
        # keep the rest
        other_top_level[to_snake(k)] = v

    # Now produce the final multi-part text
    parts = []

    # Header summary
    parts.append(f"Nom: {nom_utilisateur}")
    parts.append(f"user_id: {user_id}")
    parts.append(f"type_user: {type_user}")
    parts.append(f"recommended_action: {recommended_action}")
    parts.append("")  # blank line

    # Friendly profile summary
    parts.append("Profil (résumé):")
    parts.append(f"  - situation_familiale: {situation}")
    parts.append(f"  - secteur: {secteur}")
    parts.append(f"  - profession: {profession}")
    parts.append(f"  - age: {age}")
    parts.append("")  # blank

    # Owned products
    parts.append(f"Produits possédés: {produits_possedes_str}")
    parts.append("")  # blank

    # Recommended products
    parts.append("Produits recommandés:")
    parts.append(produits_recommandes_str)
    parts.append("")  # blank

    # Full profile details (snake_case)
    parts.append("Profil (détails complets, clés normalisées en snake_case):")
    if normalized_profile:
        for k, v in normalized_profile.items():
            # present lists as comma-separated
            if isinstance(v, list):
                parts.append(f"  - {k}: {', '.join(map(str, v)) if v else '[]'}")
            else:
                parts.append(f"  - {k}: {v}")
    else:
        parts.append("  - (vide)")

    parts.append("")  # blank

    # Other top-level fields
    parts.append("Autres champs top-level (normalisés):")
    if other_top_level:
        for k, v in other_top_level.items():
            try:
                # pretty print JSON for complex values
                if isinstance(v, (dict, list)):
                    pretty = json.dumps(v, ensure_ascii=False)
                else:
                    pretty = v
            except Exception:
                pretty = str(v)
            parts.append(f"  - {k}: {pretty}")
    else:
        parts.append("  - (aucun)")

    # Raw JSON (compact) at the end for completeness/debugging
    try:
        raw_json = json.dumps(user_data, ensure_ascii=False)
        parts.append("")  # blank
        parts.append("Données brutes (JSON compact):")
        parts.append(raw_json)
    except Exception:
        # if json fails, skip
        pass

    llm_text = "\n".join(parts).strip()
    return llm_text


def fetch_new_user_data() -> Dict[str, Any]:
    raw_user_data = fetch_new_user()
    if not raw_user_data:
        return {"data": None, "user_data_str": "Aucune donnée utilisateur disponible"}
    
    # Use endpoint-specific conversion if available, otherwise fallback to general format
    if "endpoint_strategy" in raw_user_data:
        clean_user_data = convert_endpoint_data_to_string(raw_user_data)
    else:
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
