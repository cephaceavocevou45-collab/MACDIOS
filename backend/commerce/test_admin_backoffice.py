"""Tests de séparation des rôles et des permissions du back-office."""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from commerce.models import (
    Abonnement, ConfigurationEssai, DemandePaiementManuel, JournalAudit, Plan, Produit,
    PaiementAbonnementHistorique, ProfilSousAdmin, Vente,
)
from commerce.test_helpers import entete_csrf


@override_settings(NUMERO_MTN="22961020304", NUMERO_MOOV="", NUMERO_CELTIIS="")
class BackOfficeTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.commercant = self.User.objects.create_user(
            email="marchand@example.test", password="MotDePasse123!", nom_boutique="Boutique Marchand",
        )
        self.autre = self.User.objects.create_user(
            email="autre@example.test", password="MotDePasse123!", nom_boutique="Autre Boutique",
        )
        self.superadmin = self.User.objects.create_superuser(
            email="root@example.test", password="MotDePasse123!", nom_boutique="Administration",
        )
        self.sous_admin = self.User.objects.create_user(
            email="agent@example.test", password="MotDePasse123!", nom_boutique="Back-office Agent",
            is_staff=True, first_name="Agent",
        )
        self.profil = ProfilSousAdmin.objects.create(
            utilisateur=self.sous_admin, nom="Agent", permissions=["voir_utilisateurs"], cree_par=self.superadmin,
        )
        self.plan_essai = Plan.objects.get(nom="Essai gratuit")
        self.plan = Plan.objects.create(nom="Plan Admin", prix=2500, duree_jours=30)
        debut = timezone.now()
        for commerçant in (self.commercant, self.autre):
            Abonnement.objects.create(
                commercant=commerçant, plan=self.plan_essai, statut=Abonnement.Statut.ESSAI,
                date_debut=debut, date_fin=debut + timedelta(days=14),
            )
        self.api = APIClient()

    def connecter(self, utilisateur):
        client = APIClient()
        client.force_authenticate(utilisateur)
        return client

    def demande_paiement(self, utilisateur=None):
        return DemandePaiementManuel.objects.create(
            commercant=utilisateur or self.commercant, plan=self.plan,
            montant=self.plan.prix, reference_transaction="MOMO-REF-2026",
        )

    def test_superadmin_accede_aux_statistiques_utilisateurs_audit_et_paiements(self):
        self.demande_paiement()
        DemandePaiementManuel.objects.create(
            commercant=self.autre, plan=self.plan, montant=2000,
            reference_transaction="MOMO-VALIDE", statut=DemandePaiementManuel.Statut.VALIDEE,
            date_decision=timezone.now(),
        )
        PaiementAbonnementHistorique.objects.create(
            commercant=self.commercant, plan=self.plan, montant=2500,
            statut=PaiementAbonnementHistorique.Statut.REUSSI, date_validation=timezone.now(),
        )
        produit = Produit.objects.create(commercant=self.commercant, nom="Riz", prix=500, quantite_stock=3)
        Vente.objects.create(commercant=self.commercant, produit=produit, quantite=1,
                             prix_unitaire=1, total=1)
        api = self.connecter(self.superadmin)
        for url in (
            "/api/admin/statistiques/", "/api/admin/utilisateurs/",
            "/api/admin/audit/", "/api/admin/paiements-en-attente/",
            "/api/admin/sous-admins/",
        ):
            with self.subTest(url=url):
                self.assertEqual(api.get(url).status_code, 200)
        stats = api.get("/api/admin/statistiques/")
        self.assertEqual(stats.data["nombre_commercants"], 2)
        self.assertEqual(stats.data["commercants_en_essai"], 2)
        self.assertEqual(stats.data["ventes_enregistrees"], 1)
        self.assertEqual(stats.data["revenus_totaux"], "4500.00")
        self.assertEqual(stats.data["revenus_mois"], "4500.00")

    def test_sousadmin_est_limite_a_ses_droits_individuels(self):
        api = self.connecter(self.sous_admin)
        utilisateurs = api.get("/api/admin/utilisateurs/")
        self.assertEqual(utilisateurs.status_code, 200)
        self.assertEqual(utilisateurs.data["count"], 2)
        for url in ("/api/admin/statistiques/", "/api/admin/audit/", "/api/admin/paiements-en-attente/"):
            with self.subTest(url=url):
                self.assertEqual(api.get(url).status_code, 403)
        self.assertEqual(api.post(f"/api/admin/utilisateurs/{self.commercant.pk}/suspendre/", {"motif": "Test"}).status_code, 403)

    def test_sousadmin_desactive_perd_une_session_jwt_deja_emise(self):
        csrf = entete_csrf(self.api)
        connexion = self.api.post("/api/admin/auth/connexion/", {
            "email": self.sous_admin.email, "mot_de_passe": "MotDePasse123!",
        }, format="json", **csrf)
        self.assertEqual(connexion.status_code, 200, connexion.data)
        self.sous_admin.is_active = False
        self.sous_admin.save(update_fields=["is_active"])
        acces = self.api.get("/api/admin/utilisateurs/")
        self.assertEqual(acces.status_code, 401)

    def test_commercant_ne_peut_acceder_ni_aux_routes_admin_ni_au_login_admin(self):
        api = self.connecter(self.commercant)
        for url in (
            "/api/admin/statistiques/", "/api/admin/utilisateurs/",
            "/api/admin/audit/", "/api/admin/sous-admins/", "/api/admin/paiements-en-attente/",
        ):
            with self.subTest(url=url):
                self.assertEqual(api.get(url).status_code, 403)
        csrf = entete_csrf(self.api)
        mauvais_espace = self.api.post("/api/admin/auth/connexion/", {
            "email": self.commercant.email, "mot_de_passe": "MotDePasse123!",
        }, format="json", **csrf)
        self.assertEqual(mauvais_espace.status_code, 400)
        connexion_commercant = self.api.post("/api/auth/connexion/", {
            "email": self.superadmin.email, "mot_de_passe": "MotDePasse123!",
        }, format="json", **csrf)
        self.assertEqual(connexion_commercant.status_code, 403)
        for methode, url in (
            ("post", f"/api/admin/utilisateurs/{self.commercant.pk}/suspendre/"),
            ("post", f"/api/admin/utilisateurs/{self.commercant.pk}/reactiver/"),
            ("post", "/api/admin/paiements-en-attente/1/valider/"),
            ("post", "/api/admin/paiements-en-attente/1/rejeter/"),
            ("get", "/api/admin/paiements-en-attente/1/preuve/"),
        ):
            with self.subTest(url=url):
                reponse = api.get(url) if methode == "get" else api.post(url, {}, format="json")
                self.assertEqual(reponse.status_code, 403)

    def test_superadmin_cree_invite_modifie_et_desactive_un_sousadmin_avec_audit(self):
        api = self.connecter(self.superadmin)
        with patch("commerce.admin_api.envoyer_email") as envoyer:
            with self.captureOnCommitCallbacks(execute=True):
                creation = api.post("/api/admin/sous-admins/", {
                    "email": "nouvel-agent@example.test", "nom": "Nouvel Agent",
                    "permissions": ["voir_audit", "valider_paiements"],
                }, format="json")
        self.assertEqual(creation.status_code, 201, creation.data)
        self.assertEqual(creation.data["permissions"], ["voir_audit", "valider_paiements"])
        envoyer.assert_called_once()
        profil = ProfilSousAdmin.objects.get(utilisateur__email="nouvel-agent@example.test")
        self.assertEqual(profil.utilisateur.is_staff, True)
        self.assertEqual(profil.utilisateur.is_superuser, False)
        self.assertTrue(JournalAudit.objects.filter(
            action=JournalAudit.Action.CREATION_SOUS_ADMIN,
            utilisateur=self.superadmin, objet_id=str(profil.pk),
        ).exists())

        modif = api.patch(f"/api/admin/sous-admins/{profil.utilisateur_id}/", {
            "permissions": ["voir_utilisateurs"],
        }, format="json")
        self.assertEqual(modif.status_code, 200, modif.data)
        self.assertTrue(JournalAudit.objects.filter(
            action=JournalAudit.Action.MODIFICATION_SOUS_ADMIN,
            utilisateur=self.superadmin, objet_id=str(profil.pk),
        ).exists())
        desactivation = api.patch(f"/api/admin/sous-admins/{profil.utilisateur_id}/", {
            "actif": False,
        }, format="json")
        self.assertEqual(desactivation.status_code, 200)
        profil.refresh_from_db()
        self.assertFalse(profil.utilisateur.is_active)
        self.assertTrue(JournalAudit.objects.filter(
            action=JournalAudit.Action.DESACTIVATION_SOUS_ADMIN,
            utilisateur=self.superadmin,
        ).exists())

    def test_sousadmin_ne_peut_ni_creer_ni_desactiver_un_sousadmin(self):
        api = self.connecter(self.sous_admin)
        self.assertEqual(api.get("/api/admin/sous-admins/").status_code, 403)
        self.assertEqual(api.post("/api/admin/sous-admins/", {
            "email": "nope@example.test", "nom": "Non", "permissions": [],
        }, format="json").status_code, 403)

    def test_superadmin_peut_modifier_duree_et_activation_essai_avec_audit(self):
        api = self.connecter(self.superadmin)
        initial = api.get("/api/admin/offre-essai/")
        self.assertEqual(initial.status_code, 200, initial.data)
        self.assertTrue(initial.data["actif"])
        self.assertEqual(initial.data["duree_jours"], 14)

        mise_a_jour = api.patch("/api/admin/offre-essai/", {
            "actif": False, "duree_jours": 30,
        }, format="json")
        self.assertEqual(mise_a_jour.status_code, 200, mise_a_jour.data)
        self.assertFalse(mise_a_jour.data["actif"])
        self.assertEqual(mise_a_jour.data["duree_jours"], 30)
        self.assertTrue(JournalAudit.objects.filter(
            action=JournalAudit.Action.MODIFICATION_OFFRE_ESSAI,
            utilisateur=self.superadmin,
            nouvelles_valeurs={"actif": False, "duree_jours": 30},
        ).exists())

        invalide = api.patch("/api/admin/offre-essai/", {"duree_jours": 500}, format="json")
        self.assertEqual(invalide.status_code, 400)

    def test_sousadmin_et_commercant_ne_peuvent_modifier_offre_essai(self):
        for utilisateur in (self.sous_admin, self.commercant):
            with self.subTest(utilisateur=utilisateur.email):
                api = self.connecter(utilisateur)
                self.assertEqual(api.get("/api/admin/offre-essai/").status_code, 403)
                self.assertEqual(api.patch("/api/admin/offre-essai/", {"actif": False}, format="json").status_code, 403)

    @patch("commerce.views.envoyer_email")
    def test_desactivation_offre_s_applique_aux_nouvelles_inscriptions(self, envoyer_email):
        configuration = ConfigurationEssai.obtenir()
        configuration.actif = False
        configuration.save(update_fields=["actif", "modifie_le"])
        reponse = self.api.post("/api/auth/inscription/", {
            "telephone": "+22962030408",
            "nom_boutique": "Nouvelle boutique",
            "mot_de_passe": "MotDePasse123!",
            "confirmation_mot_de_passe": "MotDePasse123!",
            "accepte_conditions": True,
        }, format="json")
        self.assertEqual(reponse.status_code, 201, reponse.data)
        abonnement = Abonnement.objects.get(commercant_id=reponse.data["id"])
        self.assertEqual(abonnement.statut, Abonnement.Statut.EXPIRE)
        self.assertEqual(abonnement.date_fin, abonnement.date_debut)
        envoyer_email.assert_not_called()

    def test_offre_essai_publique_ne_expose_que_duree_et_disponibilite(self):
        ConfigurationEssai.objects.create(actif=True, duree_jours=21)
        reponse = self.api.get("/api/offre-essai/")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.data, {"actif": True, "duree_jours": 21})

    def test_admin_django_est_inaccessible_aux_sousadmins(self):
        session = APIClient()
        session.force_login(self.sous_admin)
        self.assertEqual(session.get("/admin/").status_code, 302)

    @override_settings(REST_FRAMEWORK={"DEFAULT_THROTTLE_RATES": {"admin_connexion": "1/minute"}})
    def test_connexion_admin_a_un_rate_limit_strict(self):
        cache.clear()
        donnees = {"email": "inconnu@example.test", "mot_de_passe": "invalide"}
        csrf = entete_csrf(self.api)
        premiere = self.api.post("/api/admin/auth/connexion/", donnees, format="json", **csrf)
        seconde = self.api.post("/api/admin/auth/connexion/", donnees, format="json", **csrf)
        self.assertEqual(premiere.status_code, 400)
        self.assertEqual(seconde.status_code, 429)

    def test_suspension_exige_un_motif_est_auditee_et_bloque_la_connexion(self):
        api = self.connecter(self.superadmin)
        sans_motif = api.post(f"/api/admin/utilisateurs/{self.commercant.pk}/suspendre/", {}, format="json")
        self.assertEqual(sans_motif.status_code, 400)
        suspendu = api.post(
            f"/api/admin/utilisateurs/{self.commercant.pk}/suspendre/",
            {"motif": "Vérification requise"}, format="json",
        )
        self.assertEqual(suspendu.status_code, 200, suspendu.data)
        self.commercant.refresh_from_db()
        self.assertFalse(self.commercant.is_active)
        self.assertTrue(JournalAudit.objects.filter(
            action=JournalAudit.Action.SUSPENSION_UTILISATEUR,
            utilisateur=self.superadmin, commercant=self.commercant,
        ).exists())
        csrf = entete_csrf(self.api)
        connexion = self.api.post("/api/auth/connexion/", {
            "email": self.commercant.email, "mot_de_passe": "MotDePasse123!",
        }, format="json", **csrf)
        self.assertEqual(connexion.status_code, 403)
        self.assertIn("suspendu", connexion.data["detail"].lower())

        reactif = api.post(f"/api/admin/utilisateurs/{self.commercant.pk}/reactiver/", {}, format="json")
        self.assertEqual(reactif.status_code, 200)
        self.commercant.refresh_from_db()
        self.assertTrue(self.commercant.is_active)
        self.assertEqual(self.commercant.motif_suspension, "")
        self.assertTrue(JournalAudit.objects.filter(
            action=JournalAudit.Action.REACTIVATION_UTILISATEUR,
            utilisateur=self.superadmin,
        ).exists())

    def test_permission_paiement_valide_et_rejette_avec_trace_acteur(self):
        self.profil.permissions = ["valider_paiements"]
        self.profil.save(update_fields=["permissions"])
        demande_validee = self.demande_paiement()
        api = self.connecter(self.sous_admin)
        self.assertEqual(api.get("/api/admin/paiements-en-attente/").status_code, 200)
        with self.captureOnCommitCallbacks(execute=True):
            validation = api.post(f"/api/admin/paiements-en-attente/{demande_validee.pk}/valider/", {}, format="json")
        self.assertEqual(validation.status_code, 200, validation.data)
        demande_validee.refresh_from_db()
        self.assertEqual(demande_validee.traitee_par, self.sous_admin)
        self.assertTrue(JournalAudit.objects.filter(
            action=JournalAudit.Action.VALIDATION_PAIEMENT_ADMIN,
            utilisateur=self.sous_admin,
        ).exists())

        demande_rejetee = self.demande_paiement(self.autre)
        vide = api.post(f"/api/admin/paiements-en-attente/{demande_rejetee.pk}/rejeter/", {"motif": " "}, format="json")
        self.assertEqual(vide.status_code, 400)
        with self.captureOnCommitCallbacks(execute=True):
            rejet = api.post(f"/api/admin/paiements-en-attente/{demande_rejetee.pk}/rejeter/", {"motif": "Référence introuvable"}, format="json")
        self.assertEqual(rejet.status_code, 200, rejet.data)
        demande_rejetee.refresh_from_db()
        self.assertEqual(demande_rejetee.statut, DemandePaiementManuel.Statut.REJETEE)
        self.assertTrue(JournalAudit.objects.filter(
            action=JournalAudit.Action.REJET_PAIEMENT_ADMIN,
            utilisateur=self.sous_admin,
        ).exists())

    def test_filtrage_audit_par_commercant_admin_et_action(self):
        evenement = JournalAudit.objects.create(
            commercant=self.commercant, utilisateur=self.superadmin,
            action=JournalAudit.Action.SUSPENSION_UTILISATEUR,
            objet_type="Commercant", objet_id=str(self.commercant.pk),
        )
        api = self.connecter(self.sous_admin)
        self.profil.permissions = ["voir_audit"]
        self.profil.save(update_fields=["permissions"])
        response = api.get("/api/admin/audit/", {
            "commercant": self.commercant.email,
            "admin": self.superadmin.email,
            "action": JournalAudit.Action.SUSPENSION_UTILISATEUR,
        })
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], evenement.pk)
