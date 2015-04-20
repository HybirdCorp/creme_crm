# -*- coding: utf-8 -*-

from django.conf import settings
if settings.TESTS_ON: #TODO: remove this hack with the new test layout
    from .report import *
    from .graph import *
    from .utils import *
