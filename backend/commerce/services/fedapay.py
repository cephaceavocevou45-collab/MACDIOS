"""Client minimal FedaPay et validation idempotente des paiements d'abonnement."""

from datetime import timedelta
from decimal import Decimal, InvalidOperation
import logging

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException

from commerce.audit import enregistrer_evenement
from commerce.models import Abonnement, JournalAudit, PaiementAbonnementHistorique

logger = logging.getLogger(__name__)


class FedaPayErreur(APIException):
    status_code = 502
    default_detail = "Le service de paiement est temporairement indisponible. Réessayez plus tard."
    default_code = "fedapay_indisponible"


def _base_url():
    return "https://api.fedapay.com/v1" if settings.FEDAPAY_ENVIRONMENT == "live" else "https://sandbox-api.fedapay.com/v1"


def _requete(method, path, *, payload=None):
    if not settings.FEDAPAY_SECRET_KEY:
        raise APIException("Le paiement FedaPay n'est pas configuré sur le serveur.")
    try:
        reponse = requests.request(
            method, f"{_base_url()}{path}", json=payload,
            headers={"Authorization": f"Bearer {settings.FEDAPAY_SECRET_KEY}", "Content-Type": "application/json"},
            timeout=(5, 20),
        )
        reponse.raise_for_status()
        return reponse.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Échec de requête FedaPay (%s %s): %s", method, path, exc.__class__.__name__)
        raise FedaPayErreur() from exc


def _data(reponse):
    return reponse.get("v1/transaction", reponse.get("transaction", reponse.get("data", reponse)))


def creer_paiement(paiement):
    user = paiement.commercant
    # Le numéro du compte est facultatif dans le profil. Ne pas en fabriquer un.
    telephone = (user.telephone or "").strip()
    customer = {"email": user.email, "firstname": user.nom_boutique[:60], "lastname": "Commerçant"}
    if telephone:
        customer["phone_number"] = {"number": telephone, "country": "bj"}
    transaction_data = _data(_requete("POST", "/transactions", payload={"transaction": {
        "description": f"Abonnement {paiement.plan.nom}", "amount": int(paiement.montant),
        "currency": {"iso": "XOF"}, "callback_url": f"{settings.PUBLIC_FRONTEND_URL.rstrip('/')}/abonnement?paiement={paiement.reference}",
        "custom_metadata": {"reference_abonnement": str(paiement.reference)}, "customer": customer,
    }}))
    identifiant = transaction_data.get("id")
    if not identifiant:
        raise FedaPayErreur()
    paiement.fedapay_transaction_id = str(identifiant)
    paiement.save(update_fields=["fedapay_transaction_id"])
    token = _requete("POST", f"/transactions/{identifiant}/token", payload={})
    token_data = _data(token)
    url = token_data.get("url") or token_data.get("token_url") or token_data.get("payment_url")
    if not url or not str(url).startswith("https://"):
        raise FedaPayErreur()
    return url


@transaction.atomic
def synchroniser_paiement(paiement, donnees_fedapay):
    paiement = PaiementAbonnementHistorique.objects.select_for_update().select_related("plan", "commercant").get(pk=paiement.pk)
    # Réconcilier identité, référence et montant depuis la source FedaPay avant toute activation.
    metadata = donnees_fedapay.get("custom_metadata") or donnees_fedapay.get("metadata") or {}
    reference = metadata.get("reference_abonnement")
    try:
        montant = Decimal(str(donnees_fedapay.get("amount")))
    except (InvalidOperation, TypeError):
        return paiement
    fid = str(donnees_fedapay.get("id", ""))
    currency = donnees_fedapay.get("currency") or {}
    iso = currency.get("iso") if isinstance(currency, dict) else None
    if fid != paiement.fedapay_transaction_id or reference != str(paiement.reference) or montant != paiement.montant or (iso and iso != "XOF"):
        logger.warning("Transaction FedaPay incohérente pour le paiement local %s", paiement.reference)
        return paiement
    etat = str(donnees_fedapay.get("status", "")).lower()
    if etat == "approved" and paiement.statut != PaiementAbonnementHistorique.Statut.REUSSI:
        abonnement = Abonnement.objects.select_for_update().get(commercant=paiement.commercant)
        maintenant = timezone.now()
        debut = max(maintenant, abonnement.date_fin)
        abonnement.plan = paiement.plan
        abonnement.statut = Abonnement.Statut.ACTIF
        abonnement.date_debut = debut
        abonnement.date_fin = debut + timedelta(days=paiement.plan.duree_jours)
        abonnement.save(update_fields=["plan", "statut", "date_debut", "date_fin"])
        paiement.statut = PaiementAbonnementHistorique.Statut.REUSSI
        paiement.date_validation = maintenant
        paiement.save(update_fields=["statut", "date_validation"])
        enregistrer_evenement(
            commercant=paiement.commercant, utilisateur=paiement.commercant,
            action=JournalAudit.Action.CHANGEMENT_ABONNEMENT,
            objet_type="PaiementAbonnementHistorique", objet_id=paiement.pk,
            nouvelles_valeurs={"decision": "paiement_fedapay_verifie", "plan_id": paiement.plan_id,
                               "reference": str(paiement.reference), "date_fin": abonnement.date_fin.isoformat()},
        )
    elif etat in {"declined", "canceled", "cancelled"} and paiement.statut == PaiementAbonnementHistorique.Statut.EN_ATTENTE:
        paiement.statut = PaiementAbonnementHistorique.Statut.ECHOUE
        paiement.save(update_fields=["statut"])
    return paiement


def actualiser_paiement(paiement):
    if not paiement.fedapay_transaction_id:
        return paiement
    reponse = _requete("GET", f"/transactions/{paiement.fedapay_transaction_id}")
    return synchroniser_paiement(paiement, _data(reponse))
