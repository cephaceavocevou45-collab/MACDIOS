"""Tests de non-régression des achats et de leurs effets sur le stock."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Abonnement, Approvisionnement, Fournisseur, MouvementStock, Plan, Produit, Vente


Commercant = get_user_model()


class ApprovisionnementsAPITests(TestCase):
    def setUp(self):
        self.commercant = Commercant.objects.create_user(
            email="approvisionnement@example.test",
            telephone="+22961020304",
            nom_boutique="Boutique test",
            password="MotDePasseTest123!",
        )
        plan = Plan.objects.get(nom="Essai gratuit")
        maintenant = timezone.now()
        Abonnement.objects.create(
            commercant=self.commercant,
            plan=plan,
            statut=Abonnement.Statut.ESSAI,
            date_debut=maintenant,
            date_fin=maintenant + timedelta(days=14),
        )
        self.fournisseur = Fournisseur.objects.create(
            commercant=self.commercant,
            nom="Grossiste test",
        )
        self.produit = Produit.objects.create(
            commercant=self.commercant,
            nom="Riz",
            prix="1500.00",
            prix_achat="900.00",
            quantite_stock=4,
        )
        self.api = APIClient()
        self.api.force_authenticate(self.commercant)

    def test_reception_ajoute_stock_cout_et_mouvement(self):
        self.assertTrue(Produit.objects.filter(pk=self.produit.pk, commercant=self.commercant, actif=True).exists())
        reponse = self.api.post("/api/approvisionnements/", {
            "fournisseur": self.fournisseur.pk,
            "reference": "FACT-001",
            "lignes": [{
                "produit": self.produit.pk,
                "quantite": 6,
                "prix_achat_unitaire": "1000.00",
            }],
        }, format="json")

        self.assertEqual(reponse.status_code, 201, reponse.data)
        self.produit.refresh_from_db()
        self.assertEqual(self.produit.quantite_stock, 10)
        self.assertEqual(str(self.produit.prix_achat), "1000.00")
        self.assertEqual(Approvisionnement.objects.filter(commercant=self.commercant).count(), 1)
        mouvement = MouvementStock.objects.get(commercant=self.commercant)
        self.assertEqual(mouvement.quantite_avant, 4)
        self.assertEqual(mouvement.quantite_apres, 10)
        self.assertEqual(mouvement.variation, 6)

    def test_liste_receptions_est_accessible_et_limitee_au_commercant(self):
        creation = self.api.post("/api/approvisionnements/", {
            "fournisseur": self.fournisseur.pk,
            "lignes": [{
                "produit": self.produit.pk,
                "quantite": 2,
                "prix_achat_unitaire": "950.00",
            }],
        }, format="json")
        self.assertEqual(creation.status_code, 201, creation.data)

        liste = self.api.get("/api/approvisionnements/")

        self.assertEqual(liste.status_code, 200, liste.data)
        self.assertEqual(liste.data["count"], 1)
        self.assertEqual(liste.data["results"][0]["reference"], "")
        self.assertEqual(liste.data["results"][0]["details"][0]["produit_nom"], "Riz")

        autre = Commercant.objects.create_user(
            email="autre-approvisionnement@example.test",
            telephone="+22961020305",
            nom_boutique="Autre boutique",
            password="MotDePasseTest123!",
        )
        self.api.force_authenticate(autre)
        liste_autre = self.api.get("/api/approvisionnements/")
        self.assertEqual(liste_autre.status_code, 200, liste_autre.data)
        self.assertEqual(liste_autre.data["count"], 0)

    def test_dashboard_ne_present_pas_un_benefice_partiel_si_un_cout_manque(self):
        Vente.objects.create(
            commercant=self.commercant,
            produit=self.produit,
            quantite=1,
            prix_unitaire="1500.00",
            prix_achat_unitaire="900.00",
            total="1500.00",
        )
        Vente.objects.create(
            commercant=self.commercant,
            produit=self.produit,
            quantite=1,
            prix_unitaire="1500.00",
            prix_achat_unitaire=None,
            total="1500.00",
        )

        reponse = self.api.get("/api/dashboard/")

        self.assertEqual(reponse.status_code, 200, reponse.data)
        self.assertIsNone(reponse.data["benefice_brut_jour"])
        self.assertEqual(reponse.data["ventes_sans_cout_jour"], 1)
