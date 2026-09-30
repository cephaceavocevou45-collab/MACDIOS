"""Rend l'email obligatoire après l'import des adresses des comptes existants."""

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import migrations, models


def verifier_emails_commercants(apps, schema_editor):
    Commercant = apps.get_model("commerce", "Commercant")
    alias = schema_editor.connection.alias
    adresses_vues = set()
    for adresse in Commercant.objects.using(alias).values_list("email", flat=True):
        normalisee = (adresse or "").strip().lower()
        if not normalisee:
            raise RuntimeError(
                "Des comptes n'ont pas encore d'email. Lancez importer_emails_commercants avant cette migration."
            )
        try:
            validate_email(normalisee)
        except ValidationError as erreur:
            raise RuntimeError("Une adresse email est invalide; corrigez-la avant cette migration.") from erreur
        if normalisee in adresses_vues:
            raise RuntimeError("Des comptes partagent une adresse email; résolvez le doublon avant cette migration.")
        adresses_vues.add(normalisee)


class Migration(migrations.Migration):

    dependencies = [("commerce", "0007_email_commercant_nullable")]

    operations = [
        migrations.RunPython(verifier_emails_commercants, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="commercant",
            name="email",
            field=models.EmailField(max_length=254, unique=True),
        ),
    ]
