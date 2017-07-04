# -*- coding: utf-8 -*-

try:
    import poplib

    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.contrib.contenttypes.models import ContentType
    from django.core.urlresolvers import reverse
    from django.test.utils import override_settings
    from django.utils.translation import ungettext

    from creme.creme_core.core.job import JobManagerQueue  # Should be a test queue
    from creme.creme_core.models import Job, JobResult, FakeContact

    from creme.persons.tests.base import skipIfCustomContact

    from .. import registry
    from ..backends.models import CrudityBackend
    from ..creme_jobs import crudity_synchronize_type
    from ..fetchers.base import CrudityFetcher
    from ..inputs.base import CrudityInput
    # from ..management.commands.crudity_synchronize import Command as SyncCommand
    from ..models import WaitingAction, History
    # from ..registry import FetcherInterface, crudity_registry
    from .base import CrudityTestCase, FakeFetcher, FakeInput  # ContactFakeBackend Contact
    from .fake_crudity_register import Swallow
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


FAKE_CRUDITY_BACKENDS = [{'fetcher':     'swallow',
                          'input':       'swallow',
                          'method':      'create',
                          'model':       'creme_core.fakecontact',
                          'password':    '',
                          'limit_froms': (),
                          'in_sandbox':  True,
                          'body_map':    {},
                          'subject':     'CREATECONTACT',
                         },
                         {'fetcher':     'swallow',
                          'input':       'swallow',
                          'method':      'create',
                          'model':       'creme_core.fakecontact',
                          'password':    '',
                          'limit_froms': (),
                          'in_sandbox':  True,
                          'body_map':    {},
                          'subject':     '*',
                         },
                        ]


class FakePOP3(object):
    instances = []

    def __init__(self, host, port=None, timeout=None):
        self._host = host
        self._port = port
        self._timeout = timeout
        self._user = None
        self._pswd = None

        self._quitted = False

        FakePOP3.instances.append(self)

    def quit(self):
        self._quitted = True
        # TODO: return code

    def user(self, user):
        self._user = user

    def pass_(self, pswd):
        self._pswd = pswd

    def stat(self):
        pass

    def list(self, which=None):
        # response, messages, total_size
        return None, [], 0  # TODO: complete


class FakePOP3_SSL(FakePOP3):
    def __init__(self, host, port=None, keyfile=None, certfile=None):
        # self.host = host
        # self.port = port
        super(FakePOP3_SSL, self).__init__(host=host, port=port)
        self._keyfile = keyfile
        self._certfile = certfile


class CrudityViewsTestCase(CrudityTestCase):
    # _original_fetchers = None
    # _original_backends = None

    _original_POP3 = None
    _original_POP3_SSL = None
    _original_crudity_registry = None

    @classmethod
    def setUpClass(cls):
        # CrudityTestCase.setUpClass()
        super(CrudityViewsTestCase, cls).setUpClass()

        cls._original_POP3 = poplib.POP3
        cls._original_POP3_SSL = poplib.POP3_SSL

        poplib.POP3 = FakePOP3
        poplib.POP3_SSL = FakePOP3_SSL

        cls._original_crudity_registry = registry.crudity_registry

    def setUp(self):
        super(CrudityViewsTestCase, self).setUp()

        registry.crudity_registry = crudity_registry = registry.CRUDityRegistry()
        crudity_registry.autodiscover()

    @classmethod
    def tearDownClass(cls):
        # CrudityTestCase.tearDownClass()
        super(CrudityViewsTestCase, cls).tearDownClass()

        poplib.POP3     = cls._original_POP3
        poplib.POP3_SSL = cls._original_POP3_SSL

        registry.crudity_registry = cls._original_crudity_registry

    def tearDown(self):
        super(CrudityViewsTestCase, self).tearDown()

        # if self._original_fetchers is not None:
        #     crudity_registry._fetchers = self._original_fetchers
        #     crudity_registry._backends = self._original_backends

        FakePOP3.instances[:] = ()

    # def _build_test_registry(self):
    def _build_test_registry(self, backend_configs=None):
        # self._original_fetchers = crudity_registry._fetchers
        # self._original_backends = crudity_registry._backends
        #
        # crudity_registry._fetchers = {}
        # crudity_registry._backends = {}
        #
        # crudity_registry.autodiscover()
        # crudity_registry.dispatch()
        registry.crudity_registry.dispatch(backend_configs if backend_configs is not None else
                                           settings.CRUDITY_BACKENDS
                                          )

    # @skipIfCustomContact
    def test_validate01(self):
        self._build_test_registry()

        first_name = 'Haruhi'
        last_name  = 'Suzumiya'

        # subject = 'test_create_contact'
        subject = CrudityBackend.normalize_subject('test_create_contact')
        wa = WaitingAction()
        # wa.ct = ContentType.objects.get_for_model(Contact)
        wa.ct = ContentType.objects.get_for_model(FakeContact)
        wa.data = wa.set_data({'first_name': first_name,
                               'last_name':  last_name,
                               'user_id':    self.user.id,
                              })
        wa.subject = subject
        wa.source = 'test_f - test_i'
        wa.save()

        crudity_input = FakeInput()
        crudity_input.name = 'test_i'
        crudity_input.method = 'create'

        fetcher = registry.FetcherInterface([FakeFetcher()])
        fetcher.add_inputs(crudity_input)

        # backend = ContactFakeBackend({'subject': subject})
        backend = self.FakeContactBackend({'subject': subject})
        crudity_input.add_backend(backend)

        crudity_registry = registry.crudity_registry
        crudity_registry.register_fetchers('test_f', [fetcher])
        crudity_registry.register_inputs('test_f', [crudity_input])
        crudity_registry.register_backends([backend])

        # self.assertTrue(crudity_registry.get_configured_backend(subject))
        retrieved_be = crudity_registry.get_configured_backend('test_f', 'test_i', subject)
        self.assertEqual(backend, retrieved_be)

        # c_count = Contact.objects.count()
        c_count = FakeContact.objects.count()
        self.assertEqual(1, WaitingAction.objects.count())
        self.assertEqual(0, History.objects.count())

        # self.assertPOST200('/crudity/waiting_actions/validate', data={'ids': [wa.id]})
        self.assertPOST200(reverse('crudity__validate_actions'), data={'ids': [wa.id]})
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(1, History.objects.count())
        # self.assertEqual(c_count + 1, Contact.objects.count())
        self.assertEqual(c_count + 1, FakeContact.objects.count())

        # contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        contact = self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)
        self.assertEqual(self.user, contact.user)

    # @skipIfCustomContact
    def test_download_email_template(self):
        self._build_test_registry()

        subject = 'create_contact'
        # url = '/crudity/download_email_template/%s' % subject
        url = reverse('crudity__dl_email_template', args=(subject,))
        self.assertGET404(url)  # No backend

        crudity_input = FakeInput()
        crudity_input.name = 'raw'
        crudity_input.method = 'create'

        fetcher = registry.FetcherInterface([FakeFetcher()])
        fetcher.add_inputs(crudity_input)

        # backend = ContactFakeBackend({'subject': subject})
        backend = self.FakeContactBackend({'subject': subject})
        crudity_input.add_backend(backend)

        crudity_registry = registry.crudity_registry
        crudity_registry.register_fetchers('email', [fetcher])
        crudity_registry.register_inputs('email', [crudity_input])
        crudity_registry.register_backends([backend])

        response = self.assertGET200(url)
        self.assertEqual('attachment; filename=CREATE_CONTACT.eml',
                         response['Content-Disposition']
                        )
        self.assertEqual('application/vnd.sealed.eml', response['Content-Type'])
        self.assertContains(response, 'Subject: CREATE_CONTACT')
        self.assertTemplateUsed(response, 'crudity/create_email_template.html')

    def test_history(self):
        # response = self.assertGET200('/crudity/history')
        response = self.assertGET200(reverse('crudity__history'))
        self.assertTemplateUsed(response, 'crudity/history.html')
        # TODO: complete

    # def test_history_reload(self): TODO

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
                                        ],
                       CREME_GET_EMAIL_SSL=True,
                       CREME_GET_EMAIL_SERVER='pop.test.org',
                       CREME_GET_EMAIL_PORT=123,
                       CREME_GET_EMAIL_SSL_KEYFILE='key.pem',
                       CREME_GET_EMAIL_SSL_CERTFILE='cert.pem',
                       CREME_GET_EMAIL_USERNAME='William',
                       CREME_GET_EMAIL_PASSWORD='p4$$w0rD',
                      )
    def test_actions_fetch01(self):
        # crudity_registry.autodiscover()
        # crudity_registry.dispatch()
        self._build_test_registry()
        # response = self.assertGET200('/crudity/waiting_actions')
        response = self.assertGET200(reverse('crudity__actions'))
        self.assertTemplateUsed(response, 'emails/templatetags/block_synchronization.html')
        self.assertTemplateUsed(response, 'emails/templatetags/block_synchronization_spam.html')

        pop_instances = FakePOP3.instances
        self.assertEqual(1, len(pop_instances))

        pop_instance = pop_instances[0]
        self.assertIsInstance(pop_instance, FakePOP3_SSL)  # Because CREME_GET_EMAIL_SSL=True
        self.assertEqual('pop.test.org', pop_instance._host)
        self.assertEqual(123,            pop_instance._port)
        self.assertEqual('key.pem',      pop_instance._keyfile)
        self.assertEqual('cert.pem',     pop_instance._certfile)
        self.assertEqual('William',      pop_instance._user)
        self.assertEqual('p4$$w0rD',     pop_instance._pswd)
        self.assertTrue(pop_instance._quitted)

        # TODO: complete (FakePOP3.list() => not empty)

    # @override_settings(CRUDITY_BACKENDS=[{'fetcher':    'swallow',
    #                                       'input':      'swallow',
    #                                       'method':     'create',
    #                                       'model':      'persons.contact',
    #                                       'password':    '',
    #                                       'limit_froms': (),
    #                                       'in_sandbox':  True,
    #                                       'body_map':    {},
    #                                       'subject':     'CREATECONTACT',
    #                                      },
    #                                     ],
    #                   )
    # def _aux_test_actions_fetch(self, func):
    #     original_fetchers = crudity_registry._fetchers
    #     self.assertIsInstance(original_fetchers, dict)
    #     self.assertTrue(original_fetchers)
    #
    #     original_backends = crudity_registry._backends
    #     self.assertIsInstance(original_backends, dict)
    #     self.assertTrue(original_backends)
    #
    #     last_name = 'Ayanami'
    #
    #     class Swallow(object):
    #         def __init__(self, title, content):
    #             self.title = title
    #             self.content = content
    #
    #     class SwallowFetcher(CrudityFetcher):
    #         def fetch(self, *args, **kwargs):
    #             return [Swallow('create contact', 'last_name=%s' % last_name)]
    #
    #     mock_fetcher = SwallowFetcher()
    #
    #     class SwallowInput(CrudityInput):
    #         name = 'swallow'
    #         method = 'create'
    #
    #         def create(this, swallow):
    #             self.assertIsInstance(swallow, Swallow)
    #             self.assertEqual(1, len(this.get_backends()))
    #
    #             backend = this.get_backend(CrudityBackend.normalize_subject(swallow.title))
    #             self.assertIsNotNone(backend)
    #
    #             data = {'user_id': self.user.id}
    #             # data = {'user': self.user} TODO
    #
    #             for line in swallow.content.split('\n'):
    #                 attr, value = line.split('=', 1)
    #                 data[attr] = value
    #
    #             created, instance = backend._create_instance_n_history(data, source='Swallow mail')
    #             self.assertTrue(created)
    #             self.assertIsInstance(instance, Contact)
    #             self.assertEqual(last_name, instance.last_name)
    #             self.assertIsNotNone(instance.pk)
    #
    #             return True
    #
    #     mock_input = SwallowInput()
    #
    #     crudity_registry._fetchers = {}
    #     crudity_registry.register_fetchers('swallow', [mock_fetcher])
    #     crudity_registry.register_inputs('swallow', [mock_input])
    #
    #     crudity_registry.dispatch()
    #
    #     try:
    #         result = func()
    #     finally:
    #         # todo: crappy hack
    #         crudity_registry._fetchers = original_fetchers
    #         crudity_registry._backends = original_backends
    #
    #     return result

    # @skipIfCustomContact
    @override_settings(CRUDITY_BACKENDS=FAKE_CRUDITY_BACKENDS)
    def test_actions_fetch02(self):
        # response = self._aux_test_actions_fetch(lambda: self.client.get('/crudity/waiting_actions'))
        # self.assertEqual(200, response.status_code)
        # self.assertGET200('/crudity/waiting_actions')
        self.assertGET200(reverse('crudity__actions'))
        # TODO: complete

    # @override_settings(CRUDITY_BACKENDS=FAKE_CRUDITY_BACKENDS)
    def test_actions_fetch03(self):
        "Test Job"
        # self._aux_test_actions_fetch(lambda: SyncCommand().execute(verbosity=0))
        user = self.user

        SwallowFetcher = self.SwallowFetcher
        SwallowFetcher.user_id = user.id
        last_name = SwallowFetcher.last_name = 'Ayanami'

        self.assertFalse(FakeContact.objects.filter(last_name=last_name))

        queue = JobManagerQueue.get_main_queue()
        queue.clear()

        job = self.get_object_or_fail(Job, type_id=crudity_synchronize_type.id)
        self.assertIsNone(job.user)
        self.assertEqual(0, job.reference_run.minute)
        self.assertEqual(0, job.reference_run.second)

        self.assertEqual([], queue.started_jobs)
        self.assertEqual([], queue.refreshed_jobs)

        # self._aux_test_actions_fetch(lambda: crudity_synchronize_type.execute(job))
        # self._build_test_registry()
        self._build_test_registry(FAKE_CRUDITY_BACKENDS)
        crudity_synchronize_type.execute(job)

        self.assertGET200(job.get_absolute_url())

        jresults = JobResult.objects.filter(job=job)
        self.assertEqual(1, len(jresults))
        self.assertEqual([ungettext('There is %s change', 'There are %s changes', 1) % 1],
                         jresults[0].messages
                        )

        self.assertEqual([], queue.started_jobs)
        self.assertEqual([], queue.refreshed_jobs)

        self.get_object_or_fail(FakeContact, last_name=last_name)

    # @override_settings(CRUDITY_BACKENDS=FAKE_CRUDITY_BACKENDS)
    def test_actions_fetch04(self):
        "Default backend + job configuration"
        other_user = self.other_user

        queue = JobManagerQueue.get_main_queue()
        queue.clear()

        self.SwallowInput.force_not_handle = True
        # self._build_test_registry()
        self._build_test_registry(FAKE_CRUDITY_BACKENDS)

        # -----------------------------
        job = self.get_object_or_fail(Job, type_id=crudity_synchronize_type.id)
        with self.assertNoException():
            jdata = job.data

        self.assertIsInstance(jdata, dict)
        self.assertEqual(1, len(jdata))

        user_id = jdata.get('user')
        self.assertIsNotNone(user_id)
        self.get_object_or_fail(get_user_model(), id=user_id)

        url = job.get_edit_absolute_url()
        self.assertGET200(url)

        pdict = {'type': 'hours', 'value': 12}
        response = self.client.post(url,
                                    data={'reference_run': '26-06-2016 14:00:00',
                                          'periodicity_0': pdict['type'],
                                          'periodicity_1': str(pdict['value']),

                                          'user': other_user.id,
                                         },
                                   )
        self.assertNoFormError(response)

        job = self.refresh(job)
        self.assertEqual(pdict, job.periodicity.as_dict())
        self.assertEqual(self.create_datetime(year=2016, month=6, day=26, hour=14),
                         job.reference_run
                        )
        self.assertEqual({'user': other_user.id}, job.data)

        # -----------------------------
        crudity_synchronize_type.execute(job)

        jresults = JobResult.objects.filter(job=job)
        self.assertEqual(1, len(jresults))
        self.assertEqual([ungettext('There is %s change', 'There are %s changes', 1) % 1],
                         jresults[0].messages
                        )

        calls_args = self.FakeContactBackend.calls_args
        self.assertEqual(1, len(calls_args))
        call_args = calls_args[0]
        self.assertIsInstance(call_args[0], Swallow)
        self.assertEqual(other_user, call_args[1])

    # def test_actions_delete(self): TODO
    # def test_actions_reload(self): TODO
