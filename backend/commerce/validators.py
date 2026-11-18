"""Validations partagées du domaine commercial."""

import re

from django.core.exceptions import ValidationError
import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat

def normaliser_telephone_international(valeur):
    """Valide et retourne un numéro E.164, tous pays confondus.

    L'ancien plan béninois à huit chiffres reste accepté à l'entrée et est
    converti au plan actuel à dix chiffres avec le préfixe 01.
    """
    valeur = valeur or ""
    if re.fullmatch(r"\+229(?!01)[0-9]{8}", valeur):
        valeur = f"+22901{valeur[4:]}"
    try:
        numero = phonenumbers.parse(valeur, None)
    except NumberParseException as erreur:
        raise ValidationError(
            "Choisissez un pays puis saisissez un numéro de téléphone valide."
        ) from erreur
    if (
        not valeur.startswith("+")
        or not phonenumbers.is_valid_number(numero)
        or phonenumbers.format_number(numero, PhoneNumberFormat.E164) != valeur
    ):
        raise ValidationError(
            "Saisissez un numéro valide avec son indicatif international (ex. +22961020304)."
        )
    return phonenumbers.format_number(numero, PhoneNumberFormat.E164)


def valider_telephone_international(valeur):
    """Valide un numéro réel au format international E.164 (tous pays)."""
    normaliser_telephone_international(valeur)


# Gardé pour que les migrations historiques restent importables, sans créer
# une migration de schéma uniquement pour changer le chemin du validateur.
def valider_telephone_benin(valeur):
    return valider_telephone_international(valeur)
