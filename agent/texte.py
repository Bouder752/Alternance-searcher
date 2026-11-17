import re
import unicodedata
from functools import lru_cache


def normaliser(texte: str) -> str:
    """Minuscules, sans accents, espaces simplifiés."""
    if not texte:
        return ""
    t = unicodedata.normalize("NFKD", texte)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower().replace("’", "'")
    return re.sub(r"\s+", " ", t).strip()


@lru_cache(maxsize=4096)
def _motif(terme: str) -> re.Pattern:
    t = re.escape(normaliser(terme))
    return re.compile(rf"(?<![\w]){t}(?![\w])")


def contient(texte_normalise: str, terme: str) -> bool:
    return bool(_motif(terme).search(texte_normalise))


def premier_terme(texte_normalise: str, termes) -> str | None:
    for terme in termes:
        if contient(texte_normalise, terme):
            return terme
    return None


def nettoyer_html(texte: str) -> str:
    import html

    texte = re.sub(r"<[^>]+>", " ", texte or "")
    return re.sub(r"\s+", " ", html.unescape(texte)).strip()
