
def get_version(package_name):
    try:
        # Python >= 3.8
        from importlib.metadata import version
        return version(package_name)
    except ModuleNotFoundError:
        # Python < 3.8
        from pkg_resources import get_distribution
        distribution = get_distribution(package_name)
        return distribution.version


__version__ = get_version('creme-crm')

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
