from django.contrib.auth import get_user_model
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Abonnement, Client, Dette, Paiement, PaiementAbonnementHistorique, Plan, Produit, Vente

Commercant = get_user_model()


class CommerceAPITests(TestCase):
    def setUp(self):
        self.user = Commercant.objects.create_user(
            email="boutique-a@example.test",
            telephone="+22990000001", nom_boutique="Boutique A", password="MotDePasse123!"
        )
        self.autre = Commercant.objects.create_user(
            email="boutique-b@example.test",
            telephone="+22990000002", nom_boutique="Boutique B", password="MotDePasse123!"
        )
        plan_essai = Plan.objects.get(nom="Essai gratuit")
        debut_essai = timezone.now()
        for utilisateur in (self.user, self.autre):
            Abonnement.objects.create(
                commercant=utilisateur, plan=plan_essai, statut=Abonnement.Statut.ESSAI,
                date_debut=debut_essai, date_fin=debut_essai + timedelta(days=14),
            )
        self.client_api = APIClient()
        self.client_api.force_authenticate(self.user)
        self.produit = Produit.objects.create(
            commercant=self.user, nom="Riz", prix="1000", quantite_stock=10
        )
        self.client_obj = Client.objects.create(commercant=self.user, nom="Awa")

    def test_vente_atomique_diminue_stock_et_fige_prix(self):
        response = self.client_api.post(
            "/api/ventes/",
            {"produit": self.produit.id, "client": self.client_obj.id, "quantite": 3},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.produit.refresh_from_db()
        self.assertEqual(self.produit.quantite_stock, 7)
        vente = Vente.objects.get()
        self.assertEqual(str(vente.total), "3000.00")
        self.assertEqual(str(vente.prix_unitaire), "1000.00")

    def test_vente_refusee_si_stock_insuffisant_sans_modifier_le_stock(self):
        response = self.client_api.post(
            "/api/ventes/", {"produit": self.produit.id, "quantite": 11}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.produit.refresh_from_db()
        self.assertEqual(self.produit.quantite_stock, 10)
        self.assertFalse(Vente.objects.exists())

    def test_commercant_ne_voit_pas_les_produits_des_autres(self):
        Produit.objects.create(commercant=self.autre, nom="Huile", prix=500, quantite_stock=2)
        response = self.client_api.get("/api/produits/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["nom"], "Riz")

    def test_produits_peuvent_etre_crees_modifies_et_supprimes(self):
        creation = self.client_api.post(
            "/api/produits/",
            {"nom": "Huile", "prix": "1500", "quantite_stock": 8, "seuil_alerte": 2},
            format="json",
        )
        self.assertEqual(creation.status_code, 201, creation.data)
        produit_id = creation.data["id"]
        modification = self.client_api.patch(
            f"/api/produits/{produit_id}/", {"prix": "1750"}, format="json"
        )
        self.assertEqual(modification.status_code, 200, modification.data)
        self.assertEqual(modification.data["prix"], "1750.00")
        suppression = self.client_api.delete(f"/api/produits/{produit_id}/")
        self.assertEqual(suppression.status_code, 204)

    def test_clients_peuvent_etre_crees_modifies_et_supprimes(self):
        creation = self.client_api.post(
            "/api/clients/", {"nom": "Kossi", "telephone": "22990000003"}, format="json"
        )
        self.assertEqual(creation.status_code, 201, creation.data)
        self.assertEqual(creation.data["solde"], "0.00")
        client_id = creation.data["id"]
        modification = self.client_api.patch(
            f"/api/clients/{client_id}/", {"nom": "Kossi A."}, format="json"
        )
        self.assertEqual(modification.status_code, 200, modification.data)
        self.assertEqual(modification.data["nom"], "Kossi A.")
        suppression = self.client_api.delete(f"/api/clients/{client_id}/")
        self.assertEqual(suppression.status_code, 204)

    def test_dettes_paiements_et_solde_client(self):
        dette = self.client_api.post(
            "/api/dettes/",
            {"client": self.client_obj.id, "montant": "4500", "note": "Riz"},
            format="json",
        )
        self.assertEqual(dette.status_code, 201, dette.data)
        paiement = self.client_api.post(
            "/api/paiements/",
            {"client": self.client_obj.id, "montant": "1200"},
            format="json",
        )
        self.assertEqual(paiement.status_code, 201, paiement.data)
        solde = self.client_api.get(f"/api/clients/{self.client_obj.id}/")
        self.assertEqual(solde.data["solde"], "3300.00")
        paiement_trop_eleve = self.client_api.post(
            "/api/paiements/",
            {"client": self.client_obj.id, "montant": "4000"},
            format="json",
        )
        self.assertEqual(paiement_trop_eleve.status_code, 400)

    def test_historique_filtre_par_jour_semaine_et_mois(self):
        vente = self.client_api.post(
            "/api/ventes/",
            {"produit": self.produit.id, "quantite": 1},
            format="json",
        )
        self.assertEqual(vente.status_code, 201, vente.data)
        for periode in ("jour", "semaine", "mois"):
            with self.subTest(periode=periode):
                response = self.client_api.get("/api/ventes/", {"periode": periode})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.data), 1)

    def test_produit_autre_commercant_inutilisable_pour_vente(self):
        produit_autre = Produit.objects.create(
            commercant=self.autre, nom="Huile", prix=500, quantite_stock=5
        )
        response = self.client_api.post(
            "/api/ventes/", {"produit": produit_autre.id, "quantite": 1}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Vente.objects.exists())

    def test_solde_client_est_dettes_moins_paiements(self):
        Dette.objects.create(commercant=self.user, client=self.client_obj, montant="5000")
        Paiement.objects.create(commercant=self.user, client=self.client_obj, montant="1200")
        response = self.client_api.get(f"/api/clients/{self.client_obj.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["solde"], "3800.00")

    def test_dashboard_renvoie_les_totaux_et_les_produits_en_alerte(self):
        self.produit.quantite_stock = 3
        self.produit.save(update_fields=["quantite_stock"])
        response = self.client_api.get("/api/dashboard/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["ventes_jour"], 0)
        self.assertEqual(response.data["ventes_semaine"], 0)
        self.assertEqual(response.data["ventes_mois"], 0)
        self.assertEqual(response.data["total_dettes_en_cours"], 0)
        self.assertEqual(response.data["produits_en_rupture"][0]["nom"], "Riz")

    def test_auth_inscription_et_connexion_jwt(self):
        inscription = self.client_api.post(
            "/api/auth/inscription/",
            {"email": "nouvelle@example.test", "telephone": "+22990000003", "nom_boutique": "Nouvelle", "mot_de_passe": "MotDePasse123!", "accepte_conditions": True},
            format="json",
        )
        self.assertEqual(inscription.status_code, 201, inscription.data)
        connexion = self.client_api.post(
            "/api/auth/connexion/",
            {"email": "nouvelle@example.test", "mot_de_passe": "MotDePasse123!"},
            format="json",
        )
        self.assertEqual(connexion.status_code, 200, connexion.data)
        self.assertIn("access", connexion.data)
        self.assertIn("refresh", connexion.data)


class AbonnementAPITests(TestCase):
    def setUp(self):
        self.commercant = Commercant.objects.create_user(
            email="abonnement-a@example.test",
            telephone="+22991000001", nom_boutique="Boutique Test", password="MotDePasse123!"
        )
        self.autre = Commercant.objects.create_user(
            email="abonnement-b@example.test",
            telephone="+22991000002", nom_boutique="Autre Boutique", password="MotDePasse123!"
        )
        self.plan_essai = Plan.objects.get(nom="Essai gratuit")
        self.plan = Plan.objects.create(nom="Mensuel test", prix=2500, duree_jours=30)
        debut = timezone.now()
        for utilisateur in (self.commercant, self.autre):
            Abonnement.objects.create(
                commercant=utilisateur, plan=self.plan_essai,
                statut=Abonnement.Statut.ESSAI, date_debut=debut,
                date_fin=debut + timedelta(days=14),
            )
        self.api = APIClient()
        self.api.force_authenticate(self.commercant)

    def creer_historique(self, commercant=None):
        return PaiementAbonnementHistorique.objects.create(
            commercant=commercant or self.commercant, plan=self.plan,
            montant=self.plan.prix,
        )

    def test_inscription_cree_un_essai_de_quatorze_jours(self):
        response = self.api.post("/api/auth/inscription/", {
            "email": "nouvelle-abonnement@example.test", "telephone": "+22991000003", "nom_boutique": "Nouvelle boutique",
            "mot_de_passe": "MotDePasse123!",
            "accepte_conditions": True,
        }, format="json")
        self.assertEqual(response.status_code, 201)
        essai = Abonnement.objects.get(commercant_id=response.data["id"])
        self.assertEqual(essai.statut, Abonnement.Statut.ESSAI)
        self.assertEqual(essai.plan.nom, "Essai gratuit")
        self.assertAlmostEqual((essai.date_fin - essai.date_debut).total_seconds(), 14 * 86400, delta=2)

    def test_api_plans_et_statut_abonnement_repondent(self):
        offres = self.api.get("/api/plans/")
        etat = self.api.get("/api/abonnement/")
        self.assertEqual(offres.status_code, 200, offres.data)
        self.assertIn("Mensuel", [offre["nom"] for offre in offres.data])
        self.assertEqual(etat.status_code, 200, etat.data)
        self.assertEqual(etat.data["statut"], Abonnement.Statut.ESSAI)
        self.assertEqual(etat.data["jours_restants"], 14)

    def test_commercant_b_ne_voit_pas_les_transactions_de_a(self):
        self.creer_historique(self.commercant)
        self.creer_historique(self.autre)
        response = self.api.get("/api/abonnement/transactions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_anciens_endpoints_automatiques_ne_sont_plus_accessibles(self):
        self.assertEqual(self.api.post("/api/abonnement/payer/", {"plan": self.plan.pk}, format="json").status_code, 404)
        self.assertEqual(self.api.post("/api/abonnement/webhook/", {}, format="json").status_code, 404)

    def test_expiration_bloque_les_ecritures_mais_pas_les_lectures(self):
        abonnement = self.commercant.abonnement
        abonnement.date_fin = timezone.now() - timedelta(seconds=1)
        abonnement.save(update_fields=["date_fin"])
        lecture = self.api.get("/api/produits/")
        ecriture = self.api.post("/api/produits/", {"nom": "Riz", "prix": 1000}, format="json")
        self.assertEqual(lecture.status_code, 200)
        self.assertEqual(ecriture.status_code, 403)
