"""Tests de sécurité tenant, throttling, audit et données personnelles."""

import json
import gzip
import os
import re
import tempfile
import unittest
from datetime import timedelta
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from axes.models import AccessAttempt, AccessFailureLog, AccessLog
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.core.cache import cache
from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from cryptography.fernet import Fernet

from .admin import JournalAuditAdmin
from config.observabilite import filtrer_evenement_sentry
from .models import (
    Abonnement, Client, CorrectionDette, Dette, JournalAudit, Paiement, Plan, Produit,
    PaiementAbonnementHistorique, Vente,
)
from .test_helpers import entete_csrf

Commercant = get_user_model()


class SecuriteEtDonneesTests(TestCase):
    def setUp(self):
        self.user = Commercant.objects.create_user(
            email="securite-a@example.test",
            telephone="+22992000001", nom_boutique="Boutique test", password="MotDePasse123!"
        )
        self.autre = Commercant.objects.create_user(
            email="securite-b@example.test",
            telephone="+22992000002", nom_boutique="Autre test", password="MotDePasse123!"
        )
        self.plan = Plan.objects.get(nom="Essai gratuit")
        debut = timezone.now()
        for user in (self.user, self.autre):
            Abonnement.objects.create(
                commercant=user, plan=self.plan, statut=Abonnement.Statut.ESSAI,
                date_debut=debut, date_fin=debut + timedelta(days=14),
            )
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        from django.core.cache import cache
        cache.clear()

    def test_throttle_connexion_refuse_la_requete_suivante(self):
        reglages = {"DEFAULT_THROTTLE_RATES": {"connexion": "1/minute"}}
        csrf = entete_csrf(self.api)
        with override_settings(REST_FRAMEWORK=reglages):
            premiere = self.api.post("/api/auth/connexion/", {"email": "inconnu@example.test", "mot_de_passe": "x"}, format="json", **csrf)
            seconde = self.api.post("/api/auth/connexion/", {"email": "inconnu@example.test", "mot_de_passe": "x"}, format="json", **csrf)
        self.assertEqual(premiere.status_code, 400)
        self.assertEqual(seconde.status_code, 429)

    @unittest.skipUnless(os.environ.get("REDIS_URL", "").startswith(("redis://", "rediss://")), "Redis de test non configuré.")
    def test_rate_limit_est_partage_entre_deux_clients_via_redis(self):
        reglages = {"DEFAULT_THROTTLE_RATES": {"connexion": "1/minute"}}
        cache.clear()
        premier_client = APIClient()
        second_client = APIClient()
        csrf_premier = entete_csrf(premier_client)
        csrf_second = entete_csrf(second_client)
        with override_settings(REST_FRAMEWORK=reglages):
            premiere = premier_client.post("/api/auth/connexion/", {
                "email": "absent@example.test", "mot_de_passe": "invalide",
            }, format="json", **csrf_premier)
            seconde = second_client.post("/api/auth/connexion/", {
                "email": "absent@example.test", "mot_de_passe": "invalide",
            }, format="json", **csrf_second)
        self.assertEqual(premiere.status_code, 400)
        self.assertEqual(seconde.status_code, 429)

    def test_throttle_inscription_et_renouvellement_jwt(self):
        reglages = {"DEFAULT_THROTTLE_RATES": {"inscription": "1/minute", "refresh": "1/minute"}}
        with override_settings(REST_FRAMEWORK=reglages):
            premiere = self.api.post("/api/auth/inscription/", {
                "telephone": "+22992000003", "nom_boutique": "Nouveau",
                "mot_de_passe": "MotDePasse123!", "confirmation_mot_de_passe": "MotDePasse123!", "accepte_conditions": True,
            }, format="json")
            seconde = self.api.post("/api/auth/inscription/", {
                "telephone": "+22992000004", "nom_boutique": "Nouveau deux",
                "mot_de_passe": "MotDePasse123!", "confirmation_mot_de_passe": "MotDePasse123!", "accepte_conditions": True,
            }, format="json")
        self.assertEqual(premiere.status_code, 201, premiere.data)
        self.assertEqual(seconde.status_code, 429)

        client_session = APIClient()
        csrf_session = entete_csrf(client_session)
        connexion = client_session.post("/api/auth/connexion/", {
            "email": self.user.email, "mot_de_passe": "MotDePasse123!",
        }, format="json", **csrf_session)
        self.assertEqual(connexion.status_code, 200, connexion.data)
        with override_settings(REST_FRAMEWORK=reglages):
            premier_refresh = client_session.post("/api/auth/refresh/", {}, format="json", **csrf_session)
            second_refresh = client_session.post("/api/auth/refresh/", {}, format="json", **csrf_session)
        self.assertEqual(premier_refresh.status_code, 200, premier_refresh.data)
        self.assertEqual(second_refresh.status_code, 429)

    @override_settings(AXES_FAILURE_LIMIT=3, AXES_COOLOFF_TIME=timedelta(minutes=15))
    def test_axes_verrouille_apres_trois_mauvais_mots_de_passe(self):
        client = APIClient()
        csrf = entete_csrf(client)
        resultats = [client.post("/api/auth/connexion/", {
            "email": self.user.email, "mot_de_passe": "incorrect",
        }, format="json", **csrf) for _ in range(3)]
        verrouillage = client.post("/api/auth/connexion/", {
            "email": self.user.email, "mot_de_passe": "MotDePasse123!",
        }, format="json", **csrf)
        self.assertTrue(all(resultat.status_code in (400, 403, 429) for resultat in resultats))
        self.assertEqual(verrouillage.status_code, 429, verrouillage.data)
        self.assertIn("15 minutes", str(verrouillage.data))
        entree = JournalAudit.objects.filter(
            commercant=self.user, action=JournalAudit.Action.CONNEXION_ECHOUEE,
        ).first()
        self.assertIsNotNone(entree)
        self.assertNotIn("telephone", json.dumps(entree.nouvelles_valeurs).lower())
        self.assertNotIn("motdepasse", json.dumps(entree.nouvelles_valeurs).lower())

    def test_audit_enregistre_operations_et_admin_refuse_toute_ecriture(self):
        produit = Produit.objects.create(commercant=self.user, nom="Riz", prix=1000, quantite_stock=10)
        produit.prix = 1200
        produit.quantite_stock = 7
        produit.save()
        dette = Dette.objects.create(
            commercant=self.user,
            client=Client.objects.create(commercant=self.user, nom="Client"),
            montant=500,
            note="Appeler 22990000000; token=secret-test",
        )
        client = dette.client
        vente = Vente.objects.create(
            commercant=self.user, produit=produit, client=client, quantite=1,
            prix_unitaire=produit.prix, total=produit.prix,
        )
        paiement = Paiement.objects.create(commercant=self.user, client=client, montant=100)
        actions = set(JournalAudit.objects.filter(commercant=self.user).values_list("action", flat=True))
        self.assertIn(JournalAudit.Action.CREATION, actions)
        self.assertIn(JournalAudit.Action.MODIFICATION, actions)
        self.assertIn(JournalAudit.Action.CHANGEMENT_STOCK, actions)
        self.assertTrue(JournalAudit.objects.filter(
            objet_type="Vente", objet_id=str(vente.pk), action=JournalAudit.Action.CREATION,
        ).exists())
        self.assertTrue(JournalAudit.objects.filter(
            objet_type="Paiement", objet_id=str(paiement.pk), action=JournalAudit.Action.CREATION,
        ).exists())
        audit_dette = JournalAudit.objects.get(objet_type="Dette", objet_id=str(dette.pk))
        texte_audit = json.dumps(audit_dette.nouvelles_valeurs)
        self.assertNotIn("22990000000", texte_audit)
        self.assertNotIn("secret-test", texte_audit)
        journal_admin = JournalAuditAdmin(JournalAudit, admin.site)
        request = type("Requete", (), {"user": self.user})()
        self.assertFalse(journal_admin.has_add_permission(request))
        self.assertFalse(journal_admin.has_change_permission(request))
        self.assertFalse(journal_admin.has_delete_permission(request))
        self.assertEqual(self.api.put("/api/audit/", {}, format="json").status_code, 405)
        self.assertEqual(self.api.delete("/api/audit/").status_code, 405)

    def test_audit_est_pagine_filtre_et_isole_par_commercant(self):
        evenement_a = JournalAudit.objects.create(
            commercant=self.user, utilisateur=self.user, action=JournalAudit.Action.CREATION,
            objet_type="Produit", objet_id="1", nouvelles_valeurs={"nom": "Riz"},
        )
        JournalAudit.objects.create(
            commercant=self.autre, utilisateur=self.autre, action=JournalAudit.Action.SUPPRESSION,
            objet_type="Produit", objet_id="2",
        )
        response = self.api.get("/api/audit/", {"action": "creation", "date_debut": timezone.localdate().isoformat()})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], evenement_a.id)
        invalide = self.api.get("/api/audit/", {"action": "mot_de_passe"})
        self.assertEqual(invalide.status_code, 400)

    def test_export_contient_seulement_les_donnees_du_proprietaire_sans_hash(self):
        produit_a = Produit.objects.create(commercant=self.user, nom="Riz", prix=1000, quantite_stock=3)
        client_a = Client.objects.create(commercant=self.user, nom="Awa")
        Vente.objects.create(commercant=self.user, produit=produit_a, client=client_a, quantite=1,
                             prix_unitaire=1000, total=1000)
        dette_a = Dette.objects.create(commercant=self.user, client=client_a, montant=1500, note="A credit")
        CorrectionDette.objects.create(commercant=self.user, dette=dette_a, montant_precedent=1500,
                                       nouveau_montant=1200, raison="Correction de saisie")
        Paiement.objects.create(commercant=self.user, client=client_a, montant=500)
        Produit.objects.create(commercant=self.autre, nom="Huile confidentielle", prix=250, quantite_stock=8)
        response = self.api.get("/api/compte/export/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("export-donnees-commerce.pdf", response["Content-Disposition"])
        document = response.content
        self.assertTrue(document.startswith(b"%PDF-"))
        for texte in ("Boutique test", "Riz", "Awa", "Historique des ventes", "Paiement", "Correction de saisie", "FCFA"):
            self.assertIn(texte.encode("ascii"), document)
        self.assertNotIn(b"Huile confidentielle", document)
        self.assertNotIn(b"MotDePasse123!", document)

        # L'export d'un autre compte ne peut pas inclure les éléments du premier.
        self.api.force_authenticate(self.autre)
        Produit.objects.create(commercant=self.autre, nom="Huile de B", prix=250, quantite_stock=8)
        export_autre = self.api.get("/api/compte/export/")
        self.assertEqual(export_autre.status_code, 200)
        self.assertIn(b"Huile de B", export_autre.content)
        self.assertNotIn(b"Riz", export_autre.content)

    def test_export_pdf_pagine_un_catalogue_nombreux_sans_perdre_la_fin(self):
        for index in range(75):
            Produit.objects.create(
                commercant=self.user,
                nom=f"Produit {index:03d} - catégorie locale et description détaillée",
                prix=100 + index,
                quantite_stock=index,
            )
        response = self.api.get("/api/compte/export/")
        self.assertEqual(response.status_code, 200)
        pages = re.findall(rb"/Type\s*/Page\b", response.content)
        self.assertGreater(len(pages), 1)
        self.assertIn(b"Produit 074", response.content)

    def test_suppression_compte_efface_toutes_les_donnees_associees(self):
        identifiant_utilisateur = self.user.pk
        produit = Produit.objects.create(commercant=self.user, nom="Riz", prix=1000, quantite_stock=4)
        client = Client.objects.create(commercant=self.user, nom="Awa", telephone="22990000000")
        Dette.objects.create(commercant=self.user, client=client, montant=200)
        Paiement.objects.create(commercant=self.user, client=client, montant=100)
        vente = Vente.objects.create(
            commercant=self.user, produit=produit, client=client, quantite=1,
            prix_unitaire=1000, total=1000,
        )
        PaiementAbonnementHistorique.objects.create(commercant=self.user, plan=self.plan, montant=1)
        AccessAttempt.objects.create(username=self.user.email, ip_address="127.0.0.1", user_agent="test", http_accept="", path_info="/", get_data="", post_data="", failures_since_start=1)
        AccessFailureLog.objects.create(username=self.user.email, ip_address="127.0.0.1", user_agent="test", http_accept="", path_info="/")
        AccessLog.objects.create(username=self.user.email, ip_address="127.0.0.1", user_agent="test", http_accept="", path_info="/")
        JournalAudit.objects.create(commercant=self.user, utilisateur=self.user, action="creation", objet_type="Test")

        invalide = self.api.delete("/api/compte/", {"mot_de_passe": "faux"}, format="json")
        self.assertEqual(invalide.status_code, 400)
        supprime = self.api.delete("/api/compte/", {"mot_de_passe": "MotDePasse123!"}, format="json")
        self.assertEqual(supprime.status_code, 204)
        self.assertFalse(Commercant.objects.filter(pk=self.user.pk).exists())
        self.assertFalse(Produit.objects.filter(pk=produit.pk).exists())
        self.assertFalse(Client.objects.filter(pk=client.pk).exists())
        self.assertFalse(Vente.objects.filter(pk=vente.pk).exists())
        self.assertFalse(JournalAudit.objects.filter(commercant_id=identifiant_utilisateur).exists())
        self.assertFalse(AccessAttempt.objects.filter(username=self.user.email).exists())
        self.assertFalse(AccessFailureLog.objects.filter(username=self.user.email).exists())
        self.assertFalse(AccessLog.objects.filter(username=self.user.email).exists())
        self.assertFalse(AccessAttempt.objects.filter(username=self.user.telephone).exists())

    def test_health_check_repond_sans_detail_interne_et_signale_base_indisponible(self):
        response = self.api.get("/api/sante/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"statut": "ok", "base_de_donnees": "disponible"})
        with patch("commerce.views.connection.cursor", side_effect=DatabaseError("secret de base")):
            indisponible = self.api.get("/api/sante/")
        self.assertEqual(indisponible.status_code, 503)
        self.assertNotIn("secret de base", str(indisponible.data))

    def test_sauvegarde_chiffree_peut_etre_restauree(self):
        produit = Produit.objects.create(commercant=self.user, nom="Produit sauvegardé", prix=700, quantite_stock=2)
        cle = Fernet.generate_key().decode("ascii")
        with tempfile.TemporaryDirectory() as dossier:
            fichier = Path(dossier) / "sauvegarde.json.gz.fernet"
            with override_settings(BACKUP_ENCRYPTION_KEY=cle, BACKUP_S3_BUCKET="", EST_PRODUCTION=False):
                call_command("sauvegarde_db", sortie=fichier, verbosity=0)
            self.assertTrue(fichier.exists())
            dechiffre = Fernet(cle.encode("ascii")).decrypt(fichier.read_bytes())
            contenu = json.loads(gzip.decompress(dechiffre).decode("utf-8"))
            self.assertTrue(any(ligne["pk"] == produit.pk for ligne in contenu if ligne["model"] == "commerce.produit"))
            identifiant_produit = produit.pk
            produit.delete()
            with override_settings(BACKUP_ENCRYPTION_KEY=cle, EST_PRODUCTION=False):
                call_command("restaure_db", fichier, verbosity=0)
            self.assertTrue(Produit.objects.filter(pk=identifiant_produit).exists())

    def test_sauvegarde_s3_est_verifiee_et_peut_etre_restauree_directement(self):
        produit = Produit.objects.create(commercant=self.user, nom="Produit S3", prix=900, quantite_stock=3)
        cle = Fernet.generate_key().decode("ascii")
        with (
            patch("commerce.management.commands.sauvegarde_db.client_s3") as creer_client,
            patch("commerce.management.commands.restaure_db.client_s3", return_value=creer_client.return_value),
        ):
            s3 = creer_client.return_value
            s3.head_object.side_effect = lambda **kwargs: {
                "Metadata": {"sha256": s3.put_object.call_args.kwargs["Metadata"]["sha256"]}
            }
            with override_settings(
                BACKUP_ENCRYPTION_KEY=cle,
                BACKUP_S3_BUCKET="bucket-test",
                BACKUP_S3_PREFIX="macdios/database",
                EST_PRODUCTION=False,
            ):
                call_command("sauvegarde_db", verbosity=0)

            depot = s3.put_object.call_args.kwargs
            self.assertEqual(depot["Bucket"], "bucket-test")
            self.assertTrue(depot["Key"].startswith("macdios/database/sauvegarde_"))
            self.assertNotIn("ServerSideEncryption", depot)
            self.assertEqual(depot["Metadata"]["sha256"], sha256(depot["Body"]).hexdigest())
            self.assertTrue(depot["Body"].startswith(b"gAAAA"))

            produit_id = produit.pk
            produit.delete()
            s3.get_object.return_value = {
                "Body": BytesIO(depot["Body"]),
                "Metadata": depot["Metadata"],
            }
            with override_settings(
                BACKUP_ENCRYPTION_KEY=cle,
                BACKUP_S3_BUCKET="bucket-test",
                EST_PRODUCTION=False,
            ):
                call_command("restaure_db", "--s3-key", depot["Key"], verbosity=0)

        self.assertTrue(Produit.objects.filter(pk=produit_id).exists())

    def test_restauration_s3_refuse_une_empreinte_invalide(self):
        cle = Fernet.generate_key().decode("ascii")
        with patch("commerce.management.commands.restaure_db.client_s3") as creer_client:
            creer_client.return_value.get_object.return_value = {
                "Body": BytesIO(b"fichier altere"),
                "Metadata": {"sha256": "empreinte-incorrecte"},
            }
            with override_settings(
                BACKUP_ENCRYPTION_KEY=cle,
                BACKUP_S3_BUCKET="bucket-test",
                EST_PRODUCTION=False,
            ):
                with self.assertRaisesMessage(CommandError, "empreinte SHA-256 est invalide"):
                    call_command("restaure_db", "--s3-key", "macdios/database/sauvegarde-invalide", verbosity=0)

    def test_sauvegarde_production_sans_s3_echoue_sans_creer_de_fichier(self):
        cle = Fernet.generate_key().decode("ascii")
        with tempfile.TemporaryDirectory() as dossier:
            fichier = Path(dossier) / "sauvegarde-production.json.gz.fernet"
            with override_settings(
                EST_PRODUCTION=True,
                SAUVEGARDE_S3_ACTIVE=False,
                BACKUP_ENCRYPTION_KEY=cle,
                BACKUP_S3_BUCKET="",
            ):
                with self.assertRaisesMessage(CommandError, "Sauvegarde de production désactivée"):
                    call_command("sauvegarde_db", sortie=fichier, verbosity=0)
            self.assertFalse(fichier.exists())

    def test_inscription_exige_consentement_et_enregistre_sa_date(self):
        sans_consentement = self.api.post("/api/auth/inscription/", {
            "telephone": "+22992000003", "nom_boutique": "Nouvelle boutique",
            "mot_de_passe": "MotDePasse123!", "confirmation_mot_de_passe": "MotDePasse123!", "accepte_conditions": False,
        }, format="json")
        self.assertEqual(sans_consentement.status_code, 400)
        acceptee = self.api.post("/api/auth/inscription/", {
            "telephone": "+22992000003", "nom_boutique": "Nouvelle boutique",
            "mot_de_passe": "MotDePasse123!", "confirmation_mot_de_passe": "MotDePasse123!", "accepte_conditions": True,
        }, format="json")
        self.assertEqual(acceptee.status_code, 201, acceptee.data)
        self.assertIsNotNone(Commercant.objects.get(pk=acceptee.data["id"]).consentement_le)

    def test_sentry_masque_identite_mot_de_passe_et_tokens(self):
        evenement = {
            "user": {"username": "22992000001"},
            "message": "échec token=jeton-secret",
            "request": {
            "data": {"email": "prive@example.test", "telephone": "22990000000", "mot_de_passe": "mot-de-passe-secret"},
                "headers": {"Authorization": "Bearer eyJabcdefghijk.abcdefghijk.abcdefghijk"},
            },
        }
        resultat = filtrer_evenement_sentry(evenement, {})
        export = json.dumps(resultat)
        for donnee_interdite in (
            "securite-a@example.test", "prive@example.test", "22992000001", "22990000000",
            "mot-de-passe-secret", "jeton-secret", "eyJabcdefghijk",
        ):
            self.assertNotIn(donnee_interdite, export)
