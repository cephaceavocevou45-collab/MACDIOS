from datetime import datetime, time, timedelta
from decimal import Decimal
import hashlib
import hmac
import json
import logging
import time as unix_time
import uuid
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.middleware.csrf import get_token
from django.db import DatabaseError, IntegrityError, connection
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse
from django.db.models import Count, DecimalField, F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date
from django.utils.html import format_html
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, mixins, serializers, status, viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes, throttle_classes, throttle_scope
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema, extend_schema_view, inline_serializer

from .api_docs import (
    EXEMPLE_CLIENT, EXEMPLE_ERREUR, EXEMPLE_NON_AUTORISE, EXEMPLE_PRODUIT,
    ConnexionReponseSerializer, InscriptionReponseSerializer,
    ConfirmationSuppressionSerializer, CsrfTokenReponseSerializer,
    OffreEssaiReponseSerializer, ProfilReponseSerializer, ReponseDetailSerializer,
    SanteReponseSerializer, SessionReponseSerializer,
)
from .audit import enregistrer_evenement, suspendre_audit
from .branding import NOM_APPLICATION
from .idempotence import CreationIdempotenteMixin
from .models import Abonnement, Approvisionnement, Client, ConfigurationEssai, CorrectionDette, DemandePaiementManuel, Dette, Fournisseur, JournalAudit, LigneApprovisionnement, MouvementStock, Paiement, PaiementAbonnementHistorique, Plan, Produit, Vente
from .pagination import PaginationAudit, PaginationStandard
from .permissions import AbonnementAutoriseEcriture, EstCommercantAuthentifie, EstProprietaireObjet
from .authentication import verifier_csrf
from .jwt_sessions import (
    COOKIE_REFRESH, creer_jetons_session, definir_cookies_auth, effacer_cookies_auth,
    enregistrer_rotation, revoquer_session, revoquer_sessions_utilisateur, session_depuis_refresh,
)
from .services.export_pdf import construire_export_pdf
from .services.profil_image import logo_profil_pour_pdf, supprimer_logo_profil
from .services.recu_pdf import construire_recu_certifie
from .services.fedapay import actualiser_paiement, creer_paiement
from .throttles import (
    ThrottleConnexion, ThrottleInscription, ThrottleRefresh,
    ThrottleVerificationDocument,
)
from .serializers import (
    AbonnementSerializer, AjustementStockSerializer, ApprovisionnementSerializer, ClientSerializer, ConnexionSerializer, DemandeReinitialisationSerializer,
    DetteSerializer, InscriptionSerializer, NouvelleCorrectionDetteSerializer,
    JournalAuditSerializer, PaiementSerializer, PlanSerializer, ProduitSerializer,
    ReinitialisationMotDePasseSerializer, DemandePaiementManuelSerializer, FournisseurSerializer, MouvementStockSerializer, PaiementAbonnementHistoriqueSerializer, VenteSerializer,
    ProfilSerializer,
)
from notifications.email import ErreurEnvoiEmail, envoyer_email

Commercant = get_user_model()
logger = logging.getLogger(__name__)


def _schema_liste_paginee(nom, serializer_item):
    """Décrit la forme réellement renvoyée par le paginateur DRF."""
    return inline_serializer(
        name=nom,
        fields={
            "count": serializers.IntegerField(),
            "next": serializers.URLField(allow_null=True),
            "previous": serializers.URLField(allow_null=True),
            "results": serializer_item(many=True),
        },
    )


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
        logo_proprietaire=logo_profil_pour_pdf(dette.commercant),
        initiales_proprietaire=_initiales(dette.commercant.nom_boutique),
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
        logo_proprietaire=logo_profil_pour_pdf(demande.commercant),
        initiales_proprietaire=_initiales(demande.commercant.nom_boutique),
    )


def _initiales(nom):
    """Construit un repli lisible sans logo à partir du nom affiché."""
    mots = [mot for mot in (nom or "").split() if mot]
    return "".join(mot[0].upper() for mot in mots[:2]) or "N"


def _reponse_liste_paginee(request, queryset, serializer_class):
    """Sérialise une page bornée d'un endpoint fonctionnel retournant une liste."""
    pagination = PaginationStandard()
    page = pagination.paginate_queryset(queryset, request)
    return pagination.get_paginated_response(serializer_class(page, many=True).data)


@extend_schema(
    tags=["Auth"], summary="Inscrire un commerçant", request=InscriptionSerializer,
    responses={201: InscriptionReponseSerializer, 400: EXEMPLE_ERREUR, 429: EXEMPLE_NON_AUTORISE},
    examples=[OpenApiExample("Inscription", value={"email": "commercant@example.com", "telephone": "+22961020304", "nom_boutique": "Ma boutique", "mot_de_passe": "MotDePasse123!", "accepte_conditions": True}, request_only=True)],
)
@api_view(["POST"])
@authentication_classes([])
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
        '<h1 style="color:#0c765c">Bienvenue sur {}</h1><p>Bonjour {},</p>'
        '<p>{}</p><p>Bonne gestion de votre boutique !</p></div>',
        NOM_APPLICATION, user.nom_boutique, message_essai,
    )
    try:
        envoyer_email(user.email, f"Bienvenue sur {NOM_APPLICATION}", str(contenu_bienvenue))
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
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([ThrottleConnexion])
@throttle_scope("connexion")
def connexion(request):
    verifier_csrf(request)
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
    access, refresh = creer_jetons_session(user)
    reponse = Response({
        "commercant": {"id": str(user.id), "email": user.email, "telephone": user.telephone, "nom_boutique": user.nom_boutique},
    })
    return definir_cookies_auth(reponse, access, refresh)


class RafraichirJetonView(TokenRefreshView):
    """Renouvelle un access token à partir d'un refresh JWT valide."""

    throttle_classes = [ThrottleRefresh]
    authentication_classes = []
    throttle_scope = "refresh"

    @extend_schema(
        tags=["Auth"], summary="Renouveler le jeton d'accès",
        description="Lit le refresh token depuis le cookie HttpOnly, le fait tourner et remet le nouvel access token dans un cookie HttpOnly.",
        request=None, responses={200: ReponseDetailSerializer, 401: EXEMPLE_NON_AUTORISE},
    )
    def post(self, request, *args, **kwargs):
        verifier_csrf(request)
        refresh_brut = request.COOKIES.get(COOKIE_REFRESH)
        if not refresh_brut:
            return Response({"detail": "Session expirée. Reconnectez-vous."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            with transaction.atomic():
                session, _ = session_depuis_refresh(refresh_brut)
                serializer = self.get_serializer(data={"refresh": refresh_brut})
                serializer.is_valid(raise_exception=True)
                donnees = serializer.validated_data
                nouveau_refresh = donnees.get("refresh", refresh_brut)
                enregistrer_rotation(session, nouveau_refresh)
                reponse = Response({"detail": "Session renouvelée."})
                return definir_cookies_auth(reponse, donnees["access"], nouveau_refresh)
        except Exception:
            return effacer_cookies_auth(Response({"detail": "Session expirée ou révoquée. Reconnectez-vous."}, status=401))


@extend_schema(tags=["Auth"], summary="Obtenir un jeton CSRF pour les requêtes avec cookies", responses={200: CsrfTokenReponseSerializer})
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def jeton_csrf(request):
    """Prépare le cookie CSRF et retourne le jeton à garder uniquement en mémoire."""
    return Response({"csrfToken": get_token(request._request)})


@extend_schema(tags=["Auth"], summary="Vérifier la session actuellement authentifiée", responses={200: SessionReponseSerializer, 401: EXEMPLE_NON_AUTORISE})
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def session_authentifiee(request):
    """Expose l'identité non sensible de la session après rechargement de page."""
    user = request.user
    est_admin = bool(user.is_staff or user.is_superuser)
    permissions = ["*"] if user.is_superuser else (
        user.profil_sous_admin.permissions if est_admin and hasattr(user, "profil_sous_admin") else []
    )
    return Response({
        "administrateur": {
            "id": str(user.pk), "email": user.email,
            "nom": user.profil_sous_admin.nom if est_admin and hasattr(user, "profil_sous_admin") else user.nom_boutique,
            "super_admin": user.is_superuser, "permissions": permissions,
        } if est_admin else None,
        "commercant": None if est_admin else {
            "id": str(user.pk), "email": user.email,
            "telephone": user.telephone, "nom_boutique": user.nom_boutique,
        },
    })


@extend_schema(tags=["Auth"], summary="Révoquer la session et supprimer les cookies", request=None, responses={200: ReponseDetailSerializer, 403: EXEMPLE_ERREUR})
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def deconnexion(request):
    """Révoque côté serveur la session courante puis efface ses cookies."""
    verifier_csrf(request)
    refresh_brut = request.COOKIES.get(COOKIE_REFRESH)
    if refresh_brut:
        try:
            with transaction.atomic():
                session, jeton = session_depuis_refresh(refresh_brut)
                revoquer_session(session)
                jeton.blacklist()
        except Exception:
            pass
    return effacer_cookies_auth(Response({"detail": "Vous êtes déconnecté."}))


@extend_schema(
    tags=["Auth"], summary="Demander un lien temporaire de réinitialisation par email",
    request=DemandeReinitialisationSerializer,
    responses={200: OpenApiTypes.OBJECT, 400: EXEMPLE_ERREUR, 429: EXEMPLE_NON_AUTORISE},
)
@api_view(["POST"])
@authentication_classes([])
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
@authentication_classes([])
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
        revoquer_sessions_utilisateur(utilisateur)
    return Response({"detail": "Votre mot de passe a été mis à jour. Vous pouvez vous connecter."})


@extend_schema_view(
    list=extend_schema(tags=["Produits"], summary="Lister les produits du commerçant", parameters=[OpenApiParameter("rupture", bool, OpenApiParameter.QUERY, description="true pour ne retourner que les produits au seuil d'alerte")], responses={200: _schema_liste_paginee("ProduitsPaginee", ProduitSerializer), 401: EXEMPLE_NON_AUTORISE}),
    create=extend_schema(tags=["Produits"], summary="Créer un produit", responses={201: ProduitSerializer, 400: EXEMPLE_ERREUR, 401: EXEMPLE_NON_AUTORISE, 403: EXEMPLE_NON_AUTORISE}, examples=[EXEMPLE_PRODUIT]),
    retrieve=extend_schema(tags=["Produits"], summary="Consulter un produit", responses={200: ProduitSerializer, 401: EXEMPLE_NON_AUTORISE, 404: EXEMPLE_ERREUR}, examples=[EXEMPLE_PRODUIT]),
    update=extend_schema(tags=["Produits"], summary="Remplacer un produit", responses={400: EXEMPLE_ERREUR, 403: EXEMPLE_NON_AUTORISE, 404: EXEMPLE_ERREUR}),
    partial_update=extend_schema(tags=["Produits"], summary="Modifier un produit", responses={400: EXEMPLE_ERREUR, 403: EXEMPLE_NON_AUTORISE, 404: EXEMPLE_ERREUR}),
    destroy=extend_schema(tags=["Produits"], summary="Supprimer un produit", responses={204: None, 403: EXEMPLE_NON_AUTORISE, 404: EXEMPLE_ERREUR}),
)
class VueProprietaire(viewsets.ModelViewSet):
    permission_classes = [EstCommercantAuthentifie, AbonnementAutoriseEcriture, EstProprietaireObjet]
    pagination_class = PaginationStandard

    def perform_create(self, serializer):
        serializer.save(commercant=self.request.user)


class ProduitViewSet(VueProprietaire):
    serializer_class = ProduitSerializer
    queryset = Produit.objects.none()
    lookup_value_regex = r"\d+"

    def get_queryset(self):
        queryset = Produit.objects.filter(commercant=self.request.user)
        recherche = self.request.query_params.get("recherche", "").strip()[:120]
        if recherche:
            queryset = queryset.filter(Q(nom__icontains=recherche) | Q(code_barres__iexact=recherche))
        if self.action != "retrieve":
            queryset = queryset.filter(actif=True)
        if self.request.query_params.get("rupture", "").lower() == "true":
            queryset = queryset.filter(quantite_stock__lte=F("seuil_alerte"))
        return queryset

    def perform_destroy(self, instance):
        with transaction.atomic():
            produit = Produit.objects.select_for_update().get(
                pk=instance.pk, commercant=self.request.user, actif=True
            )
            produit.actif = False
            produit.save(update_fields=["actif"])

    @extend_schema(
        tags=["Produits"], summary="Ajuster le stock avec une trace obligatoire",
        request=AjustementStockSerializer,
        responses={200: OpenApiTypes.OBJECT, 400: EXEMPLE_ERREUR, 404: EXEMPLE_ERREUR},
    )
    @action(detail=True, methods=["post"], url_path="ajuster-stock")
    def ajuster_stock(self, request, pk=None):
        serializer = AjustementStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            produit = Produit.objects.select_for_update().get(
                pk=pk, commercant=request.user, actif=True
            )
            avant = produit.quantite_stock
            variation = serializer.validated_data["variation"]
            apres = avant + variation
            if apres < 0:
                raise serializers.ValidationError({"variation": "Le stock ne peut pas devenir négatif."})
            produit.quantite_stock = apres
            produit.save(update_fields=["quantite_stock"])
            MouvementStock.objects.create(
                commercant=request.user, produit=produit,
                type=MouvementStock.Type.AJUSTEMENT, variation=variation,
                quantite_avant=avant, quantite_apres=apres,
                note=serializer.validated_data["note"], utilisateur=request.user,
            )
        return Response({"id": produit.pk, "quantite_stock": produit.quantite_stock})


class FournisseurViewSet(VueProprietaire):
    serializer_class = FournisseurSerializer
    queryset = Fournisseur.objects.none()
    lookup_value_regex = r"\d+"

    def get_queryset(self):
        queryset = Fournisseur.objects.filter(commercant=self.request.user)
        if self.action != "retrieve":
            queryset = queryset.filter(actif=True)
        recherche = self.request.query_params.get("recherche", "").strip()[:160]
        return queryset.filter(nom__icontains=recherche) if recherche else queryset

    def perform_destroy(self, instance):
        # Les réceptions conservent leur fournisseur ; suppression = archivage.
        with transaction.atomic():
            fournisseur = Fournisseur.objects.select_for_update().get(
                pk=instance.pk, commercant=self.request.user, actif=True
            )
            fournisseur.actif = False
            fournisseur.save(update_fields=["actif"])


class ApprovisionnementViewSet(CreationIdempotenteMixin, mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    operation_idempotente = "approvisionnement"
    serializer_class = ApprovisionnementSerializer
    queryset = Approvisionnement.objects.none()
    lookup_value_regex = r"\d+"
    permission_classes = [EstCommercantAuthentifie, AbonnementAutoriseEcriture, EstProprietaireObjet]
    pagination_class = PaginationStandard

    def get_queryset(self):
        queryset = Approvisionnement.objects.filter(commercant=self.request.user).select_related("fournisseur").prefetch_related("lignes__produit")
        fournisseur = self.request.query_params.get("fournisseur")
        if fournisseur and fournisseur.isdigit():
            queryset = queryset.filter(fournisseur_id=int(fournisseur))
        return queryset


class MouvementStockViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = MouvementStockSerializer
    queryset = MouvementStock.objects.none()
    lookup_value_regex = r"\d+"
    permission_classes = [EstCommercantAuthentifie, EstProprietaireObjet]
    pagination_class = PaginationStandard

    def get_queryset(self):
        queryset = MouvementStock.objects.filter(commercant=self.request.user).select_related("produit", "utilisateur")
        produit = self.request.query_params.get("produit")
        recherche = self.request.query_params.get("recherche", "").strip()[:120]
        type_mouvement = self.request.query_params.get("type")
        if produit and produit.isdigit():
            queryset = queryset.filter(produit_id=int(produit))
        if recherche:
            queryset = queryset.filter(produit__nom__icontains=recherche)
        if type_mouvement in MouvementStock.Type.values:
            queryset = queryset.filter(type=type_mouvement)
        return queryset


@extend_schema_view(
    list=extend_schema(tags=["Clients"], summary="Lister les clients et leur solde", responses={200: _schema_liste_paginee("ClientsPaginee", ClientSerializer), 401: EXEMPLE_NON_AUTORISE}),
    create=extend_schema(tags=["Clients"], summary="Créer un client", responses={201: ClientSerializer, 400: EXEMPLE_ERREUR, 401: EXEMPLE_NON_AUTORISE, 403: EXEMPLE_NON_AUTORISE}, examples=[OpenApiExample("Nouveau client", value={"nom": "Awa", "telephone": "22990000001"}, request_only=True), EXEMPLE_CLIENT]),
    retrieve=extend_schema(tags=["Clients"], summary="Consulter un client et son solde", responses={200: ClientSerializer, 401: EXEMPLE_NON_AUTORISE, 404: EXEMPLE_ERREUR}, examples=[EXEMPLE_CLIENT]),
    update=extend_schema(tags=["Clients"], summary="Remplacer un client", responses={400: EXEMPLE_ERREUR, 403: EXEMPLE_NON_AUTORISE, 404: EXEMPLE_ERREUR}),
    partial_update=extend_schema(tags=["Clients"], summary="Modifier un client", responses={400: EXEMPLE_ERREUR, 403: EXEMPLE_NON_AUTORISE, 404: EXEMPLE_ERREUR}),
    destroy=extend_schema(tags=["Clients"], summary="Supprimer un client", responses={204: None, 403: EXEMPLE_NON_AUTORISE, 404: EXEMPLE_ERREUR}),
)
class ClientViewSet(VueProprietaire):
    serializer_class = ClientSerializer
    queryset = Client.objects.none()
    lookup_value_regex = r"\d+"

    def get_queryset(self):
        champ_montant = DecimalField(max_digits=14, decimal_places=2)
        dettes = Dette.objects.filter(client_id=OuterRef("pk")).order_by().values("client_id")
        dettes = dettes.annotate(total=Sum("montant")).values("total")[:1]
        paiements = Paiement.objects.filter(client_id=OuterRef("pk")).order_by().values("client_id")
        paiements = paiements.annotate(total=Sum("montant")).values("total")[:1]
        queryset = Client.objects.filter(commercant=self.request.user).annotate(
            _total_dettes_annote=Coalesce(Subquery(dettes, output_field=champ_montant), Value(0), output_field=champ_montant),
            _total_paiements_annote=Coalesce(Subquery(paiements, output_field=champ_montant), Value(0), output_field=champ_montant),
        )
        recherche = self.request.query_params.get("recherche", "").strip()[:120]
        if recherche:
            queryset = queryset.filter(Q(nom__icontains=recherche) | Q(telephone__icontains=recherche))
        # Les listes et les opérations ordinaires portent sur les clients actifs.
        # Le détail reste accessible afin de consulter l'historique d'un client archivé.
        if self.action != "retrieve":
            queryset = queryset.filter(actif=True)
        return queryset

    def perform_destroy(self, instance):
        # L'endpoint DELETE archive le client au lieu d'effacer son historique.
        with transaction.atomic():
            client = Client.objects.select_for_update().get(
                pk=instance.pk, commercant=self.request.user, actif=True
            )
            client.actif = False
            client.save(update_fields=["actif"])


@extend_schema_view(
    list=extend_schema(tags=["Ventes"], summary="Lister les ventes", parameters=[OpenApiParameter("periode", str, OpenApiParameter.QUERY, enum=["jour", "semaine", "mois"], description="Période de l'historique")], responses={200: _schema_liste_paginee("VentesPaginees", VenteSerializer), 401: EXEMPLE_NON_AUTORISE}),
    create=extend_schema(tags=["Ventes"], summary="Enregistrer une vente et déduire le stock", responses={201: VenteSerializer, 400: EXEMPLE_ERREUR, 403: EXEMPLE_NON_AUTORISE}, examples=[OpenApiExample("Nouvelle vente", value={"produit": 1, "client": 1, "quantite": 2}, request_only=True), OpenApiExample("Vente créée", value={"id": 42, "produit": 1, "client": 1, "quantite": 2, "prix_unitaire": "1000.00", "prix_achat_unitaire": "700.00", "benefice_brut": "600.00", "total": "2000.00", "date": "2026-09-28T12:00:00Z"}, response_only=True)]),
    retrieve=extend_schema(tags=["Ventes"], summary="Consulter une vente", responses={200: VenteSerializer, 401: EXEMPLE_NON_AUTORISE, 404: EXEMPLE_ERREUR}),
)
class VenteViewSet(CreationIdempotenteMixin, mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    operation_idempotente = "vente"
    throttle_scope = "vente"
    serializer_class = VenteSerializer
    queryset = Vente.objects.none()
    lookup_value_regex = r"\d+"
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
    list=extend_schema(tags=["Clients"], summary="Lister les dettes", responses={200: _schema_liste_paginee("DettesPaginees", DetteSerializer), 401: EXEMPLE_NON_AUTORISE}),
    create=extend_schema(tags=["Clients"], summary="Ajouter une dette client", responses={201: DetteSerializer, 400: EXEMPLE_ERREUR, 401: EXEMPLE_NON_AUTORISE, 403: EXEMPLE_NON_AUTORISE}, examples=[OpenApiExample("Nouvelle dette", value={"client": 1, "montant": "5000.00", "note": "Achats à crédit"}, request_only=True), OpenApiExample("Dette créée", value={"id": 5, "client": 1, "montant": "5000.00", "note": "Achats à crédit", "date": "2026-09-28T12:00:00Z"}, response_only=True)]),
)
class DetteViewSet(CreationIdempotenteMixin, mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    operation_idempotente = "dette"
    throttle_scope = "dette"
    serializer_class = DetteSerializer
    queryset = Dette.objects.none()
    lookup_value_regex = r"\d+"
    permission_classes = [EstCommercantAuthentifie, AbonnementAutoriseEcriture]

    def get_serializer_class(self):
        if self.action == "corriger":
            return NouvelleCorrectionDetteSerializer
        return DetteSerializer

    def perform_create(self, serializer):
        client_id = serializer.validated_data["client"].pk
        with transaction.atomic():
            try:
                client = Client.objects.select_for_update().get(
                    pk=client_id, commercant=self.request.user, actif=True
                )
            except Client.DoesNotExist as erreur:
                raise serializers.ValidationError({"client": "Ce client est archivé ou introuvable."}) from erreur
            serializer.save(commercant=self.request.user, client=client)

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
            dette_initiale = self.get_object()
            try:
                client = Client.objects.select_for_update().get(
                    pk=dette_initiale.client_id, commercant=request.user, actif=True
                )
            except Client.DoesNotExist as erreur:
                raise serializers.ValidationError({"client": "Ce client est archivé ou introuvable."}) from erreur
            dette = Dette.objects.select_for_update().get(
                pk=dette_initiale.pk, commercant=request.user, client=client
            )
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            nouveau_montant = serializer.validated_data["nouveau_montant"]
            if nouveau_montant == dette.montant:
                raise serializers.ValidationError({"nouveau_montant": "Le nouveau montant doit être différent."})
            total_dettes = Dette.objects.filter(client=client).aggregate(total=Sum("montant"))["total"] or Decimal("0")
            total_paiements = Paiement.objects.filter(client=client).aggregate(total=Sum("montant"))["total"] or Decimal("0")
            if total_dettes - dette.montant + nouveau_montant < total_paiements:
                raise serializers.ValidationError({
                    "nouveau_montant": "Cette correction rendrait le solde global du client négatif."
                })
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
@permission_classes([EstCommercantAuthentifie])
@throttle_classes([ThrottleVerificationDocument])
def document_verification_pdf(request, code):
    """Réserve le reçu financier complet au commerçant authentifié propriétaire."""
    try:
        code_uuid = uuid.UUID(str(code))
    except (ValueError, TypeError, AttributeError):
        raise Http404

    dette = Dette.objects.select_related("commercant", "client").filter(
        code_verification=code_uuid, date_generation__isnull=False, commercant=request.user,
    ).first()
    if dette is not None:
        pdf = _pdf_recu_dette(dette)
        nom_fichier = f"recu-dette-{dette.pk}.pdf"
    else:
        demande = DemandePaiementManuel.objects.select_related("commercant", "plan").filter(
            code_verification=code_uuid,
            statut=DemandePaiementManuel.Statut.VALIDEE,
            date_generation__isnull=False,
            commercant=request.user,
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
class PaiementViewSet(CreationIdempotenteMixin, mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    operation_idempotente = "paiement"
    throttle_scope = "paiement"
    serializer_class = PaiementSerializer
    queryset = Paiement.objects.none()
    lookup_value_regex = r"\d+"
    permission_classes = [EstCommercantAuthentifie, AbonnementAutoriseEcriture]

    def get_queryset(self):
        return Paiement.objects.filter(commercant=self.request.user).select_related("client")

    def perform_create(self, serializer):
        client_id = serializer.validated_data["client"].pk
        with transaction.atomic():
            try:
                client = Client.objects.select_for_update().get(
                    pk=client_id, commercant=self.request.user, actif=True
                )
            except Client.DoesNotExist as erreur:
                raise serializers.ValidationError({"client": "Ce client est archivé ou introuvable."}) from erreur
            montant = serializer.validated_data["montant"]
            # Le verrou sur le client sérialise dettes, corrections et paiements.
            if montant > client.solde:
                raise serializers.ValidationError({
                    "montant": "Le paiement dépasse le solde dû par ce client."
                })
            serializer.save(commercant=self.request.user, client=client)


@extend_schema(tags=["Tableau de bord"], summary="Afficher les indicateurs du commerçant", responses={200: OpenApiTypes.OBJECT, 401: EXEMPLE_NON_AUTORISE}, examples=[OpenApiExample("Indicateurs", value={"ventes_jour": "25000.00", "ventes_semaine": "85000.00", "ventes_mois": "260000.00", "benefice_brut_jour": "7500.00", "benefice_brut_semaine": "24000.00", "benefice_brut_mois": "71000.00", "produits_en_rupture": [], "total_dettes_en_cours": "12000.00"}, response_only=True)])
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

    def indicateurs_cout(debut):
        periode = ventes.filter(date__gte=debut)
        return periode.aggregate(
            nombre_total=Count("id"),
            nombre_avec_cout=Count("id", filter=Q(prix_achat_unitaire__isnull=False)),
            revenus=Coalesce(Sum("total"), 0, output_field=champ_montant),
            cout=Coalesce(
                Sum(
                    F("prix_achat_unitaire") * F("quantite"),
                    filter=Q(prix_achat_unitaire__isnull=False),
                    output_field=champ_montant,
                ),
                0,
                output_field=champ_montant,
            ),
        )

    cout_jour = indicateurs_cout(debut_jour)
    cout_semaine = indicateurs_cout(debut_semaine)
    cout_mois = indicateurs_cout(debut_mois)

    ventes_journalieres = ventes.filter(date__gte=debut_semaine).annotate(
        jour_local=TruncDate("date", tzinfo=timezone.get_current_timezone()),
    ).values("jour_local").annotate(total=Sum("total")).order_by("jour_local")
    par_date = {ligne["jour_local"]: ligne["total"] for ligne in ventes_journalieres}
    ventes_semaine_jour = [
        {"jour_semaine": index, "total": par_date.get((debut_semaine + timedelta(days=index)).date(), Decimal("0"))}
        for index in range(7)
    ]

    produits_alerte = Produit.objects.filter(
        commercant=commercant, actif=True, quantite_stock__lte=F("seuil_alerte")
    ).values("id", "nom", "quantite_stock", "seuil_alerte").order_by("quantite_stock", "nom")
    produits_alerte_total = produits_alerte.count()
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
        "cout_ventes_jour": cout_jour["cout"],
        "cout_ventes_semaine": cout_semaine["cout"],
        "cout_ventes_mois": cout_mois["cout"],
        # Ne pas afficher un bénéfice partiel comme s'il représentait toute la période.
        "benefice_brut_jour": cout_jour["revenus"] - cout_jour["cout"] if cout_jour["nombre_total"] and cout_jour["nombre_total"] == cout_jour["nombre_avec_cout"] else None,
        "benefice_brut_semaine": cout_semaine["revenus"] - cout_semaine["cout"] if cout_semaine["nombre_total"] and cout_semaine["nombre_total"] == cout_semaine["nombre_avec_cout"] else None,
        "benefice_brut_mois": cout_mois["revenus"] - cout_mois["cout"] if cout_mois["nombre_total"] and cout_mois["nombre_total"] == cout_mois["nombre_avec_cout"] else None,
        "ventes_sans_cout_jour": cout_jour["nombre_total"] - cout_jour["nombre_avec_cout"],
        "ventes_sans_cout_semaine": cout_semaine["nombre_total"] - cout_semaine["nombre_avec_cout"],
        "ventes_sans_cout_mois": cout_mois["nombre_total"] - cout_mois["nombre_avec_cout"],
        "ventes_semaine_jour": ventes_semaine_jour,
        # Le dashboard conserve une réponse bornée ; la page Produits permet
        # de consulter toutes les ruptures avec pagination serveur.
        "produits_en_rupture": list(produits_alerte[:100]),
        "produits_en_rupture_total": produits_alerte_total,
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
    donnees["mode_paiement"] = "fedapay"
    return Response(donnees)


@extend_schema(tags=["Abonnement"], summary="Lister les formules disponibles", responses={200: _schema_liste_paginee("PlansPaginees", PlanSerializer)})
@api_view(["GET"])
@permission_classes([AllowAny])
def plans(request):
    """Publie les tarifs actifs afin que le site vitrine lise le prix du backend."""
    offres = Plan.objects.filter(actif=True, prix__gt=0)
    return _reponse_liste_paginee(request, offres, PlanSerializer)


@extend_schema(tags=["Abonnement"], summary="Consulter l'offre d'essai publique", responses={200: OffreEssaiReponseSerializer})
@api_view(["GET"])
@permission_classes([AllowAny])
def offre_essai(request):
    """Expose uniquement la disponibilité et la durée publique de l'essai."""
    configuration = ConfigurationEssai.obtenir()
    return Response({"actif": configuration.actif, "duree_jours": configuration.duree_jours if configuration.actif else 0})


@extend_schema(tags=["Abonnement"], summary="Consulter l'historique des paiements d'abonnement", responses={200: _schema_liste_paginee("HistoriqueAbonnementsPagine", PaiementAbonnementHistoriqueSerializer), 401: EXEMPLE_NON_AUTORISE})
@api_view(["GET"])
@permission_classes([EstCommercantAuthentifie])
def historique_abonnement(request):
    paiements = PaiementAbonnementHistorique.objects.filter(commercant=request.user).select_related("plan")
    return _reponse_liste_paginee(request, paiements, PaiementAbonnementHistoriqueSerializer)


@extend_schema(tags=["Abonnement"], summary="Créer un paiement FedaPay pour une formule")
@api_view(["POST"])
@permission_classes([EstCommercantAuthentifie])
def creer_paiement_abonnement(request):
    if not settings.FEDAPAY_SECRET_KEY:
        return Response({"detail": "Le paiement FedaPay n'est pas encore configuré."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    try:
        plan_id = int(request.data.get("plan_id"))
    except (TypeError, ValueError):
        return Response({"detail": "Choisissez une formule valide."}, status=status.HTTP_400_BAD_REQUEST)
    plan = Plan.objects.filter(pk=plan_id, actif=True, prix__gt=0).first()
    if plan is None:
        return Response({"detail": "Cette formule n'est pas disponible."}, status=status.HTTP_404_NOT_FOUND)
    if plan.prix != plan.prix.to_integral_value():
        return Response({"detail": "Le prix de cette formule doit être un montant entier en FCFA."}, status=status.HTTP_400_BAD_REQUEST)
    if PaiementAbonnementHistorique.objects.filter(commercant=request.user, statut=PaiementAbonnementHistorique.Statut.EN_ATTENTE).exists():
        return Response({"detail": "Un paiement est déjà en attente. Revenez à la page abonnement pour vérifier son état."}, status=status.HTTP_409_CONFLICT)
    paiement = PaiementAbonnementHistorique.objects.create(commercant=request.user, plan=plan, montant=plan.prix)
    try:
        url = creer_paiement(paiement)
    except APIException:
        paiement.statut = PaiementAbonnementHistorique.Statut.ECHOUE
        paiement.save(update_fields=["statut"])
        raise
    return Response({"reference": str(paiement.reference), "checkout_url": url}, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Abonnement"], summary="Vérifier l'état d'un paiement FedaPay")
@api_view(["GET"])
@permission_classes([EstCommercantAuthentifie])
def verifier_paiement_abonnement(request, reference):
    paiement = PaiementAbonnementHistorique.objects.filter(reference=reference, commercant=request.user).first()
    if paiement is None:
        return Response({"detail": "Paiement introuvable."}, status=status.HTTP_404_NOT_FOUND)
    if paiement.statut == PaiementAbonnementHistorique.Statut.EN_ATTENTE:
        paiement = actualiser_paiement(paiement)
    return Response({"reference": str(paiement.reference), "statut": paiement.statut})


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def webhook_fedapay(request):
    """Vérifie la signature puis relit la transaction chez FedaPay avant traitement."""
    secret = settings.FEDAPAY_WEBHOOK_SECRET
    signature_header = request.headers.get("X-FEDAPAY-SIGNATURE", "")
    parties = dict(item.split("=", 1) for item in signature_header.split(",") if "=" in item)
    try:
        horodatage = int(parties["t"])
        signature = parties["s"]
    except (KeyError, ValueError):
        return Response({"detail": "Signature de webhook invalide."}, status=status.HTTP_400_BAD_REQUEST)
    corps_brut = request.body.decode("utf-8", errors="strict")
    attendu = hmac.new(secret.encode(), f"{horodatage}.{corps_brut}".encode(), hashlib.sha256).hexdigest() if secret else ""
    if not secret or abs(int(unix_time.time()) - horodatage) > 300 or not hmac.compare_digest(signature, attendu):
        return Response({"detail": "Signature de webhook invalide."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        corps = json.loads(corps_brut)
    except json.JSONDecodeError:
        return Response({"detail": "Événement invalide."}, status=status.HTTP_400_BAD_REQUEST)
    transaction_data = corps.get("object") or corps.get("entity") or corps.get("transaction") or corps.get("data") or corps
    if isinstance(transaction_data, str):
        try:
            transaction_data = json.loads(transaction_data)
        except json.JSONDecodeError:
            return Response({"detail": "Événement invalide."}, status=status.HTTP_400_BAD_REQUEST)
    if isinstance(transaction_data, dict) and isinstance(transaction_data.get("object"), dict):
        transaction_data = transaction_data["object"]
    identifiant = transaction_data.get("id") if isinstance(transaction_data, dict) else None
    paiement = PaiementAbonnementHistorique.objects.filter(fedapay_transaction_id=str(identifiant)).first() if identifiant else None
    if paiement is None:
        return Response(status=status.HTTP_200_OK)
    actualiser_paiement(paiement)
    return Response(status=status.HTTP_200_OK)


@extend_schema(
    methods=["GET"], tags=["Abonnement"], summary="Lister les demandes de paiement du commerçant connecté",
    responses={200: _schema_liste_paginee("DemandesPaiementPaginees", DemandePaiementManuelSerializer), 401: EXEMPLE_NON_AUTORISE},
)
@extend_schema(
    methods=["POST"], tags=["Abonnement"], summary="Soumettre une demande de paiement manuel",
    request=DemandePaiementManuelSerializer,
    responses={201: DemandePaiementManuelSerializer, 400: EXEMPLE_ERREUR, 409: EXEMPLE_ERREUR, 503: EXEMPLE_ERREUR},
)
@api_view(["GET", "POST"])
@permission_classes([EstCommercantAuthentifie])
def demandes_paiement_abonnement(request):
    """Crée une demande manuelle ou renvoie uniquement l'historique du compte courant."""
    if request.method == "GET":
        demandes = DemandePaiementManuel.objects.filter(commercant=request.user).select_related("plan")
        return _reponse_liste_paginee(request, demandes, DemandePaiementManuelSerializer)
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


@extend_schema(
    tags=["Abonnement"], summary="Télécharger la preuve d'une demande de paiement",
    responses={200: OpenApiResponse(response=OpenApiTypes.BINARY, description="Fichier de preuve du commerçant ou accessible au personnel autorisé."), 404: EXEMPLE_ERREUR},
)
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


@extend_schema(
    tags=["Abonnement"], summary="Télécharger le reçu PDF d'un paiement validé",
    responses={200: OpenApiResponse(response=OpenApiTypes.BINARY, description="Reçu PDF certifié."), 404: EXEMPLE_ERREUR},
)
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


@extend_schema(
    tags=["Système"], summary="Vérifier la disponibilité de l'API et de la base",
    responses={200: SanteReponseSerializer, 503: SanteReponseSerializer},
)
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


@extend_schema(
    tags=["Compte"], summary="Télécharger une copie PDF des données du compte",
    responses={200: OpenApiResponse(response=OpenApiTypes.BINARY, description="Export PDF personnel."), 401: EXEMPLE_NON_AUTORISE},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_compte(request):
    """Télécharge les données du commerçant connecté dans un PDF paginé."""
    contenu = construire_export_pdf(request.user)
    reponse = HttpResponse(contenu, content_type="application/pdf")
    reponse["Content-Disposition"] = 'attachment; filename="export-donnees-commerce.pdf"'
    reponse["Cache-Control"] = "private, no-store"
    return reponse


@extend_schema(
    tags=["Compte"], summary="Consulter ou modifier son profil utilisateur",
    request=ProfilSerializer,
    responses={200: ProfilReponseSerializer, 400: EXEMPLE_ERREUR, 401: EXEMPLE_NON_AUTORISE},
)
@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def profil_courant(request):
    """Ne lit et ne modifie que le compte porté par la session courante."""
    utilisateur = request.user
    if request.method == "GET":
        return Response(ProfilSerializer(utilisateur, context={"request": request}).data)

    serializer = ProfilSerializer(utilisateur, data=request.data, partial=True, context={"request": request})
    serializer.is_valid(raise_exception=True)
    donnees = serializer.validated_data.copy()
    avant = {}
    apres = {}
    logo_present_avant = bool(utilisateur.logo_profil)
    for champ in ("nom_affiche", "telephone", "adresse", "ville"):
        if champ not in donnees:
            continue
        valeur_avant = ProfilSerializer().get_nom_affiche(utilisateur) if champ == "nom_affiche" else getattr(utilisateur, champ)
        avant[champ] = valeur_avant

    logo_modifie = "logo" in donnees
    if logo_modifie and not settings.CLOUDINARY_CONFIGURE and not settings.LOGO_LOCAL_DEVELOPPEMENT:
        return Response(
            {"detail": "Le stockage des images n’est pas configuré. Retirez l’image pour enregistrer les autres informations."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    with transaction.atomic():
        try:
            serializer.save()
        except Exception:
            if not logo_modifie:
                raise
            # Un incident Cloudinary ne doit pas devenir une page HTML 500.
            logger.error("Échec du stockage Cloudinary pendant la mise à jour du profil.")
            return Response(
                {"detail": "La photo ne peut pas être enregistrée pour le moment. Réessayez ou retirez-la pour enregistrer le reste du profil."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        for champ in avant:
            apres[champ] = ProfilSerializer().get_nom_affiche(utilisateur) if champ == "nom_affiche" else getattr(utilisateur, champ)
        if logo_modifie:
            avant["logo"] = "présent" if logo_present_avant else "absent"
            apres["logo"] = "remplacé" if logo_present_avant else "présent"
        if avant and avant != apres:
            enregistrer_evenement(
                commercant=utilisateur,
                utilisateur=utilisateur,
                action=JournalAudit.Action.MODIFICATION,
                objet_type="ProfilUtilisateur",
                objet_id=utilisateur.pk,
                anciennes_valeurs=avant,
                nouvelles_valeurs=apres,
                adresse_ip=request._request.META.get("REMOTE_ADDR"),
            )
    return Response(ProfilSerializer(utilisateur, context={"request": request}).data)


@extend_schema(
    tags=["Compte"], summary="Supprimer le logo de son profil", request=None,
    responses={200: ProfilReponseSerializer, 401: EXEMPLE_NON_AUTORISE, 503: EXEMPLE_ERREUR},
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def supprimer_logo_profil_courant(request):
    """Retire uniquement le logo du compte authentifié."""
    utilisateur = request.user
    if not utilisateur.logo_profil:
        return Response(ProfilSerializer(utilisateur).data)
    try:
        supprimer_logo_profil(utilisateur)
    except Exception:
        logger.warning("Échec de suppression du logo Cloudinary du profil.")
        return Response(
            {"detail": "Le logo n'a pas pu être supprimé pour le moment. Réessayez."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    enregistrer_evenement(
        commercant=utilisateur,
        utilisateur=utilisateur,
        action=JournalAudit.Action.MODIFICATION,
        objet_type="ProfilUtilisateur",
        objet_id=utilisateur.pk,
        anciennes_valeurs={"logo": "présent"},
        nouvelles_valeurs={"logo": "absent"},
        adresse_ip=request._request.META.get("REMOTE_ADDR"),
    )
    return Response(ProfilSerializer(utilisateur).data)


@extend_schema(
    tags=["Compte"], summary="Supprimer le compte après confirmation du mot de passe",
    request=ConfirmationSuppressionSerializer,
    responses={200: ReponseDetailSerializer, 400: EXEMPLE_ERREUR, 401: EXEMPLE_NON_AUTORISE},
)
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
    try:
        supprimer_logo_profil(utilisateur)
    except Exception:
        logger.warning("Échec de suppression du logo avant la suppression du compte.")
        return Response(
            {"detail": "Le logo du profil n'a pas pu être supprimé. Réessayez avant de supprimer le compte."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    with transaction.atomic(), suspendre_audit():
        # Supprime les traces historiques sous email et sous l'ancien identifiant téléphone.
        identifiants = [utilisateur.email]
        if utilisateur.telephone:
            identifiants.append(utilisateur.telephone)
        AccessAttempt.objects.filter(username__in=identifiants).delete()
        AccessFailureLog.objects.filter(username__in=identifiants).delete()
        AccessLog.objects.filter(username__in=identifiants).delete()
        JournalAudit.objects.filter(commercant=utilisateur).delete()
        # Le FK Vente.produit est PROTECT. Les dettes et paiements précèdent
        # aussi la suppression du commerçant depuis le passage de Client en PROTECT.
        Vente.objects.filter(commercant=utilisateur).delete()
        Dette.objects.filter(commercant=utilisateur).delete()
        Paiement.objects.filter(commercant=utilisateur).delete()
        # Les nouveaux journaux protègent leurs références produit/achat.
        # Ils sont effacés ici avant la suppression définitive du compte.
        MouvementStock.objects.filter(commercant=utilisateur).delete()
        LigneApprovisionnement.objects.filter(approvisionnement__commercant=utilisateur).delete()
        Approvisionnement.objects.filter(commercant=utilisateur).delete()
        Fournisseur.objects.filter(commercant=utilisateur).delete()
        utilisateur.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
