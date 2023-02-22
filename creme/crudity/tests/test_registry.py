from django.core.exceptions import ImproperlyConfigured

from .. import registry
from .base import CrudityTestCase, FakeFetcher, FakeInput
from .fake_crudity_register import (
    FakeContact,
    FakeContactBackend,
    FakeDocument,
    FakeDocumentBackend,
    FakeOrganisation,
    FakeOrganisationBackend,
)


class CrudityRegistryTestCase(CrudityTestCase):
    def setUp(self):
        super().setUp()
        self.crudity_registry = registry.CRUDityRegistry()  # Ensure the registry is empty

    def test_register_fetchers01(self):
        crudity_registry = self.crudity_registry

        f11 = FakeFetcher()
        f12 = FakeFetcher()
        f21 = FakeFetcher()
        f22 = FakeFetcher()

        crudity_registry.register_fetchers('test1', [f11, f12])
        crudity_registry.register_fetchers('test2', [f21, f22])

        ifetcher1 = crudity_registry.get_fetcher('test1')
        self.assertIsInstance(ifetcher1, registry.FetcherInterface)
        self.assertListEqual([f11, f12], ifetcher1.fetchers)

        ifetcher2 = crudity_registry.get_fetcher('test2')
        self.assertIsInstance(ifetcher2, registry.FetcherInterface)
        self.assertListEqual([f21, f22], ifetcher2.fetchers)

        self.assertCountEqual([ifetcher1, ifetcher2], crudity_registry.get_fetchers())

    def test_register_fetchers02(self):
        crudity_registry = self.crudity_registry

        f1 = FakeFetcher()
        f2 = FakeFetcher()

        crudity_registry.register_fetchers('test', [f1])
        crudity_registry.register_fetchers('test', [f2])

        ifetcher = crudity_registry.get_fetcher('test')
        self.assertIsInstance(ifetcher, registry.FetcherInterface)
        self.assertEqual([f1, f2], ifetcher.fetchers)

    def test_register_backend01(self):
        crudity_registry = self.crudity_registry
        crudity_registry.register_backends([FakeContactBackend, FakeOrganisationBackend])
        crudity_registry.register_backends([FakeDocumentBackend])
        self.assertCountEqual(
            [FakeContact, FakeOrganisation, FakeDocument],
            crudity_registry._backends,
        )

    def test_register_input01(self):
        crudity_registry = self.crudity_registry
        crudity_registry.register_fetchers("test", [FakeFetcher(), FakeFetcher()])

        i1 = FakeInput()
        i1.name = '1'
        i1.method = 'create'
        i2 = FakeInput()
        i2.name = '2'
        i2.method = 'create'

        crudity_registry.register_inputs('test', [i1, i2])

        inputs = []
        for value in crudity_registry.get_fetcher('test')._inputs.values():
            inputs.extend(value.values())

        self.assertSetEqual({i.name for i in inputs}, {i1.name, i2.name})

    def test_dispatch01(self):
        crudity_registry = self.crudity_registry
        crudity_registry.register_fetchers('swallow', [self.SwallowFetcher()])

        class RawSwallowInput(self.SwallowInput):
            name = 'raw_swallow'

        crud_input = RawSwallowInput()
        crudity_registry.register_inputs('swallow', [crud_input])
        crudity_registry.register_backends([FakeContactBackend, FakeOrganisationBackend])

        subject1 = 'CREATECONTACT'
        subject2 = 'CREATE_ORGA'
        crudity_registry.dispatch([
            {
                'fetcher':     'swallow',
                'input':       'raw_swallow',
                'method':      'create',
                'model':       'creme_core.fakecontact',
                'password':    '',
                'limit_froms': (),
                'in_sandbox':  True,
                'body_map':    {},
                'subject':     subject1,
            }, {
                'fetcher':     'swallow',
                'input':       'raw_swallow',
                'method':      'create',
                'model':       'creme_core.fakeorganisation',
                'password':    '',
                'limit_froms': (),
                'in_sandbox':  True,
                'body_map':    {},
                'subject':     subject2,
            },
        ])

        ifetcher = crudity_registry.get_fetcher('swallow')
        self.assertIsNotNone(ifetcher)
        self.assertIsNone(ifetcher.get_default_backend())

        self.assertEqual(crud_input, ifetcher.get_input('raw_swallow', 'create'))
        self.assertEqual(2, len(crud_input._backends))

        backend1 = crud_input.get_backend(subject1)
        self.assertIsInstance(backend1, FakeContactBackend)
        self.assertEqual(subject1,                backend1.subject)
        self.assertEqual('swallow - raw_swallow', backend1.source)

        backend2 = crud_input.get_backend(subject2)
        self.assertIsInstance(backend2, FakeOrganisationBackend)
        self.assertEqual(subject2, backend2.subject)

    def test_dispatch02(self):
        "Errors: missing/erroneous information."
        crudity_registry = self.crudity_registry
        crudity_registry.register_fetchers('swallow', [self.SwallowFetcher()])

        class RawSwallowInput(self.SwallowInput):
            name = 'raw_swallow'

        input1 = RawSwallowInput()
        crudity_registry.register_inputs('swallow', [input1])
        crudity_registry.register_backends([FakeContactBackend, FakeOrganisationBackend])

        with self.assertRaises(ImproperlyConfigured):
            crudity_registry.dispatch([{
                # 'fetcher':     'swallow',
                'input':       'raw_swallow',
                'method':      'create',
                'model':       'creme_core.fakecontact',
                'password':    '',
                'limit_froms': (),
                'in_sandbox':  True,
                'body_map':    {},
                'subject':     'CREATECONTACT',
            }])

        with self.assertRaises(ImproperlyConfigured):
            crudity_registry.dispatch([{
                'fetcher':     'swallow',
                'input':       'raw_swallow',
                'method':      'create',
                # 'model':       'creme_core.fakecontact',
                'password':    '',
                'limit_froms': (),
                'in_sandbox':  True,
                'body_map':    {},
                'subject':     'CREATECONTACT',
            }])

        with self.assertRaises(ImproperlyConfigured):
            crudity_registry.dispatch([{
                'fetcher':     'swallow',
                'input':       'raw_swallow',
                'method':      'create',
                'model':       'creme_core.fakecontact',
                'password':    '',
                'limit_froms': (),
                'in_sandbox':  True,
                'body_map':    {},
                # 'subject':     'CREATECONTACT',
            }])

        with self.assertRaises(ImproperlyConfigured):
            crudity_registry.dispatch([{
                'fetcher':     'swallow',
                'input':       'raw_swallow',
                'method':      'create',
                'model':       'creme_core.fakedocument',  # <= no backend
                'password':    '',
                'limit_froms': (),
                'in_sandbox':  True,
                'body_map':    {},
                'subject':     'CREATECONTACT',
            }])

        with self.assertRaises(ImproperlyConfigured):
            crudity_registry.dispatch([{
                'fetcher':     'swallow',
                # 'input':       'raw_swallow',
                'method':      'create',
                'model':       'creme_core.fakecontact',
                'password':    '',
                'limit_froms': (),
                'in_sandbox':  True,
                'body_map':    {},
                'subject':     'CREATECONTACT',
            }])

        with self.assertRaises(ImproperlyConfigured):
            crudity_registry.dispatch([{
                'fetcher':     'swallow',
                'input':       'raw_swallow',
                'method':      'delete',  # <==
                'model':       'creme_core.fakecontact',
                'password':    '',
                'limit_froms': (),
                'in_sandbox':  True,
                'body_map':    {},
                'subject':     'CREATECONTACT',
            }])

        with self.assertRaises(ImproperlyConfigured):
            crudity_registry.dispatch([{
                'fetcher':     'swallow',
                'input':       'raw_swallow',
                'method':      'create',
                'model':       'creme_core.invalidmodel',  # <==
                'password':    '',
                'limit_froms': (),
                'in_sandbox':  True,
                'body_map':    {},
                'subject':     'CREATECONTACT',
            }])

        with self.assertRaises(ImproperlyConfigured):
            crudity_registry.dispatch([{
                'fetcher':     'invalid_fetcher',  # <==
                'input':       'raw_swallow',
                'method':      'create',
                'model':       'creme_core.fakecontact',
                'password':    '',
                'limit_froms': (),
                'in_sandbox':  True,
                'body_map':    {},
                'subject':     'CREATECONTACT',
            }])

        with self.assertRaises(ImproperlyConfigured):
            crudity_registry.dispatch([{
                'fetcher':     'swallow',
                'input':       'invalid_input',  # <===
                'method':      'create',
                'model':       'creme_core.fakecontact',
                'password':    '',
                'limit_froms': (),
                'in_sandbox':  True,
                'body_map':    {},
                'subject':     'CREATECONTACT',
            }])

    def test_dispatch03(self):
        "Errors: duplicated subject."
        crudity_registry = self.crudity_registry
        crudity_registry.register_fetchers('swallow', [self.SwallowFetcher()])

        class RawSwallowInput(self.SwallowInput):
            name = 'raw_swallow'

        input1 = RawSwallowInput()
        crudity_registry.register_inputs('swallow', [input1])
        crudity_registry.register_backends([FakeContactBackend, FakeOrganisationBackend])

        subject = 'CREATECONTACT'

        with self.assertRaises(ImproperlyConfigured):
            crudity_registry.dispatch([{
                'fetcher':     'swallow',
                'input':       'raw_swallow',
                'method':      'create',
                'model':       'creme_core.fakecontact',
                'password':    '',
                'limit_froms': (),
                'in_sandbox':  True,
                'body_map':    {},
                'subject':     subject,
            }, {
                'fetcher':     'swallow',
                'input':       'raw_swallow',
                'method':      'create',
                'model':       'creme_core.fakeorganisation',
                'password':    '',
                'limit_froms': (),
                'in_sandbox':  True,
                'body_map':    {},
                'subject':     subject,
            }])

    def test_dispatch04(self):
        "Default backend"
        crudity_registry = self.crudity_registry
        crudity_registry.register_fetchers('swallow', [self.SwallowFetcher()])

        crudity_registry.register_backends([FakeContactBackend, FakeOrganisationBackend])

        crudity_registry.dispatch([{
            'fetcher':     'swallow',
            'input':       '',
            'method':      '',
            'model':       'creme_core.fakecontact',
            'password':    '',
            'limit_froms': (),
            'in_sandbox':  True,
            'body_map':    {},
            'subject':     '*',
        }])

        ifetcher = crudity_registry.get_fetcher('swallow')
        self.assertIsNotNone(ifetcher)

        backend = ifetcher.get_default_backend()
        self.assertIsInstance(backend, FakeContactBackend)
        self.assertEqual('swallow', backend.source)

    def test_dispatch05(self):
        "Default backend: no fetcher_fallback() method."
        crudity_registry = self.crudity_registry
        crudity_registry.register_fetchers('swallow', [self.SwallowFetcher()])

        crudity_registry.register_backends([FakeContactBackend, FakeOrganisationBackend])

        with self.assertRaises(ImproperlyConfigured):
            crudity_registry.dispatch([{
                'fetcher':     'swallow',
                'input':       '',
                'method':      '',
                'model':       'creme_core.fakeorganisation',
                'password':    '',
                'limit_froms': (),
                'in_sandbox':  True,
                'body_map':    {},
                'subject':     '*',
            }])
