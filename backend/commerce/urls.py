from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    ApprovisionnementViewSet, ClientViewSet, DetteViewSet, FournisseurViewSet, MouvementStockViewSet, PaiementViewSet, ProduitViewSet, VenteViewSet,
    RafraichirJetonView, abonnement_actuel, connexion, dashboard, historique_abonnement, inscription,
    plans, VueJournalAudit, export_compte,
    supprimer_compte, sante, mot_de_passe_oublie, reinitialiser_mot_de_passe,
    verifier_document, document_verification_pdf, demandes_paiement_abonnement, preuve_demande_abonnement,
    recu_abonnement_manuel, offre_essai, jeton_csrf, session_authentifiee, deconnexion,
    profil_courant, supprimer_logo_profil_courant,
)
from .maintenance_api import MaintenanceDeploiement, statut_maintenance, version_deployee

router = DefaultRouter()
router.register("produits", ProduitViewSet, basename="produit")
router.register("fournisseurs", FournisseurViewSet, basename="fournisseur")
router.register("approvisionnements", ApprovisionnementViewSet, basename="approvisionnement")
router.register("mouvements-stock", MouvementStockViewSet, basename="mouvement-stock")
router.register("clients", ClientViewSet, basename="client")
router.register("ventes", VenteViewSet, basename="vente")
router.register("dettes", DetteViewSet, basename="dette")
router.register("paiements", PaiementViewSet, basename="paiement")

urlpatterns = [
    path("auth/inscription/", inscription, name="inscription"),
    path("auth/connexion/", connexion, name="connexion"),
    path("auth/csrf/", jeton_csrf, name="csrf"),
    path("auth/session/", session_authentifiee, name="session-authentifiee"),
    path("auth/deconnexion/", deconnexion, name="deconnexion"),
    path("auth/refresh/", RafraichirJetonView.as_view(), name="refresh"),
    path("maintenance/", statut_maintenance, name="statut-maintenance"),
    path("deploiement/maintenance/", MaintenanceDeploiement.as_view(), name="maintenance-deploiement"),
    path("version/", version_deployee, name="version-deployee"),
    path("auth/mot-de-passe/oublie/", mot_de_passe_oublie, name="mot-de-passe-oublie"),
    path("auth/mot-de-passe/reinitialiser/", reinitialiser_mot_de_passe, name="mot-de-passe-reinitialiser"),
    path("profil/", profil_courant, name="profil-courant"),
    path("profil/photo/", supprimer_logo_profil_courant, name="profil-photo-suppression"),
    path("sante/", sante, name="sante"),
    path("verifier/<str:code>/", verifier_document, name="verifier-document"),
    path("verifier/<str:code>/recu/", document_verification_pdf, name="verifier-document-pdf"),
    path("audit/", VueJournalAudit.as_view(), name="audit"),
    path("compte/export/", export_compte, name="compte-export"),
    path("compte/", supprimer_compte, name="compte-suppression"),
    path("dashboard/", dashboard, name="dashboard"),
    path("plans/", plans, name="plans"),
    path("offre-essai/", offre_essai, name="offre-essai"),
    path("abonnement/", abonnement_actuel, name="abonnement"),
    path("abonnement/transactions/", historique_abonnement, name="abonnement-transactions"),
    path("abonnement/demandes/", demandes_paiement_abonnement, name="abonnement-demandes"),
    path("abonnement/demandes/<int:pk>/preuve/", preuve_demande_abonnement, name="abonnement-demande-preuve"),
    path("abonnement/demandes/<int:pk>/recu/", recu_abonnement_manuel, name="abonnement-demande-recu"),
    path("", include(router.urls)),
]
