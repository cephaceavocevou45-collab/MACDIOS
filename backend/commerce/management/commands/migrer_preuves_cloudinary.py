"""Copie les preuves existantes du disque local vers Cloudinary privé."""

import logging
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import FileSystemStorage
from django.core.management.base import BaseCommand
from django.db import transaction

from commerce.models import DemandePaiementManuel


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Migre vers Cloudinary les preuves qui existent encore dans le répertoire local."

    def add_arguments(self, parser):
        parser.add_argument(
            "--repertoire-source",
            default=str(settings.MEDIA_ROOT),
            help="Ancien MEDIA_ROOT, ou volume media persistant monté en lecture.",
        )

    def handle(self, *args, **options):
        stockage_source = FileSystemStorage(location=Path(options["repertoire_source"]))
        migrees = 0
        absentes = 0
        for demande in DemandePaiementManuel.objects.exclude(preuve="").iterator():
            ancien_nom = demande.preuve.name
            if not stockage_source.exists(ancien_nom):
                absentes += 1
                continue
            with stockage_source.open(ancien_nom, "rb") as fichier_source:
                with transaction.atomic():
                    demande.preuve.save(
                        Path(ancien_nom).name,
                        File(fichier_source, name=Path(ancien_nom).name),
                        save=False,
                    )
                    demande.save(update_fields=["preuve"])
            stockage_source.delete(ancien_nom)
            migrees += 1

        logger.info(
            "migration_preuves_cloudinary_terminee",
            extra={"nombre_migre": migrees, "nombre_absent": absentes},
        )
        self.stdout.write(self.style.SUCCESS(
            f"Preuves migrées vers Cloudinary : {migrees}; absentes du stockage source : {absentes}."
        ))
