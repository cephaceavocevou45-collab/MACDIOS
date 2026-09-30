"""Tests du paiement d'abonnement soumis puis traité dans l'administration."""

from datetime import timedelta
from io import BytesIO
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.signals import request_finished
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from PIL import Image
from pypdf import PdfReader

from commerce.models import Abonnement, DemandePaiementManuel, JournalAudit, Plan
from commerce.services.paiement_manuel import rejeter_demande, valider_demande


Commercant = get_user_model()


@override_settings(
    NUMERO_MTN="22961020304", NUMERO_MOOV="", NUMERO_CELTIIS="",
    EMAIL_SIMULATION=True,
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    },
)
class PaiementManuelTests(TestCase):
    def setUp(self):
        self.proprietaire = Commercant.objects.create_user(
            email="a@example.test", password="MotDePasse123!", nom_boutique="Boutique A",
        )
        self.autre = Commercant.objects.create_user(
            email="b@example.test", password="MotDePasse123!", nom_boutique="Boutique B",
        )
        self.admin = Commercant.objects.create_superuser(
            email="admin@example.test", password="MotDePasse123!", nom_boutique="Administration",
        )
        self.essai = Plan.objects.get(nom="Essai gratuit")
        maintenant = timezone.now()
        for commerçant in (self.proprietaire, self.autre):
            Abonnement.objects.create(
                commercant=commerçant, plan=self.essai, statut=Abonnement.Statut.ESSAI,
                date_debut=maintenant, date_fin=maintenant + timedelta(days=14),
            )
        self.plan = Plan.objects.create(nom="Trente jours test", prix="2500", duree_jours=30)
        self.api = APIClient()
        self.api.force_authenticate(self.proprietaire)

    def creer_demande(self, api=None, owner=None):
        api = api or self.api
        owner = owner or self.proprietaire
        api.force_authenticate(owner)
        return api.post("/api/abonnement/demandes/", {
            "plan": self.plan.pk,
            "operateur": "mtn",
            "reference_transaction": "TX-MOMO-20304",
        }, format="multipart")

    def test_creation_demande_et_doublon_en_attente_refuse(self):
        reponse = self.creer_demande()
        self.assertEqual(reponse.status_code, 201, reponse.data)
        self.assertEqual(reponse.data["montant"], "2500.00")
        self.assertEqual(reponse.data["statut"], "en_attente")
        doublon = self.creer_demande()
        self.assertEqual(doublon.status_code, 409)
        self.assertEqual(DemandePaiementManuel.objects.count(), 1)

    def test_un_seul_operateur_configure_est_expose_uniquement_a_un_compte_connecte(self):
        reponse = self.api.get("/api/abonnement/")
        self.assertEqual(reponse.data["mode_paiement"], "manuel")
        self.assertEqual(reponse.data["operateurs_paiement"], [
            {"code": "mtn", "nom": "MTN", "numero": "22961020304"},
        ])
        self.api.force_authenticate(user=None)
        anonyme = self.api.get("/api/abonnement/")
        self.assertEqual(anonyme.status_code, 401)

    def test_commercant_ne_voit_que_ses_demandes_et_preuve_autre_compte_refusee(self):
        demande = self.creer_demande().data
        reponse_autre = self.creer_demande(owner=self.autre)
        self.assertEqual(reponse_autre.status_code, 201)
        self.api.force_authenticate(self.proprietaire)
        liste = self.api.get("/api/abonnement/demandes/")
        self.assertEqual([ligne["id"] for ligne in liste.data], [demande["id"]])
        self.api.force_authenticate(self.autre)
        preuve = self.api.get(f"/api/abonnement/demandes/{demande['id']}/preuve/")
        recu = self.api.get(f"/api/abonnement/demandes/{demande['id']}/recu/")
        self.assertEqual(preuve.status_code, 404)
        self.assertEqual(recu.status_code, 404)

    def test_preuve_image_est_telechargeable_par_le_proprietaire_uniquement(self):
        tampon = BytesIO()
        Image.new("RGB", (2, 2), color="green").save(tampon, format="PNG")
        with tempfile.TemporaryDirectory() as media_temporaire, override_settings(MEDIA_ROOT=media_temporaire):
            demande = DemandePaiementManuel.objects.create(
                commercant=self.proprietaire, plan=self.plan, montant=self.plan.prix,
                reference_transaction="TX-PREUVE",
                preuve=SimpleUploadedFile("capture.png", tampon.getvalue(), content_type="image/png"),
            )
            self.api.force_authenticate(self.proprietaire)
            telechargement = self.api.get(f"/api/abonnement/demandes/{demande.pk}/preuve/")
            self.assertEqual(telechargement.status_code, 200)
            contenu_preuve = b"".join(telechargement.streaming_content)
            # HttpResponse.close() émet request_finished. Django y branche
            # close_old_connections, qui ne doit pas fermer la connexion tenue
            # par la transaction englobante de TestCase dans ce test.
            request_finished.disconnect(close_old_connections)
            try:
                telechargement.close()
            finally:
                request_finished.connect(close_old_connections)
            self.assertTrue(contenu_preuve)
            self.api.force_authenticate(self.autre)
            interdit = self.api.get(f"/api/abonnement/demandes/{demande.pk}/preuve/")
            self.assertEqual(interdit.status_code, 404)

    def test_fichier_preuve_trop_volumineux_ou_non_image_refuse(self):
        fichier_trop_gros = SimpleUploadedFile(
            "capture.png", b"x" * (5 * 1024 * 1024 + 1), content_type="image/png",
        )
        trop_gros = self.api.post("/api/abonnement/demandes/", {
            "plan": self.plan.pk, "operateur": "mtn", "reference_transaction": "TX-TROP-GROS",
            "preuve": fichier_trop_gros,
        }, format="multipart")
        self.assertEqual(trop_gros.status_code, 400)
        self.assertIn("5 Mo", str(trop_gros.data))

        fichier_texte = SimpleUploadedFile(
            "capture.png", b"ceci n'est pas une image", content_type="image/png",
        )
        mauvais_type = self.api.post("/api/abonnement/demandes/", {
            "plan": self.plan.pk, "operateur": "mtn", "reference_transaction": "TX-MAUVAIS-TYPE",
            "preuve": fichier_texte,
        }, format="multipart")
        self.assertEqual(mauvais_type.status_code, 400)
        self.assertIn("image", str(mauvais_type.data).lower())

    @patch("commerce.services.paiement_manuel.envoyer_email")
    def test_validation_active_le_plan_pour_la_bonne_duree_et_genere_recu(self, envoyer):
        demande = DemandePaiementManuel.objects.create(
            commercant=self.proprietaire, plan=self.plan, montant=self.plan.prix,
            reference_transaction="TX-VALIDE",
        )
        avec_callbacks = self.captureOnCommitCallbacks(execute=True)
        with avec_callbacks:
            resultat, modifiee = valider_demande(demande.pk, self.admin)
        self.assertTrue(modifiee)
        self.assertEqual(resultat.statut, DemandePaiementManuel.Statut.VALIDEE)
        abonnement = Abonnement.objects.get(commercant=self.proprietaire)
        self.assertEqual(abonnement.plan, self.plan)
        self.assertEqual(abonnement.date_fin - abonnement.date_debut, timedelta(days=30))
        self.assertEqual(resultat.date_debut_abonnement, abonnement.date_debut)
        self.assertEqual(resultat.date_fin_abonnement, abonnement.date_fin)
        self.assertEqual(resultat.traitee_par, self.admin)
        self.assertIsNotNone(resultat.code_verification)
        self.assertTrue(JournalAudit.objects.filter(objet_type="DemandePaiementManuel", utilisateur=self.admin).exists())
        envoyer.assert_called_once()

        self.api.force_authenticate(self.proprietaire)
        pdf = self.api.get(f"/api/abonnement/demandes/{resultat.pk}/recu/")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF-"))
        validation = self.api.get(f"/api/verifier/{resultat.code_verification}/")
        self.assertEqual(validation.data["valide"], True)
        self.assertNotIn("montant", validation.data)
        self.assertNotIn("commercant", validation.data)

        document_public = APIClient().get(f"/api/verifier/{resultat.code_verification}/recu/")
        self.assertEqual(document_public.status_code, 200)
        self.assertEqual(document_public["Content-Type"], "application/pdf")
        texte = " ".join(page.extract_text() or "" for page in PdfReader(BytesIO(document_public.content)).pages)
        self.assertIn("Boutique A", texte)
        self.assertIn("Trente jours test", texte)
        self.assertIn("2 500 FCFA", texte)

    @patch("commerce.services.paiement_manuel.envoyer_email")
    def test_rejet_exige_un_motif_nactive_pas_et_notifie(self, envoyer):
        demande = DemandePaiementManuel.objects.create(
            commercant=self.proprietaire, plan=self.plan, montant=self.plan.prix,
            reference_transaction="TX-REJETE",
        )
        with self.captureOnCommitCallbacks(execute=True):
            resultat, modifiee = rejeter_demande(demande.pk, self.admin, " Référence introuvable ")
        self.assertTrue(modifiee)
        self.assertEqual(resultat.statut, DemandePaiementManuel.Statut.REJETEE)
        self.assertEqual(resultat.motif_rejet, "Référence introuvable")
        self.assertEqual(self.proprietaire.abonnement.statut, Abonnement.Statut.ESSAI)
        envoyer.assert_called_once()

    def test_client_ne_peut_pas_fabriquer_une_validation(self):
        demande = self.creer_demande().data
        reponse = self.api.patch(
            f"/api/abonnement/demandes/{demande['id']}/",
            {"statut": "validee", "traitee_par": str(self.admin.pk)}, format="json",
        )
        self.assertEqual(reponse.status_code, 404)
        self.assertEqual(DemandePaiementManuel.objects.get(pk=demande["id"]).statut, "en_attente")

    def test_action_admin_valide_et_un_non_staff_ne_peut_pas_ouvrir_admin(self):
        demande = self.creer_demande().data
        client_admin = APIClient()
        client_admin.force_login(self.proprietaire)
        acces_refuse = client_admin.get("/admin/commerce/demandepaiementmanuel/")
        self.assertEqual(acces_refuse.status_code, 302)

        client_admin.force_login(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            reponse = client_admin.post("/admin/commerce/demandepaiementmanuel/", {
                "action": "valider_selection", "_selected_action": [str(demande["id"])], "index": "0",
            })
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(DemandePaiementManuel.objects.get(pk=demande["id"]).statut, "validee")
