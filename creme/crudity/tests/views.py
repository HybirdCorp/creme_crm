# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from creme.persons.models import Contact

    from ..models import WaitingAction, History
    from ..registry import FetcherInterface, crudity_registry
    from .base import CrudityTestCase, ContactFakeBackend, FakeFetcher, FakeInput
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('CrudityViewsTestCase',)


class CrudityViewsTestCase(CrudityTestCase):
    def test_validate01(self):
        first_name = 'Haruhi'
        last_name  = 'Suzumiya'

        subject = "test_create_contact"
        wa = WaitingAction()
        wa.ct = ContentType.objects.get_for_model(Contact)
        wa.data = wa.set_data({'first_name': first_name,
                               'last_name':  last_name,
                               'user_id':    self.user.id,
                              })
        wa.subject = subject
        wa.save()

        crudity_input = FakeInput()
        crudity_input.name = "test"
        crudity_input.method = "create"

        fetcher = FetcherInterface([FakeFetcher()])
        fetcher.add_inputs(crudity_input)

        backend = ContactFakeBackend({'subject': subject})
        crudity_input.add_backend(backend)
        crudity_registry.register_fetchers("test", [fetcher])
        crudity_registry.register_inputs("test", [crudity_input])
        crudity_registry.register_backends([backend])

        self.assertTrue(crudity_registry.get_configured_backend(subject))

        c_count = Contact.objects.count()
        self.assertEqual(1, WaitingAction.objects.count())
        self.assertEqual(0, History.objects.count())

        self.assertPOST200('/crudity/waiting_actions/validate', data={'ids': [wa.id]})
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(1, History.objects.count())
        self.assertEqual(c_count + 1, Contact.objects.count())

        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertEqual(self.user, contact.user)
