"""Authentification JWT par cookie HttpOnly, session serveur et protection CSRF."""

from django.utils import timezone
from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import SAFE_METHODS

from .models import SessionJWT


def verifier_csrf(request):
    """Applique la vérification Django CSRF aux requêtes authentifiées par cookie."""
    django_request = request._request
    if not django_request.COOKIES.get("csrftoken") or not django_request.headers.get("X-CSRFToken"):
        raise PermissionDenied("Vérification de sécurité manquante. Actualisez la page et réessayez.")
    check = CSRFCheck(lambda req: None)
    check.process_request(django_request)
    raison = check.process_view(django_request, None, (), {})
    if raison:
        raise AuthenticationFailed(f"Jeton CSRF manquant ou invalide : {raison}")


class CookieSessionJWTAuthentication(JWTAuthentication):
    """Accepte les cookies HttpOnly et rejette toute session serveur révoquée."""

    cookie_name = "nobi_access"

    def authenticate(self, request):
        valeur_cookie = request.COOKIES.get(self.cookie_name)
        valeur_header = self.get_header(request)
        if valeur_cookie:
            raw_token = valeur_cookie.encode("utf-8")
            if request.method not in SAFE_METHODS:
                verifier_csrf(request)
        elif valeur_header:
            raw_token = self.get_raw_token(valeur_header)
        else:
            return None

        if raw_token is None:
            return None
        try:
            jeton = self.get_validated_token(raw_token)
        except Exception as erreur:
            raise AuthenticationFailed("La session a expiré. Reconnectez-vous.") from erreur

        identifiant_session = jeton.get("session_id")
        if not identifiant_session:
            raise AuthenticationFailed("Cette session n'est plus valide. Reconnectez-vous.")
        session = SessionJWT.objects.filter(
            pk=identifiant_session,
            utilisateur_id=jeton.get("user_id"),
            revoque_le__isnull=True,
            expire_le__gt=timezone.now(),
        ).first()
        if session is None:
            raise AuthenticationFailed("Cette session a été révoquée ou a expiré. Reconnectez-vous.")

        utilisateur = self.get_user(jeton)
        return utilisateur, jeton
