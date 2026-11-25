"""
Compliance check on a drafted message, before it is stored as `pending`.

The check never sends or blocks anything by itself: every message still waits for the
admin verdict. Its issues are surfaced in the argumentation shown on the dashboard.
"""

import re
from typing import Dict, List

FORBIDDEN_PATTERNS = {
    "absolute_guarantee": r"garanti[e]?s?\s+(à|a)\s*100\s*%|sans\s+aucun\s+risque|aucune\s+exclusion",
    "unverifiable_superlative": r"meilleur(e)?\s+(prix|offre)\s+du\s+march[ée]|imbattable",
    "pressure": r"derni[eè]re\s+chance|offre\s+expire\s+(aujourd'hui|ce\s+soir)",
}
# amounts and rates must come from the RAG context or the customer data, never from the LLM
FIGURE_RE = re.compile(r"\b\d[\d\s.,]*\s*(?:dt|tnd|dinars?|%|€)", re.IGNORECASE)


def _normalize_figure(s: str) -> str:
    return re.sub(r"[\s.,]", "", s.lower())


def check_message(response: str, rag_context: str, user_data_str: str,
                  sources: List[Dict], use_rag: bool) -> Dict:
    issues = []
    text = (response or "").strip()
    if not text:
        issues.append("empty_message")
    lowered = text.lower()
    for code, pattern in FORBIDDEN_PATTERNS.items():
        if re.search(pattern, lowered):
            issues.append(code)

    grounded = _normalize_figure(f"{rag_context} {user_data_str}")
    for figure in FIGURE_RE.findall(text):
        digits = re.sub(r"\D", "", figure)
        if digits and digits not in re.sub(r"\D", " ", grounded).split() \
                and _normalize_figure(figure) not in grounded:
            issues.append(f"unsupported_figure:{figure.strip()}")

    if use_rag and not sources:
        issues.append("no_supporting_sources")
    return {"passed": not issues, "issues": issues}
