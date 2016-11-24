# -*- coding: utf-8 -*-

from .report import Field, AbstractReport, Report  # NOQA
from .graph import AbstractReportGraph, ReportGraph  # NOQA


from django.conf import settings
if settings.TESTS_ON:
    from creme.reports.tests.fake_models import *  # NOQA
