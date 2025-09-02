"""
User Type Classification Utility

This module provides functions to classify users as either 'personne_physique' (individual)
or 'personne_morale' (legal entity/company) and create appropriate data structures for each type.
"""

from typing import Dict, Any, Optional, Tuple
from enum import Enum
import re

class UserType(Enum):
    PERSONNE_PHYSIQUE = "personne_physique"
    PERSONNE_MORALE = "personne_morale"
    UNKNOWN = "unknown"

def classify_user_type(data: Dict[str, Any]) -> Tuple[UserType, float]:
    """
    Classify a user as personne_physique or personne_morale based on available data.
    
    Args:
        data: Raw API data containing profile information
        
    Returns:
        Tuple of (UserType, confidence_score) where confidence_score is 0.0-1.0
    """
    if not data:
        return UserType.UNKNOWN, 0.0
    
    profile = data.get("profile", {})
    endpoint_key = data.get("endpoint_key", "")
    
    # Initialize confidence counters
    pp_indicators = 0  # personne physique
    pm_indicators = 0  # personne morale
    total_checks = 0
    
    # 1. Check endpoint suffix (strongest indicator)
    total_checks += 2  # This gets double weight
    if endpoint_key.endswith("_pp"):
        pp_indicators += 2
    elif endpoint_key.endswith("_pm"):
        pm_indicators += 2
    
    # 2. Check for individual vs company identifiers
    total_checks += 1
    matricule_fiscale = profile.get("matricule_fiscale", "")
    if matricule_fiscale:
        # In Tunisia, company fiscal IDs typically start with letters
        if re.match(r'^[A-Za-z]', matricule_fiscale):
            pm_indicators += 1
        else:
            pp_indicators += 1
    
    # 3. Check for personal data fields
    personal_fields = ["age", "first_name", "prenom", "nom_famille"]
    company_fields = ["raison_sociale", "forme_juridique", "capital_social", "nb_employees"]
    
    for field in personal_fields:
        total_checks += 1
        if profile.get(field):
            pp_indicators += 1
    
    for field in company_fields:
        total_checks += 1
        if profile.get(field):
            pm_indicators += 1
    
    # 4. Check activity description patterns
    total_checks += 1
    lib_activite = profile.get("lib_activite", "").lower()
    lib_secteur = profile.get("lib_secteur_activite", "").lower()
    
    # Company activity indicators
    company_patterns = [
        r'\b(sarl|sa|sas|snc|eurl|sci)\b',  # Legal forms
        r'\b(entreprise|société|compagnie|groupe|holding)\b',  # Company terms
        r'\b(industrie|manufacture|production|commerce|distribution)\b'  # Business terms
    ]
    
    # Individual activity indicators  
    individual_patterns = [
        r'\b(particulier|individuel|personnel|privé)\b',
        r'\b(profession libérale|artisan|commerçant)\b'
    ]
    
    activity_text = f"{lib_activite} {lib_secteur}"
    
    for pattern in company_patterns:
        if re.search(pattern, activity_text):
            pm_indicators += 1
            break
    else:
        for pattern in individual_patterns:
            if re.search(pattern, activity_text):
                pp_indicators += 1
                break
    
    # 5. Check product types (some are more B2B vs B2C)
    total_checks += 1
    lib_produit = profile.get("lib_produit", "").lower()
    
    b2b_products = [
        "multirisques professionnelles",
        "responsabilite civile professionnelle", 
        "transport",
        "flotte automobile"
    ]
    
    b2c_products = [
        "automobile particulier",
        "habitation",
        "individuelle accident",
        "vie"
    ]
    
    for product in b2b_products:
        if product in lib_produit:
            pm_indicators += 1
            break
    else:
        for product in b2c_products:
            if product in lib_produit:
                pp_indicators += 1
                break
    
    # Calculate confidence and determine type
    if total_checks == 0:
        return UserType.UNKNOWN, 0.0
    
    pp_confidence = pp_indicators / total_checks
    pm_confidence = pm_indicators / total_checks
    
    if pp_confidence > pm_confidence:
        return UserType.PERSONNE_PHYSIQUE, pp_confidence
    elif pm_confidence > pp_confidence:
        return UserType.PERSONNE_MORALE, pm_confidence
    else:
        # In case of tie, use endpoint as tiebreaker
        if endpoint_key.endswith("_pp"):
            return UserType.PERSONNE_PHYSIQUE, 0.5
        elif endpoint_key.endswith("_pm"):
            return UserType.PERSONNE_MORALE, 0.5
        else:
            return UserType.UNKNOWN, 0.0

def extract_personne_physique_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and structure data for an individual person (personne physique).
    
    Args:
        data: Raw API data
        
    Returns:
        Structured data for personne physique
    """
    profile = data.get("profile", {})
    
    # Core identification
    user_id = data.get("user_id", "unknown")
    email = data.get("email") or profile.get("email")
    
    # Personal information
    first_name = (
        profile.get("first_name") or 
        profile.get("prenom") or 
        profile.get("nom", "").split()[0] if profile.get("nom") else "Inconnu"
    )
    
    last_name = (
        profile.get("last_name") or 
        profile.get("nom_famille") or
        profile.get("nom", "").split()[-1] if profile.get("nom") and len(profile.get("nom", "").split()) > 1 else "Inconnu"
    )
    
    age = profile.get("age")
    if age and isinstance(age, str) and age.replace(".", "").isdigit():
        age = int(float(age))
    
    # Contact information
    phone = (
        profile.get("telephone") or
        profile.get("phone") or
        profile.get("mobile")
    )
    
    address = profile.get("address") or profile.get("adresse")
    
    # Professional information
    profession = (
        profile.get("profession") or
        profile.get("lib_activite") or
        profile.get("job")
    )
    
    sector = profile.get("lib_secteur_activite")
    
    # Financial information
    income = profile.get("income") or profile.get("revenus")
    
    # Insurance information
    current_products = []
    if profile.get("lib_produit"):
        current_products.append({
            "name": profile.get("lib_produit"),
            "branch": profile.get("branche"),
            "sub_branch": profile.get("lib_sous_branche"),
            "contract_number": profile.get("num_contrat"),
            "contract_age": profile.get("age_contract"),
            "expiration_date": profile.get("date_expiration_contract"),
            "payment_status": profile.get("statut_paiement"),
            "premium": profile.get("prime"),
            "guarantees": profile.get("current_guarantee")
        })
    
    # Recommended products
    recommended_products = []
    if profile.get("candidate_produit"):
        recommended_products.append({
            "name": profile.get("candidate_produit"),
            "score": profile.get("score") or profile.get("good_buyer_score_pct"),
            "category": profile.get("category")
        })
    
    # Risk assessment
    claims_history = {
        "total_claims": profile.get("nb_sinistre", 0),
        "recent_claims": profile.get("nb_sinistres_2025", 0)
    }
    
    # Scores and ratings
    scores = {
        "recommendation_score": profile.get("score") or profile.get("good_buyer_score_pct"),
        "good_buyer_percentage": profile.get("good_buyer_pct"),
        "risk_assessment": _calculate_individual_risk_score(profile)
    }
    
    return {
        "user_type": UserType.PERSONNE_PHYSIQUE.value,
        "identification": {
            "user_id": user_id,
            "email": email,
            "matricule_fiscal": profile.get("matricule_fiscale")
        },
        "personal_info": {
            "first_name": first_name,
            "last_name": last_name,
            "age": age,
            "full_name": f"{first_name} {last_name}".strip()
        },
        "contact_info": {
            "phone": phone,
            "email": email,
            "address": address
        },
        "professional_info": {
            "profession": profession,
            "sector": sector,
            "income": income
        },
        "insurance_portfolio": {
            "current_products": current_products,
            "recommended_products": recommended_products,
            "claims_history": claims_history
        },
        "scores": scores,
        "raw_profile": profile  # Keep original for fallback
    }

def extract_personne_morale_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and structure data for a legal entity/company (personne morale).
    
    Args:
        data: Raw API data
        
    Returns:
        Structured data for personne morale
    """
    profile = data.get("profile", {})
    
    # Core identification
    user_id = data.get("user_id", "unknown")
    email = data.get("email") or profile.get("email")
    
    # Company information
    company_name = (
        profile.get("raison_sociale") or
        profile.get("nom_entreprise") or
        profile.get("nom") or
        f"Entreprise {user_id}"
    )
    
    legal_form = profile.get("forme_juridique") or profile.get("legal_form")
    
    # Registration information
    fiscal_id = profile.get("matricule_fiscale")
    registration_number = profile.get("numero_registre") or profile.get("reg_number")
    
    # Business information
    activity = profile.get("lib_activite")
    sector = profile.get("lib_secteur_activite") 
    industry_code = profile.get("code_activite") or profile.get("nace_code")
    
    # Size indicators
    employee_count = profile.get("nb_employees") or profile.get("effectif")
    if employee_count and isinstance(employee_count, str) and employee_count.isdigit():
        employee_count = int(employee_count)
    
    turnover = profile.get("chiffre_affaires") or profile.get("ca") or profile.get("revenue")
    capital = profile.get("capital_social") or profile.get("capital")
    
    # Contact information
    phone = (
        profile.get("telephone") or
        profile.get("phone") or
        profile.get("tel_entreprise")
    )
    
    address = (
        profile.get("adresse_siege") or
        profile.get("address") or
        profile.get("adresse")
    )
    
    # Representative/Contact person
    representative = {
        "name": profile.get("representant_legal") or profile.get("contact_person"),
        "title": profile.get("titre_representant") or profile.get("contact_title"),
        "phone": profile.get("tel_representant"),
        "email": profile.get("email_representant")
    }
    
    # Insurance information
    current_products = []
    if profile.get("lib_produit"):
        current_products.append({
            "name": profile.get("lib_produit"),
            "branch": profile.get("branche"),
            "sub_branch": profile.get("lib_sous_branche"),
            "contract_number": profile.get("num_contrat"),
            "contract_age": profile.get("age_contract"),
            "expiration_date": profile.get("date_expiration_contract"),
            "payment_status": profile.get("statut_paiement"),
            "premium": profile.get("prime"),
            "guarantees": profile.get("current_guarantee"),
            "candidate_guarantees": profile.get("candidate_garanties")
        })
    
    # Recommended products
    recommended_products = []
    if profile.get("candidate_produit"):
        recommended_products.append({
            "name": profile.get("candidate_produit"),
            "score": profile.get("score") or profile.get("good_buyer_score_pct"),
            "category": profile.get("category")
        })
    
    # Risk assessment
    claims_history = {
        "total_claims": profile.get("nb_sinistre", 0),
        "recent_claims": profile.get("nb_sinistres_2025", 0)
    }
    
    # Business scores
    scores = {
        "recommendation_score": profile.get("score") or profile.get("good_buyer_score_pct"),
        "good_buyer_percentage": profile.get("good_buyer_pct"),
        "risk_assessment": _calculate_company_risk_score(profile),
        "business_stability": _assess_business_stability(profile)
    }
    
    return {
        "user_type": UserType.PERSONNE_MORALE.value,
        "identification": {
            "user_id": user_id,
            "fiscal_id": fiscal_id,
            "registration_number": registration_number,
            "email": email
        },
        "company_info": {
            "company_name": company_name,
            "legal_form": legal_form,
            "activity": activity,
            "sector": sector,
            "industry_code": industry_code
        },
        "business_metrics": {
            "employee_count": employee_count,
            "turnover": turnover,
            "capital": capital,
            "establishment_date": profile.get("date_creation"),
            "size_category": _categorize_company_size(employee_count, turnover)
        },
        "contact_info": {
            "phone": phone,
            "email": email,
            "address": address,
            "representative": representative
        },
        "insurance_portfolio": {
            "current_products": current_products,
            "recommended_products": recommended_products,
            "claims_history": claims_history
        },
        "scores": scores,
        "raw_profile": profile  # Keep original for fallback
    }

def _calculate_individual_risk_score(profile: Dict[str, Any]) -> str:
    """Calculate risk assessment for individuals."""
    age = profile.get("age", 0)
    claims = profile.get("nb_sinistre", 0)
    
    if age < 25 or claims > 3:
        return "HIGH"
    elif age > 50 and claims <= 1:
        return "LOW"
    else:
        return "MEDIUM"

def _calculate_company_risk_score(profile: Dict[str, Any]) -> str:
    """Calculate risk assessment for companies."""
    claims = profile.get("nb_sinistre", 0)
    payment_status = profile.get("statut_paiement", "").lower()
    
    if claims > 5 or "impaye" in payment_status:
        return "HIGH"
    elif claims <= 1 and "paye" in payment_status:
        return "LOW"
    else:
        return "MEDIUM"

def _assess_business_stability(profile: Dict[str, Any]) -> str:
    """Assess business stability for companies."""
    contract_age = profile.get("age_contract", 0)
    employee_count = profile.get("nb_employees", 0)
    
    if isinstance(contract_age, (int, float)) and contract_age > 5:
        return "STABLE"
    elif isinstance(employee_count, (int, float)) and employee_count > 50:
        return "ESTABLISHED"
    else:
        return "DEVELOPING"

def _categorize_company_size(employee_count: Optional[int], turnover: Optional[float]) -> str:
    """Categorize company size based on employees and turnover."""
    if employee_count:
        if employee_count < 10:
            return "MICRO"
        elif employee_count < 50:
            return "SMALL"
        elif employee_count < 250:
            return "MEDIUM"
        else:
            return "LARGE"
    elif turnover:
        # Basic turnover-based classification (adjust thresholds as needed)
        if turnover < 100000:
            return "MICRO"
        elif turnover < 1000000:
            return "SMALL"
        elif turnover < 10000000:
            return "MEDIUM"
        else:
            return "LARGE"
    else:
        return "UNKNOWN"

def get_user_display_name(structured_data: Dict[str, Any]) -> str:
    """Get appropriate display name based on user type."""
    user_type = structured_data.get("user_type")
    
    if user_type == UserType.PERSONNE_PHYSIQUE.value:
        personal_info = structured_data.get("personal_info", {})
        return personal_info.get("full_name", "Client particulier")
    elif user_type == UserType.PERSONNE_MORALE.value:
        company_info = structured_data.get("company_info", {})
        return company_info.get("company_name", "Entreprise")
    else:
        return "Client"

def get_primary_email(structured_data: Dict[str, Any]) -> Optional[str]:
    """Get primary email address regardless of user type."""
    identification = structured_data.get("identification", {})
    contact_info = structured_data.get("contact_info", {})
    
    return identification.get("email") or contact_info.get("email")

def get_primary_phone(structured_data: Dict[str, Any]) -> Optional[str]:
    """Get primary phone number regardless of user type."""
    contact_info = structured_data.get("contact_info", {})
    return contact_info.get("phone")
