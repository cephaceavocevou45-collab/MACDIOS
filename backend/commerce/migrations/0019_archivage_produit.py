"""Archive les produits sans effacer les ventes qui les référencent."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("commerce", "0018_requete_idempotente")]

    operations = [
        migrations.AddField(
            model_name="produit",
            name="actif",
            field=models.BooleanField(db_index=True, default=True),
        ),
    ]
