import sys
from os import path as os_path

from django.conf import settings
from django.utils.encoding import force_str

__main__ = sys.modules.get('__main__')

_map_file_path = '_generated_media_names.py'
# __main__ is not guaranteed to have the __file__ attribute
if hasattr(__main__, '__file__'):
    _root = os_path.dirname(__main__.__file__)
    _map_file_path = os_path.join(_root, _map_file_path)

GENERATED_MEDIA_NAMES_MODULE = getattr(
    settings, 'GENERATED_MEDIA_NAMES_MODULE', '_generated_media_names'
)
GENERATED_MEDIA_NAMES_FILE = os_path.abspath(
    getattr(settings, 'GENERATED_MEDIA_NAMES_FILE', _map_file_path)
)

PRODUCTION_MEDIA_URL = getattr(
    settings, 'PRODUCTION_MEDIA_URL',
    getattr(settings, 'STATIC_URL', settings.MEDIA_URL)
)

MEDIA_GENERATORS = getattr(settings, 'MEDIA_GENERATORS', (
    'mediagenerator.generators.copyfiles.CopyFiles',
    'mediagenerator.generators.bundles.Bundles',
    'mediagenerator.generators.manifest.Manifest',
))

GLOBAL_MEDIA_DIRS = [
    os_path.normcase(os_path.normpath(force_str(path)))
    for path in getattr(
        settings, 'GLOBAL_MEDIA_DIRS', getattr(settings, 'STATICFILES_DIRS', ())
    )
]

IGNORE_APP_MEDIA_DIRS = getattr(settings, 'IGNORE_APP_MEDIA_DIRS', ('django.contrib.admin',))
