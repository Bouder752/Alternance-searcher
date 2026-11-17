"""Point d'entrée : python -m agent"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import requests
import yaml

from . import rapport, scoring, stockage
from .sources import connexion_emploi, lba, liens

RACINE = Path(__file__).resolve().parent.parent
SOURCES = {"lba": lba, "connexion_emploi": connexion_emploi}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Agent de veille d'offres d'alternance")
    p.add_argument("--config", default=RACINE / "config" / "profil.yaml", type=Path)
    p.add_argument("--sources", default=",".join(SOURCES), help="sources à interroger, séparées par des virgules")
    p.add_argument("--sortie", default=RACINE, type=Path, help="dossier contenant data/ et reports/")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    session = requests.Session()

    brutes, par_source = [], {}
    for nom in [s.strip() for s in args.sources.split(",") if s.strip()]:
        offres = SOURCES[nom].collecter(config, session=session)
        par_source[nom] = len(offres)
        brutes += offres

    retenues, exclues = scoring.filtrer_et_noter(brutes, config)

    chemin_historique = args.sortie / "data" / "offres.json"
    historique = stockage.fusionner(retenues, stockage.charger(chemin_historique))
    stockage.sauver(chemin_historique, historique)

    stats = {"par_source": par_source, "exclues": exclues}
    rapport.ecrire(retenues, liens.generer(config), stats, args.sortie / "reports", args.sortie / "data")

    nouveaux = sum(o.nouveau for o in retenues)
    logging.info("%d résultats retenus (%d nouveaux) sur %d collectés. Rapport : reports/index.html",
                 len(retenues), nouveaux, len(brutes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
