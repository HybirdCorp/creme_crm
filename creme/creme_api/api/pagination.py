from rest_framework.pagination import CursorPagination


class CremeCursorPagination(CursorPagination):
    ordering = "id"
    page_size_query_param = "page_size"
    max_page_size = 200
