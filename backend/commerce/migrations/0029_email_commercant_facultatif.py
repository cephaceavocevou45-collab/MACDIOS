"""Autorise les nouveaux comptes à utiliser le téléphone sans email."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("commerce", "0028_produit_date_peremption")]

    operations = [
        migrations.AlterField(
            model_name="commercant",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True),
        ),
    ]
