# -*- coding: utf-8 -*-

__version__ = '1.6 beta'

# App registry hooking ---------------------------------------------------------

from django.apps.config import AppConfig
from django.apps.registry import Apps


AppConfig.all_apps_ready = lambda self: None

_original_populate = Apps.populate


def _hooked_populate(self, installed_apps=None):
    if self.ready:
        return

    if getattr(self, '_all_apps_ready', False):
        return

    _original_populate(self, installed_apps)

    with self._lock:
        if getattr(self, '_all_apps_ready', False):
            return

        for app_config in self.get_app_configs():
            app_config.all_apps_ready()

        self._all_apps_ready = True

Apps.populate = _hooked_populate

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
# There're bugs with Django 1.8 + Mediagenerator 1.12 code, which
# make the command 'generatemedia' to crash.
# We'll remove these crappy monkey patchings in a future fix release, when these
# f*cking bugs are fixed in Mediagenerator.
from django.conf import settings


if 'mediagenerator' in settings.INSTALLED_DJANGO_APPS:
    from os.path import join

    from django.apps import apps

    from mediagenerator.management.commands.generatemedia import Command as GenerateMediaCommand
    from mediagenerator import utils as mediagenerator_utils
    from mediagenerator.utils import _media_dirs_cache
    from mediagenerator.settings import GLOBAL_MEDIA_DIRS, IGNORE_APP_MEDIA_DIRS

    def get_media_dirs():
        if not _media_dirs_cache:
            if not apps.ready:
                apps.populate(settings.INSTALLED_APPS)

            media_dirs = GLOBAL_MEDIA_DIRS[:]
            for app in apps.get_app_configs():
                if app.name in IGNORE_APP_MEDIA_DIRS:
                    continue

                media_dirs.append(join(app.path, u'static'))
                media_dirs.append(join(app.path, u'media'))

            _media_dirs_cache.extend(media_dirs)
        return _media_dirs_cache

    mediagenerator_utils.get_media_dirs = get_media_dirs
    GenerateMediaCommand.leave_locale_alone = True

# [END] FIX DJANGO MEDIAGENERATOR 1.12 #########################################
