"""Restaure une sauvegarde chiffrée dans la base configurée."""

import gzip
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core import serializers
from django.core.management import BaseCommand, CommandError
from django.db import transaction
from commerce.branding import NOM_APPLICATION


class Command(BaseCommand):
    help = f"Déchiffre et restaure une sauvegarde {NOM_APPLICATION} dans la base configurée."

    def add_arguments(self, parser):
        parser.add_argument("source", type=Path, help="Fichier chiffré .json.gz.fernet.")
        parser.add_argument("--confirmer-production", action="store_true", help="Autorise explicitement une restauration en production.")

    def handle(self, *args, **options):
        if settings.EST_PRODUCTION and not options["confirmer_production"]:
            raise CommandError("La restauration en production exige --confirmer-production.")
        if not settings.BACKUP_ENCRYPTION_KEY:
            raise CommandError("BACKUP_ENCRYPTION_KEY n'est pas configurée.")
        try:
            chiffre = options["source"].expanduser().resolve().read_bytes()
            texte = gzip.decompress(Fernet(settings.BACKUP_ENCRYPTION_KEY.encode("ascii")).decrypt(chiffre)).decode("utf-8")
            objets = list(serializers.deserialize("json", texte))
        except (OSError, ValueError, UnicodeEncodeError, InvalidToken, gzip.BadGzipFile, EOFError) as erreur:
            raise CommandError("Sauvegarde illisible, altérée ou clé de déchiffrement incorrecte.") from erreur

        try:
            with transaction.atomic():
                for objet in objets:
                    objet.save()
        except Exception as erreur:
            raise CommandError("La restauration a échoué; la transaction a été annulée.") from erreur
        self.stdout.write(self.style.SUCCESS(f"Restauration terminée : {len(objets)} objets chargés."))
