"""
P2.4 — Multi-seed evaluation and champion/challenger comparison.

Every policy is evaluated on the same customer seeds (common random numbers) for each
simulator variant (conversion multiplier), so differences come from the policy.
"""

from typing import Dict, List, Optional

import numpy as np

from .env import make_env

EVAL_SEED_OFFSET = 10_000_000  # evaluation customers never overlap training episodes


def run_episodes(policy, cfg: Dict, seed: int, episodes: int, multiplier: float,
                 pool: Optional[List[Dict]] = None) -> Dict[str, float]:
    env = make_env(cfg, pool, conversion_multiplier=multiplier)
    totals = dict(ret=0.0, conversions=0, contacts=0, invalid=0, unsubscribed=0, churned=0)
    actions = np.zeros(env.action_space.n, dtype=int)
    for ep in range(episodes):
        obs, _ = env.reset(seed=EVAL_SEED_OFFSET + seed * 100_003 + ep)
        done = False
        while not done:
            mask = env.action_masks()
            action = policy.act(dict(env.f), obs, mask)
            actions[action] += 1
            obs, reward, terminated, truncated, info = env.step(action)
            totals["ret"] += reward
            totals["conversions"] += info["converted"]
            totals["contacts"] += info["contacted"]
            totals["invalid"] += info["invalid_action"]
            totals["unsubscribed"] += info["unsubscribed"]
            totals["churned"] += info["churned"]
            done = terminated or truncated
    n = float(episodes)
    return {
        "mean_return": totals["ret"] / n,
        "conversions_per_episode": totals["conversions"] / n,
        "contacts_per_episode": totals["contacts"] / n,
        "conversion_per_contact": totals["conversions"] / max(totals["contacts"], 1),
        "unsubscribe_rate": totals["unsubscribed"] / n,
        "churn_rate": totals["churned"] / n,
        "invalid_actions": int(totals["invalid"]),
        "action_distribution": (actions / max(actions.sum(), 1)).round(4).tolist(),
    }


def evaluate_policy(policy, cfg: Dict, seeds: List[int], pool=None) -> Dict:
    ev = cfg["evaluation"]
    results = {}
    for m in ev["conversion_multipliers"]:
        per_seed = [run_episodes(policy, cfg, s, ev["episodes_per_seed"], m, pool) for s in seeds]
        returns = [r["mean_return"] for r in per_seed]
        results[str(m)] = {
            "per_seed": per_seed,
            "mean_return": float(np.mean(returns)),
            "std_return": float(np.std(returns)),
            "contacts_per_episode": float(np.mean([r["contacts_per_episode"] for r in per_seed])),
            "conversions_per_episode": float(np.mean([r["conversions_per_episode"] for r in per_seed])),
            "invalid_actions": int(sum(r["invalid_actions"] for r in per_seed)),
        }
    return results


def compare(challenger: Dict, champion: Dict, thresholds: Dict, nominal: str = "1.0") -> Dict:
    """Gates for promoting a challenger over the champion (rules baseline if none approved)."""
    ch, cp = challenger[nominal], champion[nominal]
    wins = sum(
        a["mean_return"] > b["mean_return"] for a, b in zip(ch["per_seed"], cp["per_seed"])
    )
    uplift = (ch["mean_return"] - cp["mean_return"]) / max(abs(cp["mean_return"]), 1e-9)
    worst = min(
        (challenger[m]["mean_return"] - champion[m]["mean_return"])
        / max(abs(champion[m]["mean_return"]), 1e-9)
        for m in challenger
    )
    invalid = sum(challenger[m]["invalid_actions"] for m in challenger)
    return {
        "invalid_actions": {"value": invalid, "threshold": thresholds["max_invalid_actions"],
                            "passed": invalid <= thresholds["max_invalid_actions"]},
        "relative_uplift": {"value": uplift, "threshold": thresholds["min_relative_uplift"],
                            "passed": uplift >= thresholds["min_relative_uplift"]},
        "seeds_won": {"value": wins, "threshold": thresholds["min_seeds_won"],
                      "passed": wins >= thresholds["min_seeds_won"]},
        "contacts_per_episode": {"value": ch["contacts_per_episode"],
                                 "threshold": thresholds["max_contacts_per_episode"],
                                 "passed": ch["contacts_per_episode"] <= thresholds["max_contacts_per_episode"]},
        "robustness": {"value": worst, "threshold": -thresholds["robustness_tolerance"],
                       "passed": worst >= -thresholds["robustness_tolerance"]},
    }
