import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("commerce", "0019_archivage_produit"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SessionJWT",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("jti_refresh", models.CharField(max_length=255, unique=True)),
                ("cree_le", models.DateTimeField(auto_now_add=True)),
                ("expire_le", models.DateTimeField()),
                ("revoque_le", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("utilisateur", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sessions_jwt", to=settings.AUTH_USER_MODEL)),
            ],
            options={"indexes": [models.Index(fields=["utilisateur", "revoque_le"], name="commerce_session_user_rev_idx")]},
        ),
    ]
