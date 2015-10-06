# -*- coding: utf-8 -*-

__version__ = '1.6 beta'

# TODO: to be removed, it seems fixed in Django 1.8.5
## FIX DJANGO 1.8.X #############################################################
## There's a bug with Django 1.8 migration code, which crashes with
## GenericForeignKeys in some cases (sadly it happens with Creme code).
## We'll remove this crappy monkey patching in a future fix release, when these
## f*cking bug is fixed in Django.
#from django.db import models
#from django.db.migrations import state
#from django.utils import six
#
## Copy of Django's get_related_models_recursive()
#def _fixed_get_related_models_recursive(model):
#    def _related_models(m):
#        return [
#            f.related_model for f in m._meta.get_fields(include_parents=True, include_hidden=True)
#            if f.is_relation and not isinstance(f.related_model, six.string_types)
#            # DAT FIX --------
#            and f.related_model
#            # ----------------
#        ] + [
#            subclass for subclass in m.__subclasses__()
#            if issubclass(subclass, models.Model)
#        ]
#
#    seen = set()
#    queue = _related_models(model)
#    for rel_mod in queue:
#        rel_app_label, rel_model_name = rel_mod._meta.app_label, rel_mod._meta.model_name
#        if (rel_app_label, rel_model_name) in seen:
#            continue
#        seen.add((rel_app_label, rel_model_name))
#        queue.extend(_related_models(rel_mod))
#    return seen - {(model._meta.app_label, model._meta.model_name)}
#
#state.get_related_models_recursive = _fixed_get_related_models_recursive
#
## [END] FIX DJANGO 1.8.X #######################################################

# FIX DJANGO MEDIAGENERATOR 1.12 ###############################################
# There's a bug with Mediagenerator 1.12 + Django 1.8 migration code, which 
# makes the command 'generatemedia' to crashes.
# We'll remove this crappy monkey patching in a future fix release, when these
# f*cking bug is fixed in Mediagenerator.
from django.conf import settings

if 'mediagenerator' in settings.INSTALLED_DJANGO_APPS:
    from mediagenerator.management.commands.generatemedia import Command as GenerateMediaCommand

    GenerateMediaCommand.leave_locale_alone = True

# [END] FIX DJANGO MEDIAGENERATOR 1.12 #########################################
