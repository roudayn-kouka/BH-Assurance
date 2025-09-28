from typing import Any, Dict, List
from datetime import datetime
from langchain_community.document_loaders import CSVLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import torch
import logging

# --- General utilities ---
def fetch_all_existing_ids(col, batch_size=1000) -> set:
    all_ids = []
    offset = 0
    while True:
        res = col.get(limit=batch_size, offset=offset)
        ids = res.get("ids", [])
        if not ids:
            break
        for item in ids:
            if isinstance(item, list):
                all_ids.extend(item)
            else:
                all_ids.append(item)
        offset += batch_size
    return set(all_ids)


def unwrap_first_level(x: Any):
    if x is None:
        return None
    if isinstance(x, list) and len(x) > 0:
        first = x[0]
        if isinstance(first, list) and len(first) > 0:
            return first[0]
        return first
    return x


def build_metadata(source_path, filename, category, chunk_index, chunk_length):
    return {
        "source": str(source_path),
        "filename": filename,
        "category": category,
        "chunk_index": chunk_index,
        "chunk_length": chunk_length,
        "added_at": datetime.utcnow().isoformat()
    }


def safe_load_sentence_transformer(model_name: str) -> SentenceTransformer:
    """Safely load SentenceTransformer with CUDA fallback to CPU."""
    # First, determine the best available device
    device = 'cpu'  # Default fallback
    
    if torch.cuda.is_available():
        try:
            # Test if CUDA is actually usable
            test_tensor = torch.tensor([1.0]).cuda()
            device = 'cuda'
            logging.info(f"CUDA is available and working. Using device: {device}")
            del test_tensor  # Clean up test tensor
        except Exception as e:
            logging.warning(f"CUDA is available but not usable: {e}. Falling back to CPU.")
            device = 'cpu'
    else:
        logging.info("CUDA is not available. Using CPU.")
    
    # Try to load the model with the determined device
    try:
        logging.info(f"Loading SentenceTransformer '{model_name}' on device: {device}")
        model = SentenceTransformer(model_name, device=device)
        logging.info(f"Successfully loaded model on {device}")
        return model
    except Exception as e:
        if device != 'cpu':
            logging.error(f"Failed to load model on {device}: {e}")
            logging.info("Attempting to load model on CPU as fallback...")
            try:
                # Clear CUDA cache if it exists
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                model = SentenceTransformer(model_name, device='cpu')
                logging.info("Successfully loaded model on CPU")
                return model
            except Exception as cpu_e:
                logging.error(f"Failed to load model on CPU: {cpu_e}")
                raise cpu_e
        else:
            logging.error(f"Failed to load model on CPU: {e}")
            raise e


# --- Shared processing pipeline for PDFs & CSVs ---
def process_documents(docs, file_path, category, collection, existing_ids, model, model_name, chunk_prefix, chunk_size, chunk_overlap):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs = splitter.split_documents(docs)

    chunk_ids_all = [f"{chunk_prefix}_{i}" for i in range(len(docs))]
    present_ids = [cid for cid in chunk_ids_all if cid in existing_ids]

    existing_map: Dict[str, Dict[str, Any]] = {}
    if present_ids:
        res = collection.get(ids=present_ids, include=["metadatas", "embeddings"])
        fetched_ids = res.get("ids", [])
        fetched_metas = res.get("metadatas", [])
        fetched_embs = res.get("embeddings", [])

        flat_ids = []
        for item in fetched_ids:
            flat_ids.extend(item if isinstance(item, list) else [item])

        for idx, cid in enumerate(present_ids):
            meta = fetched_metas[idx] if idx < len(fetched_metas) else None
            emb = fetched_embs[idx] if idx < len(fetched_embs) else None
            meta = unwrap_first_level(meta)
            emb = unwrap_first_level(emb)
            if isinstance(meta, list) and len(meta) > 0:
                meta = meta[0]
            existing_map[cid] = {"metadata": meta or {}, "embedding": emb}

    texts_to_add, embeddings_to_add, ids_to_add, metadatas_to_add = [], [], [], []
    new_texts, new_texts_idx = [], []

    for i, doc in enumerate(docs):
        chunk_id = f"{chunk_prefix}_{i}"
        base_metadata = build_metadata(file_path, file_path.name, category, i, len(doc.page_content))
        if not len(doc.page_content):
            print(f"Empty text at chunk {i}, skipping")
        if chunk_id in existing_map:
            existing_meta = existing_map[chunk_id]["metadata"] or {}
            for k, v in base_metadata.items():
                if k not in existing_meta or existing_meta.get(k) in (None, ""):
                    existing_meta[k] = v
            final_meta = existing_meta
            final_emb = existing_map[chunk_id]["embedding"]

            ids_to_add.append(chunk_id)
            texts_to_add.append(doc.page_content)
            embeddings_to_add.append(final_emb)
            metadatas_to_add.append(final_meta)
        else:
            ids_to_add.append(chunk_id)
            texts_to_add.append(doc.page_content)
            metadatas_to_add.append(base_metadata)
            embeddings_to_add.append(None)
            new_texts_idx.append(len(embeddings_to_add) - 1)
            new_texts.append(doc.page_content)

    if new_texts:
        if model[0] is None:  # model is a list wrapper to allow lazy init
            print("Loading embedding model (lazy)...")
            model[0] = safe_load_sentence_transformer(model_name)
        new_embs = model[0].encode(new_texts, show_progress_bar=True)
        for pos, emb in zip(new_texts_idx, new_embs):
            embeddings_to_add[pos] = emb

    new_ids = [cid for cid in ids_to_add if cid not in existing_map]
    if new_ids:
        idxs = [ids_to_add.index(cid) for cid in new_ids]
        collection.add(
            documents=[texts_to_add[i] for i in idxs],
            embeddings=[embeddings_to_add[i] for i in idxs],
            ids=[ids_to_add[i] for i in idxs],
            metadatas=[metadatas_to_add[i] for i in idxs]
        )

    existing_ids_to_update = [cid for cid in ids_to_add if cid in existing_map]
    if existing_ids_to_update:
        idxs = [ids_to_add.index(cid) for cid in existing_ids_to_update]
        collection.update(
            ids=[ids_to_add[i] for i in idxs],
            metadatas=[metadatas_to_add[i] for i in idxs]
        )


# --- PDF handler ---
def process_pdf_file(pdf_file, category, collection, existing_ids, model, model_name, chunk_size, chunk_overlap):
    loader = PyPDFLoader(str(pdf_file))
    pages = loader.load()
    process_documents(pages, pdf_file, category, collection, existing_ids, model, model_name, pdf_file.stem, chunk_size, chunk_overlap)


# --- CSV handler ---
def process_csv_file(csv_file, category, collection, existing_ids, model, model_name, chunk_size, chunk_overlap):
    loader = CSVLoader(str(csv_file), encoding="utf-8")
    rows = loader.load()
    process_documents(rows, csv_file, category, collection, existing_ids, model, model_name, csv_file.stem, chunk_size, chunk_overlap)
