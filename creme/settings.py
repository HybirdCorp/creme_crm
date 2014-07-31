# -*- coding: utf-8 -*-
# Django settings for creme project.

from django.utils.translation import ugettext_lazy as _

#DEBUG = True
DEBUG = False
TEMPLATE_DEBUG = DEBUG
JAVASCRIPT_DEBUG = DEBUG

FORCE_JS_TESTVIEW = False

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

#login / password for interface of administration : admin/admin

from os.path import dirname, join, abspath, exists
CREME_ROOT = dirname(abspath(__file__))

MANAGERS = ADMINS

# NB: it's recommended to use a database engine that supports transactions.
#'OPTIONS': {'init_command': 'SET storage_engine=INNODB'}#Example to use a transaction engine in mysql
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.mysql', # 'postgresql_psycopg2', 'mysql', 'sqlite3' ('oracle' backend is not working with creme for now).
        'NAME':     'cremecrm',                 # Or path to database file if using sqlite3.
        'USER':     'creme',                    # Not used with sqlite3.
        'PASSWORD': 'creme',                    # Not used with sqlite3.
        'HOST':     '',                         # Set to empty string for localhost. Not used with sqlite3.
        'PORT':     '',                         # Set to empty string for default. Not used with sqlite3.
        'OPTIONS':  {},                         # Extra parameters for database connection. Consult backend module's document for available keywords.
    },
}

#I18N / L10N ###################################################################

USE_TZ = True

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

DEFAULT_ENCODING = 'UTF8'


DATE_FORMAT         = 'd-m-Y'
SHORT_DATE_FORMAT   = 'd-m-Y'
DATE_FORMAT_VERBOSE = _(u'Format: Day-Month-Year (Ex:31-12-2013)')
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
DATETIME_FORMAT_VERBOSE = _(u'Format: Day-Month-Year Hour:Minute:Second (Ex:31-12-2013 23:59:59)')
DATETIME_INPUT_FORMATS  = (
    '%d-%m-%Y', '%d/%m/%Y',
    '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d',
    '%m/%d/%Y %H:%M:%S', '%m/%d/%Y %H:%M', '%m/%d/%Y',
    '%m/%d/%y %H:%M:%S', '%m/%d/%y %H:%M', '%m/%d/%y',
    '%d-%m-%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S',
    '%d-%m-%Y %H:%M',    '%d/%m/%Y %H:%M',
    '%Y-%m-%dT%H:%M:%S.%fZ',#Needed for some activesync servers (/!\ %f python >=2.6)
    "%Y-%m-%dT%H:%M:%S",#Needed for infopath
)

#I18N / L10N [END]##############################################################


#SITE: URLs / PATHS / ... ######################################################

SITE_ID = 1
SITE_DOMAIN = 'http://mydomain' #No end slash!

APPEND_SLASH = False

ROOT_URLCONF = 'creme.urls' # means urls.py

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

## URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
## trailing slash.
## Examples: "http://foo.com/media/", "/media/".
#ADMIN_MEDIA_PREFIX = '/media/'
#TODO STATIC_URL ??

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
    'creme.creme_core.middleware.exceptions.Ajax500Middleware', #it must be last middleware that catch all exceptions 
    'creme.creme_core.middleware.exceptions.Ajax404Middleware',
    'creme.creme_core.middleware.exceptions.Beautiful403Middleware',
    'creme.creme_core.middleware.exceptions.Beautiful409Middleware',

    'mediagenerator.middleware.MediaMiddleware', #Media middleware has to come first

    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.locale.LocaleMiddleware',

    'creme.creme_core.middleware.global_info.GlobalInfoMiddleware', #after AuthenticationMiddleware
    'creme.creme_core.middleware.timezone.TimezoneMiddleware',

    #'creme.creme_core.middleware.module_logger.LogImportedModulesMiddleware', #debuging purpose
)

TEMPLATE_DIRS = (
    join(CREME_ROOT, "templates"),
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_DJANGO_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    #'django.contrib.sites', #remove ??
    #'django.contrib.admin',
    #'django.contrib.admindocs',

    #EXTERNAL APPS
    'mediagenerator', #It manages js/css/images
    'south',          #It manages DB migrations
)

INSTALLED_CREME_APPS = (
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
    'creme.billing',       #need 'products'
    'creme.opportunities', #need 'products'
    'creme.commercial',    #need 'opportunities'
    'creme.events',        #need 'opportunities'
    'creme.crudity',
    'creme.emails', #need 'crudity'
    #creme.'sms', #Work In Progress
    'creme.projects',
    'creme.tickets',
    #'creme.cti',
    'creme.activesync',
    'creme.vcfs',
    #'creme.polls',  #need 'commercial'
)


from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS
TEMPLATE_CONTEXT_PROCESSORS += (
     'django.core.context_processors.request',

     'creme.creme_core.context_processors.get_logo_url',
     'creme.creme_core.context_processors.get_version',
     'creme.creme_core.context_processors.get_django_version',
     'creme.creme_core.context_processors.get_today',
     'creme.creme_core.context_processors.get_css_theme',
     'creme.creme_core.context_processors.get_blocks_manager',
)

#TRUE_DELETE = True

AUTHENTICATION_BACKENDS = ('creme.creme_core.auth.backend.EntityBackend',)

ALLOWED_IMAGES_EXTENSIONS = (
    'gif', 'png', 'jpeg', 'jpg', 'jpe', 'bmp', 'psd', 'tif', 'tiff', 'tga', 'svg',
)
ALLOWED_EXTENSIONS = (
                      'pdf', 'rtf', 'xps', 'eml',
                      'psd',
                      'gtar', 'gz', 'tar', 'zip', 'rar', 'ace', 'torrent', 'tgz', 'bz2',
                      '7z', 'txt', 'c', 'cpp', 'hpp', 'diz', 'csv', 'ini', 'log', 'js',
                      'xml', 'xls', 'xlsx', 'xlsm', 'xlsb', 'doc', 'docx', 'docm', 'dot',
                      'dotx', 'dotm', 'pdf', 'ai', 'ps', 'ppt', 'pptx', 'pptm', 'odg',
                      'odp', 'ods', 'odt', 'rtf', 'rm', 'ram', 'wma', 'wmv', 'swf', 'mov',
                      'm4v', 'm4a', 'mp4', '3gp', '3g2', 'qt', 'avi', 'mpeg', 'mpg', 'mp3',
                      'ogg', 'ogm',
                      ) + ALLOWED_IMAGES_EXTENSIONS

IMPORT_BACKENDS = (
                   'creme.creme_core.backends.csv_import.CSVImportBackend',
                   'creme.creme_core.backends.xls_import.XLSImportBackend',  # You need to install xlwt and xlrd
                   'creme.creme_core.backends.xls_import.XLSXImportBackend',  # You need to install xlwt and xlrd
)
EXPORT_BACKENDS = (
                   'creme.creme_core.backends.csv_export.CSVExportBackend',
                   'creme.creme_core.backends.csv_export.SemiCSVExportBackend',
                   'creme.creme_core.backends.xls_export.XLSExportBackend',  # You need to install xlwt and xlrd
)

#EMAILS [internal] #############################################################

# Emails sent to the users of Crem (reminders, assistants.user_message, commercial.commercial_approach...)
EMAIL_SENDER        = 'sender@domain.org' #This is a creme parameter which specify from_email (sender) when sending email
EMAIL_HOST          = 'localhost'
EMAIL_HOST_USER     = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS       = False

#Dev smtp serv
#=> python -m smtpd -n -c DebuggingServer localhost:1025
#Think to comment email prod settings
#EMAIL_HOST = 'localhost'
#EMAIL_PORT = 1025

DEFAULT_USER_EMAIL = '' #Email used in case the user doesn't have filled his email


#EMAILS [END] ###################################################################

#LOGS ##########################################################################

#LOGS ##########################################################################

LOGGING_FORMATTERS = {
    'verbose': {
        '()': 'creme.utils.loggers.CremeFormatter',
        'format': '%(asctime)s %(levelname)-7s [%(modulepath)s:%(lineno)d] - %(name)s : %(message)s',
    },
    'simple': {
        '()': 'creme.utils.loggers.CremeFormatter',
        'format': '%(asctime)s [%(colored_levelname)s] - %(name)s : %(message)s',
        'datefmt': '%Y-%m-%d %H:%M:%S',
    },
}

# This filter remove all logs containing '/static_media/' string (usefull when log level is DEBUG)
# LOGGING_FILTERS = {
#     'media': {
#         '()':      'creme.utils.loggers.RegexFilter',
#         'pattern': '.*(\/static_media\/).*',
#         'exclude': True,
#     }
# }
LOGGING_FILTERS = {}

LOGGING_CONSOLE_HANDLER = {
    'level': 'WARNING', # Available levels : DEBUG < INFO < WARNING < ERROR < CRITICAL
    'class': 'logging.StreamHandler',
    'formatter': 'simple',
}

# In order to enable logging into a file use the following configuration
# LOGGING_PATH = '~/creme.log' # create a log file in user home directory
#
# LOGGING_FILE_HANDLER = { # compress log file each day in order to save some space
#     'level': 'INFO',
#     '()': 'creme.utils.loggers.CompressedTimedRotatingFileHandler',
#     'formatter': 'verbose',
#     'filename': LOGGING_PATH,
#     'interval': 1,
#     'when': 'D'
# }
LOGGING_FILE_HANDLER = {
    'class': 'logging.NullHandler',
}

LOGGING_DEFAULT_LOGGER = {
    'handlers': ['console', 'file'],
    'level': 'WARNING', # Available levels : DEBUG < INFO < WARNING < ERROR < CRITICAL
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': LOGGING_FORMATTERS,
    'filters': LOGGING_FILTERS,
    'handlers': {
        'console': LOGGING_CONSOLE_HANDLER,
        'file':    LOGGING_FILE_HANDLER,
    },
    'loggers': {
        '': LOGGING_DEFAULT_LOGGER  # the empty key '' means that all logs are redirected to this logger. 
    },
}

import warnings

# Warnings behavior choices (see Python doc):
# "error" "ignore" "always" "default" "module" "once"
warnings.simplefilter("once")

#LOGS [END]#####################################################################

#GUI ###########################################################################

#Main menu
LOGO_URL = 'images/creme_256_cropped.png' #Big image in the side menu
USE_STRUCT_MENU = True #True = use the per app menu

BLOCK_SIZE = 10 #Lines number in common blocks
MAX_LAST_ITEMS = 9 #Max number of items in the 'Last viewed items' bar

#Show or not help messages in all the application
SHOW_HELP = True

HIDDEN_VALUE = u"??"

#GUI [END]######################################################################


#MEDIA GENERATOR SETTINGS ######################################################
#http://www.allbuttonspressed.com/projects/django-mediagenerator

MEDIA_DEV_MODE = False #DEBUG
DEV_MEDIA_URL = '/devmedia/'
PRODUCTION_MEDIA_URL = '/static_media/'

#GENERATED_MEDIA_NAMES_MODULE = 'creme._generated_media_names'
GENERATED_MEDIA_DIR = join(MEDIA_ROOT, 'static')
GLOBAL_MEDIA_DIRS = (join(dirname(__file__), 'static'),)

#Available themes. A theme is represented by (theme_dir, theme verbose name)
THEMES = [('icecream',  _('Ice cream')),
          ('chantilly', _('Chantilly')),
         ]
DEFAULT_THEME = 'icecream' #'chantilly'

CSS_DEFAULT_LISTVIEW = 'left_align'
CSS_NUMBER_LISTVIEW = 'right_align'
CSS_TEXTAREA_LISTVIEW = 'text_area'
CSS_DEFAULT_HEADER_LISTVIEW = 'hd_cl_lv'
CSS_DATE_HEADER_LISTVIEW = 'hd_date_cl_lv'

#TODO: create a static/css/creme-minimal.css for login/logout ??
CREME_CORE_CSS = ('main.css',
                    'creme_core/css/jquery-css/creme-theme/jquery-ui-1.8.15.custom.css',
                    'creme_core/css/fg-menu-3.0/fg.menu.css',
                    'creme_core/css/jqplot-1.0.4/jquery.jqplot.css',
                    'creme_core/css/jquery.gccolor.1.0.3/gccolor.css',
                    'creme_core/css/chosen/chosen.css',

                    'creme_core/css/creme.css',
                    'creme_core/css/creme-ui.css',

                    'creme_core/css/blocks.css',
                    'creme_core/css/home.css',
                    'creme_core/css/my_page.css',
                    'creme_core/css/search_results.css',
                    'creme_core/css/portal.css',
                    'creme_core/css/list_view.css',
                    'creme_core/css/detail_view.css',
                    'creme_core/css/navit.css',
                    'creme_core/css/forms.css',

                    #APPS
                    'creme_config/css/creme_config.css',
                    'activities/css/fullcalendar.css',
                    'activities/css/activities.css',
                    'persons/css/persons.css',
                 )

CREME_OPT_CSS = ( #OPTIONNAL APPS
                 ('creme.billing',    'billing/css/billing.css'),
                 ('creme.commercial', 'commercial/css/commercial.css'),
                 ('creme.crudity',    'crudity/css/crudity.css'),
                )

CREME_I18N_JS = ('l10n.js',
                    {'filter': 'mediagenerator.filters.i18n.I18N'}, #to build the i18n catalog statically.
                )

CREME_CORE_JS = ('main.js',
                    {'filter': 'mediagenerator.filters.media_url.MediaURL'}, #to get the media_url() function in JS.
                    'creme_core/js/media.js',
                    'creme_core/js/jquery/jquery-1.6.2.js',
                    'creme_core/js/jquery/ui/jquery-ui-1.8.15.custom.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.4/excanvas.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.4/jquery.jqplot.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.4/plugins/jqplot.enhancedLegendRenderer.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.4/plugins/jqplot.canvasTextRenderer.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.4/plugins/jqplot.categoryAxisRenderer.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.4/plugins/jqplot.canvasTextRenderer.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.4/plugins/jqplot.canvasAxisLabelRenderer.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.4/plugins/jqplot.canvasAxisTickRenderer.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.4/plugins/jqplot.pieRenderer.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.4/plugins/jqplot.donutRenderer.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.4/plugins/jqplot.barRenderer.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.4/plugins/jqplot.pointLabels.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.4/plugins/jqplot.highlighter.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.4/plugins/jqplot.cursor.js',
                    'creme_core/js/jquery/extensions/jquery.uuid-2.0.js',
                    'creme_core/js/jquery/extensions/cookie.js',
                    'creme_core/js/jquery/extensions/fg-menu-3.0/fg.menu.js',
                    'creme_core/js/jquery/extensions/fg-menu-3.0/jquery.hotkeys-0.8.js',
                    'activities/js/jquery/extensions/fullcalendar-1.4.7.js', #TODO: move with activities.js (beware it causes errors for now)
                    'creme_core/js/jquery/extensions/gccolor-1.0.3.js',
                    'creme_core/js/jquery/extensions/json-2.2.js',
                    'creme_core/js/jquery/extensions/highlight.js',
                    'creme_core/js/jquery/extensions/magnifier.js',
                    'creme_core/js/jquery/extensions/utils.js',
                    'creme_core/js/jquery/extensions/wait.js',
                    'creme_core/js/jquery/extensions/jquery.dragtable.js',
                    'creme_core/js/jquery/extensions/jquery.form.js',
                    'creme_core/js/jquery/extensions/jquery.tinymce.js',
                    'creme_core/js/jquery/extensions/jquery.debounce.js',
                    'creme_core/js/jquery/extensions/chosen.jquery.js',

                    'creme_core/js/lib/fallbacks/object-0.1.js',
                    'creme_core/js/lib/fallbacks/array-0.9.js',
                    'creme_core/js/lib/fallbacks/string-0.1.js',
                    'creme_core/js/lib/fallbacks/console.js',
                    'creme_core/js/lib/fallbacks/event-0.1.js',
                    'creme_core/js/lib/fallbacks/htmldocument-0.1.js',
                    'creme_core/js/lib/generators-0.1.js',

                    #'creme_core/js/datejs/date-en-US.js', #TODO improve
                    'creme_core/js/datejs/date-fr-FR.js',

                    'creme_core/js/lib/jquery.navIt.0.0.6.js',

                    'creme_core/js/creme.js',
                    'creme_core/js/color.js',
                    'creme_core/js/utils.js',
                    'creme_core/js/forms.js',
                    'creme_core/js/ajax.js',
                    'creme_core/js/menu.js',
                    'creme_core/js/blocks.js',

                    'creme_core/js/widgets/base.js',

                    'creme_core/js/widgets/component/component.js',
                    'creme_core/js/widgets/component/events.js',
                    'creme_core/js/widgets/component/action.js',
                    'creme_core/js/widgets/component/chosen.js',

                    'creme_core/js/widgets/utils/template.js',
                    'creme_core/js/widgets/utils/lambda.js',
                    'creme_core/js/widgets/utils/converter.js',
                    'creme_core/js/widgets/utils/json.js',
                    'creme_core/js/widgets/utils/compare.js',

                    'creme_core/js/widgets/ajax/backend.js',
                    'creme_core/js/widgets/ajax/mockbackend.js',
                    'creme_core/js/widgets/ajax/cachebackend.js',
                    'creme_core/js/widgets/ajax/query.js',

                    'creme_core/js/widgets/layout/layout.js',
                    'creme_core/js/widgets/layout/sortlayout.js',
                    'creme_core/js/widgets/layout/columnlayout.js',
                    'creme_core/js/widgets/layout/autosize.js',

                    'creme_core/js/widgets/model/collection.js',
                    'creme_core/js/widgets/model/array.js',
                    'creme_core/js/widgets/model/renderer.js',
                    'creme_core/js/widgets/model/query.js',
                    'creme_core/js/widgets/model/controller.js',
                    'creme_core/js/widgets/model/choice.js',

                    'creme_core/js/widgets/dialog/dialog.js',
                    'creme_core/js/widgets/dialog/overlay.js',
                    'creme_core/js/widgets/dialog/frame.js',
                    'creme_core/js/widgets/dialog/confirm.js',
                    'creme_core/js/widgets/dialog/form.js',
                    'creme_core/js/widgets/dialog/select.js',

                    'creme_core/js/widgets/frame.js',
                    'creme_core/js/widgets/toggle.js',
                    'creme_core/js/widgets/pluginlauncher.js',
                    'creme_core/js/widgets/dinput.js',
                    'creme_core/js/widgets/dselect.js',
                    'creme_core/js/widgets/checklistselect.js',
                    'creme_core/js/widgets/datetime.js',
                    'creme_core/js/widgets/daterange.js',
                    'creme_core/js/widgets/daterangeselector.js',
                    'creme_core/js/widgets/chainedselect.js',
                    'creme_core/js/widgets/selectorlist.js',
                    'creme_core/js/widgets/entityselector.js',
                    'creme_core/js/widgets/pselect.js',
                    'creme_core/js/widgets/adaptivewidget.js',
                    'creme_core/js/widgets/actionlist.js',
                    'creme_core/js/widgets/plotdata.js',
                    'creme_core/js/widgets/plot.js',
                    'creme_core/js/widgets/plotselector.js',
                    'creme_core/js/widgets/scrollactivator.js',
                    'creme_core/js/widgets/container.js',

                    'creme_core/js/list_view.core.js',
                    'creme_core/js/lv_widget.js',
                    'creme_core/js/entity_cell.js',
                    'creme_core/js/export.js',
                    'creme_core/js/merge.js',
                    'creme_core/js/relations.js',

                    #OTHER APPS (mandatory ones)
                    'assistants/js/assistants.js',
                    'activities/js/activities.js',
                    #'media_managers/js/media_managers.js',
                    'persons/js/persons.js',
                )

CREME_OPT_JS = ( #OPTIONNAL APPS
                ('creme.billing',    'billing/js/billing.js'),
                ('creme.reports',    'reports/js/reports.js'),
                ('creme.emails',     'emails/js/emails.js'),
                ('creme.cti',        'cti/js/cti.js'),
                ('creme.commercial', 'commercial/js/commercial.js')
               )

TEST_CREME_CORE_JS = (#js Unit test files
    'test_core.js',
    'creme_core/js/tests/qunit/qunit-1.6.0.js',
    'creme_core/js/tests/component/component.js',
    'creme_core/js/tests/component/events.js',
    'creme_core/js/tests/component/action.js',
    'creme_core/js/tests/utils/template.js',
    'creme_core/js/tests/utils/lambda.js',
    'creme_core/js/tests/utils/converter.js',
    'creme_core/js/tests/utils/utils.js',
    'creme_core/js/tests/ajax/mockajax.js',
    'creme_core/js/tests/ajax/cacheajax.js',
    'creme_core/js/tests/ajax/query.js',
    'creme_core/js/tests/ajax/localize.js',
    'creme_core/js/tests/model/collection.js',
    'creme_core/js/tests/model/renderer.js',
    'creme_core/js/tests/model/query.js',
    'creme_core/js/tests/model/controller.js',
    'creme_core/js/tests/dialog/dialog.js',
    'creme_core/js/tests/utils.js',
    'creme_core/js/tests/fallbacks.js',
    'creme_core/js/tests/generators.js',
    'creme_core/js/tests/widgets/base.js',
    'creme_core/js/tests/widgets/widget.js',
    'creme_core/js/tests/widgets/plot.js',
    'creme_core/js/tests/widgets/frame.js',
    'creme_core/js/tests/widgets/toggle.js',
    'creme_core/js/tests/widgets/dselect.js',
    'creme_core/js/tests/widgets/dinput.js',
    'creme_core/js/tests/widgets/pselect.js',
    'creme_core/js/tests/widgets/entityselector.js',
    'creme_core/js/tests/widgets/chainedselect.js',
    'creme_core/js/tests/widgets/checklistselect.js',
    'creme_core/js/tests/widgets/selectorlist.js',
    'creme_core/js/tests/widgets/actionlist.js',
    'creme_core/js/tests/widgets/plotselector.js',
    'creme_core/js/tests/widgets/container.js',
)

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

#EMAILS [external] -------------------------------------------------------------
#Emails campaigns sent to the customers
EMAILCAMPAIGN_HOST      = 'localhost'
EMAILCAMPAIGN_HOST_USER = ''
EMAILCAMPAIGN_PASSWORD  = ''
EMAILCAMPAIGN_PORT      = 25
EMAILCAMPAIGN_USE_TLS   = True

#Emails are sent by chunks, and sleep between 2 chunks.
EMAILCAMPAIGN_SIZE = 40
EMAILCAMPAIGN_SLEEP_TIME = 2

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

CREME_GET_EMAIL_JOB_USER_ID  = 1 #Only for job. Default user id which will handle the synchronization
                                 #User used to synchronize mails with management command

#CRUDITY_BACKENDS configurates the backends (it's a list of dict)
#Here a template of a crudity backend configuration:
#CRUDITY_BACKENDS = [
#    {
#        "fetcher": "email",                #The name of the fetcher (which is registered with). Available choices: 'email'
#        "input": "infopath",               #The name of the input (which is registered with). Available choices: 'raw', 'infopath' (that needs "lcab" program)
#        "method": "create",                #The method of the input to call. Available choices: 'create'
#        "model": "activities.activity",    #The targeted model
#        "password": "meeting",             #Password to be authorized in the input
#        "limit_froms": (),                 #A white list of sender (Example with an email:
#                                           # If a recipient email's address not in this drop email, let empty to allow all email addresses)
#        "in_sandbox": True,                #True : Show in sandbox & history, False show only in history (/!\ creation will be automatic if False)
#        "body_map"   : {                   #Allowed keys format : "key": "default value".
#            "title": "",                   # Keys have to be real field names of the model
#            "user_id": 1,
#        },
#        "subject": u"CREATEACTIVITYIP"     #Target subject, nb: in the subject all spaces will be deleted, and it'll be converted to uppercase.
#                                           #You can specify * as a fallback (no previous backend handle the data returned by the fetcher,
#                                           # but be careful you're backend has to have the method:'fetcher_fallback').
#    },
#]
CRUDITY_BACKENDS = [
    {
        "fetcher": "email",
        "input": "raw",
        "method": "create",
        "model": "emails.entityemail",
        "password": "",
        "limit_froms": (),
        "in_sandbox": True,
        "body_map": {},
        "subject": u"*",
    },
]

#ACTIVESYNC ------------------------------------------------------------------------
#TODO: Rename and transform this into an AS-Version verification => A2:Body doesn't seems to work with AS version > 2.5
IS_ZPUSH = True

CONFLICT_MODE = 1 #0 Client object replaces server object. / 1 Server object replaces client object.

ACTIVE_SYNC_DEBUG = DEBUG #Make appears some debug informations on the UI

LIMIT_SYNC_KEY_HISTORY = 50 #Number of sync_keys kept in db by user

CONNECTION_TIMEOUT = 150

PICTURE_LIMIT_SIZE = 55000 #E.g: 55Ko Active sync servers don't handle pictures > to this size

#CTI ---------------------------------------------------------------------------
ABCTI_URL = 'http://127.0.0.1:8087'

#VCF ---------------------------------------------------------------------------
VCF_IMAGE_MAX_SIZE = 3145728 #Limit size (byte) of remote photo files (i.e : when the photo in the vcf file is just a url)

#APPS CONFIGURATION [END]#######################################################

try:
    from local_settings import *
except ImportError:
    pass

#GENERAL [FINAL SETTINGS]-------------------------------------------------------

#LOCALE_PATHS = [join(CREME_ROOT, "locale")] + [join(CREME_ROOT, app, "locale") for app in INSTALLED_CREME_APPS]
_LOCALE_OVERLOAD = join(CREME_ROOT, 'locale_overload', 'locale')

LOCALE_PATHS = [join(CREME_ROOT, "locale")]
if exists(_LOCALE_OVERLOAD):
    LOCALE_PATHS.append(_LOCALE_OVERLOAD)
#LOCALE_PATHS.extend(join(CREME_ROOT, app, "locale") for app in INSTALLED_CREME_APPS)
LOCALE_PATHS.extend(join(CREME_ROOT, app.rsplit('.')[-1], "locale") for app in INSTALLED_CREME_APPS)

INSTALLED_APPS = INSTALLED_DJANGO_APPS + INSTALLED_CREME_APPS


#MEDIA GENERATOR [FINAL SETTINGS]-----------------------------------------------
MEDIA_BUNDLES = (
                 CREME_I18N_JS,
                 CREME_CORE_JS + tuple(js for app, js in CREME_OPT_JS if app in INSTALLED_CREME_APPS)
                )
if FORCE_JS_TESTVIEW:
    MEDIA_BUNDLES += (TEST_CREME_CORE_JS,)

CREME_CSS = CREME_CORE_CSS + tuple(css for app, css in CREME_OPT_CSS if app in INSTALLED_CREME_APPS)
MEDIA_BUNDLES += tuple((theme_dir + CREME_CSS[0], ) + tuple(theme_dir + '/' + css_file if not isinstance(css_file, dict) else css_file for css_file in CREME_CSS[1:])
                        for theme_dir, theme_vb_name in THEMES
                       )

