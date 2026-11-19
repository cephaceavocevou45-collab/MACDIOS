from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("commerce", "0026_modemaintenance")]

    operations = [
        migrations.AddField(
            model_name="paiementabonnementhistorique",
            name="fedapay_transaction_id",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
    ]
