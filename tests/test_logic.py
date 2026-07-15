"""Tests locaux (hors réseau) pour valider la logique sans dépendre des sites en ligne."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scraper.base import find_first_date, detect_contract_type, detect_contract_duration, make_offer_id, clean_text, truncate
from matcher import score_offer, filter_and_rank
from state import merge_into_history, split_new_offers

def test_dates():
    assert find_first_date("Date limite : 08/08/2026") == "2026-08-08"
    assert find_first_date("13-07-2026 - CDI") == "2026-07-13"
    assert find_first_date("Date fin de candidature 02 Août 2026") == "2026-08-02"
    assert find_first_date("rien ici") is None
    print("OK test_dates")

def test_contract():
    assert detect_contract_type("Volontaire de Service Civique (VSC)") == "Service civique"
    assert detect_contract_type("CDD - Contrat de projet 18 mois") == "CDD"
    assert detect_contract_type("Stage de fin d'études") == "Stage"
    assert detect_contract_duration("CDD de 18 mois") == "18 mois"
    print("OK test_contract")

def test_offer_id_stable():
    id1 = make_offer_id("ofb", "https://ofb.gestmax.fr/4538/1/x", "Chargé de mission")
    id2 = make_offer_id("ofb", "https://ofb.gestmax.fr/4538/1/x", "Chargé de mission")
    id3 = make_offer_id("ofb", "https://ofb.gestmax.fr/4539/1/y", "Autre offre")
    assert id1 == id2
    assert id1 != id3
    print("OK test_offer_id_stable")

def test_scoring():
    offer_marine = {
        "title": "Chargé.e de mission pêche, aquaculture, poissons",
        "summary": "Suivi des populations d'oiseaux marins et manchots en terres australes (TAAF)",
        "raw_text": "", "location": "Crozet", "contract_type": "Service civique",
    }
    offer_unrelated = {
        "title": "Gestionnaire financier", "summary": "Comptabilité et paye",
        "raw_text": "", "location": "Paris", "contract_type": "CDI",
    }
    s1 = score_offer(offer_marine)
    s2 = score_offer(offer_unrelated)
    assert s1 > s2
    assert s1 >= 3
    print(f"OK test_scoring (marine={s1}, unrelated={s2})")

def test_filter_and_rank_sorts_desc():
    offers = [
        {"title": "Gestionnaire financier", "summary": "", "raw_text": "", "location": "", "contract_type": "CDI"},
        {"title": "Manchot royal ecologie marine ornithologie", "summary": "TAAF Crozet hivernage",
         "raw_text": "", "location": "Crozet", "contract_type": "Service civique"},
    ]
    ranked = filter_and_rank(offers)
    assert len(ranked) == 1
    assert ranked[0]["title"].startswith("Manchot")
    print("OK test_filter_and_rank_sorts_desc")

def test_dedup_and_history_merge():
    seen = {}
    offers = [{"offer_id": "a1", "title": "Offre 1"}, {"offer_id": "a2", "title": "Offre 2"}]
    new1, seen = split_new_offers(offers, seen)
    assert len(new1) == 2
    # deuxième run : mêmes offres -> plus aucune "nouvelle"
    new2, seen = split_new_offers(offers, seen)
    assert len(new2) == 0

    history = []
    history = merge_into_history(offers, history, search_date="2026-07-15")
    assert len(history) == 2
    assert all(o["date_depot"] == "2026-07-15" for o in history)
    # deuxième jour : une offre en moins, une offre déjà connue -> date_depot ne doit pas changer
    history = merge_into_history([offers[0]], history, search_date="2026-07-16")
    by_id = {o["offer_id"]: o for o in history}
    assert by_id["a1"]["date_depot"] == "2026-07-15"
    assert by_id["a1"]["search_date"] == "2026-07-16"
    assert by_id["a2"]["search_date"] == "2026-07-15"  # pas revue ce jour -> date de recherche inchangée
    print("OK test_dedup_and_history_merge")

if __name__ == "__main__":
    test_dates()
    test_contract()
    test_offer_id_stable()
    test_scoring()
    test_filter_and_rank_sorts_desc()
    test_dedup_and_history_merge()
    print("\nTous les tests locaux sont passés ✅")
