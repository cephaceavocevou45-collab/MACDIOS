import datetime
import decimal
import uuid

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def creer_offres_et_essais(apps, schema_editor):
    """Ajoute les offres initiales et un essai de 14 jours aux comptes existants."""
    Plan = apps.get_model("commerce", "Plan")
    Abonnement = apps.get_model("commerce", "Abonnement")
    Commercant = apps.get_model("commerce", "Commercant")
    alias = schema_editor.connection.alias
    essai, _ = Plan.objects.using(alias).get_or_create(
        nom="Essai gratuit",
        defaults={"prix": decimal.Decimal("0"), "duree_jours": 14, "actif": True},
    )
    Plan.objects.using(alias).get_or_create(
        nom="Mensuel",
        defaults={"prix": decimal.Decimal("2500"), "duree_jours": 30, "actif": True},
    )
    debut = timezone.now()
    for commercant in Commercant.objects.using(alias).all().iterator():
        Abonnement.objects.using(alias).get_or_create(
            commercant_id=commercant.pk,
            defaults={
                "plan_id": essai.pk,
                "statut": "essai",
                "date_debut": debut,
                "date_fin": debut + datetime.timedelta(days=14),
            },
        )


class Migration(migrations.Migration):
    dependencies = [("commerce", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Plan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nom", models.CharField(max_length=100, unique=True)),
                ("prix", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ("duree_jours", models.PositiveIntegerField()),
                ("actif", models.BooleanField(default=True)),
            ],
            options={"ordering": ["prix", "nom"]},
        ),
        migrations.CreateModel(
            name="Abonnement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("statut", models.CharField(choices=[("essai", "Essai"), ("actif", "Actif"), ("expire", "Expiré")], default="essai", max_length=10)),
                ("date_debut", models.DateTimeField()),
                ("date_fin", models.DateTimeField()),
                ("commercant", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="abonnement", to=settings.AUTH_USER_MODEL)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="abonnements", to="commerce.plan")),
            ],
        ),
        migrations.CreateModel(
            name="TransactionAbonnement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("montant", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ("statut", models.CharField(choices=[("en_attente", "En attente"), ("reussi", "Réussi"), ("echoue", "Échoué")], default="en_attente", max_length=12)),
                ("reference", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("id_transaction_prestataire", models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ("date_creation", models.DateTimeField(auto_now_add=True)),
                ("commercant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="transactions_abonnement", to=settings.AUTH_USER_MODEL)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transactions_abonnement", to="commerce.plan")),
            ],
            options={"ordering": ["-date_creation"]},
        ),
        migrations.RunPython(creer_offres_et_essais, migrations.RunPython.noop),
    ]
