# -*- coding: utf-8 -*-
# Django settings for creme project.

from django.utils.translation import ugettext_lazy as _

#DEBUG = True
DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

#login / password for interface of administration : admin/admin

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

#I18N / L10N ###################################################################

LANGUAGES = (
  ('en', 'English'), #_('English')
  ('fr', 'French'),  #_('French')
)

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Paris'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'fr' #Choose in the LANGUAGES values


DATE_FORMAT         = 'd-m-Y'
SHORT_DATE_FORMAT   = 'd-m-Y'
DATE_FORMAT_VERBOSE = _(u'Format : Day-Month-Year (Ex:31-12-2010)')
DATE_FORMAT_JS      = {
    'd-m-Y': 'dd-mm-yy',
}
DATE_FORMAT_JS_SEP = '-' #DATE_FORMAT_JS values separator
DATE_INPUT_FORMATS = (
    '%d-%m-%Y', '%d/%m/%Y',
    '%Y-%m-%d',  '%m/%d/%Y', '%m/%d/%y',  '%b %d %Y',
    '%b %d, %Y', '%d %b %Y', '%d %b, %Y', '%B %d %Y',
    '%B %d, %Y', '%d %B %Y', '%d %B, %Y',
)

DATETIME_FORMAT         = '%s H:i:s' % DATE_FORMAT
DATETIME_FORMAT_VERBOSE = _(u'Format : Day-Month-Year Hour:Minute:Second (Ex:31-12-2010 23:59:59)')
DATETIME_INPUT_FORMATS  = (
    '%d-%m-%Y', '%d/%m/%Y',
    '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d',
    '%m/%d/%Y %H:%M:%S', '%m/%d/%Y %H:%M', '%m/%d/%Y',
    '%m/%d/%y %H:%M:%S', '%m/%d/%y %H:%M', '%m/%d/%y',
    '%d-%m-%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S',
    '%d-%m-%Y %H:%M',    '%d/%m/%Y %H:%M',
    '%Y-%m-%dT%H:%M:%S.%fZ',#Needed for some activesync servers (/!\ %f python >=2.6)
    
)

#I18N / L10N [END]##############################################################


#SITE: URLs / PATHS / ... ######################################################

SITE_ID = 1
SITE_DOMAIN = 'http://mydomain' #No end slash!

APPEND_SLASH = False

ROOT_URLCONF = 'creme.urls'

LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/creme_login/'
LOGOUT_URL = '/creme_logout/'

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

#SITE: URLs / PATHS / ... [END]#################################################


# List of loaders that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    ('django.template.loaders.cached.Loader', ( #Don't use cached loader when developping (in your local_settings.py)
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
        #'django.template.loaders.eggs.Loader',
    )),
)

MIDDLEWARE_CLASSES = (
    'mediagenerator.middleware.MediaMiddleware', #Media middleware has to come first

    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.locale.LocaleMiddleware',

    'creme.creme_core.middleware.exceptions.Beautiful403Middleware',
    #'creme.creme_core.middleware.sql_logger.SQLLogToConsoleMiddleware',       #debuging purpose
    #'creme.creme_core.middleware.module_logger.LogImportedModulesMiddleware', #debuging purpose
)

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
    #'django.contrib.sites', #remove ??
    'django.contrib.admin',
    'django.contrib.admindocs',

    #EXTERNAL APPS
    'mediagenerator', #It manages js/css/images

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
    'creme.reports',
    'creme.products',
    'creme.recurrents',
    'creme.billing',       #need 'creme.products'
    'creme.opportunities', #need 'creme.billing'
    'creme.commercial',
    'creme.events',
    'creme.crudity',
    'creme.emails', #need 'creme.crudity'
    'creme.sms',
    'creme.projects',
    'creme.tickets',
)

from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS
TEMPLATE_CONTEXT_PROCESSORS += (
     'django.core.context_processors.request',

     'creme_core.context_processors.get_logo_url',
     'creme_core.context_processors.get_version',
     'creme_core.context_processors.get_django_version',
     'creme_core.context_processors.get_today',
     #'creme_core.context_processors.get_css_theme',
     'creme_core.context_processors.get_blocks_manager',
)

TRUE_DELETE = True

AUTHENTICATION_BACKENDS = ('creme_core.auth.backend.EntityBackend',)

ALLOWED_EXTENSIONS = [
                      'pdf', 'rtf', 'xps', 'eml',
                      'gif', 'png', 'jpeg', 'jpg', 'jpe', 'bmp', 'psd', 'tif', 'tiff', 'tga',
                      'gtar', 'gz', 'tar', 'zip', 'rar', 'ace', 'torrent', 'tgz', 'bz2',
                      '7z', 'txt', 'c', 'cpp', 'hpp', 'diz', 'csv', 'ini', 'log', 'js',
                      'xml', 'xls', 'xlsx', 'xlsm', 'xlsb', 'doc', 'docx', 'docm', 'dot',
                      'dotx', 'dotm', 'pdf', 'ai', 'ps', 'ppt', 'pptx', 'pptm', 'odg',
                      'odp', 'ods', 'odt', 'rtf', 'rm', 'ram', 'wma', 'wmv', 'swf', 'mov',
                      'm4v', 'm4a', 'mp4', '3gp', '3g2', 'qt', 'avi', 'mpeg', 'mpg', 'mp3',
                      'ogg', 'ogm',
                      ]

#EMAILS ########################################################################

# For module emailing campaign
EMAIL_SENDER        = 'sender@domain.org'#This is a creme parameter which specify from_email (sender) when sending email
EMAIL_HOST          = 'mail_server'
EMAIL_HOST_USER     = 'mail_user'
EMAIL_HOST_PASSWORD = 'mail_password'
EMAIL_USE_TLS       = True

CMP_EMAILS = 40
REMOTE_DJANGO = False

#Dev smtp serv
#=> python -m smtpd -n -c DebuggingServer localhost:1025
#Think to comment email prod settings
#EMAIL_HOST = 'localhost'
#EMAIL_PORT = 1025

DEFAULT_USER_EMAIL = ""#Email used in case the user doesn't have filled his email

#Settings used in emails-sending (campaigns)
CREME_EMAIL           = ""
CREME_EMAIL_SERVER    = ""
CREME_EMAIL_USERNAME  = ""
CREME_EMAIL_PASSWORD  = ""
CREME_EMAIL_PORT      = 25


#EMAILS [END] ###################################################################


#LOGS ##########################################################################

import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(message)s'
)

#LOGS [END]#####################################################################


#GUI ###########################################################################

#Main menu
LOGO_URL = 'images/creme_256_cropped.png' #Big image in the side menu
USE_STRUCT_MENU = True #True = use the per app menu

PAGGING_SIZE = 5 #TODO: remove
BLOCK_SIZE = 10 #Lines number in common blocks

#Show or not help messages in all the application
SHOW_HELP = True

HIDDEN_VALUE = u"??"

#GUI [END]######################################################################


#MEDIA GENERATOR SETTINGS ######################################################
#http://www.allbuttonspressed.com/projects/django-mediagenerator

MEDIA_DEV_MODE = False #DEBUG
DEV_MEDIA_URL = '/devmedia/'
PRODUCTION_MEDIA_URL = '/static_media/'

GENERATED_MEDIA_DIR = join(MEDIA_ROOT, 'static')
GLOBAL_MEDIA_DIRS = (join(dirname(__file__), 'static'),)

#TODO: create a static/css/creme-minimal.css for login/logout ??
CREME_CORE_CSS = ('main.css',
                    'creme_core/css/jquery-css/creme-theme/jquery-ui-1.7.2.custom.css',
                    'creme_core/css/fg-menu-3.0/fg.menu.css',
                    'creme_core/css/jquery.gccolor.1.0.3/gccolor.css',

                    'creme_core/css/creme.css',
                    'creme_core/css/creme-ui.css',

                    'creme_core/css/list_view.css',
                    'creme_core/css/rte.css',
                    'creme_core/css/navit.css',

                    #APPS
                    'activities/css/fullcalendar.css',
                    'activities/css/activities.css',
                    'commercial/css/commercial.css',
                 )

CREME_I18N_JS = ('l10n.js',
                    {'filter': 'mediagenerator.filters.i18n.I18N'}, #to build the i18n catalog statically.
                )

CREME_CORE_JS = ('main.js',
                    {'filter': 'mediagenerator.filters.media_url.MediaURL'}, #to get the media_url() function in JS.

                    'creme_core/js/jquery/jquery-1.3.2.js',
                    #'creme_core/js/jquery/ui/ui.core.js', #delete file ??
                    #'creme_core/js/jquery/ui/ui.draggable.js', #delete file ??
                    'creme_core/js/jquery/ui/jquery-ui-1.7.2.custom.min.js', #TODO: use a non minified version ?
                    'creme_core/js/jquery/extensions/cookie.js',
                    'creme_core/js/jquery/extensions/fg-menu-3.0/fg.menu.js',
                    'creme_core/js/jquery/extensions/fg-menu-3.0/jquery.hotkeys-0.7.8.js',
                    'activities/js/jquery/extensions/fullcalendar-1.4.5.js', #TODO: move with activities.js (beware it causes errors for now)
                    'creme_core/js/jquery/extensions/gccolor-1.0.3.js',
                    'creme_core/js/jquery/extensions/json-2.2.js',
                    'creme_core/js/jquery/extensions/highlight.js',
                    'creme_core/js/jquery/extensions/magnifier.js',
                    'creme_core/js/jquery/extensions/utils.js',
                    'creme_core/js/jquery/extensions/wait.js',

                    #'creme_core/js/datejs/date-en-US.js', #TODO improve
                    'creme_core/js/datejs/date-fr-FR.js',

                     #TODO: an other bundle only for graphael ??
                    'creme_core/js/lib/graphael/raphael-1.5.2.js',
                    'creme_core/js/lib/graphael/g.raphael.js',
                    'creme_core/js/lib/graphael/g.bar.js',
                    'creme_core/js/lib/graphael/g.line.js',
                    'creme_core/js/lib/graphael/g.pie.js',

                    'creme_core/js/lib/jquery.navIt.0.0.6.js',

                    'creme_core/js/utils.js',
                    'creme_core/js/forms.js',
                    'creme_core/js/ajax.js',
                    'creme_core/js/creme.graphael.js',
                    'creme_core/js/menu.js',

                    'creme_core/js/widgets/base.js',
                    'creme_core/js/widgets/dselect.js',
                    'creme_core/js/widgets/chainedselect.js',
                    'creme_core/js/widgets/selectorlist.js',
                    'creme_core/js/widgets/entityselector.js',
                    'creme_core/js/widgets/rte.js',

                    'creme_core/js/filters.js',
                    'creme_core/js/properties.js',
                    'creme_core/js/relations.js',
                    'creme_core/js/list_view.core.js',
                    'creme_core/js/lv_widget.js',
                    'creme_core/js/export.js',

                    #OTHER APPS (mandatory ones)
                    'activities/js/activities.js',
                    'documents/js/folders.js',
                    'media_managers/js/media_managers.js',
                    'persons/js/persons.js',
                )

CREME_OPT_JS = ( #OPTIONNAL APPS
                'billing/js/billing.js',
                'reports/js/reports.js',
                'emails/js/emails.js',
               )

MEDIA_BUNDLES = (CREME_CORE_CSS, CREME_I18N_JS, CREME_CORE_JS + CREME_OPT_JS)


ROOT_MEDIA_FILTERS = {
    'js':  'mediagenerator.filters.yuicompressor.YUICompressor',
    #'js':  'mediagenerator.filters.closure.Closure', #NB: Closure causes compilation errors...
    'css': 'mediagenerator.filters.yuicompressor.YUICompressor',
}

YUICOMPRESSOR_PATH = join(dirname(__file__), 'static', 'utils', 'yui', 'yuicompressor-2.4.2.jar')
#CLOSURE_COMPILER_PATH = join(dirname(__file__), 'closure.jar')

COPY_MEDIA_FILETYPES = ('gif', 'jpg', 'jpeg', 'png', 'ico', 'cur')

#MEDIA GENERATOR SETTINGS [END] ################################################


#APPS CONFIGURATION ############################################################

#ASSISTANTS --------------------------------------------------------------------
DEFAULT_TIME_ALERT_REMIND = 10
DEFAULT_TIME_TODO_REMIND = 120

#BILLING -----------------------------------------------------------------------
QUOTE_NUMBER_PREFIX = "DE"
INVOICE_NUMBER_PREFIX = "FA"
SALESORDER_NUMBER_PREFIX = "BC"

#SAMOUSSA ----------------------------------------------------------------------
CREME_SAMOUSSA_URL = 'http://localhost:8001/'
CREME_SAMOUSSA_USERNAME = 'compte21'
CREME_SAMOUSSA_PASSWORD = 'compte21'

#CRUDITY ------------------------------------------------------------------------
#Mail parameters to sync external email in creme
CREME_GET_EMAIL              = "" #Creme get email e.g : creme@cremecrm.org
CREME_GET_EMAIL_SERVER       = "" #Creme get server e.g : pop.cremecrm.org (only pop supported for now)
CREME_GET_EMAIL_USERNAME     = "" #user
CREME_GET_EMAIL_PASSWORD     = "" #pass
CREME_GET_EMAIL_PORT         = 110
CREME_GET_EMAIL_SSL          = False #True or False #Not used for the moment
CREME_GET_EMAIL_SSL_KEYFILE  = "" #Not used for the moment
CREME_GET_EMAIL_SSL_CERTFILE = "" #Not used for the moment
CREME_GET_EMAIL_JOB_USER_ID  = None #Only for job. Default user id which will handle the synchronization

CREME_GET_EMAIL_JOB_USER_ID  = 1#User used to synchronize mails with management command

from crudity import CREATE

PERSONS_CONTACT_FROM_EMAIL = {
    CREATE: {
        "password"   : u"",  #Password to be authorized in backend
        "limit_froms": (),   #If recipient email's address not in this drop email, let empty to allow all email addresses
        "in_sandbox" : True, #True : Show in sandbox & history, False show only in history (/!\ creation will be automatic if False)
        "body_map"   : {     #Allowed keys format : "key": "default value"
        },
        "subject": u""       #Target subject, nb: in the subject all spaces will be deleted, and it'll be converted to uppercase
    }
}

EMAILS_ENTITYEMAIL_FROM_EMAIL = {
    CREATE: {
        "limit_froms": (),   #If recipient email's address not in this drop email, let empty to allow all email addresses
        "in_sandbox" : True, #True : Show in sandbox & history, False show only in history (/!\ creation will be automatic if False)
    }
}

#ACTIVESYNC ------------------------------------------------------------------------
#TODO: Rename and transform this into an AS-Version verification => A2:Body doesn't seems to work with AS version > 2.5
IS_ZPUSH = True

CONFLICT_MODE = 1 #0 Client object replaces server object. / 1 Server object replaces client object.

ACTIVE_SYNC_DEBUG = DEBUG #Make appears some debug informations on the UI

LIMIT_SYNC_KEY_HISTORY = 50 #Number of sync_keys kept in db by user

CONNECTION_TIMEOUT = 150

PICTURE_LIMIT_SIZE = 55000 #E.g: 55Ko Active sync servers don't handle pictures > to this size


#APPS CONFIGURATION [END]#######################################################


try:
    from local_settings import *
except ImportError:
    pass
