# -*- coding: utf-8 -*-

skip_address_tests = False
skip_contact_tests = False
skip_organisation_tests = False

try:
    from unittest import skipIf

    from creme.creme_core.tests.base import CremeTestCase

    from .. import address_model_is_custom, contact_model_is_custom, organisation_model_is_custom

    skip_address_tests = address_model_is_custom()
    skip_contact_tests = contact_model_is_custom()
    skip_organisation_tests = organisation_model_is_custom()
except Exception as e:
     print('Error in <%s>: %s' % (__name__, e))


def skipIfCustomAddress(test_func):
    return skipIf(skip_address_tests, 'Custom Address model in use')(test_func)

def skipIfCustomContact(test_func):
    return skipIf(skip_contact_tests, 'Custom Contact model in use')(test_func)

def skipIfCustomOrganisation(test_func):
    return skipIf(skip_organisation_tests, 'Custom Organisation model in use')(test_func)


class _BaseTestCase(CremeTestCase):
    def login(self, is_superuser=True, **kwargs):
        return super(_BaseTestCase, self).login(is_superuser, allowed_apps=['persons'], **kwargs)

    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls.populate('creme_core', 'persons')
        #cls.autodiscover()

    def assertAddressOnlyContentEqual(self, address1, address2):
        self.assertNotEqual(address1.id, address2.id)

        for attr in ['city', 'state', 'zipcode', 'country', 'department', 'content_type']:
            self.assertEqual(getattr(address1, attr), getattr(address2, attr))
