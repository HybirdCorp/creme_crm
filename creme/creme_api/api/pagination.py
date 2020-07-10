from rest_framework.pagination import CursorPagination


class CremeCursorPagination(CursorPagination):
    ordering = 'id'
