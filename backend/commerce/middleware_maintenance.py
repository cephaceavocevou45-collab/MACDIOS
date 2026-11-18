"""Refuse les opérations de l'espace commerçant pendant une maintenance."""

from django.http import JsonResponse

from .maintenance import lire_mode_maintenance


class ModeMaintenanceMiddleware:
    """Laisse le back-office agir pour pouvoir terminer puis désactiver la maintenance."""

    chemins_autorises = (
        "/api/maintenance/",
        "/api/deploiement/maintenance/",
        "/api/version/",
        "/api/admin/",
        "/api/auth/csrf/",
        "/api/auth/session/",
        "/api/auth/deconnexion/",
        "/api/sante/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        est_api = request.path.startswith("/api/")
        chemin_autorise = any(request.path.startswith(chemin) for chemin in self.chemins_autorises)
        if est_api and not chemin_autorise:
            etat = lire_mode_maintenance()
            if etat["actif"]:
                return JsonResponse(
                    {"code": "maintenance_active", "detail": etat["message"]},
                    status=503,
                    headers={"Retry-After": "300"},
                )
        return self.get_response(request)
