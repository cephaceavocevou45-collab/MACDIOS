"""Stocke les réponses des ventes, dettes et paiements rejoués."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("commerce", "0017_archivage_client")]

    operations = [
        migrations.CreateModel(
            name="RequeteIdempotente",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("operation", models.CharField(max_length=20)),
                ("cle", models.CharField(max_length=100)),
                ("empreinte", models.CharField(max_length=64)),
                ("code_http", models.PositiveSmallIntegerField(default=201)),
                ("reponse", models.JSONField(default=dict)),
                ("date_creation", models.DateTimeField(auto_now_add=True)),
                (
                    "commercant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="requetes_idempotentes",
                        to="commerce.commercant",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="requeteidempotente",
            constraint=models.UniqueConstraint(
                fields=("commercant", "operation", "cle"),
                name="unique_requete_idempotente_commercant_operation",
            ),
        ),
    ]
