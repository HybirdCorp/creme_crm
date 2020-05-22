from .settings import INSTALLED_CREME_APPS

SECRET_KEY = "CircleCi-Secret-Key"

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.mysql', # 'postgresql', 'mysql', 'sqlite3' ('oracle' backend is not working with creme for now).
        'NAME':     'cremecrm',                 # Or path to database file if using sqlite3.
        'USER':     'root',                    # Not used with sqlite3.
        'PASSWORD': 'creme',                    # Not used with sqlite3.
        'HOST':     '127.0.0.1',                # Set to empty string for localhost. Not used with sqlite3.
        'PORT':     '3306',                     # Set to empty string for default. Not used with sqlite3.
        'OPTIONS':  {},                         # Extra parameters for database connection. Consult backend module's document for available keywords.
    },
}


INSTALLED_CREME_APPS.extend([
    # 'creme.sms',  # Work In Progress
    'creme.cti',
    # 'creme.activesync',  # NOT AVAILABLE ANY MORE
    'creme.polls',  # Need 'commercial'
    'creme.mobile',
])
