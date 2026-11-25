"""
P2.5 — Publish the RL candidate: bundle (model + preprocessor + action schema), manifest
and validation record. Approval = all gates passed. rl/latest.json is moved only by
`--promote` here or `python -m mlops.promote rl promote <version>`, and can be rolled back.
"""

from pathlib import Path
from typing import Dict, Optional

from mlops.common.manifest import write_manifest, write_validation
from mlops.common.schemas import GateResult, RlManifest, ValidationRecord, utc_now
from mlops.common.storage import artifact_root

from .policies import save_bundle


def bundle_dir(version: str, root: Optional[Path] = None) -> Path:
    return Path(root or artifact_root()) / "rl" / "models" / version


def publish_candidate(
    policy, version: str, gates: Dict[str, Dict], eval_report: Dict, run_id: Optional[str],
    data_hash: Optional[str], root: Optional[Path] = None,
) -> RlManifest:
    directory = save_bundle(policy, bundle_dir(version, root), {"model_version": version})
    approved = all(g["passed"] for g in gates.values())
    manifest = RlManifest(
        version=version, model_uri=directory.relative_to(Path(root or artifact_root())).as_posix(),
        algorithm=policy.algorithm, mlflow_run_id=run_id, data_hash=data_hash,
        eval_report=eval_report, approved=approved,
    )
    write_manifest(manifest, root)
    write_validation(
        ValidationRecord(
            kind="rl", version=version, gates={k: GateResult(**g) for k, g in gates.items()},
            approved=approved, approved_by="gates" if approved else None,
            approved_at=utc_now() if approved else None,
            reasons=[f"{k} failed" for k, g in gates.items() if not g["passed"]],
        ),
        root,
    )
    return manifest
