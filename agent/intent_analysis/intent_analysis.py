from pydantic import BaseModel
import re
from transformers import pipeline, AutoTokenizer
# =======================
# 🔹 Initialisation
# =======================
# Force use of the slow tokenizer (SentencePiece)
tokenizer = AutoTokenizer.from_pretrained(
    "joeddav/xlm-roberta-large-xnli",
    use_fast=False  # ⬅️ key fix here
)

classifier = pipeline(
    "zero-shot-classification",
    model="joeddav/xlm-roberta-large-xnli",
    tokenizer=tokenizer
)
INTENT_LABELS = [
    "intérêt global",
    "intérêt spécifique",
    "demande d'explication"
]

PRODUCT_LABELS = [
    "assurance auto",
    "assurance vie",
    "assurance santé",
    "assurance voyage",
    "assurance habitation",
    "assurance retraite"
]

PRODUCT_KEYWORDS = {
    "auto": "assurance auto",
    "voiture": "assurance auto",
    "vie": "assurance vie",
    "santé": "assurance santé",
    "maladie": "assurance santé",
    "médecin": "assurance santé",
    "voyage": "assurance voyage",
    "habitation": "assurance habitation",
    "maison": "assurance habitation",
    "logement": "assurance habitation",
    "retraite": "assurance retraite",
    "pension": "assurance retraite"
}

def detect_products_in_text(text):
    """Retourne tous les produits détectés dans un texte (utile pour comparaison, hésitation, multi-intérêt)."""
    found = []
    for k, v in PRODUCT_KEYWORDS.items():
        if re.search(rf"\b{k}\b", text.lower()):
            if v not in found:
                found.append(v)
    return found


def analyse_message(text, threshold=0.7):
    txt = text.lower()

    # Cas explicites
    if re.search(r"\b(pas|aucun|non|refuse|merci)\b", txt):
        return {"texte": text, "intention": {"label": "pas d'intérêt", "score": 1.0},
                "produit": {"label": "aucun", "score": 0.0}}

    if re.search(r"(pas sûr|hésite|réfléchir|décider plus tard|je verrai|je suis hésité)", txt):
        produits = detect_products_in_text(txt)
        return {"texte": text, "intention": {"label": "hésité", "score": 1.0},
                "produit": {"label": produits if produits else "aucun", "score": 1.0}}

    if re.search(r"(déjà|j’ai une autre assurance|suis couvert|assuré ailleurs)", txt):
        return {"texte": text, "intention": {"label": "déjà assuré", "score": 1.0},
                "produit": {"label": detect_products_in_text(txt) or "aucun", "score": 1.0}}

    if not re.search(r"assurance|auto|vie|santé|voyage|habitation|retraite|pension|devis|différence|comparer", txt):
        return {"texte": text, "intention": {"label": "autre sujet", "score": 1.0},
                "produit": {"label": "aucun", "score": 0.0}}

    # Cas spéciaux → comparaison / devis
    if re.search(r"(différence|comparer|comparaison)", txt):
        produits = detect_products_in_text(txt)
        return {"texte": text, "intention": {"label": "comparaison", "score": 1.0},
                "produit": {"label": produits if produits else "inconnu", "score": 1.0}}

    if re.search(r"(devis|tarif|prix|coût)", txt):
        produits = detect_products_in_text(txt)
        return {"texte": text, "intention": {"label": "devis", "score": 1.0},
                "produit": {"label": produits if produits else "inconnu", "score": 1.0}}

    # Vérification produit par regex
    forced_products = detect_products_in_text(txt)
    if forced_products:
        return {"texte": text, "intention": {"label": "intérêt spécifique", "score": 1.0},
                "produit": {"label": forced_products if len(forced_products) > 1 else forced_products[0],
                            "score": 1.0}}

    # Sinon → modèle ML
    intent_result = classifier(text, INTENT_LABELS, hypothesis_template="Ce client exprime {}.")
    intent, intent_score = intent_result["labels"][0], intent_result["scores"][0]

    produit, produit_score = "aucun", 0.0
    if intent == "intérêt spécifique" and intent_score >= threshold:
        product = classifier(text, PRODUCT_LABELS,
                             hypothesis_template="Ce client est intéressé par {}.")
        produit, produit_score = product["labels"][0], product["scores"][0]

        if produit_score < threshold:
            intent = "intérêt global"
            produit, produit_score = "aucun", 0.0

    return {
        "texte": text,
        "intention": {"label": intent, "score": round(float(intent_score), 3)},
        "produit": {"label": produit, "score": round(float(produit_score), 3)}
    }

