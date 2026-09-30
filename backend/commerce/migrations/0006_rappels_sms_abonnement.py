"""Ajoute le marqueur anti-doublon pour les SMS d'échéance."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("commerce", "0005_alter_commercant_telephone_correctiondette"),
    ]

    operations = [
        migrations.AddField(
            model_name="abonnement",
            name="rappel_sms_echeance_le",
            field=models.DateField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="abonnement",
            name="rappel_sms_envoye_le",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
    ]
