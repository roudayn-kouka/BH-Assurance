# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Union
import pandas as pd
import random
import os

app = FastAPI(
    title="User Recommendation API",
    version="1.0",
    docs_url="/",     # Swagger UI at root
    redoc_url=None,
    openapi_url="/openapi.json"
)

# ---------- Config: CSV paths (adjust if needed) ----------
PP_FILE = os.getenv("PP_FILE", "./catboost_produits_pp_ranked_final_clean.csv")
PM_FILE = os.getenv("PM_FILE", "./catboost_produits_pm_ranked_final_clean.csv")

# ---------- Load CSVs ----------
try:
    df_pp = pd.read_csv(PP_FILE, sep=";", encoding="utf-8-sig")
except FileNotFoundError:
    df_pp = pd.DataFrame()

try:
    df_pm = pd.read_csv(PM_FILE, sep=";", encoding="utf-8-sig")
except FileNotFoundError:
    df_pm = pd.DataFrame()

# ---------- Pydantic models (allow missing values) ----------
class CandidateProduct(BaseModel):
    Candidate_Produit: Optional[str] = None
    score: Optional[float] = None

class CandidateProductPM(BaseModel):
    candidate_product: Optional[str] = None
    score: Optional[float] = None

class UserPP(BaseModel):
    user_id: int
    source: str
    profile: Dict[str, Optional[str]]
    all_products: List[str]
    top3_candidates: List[CandidateProduct]

class UserPM(BaseModel):
    user_id: int
    source: str
    profile: Dict[str, Optional[str]]
    all_products: List[str]
    top3_candidates: List[CandidateProductPM]

# ---------- Helpers ----------
def sanitize_value(v) -> Optional[str]:
    if pd.isna(v):
        return None
    return str(v).strip()

def build_all_products(df_subset: pd.DataFrame, product_col: str) -> List[str]:
    if product_col not in df_subset.columns:
        return []
    vals = df_subset[product_col].dropna().unique().tolist()
    return [str(v) for v in vals if not pd.isna(v)]

def build_recommended_products(filtered_df: pd.DataFrame, product_col: str, score_col: str) -> List[Dict]:
    records = []
    top_rows = filtered_df.sort_values(score_col, ascending=False).head(3)
    for _, r in top_rows.iterrows():
        records.append({
            "nom": sanitize_value(r.get(product_col)),
            "score": None if pd.isna(r.get(score_col)) else float(r.get(score_col))
        })
    return records

def build_profile_pp(series: pd.Series) -> Dict[str, Optional[str]]:
    mapping = {
        "situation_familiale": series.get("Situation_Familiale"),
        "secteur": series.get("Lib_Secteur_Activite"),
        "profession": series.get("Lib_Profession"),
        "age": series.get("Age"),
    }
    return {k: sanitize_value(v) for k, v in mapping.items()}

def build_profile_pm(series: pd.Series) -> Dict[str, Optional[str]]:
    mapping = {
        "secteur": series.get("LIB_SECTEUR_ACTIVITE"),
        "activite": series.get("LIB_ACTIVITE"),
        "produit": series.get("LIB_PRODUIT"),
    }
    return {k: sanitize_value(v) for k, v in mapping.items()}

def choose_dataset() -> Optional[str]:
    options = []
    if "REF_pp" in df_pp.columns and not df_pp.empty:
        options.append("pp")
    if "REF_pm" in df_pm.columns and not df_pm.empty:
        options.append("pm")
    if not options:
        return None
    return random.choice(options)

# ---------- Random user endpoint ----------
@app.get("/user/random")
def get_random_user():
    dataset = choose_dataset()
    if not dataset:
        raise HTTPException(status_code=404, detail="Aucun utilisateur disponible dans les datasets")

    try:
        if dataset == "pp":
            user_row = df_pp.sample(1).iloc[0]
            user_id = int(user_row["REF_pp"])
            profile = build_profile_pp(user_row)
            user_subset = df_pp[df_pp["REF_pp"] == user_id]
            owned_products = build_all_products(user_subset, "Lib_Produit")
            filtered = user_subset[user_subset["Candidate_Produit"] != user_subset["Lib_Produit"]]
            recommended = build_recommended_products(filtered, "Candidate_Produit", "score")

        else:  # pm
            user_row = df_pm.sample(1).iloc[0]
            user_id = int(user_row["REF_pm"])
            profile = build_profile_pm(user_row)
            user_subset = df_pm[df_pm["REF_pm"] == user_id]
            owned_products = build_all_products(user_subset, "LIB_PRODUIT")
            filtered = user_subset[user_subset["candidate_product"] != user_subset["LIB_PRODUIT"]]
            recommended = build_recommended_products(filtered, "candidate_product", "score")
        source_name = "Personne Physique" if dataset == "pp" else "Personne Morale"

        return {
            "type": source_name,
            "profil": profile,
            "produits_possedes": owned_products,
            "produits_recommandes": recommended
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
from fastapi import HTTPException

@app.get("/user/id/{user_id}")
def get_user_by_id(user_id: int):
    """
    Get a user by user_id from PP or PM dataset.
    """
    try:
        # Check in PP dataset
        if "REF_pp" in df_pp.columns:
            user_subset = df_pp[df_pp["REF_pp"] == user_id]
            if not user_subset.empty:
                user_row = user_subset.iloc[0]
                profile = build_profile_pp(user_row)
                owned_products = build_all_products(user_subset, "Lib_Produit")
                filtered = user_subset[user_subset["Candidate_Produit"] != user_subset["Lib_Produit"]]
                recommended = build_recommended_products(filtered, "Candidate_Produit", "score")
                source_name = "Personne Physique"

                return {
                    "type": source_name,
                    "profil": profile,
                    "produits_possedes": owned_products,
                    "produits_recommandes": recommended
                }

        # Check in PM dataset
        if "REF_pm" in df_pm.columns:
            user_subset = df_pm[df_pm["REF_pm"] == user_id]
            if not user_subset.empty:
                user_row = user_subset.iloc[0]
                profile = build_profile_pm(user_row)
                owned_products = build_all_products(user_subset, "LIB_PRODUIT")
                filtered = user_subset[user_subset["candidate_product"] != user_subset["LIB_PRODUIT"]]
                recommended = build_recommended_products(filtered, "candidate_product", "score")
                source_name = "Personne Morale"

                return {
                    "type": source_name,
                    "profil": profile,
                    "produits_possedes": owned_products,
                    "produits_recommandes": recommended
                }

        # If user_id not found in either dataset
        raise HTTPException(status_code=404, detail=f"Utilisateur avec ID {user_id} introuvable")

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ---------- Optional: run with `python main.py` ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8083)), reload=True, log_level="info")
