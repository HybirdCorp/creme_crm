import os

from creme.settings import *

DEBUG = bool(int(os.getenv('CREME_DEBUG')))

SECRET_KEY = os.getenv('CREME_SECRET_KEY')

DATABASES = {
    'default': {
        # Possible backends: 'postgresql', 'mysql', 'sqlite3'.
        # NB: 'oracle' backend is not working with creme for now.
        'ENGINE':   os.getenv('CREME_DATABASE_ENGINE'),

        # Name of the database, or path to the database file if using 'sqlite3'.
        'NAME': os.getenv('CREME_DATABASE_NAME'),

        # Not used with sqlite3.
        'USER': os.getenv('CREME_DATABASE_USER', default=''),

        # Not used with sqlite3.
        'PASSWORD': os.getenv('CREME_DATABASE_PASSWORD', default=''),

        # Set to empty string for localhost. Not used with 'sqlite3'.
        'HOST': os.getenv('CREME_DATABASE_HOST', default=''),

        # Set to empty string for default. Not used with 'sqlite3'.
        'PORT': os.getenv('CREME_DATABASE_PORT', default=''),

        # Extra parameters for database connection.
        # Consult backend module's document for available keywords.
        'OPTIONS':  {},
    },
}

TIME_ZONE = os.getenv('CREME_TIME_ZONE')
LANGUAGE_CODE = os.getenv('CREME_LANGUAGE_CODE')

# Static files (css, js bundles...)
GENERATED_MEDIA_NAMES_FILE = "/home/creme/_generated_media_names.py"
GENERATED_MEDIA_DIR = "/home/creme/statics"
PRODUCTION_MEDIA_URL = '/static_media/'

# User uploaded files
MEDIA_ROOT = os.getenv('CREME_MEDIA_ROOT')

# Task queue broker dsn
JOBMANAGER_BROKER = os.getenv('CREME_JOBMANAGER_BROKER')
