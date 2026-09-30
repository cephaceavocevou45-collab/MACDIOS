from rest_framework.permissions import BasePermission, IsAuthenticated
from django.utils import timezone

from .models import Abonnement, ProfilSousAdmin


class EstCommercantAuthentifie(IsAuthenticated):
    """Accès réservé à un compte commerçant actif."""

    def has_permission(self, request, view):
        return (
            super().has_permission(request, view)
            and request.user.is_active
            and not request.user.is_staff
            and not request.user.is_superuser
        )


class PermissionBackOffice(BasePermission):
    """Vérifie le droit exact en relisant le profil à chaque requête."""

    message = "Vous n'avez pas la permission nécessaire pour cette action."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if user.is_superuser:
            return True
        if not user.is_staff:
            return False
        droit_requis = getattr(view, "permission_requise", None)
        if droit_requis is None:
            return False
        droits = ProfilSousAdmin.objects.filter(utilisateur_id=user.pk).values_list("permissions", flat=True).first()
        return bool(droits and droit_requis in droits)


class SuperAdminUniquement(BasePermission):
    """Protège les opérations de gestion des comptes administratifs."""

    message = "Cette action est réservée au super-administrateur."

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated
            and request.user.is_active and request.user.is_superuser
        )


class EstProprietaireObjet(BasePermission):
    """Vérifie la propriété de l'objet lors d'un accès direct."""

    def has_object_permission(self, request, view, obj):
        return getattr(obj, "commercant_id", None) == request.user.id


class AbonnementAutoriseEcriture(BasePermission):
    """Laisse consulter les données, mais bloque les écritures après expiration."""

    message = "Votre abonnement a expiré. Vous pouvez consulter vos données, mais pas les modifier."

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        try:
            abonnement = request.user.abonnement
        except Abonnement.DoesNotExist:
            return False

        if abonnement.date_fin <= timezone.now():
            if abonnement.statut != Abonnement.Statut.EXPIRE:
                abonnement.statut = Abonnement.Statut.EXPIRE
                abonnement.save(update_fields=["statut"])
            return False
        return abonnement.statut in (Abonnement.Statut.ESSAI, Abonnement.Statut.ACTIF)
