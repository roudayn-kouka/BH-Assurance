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
PATTERNS = {
    # Clear refusals or no interest
    "pas d'intérêt": (
        r"(pas\s+d['e]\s*(interet|besoin)|"
        r"\baucun(e)?\b|"
        r"pas\s*(du tout|interess[eé])|"
        r"(ça|cela)\s+ne\s+m['’]interess(e|e pas)|"
        r"\bnon\s+merci\b|"
        r"\brefus[eé]?\b|"
        r"\b(j['’]en veux pas|je n['’]ai pas besoin|inutile)\b)",
        0.95
    ),

    # Hesitation or deferral
    "hésité": (
        r"(pas\s*s[uû]r(e)?|"
        r"h[eé]site(r|z)?|"
        r"je\s*(vais|veux)?\s*y\s*r[eé]fl[eé]chir|"
        r"je\s*(vais|voudrais)?\s*d[eé]cider plus tard|"
        r"(je|on)\s+verra|"
        r"je\s*(vais|voudrais)?\s*y penser|"
        r"(besoin|donner)\s+du\s+temps|"
        r"\bj'y pense encore\b)",
        0.8
    ),

    # Already covered by another insurance
    "déjà assuré": (
        r"(d[eé]j[aà]|"
        r"(j['’]ai|nous avons)\s+une\s+autre\s+assurance|"
        r"assur[eé]\s+ailleurs|"
        r"je\s+suis\s+couvert|"
        r"(j['’]ai|nous avons)\s+une\s+couverture|"
        r"(mon|ma)\s+(banque|employeur)\s+me\s+couvre|"
        r"assur[eé]\s+autrement)",
        0.9
    ),

    # Requests for comparison
    "comparaison": (
        r"(diff[eé]rence(s)?|"
        r"comparer|comparaison|"
        r"(faire|avoir)\s+un\s+comparatif|"
        r"(quelle|quelles)\s+sont\s+les\s+options|"
        r"(qu['’]est-ce qui)\s+change)",
        0.9
    ),

    # Requests for a quote / pricing
    "devis": (
        r"(devis|"
        r"tarif(s)?|"
        r"prix|cout|co[uû]t|"
        r"combien\s+(ça|cela)\s+co[uû]te|"
        r"estimation|"
        r"montant|"
        r"offre\s+de\s+prix)",
        0.9
    ),
}