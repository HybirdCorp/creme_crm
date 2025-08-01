from unittest import skipIf

from creme import persons
from creme.creme_core.tests.base import CremeTestCase
from creme.documents import get_document_model
from creme.documents.tests.base import DocumentsTestCaseMixin

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


class _BaseTestCase(DocumentsTestCaseMixin, CremeTestCase):
    def login_as_persons_user(self, *, allowed_apps=(), **kwargs):
        return super().login_as_standard(allowed_apps=['persons', *allowed_apps], **kwargs)

    def assertAddressOnlyContentEqual(self, address1, address2):
        self.assertNotEqual(address1.id, address2.id)

        for attr in ['city', 'state', 'zipcode', 'country', 'department', 'content_type']:
            self.assertEqual(getattr(address1, attr), getattr(address2, attr))
