"""
Un scraper par site (ou famille de sites similaires).

Chaque fonction reçoit la configuration du site (dict issu de config/settings.SITES)
et renvoie une liste de dictionnaires "offre" avec les clés :

    site_id, site_name, title, link, location, summary,
    publication_date (ISO ou None), deadline_date (ISO ou None),
    contract_type, contract_duration (ou None), raw_text

Si un site change sa structure HTML, c'est CE fichier qu'il faut ajuster
(voir section "Dépannage" du README).
"""
from __future__ import annotations

import re
from typing import Optional

from config.settings import MAX_PAGES_PER_SITE, REQUEST_DELAY_SECONDS
from scraper.base import (
    clean_text,
    detect_contract_duration,
    detect_contract_type,
    fetch_html,
    find_first_date,
    polite_sleep,
    truncate,
)

# Sépare les mots collés type "GirondeAssociation" -> "Gironde Association"
# (artefact fréquent quand deux <span> HTML sont accolés sans espace)
_GLUED_WORDS_RE = re.compile(r"(?<=[a-zàâäéèêëïîôöùûüç0-9])(?=[A-ZÀ-Ý])")


def _unglue(text: str) -> str:
    return _GLUED_WORDS_RE.sub(" ", text or "")


def _make_offer(site: dict, **kwargs) -> dict:
    offer = {
        "site_id": site["id"],
        "site_name": site["name"],
        "title": "",
        "link": "",
        "location": "",
        "summary": "",
        "publication_date": None,
        "deadline_date": None,
        "contract_type": "Non précisé",
        "contract_duration": None,
        "raw_text": "",
    }
    offer.update(kwargs)
    return offer


# ---------------------------------------------------------------------------
# Office Français de la Biodiversité (gestmax) — tableau HTML statique
# ---------------------------------------------------------------------------
def scrape_ofb_gestmax(site: dict) -> list[dict]:
    offers = []
    for page in range(MAX_PAGES_PER_SITE):
        url = site["url"] if page == 0 else f"https://ofb.gestmax.fr/search/index/page/{page + 1}"
        try:
            soup = fetch_html(url)
        except Exception:
            break

        table = soup.find("table")
        if not table:
            break

        headers = [clean_text(th.get_text()) for th in table.find_all("th")]
        rows = table.find_all("tr")[1:] if headers else table.find_all("tr")
        if not rows:
            break

        for row in rows:
            cells = row.find_all("td")
            if not cells:
                continue
            link_tag = row.find("a", href=True)
            link = link_tag["href"] if link_tag else ""
            texts = [clean_text(c.get_text()) for c in cells]

            def col(name_fragment: str) -> str:
                for h, t in zip(headers, texts):
                    if name_fragment.lower() in h.lower():
                        return t
                return ""

            title = col("titre") or (texts[0] if texts else "")
            location = col("résidence") or col("affectation") or (texts[-2] if len(texts) >= 2 else "")
            deadline_raw = col("limite") or (texts[-1] if texts else "")

            offers.append(_make_offer(
                site,
                title=title,
                link=link,
                location=location,
                summary=truncate(" - ".join(t for t in texts if t)),
                deadline_date=find_first_date(deadline_raw),
                contract_type=detect_contract_type(" ".join(texts)),
                contract_duration=detect_contract_duration(" ".join(texts)),
                raw_text=" | ".join(texts),
            ))

        polite_sleep(REQUEST_DELAY_SECONDS)
        if not soup.find("a", string=re.compile("Suivant", re.IGNORECASE)):
            break
    return offers


# ---------------------------------------------------------------------------
# Muséum National d'Histoire Naturelle — tableau HTML statique
# ---------------------------------------------------------------------------
def scrape_mnhn(site: dict) -> list[dict]:
    offers = []
    urls = [
        "https://recrutement.mnhn.fr/front-jobs.html?direct",
        "https://recrutement.mnhn.fr/front-jobs.html?internship&direct",  # stages / apprentissage
    ]
    for url in urls:
        try:
            soup = fetch_html(url)
        except Exception:
            continue

        table = soup.find("table")
        if not table:
            continue

        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if not cells:
                continue
            link_tag = row.find("a", href=True)
            if not link_tag:
                continue
            texts = [clean_text(c.get_text()) for c in cells]
            title = clean_text(link_tag.get_text()) or (texts[0] if texts else "")
            location = texts[1] if len(texts) > 1 else ""
            category = texts[2] if len(texts) > 2 else ""

            offers.append(_make_offer(
                site,
                title=title,
                link=link_tag["href"],
                location=location,
                summary=truncate(f"{title} — {location} — Catégorie {category}"),
                contract_type=detect_contract_type(url + " " + title),
                raw_text=" | ".join(texts),
            ))
        polite_sleep(REQUEST_DELAY_SECONDS)
    return offers


# ---------------------------------------------------------------------------
# Institut Polaire Français (ATS "Beetween") — cartes HTML statiques
# ---------------------------------------------------------------------------
def scrape_ipev(site: dict) -> list[dict]:
    offers = []
    try:
        soup = fetch_html(site["url"])
    except Exception:
        return offers

    seen_links = set()
    for a in soup.find_all("a", href=True):
        if "/poste/" not in a["href"]:
            continue
        if a["href"] in seen_links:
            continue
        seen_links.add(a["href"])

        # Remonte jusqu'à trouver le plus petit conteneur parent qui a 3 à 6 lignes de texte
        # (titre / "Institut Polaire" / type de contrat / lieu)
        lines: list[str] = []
        node = a
        for _ in range(6):
            node = node.parent
            if node is None:
                break
            candidate_lines = [clean_text(l) for l in node.get_text("\n").split("\n") if clean_text(l)]
            if 3 <= len(candidate_lines) <= 8:
                lines = candidate_lines
                break
        if not lines:
            continue

        lines = [l for l in lines if l.lower() != "institut polaire"]
        title = lines[0] if lines else ""
        contract_type = detect_contract_type(" ".join(lines))
        location = lines[-1] if len(lines) > 1 else ""

        offers.append(_make_offer(
            site,
            title=title,
            link=a["href"],
            location=location,
            summary=truncate(" - ".join(lines)),
            contract_type=contract_type,
            raw_text=" | ".join(lines),
        ))
    return offers


# ---------------------------------------------------------------------------
# TAAF — toutes les offres + détails complets sur une seule page (accordéon)
# ---------------------------------------------------------------------------
def scrape_taaf(site: dict) -> list[dict]:
    offers = []
    try:
        soup = fetch_html(site["url"])
    except Exception:
        return offers

    # Chaque offre est un item de liste contenant la mention "Date fin de candidature"
    candidates = []
    for li in soup.find_all(["li", "div", "article"]):
        text = li.get_text(" ", strip=True)
        if "Date fin de candidature" in text or "date fin de candidature" in text.lower():
            candidates.append(li)

    # Ne garder que les conteneurs les plus "internes" (évite de dupliquer parent + enfant)
    filtered = []
    for c in candidates:
        if not any(c is not other and c in other.find_all(True) for other in candidates):
            filtered.append(c)

    for block in filtered:
        full_text = block.get_text("\n", strip=True)
        lines = [clean_text(l) for l in full_text.split("\n") if clean_text(l)]
        joined = "\n".join(lines)

        def section(label: str) -> Optional[str]:
            m = re.search(re.escape(label) + r"\s*\n?(.+?)(?:\n[A-ZÉÀ][^\n]{0,60}\n|\Z)", joined, re.DOTALL)
            return clean_text(m.group(1)) if m else None

        header = lines[0] if lines else ""
        # Coupe le header au premier mot-clé de type de contrat pour isoler un titre plus propre
        contract_type = detect_contract_type(header)
        title = header
        for kw in ["CDD", "CDI", "Volontaire", "Stagiaire", "Stage", "VSC", "Militaire"]:
            idx = header.find(kw)
            if idx > 10:
                title = header[:idx].strip(" -–")
                break

        domaine = section("Domaine(s) d'activités") or ""
        duree = section("Durée de la ou des missions") or ""
        deadline_raw = section("Date fin de candidature") or ""

        offers.append(_make_offer(
            site,
            title=truncate(title, 160),
            link=site["url"],
            location="TAAF (Terres australes et antarctiques françaises)",
            summary=truncate(domaine or full_text),
            deadline_date=find_first_date(deadline_raw),
            contract_type=contract_type,
            contract_duration=detect_contract_duration(duree) or truncate(duree, 60) or None,
            raw_text=truncate(full_text, 600),
        ))
    return offers


# ---------------------------------------------------------------------------
# Réseau TEE — gros volume (600+ offres) : on lit seulement les pages les + récentes
# ---------------------------------------------------------------------------
def scrape_reseau_tee(site: dict) -> list[dict]:
    offers = []
    for page in range(MAX_PAGES_PER_SITE):
        url = f"https://www.reseau-tee.net/espace-candidats-offres.php?page={page}"
        try:
            soup = fetch_html(url)
        except Exception:
            break

        links = [a for a in soup.find_all("a", href=True) if re.search(r"/\d+_offre-emploi-", a["href"])]
        if not links:
            break

        for a in links:
            text = _unglue(clean_text(a.get_text(" ")))
            dates = find_first_date(text)
            contract_type = detect_contract_type(text)
            # Le titre = texte avant la date (les colonnes suivantes sont contrat/lieu/structure)
            title = text
            m = re.search(r"\d{1,2}-\d{1,2}-\d{2,4}", text)
            if m:
                title = text[: m.start()].strip(" -")

            href = a["href"]
            if href.startswith("/"):
                href = "https://www.reseau-tee.net" + href

            offers.append(_make_offer(
                site,
                title=truncate(title, 160),
                link=href,
                location="",
                summary=truncate(text),
                publication_date=dates,
                contract_type=contract_type,
                raw_text=text,
            ))
        polite_sleep(REQUEST_DELAY_SECONDS)
    return offers


# ---------------------------------------------------------------------------
# SFEcodiff — formulaire de recherche en JavaScript (AJAX)
# ---------------------------------------------------------------------------
def scrape_sfecologie(site: dict) -> list[dict]:
    """
    ATTENTION (limitation connue) : la liste d'annonces SFEcodiff est chargée en
    JavaScript après un appel AJAX déclenché par le formulaire de recherche. Une
    requête HTTP simple (utilisée ici) ne peut pas exécuter ce JavaScript et ne
    verra donc probablement AUCUNE offre.

    Ce scraper est laissé en place "au cas où" (si le site évolue vers du HTML
    statique) mais renvoie une liste vide en pratique. Voir le README, section
    "Dépannage", pour deux alternatives concrètes :
      1) s'abonner directement à l'alerte mail native de SFEcodiff
         (https://sfecologie.org/sfecodiff/sabonner/) en complément de ce bot ;
      2) migrer ce scraper vers Playwright (navigateur headless) si besoin.
    """
    offers = []
    try:
        soup = fetch_html(site["url"])
    except Exception:
        return offers

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/sfecodiff/" not in href or href.rstrip("/").endswith("consulter"):
            continue
        text = clean_text(a.get_text())
        if len(text) < 8:
            continue
        offers.append(_make_offer(
            site,
            title=text,
            link=href,
            summary=truncate(text),
            raw_text=text,
        ))
    return offers


# ---------------------------------------------------------------------------
# Scraper générique — utilisé pour les sites non finement configurés
# (CNRS, IRD, Bretagne Vivante, Temeum, Réserves Naturelles, LPO, Tour du Valat...)
# ---------------------------------------------------------------------------
_JOB_HREF_HINTS = re.compile(
    r"offre|emploi|poste|job|recrutement|stage|vacature|vacancy|annonce|candidat",
    re.IGNORECASE,
)
_NOISE_TEXT = re.compile(
    r"^(accueil|contact|mentions? l[ée]gales?|plan du site|newsletter|accessibilit[ée]|"
    r"connexion|inscription|rgpd|cookies?|suivez[- ]nous|facebook|twitter|instagram|linkedin)$",
    re.IGNORECASE,
)


def scrape_generic(site: dict) -> list[dict]:
    offers = []
    try:
        soup = fetch_html(site["url"])
    except Exception:
        return offers

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = clean_text(a.get_text())

        if not text or len(text) < 12 or _NOISE_TEXT.match(text):
            continue
        if not (_JOB_HREF_HINTS.search(href) or _JOB_HREF_HINTS.search(text)):
            continue

        if href.startswith("/"):
            base = re.match(r"https?://[^/]+", site["url"])
            href = (base.group(0) if base else "") + href

        # Contexte élargi : texte du parent (souvent une carte/ligne avec + de détails)
        parent_text = clean_text(a.find_parent().get_text(" ")) if a.find_parent() else text

        offers.append(_make_offer(
            site,
            title=text,
            link=href,
            summary=truncate(parent_text if len(parent_text) > len(text) else text),
            publication_date=find_first_date(parent_text),
            contract_type=detect_contract_type(parent_text),
            contract_duration=detect_contract_duration(parent_text),
            raw_text=parent_text,
        ))
    return offers


SCRAPERS = {
    "scrape_ofb_gestmax": scrape_ofb_gestmax,
    "scrape_mnhn": scrape_mnhn,
    "scrape_ipev": scrape_ipev,
    "scrape_taaf": scrape_taaf,
    "scrape_reseau_tee": scrape_reseau_tee,
    "scrape_sfecologie": scrape_sfecologie,
    "scrape_generic": scrape_generic,
}
