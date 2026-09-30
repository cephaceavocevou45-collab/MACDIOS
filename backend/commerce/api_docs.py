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
    access = serializers.CharField()
    refresh = serializers.CharField()
    commercant = InscriptionReponseSerializer()


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
    value={"id": 1, "nom": "Riz", "prix": "1000.00", "quantite_stock": 18, "seuil_alerte": 5, "date_creation": "2026-09-28T12:00:00Z"},
    response_only=True,
)
EXEMPLE_CLIENT = OpenApiExample(
    "Client avec solde",
    value={"id": 1, "nom": "Awa", "telephone": "22990000001", "solde": "3000.00"},
    response_only=True,
)
EXEMPLE_VENTE = OpenApiExample(
    "Vente enregistrée",
    value={"id": 42, "produit": 1, "client": 1, "quantite": 2, "prix_unitaire": "1000.00", "total": "2000.00", "date": "2026-09-28T12:00:00Z"},
    response_only=True,
)
