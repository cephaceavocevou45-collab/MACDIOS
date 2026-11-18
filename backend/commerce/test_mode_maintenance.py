"""Tests du mode maintenance global et de ses garde-fous d'administration."""

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Commercant, JournalAudit, ModeMaintenance
from .maintenance import reinitialiser_cache_local_maintenance


class ModeMaintenanceTests(TestCase):
    def setUp(self):
        cache.delete("commerce.mode_maintenance.v1")
        reinitialiser_cache_local_maintenance()
        self.client = APIClient()
        self.super_admin = Commercant.objects.create_superuser(
            email="super-maintenance@example.test",
            password="MotDePasseSecurise123!",
            nom_boutique="Administration",
        )
        self.commercant = Commercant.objects.create_user(
            email="boutique-maintenance@example.test",
            password="MotDePasseSecurise123!",
            nom_boutique="Boutique test",
        )

    def tearDown(self):
        cache.delete("commerce.mode_maintenance.v1")
        reinitialiser_cache_local_maintenance()

    def test_statut_public_ne_revele_que_le_message_et_l_etat(self):
        reponse = self.client.get("/api/maintenance/")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(set(reponse.data), {"actif", "message"})
        self.assertFalse(reponse.data["actif"])

    def test_super_admin_active_et_desactive_le_mode_et_est_audite(self):
        self.client.force_authenticate(self.super_admin)
        activation = self.client.patch("/api/admin/maintenance/", {
            "actif": True,
            "message": "Maintenance programmée.",
        }, format="json")
        self.assertEqual(activation.status_code, 200)
        self.assertTrue(activation.data["actif"])
        self.assertEqual(activation.data["message"], "Maintenance programmée.")
        self.assertTrue(JournalAudit.objects.filter(
            utilisateur=self.super_admin, objet_type="ModeMaintenance",
            nouvelles_valeurs__actif=True,
        ).exists())

        desactivation = self.client.patch("/api/admin/maintenance/", {"actif": False}, format="json")
        self.assertEqual(desactivation.status_code, 200)
        self.assertFalse(desactivation.data["actif"])

    def test_maintenance_bloque_les_apis_commercant_et_preserve_le_back_office(self):
        ModeMaintenance.objects.update_or_create(
            pk=1,
            defaults={"actif": True, "message": "Maintenance en cours."},
        )
        cache.delete("commerce.mode_maintenance.v1")
        reinitialiser_cache_local_maintenance()

        self.client.force_authenticate(self.commercant)
        bloque = self.client.get("/api/produits/")
        self.assertEqual(bloque.status_code, 503)
        self.assertEqual(bloque.json()["code"], "maintenance_active")

        self.client.force_authenticate(self.super_admin)
        acces_admin = self.client.get("/api/admin/statistiques/")
        self.assertNotEqual(acces_admin.status_code, 503)

    def test_commercant_ne_peut_pas_activer_la_maintenance(self):
        self.client.force_authenticate(self.commercant)
        reponse = self.client.patch("/api/admin/maintenance/", {"actif": True}, format="json")
        self.assertEqual(reponse.status_code, 403)

    def test_message_personnalise_est_obligatoire_et_limite(self):
        self.client.force_authenticate(self.super_admin)
        vide = self.client.patch("/api/admin/maintenance/", {"actif": True, "message": "  "}, format="json")
        trop_long = self.client.patch("/api/admin/maintenance/", {"actif": True, "message": "x" * 301}, format="json")
        self.assertEqual(vide.status_code, 400)
        self.assertEqual(trop_long.status_code, 400)
