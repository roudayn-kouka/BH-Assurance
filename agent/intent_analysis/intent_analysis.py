import re
import logging
from .config import *
import unicodedata

from transformers import pipeline, AutoTokenizer

def initialize_classifier():
    """Initialize the classifier with proper error handling."""
    try:
        # Try with use_fast=False first
        tokenizer = AutoTokenizer.from_pretrained(
            "joeddav/xlm-roberta-large-xnli",
            use_fast=False,
            trust_remote_code=False
        )
        
        classifier = pipeline(
            "zero-shot-classification",
            model="joeddav/xlm-roberta-large-xnli",
            tokenizer=tokenizer,
            device=-1  # Force CPU usage to avoid GPU issues
        )
        return classifier, True
        
    except Exception as e:
        print(f"Warning: Failed to load XLM-RoBERTa model: {e}")
        try:
            # Fallback to a simpler model
            classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=-1
            )
            print("Using BART model as fallback")
            return classifier, True
            
        except Exception as e2:
            print(f"Error: Failed to load any classification model: {e2}")
            return None, False

# Configure logging
logging.getLogger("transformers").setLevel(logging.ERROR)


# Initialize the classifier
classifier, model_available = initialize_classifier()

def detect_products_in_text(text):
    """Retourne tous les produits détectés dans un texte (utile pour comparaison, hésitation, multi-intérêt)."""
    found = []
    for k, v in PRODUCT_KEYWORDS.items():
        if re.search(rf"\b{k}\b", text.lower()):
            if v not in found:
                found.append(v)
    return found

def normalize_text(text):
    text = text.lower().strip()
    text = ''.join(c for c in unicodedata.normalize('NFD', text)
                   if unicodedata.category(c) != 'Mn')  # remove accents
    return text

def analyse_message(text, threshold=0.7):
    txt = normalize_text(text)

    # --- Rule-based intent detection ---
    for intent, (pattern, score) in PATTERNS.items():
        if re.search(pattern, txt):
            produits = detect_products_in_text(txt)
            return {
                "texte": text,
                "intention": {"label": intent, "score": score},
                "produit": {"label": produits[0] if produits else "aucun", "score": 1.0 if produits else 0.0}
            }

    # --- Product-specific interest ---
    produits = detect_products_in_text(txt)
    if produits:
        return {
            "texte": text,
            "intention": {"label": "intérêt spécifique", "score": 0.85},
            "produit": {"label": produits[0], "score": 0.9}
        }

    # --- Fallback: ML classifier if available ---
    intent, intent_score, produit, produit_score = "intérêt global", 0.7, "aucun", 0.0
    if model_available and classifier is not None:
        try:
            result = classifier(text, INTENT_LABELS, hypothesis_template="Ce client exprime {}.")
            intent, intent_score = result["labels"][0], float(result["scores"][0])

            if intent == "intérêt spécifique" and intent_score >= threshold:
                product_result = classifier(text, PRODUCT_LABELS, hypothesis_template="Ce client est intéressé par {}.")
                produit, produit_score = product_result["labels"][0], float(product_result["scores"][0])
        except Exception as e:
            print(f"[Warning] ML model failed, using fallback: {e}")

    return {
        "texte": text,
        "intention": {"label": intent, "score": round(intent_score, 3)},
        "produit": {"label": produit, "score": round(produit_score, 3)}
    }
