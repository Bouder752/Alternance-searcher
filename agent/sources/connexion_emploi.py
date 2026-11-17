"""Source « Connexion Emploi » : flux RSS public des offres franco-allemandes.

Le site publie lui-même ces flux (liens RSS en pied de page) et son robots.txt autorise l'accès.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

from ..models import Offre
from ..texte import nettoyer_html

log = logging.getLogger(__name__)

FLUX = [
    "https://www.connexion-emploi.com/fr/offers/jobfeed.rss",
    "https://www.connexion-emploi.com/de/offers/jobfeed.rss",
]


def _date(v: str) -> str:
    try:
        return parsedate_to_datetime(v).date().isoformat()
    except (TypeError, ValueError):
        return ""


def analyser_flux(xml: bytes | str) -> list[Offre]:
    racine = ET.fromstring(xml)
    offres = []
    for item in racine.iter("item"):
        titre = (item.findtext("title") or "").strip()
        lien = (item.findtext("link") or "").strip()
        ref = (item.findtext("reference") or item.findtext("guid") or lien).strip()
        # L'intitulé se termine par « , Ville » (ex. « Alternance - Logistique (H/F), Strasbourg »)
        lieu = titre.rsplit(",", 1)[1].strip() if "," in titre else ""
        offres.append(Offre(
            id=f"ce:{ref}",
            source="Connexion Emploi",
            titre=titre,
            lieu=lieu,
            url=lien,
            description=nettoyer_html(item.findtext("description") or ""),
            publie_le=_date(item.findtext("pubDate") or ""),
        ))
    return offres


def collecter(config: dict, session: requests.Session | None = None) -> list[Offre]:
    session = session or requests.Session()
    resultats: dict[str, Offre] = {}
    for url in FLUX:
        try:
            r = session.get(url, timeout=60, headers={"User-Agent": "alternance-searcher (usage personnel)"})
            r.raise_for_status()
            offres = analyser_flux(r.content)
        except (requests.RequestException, ET.ParseError) as e:
            log.warning("Connexion Emploi %s : %s", url, e)
            continue
        log.info("Connexion Emploi %s : %d offres", url.split("/")[3], len(offres))
        for o in offres:
            resultats.setdefault(o.url or o.id, o)
    return list(resultats.values())
