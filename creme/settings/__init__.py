from os.path import exists, join

from creme.settings.default import *  # noqa isort:skip
from creme.settings.media import *  # noqa isort:skip
from creme.settings.project import *  # noqa isort:skip

try:
    from creme.settings.local import *  # noqa isort:skip
except ImportError as e:
    print(e)
    pass

_LOCALE_OVERLOAD = join(CREME_ROOT, 'locale_overload', 'locale')  # noqa
LOCALE_PATHS = [join(CREME_ROOT, 'locale')]  # noqa

if exists(_LOCALE_OVERLOAD):
    LOCALE_PATHS.append(_LOCALE_OVERLOAD)

INSTALLED_APPS = INSTALLED_DJANGO_APPS + INSTALLED_CREME_APPS  # noqa
