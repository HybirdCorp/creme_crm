# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType
    from django.test.utils import override_settings

    from creme.persons.models import Contact

    from ..backends.models import CrudityBackend
    from ..fetchers.base import CrudityFetcher
    from ..inputs.base import CrudityInput
    from ..management.commands.crudity_synchronize import Command as SyncCommand
    from ..models import WaitingAction, History
    from ..registry import FetcherInterface, crudity_registry
    from .base import CrudityTestCase, ContactFakeBackend, FakeFetcher, FakeInput
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


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

        #self.assertGET404(url) #no contact related to user

        #user = self.user
        #Contact.objects.create(user=user, is_user=user, first_name='Haruhi',
                               #last_name ='Suzumiya',
                              #)

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

    @override_settings(CRUDITY_BACKENDS=[{'fetcher': 'email',
                                          'input': 'raw',
                                          'method': 'create',
                                          'model': 'emails.entityemail',
                                          'password': '',
                                          'limit_froms': (),
                                          'in_sandbox': True,
                                          'body_map': {},
                                          'subject': '*',
                                         },
                                        ])
    def test_actions_fetch01(self):
        response = self.assertGET200('/crudity/waiting_actions')
        self.assertTemplateUsed(response, 'emails/templatetags/block_synchronization.html')
        self.assertTemplateUsed(response, 'emails/templatetags/block_synchronization_spam.html')

    @override_settings(CRUDITY_BACKENDS=[{'fetcher':    'swallow',
                                          "input":      'swallow',
                                          "method":     'create',
                                          "model":      'persons.contact',
                                          "password":    '',
                                          "limit_froms": (),
                                          "in_sandbox":  True,
                                          "body_map" :   {},
                                          "subject":     'CREATECONTACT',
                                         },
                                        ],
                      )
    def _aux_test_actions_fetch(self, func):
        original_fetchers = crudity_registry._fetchers
        self.assertIsInstance(original_fetchers, dict)
        self.assertTrue(original_fetchers)

        original_backends = crudity_registry._backends
        self.assertIsInstance(original_backends, dict)
        self.assertTrue(original_backends)

        last_name = 'Ayanami'

        class Swallow(object):
            def __init__(self, title, content):
                self.title = title
                self.content = content

        class SwallowFetcher(CrudityFetcher):
            def fetch(self, *args, **kwargs):
                return [Swallow('create contact', 'last_name=%s' % last_name)]

        mock_fetcher = SwallowFetcher()

        class SwallowInput(CrudityInput):
            name = 'swallow'
            method = 'create'

            def create(this, swallow):
                self.assertEqual(1, len(this.get_backends()))

                backend = this.get_backend(CrudityBackend.normalize_subject(swallow.title))
                self.assertIsNotNone(backend)

                data = {'user_id': self.user.id}
                #data = {'user': self.user} TODO

                for line in swallow.content.split('\n'):
                    attr, value = line.split('=', 1)
                    data[attr] = value

                created, instance = backend._create_instance_n_history(data, source="Swallow mail")
                self.assertTrue(created)
                self.assertIsInstance(instance, Contact)
                self.assertEqual(last_name, instance.last_name)
                self.assertIsNotNone(instance.pk)

                return True

        mock_input = SwallowInput()

        crudity_registry._fetchers = {}
        crudity_registry.register_fetchers('swallow', [mock_fetcher])
        crudity_registry.register_inputs('swallow', [mock_input])

        crudity_registry.dispatch()

        try:
            result = func()
        finally:
            #TODO: crappy hack
            crudity_registry._fetchers = original_fetchers
            crudity_registry._backends = original_backends

        return result

    def test_actions_fetch02(self):
        response = self._aux_test_actions_fetch(lambda: self.client.get('/crudity/waiting_actions'))

        self.assertEqual(200, response.status_code)

    def test_actions_fetch03(self):
        self._aux_test_actions_fetch(lambda: SyncCommand().handle(verbosity=0))

    #def test_actions_delete(self): TODO
    #def test_actions_reload(self): TODO
