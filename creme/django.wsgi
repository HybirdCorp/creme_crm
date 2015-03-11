import os
from os.path import dirname, abspath
import sys


CREME_ROOT = dirname(abspath(__file__))
sys.path.append(CREME_ROOT)

os.environ['DJANGO_SETTINGS_MODULE'] = 'creme.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
