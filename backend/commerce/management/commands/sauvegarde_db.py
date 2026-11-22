"""Crée une sauvegarde JSON compressée et chiffrée; l'envoie vers S3 en production."""

from datetime import datetime, timezone
from hashlib import sha256
from io import StringIO
from pathlib import Path
import gzip
import uuid

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.management import BaseCommand, call_command, CommandError
from commerce.backup_storage import client_s3, cle_objet_s3


class Command(BaseCommand):
    help = "Exporte la base en sauvegarde compressée et chiffrée; en production, l'envoie vers S3."

    def add_arguments(self, parser):
        parser.add_argument("--sortie", type=Path, help="Copie locale chiffrée facultative.")

    def handle(self, *args, **options):
        if settings.EST_PRODUCTION and not settings.SAUVEGARDE_S3_ACTIVE:
            raise CommandError(
                "Sauvegarde de production désactivée : configurez BACKUP_ENCRYPTION_KEY et "
                "BACKUP_S3_BUCKET ensemble. Aucun fichier de sauvegarde n'a été créé."
            )
        if not settings.BACKUP_ENCRYPTION_KEY:
            raise CommandError("BACKUP_ENCRYPTION_KEY n'est pas configurée.")
        try:
            chiffreur = Fernet(settings.BACKUP_ENCRYPTION_KEY.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as erreur:
            raise CommandError("BACKUP_ENCRYPTION_KEY doit être une clé Fernet valide.") from erreur

        texte = StringIO()
        call_command("dumpdata", exclude=["contenttypes", "sessions"], indent=2, stdout=texte, verbosity=0)
        chiffre = chiffreur.encrypt(gzip.compress(texte.getvalue().encode("utf-8"), mtime=0))
        empreinte = sha256(chiffre).hexdigest()
        date = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
        nom = f"sauvegarde_{date}_{uuid.uuid4().hex[:8]}.json.gz.fernet"

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
            cle = cle_objet_s3(nom)
            try:
                s3 = client_s3()
                parametres = dict(
                    Bucket=settings.BACKUP_S3_BUCKET,
                    Key=cle,
                    Body=chiffre,
                    ContentType="application/octet-stream",
                    Metadata={"sha256": empreinte, "format": "fernet-gzip-json"},
                )
                if settings.BACKUP_S3_SERVER_SIDE_ENCRYPTION:
                    parametres["ServerSideEncryption"] = settings.BACKUP_S3_SERVER_SIDE_ENCRYPTION
                s3.put_object(**parametres)
                confirmation = s3.head_object(Bucket=settings.BACKUP_S3_BUCKET, Key=cle)
                if confirmation.get("Metadata", {}).get("sha256") != empreinte:
                    raise CommandError("La vérification de la sauvegarde S3 a échoué.")
            except CommandError:
                raise
            except Exception as erreur:
                raise CommandError(
                    "L'envoi ou la vérification S3 a échoué. Vérifiez le bucket, la région et les droits IAM."
                ) from erreur
            self.stdout.write(self.style.SUCCESS(f"Copie chiffrée envoyée et vérifiée sur S3 : {cle}"))
        elif not destination and not settings.EST_PRODUCTION:
            destination = Path.cwd() / "backups" / nom
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(chiffre)
            self.stdout.write(self.style.SUCCESS(f"Copie locale chiffrée créée : {destination}"))
        elif not destination:
            raise CommandError(
                "Aucune sauvegarde S3 n'a été créée. Les sauvegardes locales automatiques sont désactivées en production."
            )
        self.stdout.write(f"Empreinte SHA-256 du fichier chiffré : {empreinte}")
