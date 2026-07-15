"""
Calcule un score de pertinence pour chaque offre par rapport au profil de Lucile,
et ne retient que celles au-dessus du seuil configuré.
"""
from __future__ import annotations

from config.settings import (
    MIN_SCORE_TO_NOTIFY,
    NEGATIVE_KEYWORDS,
    POSITIVE_KEYWORDS,
    WANTED_CONTRACT_TYPES,
)


def score_offer(offer: dict) -> int:
    """Renvoie un score entier. Plus il est élevé, plus l'offre est pertinente."""
    haystack = " ".join([
        offer.get("title", ""),
        offer.get("summary", ""),
        offer.get("raw_text", ""),
        offer.get("location", ""),
    ]).lower()

    score = 0
    for keyword, weight in POSITIVE_KEYWORDS.items():
        if keyword in haystack:
            score += weight

    for keyword, weight in NEGATIVE_KEYWORDS.items():
        if keyword in haystack:
            score -= weight

    contract = (offer.get("contract_type") or "").lower()
    if any(w in contract for w in WANTED_CONTRACT_TYPES):
        score += 2

    return score


def filter_and_rank(offers: list[dict]) -> list[dict]:
    """Ajoute le score à chaque offre, filtre selon le seuil, trie du plus au moins pertinent."""
    scored = []
    for offer in offers:
        s = score_offer(offer)
        if s >= MIN_SCORE_TO_NOTIFY:
            offer = dict(offer)
            offer["relevance_score"] = s
            scored.append(offer)
    scored.sort(key=lambda o: o["relevance_score"], reverse=True)
    return scored
