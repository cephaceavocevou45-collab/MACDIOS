"""Régressions pour les nouveaux flux téléphone, mot de passe et dettes."""

from datetime import datetime, timedelta
from html import unescape
from io import BytesIO
import re
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from django.contrib.auth import get_user_model
from commerce.branding import NOM_APPLICATION
from django.core.cache import cache
from django.utils import timezone
from pypdf import PdfReader
from rest_framework.test import APIClient
from django.test import TestCase, override_settings
from rest_framework import status

from .models import Abonnement, Client, Dette, JournalAudit, Paiement, Plan

Commercant = get_user_model()


@override_settings(DEBUG=True, EMAIL_SIMULATION=True)
class NouvellesFonctionnalitesTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = Commercant.objects.create_user(
            email="etoile@example.test",
            telephone="+22961020304", nom_boutique="Boutique Étoile", password="AncienMotDePasse123!",
        )
        self.plan = Plan.objects.get(nom="Essai gratuit")
        maintenant = timezone.now()
        Abonnement.objects.create(
            commercant=self.user, plan=self.plan, statut=Abonnement.Statut.ESSAI,
            date_debut=maintenant, date_fin=maintenant + timedelta(days=14),
        )
        self.client_api = APIClient()
        self.client_api.force_authenticate(self.user)

    @override_settings(REST_FRAMEWORK={"DEFAULT_THROTTLE_RATES": {"inscription": "20/hour"}})
    def test_telephone_inscription_refuse_formats_invalides_et_normalise_le_benin(self):
        formats_invalides = (
            "+2290102", "+2296102030", "+229610203040", "22961020304", "+229 61020304", "+229abcdefgh",
        )
        for index, telephone in enumerate(formats_invalides):
            with self.subTest(telephone=telephone):
                reponse = APIClient().post("/api/auth/inscription/", {
                    "telephone": telephone, "nom_boutique": "Test téléphone",
                    "mot_de_passe": "MotDePasse123!", "confirmation_mot_de_passe": "MotDePasse123!", "accepte_conditions": True,
                }, format="json")
                self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("numéro", str(reponse.data).lower())
        telephone_valide = "+2290161020305"
        acceptee = APIClient().post("/api/auth/inscription/", {
            "telephone": telephone_valide, "nom_boutique": "Boutique valide",
            "mot_de_passe": "MotDePasse123!", "confirmation_mot_de_passe": "MotDePasse123!", "accepte_conditions": True,
        }, format="json")
        self.assertEqual(acceptee.status_code, status.HTTP_201_CREATED, acceptee.data)
        self.assertTrue(Commercant.objects.filter(telephone=telephone_valide).exists())
        telephone_etranger = APIClient().post("/api/auth/inscription/", {
            "telephone": "+12025550123", "nom_boutique": "Boutique étrangère",
            "mot_de_passe": "MotDePasse123!", "confirmation_mot_de_passe": "MotDePasse123!", "accepte_conditions": True,
        }, format="json")
        self.assertEqual(telephone_etranger.status_code, status.HTTP_201_CREATED, telephone_etranger.data)

    def demander_lien(self):
        with patch("commerce.views.envoyer_email") as envoi_email:
            reponse = APIClient().post("/api/auth/mot-de-passe/oublie/", {
                "email": self.user.email,
            }, format="json")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK, reponse.data)
        envoi_email.assert_called_once()
        self.assertEqual(envoi_email.call_args.args[0], self.user.email)
        lien = unescape(re.search(r'href="([^"]+)"', envoi_email.call_args.args[2]).group(1))
        return parse_qs(urlparse(lien).query)

    def reinitialiser(self, uid, token, nouveau="NouveauMotDePasse2026!"):
        return APIClient().post("/api/auth/mot-de-passe/reinitialiser/", {
            "uid": uid, "token": token, "nouveau_mot_de_passe": nouveau,
        }, format="json")

    def test_demande_valide_emet_un_lien_temporaire(self):
        parametres = self.demander_lien()
        self.assertTrue(parametres.get("uid"))
        self.assertTrue(parametres.get("token"))

    def test_email_inexistant_ne_revele_pas_si_le_compte_existe(self):
        with patch("commerce.views.envoyer_email") as envoi_email:
            existant = APIClient().post("/api/auth/mot-de-passe/oublie/", {
                "email": self.user.email,
            }, format="json")
            inconnu = APIClient().post("/api/auth/mot-de-passe/oublie/", {
                "email": "inconnu@example.test",
            }, format="json")
        self.assertEqual(existant.status_code, inconnu.status_code)
        self.assertEqual(existant.data, inconnu.data)
        self.assertEqual(envoi_email.call_count, 1)

    def test_inscription_exige_un_telephone_et_ne_demande_pas_email(self):
        with patch("commerce.views.envoyer_email") as envoi_email:
            response = APIClient().post("/api/auth/inscription/", {
                "telephone": "+22962030407", "nom_boutique": "Boutique sans email",
                "mot_de_passe": "MotDePasseLong2026!", "confirmation_mot_de_passe": "MotDePasseLong2026!", "accepte_conditions": True,
            }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        commercant = Commercant.objects.get(pk=response.data["id"])
        self.assertIsNone(commercant.email)
        self.assertEqual(commercant.telephone, "+2290162030407")
        envoi_email.assert_not_called()

    def test_email_invalide_est_refuse_a_l_inscription(self):
        response = APIClient().post("/api/auth/inscription/", {
            "email": "pas-une-adresse", "nom_boutique": "Test", "mot_de_passe": "MotDePasseLong2026!",
            "accepte_conditions": True,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lien_expire_apres_quinze_minutes(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        date_expiree = datetime.now() - timedelta(minutes=16)
        timestamp = default_token_generator._num_seconds(date_expiree)
        jeton_expire = default_token_generator._make_token_with_timestamp(
            self.user, timestamp, default_token_generator.secret,
        )
        reponse = self.reinitialiser(uid, jeton_expire)
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("invalide ou a expiré", str(reponse.data))

    def test_jeton_ne_peut_pas_etre_rejoue_apres_son_usage(self):
        parametres = self.demander_lien()
        uid, token = parametres["uid"][0], parametres["token"][0]
        premier = self.reinitialiser(uid, token)
        rejoue = self.reinitialiser(uid, token)
        self.assertEqual(premier.status_code, status.HTTP_200_OK, premier.data)
        self.assertEqual(rejoue.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Commercant.objects.get(pk=self.user.pk).check_password("NouveauMotDePasse2026!"))

    def test_jeton_invalide_est_refuse(self):
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        reponse = self.reinitialiser(uid, "jeton-falsifie")
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)

    def test_correction_garde_la_valeur_initiale_et_journalise_la_raison(self):
        client = Client.objects.create(commercant=self.user, nom="Awa")
        dette = Dette.objects.create(commercant=self.user, client=client, montant=5000)
        Paiement.objects.create(commercant=self.user, client=client, montant=1000)
        sans_raison = self.client_api.post(f"/api/dettes/{dette.pk}/correction/", {
            "nouveau_montant": "4500.00", "raison": "   ",
        }, format="json")
        self.assertEqual(sans_raison.status_code, 400)
        directe = self.client_api.put(f"/api/dettes/{dette.pk}/", {"montant": 4500}, format="json")
        self.assertEqual(directe.status_code, 405)
        reponse = self.client_api.post(f"/api/dettes/{dette.pk}/correction/", {
            "nouveau_montant": "4500.00", "raison": "Montant saisi en trop",
        }, format="json")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK, reponse.data)
        dette.refresh_from_db()
        self.assertEqual(str(dette.montant), "4500.00")
        historique = dette.corrections.get()
        self.assertEqual(str(historique.montant_precedent), "5000.00")
        self.assertEqual(historique.raison, "Montant saisi en trop")
        self.assertTrue(JournalAudit.objects.filter(
            commercant=self.user, objet_type="CorrectionDette", objet_id=str(historique.pk),
        ).exists())

    def test_recu_pdf_contient_les_informations_attendues(self):
        client = Client.objects.create(commercant=self.user, nom="Awa")
        dette = Dette.objects.create(commercant=self.user, client=client, montant=12500, note="Marchandises")
        Dette.objects.create(commercant=self.user, client=client, montant=2500)
        Paiement.objects.create(commercant=self.user, client=client, montant=2000)
        reponse = self.client_api.get(f"/api/dettes/{dette.pk}/recu/")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse["Content-Type"], "application/pdf")
        self.assertIn("attachment; filename=", reponse["Content-Disposition"])
        texte = " ".join(page.extract_text() or "" for page in PdfReader(BytesIO(reponse.content)).pages)
        self.assertIn("Boutique Étoile", texte)
        self.assertIn("Awa", texte)
        self.assertIn("12 500 FCFA", texte)
        self.assertIn("13 000 FCFA", texte)
        self.assertIn(timezone.localtime(dette.date).strftime("%d/%m/%Y"), texte)
        self.assertIn("12 500 FCFA", texte)
        self.assertIn(f"Document certifié {NOM_APPLICATION}", texte)
        dette.refresh_from_db()
        self.assertIsNotNone(dette.code_verification)
        self.assertIsNotNone(dette.date_generation)
        self.assertIn(str(dette.code_verification), texte)
        self.assertTrue(PdfReader(BytesIO(reponse.content)).pages[0].images)

        # Les téléchargements suivants réutilisent le même code et la même date.
        code_initial = dette.code_verification
        date_initiale = dette.date_generation
        seconde_reponse = self.client_api.get(f"/api/dettes/{dette.pk}/recu/")
        self.assertEqual(seconde_reponse.status_code, status.HTTP_200_OK)
        dette.refresh_from_db()
        self.assertEqual(dette.code_verification, code_initial)
        self.assertEqual(dette.date_generation, date_initiale)

    def test_verification_publique_retourne_uniquement_validite_et_date(self):
        client = Client.objects.create(commercant=self.user, nom="Client confidentiel")
        dette = Dette.objects.create(commercant=self.user, client=client, montant=987654)
        self.client_api.get(f"/api/dettes/{dette.pk}/recu/")
        dette.refresh_from_db()

        reponse = APIClient().get(f"/api/verifier/{dette.code_verification}/")

        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(set(reponse.data), {"valide", "date_generation"})
        self.assertTrue(reponse.data["valide"])
        self.assertEqual(reponse.data["date_generation"], dette.date_generation)
        contenu = str(reponse.data)
        self.assertNotIn("Client confidentiel", contenu)
        self.assertNotIn("987654", contenu)
        self.assertNotIn("commercant", contenu)
        self.assertNotIn("montant", contenu)

    def test_verification_publique_code_invalide(self):
        reponse = APIClient().get("/api/verifier/code-invalide/")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data, {"valide": False})

    def test_pdf_du_qr_est_prive_et_reste_accessible_a_son_proprietaire(self):
        client = Client.objects.create(commercant=self.user, nom="Awa")
        dette = Dette.objects.create(commercant=self.user, client=client, montant=12500)
        generation = self.client_api.get(f"/api/dettes/{dette.pk}/recu/")
        self.assertEqual(generation.status_code, status.HTTP_200_OK)
        dette.refresh_from_db()

        reponse_publique = APIClient().get(f"/api/verifier/{dette.code_verification}/recu/")
        self.assertEqual(reponse_publique.status_code, status.HTTP_401_UNAUTHORIZED)

        autre = Commercant.objects.create_user(
            email="autre-recu-prive@example.test", nom_boutique="Autre", password="AncienMotDePasse123!",
        )
        api_autre = APIClient()
        api_autre.force_authenticate(autre)
        self.assertEqual(
            api_autre.get(f"/api/verifier/{dette.code_verification}/recu/").status_code,
            status.HTTP_404_NOT_FOUND,
        )

        reponse = self.client_api.get(f"/api/verifier/{dette.code_verification}/recu/")

        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse["Content-Type"], "application/pdf")
        self.assertTrue(reponse["Content-Disposition"].startswith("inline;"))
        texte = " ".join(page.extract_text() or "" for page in PdfReader(BytesIO(reponse.content)).pages)
        self.assertIn("Boutique Étoile", texte)
        self.assertIn("Awa", texte)
        self.assertIn("12 500 FCFA", texte)

    def test_scan_du_code_qr_invalide_ne_delivre_aucun_pdf(self):
        reponse = self.client_api.get("/api/verifier/00000000-0000-0000-0000-000000000000/recu/")
        self.assertEqual(reponse.status_code, status.HTTP_404_NOT_FOUND)

    def test_code_d_un_recu_supprime_devient_invalide(self):
        client = Client.objects.create(commercant=self.user, nom="Awa")
        dette = Dette.objects.create(commercant=self.user, client=client, montant=1200)
        self.client_api.get(f"/api/dettes/{dette.pk}/recu/")
        dette.refresh_from_db()
        code = dette.code_verification
        dette.delete()

        reponse = APIClient().get(f"/api/verifier/{code}/")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data, {"valide": False})

    @override_settings(REST_FRAMEWORK={
        "DEFAULT_THROTTLE_RATES": {"verification_document": "1/minute"},
    })
    def test_verification_publique_est_limitee_par_adresse_ip(self):
        cache.clear()
        premier = APIClient().get("/api/verifier/premier-code/", REMOTE_ADDR="192.0.2.44")
        second = APIClient().get("/api/verifier/deuxieme-code/", REMOTE_ADDR="192.0.2.44")
        self.assertEqual(premier.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        cache.clear()

    def test_un_commercant_ne_telecharge_pas_le_recu_d_un_autre(self):
        autre = Commercant.objects.create_user(
            email="autre-dette@example.test",
            telephone="+22961020306", nom_boutique="Autre boutique", password="AncienMotDePasse123!",
        )
        client = Client.objects.create(commercant=autre, nom="Client privé")
        dette = Dette.objects.create(commercant=autre, client=client, montant=800)
        reponse = self.client_api.get(f"/api/dettes/{dette.pk}/recu/")
        self.assertEqual(reponse.status_code, status.HTTP_404_NOT_FOUND)
