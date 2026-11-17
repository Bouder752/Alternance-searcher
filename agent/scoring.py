"""Filtrage et notation des offres selon le profil (config/profil.yaml)."""

from __future__ import annotations

import re

from .geo import distance_depuis_texte
from .models import Offre
from .texte import contient, normaliser, premier_terme


def taille_min(taille: str) -> int | None:
    """« 1000-1999 » → 1000 ; « 10000+ » → 10000."""
    m = re.search(r"\d+", (taille or "").replace(" ", ""))
    return int(m.group()) if m else None


def _est_cible(entreprise_n: str, texte_n: str, cibles) -> str | None:
    for c in cibles:
        if contient(entreprise_n, c) or contient(texte_n[:300], c):
            return c
    return None


def exclusion(offre: Offre, config: dict) -> str | None:
    """Renvoie la raison d'exclusion, ou None si l'offre est conservée."""
    titre_n = normaliser(offre.titre)
    desc_n = normaliser(offre.description)

    terme = premier_terme(titre_n, config.get("exclusions_titre") or [])
    if terme:
        return f"intitulé exclu (« {terme} »)"
    if contient(titre_n, "commercial") or contient(titre_n, "commerciale"):
        indice = premier_terme(desc_n, config.get("indices_terrain") or [])
        if indice:
            return f"poste commercial terrain (« {indice} »)"

    # Les offres hors La bonne alternance ne sont pas forcément des alternances
    if offre.nature == "offre" and not offre.source.startswith("La bonne alternance"):
        if not premier_terme(f"{titre_n} {desc_n}", config.get("termes_alternance") or []):
            return "pas une alternance"

    loc = config["localisation"]
    if offre.distance_km is None:
        offre.distance_km = distance_depuis_texte(offre.lieu or offre.titre, loc["latitude"], loc["longitude"])
        if offre.distance_km is not None:
            offre.distance_km = round(offre.distance_km, 1)
    if offre.distance_km is not None and offre.distance_km > loc["rayon_km"]:
        return f"trop loin ({offre.distance_km:.0f} km)"
    if offre.distance_km is None and not offre.source.startswith("La bonne alternance"):
        return "lieu hors zone ou inconnu"
    return None


def noter(offre: Offre, config: dict) -> Offre:
    titre_n = normaliser(offre.titre)
    desc_n = normaliser(f"{offre.description} {offre.secteur}")
    entreprise_n = normaliser(offre.entreprise)
    raisons, alertes = [], []
    score = 0

    for groupe in config.get("mots_cles") or []:
        terme = premier_terme(titre_n, groupe["termes"])
        if terme:
            score += 2 * groupe["poids"]
            raisons.append(f"{groupe['groupe']} : « {terme} » dans l'intitulé")
            continue
        terme = premier_terme(desc_n, groupe["termes"])
        if terme:
            score += groupe["poids"]
            raisons.append(f"{groupe['groupe']} : « {terme} »")

    secteur_n = normaliser(f"{offre.secteur} {offre.entreprise}")
    meilleur = None
    for s in config.get("secteurs") or []:
        # Le secteur est cherché d'abord dans le secteur d'activité / le nom de l'entreprise
        terme = premier_terme(secteur_n, s["termes"])
        poids = s["poids"] if terme else 0
        if not terme:
            terme = premier_terme(f"{titre_n} {desc_n}", s["termes"])
            poids = s["poids"] // 2 if terme else 0
        if terme and (meilleur is None or poids > meilleur[0]):
            meilleur = (poids, s["nom"], terme)
    if meilleur:
        score += meilleur[0]
        raisons.append(f"Secteur {meilleur[1]} (« {meilleur[2]} »)")

    cible = _est_cible(entreprise_n, desc_n, config.get("entreprises_cibles") or [])
    taille = taille_min(offre.taille_entreprise)
    seuil = config.get("grande_entreprise_min", 250)
    if cible:
        score += 12
        raisons.append(f"Grand groupe ciblé ({cible})")
    elif taille is not None and taille >= seuil:
        score += 10 if taille >= 1000 else 6
        raisons.append(f"Grande entreprise ({offre.taille_entreprise} salariés)")
    elif taille is not None and taille < 50:
        score -= 8
        alertes.append(f"Petite structure ({offre.taille_entreprise} salariés)")

    if offre.niveau_diplome is not None:
        visé = int(config["profil"].get("niveau_diplome", 7))
        if offre.niveau_diplome < visé - 1:
            score -= 15
            alertes.append(f"Niveau visé bas ({offre.diplome or offre.niveau_diplome})")
        elif offre.niveau_diplome < visé:
            score -= 5
            alertes.append(f"Niveau visé : {offre.diplome or offre.niveau_diplome}")
    if re.search(r"\b(bts|bac \+ ?2|bac\+2|cap|bac pro)\b", titre_n):
        score -= 15
        alertes.append("Intitulé orienté Bac+2 / BTS")

    debut_souhaite = config["profil"].get("debut_souhaite", "")
    if offre.debut and debut_souhaite and offre.debut < debut_souhaite[:7] + "-01":
        # Une offre qui démarre avant la rentrée visée reste intéressante comme signal
        # (l'entreprise recrute des alternants sur ce type de poste) mais pèse moins.
        score -= 5
        alertes.append(f"Début annoncé le {offre.debut} (avant ta rentrée)")

    if offre.nature == "recruteur":
        # Pas d'annonce à analyser : La bonne alternance a renvoyé cette entreprise parce
        # qu'elle recrute des alternants sur un des métiers ROME visés. On valorise surtout
        # la taille et le secteur.
        score += 15
        if meilleur:
            score += meilleur[0]

    offre.score = max(0, min(100, score))
    offre.raisons = raisons
    offre.alertes = alertes
    return offre


def filtrer_et_noter(offres: list[Offre], config: dict) -> tuple[list[Offre], dict[str, int]]:
    gardees, exclues = [], {}
    minimum = config.get("score_minimum", 0)
    for o in offres:
        raison = exclusion(o, config)
        if raison:
            cle = raison.split(" (")[0]
            exclues[cle] = exclues.get(cle, 0) + 1
            continue
        noter(o, config)
        if o.score < minimum:
            exclues["score trop faible"] = exclues.get("score trop faible", 0) + 1
            continue
        gardees.append(o)
    gardees.sort(key=lambda o: (o.nature != "offre", -o.score))
    return gardees, exclues
