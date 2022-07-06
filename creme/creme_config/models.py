from django.conf import settings

if settings.TESTS_ON:
    from creme.creme_config.tests.fake_models import *  # NOQA
