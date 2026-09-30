"""API séparée de gestion de la plateforme et à permissions individuelles."""

from datetime import datetime, time
from decimal import Decimal
import logging
import mimetypes
import secrets
import uuid
from urllib.parse import urlencode
from xml.sax.saxutils import escape

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.db.models import DecimalField, Q, Sum
from django.db.models.functions import Coalesce
from django.http import FileResponse, Http404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import generics, serializers, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from notifications.email import ErreurEnvoiEmail, envoyer_email

from .admin_serializers import (
    AuditPlateformeSerializer, ConfigurationEssaiSerializer, DemandePaiementAdminSerializer, MotifRejetAdminSerializer,
    SousAdminCreationSerializer, SousAdminModificationSerializer, SousAdminSerializer,
    UtilisateurBackOfficeSerializer,
)
from .audit import enregistrer_evenement
from .models import (
    Abonnement, Commercant, ConfigurationEssai, DemandePaiementManuel, Dette, JournalAudit, Paiement,
    PaiementAbonnementHistorique, ProfilSousAdmin, Vente,
)
from .pagination import PaginationAudit
from .permissions import PermissionBackOffice, SuperAdminUniquement
from .services.paiement_manuel import rejeter_demande, valider_demande
from .serializers import ConnexionSerializer
from .throttles import ThrottleConnexionAdmin


logger = logging.getLogger(__name__)


def _montant_texte(montant):
    """Retourne un montant avec deux décimales stables dans la réponse JSON."""
    return f"{montant:.2f}"


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([ThrottleConnexionAdmin])
def connexion_backoffice(request):
    """Délivre un JWT uniquement aux comptes administratifs actifs."""
    serializer = ConnexionSerializer(data=request.data, context={"request": request})
    if not serializer.is_valid():
        return Response({"detail": "Email ou mot de passe incorrect."}, status=status.HTTP_400_BAD_REQUEST)
    administrateur = serializer.validated_data["user"]
    if not administrateur.is_staff or not (administrateur.is_superuser or hasattr(administrateur, "profil_sous_admin")):
        return Response({"detail": "Email ou mot de passe incorrect."}, status=status.HTTP_400_BAD_REQUEST)
    droits = ["*"] if administrateur.is_superuser else administrateur.profil_sous_admin.permissions
    enregistrer_evenement(
        commercant=administrateur, utilisateur=administrateur,
        action=JournalAudit.Action.CONNEXION_REUSSIE,
        objet_type="AuthentificationAdmin", objet_id=administrateur.pk,
        nouvelles_valeurs={"role": "super_admin" if administrateur.is_superuser else "sous_admin"},
        adresse_ip=request.META.get("REMOTE_ADDR"),
    )
    jeton = RefreshToken.for_user(administrateur)
    return Response({
        "access": str(jeton.access_token),
        "refresh": str(jeton),
        "administrateur": {
            "id": str(administrateur.pk),
            "email": administrateur.email,
            "nom": administrateur.profil_sous_admin.nom if not administrateur.is_superuser else administrateur.get_full_name() or administrateur.nom_boutique,
            "super_admin": administrateur.is_superuser,
            "permissions": droits,
        },
    })


class VueBackOffice(APIView):
    """Base de toutes les vues protégées de l'API d'administration."""

    permission_classes = [PermissionBackOffice]


class ConfigurationOffreEssaiBackOffice(APIView):
    """Consultation et modification réservées au super-admin."""

    permission_classes = [SuperAdminUniquement]

    def get(self, request):
        return Response(ConfigurationEssaiSerializer(ConfigurationEssai.obtenir()).data)

    def patch(self, request):
        configuration = ConfigurationEssai.obtenir()
        avant = {"actif": configuration.actif, "duree_jours": configuration.duree_jours}
        serializer = ConfigurationEssaiSerializer(configuration, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        configuration = serializer.save()
        apres = {"actif": configuration.actif, "duree_jours": configuration.duree_jours}
        if avant != apres:
            enregistrer_evenement(
                commercant=request.user, utilisateur=request.user,
                action=JournalAudit.Action.MODIFICATION_OFFRE_ESSAI,
                objet_type="ConfigurationEssai", objet_id="1",
                anciennes_valeurs=avant, nouvelles_valeurs=apres,
                adresse_ip=request.META.get("REMOTE_ADDR"),
            )
        return Response(ConfigurationEssaiSerializer(configuration).data)


class StatistiquesPlateforme(VueBackOffice):
    permission_requise = "voir_statistiques"

    def get(self, request):
        maintenant = timezone.now()
        debut_mois = timezone.make_aware(datetime.combine(timezone.localdate().replace(day=1), time.min))
        commercants = Commercant.objects.filter(is_staff=False, is_superuser=False)
        abonnements = Abonnement.objects.filter(commercant__in=commercants)
        montant = Sum("montant")
        champ_montant = DecimalField(max_digits=16, decimal_places=2)
        revenus_transactions = PaiementAbonnementHistorique.objects.filter(statut=PaiementAbonnementHistorique.Statut.REUSSI)
        revenus_manuels = DemandePaiementManuel.objects.filter(statut=DemandePaiementManuel.Statut.VALIDEE)
        total_transactions = revenus_transactions.aggregate(total=Coalesce(montant, Decimal("0"), output_field=champ_montant))["total"]
        total_manuels = revenus_manuels.aggregate(total=Coalesce(montant, Decimal("0"), output_field=champ_montant))["total"]
        mois_transactions = revenus_transactions.filter(date_validation__gte=debut_mois).aggregate(total=Coalesce(montant, Decimal("0"), output_field=champ_montant))["total"]
        mois_manuels = revenus_manuels.filter(date_decision__gte=debut_mois).aggregate(total=Coalesce(montant, Decimal("0"), output_field=champ_montant))["total"]
        total_dettes = Dette.objects.filter(commercant__in=commercants).aggregate(total=Coalesce(Sum("montant"), Decimal("0"), output_field=champ_montant))["total"]
        total_paiements = Paiement.objects.filter(commercant__in=commercants).aggregate(total=Coalesce(Sum("montant"), Decimal("0"), output_field=champ_montant))["total"]
        return Response({
            "nombre_commercants": commercants.count(),
            "commercants_actifs": commercants.filter(is_active=True).count(),
            "commercants_en_essai": abonnements.filter(statut=Abonnement.Statut.ESSAI, date_fin__gt=maintenant).count(),
            "commercants_expires": abonnements.filter(Q(statut=Abonnement.Statut.EXPIRE) | Q(date_fin__lte=maintenant)).count(),
            "revenus_mois": _montant_texte(mois_transactions + mois_manuels),
            "revenus_totaux": _montant_texte(total_transactions + total_manuels),
            "ventes_enregistrees": Vente.objects.filter(commercant__in=commercants).count(),
            "dettes_en_cours": _montant_texte(total_dettes - total_paiements),
        })


class ListeUtilisateursBackOffice(generics.ListAPIView):
    permission_classes = [PermissionBackOffice]
    permission_requise = "voir_utilisateurs"
    serializer_class = UtilisateurBackOfficeSerializer
    pagination_class = PaginationAudit

    def get_queryset(self):
        queryset = Commercant.objects.filter(is_staff=False, is_superuser=False).select_related("abonnement__plan")
        recherche = self.request.query_params.get("recherche", "").strip()
        if recherche:
            queryset = queryset.filter(Q(email__icontains=recherche) | Q(nom_boutique__icontains=recherche))
        statut = self.request.query_params.get("statut_abonnement")
        if statut:
            if statut not in Abonnement.Statut.values:
                raise serializers.ValidationError({"statut_abonnement": "Statut invalide."})
            maintenant = timezone.now()
            if statut == Abonnement.Statut.EXPIRE:
                queryset = queryset.filter(Q(abonnement__statut=statut) | Q(abonnement__date_fin__lte=maintenant))
            elif statut == Abonnement.Statut.ACTIF:
                queryset = queryset.filter(abonnement__statut=statut, abonnement__date_fin__gt=maintenant)
            else:
                queryset = queryset.filter(abonnement__statut=statut, abonnement__date_fin__gt=maintenant)
        return queryset.order_by("-date_joined")


class ActionUtilisateurBackOffice(VueBackOffice):
    permission_requise = "suspendre_utilisateur"

    def post(self, request, pk, action):
        try:
            with transaction.atomic():
                utilisateur = Commercant.objects.select_for_update().get(pk=pk, is_staff=False, is_superuser=False)
                if action == "suspendre":
                    motif = request.data.get("motif", "").strip()
                    if not motif:
                        return Response({"detail": "Le motif de suspension est obligatoire."}, status=status.HTTP_400_BAD_REQUEST)
                    if len(motif) > 250:
                        return Response({"detail": "Le motif ne peut dépasser 250 caractères."}, status=status.HTTP_400_BAD_REQUEST)
                    anciennes = {"actif": utilisateur.is_active, "motif": utilisateur.motif_suspension}
                    utilisateur.is_active = False
                    utilisateur.motif_suspension = motif
                    utilisateur.suspendu_le = timezone.now()
                    utilisateur.suspendu_par = request.user
                    utilisateur.save(update_fields=["is_active", "motif_suspension", "suspendu_le", "suspendu_par"])
                    action_audit = JournalAudit.Action.SUSPENSION_UTILISATEUR
                    nouvelles = {"actif": False, "motif": motif}
                else:
                    anciennes = {"actif": utilisateur.is_active, "motif": utilisateur.motif_suspension}
                    utilisateur.is_active = True
                    utilisateur.motif_suspension = ""
                    utilisateur.suspendu_le = None
                    utilisateur.suspendu_par = None
                    utilisateur.save(update_fields=["is_active", "motif_suspension", "suspendu_le", "suspendu_par"])
                    action_audit = JournalAudit.Action.REACTIVATION_UTILISATEUR
                    nouvelles = {"actif": True}
                enregistrer_evenement(
                    commercant=utilisateur, utilisateur=request.user, action=action_audit,
                    objet_type="Commercant", objet_id=utilisateur.pk,
                    anciennes_valeurs=anciennes, nouvelles_valeurs=nouvelles,
                    adresse_ip=request.META.get("REMOTE_ADDR"),
                )
        except Commercant.DoesNotExist:
            raise Http404
        return Response(UtilisateurBackOfficeSerializer(utilisateur).data)


class PaiementsEnAttenteBackOffice(generics.ListAPIView):
    permission_classes = [PermissionBackOffice]
    permission_requise = "valider_paiements"
    serializer_class = DemandePaiementAdminSerializer
    pagination_class = PaginationAudit

    def get_queryset(self):
        return DemandePaiementManuel.objects.filter(
            statut=DemandePaiementManuel.Statut.EN_ATTENTE,
        ).select_related("commercant", "plan").order_by("date_demande")


class DecisionPaiementBackOffice(VueBackOffice):
    permission_requise = "valider_paiements"

    def post(self, request, pk, action):
        demande = DemandePaiementManuel.objects.filter(pk=pk).first()
        if demande is None:
            raise Http404
        if action == "valider":
            demande, modifiee = valider_demande(demande.pk, request.user)
            if not modifiee:
                return Response({"detail": "Cette demande a déjà été traitée."}, status=status.HTTP_409_CONFLICT)
        else:
            serializer = MotifRejetAdminSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            demande, modifiee = rejeter_demande(demande.pk, request.user, serializer.validated_data["motif"])
            if not modifiee:
                return Response({"detail": "Cette demande a déjà été traitée."}, status=status.HTTP_409_CONFLICT)
        return Response(DemandePaiementAdminSerializer(demande).data)


class PreuvePaiementBackOffice(VueBackOffice):
    permission_requise = "valider_paiements"

    def get(self, request, pk):
        demande = DemandePaiementManuel.objects.filter(pk=pk).first()
        if demande is None or not demande.preuve:
            raise Http404
        type_fichier = mimetypes.guess_type(demande.preuve.name)[0] or "application/octet-stream"
        try:
            fichier = demande.preuve.open("rb")
        except OSError:
            return Response({"detail": "La preuve de paiement est temporairement indisponible."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        reponse = FileResponse(fichier, content_type=type_fichier, as_attachment=True, filename="preuve-paiement")
        reponse["Cache-Control"] = "private, no-store"
        return reponse


class AuditPlateformeBackOffice(generics.ListAPIView):
    permission_classes = [PermissionBackOffice]
    permission_requise = "voir_audit"
    serializer_class = AuditPlateformeSerializer
    pagination_class = PaginationAudit

    def get_queryset(self):
        queryset = JournalAudit.objects.select_related("commercant", "utilisateur")
        commercant = self.request.query_params.get("commercant")
        admin = self.request.query_params.get("admin")
        action = self.request.query_params.get("action")
        date_debut = self.request.query_params.get("date_debut")
        date_fin = self.request.query_params.get("date_fin")
        if commercant:
            try:
                uuid.UUID(commercant)
            except (ValueError, TypeError, AttributeError):
                queryset = queryset.filter(commercant__email__iexact=commercant)
            else:
                queryset = queryset.filter(commercant_id=commercant)
        if admin:
            try:
                uuid.UUID(admin)
            except (ValueError, TypeError, AttributeError):
                queryset = queryset.filter(utilisateur__email__iexact=admin)
            else:
                queryset = queryset.filter(utilisateur_id=admin)
        if action:
            if action not in JournalAudit.Action.values:
                raise serializers.ValidationError({"action": "Type d'action invalide."})
            queryset = queryset.filter(action=action)
        if date_debut:
            date_parsee = parse_date(date_debut)
            if date_parsee is None:
                raise serializers.ValidationError({"date_debut": "Utilisez le format AAAA-MM-JJ."})
            queryset = queryset.filter(date__date__gte=date_parsee)
        if date_fin:
            date_parsee = parse_date(date_fin)
            if date_parsee is None:
                raise serializers.ValidationError({"date_fin": "Utilisez le format AAAA-MM-JJ."})
            queryset = queryset.filter(date__date__lte=date_parsee)
        return queryset.order_by("-date", "-id")


class GestionSousAdminsBackOffice(APIView):
    permission_classes = [SuperAdminUniquement]

    def get(self, request):
        profils = ProfilSousAdmin.objects.select_related("utilisateur", "cree_par")
        page = PaginationAudit()
        resultat = page.paginate_queryset(profils, request, view=self)
        return page.get_paginated_response(SousAdminSerializer(resultat, many=True).data)

    def post(self, request):
        serializer = SousAdminCreationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data
        if Commercant.objects.filter(email__iexact=donnees["email"]).exists():
            return Response({"email": "Cette adresse email est déjà utilisée."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            utilisateur = Commercant.objects.create_user(
                email=donnees["email"],
                password=secrets.token_urlsafe(48),
                first_name=donnees["nom"],
                nom_boutique=f"Administration — {donnees['nom']}",
                is_staff=True,
                is_superuser=False,
            )
            profil = ProfilSousAdmin.objects.create(
                utilisateur=utilisateur, nom=donnees["nom"],
                permissions=donnees["permissions"], cree_par=request.user,
            )
            enregistrer_evenement(
                commercant=utilisateur, utilisateur=request.user,
                action=JournalAudit.Action.CREATION_SOUS_ADMIN,
                objet_type="ProfilSousAdmin", objet_id=profil.pk,
                nouvelles_valeurs={"email": utilisateur.email, "permissions": profil.permissions},
                adresse_ip=request.META.get("REMOTE_ADDR"),
            )
            transaction.on_commit(lambda: _envoyer_invitation(utilisateur, profil.nom))
        return Response(SousAdminSerializer(profil).data, status=status.HTTP_201_CREATED)


class DetailSousAdminBackOffice(APIView):
    permission_classes = [SuperAdminUniquement]

    def patch(self, request, pk):
        profil = ProfilSousAdmin.objects.select_related("utilisateur").filter(utilisateur_id=pk).first()
        if profil is None:
            raise Http404
        serializer = SousAdminModificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data
        ancien_etat = {"permissions": profil.permissions, "actif": profil.utilisateur.is_active}
        if "permissions" in donnees:
            profil.permissions = donnees["permissions"]
            profil.save(update_fields=["permissions", "date_modification"])
        if "actif" in donnees:
            profil.utilisateur.is_active = donnees["actif"]
            profil.utilisateur.save(update_fields=["is_active"])
        nouvelle_action = (
            JournalAudit.Action.DESACTIVATION_SOUS_ADMIN
            if donnees.get("actif") is False
            else JournalAudit.Action.MODIFICATION_SOUS_ADMIN
        )
        enregistrer_evenement(
            commercant=profil.utilisateur, utilisateur=request.user,
            action=nouvelle_action, objet_type="ProfilSousAdmin", objet_id=profil.pk,
            anciennes_valeurs=ancien_etat,
            nouvelles_valeurs={"permissions": profil.permissions, "actif": profil.utilisateur.is_active},
            adresse_ip=request.META.get("REMOTE_ADDR"),
        )
        return Response(SousAdminSerializer(profil).data)


def _envoyer_invitation(utilisateur, nom):
    """Réutilise le jeton de réinitialisation à durée courte pour définir le mot de passe."""
    identifiant = urlsafe_base64_encode(force_bytes(utilisateur.pk))
    jeton = default_token_generator.make_token(utilisateur)
    lien = f"{settings.FRONTEND_URL.rstrip('/')}/nouveau-mot-de-passe?{urlencode({'uid': identifiant, 'token': jeton})}"
    contenu = (
        "<div style='font-family:Arial,sans-serif;color:#243b36;line-height:1.6'>"
        f"<h1>Invitation au back-office</h1><p>Bonjour {escape(nom)}, votre accès d'administration est prêt.</p>"
        f"<p><a href='{escape(lien)}'>Définir votre mot de passe</a></p>"
        "<p>Ce lien expire après 15 minutes et ne peut être utilisé qu'une fois.</p></div>"
    )
    try:
        envoyer_email(utilisateur.email, "Votre invitation au back-office Nobi", contenu)
    except (ErreurEnvoiEmail, ValueError):
        logger.warning("Échec de l'envoi d'une invitation au back-office.")
