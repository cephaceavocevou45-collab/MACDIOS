"""Réglages de test sans expiration des connexions pendant TestCase."""

from . import settings as reglages_application
from .settings import *  # noqa: F403

# TestCase garde une transaction ouverte autour de chaque test. Le client Django
# déclenche close_old_connections à la fin de ses requêtes; avec CONN_MAX_AGE=60,
# une longue suite peut donc fermer une connexion PostgreSQL encore dans atomic().
# Sans expiration en test, Django ne coupe pas cette connexion au milieu du test.
DATABASES = {
    alias: {**configuration, "CONN_MAX_AGE": None}
    for alias, configuration in reglages_application.DATABASES.items()
}
