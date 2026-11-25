"""P2.3 — Training: LinUCB contextual bandit and MaskablePPO, with fixed seeds."""

import logging
from typing import Dict, List, Optional

import numpy as np

from .env import make_env
from .policies import LinUCBPolicy, MaskablePPOPolicy

log = logging.getLogger("rl.train")


def ppo_available() -> bool:
    try:
        import sb3_contrib  # noqa: F401
    except ImportError:
        return False
    return True


def train_linucb(cfg: Dict, seed: int, pool: Optional[List[Dict]] = None) -> LinUCBPolicy:
    params = cfg["training"]["linucb"]
    env = make_env(cfg, pool)
    policy = LinUCBPolicy(alpha=params["alpha"])
    for episode in range(params["train_episodes"]):
        obs, _ = env.reset(seed=seed * 1_000_003 + episode)
        done = False
        while not done:
            features = dict(env.f)
            action = policy.act(features, obs, env.action_masks(), explore=True)
            next_obs, reward, terminated, truncated, _ = env.step(action)
            policy.update(obs, action, reward)
            obs, done = next_obs, terminated or truncated
    return policy


def train_maskable_ppo(cfg: Dict, seed: int, pool: Optional[List[Dict]] = None) -> MaskablePPOPolicy:
    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.wrappers import ActionMasker

    params = dict(cfg["training"]["ppo"])
    total = params.pop("total_timesteps")
    env = ActionMasker(make_env(cfg, pool), lambda e: e.action_masks())
    env.reset(seed=seed)
    model = MaskablePPO("MlpPolicy", env, seed=seed, verbose=0, device="cpu", **params)
    model.learn(total_timesteps=total)
    return MaskablePPOPolicy(model)


TRAINERS = {"linucb": train_linucb, "maskable_ppo": train_maskable_ppo}


def train(algorithm: str, cfg: Dict, seed: int, pool=None):
    np.random.seed(seed)
    log.info("training %s seed=%d", algorithm, seed)
    return TRAINERS[algorithm](cfg, seed, pool)
