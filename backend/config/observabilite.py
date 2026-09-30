"""Filtrage des valeurs sensibles avant Sentry ou les journaux de production."""

import json
import re
from datetime import datetime, timezone
from logging import Formatter

_CLE_SENSIBLE = re.compile(r"password|mot.?de.?passe|token|authorization|secret|api.?key|telephone|phone|email|courriel", re.I)
_TELEPHONE = re.compile(r"(?<!\w)(?:\+?\d[\d .()/-]{7,}\d)(?!\w)")
_EMAIL = re.compile(r"(?i)(?<![\w.+-])[\w.+-]+@[\w.-]+\.[a-z]{2,}(?![\w.-])")
_JWT = re.compile(r"(?<![\w-])eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")
_SECRET_DANS_TEXTE = re.compile(
    r"(?i)(password|mot.?de.?passe|token|secret|api.?key)\s*[:=]\s*[^\s,;]+"
)


def _nettoyer_texte(valeur):
    valeur = _JWT.sub("[JETON MASQUÉ]", str(valeur))
    valeur = _SECRET_DANS_TEXTE.sub(r"\1=[MASQUÉ]", valeur)
    valeur = _EMAIL.sub("[EMAIL MASQUÉ]", valeur)
    return _TELEPHONE.sub("[NUMÉRO MASQUÉ]", valeur)


def nettoyer_objet(valeur):
    if isinstance(valeur, dict):
        return {
            cle: "[MASQUÉ]" if _CLE_SENSIBLE.search(str(cle)) else nettoyer_objet(contenu)
            for cle, contenu in valeur.items()
        }
    if isinstance(valeur, list):
        return [nettoyer_objet(element) for element in valeur]
    if isinstance(valeur, str):
        return _nettoyer_texte(valeur)
    return valeur


def filtrer_evenement_sentry(event, hint):
    """Retire l'identité et masque secrets, JWT, numéros de téléphone et IP."""
    event.pop("user", None)
    return nettoyer_objet(event)


class JsonSansDonneesSensibles(Formatter):
    """Log JSON compact, sans contenu d'exception ni valeurs de requête."""

    def format(self, record):
        donnees = {
            "horodatage": datetime.now(timezone.utc).isoformat(),
            "niveau": record.levelname,
            "logger": record.name,
            "message": _nettoyer_texte(record.getMessage()),
        }
        if record.exc_info:
            donnees["exception"] = record.exc_info[0].__name__
        return json.dumps(donnees, ensure_ascii=False)
