"""Artifact storage helpers: deterministic hashing and atomic writes."""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]


def artifact_root() -> Path:
    return Path(os.getenv("ARTIFACT_ROOT", REPO_ROOT / "artifacts"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_tree(paths: Iterable[Path], base: Path) -> str:
    """Hash a set of files independently of filesystem ordering."""
    digest = hashlib.sha256()
    for path in sorted(Path(p) for p in paths):
        digest.update(path.relative_to(base).as_posix().encode())
        digest.update(sha256_file(path).encode())
    return digest.hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    """Write via a temp file in the same directory then os.replace (atomic on POSIX and NTFS)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def atomic_write_json(path: Path, data: Any) -> None:
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def read_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
