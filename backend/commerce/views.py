from datetime import datetime, time, timedelta
from decimal import Decimal
import logging
import uuid
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError, IntegrityError, connection
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse
from django.db.models import DecimalField, F, Sum
from django.db.models.functions import Coalesce
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.html import format_html
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, mixins, serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes, throttle_scope
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema, extend_schema_view

from .api_docs import (
    EXEMPLE_CLIENT, EXEMPLE_ERREUR, EXEMPLE_NON_AUTORISE, EXEMPLE_PRODUIT,
    EXEMPLE_VENTE, ConnexionReponseSerializer, InscriptionReponseSerializer,
)
from .audit import enregistrer_evenement, suspendre_audit
from .models import Abonnement, Client, ConfigurationEssai, CorrectionDette, DemandePaiementManuel, Dette, JournalAudit, Paiement, PaiementAbonnementHistorique, Plan, Produit, Vente
from .pagination import PaginationAudit
from .permissions import AbonnementAutoriseEcriture, EstCommercantAuthentifie, EstProprietaireObjet
from .services.export_pdf import construire_export_pdf
from .services.recu_pdf import construire_recu_certifie
from .throttles import (
    ThrottleConnexion, ThrottleInscription, ThrottleRefresh,
    ThrottleVerificationDocument,
)
from .serializers import (
    AbonnementSerializer, ClientSerializer, ConnexionSerializer, DemandeReinitialisationSerializer,
    DetteSerializer, InscriptionSerializer, NouvelleCorrectionDetteSerializer,
    JournalAuditSerializer, PaiementSerializer, PlanSerializer, ProduitSerializer,
    ReinitialisationMotDePasseSerializer, DemandePaiementManuelSerializer, PaiementAbonnementHistoriqueSerializer, VenteSerializer,
)
from notifications.email import ErreurEnvoiEmail, envoyer_email

Commercant = get_user_model()
logger = logging.getLogger(__name__)


def _date_recu(valeur):
    return timezone.localtime(valeur).strftime("%d/%m/%Y à %H:%M") if valeur else "—"


def _pdf_recu_dette(dette):
    code = str(dette.code_verification)
    solde = max(Decimal("0"), dette.client.solde)
    return construire_recu_certifie(
        titre="Reçu de dette",
        sous_titre="Justificatif d’une dette enregistrée par le commerçant.",
        lignes=[
            ("Commerçant", dette.commercant.nom_boutique),
            ("Client", dette.client.nom),
            ("Enregistrée le", _date_recu(dette.date)),
            ("Solde restant du client", f"{solde:,.0f}".replace(",", " ") + " FCFA"),
            ("Note", dette.note or "Aucune note"),
        ],
        montant_principal=dette.montant,
        code=code,
        url_qr=f"{settings.PUBLIC_FRONTEND_URL.rstrip('/')}/verifier/{code}",
        date_generation=_date_recu(dette.date_generation),
    )


def _pdf_recu_abonnement(demande):
    code = str(demande.code_verification)
    debut = demande.date_debut_abonnement
    fin = demande.date_fin_abonnement
    periode = f"{timezone.localtime(debut):%d/%m/%Y} au {timezone.localtime(fin):%d/%m/%Y}"
    return construire_recu_certifie(
        titre="Reçu d’abonnement",
        sous_titre="Confirmation du règlement et de la période couverte.",
        lignes=[
            ("Commerçant", demande.commercant.nom_boutique),
            ("Formule", demande.plan.nom),
            ("Date de validation", _date_recu(demande.date_decision)),
            ("Période couverte", periode),
        ],
        montant_principal=demande.montant,
        code=code,
        url_qr=f"{settings.PUBLIC_FRONTEND_URL.rstrip('/')}/verifier/{code}",
        date_generation=_date_recu(demande.date_generation),
    )


@extend_schema(
    tags=["Auth"], summary="Inscrire un commerçant", request=InscriptionSerializer,
    responses={201: InscriptionReponseSerializer, 400: EXEMPLE_ERREUR, 429: EXEMPLE_NON_AUTORISE},
    examples=[OpenApiExample("Inscription", value={"email": "commercant@example.com", "telephone": "+22961020304", "nom_boutique": "Ma boutique", "mot_de_passe": "MotDePasse123!", "accepte_conditions": True}, request_only=True)],
)
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([ThrottleInscription])
@throttle_scope("inscription")
def inscription(request):
    serializer = InscriptionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    duree_essai = user.abonnement.plan.duree_jours if user.abonnement.statut == Abonnement.Statut.ESSAI else 0
    message_essai = (
        f"Vous bénéficiez de {duree_essai} jours d’essai gratuit pour suivre vos ventes, vos produits et les dettes de vos clients."
        if duree_essai else "L’essai gratuit n’est actuellement pas proposé. Vous pouvez consulter les offres d’abonnement dans votre espace."
    )
    contenu_bienvenue = format_html(
        '<div style="font-family:Arial,sans-serif;color:#243b36;line-height:1.6">'
        '<h1 style="color:#0c765c">Bienvenue sur Nobi</h1><p>Bonjour {},</p>'
        '<p>{}</p><p>Bonne gestion de votre boutique !</p></div>',
        user.nom_boutique, message_essai,
    )
    try:
        envoyer_email(user.email, "Bienvenue sur Nobi", str(contenu_bienvenue))
    except (ErreurEnvoiEmail, ValueError):
        # La création du compte ne dépend pas de la disponibilité du fournisseur.
        logger.warning("Échec de l'envoi de l'email de bienvenue.")
    return Response(
        {"id": str(user.id), "email": user.email, "telephone": user.telephone, "nom_boutique": user.nom_boutique},
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    tags=["Auth"], summary="Ouvrir une session commerçant", request=ConnexionSerializer,
    responses={200: ConnexionReponseSerializer, 400: EXEMPLE_ERREUR, 429: EXEMPLE_NON_AUTORISE},
    examples=[OpenApiExample("Connexion", value={"email": "commercant@example.com", "mot_de_passe": "MotDePasse123!"}, request_only=True)],
)
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([ThrottleConnexion])
@throttle_scope("connexion")
def connexion(request):
    serializer = ConnexionSerializer(data=request.data, context={"request": request})
    try:
        serializer.is_valid(raise_exception=True)
    except APIException:
        email = str(request.data.get("email", ""))[:254].strip().lower()
        commercant_tente = Commercant.objects.filter(email=email).first() if email else None
        if (
            commercant_tente and not commercant_tente.is_staff
            and not commercant_tente.is_active and commercant_tente.motif_suspension
            and commercant_tente.check_password(str(request.data.get("mot_de_passe", "")))
        ):
            enregistrer_evenement(
                commercant=commercant_tente, utilisateur=commercant_tente,
                action=JournalAudit.Action.CONNEXION_ECHOUEE,
                objet_type="Authentification", objet_id=commercant_tente.pk,
                nouvelles_valeurs={"motif": "compte_suspendu"},
                adresse_ip=request._request.META.get("REMOTE_ADDR"),
            )
            return Response(
                {"detail": "Votre compte est suspendu. Contactez l'assistance pour obtenir de l'aide."},
                status=status.HTTP_403_FORBIDDEN,
            )
        enregistrer_evenement(
            commercant=commercant_tente, utilisateur=commercant_tente,
            action=JournalAudit.Action.CONNEXION_ECHOUEE, objet_type="Authentification",
            objet_id=commercant_tente.pk if commercant_tente else "",
            nouvelles_valeurs={"motif": "identifiants_invalides"},
            adresse_ip=request._request.META.get("REMOTE_ADDR"),
        )
        raise
    user = serializer.validated_data["user"]
    if user.is_staff or user.is_superuser:
        enregistrer_evenement(
            commercant=user, utilisateur=user, action=JournalAudit.Action.CONNEXION_ECHOUEE,
            objet_type="AuthentificationAdmin", objet_id=user.pk,
            nouvelles_valeurs={"motif": "utiliser_connexion_backoffice"},
            adresse_ip=request._request.META.get("REMOTE_ADDR"),
        )
        return Response(
            {"detail": "Ce compte est réservé au back-office. Utilisez la connexion d'administration."},
            status=status.HTTP_403_FORBIDDEN,
        )
    enregistrer_evenement(
        commercant=user, utilisateur=user, action=JournalAudit.Action.CONNEXION_REUSSIE,
        objet_type="Authentification", objet_id=user.pk,
        nouvelles_valeurs={"resultat": "reussie"},
        adresse_ip=request._request.META.get("REMOTE_ADDR"),
    )
    refresh = RefreshToken.for_user(user)
    return Response({
        "refresh": str(refresh), "access": str(refresh.access_token),
        "commercant": {"id": str(user.id), "email": user.email, "telephone": user.telephone, "nom_boutique": user.nom_boutique},
    })


class RafraichirJetonView(TokenRefreshView):
    """Renouvelle un access token à partir d'un refresh JWT valide."""

    throttle_classes = [ThrottleRefresh]
    throttle_scope = "refresh"

    @extend_schema(
        tags=["Auth"], summary="Renouveler le jeton d'accès",
        request=TokenRefreshSerializer, responses={200: TokenRefreshSerializer, 401: EXEMPLE_NON_AUTORISE},
        examples=[OpenApiExample("Refresh", value={"refresh": "<refresh-jwt>"}, request_only=True)],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(
    tags=["Auth"], summary="Demander un lien temporaire de réinitialisation par email",
    request=DemandeReinitialisationSerializer,
    responses={200: OpenApiTypes.OBJECT, 400: EXEMPLE_ERREUR, 429: EXEMPLE_NON_AUTORISE},
)
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_scope("mot_de_passe_oublie")
def mot_de_passe_oublie(request):
    """Répond de façon identique, que l'adresse email corresponde ou non."""
    serializer = DemandeReinitialisationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    utilisateur = Commercant.objects.filter(
        email=serializer.validated_data["email"], is_active=True,
    ).first()
    if utilisateur is not None:
        uid = urlsafe_base64_encode(force_bytes(utilisateur.pk))
        jeton = default_token_generator.make_token(utilisateur)
        lien = f"{settings.FRONTEND_URL.rstrip('/')}/nouveau-mot-de-passe?{urlencode({'uid': uid, 'token': jeton})}"
        contenu = format_html(
            '<div style="font-family:Arial,sans-serif;color:#243b36;line-height:1.6">'
            '<h1 style="color:#0c765c">Réinitialisation du mot de passe</h1>'
            '<p>Bonjour {},</p><p>Vous avez demandé à modifier le mot de passe de votre boutique.</p>'
            '<p>Ce lien est valable pendant 15 minutes et ne peut être utilisé qu’une fois.</p>'
            '<p><a href="{}" style="display:inline-block;padding:12px 18px;background:#0c765c;'
            'color:#fff;text-decoration:none;border-radius:8px">Choisir un nouveau mot de passe</a></p>'
            '<p>Si vous n’êtes pas à l’origine de cette demande, ignorez cet email.</p></div>',
            utilisateur.nom_boutique,
            lien,
        )
        try:
            envoyer_email(utilisateur.email, "Réinitialisation de votre mot de passe", str(contenu))
        except (ErreurEnvoiEmail, ValueError):
            # La réponse reste identique afin de ne pas révéler si le compte existe.
            logger.warning("Échec de l'envoi de l'email de réinitialisation.")
    if settings.EMAIL_SIMULATION:
        detail = (
            "Mode simulation actif : aucun email réel n'a été envoyé. "
            "En mode réel, un lien sera envoyé si cette adresse correspond à un compte actif."
        )
    else:
        detail = "Si cette adresse correspond à un compte actif, un lien de réinitialisation sera envoyé par email."
    return Response({"detail": detail}, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Auth"], summary="Définir un nouveau mot de passe avec le lien temporaire",
    request=ReinitialisationMotDePasseSerializer,
    responses={200: OpenApiTypes.OBJECT, 400: EXEMPLE_ERREUR, 429: EXEMPLE_NON_AUTORISE},
)
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_scope("reinitialisation_mot_de_passe")
def reinitialiser_mot_de_passe(request):
    """Un jeton Django expiré ou déjà consommé ne permet plus d'écrire un mot de passe."""
    serializer = ReinitialisationMotDePasseSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    donnees = serializer.validated_data
    try:
        identifiant = force_str(urlsafe_base64_decode(donnees["uid"]))
    except (ValueError, TypeError, OverflowError):
        return Response({"detail": "Ce lien est invalide ou a expiré. Demandez-en un nouveau."}, status=400)

    with transaction.atomic():
        utilisateur = Commercant.objects.select_for_update().filter(pk=identifiant, is_active=True).first()
        if utilisateur is None or not default_token_generator.check_token(utilisateur, donnees["token"]):
            return Response({"detail": "Ce lien est invalide ou a expiré. Demandez-en un nouveau."}, status=400)
        try:
            password_validation.validate_password(donnees["nouveau_mot_de_passe"], user=utilisateur)
        except DjangoValidationError as erreur:
            return Response({"nouveau_mot_de_passe": erreur.messages}, status=400)
        utilisateur.set_password(donnees["nouveau_mot_de_passe"])
        utilisateur.save(update_fields=["password"])
    return Response({"detail": "Votre mot de passe a été mis à jour. Vous pouvez vous connecter."})


@extend_schema_view(
    list=extend_schema(tags=["Produits"], summary="Lister les produits du commerçant", parameters=[OpenApiParameter("rupture", bool, OpenApiParameter.QUERY, description="true pour ne retourner que les produits au seuil d'alerte")], responses={200: ProduitSerializer(many=True), 401: EXEMPLE_NON_AUTORISE}, examples=[OpenApiExample("Produits", value=[EXEMPLE_PRODUIT.value], response_only=True)]),
    create=extend_schema(tags=["Produits"], summary="Créer un produit", responses={201: ProduitSerializer, 400: EXEMPLE_ERREUR, 401: EXEMPLE_NON_AUTORISE, 403: EXEMPLE_NON_AUTORISE}, examples=[EXEMPLE_PRODUIT]),
    retrieve=extend_schema(tags=["Produits"], summary="Consulter un produit", responses={200: ProduitSerializer, 401: EXEMPLE_NON_AUTORISE, 404: EXEMPLE_ERREUR}, examples=[EXEMPLE_PRODUIT]),
    update=extend_schema(tags=["Produits"], summary="Remplacer un produit", responses={400: EXEMPLE_ERREUR, 403: EXEMPLE_NON_AUTORISE, 404: EXEMPLE_ERREUR}),
    partial_update=extend_schema(tags=["Produits"], summary="Modifier un produit", responses={400: EXEMPLE_ERREUR, 403: EXEMPLE_NON_AUTORISE, 404: EXEMPLE_ERREUR}),
    destroy=extend_schema(tags=["Produits"], summary="Supprimer un produit", responses={204: None, 403: EXEMPLE_NON_AUTORISE, 404: EXEMPLE_ERREUR}),
)
class VueProprietaire(viewsets.ModelViewSet):
    permission_classes = [EstCommercantAuthentifie, AbonnementAutoriseEcriture, EstProprietaireObjet]

    def perform_create(self, serializer):
        serializer.save(commercant=self.request.user)


class ProduitViewSet(VueProprietaire):
    serializer_class = ProduitSerializer

    def get_queryset(self):
        queryset = Produit.objects.filter(commercant=self.request.user)
        if self.request.query_params.get("rupture", "").lower() == "true":
            queryset = queryset.filter(quantite_stock__lte=F("seuil_alerte"))
        return queryset


@extend_schema_view(
    list=extend_schema(tags=["Clients"], summary="Lister les clients et leur solde", responses={200: ClientSerializer(many=True), 401: EXEMPLE_NON_AUTORISE}, examples=[OpenApiExample("Liste des clients", value=[EXEMPLE_CLIENT.value], response_only=True)]),
    create=extend_schema(tags=["Clients"], summary="Créer un client", responses={201: ClientSerializer, 400: EXEMPLE_ERREUR, 401: EXEMPLE_NON_AUTORISE, 403: EXEMPLE_NON_AUTORISE}, examples=[OpenApiExample("Nouveau client", value={"nom": "Awa", "telephone": "22990000001"}, request_only=True), EXEMPLE_CLIENT]),
    retrieve=extend_schema(tags=["Clients"], summary="Consulter un client et son solde", responses={200: ClientSerializer, 401: EXEMPLE_NON_AUTORISE, 404: EXEMPLE_ERREUR}, examples=[EXEMPLE_CLIENT]),
    update=extend_schema(tags=["Clients"], summary="Remplacer un client", responses={400: EXEMPLE_ERREUR, 403: EXEMPLE_NON_AUTORISE, 404: EXEMPLE_ERREUR}),
    partial_update=extend_schema(tags=["Clients"], summary="Modifier un client", responses={400: EXEMPLE_ERREUR, 403: EXEMPLE_NON_AUTORISE, 404: EXEMPLE_ERREUR}),
    destroy=extend_schema(tags=["Clients"], summary="Supprimer un client", responses={204: None, 403: EXEMPLE_NON_AUTORISE, 404: EXEMPLE_ERREUR}),
)
class ClientViewSet(VueProprietaire):
    serializer_class = ClientSerializer

    def get_queryset(self):
        return Client.objects.filter(commercant=self.request.user)


@extend_schema_view(
    list=extend_schema(tags=["Ventes"], summary="Lister les ventes", parameters=[OpenApiParameter("periode", str, OpenApiParameter.QUERY, enum=["jour", "semaine", "mois"], description="Période de l'historique")], responses={200: VenteSerializer(many=True), 401: EXEMPLE_NON_AUTORISE}, examples=[OpenApiExample("Historique", value=[EXEMPLE_VENTE.value], response_only=True)]),
    create=extend_schema(tags=["Ventes"], summary="Enregistrer une vente et déduire le stock", responses={201: VenteSerializer, 400: EXEMPLE_ERREUR, 403: EXEMPLE_NON_AUTORISE}, examples=[OpenApiExample("Nouvelle vente", value={"produit": 1, "client": 1, "quantite": 2}, request_only=True), OpenApiExample("Vente créée", value={"id": 42, "produit": 1, "client": 1, "quantite": 2, "prix_unitaire": "1000.00", "total": "2000.00", "date": "2026-09-28T12:00:00Z"}, response_only=True)]),
    retrieve=extend_schema(tags=["Ventes"], summary="Consulter une vente", responses={200: VenteSerializer, 401: EXEMPLE_NON_AUTORISE, 404: EXEMPLE_ERREUR}),
)
class VenteViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = VenteSerializer
    permission_classes = [EstCommercantAuthentifie, AbonnementAutoriseEcriture, EstProprietaireObjet]

    def get_queryset(self):
        queryset = Vente.objects.filter(commercant=self.request.user).select_related("produit", "client")
        periode = self.request.query_params.get("periode")
        maintenant = timezone.localtime()
        debut_jour = maintenant.replace(hour=0, minute=0, second=0, microsecond=0)
        if periode == "jour":
            queryset = queryset.filter(date__gte=debut_jour)
        elif periode == "semaine":
            queryset = queryset.filter(date__gte=debut_jour - timedelta(days=debut_jour.weekday()))
        elif periode == "mois":
            queryset = queryset.filter(date__gte=debut_jour.replace(day=1))
        return queryset


@extend_schema_view(
    list=extend_schema(tags=["Clients"], summary="Lister les dettes", responses={200: DetteSerializer(many=True), 401: EXEMPLE_NON_AUTORISE}),
    create=extend_schema(tags=["Clients"], summary="Ajouter une dette client", responses={201: DetteSerializer, 400: EXEMPLE_ERREUR, 401: EXEMPLE_NON_AUTORISE, 403: EXEMPLE_NON_AUTORISE}, examples=[OpenApiExample("Nouvelle dette", value={"client": 1, "montant": "5000.00", "note": "Achats à crédit"}, request_only=True), OpenApiExample("Dette créée", value={"id": 5, "client": 1, "montant": "5000.00", "note": "Achats à crédit", "date": "2026-09-28T12:00:00Z"}, response_only=True)]),
)
class DetteViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = DetteSerializer
    permission_classes = [EstCommercantAuthentifie, AbonnementAutoriseEcriture]

    def get_serializer_class(self):
        if self.action == "corriger":
            return NouvelleCorrectionDetteSerializer
        return DetteSerializer

    def perform_create(self, serializer):
        serializer.save(commercant=self.request.user)

    def get_queryset(self):
        queryset = Dette.objects.filter(commercant=self.request.user).select_related("client", "commercant")
        identifiant_client = self.request.query_params.get("client")
        if identifiant_client:
            queryset = queryset.filter(client_id=identifiant_client, client__commercant=self.request.user)
        return queryset.prefetch_related("corrections")

    @extend_schema(
        tags=["Clients"], summary="Corriger une dette et conserver la trace historique",
        request=NouvelleCorrectionDetteSerializer,
        responses={200: DetteSerializer, 400: EXEMPLE_ERREUR, 404: EXEMPLE_ERREUR},
    )
    @action(detail=True, methods=["post"], url_path="correction")
    def corriger(self, request, pk=None):
        """Ajuste le montant avec une raison et une trace historique permanente."""
        with transaction.atomic():
            dette = self.get_object()
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            nouveau_montant = serializer.validated_data["nouveau_montant"]
            if nouveau_montant == dette.montant:
                raise serializers.ValidationError({"nouveau_montant": "Le nouveau montant doit être différent."})
            CorrectionDette.objects.create(
                commercant=request.user,
                dette=dette,
                montant_precedent=dette.montant,
                nouveau_montant=nouveau_montant,
                raison=serializer.validated_data["raison"],
            )
            dette.montant = nouveau_montant
            dette.save(update_fields=["montant"])
        return Response(DetteSerializer(dette, context=self.get_serializer_context()).data)

    @extend_schema(
        tags=["Clients"], summary="Télécharger le reçu PDF d'une dette",
        responses={200: OpenApiResponse(response=OpenApiTypes.BINARY, description="Fichier PDF"), 404: EXEMPLE_ERREUR},
    )
    @action(
        detail=True, methods=["get"], url_path="recu",
        permission_classes=[EstCommercantAuthentifie, AbonnementAutoriseEcriture, EstProprietaireObjet],
    )
    def recu(self, request, pk=None):
        """Produit un reçu vérifiable, sans changer l'accès propriétaire existant."""
        dette = self.get_object()
        with transaction.atomic():
            # Le verrou garantit qu'un seul UUID est créé si deux téléchargements
            # du même reçu arrivent simultanément.
            dette = Dette.objects.select_for_update().get(pk=dette.pk)
            self.check_object_permissions(request, dette)
            if dette.code_verification is None or dette.date_generation is None:
                if dette.code_verification is None:
                    dette.code_verification = uuid.uuid4()
                if dette.date_generation is None:
                    dette.date_generation = timezone.now()
                dette.save(update_fields=["code_verification", "date_generation"])

        reponse = HttpResponse(_pdf_recu_dette(dette), content_type="application/pdf")
        reponse["Content-Disposition"] = f'attachment; filename="recu-dette-{dette.pk}.pdf"'
        reponse["Cache-Control"] = "private, no-store"
        return reponse


@extend_schema(
    tags=["Clients"],
    summary="Vérifier publiquement l'authenticité d'un reçu de dette",
    responses={
        200: OpenApiResponse(
            description="Ne renvoie que le statut d'authenticité et, si valide, la date de génération.",
            examples=[
                OpenApiExample("Code valide", value={"valide": True, "date_generation": "2026-09-30T12:00:00Z"}),
                OpenApiExample("Code invalide", value={"valide": False}),
            ],
        ),
        429: EXEMPLE_NON_AUTORISE,
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([ThrottleVerificationDocument])
def verifier_document(request, code):
    """Confirme l'existence d'un reçu sans révéler les parties ni les montants."""
    try:
        code_uuid = uuid.UUID(str(code))
    except (ValueError, TypeError, AttributeError):
        return Response({"valide": False})

    date_generation = Dette.objects.filter(
        code_verification=code_uuid,
        date_generation__isnull=False,
    ).values_list("date_generation", flat=True).first()
    if date_generation is None:
        date_generation = DemandePaiementManuel.objects.filter(
            code_verification=code_uuid,
            statut=DemandePaiementManuel.Statut.VALIDEE,
            date_generation__isnull=False,
        ).values_list("date_generation", flat=True).first()
    if date_generation is None:
        return Response({"valide": False})
    return Response({"valide": True, "date_generation": date_generation})


@extend_schema(
    tags=["Clients"],
    summary="Afficher le reçu certifié associé à un code QR",
    responses={200: OpenApiResponse(response=OpenApiTypes.BINARY, description="Reçu PDF certifié"), 404: EXEMPLE_ERREUR, 429: EXEMPLE_NON_AUTORISE},
)
@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([ThrottleVerificationDocument])
def document_verification_pdf(request, code):
    """Affiche le reçu complet au porteur du code QR imprévisible."""
    try:
        code_uuid = uuid.UUID(str(code))
    except (ValueError, TypeError, AttributeError):
        raise Http404

    dette = Dette.objects.select_related("commercant", "client").filter(
        code_verification=code_uuid, date_generation__isnull=False,
    ).first()
    if dette is not None:
        pdf = _pdf_recu_dette(dette)
        nom_fichier = f"recu-dette-{dette.pk}.pdf"
    else:
        demande = DemandePaiementManuel.objects.select_related("commercant", "plan").filter(
            code_verification=code_uuid,
            statut=DemandePaiementManuel.Statut.VALIDEE,
            date_generation__isnull=False,
        ).first()
        if demande is None:
            raise Http404
        pdf = _pdf_recu_abonnement(demande)
        nom_fichier = f"recu-abonnement-{demande.pk}.pdf"

    reponse = HttpResponse(pdf, content_type="application/pdf")
    reponse["Content-Disposition"] = f'inline; filename="{nom_fichier}"'
    reponse["Cache-Control"] = "no-store"
    reponse["X-Content-Type-Options"] = "nosniff"
    return reponse


@extend_schema_view(
    list=extend_schema(tags=["Clients"], summary="Lister les paiements de dettes", responses={200: PaiementSerializer(many=True), 401: EXEMPLE_NON_AUTORISE}),
    create=extend_schema(tags=["Clients"], summary="Enregistrer un paiement client", responses={201: PaiementSerializer, 400: EXEMPLE_ERREUR, 401: EXEMPLE_NON_AUTORISE, 403: EXEMPLE_NON_AUTORISE}, examples=[OpenApiExample("Nouveau paiement", value={"client": 1, "montant": "2000.00"}, request_only=True), OpenApiExample("Paiement enregistré", value={"id": 3, "client": 1, "montant": "2000.00", "date": "2026-09-28T12:00:00Z"}, response_only=True)]),
)
class PaiementViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = PaiementSerializer
    permission_classes = [EstCommercantAuthentifie, AbonnementAutoriseEcriture]

    def get_queryset(self):
        return Paiement.objects.filter(commercant=self.request.user).select_related("client")

    def perform_create(self, serializer):
        serializer.save(commercant=self.request.user)


@extend_schema(tags=["Tableau de bord"], summary="Afficher les indicateurs du commerçant", responses={200: OpenApiTypes.OBJECT, 401: EXEMPLE_NON_AUTORISE}, examples=[OpenApiExample("Indicateurs", value={"ventes_jour": "25000.00", "ventes_semaine": "85000.00", "ventes_mois": "260000.00", "produits_en_rupture": [], "total_dettes_en_cours": "12000.00"}, response_only=True)])
@api_view(["GET"])
@permission_classes([EstCommercantAuthentifie])
def dashboard(request):
    commercant = request.user
    maintenant = timezone.localtime()
    debut_jour = maintenant.replace(hour=0, minute=0, second=0, microsecond=0)
    debut_semaine = debut_jour - timedelta(days=debut_jour.weekday())
    debut_mois = debut_jour.replace(day=1)
    ventes = Vente.objects.filter(commercant=commercant)
    champ_montant = DecimalField(max_digits=14, decimal_places=2)

    def total_ventes(debut):
        return ventes.filter(date__gte=debut).aggregate(
            total=Coalesce(Sum("total"), 0, output_field=champ_montant)
        )["total"]

    produits_alerte = Produit.objects.filter(
        commercant=commercant, quantite_stock__lte=F("seuil_alerte")
    ).values("id", "nom", "quantite_stock", "seuil_alerte")
    dettes = Dette.objects.filter(commercant=commercant).aggregate(
        total=Coalesce(Sum("montant"), 0, output_field=champ_montant)
    )["total"]
    paiements = Paiement.objects.filter(commercant=commercant).aggregate(
        total=Coalesce(Sum("montant"), 0, output_field=champ_montant)
    )["total"]
    return Response({
        "ventes_jour": total_ventes(debut_jour),
        "ventes_semaine": total_ventes(debut_semaine),
        "ventes_mois": total_ventes(debut_mois),
        "produits_en_rupture": list(produits_alerte),
        "total_dettes_en_cours": dettes - paiements,
    })


@extend_schema(tags=["Abonnement"], summary="Consulter l'abonnement et les jours restants", responses={200: AbonnementSerializer, 401: EXEMPLE_NON_AUTORISE})
@api_view(["GET"])
@permission_classes([EstCommercantAuthentifie])
def abonnement_actuel(request):
    abonnement = request.user.abonnement
    if abonnement.date_fin <= timezone.now() and abonnement.statut != Abonnement.Statut.EXPIRE:
        abonnement.statut = Abonnement.Statut.EXPIRE
        abonnement.save(update_fields=["statut"])
    donnees = AbonnementSerializer(abonnement).data
    donnees["mode_paiement"] = "manuel"
    operateurs = [
        (DemandePaiementManuel.Operateur.MTN, "MTN", settings.NUMERO_MTN),
        (DemandePaiementManuel.Operateur.MOOV, "Moov", settings.NUMERO_MOOV),
        (DemandePaiementManuel.Operateur.CELTIIS, "Celtiis", settings.NUMERO_CELTIIS),
    ]
    donnees["operateurs_paiement"] = [
        {"code": code, "nom": nom, "numero": numero}
        for code, nom, numero in operateurs if numero
    ]
    return Response(donnees)


@extend_schema(tags=["Abonnement"], summary="Lister les formules disponibles", responses={200: PlanSerializer(many=True), 401: EXEMPLE_NON_AUTORISE}, examples=[OpenApiExample("Formule mensuelle", value=[{"id": 1, "nom": "Mensuel", "prix": "2500.00", "duree_jours": 30}], response_only=True)])
@api_view(["GET"])
@permission_classes([EstCommercantAuthentifie])
def plans(request):
    offres = Plan.objects.filter(actif=True, prix__gt=0)
    return Response(PlanSerializer(offres, many=True).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def offre_essai(request):
    """Expose uniquement la disponibilité et la durée publique de l'essai."""
    configuration = ConfigurationEssai.obtenir()
    return Response({"actif": configuration.actif, "duree_jours": configuration.duree_jours if configuration.actif else 0})


@extend_schema(tags=["Abonnement"], summary="Consulter l'historique des paiements d'abonnement", responses={200: PaiementAbonnementHistoriqueSerializer(many=True), 401: EXEMPLE_NON_AUTORISE})
@api_view(["GET"])
@permission_classes([EstCommercantAuthentifie])
def historique_abonnement(request):
    paiements = PaiementAbonnementHistorique.objects.filter(commercant=request.user).select_related("plan")
    return Response(PaiementAbonnementHistoriqueSerializer(paiements, many=True).data)


@api_view(["GET", "POST"])
@permission_classes([EstCommercantAuthentifie])
def demandes_paiement_abonnement(request):
    """Crée une demande manuelle ou renvoie uniquement l'historique du compte courant."""
    if request.method == "GET":
        demandes = DemandePaiementManuel.objects.filter(commercant=request.user).select_related("plan")
        return Response(DemandePaiementManuelSerializer(demandes, many=True).data)
    if not any([settings.NUMERO_MTN, settings.NUMERO_MOOV, settings.NUMERO_CELTIIS]):
        return Response({"detail": "Aucun opérateur Mobile Money n'est configuré."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    if DemandePaiementManuel.objects.filter(commercant=request.user, statut=DemandePaiementManuel.Statut.EN_ATTENTE).exists():
        return Response({"detail": "Une demande de paiement est déjà en attente de vérification."}, status=status.HTTP_409_CONFLICT)
    serializer = DemandePaiementManuelSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        with transaction.atomic():
            demande = serializer.save(commercant=request.user, montant=serializer.validated_data["plan"].prix)
            enregistrer_evenement(
                commercant=request.user, utilisateur=request.user,
                action=JournalAudit.Action.CHANGEMENT_ABONNEMENT,
                objet_type="DemandePaiementManuel", objet_id=demande.pk,
                nouvelles_valeurs={"decision": "soumise", "plan_id": demande.plan_id, "montant": str(demande.montant), "operateur": demande.operateur},
            )
    except IntegrityError:
        # L'index partiel tranche aussi correctement en cas de deux envois simultanés.
        if DemandePaiementManuel.objects.filter(commercant=request.user, statut=DemandePaiementManuel.Statut.EN_ATTENTE).exists():
            return Response({"detail": "Une demande de paiement est déjà en attente de vérification."}, status=status.HTTP_409_CONFLICT)
        raise
    return Response(DemandePaiementManuelSerializer(demande).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([EstCommercantAuthentifie])
def preuve_demande_abonnement(request, pk):
    demande = DemandePaiementManuel.objects.filter(pk=pk).first()
    autorise_admin = request.user.is_superuser or (
        request.user.is_staff
        and getattr(request.user, "profil_sous_admin", None)
        and "valider_paiements" in request.user.profil_sous_admin.permissions
    )
    if demande is None or (not autorise_admin and demande.commercant_id != request.user.id) or not demande.preuve:
        raise Http404
    try:
        fichier = demande.preuve.open("rb")
    except OSError:
        return Response({"detail": "La preuve de paiement est temporairement indisponible."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return FileResponse(fichier, content_type="application/octet-stream", as_attachment=True, filename="preuve-paiement")


@api_view(["GET"])
@permission_classes([EstCommercantAuthentifie])
def recu_abonnement_manuel(request, pk):
    demande = DemandePaiementManuel.objects.select_related("commercant", "plan").filter(pk=pk, commercant=request.user, statut=DemandePaiementManuel.Statut.VALIDEE).first()
    if demande is None or not demande.code_verification:
        raise Http404
    response = HttpResponse(_pdf_recu_abonnement(demande), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="recu-abonnement-{demande.pk}.pdf"'
    response["Cache-Control"] = "private, no-store"
    return response


class VueJournalAudit(generics.ListAPIView):
    """Historique paginé limité au commerçant connecté."""

    serializer_class = JournalAuditSerializer
    pagination_class = PaginationAudit

    def get_queryset(self):
        queryset = JournalAudit.objects.filter(commercant=self.request.user).select_related("utilisateur")
        action = self.request.query_params.get("action")
        if action:
            if action not in JournalAudit.Action.values:
                raise serializers.ValidationError({"action": "Action de journal inconnue."})
            queryset = queryset.filter(action=action)
        for parametre, lookup, borne_fin in (
            ("date_debut", "date__gte", False), ("date_fin", "date__lte", True),
        ):
            valeur = self.request.query_params.get(parametre)
            if valeur:
                jour = parse_date(valeur)
                if jour is None:
                    raise serializers.ValidationError({parametre: "Utilisez le format AAAA-MM-JJ."})
                instant = timezone.make_aware(datetime.combine(jour, time.max if borne_fin else time.min))
                queryset = queryset.filter(**{lookup: instant})
        return queryset


@api_view(["GET"])
@permission_classes([AllowAny])
def sante(request):
    """Vérifie que l'API répond et que la base accepte une requête simple."""
    try:
        with connection.cursor() as curseur:
            curseur.execute("SELECT 1")
            curseur.fetchone()
    except DatabaseError:
        return Response(
            {"statut": "indisponible", "detail": "Service temporairement indisponible."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response({"statut": "ok", "base_de_donnees": "disponible"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_compte(request):
    """Télécharge les données du commerçant connecté dans un PDF paginé."""
    contenu = construire_export_pdf(request.user)
    reponse = HttpResponse(contenu, content_type="application/pdf")
    reponse["Content-Disposition"] = 'attachment; filename="export-donnees-commerce.pdf"'
    reponse["Cache-Control"] = "private, no-store"
    return reponse


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def supprimer_compte(request):
    """Supprime définitivement les données après vérification du mot de passe."""
    mot_de_passe = request.data.get("mot_de_passe", "")
    if not mot_de_passe or not request.user.check_password(mot_de_passe):
        return Response(
            {"detail": "Mot de passe incorrect. Le compte n'a pas été supprimé."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    from axes.models import AccessAttempt, AccessFailureLog, AccessLog

    utilisateur = request.user
    with transaction.atomic(), suspendre_audit():
        # Supprime les traces historiques sous email et sous l'ancien identifiant téléphone.
        identifiants = [utilisateur.email]
        if utilisateur.telephone:
            identifiants.append(utilisateur.telephone)
        AccessAttempt.objects.filter(username__in=identifiants).delete()
        AccessFailureLog.objects.filter(username__in=identifiants).delete()
        AccessLog.objects.filter(username__in=identifiants).delete()
        JournalAudit.objects.filter(commercant=utilisateur).delete()
        # Le FK Vente.produit est PROTECT ; ses ventes sont effacées avant le catalogue.
        Vente.objects.filter(commercant=utilisateur).delete()
        utilisateur.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
