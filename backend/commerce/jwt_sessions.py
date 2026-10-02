"""Création, rotation et révocation des sessions JWT de Nobi."""

from datetime import datetime, timezone as datetime_timezone
import uuid

from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import SessionJWT

COOKIE_ACCESS = "nobi_access"
COOKIE_REFRESH = "nobi_refresh"


def creer_jetons_session(utilisateur):
    """Crée une session révocable puis des JWT liés à son identifiant serveur."""
    refresh = RefreshToken.for_user(utilisateur)
    identifiant_session = uuid.uuid4()
    refresh["session_id"] = str(identifiant_session)
    expiration = datetime.fromtimestamp(refresh["exp"], tz=datetime_timezone.utc)
    SessionJWT.objects.create(
        id=identifiant_session,
        utilisateur=utilisateur,
        jti_refresh=str(refresh["jti"]),
        expire_le=expiration,
    )
    return str(refresh.access_token), str(refresh)


def definir_cookies_auth(response, access, refresh):
    """Dépose les JWT uniquement dans des cookies inaccessibles au JavaScript."""
    options = {
        "secure": settings.AUTH_COOKIE_SECURE,
        "httponly": True,
        "samesite": settings.AUTH_COOKIE_SAMESITE,
        "path": "/",
    }
    response.set_cookie(COOKIE_ACCESS, access, max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()), **options)
    response.set_cookie(COOKIE_REFRESH, refresh, max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()), **options)
    response["Cache-Control"] = "no-store"
    return response


def effacer_cookies_auth(response):
    """Efface les cookies de session après révocation ou déconnexion."""
    for nom in (COOKIE_ACCESS, COOKIE_REFRESH):
        response.delete_cookie(
            nom, path="/", samesite=settings.AUTH_COOKIE_SAMESITE,
        )
    response["Cache-Control"] = "no-store"
    return response


def revoquer_sessions_utilisateur(utilisateur):
    """Révoque immédiatement tous les access et refresh de l'utilisateur."""
    SessionJWT.objects.filter(utilisateur=utilisateur, revoque_le__isnull=True).update(revoque_le=timezone.now())


def session_depuis_refresh(refresh_brut):
    """Valide qu'un refresh appartient à une session connue et encore active."""
    try:
        jeton = RefreshToken(refresh_brut)
    except (TokenError, TypeError, ValueError) as erreur:
        raise TokenError("Refresh token invalide ou expiré.") from erreur
    session = SessionJWT.objects.select_for_update().filter(
        pk=jeton.get("session_id"),
        utilisateur_id=jeton.get("user_id"),
        jti_refresh=str(jeton.get("jti")),
        revoque_le__isnull=True,
        expire_le__gt=timezone.now(),
    ).first()
    if session is None:
        raise TokenError("Cette session a été révoquée ou a déjà été renouvelée.")
    return session, jeton


def enregistrer_rotation(session, refresh_brut):
    """Associe la session au nouveau refresh token après rotation."""
    refresh = RefreshToken(refresh_brut)
    session.jti_refresh = str(refresh["jti"])
    session.expire_le = datetime.fromtimestamp(refresh["exp"], tz=datetime_timezone.utc)
    session.save(update_fields=["jti_refresh", "expire_le"])


def revoquer_session(session):
    """Révoque une session individuelle, sans attendre l'expiration des access."""
    if session and session.revoque_le is None:
        session.revoque_le = timezone.now()
        session.save(update_fields=["revoque_le"])
