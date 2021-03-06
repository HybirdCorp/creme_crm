from unittest import skipIf

from .. import get_rgenerator_model, rgenerator_model_is_custom

skip_generator_tests = rgenerator_model_is_custom()

RecurrentGenerator = get_rgenerator_model()
CTYPE_KEY = '0-cform_extra-recurrents_ctype'


def skipIfCustomGenerator(test_func):
    return skipIf(skip_generator_tests, 'Custom generator model in use')(test_func)
