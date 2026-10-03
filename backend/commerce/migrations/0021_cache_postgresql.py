"""Crée la table du cache partagé utilisée si Redis n'est pas configuré."""

from django.core.management import call_command
from django.db import migrations


NOM_TABLE_CACHE = "nobi_cache"


def creer_table_cache(apps, schema_editor):
    """Crée la table avec le schéma natif du backend Django DatabaseCache."""
    call_command(
        "createcachetable",
        NOM_TABLE_CACHE,
        database=schema_editor.connection.alias,
        verbosity=0,
    )


def supprimer_table_cache(apps, schema_editor):
    """Supprime la table uniquement lors d'une annulation explicite."""
    tables = schema_editor.connection.introspection.table_names()
    if NOM_TABLE_CACHE in tables:
        table = schema_editor.connection.ops.quote_name(NOM_TABLE_CACHE)
        schema_editor.execute(f"DROP TABLE {table}")


class Migration(migrations.Migration):
    dependencies = [("commerce", "0020_session_jwt")]

    operations = [
        migrations.RunPython(creer_table_cache, supprimer_table_cache),
    ]
