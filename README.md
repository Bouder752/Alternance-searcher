# Alternance searcher

Agent de veille qui parcourt chaque jour les offres d'alternance publiées autour de Strasbourg,
les note selon le profil défini dans [`config/profil.yaml`](config/profil.yaml) et produit un rapport :

- [`reports/rapport.md`](reports/rapport.md) : tableau lisible directement sur GitHub ;
- `reports/index.html` : version interactive (filtres « Nouveautés », « Offres », « Candidatures spontanées ») ;
- `data/resultats.json` : données brutes du jour ; `data/offres.json` : historique pour repérer les nouveautés.

Gratuit : aucune IA payante, exécution quotidienne via GitHub Actions.

## Sources

| Source | Méthode | Cadre |
|---|---|---|
| **La bonne alternance** (offres LBA, France Travail, partenaires + entreprises qui recrutent des alternants) | API officielle de l'État | Prévue pour cet usage, clé gratuite |
| **Connexion Emploi** (offres franco-allemandes) | Flux RSS public publié par le site | Autorisé (robots.txt) |
| Welcome to the Jungle, Indeed, LinkedIn, HelloWork, JobTeaser, APEC | Liens de recherche pré-remplis dans le rapport | Rien n'est collecté automatiquement (CGU) |

L'agent ne postule jamais à ta place.

## Mise en route

1. **Dépôt privé** : garde ce dépôt en privé (les offres peuvent contenir des coordonnées de recruteurs).
   Ne versionne jamais ton CV (`*.pdf` est ignoré par git).
2. **Clé La bonne alternance** (gratuite) : crée un compte sur
   <https://api.apprentissage.beta.gouv.fr/compte/profil> et génère une clé API.
   Sur GitHub : *Settings → Secrets and variables → Actions → New repository secret*,
   nom `LBA_API_KEY`. Sans cette clé, seule la source Connexion Emploi est interrogée.
3. **Lancer** : onglet *Actions → Veille alternance → Run workflow*. Ensuite, l'agent tourne
   tout seul chaque matin et met à jour `reports/`.

En local :

```bash
pip install -r requirements.txt
export LBA_API_KEY=ta_cle          # optionnel
python -m agent                    # puis ouvre reports/index.html
python -m unittest discover tests  # tests hors ligne
```

## Comment les offres sont notées (0 à 100)

Tout se règle dans `config/profil.yaml` :

- **Mots-clés par groupe** (supply chain & planification, chargé de mission / projet, RSE,
  international, débouchés officiels du master EDSB, compétences). Un groupe compte une fois,
  double si le mot est dans l'intitulé.
- **Secteur** : pharmaceutique, sport, logistique, agroalimentaire, puis industrie
  (secteurs recruteurs du master EDSB).
- **Grands groupes** : bonus pour les entreprises ciblées (Lilly, Merck, Hager, adidas…) ou de plus de
  250 salariés ; malus pour les très petites structures.
- **Exclusions** : commercial terrain, technico-commercial, vendeur, postes non cadres…
- **Malus** : niveau Bac+2 / BTS, début de contrat avant septembre 2027 (l'offre reste visible :
  elle montre que l'entreprise recrute des alternants sur ce poste).
- **Zone** : Strasbourg ± 50 km (`localisation.rayon_km`).

Les résultats sous `score_minimum` (25 par défaut) sont écartés ; le nombre d'offres écartées
et la raison figurent en haut du rapport.

## Calendrier

Les offres pour une rentrée en septembre 2027 sont surtout publiées entre janvier et juin 2027.
En attendant, la rubrique « Candidatures spontanées » liste les grandes entreprises de la zone
qui recrutent régulièrement des alternants sur tes métiers.
