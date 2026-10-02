from django.apps import AppConfig


class CommerceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "commerce"
    verbose_name = "Gestion commerciale"

    def ready(self):
        # Connexion des signaux de journalisation et du verrouillage Axes/DRF.
        from . import signals  # noqa: F401
        # Enregistre le schéma d'authentification cookie auprès de drf-spectacular.
        from . import schema_extensions  # noqa: F401
