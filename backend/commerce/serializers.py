import math
import logging
from datetime import timedelta
from decimal import Decimal
import io
import warnings

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from PIL import Image
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Abonnement, Approvisionnement, Client, ConfigurationEssai, CorrectionDette, DemandePaiementManuel, Dette, Fournisseur, JournalAudit, LigneApprovisionnement, MouvementStock, Paiement, PaiementAbonnementHistorique, Plan, Produit, Vente
from .validators import normaliser_telephone_international
from .services.profil_image import ImageProfilInvalide, nettoyer_image_profil, url_logo_profil

Commercant = get_user_model()
logger = logging.getLogger(__name__)


class ImageProfilField(serializers.FileField):
    """Réencode l'image envoyée avant de la confier au stockage Cloudinary."""

    def to_internal_value(self, data):
        fichier = super().to_internal_value(data)
        try:
            return nettoyer_image_profil(fichier)
        except ImageProfilInvalide as erreur:
            raise serializers.ValidationError(str(erreur)) from erreur


class NomAfficheField(serializers.CharField):
    """Lit le nom de boutique ou celui du sous-admin depuis son profil existant."""

    def get_attribute(self, utilisateur):
        profil = getattr(utilisateur, "profil_sous_admin", None)
        return profil.nom if utilisateur.is_staff and profil else utilisateur.nom_boutique


class ProfilSerializer(serializers.Serializer):
    """Profil de l'utilisateur authentifié, quel que soit son rôle."""

    nom_affiche = NomAfficheField(max_length=120, required=False, trim_whitespace=True)
    email = serializers.EmailField(read_only=True, allow_null=True)
    telephone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    adresse = serializers.CharField(max_length=200, required=False, allow_blank=True, trim_whitespace=True)
    ville = serializers.CharField(max_length=120, required=False, allow_blank=True, trim_whitespace=True)
    logo = ImageProfilField(required=False, allow_empty_file=False, write_only=True)
    logo_url = serializers.SerializerMethodField()

    def get_nom_affiche(self, utilisateur):
        profil = getattr(utilisateur, "profil_sous_admin", None)
        if utilisateur.is_staff and profil:
            return profil.nom
        return utilisateur.nom_boutique

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_logo_url(self, utilisateur):
        url = url_logo_profil(utilisateur)
        requete = self.context.get("request")
        if url and settings.LOGO_LOCAL_DEVELOPPEMENT and requete:
            return requete.build_absolute_uri(url)
        return url

    def to_representation(self, utilisateur):
        representation = super().to_representation(utilisateur)
        representation["nom_affiche"] = self.get_nom_affiche(utilisateur)
        return representation

    def validate_telephone(self, valeur):
        if not valeur:
            if self.instance and not self.instance.email:
                raise serializers.ValidationError("Un numéro de téléphone est nécessaire pour vous connecter.")
            return ""
        try:
            numero = normaliser_telephone_international(valeur)
        except DjangoValidationError as erreur:
            raise serializers.ValidationError(erreur.messages) from erreur
        doublons = Commercant.objects.filter(telephone=numero)
        if self.instance:
            doublons = doublons.exclude(pk=self.instance.pk)
        if doublons.exists():
            raise serializers.ValidationError("Ce numéro est déjà associé à un autre compte.")
        return numero

    def update(self, utilisateur, donnees):
        logo_precedent = utilisateur.logo_profil.name if utilisateur.logo_profil else ""
        profil_sous_admin = getattr(utilisateur, "profil_sous_admin", None)
        champs_utilisateur = []

        nom_affiche = donnees.pop("nom_affiche", None)
        if nom_affiche is not None:
            if utilisateur.is_staff and profil_sous_admin:
                profil_sous_admin.nom = nom_affiche
                profil_sous_admin.save(update_fields=["nom"])
            else:
                utilisateur.nom_boutique = nom_affiche
                champs_utilisateur.append("nom_boutique")

        for champ in ("telephone", "adresse", "ville", "logo_profil"):
            cle = "logo" if champ == "logo_profil" else champ
            if cle in donnees:
                setattr(utilisateur, champ, donnees.pop(cle))
                champs_utilisateur.append(champ)

        if champs_utilisateur:
            utilisateur.save(update_fields=champs_utilisateur)

        nouveau_logo = utilisateur.logo_profil.name if utilisateur.logo_profil else ""
        if logo_precedent and logo_precedent != nouveau_logo:
            from .services.profil_image import invalider_cache_logo_profil

            try:
                suppression_reussie = utilisateur.logo_profil.storage.delete(logo_precedent)
                if suppression_reussie is False:
                    logger.warning("Cloudinary n'a pas confirmé la suppression de l'ancien logo.")
            except Exception:
                # La mise à jour du profil reste utilisable ; l'échec de nettoyage est journalisé.
                logger.warning("Échec de suppression d'un ancien logo Cloudinary.")
            invalider_cache_logo_profil()
        return utilisateur


class InscriptionSerializer(serializers.ModelSerializer):
    telephone = serializers.CharField(max_length=20, required=True, allow_blank=False)
    mot_de_passe = serializers.CharField(write_only=True, max_length=128)
    confirmation_mot_de_passe = serializers.CharField(write_only=True, max_length=128)
    accepte_conditions = serializers.BooleanField(write_only=True, required=True)

    class Meta:
        model = Commercant
        fields = ["id", "telephone", "nom_boutique", "mot_de_passe", "confirmation_mot_de_passe", "accepte_conditions", "consentement_le"]
    read_only_fields = ["id", "consentement_le"]

    def validate_telephone(self, valeur):
        try:
            numero = normaliser_telephone_international(valeur)
        except DjangoValidationError as erreur:
            raise serializers.ValidationError(erreur.messages) from erreur
        if Commercant.objects.filter(telephone=numero).exists():
            raise serializers.ValidationError("Ce numéro est déjà associé à un compte.")
        return numero

    def validate(self, attrs):
        if attrs["mot_de_passe"] != attrs["confirmation_mot_de_passe"]:
            raise serializers.ValidationError({"confirmation_mot_de_passe": "Les mots de passe ne correspondent pas."})
        utilisateur = Commercant(
            telephone=attrs["telephone"], nom_boutique=attrs["nom_boutique"],
        )
        try:
            validate_password(attrs["mot_de_passe"], user=utilisateur)
        except DjangoValidationError as erreur:
            raise serializers.ValidationError({"mot_de_passe": erreur.messages}) from erreur
        return attrs

    def validate_accepte_conditions(self, valeur):
        if not valeur:
            raise serializers.ValidationError("Vous devez accepter les conditions et la politique de confidentialité.")
        return valeur

    def create(self, validated_data):
        password = validated_data.pop("mot_de_passe")
        validated_data.pop("confirmation_mot_de_passe")
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
    telephone = serializers.CharField(max_length=20, required=False, allow_blank=False)
    email = serializers.EmailField(max_length=254, required=False)
    mot_de_passe = serializers.CharField(write_only=True)

    def validate_telephone(self, valeur):
        try:
            return normaliser_telephone_international(valeur)
        except DjangoValidationError as erreur:
            raise serializers.ValidationError(erreur.messages) from erreur

    def validate_email(self, valeur):
        return valeur.strip().lower()

    def validate(self, attrs):
        telephone = attrs.get("telephone")
        email = attrs.get("email")
        if bool(telephone) == bool(email):
            raise serializers.ValidationError("Saisissez un numéro de téléphone ou l’email d’un ancien compte.")
        identifiant = telephone or email
        user = authenticate(
            request=self.context.get("request"),
            username=identifiant,
            password=attrs["mot_de_passe"],
        )
        if not user:
            raise serializers.ValidationError("Numéro ou mot de passe incorrect.")
        if not user.is_active:
            raise serializers.ValidationError("Ce compte est désactivé.")
        attrs["user"] = user
        return attrs


class ProduitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Produit
        fields = ["id", "nom", "code_barres", "prix", "prix_achat", "quantite_stock", "seuil_alerte", "date_peremption", "date_creation", "actif"]
        read_only_fields = ["id", "date_creation", "actif"]

    def validate_code_barres(self, valeur):
        valeur = valeur.strip()
        if not valeur:
            return ""
        commercant = self.context["request"].user
        doublons = Produit.objects.filter(commercant=commercant, code_barres__iexact=valeur)
        if self.instance:
            doublons = doublons.exclude(pk=self.instance.pk)
        if doublons.exists():
            raise serializers.ValidationError("Ce code-barres est déjà utilisé par un autre produit de votre boutique.")
        return valeur

    @transaction.atomic
    def create(self, validated_data):
        produit = super().create(validated_data)
        if produit.quantite_stock:
            MouvementStock.objects.create(
                commercant=produit.commercant, produit=produit,
                type=MouvementStock.Type.INITIAL, variation=produit.quantite_stock,
                quantite_avant=0, quantite_apres=produit.quantite_stock,
                note="Stock initial saisi à la création du produit.",
                utilisateur=self.context.get("request").user if self.context.get("request") else None,
            )
        return produit

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get("request")
        commercant = request.user if request and request.user.is_authenticated else instance.commercant
        produit = Produit.objects.select_for_update().get(pk=instance.pk, commercant=commercant)
        stock_avant = produit.quantite_stock
        produit = super().update(produit, validated_data)
        if produit.quantite_stock != stock_avant:
            MouvementStock.objects.create(
                commercant=commercant, produit=produit,
                type=MouvementStock.Type.AJUSTEMENT,
                variation=produit.quantite_stock - stock_avant,
                quantite_avant=stock_avant, quantite_apres=produit.quantite_stock,
                note="Ajustement effectué depuis la fiche produit.",
                utilisateur=request.user if request and request.user.is_authenticated else None,
            )
        return produit


class AjustementStockSerializer(serializers.Serializer):
    variation = serializers.IntegerField(min_value=-1_000_000, max_value=1_000_000)
    note = serializers.CharField(max_length=250, allow_blank=False, trim_whitespace=True)

    def validate_variation(self, valeur):
        if valeur == 0:
            raise serializers.ValidationError("La variation du stock ne peut pas être nulle.")
        return valeur


class FournisseurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fournisseur
        fields = ["id", "nom", "telephone", "email", "adresse", "actif", "date_creation"]
        read_only_fields = ["id", "actif", "date_creation"]


class LigneApprovisionnementLectureSerializer(serializers.ModelSerializer):
    produit_nom = serializers.CharField(source="produit.nom", read_only=True)
    total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = LigneApprovisionnement
        fields = ["id", "produit", "produit_nom", "quantite", "prix_achat_unitaire", "total"]
        read_only_fields = fields


class LigneApprovisionnementEcritureSerializer(serializers.Serializer):
    produit = serializers.PrimaryKeyRelatedField(queryset=Produit.objects.none())
    quantite = serializers.IntegerField(min_value=1, max_value=1_000_000)
    prix_achat_unitaire = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))


class ApprovisionnementSerializer(serializers.ModelSerializer):
    fournisseur = serializers.PrimaryKeyRelatedField(queryset=Fournisseur.objects.none(), required=False, allow_null=True)
    fournisseur_nom = serializers.CharField(source="fournisseur.nom", read_only=True, allow_null=True)
    lignes = LigneApprovisionnementEcritureSerializer(many=True, write_only=True, allow_empty=False)
    details = LigneApprovisionnementLectureSerializer(source="lignes", many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Approvisionnement
        fields = ["id", "fournisseur", "fournisseur_nom", "reference", "note", "date_reception", "lignes", "details", "total"]
        read_only_fields = ["id", "date_reception", "details", "total"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["fournisseur"].queryset = Fournisseur.objects.filter(commercant=request.user, actif=True)
            # Le serializer enfant d'une liste ne reçoit pas toujours le contexte
            # à son initialisation. Le queryset est donc limité ici, côté parent.
            self.fields["lignes"].child.fields["produit"].queryset = Produit.objects.filter(
                commercant=request.user, actif=True
            )

    @extend_schema_field(serializers.DecimalField(max_digits=14, decimal_places=2))
    def get_total(self, approvisionnement):
        return sum((ligne.total for ligne in approvisionnement.lignes.all()), Decimal("0"))

    def validate_lignes(self, lignes):
        produits = [ligne["produit"].pk for ligne in lignes]
        if len(produits) != len(set(produits)):
            raise serializers.ValidationError("Un produit ne peut apparaître qu'une fois dans le même approvisionnement.")
        return lignes

    @transaction.atomic
    def create(self, validated_data):
        lignes = validated_data.pop("lignes")
        commercant = self.context["request"].user
        approvisionnement = Approvisionnement.objects.create(commercant=commercant, **validated_data)
        ids = sorted(ligne["produit"].pk for ligne in lignes)
        produits = {
            produit.pk: produit for produit in Produit.objects.select_for_update().filter(
                commercant=commercant, actif=True, pk__in=ids
            ).order_by("pk")
        }
        if len(produits) != len(ids):
            raise serializers.ValidationError({"lignes": "Un produit n'appartient plus à cette boutique ou est archivé."})

        for donnees in lignes:
            produit = produits[donnees["produit"].pk]
            avant = produit.quantite_stock
            quantite = donnees["quantite"]
            cout = donnees["prix_achat_unitaire"]
            produit.quantite_stock += quantite
            produit.prix_achat = cout
            produit.save(update_fields=["quantite_stock", "prix_achat"])
            ligne = LigneApprovisionnement.objects.create(
                approvisionnement=approvisionnement, produit=produit,
                quantite=quantite, prix_achat_unitaire=cout,
            )
            MouvementStock.objects.create(
                commercant=commercant, produit=produit, type=MouvementStock.Type.ACHAT,
                variation=quantite, quantite_avant=avant, quantite_apres=produit.quantite_stock,
                note=f"Réception {approvisionnement.reference}".strip(),
                ligne_approvisionnement=ligne, utilisateur=commercant,
            )
        return approvisionnement


class MouvementStockSerializer(serializers.ModelSerializer):
    produit_nom = serializers.CharField(source="produit.nom", read_only=True)
    utilisateur_email = serializers.EmailField(source="utilisateur.email", read_only=True, allow_null=True)
    type_libelle = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = MouvementStock
        fields = ["id", "produit", "produit_nom", "type", "type_libelle", "variation", "quantite_avant", "quantite_apres", "note", "utilisateur_email", "date"]
        read_only_fields = fields


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
    benefice_brut = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True, allow_null=True)

    class Meta:
        model = Vente
        fields = ["id", "produit", "produit_nom", "client", "client_nom", "quantite", "prix_unitaire", "prix_achat_unitaire", "benefice_brut", "total", "date"]
        read_only_fields = ["id", "prix_unitaire", "prix_achat_unitaire", "benefice_brut", "total", "date"]

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
        stock_avant = produit.quantite_stock
        produit.quantite_stock -= quantite
        produit.save(update_fields=["quantite_stock"])
        prix_unitaire = produit.prix
        vente = Vente.objects.create(
            commercant=commercant,
            produit=produit,
            client=client,
            quantite=quantite,
            prix_unitaire=prix_unitaire,
            prix_achat_unitaire=produit.prix_achat,
            total=prix_unitaire * quantite,
        )
        MouvementStock.objects.create(
            commercant=commercant, produit=produit, type=MouvementStock.Type.VENTE,
            variation=-quantite, quantite_avant=stock_avant, quantite_apres=produit.quantite_stock,
            note=f"Vente {vente.pk}", vente=vente, utilisateur=commercant,
        )
        return vente


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
    telephone = serializers.CharField(max_length=20, required=False, allow_blank=False)
    email = serializers.EmailField(max_length=254, required=False)

    def validate_telephone(self, valeur):
        try:
            return normaliser_telephone_international(valeur)
        except DjangoValidationError as erreur:
            raise serializers.ValidationError(erreur.messages) from erreur

    def validate_email(self, valeur):
        return valeur.strip().lower()

    def validate(self, attrs):
        if bool(attrs.get("telephone")) == bool(attrs.get("email")):
            raise serializers.ValidationError("Saisissez votre numéro ou l’email d’un ancien compte.")
        return attrs


class ReinitialisationMotDePasseSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=80)
    token = serializers.CharField(max_length=100)
    nouveau_mot_de_passe = serializers.CharField(write_only=True, min_length=8, max_length=128)


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
        fields = ["reference", "plan", "plan_nom", "montant", "statut", "date_creation", "date_confirmation_fedapay", "date_validation"]
        read_only_fields = fields


class PreuveImageField(serializers.ImageField):
    """Limite et réencode les preuves avant leur stockage privé."""

    def to_internal_value(self, data):
        limite_octets = 5 * 1024 * 1024
        if data is not None and getattr(data, "size", 0) > limite_octets:
            raise serializers.ValidationError("La preuve ne doit pas dépasser 5 Mo.")
        fichier = super().to_internal_value(data)
        try:
            contenu = fichier.read()
            fichier.seek(0)
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                image = Image.open(io.BytesIO(contenu))
                format_image = image.format
                if format_image not in {"JPEG", "PNG", "WEBP"}:
                    raise serializers.ValidationError("Joignez une image JPEG, PNG ou WEBP.")
                if image.width * image.height > 20_000_000:
                    raise serializers.ValidationError("Les dimensions de la preuve sont trop importantes.")
                image.verify()
                image = Image.open(io.BytesIO(contenu))
                image.load()
                if format_image == "JPEG":
                    image = image.convert("RGB")
                    extension = "jpg"
                    options = {"quality": 90, "optimize": True}
                elif format_image == "PNG":
                    image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
                    extension = "png"
                    options = {"optimize": True}
                else:
                    image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
                    extension = "webp"
                    options = {"quality": 90, "method": 4}
                sortie = io.BytesIO()
                image.save(sortie, format=format_image, **options)
                contenu = sortie.getvalue()
        except serializers.ValidationError:
            raise
        except Exception as erreur:
            raise serializers.ValidationError("Le fichier envoyé n'est pas une image valide.") from erreur
        if len(contenu) > limite_octets:
            raise serializers.ValidationError("La preuve optimisée dépasse la limite de 5 Mo.")
        return ContentFile(contenu, name=f"preuve.{extension}")


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
