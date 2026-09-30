"""Envoi d'emails transactionnels isolé derrière une interface fournisseur."""

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags

from config.observabilite import nettoyer_objet

logger = logging.getLogger(__name__)
_URL_BREVO = "https://api.brevo.com/v3/smtp/email"
_DELAI_REQUETE_SECONDES = 10


class ErreurEnvoiEmail(Exception):
    """Erreur d'envoi email sans détail fournisseur ni secret exposé."""


def envoyer_email(destinataire, sujet, contenu):
    """Envoie un email HTML via Brevo ou simule l'envoi sans réseau.

    ``contenu`` est du HTML construit par le backend avec valeurs échappées.
    Retourne ``True`` si l'email est accepté ou simulé. Lève ``ValueError``
    pour les données invalides et ``ErreurEnvoiEmail`` en cas d'échec fournisseur.
    """
    try:
        validate_email(destinataire)
    except (ValidationError, TypeError) as erreur:
        raise ValueError("L'adresse email du destinataire est invalide.") from erreur
    if not isinstance(sujet, str) or not sujet.strip() or "\n" in sujet or "\r" in sujet:
        raise ValueError("L'objet de l'email est invalide.")
    if not isinstance(contenu, str) or not contenu.strip():
        raise ValueError("Le contenu de l'email ne peut pas être vide.")

    destinataire = destinataire.strip().lower()
    if settings.EMAIL_SIMULATION:
        evenement = nettoyer_objet({
            "email": destinataire,
            "sujet": sujet,
            "contenu": contenu,
        })
        logger.info("Email simulé : %s", json.dumps(evenement, ensure_ascii=False))
        return True

    cle_api = settings.BREVO_API_KEY
    expediteur = settings.BREVO_SENDER_EMAIL
    nom_expediteur = settings.BREVO_SENDER_NAME
    if not cle_api or not expediteur:
        raise ErreurEnvoiEmail("La configuration du service email est incomplète.")
    try:
        validate_email(expediteur)
    except ValidationError as erreur:
        raise ErreurEnvoiEmail("L'adresse email expéditeur est invalide.") from erreur

    corps = json.dumps({
        "sender": {"email": expediteur, "name": nom_expediteur},
        "to": [{"email": destinataire}],
        "subject": sujet.strip(),
        "htmlContent": contenu,
        "textContent": strip_tags(contenu),
    }, ensure_ascii=False).encode("utf-8")
    requete = Request(
        _URL_BREVO,
        data=corps,
        headers={
            "api-key": cle_api,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(requete, timeout=_DELAI_REQUETE_SECONDES) as reponse:
            resultat = json.loads(reponse.read().decode("utf-8"))
            if reponse.status != 201 or not resultat.get("messageId"):
                raise ErreurEnvoiEmail("Brevo n'a pas accepté l'email.")
    except ErreurEnvoiEmail:
        raise
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        logger.warning("Le fournisseur email n'a pas répondu correctement.")
        raise ErreurEnvoiEmail("Le fournisseur email n'a pas accepté l'envoi.") from None
    return True
