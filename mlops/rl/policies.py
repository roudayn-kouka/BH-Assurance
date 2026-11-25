"""
Policies sharing one interface — act(features, obs, mask) -> action index — and the bundle
format (model + preprocessor + action schema) that the policy-service loads.

Bundle directory:
    policy.json      algorithm, feature/action schema, action list, preprocessor spec
    linucb.npz       (linucb)   per-arm A^-1 and b
    model.zip        (maskable_ppo)  sb3-contrib model
"""

import json
from pathlib import Path
from typing import Dict, Optional

import numpy as np

from .actions import ACTION_SCHEMA, ACTIONS_V1, rules_action
from .features import FEATURE_SCHEMA, OBS_DIM, preprocessor_spec


class SchemaMismatch(RuntimeError):
    pass


class RulesPolicy:
    algorithm = "rules"

    def act(self, features: Dict, obs: np.ndarray, mask: np.ndarray) -> int:
        return rules_action(features, mask)[0]


class RandomPolicy:
    algorithm = "random"

    def __init__(self, seed: int = 0):
        self.rng = np.random.default_rng(seed)

    def act(self, features: Dict, obs: np.ndarray, mask: np.ndarray) -> int:
        return int(self.rng.choice(np.flatnonzero(mask)))


class LinUCBPolicy:
    """Disjoint LinUCB contextual bandit restricted to the allowed actions."""

    algorithm = "linucb"

    def __init__(self, n_actions: int = len(ACTIONS_V1), dim: int = OBS_DIM + 1, alpha: float = 0.5):
        self.alpha = alpha
        self.A_inv = np.stack([np.eye(dim) for _ in range(n_actions)])
        self.b = np.zeros((n_actions, dim))

    @staticmethod
    def _x(obs: np.ndarray) -> np.ndarray:
        return np.append(obs.astype(np.float64), 1.0)  # bias term

    def scores(self, obs: np.ndarray, explore: bool) -> np.ndarray:
        x = self._x(obs)
        theta = np.einsum("aij,aj->ai", self.A_inv, self.b)
        s = theta @ x
        if explore:
            s = s + self.alpha * np.sqrt(np.einsum("i,aij,j->a", x, self.A_inv, x))
        return s

    def act(self, features: Dict, obs: np.ndarray, mask: np.ndarray, explore: bool = False) -> int:
        s = np.where(mask, self.scores(obs, explore), -np.inf)
        return int(np.argmax(s))

    def update(self, obs: np.ndarray, action: int, reward: float) -> None:
        x = self._x(obs)
        A_inv = self.A_inv[action]
        Ax = A_inv @ x
        self.A_inv[action] = A_inv - np.outer(Ax, Ax) / (1.0 + x @ Ax)  # Sherman-Morrison
        self.b[action] += reward * x

    def save(self, directory: Path) -> None:
        np.savez(directory / "linucb.npz", A_inv=self.A_inv, b=self.b, alpha=self.alpha)

    @classmethod
    def load(cls, directory: Path) -> "LinUCBPolicy":
        data = np.load(directory / "linucb.npz")
        policy = cls(alpha=float(data["alpha"]))
        policy.A_inv, policy.b = data["A_inv"], data["b"]
        return policy


class MaskablePPOPolicy:
    algorithm = "maskable_ppo"

    def __init__(self, model):
        self.model = model

    def act(self, features: Dict, obs: np.ndarray, mask: np.ndarray) -> int:
        action, _ = self.model.predict(obs, action_masks=mask, deterministic=True)
        return int(action)

    def save(self, directory: Path) -> None:
        self.model.save(directory / "model.zip")

    @classmethod
    def load(cls, directory: Path) -> "MaskablePPOPolicy":
        from sb3_contrib import MaskablePPO

        return cls(MaskablePPO.load(directory / "model.zip", device="cpu"))


def save_bundle(policy, directory: Path, extra: Optional[Dict] = None) -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if hasattr(policy, "save"):
        policy.save(directory)
    spec = {
        "algorithm": policy.algorithm,
        "feature_schema": FEATURE_SCHEMA,
        "action_schema": ACTION_SCHEMA,
        "actions": ACTIONS_V1,
        "preprocessor": preprocessor_spec(),
        **(extra or {}),
    }
    (directory / "policy.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return directory


def load_bundle(directory: Path):
    """Load a policy bundle, refusing any feature/action schema other than the served one."""
    directory = Path(directory)
    spec = json.loads((directory / "policy.json").read_text(encoding="utf-8"))
    if spec["feature_schema"] != FEATURE_SCHEMA or spec["action_schema"] != ACTION_SCHEMA \
            or spec["actions"] != ACTIONS_V1:
        raise SchemaMismatch(
            f"bundle {directory} uses features {spec['feature_schema']} / actions "
            f"{spec['action_schema']}, service expects {FEATURE_SCHEMA} / {ACTION_SCHEMA}"
        )
    loaders = {"linucb": LinUCBPolicy.load, "maskable_ppo": MaskablePPOPolicy.load,
               "rules": lambda _: RulesPolicy()}
    if spec["algorithm"] not in loaders:
        raise SchemaMismatch(f"Unknown algorithm {spec['algorithm']}")
    return loaders[spec["algorithm"]](directory), spec
