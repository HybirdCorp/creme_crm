skip_generator_tests = False

try:
    from unittest import skipIf

    from .. import rgenerator_model_is_custom, get_rgenerator_model

    skip_generator_tests = rgenerator_model_is_custom()

    RecurrentGenerator = get_rgenerator_model()
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


def skipIfCustomGenerator(test_func):
    return skipIf(skip_generator_tests, 'Custom generator model in use')(test_func)
