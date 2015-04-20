# -*- coding: utf-8 -*-

from django.conf import settings
if settings.TESTS_ON: #TODO: remove this hack with the new test layout
    from .utils import *
    from .models import *
    from .views import *
    from .forms import *
    from .gui import *
    from .templatetags import *
    from .core import *
