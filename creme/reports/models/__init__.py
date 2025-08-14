from django.conf import settings

from .chart import ReportChart  # NOQA
# from .graph import AbstractReportGraph, ReportGraph  # NOQA
from .report import AbstractReport, Field, Report  # NOQA

if settings.TESTS_ON:
    from creme.reports.tests.fake_models import *  # NOQA

del settings
