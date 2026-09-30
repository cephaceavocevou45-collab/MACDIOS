"""Prépare l'email unique sans inventer d'adresse pour les anciens comptes."""

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import migrations, models

import commerce.validators


def normaliser_emails_existants(apps, schema_editor):
    Commercant = apps.get_model("commerce", "Commercant")
    alias = schema_editor.connection.alias
    lignes = list(Commercant.objects.using(alias).values_list("pk", "email"))
    adresses_vues = set()
    for identifiant, adresse in lignes:
        normalisee = (adresse or "").strip().lower()
        if not normalisee:
            Commercant.objects.using(alias).filter(pk=identifiant).update(email=None)
            continue
        try:
            validate_email(normalisee)
        except ValidationError as erreur:
            raise RuntimeError(
                "Un compte possède une adresse email invalide. Corrigez-la avant de relancer la migration."
            ) from erreur
        if normalisee in adresses_vues:
            raise RuntimeError(
                "Plusieurs comptes utilisent la même adresse email. Résolvez le doublon avant la migration."
            )
        adresses_vues.add(normalisee)
        Commercant.objects.using(alias).filter(pk=identifiant).update(email=normalisee)


class Migration(migrations.Migration):

    dependencies = [("commerce", "0006_rappels_sms_abonnement")]

    operations = [
        migrations.AlterField(
            model_name="commercant",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True, verbose_name="email address"),
        ),
        migrations.RunPython(normaliser_emails_existants, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="commercant",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True, verbose_name="email address"),
        ),
        migrations.AlterField(
            model_name="commercant",
            name="telephone",
            field=models.CharField(blank=True, max_length=20, validators=[commerce.validators.valider_telephone_benin]),
        ),
    ]
