"""Crée une sauvegarde JSON compressée et chiffrée; l'envoie vers S3 en production."""

from datetime import datetime, timezone
from hashlib import sha256
from io import StringIO
from pathlib import Path
import gzip

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.management import BaseCommand, call_command, CommandError


class Command(BaseCommand):
    help = "Exporte la base en sauvegarde compressée et chiffrée; en production, l'envoie vers S3."

    def add_arguments(self, parser):
        parser.add_argument("--sortie", type=Path, help="Copie locale chiffrée facultative.")

    def handle(self, *args, **options):
        if not settings.BACKUP_ENCRYPTION_KEY:
            raise CommandError("BACKUP_ENCRYPTION_KEY n'est pas configurée.")
        if settings.EST_PRODUCTION and not settings.BACKUP_S3_BUCKET:
            raise CommandError("BACKUP_S3_BUCKET est obligatoire en production.")
        try:
            chiffreur = Fernet(settings.BACKUP_ENCRYPTION_KEY.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as erreur:
            raise CommandError("BACKUP_ENCRYPTION_KEY doit être une clé Fernet valide.") from erreur

        texte = StringIO()
        call_command("dumpdata", exclude=["contenttypes", "sessions"], indent=2, stdout=texte, verbosity=0)
        chiffre = chiffreur.encrypt(gzip.compress(texte.getvalue().encode("utf-8"), mtime=0))
        empreinte = sha256(chiffre).hexdigest()
        date = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        nom = f"sauvegarde_{date}.json.gz.fernet"

        destination = options.get("sortie")
        if destination:
            destination = destination.expanduser().resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporaire = destination.with_suffix(destination.suffix + ".tmp")
            try:
                temporaire.write_bytes(chiffre)
                temporaire.replace(destination)
            finally:
                if temporaire.exists():
                    temporaire.unlink()
            self.stdout.write(self.style.SUCCESS(f"Copie locale chiffrée créée : {destination}"))

        if settings.BACKUP_S3_BUCKET:
            import boto3
            s3 = boto3.client("s3", region_name=settings.AWS_REGION or None, endpoint_url=settings.AWS_ENDPOINT_URL or None)
            cle = f"{settings.BACKUP_S3_PREFIX}/{nom}" if settings.BACKUP_S3_PREFIX else nom
            s3.put_object(
                Bucket=settings.BACKUP_S3_BUCKET, Key=cle, Body=chiffre,
                ServerSideEncryption="AES256", Metadata={"sha256": empreinte, "format": "fernet-gzip-json"},
            )
            self.stdout.write(self.style.SUCCESS(f"Copie chiffrée envoyée au stockage externe : {cle}"))
        elif not destination:
            destination = Path.cwd() / "backups" / nom
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(chiffre)
            self.stdout.write(self.style.SUCCESS(f"Copie locale chiffrée créée : {destination}"))
        self.stdout.write(f"Empreinte SHA-256 du fichier chiffré : {empreinte}")
