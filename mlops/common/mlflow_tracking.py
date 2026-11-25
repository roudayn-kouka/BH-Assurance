"""
Experiment tracking. Uses MLflow when MLFLOW_TRACKING_URI is set and mlflow is installed,
otherwise records the run as JSON under <artifact_root>/runs/<run_id>/ so every pipeline
run stays reproducible and comparable without the server.
"""

import json
import os
import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, Optional

from .schemas import utc_now
from .storage import artifact_root, atomic_write_json


class LocalRun:
    def __init__(self, experiment: str, run_name: str, tags: Dict[str, str]):
        self.run_id = uuid.uuid4().hex
        self.dir = artifact_root() / "runs" / self.run_id
        self.record = {
            "run_id": self.run_id, "experiment": experiment, "run_name": run_name,
            "tags": tags, "params": {}, "metrics": {}, "artifacts": [],
            "started_at": utc_now(), "backend": "local",
        }

    def log_params(self, params: Dict) -> None:
        self.record["params"].update({k: str(v) for k, v in params.items()})

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None) -> None:
        self.record["metrics"].update({k: float(v) for k, v in metrics.items()})

    def log_artifact(self, path: Path) -> None:
        path = Path(path)
        dest = self.dir / "artifacts" / path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            shutil.copytree(path, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(path, dest)
        self.record["artifacts"].append(path.name)

    def log_dict(self, data: Dict, name: str) -> None:
        dest = self.dir / "artifacts" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.record["artifacts"].append(name)

    def close(self, status: str) -> None:
        self.record.update(status=status, ended_at=utc_now())
        atomic_write_json(self.dir / "run.json", self.record)


class MlflowRun:
    def __init__(self, mlflow, active_run):
        self._mlflow = mlflow
        self.run_id = active_run.info.run_id

    def log_params(self, params: Dict) -> None:
        self._mlflow.log_params(params)

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None) -> None:
        self._mlflow.log_metrics(metrics, step=step)

    def log_artifact(self, path: Path) -> None:
        path = Path(path)
        if path.is_dir():
            self._mlflow.log_artifacts(str(path), artifact_path=path.name)
        else:
            self._mlflow.log_artifact(str(path))

    def log_dict(self, data: Dict, name: str) -> None:
        self._mlflow.log_dict(data, name)


def _mlflow():
    if not os.getenv("MLFLOW_TRACKING_URI"):
        return None
    try:
        import mlflow
    except ImportError:
        return None
    return mlflow


@contextmanager
def start_run(experiment: str, run_name: str, tags: Optional[Dict[str, str]] = None) -> Iterator:
    tags = dict(tags or {})
    tags.setdefault("git_commit", os.getenv("GITHUB_SHA", os.getenv("GIT_COMMIT", "local")))
    mlflow = _mlflow()
    if mlflow is not None:
        mlflow.set_experiment(experiment)
        with mlflow.start_run(run_name=run_name, tags=tags) as active:
            yield MlflowRun(mlflow, active)
        return

    run = LocalRun(experiment, run_name, tags)
    try:
        yield run
    except BaseException:
        run.close("FAILED")
        raise
    run.close("FINISHED")
