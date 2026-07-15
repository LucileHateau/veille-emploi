"""
Point d'entrée du bot. Exécuté chaque jour par GitHub Actions (voir
.github/workflows/daily.yml), mais peut aussi être lancé à la main :

    python main.py                  # exécution complète (scrape + mail + dashboard)
    python main.py --dry-run        # scrape + affiche ce qui serait envoyé, sans envoyer de mail
    python main.py --site ofb       # ne teste qu'un seul site (pratique pour déboguer un scraper)
    python main.py --site ofb --debug   # affiche le détail des offres brutes trouvées
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from config.settings import SITES
from emailer import send_digest_email
from matcher import filter_and_rank
from scraper.base import FetchError
from scraper.base import make_offer_id
from scraper.sites import SCRAPERS
from state import (
    load_all_offers,
    load_seen_offers,
    merge_into_history,
    save_all_offers,
    save_seen_offers,
    split_new_offers,
)


def today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def run_site(site: dict, debug: bool = False) -> list[dict]:
    if not site.get("enabled", True) or not site.get("scraper"):
        return []
    scraper_fn = SCRAPERS.get(site["scraper"])
    if scraper_fn is None:
        print(f"⚠️  [{site['id']}] scraper '{site['scraper']}' introuvable dans scraper/sites.py")
        return []

    print(f"→ [{site['id']}] {site['name']} … ", end="", flush=True)
    try:
        offers = scraper_fn(site)
    except FetchError as exc:
        print(f"ÉCHEC ({exc})")
        return []
    except Exception as exc:  # défensif : un site qui plante ne doit jamais arrêter les autres
        print(f"ERREUR INATTENDUE ({exc.__class__.__name__}: {exc})")
        return []

    print(f"{len(offers)} offre(s) brute(s)")
    if debug:
        for o in offers[:20]:
            print(f"    - {o['title'][:90]!r}  |  {o['link']}")
        if len(offers) > 20:
            print(f"    … et {len(offers) - 20} de plus")

    for offer in offers:
        offer["offer_id"] = make_offer_id(offer["site_id"], offer.get("link", ""), offer.get("title", ""))
    return offers


def main() -> int:
    parser = argparse.ArgumentParser(description="Bot de veille emploi de Lucile.")
    parser.add_argument("--site", help="Ne scraper qu'un seul site (par son 'id' dans config/settings.py)")
    parser.add_argument("--dry-run", action="store_true", help="N'envoie pas de mail, affiche juste le résultat")
    parser.add_argument("--debug", action="store_true", help="Affiche le détail des offres brutes trouvées")
    args = parser.parse_args()

    sites_to_run = SITES
    if args.site:
        sites_to_run = [s for s in SITES if s["id"] == args.site]
        if not sites_to_run:
            print(f"Site inconnu : {args.site!r}. Ids disponibles : {[s['id'] for s in SITES]}")
            return 1

    all_raw_offers: list[dict] = []
    for site in sites_to_run:
        all_raw_offers.extend(run_site(site, debug=args.debug))

    print(f"\nTotal brut : {len(all_raw_offers)} offre(s) sur {len(sites_to_run)} site(s).")

    relevant = filter_and_rank(all_raw_offers)
    print(f"Offres jugées pertinentes (score suffisant) : {len(relevant)}")

    seen = load_seen_offers()
    new_offers, seen = split_new_offers(relevant, seen)
    print(f"Dont NOUVELLES (jamais notifiées) : {len(new_offers)}")

    if args.debug or args.dry_run:
        for o in new_offers:
            print(f"  🆕 [{o['relevance_score']}] {o['title']}  →  {o['link']}")

    if args.dry_run:
        print("\n--dry-run : aucun mail envoyé, aucun fichier modifié.")
        return 0

    # Historique complet (utilisé par le dashboard) : on y intègre TOUTES les offres
    # pertinentes du run (pas seulement les nouvelles), pour rafraîchir les dates.
    history = load_all_offers()
    history = merge_into_history(relevant, history, search_date=today_iso())
    save_all_offers(history)

    save_seen_offers(seen)

    send_digest_email(new_offers)

    return 0


if __name__ == "__main__":
    sys.exit(main())
