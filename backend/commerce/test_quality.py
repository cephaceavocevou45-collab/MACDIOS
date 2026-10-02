"""Tests ciblés pour les outils de documentation et de démonstration."""

from io import StringIO
import os
from pathlib import Path
import subprocess
import sys

from django.core.management import call_command
from django.test import TestCase
from unittest.mock import patch

from commerce.models import Client, Commercant, Dette, Paiement, Plan, Produit, Vente


class QualiteProjetTests(TestCase):
    def test_reglages_production_refusent_les_replis_dangereux(self):
        environnement_base = os.environ.copy()
        environnement_base.update({
            "ENVIRONMENT": "production",
            "RENDER": "False",
            "RAILWAY_ENVIRONMENT": "",
            "ALLOWED_HOSTS": "api.example.test",
            "CORS_ALLOWED_ORIGINS": "https://app.example.test",
            "DATABASE_URL": "sqlite:///:memory:",
            "REDIS_URL": "redis://localhost:6379/0",
            # Le garde-fou de démarrage en production vérifie aussi la destination
            # et le chiffrement des sauvegardes avant d'atteindre les scénarios testés.
            "BACKUP_ENCRYPTION_KEY": "cle-de-chiffrement-de-test-sans-valeur-reelle",
            "BACKUP_S3_BUCKET": "bucket-test-non-utilise",
            "SENTRY_DSN": "",
        })
        racine_backend = Path(__file__).resolve().parents[1]
        scenarios = (
            ({"DEBUG": "", "SECRET_KEY": "cle-test"}, "DEBUG doit être explicitement"),
            ({"DEBUG": "True", "SECRET_KEY": "cle-test"}, "DEBUG=True est interdit"),
            ({"DEBUG": "False", "SECRET_KEY": ""}, "SECRET_KEY doit être explicitement"),
            ({"DEBUG": "False", "SECRET_KEY": "cle-test-securisee-pour-le-test", "REDIS_URL": ""}, "REDIS_URL est obligatoire"),
            ({"DEBUG": "False", "SECRET_KEY": "cle-test-securisee-pour-le-test"}, None),
        )
        for valeurs, message_attendu in scenarios:
            with self.subTest(valeurs=tuple(valeurs)):
                environnement = environnement_base | valeurs
                resultat = subprocess.run(
                    [sys.executable, "-c", "import config.settings"],
                    cwd=racine_backend,
                    env=environnement,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                sortie = resultat.stdout + resultat.stderr
                if message_attendu is None:
                    self.assertEqual(resultat.returncode, 0, sortie)
                else:
                    self.assertNotEqual(resultat.returncode, 0, sortie)
                    self.assertIn(message_attendu, sortie)

    def test_schema_openapi_documente_les_routes_principales(self):
        reponse = self.client.get("/api/schema/?format=json")
        self.assertEqual(reponse.status_code, 200)
        schema = reponse.json()
        self.assertIn("/api/ventes/", schema["paths"])
        self.assertNotIn("/api/abonnement/payer/", schema["paths"])
        self.assertNotIn("/api/abonnement/webhook/", schema["paths"])
        self.assertIn("/api/produits/", schema["paths"])
        self.assertIn("CookieJWT", schema["components"]["securitySchemes"])
        self.assertIn({"CookieJWT": []}, schema["paths"]["/api/produits/"]["get"]["security"])
        self.assertIn({}, schema["paths"]["/api/sante/"]["get"]["security"])
        self.assertNotIn("requestBody", schema["paths"]["/api/auth/refresh/"]["post"])
        page_schema = schema["paths"]["/api/produits/"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        composant_page = page_schema["$ref"].rsplit("/", 1)[-1]
        champs_page = schema["components"]["schemas"][composant_page]["properties"]
        self.assertTrue({"count", "next", "previous", "results"}.issubset(champs_page))

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
