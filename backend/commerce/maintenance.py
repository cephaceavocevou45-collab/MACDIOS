"""Lecture partagée et cache du réglage global de maintenance."""

import logging
import threading
import time

from django.core.cache import cache

from .models import ModeMaintenance

logger = logging.getLogger(__name__)
CLE_CACHE_MAINTENANCE = "commerce.mode_maintenance.v1"
DUREE_CACHE_MAINTENANCE = 5
MESSAGE_MAINTENANCE_DEFAUT = "Une maintenance est en cours. Merci de revenir dans quelques instants."
_verrou_etat_local = threading.Lock()
_etat_local = None
_expiration_locale = 0.0


def lire_mode_maintenance():
    """Retourne un état compact avec une courte mémoire locale par processus."""
    global _etat_local, _expiration_locale
    with _verrou_etat_local:
        if _etat_local is not None and time.monotonic() < _expiration_locale:
            return dict(_etat_local)

        try:
            etat = cache.get(CLE_CACHE_MAINTENANCE)
        except Exception:
            # Le réglage reste lisible depuis PostgreSQL si le cache est indisponible.
            logger.warning("Cache de maintenance indisponible ; lecture directe en base.")
            etat = None

        if etat is None:
            try:
                configuration = ModeMaintenance.objects.filter(pk=1).values("actif", "message").first()
            except Exception:
                # Une panne de base ne doit pas transformer une indisponibilité en maintenance annoncée.
                logger.exception("Impossible de lire le réglage de maintenance.")
                return {"actif": False, "message": MESSAGE_MAINTENANCE_DEFAUT}
            etat = {
                "actif": bool(configuration and configuration["actif"]),
                "message": (configuration or {}).get("message") or MESSAGE_MAINTENANCE_DEFAUT,
            }
            try:
                cache.set(CLE_CACHE_MAINTENANCE, etat, DUREE_CACHE_MAINTENANCE)
            except Exception:
                logger.warning("Impossible de mettre en cache le réglage de maintenance.")

        _etat_local = dict(etat)
        _expiration_locale = time.monotonic() + DUREE_CACHE_MAINTENANCE
        return dict(_etat_local)


def publier_mode_maintenance(actif, message):
    """Diffuse le nouvel état via le cache partagé déjà configuré pour le projet."""
    global _etat_local, _expiration_locale
    etat = {"actif": bool(actif), "message": message or MESSAGE_MAINTENANCE_DEFAUT}
    try:
        cache.set(CLE_CACHE_MAINTENANCE, etat, DUREE_CACHE_MAINTENANCE)
    except Exception:
        logger.warning("Impossible de publier le nouvel état de maintenance dans le cache.")
    with _verrou_etat_local:
        _etat_local = dict(etat)
        _expiration_locale = time.monotonic() + DUREE_CACHE_MAINTENANCE
    return dict(etat)


def reinitialiser_cache_local_maintenance():
    """Réinitialise le cache mémoire local, principalement pour isoler les tests."""
    global _etat_local, _expiration_locale
    with _verrou_etat_local:
        _etat_local = None
        _expiration_locale = 0.0
