from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb
from datetime import datetime
from typing import Any, Dict

# --- CONFIG ---
PDF_DIR = Path("./data/french_docs")  # PDF root folder
MODEL_NAME = "intfloat/multilingual-e5-large"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# --- Mapping folder codes to full category names ---
CATEGORY_MAP = {
    "CG-Vie": "Assurance Vie",
    "CG-Santé": "Assurance Santé",
    "CG-Transport": "Assurance Transport",
    "CG-IARD": "Assurance IARD",
    "CG-Engineering": "Assurance Engineering",
    "CG-Automobile": "Assurance Automobile"
}

# --- Init Chroma vector DB ---
chroma_client = chromadb.HttpClient(host="localhost", port=8000)
collection = chroma_client.get_or_create_collection(name="legal_docs")

# --- Helper to safely flatten/get existing ids from collection.get(...) ---
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


existing_ids = fetch_all_existing_ids(collection)

# --- Utility to unpack Chroma get results robustly ---
def unwrap_first_level(x: Any):
    """
    Chroma returns nested lists in some endpoints; this makes sure we always get
    the first-level item.
    """
    if x is None:
        return None
    if isinstance(x, list) and len(x) > 0:
        first = x[0]
        # if first is a list, return its first element
        if isinstance(first, list) and len(first) > 0:
            return first[0]
        return first
    return x

# Delay model loading until needed
model = None

# --- Process PDFs ---
pdf_files = list(PDF_DIR.rglob("*.pdf"))
print(f"Found {len(pdf_files)} PDF(s) in {PDF_DIR} and subdirectories.")

for pdf_file in pdf_files:
    print(f"\nProcessing {pdf_file}...")
    try:
        # Determine category
        raw_category = pdf_file.parent.name  # e.g., "1-CG-Vie"
        code = "-".join(raw_category.split("-")[1:]) if "-" in raw_category else raw_category
        category = CATEGORY_MAP.get(code, code)

        # Load PDF and split into docs
        loader = PyPDFLoader(str(pdf_file))
        pages = loader.load()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )
        docs = splitter.split_documents(pages)

        # Precompute all chunk ids for this pdf
        chunk_ids_all = [f"{pdf_file.stem}_{i}" for i in range(len(docs))]

        # Determine which of these already exist
        present_ids = [cid for cid in chunk_ids_all if cid in existing_ids]

        # Batch-fetch existing metadata + embeddings for present ids (if any)
        existing_map: Dict[str, Dict[str, Any]] = {}
        if present_ids:
            res = collection.get(ids=present_ids, include=["metadatas", "embeddings"])
            # res fields should correspond in order to present_ids
            fetched_ids = res.get("ids", [])
            fetched_metas = res.get("metadatas", [])
            fetched_embs = res.get("embeddings", [])

            # normalize fetched_ids to flat list
            flat_ids = []
            for item in fetched_ids:
                if isinstance(item, list):
                    flat_ids.extend(item)
                else:
                    flat_ids.append(item)

            # map them with index safe extraction
            for idx, cid in enumerate(present_ids):
                # metadata and embeddings may be nested, unwrap gracefully
                meta = None
                emb = None
                try:
                    meta = fetched_metas[idx]
                except Exception:
                    meta = unwrap_first_level(fetched_metas)
                try:
                    emb = fetched_embs[idx]
                except Exception:
                    emb = unwrap_first_level(fetched_embs)
                # ensure meta is a dict
                if isinstance(meta, list) and len(meta) > 0:
                    meta = meta[0]
                existing_map[cid] = {"metadata": meta or {}, "embedding": emb}

        # Prepare lists to upsert (both new and existing with updated metadata)
        texts_to_add = []
        embeddings_to_add = []
        ids_to_add = []
        metadatas_to_add = []

        # Collect texts that are new (for batch embedding) and track their target index
        new_texts = []
        new_texts_idx = []  # positions in final lists where these new embeddings should go

        for i, doc in enumerate(docs):
            chunk_id = f"{pdf_file.stem}_{i}"
            base_metadata = {
                "source": str(pdf_file),
                "filename": pdf_file.name,
                "category": category,
                "chunk_index": i,
                "chunk_length": len(doc.page_content),
                "added_at": datetime.utcnow().isoformat()
            }

            if chunk_id in existing_map:
                # Merge missing fields into existing metadata
                existing_meta = existing_map[chunk_id]["metadata"] or {}
                for k, v in base_metadata.items():
                    if k not in existing_meta or existing_meta.get(k) in (None, ""):
                        existing_meta[k] = v
                final_meta = existing_meta
                final_emb = existing_map[chunk_id]["embedding"]

                # Append to upsert lists using existing embedding (no recompute)
                ids_to_add.append(chunk_id)
                texts_to_add.append(doc.page_content)
                embeddings_to_add.append(final_emb)
                metadatas_to_add.append(final_meta)

            else:
                # New chunk: add placeholder and schedule for batch embedding
                ids_to_add.append(chunk_id)
                texts_to_add.append(doc.page_content)
                metadatas_to_add.append(base_metadata)
                # placeholder for embedding, will fill after encoding
                embeddings_to_add.append(None)
                new_texts_idx.append(len(embeddings_to_add) - 1)
                new_texts.append(doc.page_content)

        # If there are new texts, load model lazily and encode in batch
        if new_texts:
            if model is None:
                print("Loading embedding model (lazy)...")
                model = SentenceTransformer(MODEL_NAME)
            print(f"Encoding {len(new_texts)} new chunk(s)...")
            new_embs = model.encode(new_texts, show_progress_bar=True)

            # fill embeddings_to_add placeholders
            for pos, emb in zip(new_texts_idx, new_embs):
                embeddings_to_add[pos] = emb

        # Finally, upsert all ids for this PDF (this will add new chunks and overwrite metadata for existing ones)
        # Upsert new chunks
        new_ids = [cid for cid in ids_to_add if cid not in existing_map]
        if new_ids:
            idxs = [ids_to_add.index(cid) for cid in new_ids]
            collection.add(
                documents=[texts_to_add[i] for i in idxs],
                embeddings=[embeddings_to_add[i] for i in idxs],
                ids=[ids_to_add[i] for i in idxs],
                metadatas=[metadatas_to_add[i] for i in idxs]
            )

        # Update metadata for existing chunks
        existing_ids_to_update = [cid for cid in ids_to_add if cid in existing_map]
        if existing_ids_to_update:
            idxs = [ids_to_add.index(cid) for cid in existing_ids_to_update]
            collection.update(
                ids=[ids_to_add[i] for i in idxs],
                metadatas=[metadatas_to_add[i] for i in idxs]
            )
            
        else:
            print("No chunks to upsert for this file.")

    except Exception as e:
        print(f"❌ Failed to process {pdf_file}: {e}")

print("\n✅ All documents processed and embedded (metadata merged/upserted).")
