"""Fournit l'adresse IP aux signaux du journal sans la propager entre requêtes."""

from .audit import definir_contexte_requete, reinitialiser_contexte_requete


class ContexteAuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        utilisateur = getattr(request, "user", None)
        jeton = definir_contexte_requete(utilisateur, request.META.get("REMOTE_ADDR"))
        try:
            return self.get_response(request)
        finally:
            reinitialiser_contexte_requete(jeton)
