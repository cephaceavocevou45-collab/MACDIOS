"""Utilitaires communs qui empêchent d'enregistrer des champs sensibles."""

from contextvars import ContextVar
from contextlib import contextmanager

from config.observabilite import nettoyer_objet

from .models import JournalAudit

_contexte_requete = ContextVar("audit_contexte_requete", default=(None, None))
_audit_active = ContextVar("audit_active", default=True)

# Une liste explicite évite d'ajouter par mégarde un champ secret au journal.
CHAMPS_AUDITES = {
    "Produit": ("nom", "code_barres", "prix", "prix_achat", "quantite_stock", "seuil_alerte", "actif"),
    "Client": ("nom", "actif"),  # Le téléphone du client ne quitte jamais la table métier.
    "Vente": ("produit_id", "client_id", "quantite", "prix_unitaire", "total"),
    "Dette": ("client_id", "montant", "note"),
    "CorrectionDette": ("dette_id", "montant_precedent", "nouveau_montant", "raison"),
    "Paiement": ("client_id", "montant"),
    "Abonnement": ("plan_id", "statut", "date_debut", "date_fin"),
    "PaiementAbonnementHistorique": ("plan_id", "montant", "statut", "reference"),
    "Fournisseur": ("nom", "adresse", "actif"),
    "Approvisionnement": ("fournisseur_id", "reference", "note"),
    "LigneApprovisionnement": ("approvisionnement_id", "produit_id", "quantite", "prix_achat_unitaire"),
    "MouvementStock": ("produit_id", "type", "variation", "quantite_avant", "quantite_apres", "note"),
}


def definir_contexte_requete(utilisateur, adresse_ip):
    """Attache brièvement l'utilisateur et l'adresse réseau à la requête courante."""
    return _contexte_requete.set((utilisateur, adresse_ip))


def reinitialiser_contexte_requete(jeton):
    _contexte_requete.reset(jeton)


@contextmanager
def suspendre_audit():
    """Empêche les signaux de recréer des traces pendant l'effacement du compte."""
    jeton = _audit_active.set(False)
    try:
        yield
    finally:
        _audit_active.reset(jeton)


def enregistrer_evenement(
    *, commercant, action, objet_type, objet_id="", anciennes_valeurs=None,
    nouvelles_valeurs=None, utilisateur=None, adresse_ip=None,
):
    """Crée une ligne d'audit en ne conservant que les valeurs fournies et autorisées."""
    if not _audit_active.get():
        return None
    contexte_utilisateur, contexte_ip = _contexte_requete.get()
    utilisateur = utilisateur or contexte_utilisateur or commercant
    if utilisateur is not None and not getattr(utilisateur, "is_authenticated", False):
        utilisateur = None
    return JournalAudit.objects.create(
        commercant=commercant,
        utilisateur=utilisateur,
        action=action,
        objet_type=objet_type,
        objet_id=str(objet_id or ""),
        anciennes_valeurs=nettoyer_objet(anciennes_valeurs or {}),
        nouvelles_valeurs=nettoyer_objet(nouvelles_valeurs or {}),
        adresse_ip=adresse_ip or contexte_ip,
    )
