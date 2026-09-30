"""Limites dédiées aux routes publiques sensibles."""

from rest_framework.settings import api_settings
from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle


class ThrottleRouteSensible(ScopedRateThrottle):
    """Nom français pour les routes publiques protégées par un scope DRF."""

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES[self.scope]


class ThrottleConnexion(ThrottleRouteSensible):
    def allow_request(self, request, view):
        view.throttle_scope = "connexion"
        return super().allow_request(request, view)


class ThrottleConnexionAdmin(ThrottleRouteSensible):
    """Resserre les tentatives contre le compte d'administration."""

    def allow_request(self, request, view):
        view.throttle_scope = "admin_connexion"
        return super().allow_request(request, view)


class ThrottleInscription(ThrottleRouteSensible):
    def allow_request(self, request, view):
        view.throttle_scope = "inscription"
        return super().allow_request(request, view)


class ThrottleRefresh(ThrottleRouteSensible):
    """Version à taux dynamique pour permettre une configuration par environnement."""

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES[self.scope]


class ThrottleVerificationDocument(SimpleRateThrottle):
    """Limite les vérifications publiques par IP, même si un JWT est fourni."""

    scope = "verification_document"

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES[self.scope]

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }
