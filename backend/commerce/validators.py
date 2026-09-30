"""Validations partagées du domaine commercial."""

import re

from django.core.exceptions import ValidationError

FORMAT_TELEPHONE = re.compile(r"^\+229[0-9]{8}$")


def valider_telephone_benin(valeur):
    """Exige le format international béninois exact, sans espace ni séparateur."""
    if not FORMAT_TELEPHONE.fullmatch(valeur or ""):
        raise ValidationError(
            "Saisissez un numéro béninois valide au format +229 suivi de 8 chiffres (ex. +22961020304)."
        )
