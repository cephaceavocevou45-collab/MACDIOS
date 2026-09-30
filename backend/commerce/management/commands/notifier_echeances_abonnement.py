"""Envoie une fois le rappel SMS précédant l'échéance d'un abonnement."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from commerce.models import Abonnement
from notifications.sms import ErreurEnvoiSms, envoyer_sms


class Command(BaseCommand):
    help = "Envoie les rappels SMS des essais et abonnements qui expirent sous trois jours."

    def handle(self, *args, **options):
        maintenant = timezone.now()
        echeance_max = maintenant + timedelta(days=3)
        abonnements = Abonnement.objects.select_related("commercant").filter(
            statut__in=[Abonnement.Statut.ESSAI, Abonnement.Statut.ACTIF],
            date_fin__gt=maintenant,
            date_fin__lte=echeance_max,
        )

        nombre_envoye = 0
        nombre_echec = 0
        nombre_ignore = 0
        for abonnement in abonnements.iterator():
            date_cible = timezone.localtime(abonnement.date_fin).date()
            if abonnement.rappel_sms_echeance_le == date_cible:
                continue
            if not abonnement.commercant.telephone:
                # Le téléphone est facultatif depuis le passage à la connexion email.
                nombre_ignore += 1
                continue
            date_echeance = timezone.localtime(abonnement.date_fin).strftime("%d/%m/%Y")
            message = (
                f"{abonnement.commercant.nom_boutique} : votre "
                f"{'essai gratuit' if abonnement.statut == Abonnement.Statut.ESSAI else 'abonnement'} "
                f"prend fin le {date_echeance}. Renouvelez-le pour continuer à créer des ventes."
            )
            try:
                envoyer_sms(abonnement.commercant.telephone, message)
            except (ErreurEnvoiSms, ValueError):
                # On ne marque pas l'échéance : la tâche pourra réessayer demain.
                nombre_echec += 1
                self.stderr.write("Échec d'envoi d'un rappel d'échéance; nouvelle tentative ultérieure.")
                continue

            abonnement.rappel_sms_echeance_le = date_cible
            abonnement.rappel_sms_envoye_le = maintenant
            abonnement.save(update_fields=["rappel_sms_echeance_le", "rappel_sms_envoye_le"])
            nombre_envoye += 1

        self.stdout.write(self.style.SUCCESS(
            f"Rappels terminés : {nombre_envoye} envoyé(s), {nombre_echec} échec(s), "
            f"{nombre_ignore} sans téléphone de contact."
        ))
