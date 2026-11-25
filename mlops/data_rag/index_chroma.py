"""
P1.3 — Build an isolated, versioned ChromaDB collection for a candidate index.

The active collection (the one named in rag/latest.json, or the legacy `legal_docs`)
is never written to: a candidate always gets its own `<prefix>__<index_version>` collection.
"""

import re
from typing import Callable, Dict, List, Optional, Sequence

from mlops.common.storage import sha256_bytes

EmbedFn = Callable[[Sequence[str]], List[List[float]]]


def index_version(corpus_hash: str, embedding_model: str, chunk_size: int, overlap: int) -> str:
    recipe = sha256_bytes(f"{embedding_model}|{chunk_size}|{overlap}".encode())
    return f"rag-{corpus_hash[:10]}-{recipe[:6]}"


def collection_name(prefix: str, version: str) -> str:
    # Chroma names: 3-63 chars, [a-zA-Z0-9._-]
    return re.sub(r"[^a-zA-Z0-9._-]", "_", f"{prefix}__{version}")[:63]


def sentence_transformer_embedder(model_name: str, batch_size: int = 32) -> EmbedFn:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)

    def embed(texts: Sequence[str]) -> List[List[float]]:
        return model.encode(list(texts), batch_size=batch_size, show_progress_bar=True).tolist()

    return embed


def chroma_client(host: str, port: int):
    import chromadb

    return chromadb.HttpClient(host=host, port=port)


def build_index(
    client,
    chunks: List[Dict],
    name: str,
    embed: EmbedFn,
    protected: Optional[set] = None,
    batch_size: int = 256,
    metadata: Optional[Dict] = None,
):
    if name in (protected or set()):
        raise RuntimeError(f"Refusing to rebuild the active collection {name}")
    # a candidate collection can be rebuilt from scratch: it is not served yet
    existing = {getattr(c, "name", c) for c in client.list_collections()}
    if name in existing:
        client.delete_collection(name)
    collection = client.create_collection(name=name, metadata=metadata or None)

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        texts = [c["text"] for c in batch]
        collection.add(
            ids=[c["id"] for c in batch],
            documents=texts,
            embeddings=embed(texts),
            metadatas=[c["metadata"] for c in batch],
        )
    return collection
