"""Configuration du backend, avec des garde-fous renforcés hors développement."""

from datetime import timedelta
from pathlib import Path
import sys
import warnings

from decouple import Csv, config
import dj_database_url
from corsheaders.defaults import default_headers
from django.core.exceptions import ImproperlyConfigured
from commerce.branding import NOM_APPLICATION

from .observabilite import filtrer_evenement_sentry

BASE_DIR = Path(__file__).resolve().parent.parent
ENVIRONMENT = config("ENVIRONMENT", default="").strip().lower()
if not ENVIRONMENT:
    raise ImproperlyConfigured("ENVIRONMENT doit être explicitement défini.")
if ENVIRONMENT not in {"development", "test", "production"}:
    raise ImproperlyConfigured("ENVIRONMENT doit être development, test ou production.")

# Railway est reconnu même si ENVIRONMENT a été oublié dans sa configuration.
EST_PRODUCTION = (
    ENVIRONMENT == "production"
    or bool(config("RAILWAY_ENVIRONMENT", default="").strip())
)

# DEBUG est désactivé par défaut. En production, les deux réglages critiques
# doivent être explicitement fournis et ne peuvent pas être remplacés par un repli.
debug_env = config("DEBUG", default=None)
if EST_PRODUCTION:
    if debug_env is None or not str(debug_env).strip():
        raise ImproperlyConfigured("DEBUG doit être explicitement défini à False en production.")
    DEBUG = config("DEBUG", cast=bool)
    if DEBUG:
        raise ImproperlyConfigured("DEBUG=True est interdit en production.")
    SECRET_KEY = config("SECRET_KEY", default="").strip()
    if not SECRET_KEY:
        raise ImproperlyConfigured("SECRET_KEY doit être explicitement définie en production.")
else:
    DEBUG = config("DEBUG", default=False, cast=bool)
    SECRET_KEY = config(
        "SECRET_KEY",
        default="django-insecure-local-only-change-before-deployment",
    ).strip()
    if not SECRET_KEY:
        raise ImproperlyConfigured("SECRET_KEY ne peut pas être vide.")

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", default="localhost,127.0.0.1" if not EST_PRODUCTION else "", cast=Csv()
)
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS", default="http://localhost:5173" if not EST_PRODUCTION else "", cast=Csv()
)
CORS_ALLOW_HEADERS = (*default_headers, "idempotency-key")
if EST_PRODUCTION and (not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS):
    raise ValueError("ALLOWED_HOSTS doit contenir les domaines exacts en production.")
if EST_PRODUCTION and (not CORS_ALLOWED_ORIGINS or "*" in CORS_ALLOWED_ORIGINS):
    raise ValueError("CORS_ALLOWED_ORIGINS doit contenir les origines exactes en production.")

INSTALLED_APPS = [
    "commerce.admin_config.AdministrationConfig", "django.contrib.auth", "django.contrib.contenttypes",
    # Les preuves utilisent directement le backend Cloudinary ; l'application
    # Cloudinary n'est pas nécessaire ici et remplace collectstatic par une
    # commande incompatible avec les réglages STORAGES de Django récent.
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "rest_framework_simplejwt", "rest_framework_simplejwt.token_blacklist", "corsheaders", "drf_spectacular",
    "axes", "commerce.apps.CommerceConfig",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware", "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "commerce.audit_middleware.ContexteAuditMiddleware",
    "commerce.middleware_maintenance.ModeMaintenanceMiddleware",
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

# Le cache local sert au développement. En production, REDIS_URL permet de
# partager les compteurs DRF/Axes entre plusieurs processus ou instances.
REDIS_URL = config("REDIS_URL", default="").strip()
if REDIS_URL:
    if not REDIS_URL.startswith(("redis://", "rediss://", "unix://")):
        raise ImproperlyConfigured("REDIS_URL doit utiliser redis://, rediss:// ou unix://.")
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "TIMEOUT": 300,
            "KEY_PREFIX": "nobi",
            "OPTIONS": {
                "socket_connect_timeout": 3,
                "socket_timeout": 3,
                "retry_on_timeout": True,
            },
        }
    }
elif EST_PRODUCTION:
    # Le cache PostgreSQL reste partagé entre les workers lorsque Redis n'est
    # pas encore provisionné. Il augmente toutefois la charge de la base.
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "nobi_cache",
            "TIMEOUT": 300,
            "KEY_PREFIX": "nobi",
            "OPTIONS": {"MAX_ENTRIES": 10000, "CULL_FREQUENCY": 3},
        }
    }
    warnings.warn(
        "REDIS_URL absent : les compteurs partagés utilisent la table de cache PostgreSQL. "
        "Redis n'est pas configuré et cette solution augmente la charge de la base.",
        RuntimeWarning,
        stacklevel=1,
    )
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "nobi-local-throttles",
            "TIMEOUT": 300,
        }
    }

BACKUP_ENCRYPTION_KEY = config("BACKUP_ENCRYPTION_KEY", default="").strip()
BACKUP_S3_BUCKET = config("BACKUP_S3_BUCKET", default="").strip()
BACKUP_S3_PREFIX = config("BACKUP_S3_PREFIX", default="nobi/database").strip("/")
AWS_REGION = config("AWS_REGION", default="")
AWS_ENDPOINT_URL = config("AWS_ENDPOINT_URL", default="")
SAUVEGARDE_S3_ACTIVE = bool(BACKUP_ENCRYPTION_KEY and BACKUP_S3_BUCKET)
if EST_PRODUCTION and not SAUVEGARDE_S3_ACTIVE:
    warnings.warn(
        "Sauvegardes S3 désactivées : BACKUP_ENCRYPTION_KEY et BACKUP_S3_BUCKET "
        "doivent être configurées ensemble. Aucune sauvegarde distante n'est assurée.",
        RuntimeWarning,
        stacklevel=1,
    )

AUTH_USER_MODEL = "commerce.Commercant"
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
    "commerce.authentication.TelephoneBackend",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
if ENVIRONMENT == "test":
    # Hachage rapide uniquement dans les bases jetables des tests automatisés.
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
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
if EST_PRODUCTION:
    # Railway place l'application derrière son proxy HTTPS.
    AXES_IPWARE_META_PRECEDENCE_ORDER = ("HTTP_X_FORWARDED_FOR", "REMOTE_ADDR")
    AXES_IPWARE_PROXY_COUNT = 1

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Porto-Novo"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": config("CLOUDINARY_CLOUD_NAME", default=""),
    "API_KEY": config("CLOUDINARY_API_KEY", default=""),
    "API_SECRET": config("CLOUDINARY_API_SECRET", default=""),
    "SECURE": True,
}
CLOUDINARY_CONFIGURE = all(CLOUDINARY_STORAGE[cle] for cle in ("CLOUD_NAME", "API_KEY", "API_SECRET"))
# Le stockage local n'est permis que pour les logos en développement : les preuves
# et toute donnée de production restent sur Cloudinary.
EXECUTION_TESTS = any("pytest" in str(argument).lower() for argument in sys.argv[:2]) or (
    len(sys.argv) > 1 and sys.argv[1] == "test"
)
LOGO_LOCAL_DEVELOPPEMENT = ENVIRONMENT == "development" and not EXECUTION_TESTS and not CLOUDINARY_CONFIGURE
if LOGO_LOCAL_DEVELOPPEMENT:
    import logging

    logging.getLogger("django.config").warning(
        "Cloudinary n'est pas configuré : les logos de profil seront stockés localement pour le développement."
    )

STORAGES = {
    "default": {
        "BACKEND": (
            "django.core.files.storage.FileSystemStorage"
            if LOGO_LOCAL_DEVELOPPEMENT
            else "commerce.storage.PreuveCloudinaryStorage"
        )
    },
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:5173")
PUBLIC_FRONTEND_URL = config("PUBLIC_FRONTEND_URL", default=FRONTEND_URL)
# Optionnel. Le point machine de bascule maintenance reste fermé si le secret manque.
DEPLOYMENT_MAINTENANCE_TOKEN = config("DEPLOYMENT_MAINTENANCE_TOKEN", default="").strip()
NUMERO_MTN = config("NUMERO_MTN", default="").strip()
NUMERO_MOOV = config("NUMERO_MOOV", default="").strip()
NUMERO_CELTIIS = config("NUMERO_CELTIIS", default="").strip()
FEDAPAY_SECRET_KEY = config("FEDAPAY_SECRET_KEY", default="").strip()
FEDAPAY_WEBHOOK_SECRET = config("FEDAPAY_WEBHOOK_SECRET", default="").strip()
FEDAPAY_ENVIRONMENT = config("FEDAPAY_ENVIRONMENT", default="sandbox").strip().lower()
if FEDAPAY_ENVIRONMENT not in {"sandbox", "live"}:
    raise ImproperlyConfigured("FEDAPAY_ENVIRONMENT doit valoir sandbox ou live.")
PASSWORD_RESET_TIMEOUT = 15 * 60
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())
CORS_ALLOW_CREDENTIALS = True
AUTH_COOKIE_SECURE = config("AUTH_COOKIE_SECURE", default=EST_PRODUCTION, cast=bool)
AUTH_COOKIE_SAMESITE = config("AUTH_COOKIE_SAMESITE", default="None" if EST_PRODUCTION else "Lax")
if AUTH_COOKIE_SAMESITE not in {"Strict", "Lax", "None"}:
    raise ImproperlyConfigured("AUTH_COOKIE_SAMESITE doit valoir Strict, Lax ou None.")
if EST_PRODUCTION and (not AUTH_COOKIE_SECURE or AUTH_COOKIE_SAMESITE != "None"):
    raise ImproperlyConfigured("En production, les cookies JWT exigent Secure et SameSite=None pour l'interface séparée.")
if not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = list(CORS_ALLOWED_ORIGINS)
CSRF_COOKIE_SECURE = AUTH_COOKIE_SECURE
CSRF_COOKIE_SAMESITE = AUTH_COOKIE_SAMESITE


# Vonage SMS : la simulation est activée par défaut pour éviter tout coût en local.
SMS_SIMULATION = config("SMS_SIMULATION", default=True, cast=bool)
VONAGE_API_KEY = config("VONAGE_API_KEY", default="")
VONAGE_API_SECRET = config("VONAGE_API_SECRET", default="")
VONAGE_SMS_SENDER = config("VONAGE_SMS_SENDER", default=NOM_APPLICATION) or NOM_APPLICATION

# Brevo Transactional Email : simulation activée par défaut en local.
EMAIL_SIMULATION = config("EMAIL_SIMULATION", default=True, cast=bool)
BREVO_API_KEY = config("BREVO_API_KEY", default="")
BREVO_SENDER_EMAIL = config("BREVO_SENDER_EMAIL", default="")
BREVO_SENDER_NAME = config("BREVO_SENDER_NAME", default=NOM_APPLICATION) or NOM_APPLICATION

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["commerce.authentication.CookieSessionJWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PAGINATION_CLASS": "commerce.pagination.PaginationStandard",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "connexion": "5/minute", "admin_connexion": "3/minute", "inscription": "3/hour", "refresh": "30/minute",
        "mot_de_passe_oublie": "3/hour", "reinitialisation_mot_de_passe": "5/hour",
        "verification_document": "10/minute", "vente": "60/minute", "dette": "30/minute",
        "paiement": "30/minute",
    },
    "NUM_PROXIES": 1 if EST_PRODUCTION else None,
}
SPECTACULAR_SETTINGS = {
    "TITLE": f"{NOM_APPLICATION} — API de gestion commerciale",
    "DESCRIPTION": "API REST pour gérer les ventes, le stock, les clients et les abonnements.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "AbonnementStatutEnum": [("essai", "Essai"), ("actif", "Actif"), ("expire", "Expiré")],
        "HistoriquePaiementStatutEnum": [("en_attente", "En attente"), ("reussi", "Réussi"), ("echoue", "Échoué")],
        "DemandePaiementStatutEnum": [("en_attente", "En attente"), ("validee", "Validée"), ("rejetee", "Rejetée")],
    },
    "TAGS": [
        {"name": "Auth", "description": "Inscription, connexion et renouvellement JWT."},
        {"name": "Tableau de bord", "description": "Indicateurs du commerçant connecté."},
        {"name": "Produits", "description": "Catalogue et niveau de stock."},
        {"name": "Ventes", "description": "Ventes et historique filtré."},
        {"name": "Clients", "description": "Clients, dettes et règlements."},
        {"name": "Abonnement", "description": "Offres, paiements Mobile Money et statut d'abonnement."},
    ],
    "COMPONENT_SPLIT_REQUEST": True,
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# En-têtes de transport adaptés au reverse proxy HTTPS en production.
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=EST_PRODUCTION, cast=bool)
SESSION_COOKIE_SECURE = EST_PRODUCTION
CSRF_COOKIE_SECURE = EST_PRODUCTION
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=0 if not EST_PRODUCTION else 31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = EST_PRODUCTION
SECURE_HSTS_PRELOAD = False
if EST_PRODUCTION and not SECURE_SSL_REDIRECT:
    raise ImproperlyConfigured("SECURE_SSL_REDIRECT doit être activé en production.")
if EST_PRODUCTION and SECURE_HSTS_SECONDS < 31536000:
    raise ImproperlyConfigured("SECURE_HSTS_SECONDS doit être au moins égal à un an en production.")
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

if EST_PRODUCTION:
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
