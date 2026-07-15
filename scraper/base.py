"""
Fonctions utilitaires partagées par tous les scrapers de site.
"""
from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from config.settings import REQUEST_TIMEOUT_SECONDS, USER_AGENT

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "fr-FR,fr;q=0.9"})


class FetchError(Exception):
    """Levée quand une page ne peut pas être récupérée."""


def fetch_html(url: str, timeout: int = REQUEST_TIMEOUT_SECONDS) -> BeautifulSoup:
    """Récupère une URL et renvoie un objet BeautifulSoup. Lève FetchError en cas d'échec."""
    try:
        resp = _session.get(url, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise FetchError(f"Échec de récupération de {url} : {exc}") from exc
    resp.encoding = resp.apparent_encoding or resp.encoding
    return BeautifulSoup(resp.text, "html.parser")


def polite_sleep(seconds: float) -> None:
    """Pause courte entre deux requêtes pour ne pas surcharger les sites."""
    time.sleep(seconds)


# ---------------------------------------------------------------------------
# Extraction de dates
# ---------------------------------------------------------------------------

_MONTHS_FR = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5,
    "juin": 6, "juillet": 7, "août": 8, "aout": 8, "septembre": 9,
    "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}

_DATE_NUMERIC_RE = re.compile(r"\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})\b")
_DATE_TEXT_RE = re.compile(
    r"\b(\d{1,2})\s+(" + "|".join(_MONTHS_FR.keys()) + r")\s+(\d{4})\b", re.IGNORECASE
)


def find_first_date(text: str) -> Optional[str]:
    """Cherche une date (formats JJ/MM/AAAA, JJ-MM-AAAA ou '12 août 2026') dans un texte.
    Renvoie une chaîne ISO (AAAA-MM-JJ) ou None si rien trouvé."""
    if not text:
        return None

    m = _DATE_NUMERIC_RE.search(text)
    if m:
        day, month, year = m.groups()
        year = int(year)
        if year < 100:
            year += 2000
        try:
            return datetime(year, int(month), int(day)).strftime("%Y-%m-%d")
        except ValueError:
            pass

    m = _DATE_TEXT_RE.search(text)
    if m:
        day, month_name, year = m.groups()
        month = _MONTHS_FR.get(month_name.lower())
        if month:
            try:
                return datetime(int(year), month, int(day)).strftime("%Y-%m-%d")
            except ValueError:
                pass
    return None


def find_all_dates(text: str) -> list[str]:
    """Renvoie toutes les dates détectées dans un texte, dans l'ordre d'apparition."""
    found = []
    for m in _DATE_NUMERIC_RE.finditer(text or ""):
        day, month, year = m.groups()
        year_i = int(year)
        if year_i < 100:
            year_i += 2000
        try:
            found.append(datetime(year_i, int(month), int(day)).strftime("%Y-%m-%d"))
        except ValueError:
            continue
    for m in _DATE_TEXT_RE.finditer(text or ""):
        day, month_name, year = m.groups()
        month = _MONTHS_FR.get(month_name.lower())
        if month:
            try:
                found.append(datetime(int(year), month, int(day)).strftime("%Y-%m-%d"))
            except ValueError:
                continue
    return found


# ---------------------------------------------------------------------------
# Détection type / durée de contrat
# ---------------------------------------------------------------------------

_CONTRACT_PATTERNS = [
    ("Service civique", r"service\s+civique|\bvsc\b"),
    ("VIA (Volontariat International)", r"\bvia\b|volontariat international"),
    ("Stage", r"\bstage\b|stagiaire|convention de stage"),
    ("Alternance", r"alternance|apprentissage|contrat pro"),
    ("CDI", r"\bcdi\b"),
    ("CDD", r"\bcdd\b|contrat de projet|contrat à durée déterminée"),
    ("Bénévolat / Éco-volontariat", r"bénévolat|benevolat|éco-volontariat|eco-volontariat|volontaire\b"),
    ("Fonction publique / Titulaire", r"fonction publique|titulaire de la fonction"),
    ("Intérim", r"intérim|interim"),
    ("Saisonnier", r"saisonnier"),
]

_DURATION_RE = re.compile(
    r"(\d{1,2})\s*(mois|an(?:s|née)?)", re.IGNORECASE
)


def detect_contract_type(text: str) -> str:
    """Devine le type de contrat à partir d'un texte libre. Renvoie 'Non précisé' si rien trouvé."""
    if not text:
        return "Non précisé"
    low = text.lower()
    for label, pattern in _CONTRACT_PATTERNS:
        if re.search(pattern, low):
            return label
    return "Non précisé"


def detect_contract_duration(text: str) -> Optional[str]:
    """Cherche une durée exprimée en mois/ans (ex: '6 mois', '18 mois')."""
    if not text:
        return None
    m = _DURATION_RE.search(text)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return None


# ---------------------------------------------------------------------------
# Identifiant unique d'offre (pour dédoublonnage)
# ---------------------------------------------------------------------------

def make_offer_id(site_id: str, link: str, title: str = "") -> str:
    """Génère un identifiant stable pour une offre, utilisé pour éviter de la renvoyer
    plusieurs fois par mail. Basé sur le lien (le plus stable) + repli sur le titre."""
    base = link.strip() if link else f"{site_id}:{title.strip().lower()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:20]


def clean_text(text: str) -> str:
    """Nettoie les espaces multiples / retours à la ligne d'un texte extrait du HTML."""
    return re.sub(r"\s+", " ", (text or "")).strip()


def truncate(text: str, max_len: int = 320) -> str:
    text = clean_text(text)
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rsplit(" ", 1)[0] + "…"
