import os
import sys

from django.conf import settings
from django.utils.encoding import force_text

__main__ = sys.modules.get('__main__')

_map_file_path = '_generated_media_names.py'
_media_dir = '_generated_media'
# __main__ is not guaranteed to have the __file__ attribute
if hasattr(__main__, '__file__'):
    _root = os.path.dirname(__main__.__file__)
    _map_file_path = os.path.join(_root, _map_file_path)
    _media_dir = os.path.join(_root, _media_dir)
GENERATED_MEDIA_DIR = os.path.abspath(getattr(settings, 'GENERATED_MEDIA_DIR', _media_dir))
GENERATED_MEDIA_NAMES_MODULE = getattr(settings, 'GENERATED_MEDIA_NAMES_MODULE', '_generated_media_names')
GENERATED_MEDIA_NAMES_FILE = os.path.abspath(
    getattr(settings, 'GENERATED_MEDIA_NAMES_FILE', _map_file_path))

DEV_MEDIA_URL = getattr(settings, 'DEV_MEDIA_URL',
                        getattr(settings, 'STATIC_URL', settings.MEDIA_URL))
PRODUCTION_MEDIA_URL = getattr(settings, 'PRODUCTION_MEDIA_URL', DEV_MEDIA_URL)

MEDIA_GENERATORS = getattr(settings, 'MEDIA_GENERATORS', (
    'mediagenerator.generators.copyfiles.CopyFiles',
    'mediagenerator.generators.bundles.Bundles',
    'mediagenerator.generators.manifest.Manifest',
))

_global_media_dirs = getattr(settings, 'GLOBAL_MEDIA_DIRS',
                             getattr(settings, 'STATICFILES_DIRS', ()))
GLOBAL_MEDIA_DIRS = [
    os.path.normcase(os.path.normpath(force_text(path)))
                     for path in _global_media_dirs
]

IGNORE_APP_MEDIA_DIRS = getattr(settings, 'IGNORE_APP_MEDIA_DIRS', ('django.contrib.admin',))

MEDIA_DEV_MODE = getattr(settings, 'MEDIA_DEV_MODE', settings.DEBUG)
