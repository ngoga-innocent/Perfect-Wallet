# core/pagination.py

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """
    Global pagination used by list endpoints.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100