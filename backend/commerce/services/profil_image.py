"""Validation, nettoyage et accès limité aux images de profil privées."""

from functools import lru_cache
import io
import logging
import os
import time
import warnings

import cloudinary.utils
import requests
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

TAILLE_MAX_IMAGE = 2 * 1024 * 1024
TAILLE_MAX_LOGO_PDF = 2 * 1024 * 1024
logger = logging.getLogger(__name__)


class ImageProfilInvalide(ValueError):
    """Indique que l'image envoyée ne respecte pas les règles de profil."""


def nettoyer_image_profil(fichier):
    """Valide le contenu, enlève ses métadonnées et limite sa taille à 512 px."""
    if fichier.size > TAILLE_MAX_IMAGE:
        raise ImageProfilInvalide("L'image ne doit pas dépasser 2 Mo.")

    try:
        contenu = fichier.read()
        fichier.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(io.BytesIO(contenu))
            format_image = image.format
            if format_image not in {"JPEG", "PNG", "WEBP"}:
                raise ImageProfilInvalide("Choisissez une image JPEG, PNG ou WebP (SVG refusé).")
            image.verify()
            image = Image.open(io.BytesIO(contenu))
            image = ImageOps.exif_transpose(image)
            if image.width * image.height > 40_000_000:
                raise ImageProfilInvalide("Les dimensions de l'image sont trop importantes.")
            image.thumbnail((512, 512), Image.Resampling.LANCZOS)

            if format_image == "JPEG":
                image = image.convert("RGB")
                extension = "jpg"
                options = {"quality": 86, "optimize": True, "progressive": True}
            elif format_image == "PNG":
                image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
                extension = "png"
                options = {"optimize": True}
            else:
                image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
                extension = "webp"
                options = {"quality": 86, "method": 6}

            sortie = io.BytesIO()
            # Une nouvelle image et une sauvegarde sans exif/ipc suppriment les métadonnées.
            image.save(sortie, format=format_image, **options)
            contenu_nettoye = sortie.getvalue()
    except ImageProfilInvalide:
        raise
    except Exception as erreur:
        raise ImageProfilInvalide("Le fichier envoyé n'est pas une image valide.") from erreur

    if len(contenu_nettoye) > TAILLE_MAX_IMAGE:
        raise ImageProfilInvalide("L'image optimisée dépasse la limite de 2 Mo.")
    return ContentFile(contenu_nettoye, name=f"{os.urandom(16).hex()}.{extension}")


def _details_storage(nom):
    public_id, extension = os.path.splitext(nom)
    return public_id, extension.lstrip(".").lower()


def url_logo_profil(utilisateur, duree_secondes=300):
    """Produit un lien signé court pour le logo privé de son propre profil."""
    if not utilisateur.logo_profil:
        return None
    if settings.LOGO_LOCAL_DEVELOPPEMENT:
        return utilisateur.logo_profil.url
    try:
        public_id, extension = _details_storage(utilisateur.logo_profil.name)
        return cloudinary.utils.private_download_url(
            public_id, extension, resource_type="image", type="authenticated",
            expires_at=int(time.time()) + duree_secondes,
        )
    except Exception:
        logger.warning("Impossible de signer le logo de profil.")
        return None


@lru_cache(maxsize=128)
def _telecharger_logo(nom):
    """Télécharge et met en cache les octets d'un logo validé, par nom Cloudinary."""
    if settings.LOGO_LOCAL_DEVELOPPEMENT:
        with default_storage.open(nom, "rb") as fichier:
            return fichier.read()
    public_id, extension = _details_storage(nom)
    lien = cloudinary.utils.private_download_url(
        public_id, extension, resource_type="image", type="authenticated",
        expires_at=int(time.time()) + 30,
    )
    reponse = requests.get(lien, timeout=(0.5, 1.5), stream=True)
    try:
        reponse.raise_for_status()
        morceaux = []
        taille = 0
        for morceau in reponse.iter_content(chunk_size=64 * 1024):
            taille += len(morceau)
            if taille > TAILLE_MAX_LOGO_PDF:
                raise ValueError("Logo trop volumineux pour un PDF.")
            morceaux.append(morceau)
        contenu = b"".join(morceaux)
    finally:
        reponse.close()
    with Image.open(io.BytesIO(contenu)) as image:
        if image.format not in {"JPEG", "PNG", "WEBP"}:
            raise ValueError("Format du logo inattendu.")
        image.verify()
    return contenu


def logo_profil_pour_pdf(utilisateur):
    """Retourne les octets du logo ou None pour laisser le PDF afficher son repli."""
    if not utilisateur.logo_profil:
        return None
    try:
        return _telecharger_logo(utilisateur.logo_profil.name)
    except Exception:
        # Le reçu doit rester disponible même si Cloudinary ne répond pas.
        logger.warning("Logo Cloudinary indisponible pendant la génération d'un PDF.")
        return None


def supprimer_logo_profil(utilisateur):
    """Supprime l'objet Cloudinary et retire sa référence du profil."""
    if not utilisateur.logo_profil:
        return False
    fichier = utilisateur.logo_profil
    nom = fichier.name
    suppression_reussie = fichier.storage.delete(nom)
    if suppression_reussie is False:
        raise OSError("Cloudinary n'a pas confirmé la suppression du logo.")
    utilisateur.logo_profil = None
    utilisateur.save(update_fields=["logo_profil"])
    _telecharger_logo.cache_clear()
    return True


def invalider_cache_logo_profil():
    """Évite de conserver en mémoire un logo remplacé ou supprimé."""
    _telecharger_logo.cache_clear()
