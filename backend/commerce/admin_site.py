"""Interface Django réservée aux comptes super-administrateurs."""

from django.contrib.admin import AdminSite
from .branding import NOM_APPLICATION


class SiteSuperAdmin(AdminSite):
    """Empêche un sous-admin staff de contourner les droits de l'API."""

    site_header = f"Administration de {NOM_APPLICATION}"
    site_title = f"Administration {NOM_APPLICATION}"
    index_title = "Gestion de la plateforme"

    def has_permission(self, request):
        return bool(
            request.user.is_active
            and request.user.is_authenticated
            and request.user.is_superuser
        )
