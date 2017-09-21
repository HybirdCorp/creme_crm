# -*- coding: utf-8 -*-
# Django settings for creme project.

from sys import argv

from django.utils.translation import ugettext_lazy as _

DEBUG = False
JAVASCRIPT_DEBUG = DEBUG

TESTS_ON = len(argv) > 1 and argv[1] == 'test'
FORCE_JS_TESTVIEW = False

# Commands which do not need to perform SQL queries (so the apps do not need to be totally initialized)
NO_SQL_COMMANDS = ('help', 'version', '--help', '--version', '-h',
                   'compilemessages', 'makemessages',
                   'startapp', 'startproject',
                   'migrate',
                   'generatemedia',
                   'build_secret_key',
                  )

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

from os.path import dirname, join, abspath, exists
BASE_DIR = dirname(dirname(__file__))
CREME_ROOT = dirname(abspath(__file__))  # BASE_DIR + '/creme'

# Define 'MANAGERS' if you use BrokenLinkEmailsMiddleware
# MANAGERS = ADMINS

# NB: it's recommended to :
#   - use a database engine that supports transactions (ie: not MyISAM for MySQL, which uses now INNODB by default).
#   - configure your database to use utf8 (eg: with MySQL, 'utf8_general_ci' is OK).
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

MIGRATION_MODULES = {
    'auth': 'creme.creme_core.migrations_auth', # XXX: should be removed in Creme 1.7 ...
}

# When this number of Entities is reached (in some views), Creme switches to a fast-mode.
# Currently, this fast-mode involves the following optimisations in list-views:
# - the main SQL query uses less complex ORDER BY instructions.
# - the paginator only allows to go to the next & the previous pages (& the main query is faster).
FAST_QUERY_MODE_THRESHOLD = 100000

# JOBS #########################################################################
# Maximum number of jobs each user can have at the same time. When this number
# is reached for a user, he must terminate one of his jobs in order to create a
# new one (ie: generally he'll wait that one of his existing jobs to be
# finished before he terminate it, of course).
# It allows you to avoid that a user, for example, create a lots of CSV imports
# & does not understand why they do not start immediately (see MAX_USER_JOBS).
MAX_JOBS_PER_USER = 1

# Maximum of jobs which can run at the same time. When this number is reached,
# a new created job will have to wait that a running jobs is finished).
# It allows you to limit the number of processes which are running.
# Notice that system jobs (sending mails, retrieving mails...) count is not
# limited (because they are created at installation, so their number &
# periodicity can be precisely managed).
MAX_USER_JOBS = 2

# 'security' period for pseudo-periodic jobs : they will be run at least with
# this periodicity, even if they do not receive a new request (in order to reduce
# the effects of an hypothetical redis problem).
PSEUDO_PERIOD = 1  # In hours

# URL with the pattern: redis://[:password]@host:port/db
# (password is optional; port & db are integers)
JOBMANAGER_BROKER = 'redis://@localhost:6379/0'


# AUTHENTICATION ###############################################################

AUTHENTICATION_BACKENDS = ('creme.creme_core.auth.backend.EntityBackend',)
AUTH_USER_MODEL = 'creme_core.CremeUser'


# I18N / L10N ##################################################################

USE_TZ = True

LANGUAGES = (
  ('en', 'English'),
  ('fr', 'French'),
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
LANGUAGE_CODE = 'fr'  # Choose in the LANGUAGES values

DEFAULT_ENCODING = 'UTF8'


DATE_FORMAT         = 'd-m-Y'
SHORT_DATE_FORMAT   = 'd-m-Y'
DATE_FORMAT_VERBOSE = _(u'Format: Day-Month-Year (Ex:31-12-2016)')
DATE_FORMAT_JS      = {
    DATE_FORMAT: 'dd-mm-yy',
}
DATE_FORMAT_JS_SEP = '-' # DATE_FORMAT_JS values separator
DATE_INPUT_FORMATS = (
    '%d-%m-%Y', '%d/%m/%Y',
    '%Y-%m-%d',  # DO NOT REMOVE ! Needed by the core (eg: to store queries in session)
    '%m/%d/%Y', '%m/%d/%y',  '%b %d %Y',
    '%b %d, %Y', '%d %b %Y', '%d %b, %Y', '%B %d %Y',
    '%B %d, %Y', '%d %B %Y', '%d %B, %Y',
)

DATETIME_FORMAT         = '%s H:i:s' % DATE_FORMAT
DATETIME_FORMAT_VERBOSE = _(u'Format: Day-Month-Year Hour:Minute:Second (Ex:31-12-2016 23:59:59)')
DATETIME_INPUT_FORMATS  = (
    '%d-%m-%Y', '%d/%m/%Y',
    '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d',
    '%m/%d/%Y %H:%M:%S', '%m/%d/%Y %H:%M', '%m/%d/%Y',
    '%m/%d/%y %H:%M:%S', '%m/%d/%y %H:%M', '%m/%d/%y',
    '%d-%m-%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S',
    '%d-%m-%Y %H:%M',    '%d/%m/%Y %H:%M',
    '%Y-%m-%dT%H:%M:%S.%fZ',  # DO NOT REMOVE ! Needed by the core (eg: to store queries in session) (+for some activesync servers)
    '%Y-%m-%dT%H:%M:%S',  # Needed for infopath
)

# I18N / L10N [END]#############################################################


# SITE: URLs / PATHS / ... #####################################################

SITE_ID = 1
SITE_DOMAIN = 'http://mydomain'  # No end slash!

APPEND_SLASH = False

ROOT_URLCONF = 'creme.urls'  # Means urls.py

LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/creme_login/'
LOGOUT_URL = '/creme_logout/'

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = join(CREME_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = 'http://127.0.0.1:8000/site_media/'

# Make this unique, and don't share it with anybody.
# Use 'python manage.py build_secret_key' to generate it.
SECRET_KEY = '1&7rbnl7u#+j-2#@5=7@Z0^9v@y_Q!*y^krWS)r)39^M)9(+6('

# A list of strings representing the host/domain names that this Django site can serve.
# You should set this list for security purposes.
# See: https://docs.djangoproject.com/en/1.8/ref/settings/#allowed-hosts
ALLOWED_HOSTS = '*'

# SITE: URLs / PATHS / ... [END]################################################

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            join(CREME_ROOT, 'templates'),
        ],
        'OPTIONS': {
            'context_processors': [
                # Default processors
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',

                # Creme additional processors
                'django.template.context_processors.request',

                'creme.creme_core.context_processors.get_logo_url',
                'creme.creme_core.context_processors.get_version',
                'creme.creme_core.context_processors.get_hidden_value',
                'creme.creme_core.context_processors.get_django_version',
                'creme.creme_core.context_processors.get_today',
                'creme.creme_core.context_processors.get_css_theme',
                # 'creme.creme_core.context_processors.get_blocks_manager',
                'creme.creme_core.context_processors.get_bricks_manager',
                'creme.creme_core.context_processors.get_fields_configs',
                'creme.creme_core.context_processors.get_shared_data',
                'creme.creme_core.context_processors.get_old_menu',
            ],
            'loaders': [
                # Don't use cached loader when developing (in your local_settings.py)
                ('django.template.loaders.cached.Loader', (
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                    # 'django.template.loaders.eggs.Loader',
                )),
            ],
            'debug': DEBUG,
        },
    },
]

MIDDLEWARE_CLASSES = (
    'creme.creme_core.middleware.exceptions.Ajax500Middleware',  # It must be last middleware that catch all exceptions
    'creme.creme_core.middleware.exceptions.Ajax404Middleware',
    'creme.creme_core.middleware.exceptions.Beautiful403Middleware',
    'creme.creme_core.middleware.exceptions.Beautiful409Middleware',

    'mediagenerator.middleware.MediaMiddleware',  # Media middleware has to come first

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',

    'creme.creme_core.middleware.global_info.GlobalInfoMiddleware',  # After AuthenticationMiddleware
    'creme.creme_core.middleware.timezone.TimezoneMiddleware',
)

INSTALLED_DJANGO_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    # 'django.contrib.sites', #remove ??

    # EXTERNAL APPS
    'creme.creme_core.apps.MediaGeneratorConfig',  # It manages js/css/images
)

INSTALLED_CREME_APPS = (
    # CREME CORE APPS
    'creme.creme_core',
    'creme.creme_config',
    'creme.media_managers',  # NB: will be removed in Creme 1.8
    'creme.documents',
    'creme.assistants',
    'creme.activities',
    'creme.persons',

    # CREME OPTIONAL APPS (can be safely commented)
    'creme.graphs',
    'creme.reports',
    'creme.products',
    'creme.recurrents',
    'creme.billing',  # Need 'products'
    'creme.opportunities',  # Need 'products'
    'creme.commercial',  # Need 'opportunities'
    'creme.events',  # Need 'opportunities'
    'creme.crudity',
    'creme.emails',
    # 'creme.sms',  # Work In Progress
    'creme.projects',
    'creme.tickets',
    # 'creme.cti',
    # 'creme.activesync',  # DEPRECATED
    'creme.vcfs',
    # 'creme.polls',  # Need 'commercial'
    # 'creme.mobile',
    'creme.geolocation',
)


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

# EMAILS [internal] ############################################################

# Emails sent to the users of Creme (reminders, assistants.user_message, commercial.commercial_approach...)
EMAIL_SENDER        = 'sender@domain.org'  # This is a Creme parameter which specifies from_email (sender) when sending email.
EMAIL_HOST          = 'localhost'
EMAIL_HOST_USER     = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS       = False
# EMAIL_PORT         = 1025 # Default value in django/conf/global_settings.py

# Tip: _developpement_ SMTP server
# => python -m smtpd -n -c DebuggingServer localhost:1025

DEFAULT_USER_EMAIL = ''  # Email address used in case the user doesn't have filled his one.


# EMAILS [END] #################################################################

# LOGS #########################################################################

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
    'level': 'WARNING',  # Available levels : DEBUG < INFO < WARNING < ERROR < CRITICAL
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
    'level': 'WARNING',  # Available levels : DEBUG < INFO < WARNING < ERROR < CRITICAL
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
        '': LOGGING_DEFAULT_LOGGER  # The empty key '' means that all logs are redirected to this logger.
    },
}

import warnings

# Warnings behavior choices (see Python doc):
# "error" "ignore" "always" "default" "module" "once"
warnings.simplefilter('once')

# LOGS [END]####################################################################

# TESTING ######################################################################

TEST_RUNNER = 'creme.creme_core.utils.test.CremeDiscoverRunner'

# GUI ##########################################################################

# Main menu
# LOGO_URL = 'images/creme_256_cropped.png'  # Big image in the side menu (for OLD_MENU = True)
LOGO_URL = 'images/creme_30.png'  # Small image in the side menu
# USE_STRUCT_MENU = True  # True = use the per app menu # DEPRECATED
OLD_MENU = False  # True use pre 1.7 menu (left side menu, with items per app)

BLOCK_SIZE = 10  # Lines number in common blocks
MAX_LAST_ITEMS = 9  # Max number of items in the 'Last viewed items' bar

HIDDEN_VALUE = u'??'  # Used to replace contents which a user is not allowed to see.

# List-view
PAGE_SIZES = [10, 25, 50, 100, 200]  # Available page sizes  (list of integers)
DEFAULT_PAGE_SIZE_IDX = 1  # Index (0-based, in PAGE_SIZES) of the default size of pages.

# GUI [END]#####################################################################


# MEDIA GENERATOR & THEME SETTINGS #############################################
# http://www.allbuttonspressed.com/projects/django-mediagenerator

MEDIA_DEV_MODE = False
DEV_MEDIA_URL = '/devmedia/'
PRODUCTION_MEDIA_URL = '/static_media/'

GENERATED_MEDIA_DIR = join(MEDIA_ROOT, 'static')
GLOBAL_MEDIA_DIRS = (join(dirname(__file__), 'static'),)

# Available themes. A theme is represented by (theme_dir, theme verbose name)
# First theme is the default one.
THEMES = [('icecream',  _('Ice cream')),
          ('chantilly', _('Chantilly')),
         ]
# DEPRECATED: use THEMES[0](0] instead
DEFAULT_THEME = 'icecream'  # Other available choice: 'chantilly'

CSS_DEFAULT_LISTVIEW = 'left_align'
CSS_NUMBER_LISTVIEW = 'right_align'
CSS_TEXTAREA_LISTVIEW = 'text_area'
CSS_DEFAULT_HEADER_LISTVIEW = 'hd_cl_lv'
CSS_DATE_HEADER_LISTVIEW = 'hd_date_cl_lv'

# TODO: create a static/css/creme-minimal.css for login/logout ??
CREME_CORE_CSS = ('main.css',
                    'creme_core/css/jquery-css/creme-theme/jquery-ui-1.11.4.custom.css',
                    'creme_core/css/fg-menu-3.0/fg.menu.css',
                    'creme_core/css/jqplot-1.0.8/jquery.jqplot.css',
                    'creme_core/css/jquery.gccolor.1.0.3/gccolor.css',
                    'creme_core/css/chosen/chosen-0.9.15-unchosen.css',

                    'creme_core/css/creme.css',
                    'creme_core/css/creme-ui.css',

                    'creme_core/css/header_menu.css',
                    'creme_core/css/blocks.css',
                    'creme_core/css/bricks.css',
                    'creme_core/css/home.css',
                    'creme_core/css/my_page.css',
                    'creme_core/css/search_results.css',
                    'creme_core/css/portal.css',
                    'creme_core/css/list_view.css',
                    'creme_core/css/detail_view.css',
                    'creme_core/css/navit.css',
                    'creme_core/css/forms.css',
                    'creme_core/css/popover.css',

                    'creme_config/css/creme_config.css',
                 )

CREME_OPT_CSS = (  # APPS
     ('creme.persons',          'persons/css/persons.css'),

     ('creme.activities',       'activities/css/activities.css'),
     ('creme.activities',       'activities/css/fullcalendar-1.6.7.css'),

     ('creme.billing',          'billing/css/billing.css'),
     ('creme.opportunities',    'opportunities/css/opportunities.css'),
     ('creme.commercial',       'commercial/css/commercial.css'),
     ('creme.crudity',          'crudity/css/crudity.css'),
     ('creme.emails',           'emails/css/emails.css'),
     ('creme.geolocation',      'geolocation/css/geolocation.css'),
     ('creme.polls',            'polls/css/polls.css'),
     ('creme.products',         'products/css/products.css'),
     ('creme.projects',         'projects/css/projects.css'),
     ('creme.reports',          'reports/css/reports.css'),
     ('creme.tickets',          'tickets/css/tickets.css'),
     ('creme.mobile',           'mobile/css/mobile.css'),
     ('creme.cti',              'cti/css/cti.css'),
)

CREME_I18N_JS = ('l10n.js',
                    {'filter': 'mediagenerator.filters.i18n.I18N'},  # To build the i18n catalog statically.
                    # 'creme_core/js/datejs/date-en-US.js', # TODO improve
                    'creme_core/js/datejs/date-fr-FR.js',
                )

CREME_LIB_JS = ('lib.js',
                    {'filter': 'mediagenerator.filters.media_url.MediaURL'},  # To get the media_url() function in JS.
                    'creme_core/js/media.js',
                    'creme_core/js/jquery/jquery-1.11.2.js',
                    'creme_core/js/jquery/jquery-migrate-1.2.1.js',
                    'creme_core/js/jquery/ui/jquery-ui-1.11.4.custom.js',
                    'creme_core/js/jquery/ui/jquery-ui-locale.js',
                    'creme_core/js/jquery/extensions/jquery.browser.js',
                    'creme_core/js/jquery/extensions/jquery.uuid-2.0.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.8/excanvas.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.8/jquery.jqplot.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.enhancedLegendRenderer.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.canvasTextRenderer.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.categoryAxisRenderer.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.canvasTextRenderer.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.canvasAxisLabelRenderer.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.canvasAxisTickRenderer.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.pieRenderer.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.donutRenderer.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.barRenderer.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.pointLabels.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.highlighter.js',
                    'creme_core/js/jquery/extensions/jqplot-1.0.8/plugins/jqplot.cursor.js',
                    'creme_core/js/jquery/extensions/cookie.js',
                    'creme_core/js/jquery/extensions/fg-menu-3.0/fg.menu.js',
                    'creme_core/js/jquery/extensions/fg-menu-3.0/jquery.hotkeys-0.8.js',
                    'creme_core/js/jquery/extensions/gccolor-1.0.3.js',
                    'creme_core/js/jquery/extensions/json-2.2.js',
                    'creme_core/js/jquery/extensions/highlight.js',
                    'creme_core/js/jquery/extensions/magnifier.js',
                    'creme_core/js/jquery/extensions/utils.js',
                    'creme_core/js/jquery/extensions/wait.js',
                    'creme_core/js/jquery/extensions/jquery.dragtable.js',
                    'creme_core/js/jquery/extensions/jquery.form-3.51.js',
                    'creme_core/js/jquery/extensions/jquery.tinymce.js',
                    'creme_core/js/jquery/extensions/jquery.debounce.js',
                    'creme_core/js/jquery/extensions/chosen.jquery-0.9.15-unchosen.js',
                    'creme_core/js/jquery/extensions/jquery.bind-first.js',
                    'creme_core/js/lib/jquery.navIt.0.0.6.js',
                )

CREME_CORE_JS = ('main.js',
                    'creme_core/js/lib/fallbacks/object-0.1.js',
                    'creme_core/js/lib/fallbacks/array-0.9.js',
                    'creme_core/js/lib/fallbacks/string-0.1.js',
                    'creme_core/js/lib/fallbacks/console.js',
                    'creme_core/js/lib/fallbacks/event-0.1.js',
                    'creme_core/js/lib/fallbacks/htmldocument-0.1.js',
                    'creme_core/js/lib/generators-0.1.js',

                    'creme_core/js/creme.js',
                    'creme_core/js/color.js',
                    'creme_core/js/utils.js',
                    'creme_core/js/forms.js',
                    'creme_core/js/ajax.js',

                    'creme_core/js/widgets/base.js',

                    'creme_core/js/widgets/component/component.js',
                    'creme_core/js/widgets/component/events.js',
                    'creme_core/js/widgets/component/action.js',
                    'creme_core/js/widgets/component/action-link.js',
                    'creme_core/js/widgets/component/chosen.js',

                    'creme_core/js/widgets/utils/template.js',
                    'creme_core/js/widgets/utils/lambda.js',
                    'creme_core/js/widgets/utils/converter.js',
                    'creme_core/js/widgets/utils/json.js',
                    'creme_core/js/widgets/utils/compare.js',
                    'creme_core/js/widgets/utils/history.js',

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
                    'creme_core/js/widgets/dialog/glasspane.js',
                    'creme_core/js/widgets/dialog/popover.js',

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
                    # 'creme_core/js/widgets/adaptivewidget.js',
                    'creme_core/js/widgets/actionlist.js',
                    'creme_core/js/widgets/plotdata.js',
                    'creme_core/js/widgets/plot.js',
                    'creme_core/js/widgets/plotselector.js',
                    'creme_core/js/widgets/scrollactivator.js',
                    'creme_core/js/widgets/container.js',

                    'creme_core/js/menu.js',
                    'creme_core/js/search.js',
                    'creme_core/js/blocks.js',

                    'creme_core/js/bricks.js',

                    'creme_core/js/list_view.core.js',
                    'creme_core/js/lv_widget.js',
                    'creme_core/js/detailview.js',

                    'creme_core/js/entity_cell.js',
                    'creme_core/js/export.js',
                    'creme_core/js/merge.js',
                    'creme_core/js/relations.js',
                    'creme_core/js/jobs.js',
                )

CREME_OPTLIB_JS = (
    ('creme.activities', 'activities/js/jquery/extensions/fullcalendar-1.6.7.js'),
)

CREME_OPT_JS = (  # OPTIONAL APPS
    ('creme.persons',       'persons/js/persons.js'),

    ('creme.assistants',    'assistants/js/assistants.js'),

    ('creme.activities',    'activities/js/activities.js'),

    ('creme.billing',       'billing/js/billing.js'),

    ('creme.opportunities', 'opportunities/js/opportunities.js'),

    ('creme.commercial',    'commercial/js/commercial.js'),

    ('creme.reports',       'reports/js/reports.js'),

    ('creme.crudity',       'crudity/js/crudity.js'),

    ('creme.emails',        'emails/js/emails.js'),

    ('creme.cti',           'cti/js/cti.js'),

    ('creme.events',        'events/js/events.js'),

    ('creme.geolocation',   'geolocation/js/geolocation.js'),
    ('creme.geolocation',   'geolocation/js/brick.js'),
)

TEST_CREME_LIB_JS = ('testlib.js',
                        'creme_core/js/tests/qunit/qunit-1.18.0.js',
                   )

TEST_CREME_CORE_JS = ('testcore.js',
                        'creme_core/js/tests/component/component.js',
                        'creme_core/js/tests/component/events.js',
                        'creme_core/js/tests/component/action.js',
                        'creme_core/js/tests/component/chosen.js',
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

TEST_CREME_OPT_JS = (
#   ('creme.my_app',       'my_app/js/tests/my_app.js'),
)

# Optional js/css bundles for extending projects.
# Beware to clashes with existing bundles ('main.js', 'l10n.js').
CREME_OPT_MEDIA_BUNDLES = ()

ROOT_MEDIA_FILTERS = {
    'js':  'mediagenerator.filters.yuicompressor.YUICompressor',
    # 'js':  'mediagenerator.filters.closure.Closure', # NB: Closure causes compilation errors...
    'css': 'mediagenerator.filters.yuicompressor.YUICompressor',
}

YUICOMPRESSOR_PATH = join(dirname(__file__), 'static', 'utils', 'yui', 'yuicompressor-2.4.2.jar')
# CLOSURE_COMPILER_PATH = join(dirname(__file__), 'closure.jar')

COPY_MEDIA_FILETYPES = (
    'gif', 'jpg', 'jpeg', 'png', 'ico', 'cur',  # Images
    'woff', 'tff', 'eot',  # Fonts
)

# MEDIA GENERATOR & THEME SETTINGS [END] #######################################


# APPS CONFIGURATION ###########################################################

# If you change a <APP>_<MODEL>_MODEL setting (eg: PERSONS_CONTACT_MODEL) in order
# to use your own model class (eg: 'my_persons.Contact') :
#   - It will be easier to inherit the corresponding abstract class
#     (eg: persons.model.AbstractContact).
#   - you should keep the same class name (eg: 'my_persons.Contact' replaces
#     'persons.Contact') in order to avoids problems (mainly with related_names).
#   - You have to manage the migrations of your model
#     (see the django command 'makemigrations').
#   - In your file my_app.urls.py, you have to define the URLs which are only
#     defined for vanilla models
#     (eg: see persons.urls.py => 'if not contact_model_is_custom()' block).
#     You can use the vanilla views or define your own ones (by calling
#     the abstract views or by writing them from scratch).
#   - You probably should copy (in your 'tests' module) then modify the unit
#     tests which are skipped for custom models, & make them pass.
#
# But if you set the related <APP>_<MODEL>_FORCE_NOT_CUSTOM setting
# (eg: PERSONS_CONTACT_FORCE_NOT_CUSTOM for PERSONS_CONTACT_MODEL) to 'True'
# when you use a custom model, the model will not be considered as custom.
# So the vanilla URLs will be defined on the vanilla views (& tests will not
# be skipped). YOU MUST USE THIS FEATURE WITH CAUTION ; it's OK if your model
# is identical to the vanilla model (eg: he just inherits the abstract class)
# or it has some not required additional fields. In the other cases it is
# probably a bad idea to set the *_FORCE_NOT_CUSTOM setting to 'True' (ie
# you should define URLs etc...).

# DOCUMENTS --------------------------------------------------------------------
DOCUMENTS_FOLDER_MODEL   = 'documents.Folder'
DOCUMENTS_DOCUMENT_MODEL = 'documents.Document'

DOCUMENTS_FOLDER_FORCE_NOT_CUSTOM   = False
DOCUMENTS_DOCUMENT_FORCE_NOT_CUSTOM = False

# PERSONS ----------------------------------------------------------------------
PERSONS_ADDRESS_MODEL      = 'persons.Address'
PERSONS_CONTACT_MODEL      = 'persons.Contact'
PERSONS_ORGANISATION_MODEL = 'persons.Organisation'

PERSONS_ADDRESS_FORCE_NOT_CUSTOM      = False
PERSONS_CONTACT_FORCE_NOT_CUSTOM      = False
PERSONS_ORGANISATION_FORCE_NOT_CUSTOM = False

# ASSISTANTS -------------------------------------------------------------------
DEFAULT_TIME_ALERT_REMIND = 10
DEFAULT_TIME_TODO_REMIND = 120

# REPORTS ----------------------------------------------------------------------
REPORTS_REPORT_MODEL = 'reports.Report'
REPORTS_GRAPH_MODEL  = 'reports.ReportGraph'

REPORTS_REPORT_FORCE_NOT_CUSTOM = False
REPORTS_GRAPH_FORCE_NOT_CUSTOM  = False

# ACTIVITIES -------------------------------------------------------------------
ACTIVITIES_ACTIVITY_MODEL = 'activities.Activity'
ACTIVITIES_ACTIVITY_FORCE_NOT_CUSTOM = False

# GRAPHS -----------------------------------------------------------------------
GRAPHS_GRAPH_MODEL = 'graphs.Graph'
GRAPHS_GRAPH_FORCE_NOT_CUSTOM = False

# PRODUCTS ---------------------------------------------------------------------
PRODUCTS_PRODUCT_MODEL = 'products.Product'
PRODUCTS_SERVICE_MODEL = 'products.Service'

PRODUCTS_PRODUCT_FORCE_NOT_CUSTOM = False
PRODUCTS_SERVICE_FORCE_NOT_CUSTOM = False

# RECURRENTS -------------------------------------------------------------------
RECURRENTS_RGENERATOR_MODEL = 'recurrents.RecurrentGenerator'
RECURRENTS_RGENERATOR_FORCE_NOT_CUSTOM = False

# BILLING ----------------------------------------------------------------------
BILLING_CREDIT_NOTE_MODEL   = 'billing.CreditNote'
BILLING_INVOICE_MODEL       = 'billing.Invoice'
BILLING_PRODUCT_LINE_MODEL  = 'billing.ProductLine'
BILLING_QUOTE_MODEL         = 'billing.Quote'
BILLING_SALES_ORDER_MODEL   = 'billing.SalesOrder'
BILLING_SERVICE_LINE_MODEL  = 'billing.ServiceLine'
BILLING_TEMPLATE_BASE_MODEL = 'billing.TemplateBase'

BILLING_CREDIT_NOTE_FORCE_NOT_CUSTOM   = False
BILLING_INVOICE_FORCE_NOT_CUSTOM       = False
BILLING_PRODUCT_LINE_FORCE_NOT_CUSTOM  = False
BILLING_QUOTE_FORCE_NOT_CUSTOM         = False
BILLING_SALES_ORDER_FORCE_NOT_CUSTOM   = False
BILLING_SERVICE_LINE_FORCE_NOT_CUSTOM  = False
BILLING_TEMPLATE_BASE_FORCE_NOT_CUSTOM = False

# Prefixes used to generate the numbers of the billing documents
# (with the 'vanilla' number generator)
QUOTE_NUMBER_PREFIX = 'DE'
INVOICE_NUMBER_PREFIX = 'FA'
SALESORDER_NUMBER_PREFIX = 'BC'

# OPPORTUNITIES ----------------------------------------------------------------
OPPORTUNITIES_OPPORTUNITY_MODEL = 'opportunities.Opportunity'
OPPORTUNITIES_OPPORTUNITY_FORCE_NOT_CUSTOM = False

# COMMERCIAL -------------------------------------------------------------------
COMMERCIAL_ACT_MODEL      = 'commercial.Act'
COMMERCIAL_PATTERN_MODEL  = 'commercial.ActObjectivePattern'
COMMERCIAL_STRATEGY_MODEL = 'commercial.Strategy'

COMMERCIAL_ACT_FORCE_NOT_CUSTOM      = False
COMMERCIAL_PATTERN_FORCE_NOT_CUSTOM  = False
COMMERCIAL_STRATEGY_FORCE_NOT_CUSTOM = False

# EMAILS [external] ------------------------------------------------------------
EMAILS_CAMPAIGN_MODEL = 'emails.EmailCampaign'
EMAILS_TEMPLATE_MODEL = 'emails.EmailTemplate'
EMAILS_EMAIL_MODEL    = 'emails.EntityEmail'
EMAILS_MLIST_MODEL    = 'emails.MailingList'

EMAILS_CAMPAIGN_FORCE_NOT_CUSTOM = False
EMAILS_TEMPLATE_FORCE_NOT_CUSTOM = False
EMAILS_EMAIL_FORCE_NOT_CUSTOM    = False
EMAILS_MLIST_FORCE_NOT_CUSTOM    = False

# Emails campaigns sent to the customers
EMAILCAMPAIGN_HOST      = 'localhost'
EMAILCAMPAIGN_HOST_USER = ''
EMAILCAMPAIGN_PASSWORD  = ''
EMAILCAMPAIGN_PORT      = 25
EMAILCAMPAIGN_USE_TLS   = True

# Emails are sent by chunks, and sleep between 2 chunks.
EMAILCAMPAIGN_SIZE = 40
EMAILCAMPAIGN_SLEEP_TIME = 2

# SMS --------------------------------------------------------------------------
SMS_CAMPAIGN_MODEL = 'sms.SMSCampaign'
SMS_MLIST_MODEL    = 'sms.MessagingList'
SMS_TEMPLATE_MODEL = 'sms.MessageTemplate'

SMS_CAMPAIGN_FORCE_NOT_CUSTOM = False
SMS_MLIST_FORCE_NOT_CUSTOM    = False
SMS_TEMPLATE_FORCE_NOT_CUSTOM = False

CREME_SAMOUSSA_URL = 'http://localhost:8001/'
CREME_SAMOUSSA_USERNAME = ''
CREME_SAMOUSSA_PASSWORD = ''

# CRUDITY -----------------------------------------------------------------------
# EMail parameters to sync external emails in Creme
CREME_GET_EMAIL              = ''  # Creme gets email. e.g : creme@cremecrm.org
CREME_GET_EMAIL_SERVER       = ''  # Creme gets server. e.g : pop.cremecrm.org (only pop supported for now)
CREME_GET_EMAIL_USERNAME     = ''
CREME_GET_EMAIL_PASSWORD     = ''
CREME_GET_EMAIL_PORT         = 110
CREME_GET_EMAIL_SSL          = False  # True or False
CREME_GET_EMAIL_SSL_KEYFILE  = ''  # PEM formatted file that contains your private key (only used if CREME_GET_EMAIL_SSL is True).
CREME_GET_EMAIL_SSL_CERTFILE = ''  # PEM formatted certificate chain file (only used if CREME_GET_EMAIL_SSL is True).

# Path to a readable directory. Used by the fetcher 'filesystem'.
# The contained files are used to create entity (ex: the input 'ini' used .ini files) ; used files are deleted.
CRUDITY_FILESYS_FETCHER_DIR = ''

# Only for job. Default user id which will handle the synchronization
# User used to synchronize mails with management command.
# This ID is only used during the installation for the crudity's job configuration.
# Configure (graphically) the job if you want to change it later.
# TODO: delete it in creme1.8
CREME_GET_EMAIL_JOB_USER_ID = 1

# CRUDITY_BACKENDS configures the backends (it's a list of dict)
# Here a template of a crudity backend configuration:
#CRUDITY_BACKENDS = [
#    {
#        "fetcher": "email",                # The name of the fetcher (which is registered with).
#                                           #  Available choices:
#                                           #   - 'email' (need the settings CREME_GET_EMAIL* to be filled).
#                                           #   - 'filesystem' (see CRUDITY_FILESYS_FETCHER_DIR).
#        "input": "infopath",               # The name of the input (which is registered with).
#                                           #  Available choices:
#                                           #   - for the fetcher 'email': 'raw', 'infopath' (that needs "lcab" program).
#                                           #   - for the fetcher 'filesystem': 'ini'.
#                                           # Can be omitted if 'subject' is '*' (see below).
#        "method": "create",                # The method of the input to call. Available choices: 'create'
#                                           #  Can be omitted if 'subject' is '*' (see below).
#        "model": "activities.activity",    # The targeted model
#        "password": "meeting",             # Password to be authorized in the input
#        "limit_froms": (),                 # A white list of sender (Example with an email:
#                                           #  If a recipient email's address not in this drop email, let empty to allow all email addresses)
#        "in_sandbox": True,                # True : Show in sandbox & history, False show only in history (/!\ creation will be automatic if False)
#        "body_map"   : {                   # Allowed keys format : "key": "default value".
#            "title": "",                   #  Keys have to be real field names of the model
#            "user_id": 1,
#        },
#        "subject": u"CREATEACTIVITYIP"     # Target subject, nb: in the subject all spaces will be deleted, and it'll be converted to uppercase.
#                                           #  You can specify * as a fallback (no previous backend handle the data returned by the fetcher,
#                                           #  but be careful your backend has to have the method: 'fetcher_fallback').
#    },
#]
CRUDITY_BACKENDS = [
    {
        'fetcher': 'email',
        # 'input': 'raw',
        'input': '',
        # 'method': 'create',
        'method': '',
        'model': 'emails.entityemail',
        'password': '',
        'limit_froms': (),
        'in_sandbox': True,
        'body_map': {},
        'subject': u'*',
    },
]

# ACTIVESYNC -------------------------------------------------------------------
# TODO: Rename and transform this into an AS-Version verification => A2:Body doesn't seems to work with AS version > 2.5
IS_ZPUSH = True

# 0 = Client object replaces server object.
# 1 = Server object replaces client object.
CONFLICT_MODE = 1

ACTIVE_SYNC_DEBUG = DEBUG  # Make appears some debug informations on the UI

LIMIT_SYNC_KEY_HISTORY = 50  # Number of sync_keys kept in db by user

CONNECTION_TIMEOUT = 150

PICTURE_LIMIT_SIZE = 55000  # E.g: 55Ko Active sync servers don't handle pictures > to this size

# TICKETS ----------------------------------------------------------------------
TICKETS_TICKET_MODEL   = 'tickets.Ticket'
TICKETS_TEMPLATE_MODEL = 'tickets.TicketTemplate'

TICKETS_TICKET_FORCE_NOT_CUSTOM   = False
TICKETS_TEMPLATE_FORCE_NOT_CUSTOM = False

# If a Ticket is still open TICKETS_COLOR_DELAY days after its creation, it is red in the listview
TICKETS_COLOR_DELAY = 7

# EVENTS -----------------------------------------------------------------------
EVENTS_EVENT_MODEL = 'events.Event'
EVENTS_EVENT_FORCE_NOT_CUSTOM = False

# CTI --------------------------------------------------------------------------
ABCTI_URL = 'http://127.0.0.1:8087'

# VCF --------------------------------------------------------------------------
# Limit size (byte) of remote photo files
# (i.e : when the photo in the vcf file is just a url)
VCF_IMAGE_MAX_SIZE = 3145728

# PROJECTS ---------------------------------------------------------------------
PROJECTS_PROJECT_MODEL = 'projects.Project'
PROJECTS_TASK_MODEL    = 'projects.ProjectTask'

PROJECTS_PROJECT_FORCE_NOT_CUSTOM = False
PROJECTS_TASK_FORCE_NOT_CUSTOM    = False

# POLLS ------------------------------------------------------------------------
POLLS_CAMPAIGN_MODEL = 'polls.PollCampaign'
POLLS_FORM_MODEL     = 'polls.PollForm'
POLLS_REPLY_MODEL    = 'polls.PollReply'

POLLS_CAMPAIGN_FORCE_NOT_CUSTOM = False
POLLS_FORM_FORCE_NOT_CUSTOM     = False
POLLS_REPLY_FORCE_NOT_CUSTOM    = False

# MOBILE -----------------------------------------------------------------------
# Domain of the complete version (in order to go to it from the mobile version).
# eg: 'http://mydomain' #No end slash!
# '' means that there is only one domain for the complete & the mobile versions ;
# so SITE_DOMAIN will be used.
NON_MOBILE_SITE_DOMAIN = ''

# GEOLOCATION ------------------------------------------------------------------
# Files containing towns with their location.
# It can be an URL or a local file ; zip files are also supported.
GEOLOCATION_TOWNS = (
    (join(CREME_ROOT, 'geolocation/data/towns.france.csv.zip'), {'country': 'France'}),
)


# APPS CONFIGURATION [END]######################################################

try:
    from project_settings import *
except ImportError:
    pass

try:
    from local_settings import *
except ImportError:
    pass

# GENERAL [FINAL SETTINGS]------------------------------------------------------

_LOCALE_OVERLOAD = join(CREME_ROOT, 'locale_overload', 'locale')

LOCALE_PATHS = [join(CREME_ROOT, 'locale')]
if exists(_LOCALE_OVERLOAD):
    LOCALE_PATHS.append(_LOCALE_OVERLOAD)
# LOCALE_PATHS.extend(join(CREME_ROOT, app.rsplit('.')[-1], "locale") for app in INSTALLED_CREME_APPS)

INSTALLED_APPS = INSTALLED_DJANGO_APPS + INSTALLED_CREME_APPS


# MEDIA GENERATOR [FINAL SETTINGS]----------------------------------------------

# NB: done in MediaGeneratorConfig now
# MEDIA_BUNDLES = (
#                  CREME_I18N_JS,
#                  CREME_CORE_JS + tuple(js for app, js in CREME_OPT_JS if app in INSTALLED_CREME_APPS)
#                 )
# if FORCE_JS_TESTVIEW:
#     MEDIA_BUNDLES += (TEST_CREME_CORE_JS,)
#
# MEDIA_BUNDLES += CREME_OPT_MEDIA_BUNDLES
#
# CREME_CSS = CREME_CORE_CSS + tuple(css for app, css in CREME_OPT_CSS if app in INSTALLED_CREME_APPS)
# MEDIA_BUNDLES += tuple((theme_dir + CREME_CSS[0], ) + tuple(theme_dir + '/' + css_file if not isinstance(css_file, dict) else css_file for css_file in CREME_CSS[1:])
#                         for theme_dir, theme_vb_name in THEMES
#                        )
