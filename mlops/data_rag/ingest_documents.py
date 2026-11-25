"""
P1.2 — Parse and chunk the inventoried documents, keeping provenance on every chunk.

PDF/CSV parsing reuses agent/rag_model/utils.py (the loaders used by document-parseer.py)
so the online and batch indexes are built from identical chunks. Text/Markdown files use a
built-in splitter and need no extra dependency.
"""

import importlib.util
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from mlops.common.storage import REPO_ROOT

_PARSER = None


def _agent_parser():
    """Load agent/rag_model/utils.py under a private name (agent/utils would shadow `utils`)."""
    global _PARSER
    if _PARSER is None:
        path = REPO_ROOT / "agent" / "rag_model" / "utils.py"
        spec = importlib.util.spec_from_file_location("nextbh_rag_parser", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _PARSER = module
    return _PARSER


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Deterministic splitter preferring paragraph, then line, then word boundaries."""
    text = text.strip()
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            window = text[start:end]
            for sep in ("\n\n", "\n", " "):
                cut = window.rfind(sep)
                if cut > chunk_size // 2:
                    end = start + cut
                    break
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - chunk_overlap, start + 1)
    return chunks


def _pieces(path: Path, doc_type: str, chunk_size: int, chunk_overlap: int) -> Iterator[tuple]:
    if doc_type in ("txt", "md"):
        for chunk in split_text(path.read_text(encoding="utf-8"), chunk_size, chunk_overlap):
            yield chunk, None
        return
    parser = _agent_parser()
    for doc in parser.split_documents(parser.load_documents(path), chunk_size, chunk_overlap):
        page = doc.metadata.get("page", doc.metadata.get("row"))
        yield doc.page_content, page


def ingest(
    inventory: dict, chunk_size: int, chunk_overlap: int, base: Optional[Path] = None
) -> List[Dict]:
    base = Path(base or REPO_ROOT)
    chunks = []
    for doc in inventory["documents"]:
        path = base / doc["source_uri"]
        for i, (text, page) in enumerate(_pieces(path, doc["type"], chunk_size, chunk_overlap)):
            if not text.strip():
                continue
            metadata = {
                "source": doc["source_uri"],
                "filename": doc["filename"],
                "category": doc["category"],
                "product": doc["product"],
                "document_id": doc["document_id"],
                "document_version": doc["version"],
                "chunk_index": i,
                "chunk_length": len(text),
            }
            if doc.get("date_effet"):
                metadata["date_effet"] = str(doc["date_effet"])
            if page is not None:
                metadata["page"] = int(page)
            chunks.append({
                "id": f"{doc['document_id']}:{doc['version']}:{i}",
                "text": text,
                "metadata": metadata,
            })
    return chunks
