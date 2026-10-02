from django.contrib.auth import get_user_model
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections, connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Abonnement, Client, Dette, Paiement, PaiementAbonnementHistorique, Plan, Produit, Vente
from .test_helpers import entete_csrf

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

    def test_vente_rejouee_avec_la_meme_cle_ne_decremente_pas_deux_fois(self):
        donnees = {"produit": self.produit.pk, "quantite": 2}
        entetes = {"HTTP_IDEMPOTENCY_KEY": "vente-reseau-123"}
        premiere = self.client_api.post("/api/ventes/", donnees, format="json", **entetes)
        rejouee = self.client_api.post("/api/ventes/", donnees, format="json", **entetes)

        self.assertEqual(premiere.status_code, 201, premiere.data)
        self.assertEqual(rejouee.status_code, 201, rejouee.data)
        self.assertEqual(rejouee.data["id"], premiere.data["id"])
        self.produit.refresh_from_db()
        self.assertEqual(self.produit.quantite_stock, 8)
        self.assertEqual(Vente.objects.filter(produit=self.produit).count(), 1)

    def test_cle_idempotence_reutilisee_avec_un_autre_corps_est_refusee(self):
        entetes = {"HTTP_IDEMPOTENCY_KEY": "vente-reseau-456"}
        premiere = self.client_api.post(
            "/api/ventes/", {"produit": self.produit.pk, "quantite": 1}, format="json", **entetes
        )
        conflit = self.client_api.post(
            "/api/ventes/", {"produit": self.produit.pk, "quantite": 2}, format="json", **entetes
        )

        self.assertEqual(premiere.status_code, 201, premiere.data)
        self.assertEqual(conflit.status_code, 409, conflit.data)
        self.assertEqual(Vente.objects.count(), 1)
        self.produit.refresh_from_db()
        self.assertEqual(self.produit.quantite_stock, 9)

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
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["nom"], "Riz")

    def test_pagination_liste_produits_filtre_limites_et_page_inexistante(self):
        for index in range(105):
            Produit.objects.create(
                commercant=self.user, nom=f"Article {index:02}", prix=100,
                quantite_stock=index, seuil_alerte=0,
            )
        premiere = self.client_api.get("/api/produits/?page=1&page_size=20")
        seconde = self.client_api.get("/api/produits/?page=2&page_size=20")
        trop_grande = self.client_api.get("/api/produits/?page=1&page_size=1000000")
        inexistante = self.client_api.get("/api/produits/?page=7&page_size=20")
        filtree = self.client_api.get("/api/produits/?rupture=true&page_size=100")

        self.assertEqual(premiere.status_code, 200)
        self.assertEqual(premiere.data["count"], 106)
        self.assertEqual(len(premiere.data["results"]), 20)
        self.assertIsNotNone(premiere.data["next"])
        self.assertEqual(len(seconde.data["results"]), 20)
        self.assertEqual(len(trop_grande.data["results"]), 100)
        self.assertEqual(inexistante.status_code, 404)
        self.assertTrue(all(item["quantite_stock"] <= item["seuil_alerte"] for item in filtree.data["results"]))

    def test_isolation_complete_des_objets_et_rejet_des_identifiants_etrangers(self):
        produit_b = Produit.objects.create(commercant=self.autre, nom="Huile B", prix=500, quantite_stock=4)
        client_b = Client.objects.create(commercant=self.autre, nom="Client B")
        vente_b = Vente.objects.create(
            commercant=self.autre, produit=produit_b, client=client_b,
            quantite=1, prix_unitaire=500, total=500,
        )
        dette_b = Dette.objects.create(commercant=self.autre, client=client_b, montant=800)
        paiement_b = Paiement.objects.create(commercant=self.autre, client=client_b, montant=100)

        routes_objets_etrangers = (
            f"/api/produits/{produit_b.pk}/", f"/api/clients/{client_b.pk}/",
            f"/api/ventes/{vente_b.pk}/", f"/api/dettes/{dette_b.pk}/", f"/api/paiements/{paiement_b.pk}/",
        )
        for route in routes_objets_etrangers:
            with self.subTest(route=route):
                self.assertEqual(self.client_api.get(route).status_code, 404)

        for method in ("put", "patch", "delete"):
            for route in routes_objets_etrangers:
                with self.subTest(method=method, route=route):
                    reponse = getattr(self.client_api, method)(route, {"nom": "Manipulé", "montant": 1}, format="json")
                    self.assertIn(reponse.status_code, (404, 405))

        self.assertEqual(self.client_api.post(
            "/api/ventes/", {"produit": produit_b.pk, "quantite": 1}, format="json"
        ).status_code, 400)
        self.assertEqual(self.client_api.post(
            "/api/dettes/", {"client": client_b.pk, "montant": "10.00"}, format="json"
        ).status_code, 400)
        self.assertEqual(self.client_api.post(
            "/api/paiements/", {"client": client_b.pk, "montant": "10.00"}, format="json"
        ).status_code, 400)

    def test_champ_commercant_envoye_par_le_client_est_ignore(self):
        creation = self.client_api.post("/api/produits/", {
            "nom": "Produit isolé", "prix": "100.00", "commercant": self.autre.pk,
            "merchant_id": self.autre.pk, "owner_id": self.autre.pk, "user_id": self.autre.pk,
            "role": "admin", "is_staff": True, "is_superuser": True,
            "subscription": "active", "balance": "999999999", "solde": "999999999",
            "status": "active", "permissions": ["*"],
        }, format="json")
        self.assertEqual(creation.status_code, 201, creation.data)
        produit = Produit.objects.get(pk=creation.data["id"])
        self.assertEqual(produit.commercant_id, self.user.pk)
        self.assertTrue(produit.actif)

    def test_les_champs_sensibles_du_client_sont_ignores_en_creation_et_modification(self):
        creation = self.client_api.post("/api/clients/", {
            "nom": "Client sécurisé", "commercant": self.autre.pk,
            "merchant_id": self.autre.pk, "owner_id": self.autre.pk,
            "solde": "999999999", "balance": "999999999", "status": "active",
            "role": "admin", "is_staff": True, "permissions": ["*"],
        }, format="json")
        self.assertEqual(creation.status_code, 201, creation.data)
        client = Client.objects.get(pk=creation.data["id"])
        self.assertEqual(client.commercant_id, self.user.pk)
        self.assertEqual(client.solde, 0)
        self.assertTrue(client.actif)

        modification = self.client_api.patch(
            f"/api/clients/{client.pk}/",
            {"nom": "Client modifié", "commercant": self.autre.pk, "solde": "999999999", "actif": False},
            format="json",
        )
        self.assertEqual(modification.status_code, 200, modification.data)
        client.refresh_from_db()
        self.assertEqual(client.commercant_id, self.user.pk)
        self.assertEqual(client.solde, 0)
        self.assertTrue(client.actif)

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

    def test_archivage_produit_preserve_les_ventes_et_empeche_une_nouvelle_vente(self):
        vente = self.client_api.post(
            "/api/ventes/", {"produit": self.produit.pk, "quantite": 1}, format="json"
        )
        self.assertEqual(vente.status_code, 201, vente.data)

        archivage = self.client_api.delete(f"/api/produits/{self.produit.pk}/")

        self.assertEqual(archivage.status_code, 204)
        self.produit.refresh_from_db()
        self.assertFalse(self.produit.actif)
        self.assertTrue(Vente.objects.filter(pk=vente.data["id"], produit=self.produit).exists())
        self.assertEqual(self.client_api.get("/api/produits/").data["count"], 0)
        nouvelle_vente = self.client_api.post(
            "/api/ventes/", {"produit": self.produit.pk, "quantite": 1}, format="json"
        )
        self.assertEqual(nouvelle_vente.status_code, 400)

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

    def test_archivage_client_preserve_dettes_et_paiements(self):
        dette = Dette.objects.create(
            commercant=self.user, client=self.client_obj, montant="5000.00"
        )
        paiement = Paiement.objects.create(
            commercant=self.user, client=self.client_obj, montant="1200.00"
        )

        reponse = self.client_api.delete(f"/api/clients/{self.client_obj.pk}/")

        self.assertEqual(reponse.status_code, 204)
        self.client_obj.refresh_from_db()
        self.assertFalse(self.client_obj.actif)
        self.assertTrue(Dette.objects.filter(pk=dette.pk, client=self.client_obj).exists())
        self.assertTrue(Paiement.objects.filter(pk=paiement.pk, client=self.client_obj).exists())
        from django.db.models.deletion import ProtectedError
        with self.assertRaises(ProtectedError):
            self.client_obj.delete()
        self.assertFalse(any(c["id"] == self.client_obj.pk for c in self.client_api.get("/api/clients/").data["results"]))
        detail = self.client_api.get(f"/api/clients/{self.client_obj.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertFalse(detail.data["actif"])

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
                self.assertEqual(len(response.data["results"]), 1)

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

    def test_paiement_est_refuse_si_le_solde_a_deja_baisse(self):
        Dette.objects.create(commercant=self.user, client=self.client_obj, montant="10000.00")
        premier = self.client_api.post(
            "/api/paiements/", {"client": self.client_obj.pk, "montant": "8000.00"}, format="json"
        )
        second = self.client_api.post(
            "/api/paiements/", {"client": self.client_obj.pk, "montant": "8000.00"}, format="json"
        )
        self.assertEqual(premier.status_code, 201, premier.data)
        self.assertEqual(second.status_code, 400, second.data)
        self.assertEqual(Paiement.objects.filter(client=self.client_obj).count(), 1)
        self.assertEqual(self.client_obj.solde, 2000)

    def test_paiement_rejoue_ne_cree_pas_un_second_reglement(self):
        Dette.objects.create(commercant=self.user, client=self.client_obj, montant="5000.00")
        donnees = {"client": self.client_obj.pk, "montant": "1200.00"}
        entetes = {"HTTP_IDEMPOTENCY_KEY": "paiement-reseau-123"}
        premiere = self.client_api.post("/api/paiements/", donnees, format="json", **entetes)
        rejouee = self.client_api.post("/api/paiements/", donnees, format="json", **entetes)

        self.assertEqual(premiere.status_code, 201, premiere.data)
        self.assertEqual(rejouee.status_code, 201, rejouee.data)
        self.assertEqual(rejouee.data["id"], premiere.data["id"])
        self.assertEqual(Paiement.objects.filter(client=self.client_obj).count(), 1)
        self.assertEqual(self.client_obj.solde, 3800)

    def test_correction_dette_ne_peut_pas_rendre_le_solde_negatif(self):
        dette = self.client_api.post(
            "/api/dettes/", {"client": self.client_obj.pk, "montant": "5000.00"}, format="json"
        )
        self.assertEqual(dette.status_code, 201, dette.data)
        paiement = self.client_api.post(
            "/api/paiements/", {"client": self.client_obj.pk, "montant": "1200.00"}, format="json"
        )
        self.assertEqual(paiement.status_code, 201, paiement.data)

        correction = self.client_api.post(
            f"/api/dettes/{dette.data['id']}/correction/",
            {"nouveau_montant": "1000.00", "raison": "Montant mal saisi"},
            format="json",
        )

        self.assertEqual(correction.status_code, 400, correction.data)
        dette_obj = Dette.objects.get(pk=dette.data["id"])
        self.assertEqual(dette_obj.montant, 5000)
        self.assertFalse(dette_obj.corrections.exists())


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
        self.assertEqual(response.data["produits_en_rupture_total"], 1)

    def test_dashboard_limite_la_liste_des_ruptures(self):
        Produit.objects.bulk_create([
            Produit(commercant=self.user, nom=f"Rupture {index:03}", prix=10, quantite_stock=0)
            for index in range(105)
        ])
        response = self.client_api.get("/api/dashboard/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["produits_en_rupture"]), 100)
        self.assertEqual(response.data["produits_en_rupture_total"], 105)

    def test_auth_inscription_et_connexion_jwt(self):
        csrf = entete_csrf(self.client_api)
        inscription = self.client_api.post(
            "/api/auth/inscription/",
            {"email": "nouvelle@example.test", "telephone": "+22990000003", "nom_boutique": "Nouvelle", "mot_de_passe": "MotDePasse123!", "accepte_conditions": True},
            format="json",
            **csrf,
        )
        self.assertEqual(inscription.status_code, 201, inscription.data)
        connexion = self.client_api.post(
            "/api/auth/connexion/",
            {"email": "nouvelle@example.test", "mot_de_passe": "MotDePasse123!"},
            format="json",
            **csrf,
        )
        self.assertEqual(connexion.status_code, 200, connexion.data)
        self.assertNotIn("access", connexion.data)
        self.assertNotIn("refresh", connexion.data)
        self.assertTrue(connexion.cookies["nobi_access"]["httponly"])


@skipUnlessDBFeature("has_select_for_update")
class PaiementConcurrenceTests(TransactionTestCase):
    """Deux règlements simultanés ne peuvent pas dépasser le solde disponible."""

    reset_sequences = True

    def setUp(self):
        self.user = Commercant.objects.create_user(
            email="paiement-concurrent@example.test",
            nom_boutique="Boutique concurrente",
            password="MotDePasse123!",
        )
        self.plan, _ = Plan.objects.get_or_create(
            nom="Essai gratuit",
            defaults={"prix": "0.00", "duree_jours": 14, "actif": True},
        )
        maintenant = timezone.now()
        Abonnement.objects.create(
            commercant=self.user,
            plan=self.plan,
            statut=Abonnement.Statut.ESSAI,
            date_debut=maintenant,
            date_fin=maintenant + timedelta(days=14),
        )
        self.client_obj = Client.objects.create(commercant=self.user, nom="Client concurrent")
        Dette.objects.create(commercant=self.user, client=self.client_obj, montant="10000.00")

    def _payer_en_thread(self):
        close_old_connections()
        try:
            utilisateur = Commercant.objects.get(pk=self.user.pk)
            api = APIClient()
            api.force_authenticate(utilisateur)
            reponse = api.post(
                "/api/paiements/",
                {"client": self.client_obj.pk, "montant": "8000.00"},
                format="json",
            )
            return reponse.status_code
        finally:
            connections.close_all()

    def test_deux_paiements_simultanes_sont_serialises_par_client(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuts = list(pool.map(lambda _: self._payer_en_thread(), range(2)))

        self.assertEqual(sorted(statuts), [201, 400])
        self.assertEqual(Paiement.objects.filter(client=self.client_obj).count(), 1)
        self.assertEqual(self.client_obj.solde, 2000)


@skipUnlessDBFeature("has_select_for_update")
class VenteConcurrenceTests(TransactionTestCase):
    """Les ventes simultanées ne peuvent pas vendre deux fois la dernière unité."""

    reset_sequences = True

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.user = Commercant.objects.create_user(
            email="vente-concurrente@example.test", nom_boutique="Boutique stock", password="MotDePasse123!",
        )
        plan, _ = Plan.objects.get_or_create(
            nom="Essai gratuit",
            defaults={"prix": "0.00", "duree_jours": 14, "actif": True},
        )
        maintenant = timezone.now()
        Abonnement.objects.create(
            commercant=self.user, plan=plan, statut=Abonnement.Statut.ESSAI,
            date_debut=maintenant, date_fin=maintenant + timedelta(days=14),
        )
        self.produit = Produit.objects.create(
            commercant=self.user, nom="Dernier sac", prix="4000.00", quantite_stock=1,
        )

    def _vendre_en_thread(self, cle):
        close_old_connections()
        try:
            utilisateur = Commercant.objects.get(pk=self.user.pk)
            api = APIClient()
            api.force_authenticate(utilisateur)
            return api.post(
                "/api/ventes/", {"produit": self.produit.pk, "quantite": 1},
                format="json", HTTP_IDEMPOTENCY_KEY=cle,
            )
        finally:
            connections.close_all()

    def test_ventes_simultanees_ne_peuvent_pas_depasser_le_stock(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            reponses = list(pool.map(lambda cle: self._vendre_en_thread(cle), ("vente-stock-a-001", "vente-stock-b-001")))

        self.assertEqual(sorted(reponse.status_code for reponse in reponses), [201, 400])
        self.produit.refresh_from_db()
        self.assertEqual(self.produit.quantite_stock, 0)
        self.assertEqual(Vente.objects.filter(produit=self.produit).count(), 1)

    def test_idempotence_simultanee_ne_cree_qu_une_vente(self):
        cle = "vente-idem-concurrente-001"
        with ThreadPoolExecutor(max_workers=2) as pool:
            reponses = list(pool.map(lambda _: self._vendre_en_thread(cle), range(2)))

        self.assertEqual([reponse.status_code for reponse in reponses], [201, 201])
        self.assertEqual(reponses[0].data["id"], reponses[1].data["id"])
        self.produit.refresh_from_db()
        self.assertEqual(self.produit.quantite_stock, 0)
        self.assertEqual(Vente.objects.filter(produit=self.produit).count(), 1)


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
        self.assertIn("Mensuel", [offre["nom"] for offre in offres.data["results"]])
        self.assertEqual(etat.status_code, 200, etat.data)
        self.assertEqual(etat.data["statut"], Abonnement.Statut.ESSAI)
        self.assertEqual(etat.data["jours_restants"], 14)

    def test_tarifs_actifs_sont_consultables_sans_connexion(self):
        anonyme = APIClient().get("/api/plans/")
        self.assertEqual(anonyme.status_code, 200, anonyme.data)
        self.assertIn(self.plan.pk, [offre["id"] for offre in anonyme.data["results"]])

    def test_commercant_b_ne_voit_pas_les_transactions_de_a(self):
        self.creer_historique(self.commercant)
        self.creer_historique(self.autre)
        response = self.api.get("/api/abonnement/transactions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)

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


class SoldeClientPerformanceTests(TestCase):
    """Le calcul des soldes d'une liste doit rester dans une seule requête SQL."""

    def test_liste_clients_charge_les_soldes_sans_requete_par_client(self):
        commercant = Commercant.objects.create_user(
            email="solde-performance@example.test", nom_boutique="Boutique", password="MotDePasse123!",
        )
        clients = [Client.objects.create(commercant=commercant, nom=f"Client {index}") for index in range(8)]
        for client in clients:
            Dette.objects.create(commercant=commercant, client=client, montant="10000.00")
            Paiement.objects.create(commercant=commercant, client=client, montant="2500.00")

        api = APIClient()
        api.force_authenticate(commercant)
        # Une requête compte la page; l'autre calcule les soldes sans N+1.
        with self.assertNumQueries(2):
            reponse = api.get("/api/clients/")

        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(len(reponse.data["results"]), 8)
        self.assertTrue(all(str(client["solde"]) == "7500.00" for client in reponse.data["results"]))
