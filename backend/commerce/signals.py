"""Journalisation automatique des écritures métier et des connexions."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from axes.signals import user_locked_out
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from rest_framework.exceptions import Throttled

from .audit import CHAMPS_AUDITES, _audit_active, enregistrer_evenement
from .models import Abonnement, Client, CorrectionDette, Dette, JournalAudit, Paiement, PaiementAbonnementHistorique, Produit, Vente

MODELES_AUDITES = (Produit, Client, Vente, Dette, CorrectionDette, Paiement, Abonnement, PaiementAbonnementHistorique)


def _valeur_json(valeur):
    if isinstance(valeur, (Decimal, UUID, date, datetime)):
        return str(valeur)
    return valeur


def _valeurs(instance):
    return {
        champ: _valeur_json(getattr(instance, champ))
        for champ in CHAMPS_AUDITES[instance.__class__.__name__]
    }


@receiver(pre_save)
def memoriser_etat_precedent(sender, instance, **kwargs):
    if not _audit_active.get() or sender not in MODELES_AUDITES or not instance.pk:
        return
    try:
        precedent = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._audit_precedent = None
    else:
        instance._audit_precedent = _valeurs(precedent)


@receiver(post_save)
def journaliser_ecriture(sender, instance, created, **kwargs):
    if not _audit_active.get() or sender not in MODELES_AUDITES:
        return
    commercant = getattr(instance, "commercant", None)
    if commercant is None:
        return

    anciennes = getattr(instance, "_audit_precedent", None)
    nouvelles_completes = _valeurs(instance)
    if sender in (Abonnement, PaiementAbonnementHistorique):
        action = JournalAudit.Action.CHANGEMENT_ABONNEMENT
    elif created:
        action = JournalAudit.Action.CREATION
    else:
        anciennes = anciennes or {}
        anciennes = {cle: val for cle, val in anciennes.items() if nouvelles_completes.get(cle) != val}
        if not anciennes:
            return
        action = JournalAudit.Action.MODIFICATION

    nouvelles = nouvelles_completes if created or action == JournalAudit.Action.CHANGEMENT_ABONNEMENT else {
        cle: nouvelles_completes[cle] for cle in anciennes
    }
    enregistrer_evenement(
        commercant=commercant, action=action, objet_type=sender.__name__, objet_id=instance.pk,
        anciennes_valeurs=anciennes or {}, nouvelles_valeurs=nouvelles,
    )

    if sender is Produit and not created:
        ancien_stock = (anciennes or {}).get("quantite_stock")
        nouveau_stock = nouvelles_completes["quantite_stock"]
        if ancien_stock != nouveau_stock:
            enregistrer_evenement(
                commercant=commercant,
                action=JournalAudit.Action.CHANGEMENT_STOCK,
                objet_type="Produit",
                objet_id=instance.pk,
                anciennes_valeurs={"quantite_stock": ancien_stock},
                nouvelles_valeurs={"quantite_stock": nouveau_stock},
            )


@receiver(pre_delete)
def journaliser_suppression(sender, instance, **kwargs):
    if not _audit_active.get() or sender not in MODELES_AUDITES:
        return
    commercant = getattr(instance, "commercant", None)
    if commercant is None:
        return
    action = (
        JournalAudit.Action.CHANGEMENT_ABONNEMENT
        if sender in (Abonnement, PaiementAbonnementHistorique)
        else JournalAudit.Action.SUPPRESSION
    )
    enregistrer_evenement(
        commercant=commercant, action=action, objet_type=sender.__name__, objet_id=instance.pk,
        anciennes_valeurs=_valeurs(instance),
    )


@receiver(user_locked_out)
def bloquer_connexion_dans_api(sender, request, **kwargs):
    """Axes émet ce signal au seuil configuré; DRF renvoie un message en français."""
    raise Throttled(
        detail="Trop de tentatives de connexion. Réessayez dans 15 minutes.", wait=15 * 60
    )
