# -*- coding: utf-8 -*-

__version__ = '2.3.7'

# App registry hooking ---------------------------------------------------------

try:
    from django.apps.config import AppConfig
    from django.apps.registry import Apps
except ImportError:
    # This error may appear with old versions of setuptools during installation
    import sys

    sys.stderr.write(
        'Django is not installed ; '
        'ignore this message if you are installing Creme.'
    )
else:
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
