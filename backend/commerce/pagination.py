from rest_framework.pagination import PageNumberPagination


class PaginationAudit(PageNumberPagination):
    page_size = 20
    page_size_query_param = "taille_page"
    max_page_size = 100
