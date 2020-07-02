from .settings import INSTALLED_CREME_APPS, INSTALLED_DJANGO_APPS

SECRET_KEY = "CircleCi-Secret-Key"

INSTALLED_DJANGO_APPS.extend([
    'django_extensions',
])

INSTALLED_CREME_APPS.extend([
    # 'creme.sms',  # Work In Progress
    'creme.cti',
    'creme.polls',  # Need 'commercial'
    'creme.mobile',
])
