# from creme.settings import INSTALLED_CREME_APPS, INSTALLED_DJANGO_APPS
#
# SECRET_KEY = "CircleCi-Secret-Key"
#
# INSTALLED_DJANGO_APPS.extend([
#     'django_extensions',
# ])
#
# INSTALLED_CREME_APPS.extend([
#     'creme.sms',  # Work In Progress
#     'creme.cti',
#     'creme.polls',  # Need 'commercial'
#     'creme.mobile',
# ])
from pathlib import Path

from creme.settings import *  # NOQA
from creme.settings import INSTALLED_APPS

SECRET_KEY = 'CircleCi-Secret-Key'

BASE_DIR = Path(__file__).resolve().parent

# LANGUAGE_CODE = 'fr'
TIME_ZONE = 'Europe/Paris'

INSTALLED_APPS.extend([
    'django_extensions',

    'creme.sms',  # Work In Progress
    'creme.cti',
    'creme.polls',  # Need 'commercial'
    'creme.mobile',
])

GENERATED_MEDIA_NAMES_FILE = BASE_DIR / '_generated_media_names.py'
# NB: "creme_project" same name in config.yml
GENERATED_MEDIA_NAMES_MODULE = 'creme_project._generated_media_names'

MEDIA_ROOT = BASE_DIR / 'media' / 'upload'
STATIC_ROOT = BASE_DIR / 'media' / 'static'

# JOBMANAGER_BROKER = 'redis://@localhost:6379/0'

try:
    from .local_settings import *  # NOQA
except ImportError:
    pass
