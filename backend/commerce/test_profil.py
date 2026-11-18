"""Tests du profil partagé par les commerçants et les comptes du back-office."""

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from .models import JournalAudit, ProfilSousAdmin
from .services.profil_image import nettoyer_image_profil

Commercant = get_user_model()


def creer_png(nom="logo.png"):
    tampon = BytesIO()
    Image.new("RGB", (900, 600), "#0c765c").save(tampon, format="PNG")
    return SimpleUploadedFile(nom, tampon.getvalue(), content_type="image/png")


class ProfilUtilisateurTests(TestCase):
    def setUp(self):
        self.proprietaire = Commercant.objects.create_user(
            email="profil@example.test", password="MotDePasseLong2026!",
            nom_boutique="Boutique Profil",
        )
        self.autre = Commercant.objects.create_user(
            email="autre-profil@example.test", password="MotDePasseLong2026!",
            nom_boutique="Autre boutique",
        )
        self.api = APIClient()
        self.api.force_authenticate(self.proprietaire)

    def test_profil_est_limite_a_l_utilisateur_connecte(self):
        lecture = self.api.get("/api/profil/")
        self.assertEqual(lecture.status_code, 200)
        self.assertEqual(lecture.data["nom_affiche"], "Boutique Profil")
        modification = self.api.patch("/api/profil/", {
            "nom_affiche": "Boutique Modifiée",
            "adresse": "Rue du Marché",
            "ville": "Cotonou",
            "id": str(self.autre.pk),
            "commercant": str(self.autre.pk),
        }, format="json")
        self.assertEqual(modification.status_code, 200, modification.data)
        self.proprietaire.refresh_from_db()
        self.autre.refresh_from_db()
        self.assertEqual(self.proprietaire.nom_boutique, "Boutique Modifiée")
        self.assertEqual(self.proprietaire.adresse, "Rue du Marché")
        self.assertEqual(self.proprietaire.ville, "Cotonou")
        self.assertEqual(self.autre.nom_boutique, "Autre boutique")
        evenement = JournalAudit.objects.get(objet_type="ProfilUtilisateur")
        self.assertEqual(evenement.utilisateur_id, self.proprietaire.pk)
        self.assertEqual(evenement.nouvelles_valeurs["adresse"], "Rue du Marché")

    def test_sous_admin_peut_lire_et_modifier_son_profil(self):
        sous_admin = Commercant.objects.create_user(
            email="agent@example.test", password="MotDePasseLong2026!",
            nom_boutique="Compte agent", is_staff=True,
        )
        ProfilSousAdmin.objects.create(
            utilisateur=sous_admin, nom="Agent Initial", permissions=["voir_statistiques"],
        )
        self.api.force_authenticate(sous_admin)
        self.assertEqual(self.api.get("/api/profil/").data["nom_affiche"], "Agent Initial")
        reponse = self.api.patch("/api/profil/", {"nom_affiche": "Agent Mis à jour"}, format="json")
        self.assertEqual(reponse.status_code, 200, reponse.data)
        sous_admin.profil_sous_admin.refresh_from_db()
        self.assertEqual(sous_admin.profil_sous_admin.nom, "Agent Mis à jour")

    def test_super_admin_peut_modifier_son_profil(self):
        super_admin = Commercant.objects.create_superuser(
            email="super-admin-profil@example.test", password="MotDePasseLong2026!",
            nom_boutique="Administration",
        )
        self.api.force_authenticate(super_admin)
        reponse = self.api.patch("/api/profil/", {"nom_affiche": "Nobi Administration"}, format="json")
        self.assertEqual(reponse.status_code, 200, reponse.data)
        super_admin.refresh_from_db()
        self.assertEqual(super_admin.nom_boutique, "Nobi Administration")

    def test_telephone_de_contact_accepte_les_pays_et_normalise_l_ancien_format_beninois(self):
        invalide = self.api.patch("/api/profil/", {"telephone": "+2290102"}, format="json")
        self.assertEqual(invalide.status_code, 400)
        valide = self.api.patch("/api/profil/", {"telephone": "+12025550123"}, format="json")
        self.assertEqual(valide.status_code, 200, valide.data)
        self.assertEqual(valide.data["telephone"], "+12025550123")
        benin_historique = self.api.patch("/api/profil/", {"telephone": "+22961020304"}, format="json")
        self.assertEqual(benin_historique.status_code, 200, benin_historique.data)
        self.assertEqual(benin_historique.data["telephone"], "+2290161020304")

    @override_settings(
        CLOUDINARY_STORAGE={"CLOUD_NAME": "test", "API_KEY": "test", "API_SECRET": "test"},
        CLOUDINARY_CONFIGURE=True,
    )
    @patch("commerce.storage.PreuveCloudinaryStorage._save", side_effect=OSError("Cloudinary indisponible"))
    def test_echec_cloudinary_affiche_une_erreur_service_claire_sans_500(self, sauvegarder):
        reponse = self.api.patch("/api/profil/", {"logo": creer_png()}, format="multipart")
        self.assertEqual(reponse.status_code, 503, reponse.data)
        self.assertIn("photo", reponse.data["detail"].lower())

    def test_logo_utilise_un_stockage_local_explicite_en_developpement(self):
        with TemporaryDirectory() as dossier:
            champ_logo = Commercant._meta.get_field("logo_profil")
            ancien_stockage = champ_logo.storage
            champ_logo.storage = FileSystemStorage(location=dossier, base_url="/media/")
            stockage = {
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
            }
            try:
                with override_settings(
                    LOGO_LOCAL_DEVELOPPEMENT=True,
                    CLOUDINARY_CONFIGURE=False,
                    MEDIA_ROOT=dossier,
                    STORAGES=stockage,
                ):
                    reponse = self.api.patch("/api/profil/", {"logo": creer_png()}, format="multipart")
                    self.assertEqual(reponse.status_code, 200, reponse.data)
                    self.proprietaire.refresh_from_db()
                    self.assertTrue(Path(dossier, self.proprietaire.logo_profil.name).is_file())
                    self.assertTrue(reponse.data["logo_url"].startswith("http://testserver/media/"))
            finally:
                champ_logo.storage = ancien_stockage

    def test_image_trop_lourde_et_svg_sont_refuses(self):
        lourde = SimpleUploadedFile("logo.png", b"x" * (2 * 1024 * 1024 + 1), content_type="image/png")
        reponse_lourde = self.api.patch("/api/profil/", {"logo": lourde}, format="multipart")
        self.assertEqual(reponse_lourde.status_code, 400)
        svg = SimpleUploadedFile("logo.svg", b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", content_type="image/svg+xml")
        reponse_svg = self.api.patch("/api/profil/", {"logo": svg}, format="multipart")
        self.assertEqual(reponse_svg.status_code, 400)

    def test_image_est_redimensionnee_et_ses_metadonnees_exif_supprimees(self):
        tampon = BytesIO()
        image = Image.new("RGB", (1200, 800), "#123456")
        exif = image.getexif()
        exif[315] = "Information privée"
        image.save(tampon, format="JPEG", exif=exif)
        nettoyee = nettoyer_image_profil(SimpleUploadedFile(
            "photo.jpg", tampon.getvalue(), content_type="image/jpeg",
        ))
        with Image.open(nettoyee) as image_nettoyee:
            self.assertLessEqual(max(image_nettoyee.size), 512)
            self.assertEqual(len(image_nettoyee.getexif()), 0)

    @override_settings(
        CLOUDINARY_STORAGE={"CLOUD_NAME": "test", "API_KEY": "test", "API_SECRET": "test"},
        CLOUDINARY_CONFIGURE=True,
    )
    @patch("commerce.storage.PreuveCloudinaryStorage.delete", return_value=True)
    @patch("commerce.storage.PreuveCloudinaryStorage._save", return_value="profils/logo-nettoye.png")
    def test_image_est_reencodee_et_remplacement_supprime_l_ancienne(self, sauver_cloudinary, supprimer_cloudinary):
        self.proprietaire.logo_profil.name = "profils/logo-ancien.png"
        self.proprietaire.save(update_fields=["logo_profil"])
        reponse = self.api.patch("/api/profil/", {"logo": creer_png()}, format="multipart")
        self.assertEqual(reponse.status_code, 200, reponse.data)
        self.proprietaire.refresh_from_db()
        self.assertEqual(self.proprietaire.logo_profil.name, "profils/logo-nettoye.png")
        sauver_cloudinary.assert_called_once()
        supprimer_cloudinary.assert_called_once_with("profils/logo-ancien.png")
        evenement = JournalAudit.objects.filter(objet_type="ProfilUtilisateur").latest("date")
        self.assertEqual(evenement.nouvelles_valeurs["logo"], "remplacé")
        self.assertNotIn("profils/", str(evenement.nouvelles_valeurs))

    @patch("commerce.storage.PreuveCloudinaryStorage.delete", return_value=True)
    def test_suppression_du_logo_efface_le_fichier_et_trace_sans_chemin(self, supprimer_cloudinary):
        self.proprietaire.logo_profil.name = "profils/logo-prive.png"
        self.proprietaire.save(update_fields=["logo_profil"])
        reponse = self.api.delete("/api/profil/photo/")
        self.assertEqual(reponse.status_code, 200, reponse.data)
        self.proprietaire.refresh_from_db()
        self.assertFalse(self.proprietaire.logo_profil)
        supprimer_cloudinary.assert_called_once_with("profils/logo-prive.png")
        evenement = JournalAudit.objects.filter(objet_type="ProfilUtilisateur").latest("date")
        self.assertEqual(evenement.nouvelles_valeurs, {"logo": "absent"})
        self.assertNotIn("logo-prive", str(evenement.nouvelles_valeurs))

    @patch("commerce.storage.PreuveCloudinaryStorage.delete", return_value=True)
    def test_suppression_du_compte_supprime_aussi_le_logo(self, supprimer_cloudinary):
        self.proprietaire.logo_profil.name = "profils/compte-a-supprimer.png"
        self.proprietaire.save(update_fields=["logo_profil"])
        identifiant = self.proprietaire.pk
        reponse = self.api.delete("/api/compte/", {"mot_de_passe": "MotDePasseLong2026!"}, format="json")
        self.assertEqual(reponse.status_code, 204, reponse.data)
        self.assertFalse(Commercant.objects.filter(pk=identifiant).exists())
        supprimer_cloudinary.assert_called_once_with("profils/compte-a-supprimer.png")
