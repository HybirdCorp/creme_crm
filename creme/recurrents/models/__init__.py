# -*- coding: utf-8 -*-

from django.conf import settings

from .recurrentgenerator import (  # NOQA
    AbstractRecurrentGenerator,
    RecurrentGenerator,
)

if settings.TESTS_ON:
    from creme.recurrents.tests.fake_models import *  # NOQA

del settings
