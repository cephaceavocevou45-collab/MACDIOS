"""Envoi SMS isolé derrière une interface fournisseur indépendante."""

import base64
import json
import logging
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ValidationError

from commerce.validators import valider_telephone_benin
from config.observabilite import nettoyer_objet

logger = logging.getLogger(__name__)
_URL_VONAGE = "https://rest.nexmo.com/sms/json"
_DELAI_REQUETE_SECONDES = 10


class ErreurEnvoiSms(Exception):
    """Erreur d'envoi SMS sans détail fournisseur ni secret exposé."""


def _valider_message(numero, message):
    """Valide le format téléphone officiel de l'application avant tout envoi."""
    try:
        valider_telephone_benin(numero)
    except ValidationError as erreur:
        raise ValueError("Le numéro doit respecter le format +229 suivi de 8 chiffres.") from erreur
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Le message SMS ne peut pas être vide.")


def envoyer_sms(numero, message):
    """Envoie un SMS via Vonage, ou simule l'envoi sans appeler le réseau.

    Lève ``ValueError`` si les données sont invalides et ``ErreurEnvoiSms`` si
    la configuration ou le fournisseur empêche l'envoi. Retourne ``True`` si
    le fournisseur accepte le message, ou si le mode simulation est actif.
    """
    _valider_message(numero, message)

    if settings.SMS_SIMULATION:
        evenement = nettoyer_objet({"numero": numero, "message": message})
        logger.info("SMS simulé : %s", json.dumps(evenement, ensure_ascii=False))
        return True

    api_key = settings.VONAGE_API_KEY
    api_secret = settings.VONAGE_API_SECRET
    expediteur = settings.VONAGE_SMS_SENDER
    if not api_key or not api_secret or not expediteur:
        raise ErreurEnvoiSms("La configuration du service SMS est incomplète.")

    identifiants = base64.b64encode(f"{api_key}:{api_secret}".encode("utf-8")).decode("ascii")
    # Vonage attend le numéro international sans le signe + dans le champ `to`.
    donnees = urlencode({
        "from": expediteur,
        "to": numero[1:],
        "text": message,
        "type": "unicode",
    }).encode("utf-8")
    requete = Request(
        _URL_VONAGE,
        data=donnees,
        headers={
            "Authorization": f"Basic {identifiants}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(requete, timeout=_DELAI_REQUETE_SECONDES) as reponse:
            resultat = json.loads(reponse.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        logger.warning("Le fournisseur SMS n'a pas répondu correctement.")
        raise ErreurEnvoiSms("Le fournisseur SMS n'a pas accepté l'envoi.") from None

    messages = resultat.get("messages", [])
    if not messages or messages[0].get("status") != "0":
        # Ne pas journaliser la réponse brute : elle peut contenir un numéro.
        logger.warning("Le fournisseur SMS a refusé l'envoi (code=%s).", re.sub(
            r"[^0-9]", "", str(messages[0].get("status", "inconnu"))[:8]
        ) if messages else "inconnu")
        raise ErreurEnvoiSms("Le fournisseur SMS n'a pas accepté l'envoi.")
    return True
