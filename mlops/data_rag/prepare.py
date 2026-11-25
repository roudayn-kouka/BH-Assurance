"""
P1.1/P1.2 — Inventory and normalise the document corpus.

Each document gets document_id, version (content hash), product/category, date_effet and
source_uri. The corpus hash only depends on file contents and relative paths, so the same
corpus always yields the same index version.
"""

import hashlib
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from mlops.common.storage import REPO_ROOT, sha256_bytes, sha256_file


def _category(folder: str, category_map: Dict[str, str]) -> str:
    # same convention as agent/rag_model/document-parseer.py: "<n>-CG-Automobile" -> "CG-Automobile"
    code = "-".join(folder.split("-")[1:]) if folder.count("-") >= 2 else folder
    return category_map.get(code, category_map.get(folder, code))


def _sidecar(path: Path) -> dict:
    """Optional <file>.meta.yaml with business metadata (date_effet, produit, version)."""
    meta = path.with_name(path.name + ".meta.yaml")
    if meta.exists():
        return yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
    return {}


def build_inventory(
    source_dirs: List[str], extensions: List[str], category_map: Dict[str, str],
    base: Optional[Path] = None,
) -> dict:
    base = Path(base or REPO_ROOT)
    docs = []
    for source in source_dirs:
        root = (base / source).resolve()
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in extensions:
                continue
            content_hash = sha256_file(path)
            source_uri = path.relative_to(base).as_posix()
            extra = _sidecar(path)
            docs.append({
                "document_id": hashlib.sha1(source_uri.encode()).hexdigest()[:16],
                "version": str(extra.get("version") or content_hash[:12]),
                "sha256": content_hash,
                "source_uri": source_uri,
                "filename": path.name,
                "category": _category(path.parent.name, category_map),
                "product": extra.get("produit") or _category(path.parent.name, category_map),
                # YAML parses 2024-01-01 as a date object: keep the manifest JSON-serialisable
                "date_effet": str(extra["date_effet"]) if extra.get("date_effet") else None,
                "type": path.suffix.lower().lstrip("."),
            })

    docs.sort(key=lambda d: d["source_uri"])
    corpus_hash = sha256_bytes(
        "\n".join(f"{d['source_uri']}:{d['sha256']}" for d in docs).encode()
    )
    return {"corpus_hash": corpus_hash, "documents": docs}
