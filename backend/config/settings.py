"""Configuration du backend, avec des garde-fous renforcés hors développement."""

from datetime import timedelta
from pathlib import Path

from decouple import Csv, config
import dj_database_url

from .observabilite import filtrer_evenement_sentry

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = config("SECRET_KEY", default="cle-de-developpement-a-remplacer")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", default="localhost,127.0.0.1" if DEBUG else "", cast=Csv()
)
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS", default="http://localhost:5173" if DEBUG else "", cast=Csv()
)
if not DEBUG and (not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS):
    raise ValueError("ALLOWED_HOSTS doit contenir les domaines exacts en production.")
if not DEBUG and (not CORS_ALLOWED_ORIGINS or "*" in CORS_ALLOWED_ORIGINS):
    raise ValueError("CORS_ALLOWED_ORIGINS doit contenir les origines exactes en production.")

INSTALLED_APPS = [
    "commerce.admin_config.AdministrationConfig", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "cloudinary_storage", "django.contrib.staticfiles",
    "rest_framework", "rest_framework_simplejwt", "corsheaders", "drf_spectacular",
    "axes", "commerce.apps.CommerceConfig",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware", "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "commerce.audit_middleware.ContexteAuditMiddleware",
    # Axes doit rester le dernier middleware pour ses réponses de verrouillage.
    "axes.middleware.AxesMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": dj_database_url.parse(
        config("DATABASE_URL", default="postgresql://postgres:postgres@localhost:5432/gestion_commerce"),
        conn_max_age=60,
        ssl_require=not DEBUG,
    )
}

AUTH_USER_MODEL = "commerce.Commercant"
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_USE_ATTEMPT_EXPIRATION = True
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_HTTP_RESPONSE_CODE = 429
AXES_ENABLE_RETRY_AFTER_HEADER = True
AXES_LOCKOUT_CALLABLE = "commerce.security.reponse_verrouillage"
AXES_USERNAME_CALLABLE = "commerce.security.identifiant_connexion"
AXES_PASSWORD_FORM_FIELD = "mot_de_passe"
AXES_SENSITIVE_PARAMETERS = ["email", "telephone", "mot_de_passe", "token", "authorization", "secret", "api-key"]
if not DEBUG:
    # Render ajoute l'adresse réelle en fin de X-Forwarded-For derrière son proxy TLS.
    AXES_IPWARE_META_PRECEDENCE_ORDER = ("HTTP_X_FORWARDED_FOR", "REMOTE_ADDR")
    AXES_IPWARE_PROXY_COUNT = 1

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Porto-Novo"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "commerce.storage.PreuveCloudinaryStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:5173")
PUBLIC_FRONTEND_URL = config("PUBLIC_FRONTEND_URL", default=FRONTEND_URL)
NUMERO_MTN = config("NUMERO_MTN", default="").strip()
NUMERO_MOOV = config("NUMERO_MOOV", default="").strip()
NUMERO_CELTIIS = config("NUMERO_CELTIIS", default="").strip()
MEDIA_ROOT = BASE_DIR / "media"
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": config("CLOUDINARY_CLOUD_NAME", default=""),
    "API_KEY": config("CLOUDINARY_API_KEY", default=""),
    "API_SECRET": config("CLOUDINARY_API_SECRET", default=""),
    "SECURE": True,
}
PASSWORD_RESET_TIMEOUT = 15 * 60
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())
CORS_ALLOW_CREDENTIALS = False


# Vonage SMS : la simulation est activée par défaut pour éviter tout coût en local.
SMS_SIMULATION = config("SMS_SIMULATION", default=True, cast=bool)
VONAGE_API_KEY = config("VONAGE_API_KEY", default="")
VONAGE_API_SECRET = config("VONAGE_API_SECRET", default="")
VONAGE_SMS_SENDER = config("VONAGE_SMS_SENDER", default="Nobi")

# Brevo Transactional Email : simulation activée par défaut en local.
EMAIL_SIMULATION = config("EMAIL_SIMULATION", default=True, cast=bool)
BREVO_API_KEY = config("BREVO_API_KEY", default="")
BREVO_SENDER_EMAIL = config("BREVO_SENDER_EMAIL", default="")
BREVO_SENDER_NAME = config("BREVO_SENDER_NAME", default="Nobi")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "connexion": "5/minute", "admin_connexion": "3/minute", "inscription": "3/hour", "refresh": "30/minute",
        "mot_de_passe_oublie": "3/hour", "reinitialisation_mot_de_passe": "5/hour",
        "verification_document": "10/minute",
    },
    "NUM_PROXIES": 1 if not DEBUG else None,
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Nobi — API de gestion commerciale",
    "DESCRIPTION": "API REST pour gérer les ventes, le stock, les clients et les abonnements.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "TAGS": [
        {"name": "Auth", "description": "Inscription, connexion et renouvellement JWT."},
        {"name": "Tableau de bord", "description": "Indicateurs du commerçant connecté."},
        {"name": "Produits", "description": "Catalogue et niveau de stock."},
        {"name": "Ventes", "description": "Ventes et historique filtré."},
        {"name": "Clients", "description": "Clients, dettes et règlements."},
        {"name": "Abonnement", "description": "Offres, paiements Mobile Money et statut d'abonnement."},
    ],
    "COMPONENT_SPLIT_REQUEST": True,
    "SECURITY": [{"BearerAuth": []}],
    "APPEND_COMPONENTS": {"securitySchemes": {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
    }},
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# En-têtes de transport adaptés à Render / reverse proxy en production.
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=not DEBUG, cast=bool)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=0 if DEBUG else 31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Sentry ne s'initialise que si un DSN est fourni, et filtre les données en amont.
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN, integrations=[DjangoIntegration()], send_default_pii=False,
        before_send=filtrer_evenement_sentry,
    )

if not DEBUG:
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"json": {"()": "config.observabilite.JsonSansDonneesSensibles"}},
        "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
        "root": {"handlers": ["console"], "level": config("LOG_LEVEL", default="INFO")},
        "loggers": {
            "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
            "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        },
    }
