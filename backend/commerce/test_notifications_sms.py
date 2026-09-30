"""Tests hors ligne du service SMS et des rappels d'abonnement."""

import json
from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from commerce.models import Abonnement, Plan
from notifications.sms import ErreurEnvoiSms, envoyer_sms

Commercant = get_user_model()


class ServiceSmsTests(TestCase):
    def setUp(self):
        self.numero = "+22961020304"
        self.message = "Votre boutique : essai terminé le 01/10/2026."

    @override_settings(SMS_SIMULATION=False, VONAGE_API_KEY="cle-test", VONAGE_API_SECRET="secret-test", VONAGE_SMS_SENDER="Nobi")
    @patch("notifications.sms.urlopen")
    def test_envoi_reussi_interprete_la_reponse_vonage(self, ouvrir):
        reponse = MagicMock()
        reponse.__enter__.return_value.read.return_value = json.dumps({
            "messages": [{"status": "0", "message-id": "id-test"}],
        }).encode()
        ouvrir.return_value = reponse

        self.assertTrue(envoyer_sms(self.numero, self.message))
        requete = ouvrir.call_args.args[0]
        self.assertEqual(requete.full_url, "https://rest.nexmo.com/sms/json")
        self.assertEqual(requete.get_header("Authorization").split()[0], "Basic")
        self.assertIn(b"to=22961020304", requete.data)
        ouvrir.assert_called_once()

    @override_settings(SMS_SIMULATION=False, VONAGE_API_KEY="cle-test", VONAGE_API_SECRET="secret-test", VONAGE_SMS_SENDER="Nobi")
    @patch("notifications.sms.urlopen")
    def test_echec_fournisseur_est_converti_en_erreur_sans_detail_sensible(self, ouvrir):
        reponse = MagicMock()
        reponse.__enter__.return_value.read.return_value = json.dumps({
            "messages": [{"status": "9", "error-text": "numéro privé"}],
        }).encode()
        ouvrir.return_value = reponse

        with self.assertRaisesRegex(ErreurEnvoiSms, "n'a pas accepté"):
            envoyer_sms(self.numero, self.message)

    @override_settings(SMS_SIMULATION=False, VONAGE_API_KEY="cle-test", VONAGE_API_SECRET="secret-test", VONAGE_SMS_SENDER="Nobi")
    @patch("notifications.sms.urlopen")
    def test_numero_invalide_est_refuse_avant_appel_fournisseur(self, ouvrir):
        with self.assertRaisesRegex(ValueError, r"\+229 suivi de 8 chiffres"):
            envoyer_sms("+2290102", self.message)
        ouvrir.assert_not_called()

    @override_settings(SMS_SIMULATION=False, VONAGE_API_KEY="", VONAGE_API_SECRET="", VONAGE_SMS_SENDER="")
    @patch("notifications.sms.urlopen")
    def test_configuration_manquante_est_refusee(self, ouvrir):
        with self.assertRaisesRegex(ErreurEnvoiSms, "configuration.*incomplète"):
            envoyer_sms(self.numero, self.message)
        ouvrir.assert_not_called()

    @override_settings(SMS_SIMULATION=False, VONAGE_API_KEY="cle-test", VONAGE_API_SECRET="secret-test", VONAGE_SMS_SENDER="Nobi")
    @patch("notifications.sms.urlopen", side_effect=URLError("détail privé du fournisseur"))
    def test_erreur_reseau_est_convertie_en_erreur_generique(self, ouvrir):
        with self.assertRaisesRegex(ErreurEnvoiSms, "n'a pas accepté") as erreur:
            envoyer_sms(self.numero, self.message)
        self.assertNotIn("détail privé", str(erreur.exception))
        ouvrir.assert_called_once()

    @override_settings(SMS_SIMULATION=True)
    def test_simulation_ne_journalise_pas_le_lien_secret_en_clair(self):
        message = "Lien?uid=abc&token=secretjeton123"
        with self.assertLogs("notifications.sms", level="INFO") as journaux:
            envoyer_sms(self.numero, message)
        self.assertIn("SMS simulé", journaux.output[0])
        self.assertNotIn("secretjeton123", journaux.output[0])
        self.assertNotIn(self.numero, journaux.output[0])


class RappelsEcheanceTests(TestCase):
    def setUp(self):
        self.commercant = Commercant.objects.create_user(
            email="sms-reminder@example.test",
            telephone="+22961020307", nom_boutique="Boutique Démo", password="MotDePasseValide2026!",
        )
        self.plan = Plan.objects.get(nom="Essai gratuit")
        debut = timezone.now()
        self.abonnement = Abonnement.objects.create(
            commercant=self.commercant, plan=self.plan, statut=Abonnement.Statut.ESSAI,
            date_debut=debut, date_fin=debut + timedelta(days=3),
        )

    @patch("commerce.management.commands.notifier_echeances_abonnement.envoyer_sms")
    def test_rappel_envoye_une_seule_fois_par_date_echeance(self, envoyer):
        call_command("notifier_echeances_abonnement", stdout=StringIO())
        call_command("notifier_echeances_abonnement", stdout=StringIO())

        envoyer.assert_called_once()
        self.abonnement.refresh_from_db()
        self.assertEqual(self.abonnement.rappel_sms_echeance_le, timezone.localtime(self.abonnement.date_fin).date())

    @patch("commerce.management.commands.notifier_echeances_abonnement.envoyer_sms", side_effect=ErreurEnvoiSms)
    def test_echec_du_rappel_permet_une_nouvelle_tentative(self, envoyer):
        call_command("notifier_echeances_abonnement", stderr=StringIO(), stdout=StringIO())
        self.abonnement.refresh_from_db()
        self.assertIsNone(self.abonnement.rappel_sms_echeance_le)

        call_command("notifier_echeances_abonnement", stderr=StringIO(), stdout=StringIO())
        self.assertEqual(envoyer.call_count, 2)

    @patch("commerce.management.commands.notifier_echeances_abonnement.envoyer_sms")
    def test_rappel_est_ignore_si_le_telephone_est_absent(self, envoyer):
        self.commercant.telephone = ""
        self.commercant.save(update_fields=["telephone"])

        sortie = StringIO()
        call_command("notifier_echeances_abonnement", stdout=sortie)

        envoyer.assert_not_called()
        self.assertIn("sans téléphone de contact", sortie.getvalue())
