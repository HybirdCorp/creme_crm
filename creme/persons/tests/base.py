# -*- coding: utf-8 -*-

from unittest import skipIf

from creme import persons
from creme.documents import get_document_model
from creme.documents.tests.base import _DocumentsTestCase

skip_address_tests = persons.address_model_is_custom()
skip_contact_tests = persons.contact_model_is_custom()
skip_organisation_tests = persons.organisation_model_is_custom()

Document = get_document_model()

Address = persons.get_address_model()
Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()


def skipIfCustomAddress(test_func):
    return skipIf(skip_address_tests, 'Custom Address model in use')(test_func)


def skipIfCustomContact(test_func):
    return skipIf(skip_contact_tests, 'Custom Contact model in use')(test_func)


def skipIfCustomOrganisation(test_func):
    return skipIf(skip_organisation_tests, 'Custom Organisation model in use')(test_func)


class _BaseTestCase(_DocumentsTestCase):
    def login(self, is_superuser=True, allowed_apps=('persons',), **kwargs):
        return super().login(is_superuser=is_superuser, allowed_apps=allowed_apps, **kwargs)

    def assertAddressOnlyContentEqual(self, address1, address2):
        self.assertNotEqual(address1.id, address2.id)

        for attr in ['city', 'state', 'zipcode', 'country', 'department', 'content_type']:
            self.assertEqual(getattr(address1, attr), getattr(address2, attr))
