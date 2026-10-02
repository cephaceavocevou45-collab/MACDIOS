from rest_framework.pagination import PageNumberPagination


class PaginationAudit(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class PaginationStandard(PaginationAudit):
    """Pagination par défaut de toutes les listes d'API exposées."""
