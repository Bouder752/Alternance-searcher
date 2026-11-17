"""Source « La bonne alternance » : API officielle de l'État (api.apprentissage.beta.gouv.fr).

Agrège les offres déposées sur La bonne alternance, celles de France Travail et de
partenaires, ainsi qu'une liste d'entreprises susceptibles de recruter en alternance
(candidatures spontanées). Clé API gratuite : https://api.apprentissage.beta.gouv.fr/compte/profil
"""

from __future__ import annotations

import logging
import os
import time

import requests

from ..models import Offre
from ..texte import nettoyer_html

log = logging.getLogger(__name__)

URL = "https://api.apprentissage.beta.gouv.fr/api/job/v1/search"
PAGE_LBA = "https://labonnealternance.apprentissage.beta.gouv.fr"


def _get(d, *chemin, defaut=None):
    for cle in chemin:
        if not isinstance(d, dict):
            return defaut
        d = d.get(cle)
    return defaut if d is None else d


def _date(v) -> str:
    return str(v)[:10] if v else ""


def _texte(v) -> str:
    if isinstance(v, list):
        return " ; ".join(str(x) for x in v if x)
    return nettoyer_html(str(v)) if v else ""


def _lieu(workplace: dict) -> str:
    return _get(workplace, "location", "address", defaut="")


def _coordonnees(workplace: dict):
    coords = _get(workplace, "location", "geopoint", "coordinates")
    if isinstance(coords, list) and len(coords) == 2:
        return coords[1], coords[0]  # GeoJSON : [longitude, latitude]
    return None


def _nom_entreprise(workplace: dict) -> str:
    return (workplace.get("brand") or workplace.get("name") or workplace.get("legal_name") or "").strip()


def _secteur(workplace: dict) -> str:
    return _get(workplace, "domain", "naf", "label", defaut="")


def convertir_offre(job: dict) -> Offre:
    ident = job.get("identifier") or {}
    wp = job.get("workplace") or {}
    offre = job.get("offer") or {}
    contrat = job.get("contract") or {}
    apply = job.get("apply") or {}
    diplome = offre.get("target_diploma") or {}
    id_ = ident.get("id") or ident.get("partner_job_id") or ""
    partenaire = ident.get("partner_label") or "La bonne alternance"
    type_contrat = contrat.get("type")
    if isinstance(type_contrat, list):
        type_contrat = ", ".join(type_contrat)
    description = " ".join(
        filter(None, [
            _texte(offre.get("description")),
            _texte(offre.get("desired_skills")),
            _texte(offre.get("to_be_acquired_skills")),
            _texte(wp.get("description")),
        ])
    )
    niveau = diplome.get("european")
    try:
        niveau = int(niveau) if niveau is not None else None
    except (TypeError, ValueError):
        niveau = None
    return Offre(
        id=f"lba:{id_}",
        source="La bonne alternance" + ("" if partenaire == "La bonne alternance" else f" (via {partenaire})"),
        titre=(offre.get("title") or "").strip(),
        entreprise=_nom_entreprise(wp),
        lieu=_lieu(wp),
        url=apply.get("url") or f"{PAGE_LBA}/recherche?job_name={requests.utils.quote(offre.get('title') or '')}",
        description=description,
        publie_le=_date(_get(offre, "publication", "creation")),
        debut=_date(contrat.get("start")),
        type_contrat=type_contrat or "",
        taille_entreprise=str(wp.get("size") or ""),
        secteur=_secteur(wp),
        diplome=diplome.get("label") or "",
        niveau_diplome=niveau,
        nature="offre",
    )


def convertir_recruteur(rec: dict) -> Offre:
    ident = rec.get("identifier") or {}
    wp = rec.get("workplace") or {}
    apply = rec.get("apply") or {}
    nom = _nom_entreprise(wp)
    return Offre(
        id=f"lba-rec:{ident.get('id') or wp.get('siret') or nom}",
        source="La bonne alternance (candidature spontanée)",
        titre=f"Candidature spontanée — {nom}",
        entreprise=nom,
        lieu=_lieu(wp),
        url=apply.get("url") or wp.get("website") or PAGE_LBA,
        description=_texte(wp.get("description")),
        taille_entreprise=str(wp.get("size") or ""),
        secteur=_secteur(wp),
        nature="recruteur",
    )


def _distance(o: Offre, wp: dict, config) -> None:
    from ..geo import distance_km

    c = _coordonnees(wp)
    if c:
        loc = config["localisation"]
        o.distance_km = round(distance_km(loc["latitude"], loc["longitude"], *c), 1)


def collecter(config: dict, session: requests.Session | None = None) -> list[Offre]:
    cle = os.environ.get("LBA_API_KEY", "").strip()
    if not cle:
        log.warning("La bonne alternance ignorée : variable d'environnement LBA_API_KEY absente.")
        return []
    session = session or requests.Session()
    session.headers.update({"Authorization": f"Bearer {cle}", "Accept": "application/json"})
    loc = config["localisation"]
    niveau = str(config["profil"].get("niveau_diplome", ""))
    resultats: dict[str, Offre] = {}
    for rome, libelle in (config.get("lba_romes") or {}).items():
        params = {
            "latitude": loc["latitude"],
            "longitude": loc["longitude"],
            "radius": min(int(loc["rayon_km"]), 200),
            "romes": rome,
        }
        if niveau:
            params["target_diploma_level"] = niveau
        try:
            r = session.get(URL, params=params, timeout=60)
            if r.status_code in (401, 403):
                log.error("La bonne alternance : clé API refusée (HTTP %s).", r.status_code)
                return list(resultats.values())
            r.raise_for_status()
            data = r.json()
        except (requests.RequestException, ValueError) as e:
            log.warning("La bonne alternance %s (%s) : %s", rome, libelle, e)
            continue
        for job in data.get("jobs") or []:
            o = convertir_offre(job)
            _distance(o, job.get("workplace") or {}, config)
            resultats.setdefault(o.id, o)
        for rec in data.get("recruiters") or []:
            o = convertir_recruteur(rec)
            _distance(o, rec.get("workplace") or {}, config)
            resultats.setdefault(o.id, o)
        log.info("La bonne alternance %s : %d offres, %d recruteurs",
                 rome, len(data.get("jobs") or []), len(data.get("recruiters") or []))
        time.sleep(1)  # politesse envers l'API
    return list(resultats.values())
