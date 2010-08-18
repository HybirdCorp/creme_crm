import os
import sys

from os.path import dirname, join, abspath
CREME_ROOT = dirname(abspath(__file__))


sys.path.append(CREME_ROOT)


os.environ['DJANGO_SETTINGS_MODULE'] = 'creme.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
