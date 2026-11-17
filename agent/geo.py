"""Géolocalisation simple : communes autour de Strasbourg (pour les sources sans coordonnées GPS)."""

from math import asin, cos, radians, sin, sqrt

from .texte import contient, normaliser

COMMUNES = {
    "strasbourg": (48.573, 7.752), "schiltigheim": (48.606, 7.750), "bischheim": (48.616, 7.752),
    "hoenheim": (48.625, 7.756), "illkirch": (48.530, 7.715), "illkirch-graffenstaden": (48.530, 7.715),
    "ostwald": (48.542, 7.711), "lingolsheim": (48.557, 7.683), "eckbolsheim": (48.581, 7.687),
    "geispolsheim": (48.515, 7.645), "entzheim": (48.534, 7.637), "fegersheim": (48.490, 7.680),
    "eschau": (48.488, 7.717), "erstein": (48.422, 7.663), "benfeld": (48.371, 7.594),
    "obernai": (48.462, 7.482), "rosheim": (48.497, 7.470), "molsheim": (48.542, 7.492),
    "mutzig": (48.539, 7.455), "dachstein": (48.562, 7.532), "duttlenheim": (48.526, 7.567),
    "duppigheim": (48.528, 7.596), "holtzheim": (48.556, 7.645), "marlenheim": (48.621, 7.491),
    "wasselonne": (48.637, 7.449), "saverne": (48.741, 7.363), "landersheim": (48.685, 7.497),
    "brumath": (48.733, 7.711), "vendenheim": (48.669, 7.713), "reichstett": (48.648, 7.754),
    "mundolsheim": (48.641, 7.715), "hoerdt": (48.696, 7.784), "la wantzenau": (48.658, 7.829),
    "gambsheim": (48.693, 7.882), "haguenau": (48.816, 7.790), "bischwiller": (48.766, 7.857),
    "drusenheim": (48.762, 7.947), "herrlisheim": (48.731, 7.904), "soufflenheim": (48.830, 7.962),
    "selestat": (48.259, 7.454), "barr": (48.408, 7.448), "rhinau": (48.319, 7.705),
    "marckolsheim": (48.163, 7.545), "schirmeck": (48.482, 7.217), "hochfelden": (48.756, 7.567),
    "dettwiller": (48.754, 7.468), "bouxwiller": (48.825, 7.483), "ingwiller": (48.873, 7.480),
    "seltz": (48.893, 8.105), "roeschwoog": (48.826, 8.035), "wissembourg": (49.037, 7.946),
    "kehl": (48.573, 7.816), "offenburg": (48.473, 7.944), "lahr": (48.338, 7.873),
    "achern": (48.631, 8.077), "oberkirch": (48.532, 8.079), "colmar": (48.079, 7.358),
    "mulhouse": (47.750, 7.336), "huningue": (47.592, 7.583), "bale": (47.559, 7.588),
    "basel": (47.559, 7.588), "karlsruhe": (49.007, 8.404), "freiburg": (47.999, 7.842),
}

REGIONS_PROCHES = ["bas-rhin", "(67)", "67000", "eurometropole", "eurométropole"]


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def distance_depuis_texte(lieu: str, lat: float, lon: float) -> float | None:
    """Distance (km) de la commune connue la plus proche citée dans `lieu`, sinon None."""
    t = normaliser(lieu).replace("-", " ")
    meilleure = None
    for nom, (clat, clon) in COMMUNES.items():
        if contient(t, nom.replace("-", " ")):
            d = distance_km(lat, lon, clat, clon)
            meilleure = d if meilleure is None else min(meilleure, d)
    if meilleure is None and any(normaliser(r) in t for r in REGIONS_PROCHES):
        return 0.0
    return meilleure
