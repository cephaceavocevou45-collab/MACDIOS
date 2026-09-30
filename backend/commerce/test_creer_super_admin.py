"""Vérifie que le premier super-admin est créé sans secret prédéfini."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase


class CreationSuperAdminTests(TestCase):
    @patch("commerce.management.commands.creer_super_admin.getpass", side_effect=["Kp!82gHq4bZa#9", "Kp!82gHq4bZa#9"])
    @patch("builtins.input", side_effect=["premier-admin@example.test", "Administration Nobi"])
    def test_commande_demande_les_informations_et_cree_un_compte_superuser(self, saisie, mot_de_passe):
        call_command("creer_super_admin")
        administrateur = get_user_model().objects.get(email="premier-admin@example.test")
        self.assertTrue(administrateur.is_superuser)
        self.assertTrue(administrateur.is_staff)
        self.assertTrue(administrateur.check_password("Kp!82gHq4bZa#9"))
