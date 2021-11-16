import os
from os.path import dirname, abspath
import sys
import warnings

warnings.warn(
    'The file "creme/django.wsgi" is deprecated ; '
    'you should use the file "wsgi.py" in your project folder instead.',
    DeprecationWarning,
)

CREME_ROOT = dirname(abspath(__file__))
sys.path.append(CREME_ROOT)

os.environ['DJANGO_SETTINGS_MODULE'] = 'creme.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
