"""Extensions OpenAPI pour décrire les mécanismes d'authentification locaux."""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CookieSessionJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """Décrit le cookie HttpOnly utilisé par l'authentification JWT."""

    target_class = "commerce.authentication.CookieSessionJWTAuthentication"
    name = "CookieJWT"
    priority = 1

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": "nobi_access",
            "description": (
                "Cookie d'accès HttpOnly. Pour toute requête modifiant des données, "
                "fournir aussi le jeton CSRF dans X-CSRFToken, obtenu via /api/auth/csrf/."
            ),
        }
