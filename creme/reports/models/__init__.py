# -*- coding: utf-8 -*-

from django.conf import settings

from .graph import AbstractReportGraph, ReportGraph  # NOQA
from .report import AbstractReport, Field, Report  # NOQA

if settings.TESTS_ON:
    from creme.reports.tests.fake_models import *  # NOQA

del settings
