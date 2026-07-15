"""
Gestion de l'état persistant entre deux exécutions du bot :
- quelles offres ont déjà été vues (pour ne pas les renvoyer par mail chaque jour)
- l'historique complet des offres (utilisé par le dashboard)

Le fichier data/seen_offers.json est commité dans le dépôt Git par le workflow
GitHub Actions après chaque exécution, ce qui permet de garder la mémoire d'un
run à l'autre (GitHub Actions ne persiste rien d'autre par défaut).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

SEEN_OFFERS_PATH = os.path.join("data", "seen_offers.json")
ALL_OFFERS_PATH = os.path.join("docs", "offers.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_seen_offers() -> dict:
    if not os.path.exists(SEEN_OFFERS_PATH):
        return {}
    try:
        with open(SEEN_OFFERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_seen_offers(seen: dict) -> None:
    os.makedirs(os.path.dirname(SEEN_OFFERS_PATH), exist_ok=True)
    with open(SEEN_OFFERS_PATH, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2, sort_keys=True)


def load_all_offers() -> list[dict]:
    if not os.path.exists(ALL_OFFERS_PATH):
        return []
    try:
        with open(ALL_OFFERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_all_offers(offers: list[dict]) -> None:
    os.makedirs(os.path.dirname(ALL_OFFERS_PATH), exist_ok=True)
    with open(ALL_OFFERS_PATH, "w", encoding="utf-8") as f:
        json.dump(offers, f, ensure_ascii=False, indent=2, sort_keys=True)


def split_new_offers(offers: list[dict], seen: dict) -> tuple[list[dict], dict]:
    """Sépare les offres jamais vues des autres. Met à jour (sans sauvegarder) le dict `seen`."""
    new_offers = []
    today = _now_iso()
    for offer in offers:
        offer_id = offer["offer_id"]
        if offer_id not in seen:
            new_offers.append(offer)
            seen[offer_id] = {
                "first_seen": today,
                "title": offer.get("title", ""),
                "site_id": offer.get("site_id", ""),
            }
    return new_offers, seen


def merge_into_history(current_run_offers: list[dict], history: list[dict], search_date: str) -> list[dict]:
    """
    Fusionne les offres du run du jour dans l'historique complet utilisé par le dashboard :
    - une offre déjà connue voit sa 'date de recherche' (dernière fois vue) mise à jour
    - une offre nouvelle est ajoutée avec sa 'date de dépôt' (première fois vue par le bot)
    """
    by_id = {o["offer_id"]: o for o in history}
    for offer in current_run_offers:
        oid = offer["offer_id"]
        if oid in by_id:
            existing = by_id[oid]
            existing["search_date"] = search_date
            # Garde la date de dépôt d'origine, mais rafraîchit le reste (au cas où
            # la description / date de clôture aurait été mise à jour sur le site source)
            date_depot = existing.get("date_depot", search_date)
            existing.update(offer)
            existing["date_depot"] = date_depot
            existing["search_date"] = search_date
        else:
            offer = dict(offer)
            offer["date_depot"] = search_date
            offer["search_date"] = search_date
            by_id[oid] = offer
    return list(by_id.values())
