"""Archive les clients et protège leurs références financières historiques."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("commerce", "0016_paiementabonnementhistorique")]

    operations = [
        migrations.AddField(
            model_name="client",
            name="actif",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AlterField(
            model_name="dette",
            name="client",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="dettes",
                to="commerce.client",
            ),
        ),
        migrations.AlterField(
            model_name="paiement",
            name="client",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="paiements",
                to="commerce.client",
            ),
        ),
    ]
