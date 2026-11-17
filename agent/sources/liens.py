"""Liens de recherche pré-remplis vers des sites sans API ouverte.

Rien n'est collecté automatiquement sur ces sites (leurs CGU l'interdisent) : le rapport
propose simplement des liens à ouvrir soi-même.
"""

from urllib.parse import quote_plus


def generer(config: dict) -> list[dict]:
    rayon = config["localisation"]["rayon_km"]
    liens = []
    for requete, ville in config.get("recherches_manuelles") or []:
        q = quote_plus(requete)
        v = quote_plus(ville)
        liens.append({
            "requete": f"{requete} — {ville}",
            "sites": {
                "Welcome to the Jungle": f"https://www.welcometothejungle.com/fr/jobs?query={q}&aroundQuery={v}&refinementList%5Bcontract_type%5D%5B%5D=apprenticeship",
                "Indeed": f"https://fr.indeed.com/emplois?q={q}&l={v}&radius={rayon}",
                "LinkedIn": f"https://www.linkedin.com/jobs/search/?keywords={q}&location={v}&distance={min(rayon, 100)}",
                "HelloWork": f"https://www.hellowork.com/fr-fr/emploi/recherche.html?k={q}&l={v}&c=Alternance",
                "JobTeaser": f"https://www.jobteaser.com/fr/job-offers?q={q}&contract=alternating",
                "APEC": f"https://www.apec.fr/candidat/recherche-emploi.html/emploi?motsCles={q}&lieux={v}",
            },
        })
    return liens
