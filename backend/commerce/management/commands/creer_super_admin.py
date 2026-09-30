"""Crée le premier administrateur avec des identifiants saisis de façon interactive."""

from getpass import getpass

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Crée un compte Super Admin sans identifiants ou mot de passe prédéfinis."

    def handle(self, *args, **options):
        User = get_user_model()
        email = input("Email du Super Admin : ").strip().lower()
        nom_boutique = input("Nom de l'administration : ").strip()
        if not email or not nom_boutique:
            raise CommandError("L'email et le nom de l'administration sont obligatoires.")
        if User.objects.filter(email=email).exists():
            raise CommandError("Cette adresse email est déjà utilisée.")

        mot_de_passe = getpass("Mot de passe (saisie masquée) : ")
        confirmation = getpass("Confirmer le mot de passe : ")
        if not mot_de_passe or mot_de_passe != confirmation:
            raise CommandError("Les mots de passe sont vides ou ne correspondent pas.")

        administrateur = User(email=email, nom_boutique=nom_boutique)
        try:
            password_validation.validate_password(mot_de_passe, user=administrateur)
        except ValidationError as erreur:
            raise CommandError("Mot de passe refusé : " + " ".join(erreur.messages)) from erreur

        administrateur = User.objects.create_superuser(
            email=email, password=mot_de_passe, nom_boutique=nom_boutique,
        )
        self.stdout.write(self.style.SUCCESS(f"Super Admin créé pour {administrateur.email}."))
