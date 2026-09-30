"""Sérialise les données strictement nécessaires au back-office."""

from rest_framework import serializers
from django.utils import timezone

from .models import Commercant, ConfigurationEssai, DemandePaiementManuel, JournalAudit, ProfilSousAdmin


class ConfigurationEssaiSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigurationEssai
        fields = ["actif", "duree_jours", "modifie_le"]
        read_only_fields = ["modifie_le"]

    def validate_duree_jours(self, valeur):
        if not 1 <= valeur <= 365:
            raise serializers.ValidationError("La durée doit être comprise entre 1 et 365 jours.")
        return valeur


class SousAdminCreationSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    nom = serializers.CharField(max_length=120, trim_whitespace=True)
    permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=ProfilSousAdmin.PERMISSIONS),
        allow_empty=True,
    )

    def validate_email(self, valeur):
        return valeur.strip().lower()

    def validate_permissions(self, valeurs):
        if len(set(valeurs)) != len(valeurs):
            raise serializers.ValidationError("Une permission ne peut être cochée qu'une fois.")
        return valeurs


class SousAdminModificationSerializer(serializers.Serializer):
    permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=ProfilSousAdmin.PERMISSIONS),
        required=False,
        allow_empty=True,
    )
    actif = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Indiquez les permissions ou l'état du compte à modifier.")
        return attrs


class SousAdminSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="utilisateur_id", read_only=True)
    email = serializers.EmailField(source="utilisateur.email", read_only=True)
    actif = serializers.BooleanField(source="utilisateur.is_active", read_only=True)
    cree_par_email = serializers.EmailField(source="cree_par.email", read_only=True, allow_null=True)

    class Meta:
        model = ProfilSousAdmin
        fields = ["id", "email", "nom", "permissions", "actif", "cree_par_email", "date_creation", "date_modification"]
        read_only_fields = fields


class UtilisateurBackOfficeSerializer(serializers.ModelSerializer):
    statut_abonnement = serializers.SerializerMethodField()
    date_fin_abonnement = serializers.SerializerMethodField()

    class Meta:
        model = Commercant
        fields = ["id", "email", "nom_boutique", "is_active", "motif_suspension", "suspendu_le", "statut_abonnement", "date_fin_abonnement", "date_joined"]
        read_only_fields = fields

    def get_statut_abonnement(self, utilisateur):
        abonnement = getattr(utilisateur, "abonnement", None)
        if abonnement is None:
            return None
        if abonnement.date_fin <= timezone.now():
            return "expire"
        return abonnement.statut

    def get_date_fin_abonnement(self, utilisateur):
        abonnement = getattr(utilisateur, "abonnement", None)
        return abonnement.date_fin if abonnement else None


class DemandePaiementAdminSerializer(serializers.ModelSerializer):
    commercant_email = serializers.EmailField(source="commercant.email", read_only=True)
    nom_boutique = serializers.CharField(source="commercant.nom_boutique", read_only=True)
    plan_nom = serializers.CharField(source="plan.nom", read_only=True)
    operateur_nom = serializers.CharField(source="get_operateur_display", read_only=True)
    preuve_disponible = serializers.SerializerMethodField()

    class Meta:
        model = DemandePaiementManuel
        fields = ["id", "commercant_email", "nom_boutique", "plan", "plan_nom", "montant", "operateur", "operateur_nom", "reference_transaction", "preuve_disponible", "statut", "date_demande", "date_decision", "motif_rejet"]
        read_only_fields = fields

    def get_preuve_disponible(self, demande):
        return bool(demande.preuve)


class MotifRejetAdminSerializer(serializers.Serializer):
    motif = serializers.CharField(max_length=250, trim_whitespace=True)

    def validate_motif(self, valeur):
        if not valeur:
            raise serializers.ValidationError("Le motif du rejet est obligatoire.")
        return valeur


class AuditPlateformeSerializer(serializers.ModelSerializer):
    commercant_email = serializers.EmailField(source="commercant.email", read_only=True, allow_null=True)
    admin_responsable = serializers.EmailField(source="utilisateur.email", read_only=True, allow_null=True)

    class Meta:
        model = JournalAudit
        fields = ["id", "commercant_email", "admin_responsable", "action", "objet_type", "objet_id", "anciennes_valeurs", "nouvelles_valeurs", "date", "adresse_ip"]
        read_only_fields = fields
