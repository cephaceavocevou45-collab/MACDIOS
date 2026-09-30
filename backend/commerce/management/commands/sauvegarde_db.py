"""Produit une sauvegarde logique portable de la base Django au format JSON."""

from datetime import datetime
from pathlib import Path

from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Exporte les données Django pour une restauration avec la commande loaddata."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sortie", type=Path,
            help="Fichier de destination (par défaut : backend/backups/sauvegarde_<date>.json).",
        )

    def handle(self, *args, **options):
        destination = options["sortie"] or (
            Path.cwd() / "backups" / f"sauvegarde_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        destination = destination.expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporaire = destination.with_suffix(destination.suffix + ".tmp")
        try:
            with temporaire.open("w", encoding="utf-8", newline="\n") as sortie:
                call_command(
                    "dumpdata", exclude=["contenttypes", "sessions"], indent=2,
                    stdout=sortie, verbosity=0,
                )
            temporaire.replace(destination)
        finally:
            if temporaire.exists():
                temporaire.unlink()
        self.stdout.write(self.style.SUCCESS(f"Sauvegarde créée : {destination}"))
        self.stdout.write("Ce fichier contient des données sensibles, notamment des hashes de mots de passe ; protégez-le.")
