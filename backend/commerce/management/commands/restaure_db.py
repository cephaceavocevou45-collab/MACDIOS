"""Restaure une sauvegarde chiffrée dans la base configurée."""

import gzip
from hashlib import sha256
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core import serializers
from django.core.management import BaseCommand, CommandError
from django.db import transaction
from commerce.branding import NOM_APPLICATION
from commerce.backup_storage import client_s3


class Command(BaseCommand):
    help = f"Déchiffre et restaure une sauvegarde {NOM_APPLICATION} dans la base configurée."

    def add_arguments(self, parser):
        parser.add_argument("source", type=Path, nargs="?", help="Fichier chiffré .json.gz.fernet.")
        parser.add_argument("--s3-key", help="Clé exacte du fichier chiffré dans le bucket configuré.")
        parser.add_argument("--confirmer-production", action="store_true", help="Autorise explicitement une restauration en production.")

    def handle(self, *args, **options):
        if settings.EST_PRODUCTION and not options["confirmer_production"]:
            raise CommandError("La restauration en production exige --confirmer-production.")
        if not settings.BACKUP_ENCRYPTION_KEY:
            raise CommandError("BACKUP_ENCRYPTION_KEY n'est pas configurée.")
        if bool(options.get("source")) == bool(options.get("s3_key")):
            raise CommandError("Indiquez soit un fichier local, soit --s3-key, mais pas les deux.")
        try:
            if options.get("s3_key"):
                if not settings.BACKUP_S3_BUCKET:
                    raise CommandError("BACKUP_S3_BUCKET n'est pas configurée.")
                objet = client_s3().get_object(Bucket=settings.BACKUP_S3_BUCKET, Key=options["s3_key"])
                corps = objet["Body"]
                try:
                    chiffre = corps.read()
                finally:
                    corps.close()
                empreinte_attendue = objet.get("Metadata", {}).get("sha256")
                if not empreinte_attendue or sha256(chiffre).hexdigest() != empreinte_attendue:
                    raise CommandError("La sauvegarde S3 est incomplète ou son empreinte SHA-256 est invalide.")
            else:
                chiffre = options["source"].expanduser().resolve().read_bytes()
            texte = gzip.decompress(Fernet(settings.BACKUP_ENCRYPTION_KEY.encode("ascii")).decrypt(chiffre)).decode("utf-8")
            objets = list(serializers.deserialize("json", texte))
        except CommandError:
            raise
        except (OSError, ValueError, UnicodeEncodeError, InvalidToken, gzip.BadGzipFile, EOFError) as erreur:
            raise CommandError("Sauvegarde illisible, altérée ou clé de déchiffrement incorrecte.") from erreur
        except Exception as erreur:
            if options.get("s3_key"):
                raise CommandError("Téléchargement ou validation S3 impossible; vérifiez la clé et les droits IAM.") from erreur
            raise

        try:
            with transaction.atomic():
                for objet in objets:
                    objet.save()
        except Exception as erreur:
            raise CommandError("La restauration a échoué; la transaction a été annulée.") from erreur
        self.stdout.write(self.style.SUCCESS(f"Restauration terminée : {len(objets)} objets chargés."))
