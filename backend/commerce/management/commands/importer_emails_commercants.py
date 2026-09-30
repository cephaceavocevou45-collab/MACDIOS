"""Associe des emails vérifiés aux anciens comptes commerçants."""

import csv

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction


class Command(BaseCommand):
    help = "Importe les emails confirmés des anciens comptes depuis un CSV telephone,email."

    def add_arguments(self, parser):
        parser.add_argument("fichier", help="CSV UTF-8 avec les colonnes telephone,email.")
        parser.add_argument("--dry-run", action="store_true", help="Vérifie le fichier sans enregistrer les changements.")

    @transaction.atomic
    def handle(self, *args, **options):
        Utilisateur = get_user_model()
        entrees = []
        telephones_vus = set()
        emails_vus = set()
        try:
            with open(options["fichier"], encoding="utf-8-sig", newline="") as fichier:
                lecteur = csv.DictReader(fichier)
                if not lecteur.fieldnames or not {"telephone", "email"}.issubset(lecteur.fieldnames):
                    raise CommandError("Le CSV doit avoir les colonnes telephone,email.")
                for numero_ligne, ligne in enumerate(lecteur, start=2):
                    telephone = (ligne.get("telephone") or "").strip()
                    email = (ligne.get("email") or "").strip().lower()
                    if not telephone or not email:
                        raise CommandError(f"Ligne {numero_ligne} : téléphone et email sont obligatoires.")
                    try:
                        validate_email(email)
                    except ValidationError as erreur:
                        raise CommandError(f"Ligne {numero_ligne} : adresse email invalide.") from erreur
                    if telephone in telephones_vus:
                        raise CommandError(f"Ligne {numero_ligne} : téléphone présent plusieurs fois dans le fichier.")
                    if email in emails_vus:
                        raise CommandError(f"Ligne {numero_ligne} : email présent plusieurs fois dans le fichier.")
                    commercants = list(Utilisateur.objects.select_for_update().filter(telephone=telephone)[:2])
                    if len(commercants) != 1:
                        raise CommandError(f"Ligne {numero_ligne} : aucun compte unique ne correspond à ce téléphone.")
                    conflit = Utilisateur.objects.exclude(pk=commercants[0].pk).filter(email__iexact=email).exists()
                    if conflit:
                        raise CommandError(f"Ligne {numero_ligne} : cet email est déjà attribué à un autre compte.")
                    entrees.append((commercants[0], email))
                    telephones_vus.add(telephone)
                    emails_vus.add(email)
        except OSError as erreur:
            raise CommandError("Impossible de lire le fichier CSV indiqué.") from erreur

        if not entrees:
            raise CommandError("Le fichier ne contient aucune adresse à importer.")
        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"Vérification réussie : {len(entrees)} compte(s) prêt(s) à être mis à jour."))
            return

        for commercant, email in entrees:
            commercant.email = email
            commercant.save(update_fields=["email"])
            # Les anciennes traces Axes sont renommées pour rester supprimables avec le compte.
            from axes.models import AccessAttempt, AccessFailureLog, AccessLog

            for modele in (AccessAttempt, AccessFailureLog, AccessLog):
                modele.objects.filter(username=commercant.telephone).update(username=email)
        self.stdout.write(self.style.SUCCESS(f"Emails importés pour {len(entrees)} compte(s)."))
