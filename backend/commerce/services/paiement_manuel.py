"""Opérations atomiques réservées aux décisions d'administration."""

from datetime import timedelta
import uuid

from django.db import transaction
from django.utils.html import escape
from django.utils import timezone

from commerce.audit import enregistrer_evenement
from commerce.models import Abonnement, DemandePaiementManuel, Dette, JournalAudit
from notifications.email import ErreurEnvoiEmail, envoyer_email


def _nouveau_code_verification():
    """Évite aussi une collision avec les codes des reçus de dettes."""
    while True:
        code = uuid.uuid4()
        if not Dette.objects.filter(code_verification=code).exists() and not DemandePaiementManuel.objects.filter(code_verification=code).exists():
            return code


@transaction.atomic
def valider_demande(demande_id, administrateur):
    demande = DemandePaiementManuel.objects.select_for_update().select_related("plan", "commercant").get(pk=demande_id)
    if demande.statut != DemandePaiementManuel.Statut.EN_ATTENTE:
        return demande, False

    abonnement = Abonnement.objects.select_for_update().get(commercant=demande.commercant)
    maintenant = timezone.now()
    debut = max(maintenant, abonnement.date_fin)
    fin = debut + timedelta(days=demande.plan.duree_jours)
    abonnement.plan = demande.plan
    abonnement.statut = Abonnement.Statut.ACTIF
    abonnement.date_debut = debut
    abonnement.date_fin = fin
    abonnement.save(update_fields=["plan", "statut", "date_debut", "date_fin"])

    demande.statut = DemandePaiementManuel.Statut.VALIDEE
    demande.traitee_par = administrateur
    demande.date_decision = maintenant
    demande.date_debut_abonnement = debut
    demande.date_fin_abonnement = fin
    demande.code_verification = _nouveau_code_verification()
    demande.date_generation = maintenant
    demande.save(update_fields=["statut", "traitee_par", "date_decision", "date_debut_abonnement", "date_fin_abonnement", "code_verification", "date_generation"])
    enregistrer_evenement(
        commercant=demande.commercant,
        utilisateur=administrateur,
        action=JournalAudit.Action.VALIDATION_PAIEMENT_ADMIN,
        objet_type="DemandePaiementManuel",
        objet_id=demande.pk,
        nouvelles_valeurs={"decision": "validee", "plan_id": demande.plan_id, "date_debut": debut.isoformat(), "date_fin": fin.isoformat()},
    )
    transaction.on_commit(lambda: _email_validation(demande))
    return demande, True


def _email_validation(demande):
    try:
        envoyer_email(
            demande.commercant.email,
            "Paiement d'abonnement vérifié",
            f"<div style='font-family:Arial,sans-serif;color:#243b36'><h1>Paiement vérifié</h1><p>Bonjour {escape(demande.commercant.nom_boutique)}, votre abonnement {escape(demande.plan.nom)} est actif jusqu'au {demande.date_fin_abonnement:%d/%m/%Y}.</p></div>",
        )
    except (ErreurEnvoiEmail, ValueError):
        # La décision d'abonnement reste enregistrée même si le fournisseur email est indisponible.
        pass


@transaction.atomic
def rejeter_demande(demande_id, administrateur, motif):
    motif = (motif or "").strip()
    if not motif:
        raise ValueError("Un motif de rejet est obligatoire.")
    demande = DemandePaiementManuel.objects.select_for_update().select_related("plan", "commercant").get(pk=demande_id)
    if demande.statut != DemandePaiementManuel.Statut.EN_ATTENTE:
        return demande, False
    demande.statut = DemandePaiementManuel.Statut.REJETEE
    demande.traitee_par = administrateur
    demande.date_decision = timezone.now()
    demande.motif_rejet = motif
    demande.save(update_fields=["statut", "traitee_par", "date_decision", "motif_rejet"])
    enregistrer_evenement(
        commercant=demande.commercant,
        utilisateur=administrateur,
        action=JournalAudit.Action.REJET_PAIEMENT_ADMIN,
        objet_type="DemandePaiementManuel",
        objet_id=demande.pk,
        nouvelles_valeurs={"decision": "rejetee", "motif": demande.motif_rejet},
    )
    transaction.on_commit(lambda: _email_rejet(demande))
    return demande, True


def _email_rejet(demande):
    try:
        envoyer_email(
            demande.commercant.email,
            "Votre demande de paiement doit être vérifiée",
            f"<div style='font-family:Arial,sans-serif;color:#243b36'><h1>Demande non validée</h1><p>Bonjour {escape(demande.commercant.nom_boutique)}, votre demande du {demande.date_demande:%d/%m/%Y} n'a pas été validée.</p><p>Motif : {escape(demande.motif_rejet)}</p><p>Vérifiez la référence de votre transfert puis soumettez une nouvelle demande.</p></div>",
        )
    except (ErreurEnvoiEmail, ValueError):
        pass
