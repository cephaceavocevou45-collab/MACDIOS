"""Crée un jeu de données réutilisable pour une démonstration locale."""

from datetime import timedelta
from decimal import Decimal
from getpass import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from commerce.models import Abonnement, Client, Dette, Paiement, Plan, Produit, Vente


class Command(BaseCommand):
    help = "Crée ou remet à jour le commerçant et les données de démonstration."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="demo@nobi.example", help="Email réservé au compte de démonstration.")
        parser.add_argument("--telephone", default="+22900000000", help="Téléphone réservé au compte de démonstration.")

    @transaction.atomic
    def handle(self, *args, **options):
        Utilisateur = get_user_model()
        email = options["email"].strip().lower()
        telephone = options["telephone"]
        commercant, cree = Utilisateur.objects.get_or_create(
            email=email,
            defaults={"telephone": telephone, "nom_boutique": "Boutique Démo"},
        )
        if cree:
            mot_de_passe = getpass("Mot de passe du compte de démonstration (saisie masquée) : ")
            confirmation = getpass("Confirmer le mot de passe : ")
            if not mot_de_passe or mot_de_passe != confirmation:
                raise ValueError("Les mots de passe sont vides ou ne correspondent pas.")
            commercant.set_password(mot_de_passe)
            commercant.save(update_fields=["password"])
        elif commercant.nom_boutique != "Boutique Démo":
            raise ValueError("Cet email appartient déjà à une autre boutique ; utilisez --email.")
        # Une exécution ultérieure met à jour les données, sans réinitialiser le mot de passe.

        plan, _ = Plan.objects.get_or_create(
            nom="Essai gratuit",
            defaults={"prix": Decimal("0"), "duree_jours": 14, "actif": True},
        )
        debut = timezone.now()
        Abonnement.objects.get_or_create(
            commercant=commercant,
            defaults={"plan": plan, "statut": Abonnement.Statut.ESSAI, "date_debut": debut, "date_fin": debut + timedelta(days=14)},
        )

        produits = {}
        for nom, prix, stock in (("Riz", "1000.00", 40), ("Huile", "1500.00", 25), ("Savon", "500.00", 30)):
            produit, _ = Produit.objects.get_or_create(
                commercant=commercant, nom=nom,
                defaults={"prix": Decimal(prix), "quantite_stock": stock},
            )
            produits[nom] = produit

        clients = {}
        for nom, telephone_client in (("Awa Demo", "22900000001"), ("Koffi Demo", "22900000002")):
            client, _ = Client.objects.get_or_create(
                commercant=commercant, nom=nom,
                defaults={"telephone": telephone_client},
            )
            clients[nom] = client

        aujourd_hui = timezone.localdate()
        if not Vente.objects.filter(commercant=commercant, produit=produits["Riz"], client=clients["Awa Demo"], date__date=aujourd_hui).exists():
            quantite = 2
            produit = Produit.objects.select_for_update().get(pk=produits["Riz"].pk)
            if produit.quantite_stock >= quantite:
                produit.quantite_stock -= quantite
                produit.save(update_fields=["quantite_stock"])
                Vente.objects.create(
                    commercant=commercant, produit=produit, client=clients["Awa Demo"],
                    quantite=quantite, prix_unitaire=produit.prix, total=produit.prix * quantite,
                )

        if not Dette.objects.filter(commercant=commercant, client=clients["Awa Demo"], note="Exemple de dette", date__date=aujourd_hui).exists():
            Dette.objects.create(commercant=commercant, client=clients["Awa Demo"], montant=Decimal("5000.00"), note="Exemple de dette")
        if not Paiement.objects.filter(commercant=commercant, client=clients["Awa Demo"], montant=Decimal("1000.00"), date__date=aujourd_hui).exists():
            Paiement.objects.create(commercant=commercant, client=clients["Awa Demo"], montant=Decimal("1000.00"))

        self.stdout.write(self.style.SUCCESS("Données de démonstration prêtes."))
        self.stdout.write(f"Compte de démonstration : {email}. Le mot de passe est celui saisi lors de la première exécution.")
