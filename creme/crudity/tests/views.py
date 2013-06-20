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

    def test_download_email_template(self):
        subject = 'create_contact'
        url = '/crudity/download_email_template/%s' % subject
        self.assertGET404(url) #no backend

        crudity_input = FakeInput()
        crudity_input.name = "raw"
        crudity_input.method = "create"

        #TODO: clean crudity_registry ??
        fetcher = FetcherInterface([FakeFetcher()])
        fetcher.add_inputs(crudity_input)

        backend = ContactFakeBackend({'subject': subject})
        crudity_input.add_backend(backend)
        crudity_registry.register_fetchers("email", [fetcher])
        crudity_registry.register_inputs("email", [crudity_input])
        crudity_registry.register_backends([backend])

        self.assertGET404(url) #no contact related to user

        user = self.user
        Contact.objects.create(user=user, is_user=user, first_name='Haruhi',
                               last_name ='Suzumiya',
                              )

        response = self.assertGET200(url)
        self.assertEqual('attachment; filename=CREATE_CONTACT.eml',
                         response['Content-Disposition']
                        )
        self.assertEqual('application/vnd.sealed.eml', response['Content-Type'])
        self.assertContains(response, 'Subject: CREATE_CONTACT')
        self.assertTemplateUsed(response, 'crudity/create_email_template.html')

    def test_history(self):
        response = self.assertGET200('/crudity/history')
        self.assertTemplateUsed(response, 'crudity/history.html')
        #TODO: complete

    #def test_history_reload(self): TODO

    def test_actions_fetch(self): #TODO: test with data
        response = self.assertGET200('/crudity/waiting_actions')
        self.assertTemplateUsed(response, 'emails/templatetags/block_synchronization.html')
        self.assertTemplateUsed(response, 'emails/templatetags/block_synchronization_spam.html')

    #def test_actions_delete(self): TODO
    #def test_actions_reload(self): TODO
