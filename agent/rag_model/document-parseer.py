import chromadb
from typing import Any, Dict
import os
import sys
import signal
import atexit
import logging
import torch

from utils import fetch_all_existing_ids, process_pdf_file, process_csv_file
from config import *


# --- Init Chroma ---
chroma_client = chromadb.HttpClient(host="localhost", port=8000)
collection = chroma_client.get_or_create_collection(name="legal_docs")

# Existing IDs
existing_ids = fetch_all_existing_ids(collection)

# Lazy model wrapper
model = [None]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
# --- Process PDFs ---
pdf_files = list(PDF_DIR.rglob("*.pdf"))
print(f"Found {len(pdf_files)} PDF(s).")

def cleanup_resources():
    """Clear cache and release resources from libraries and tools."""
    logging.info("Cleaning up resources...")

    # Hugging Face / Transformers / Torch cleanup
    if torch is not None:
        try:
            torch.cuda.empty_cache()
            logging.info("Cleared torch CUDA cache.")
        except Exception as e:
            logging.warning(f"Failed to clear torch cache: {e}")

    # Add other libraries here if needed
    # Example: closing DB connections, shutting down Chroma, etc.

    logging.info("Cleanup completed.")

# Ensure cleanup is always called at exit
atexit.register(cleanup_resources)
for pdf_file in pdf_files:
    try:
        raw_category = pdf_file.parent.name
        code = "-".join(raw_category.split("-")[1:]) if "-" in raw_category else raw_category
        category = CATEGORY_MAP.get(code, code)
        print(f"\nProcessing PDF: {pdf_file}")
        process_pdf_file(pdf_file, category, collection, existing_ids, model, MODEL_NAME, CHUNK_SIZE, CHUNK_OVERLAP)
    except KeyboardInterrupt:
        logging.warning("Interrupted by user (Ctrl+C). Exiting gracefully...")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


# --- Process CSVs ---
csv_files = list(CSV_DIR.rglob("*.csv"))
print(f"\nFound {len(csv_files)} CSV(s).")

for csv_file in csv_files:
    try:
        raw_category = csv_file.parent.name
        code = "-".join(raw_category.split("-")[1:]) if "-" in raw_category else raw_category
        category = CATEGORY_MAP.get(code, code) if raw_category else "CSV Data"
        print(f"\nProcessing CSV: {csv_file}")
        process_csv_file(csv_file, category, collection, existing_ids, model, MODEL_NAME, CHUNK_SIZE, CHUNK_OVERLAP)
    except KeyboardInterrupt:
        logging.warning("Interrupted by user (Ctrl+C). Exiting gracefully...")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)

print("\n✅ All PDFs and CSVs processed and embedded (metadata merged/upserted).")