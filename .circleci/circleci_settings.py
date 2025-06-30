# import warnings
from pathlib import Path

# from django.utils import deprecation
from creme.settings import *  # NOQA
from creme.settings import CREME_ROOT, INSTALLED_APPS

SECRET_KEY = 'CircleCi-Secret-Key'

BASE_DIR = Path(__file__).resolve().parent

# LANGUAGE_CODE = 'fr'
TIME_ZONE = 'Europe/Paris'

SITE_DOMAIN = 'http://localhost'

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

GEOLOCATION_TOWNS = [
    (
        Path(CREME_ROOT) / 'geolocation' / 'tests' / 'data' / 'test.towns.france.csv.zip',
        {'country': 'France'}
    ),
]

# TODO? (many USE_i18N use are annoying)
# # Transform some warnings into errors
# warnings.filterwarnings(action='error', category=deprecation.RemovedInNextVersionWarning)
# warnings.filterwarnings(action='error', category=deprecation.RemovedAfterNextVersionWarning)

try:
    from .local_settings import *  # NOQA
except ImportError:
    pass
