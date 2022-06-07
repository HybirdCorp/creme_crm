from django.test import TestCase

from .persons import ContactFactory


class ContactFactoryTestCase(TestCase):
    def test_contact_factory(self):
        contact = ContactFactory()

        self.assertIsNotNone(contact.user)
        self.assertIsNotNone(contact.description)
        self.assertIsNotNone(contact.first_name)
        self.assertIsNotNone(contact.last_name)
        self.assertIsNotNone(contact.skype)
        self.assertIsNotNone(contact.phone)
        self.assertIsNotNone(contact.mobile)
        self.assertIsNotNone(contact.fax)
        self.assertIsNotNone(contact.email)
        self.assertIsNotNone(contact.url_site)
        self.assertIsNotNone(contact.full_position)
        self.assertIsNotNone(contact.birthday)
        self.assertIsNotNone(contact.civility)
        self.assertIsNotNone(contact.position)
        self.assertIsNotNone(contact.sector)

        self.assertIsNone(contact.billing_address)
        self.assertIsNone(contact.shipping_address)

    def test_contact_factory__with_addresses(self):
        contact = ContactFactory(billing_address=True, shipping_address=True)
        contact.refresh_from_db()

        self.assertIsNotNone(contact.billing_address)
        self.assertEqual(contact.billing_address.owner, contact)

        self.assertIsNotNone(contact.shipping_address)
        self.assertEqual(contact.shipping_address.owner, contact)
