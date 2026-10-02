import uuid
from decimal import Decimal

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import validate_email
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from .validators import valider_telephone_benin


class CommercantManager(BaseUserManager):
    """Crée les comptes avec une adresse email comme identifiant."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire.")
        email = self.normalize_email(email).strip().lower()
        validate_email(email)
        telephone = extra_fields.get("telephone", "")
        if telephone:
            valider_telephone_benin(telephone)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Un superutilisateur doit être staff et superuser.")
        return self.create_user(email, password, **extra_fields)


class Commercant(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField(max_length=254, unique=True)
    telephone = models.CharField(max_length=20, blank=True, validators=[valider_telephone_benin])
    nom_boutique = models.CharField(max_length=120)
    # Date à laquelle l'utilisateur a accepté les textes juridiques en vigueur.
    consentement_le = models.DateTimeField(null=True, blank=True)
    motif_suspension = models.CharField(max_length=250, blank=True)
    suspendu_le = models.DateTimeField(null=True, blank=True)
    suspendu_par = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="commercants_suspendus",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nom_boutique"]
    objects = CommercantManager()

    def __str__(self):
        return f"{self.nom_boutique} ({self.email})"


class ProfilSousAdmin(models.Model):
    """Permissions individuelles d'un agent du back-office."""

    PERMISSIONS = (
        "voir_utilisateurs", "suspendre_utilisateur", "valider_paiements",
        "voir_audit", "voir_statistiques",
    )

    utilisateur = models.OneToOneField(
        Commercant, on_delete=models.CASCADE, related_name="profil_sous_admin",
    )
    nom = models.CharField(max_length=120)
    permissions = models.JSONField(default=list)
    cree_par = models.ForeignKey(
        Commercant, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sous_admins_crees",
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["utilisateur__email"]

    def __str__(self):
        return f"Sous-admin {self.utilisateur.email}"


class SessionJWT(models.Model):
    """Session serveur permettant de révoquer immédiatement access et refresh."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(Commercant, on_delete=models.CASCADE, related_name="sessions_jwt")
    jti_refresh = models.CharField(max_length=255, unique=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    expire_le = models.DateTimeField()
    revoque_le = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["utilisateur", "revoque_le"], name="commerce_session_user_rev_idx")]

    def __str__(self):
        return f"Session {self.id} — {self.utilisateur.email}"


class JournalAudit(models.Model):
    """Trace immuable des actions métier d'un commerçant."""

    class Action(models.TextChoices):
        CREATION = "creation", "Création"
        MODIFICATION = "modification", "Modification"
        SUPPRESSION = "suppression", "Suppression"
        CHANGEMENT_STOCK = "changement_stock", "Changement de stock"
        CONNEXION_REUSSIE = "connexion_reussie", "Connexion réussie"
        CONNEXION_ECHOUEE = "connexion_echouee", "Connexion échouée"
        CHANGEMENT_ABONNEMENT = "changement_abonnement", "Changement d'abonnement"
        MODIFICATION_OFFRE_ESSAI = "modification_offre_essai", "Modification de l'offre d'essai"
        CREATION_SOUS_ADMIN = "creation_sous_admin", "Création d'un sous-admin"
        MODIFICATION_SOUS_ADMIN = "modification_sous_admin", "Modification d'un sous-admin"
        DESACTIVATION_SOUS_ADMIN = "desactivation_sous_admin", "Désactivation d'un sous-admin"
        SUSPENSION_UTILISATEUR = "suspension_utilisateur", "Suspension d'un commerçant"
        REACTIVATION_UTILISATEUR = "reactivation_utilisateur", "Réactivation d'un commerçant"
        VALIDATION_PAIEMENT_ADMIN = "validation_paiement_admin", "Validation d'un paiement par l'administration"
        REJET_PAIEMENT_ADMIN = "rejet_paiement_admin", "Rejet d'un paiement par l'administration"

    commercant = models.ForeignKey(
        Commercant, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="evenements_audit",
    )
    utilisateur = models.ForeignKey(
        Commercant, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="actions_audit",
    )
    action = models.CharField(max_length=32, choices=Action.choices, db_index=True)
    objet_type = models.CharField(max_length=80)
    objet_id = models.CharField(max_length=64, blank=True)
    anciennes_valeurs = models.JSONField(default=dict, blank=True)
    nouvelles_valeurs = models.JSONField(default=dict, blank=True)
    date = models.DateTimeField(auto_now_add=True, db_index=True)
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [models.Index(fields=["commercant", "date"])]

    def __str__(self):
        return f"{self.get_action_display()} — {self.objet_type} {self.objet_id}"


class Produit(models.Model):
    commercant = models.ForeignKey(Commercant, on_delete=models.CASCADE, related_name="produits")
    nom = models.CharField(max_length=120)
    prix = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    quantite_stock = models.PositiveIntegerField(default=0)
    seuil_alerte = models.PositiveIntegerField(default=5)
    date_creation = models.DateTimeField(auto_now_add=True)
    # L'archivage masque le produit sans casser les références des ventes.
    actif = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["nom"]
        constraints = [models.CheckConstraint(condition=models.Q(prix__gte=0), name="produit_prix_non_negatif")]

    def __str__(self):
        return self.nom


class Client(models.Model):
    commercant = models.ForeignKey(Commercant, on_delete=models.CASCADE, related_name="clients")
    nom = models.CharField(max_length=120)
    telephone = models.CharField(max_length=20, blank=True)
    # Une archive conserve les dettes, paiements et ventes historiques du client.
    actif = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["nom"]

    @property
    def solde(self):
        # Les listes annotent ces deux totaux afin d'éviter deux requêtes par client.
        if hasattr(self, "_total_dettes_annote") and hasattr(self, "_total_paiements_annote"):
            return self._total_dettes_annote - self._total_paiements_annote
        montant_decimal = models.DecimalField(max_digits=14, decimal_places=2)
        dettes = self.dettes.aggregate(
            total=Coalesce(Sum("montant"), 0, output_field=montant_decimal)
        )["total"]
        paiements = self.paiements.aggregate(
            total=Coalesce(Sum("montant"), 0, output_field=montant_decimal)
        )["total"]
        return dettes - paiements

    def __str__(self):
        return self.nom


class RequeteIdempotente(models.Model):
    """Conserve la réponse d'une opération rejouée avec la même clé."""

    commercant = models.ForeignKey(
        Commercant, on_delete=models.CASCADE, related_name="requetes_idempotentes"
    )
    operation = models.CharField(max_length=20)
    cle = models.CharField(max_length=100)
    empreinte = models.CharField(max_length=64)
    code_http = models.PositiveSmallIntegerField(default=201)
    reponse = models.JSONField(default=dict)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["commercant", "operation", "cle"],
                name="unique_requete_idempotente_commercant_operation",
            )
        ]


class Vente(models.Model):
    commercant = models.ForeignKey(Commercant, on_delete=models.CASCADE, related_name="ventes")
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT, related_name="ventes")
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, related_name="ventes", null=True, blank=True)
    quantite = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    prix_unitaire = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=14, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.quantite} × {self.produit.nom}"


class Dette(models.Model):
    commercant = models.ForeignKey(Commercant, on_delete=models.CASCADE, related_name="dettes")
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="dettes")
    montant = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    note = models.CharField(max_length=250, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    # Créés au premier téléchargement du reçu, puis conservés pour les scans suivants.
    code_verification = models.UUIDField(null=True, blank=True, unique=True, editable=False)
    date_generation = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-date"]


class CorrectionDette(models.Model):
    """Conserve chaque ajustement du montant d'une dette sans effacer sa valeur précédente."""

    commercant = models.ForeignKey(Commercant, on_delete=models.CASCADE, related_name="corrections_dettes")
    dette = models.ForeignKey(Dette, on_delete=models.CASCADE, related_name="corrections")
    montant_precedent = models.DecimalField(max_digits=14, decimal_places=2)
    nouveau_montant = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    raison = models.CharField(max_length=250)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"Correction de la dette {self.dette_id} — {self.nouveau_montant} FCFA"


class Paiement(models.Model):
    commercant = models.ForeignKey(Commercant, on_delete=models.CASCADE, related_name="paiements")
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="paiements")
    montant = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]


class Plan(models.Model):
    """Offre d'abonnement proposée aux commerçants."""

    nom = models.CharField(max_length=100, unique=True)
    prix = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    duree_jours = models.PositiveIntegerField()
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ["prix", "nom"]

    def __str__(self):
        return f"{self.nom} ({self.prix} FCFA)"


class ConfigurationEssai(models.Model):
    """Réglage unique de l'offre d'essai, modifiable uniquement par le super-admin."""

    actif = models.BooleanField(default=True)
    duree_jours = models.PositiveSmallIntegerField(default=14)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuration de l'essai gratuit"
        verbose_name_plural = "Configuration de l'essai gratuit"

    def save(self, *args, **kwargs):
        # Une seule configuration globale est autorisée.
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Le réglage global ne peut pas être supprimé par erreur.
        return None

    @classmethod
    def obtenir(cls):
        return cls.objects.get_or_create(pk=1)[0]


class Abonnement(models.Model):
    class Statut(models.TextChoices):
        ESSAI = "essai", "Essai"
        ACTIF = "actif", "Actif"
        EXPIRE = "expire", "Expiré"

    commercant = models.OneToOneField(Commercant, on_delete=models.CASCADE, related_name="abonnement")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="abonnements")
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.ESSAI)
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    # Date d'échéance déjà notifiée, pour rendre la tâche quotidienne idempotente.
    rappel_sms_echeance_le = models.DateField(null=True, blank=True, editable=False)
    rappel_sms_envoye_le = models.DateTimeField(null=True, blank=True, editable=False)

    def __str__(self):
        return f"{self.commercant} — {self.get_statut_display()}"


class PaiementAbonnementHistorique(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        REUSSI = "reussi", "Réussi"
        ECHOUE = "echoue", "Échoué"

    commercant = models.ForeignKey(Commercant, on_delete=models.CASCADE, related_name="historique_paiements_abonnement")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="historique_paiements_abonnement")
    montant = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.EN_ATTENTE)
    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_validation = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date_creation"]

    def __str__(self):
        return f"{self.reference} — {self.get_statut_display()}"


def preuve_abonnement_upload_to(instance, nom_fichier):
    """Range les preuves sous un nom aléatoire ; elles ne sont jamais servies publiquement."""
    extension = nom_fichier.rsplit(".", 1)[-1].lower()[:8]
    return f"preuves-abonnement/{uuid.uuid4().hex}.{extension}"


class DemandePaiementManuel(models.Model):
    """Demande de règlement vérifiée manuellement par un administrateur."""

    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        VALIDEE = "validee", "Validée"
        REJETEE = "rejetee", "Rejetée"

    class Operateur(models.TextChoices):
        MTN = "mtn", "MTN"
        MOOV = "moov", "Moov"
        CELTIIS = "celtiis", "Celtiis"

    commercant = models.ForeignKey(Commercant, on_delete=models.CASCADE, related_name="demandes_paiement_abonnement")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="demandes_paiement_manuel")
    montant = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    # Vide uniquement pour conserver les demandes historiques faites avant le choix d'opérateur.
    operateur = models.CharField(max_length=10, choices=Operateur.choices, blank=True, default="")
    reference_transaction = models.CharField(max_length=120)
    preuve = models.ImageField(upload_to=preuve_abonnement_upload_to, null=True, blank=True)
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.EN_ATTENTE)
    date_demande = models.DateTimeField(auto_now_add=True)
    traitee_par = models.ForeignKey(Commercant, on_delete=models.SET_NULL, null=True, blank=True, related_name="demandes_abonnement_traitees")
    date_decision = models.DateTimeField(null=True, blank=True)
    date_debut_abonnement = models.DateTimeField(null=True, blank=True)
    date_fin_abonnement = models.DateTimeField(null=True, blank=True)
    motif_rejet = models.CharField(max_length=250, blank=True)
    code_verification = models.UUIDField(null=True, blank=True, unique=True, editable=False)
    date_generation = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-date_demande"]
        constraints = [models.UniqueConstraint(fields=["commercant"], condition=Q(statut="en_attente"), name="unique_demande_abonnement_en_attente")]

    def __str__(self):
        return f"{self.commercant} — {self.get_statut_display()} — {self.plan}"
