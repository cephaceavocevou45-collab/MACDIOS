"""Tests de la tâche planifiée d'expiration des abonnements."""

from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from commerce.models import Abonnement, Plan


class ExpirationAbonnementsTests(TestCase):
    def test_expire_uniquement_les_abonnements_arrives_a_echeance_et_peut_etre_relancee(self):
        utilisateur = get_user_model().objects.create_user(
            email="expiration@example.test", password="MotDePasse123!", nom_boutique="Boutique Échéance",
        )
        plan = Plan.objects.get(nom="Essai gratuit")
        maintenant = timezone.now()
        expire = Abonnement.objects.create(
            commercant=utilisateur, plan=plan, statut=Abonnement.Statut.ACTIF,
            date_debut=maintenant - timedelta(days=15), date_fin=maintenant - timedelta(seconds=1),
        )
        valide = get_user_model().objects.create_user(
            email="valide@example.test", password="MotDePasse123!", nom_boutique="Boutique Valide",
        )
        encore_valide = Abonnement.objects.create(
            commercant=valide, plan=plan, statut=Abonnement.Statut.ESSAI,
            date_debut=maintenant, date_fin=maintenant + timedelta(days=2),
        )

        premiere_sortie = StringIO()
        call_command("expirer_abonnements", stdout=premiere_sortie)
        expire.refresh_from_db()
        encore_valide.refresh_from_db()
        self.assertEqual(expire.statut, Abonnement.Statut.EXPIRE)
        self.assertEqual(encore_valide.statut, Abonnement.Statut.ESSAI)
        self.assertIn("Abonnements expirés : 1", premiere_sortie.getvalue())

        seconde_sortie = StringIO()
        call_command("expirer_abonnements", stdout=seconde_sortie)
        self.assertIn("Abonnements expirés : 0", seconde_sortie.getvalue())
