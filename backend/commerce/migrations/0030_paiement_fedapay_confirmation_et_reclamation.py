from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("commerce", "0029_email_commercant_facultatif"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="paiementabonnementhistorique",
            name="statut",
            field=models.CharField(
                choices=[
                    ("en_attente", "En attente"),
                    ("a_valider", "À valider par l'équipe"),
                    ("reussi", "Réussi"),
                    ("echoue", "Échoué"),
                    ("annule", "Annulé"),
                ],
                default="en_attente",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="paiementabonnementhistorique",
            name="checkout_url",
            field=models.URLField(blank=True, editable=False, max_length=1000),
        ),
        migrations.AddField(
            model_name="paiementabonnementhistorique",
            name="date_confirmation_fedapay",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="paiementabonnementhistorique",
            name="valide_par",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="paiements_abonnement_valides",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name="ReclamationPaiementAbonnement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.TextField(max_length=2000)),
                ("date_creation", models.DateTimeField(auto_now_add=True)),
                ("commercant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reclamations_paiement", to=settings.AUTH_USER_MODEL)),
                ("paiement", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="reclamation", to="commerce.paiementabonnementhistorique")),
            ],
            options={"ordering": ["-date_creation"]},
        ),
    ]
