"""Stockage Cloudinary privé dédié aux preuves de paiement d'abonnement."""

import os
import time

import cloudinary.uploader
import cloudinary.utils
import requests
from cloudinary_storage.storage import MediaCloudinaryStorage
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile


class PreuveCloudinaryStorage(MediaCloudinaryStorage):
    """Enregistre les preuves en mode authentifié et les ouvre via un lien signé court."""

    def _upload(self, name, content):
        options = {
            "use_filename": True,
            "resource_type": "image",
            "type": "authenticated",
            "tags": self.TAG,
        }
        dossier = os.path.dirname(name)
        if dossier:
            options["folder"] = dossier
        return cloudinary.uploader.upload(content, **options)

    def _save(self, name, content):
        nom_normalise = self._prepend_prefix(self._normalise_name(name))
        resultat = self._upload(nom_normalise, UploadedFile(content, nom_normalise))
        # Le format est conservé pour construire le lien privé de téléchargement.
        return f"{resultat['public_id']}.{resultat['format']}"

    def _open(self, name, mode="rb"):
        extension = os.path.splitext(name)[1].lstrip(".").lower()
        public_id = os.path.splitext(name)[0]
        lien = cloudinary.utils.private_download_url(
            public_id,
            extension,
            resource_type="image",
            type="authenticated",
            expires_at=int(time.time()) + 60,
        )
        try:
            reponse = requests.get(lien, timeout=15)
            reponse.raise_for_status()
        except requests.RequestException as erreur:
            raise OSError("La preuve de paiement est temporairement indisponible.") from erreur
        fichier = ContentFile(reponse.content, name=name)
        fichier.mode = mode
        return fichier

    def delete(self, name):
        public_id = os.path.splitext(name)[0]
        resultat = cloudinary.uploader.destroy(
            public_id, invalidate=True, resource_type="image", type="authenticated",
        )
        return resultat.get("result") == "ok"
