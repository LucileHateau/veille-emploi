"""
Configuration centrale du bot de recherche d'emploi.

Tout ce que Lucile voudra modifier (mots-clés, sites, seuils) se trouve ICI.
Aucun autre fichier n'a besoin d'être touché pour ajuster la recherche.
"""

# ---------------------------------------------------------------------------
# 1. PROFIL CANDIDAT — utilisé pour noter la pertinence de chaque offre
# ---------------------------------------------------------------------------

# Mots-clés qui AUGMENTENT la pertinence d'une offre (poids donné entre parenthèses)
# Regroupés par thème pour rester lisibles / faciles à éditer.
POSITIVE_KEYWORDS = {
    # Écologie marine / océanographie
    "écologie marine": 3, "ecologie marine": 3, "biologie marine": 3,
    "océanographie": 3, "oceanographie": 3, "milieu marin": 2,
    "biodiversité marine": 3, "biodiversite marine": 3,
    "intertidal": 2, "benthique": 2, "plancton": 2, "récif": 2,
    "aire marine protégée": 3, "amp": 1, "zone côtière": 2, "littoral": 2,

    # Ornithologie / oiseaux marins / manchots
    "ornithologie": 3, "oiseaux marins": 3, "avifaune": 2,
    "manchot": 3, "manchots": 3, "pingouin": 2, "limicole": 2, "anatidé": 2,
    "anatidés": 2, "baguage": 2, "bague": 1, "suivi ornithologique": 3,

    # Pêche / halieutique
    "pêche": 2, "peche": 2, "halieutique": 3, "aquaculture": 2,
    "ressources marines": 2, "pêcherie": 2, "pecherie": 2,

    # Terrain / expéditions / milieux isolés (son point fort)
    "terrain": 1, "hivernage": 3, "expédition": 2, "expedition": 2,
    "terres australes": 3, "taaf": 3, "crozet": 3, "kerguelen": 3,
    "antarctique": 2, "subantarctique": 3, "polaire": 2, "île isolée": 2,
    "milieu isolé": 2, "ipev": 3,

    # Biodiversité / conservation générale (cohérent avec son profil)
    "biodiversité": 1, "biodiversite": 1, "conservation": 1,
    "réserve naturelle": 2, "reserve naturelle": 2, "espèce protégée": 1,
    "eee": 1, "espèces exotiques envahissantes": 2,
    "pinnipède": 3, "pinnipedes": 3, "mammifère marin": 3, "cétacé": 2,

    # Compétences techniques qu'elle a
    "sig": 1, "qgis": 1, "rstudio": 1, "r studio": 1, "statistiques": 1,
    "taxonomie": 1, "taxinomie": 1, "génétique": 1,
}

# Mots-clés qui BAISSENT la pertinence (seniorité/exigences trop élevées pour bac+5 ou moins,
# ou hors-sujet). Une offre n'est pas rejetée d'office : son score est pénalisé.
NEGATIVE_KEYWORDS = {
    "doctorat exigé": 5, "thèse exigée these exigee": 4, "postdoc": 3, "post-doctorat": 3,
    "10 ans d'expérience": 4, "15 ans d'expérience": 5, "8 ans d'expérience": 3,
    "directeur": 3, "directrice": 3, "chef de service": 2, "responsable d'unité": 2,
    "encadrement supérieur": 2, "cadre dirigeant": 3,
    "phd required": 4, "senior": 2,
}

# Types de contrat qui l'intéressent (utilisés pour bonus de score + filtre affichage)
WANTED_CONTRACT_TYPES = [
    "stage", "service civique", "volontariat", "vsc", "via",
    "cdd", "contrat de projet", "saisonnier", "bénévolat", "eco-volontariat",
]

# Score minimum pour qu'une offre soit retenue et envoyée par mail.
# Plus bas = plus d'offres remontées (plus de "bruit"), plus haut = plus sélectif.
MIN_SCORE_TO_NOTIFY = 3

# Elle est mobile / partante à l'international : aucun filtre géographique n'est appliqué.
RESTRICT_TO_COUNTRY = None  # ex: "France" pour filtrer, None = pas de filtre géographique


# ---------------------------------------------------------------------------
# 2. SITES SURVEILLÉS — configurable : ajouter / retirer / désactiver une source
# ---------------------------------------------------------------------------
# `id`        : identifiant technique unique (utilisé dans les clés de dédoublonnage)
# `name`      : nom affiché dans les mails et le dashboard
# `url`       : page de listing à scraper
# `scraper`   : nom de la fonction dans scraper/sites.py qui sait lire ce site
# `enabled`   : True/False pour activer ou couper une source sans la supprimer
# `notes`     : indications libres (utile si un scraper est "best effort")

SITES = [
    {
        "id": "ofb",
        "name": "Office Français de la Biodiversité (gestmax)",
        "url": "https://ofb.gestmax.fr/search",
        "scraper": "scrape_ofb_gestmax",
        "enabled": True,
        "notes": "Tableau HTML statique, pagination via /search/index/page/N",
    },
    {
        "id": "mnhn",
        "name": "Muséum National d'Histoire Naturelle",
        "url": "https://recrutement.mnhn.fr/front-jobs.html?direct",
        "scraper": "scrape_mnhn",
        "enabled": True,
        "notes": "Tableau HTML statique, y compris stages via ?internship&direct",
    },
    {
        "id": "ipev",
        "name": "Institut Polaire Français (IPEV)",
        "url": "https://institutpolaire.nous-recrutons.fr/offres-emploi/",
        "scraper": "scrape_ipev",
        "enabled": True,
        "notes": "ATS Beetween, cartes HTML statiques",
    },
    {
        "id": "taaf",
        "name": "TAAF - Terres australes et antarctiques françaises",
        "url": "https://taaf.fr/recrutement/",
        "scraper": "scrape_taaf",
        "enabled": True,
        "notes": "Toutes les offres + détails complets sur une seule page (accordéon Wordpress)",
    },
    {
        "id": "reseau_tee",
        "name": "Réseau TEE (emploi environnemental)",
        "url": "https://www.reseau-tee.net/espace-candidats-offres.html?defiltre",
        "scraper": "scrape_reseau_tee",
        "enabled": True,
        "notes": "607+ offres toutes thématiques : filtrage mots-clés indispensable ici. "
                 "Pagination lourde -> on ne lit que les 3 premières pages (les plus récentes).",
    },
    {
        "id": "sfecologie",
        "name": "SFEcodiff (Société Française d'Écologie et d'Évolution)",
        "url": "https://sfecologie.org/sfecodiff/consulter/",
        "scraper": "scrape_sfecologie",
        "enabled": True,
        "notes": "Formulaire de recherche en JavaScript (AJAX) : scraper 'best effort', "
                 "à vérifier/ajuster si 0 résultat remonte (voir README section Dépannage).",
    },
    {
        "id": "cnrs",
        "name": "Emploi CNRS",
        "url": "https://emploi.cnrs.fr/",
        "scraper": "scrape_generic",
        "enabled": True,
        "notes": "Scraper générique (liens + mots-clés) : structure du site non vérifiée en détail.",
    },
    {
        "id": "ird",
        "name": "IRD - Institut de Recherche pour le Développement",
        "url": "https://emploi-recrutement.ird.fr/accueil.aspx?LCID=1036",
        "scraper": "scrape_generic",
        "enabled": True,
        "notes": "Scraper générique.",
    },
    {
        "id": "bretagne_vivante",
        "name": "Bretagne Vivante",
        "url": "https://www.bretagne-vivante.org/recrutement/",
        "scraper": "scrape_generic",
        "enabled": True,
        "notes": "Scraper générique.",
    },
    {
        "id": "temeum",
        "name": "Temeum (OFB) - emplois et stages",
        "url": "https://temeum.ofb.fr/emplois-et-stages",
        "scraper": "scrape_generic",
        "enabled": True,
        "notes": "Scraper générique.",
    },
    {
        "id": "reserves_naturelles",
        "name": "Réserves Naturelles de France",
        "url": "https://reserves-naturelles.org/offres-emploi-stages/",
        "scraper": "scrape_generic",
        "enabled": True,
        "notes": "Scraper générique.",
    },
    {
        "id": "lpo",
        "name": "LPO - Ligue pour la Protection des Oiseaux",
        "url": "https://www.lpo.fr/s-engager-a-nos-cotes/travailler-a-la-lpo/recrutement-lpo/recrutement",
        "scraper": "scrape_generic",
        "enabled": True,
        "notes": "Scraper générique.",
    },
    # --- Suggestions supplémentaires (désactivées par défaut, à activer si utiles) ---
    {
        "id": "tour_du_valat",
        "name": "Tour du Valat",
        "url": "https://tourduvalat.org/offres-demploi/",
        "scraper": "scrape_generic",
        "enabled": True,
        "notes": "Institut de recherche sur les zones humides méditerranéennes - pertinent "
                 "pour son profil (avifaune, écologie des zones humides).",
    },
    {
        "id": "linkedin",
        "name": "LinkedIn",
        "url": None,
        "scraper": None,
        "enabled": False,
        "notes": "LinkedIn bloque le scraping automatisé et change fréquemment sa structure "
                 "(+ CGU l'interdisant). Non implémenté : utiliser plutôt une alerte-mail "
                 "LinkedIn native en parallèle de ce bot.",
    },
]


# ---------------------------------------------------------------------------
# 3. EMAIL
# ---------------------------------------------------------------------------
EMAIL_SUBJECT = "recherche d'emploi"   # sujet imposé, identique pour chaque envoi
SEND_EMPTY_DIGEST = False              # si False : pas de mail envoyé quand 0 nouvelle offre

# ---------------------------------------------------------------------------
# 4. LIMITES TECHNIQUES
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT_SECONDS = 20
REQUEST_DELAY_SECONDS = 1.5          # pause entre deux requêtes (politesse envers les sites)
MAX_PAGES_PER_SITE = 3               # pagination max explorée par site à chaque run
USER_AGENT = (
    "Mozilla/5.0 (compatible; LucileJobBot/1.0; "
    "usage personnel de veille emploi; contact: lucile.hateau@gmail.com)"
)
