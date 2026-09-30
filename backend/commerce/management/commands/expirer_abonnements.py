"""Marque comme expirés les essais et abonnements arrivés à échéance."""

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from commerce.models import Abonnement


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Expire les abonnements dont la date de fin est passée."

    def handle(self, *args, **options):
        maintenant = timezone.now()
        ids = list(Abonnement.objects.filter(
            statut__in=[Abonnement.Statut.ESSAI, Abonnement.Statut.ACTIF],
            date_fin__lte=maintenant,
        ).values_list("pk", flat=True))
        if ids:
            Abonnement.objects.filter(pk__in=ids).update(statut=Abonnement.Statut.EXPIRE)
        logger.info("expiration_abonnements_terminee", extra={"nombre_expire": len(ids)})
        self.stdout.write(self.style.SUCCESS(f"Abonnements expirés : {len(ids)}."))
