"""Historique des offres déjà vues (data/offres.json) pour signaler les nouveautés."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from .models import Offre

CONSERVATION_JOURS = 120


def charger(chemin: Path) -> dict[str, dict]:
    if chemin.exists():
        return json.loads(chemin.read_text(encoding="utf-8"))
    return {}


def fusionner(offres: list[Offre], historique: dict[str, dict], aujourdhui: date | None = None) -> dict[str, dict]:
    aujourdhui = aujourdhui or date.today()
    jour = aujourdhui.isoformat()
    for o in offres:
        ancien = historique.get(o.id)
        o.vu_le = ancien["vu_le"] if ancien else jour
        o.nouveau = o.vu_le == jour
        historique[o.id] = {"vu_le": o.vu_le, "derniere_vue": jour, "titre": o.titre,
                            "entreprise": o.entreprise, "score": o.score, "url": o.url}
    limite = (aujourdhui - timedelta(days=CONSERVATION_JOURS)).isoformat()
    return {k: v for k, v in historique.items() if v.get("derniere_vue", jour) >= limite}


def sauver(chemin: Path, historique: dict[str, dict]) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(historique, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
