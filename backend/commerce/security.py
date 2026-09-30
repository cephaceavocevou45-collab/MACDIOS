"""Réponses de sécurité en français pour les intégrations Django tierces."""

from django.http import JsonResponse


def reponse_verrouillage(request, response, credentials, *args, **kwargs):
    """Format JSON simple du verrouillage temporaire d'une connexion."""
    return JsonResponse(
        {"detail": "Trop de tentatives de connexion. Réessayez dans 15 minutes."},
        status=429,
    )


def identifiant_connexion(request, credentials):
    """Récupère l'adresse email depuis les identifiants pour Axes."""
    identifiant = (credentials or {}).get("username") or (credentials or {}).get("email")
    if not identifiant:
        identifiant = getattr(request, "data", {}).get("email", "")
    return str(identifiant or "").strip().lower()
