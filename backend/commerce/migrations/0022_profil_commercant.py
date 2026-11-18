import commerce.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("commerce", "0021_cache_postgresql"),
    ]

    operations = [
        migrations.AddField(
            model_name="commercant",
            name="logo_profil",
            field=models.ImageField(blank=True, null=True, upload_to=commerce.models.profil_logo_upload_to),
        ),
        migrations.AddField(
            model_name="commercant",
            name="adresse",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="commercant",
            name="ville",
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
