"""Routes distinctes du back-office ; elles ne sont pas mêlées à l'espace commerçant."""

from django.urls import path

from .admin_api import (
    ActionUtilisateurBackOffice, AuditPlateformeBackOffice, ConfigurationOffreEssaiBackOffice,
    DecisionPaiementBackOffice, DetailSousAdminBackOffice,
    GestionSousAdminsBackOffice, ListeUtilisateursBackOffice,
    PaiementsEnAttenteBackOffice, PreuvePaiementBackOffice,
    StatistiquesPlateforme, connexion_backoffice,
)


urlpatterns = [
    path("auth/connexion/", connexion_backoffice, name="admin-connexion"),
    path("statistiques/", StatistiquesPlateforme.as_view(), name="admin-statistiques"),
    path("offre-essai/", ConfigurationOffreEssaiBackOffice.as_view(), name="admin-offre-essai"),
    path("utilisateurs/", ListeUtilisateursBackOffice.as_view(), name="admin-utilisateurs"),
    path("utilisateurs/<uuid:pk>/suspendre/", ActionUtilisateurBackOffice.as_view(), {"action": "suspendre"}, name="admin-utilisateur-suspendre"),
    path("utilisateurs/<uuid:pk>/reactiver/", ActionUtilisateurBackOffice.as_view(), {"action": "reactiver"}, name="admin-utilisateur-reactiver"),
    path("paiements-en-attente/", PaiementsEnAttenteBackOffice.as_view(), name="admin-paiements-en-attente"),
    path("paiements-en-attente/<int:pk>/preuve/", PreuvePaiementBackOffice.as_view(), name="admin-paiement-preuve"),
    path("paiements-en-attente/<int:pk>/valider/", DecisionPaiementBackOffice.as_view(), {"action": "valider"}, name="admin-paiement-valider"),
    path("paiements-en-attente/<int:pk>/rejeter/", DecisionPaiementBackOffice.as_view(), {"action": "rejeter"}, name="admin-paiement-rejeter"),
    path("audit/", AuditPlateformeBackOffice.as_view(), name="admin-audit"),
    path("sous-admins/", GestionSousAdminsBackOffice.as_view(), name="admin-sous-admins"),
    path("sous-admins/<uuid:pk>/", DetailSousAdminBackOffice.as_view(), name="admin-sous-admin-detail"),
]
