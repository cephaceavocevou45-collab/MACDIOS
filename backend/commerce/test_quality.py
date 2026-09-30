"""Tests ciblés pour les outils de documentation et de démonstration."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from unittest.mock import patch

from commerce.models import Client, Commercant, Dette, Paiement, Plan, Produit, Vente


class QualiteProjetTests(TestCase):
    def test_schema_openapi_documente_les_routes_principales(self):
        reponse = self.client.get("/api/schema/?format=json")
        self.assertEqual(reponse.status_code, 200)
        schema = reponse.json()
        self.assertIn("/api/ventes/", schema["paths"])
        self.assertNotIn("/api/abonnement/payer/", schema["paths"])
        self.assertNotIn("/api/abonnement/webhook/", schema["paths"])
        self.assertIn("/api/produits/", schema["paths"])

    def test_interfaces_swagger_et_redoc_sont_servies(self):
        swagger = self.client.get("/api/docs/")
        redoc = self.client.get("/api/redoc/")
        self.assertEqual(swagger.status_code, 200)
        self.assertEqual(redoc.status_code, 200)

    def test_seed_demo_est_rejouable_sans_dupliquer_les_donnees(self):
        sortie = StringIO()
        with patch("commerce.management.commands.seed_demo.getpass", side_effect=["MotDePasseSecurise123!", "MotDePasseSecurise123!"]):
            call_command("seed_demo", stdout=sortie)
        call_command("seed_demo", stdout=StringIO())
        commercant = Commercant.objects.get(email="demo@nobi.example")
        self.assertEqual(Produit.objects.filter(commercant=commercant).count(), 3)
        self.assertEqual(Client.objects.filter(commercant=commercant).count(), 2)
        self.assertEqual(Vente.objects.filter(commercant=commercant).count(), 1)
        self.assertEqual(Dette.objects.filter(commercant=commercant).count(), 1)
        self.assertEqual(Paiement.objects.filter(commercant=commercant).count(), 1)
        self.assertTrue(Plan.objects.filter(nom="Essai gratuit").exists())
        self.assertIn("Données de démonstration prêtes", sortie.getvalue())
