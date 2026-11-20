"""Schémas et exemples partagés pour la documentation OpenAPI."""

from drf_spectacular.utils import OpenApiExample, OpenApiResponse
from rest_framework import serializers


class ReponseDetailSerializer(serializers.Serializer):
    detail = serializers.CharField()


class InscriptionReponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    telephone = serializers.CharField(allow_blank=True)
    nom_boutique = serializers.CharField()


class ConnexionReponseSerializer(serializers.Serializer):
    detail = serializers.CharField(required=False)
    commercant = InscriptionReponseSerializer()


class ConnexionAdminReponseSerializer(serializers.Serializer):
    """Réponse publique du login admin, sans jeton dans le JSON."""

    administrateur = serializers.JSONField()


class OffreEssaiReponseSerializer(serializers.Serializer):
    actif = serializers.BooleanField()
    duree_jours = serializers.IntegerField()


class SanteReponseSerializer(serializers.Serializer):
    statut = serializers.CharField()
    base_de_donnees = serializers.CharField(required=False)
    detail = serializers.CharField(required=False)


class CsrfTokenReponseSerializer(serializers.Serializer):
    csrfToken = serializers.CharField()


class SessionReponseSerializer(serializers.Serializer):
    administrateur = serializers.JSONField(allow_null=True)
    commercant = serializers.JSONField(allow_null=True)


class ProfilReponseSerializer(serializers.Serializer):
    nom_affiche = serializers.CharField()
    email = serializers.EmailField()
    telephone = serializers.CharField(allow_blank=True)
    adresse = serializers.CharField(allow_blank=True)
    ville = serializers.CharField(allow_blank=True)
    logo_url = serializers.URLField(allow_null=True)


class ConfirmationSuppressionSerializer(serializers.Serializer):
    mot_de_passe = serializers.CharField(write_only=True)


class ReponseListePaginee(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = serializers.ListField(child=serializers.JSONField())


EXEMPLE_ERREUR = OpenApiResponse(
    response=ReponseDetailSerializer,
    description="Requête refusée ou données invalides.",
    examples=[OpenApiExample("Erreur", value={"detail": "Données invalides."})],
)

EXEMPLE_NON_AUTORISE = OpenApiResponse(
    response=ReponseDetailSerializer,
    description="Authentification requise ou abonnement expiré pour cette écriture.",
    examples=[OpenApiExample("Accès refusé", value={"detail": "Votre abonnement a expiré."})],
)

EXEMPLE_PRODUIT = OpenApiExample(
    "Produit courant",
    value={"id": 1, "nom": "Riz", "code_barres": "3760123456789", "prix": "1000.00", "prix_achat": "700.00", "quantite_stock": 18, "seuil_alerte": 5, "date_peremption": "2027-06-30", "date_creation": "2026-09-28T12:00:00Z"},
    response_only=True,
)
EXEMPLE_CLIENT = OpenApiExample(
    "Client avec solde",
    value={"id": 1, "nom": "Awa", "telephone": "22990000001", "solde": "3000.00"},
    response_only=True,
)
EXEMPLE_VENTE = OpenApiExample(
    "Vente enregistrée",
    value={"id": 42, "produit": 1, "client": 1, "quantite": 2, "prix_unitaire": "1000.00", "prix_achat_unitaire": "700.00", "benefice_brut": "600.00", "total": "2000.00", "date": "2026-09-28T12:00:00Z"},
    response_only=True,
)
