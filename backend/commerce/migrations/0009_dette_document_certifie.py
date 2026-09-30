"""Ajoute des identifiants de vérification aux reçus de dette existants."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("commerce", "0008_email_commercant_obligatoire")]

    operations = [
        migrations.AddField(
            model_name="dette",
            name="code_verification",
            field=models.UUIDField(blank=True, editable=False, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="dette",
            name="date_generation",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
    ]
