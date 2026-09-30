"""Tests sans réseau du service Brevo et de l'import des anciens comptes."""

import json
from io import StringIO
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings

from notifications.email import ErreurEnvoiEmail, envoyer_email

Commercant = get_user_model()


class ServiceEmailTests(TestCase):
    def setUp(self):
        self.destinataire = "commercant@example.test"
        self.sujet = "Réinitialiser le mot de passe"
        self.contenu = '<html><body><a href="https://app.example.test/reset?token=secret">Continuer</a></body></html>'

    @override_settings(
        EMAIL_SIMULATION=False,
        BREVO_API_KEY="cle-test-brevo",
        BREVO_SENDER_EMAIL="noreply@example.test",
        BREVO_SENDER_NAME="Nobi test",
    )
    @patch("notifications.email.urlopen")
    def test_envoi_reussi_utilise_l_api_transactionnelle_brevo(self, ouvrir):
        reponse = MagicMock()
        reponse.__enter__.return_value.status = 201
        reponse.__enter__.return_value.read.return_value = json.dumps({"messageId": "message-test"}).encode()
        ouvrir.return_value = reponse

        self.assertTrue(envoyer_email(self.destinataire, self.sujet, self.contenu))
        requete = ouvrir.call_args.args[0]
        self.assertEqual(requete.full_url, "https://api.brevo.com/v3/smtp/email")
        self.assertEqual(requete.get_header("Api-key"), "cle-test-brevo")
        corps = json.loads(requete.data)
        self.assertEqual(corps["to"][0]["email"], self.destinataire)
        self.assertIn("htmlContent", corps)
        self.assertIn("textContent", corps)
        ouvrir.assert_called_once()

    @override_settings(
        EMAIL_SIMULATION=False,
        BREVO_API_KEY="cle-test-brevo",
        BREVO_SENDER_EMAIL="noreply@example.test",
        BREVO_SENDER_NAME="Nobi test",
    )
    @patch("notifications.email.urlopen", side_effect=URLError("détail fournisseur privé"))
    def test_echec_fournisseur_est_converti_en_erreur_generique(self, ouvrir):
        with self.assertRaisesRegex(ErreurEnvoiEmail, "n'a pas accepté") as erreur:
            envoyer_email(self.destinataire, self.sujet, self.contenu)
        self.assertNotIn("privé", str(erreur.exception))
        ouvrir.assert_called_once()

    @override_settings(EMAIL_SIMULATION=False)
    @patch("notifications.email.urlopen")
    def test_email_invalide_est_refuse_avant_appel_brevo(self, ouvrir):
        with self.assertRaisesRegex(ValueError, "adresse email.*invalide"):
            envoyer_email("adresse-invalide", self.sujet, self.contenu)
        ouvrir.assert_not_called()

    @override_settings(EMAIL_SIMULATION=True)
    def test_simulation_masque_email_et_jeton_dans_les_logs(self):
        with self.assertLogs("notifications.email", level="INFO") as journaux:
            self.assertTrue(envoyer_email(self.destinataire, self.sujet, self.contenu))
        self.assertNotIn(self.destinataire, journaux.output[0])
        self.assertNotIn("secret", journaux.output[0])
        self.assertIn("[MASQUÉ]", journaux.output[0])


class ImportEmailsCommercantsTests(TestCase):
    def setUp(self):
        self.commercant = Commercant.objects.create_user(
            email="ancien@example.test", telephone="+22962030405",
            nom_boutique="Boutique migrée", password="MotDePasseValide2026!",
        )

    def _creer_csv(self, dossier, contenu):
        chemin = Path(dossier) / "emails.csv"
        chemin.write_text(contenu, encoding="utf-8")
        return chemin

    def test_import_email_ancien_compte_et_mode_verification(self):
        with TemporaryDirectory() as dossier:
            fichier = self._creer_csv(dossier, "telephone,email\n+22962030405,nouveau@example.test\n")
            sortie = StringIO()
            call_command("importer_emails_commercants", str(fichier), dry_run=True, stdout=sortie)
            self.commercant.refresh_from_db()
            self.assertEqual(self.commercant.email, "ancien@example.test")

            call_command("importer_emails_commercants", str(fichier), stdout=StringIO())
            self.commercant.refresh_from_db()
            self.assertEqual(self.commercant.email, "nouveau@example.test")

    def test_import_refuse_les_emails_dupliques_sans_modifier_les_comptes(self):
        autre = Commercant.objects.create_user(
            email="autre@example.test", telephone="+22962030406",
            nom_boutique="Autre boutique", password="MotDePasseValide2026!",
        )
        with TemporaryDirectory() as dossier:
            fichier = self._creer_csv(
                dossier,
                "telephone,email\n+22962030405,commun@example.test\n+22962030406,commun@example.test\n",
            )
            with self.assertRaises(CommandError):
                call_command("importer_emails_commercants", str(fichier), stdout=StringIO())
        self.commercant.refresh_from_db()
        autre.refresh_from_db()
        self.assertEqual(self.commercant.email, "ancien@example.test")
        self.assertEqual(autre.email, "autre@example.test")
