# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from crudity.models.actions import WaitingAction
    from crudity.models.history import History
    from crudity.registry import FetcherInterface, crudity_registry
    from crudity.tests.base import CrudityTestCase, ContactFakeBackend, FakeFetcher, FakeInput

    from persons.models import Contact
except Exception as e:
    print 'Error:', e


class CrudityViewsTestCase(CrudityTestCase):
    def test_validate01(self):
        subject = "test_create_contact"
        wa = WaitingAction()
        wa.ct = ContentType.objects.get_for_model(Contact)
        wa.data = wa.set_data({'first_name': 'Happy', 'last_name': 'Neko', 'user_id': self.user.id})
        wa.subject = subject
        wa.save()

        fake_fetcher = FakeFetcher()
        fetcher = FetcherInterface([fake_fetcher])
        input = FakeInput()
        input.name = "test"
        input.method = "create"
        fetcher.add_inputs(input)
        backend = ContactFakeBackend({'subject': subject})
        input.add_backend(backend)
        crudity_registry.register_fetchers("test", [fetcher])
        crudity_registry.register_inputs("test", [input])
        crudity_registry.register_backends([backend])

        self.assertTrue(crudity_registry.get_configured_backend(subject))

        c_count = Contact.objects.count()
        self.assertEqual(1, WaitingAction.objects.count())
        self.assertEqual(0, History.objects.count())
        response = self.client.post('/crudity/waiting_actions/validate', data={'ids': [wa.id]})
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(1, History.objects.count())
        self.assertEqual(c_count + 1, Contact.objects.count())

        contact = Contact.objects.all()[c_count]
        self.assertEqual("Happy", contact.first_name)
        self.assertEqual("Neko", contact.last_name)
        self.assertEqual(self.user, contact.user)
