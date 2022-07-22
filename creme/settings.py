# -*- coding: utf-8 -*-
# Django settings for creme project.

import warnings
# from os.path import exists
from os.path import abspath, dirname, join
from sys import argv

from django.utils.translation import gettext_lazy as _

DEBUG = False

TESTS_ON = len(argv) > 1 and argv[1] == 'test'
FORCE_JS_TESTVIEW = False

# Commands which do not need to perform SQL queries
# (so the apps do not need to be totally initialized)
NO_SQL_COMMANDS = (
    'help', 'version', '--help', '--version', '-h',
    'compilemessages', 'makemessages',
    'startapp', 'startproject',
    'migrate',
    'generatemedia',
    'build_secret_key',
    'creme_start_project',
)

# People who get code error notifications.
# ADMINS = [
#     ('Full Name', 'email@example.com'),
#     ('Full Name', 'anotheremail@example.com')
# ]

# BASE_DIR = dirname(dirname(__file__))
# CREME_ROOT = dirname(abspath(__file__))  # BASE_DIR + '/creme'
# BASE_DIR should be define in the project's settings
# TODO: use pathlib.Path
CREME_ROOT = dirname(abspath(__file__))  # Folder 'creme/'

# Define 'MANAGERS' if you use BrokenLinkEmailsMiddleware
# MANAGERS = ADMINS

# NB: it's recommended to :
#   - use a database engine that supports transactions
#     (ie: not MyISAM for MySQL, which uses now INNODB by default).
#   - configure your database to use utf8 (eg: with MySQL, 'utf8_general_ci' is OK).
DATABASES = {
    'default': {
        # Possible backends: 'postgresql', 'mysql', 'sqlite3'.
        # NB: 'oracle' backend is not working with creme for now.
        # 'ENGINE': 'django.db.backends.mysql',
        'ENGINE': 'django.db.backends.sqlite3',

        # Name of the database, or path to the database file if using 'sqlite3'.
        'NAME': 'cremecrm',

        # Not used with sqlite3.
        'USER': 'creme',

        # Not used with sqlite3.
        'PASSWORD': 'creme',

        # Set to empty string for localhost. Not used with 'sqlite3'.
        'HOST': '',

        # Set to empty string for default. Not used with 'sqlite3'.
        'PORT': '',

        # Extra parameters for database connection.
        # Consult backend module's document for available keywords.
        'OPTIONS':  {},
    },
}

# MIGRATION_MODULES = {}

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# When this number of Entities is reached (in some views), Creme switches to a fast-mode.
# Currently, this fast-mode involves the following optimisations in list-views:
# - the main SQL query uses less complex ORDER BY instructions.
# - the paginator only allows to go to the next & the previous pages (& the main query is faster).
FAST_QUERY_MODE_THRESHOLD = 100000

# JOBS #########################################################################
# Maximum number of not finished jobs each user can have at the same time.
#  When this number is reached for a user, he must wait one of his
# running/waiting jobs is finished in order to create a new one
# It allows you :
#  - to avoid that a user, for example, create a lots of CSV imports
#    & does not understand why they do not start immediately (see MAX_USER_JOBS).
#  - avoid that a user creates several jobs which hold all the slots for
#    user-jobs (see MAX_USER_JOBS), avoiding other user to run their own jobs.
MAX_JOBS_PER_USER = 2

# Maximum of jobs which can run at the same time. When this number is reached,
# a new created job will have to wait that a running jobs is finished).
# It allows you to limit the number of processes which are running.
# Notice that system jobs (sending mails, retrieving mails...) count is not
# limited (because they are created at installation, so their number &
# periodicity can be precisely managed).
MAX_USER_JOBS = 5

# 'security' period for pseudo-periodic jobs : they will be run at least with
# this periodicity, even if they do not receive a new request (in order to reduce
# the effects of an hypothetical redis problem).
PSEUDO_PERIOD = 1  # In hours

# Broker's URL (communication between the views and the job scheduler)
# It's a URL which starts by "type://".
# Currently there are 2 queue types:
#  - Redis (type: "redis"):
#     It needs a Redis server to be launched, and the python package "redis".
#     It's multi-platform & distributed, so it's currently the default choice.
#     The URL follows this pattern: redis://[:password]@host:port/db
#     (password is optional; port & db are integers)
#  - Unix socket (type: "unix_socket"):
#     It needs a POSIX Operating System (*Linux, *BSD, ...).
#     The web servers & the job scheduler must run on the same machine.
#     Example of URL: unix_socket:///tmp/creme/
#      Remarks:
#         - The directories of the URL which do not exist will be created by
#           the scheduler (here "creme/", you do don't have to create it &
#           simply use /tmp as usual).
#         - The system user who runs Creme must have the permission to read &
#           write in the given directory of course.
#         - An additional/temporary directory "private-{username}/", containing
#           a file named "socket", will be created dynamically. So your URL just
#           have to indicate the parent directory.
JOBMANAGER_BROKER = 'redis://@localhost:6379/0'


# AUTHENTICATION ###############################################################

# (see the documentation of the Django's app "auth")
AUTHENTICATION_BACKENDS = ['creme.creme_core.auth.backend.EntityBackend']
AUTH_USER_MODEL = 'creme_core.CremeUser'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# I18N / L10N ##################################################################

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Paris'

# Use timezone-aware date-times ? (you probably should keep the "True" value here).
USE_TZ = True

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'fr'  # Choose in the LANGUAGES values

# Available languages (ie: with a translation), proposed in each user settings.
LANGUAGES = [
    ('en', 'English'),
    ('fr', 'Français'),
]

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# DO NOT CHANGE THIS VALUE, Creme is not ready for that yet.
# If you set this to True, Django will format dates, numbers and calendars
# according to user current locale.
# TODO: pass to 'True' by default  (in a future release...)
USE_L10N = False

DEFAULT_ENCODING = 'UTF8'


DATE_FORMAT         = 'd-m-Y'
SHORT_DATE_FORMAT   = 'd-m-Y'
DATE_FORMAT_VERBOSE = _('Format: Day-Month-Year (Ex:31-12-2022)')
DATE_FORMAT_JS      = {
    DATE_FORMAT: 'dd-mm-yy',
}
DATE_FORMAT_JS_SEP = '-'  # DATE_FORMAT_JS values separator
DATE_INPUT_FORMATS = [
    '%d-%m-%Y', '%d/%m/%Y',
    '%Y-%m-%d',  # DO NOT REMOVE ! Needed by the core (eg: to store queries in session)
    '%m/%d/%Y', '%m/%d/%y',  '%b %d %Y',
    '%b %d, %Y', '%d %b %Y', '%d %b, %Y', '%B %d %Y',
    '%B %d, %Y', '%d %B %Y', '%d %B, %Y',
]

DATETIME_FORMAT         = '%s H:i:s' % DATE_FORMAT
DATETIME_FORMAT_VERBOSE = _(
    'Format: Day-Month-Year Hour:Minute:Second (Ex:31-12-2022 23:59:59)'
)
DATETIME_INPUT_FORMATS  = [
    '%d-%m-%Y', '%d/%m/%Y',
    '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d',
    '%m/%d/%Y %H:%M:%S', '%m/%d/%Y %H:%M', '%m/%d/%Y',
    '%m/%d/%y %H:%M:%S', '%m/%d/%y %H:%M', '%m/%d/%y',
    '%d-%m-%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S',
    '%d-%m-%Y %H:%M',    '%d/%m/%Y %H:%M',
    # DO NOT REMOVE ! Needed by the core (eg: to store queries in session)
    '%Y-%m-%dT%H:%M:%S.%fZ',
    '%Y-%m-%dT%H:%M:%S',  # Needed for infopath
]

# I18N / L10N [END]#############################################################


# SITE: URLs / PATHS / ... #####################################################

# SITE_ID = 1
SITE_DOMAIN = 'http://mydomain'  # No end slash!

APPEND_SLASH = False

ROOT_URLCONF = 'creme.urls'  # Means urls.py

LOGIN_REDIRECT_URL = 'creme_core__home'
LOGIN_URL = 'creme_login'

# Absolute filesystem path to the directory that will hold user-uploaded files,
# and files that are generated dynamically (CSV, PDF...).
# Example: "/var/www/example.com/media/"
# MEDIA_ROOT = join(CREME_ROOT, 'media')
MEDIA_ROOT = join(CREME_ROOT, 'media', 'upload')

# NB: not currently used (see root's urls.py)  TODO: remove it ?
# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = 'http://127.0.0.1:8000/site_media/'

# Absolute path to the directory static files should be collected to.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = join(CREME_ROOT, 'media', 'static')

# Make this unique, and don't share it with anybody.
# Use the command 'build_secret_key' to generate it.
# eg: SECRET_KEY = '1&7rbnl7u#+j-2#@5=7@Z0^9v@y_Q!*y^krWS)r)39^M)9(+6('
SECRET_KEY = ''

# A list of strings representing the host/domain names that this Django site can serve.
# You should set this list for security purposes.
# See: https://docs.djangoproject.com/en/3.2/ref/settings/#allowed-hosts
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

                'creme.creme_core.context_processors.get_version',
                'creme.creme_core.context_processors.get_hidden_value',
                'creme.creme_core.context_processors.get_django_version',
                'creme.creme_core.context_processors.get_repository',
                'creme.creme_core.context_processors.get_site_domain',
                'creme.creme_core.context_processors.get_today',
                'creme.creme_core.context_processors.get_css_theme',
                'creme.creme_core.context_processors.get_bricks_manager',
                'creme.creme_core.context_processors.get_fields_configs',
                'creme.creme_core.context_processors.get_shared_data',
                'creme.creme_core.context_processors.get_jqmigrate_mute',
            ],
            'loaders': [
                # Don't use cached loader when developing (in your local_settings.py)
                ('django.template.loaders.cached.Loader', (
                    'django.template.loaders.app_directories.Loader',
                    'django.template.loaders.filesystem.Loader',
                )),
            ],
            'debug': DEBUG,
        },
    },
]

MIDDLEWARE = [
    # It must be last middleware that catches all exceptions
    'creme.creme_core.middleware.exceptions.Ajax500Middleware',

    'creme.creme_core.middleware.exceptions.Ajax404Middleware',
    'creme.creme_core.middleware.exceptions.Ajax403Middleware',
    'creme.creme_core.middleware.exceptions.Beautiful409Middleware',
    'creme.creme_core.middleware.exceptions.BadRequestMiddleware',

    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # Must be after SessionMiddleware:
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # After AuthenticationMiddleware:
    'creme.creme_core.middleware.locale.LocaleMiddleware',
    'creme.creme_core.middleware.global_info.GlobalInfoMiddleware',
    'creme.creme_core.middleware.timezone.TimezoneMiddleware',
]

INSTALLED_DJANGO_APPS = [
    'creme.creme_core.apps.ContentTypesConfig',  # Replaces 'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',

    # EXTERNAL APPS
    'formtools',
    'creme.creme_core.apps.MediaGeneratorConfig',  # It manages JS, CSS & static images
]

INSTALLED_CREME_APPS = [
    # ----------------------
    # MANDATORY CREME APPS #
    # ----------------------
    'creme.creme_core',

    # Manages the Configuration portal.
    'creme.creme_config',

    # Manages Folders & Documents entities.
    # NB: currently used by "creme_core" for mass-importing,
    #     so it's a mandatory app.
    'creme.documents',

    # Manages Contacts & Organisations entities.
    'creme.persons',

    # -----------------------------------------------
    # CREME OPTIONAL APPS (can be safely commented) #
    # -----------------------------------------------

    # Manages Activities entities:
    #   - they represent meetings, phone calls, tasks...
    #   - have participants (Contacts) & subjects.
    #   - can be displayed in a calendar view.
    # There are extra features if the app "assistants" is installed
    # (Alerts & UserMessages can be created when an Activity is created).
    'creme.activities',

    # Manage the following auxiliary models (related to an entity):
    # Alert, ToDO, Memo, Action, UserMessage
    # They can be created through specific blocks in detailed views of entities.
    'creme.assistants',

    # Manages the Graphs entities ; they are used to generated images to
    # visualize all the entities which are linked to given entities.
    'creme.graphs',

    # Manages the Reports entities:
    #   - they can generate CSV/XLS files containing information about entities,
    #     generally filtered on a date range.
    #   - they can be used by special blocks to display some statistics
    #     (eg: number of related Invoices per month in the current year) as
    #     histograms/pie-charts...
    'creme.reports',

    # Manages Products & Services entities, to represent what an Organisation
    # sells.
    'creme.products',

    # Manages RecurrentGenerator entities, which can generate recurrently some
    # types of entities.
    # Compatible with these apps:
    #   - billing (models Invoice/Quote/SalesOrder/CreditNote)
    #   - tickets
    'creme.recurrents',

    # Manages Invoices, Quotes, SalesOrders & CreditNotes entities.
    # BEWARE: needs the app "products".
    'creme.billing',

    # Manages Opportunities entities, which represent business opportunities
    # (typically an Organisation trying to sell Products/Services to another
    # Organisation).
    # BEWARE: needs the app "products".
    # There are extra features if the app "billing" is installed, like new
    # blocks with related Quotes or Invoices.
    'creme.opportunities',

    # Manages several types of entities related to salesmen :
    #   - Act (commercial actions), which are used to define some goals to reach
    #     (eg: a minimum number of people met on a show).
    #   - Strategy to study market segments, assets & charms.
    # BEWARE: needs the apps "activities & "opportunities".
    'creme.commercial',

    # Manages the Events entities, which represents shows/conferences/... where
    # people are invited.
    # BEWARE: needs the app "opportunities".
    'creme.events',

    # CReates/Removes/UpDates entities from data contained in emails/files...
    # Actions can be stored ina sand-box before being really applied.
    # NB1: currently only creation is implemented.
    # NB2: currently accepted actions are defined below in the section
    #      'crudity' (if the future they will be defined from a GUI).
    'creme.crudity',

    # Manages EntityEmails, MailingLists & EmailCampaign entities.
    # If the app "crudity" is installed, emails can be synchronised with Creme.
    'creme.emails',

    # 'creme.sms',  # Work In Progress

    # Manages Projects & ProjectTasks entities. Projects contain tasks, which
    # can depend on other tasks (their parents), & be associated to Activities.
    # It's a lightweight project manager, don't expect things like GANTT chart.
    # BEWARE: needs the app "activities".
    'creme.projects',

    # Manages Tickets entities, which notably have a status (open, closed...)
    # & a priority (low, high...). They are often used to manages issues
    # encountered by customers.
    'creme.tickets',

    # <Computer Telephony Integration> features.
    # BEWARE: needs the app "activities".
    # 'creme.cti',

    # Manages VCF files:
    #   - Export a Contact as a VCF file
    #   - Import a Contact (& eventually the related Organisation) from a VCF
    #     file.
    'creme.vcfs',

    # Manages PollForms, PollReplies & PollCampaigns entities, to create
    # internal polls.
    # Answers have type (integers, date, boolean...) & can depend on previous
    # answers.
    # BEWARE: needs the app "commercial".
    # 'creme.polls',

    # Display some lightweight views, about Contacts, Organisations &
    # Activities, which are adapted to smartphones.
    # BEWARE: needs the app "activities".
    # 'creme.mobile',

    # Adds some specific blocks to detailed view of Contacts/Organisations which
    # display maps (Google Maps, Open Street Map) using the address information.
    # I can be useful to plan a business itinerary.
    'creme.geolocation',
]


ALLOWED_IMAGES_EXTENSIONS = [
    'gif', 'png', 'jpeg', 'jpg', 'jpe', 'bmp', 'psd', 'tif', 'tiff', 'tga', 'svg',
]
ALLOWED_EXTENSIONS = [
    'pdf', 'rtf', 'xps', 'eml',
    'psd',
    'gtar', 'gz', 'tar', 'zip', 'rar', 'ace', 'torrent', 'tgz', 'bz2',
    '7z', 'txt', 'c', 'cpp', 'hpp', 'diz', 'csv', 'ini', 'log', 'js',
    'xml', 'xls', 'xlsx', 'xlsm', 'xlsb', 'doc', 'docx', 'docm', 'dot',
    'dotx', 'dotm', 'pdf', 'ai', 'ps', 'ppt', 'pptx', 'pptm', 'odg',
    'odp', 'ods', 'odt', 'rtf', 'rm', 'ram', 'wma', 'wmv', 'swf', 'mov',
    'm4v', 'm4a', 'mp4', '3gp', '3g2', 'qt', 'avi', 'mpeg', 'mpg', 'mp3',
    'ogg', 'ogm',
    *ALLOWED_IMAGES_EXTENSIONS,
]

IMPORT_BACKENDS = [
    'creme.creme_core.backends.csv_import.CSVImportBackend',
    'creme.creme_core.backends.xls_import.XLSImportBackend',
    'creme.creme_core.backends.xls_import.XLSXImportBackend',
]
EXPORT_BACKENDS = [
    'creme.creme_core.backends.csv_export.CSVExportBackend',
    'creme.creme_core.backends.csv_export.SemiCSVExportBackend',
    'creme.creme_core.backends.xls_export.XLSExportBackend',
]

# EMAILS [internal] ############################################################

# Emails sent to the users of Creme
# (reminders, assistants.user_message, commercial.commercial_approach...)

# This is a Creme parameter which specifies from_email (sender) when sending email.
EMAIL_SENDER = 'sender@domain.org'

# Following values are from Django :
#  See https://docs.djangoproject.com/en/3.1/ref/settings/#email-host
#  or the file "django/conf/global_settings.py"
#  for a complete documentation.
#  BEWARE: the Django's names for secure parameters may be misleading.
#    EMAIL_USE_TLS is for startTLS (often with port 587) ; for communication
#    with TLS use EMAIL_USE_SSL. See :
#     - https://docs.djangoproject.com/fr/3.1/ref/settings/#email-use-tls
#     - https://docs.djangoproject.com/fr/3.1/ref/settings/#email-use-ssl
EMAIL_HOST = 'localhost'
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = False
# EMAIL_PORT = 25
# EMAIL_SSL_CERTFILE = None
# EMAIL_SSL_KEYFILE = None
# EMAIL_TIMEOUT = None
# ...

# Tip: _development_ SMTP server
# => python -m smtpd -n -c DebuggingServer localhost:1025

# Email address used in case the user doesn't have filled his one.
DEFAULT_USER_EMAIL = ''


# EMAILS [END] #################################################################

# LOGS #########################################################################

LOGGING_FORMATTERS = {
    'verbose': {
        '()': 'creme.utils.loggers.CremeFormatter',
        'format': (
            '[%(asctime)s] %(levelname)-7s (%(modulepath)s:%(lineno)d) %(name)s : %(message)s'
        ),
        'datefmt': '%Y-%m-%d %H:%M:%S',
    },
    'simple': {
        '()': 'creme.utils.loggers.CremeFormatter',
        'format': '[%(asctime)s] %(colored_levelname)s - %(name)s : %(message)s',
        'datefmt': '%Y-%m-%d %H:%M:%S',
        # To customise the palette, the option "palette" can be set to:
        #  - A palette name. Available: 'dark', 'light'
        #  - A palette dictionary (see 'creme.utils.loggers.CremeFormatter.PALETTES')
        #  The default value is "dark".
    },
    'django.server': {
        '()': 'django.utils.log.ServerFormatter',
        'format': '[%(server_time)s] SERVER: %(message)s',
    },
    'django.db.backends': {
        '()': 'creme.utils.loggers.CremeFormatter',
        'format': '[%(asctime)s] QUERY: %(message)s',
        'datefmt': '%Y-%m-%d %H:%M:%S',
    },
}

# This filter removes all logs containing '/static_media/' string (useful when log level is DEBUG)
# LOGGING_FILTERS = {
#     'media': {
#         '()':      'creme.utils.loggers.RegexFilter',
#         'pattern': r'.*(/static_media/).*',
#         'exclude': True,
#     }
# }
LOGGING_FILTERS = {}

LOGGING_CONSOLE_HANDLER = {
    'level': 'WARNING',  # Available levels : DEBUG < INFO < WARNING < ERROR < CRITICAL
    'class': 'logging.StreamHandler',
    'formatter': 'simple',
}

# In order to enable logging into a file you can use the following configuration ;
# it's a improvement of TimedRotatingFileHandler because
#   - it compresses log file each day in order to save some space
#   - the "filename" create the directories in path if they do not exist,
#     & expand the user directory
# See the documentation of the options :
#     https://docs.python.org/3/library/logging.handlers.html#logging.handlers.TimedRotatingFileHandler
# LOGGING_FILE_HANDLER = {
#     'level': 'INFO',
#     '()': 'creme.utils.loggers.CompressedTimedRotatingFileHandler',
#     'formatter': 'verbose',
#     'filename': '~/creme.log', # create a log file in user home directory
#     'interval': 1,
#     'when': 'D',
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
    'disable_existing_loggers': False,
    'formatters': LOGGING_FORMATTERS,
    'filters': LOGGING_FILTERS,
    'handlers': {
        'console': LOGGING_CONSOLE_HANDLER,
        'file':    LOGGING_FILE_HANDLER,
        'django.server': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'django.server',
        },
        'django.db.backends': {
            'level':     'DEBUG',
            'class':     'logging.StreamHandler',
            'formatter': 'django.db.backends',
        },
    },
    'loggers': {
        # The empty key '' means that all logs are redirected to this logger.
        '': LOGGING_DEFAULT_LOGGER,

        # To display the DB queries (beware works only with <settings.DEBUG==True>.
        # 'django.db.backends': {
        #     'level':    'DEBUG',
        #     'handlers': ['django.db.backends'],
        #     'propagate': False,
        # },
        'django.server': {
            'handlers': ['django.server'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Warnings behavior choices (see Python doc):
# "error" "ignore" "always" "default" "module" "once"
warnings.simplefilter('once')

# LOGS [END]####################################################################

# TESTING ######################################################################

TEST_RUNNER = 'creme.creme_core.utils.test.CremeDiscoverRunner'

KARMA = {
    'browsers': ['FirefoxHeadless'],
    'debug': '9333',
    'lang': 'en',
    'config': '.karma.conf.js',
    'coverage': '.coverage-karma',
}

ESLINT = {
    'config': '.eslintrc',
    'ignore': '.eslintignore',
    'output': '.eslint.output.html'
}

# GUI ##########################################################################

# Lines number in common blocks
BLOCK_SIZE = 10

# Maximum number of items in the menu entry "Recent entities"
MAX_LAST_ITEMS = 9

# Used to replace contents which a user is not allowed to see.
HIDDEN_VALUE = '??'

# List-view
PAGE_SIZES = [10, 25, 50, 100, 200]  # Available page sizes  (list of integers)
DEFAULT_PAGE_SIZE_IDX = 1  # Index (0-based, in PAGE_SIZES) of the default size of pages.

# Initial value of the checkbox "Is private?" in the creation forms of
# HeaderFilter (views of list) & EntityFilters.
FILTERS_INITIAL_PRIVATE = False

# Forms
# Add some fields to create Relationships & Properties in all common entities
# creation forms (only for not custom-form).
FORMS_RELATION_FIELDS = True

# When <a> tags are generated in TextFields,
# add an attribute <target="_blank"> if the value is 'True'.
URLIZE_TARGET_BLANK = False

# URL used in the GUI to indicate the repository address
# REPOSITORY = 'https://bitbucket.org/hybird/creme_crm/src/'
REPOSITORY = 'https://github.com/HybirdCorp/creme_crm'
SCM = 'git'  # Other possible values: 'hg'

# GUI [END]#####################################################################

# MEDIA GENERATOR & THEME SETTINGS #############################################
# TODO: use STATIC_URL in future version? (but URL VS URL fragment)
# URL fragment used to be build the URL of static media (see STATIC_ROOT).
# Must start & end with "/".
PRODUCTION_MEDIA_URL = '/static_media/'

# GENERATED_MEDIA_DIR = join(MEDIA_ROOT, 'static')
GLOBAL_MEDIA_DIRS = [join(dirname(__file__), 'static')]

# Available themes. A theme is represented by (theme_dir, theme verbose name)
# First theme is the default one.
THEMES = [
    ('icecream',  _('Ice cream')),
    ('chantilly', _('Chantilly')),
]

CSS_DEFAULT_LISTVIEW = 'left_align'
CSS_NUMBER_LISTVIEW = 'right_align'
CSS_TEXTAREA_LISTVIEW = 'text_area'
CSS_DEFAULT_HEADER_LISTVIEW = 'hd_cl_lv'
CSS_DATE_HEADER_LISTVIEW = 'hd_date_cl_lv'

JQUERY_MIGRATE_MUTE = True

# TODO: create a static/css/creme-minimal.css for login/logout ??
CREME_CORE_CSS = [
    # Name
    'main.css',

    # Content
    'creme_core/css/jquery-css/creme-theme/jquery-ui-1.11.4.custom.css',
    'creme_core/css/jqplot-1.0.8/jquery.jqplot.css',
    'creme_core/css/jquery.gccolor.1.0.3/gccolor.css',
    'creme_core/css/chosen/chosen-0.9.15-unchosen.css',

    'creme_core/css/creme.css',
    'creme_core/css/creme-ui.css',

    'creme_core/css/header_menu.css',
    'creme_core/css/forms.css',
    # 'creme_core/css/blocks.css',  # TODO: remove the files in creme 2.4
    'creme_core/css/bricks.css',
    'creme_core/css/home.css',
    'creme_core/css/my_page.css',
    'creme_core/css/list_view.css',
    'creme_core/css/detail_view.css',
    'creme_core/css/search_results.css',
    'creme_core/css/popover.css',

    'creme_config/css/creme_config.css',
    'creme_config/css/widgets.css',
]

CREME_OPT_CSS = [  # APPS
    ('creme.persons',          'persons/css/persons.css'),

    ('creme.activities',       'activities/css/activities.css'),
    ('creme.activities',       'activities/css/fullcalendar-3.10.2.css'),

    ('creme.billing',          'billing/css/billing.css'),
    ('creme.opportunities',    'opportunities/css/opportunities.css'),
    ('creme.commercial',       'commercial/css/commercial.css'),
    ('creme.emails',           'emails/css/emails.css'),

    ('creme.geolocation',      'geolocation/css/leaflet-1.6.0.css'),
    ('creme.geolocation',      'geolocation/css/geolocation.css'),

    ('creme.polls',            'polls/css/polls.css'),
    ('creme.products',         'products/css/products.css'),
    ('creme.projects',         'projects/css/projects.css'),
    ('creme.reports',          'reports/css/reports.css'),
    ('creme.tickets',          'tickets/css/tickets.css'),
    ('creme.mobile',           'mobile/css/mobile.css'),
    ('creme.cti',              'cti/css/cti.css'),
]

CREME_I18N_JS = [
    'l10n.js',

    {'filter': 'mediagenerator.filters.i18n.I18N'},  # To build the i18n catalog statically.
]

CREME_LIB_JS = [
    'lib.js',

    # To get the media_url() function in JS.
    {'filter': 'mediagenerator.filters.media_url.MediaURL'},

    'creme_core/js/media.js',
    'creme_core/js/jquery/3.x/jquery-3.6.0.js',
    'creme_core/js/jquery/3.x/jquery-migrate-3.3.2.js',
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
    'creme_core/js/jquery/extensions/gccolor-1.0.3.js',
    'creme_core/js/jquery/extensions/jquery.dragtable.js',
    'creme_core/js/jquery/extensions/jquery.form-3.51.js',
    'creme_core/js/jquery/extensions/jquery.debounce.js',
    'creme_core/js/jquery/extensions/chosen.jquery-0.9.15-unchosen.js',
    'creme_core/js/jquery/extensions/jquery.floatthead-2.2.1.js',
    'creme_core/js/lib/momentjs/moment-2.24.0.js',
    'creme_core/js/lib/momentjs/locale/en-us.js',
    'creme_core/js/lib/momentjs/locale/fr-fr.js',
    'creme_core/js/lib/editor/tinymce.3.4.9.js',
    'creme_core/js/lib/Sortable/Sortable.js',
]

CREME_CORE_JS = [
    # Name
    'main.js',

    # jQuery tools
    'creme_core/js/jquery/extensions/jquery.toggle-attr.js',

    # Base tools
    'creme_core/js/lib/fallbacks/object-0.1.js',
    'creme_core/js/lib/fallbacks/array-0.9.js',
    'creme_core/js/lib/fallbacks/string-0.1.js',
    'creme_core/js/lib/fallbacks/console.js',
    'creme_core/js/lib/fallbacks/event-0.1.js',
    'creme_core/js/lib/fallbacks/htmldocument-0.1.js',
    'creme_core/js/lib/generators-0.1.js',
    'creme_core/js/lib/color.js',
    'creme_core/js/lib/assert.js',
    'creme_core/js/lib/faker.js',
    'creme_core/js/lib/browser.js',

    # Legacy tools
    'creme_core/js/creme.js',
    # 'creme_core/js/color.js',
    'creme_core/js/utils.js',
    'creme_core/js/forms.js',
    'creme_core/js/ajax.js',

    'creme_core/js/widgets/base.js',

    'creme_core/js/widgets/component/component.js',
    'creme_core/js/widgets/component/factory.js',
    'creme_core/js/widgets/component/events.js',
    'creme_core/js/widgets/component/action.js',
    'creme_core/js/widgets/component/action-registry.js',
    'creme_core/js/widgets/component/action-link.js',
    'creme_core/js/widgets/component/chosen.js',

    'creme_core/js/widgets/utils/template.js',
    'creme_core/js/widgets/utils/lambda.js',
    'creme_core/js/widgets/utils/converter.js',
    'creme_core/js/widgets/utils/json.js',
    'creme_core/js/widgets/utils/compare.js',
    'creme_core/js/widgets/utils/history.js',
    'creme_core/js/widgets/utils/plugin.js',

    'creme_core/js/widgets/ajax/url.js',
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

    'creme_core/js/widgets/list/pager.js',

    'creme_core/js/widgets/frame.js',
    'creme_core/js/widgets/toggle.js',
    'creme_core/js/widgets/pluginlauncher.js',
    'creme_core/js/widgets/dinput.js',
    'creme_core/js/widgets/autosizedarea.js',
    'creme_core/js/widgets/dselect.js',
    'creme_core/js/widgets/checklistselect.js',
    'creme_core/js/widgets/datetime.js',
    'creme_core/js/widgets/daterange.js',
    'creme_core/js/widgets/daterangeselector.js',
    'creme_core/js/widgets/chainedselect.js',
    'creme_core/js/widgets/selectorlist.js',
    'creme_core/js/widgets/entityselector.js',
    'creme_core/js/widgets/pselect.js',
    'creme_core/js/widgets/actionlist.js',
    'creme_core/js/widgets/plotdata.js',
    'creme_core/js/widgets/plot.js',
    'creme_core/js/widgets/plotselector.js',
    'creme_core/js/widgets/scrollactivator.js',
    'creme_core/js/widgets/container.js',
    'creme_core/js/widgets/editor.js',

    'creme_core/js/menu.js',
    'creme_core/js/search.js',
    'creme_core/js/bricks.js',
    'creme_core/js/bricks-action.js',

    'creme_core/js/list_view.core.js',
    'creme_core/js/lv_widget.js',
    'creme_core/js/detailview.js',

    'creme_core/js/entity_cell.js',
    'creme_core/js/export.js',
    'creme_core/js/merge.js',
    'creme_core/js/relations.js',
    'creme_core/js/jobs.js',
]

CREME_OPTLIB_JS = [
    ('creme.activities', 'activities/js/jquery/extensions/fullcalendar-3.10.2.js'),
    ('creme.geolocation', 'geolocation/js/lib/leaflet-1.6.0.js'),
]

CREME_OPT_JS = [  # OPTIONAL APPS
    ('creme.creme_config',  'creme_config/js/custom-forms-brick.js'),
    ('creme.creme_config',  'creme_config/js/button-menu-editor.js'),
    ('creme.creme_config',  'creme_config/js/menu-brick.js'),
    ('creme.creme_config',  'creme_config/js/menu-editor.js'),
    ('creme.creme_config',  'creme_config/js/bricks-config-editor.js'),
    ('creme.creme_config',  'creme_config/js/settings-menu.js'),

    ('creme.persons',       'persons/js/persons.js'),

    ('creme.activities',    'activities/js/activities.js'),
    ('creme.activities',    'activities/js/activities-calendar.js'),

    ('creme.billing',       'billing/js/billing.js'),
    ('creme.billing',       'billing/js/billing-actions.js'),

    ('creme.opportunities', 'opportunities/js/opportunities.js'),

    ('creme.commercial',    'commercial/js/commercial.js'),

    ('creme.projects',      'projects/js/projects.js'),

    ('creme.reports',       'reports/js/reports.js'),
    ('creme.reports',       'reports/js/reports-actions.js'),

    ('creme.crudity',       'crudity/js/crudity.js'),

    ('creme.emails',        'emails/js/emails.js'),

    ('creme.cti',           'cti/js/cti.js'),

    ('creme.events',        'events/js/events.js'),

    ('creme.geolocation',   'geolocation/js/geolocation.js'),
    ('creme.geolocation',   'geolocation/js/geolocation-google.js'),
    ('creme.geolocation',   'geolocation/js/geolocation-leaflet.js'),
    ('creme.geolocation',   'geolocation/js/brick.js'),
]

TEST_CREME_LIB_JS = [
    # Name
    'testlib.js',

    # Content
    'creme_core/js/tests/qunit/qunit-1.18.0.js',
    'creme_core/js/tests/qunit/qunit-mixin.js',
    'creme_core/js/tests/component/qunit-event-mixin.js',
    'creme_core/js/tests/ajax/qunit-ajax-mixin.js',
    'creme_core/js/tests/dialog/qunit-dialog-mixin.js',
    'creme_core/js/tests/widgets/qunit-widget-mixin.js',
    'creme_core/js/tests/widgets/qunit-plot-mixin.js',
    'creme_core/js/tests/list/qunit-listview-mixin.js',
    'creme_core/js/tests/brick/qunit-brick-mixin.js',
    'creme_core/js/tests/views/qunit-detailview-mixin.js',
]

TEST_CREME_CORE_JS = [
    # Name
    'testcore.js',

    'creme_core/js/tests/jquery/toggle-attr.js',

    # Content
    'creme_core/js/tests/component/component.js',
    'creme_core/js/tests/component/events.js',
    'creme_core/js/tests/component/action.js',
    'creme_core/js/tests/component/actionregistry.js',
    'creme_core/js/tests/component/actionlink.js',
    'creme_core/js/tests/component/chosen.js',

    'creme_core/js/tests/utils/template.js',
    'creme_core/js/tests/utils/lambda.js',
    'creme_core/js/tests/utils/converter.js',
    'creme_core/js/tests/utils/utils.js',
    'creme_core/js/tests/utils/plugin.js',

    'creme_core/js/tests/ajax/mockajax.js',
    'creme_core/js/tests/ajax/cacheajax.js',
    'creme_core/js/tests/ajax/query.js',
    'creme_core/js/tests/ajax/localize.js',
    'creme_core/js/tests/ajax/utils.js',

    'creme_core/js/tests/model/collection.js',
    'creme_core/js/tests/model/renderer-list.js',
    'creme_core/js/tests/model/renderer-choice.js',
    'creme_core/js/tests/model/renderer-checklist.js',
    'creme_core/js/tests/model/query.js',
    'creme_core/js/tests/model/controller.js',

    'creme_core/js/tests/layout/textautosize.js',

    'creme_core/js/tests/dialog/frame.js',
    'creme_core/js/tests/dialog/overlay.js',
    'creme_core/js/tests/dialog/dialog.js',
    'creme_core/js/tests/dialog/dialog-form.js',
    'creme_core/js/tests/dialog/popover.js',
    'creme_core/js/tests/dialog/glasspane.js',

    'creme_core/js/tests/fallbacks.js',
    'creme_core/js/tests/generators.js',
    'creme_core/js/tests/color.js',
    'creme_core/js/tests/assert.js',
    'creme_core/js/tests/faker.js',
    'creme_core/js/tests/browser.js',

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
    'creme_core/js/tests/widgets/entitycells.js',
    'creme_core/js/tests/widgets/editor.js',
    'creme_core/js/tests/widgets/datetimepicker.js',

    'creme_core/js/tests/form/forms.js',

    'creme_core/js/tests/list/list-pager.js',
    'creme_core/js/tests/list/listview-actions.js',
    'creme_core/js/tests/list/listview-header.js',
    'creme_core/js/tests/list/listview-core.js',
    'creme_core/js/tests/list/listview-dialog.js',

    'creme_core/js/tests/brick/brick.js',
    'creme_core/js/tests/brick/brick-actions.js',
    'creme_core/js/tests/brick/brick-menu.js',
    'creme_core/js/tests/brick/brick-table.js',
    'creme_core/js/tests/brick/dependencies.js',

    'creme_core/js/tests/views/detailview-actions.js',
    'creme_core/js/tests/views/hatmenubar.js',
    'creme_core/js/tests/views/jobs.js',
    'creme_core/js/tests/views/menu.js',
    'creme_core/js/tests/views/search.js',
    'creme_core/js/tests/views/utils.js',
]

TEST_CREME_OPT_JS = [
    # ('creme.my_app',       'my_app/js/tests/my_app.js'),
    ('creme.activities',    'activities/js/tests/activities-listview.js'),
    ('creme.activities',    'activities/js/tests/activities-calendar.js'),
    ('creme.billing',       'billing/js/tests/billing.js'),
    ('creme.billing',       'billing/js/tests/billing-actions.js'),
    ('creme.billing',       'billing/js/tests/billing-listview.js'),
    ('creme.commercial',    'commercial/js/tests/commercial-score.js'),
    ('creme.creme_config',  'creme_config/js/tests/brick-config-editor.js'),
    ('creme.creme_config',  'creme_config/js/tests/button-menu-editor.js'),
    ('creme.creme_config',  'creme_config/js/tests/custom-forms-brick.js',),
    ('creme.creme_config',  'creme_config/js/tests/settings-menu.js'),
    ('creme.crudity',       'crudity/js/tests/crudity-actions.js'),
    ('creme.cti',           'cti/js/tests/cti-actions.js'),
    ('creme.emails',        'emails/js/tests/emails-actions.js'),
    ('creme.emails',        'emails/js/tests/emails-listview.js'),
    ('creme.events',        'events/js/tests/events-listview.js'),
    ('creme.geolocation',   'geolocation/js/tests/qunit-geolocation-mixin.js'),
    ('creme.geolocation',   'geolocation/js/tests/geolocation.js'),
    ('creme.geolocation',   'geolocation/js/tests/geolocation-google.js'),
    ('creme.geolocation',   'geolocation/js/tests/persons-brick.js'),
    ('creme.geolocation',   'geolocation/js/tests/addresses-brick.js'),
    ('creme.geolocation',   'geolocation/js/tests/persons-neighborhood-brick.js'),
    ('creme.opportunities', 'opportunities/js/tests/opportunities.js'),
    ('creme.persons',       'persons/js/tests/persons.js'),
    ('creme.persons',       'persons/js/tests/persons-actions.js'),
    ('creme.projects',      'projects/js/tests/projects.js'),
    ('creme.reports',       'reports/js/tests/reports-actions.js'),
    ('creme.reports',       'reports/js/tests/reports-listview.js'),
    ('creme.reports',       'reports/js/tests/reports-chart.js'),
    # ('creme.reports',       'reports/js/tests/reports-filter.js'),
]

# Optional js/css bundles for extending projects.
# Beware to clashes with existing bundles ('main.js', 'l10n.js').
CREME_OPT_MEDIA_BUNDLES = []

ROOT_MEDIA_FILTERS = {
    # NB: Closure produces smaller JS files than RJSMin, but it needs Java 1.4+
    #     to be installed, and the generation is slow.
    #     Comparison of "main.js" sizes (measured during Creme 2.3 beta) :
    #       - concatenated files (no minification):  822.0 Kb
    #       - Closure:                               355.7 Kb
    #       - rJSmin:                                457.5 Kb
    # 'js':  'mediagenerator.filters.closure.Closure',
    'js':  'mediagenerator.filters.rjsmin.RJSMin',

    # NB: CSSCompressor gives a result slightly better than YUICompressor, & it
    #     does not need Java...
    # 'css': 'mediagenerator.filters.yuicompressor.YUICompressor',
    'css': 'mediagenerator.filters.csscompressor.CSSCompressor',
}

YUICOMPRESSOR_PATH = join(
    dirname(__file__), 'static', 'utils', 'yui', 'yuicompressor-2.4.2.jar',
)
CLOSURE_COMPILER_PATH = join(
    dirname(__file__), 'static', 'utils', 'closure', 'closure-compiler-v20200112.jar',
)

COPY_MEDIA_FILETYPES = {
    'gif', 'jpg', 'jpeg', 'png', 'ico', 'cur',  # Images
    'woff', 'ttf', 'eot',  # Fonts
}

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

# PERSONS_MENU_CUSTOMERS_ENABLED = True

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

# Create automatically the default calendar of a user when the user is created ?
#  - True => yes & the default calendar is public.
#  - False => yes & the default calendar is private.
#  - None => no automatic creation (it's created when the user go to the calendar view).
# Note: the command "python manager.py activities_create_default_calendars"
#       creates the "missing" calendars for the existing users.
ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC = True

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

BILLING_EXPORTERS = [
    'creme.billing.exporters.xls.XLSExportEngine',
    'creme.billing.exporters.xhtml2pdf.Xhtml2pdfExportEngine',

    # You needed to install LateX on the server (the command "pdflatex" is run).
    # Some extra packages may be needed to render correctly the themes
    # (see FLAVOURS_INFO in 'creme/billing/exporters/latex.py')
    # 'creme.billing.exporters.latex.LatexExportEngine',

    # Need the package "weasyprint" (pip install weasyprint) (tested with weasyprint == 51).
    # 'creme.billing.exporters.weasyprint.WeasyprintExportEngine',

    # Other possibilities:
    #   https://wkhtmltopdf.org/  => uses Qt WebKit
]

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

CREME_SAMOUSSA_URL = 'http://localhost:8002/'
CREME_SAMOUSSA_USERNAME = ''
CREME_SAMOUSSA_PASSWORD = ''

# CRUDITY -----------------------------------------------------------------------
# EMail parameters to sync external emails in Creme
# email address where to send the emails to sync (used in email templates)
#  eg: creme@cremecrm.org
CREME_GET_EMAIL              = ''
# server URL (eg: pop.cremecrm.org)  -- only pop supported for now.
CREME_GET_EMAIL_SERVER       = ''
CREME_GET_EMAIL_USERNAME     = ''
CREME_GET_EMAIL_PASSWORD     = ''
CREME_GET_EMAIL_PORT         = 110
CREME_GET_EMAIL_SSL          = False  # True or False
# PEM formatted file that contains your private key (only used if CREME_GET_EMAIL_SSL is True).
CREME_GET_EMAIL_SSL_KEYFILE  = ''
# PEM formatted certificate chain file (only used if CREME_GET_EMAIL_SSL is True).
CREME_GET_EMAIL_SSL_CERTFILE = ''

# Path to a readable directory. Used by the fetcher 'filesystem'.
# The contained files are used to create entity
# (eg: the input 'ini' used .ini files) ; used files are deleted.
CRUDITY_FILESYS_FETCHER_DIR = ''

# CRUDITY_BACKENDS configures the backends (it's a list of dict)
# Here a template of a crudity backend configuration:
# CRUDITY_BACKENDS = [
#     {
#         # The name of the fetcher (which is registered with).
#         #  Available choices:
#         #   - 'email' (need the settings CREME_GET_EMAIL* to be filled).
#         #   - 'filesystem' (see CRUDITY_FILESYS_FETCHER_DIR).
#         'fetcher': 'email',
#
#         # The name of the input (which is registered with).
#         #  Available choices:
#         #   - for the fetcher 'email': 'raw', 'infopath' (that needs "lcab" program).
#         #   - for the fetcher 'filesystem': 'ini'.
#         # Can be omitted if 'subject' is '*' (see below).
#         'input': 'infopath',
#
#         # The method of the input to call. Available choices: 'create'
#         #  Can be omitted if 'subject' is '*' (see below).
#         'method': 'create',
#
#         'model': 'activities.activity',    # The targeted model
#         'password': 'meeting',             # Password to be authorized in the input
#
#         # A white list of sender
#         # (Example with an email: if a recipient email's address not in this
#         # drop email, let empty to allow all email addresses).
#         'limit_froms': (),
#
#         # True : Show in sandbox & history, False show only in history
#         #  (/!\ creation will be automatic if False)
#         'in_sandbox': True,
#
#         # Allowed keys format : "key": "default value".
#         'body_map': {
#             'title': '',   #  Keys have to be real field names of the model
#             'user_id': 1,
#         },
#
#         # Target subject
#         # NB: in the subject all spaces will be deleted, and it'll be converted to uppercase.
#         # You can specify * as a fallback (no previous backend handle the data
#         # returned by the fetcher, but be careful your backend must have the
#         # method: 'fetcher_fallback').
#         'subject': 'CREATEACTIVITYIP',
#     },
# ]
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
        'subject': '*',
    },
]

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
# (i.e : when the photo in the vcf file is just an URL)
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
GEOLOCATION_TOWNS = [
    (join(CREME_ROOT, 'geolocation', 'data', 'towns.france.csv.zip'), {'country': 'France'}),
    # For the unit tests a lighter version of the file exists with only the "chef-lieu"
    # (
    #    join(CREME_ROOT, 'geolocation', 'tests', 'data', 'test.towns.france.csv.zip'),
    #    {'country': 'France'}
    # ),
]

# Url for address geolocation search (nominatim is the only supported backend for now)
GEOLOCATION_OSM_NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
# URL pattern for tiles of the geolocation
# {s} − one of the available subdomains
# {z} — zoom level
# {x} and {y} — tile coordinates
# see https://leafletjs.com/reference-1.7.1.html#tilelayer
GEOLOCATION_OSM_TILEMAP_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'

# Copyright link href & title (appears in the bottom-right of the maps)
GEOLOCATION_OSM_COPYRIGHT_URL = 'https://www.openstreetmap.org/copyright'
GEOLOCATION_OSM_COPYRIGHT_TITLE = 'OpenStreetMap contributors'

# APPS CONFIGURATION [END]######################################################

try:
    from .project_settings import *  # NOQA
except ImportError:
    pass
else:
    from . import project_settings as __project_settings

    if any(not symbol.startswith('__') for symbol in dir(__project_settings)):
        warnings.warn(
            "Use of file 'project_settings.py' in creme/ is deprecated ; "
            "use the new project layout <see command 'creme_start_project'>.",
            DeprecationWarning,
        )

try:
    from .local_settings import *  # NOQA
except ImportError:
    pass
else:
    warnings.warn(
        "Use of file 'local_settings.py' in creme/ is deprecated ; "
        "use the new project layout <see command 'creme_start_project'>.",
        DeprecationWarning,
    )

# GENERAL [FINAL SETTINGS]------------------------------------------------------
# TODO: move up this code & remove this whole section in Creme 2.4 when
#       local_settings/project_settings loading has been removed.

# _LOCALE_OVERLOAD = join(CREME_ROOT, 'locale_overload', 'locale')

LOCALE_PATHS = [join(CREME_ROOT, 'locale')]
# if exists(_LOCALE_OVERLOAD):
#     LOCALE_PATHS.insert(0, _LOCALE_OVERLOAD)

INSTALLED_APPS = INSTALLED_DJANGO_APPS + INSTALLED_CREME_APPS
