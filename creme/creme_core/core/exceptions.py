# -*- coding: utf-8 -*-

from django.db.models import ProtectedError


class ConflictError(Exception):
    "Corresponds to HTTP error 409"
    pass


class SpecificProtectedError(ProtectedError):
    """A ProtectedError corresponding to a business logic protection (and not
    a simple dependency problem).
    The message should be localized.
    """
    pass
