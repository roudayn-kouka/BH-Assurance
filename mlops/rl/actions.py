"""
Action schema v1, business action mask and the rule baseline.

The mask encodes business/compliance rules and is enforced outside the model: the policy
only chooses among allowed actions, and the policy-service re-checks the mask on every call.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np

ACTION_SCHEMA = "v1"
ACTIONS_V1 = [
    "wait",
    "recommend_product",
    "recommend_guarantee",
    "contract_renewal",
    "payment_reminder",
]
ACTION_INDEX = {a: i for i, a in enumerate(ACTIONS_V1)}

# How the agent turns an action into its existing prompts (endpoint_strategy / recommended_action)
ACTION_TO_STRATEGY = {
    "wait": None,
    "recommend_product": ("product_recommendation", "recommend_produit"),
    "recommend_guarantee": ("product_recommendation", "recommend_garantie"),
    "contract_renewal": ("contract_renewal", "renouvellement_contrat"),
    "payment_reminder": ("payment_reminder", "paiement_facture"),
}
STRATEGY_TO_ACTION = {
    ("product_recommendation", "recommend_produit"): "recommend_product",
    ("product_recommendation", "recommend_garantie"): "recommend_guarantee",
    ("contract_renewal", None): "contract_renewal",
    ("payment_reminder", None): "payment_reminder",
}

DEFAULT_RULES = {"max_contacts_30d": 3, "renewal_window_days": [-30, 60]}


def legacy_action(endpoint_strategy: Optional[str], recommended_action: Optional[str]) -> str:
    """Action the legacy flow (api_datasets endpoint + threshold rule) would take."""
    return (
        STRATEGY_TO_ACTION.get((endpoint_strategy, recommended_action))
        or STRATEGY_TO_ACTION.get((endpoint_strategy, None))
        or "recommend_product"
    )


def in_renewal_window(f: Dict, rules: Dict) -> bool:
    lo, hi = rules.get("renewal_window_days", DEFAULT_RULES["renewal_window_days"])
    d = f.get("days_to_expiry")
    return bool(f.get("has_active_contract")) and d is not None and lo <= d <= hi


def business_mask(f: Dict, rules: Optional[Dict] = None) -> np.ndarray:
    rules = {**DEFAULT_RULES, **(rules or {})}
    mask = np.zeros(len(ACTIONS_V1), dtype=bool)
    mask[ACTION_INDEX["wait"]] = True
    if (f.get("contacts_30d") or 0) >= rules["max_contacts_30d"]:
        return mask  # contact fatigue: nothing but wait

    unpaid = bool(f.get("unpaid_invoice"))
    scored = f.get("good_buyer_score") is not None or f.get("recommended_score") is not None
    # no upsell to a customer with an unpaid invoice
    mask[ACTION_INDEX["recommend_product"]] = scored and not unpaid
    mask[ACTION_INDEX["recommend_guarantee"]] = bool(f.get("has_active_contract")) and not unpaid
    mask[ACTION_INDEX["contract_renewal"]] = in_renewal_window(f, rules)
    mask[ACTION_INDEX["payment_reminder"]] = unpaid
    return mask


def restrict(mask: np.ndarray, allowed: Optional[List[str]]) -> np.ndarray:
    """Intersect the business mask with a caller restriction; `wait` always stays allowed."""
    if allowed is None:
        return mask
    out = mask.copy()
    for a, i in ACTION_INDEX.items():
        if a not in allowed and a != "wait":
            out[i] = False
    return out


def reason_codes(f: Dict, action: str, rules: Optional[Dict] = None) -> List[str]:
    rules = {**DEFAULT_RULES, **(rules or {})}
    codes = []
    gb = f.get("good_buyer_score")
    if gb is not None:
        codes.append("high_propensity" if gb > 50 else "low_propensity")
    if in_renewal_window(f, rules):
        codes.append("renewal_window")
    if f.get("unpaid_invoice"):
        codes.append("unpaid_invoice")
    if (f.get("contacts_30d") or 0) >= rules["max_contacts_30d"]:
        codes.append("contact_fatigue")
    elif (f.get("contacts_30d") or 0) >= 1:
        codes.append("recent_contact")
    return codes


def rules_action(f: Dict, mask: np.ndarray) -> Tuple[int, List[str]]:
    """
    Rule baseline = today's business logic: unpaid → reminder, renewal window → renewal,
    otherwise api_datasets' threshold (score <= 50 → guarantee, else product).
    """
    gb = f.get("good_buyer_score")
    if gb is None:
        gb = f.get("recommended_score")
    preference = ["payment_reminder", "contract_renewal"]
    if gb is not None and gb <= 50:
        preference += ["recommend_guarantee", "recommend_product"]
    else:
        preference += ["recommend_product", "recommend_guarantee"]
    for name in preference + ["wait"]:
        if mask[ACTION_INDEX[name]]:
            return ACTION_INDEX[name], ["rules_baseline"]
    return ACTION_INDEX["wait"], ["rules_baseline"]
