# -*- coding: utf-8 -*-

from .entity_credentials import EntityCredentials  # NOQA

# NB: with '*' there cannot be collision with app label
SUPERUSER_PERM = '*superuser*'
STAFF_PERM     = '*staff*'


def build_creation_perm(model):
    return f'{model._meta.app_label}.add_{model.__name__.lower()}'


def build_link_perm(model):
    return f'{model._meta.app_label}.link_{model.__name__.lower()}'
