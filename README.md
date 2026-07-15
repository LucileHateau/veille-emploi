# 🐧 Bot de veille emploi — écologie marine / océanographie / ornithologie

Recherche automatiquement, **chaque jour**, des offres d'emploi/stage/service civique
correspondant à ton profil sur 13 sites spécialisés, t'envoie un mail récapitulatif des
nouvelles offres, et tient à jour un tableau de bord en ligne.

- 📬 **Mail quotidien** : sujet "recherche d'emploi", avec pour chaque nouvelle offre le
  nom, le site, un résumé, le lien, la date limite de candidature, le type et la durée du contrat.
- 📊 **Dashboard en ligne** (via GitHub Pages) : historique complet, filtrable par site /
  type de contrat / mots-clés, avec repérage visuel des offres dont la clôture approche.
- ⚙️ **100% gratuit** : hébergé sur GitHub Actions (2 000 min/mois gratuites, un run quotidien
  en consomme quelques minutes), aucun serveur à payer.

---

## 1. Mise en route (à faire une seule fois)

### 1.1 Créer le dépôt GitHub

1. Crée un compte GitHub si tu n'en as pas (https://github.com/signup).
2. Crée un nouveau dépôt (bouton vert **New**), par exemple nommé `veille-emploi`.
   - **Public ou privé ?** Les offres d'emploi affichées ne sont que des informations déjà
     publiques (rien de confidentiel), donc un dépôt **public** ne pose pas de problème.
     Si tu préfères **privé**, c'est possible, mais le dashboard (étape 1.4) sera quand même
     visible par toute personne qui a le lien, car GitHub Pages ne restreint pas l'accès
     sur les comptes gratuits.
3. Mets tous les fichiers de ce projet dans le dépôt (glisser-déposer sur github.com fonctionne,
   ou en ligne de commande : `git init`, `git add .`, `git commit -m "Initial"`,
   `git remote add origin <URL de ton dépôt>`, `git push -u origin main`).

### 1.2 Créer un "mot de passe d'application" Gmail

Le bot envoie les mails depuis lucile.hateau@gmail.com via Gmail. Google exige un mot de
passe dédié (différent de ton mot de passe habituel) pour ce genre d'usage automatisé :

1. Va sur https://myaccount.google.com/security
2. Active la **validation en 2 étapes** si ce n'est pas déjà fait (obligatoire pour l'étape suivante).
3. Va sur https://myaccount.google.com/apppasswords
4. Crée un mot de passe d'application (nom libre, ex : "bot-emploi-github"). Google te donne
   un code de 16 caractères — **copie-le tout de suite**, il ne sera plus jamais affiché.

### 1.3 Ajouter les secrets dans GitHub

Dans ton dépôt GitHub : **Settings → Secrets and variables → Actions → New repository secret**.
Ajoute :

| Nom du secret         | Valeur                                              |
|-----------------------|------------------------------------------------------|
| `EMAIL_ADDRESS`       | `lucile.hateau@gmail.com`                            |
| `EMAIL_APP_PASSWORD`  | le code à 16 caractères généré à l'étape 1.2         |
| `RECIPIENT_EMAIL`     | `lucile.hateau@gmail.com` (optionnel, sinon = EMAIL_ADDRESS) |

Ces secrets ne sont jamais visibles dans le code ni dans les logs.

### 1.4 Activer le dashboard (GitHub Pages)

Dans ton dépôt : **Settings → Pages** → Source : "Deploy from a branch" → Branch : `main`,
dossier `/docs` → **Save**. Après quelques minutes, ton dashboard est accessible à une URL du
type `https://<ton-nom-utilisateur>.github.io/veille-emploi/`.

### 1.5 Activer les Actions et lancer un premier test

1. Onglet **Actions** du dépôt → si demandé, clique "I understand my workflows, go ahead
   and enable them".
2. Clique sur le workflow **"Veille emploi quotidienne"** → **Run workflow** → **Run workflow**
   (bouton vert) pour un premier essai manuel, sans attendre le lendemain.
3. Regarde les logs du run : chaque site scrapé affiche le nombre d'offres trouvées. En cas
   d'erreur sur un site, les autres sites ne sont pas affectés (voir section Dépannage).

C'est terminé : le bot tournera ensuite automatiquement tous les jours à 6h UTC
(7h ou 8h heure de Paris selon l'heure d'été/hiver).

---

## 2. Personnaliser la recherche

Tout se configure dans **`config/settings.py`**, sans toucher au reste du code :

- **`SITES`** : liste des sites surveillés. Chaque site a un `enabled: True/False` — mets
  `False` pour désactiver une source sans la supprimer. Pour ajouter un nouveau site, copie
  un bloc existant, donne-lui un `id` unique, son `url`, et `"scraper": "scrape_generic"`
  (le scraper générique fonctionne sur beaucoup de sites, avec une précision variable — voir
  section Dépannage pour l'améliorer si besoin).
- **`POSITIVE_KEYWORDS` / `NEGATIVE_KEYWORDS`** : mots-clés qui augmentent ou diminuent le
  score de pertinence d'une offre. Ajoute tes propres mots-clés avec un poids (1 à 3).
- **`MIN_SCORE_TO_NOTIFY`** : seuil au-dessus duquel une offre est retenue. Baisse-le pour
  voir plus d'offres (avec plus de "bruit"), augmente-le pour être plus sélectif.
- **`WANTED_CONTRACT_TYPES`** : types de contrat qui te correspondent (bonus de score).

Après toute modification, il suffit de faire un `git commit` + `git push` : le prochain run
programmé (ou un run manuel via l'onglet Actions) utilisera automatiquement la nouvelle config.

---

## 3. Tester en local (optionnel, pour les curieuses)

```bash
pip install -r requirements.txt

# Teste un seul site et affiche le détail des offres brutes trouvées, sans envoyer de mail :
python main.py --site ofb --debug

# Simule un run complet (tous les sites) sans envoyer de mail ni modifier de fichier :
python main.py --dry-run

# Run réel (nécessite d'avoir défini EMAIL_ADDRESS et EMAIL_APP_PASSWORD en variables
# d'environnement locales, sinon l'envoi de mail est simplement ignoré) :
python main.py
```

---

## 4. Dépannage — "un site ne remonte plus d'offres"

Les sites web changent parfois leur structure HTML, ce qui peut casser un scraper. Si un
site remonte 0 offre alors qu'il y en a clairement sur le site :

1. Lance `python main.py --site <id_du_site> --debug` pour voir ce qui est récupéré.
2. Va sur la page du site dans ton navigateur, clic droit → "Afficher le code source de la
   page" (ou "Inspecter" pour un site en JavaScript), et regarde si la structure des offres
   (tableau, cartes, liens) a changé par rapport à ce qui est décrit dans
   `scraper/sites.py`.
3. Ajuste la fonction correspondante dans `scraper/sites.py` (chaque fonction est commentée).
   Tu peux aussi demander à Claude de le faire pour toi en lui donnant l'URL du site.

### Limitations connues à ce jour

- **SFEcodiff** (`sfecologie.org`) : le moteur de recherche du site charge les annonces en
  JavaScript après un appel en coulisses (AJAX), qu'un simple téléchargement de page ne peut
  pas déclencher. Le scraper est donc susceptible de renvoyer 0 offre. Deux solutions :
  1. **En complément**, abonne-toi directement à leur propre système d'alerte mail natif :
     https://sfecologie.org/sfecodiff/sabonner/ (le plus simple, et fiable à 100%).
  2. Si tu veux vraiment l'automatiser via ce bot, il faudrait ajouter un navigateur headless
     (ex : Playwright) — plus lourd à faire tourner sur GitHub Actions mais possible ; demande
     à Claude si tu veux cette évolution.
- **Réseau-TEE** (607+ offres, toutes thématiques confondues) : par souci de performance, le
  bot ne lit que les 3 premières pages (les annonces les plus récentes), et compte sur le
  filtrage par mots-clés pour ne garder que celles qui te concernent. Comme le site est trié
  par date décroissante, cela couvre en pratique largement une journée de nouvelles annonces.
- **TAAF** : toutes les offres sont publiées sur une seule page (pas de lien individuel par
  offre) — le lien envoyé par mail pointe donc vers la page recrutement générale, à charge
  pour toi de retrouver l'offre précise dans la liste (le titre et le résumé du mail
  permettent de la repérer facilement).
- **Scraper générique** (CNRS, IRD, Bretagne Vivante, Temeum, Réserves Naturelles, LPO, Tour
  du Valat) : fonctionne en repérant les liens dont le texte ou l'adresse contiennent des mots
  comme "offre", "emploi", "stage", etc. C'est efficace sur la plupart des sites simples, mais
  moins précis qu'un scraper dédié. Si un de ces sites s'avère peu fiable à l'usage, dis-le à
  Claude en lui donnant l'URL : un scraper dédié (comme pour l'OFB ou le MNHN) peut être écrit
  spécifiquement pour lui.

---

## 5. Structure du projet

```
config/settings.py       # profil candidat, mots-clés, liste des sites (LE fichier à éditer)
scraper/base.py          # fonctions utilitaires (dates, types de contrat, requêtes HTTP)
scraper/sites.py         # un scraper par site
matcher.py                # calcule le score de pertinence de chaque offre
state.py                  # mémorise les offres déjà vues (data/seen_offers.json)
                           # + historique complet pour le dashboard (docs/offers.json)
emailer.py                 # compose et envoie le mail quotidien
main.py                    # point d'entrée, orchestre tout le pipeline
docs/index.html            # le dashboard (page publiée par GitHub Pages)
.github/workflows/daily.yml # planifie l'exécution quotidienne automatique
tests/                      # tests locaux (hors-ligne, ne nécessitent pas internet)
```

## 6. Ajouter une nouvelle source suggérée : LinkedIn ?

LinkedIn interdit contractuellement (CGU) le scraping automatisé de ses pages et bloque
activement ce type d'outil — il n'est donc pas inclus ici. En complément de ce bot, pense à
activer une **alerte emploi native LinkedIn** (bouton "Créer une alerte" sur une recherche
LinkedIn Jobs) : c'est autorisé, fiable, et gratuit.
