"""
Gymnasium simulator for next-best-action.

One episode = one customer over `horizon_steps` weeks. Conversion probabilities are
explicit, documented hypotheses (mlops/configs/rl.yaml) scaled by the customer's CatBoost
scores, and degraded by contact fatigue. Results are simulated, not observed conversions.

`action_masks()` exposes the business mask for sb3-contrib's MaskablePPO; an action outside
the mask is penalised and counted in info["invalid_action"].
"""

from typing import Dict, List, Optional

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .actions import ACTIONS_V1, business_mask, in_renewal_window
from .features import OBS_DIM, vectorize


class NextBestActionEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        sim: Dict,
        rules: Optional[Dict] = None,
        profile_pool: Optional[List[Dict]] = None,
        conversion_multiplier: Optional[float] = None,
    ):
        super().__init__()
        self.sim = sim
        self.rules = rules or {}
        self.pool = profile_pool or []
        self.multiplier = (
            conversion_multiplier if conversion_multiplier is not None
            else sim.get("conversion_multiplier", 1.0)
        )
        self.action_space = spaces.Discrete(len(ACTIONS_V1))
        self.observation_space = spaces.Box(-1.0, 1.0, shape=(OBS_DIM,), dtype=np.float32)
        self.f: Dict = {}

    # ---------------- customer generation ----------------

    def _synthetic_customer(self) -> Dict:
        rng, syn = self.np_random, self.sim.get("synthetic", {})
        company = rng.random() < syn.get("company_share", 0.3)
        active = rng.random() < syn.get("active_contract_share", 0.8)
        return {
            "age": None if company else float(rng.integers(22, 71)),
            "contract_age": float(rng.integers(0, 11)) if active else None,
            "good_buyer_score": None if rng.random() < 0.1 else float(rng.beta(2, 2) * 100),
            "recommended_score": None if rng.random() < 0.1 else float(rng.beta(2, 3) * 100),
            "nb_products": float(rng.poisson(1) + active),
            "has_active_contract": float(active),
            "days_to_expiry": float(rng.integers(-20, 300)) if active else None,
            "unpaid_invoice": float(active and rng.random() < syn.get("unpaid_share", 0.2)),
            "nb_claims": float(rng.poisson(2)),
            "is_company": float(company),
        }

    def _pool_customer(self) -> Dict:
        f = dict(self.pool[int(self.np_random.integers(len(self.pool)))])
        if f.get("has_active_contract"):
            # CSV expiry dates are historical: keep the real scores, re-draw the calendar position
            f["days_to_expiry"] = float(self.np_random.integers(-20, 300))
        return f

    # ---------------- gym API ----------------

    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict] = None):
        super().reset(seed=seed)
        f = self._pool_customer() if self.pool else self._synthetic_customer()
        f.update(contacts_30d=0.0, days_since_last_contact=365.0)
        self.f = f
        gb = f.get("good_buyer_score")
        self.propensity = gb / 100 if gb is not None else float(self.np_random.uniform(0.2, 0.8))
        self.contact_log: List[int] = []
        self.t = 0
        return vectorize(self.f), {"action_mask": self.action_masks()}

    def action_masks(self) -> np.ndarray:
        return business_mask(self.f, self.rules)

    def _conversion_prob(self, action: str) -> float:
        a = self.sim["actions"][action]
        fatigue = np.exp(-self.sim["fatigue_alpha"] * self.f["contacts_30d"])
        p = a["base_prob"] * fatigue * self.multiplier
        if action == "recommend_product":
            rs = self.f.get("recommended_score")
            p *= (0.3 + 0.7 * self.propensity) * (0.5 + (rs if rs is not None else 50) / 100)
        elif action == "recommend_guarantee":
            p *= 0.5 + 0.5 * (1 - self.propensity)
        elif action == "contract_renewal" and self.f.get("unpaid_invoice"):
            p *= 0.5
        return float(np.clip(p, 0.0, 1.0))

    def step(self, action_idx: int):
        rng, sim, f = self.np_random, self.sim, self.f
        action = ACTIONS_V1[int(action_idx)]
        info = {"action": action, "invalid_action": False, "converted": False,
                "contacted": False, "unsubscribed": False, "churned": False}
        reward, terminated = 0.0, False

        if not self.action_masks()[int(action_idx)]:
            info["invalid_action"] = True
            reward -= sim["invalid_action_penalty"]
        elif action != "wait":
            info["contacted"] = True
            reward -= sim["contact_cost"]
            fatigued = f["contacts_30d"] >= 2
            if rng.random() < self._conversion_prob(action):
                info["converted"] = True
                reward += sim["actions"][action]["value"]
                self._apply_conversion(action)
            if fatigued and rng.random() < sim["unsubscribe_prob_when_fatigued"]:
                info["unsubscribed"] = True
                reward -= sim["unsubscribe_penalty"]
                terminated = True

        reward += self._advance_time(contacted=info["contacted"], info=info)
        self.t += 1
        truncated = self.t >= sim["horizon_steps"]
        info["action_mask"] = self.action_masks()
        return vectorize(f), float(reward), terminated, truncated, info

    def _apply_conversion(self, action: str) -> None:
        f = self.f
        if action == "recommend_product":
            f["nb_products"] = (f.get("nb_products") or 0) + 1
            self.propensity *= 0.6  # saturation after a purchase
        elif action == "recommend_guarantee":
            self.propensity *= 0.8
        elif action == "contract_renewal":
            f["days_to_expiry"] = (f["days_to_expiry"] or 0) + 365
        elif action == "payment_reminder":
            f["unpaid_invoice"] = 0.0

    def _advance_time(self, contacted: bool, info: Dict) -> float:
        f, sim, step_days = self.f, self.sim, self.sim.get("step_days", 7)
        penalty = 0.0
        self.contact_log = (self.contact_log + [int(contacted)])[-4:]  # ~30 days of weekly steps
        f["contacts_30d"] = float(sum(self.contact_log))
        f["days_since_last_contact"] = 0.0 if contacted else min(
            f["days_since_last_contact"] + step_days, 365.0)

        if f.get("unpaid_invoice") and self.np_random.random() < 0.05:
            f["unpaid_invoice"] = 0.0  # pays spontaneously
        if f.get("has_active_contract") and f.get("days_to_expiry") is not None:
            if in_renewal_window(f, self.rules) and self.np_random.random() < 0.04:
                f["days_to_expiry"] += 365  # renews without being contacted
            f["days_to_expiry"] -= step_days
            lo = self.rules.get("renewal_window_days", [-30, 60])[0]
            if f["days_to_expiry"] < lo:
                f["has_active_contract"] = 0.0
                f["days_to_expiry"] = None
                info["churned"] = True
                penalty -= sim["churn_penalty"]
        return penalty


def make_env(cfg: Dict, profile_pool=None, conversion_multiplier=None) -> NextBestActionEnv:
    return NextBestActionEnv(
        cfg["simulator"], cfg.get("business_rules"), profile_pool, conversion_multiplier
    )
