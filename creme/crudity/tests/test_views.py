from __future__ import annotations

import configparser
import io
import poplib

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

# Should be a test queue
from creme.creme_core.core.job import get_queue
from creme.creme_core.models import FakeContact, FakeImage, Job, JobResult
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from .. import registry
from ..backends.models import CrudityBackend
from ..bricks import CrudityHistoryBrick
from ..creme_jobs import crudity_synchronize_type
from ..models import History, WaitingAction
from ..views.actions import RegistryMixin
from .base import CrudityTestCase, FakeFetcher, FakeInput
from .fake_crudity_register import Swallow

FAKE_CRUDITY_BACKENDS = [
    {
        'fetcher':     'swallow',
        'input':       'swallow',
        'method':      'create',
        'model':       'creme_core.fakecontact',
        'password':    '',
        'limit_froms': (),
        'in_sandbox':  True,
        'body_map':    {},
        'subject':     'CREATECONTACT',
    },
    {
        'fetcher':     'swallow',
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


class FakePOP3:
    instances: list[FakePOP3] = []

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
        super().__init__(host=host, port=port)
        self._keyfile = keyfile
        self._certfile = certfile


class CrudityViewsTestCase(BrickTestCaseMixin, CrudityTestCase):
    _original_POP3 = None
    _original_POP3_SSL = None
    _original_crudity_registry = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._original_POP3 = poplib.POP3
        cls._original_POP3_SSL = poplib.POP3_SSL

        poplib.POP3 = FakePOP3
        poplib.POP3_SSL = FakePOP3_SSL

        cls._original_crudity_registry = registry.crudity_registry

    def setUp(self):
        super().setUp()

        crudity_registry = registry.CRUDityRegistry()
        crudity_registry.autodiscover()

        # TODO: remove <registry.crudity_registry = ...> when
        #       download_ini_template() is class-based
        #       (& set its "crudity_registry" attr of course)
        self.registry = \
            registry.crudity_registry = \
            RegistryMixin.crudity_registry = \
            crudity_synchronize_type.crudity_registry = \
            crudity_registry

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        poplib.POP3     = cls._original_POP3
        poplib.POP3_SSL = cls._original_POP3_SSL

        registry.crudity_registry = \
            RegistryMixin.crudity_registry = \
            crudity_synchronize_type.crudity_registry = \
            cls._original_crudity_registry

    def tearDown(self):
        super().tearDown()

        FakePOP3.instances.clear()

    def _build_test_registry(self, backend_configs=None):
        self.registry.dispatch(
            backend_configs
            if backend_configs is not None else
            settings.CRUDITY_BACKENDS
        )

    def test_validate(self):
        user = self.login_as_root_and_get()
        self._build_test_registry()

        first_name = 'Haruhi'
        last_name  = 'Suzumiya'

        subject = CrudityBackend.normalize_subject('test_create_contact')
        wa = WaitingAction()
        wa.ct = ContentType.objects.get_for_model(FakeContact)
        wa.data = {
            'first_name': first_name,
            'last_name':  last_name,
            'user_id':    user.id,
        }
        wa.subject = subject
        wa.source = 'test_f - test_i'
        wa.save()

        crudity_input = FakeInput()
        crudity_input.name = 'test_i'
        crudity_input.method = 'create'

        fetcher = registry.FetcherInterface([FakeFetcher()])
        fetcher.add_inputs(crudity_input)

        backend = self.FakeContactBackend({'subject': subject})
        crudity_input.add_backend(backend)

        crudity_registry = self.registry
        crudity_registry.register_fetchers('test_f', [fetcher])
        crudity_registry.register_inputs('test_f', [crudity_input])
        crudity_registry.register_backends([backend])

        retrieved_be = crudity_registry.get_configured_backend('test_f', 'test_i', subject)
        self.assertEqual(backend, retrieved_be)

        c_count = FakeContact.objects.count()
        self.assertEqual(1, WaitingAction.objects.count())
        self.assertEqual(0, History.objects.count())

        url = reverse('crudity__validate_actions')
        data = {'ids': [wa.id]}
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data)
        self.assertEqual(0, WaitingAction.objects.count())
        self.assertEqual(1, History.objects.count())
        self.assertEqual(c_count + 1, FakeContact.objects.count())

        contact = self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)
        self.assertEqual(user, contact.user)

    def test_delete01(self):
        user = self.login_as_standard(allowed_apps=['crudity'])
        subject = CrudityBackend.normalize_subject('test_create_contact')

        def create_action(first_name, last_name):
            return WaitingAction.objects.create(
                ct=FakeContact,
                data={
                    'first_name': first_name,
                    'last_name': last_name,
                    'user_id':   user.id,
                },
                subject=subject,
                source='test_f - test_i',
            )

        wa1 = create_action(first_name='Haruhi',  last_name='Suzumiya')
        wa2 = create_action(first_name='Yuki',    last_name='Nagato')
        wa3 = create_action(first_name=' Mikuru', last_name='Asahina')

        url = reverse('crudity__delete_actions')
        data = {'ids': [wa1.id, wa3.id]}
        self.assertGET405(url, data=data)

        response = self.assertPOST200(url, data=data)
        self.assertDoesNotExist(wa1)
        self.assertDoesNotExist(wa3)
        self.assertStillExists(wa2)

        self.assertEqual(
            _('Operation successfully completed'),
            # response.content.decode()
            response.text,
        )

    def test_delete02(self):
        "Not allowed."
        user = self.login_as_standard(allowed_apps=['crudity'])
        subject = CrudityBackend.normalize_subject('test_create_contact')

        def create_action(first_name, last_name, owner):
            return WaitingAction.objects.create(
                ct=FakeContact,
                data={
                    'first_name': first_name,
                    'last_name': last_name,
                    'user_id':   user.id,
                },
                subject=subject,
                source='test_f - test_i',
                user=owner,
            )

        wa1 = create_action(first_name='Haruhi', last_name='Suzumiya', owner=user)
        wa2 = create_action(first_name='Yuki', last_name='Nagato',     owner=self.get_root_user())

        url = reverse('crudity__delete_actions')
        data = {'ids': [wa1.id, wa2.id]}
        self.assertGET405(url, data=data)

        response = self.assertPOST(400, url, data=data)
        self.assertDoesNotExist(wa1)
        self.assertStillExists(wa2)

        self.assertEqual(
            _('You are not allowed to validate/delete the waiting action <{}>').format(wa2.id),
            # response.content.decode()
            response.text,
        )

    def test_delete03(self):
        "Errors."
        self.login_as_root()
        url = reverse('crudity__delete_actions')
        self.assertPOST404(url, data={'ids': [1235]})
        self.assertPOST(400, url, data={'ids': ['notanint']})
        self.assertPOST(400, url, data={'ids': []})

    def test_download_email_template(self):
        self.login_as_root()
        self._build_test_registry()

        subject = 'create_contact'
        url = reverse('crudity__dl_email_template', args=(subject,))
        self.assertGET404(url)  # No backend

        crudity_input = FakeInput()
        crudity_input.name = 'raw'
        crudity_input.method = 'create'

        fetcher = registry.FetcherInterface([FakeFetcher()])
        fetcher.add_inputs(crudity_input)

        backend = self.FakeContactBackend({'subject': subject})
        crudity_input.add_backend(backend)

        crudity_registry = registry.crudity_registry
        crudity_registry.register_fetchers('email', [fetcher])
        crudity_registry.register_inputs('email', [crudity_input])
        crudity_registry.register_backends([backend])

        response = self.assertGET200(url)
        self.assertEqual(
            'attachment; filename="CREATE_CONTACT.eml"',
            response['Content-Disposition']
        )
        self.assertEqual('application/vnd.sealed.eml', response['Content-Type'])
        self.assertContains(response, 'Subject: CREATE_CONTACT')
        self.assertTemplateUsed(response, 'crudity/create_email_template.html')

    def test_download_ini_template01(self):
        "Error."
        self.login_as_root()
        self._build_test_registry(FAKE_CRUDITY_BACKENDS)

        # No backend
        self.assertGET404(reverse('crudity__dl_fs_ini_template', args=('INVALID',)))

        # Backend with bad type
        self.assertGET404(reverse('crudity__dl_fs_ini_template', args=('CREATECONTACT',)))

    def test_download_ini_template02(self):
        self.login_as_root()
        subject = 'CREATE_CONTACT'
        last_name = 'Suzumiya'
        description = 'The best waifu\nis here'

        self._build_test_registry([{
            'fetcher':     'filesystem',
            'input':       'ini',
            'method':      'create',
            'model':       'creme_core.fakecontact',
            'password':    '',
            'limit_froms': (),
            'in_sandbox':  True,
            'body_map':    {
                'user_id':     1,
                'first_name':  '',
                'last_name':   last_name,
                'description': description,
            },
            'subject':     subject,
        }])

        response = self.assertGET200(reverse('crudity__dl_fs_ini_template', args=(subject,)))
        self.assertEqual(
            f'attachment; filename="{subject}.ini"',
            response['Content-Disposition']
        )
        self.assertEqual('text/plain', response['Content-Type'])

        config = configparser.RawConfigParser()

        with self.assertNoException():
            # config.read_file(io.StringIO(response.content.decode()))
            config.read_file(io.StringIO(response.text))

        with self.assertNoException():
            action = config.get('head', 'action')
        self.assertEqual(subject, action)

        with self.assertNoException():
            read_user_id = config.get('body', 'user_id')
        self.assertEqual('1', read_user_id)

        with self.assertNoException():
            read_first_name = config.get('body', 'first_name')
        self.assertEqual('', read_first_name)

        with self.assertNoException():
            read_last_name = config.get('body', 'last_name')
        self.assertEqual(last_name, read_last_name)

        with self.assertRaises(configparser.NoOptionError):
            config.get('body', 'sector')

        with self.assertNoException():
            read_desc = config.get('body', 'description')
        self.assertEqual(description, read_desc)

    def test_download_ini_template03(self):
        "Sandbox per user."
        user = self.login_as_root_and_get()
        self._set_sandbox_by_user()

        subject = 'CREATE_CONTACT'
        self._build_test_registry([{
            'fetcher':     'filesystem',
            'input':       'ini',
            'method':      'create',
            'model':       'creme_core.fakecontact',
            'password':    '',
            'limit_froms': (),
            'in_sandbox':  True,
            'body_map':    {
                'user_id':     1,
                'last_name':   '',
            },
            'subject':     subject,
        }])

        response = self.assertGET200(
            reverse('crudity__dl_fs_ini_template', args=(subject,)),
        )
        config = configparser.RawConfigParser()

        with self.assertNoException():
            # config.read_file(io.StringIO(response.content.decode()))
            config.read_file(io.StringIO(response.text))

        with self.assertNoException():
            username = config.get('head', 'username')
        self.assertEqual(user.username, username)

    def test_history(self):
        self.login_as_root()

        response = self.assertGET200(reverse('crudity__history'))
        self.assertTemplateUsed(response, 'crudity/history.html')

        context = response.context
        self.assertEqual(
            reverse('crudity__reload_history_bricks'),
            context.get('bricks_reload_url')
        )

        with self.assertNoException():
            # bricks = [*context['bricks']]
            bricks = [*context['bricks']['main']]

        self.assertTrue(bricks)
        models = set()

        for brick in bricks:
            self.assertIsInstance(brick, CrudityHistoryBrick)
            models.add(brick.ct.model_class())

        self.assertIn(FakeContact, models)
        self.assertNotIn(FakeImage, models)

    def test_history_reload01(self):
        self.login_as_root()

        ct = ContentType.objects.get_for_model(FakeContact)
        # brick_id = f'block_crudity-{ct.id}'
        brick_id = f'regular-crudity-{ct.id}'
        response = self.assertGET200(
            reverse('crudity__reload_history_bricks'),
            data={'brick_id': brick_id},
        )

        reload_data = response.json()

        self.assertEqual(reload_data[0][0], brick_id)

        l_document = self.get_html_tree(reload_data[0][1])
        self.get_brick_node(l_document, brick_id)
        # TODO: complete ?

    def test_history_reload02(self):
        self.login_as_root()

        ct = ContentType.objects.get_for_model(FakeImage)
        self.assertGET200(
            reverse('crudity__reload_history_bricks'),
            # data={'brick_id': f'block_crudity-{ct.id}'},
            data={'brick_id': f'regular-crudity-{ct.id}'},
        )

    @override_settings(
        CRUDITY_BACKENDS=[{
            'fetcher': 'email',
            'input': 'raw',
            # 'input': '',
            'method': 'create',
            # 'model': 'emails.entityemail',
            'model': 'creme_core.fakecontact',
            'password': '',
            'limit_froms': (),
            'in_sandbox': True,
            # 'body_map': {},
            'body_map': {'user_id': 1},
            # 'subject': '*',
            'subject': 'CONTACT_CREATE',
        }],
        CREME_GET_EMAIL_SSL=True,
        CREME_GET_EMAIL_SERVER='pop.test.org',
        CREME_GET_EMAIL_PORT=123,
        CREME_GET_EMAIL_SSL_KEYFILE='key.pem',
        CREME_GET_EMAIL_SSL_CERTFILE='cert.pem',
        CREME_GET_EMAIL_USERNAME='William',
        CREME_GET_EMAIL_PASSWORD='p4$$w0rD',
    )
    def test_actions_portal01(self):
        self.login_as_root()
        self._build_test_registry()

        response = self.assertGET200(reverse('crudity__actions'))
        self.assertTemplateUsed(
            response, 'crudity/bricks/header-actions/email-creation-template.html'
        )

        get = response.context.get
        self.assertEqual(reverse('crudity__reload_actions_bricks'), get('bricks_reload_url'))
        # self.assertIsList(get('bricks'))
        self.assertIsDict(get('bricks'), length=1)  # TODO: improve

        self.assertFalse(FakePOP3.instances)

    def test_actions_portal02(self):
        self.login_as_root()

        self._build_test_registry(FAKE_CRUDITY_BACKENDS)
        response = self.assertGET200(reverse('crudity__actions'))

        # brick_id = 'block_crudity-waiting_actions-swallow|swallow|CREATECONTACT'
        brick_id = 'regular-crudity-waiting_actions-swallow|swallow|CREATECONTACT'
        document = self.get_html_tree(response.content)
        self.get_brick_node(document, brick_id)
        # TODO: complete

    def test_actions_reload(self):
        self.login_as_root()

        self._build_test_registry(FAKE_CRUDITY_BACKENDS)
        # brick_id = 'block_crudity-waiting_actions-swallow|swallow|CREATECONTACT'
        brick_id = 'regular-crudity-waiting_actions-swallow|swallow|CREATECONTACT'
        response = self.assertGET200(
            reverse('crudity__reload_actions_bricks'),
            data={'brick_id': brick_id},
        )

        reload_data = response.json()

        self.assertEqual(reload_data[0][0], brick_id)

        l_document = self.get_html_tree(reload_data[0][1])
        self.get_brick_node(l_document, brick_id)
        # TODO: complete

    @override_settings(
        CRUDITY_BACKENDS=[{
            'fetcher':     'email',
            'input': 'raw',
            'method':      'create',
            'model':       'creme_core.fakecontact',
            'password':    '',
            'limit_froms': (),
            'in_sandbox':  True,
            'body_map': {'user_id': 1},
            'subject':     'CREATE_CONTACT',
        }],
        CREME_GET_EMAIL_SSL=True,
        CREME_GET_EMAIL_SERVER='pop.test.org',
        CREME_GET_EMAIL_PORT=123,
        CREME_GET_EMAIL_SSL_KEYFILE='key.pem',
        CREME_GET_EMAIL_SSL_CERTFILE='cert.pem',
        CREME_GET_EMAIL_USERNAME='William',
        CREME_GET_EMAIL_PASSWORD='p4$$w0rD',
    )
    def test_actions_fetch01(self):
        self.login_as_root()

        self._build_test_registry()
        url = reverse('crudity__refresh_actions')
        self.assertGET405(url)

        response = self.assertPOST200(url)
        ldata = response.json()
        self.assertEqual([], ldata)

        pop_instance = self.get_alone_element(FakePOP3.instances)
        self.assertIsInstance(pop_instance, FakePOP3_SSL)  # Because CREME_GET_EMAIL_SSL=True
        self.assertEqual('pop.test.org', pop_instance._host)
        self.assertEqual(123,            pop_instance._port)
        self.assertEqual('key.pem',      pop_instance._keyfile)
        self.assertEqual('cert.pem',     pop_instance._certfile)
        self.assertEqual('William',      pop_instance._user)
        self.assertEqual('p4$$w0rD',     pop_instance._pswd)
        self.assertTrue(pop_instance._quitted)

        # TODO: complete (FakePOP3.list() => not empty)

    @override_settings(CRUDITY_BACKENDS=FAKE_CRUDITY_BACKENDS)
    def test_actions_fetch02(self):
        "Fetcher without backend are not used + not default backend"
        user = self.login_as_root_and_get()

        self.SwallowFetcher.last_name = last_name = 'Suzumiya'
        self.SwallowFetcher.user_id = user.id

        self._build_test_registry()

        self.assertPOST200(reverse('crudity__refresh_actions'))

        # Pop is not fetched because the fetcher has no configured backend.
        self.assertFalse(FakePOP3.instances)

        self.get_object_or_fail(FakeContact, last_name=last_name)

    def test_job01(self):
        user = self.login_as_root_and_get()

        SwallowFetcher = self.SwallowFetcher
        SwallowFetcher.user_id = user.id
        last_name = SwallowFetcher.last_name = 'Ayanami'

        self.assertFalse(FakeContact.objects.filter(last_name=last_name))

        queue = get_queue()
        queue.clear()

        job = self.get_object_or_fail(Job, type_id=crudity_synchronize_type.id)
        self.assertIsNone(job.user)
        self.assertEqual(0, job.reference_run.minute)
        self.assertEqual(0, job.reference_run.second)

        self.assertEqual([], queue.started_jobs)
        self.assertEqual([], queue.refreshed_jobs)

        self._build_test_registry(FAKE_CRUDITY_BACKENDS)
        crudity_synchronize_type.execute(job)

        self.assertGET200(job.get_absolute_url())

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                ngettext(
                    'There is {count} change',
                    'There are {count} changes',
                    1
                ).format(count=1),
            ],
            jresult.messages,
        )

        self.assertListEqual([], queue.started_jobs)
        self.assertListEqual([], queue.refreshed_jobs)

        self.get_object_or_fail(FakeContact, last_name=last_name)

    def test_job02(self):
        "Default backend + job configuration."
        self.login_as_root()
        # other_user = self.other_user
        other_user = self.create_user()

        queue = get_queue()
        queue.clear()

        self.SwallowInput.force_not_handle = True
        self._build_test_registry(FAKE_CRUDITY_BACKENDS)

        # -----------------------------
        job = self.get_object_or_fail(Job, type_id=crudity_synchronize_type.id)
        with self.assertNoException():
            jdata = job.data

        self.assertIsDict(jdata, length=1)

        user_id = jdata.get('user')
        self.assertIsNotNone(user_id)
        self.get_object_or_fail(get_user_model(), id=user_id)

        url = job.get_edit_absolute_url()
        self.assertGET200(url)

        pdict = {'type': 'hours', 'value': 12}
        response = self.client.post(
            url,
            data={
                'reference_run': self.formfield_value_datetime(
                    year=2016, month=6, day=26, hour=14,
                ),
                'periodicity_0': pdict['type'],
                'periodicity_1': str(pdict['value']),

                'user': other_user.id,
            },
        )
        self.assertNoFormError(response)

        job = self.refresh(job)
        self.assertEqual(pdict, job.periodicity.as_dict())
        self.assertEqual(
            self.create_datetime(year=2016, month=6, day=26, hour=14),
            job.reference_run,
        )
        self.assertDictEqual({'user': other_user.id}, job.data)

        # -----------------------------
        crudity_synchronize_type.execute(job)

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                ngettext(
                    'There is {count} change',
                    'There are {count} changes',
                    1
                ).format(count=1),
            ],
            jresult.messages,
        )

        calls_args = self.FakeContactBackend.calls_args
        self.assertEqual(1, len(calls_args))
        call_args = calls_args[0]
        self.assertIsInstance(call_args[0], Swallow)
        self.assertEqual(other_user, call_args[1])

    # def test_actions_delete(self): TODO
