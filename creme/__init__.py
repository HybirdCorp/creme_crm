# -*- coding: utf-8 -*-

__version__ = '1.7 alpha'

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


# FIX DJANGO MEDIAGENERATOR 1.12 ###############################################
# There're bugs with Django 1.8 + Mediagenerator 1.12 code, which
# make the command 'generatemedia' to crash.
# We'll remove these crappy monkey patchings in a future fix release, when these
# f*cking bugs are fixed in Mediagenerator.
from django.conf import settings


try:
    import mediagenerator  # NB: we cannot use django.apps.apps.is_installed here, because apps are not registered yet.
except ImportError:
    print 'It seems "mediagenerator" is not used'
else:
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
