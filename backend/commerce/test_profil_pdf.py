"""Vérifie les PDF avec logo, avec repli et en cas d'indisponibilité Cloudinary."""

from decimal import Decimal
from io import BytesIO
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from pypdf import PdfReader
from PIL import Image

from .services.profil_image import _telecharger_logo, logo_profil_pour_pdf
from .services.recu_pdf import construire_recu_certifie
from .services.export_pdf import construire_export_pdf

Commercant = get_user_model()


def logo_png():
    tampon = BytesIO()
    Image.new("RGB", (64, 64), "#0c765c").save(tampon, format="PNG")
    return tampon.getvalue()


def nombre_images(pdf):
    lecteur = PdfReader(BytesIO(pdf))
    ressources = lecteur.pages[0]["/Resources"].get_object()
    objets = ressources.get("/XObject", {}).get_object()
    return sum(1 for objet in objets.values() if objet.get_object().get("/Subtype") == "/Image")


class ProfilPDFTests(TestCase):
    def setUp(self):
        self.utilisateur = Commercant.objects.create_user(
            email="pdf-profil@example.test", password="MotDePasseLong2026!",
            nom_boutique="Boutique PDF", telephone="+22961020304",
            adresse="Rue du Marché", ville="Cotonou",
        )
        _telecharger_logo.cache_clear()

    def construire_recu(self, logo=None):
        return construire_recu_certifie(
            titre="Reçu de test", sous_titre="Document justificatif.",
            lignes=[("Commerçant", self.utilisateur.nom_boutique)],
            montant_principal=Decimal("2500"), code="verification-test",
            url_qr="https://nobi.test/verifier/verification-test",
            date_generation="16/11/2026", logo_proprietaire=logo,
            initiales_proprietaire="BP",
        )

    def test_recu_pdf_avec_logo_et_sans_logo(self):
        avec_logo = self.construire_recu(logo_png())
        sans_logo = self.construire_recu()
        self.assertTrue(avec_logo.startswith(b"%PDF"))
        self.assertTrue(sans_logo.startswith(b"%PDF"))
        # Le wordmark MACDIOS et le QR restent présents, plus le logo boutique si fourni.
        self.assertEqual(nombre_images(sans_logo), 2)
        self.assertEqual(nombre_images(avec_logo), 3)

    @patch("commerce.services.profil_image.cloudinary.utils.private_download_url", return_value="https://cloudinary.test/signe")
    @patch("commerce.services.profil_image.requests.get")
    def test_logo_cloudinary_est_mis_en_cache(self, telecharger, generer_lien):
        self.utilisateur.logo_profil.name = "profils/logo-prive.png"
        telecharger.return_value = Mock()
        telecharger.return_value.iter_content.return_value = [logo_png()]
        contenu = logo_profil_pour_pdf(self.utilisateur)
        self.assertEqual(contenu, logo_png())
        self.assertEqual(logo_profil_pour_pdf(self.utilisateur), logo_png())
        self.assertEqual(telecharger.call_count, 1)
        self.assertEqual(telecharger.call_args.kwargs["timeout"], (0.5, 1.5))
        self.assertGreater(generer_lien.call_args.kwargs["expires_at"], 0)

    @patch("commerce.services.profil_image.cloudinary.utils.private_download_url", return_value="https://cloudinary.test/signe")
    @patch("commerce.services.profil_image.requests.get", side_effect=TimeoutError("Cloudinary indisponible"))
    def test_panne_cloudinary_ne_bloque_pas_la_generation_pdf(self, telecharger, generer_lien):
        self.utilisateur.logo_profil.name = "profils/logo-inaccessible.png"
        _telecharger_logo.cache_clear()
        logo = logo_profil_pour_pdf(self.utilisateur)
        pdf = self.construire_recu(logo)
        self.assertIsNone(logo)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(nombre_images(pdf), 2)

    @patch("commerce.services.export_pdf.logo_profil_pour_pdf", return_value=None)
    def test_export_pdf_inclut_les_champs_du_profil(self, sans_logo):
        contenu = construire_export_pdf(self.utilisateur)
        texte = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(contenu)).pages)
        self.assertIn("Rue du Marché", texte)
        self.assertIn("Cotonou", texte)
        self.assertTrue(contenu.startswith(b"%PDF"))
