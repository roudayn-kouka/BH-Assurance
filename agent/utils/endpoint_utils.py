"""
Endpoint-specific utility functions for handling different API endpoint strategies.
This module provides functions to convert endpoint data to string format and handle
different business strategies (product recommendation, payment reminder, contract renewal).
"""

from typing import Dict, Any, Optional
import json
# User type classification now handled by API directly


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


def convert_endpoint_data_to_string(data: Dict[str, Any]) -> str:
    """
    Convert API endpoint data to a formatted string representation based on the endpoint strategy.
    
    Args:
        data: Raw API response data containing user_id, profile, recommended_action, and metadata
        
    Returns:
        Formatted string representation of the data suitable for LLM processing
    """
    if not data:
        return "Aucune donnée disponible"
    
    endpoint_strategy = data.get("endpoint_strategy", "unknown")
    
    # Route to specific conversion function based on strategy
    if endpoint_strategy == "product_recommendation":
        return _convert_product_recommendation_data(data)
    elif endpoint_strategy == "payment_reminder":
        return _convert_payment_reminder_data(data)
    elif endpoint_strategy == "contract_renewal":
        return _convert_contract_renewal_data(data)
    else:
        # Fallback to general conversion
        return _convert_general_data(data)


def _convert_product_recommendation_data(data: Dict[str, Any]) -> str:
    """Convert product recommendation endpoint data to string format."""
    profile = data.get("profile", {})
    user_id = data.get("user_id", "Unknown")
    endpoint_key = data.get("endpoint_key", "unknown")
    user_type = data.get("user_type", "unknown")
    
    # Get user type from API response directly
    type_display = user_type.upper() if user_type != "unknown" else "INDÉTERMINÉ"
    
    # Get display name from profile
    if user_type == "personne_physique":
        display_name = (
            profile.get("full_name") or 
            f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip() or
            f"{profile.get('prenom', '')} {profile.get('nom', '')}".strip() or
            "Client particulier"
        )
        type_specific_info = f"Particulier: {display_name}"
    elif user_type == "personne_morale":
        display_name = (
            profile.get("company_name") or
            profile.get("raison_sociale") or
            "Entreprise"
        )
        type_specific_info = f"Entreprise: {display_name}"
    else:
        type_specific_info = "Type: Non déterminé"
    
    # Extract key information for product recommendation
    candidate_product = profile.get("candidate_produit", "Non spécifié")
    current_product = profile.get("lib_produit", "Non spécifié")
    sector = profile.get("lib_secteur_activite", "Non spécifié")
    activity = profile.get("lib_activite", "Non spécifié")
    category = profile.get("category", "Non spécifié")
    score = normalize_score_raw(profile.get("score", profile.get("good_buyer_score_pct")))
    nb_products = profile.get("nb_products", 0)
    
    # Build formatted string with user type information
    lines = [
        f"=== RECOMMANDATION PRODUIT ({endpoint_key.upper()}) ===",
        f"TYPE CLIENT: {type_display}",
        f"{type_specific_info}",
        f"ID Client: {user_id}",
        "",
        f"Secteur d'activité: {sector}",
        f"Activité: {activity}",
        f"Catégorie: {category}",
        f"Produit actuel: {current_product}",
        f"Produit recommandé: {candidate_product}",
        f"Score de confiance: {score}%" if score else "Score de confiance: Non disponible",
        f"Nombre de produits: {nb_products}",
        "",
        "Profil détaillé:"
    ]
    
    # Add profile details
    important_fields = [
        "age", "age_contract", "branche", "lib_sous_branche", 
        "good_buyer_score_pct", "good_buyer_pct", "email"
    ]
    
    for field in important_fields:
        value = profile.get(field)
        if value is not None and value != "":
            if "score" in field or "pct" in field:
                value = normalize_score_raw(value)
                lines.append(f"  - {field}: {value}%" if value else f"  - {field}: Non disponible")
            else:
                lines.append(f"  - {field}: {value}")
    
    return "\n".join(lines)


def _convert_payment_reminder_data(data: Dict[str, Any]) -> str:
    """Convert payment reminder endpoint data to string format."""
    profile = data.get("profile", {})
    user_id = data.get("user_id", "Unknown")
    endpoint_key = data.get("endpoint_key", "unknown")
    user_type = data.get("user_type", "unknown")
    
    # Get user type from API response directly
    type_display = user_type.upper() if user_type != "unknown" else "INDÉTERMINÉ"
    
    # Get display name from profile
    if user_type == "personne_physique":
        display_name = (
            profile.get("full_name") or 
            f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip() or
            f"{profile.get('prenom', '')} {profile.get('nom', '')}".strip() or
            "Client particulier"
        )
        type_specific_info = f"Particulier: {display_name}"
    elif user_type == "personne_morale":
        display_name = (
            profile.get("company_name") or
            profile.get("raison_sociale") or
            "Entreprise"
        )
        type_specific_info = f"Entreprise: {display_name}"
    else:
        type_specific_info = "Type: Non déterminé"
    
    # Extract key information for payment reminder
    statut_paiement = profile.get("statut_paiement", "Non spécifié")
    num_contrat = profile.get("num_contrat", "Non spécifié")
    lib_produit = profile.get("lib_produit", "Non spécifié")
    current_guarantee = profile.get("current_guarantee", "Non spécifié")
    candidate_garanties = profile.get("candidate_garanties", "Aucune")
    nb_sinistre = profile.get("nb_sinistre", 0)
    effet_contrat_date = profile.get("effet_contrat_date", "Non spécifié")
    
    # Build formatted string with user type information
    lines = [
        f"=== RAPPEL DE PAIEMENT ({endpoint_key.upper()}) ===",
        f"TYPE CLIENT: {type_display}",
        f"{type_specific_info}",
        f"ID Client: {user_id}",
        "",
        f"Numéro de contrat: {num_contrat}",
        f"Produit: {lib_produit}",
        f"Statut de paiement: {statut_paiement}",
        f"Date d'effet du contrat: {effet_contrat_date}",
        f"Nombre de sinistres: {nb_sinistre}",
        "",
        "Garanties actuelles:",
        f"  {current_guarantee}" if current_guarantee != "Non spécifié" else "  Aucune garantie spécifiée",
        "",
        "Garanties candidates (upselling):",
        f"  {candidate_garanties}" if candidate_garanties != "Aucune" else "  Aucune garantie candidate",
        "",
        "Profil détaillé:"
    ]
    
    # Add other profile details
    important_fields = [
        "matricule_fiscale", "lib_secteur_activite", "lib_activite", 
        "branche", "lib_sous_branche", "category", "nb_sinistres_2025"
    ]
    
    for field in important_fields:
        value = profile.get(field)
        if value is not None and value != "":
            lines.append(f"  - {field}: {value}")
    
    return "\n".join(lines)


def _convert_contract_renewal_data(data: Dict[str, Any]) -> str:
    """Convert contract renewal endpoint data to string format."""
    profile = data.get("profile", {})
    user_id = data.get("user_id", "Unknown")
    endpoint_key = data.get("endpoint_key", "unknown")
    user_type = data.get("user_type", "unknown")
    
    # Get user type from API response directly
    type_display = user_type.upper() if user_type != "unknown" else "INDÉTERMINÉ"
    
    # Get display name from profile
    if user_type == "personne_physique":
        display_name = (
            profile.get("full_name") or 
            f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip() or
            f"{profile.get('prenom', '')} {profile.get('nom', '')}".strip() or
            "Client particulier"
        )
        type_specific_info = f"Particulier: {display_name}"
    elif user_type == "personne_morale":
        display_name = (
            profile.get("company_name") or
            profile.get("raison_sociale") or
            "Entreprise"
        )
        type_specific_info = f"Entreprise: {display_name}"
    else:
        type_specific_info = "Type: Non déterminé"
    
    # Extract key information for contract renewal
    date_expiration_contract = profile.get("date_expiration_contract", "Non spécifié")
    age_contract = profile.get("age_contract", "Non spécifié")
    num_contrat = profile.get("num_contrat", "Non spécifié")
    lib_produit = profile.get("lib_produit", "Non spécifié")
    statut_paiement = profile.get("statut_paiement", "Non spécifié")
    current_guarantee = profile.get("current_guarantee", "Non spécifié")
    candidate_garanties = profile.get("candidate_garanties", "Aucune")
    candidate_product = profile.get("candidate_product", "Non spécifié")
    
    # Build formatted string with user type information
    lines = [
        f"=== RENOUVELLEMENT DE CONTRAT ({endpoint_key.upper()}) ===",
        f"TYPE CLIENT: {type_display}",
        f"{type_specific_info}",
        f"ID Client: {user_id}",
        "",
        f"Numéro de contrat: {num_contrat}",
        f"Produit: {lib_produit}",
        f"Date d'expiration: {date_expiration_contract}",
        f"Âge du contrat: {age_contract} ans" if age_contract != "Non spécifié" else f"Âge du contrat: {age_contract}",
        f"Statut de paiement: {statut_paiement}",
        "",
        "Garanties actuelles:",
        f"  {current_guarantee}" if current_guarantee != "Non spécifié" else "  Aucune garantie spécifiée",
        "",
        "Nouvelles garanties proposées:",
        f"  {candidate_garanties}" if candidate_garanties != "Aucune" else "  Aucune nouvelle garantie",
        "",
        "Produits candidats (cross-selling):",
        f"  {candidate_product}" if candidate_product != "Non spécifié" else "  Aucun produit candidat",
        "",
        "Profil détaillé:"
    ]
    
    # Add other profile details
    important_fields = [
        "matricule_fiscale", "lib_secteur_activite", "lib_activite", 
        "branche", "lib_sous_branche", "category", "effet_contrat_date",
        "nb_sinistre", "nb_sinistres_2025"
    ]
    
    for field in important_fields:
        value = profile.get(field)
        if value is not None and value != "":
            lines.append(f"  - {field}: {value}")
    
    return "\n".join(lines)


def _convert_general_data(data: Dict[str, Any]) -> str:
    """Fallback conversion for unknown endpoint strategies."""
    try:
        return f"=== DONNÉES UTILISATEUR (STRATÉGIE INCONNUE) ===\n\n{json.dumps(data, ensure_ascii=False, indent=2)}"
    except Exception:
        return f"=== DONNÉES UTILISATEUR (STRATÉGIE INCONNUE) ===\n\nDonnées non-sérialisables: {str(data)}"


def get_strategy_specific_prompts(endpoint_strategy: str) -> Dict[str, str]:
    """
    Get strategy-specific prompt modifications based on the endpoint strategy.
    
    Args:
        endpoint_strategy: The strategy type from the endpoint data
        
    Returns:
        Dict containing strategy-specific prompts and configurations
    """
    strategy_configs = {
        "product_recommendation": {
            "system_prompt_addition": (
                "CONTEXTE SPÉCIALISÉ: Recommandation de produit d'assurance. "
                "Votre objectif est de présenter le produit recommandé en mettant en avant "
                "sa pertinence par rapport au profil du client (secteur, activité, produits actuels). "
                "Utilisez le score de confiance pour renforcer votre argumentation."
            ),
            "max_sentences": 6,
            "focus_areas": ["produit_recommandé", "score_confiance", "secteur_activité", "bénéfices"]
        },
        
        "payment_reminder": {
            "system_prompt_addition": (
                "CONTEXTE SPÉCIALISÉ: Rappel de paiement de facture d'assurance. "
                "Votre approche doit être respectueuse mais ferme. Rappelez les obligations "
                "contractuelles tout en proposant des solutions (échéancier, aide). "
                "Profitez-en pour proposer des garanties additionnelles si approprié."
            ),
            "max_sentences": 5,
            "focus_areas": ["statut_paiement", "numéro_contrat", "garanties_additionnelles", "solutions_paiement"]
        },
        
        "contract_renewal": {
            "system_prompt_addition": (
                "CONTEXTE SPÉCIALISÉ: Renouvellement de contrat d'assurance. "
                "Mettez en avant la fidélité du client et les avantages du renouvellement. "
                "Proposez des améliorations de garanties ou de nouveaux produits complémentaires "
                "en fonction de l'évolution des besoins depuis la souscription initiale."
            ),
            "max_sentences": 6,
            "focus_areas": ["date_expiration", "fidélité", "nouvelles_garanties", "produits_complémentaires"]
        }
    }
    
    return strategy_configs.get(endpoint_strategy, {
        "system_prompt_addition": "",
        "max_sentences": 5,
        "focus_areas": []
    })


def get_product_name_from_endpoint_data(data: Dict[str, Any]) -> str:
    """
    Extract the most relevant product name from endpoint data for RAG queries based on business scenario.
    
    Args:
        data: API endpoint response data
        
    Returns:
        Product name string suitable for RAG queries
    """
    if not data or "profile" not in data:
        return "assurance générale"
    
    profile = data.get("profile", {})
    endpoint_strategy = data.get("endpoint_strategy", "")
    recommended_action = data.get("recommended_action", "")
    
    # Scenario-specific product extraction
    if endpoint_strategy == "product_recommendation":
        # For product recommendations: extract from recommended product field
        recommended_product = profile.get("recommended_product")
        if recommended_product and str(recommended_product).strip():
            return str(recommended_product).strip()
        
        # Fallback to candidate product fields
        candidate_product = profile.get("candidate_produit") or profile.get("candidate_product")
        if candidate_product and str(candidate_product).strip():
            return str(candidate_product).strip()
    
    elif recommended_action == "recommend_garantie" or "garantie" in recommended_action.lower():
        # For guarantee recommendations: take the first guarantee only
        candidate_garanties = profile.get("candidate_garanties")
        if candidate_garanties and str(candidate_garanties).strip():
            # Split by semicolon and take the first guarantee
            guarantees = str(candidate_garanties).split(';')
            first_guarantee = guarantees[0].strip()
            if first_guarantee:
                return first_guarantee
    
    elif endpoint_strategy in ["contract_renewal", "payment_reminder"]:
        # For contract renewal or bill reminders: use the product in the contract/bill
        lib_produit = profile.get("lib_produit")
        if lib_produit and str(lib_produit).strip():
            return str(lib_produit).strip()
        
        # Fallback to branch/sub-branch if lib_produit is not available
        lib_sous_branche = profile.get("lib_sous_branche")
        if lib_sous_branche and str(lib_sous_branche).strip():
            return str(lib_sous_branche).strip()
            
        branche = profile.get("branche")
        if branche and str(branche).strip():
            return str(branche).strip()
    
    # Generic fallback: try the most common product fields
    generic_candidates = [
        profile.get("lib_produit"),
        profile.get("recommended_product"),
        profile.get("candidate_produit"),
        profile.get("candidate_product"),
        profile.get("lib_sous_branche"),
        profile.get("branche")
    ]
    
    for candidate in generic_candidates:
        if candidate and str(candidate).strip():
            return str(candidate).strip()
    
    # Final fallback based on strategy
    strategy_fallbacks = {
        "product_recommendation": "assurance professionnelle",
        "payment_reminder": "assurance automobile", 
        "contract_renewal": "renouvellement contrat assurance"
    }
    
    return strategy_fallbacks.get(endpoint_strategy, "assurance générale")
