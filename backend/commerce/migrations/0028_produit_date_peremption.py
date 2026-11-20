from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("commerce", "0027_paiementabonnement_fedapay_id")]

    operations = [
        migrations.AddField(
            model_name="produit",
            name="date_peremption",
            field=models.DateField(blank=True, null=True),
        ),
    ]
