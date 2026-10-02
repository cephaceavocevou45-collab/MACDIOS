"""Petits utilitaires partagés par les tests API nécessitant CSRF."""


def entete_csrf(client):
    """Initialise le cookie CSRF et retourne l'en-tête à joindre aux POST."""
    reponse = client.get("/api/auth/csrf/")
    jeton = reponse.data["csrfToken"]
    # Le client de test ne conserve pas toujours le cookie créé par une vue DRF.
    client.cookies["csrftoken"] = jeton
    return {"HTTP_X_CSRFTOKEN": jeton}
