import math
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Abonnement, Client, ConfigurationEssai, CorrectionDette, DemandePaiementManuel, Dette, JournalAudit, Paiement, PaiementAbonnementHistorique, Plan, Produit, Vente
from .validators import valider_telephone_benin

Commercant = get_user_model()


class InscriptionSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    mot_de_passe = serializers.CharField(write_only=True, validators=[validate_password])
    accepte_conditions = serializers.BooleanField(write_only=True, required=True)

    class Meta:
        model = Commercant
        fields = ["id", "email", "telephone", "nom_boutique", "mot_de_passe", "accepte_conditions", "consentement_le"]
    read_only_fields = ["id", "consentement_le"]

    def validate_email(self, valeur):
        valeur = valeur.strip().lower()
        if Commercant.objects.filter(email__iexact=valeur).exists():
            raise serializers.ValidationError("Cette adresse email est déjà associée à un compte.")
        return valeur

    def validate_telephone(self, valeur):
        if not valeur:
            return ""
        try:
            valider_telephone_benin(valeur)
        except DjangoValidationError as erreur:
            raise serializers.ValidationError(erreur.messages) from erreur
        return valeur

    def validate_accepte_conditions(self, valeur):
        if not valeur:
            raise serializers.ValidationError("Vous devez accepter les conditions et la politique de confidentialité.")
        return valeur

    def create(self, validated_data):
        password = validated_data.pop("mot_de_passe")
        validated_data.pop("accepte_conditions")
        with transaction.atomic():
            commercant = Commercant.objects.create_user(
                password=password, consentement_le=timezone.now(), **validated_data
            )
            # Le plan d'essai est créé par la migration initiale. get() évite
            # de créer des variantes accidentelles à chaque inscription.
            configuration_essai = ConfigurationEssai.obtenir()
            plan_essai = Plan.objects.get(nom="Essai gratuit")
            debut = timezone.now()
            fin = debut + timedelta(days=configuration_essai.duree_jours) if configuration_essai.actif else debut
            Abonnement.objects.create(
                commercant=commercant,
                plan=plan_essai,
                statut=Abonnement.Statut.ESSAI if configuration_essai.actif else Abonnement.Statut.EXPIRE,
                date_debut=debut,
                date_fin=fin,
            )
        return commercant


class ConnexionSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    mot_de_passe = serializers.CharField(write_only=True)

    def validate_email(self, valeur):
        return valeur.strip().lower()

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            email=attrs["email"],
            password=attrs["mot_de_passe"],
        )
        if not user:
            raise serializers.ValidationError("Email ou mot de passe incorrect.")
        if not user.is_active:
            raise serializers.ValidationError("Ce compte est désactivé.")
        attrs["user"] = user
        return attrs


class ProduitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Produit
        fields = ["id", "nom", "prix", "quantite_stock", "seuil_alerte", "date_creation", "actif"]
        read_only_fields = ["id", "date_creation", "actif"]


class ClientSerializer(serializers.ModelSerializer):
    solde = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Client
        fields = ["id", "nom", "telephone", "solde", "actif"]
        read_only_fields = ["id", "solde", "actif"]


class VenteSerializer(serializers.ModelSerializer):
    produit = serializers.PrimaryKeyRelatedField(queryset=Produit.objects.none())
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.none(), required=False, allow_null=True)
    produit_nom = serializers.CharField(source="produit.nom", read_only=True)
    client_nom = serializers.CharField(source="client.nom", read_only=True, allow_null=True)

    class Meta:
        model = Vente
        fields = ["id", "produit", "produit_nom", "client", "client_nom", "quantite", "prix_unitaire", "total", "date"]
        read_only_fields = ["id", "prix_unitaire", "total", "date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["produit"].queryset = Produit.objects.filter(commercant=request.user, actif=True)
            self.fields["client"].queryset = Client.objects.filter(commercant=request.user, actif=True)

    @transaction.atomic
    def create(self, validated_data):
        commercant = self.context["request"].user
        produit = Produit.objects.select_for_update().get(
            pk=validated_data["produit"].pk, commercant=commercant
        )
        quantite = validated_data["quantite"]
        if produit.quantite_stock < quantite:
            raise serializers.ValidationError({"quantite": "Stock insuffisant pour cette vente."})
        client = validated_data.get("client")
        produit.quantite_stock -= quantite
        produit.save(update_fields=["quantite_stock"])
        prix_unitaire = produit.prix
        return Vente.objects.create(
            commercant=commercant,
            produit=produit,
            client=client,
            quantite=quantite,
            prix_unitaire=prix_unitaire,
            total=prix_unitaire * quantite,
        )


class CorrectionDetteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrectionDette
        fields = ["id", "montant_precedent", "nouveau_montant", "raison", "date"]
        read_only_fields = fields


class NouvelleCorrectionDetteSerializer(serializers.Serializer):
    nouveau_montant = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    raison = serializers.CharField(max_length=250, allow_blank=False, trim_whitespace=True)

    def validate_raison(self, valeur):
        if not valeur:
            raise serializers.ValidationError("La raison de la correction est obligatoire.")
        return valeur


class DemandeReinitialisationSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)

    def validate_email(self, valeur):
        return valeur.strip().lower()


class ReinitialisationMotDePasseSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=80)
    token = serializers.CharField(max_length=100)
    nouveau_mot_de_passe = serializers.CharField(write_only=True, min_length=12, max_length=128)


class DetteSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.none())
    corrections = CorrectionDetteSerializer(many=True, read_only=True)

    class Meta:
        model = Dette
        fields = ["id", "client", "montant", "note", "date", "corrections"]
        read_only_fields = ["id", "date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["client"].queryset = Client.objects.filter(commercant=request.user, actif=True)


class PaiementSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.none())

    class Meta:
        model = Paiement
        fields = ["id", "client", "montant", "date"]
        read_only_fields = ["id", "date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["client"].queryset = Client.objects.filter(commercant=request.user, actif=True)

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ["id", "nom", "prix", "duree_jours"]
        read_only_fields = fields


class AbonnementSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    jours_restants = serializers.SerializerMethodField()

    class Meta:
        model = Abonnement
        fields = ["statut", "plan", "date_debut", "date_fin", "jours_restants"]
        read_only_fields = fields

    @extend_schema_field(serializers.IntegerField())
    def get_jours_restants(self, abonnement):
        secondes = (abonnement.date_fin - timezone.now()).total_seconds()
        return max(0, math.ceil(secondes / 86400))


class PaiementAbonnementHistoriqueSerializer(serializers.ModelSerializer):
    plan_nom = serializers.CharField(source="plan.nom", read_only=True)

    class Meta:
        model = PaiementAbonnementHistorique
        fields = ["reference", "plan", "plan_nom", "montant", "statut", "date_creation", "date_validation"]
        read_only_fields = fields


class PreuveImageField(serializers.ImageField):
    """Applique la limite avant que Pillow ne tente de décoder le fichier."""

    def to_internal_value(self, data):
        if data is not None and getattr(data, "size", 0) > 5 * 1024 * 1024:
            raise serializers.ValidationError("La preuve ne doit pas dépasser 5 Mo.")
        return super().to_internal_value(data)


class DemandePaiementManuelSerializer(serializers.ModelSerializer):
    preuve = PreuveImageField(required=False, allow_null=True)

    plan_nom = serializers.CharField(source="plan.nom", read_only=True)
    operateur = serializers.ChoiceField(choices=DemandePaiementManuel.Operateur.choices, required=True)
    operateur_nom = serializers.SerializerMethodField()

    class Meta:
        model = DemandePaiementManuel
        fields = ["id", "plan", "plan_nom", "montant", "operateur", "operateur_nom", "reference_transaction", "preuve", "statut", "date_demande", "date_decision", "date_debut_abonnement", "date_fin_abonnement", "motif_rejet", "code_verification", "date_generation"]
        read_only_fields = ["id", "montant", "statut", "date_demande", "date_decision", "date_debut_abonnement", "date_fin_abonnement", "motif_rejet", "code_verification", "date_generation"]
        extra_kwargs = {"preuve": {"write_only": True, "required": False}}

    def validate_plan(self, plan):
        if not plan.actif or plan.prix <= 0:
            raise serializers.ValidationError("Cette formule n'est pas disponible.")
        return plan

    def validate_operateur(self, operateur):
        numeros = {
            DemandePaiementManuel.Operateur.MTN: settings.NUMERO_MTN,
            DemandePaiementManuel.Operateur.MOOV: settings.NUMERO_MOOV,
            DemandePaiementManuel.Operateur.CELTIIS: settings.NUMERO_CELTIIS,
        }
        if not numeros.get(operateur):
            raise serializers.ValidationError("Cet opérateur Mobile Money n'est pas disponible actuellement.")
        return operateur

    @extend_schema_field(serializers.CharField())
    def get_operateur_nom(self, demande):
        return demande.get_operateur_display() or "Opérateur non renseigné"

    def validate_preuve(self, fichier):
        if fichier is None:
            return fichier
        if fichier.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("La preuve ne doit pas dépasser 5 Mo.")
        try:
            from PIL import Image
            image = Image.open(fichier)
            image.verify()
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                raise serializers.ValidationError("Joignez une image JPEG, PNG ou WEBP.")
            fichier.seek(0)
        except (OSError, ValueError):
            raise serializers.ValidationError("Le fichier envoyé n'est pas une image valide.")
        return fichier


class JournalAuditSerializer(serializers.ModelSerializer):
    utilisateur_id = serializers.UUIDField(source="utilisateur.id", read_only=True, allow_null=True)

    class Meta:
        model = JournalAudit
        fields = [
            "id", "action", "objet_type", "objet_id", "anciennes_valeurs",
            "nouvelles_valeurs", "date", "adresse_ip", "utilisateur_id",
        ]
        read_only_fields = fields
