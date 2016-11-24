# -*- coding: utf-8 -*-

from .entity_credentials import EntityCredentials  # NOQA


def build_creation_perm(model):
    return '%s.add_%s' % (model._meta.app_label, model.__name__.lower())


def build_link_perm(model):
    return '%s.link_%s' % (model._meta.app_label, model.__name__.lower())
