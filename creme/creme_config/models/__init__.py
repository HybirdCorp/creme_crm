from django.conf import settings

from .admin_history import AdminHistoryLine  # NOQA

if settings.TESTS_ON:
    from creme.creme_config.tests.fake_models import *  # NOQA
