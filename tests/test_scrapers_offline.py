"""
Tests hors-ligne des scrapers : on fournit du HTML de synthèse qui reproduit fidèlement
la structure réellement observée sur chaque site (tableaux, cartes, accordéon...), et on
vérifie que le parsing produit bien les champs attendus.

Ces tests ne remplacent pas une vérification ponctuelle sur les vrais sites (à faire après
le premier déploiement, voir README section Dépannage), mais garantissent que la logique
de parsing elle-même est correcte.
"""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bs4 import BeautifulSoup
import scraper.sites as sites_mod

FAKE_SITE = lambda **kw: {"id": "x", "name": "X", "url": "https://example.org", **kw}


def with_html(html):
    return BeautifulSoup(html, "html.parser")


def test_ofb_gestmax():
    html = """
    <table>
      <tr><th>Titre</th><th>Catégorie</th><th>Affectation</th>
          <th>Résidence administrative</th><th>Date limite de candidature</th></tr>
      <tr>
        <td><a href="/4538/1/charge-e-de-mission-peche">Chargé.e de mission pêche, aquaculture, poissons</a></td>
        <td>A</td>
        <td>Direction régionale Normandie</td>
        <td>Le Havre</td>
        <td><a href="/4538/1/charge-e-de-mission-peche">07/08/2026</a></td>
      </tr>
    </table>
    """
    with patch.object(sites_mod, "fetch_html", return_value=with_html(html)):
        offers = sites_mod.scrape_ofb_gestmax(FAKE_SITE(url="https://ofb.gestmax.fr/search"))
    assert len(offers) == 1
    o = offers[0]
    assert "pêche" in o["title"].lower()
    assert o["link"] == "/4538/1/charge-e-de-mission-peche"
    assert o["deadline_date"] == "2026-08-07"
    assert o["location"] == "Le Havre"
    print("OK test_ofb_gestmax", o["title"], o["deadline_date"])


def test_mnhn():
    html = """
    <table>
      <tr><th>Offre</th><th>Localisation</th><th>Catégorie</th><th></th></tr>
      <tr>
        <td><a href="https://recrutement.mnhn.fr/front-jobs-detail.html?id_job=1561">
            Technicien en aménagement - Station marine de Concarneau (F/H)</a></td>
        <td>29 - Station marine de Concarneau</td>
        <td>B</td>
        <td></td>
      </tr>
    </table>
    """
    with patch.object(sites_mod, "fetch_html", return_value=with_html(html)):
        offers = sites_mod.scrape_mnhn(FAKE_SITE())
    assert len(offers) >= 1
    o = offers[0]
    assert "concarneau" in o["title"].lower() or "concarneau" in o["location"].lower()
    assert o["link"].startswith("https://recrutement.mnhn.fr")
    print("OK test_mnhn", o["title"], o["location"])


def test_ipev_cards():
    html = """
    <div class="offer-card">
      <h3>Volontaire de Service Civique Tous Corps d'État (F/H) Terre Adélie</h3>
      <p>Institut Polaire</p>
      <p>VSC</p>
      <p>Dumont d'Urville</p>
      <a href="/poste/1wmtei94mh-volontaire-terre-adelie/"></a>
    </div>
    <div class="offer-card">
      <h3>Chef mécanicien centrale électrique (F/H) - Concordia - Antarctique</h3>
      <p>Institut Polaire</p>
      <p>CDD</p>
      <p>Concordia</p>
      <a href="/poste/ehwdkgaxgi-chef-mecanicien/"></a>
    </div>
    """
    with patch.object(sites_mod, "fetch_html", return_value=with_html(html)):
        offers = sites_mod.scrape_ipev(FAKE_SITE())
    assert len(offers) == 2
    assert offers[0]["title"].startswith("Volontaire de Service Civique")
    assert offers[0]["contract_type"] == "Service civique"
    assert offers[0]["location"] == "Dumont d'Urville"
    assert offers[1]["contract_type"] == "CDD"
    print("OK test_ipev_cards", [o["title"] for o in offers])


def test_taaf_accordion():
    html = """
    <ul>
      <li>
        <h2>Volontaire pour la réserve naturelle nationale H/F Iles Kerguelen VSC</h2>
        <h3>Domaine(s) d'activités</h3>
        <p>Environnement / Ecologie / Botanique</p>
        <h3>Durée de la ou des missions</h3>
        <p>octobre 2026 - avril 2027 (6 mois) Kerguelen</p>
        <h3>Date fin de candidature</h3>
        <p>02 Août 2026</p>
      </li>
    </ul>
    """
    with patch.object(sites_mod, "fetch_html", return_value=with_html(html)):
        offers = sites_mod.scrape_taaf(FAKE_SITE(url="https://taaf.fr/recrutement/"))
    assert len(offers) == 1
    o = offers[0]
    assert "kerguelen" in o["title"].lower() or "réserve naturelle" in o["title"].lower()
    assert o["deadline_date"] == "2026-08-02"
    print("OK test_taaf_accordion", o["title"], o["deadline_date"], o["contract_duration"])


def test_reseau_tee_links():
    html = """
    <table>
      <tr><td>
        <a href="/129315_offre-emploi-expert--botaniste--h-f.html">EODD INGÉNIEURS CONSEILS
        EXPERT - BOTANISTE (H/F) 13-07-2026 - CDI Bouches-du-RhôneEntreprise</a>
        <a href="/129314_offre-emploi-cdd-charge-etudes-peche.html">AGENCE DE L'EAU
        CDD 6 mois - Chargé.e d'études pêche et aquaculture 13-07-2026 - CDD 6 mois GirondeAssociation</a>
      </td></tr>
    </table>
    """
    with patch.object(sites_mod, "fetch_html", side_effect=[with_html(html)] + [with_html("<html></html>")] * 5):
        offers = sites_mod.scrape_reseau_tee(FAKE_SITE())
    assert len(offers) == 2
    assert offers[0]["publication_date"] == "2026-07-13"
    assert offers[1]["contract_type"] == "CDD"
    assert "Gironde" in offers[1]["title"] or "Gironde" in offers[1]["summary"]
    print("OK test_reseau_tee_links", [o["title"] for o in offers])


def test_generic_scraper_filters_noise():
    html = """
    <nav><a href="/contact">Contact</a><a href="/mentions-legales">Mentions légales</a></nav>
    <div class="job">
      <a href="/offre-emploi/charge-de-mission-ecologie-marine">
        Chargé de mission écologie marine et suivi ornithologique - CDD 6 mois
      </a>
    </div>
    """
    with patch.object(sites_mod, "fetch_html", return_value=with_html(html)):
        offers = sites_mod.scrape_generic(FAKE_SITE(url="https://example.org/recrutement"))
    assert len(offers) == 1
    assert "écologie marine" in offers[0]["title"].lower()
    assert offers[0]["link"] == "https://example.org/offre-emploi/charge-de-mission-ecologie-marine"
    print("OK test_generic_scraper_filters_noise", offers[0]["title"])


if __name__ == "__main__":
    test_ofb_gestmax()
    test_mnhn()
    test_ipev_cards()
    test_taaf_accordion()
    test_reseau_tee_links()
    test_generic_scraper_filters_noise()
    print("\nTous les tests de scraping (hors-ligne) sont passés ✅")
