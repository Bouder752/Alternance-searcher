"""Tests hors ligne : python -m unittest discover tests"""

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import yaml

from agent import rapport, scoring, stockage
from agent.sources import connexion_emploi, lba

ICI = Path(__file__).parent
CONFIG = yaml.safe_load((ICI.parent / "config" / "profil.yaml").read_text(encoding="utf-8"))


class FausseReponse:
    def __init__(self, data=None, content=b"", status_code=200):
        self._data, self.content, self.status_code = data, content, status_code

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class FausseSession:
    def __init__(self, reponse):
        self.reponse, self.headers, self.appels = reponse, {}, []

    def get(self, url, params=None, **_):
        self.appels.append((url, params))
        return self.reponse


def offres_lba():
    data = json.loads((ICI / "fixtures" / "lba_search.json").read_text(encoding="utf-8"))
    config = dict(CONFIG, lba_romes={"N1301": "test"})
    session = FausseSession(FausseReponse(data))
    with mock.patch.dict("os.environ", {"LBA_API_KEY": "cle-test"}), mock.patch("time.sleep"):
        offres = lba.collecter(config, session=session)
    return offres, session


class TestLBA(unittest.TestCase):
    def test_sans_cle_la_source_est_ignoree(self):
        with mock.patch.dict("os.environ", {"LBA_API_KEY": ""}):
            self.assertEqual(lba.collecter(CONFIG, session=FausseSession(None)), [])

    def test_conversion_et_parametres(self):
        offres, session = offres_lba()
        self.assertEqual(len(offres), 6)
        url, params = session.appels[0]
        self.assertEqual(params["radius"], 50)
        self.assertEqual(params["target_diploma_level"], "7")
        self.assertEqual(session.headers["Authorization"], "Bearer cle-test")
        lilly = next(o for o in offres if o.id == "lba:job-1")
        self.assertEqual(lilly.entreprise, "Lilly")
        self.assertEqual(lilly.debut, "2027-09-01")
        self.assertEqual(lilly.niveau_diplome, 7)
        self.assertAlmostEqual(lilly.distance_km, 10.4, delta=1)
        self.assertIn("Power BI", lilly.description)


class TestScoring(unittest.TestCase):
    def test_classement_et_exclusions(self):
        offres, _ = offres_lba()
        retenues, exclues = scoring.filtrer_et_noter(offres, CONFIG)
        ids = [o.id for o in retenues]
        self.assertNotIn("lba:job-2", ids)  # commercial terrain
        self.assertEqual(exclues.get("poste commercial terrain"), 1)
        self.assertNotIn("lba:job-3", ids)  # BTS, petite structure → score trop faible
        self.assertNotIn("lba-rec:rec-2", ids)  # petit commerce
        self.assertIn("lba:job-1", ids)
        self.assertIn("lba:job-4", ids)
        self.assertIn("lba-rec:rec-1", ids)
        # Les offres passent avant les candidatures spontanées
        self.assertEqual(retenues[-1].nature, "recruteur")
        lilly = next(o for o in retenues if o.id == "lba:job-1")
        self.assertGreaterEqual(lilly.score, 70)
        self.assertTrue(any("Pharmaceutique" in r for r in lilly.raisons))

    def test_connexion_emploi(self):
        xml = (ICI / "fixtures" / "connexion_emploi.rss").read_bytes()
        offres = connexion_emploi.collecter(CONFIG, session=FausseSession(FausseReponse(content=xml)))
        self.assertEqual(len(offres), 3)  # dédoublonnées entre flux FR et DE
        retenues, exclues = scoring.filtrer_et_noter(offres, CONFIG)
        self.assertEqual([o.lieu for o in retenues], ["Molsheim"])
        self.assertEqual(exclues, {"pas une alternance": 1, "lieu hors zone ou inconnu": 1})

    def test_mots_sans_accents_ni_casse(self):
        from agent.models import Offre
        o = Offre(id="x", source="La bonne alternance", titre="CHARGEE DE MISSION DEVELOPPEMENT DURABLE")
        scoring.noter(o, CONFIG)
        self.assertTrue(any("RSE" in r for r in o.raisons))
        self.assertTrue(any("mission" in r for r in o.raisons))


class TestStockageEtRapport(unittest.TestCase):
    def test_nouveautes_et_rapport(self):
        offres, _ = offres_lba()
        retenues, _ = scoring.filtrer_et_noter(offres, CONFIG)
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            h = stockage.fusionner(retenues, {}, date(2026, 11, 17))
            self.assertTrue(all(o.nouveau for o in retenues))
            h = stockage.fusionner(retenues, h, date(2026, 11, 18))
            self.assertFalse(any(o.nouveau for o in retenues))
            stockage.sauver(d / "offres.json", h)
            self.assertEqual(len(stockage.charger(d / "offres.json")), len(retenues))
            rapport.ecrire(retenues, [], {"par_source": {"lba": 6}}, d / "reports", d / "data", "2026-11-18")
            page = (d / "reports" / "index.html").read_text(encoding="utf-8")
            self.assertIn("Alternant Supply Chain Planner", page)
            self.assertIn("| Score |", (d / "reports" / "rapport.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
