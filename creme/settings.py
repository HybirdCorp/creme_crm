# Django settings for creme project.

DEBUG = True
#DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

#login / password pour l'interface admin : admin/admin

from os.path import dirname, join, abspath
CREME_ROOT = dirname(abspath(__file__))

MANAGERS = ADMINS

# NB: it's recommended to use a database engine that supports transactions.
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.mysql', # 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME':     'cremecrm',                 # Or path to database file if using sqlite3.
        'USER':     'creme',                    # Not used with sqlite3.
        'PASSWORD': 'creme',                    # Not used with sqlite3.
        'HOST':     '',                         # Set to empty string for localhost. Not used with sqlite3.
        'PORT':     '',                         # Set to empty string for default. Not used with sqlite3.
        'OPTIONS':  {},                         # Extra parameters for database connection. Consult backend module's document for available keywords.
    },
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Paris'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'fr-FR'

#LANGUAGES = (
  #('en', 'English'), #_('English')
  #('fr', 'French'),  #_('French')
#)

SITE_ID = 1
SITE_DOMAIN = 'http://mydomain' #No end slash!

APPEND_SLASH = False
# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# For module emailing campaign
EMAIL_HOST = 'mail_server'
EMAIL_HOST_USER = 'mail_user'
EMAIL_HOST_PASSWORD = 'mail_password'

EMAIL_USE_TLS = True
CMP_EMAILS = 40 
REMOTE_DJANGO = False

#Dev smtp serv
#=> python -m smtpd -n -c DebuggingServer localhost:1025
#Think to comment email prod settings
#EMAIL_HOST = 'localhost'
#EMAIL_PORT = 1025

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = join(CREME_ROOT, "media")

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = 'http://127.0.0.1:8000/site_media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '1&7rbnl7u#+j-2#@5=7@Z0^9v@y_Q!*y^krWS)r)39^M)9(+6('

# List of loaders that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    ('django.template.loaders.cached.Loader', (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
        #'django.template.loaders.eggs.Loader',
    )),
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',

    #'creme.creme_core.middleware.sql_logger.SQLLogToConsoleMiddleware',
    #'creme.creme_core.middleware.module_logger.LogImportedModulesMiddleware',
)

ROOT_URLCONF = 'creme.urls'


#Principal template directory, note the tail slash
MANDATORY_TEMPLATE = join(CREME_ROOT, "templates")

TEMPLATE_DIRS = (
    join(CREME_ROOT, "templates"),
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django_extensions',

    #CREME CORE APPS
    'creme.creme_core',
    'creme.creme_config',
    'creme.media_managers',
    'creme.documents',
    'creme.assistants',
    'creme.activities',
    'creme.persons',

    #CREME OPTIONNAL APPS (can be safely commented)
    'creme.graphs',
    'creme.products',
    'creme.recurrents',
    'creme.billing',       #need 'creme.products'
    'creme.opportunities', #need 'creme.billing'
    'creme.commercial',
    'creme.emails',
    'creme.sms',
    'creme.projects',
    'creme.tickets',
    'creme.reports',
)


#LOGO_URL = '/site_media/images/creme_256.png'
LOGO_URL = '/site_media/images/creme_256_cropped.png'
#LOGO_URL = '/site_media/images/logos/hybird.png'

from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS
TEMPLATE_CONTEXT_PROCESSORS += (
     'django.core.context_processors.request',

     'creme_core.context_processors.get_logo_url',
     'creme_core.context_processors.get_today',
     'creme_core.context_processors.get_css_theme',
     'creme_core.context_processors.get_blocks_manager',
)


LOGIN_REDIRECT_URL = '/'

LOGIN_URL = '/creme_login/'

LOGOUT_URL = '/creme_logout/'

TRUE_DELETE = True

CREME_EMAIL = "to"

AUTH_PROFILE_MODULE = "creme_core.cremeprofile"

#TODO: remove
PAGGING_SIZE = 5

BLOCK_SIZE = 10 #lines number in common blocks


import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(message)s'
)

DATE_FORMAT = 'j-m-Y'

ALLOWED_EXTENSIONS = [
                      'pdf', 'rtf', 'xps', 'eml'
                      'gif', 'png', 'jpeg', 'jpg', 'jpe', 'bmp', 'psd', 'tif', 'tiff', 'tga',
                      'gtar', 'gz', 'tar', 'zip', 'rar', 'ace', 'torrent', 'tgz', 'bz2',
                      '7z', 'txt', 'c', 'cpp', 'hpp', 'diz', 'csv', 'ini', 'log', 'js',
                      'xml', 'xls', 'xlsx', 'xlsm', 'xlsb', 'doc', 'docx', 'docm', 'dot',
                      'dotx', 'dotm', 'pdf', 'ai', 'ps', 'ppt', 'pptx', 'pptm', 'odg',
                      'odp', 'ods', 'odt', 'rtf', 'rm', 'ram', 'wma', 'wmv', 'swf', 'mov',
                      'm4v', 'm4a', 'mp4', '3gp', '3g2', 'qt', 'avi', 'mpeg', 'mpg', 'mp3',
                      'ogg', 'ogm'
                      ]



USE_STRUCT_MENU = True

DEFAULT_TIME_ALERT_REMIND = 10
DEFAULT_TIME_TODO_REMIND = 120

#Show or not help messages in all the application
SHOW_HELP = True

try:
    from local_settings import *
except ImportError:
    pass
