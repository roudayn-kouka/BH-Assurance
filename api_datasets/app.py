from typing import Any, Dict, Optional
import os
import math
import random
from datetime import datetime

import pandas as pd
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

# Import Tunisian names utility
from tunisian_names import (
    generate_tunisian_individual_name,
    generate_tunisian_company_name,
    generate_tunisian_phone_number,
    generate_tunisian_email,
    generate_tunisian_fiscal_id,
)

# ---------------- FastAPI app ----------------
app = FastAPI(
    title="Recommendation API",
    description="API pour recommander Produits, Garanties, Factures et Renouvellements (PM et PP)",
    version="4.5",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ----------------- Config fichiers -----------------
PM_FILE = "./catboost_pm.csv"
PP_FILE = "./catboost_pp_updated.csv"
FACTURE_PM_FILE = "./facture_pm.csv"
FACTURE_PP_FILE = "./reglement_facture_pp.csv"
RENOUV_PP_FILE = "./renouvellement_contrat_pp.csv"
RENOUV_PM_FILE = "./renouvellement_pm.csv"

RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

# ----------------- Helpers for aliasing -----------------


def to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


# ----------------- Schemas (snake_case internally, camelCase externally) -----------------


class Profile(BaseModel):
    # known / common fields (snake_case names)
    age: Optional[float] = None
    age_contract: Optional[float] = None
    candidate_garanties: Optional[str] = None
    current_guarantee: Optional[str] = None
    good_buyer_score_pct: Optional[float] = None
    good_buyer_pct: Optional[float] = None
    recommended_product: Optional[str] = None
    recommended_score: Optional[float] = None
    date_expiration: Optional[str] = None
    date_expiration_contract: Optional[str] = None
    nb_products: Optional[int] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class UserResponse(BaseModel):
    user_id: Any = Field(..., example="REF_pm_12345")
    user_type: str = Field(
        ...,
        example="personne_physique",
        description="Type d'utilisateur: personne_physique ou personne_morale",
    )
    endpoint_strategy: str = Field(
        ...,
        example="product_recommendation",
        description="Stratégie business de l'endpoint",
    )
    endpoint_key: str = Field(
        ...,
        example="pm_recommendation",
        description="Clé d'identification de l'endpoint",
    )
    profile: Profile
    recommended_action: str = Field(..., example="recommend_produit")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class ErrorResponse(BaseModel):
    message: str = Field(..., example="Aucun utilisateur trouvé")

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True


# ----------------- Utils -----------------


def clean_dict(d: dict) -> dict:
    """Replace NaN/NaT with None for JSON serialization."""
    out = {}
    for k, v in d.items():
        try:
            if isinstance(v, float) and (pd.isna(v) or math.isnan(v)):
                out[k] = None
            elif pd.isna(v):
                out[k] = None
            else:
                out[k] = v
        except Exception:
            out[k] = v
    return out


def load_csv_with_age(path: str, sep: str = ";") -> pd.DataFrame:
    """Load CSV and coerce Age / Age_Contrat numeric columns."""
    df = pd.read_csv(path, encoding="utf-8-sig", sep=sep)
    if "Age" in df.columns:
        df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
    if "Age_Contrat" in df.columns:
        df["Age_Contrat"] = pd.to_numeric(df["Age_Contrat"], errors="coerce")
    return df.where(pd.notnull(df), None)


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
        return s * 100
    return s


def safe_read_csv(path: str, sep: str = ","):
    if not os.path.exists(path):
        return None
    try:
        return pd.read_csv(path, encoding="utf-8-sig", sep=sep)
    except Exception:
        try:
            return pd.read_csv(path, encoding="utf-8-sig", sep=";")
        except Exception:
            return None


def map_profile_keys(raw: dict) -> dict:
    """
    Map CSV/raw keys to normalized snake_case keys used by Profile.
    Leaves unknown keys (that aren't REF* or nb_produits) and maps them to snake_case-ish keys where reasonable.
    """
    if raw is None:
        return {}

    clean = clean_dict(raw)
    out = {}

    # direct mappings (common variants)
    mappings = {
        "Age": "age",
        "Age_Contrat": "age_contract",
        "Candidate_Garanties": "candidate_garanties",
        "Lib_Garantie": "current_guarantee",
        "goodBuyer_score_pourcent": "good_buyer_score_pct",
        "good_buyer_pct": "good_buyer_pct",
        "recommended_product": "recommended_product",
        "recommended_score": "recommended_score",
        "Date_Expiration": "date_expiration",
        "DATE_EXPIRATION_CONTRAT": "date_expiration_contract",
        "nb_produits": "nb_products",
    }

    for k, v in clean.items():
        if k.startswith("REF"):
            # skip REF*
            continue
        if k in mappings:
            out[mappings[k]] = v
            continue

        # fallback: convert to snake_case-ish by replacing spaces and dots and upper->lower
        key = k.strip().replace(" ", "_").replace(".", "_")
        key = key.lower()
        out[key] = v

    return out


def add_tunisian_names_and_type(
    user_id: Any, profile: dict, endpoint_info: dict
) -> dict:
    """
    Add Tunisian names and user type information to profile based on endpoint type.

    Args:
        user_id: User identifier
        profile: Original profile data
        endpoint_info: Dict with 'strategy' and 'key' for endpoint identification

    Returns:
        Enhanced profile with Tunisian names and type information
    """
    enhanced_profile = profile.copy()

    # Determine user type based on user_id and endpoint
    if (
        str(user_id).startswith("REF_pm")
        or "pm" in endpoint_info.get("key", "").lower()
    ):
        user_type = "personne_morale"
        is_company = True
    elif (
        str(user_id).startswith("REF_pp")
        or "pp" in endpoint_info.get("key", "").lower()
    ):
        user_type = "personne_physique"
        is_company = False
    else:
        # Fallback: random choice
        is_company = random.choice([True, False])
        user_type = "personne_morale" if is_company else "personne_physique"

    if is_company:
        # Generate Tunisian company information
        company_info = generate_tunisian_company_name()
        email = generate_tunisian_email(company_info, True)
        phone = generate_tunisian_phone_number()
        fiscal_id = generate_tunisian_fiscal_id(True)

        # Add company-specific fields
        enhanced_profile.update(
            {
                "company_name": company_info["company_name"],
                "contact_person": company_info["contact_person"],
                "first_name": company_info["contact_first_name"],
                "last_name": company_info["contact_last_name"],
                "prenom": company_info["contact_first_name"],
                "nom": company_info["contact_last_name"],
                "email": email,
                "telephone": phone,
                "phone": phone,
                "matricule_fiscale": fiscal_id,
                "category": "Entreprise",
                "client_type": "company",
                "raison_sociale": company_info["company_name"],
                "siret": f"{random.randint(10000000000000, 99999999999999)}",
            }
        )
    else:
        # Generate Tunisian individual information
        person_info = generate_tunisian_individual_name()
        email = generate_tunisian_email(person_info, False)
        phone = generate_tunisian_phone_number()
        fiscal_id = generate_tunisian_fiscal_id(False)

        # Add individual-specific fields
        enhanced_profile.update(
            {
                "first_name": person_info["first_name"],
                "last_name": person_info["last_name"],
                "prenom": person_info["first_name"],
                "nom": person_info["last_name"],
                "full_name": person_info["full_name"],
                "email": email,
                "telephone": phone,
                "phone": phone,
                "matricule_fiscale": fiscal_id,
                "category": "Particulier",
                "client_type": "individual",
                # Generate realistic age if not present
                "age": enhanced_profile.get("age") or random.randint(25, 65),
            }
        )

    return enhanced_profile, user_type


def format_user_enhanced(
    user_id: Any,
    profile: dict,
    decision: str,
    endpoint_strategy: str,
    endpoint_key: str,
) -> dict:
    """
    Return the final normalized dict matching UserResponse model field names with enhanced Tunisian data:
    - user_id
    - user_type (personne_physique or personne_morale)
    - endpoint_strategy and endpoint_key
    - profile: mapped keys with Tunisian names
    - recommended_action
    """
    # Add Tunisian names and determine user type
    endpoint_info = {"strategy": endpoint_strategy, "key": endpoint_key}
    enhanced_profile, user_type = add_tunisian_names_and_type(
        user_id, profile, endpoint_info
    )

    # Map profile keys
    mapped_profile = map_profile_keys(enhanced_profile)

    # Post-process candidate_garanties: remove current_guarantee and limit to 3
    cand_key = "candidate_garanties"
    curr_key = "current_guarantee"
    if cand_key in mapped_profile:
        lib_g = (
            set(str(mapped_profile.get(curr_key, "")).split(";"))
            if mapped_profile.get(curr_key)
            else set()
        )
        candidates = [
            c
            for c in str(mapped_profile.get(cand_key, "")).split(";")
            if c and c not in lib_g
        ]
        if candidates:
            mapped_profile[cand_key] = ";".join(
                random.sample(candidates, min(3, len(candidates)))
            )
        else:
            mapped_profile[cand_key] = None

    # Ensure numeric scores normalized (to percent)
    if "good_buyer_score_pct" in mapped_profile:
        mapped_profile["good_buyer_score_pct"] = normalize_score_raw(
            mapped_profile["good_buyer_score_pct"]
        )
    if "good_buyer_pct" in mapped_profile:
        mapped_profile["good_buyer_pct"] = normalize_score_raw(
            mapped_profile["good_buyer_pct"]
        )
    if "recommended_score" in mapped_profile:
        mapped_profile["recommended_score"] = normalize_score_raw(
            mapped_profile["recommended_score"]
        )

    return {
        "user_id": user_id,
        "user_type": user_type,
        "endpoint_strategy": endpoint_strategy,
        "endpoint_key": endpoint_key,
        "profile": mapped_profile,
        "recommended_action": decision,
    }


def format_user(user_id: Any, profile: dict, decision: str) -> dict:
    """
    Legacy format_user function for backward compatibility.
    Uses enhanced version with default endpoint info.
    """
    # Determine endpoint info from legacy context
    if "pm" in str(user_id).lower():
        endpoint_strategy = "product_recommendation"
        endpoint_key = "pm_recommendation"
    else:
        endpoint_strategy = "product_recommendation"
        endpoint_key = "pp_recommendation"

    return format_user_enhanced(
        user_id, profile, decision, endpoint_strategy, endpoint_key
    )


# ----------------- ROUTES -----------------


@app.get(
    "/", include_in_schema=True, tags=["Meta"], summary="Health", response_model=dict
)
def root():
    return {"status": "ok"}


@app.get(
    "/recommend_pm/",
    include_in_schema=True,
    response_model=UserResponse,
    summary="Recommande un produit PM",
    description="Retourne la meilleure recommandation de produit pour les clients PM (meilleur goodBuyer_score_pourcent).",
    tags=["Produits"],
    responses={404: {"model": ErrorResponse}},
)
def recommend_pm():
    df_pm = safe_read_csv(PM_FILE, sep=",")
    if df_pm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fichier introuvable ou illisible: {PM_FILE}",
        )

    if "Candidate_Produit" not in df_pm.columns:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Colonne Candidate_Produit manquante dans PM file",
        )

    df_valid = df_pm[df_pm["Candidate_Produit"].notna()]
    if df_valid.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Aucun utilisateur trouvé"
        )

    sort_col = "goodBuyer_score_pourcent"
    if sort_col not in df_valid.columns:
        sort_col = next(
            (
                c
                for c in df_valid.columns
                if "good" in c.lower() and "score" in c.lower()
            ),
            df_valid.columns[0],
        )

    row = df_valid.sort_values(by=sort_col, ascending=False).head(1).iloc[0].to_dict()

    # derive decision same logic but using normalized percentage
    score = normalize_score_raw(row.get("goodBuyer_score_pourcent", row.get(sort_col)))
    decision = (
        "recommend_garantie"
        if (score is not None and score <= 50)
        else "recommend_produit"
    )

    result = format_user_enhanced(
        row.get("REF_pm", row.get("REF")),
        row,
        decision,
        "product_recommendation",
        "pm_recommendation",
    )
    pd.DataFrame([result]).to_json(
        f"{RESULTS_DIR}/recommend_pm.json",
        orient="records",
        force_ascii=False,
        indent=2,
    )
    # return will be serialized to camelCase (aliases) thanks to Pydantic config
    return UserResponse.model_validate(result)


@app.get(
    "/recommend_pp/",
    include_in_schema=True,
    response_model=UserResponse,
    summary="Recommande un produit PP",
    description="Retourne la meilleure recommandation de produit pour les clients PP (meilleur good_buyer_pct).",
    tags=["Produits"],
    responses={404: {"model": ErrorResponse}},
)
def recommend_pp():
    df_pp = safe_read_csv(PP_FILE, sep=";")
    if df_pp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fichier introuvable ou illisible: {PP_FILE}",
        )

    if "recommended_product" not in df_pp.columns:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Colonne recommended_product manquante dans PP file",
        )

    df_valid = df_pp[df_pp["recommended_product"].notna()]
    if df_valid.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Aucun utilisateur trouvé"
        )

    sort_col = "good_buyer_pct"
    if sort_col not in df_valid.columns:
        sort_col = next(
            (
                c
                for c in df_valid.columns
                if "good" in c.lower() and "buyer" in c.lower()
            ),
            df_valid.columns[0],
        )

    row = df_valid.sort_values(by=sort_col, ascending=False).head(1).iloc[0].to_dict()
    score = normalize_score_raw(row.get("recommended_score", None))
    goodbuyer = normalize_score_raw(row.get("good_buyer_pct", row.get(sort_col)))
    decision = (
        "recommend_garantie"
        if (
            (score is not None and score <= 50)
            or (goodbuyer is not None and goodbuyer <= 50)
        )
        else "recommend_produit"
    )

    result = format_user_enhanced(
        row.get("REF_pp", row.get("REF")),
        row,
        decision,
        "product_recommendation",
        "pp_recommendation",
    )
    pd.DataFrame([result]).to_json(
        f"{RESULTS_DIR}/recommend_pp.json",
        orient="records",
        force_ascii=False,
        indent=2,
    )
    return UserResponse.model_validate(result)


@app.get(
    "/facture_pm/",
    include_in_schema=True,
    response_model=UserResponse,
    summary="Facture PM",
    description="Retourne un enregistrement facture PM (première ligne du fichier).",
    tags=["Factures"],
    responses={404: {"model": ErrorResponse}},
)
def facture_pm():
    if not os.path.exists(FACTURE_PM_FILE):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fichier introuvable: {FACTURE_PM_FILE}",
        )

    df = load_csv_with_age(FACTURE_PM_FILE, sep=";")
    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Aucun utilisateur trouvé"
        )

    row = df.iloc[0].to_dict()
    result = format_user_enhanced(
        row.get("REF_pm", row.get("REF")),
        row,
        "paiement_facture",
        "payment_reminder",
        "pm_payment_reminder",
    )
    pd.DataFrame([result]).to_json(
        f"{RESULTS_DIR}/facture_pm.json", orient="records", force_ascii=False, indent=2
    )
    return UserResponse.model_validate(result)


@app.get(
    "/facture_pp/",
    include_in_schema=True,
    response_model=UserResponse,
    summary="Facture PP",
    description="Retourne un enregistrement facture PP (première ligne du fichier).",
    tags=["Factures"],
    responses={404: {"model": ErrorResponse}},
)
def facture_pp():
    if not os.path.exists(FACTURE_PP_FILE):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fichier introuvable: {FACTURE_PP_FILE}",
        )

    df = load_csv_with_age(FACTURE_PP_FILE, sep=";")
    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Aucun utilisateur trouvé"
        )

    row = df.iloc[0].to_dict()
    result = format_user_enhanced(
        row.get("REF_pp", row.get("REF")),
        row,
        "paiement_facture",
        "payment_reminder",
        "pp_payment_reminder",
    )
    pd.DataFrame([result]).to_json(
        f"{RESULTS_DIR}/facture_pp.json", orient="records", force_ascii=False, indent=2
    )
    return UserResponse.model_validate(result)


# ----------------- RENOUVELLEMENT PM -----------------


@app.get(
    "/renouvellement_pm/",
    include_in_schema=True,
    response_model=UserResponse,
    summary="Renouvellement PM",
    description="Sélectionne le premier contrat PM expirant à ou après 2025-09-01.",
    tags=["Renouvellements"],
    responses={404: {"model": ErrorResponse}},
)
def renouvellement_pm():
    if not os.path.exists(RENOUV_PM_FILE):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fichier introuvable: {RENOUV_PM_FILE}",
        )

    df = load_csv_with_age(RENOUV_PM_FILE, sep=";")
    if "DATE_EXPIRATION_CONTRAT" not in df.columns:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Colonne DATE_EXPIRATION_CONTRAT manquante",
        )

    df["DATE_EXPIRATION_CONTRAT"] = pd.to_datetime(
        df["DATE_EXPIRATION_CONTRAT"], errors="coerce"
    )
    df = df[df["DATE_EXPIRATION_CONTRAT"] >= datetime(2025, 9, 1)]

    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Aucun utilisateur trouvé"
        )

    df["DATE_EXPIRATION_CONTRAT"] = df["DATE_EXPIRATION_CONTRAT"].dt.strftime(
        "%Y-%m-%d"
    )
    row = df.iloc[0].to_dict()
    result = format_user_enhanced(
        row.get("REF_pm", row.get("REF")),
        row,
        "renouvellement_contrat",
        "contract_renewal",
        "pm_renewal",
    )
    return UserResponse.model_validate(result)


# ----------------- RENOUVELLEMENT PP -----------------


@app.get(
    "/renouvellement_pp/",
    include_in_schema=True,
    response_model=UserResponse,
    summary="Renouvellement PP",
    description="Sélectionne le premier contrat PP expirant à ou après 2025-09-01.",
    tags=["Renouvellements"],
    responses={404: {"model": ErrorResponse}},
)
def renouvellement_pp():
    if not os.path.exists(RENOUV_PP_FILE):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fichier introuvable: {RENOUV_PP_FILE}",
        )

    df = load_csv_with_age(RENOUV_PP_FILE, sep=";")
    if "Date_Expiration" not in df.columns:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Colonne Date_Expiration manquante",
        )

    df["Date_Expiration"] = pd.to_datetime(df["Date_Expiration"], errors="coerce")
    df = df[df["Date_Expiration"] >= datetime(2025, 9, 1)]

    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Aucun utilisateur trouvé"
        )

    df["Date_Expiration"] = df["Date_Expiration"].dt.strftime("%Y-%m-%d")
    row = df.iloc[0].to_dict()
    result = format_user_enhanced(
        row.get("REF_pp", row.get("REF")),
        row,
        "renouvellement_contrat",
        "contract_renewal",
        "pp_renewal",
    )
    return UserResponse.model_validate(result)
