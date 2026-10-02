"""Tests des cookies JWT, de la rotation et de la révocation serveur."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from .jwt_sessions import creer_jetons_session
from .models import Abonnement, Plan, SessionJWT
from .test_helpers import entete_csrf


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class SessionsJWTTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="jwt@example.test", password="MotDePasse123!", nom_boutique="Boutique JWT",
        )
        plan = Plan.objects.get(nom="Essai gratuit")
        maintenant = timezone.now()
        Abonnement.objects.create(
            commercant=self.user, plan=plan, statut=Abonnement.Statut.ESSAI,
            date_debut=maintenant, date_fin=maintenant + timedelta(days=14),
        )
        self.client_api = APIClient()
        self.csrf = entete_csrf(self.client_api)

    def connexion(self):
        return self.client_api.post("/api/auth/connexion/", {
            "email": self.user.email, "mot_de_passe": "MotDePasse123!",
        }, format="json", **self.csrf)

    def test_connexion_place_les_jetons_dans_des_cookies_httponly(self):
        reponse = self.connexion()
        self.assertEqual(reponse.status_code, 200, reponse.data)
        self.assertNotIn("access", reponse.data)
        self.assertNotIn("refresh", reponse.data)
        self.assertTrue(reponse.cookies["nobi_access"]["httponly"])
        self.assertTrue(reponse.cookies["nobi_refresh"]["httponly"])
        self.assertEqual(self.client_api.get("/api/dashboard/").status_code, 200)

    def test_refresh_fait_rotation_et_refuse_le_rejeu(self):
        connexion = self.connexion()
        self.assertEqual(connexion.status_code, 200)
        ancien_refresh = self.client_api.cookies["nobi_refresh"].value
        renouvellement = self.client_api.post("/api/auth/refresh/", {}, format="json", **self.csrf)
        self.assertEqual(renouvellement.status_code, 200, renouvellement.data)
        nouveau_refresh = self.client_api.cookies["nobi_refresh"].value
        self.assertNotEqual(ancien_refresh, nouveau_refresh)

        client_rejeu = APIClient()
        client_rejeu.cookies["nobi_refresh"] = ancien_refresh
        client_rejeu.cookies["csrftoken"] = self.client_api.cookies["csrftoken"].value
        rejouee = client_rejeu.post("/api/auth/refresh/", {}, format="json", **self.csrf)
        self.assertEqual(rejouee.status_code, 401)

    def test_logout_revoque_egalement_access_token_de_la_session(self):
        self.assertEqual(self.connexion().status_code, 200)
        self.assertEqual(self.client_api.get("/api/dashboard/").status_code, 200)
        sortie = self.client_api.post("/api/auth/deconnexion/", {}, format="json", **self.csrf)
        self.assertEqual(sortie.status_code, 200)
        self.assertEqual(self.client_api.get("/api/dashboard/").status_code, 401)

    def test_session_expiree_access_sans_token_et_token_falsifie_sont_refuses(self):
        self.assertEqual(self.client_api.get("/api/dashboard/").status_code, 401)
        access, _ = creer_jetons_session(self.user)
        session = SessionJWT.objects.get(utilisateur=self.user)
        session.expire_le = timezone.now() - timedelta(seconds=1)
        session.save(update_fields=["expire_le"])
        client = APIClient()
        client.cookies["nobi_access"] = access
        self.assertEqual(client.get("/api/dashboard/").status_code, 401)
        client.cookies["nobi_access"] = "eyJhbGciOiJIUzI1NiJ9.falsifie.signature"
        self.assertEqual(client.get("/api/dashboard/").status_code, 401)

    def test_access_token_expire_et_changement_mot_de_passe_revoquent_les_sessions(self):
        access, _ = creer_jetons_session(self.user)
        jeton_access = AccessToken(access)
        jeton_access.set_exp(lifetime=timedelta(seconds=-1))
        client_expire = APIClient()
        client_expire.cookies["nobi_access"] = str(jeton_access)
        self.assertEqual(client_expire.get("/api/dashboard/").status_code, 401)

        session_client = APIClient()
        csrf = entete_csrf(session_client)
        acces_actif, refresh_actif = creer_jetons_session(self.user)
        session_client.cookies["nobi_access"] = acces_actif
        session_client.cookies["nobi_refresh"] = refresh_actif
        from django.contrib.auth.tokens import default_token_generator
        reinitialisation = session_client.post("/api/auth/mot-de-passe/reinitialiser/", {
            "uid": urlsafe_base64_encode(force_bytes(self.user.pk)),
            "token": default_token_generator.make_token(self.user),
            "nouveau_mot_de_passe": "NouveauMotDePasse2026!",
        }, format="json", **csrf)
        self.assertEqual(reinitialisation.status_code, 200, reinitialisation.data)
        self.assertEqual(session_client.get("/api/dashboard/").status_code, 401)
        refresh_revoque = session_client.post("/api/auth/refresh/", {}, format="json", **csrf)
        self.assertEqual(refresh_revoque.status_code, 401)

    def test_login_refuse_une_requete_sans_csrf(self):
        client = APIClient()
        reponse = client.post("/api/auth/connexion/", {
            "email": self.user.email, "mot_de_passe": "MotDePasse123!",
        }, format="json")
        self.assertEqual(reponse.status_code, 403)
