"""Génération des rapports : reports/index.html (lisible dans un navigateur) et reports/rapport.md (lisible sur GitHub)."""

from __future__ import annotations

import html
import json
from datetime import date
from pathlib import Path

from .models import Offre


def _e(v) -> str:
    return html.escape(str(v or ""))


def _carte(o: Offre) -> str:
    meta = " · ".join(filter(None, [
        _e(o.entreprise),
        _e(o.lieu) + (f" ({o.distance_km:.0f} km)" if o.distance_km is not None else ""),
        f"publiée le {_e(o.publie_le)}" if o.publie_le else "",
        f"début {_e(o.debut)}" if o.debut else "",
        f"{_e(o.taille_entreprise)} salariés" if o.taille_entreprise else "",
    ]))
    raisons = "".join(f"<li>{_e(r)}</li>" for r in o.raisons)
    alertes = "".join(f"<li class='alerte'>{_e(a)}</li>" for a in o.alertes)
    extrait = _e(o.description[:400] + ("…" if len(o.description) > 400 else ""))
    badge = "<span class='badge'>Nouveau</span>" if o.nouveau else ""
    return f"""
<article class="carte" data-nouveau="{int(o.nouveau)}" data-nature="{o.nature}">
  <div class="tete">
    <span class="score" style="--s:{o.score}">{o.score}</span>
    <div>
      <h3><a href="{_e(o.url)}" target="_blank" rel="noopener">{_e(o.titre)}</a> {badge}</h3>
      <p class="meta">{meta}</p>
      <p class="source">{_e(o.source)}{' · ' + _e(o.secteur) if o.secteur else ''}</p>
    </div>
  </div>
  <ul class="raisons">{raisons}{alertes}</ul>
  {f'<details><summary>Extrait</summary><p>{extrait}</p></details>' if extrait else ''}
</article>"""


CSS = """
:root{--fond:#f6f7f9;--carte:#fff;--texte:#1d2430;--doux:#5d6878;--bord:#e2e6ec;--accent:#2457c5;--ok:#1f8a4c;--alerte:#b3541e}
@media (prefers-color-scheme:dark){:root{--fond:#12151a;--carte:#1b2028;--texte:#e6e9ee;--doux:#9aa4b2;--bord:#2b323d;--accent:#7aa2ff;--ok:#4cc38a;--alerte:#f0a060}}
*{box-sizing:border-box}body{margin:0;background:var(--fond);color:var(--texte);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:920px;margin:0 auto;padding:24px 16px 64px}h1{margin:0 0 4px;font-size:1.6rem}
.sous{color:var(--doux);margin:0 0 20px}.filtres{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 16px}
.filtres button{border:1px solid var(--bord);background:var(--carte);color:var(--texte);border-radius:999px;padding:6px 14px;cursor:pointer;font:inherit}
.filtres button.actif{background:var(--accent);border-color:var(--accent);color:#fff}
.carte{background:var(--carte);border:1px solid var(--bord);border-radius:12px;padding:14px 16px;margin:0 0 12px}
.tete{display:flex;gap:14px;align-items:flex-start}.tete h3{margin:0;font-size:1.05rem}.tete a{color:var(--accent);text-decoration:none}
.score{flex:none;width:44px;height:44px;border-radius:50%;display:grid;place-items:center;font-weight:700;color:#fff;
 background:color-mix(in srgb,var(--ok) calc(var(--s)*1%),var(--alerte))}
.meta,.source{margin:2px 0 0;color:var(--doux);font-size:.88rem}.badge{background:var(--ok);color:#fff;border-radius:6px;padding:1px 7px;font-size:.75rem;vertical-align:middle}
.raisons{margin:10px 0 0;padding-left:20px;font-size:.9rem}.raisons .alerte{color:var(--alerte)}
details{margin-top:8px;font-size:.88rem;color:var(--doux)}h2{margin:32px 0 12px;font-size:1.2rem}
.liens{display:grid;gap:10px}.liens div{background:var(--carte);border:1px solid var(--bord);border-radius:10px;padding:10px 14px}
.liens a{margin-right:12px;color:var(--accent);white-space:nowrap}.vide{color:var(--doux)}
"""

JS = """
const boutons=document.querySelectorAll('.filtres button');
boutons.forEach(b=>b.addEventListener('click',()=>{boutons.forEach(x=>x.classList.remove('actif'));b.classList.add('actif');
const f=b.dataset.f;document.querySelectorAll('.carte').forEach(c=>{const ok=f==='tout'||(f==='nouveau'&&c.dataset.nouveau==='1')||c.dataset.nature===f;c.style.display=ok?'':'none'})}));
"""


def html_rapport(offres: list[Offre], liens: list[dict], stats: dict, jour: str) -> str:
    nb_nouveaux = sum(o.nouveau for o in offres)
    nb_offres = sum(o.nature == "offre" for o in offres)
    nb_rec = len(offres) - nb_offres
    cartes = "".join(_carte(o) for o in offres) or "<p class='vide'>Aucune offre retenue aujourd'hui.</p>"
    blocs_liens = "".join(
        f"<div><strong>{_e(l['requete'])}</strong><br>"
        + "".join(f"<a href='{_e(u)}' target='_blank' rel='noopener'>{_e(s)}</a>" for s, u in l["sites"].items())
        + "</div>" for l in liens)
    sources = ", ".join(f"{k} : {v}" for k, v in stats.get("par_source", {}).items()) or "aucune"
    exclues = ", ".join(f"{k} : {v}" for k, v in stats.get("exclues", {}).items()) or "aucune"
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Veille alternance</title><style>{CSS}</style></head>
<body><main>
<h1>Veille alternance — {jour}</h1>
<p class="sous">{nb_offres} offres et {nb_rec} entreprises pour candidature spontanée retenues, dont {nb_nouveaux} nouvelles.<br>
Collectées par source : {_e(sources)}. Écartées : {_e(exclues)}.</p>
<div class="filtres">
<button class="actif" data-f="tout">Tout</button><button data-f="nouveau">Nouveautés ({nb_nouveaux})</button>
<button data-f="offre">Offres ({nb_offres})</button><button data-f="recruteur">Candidatures spontanées ({nb_rec})</button></div>
{cartes}
<h2>Recherches à faire toi-même</h2>
<p class="sous">Ces sites n'autorisent pas la collecte automatique : ouvre les liens pour vérifier les nouveautés.</p>
<div class="liens">{blocs_liens}</div>
</main><script>{JS}</script></body></html>"""


def markdown_rapport(offres: list[Offre], liens: list[dict], stats: dict, jour: str) -> str:
    lignes = [f"# Veille alternance — {jour}", ""]
    nouveaux = [o for o in offres if o.nouveau]
    lignes.append(f"**{len(offres)} résultats retenus, dont {len(nouveaux)} nouveaux.** "
                  f"Version interactive : `reports/index.html`.")
    lignes.append("")
    for titre, sel in (("Offres", "offre"), ("Candidatures spontanées (grandes entreprises qui recrutent des alternants)", "recruteur")):
        groupe = [o for o in offres if o.nature == sel]
        lignes += [f"## {titre} ({len(groupe)})", ""]
        if not groupe:
            lignes += ["_Aucun résultat._", ""]
            continue
        lignes += ["| Score | Poste | Entreprise | Lieu | Pourquoi |", "|---:|---|---|---|---|"]
        for o in groupe:
            nouveau = " 🆕" if o.nouveau else ""
            pourquoi = "; ".join(o.raisons[:3] + [f"⚠️ {a}" for a in o.alertes[:2]]).replace("|", "/")
            lieu = (o.lieu or "").replace("|", "/")
            if o.distance_km is not None:
                lieu += f" ({o.distance_km:.0f} km)"
            lignes.append(f"| {o.score} | [{o.titre.replace('|', '/')}]({o.url}){nouveau} | "
                          f"{o.entreprise.replace('|', '/')} | {lieu} | {pourquoi} |")
        lignes.append("")
    lignes += ["## Recherches à faire toi-même", ""]
    for l in liens:
        lignes.append(f"- **{l['requete']}** : " + " · ".join(f"[{s}]({u})" for s, u in l["sites"].items()))
    return "\n".join(lignes) + "\n"


def ecrire(offres: list[Offre], liens: list[dict], stats: dict, dossier_rapports: Path, dossier_data: Path,
           jour: str | None = None) -> None:
    jour = jour or date.today().isoformat()
    dossier_rapports.mkdir(parents=True, exist_ok=True)
    dossier_data.mkdir(parents=True, exist_ok=True)
    (dossier_rapports / "index.html").write_text(html_rapport(offres, liens, stats, jour), encoding="utf-8")
    (dossier_rapports / "rapport.md").write_text(markdown_rapport(offres, liens, stats, jour), encoding="utf-8")
    # Données brutes du jour (utilisables pour une analyse par Claude)
    (dossier_data / "resultats.json").write_text(
        json.dumps({"date": jour, "stats": stats, "offres": [o.to_dict() for o in offres]},
                   ensure_ascii=False, indent=1), encoding="utf-8")
