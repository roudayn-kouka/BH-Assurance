import logging
from typing import List, Dict
from sentence_transformers import SentenceTransformer
import chromadb
import os
import sys
import traceback
import torch

# --- CONFIG ---
CHROMA_COLLECTION_NAME = "legal_docs"
CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-large"
TOP_K = 5  # default number of results to retrieve
MODEL_NAME = "intfloat/multilingual-e5-large"

# --- Setup logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

FALLBACK_SMALL = "all-MiniLM-L6-v2"   # lightweight fallback
FALLBACK_MEDIUM = "intfloat/multilingual-e5-base"  # medium fallback

def _clear_cuda():
    if torch.cuda.is_available():
        try:
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
        except Exception:
            pass

def _try_load(name, device, half=False):
    model = SentenceTransformer(name, device=device)
    if half and device.startswith("cuda"):
        try:
            model = model.half()
        except Exception:
            pass
    return model

def load_embedding_model(preferred=EMBEDDING_MODEL_NAME):
    # prefer cuda if available
    use_cuda = torch.cuda.is_available()
    device = "cuda" if use_cuda else "cpu"

    # set allocator to reduce fragmentation (helpful)
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    try:
        _clear_cuda()
        print(f"[loader] trying to load {preferred} on {device}")
        return _try_load(preferred, device=device, half=False)

    except Exception as e:
        err = str(e).lower()
        print("[loader] primary load failed:", err.splitlines()[0])
        # If it's an OOM-like error and we have cuda available, try strategies
        if use_cuda and ("outofmemory" in err or "out of memory" in err or isinstance(e, torch.cuda.OutOfMemoryError)):
            try:
                print("[loader] clearing cache and retrying (half precision)...")
                _clear_cuda()
                # attempt half precision on cuda (may still fail)
                return _try_load(preferred, device="cuda", half=True)
            except Exception as e2:
                print("[loader] half-precision retry failed:", str(e2).splitlines()[0])
                _clear_cuda()

            # try medium fallback on cuda first
            try:
                print(f"[loader] trying medium fallback {FALLBACK_MEDIUM} on cuda")
                return _try_load(FALLBACK_MEDIUM, device="cuda", half=True)
            except Exception as e3:
                print("[loader] medium fallback failed:", str(e3).splitlines()[0])
                _clear_cuda()

        # final fallback: load a small model on CPU
        try:
            print(f"[loader] falling back to small model {FALLBACK_SMALL} on cpu")
            return _try_load(FALLBACK_SMALL, device="cpu", half=False)
        except Exception as final_e:
            print("[loader] final fallback failed; raising original exception")
            traceback.print_exc()
            raise
embedding_model = load_embedding_model()

try:
    logger.info("Connecting to Chroma vector store...")
    chroma_client = chromadb.HttpClient(host="localhost", port=8000)
    collection = chroma_client.get_or_create_collection(name="legal_docs")
except Exception as e:
    logger.exception("Failed to connect to Chroma vector store")
    raise e


def retrieve(query: str, top_k: int = TOP_K) -> List[Dict]:
    """
    Retrieve top_k relevant documents from Chroma for a given query.
    Returns a list of dicts with document content and metadata.
    """
    if not query or not query.strip():
        logger.warning("Empty query received")
        return []

    try:
        logger.info(f"Retrieving top {top_k} documents for query: {query}")
        query_embedding = embedding_model.encode([query])[0]
        results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas"]  # ensure we return metadata
    )
        output = []
        for doc in results:
            output.append({
                "document": getattr(doc, "page_content", ""),
                "metadata": getattr(doc, "metadata", {}) or {}
            })
        logger.info(f"Retrieved {len(output)} documents")
        return output
    except Exception as e:
        logger.exception("Error during retrieval: " + e)
        return []


def retrieve_context(query: str, top_k: int = TOP_K) -> str:
    """
    Concatenates top_k retrieved documents into a single string
    suitable to feed into an LLM prompt.
    """
    try:
        logger.info(f"Retrieving context for query: {query} (top_k={top_k})")
        docs = retrieve(query, top_k)

        if not docs:
            logger.warning("No documents retrieved for query: %s", query)
            return ""

        logger.info("Retrieved %d documents for query: %s", len(docs), query)
        for idx, d in enumerate(docs, 1):
           print("[rag]: Raw doc %d: %s", idx, d)  # log the entire doc dict

        context_parts = []
        for idx, d in enumerate(docs, 1):
            src = d.get('metadata', {}).get('source', 'unknown')
            snippet = d.get('document')[:200].replace("\n", " ")  # log preview only
            print("[RAG]: Doc %d from %s (preview: %s...)", idx, src, snippet)
            context_parts.append(f"[Doc {idx} - {src}]\n{d['document']}\n\n")

        context = "".join(context_parts)
        logger.info("Final context length: %d characters", len(context))
        return context

    except Exception as e:
        logger.exception("Error creating context for LLM: %s", str(e))
        return ""


# --- Example usage ---
if __name__ == "__main__":
    query = "Assurance vie décès"
    retrieved_docs = retrieve(query)
    for doc in retrieved_docs:
        logger.info(f"Source: {doc['metadata'].get('source', 'unknown')}, Text snippet: {doc['document'][:200]}...")
    
    context_str = retrieve_context(query)
    logger.info(f"Concatenated context for LLM:\n{context_str[:500]}...")  # show first 500 chars
