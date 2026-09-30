from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from .models import Abonnement, Client, Commercant, CorrectionDette, DemandePaiementManuel, Dette, JournalAudit, Paiement, PaiementAbonnementHistorique, Plan, Produit, Vente
from .services.paiement_manuel import rejeter_demande, valider_demande


class CommercantCreationForm(UserCreationForm):
    """Formulaire d'administration adapté au nouvel identifiant email."""

    class Meta(UserCreationForm.Meta):
        model = Commercant
        fields = ("email", "telephone", "nom_boutique")

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


@admin.register(Commercant)
class CommercantAdmin(UserAdmin):
    add_form = CommercantCreationForm
    ordering = ("email",)
    list_display = ("email", "telephone", "nom_boutique", "is_staff", "is_active")
    search_fields = ("email", "telephone", "nom_boutique")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Contact", {"fields": ("telephone",)}),
        ("Boutique", {"fields": ("nom_boutique",)}),
        ("Accès", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "telephone", "nom_boutique", "password1", "password2")}),)
    readonly_fields = ("last_login", "date_joined")


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ("nom", "commercant", "prix", "quantite_stock", "seuil_alerte")
    list_filter = ("commercant",)
    search_fields = ("nom", "commercant__telephone", "commercant__nom_boutique")


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("nom", "telephone", "commercant")
    list_filter = ("commercant",)
    search_fields = ("nom", "telephone")


@admin.register(Vente)
class VenteAdmin(admin.ModelAdmin):
    list_display = ("date", "commercant", "produit", "client", "quantite", "total")
    list_filter = ("commercant", "date")
    date_hierarchy = "date"


@admin.register(Dette)
class DetteAdmin(admin.ModelAdmin):
    list_display = ("date", "commercant", "client", "montant")
    list_filter = ("commercant", "date")
    date_hierarchy = "date"
    # Le montant ne se remplace pas : passer par l'opération de correction dédiée.
    def get_readonly_fields(self, request, obj=None):
        return ("montant", "date") if obj else ("date",)


@admin.register(CorrectionDette)
class CorrectionDetteAdmin(admin.ModelAdmin):
    list_display = ("date", "commercant", "dette", "montant_precedent", "nouveau_montant")
    list_filter = ("commercant", "date")
    readonly_fields = tuple(champ.name for champ in CorrectionDette._meta.fields)
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ("date", "commercant", "client", "montant")
    list_filter = ("commercant", "date")
    date_hierarchy = "date"


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("nom", "prix", "duree_jours", "actif")
    list_filter = ("actif",)
    search_fields = ("nom",)


@admin.register(Abonnement)
class AbonnementAdmin(admin.ModelAdmin):
    list_display = ("commercant", "plan", "statut", "date_debut", "date_fin")
    list_filter = ("statut", "plan")
    search_fields = ("commercant__telephone", "commercant__nom_boutique")


@admin.register(PaiementAbonnementHistorique)
class PaiementAbonnementHistoriqueAdmin(admin.ModelAdmin):
    list_display = ("reference", "commercant", "plan", "montant", "statut", "date_creation")
    list_filter = ("statut", "plan", "date_creation")
    search_fields = ("reference", "commercant__email")
    readonly_fields = ("reference", "date_creation")


class MotifRejetForm(forms.Form):
    motif = forms.CharField(label="Motif du rejet", max_length=250, required=True, widget=forms.Textarea(attrs={"rows": 3}))


@admin.register(DemandePaiementManuel)
class DemandePaiementManuelAdmin(admin.ModelAdmin):
    """Les preuves restent derrière une vue admin et les décisions sont tracées."""

    list_display = ("date_demande", "commercant", "plan", "montant", "operateur_affiche", "reference_transaction", "statut", "lien_preuve")
    list_filter = ("statut", "date_demande", "plan")
    search_fields = ("commercant__email", "commercant__nom_boutique", "reference_transaction")
    readonly_fields = tuple(champ.name for champ in DemandePaiementManuel._meta.fields)
    actions = ("valider_selection", "rejeter_selection")

    @admin.display(description="Opérateur")
    def operateur_affiche(self, obj):
        return obj.get_operateur_display() or "Non renseigné"

    def get_urls(self):
        return [path("<int:pk>/preuve-privee/", self.admin_site.admin_view(self.voir_preuve), name="commerce_demandepaiementmanuel_preuve")] + super().get_urls()

    def lien_preuve(self, obj):
        if not obj.preuve:
            return "Aucune"
        url = reverse("admin:commerce_demandepaiementmanuel_preuve", args=[obj.pk])
        return format_html('<a href="{}">Voir la preuve</a>', url)
    lien_preuve.short_description = "Preuve"

    def voir_preuve(self, request, pk):
        demande = DemandePaiementManuel.objects.filter(pk=pk).first()
        if demande is None or not demande.preuve:
            raise Http404
        try:
            fichier = demande.preuve.open("rb")
        except OSError:
            return HttpResponse("La preuve de paiement est temporairement indisponible.", status=503)
        return FileResponse(fichier, content_type="application/octet-stream", as_attachment=True, filename="preuve-paiement")

    @admin.action(description="Valider les demandes sélectionnées")
    def valider_selection(self, request, queryset):
        validees = 0
        for demande in queryset:
            _, modifiee = valider_demande(demande.pk, request.user)
            validees += int(modifiee)
        self.message_user(request, f"{validees} demande(s) validée(s).", messages.SUCCESS)

    @admin.action(description="Rejeter les demandes sélectionnées…")
    def rejeter_selection(self, request, queryset):
        ids = [str(pk) for pk in queryset.values_list("pk", flat=True)]
        if request.POST.get("confirmer_rejet"):
            form = MotifRejetForm(request.POST)
            if form.is_valid():
                rejetees = 0
                for demande in DemandePaiementManuel.objects.filter(pk__in=ids):
                    _, modifiee = rejeter_demande(demande.pk, request.user, form.cleaned_data["motif"])
                    rejetees += int(modifiee)
                self.message_user(request, f"{rejetees} demande(s) rejetée(s).", messages.SUCCESS)
                return redirect(request.get_full_path())
        else:
            form = MotifRejetForm()
        contexte = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "titre": "Motif obligatoire du rejet",
            "form": form,
            "ids": ids,
        }
        return TemplateResponse(request, "admin/commerce/demandepaiementmanuel/rejeter_selection.html", contexte)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(JournalAudit)
class JournalAuditAdmin(admin.ModelAdmin):
    """Le journal est consultable, mais toute modification administrative est bloquée."""

    list_display = ("date", "commercant", "action", "objet_type", "objet_id", "adresse_ip")
    list_filter = ("action", "date")
    search_fields = ("objet_type", "objet_id", "commercant__telephone")
    readonly_fields = tuple(champ.name for champ in JournalAudit._meta.fields)
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
