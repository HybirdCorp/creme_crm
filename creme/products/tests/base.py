# -*- coding: utf-8 -*-

skip_product_tests = False
skip_service_tests = False

try:
    from unittest import skipIf

    from creme.creme_core.tests.base import CremeTestCase

    from .. import product_model_is_custom, service_model_is_custom

    skip_product_tests = product_model_is_custom()
    skip_service_tests = service_model_is_custom()
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


def skipIfCustomProduct(test_func):
    return skipIf(skip_product_tests, 'Custom Product model in use')(test_func)


def skipIfCustomService(test_func):
    return skipIf(skip_service_tests, 'Custom Service model in use')(test_func)


class _ProductsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls.populate('products')

    def _cat_field(self, category, sub_category):
        return '{"category": %s, "subcategory": %s}' % (category.id, sub_category.id)
