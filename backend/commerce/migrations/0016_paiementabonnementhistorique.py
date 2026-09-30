"""Conserve les anciennes transactions automatiques comme historique générique."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("commerce", "0015_configurationessai_alter_journalaudit_action")]

    operations = [
        migrations.RenameModel(
            old_name="TransactionAbonnement",
            new_name="PaiementAbonnementHistorique",
        ),
        migrations.AlterField(
            model_name="paiementabonnementhistorique",
            name="commercant",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="historique_paiements_abonnement",
                to="commerce.commercant",
            ),
        ),
        migrations.AlterField(
            model_name="paiementabonnementhistorique",
            name="plan",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="historique_paiements_abonnement",
                to="commerce.plan",
            ),
        ),
        migrations.RemoveField(
            model_name="paiementabonnementhistorique",
            name="id_transaction_prestataire",
        ),
    ]
