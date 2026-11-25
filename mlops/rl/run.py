"""
Pipeline B — RL: export → features → train (multi-seed) → evaluate vs champion → publish.

    python -m mlops.rl.run [--algorithms linucb maskable_ppo] [--quick] [--promote --by <name>]
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Dict

import numpy as np

from mlops.common.manifest import latest_path, load_latest, promote
from mlops.common.mlflow_tracking import start_run
from mlops.common.settings import load_config
from mlops.common.storage import REPO_ROOT, artifact_root, atomic_write_json, sha256_bytes

from . import evaluate, export_events, features, publish, train
from .policies import RulesPolicy, SchemaMismatch, load_bundle

log = logging.getLogger("rl")


def _champion(cfg):
    """Approved model from rl/latest.json, else the rule baseline (today's business logic)."""
    latest = load_latest(latest_path("rl"), "rl")
    if latest:
        try:
            policy, _ = load_bundle(artifact_root() / latest["model_uri"])
            return policy, latest["version"]
        except (SchemaMismatch, OSError, ImportError) as e:
            log.warning("champion %s unusable (%s); comparing with rules", latest["version"], e)
    return RulesPolicy(), "rules-baseline"


def _summary(results: Dict) -> Dict:
    return {m: {k: v for k, v in r.items() if k != "per_seed"} for m, r in results.items()}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--algorithms", nargs="+")
    parser.add_argument("--quick", action="store_true", help="smoke run: tiny budgets (CI)")
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--by", default="pipeline")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    cfg = load_config("rl")
    thresholds = load_config("validation")["rl"]
    if args.quick:
        cfg["training"]["ppo"]["total_timesteps"] = 4096
        cfg["training"]["linucb"]["train_episodes"] = 300
        cfg["evaluation"]["episodes_per_seed"] = 50
    algorithms = args.algorithms or cfg["training"]["algorithms"]
    if "maskable_ppo" in algorithms and not train.ppo_available():
        log.warning("sb3-contrib not installed: skipping maskable_ppo")
        algorithms = [a for a in algorithms if a != "maskable_ppo"]
    seeds = cfg["training"]["seeds"]
    # gates are computed on holdout customer seeds, never on the ones used to pick the candidate
    holdout = [s + 1000 for s in seeds]

    # P2.1 export (optional) + P2.2 calibration population
    data_parts = []
    if cfg["data"].get("events_jsonl"):
        report = export_events.export(
            export_events.read_jsonl(REPO_ROOT / cfg["data"]["events_jsonl"]),
            artifact_root() / "rl" / "datasets",
        )
        data_parts.append(report["data_hash"])
    pool = features.load_profile_pool(cfg["data"]["profile_csvs"], REPO_ROOT)
    log.info("profile pool: %d customers (%s)", len(pool), "CSV" if pool else "synthetic generator")
    data_parts.append(sha256_bytes(json.dumps(pool, sort_keys=True, default=str).encode()))
    data_hash = sha256_bytes("|".join(data_parts).encode())

    champion, champion_version = _champion(cfg)
    champion_eval = evaluate.evaluate_policy(champion, cfg, holdout, pool)
    log.info("champion %s: %.3f", champion_version, champion_eval["1.0"]["mean_return"])

    benchmark, best = {}, None
    for algo in algorithms:
        with start_run("next-bh-rl", f"{algo}-benchmark", {"algorithm": algo}) as run:
            run.log_params({"algorithm": algo, "seeds": seeds, "data_hash": data_hash,
                            **{f"{algo}.{k}": v for k, v in cfg["training"].get(algo, {}).items()}})
            # one model per training seed, each scored on the same evaluation seeds
            trained = []
            for seed in seeds:
                policy = train.train(algo, cfg, seed, pool)
                score = evaluate.evaluate_policy(policy, cfg, seeds, pool)
                trained.append((score["1.0"]["mean_return"], seed, policy))
                run.log_metrics({f"mean_return_seed{seed}": score["1.0"]["mean_return"]})
            returns = [t[0] for t in trained]
            run.log_metrics({"mean_return": float(np.mean(returns)),
                             "std_return": float(np.std(returns))})
            # candidate = median training seed (not the luckiest one)
            median = sorted(trained, key=lambda t: t[0])[len(trained) // 2]
            benchmark[algo] = {"per_training_seed": dict(zip(map(str, seeds), returns)),
                               "mean": float(np.mean(returns)), "std": float(np.std(returns)),
                               "candidate_seed": median[1], "run_id": run.run_id}
            if best is None or median[0] > best[0]:
                best = (median[0], algo, median[2], run.run_id)

    if best is None:
        log.error("no algorithm trained")
        return 1
    _, algo, policy, run_id = best
    challenger_eval = evaluate.evaluate_policy(policy, cfg, holdout, pool)
    gates = evaluate.compare(challenger_eval, champion_eval, thresholds)
    version = f"rl-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{algo}"
    eval_report = {
        "champion": champion_version, "challenger_algorithm": algo,
        "challenger": _summary(challenger_eval), "champion_eval": _summary(champion_eval),
        "benchmark": benchmark, "gates": gates, "simulated": True,
    }
    manifest = publish.publish_candidate(policy, version, gates, eval_report, run_id, data_hash)
    atomic_write_json(artifact_root() / "rl" / "reports" / f"{version}.json", eval_report)

    summary = {"version": version, "algorithm": algo, "approved": manifest.approved,
               "champion": champion_version,
               "challenger_return": challenger_eval["1.0"]["mean_return"],
               "champion_return": champion_eval["1.0"]["mean_return"],
               "gates": {k: g["passed"] for k, g in gates.items()}}
    atomic_write_json(artifact_root() / "rl" / "reports" / "last_run.json", summary)
    print(json.dumps(summary, indent=2))

    if args.promote and manifest.approved:
        promote("rl", version, args.by)
        log.info("rl/latest.json -> %s", version)
    return 0 if manifest.approved else 2


if __name__ == "__main__":
    sys.exit(main())
