"""Protection contre les renvois d'une même écriture après un délai réseau."""

import hashlib
import json
import re

from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from .models import RequeteIdempotente

_FORMAT_CLE = re.compile(r"^[A-Za-z0-9._:-]{8,100}$")


class CreationIdempotenteMixin:
    """Rejoue la réponse originale au lieu de recréer une opération financière."""

    operation_idempotente = ""

    def create(self, request, *args, **kwargs):
        cle = request.headers.get("Idempotency-Key", "").strip()
        if not cle:
            if getattr(settings, "EST_PRODUCTION", False):
                return Response(
                    {"detail": "Une clé de requête est nécessaire. Réessayez depuis l’application."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return super().create(request, *args, **kwargs)
        if not _FORMAT_CLE.fullmatch(cle):
            return Response(
                {"detail": "La clé de requête est invalide. Réessayez."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        corps = json.dumps(
            request.data,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
        empreinte = hashlib.sha256(corps.encode("utf-8")).hexdigest()

        # La contrainte unique et get_or_create coordonnent aussi deux envois
        # simultanés de la même clé sur plusieurs processus Django.
        with transaction.atomic():
            requete, creee = RequeteIdempotente.objects.get_or_create(
                commercant=request.user,
                operation=self.operation_idempotente,
                cle=cle,
                defaults={"empreinte": empreinte},
            )
            if not creee:
                if requete.empreinte != empreinte:
                    return Response(
                        {"detail": "Cette clé a déjà été utilisée pour une autre opération."},
                        status=status.HTTP_409_CONFLICT,
                    )
                return Response(requete.reponse, status=requete.code_http)

            reponse = super().create(request, *args, **kwargs)
            requete.code_http = reponse.status_code
            requete.reponse = reponse.data if isinstance(reponse.data, (dict, list)) else {}
            requete.save(update_fields=["code_http", "reponse"])
            return reponse
