from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Offre:
    """Une offre (ou une entreprise susceptible de recruter) normalisée, quelle que soit la source."""

    id: str
    source: str
    titre: str
    entreprise: str = ""
    lieu: str = ""
    url: str = ""
    description: str = ""
    publie_le: str = ""          # date ISO (AAAA-MM-JJ) si connue
    debut: str = ""              # date ISO de début de contrat si connue
    type_contrat: str = ""
    taille_entreprise: str = ""  # ex. « 1000-1999 »
    secteur: str = ""            # libellé NAF ou équivalent
    diplome: str = ""
    niveau_diplome: int | None = None  # nomenclature européenne (3 à 7)
    distance_km: float | None = None
    nature: str = "offre"        # « offre » ou « recruteur » (candidature spontanée)

    # Remplis par le scoring
    score: int = 0
    raisons: list[str] = field(default_factory=list)
    alertes: list[str] = field(default_factory=list)

    # Rempli par le stockage
    vu_le: str = ""
    nouveau: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Offre":
        champs = cls.__dataclass_fields__
        return cls(**{k: v for k, v in d.items() if k in champs})
