"""Vérifie que les preuves sont stockées et ouvertes en mode privé Cloudinary."""

from unittest.mock import Mock, patch

from django.core.files.base import ContentFile
from django.test import SimpleTestCase

from commerce.storage import PreuveCloudinaryStorage


class PreuveCloudinaryStorageTests(SimpleTestCase):
    @patch("commerce.storage.cloudinary.uploader.upload")
    def test_upload_utilise_le_type_authentifie(self, upload):
        upload.return_value = {"public_id": "preuves-abonnement/preuve-test", "format": "png"}
        stockage = PreuveCloudinaryStorage()
        nom = stockage._save("preuves-abonnement/preuve-test.png", ContentFile(b"image", name="preuve-test.png"))
        self.assertEqual(nom, "preuves-abonnement/preuve-test.png")
        self.assertEqual(upload.call_args.kwargs["type"], "authenticated")

    @patch("commerce.storage.requests.get")
    @patch("commerce.storage.cloudinary.utils.private_download_url", return_value="https://cloudinary.test/signe")
    def test_ouverture_genere_un_lien_signe_a_duree_courte(self, lien_signe, telecharger):
        telecharger.return_value = Mock(content=b"contenu preuve")
        telecharger.return_value.raise_for_status.return_value = None
        contenu = PreuveCloudinaryStorage()._open("preuves-abonnement/preuve-test.png").read()
        self.assertEqual(contenu, b"contenu preuve")
        self.assertEqual(lien_signe.call_args.args[0], "preuves-abonnement/preuve-test")
        self.assertEqual(lien_signe.call_args.kwargs["type"], "authenticated")
        self.assertEqual(telecharger.call_args.kwargs["timeout"], 15)
