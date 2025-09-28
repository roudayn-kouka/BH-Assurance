from pathlib import Path

PDF_DIR = Path("./data/french_docs")
CSV_DIR = Path("./data/csv_docs")

MODEL_NAME = "intfloat/multilingual-e5-large"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

CATEGORY_MAP = {
    "CG-Vie": "Assurance Vie",
    "CG-Santé": "Assurance Santé",
    "CG-Transport": "Assurance Transport",
    "CG-IARD": "Assurance IARD",
    "CG-Engineering": "Assurance Engineering",
    "CG-Automobile": "Assurance Automobile"
}

