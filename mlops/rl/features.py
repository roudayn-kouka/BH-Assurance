"""
State schema v1: raw features built from an api_datasets profile, and their stable vector form.

The same functions are used by the simulator, the policy-service and the agent so a model
is always served with exactly the preprocessing it was trained with.
"""

from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

FEATURE_SCHEMA = "v1"

RAW_FEATURES_V1 = [
    "age", "contract_age", "good_buyer_score", "recommended_score", "nb_products",
    "has_active_contract", "days_to_expiry", "unpaid_invoice", "nb_claims",
    "contacts_30d", "days_since_last_contact", "is_company",
]

VECTOR_FEATURES_V1 = [
    "age", "age_missing", "contract_age", "good_buyer_score", "good_buyer_missing",
    "recommended_score", "recommended_missing", "nb_products", "has_active_contract",
    "days_to_expiry", "expiry_missing", "unpaid_invoice", "nb_claims", "contacts_30d",
    "days_since_last_contact", "is_company",
]
OBS_DIM = len(VECTOR_FEATURES_V1)


def _first(d: Dict[str, Any], *keys) -> Any:
    for k in keys:
        v = d.get(k)
        if v not in (None, "", "nan"):
            return v
    return None


def _num(v: Any) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if np.isnan(f) else f


def _score_pct(v: Any) -> Optional[float]:
    f = _num(v)
    if f is None:
        return None
    return f * 100 if 0 <= f <= 1 else f


def _days_until(v: Any, today: date) -> Optional[float]:
    if not v:
        return None
    try:
        d = datetime.fromisoformat(str(v)[:10]).date()
    except ValueError:
        return None
    return float((d - today).days)


def profile_to_features(
    profile: Dict[str, Any], context: Optional[Dict[str, Any]] = None,
    today: Optional[date] = None,
) -> Dict[str, Optional[float]]:
    """Map an api_datasets profile (snake_case keys from map_profile_keys) to raw features v1."""
    p = {str(k).lower(): v for k, v in (profile or {}).items()}
    ctx = context or {}
    today = today or date.today()

    age = _num(_first(p, "age"))
    expiry = _days_until(_first(p, "date_expiration_contract", "date_expiration"), today)
    contract_age = _num(_first(p, "age_contract", "age_contrat"))
    statut = str(_first(p, "statut_paiement") or "").lower()
    company = (
        str(_first(p, "client_type") or "") == "company"
        or str(_first(p, "user_type") or ctx.get("user_type") or "") == "personne_morale"
        or str(_first(p, "category") or "") == "Entreprise"
    )

    return {
        "age": age if age and age > 0 else None,  # the CSVs use 0 for unknown age
        "contract_age": contract_age,
        "good_buyer_score": _score_pct(_first(
            p, "good_buyer_score_pct", "good_buyer_pct", "goodbuyer_score_pourcent", "score")),
        "recommended_score": _score_pct(_first(p, "recommended_score")),
        "nb_products": _num(_first(p, "nb_products", "nb_produits")) or 0.0,
        "has_active_contract": float(bool(
            _first(p, "num_contrat") or expiry is not None or contract_age is not None)),
        "days_to_expiry": expiry,
        "unpaid_invoice": float("non" in statut or "impay" in statut),
        "nb_claims": _num(_first(p, "nb_sinistres_2025", "nb_sinistres")) or 0.0,
        "contacts_30d": float(ctx.get("contacts_30d", 0)),
        "days_since_last_contact": float(ctx.get("days_since_last_contact", 365)),
        "is_company": float(company),
    }


def vectorize(f: Dict[str, Optional[float]]) -> np.ndarray:
    def val(name, scale, default=0.0):
        v = f.get(name)
        return default if v is None else float(v) / scale

    expiry = f.get("days_to_expiry")
    return np.array([
        val("age", 100), float(f.get("age") is None),
        min(val("contract_age", 20), 1.0),
        val("good_buyer_score", 100, 0.5), float(f.get("good_buyer_score") is None),
        val("recommended_score", 100, 0.5), float(f.get("recommended_score") is None),
        min(val("nb_products", 10), 1.0),
        val("has_active_contract", 1),
        0.0 if expiry is None else float(np.clip(expiry, -365, 365)) / 365,
        float(expiry is None),
        val("unpaid_invoice", 1),
        min(val("nb_claims", 100), 1.0),
        min(val("contacts_30d", 5), 1.0),
        min(val("days_since_last_contact", 365), 1.0),
        val("is_company", 1),
    ], dtype=np.float32)


def preprocessor_spec() -> Dict[str, Any]:
    return {"feature_schema": FEATURE_SCHEMA, "raw_features": RAW_FEATURES_V1,
            "vector_features": VECTOR_FEATURES_V1}


def load_profile_pool(csv_specs: Iterable[Dict], base) -> List[Dict[str, Optional[float]]]:
    """Profiles from the CatBoost/business CSVs, used to calibrate the simulator population."""
    import pandas as pd

    pool = []
    for spec in csv_specs:
        path = base / spec["path"]
        if not path.exists():
            continue
        df = pd.read_csv(path, sep=spec.get("sep", ","), encoding="utf-8-sig")
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        is_pm = "_pm" in path.stem or path.stem.endswith("pm")
        for row in df.to_dict("records"):
            row["user_type"] = "personne_morale" if is_pm else "personne_physique"
            pool.append(profile_to_features(row))
    return pool
