"""
Immutable manifests + approved pointer, for both pipelines.

Layout under <artifact_root>/<kind>/:
    manifests/<version>.json   immutable, written once per candidate
    validation/<version>.json  gate results (registry/validation.json of the architecture doc)
    latest.json                pointer to the approved version consumed by the services
    history.jsonl              append-only promotion / rollback log

`latest.json` is only ever written by `promote()`, which refuses unapproved manifests,
so "latest" can never implicitly designate a candidate.
"""

import json
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel

from .schemas import RagManifest, RlManifest, ValidationRecord, utc_now
from .storage import artifact_root, atomic_write_json, read_json

MANIFEST_TYPES = {"rag": RagManifest, "rl": RlManifest}
Manifest = Union[RagManifest, RlManifest]


class ManifestError(RuntimeError):
    pass


def _kind_dir(kind: str, root: Optional[Path] = None) -> Path:
    if kind not in MANIFEST_TYPES:
        raise ManifestError(f"Unknown artifact kind: {kind}")
    return Path(root or artifact_root()) / kind


def manifest_path(kind: str, version: str, root: Optional[Path] = None) -> Path:
    return _kind_dir(kind, root) / "manifests" / f"{version}.json"


def latest_path(kind: str, root: Optional[Path] = None) -> Path:
    return _kind_dir(kind, root) / "latest.json"


def write_manifest(manifest: Manifest, root: Optional[Path] = None) -> Path:
    """Write a candidate manifest. An existing version can't be rewritten with different content."""
    path = manifest_path(manifest.kind, manifest.version, root)
    data = manifest.model_dump()
    if path.exists():
        existing = read_json(path)
        if {**existing, "created_at": None} != {**data, "created_at": None}:
            raise ManifestError(f"Manifest {path} already exists and is immutable")
        return path
    atomic_write_json(path, data)
    return path


def read_manifest(kind: str, version: str, root: Optional[Path] = None) -> Manifest:
    path = manifest_path(kind, version, root)
    if not path.exists():
        raise ManifestError(f"No manifest for {kind} version {version}")
    return MANIFEST_TYPES[kind].model_validate(read_json(path))


def write_validation(record: ValidationRecord, root: Optional[Path] = None) -> Path:
    path = _kind_dir(record.kind, root) / "validation" / f"{record.version}.json"
    atomic_write_json(path, record.model_dump())
    return path


def _append_history(kind: str, entry: dict, root: Optional[Path]) -> None:
    path = _kind_dir(kind, root) / "history.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def promote(
    kind: str,
    version: str,
    approved_by: str,
    root: Optional[Path] = None,
    action: str = "promote",
) -> Path:
    manifest = read_manifest(kind, version, root)
    if not manifest.approved:
        raise ManifestError(f"{kind} {version} is not approved; refusing to point latest.json at it")

    pointer = latest_path(kind, root)
    previous = read_json(pointer).get("version") if pointer.exists() else None
    data = manifest.model_dump()
    data.update(
        previous_version=previous, promoted_by=approved_by, promoted_at=utc_now()
    )
    atomic_write_json(pointer, data)
    _append_history(
        kind,
        {"action": action, "version": version, "previous_version": previous,
         "by": approved_by, "at": data["promoted_at"]},
        root,
    )
    return pointer


def rollback(
    kind: str, approved_by: str, to_version: Optional[str] = None, root: Optional[Path] = None
) -> Path:
    pointer = latest_path(kind, root)
    if not pointer.exists():
        raise ManifestError(f"No {kind}/latest.json to roll back")
    target = to_version or read_json(pointer).get("previous_version")
    if not target:
        raise ManifestError(f"No previous {kind} version recorded; pass an explicit version")
    return promote(kind, target, approved_by, root, action="rollback")


def load_latest(source: Union[str, Path, None], kind: str) -> Optional[dict]:
    """
    Load an approved pointer for a service. `source` is either the latest.json path
    or None (then <artifact_root>/<kind>/latest.json). Returns None when missing,
    unreadable, of the wrong kind or not approved — callers then fall back.
    """
    path = Path(source) if source else latest_path(kind)
    if not path.exists():
        return None
    try:
        data = read_json(path)
        MANIFEST_TYPES[kind].model_validate(
            {k: v for k, v in data.items() if k in MANIFEST_TYPES[kind].model_fields}
        )
    except Exception:
        return None
    if data.get("kind") != kind or data.get("approved") is not True:
        return None
    return data


def as_dict(model: BaseModel) -> dict:
    return model.model_dump()
