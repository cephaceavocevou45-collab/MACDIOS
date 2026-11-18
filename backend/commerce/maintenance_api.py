"""API de consultation publique et de pilotage du mode maintenance."""

import hmac
import logging
import os

from django.conf import settings
from django.db import transaction
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .admin_serializers import ModeMaintenanceSerializer
from .audit import enregistrer_evenement
from .maintenance import lire_mode_maintenance, publier_mode_maintenance
from .models import JournalAudit, ModeMaintenance
from .permissions import SuperAdminUniquement

logger = logging.getLogger(__name__)


class StatutMaintenanceSerializer(serializers.Serializer):
    actif = serializers.BooleanField()
    message = serializers.CharField()


class ReponseMaintenanceDeploiementSerializer(serializers.Serializer):
    actif = serializers.BooleanField()
    message = serializers.CharField()
    etat_precedent = serializers.JSONField()


class VersionDeployeeSerializer(serializers.Serializer):
    commit = serializers.CharField()


@extend_schema(
    tags=["Admin"],
    summary="Consulter le statut public de maintenance",
    responses=StatutMaintenanceSerializer,
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def statut_maintenance(request):
    """Ne révèle que l'état et le message destinés à l'ensemble des visiteurs."""
    return Response(lire_mode_maintenance())


class ModeMaintenanceBackOffice(APIView):
    """Activation réservée au super-admin ; le back-office reste accessible."""

    permission_classes = [SuperAdminUniquement]
    serializer_class = ModeMaintenanceSerializer

    @extend_schema(tags=["Admin"], summary="Lire le mode maintenance")
    def get(self, request):
        configuration, _ = ModeMaintenance.objects.get_or_create(pk=1)
        return Response(ModeMaintenanceSerializer(configuration).data)

    @extend_schema(tags=["Admin"], summary="Activer ou désactiver le mode maintenance", request=ModeMaintenanceSerializer)
    def patch(self, request):
        with transaction.atomic():
            configuration = ModeMaintenance.objects.select_for_update().filter(pk=1).first()
            if configuration is None:
                configuration = ModeMaintenance(pk=1)
            avant = {"actif": configuration.actif, "message": configuration.message}
            serializer = ModeMaintenanceSerializer(configuration, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            configuration = serializer.save(modifie_par=request.user)
            apres = {"actif": configuration.actif, "message": configuration.message}

        publier_mode_maintenance(**apres)
        if avant != apres:
            enregistrer_evenement(
                commercant=request.user,
                utilisateur=request.user,
                action=JournalAudit.Action.MODIFICATION,
                objet_type="ModeMaintenance",
                objet_id="1",
                anciennes_valeurs=avant,
                nouvelles_valeurs=apres,
                adresse_ip=request.META.get("REMOTE_ADDR"),
            )
        return Response(ModeMaintenanceSerializer(configuration).data)


class MaintenanceDeploiement(APIView):
    """Point de contrôle machine, limité à l'activation et à la restauration."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Admin"],
        summary="Piloter la maintenance autour d'un déploiement CI autorisé",
        responses=ReponseMaintenanceDeploiementSerializer,
        request=inline_serializer(
            name="MaintenanceDeploiementRequete",
            fields={
                "action": serializers.ChoiceField(choices=["activer", "restaurer"]),
                "etat_precedent": serializers.JSONField(required=False),
            },
        ),
    )
    def post(self, request):
        """Le jeton n'est jamais journalisé ni retourné."""
        jeton_attendu = getattr(settings, "DEPLOYMENT_MAINTENANCE_TOKEN", "")
        autorisation = request.headers.get("Authorization", "")
        jeton_recu = autorisation[7:] if autorisation.startswith("Bearer ") else ""
        if len(jeton_attendu) < 32:
            return Response({"detail": "Le contrôle de déploiement n'est pas configuré."}, status=503)
        if not jeton_recu or not hmac.compare_digest(jeton_attendu, jeton_recu):
            return Response({"detail": "Autorisation invalide."}, status=403)

        action = request.data.get("action")
        if action not in {"activer", "restaurer"}:
            return Response({"detail": "Action de déploiement invalide."}, status=400)

        with transaction.atomic():
            configuration = ModeMaintenance.objects.select_for_update().filter(pk=1).first()
            if configuration is None:
                configuration = ModeMaintenance(pk=1)
            avant = {"actif": configuration.actif, "message": configuration.message}

            if action == "activer":
                etat_precedent = avant
                configuration.actif = True
                configuration.message = "Mise à jour en cours. Merci de revenir dans quelques instants."
            else:
                etat_precedent = request.data.get("etat_precedent")
                if (
                    not isinstance(etat_precedent, dict)
                    or not isinstance(etat_precedent.get("actif"), bool)
                    or not isinstance(etat_precedent.get("message"), str)
                    or not etat_precedent["message"].strip()
                    or len(etat_precedent["message"]) > 300
                ):
                    return Response({"detail": "L'état précédent fourni est invalide."}, status=400)
                configuration.actif = etat_precedent["actif"]
                configuration.message = etat_precedent["message"].strip()

            configuration.modifie_par = None
            configuration.save(update_fields=["actif", "message", "modifie_par", "modifie_le"])
            apres = {"actif": configuration.actif, "message": configuration.message}

        publier_mode_maintenance(**apres)
        if avant != apres:
            enregistrer_evenement(
                commercant=None,
                utilisateur=None,
                action=JournalAudit.Action.MODIFICATION,
                objet_type="ModeMaintenance",
                objet_id="1",
                anciennes_valeurs={**avant, "source": "automatisation_deploiement"},
                nouvelles_valeurs={**apres, "source": "automatisation_deploiement"},
            )
        logger.info("Maintenance de déploiement mise à jour : action=%s actif=%s", action, apres["actif"])
        return Response({**apres, "etat_precedent": etat_precedent})


@extend_schema(
    tags=["Sante"],
    summary="Consulter la version déployée, sans données internes",
    responses=VersionDeployeeSerializer,
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def version_deployee(request):
    """Expose uniquement le SHA public du commit pour vérifier la fin d'un déploiement."""
    commit = os.environ.get("APP_RELEASE_SHA", "").strip()
    return Response({"commit": commit or "unknown"}, headers={"Cache-Control": "no-store, max-age=0"})
