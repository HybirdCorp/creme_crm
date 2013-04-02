# -*- coding: utf-8 -*-

try:
    from creme.persons.models import Contact, Organisation

    from creme.documents.models import Document

    from ..registry import CRUDityRegistry
    from .base import (CrudityTestCase, FakeFetcher, ContactFakeBackend,
                       OrganisationFakeBackend, DocumentFakeBackend, FakeInput)
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class CrudityRegistryTestCase(CrudityTestCase):
    def setUp(self):
        super(CrudityRegistryTestCase, self).setUp()
        self.crudity_registry = CRUDityRegistry()#Ensure the registry is empty

    def test_register_fetchers01(self):
        crudity_registry = self.crudity_registry
        crudity_registry.register_fetchers("test", [FakeFetcher(), FakeFetcher()])
        crudity_registry.register_fetchers("test2", [FakeFetcher(), FakeFetcher()])

        fetcher = crudity_registry.get_fetcher("test")
        fetcher2 = crudity_registry.get_fetcher("test2")
        self.assertTrue(fetcher)
        self.assertTrue(fetcher2)
        self.assertEqual([fetcher, fetcher2], crudity_registry.get_fetchers())

    def test_register_backend01(self):
        crudity_registry = self.crudity_registry
        crudity_registry.register_backends([ContactFakeBackend, OrganisationFakeBackend])
        crudity_registry.register_backends([DocumentFakeBackend])
        self.assertEqual(set([Contact, Organisation, Document]), set(crudity_registry._backends))

    def test_register_input01(self):
        crudity_registry = self.crudity_registry
        crudity_registry.register_fetchers("test", [FakeFetcher(), FakeFetcher()])

        i1 = FakeInput()
        i1.name = u"1"
        i1.method = u"create"
        i2 = FakeInput()
        i2.name = u"2"
        i2.method = u"create"

        crudity_registry.register_inputs("test", [i1, i2])

        fetcher = crudity_registry.get_fetcher("test")
        inputs = []
        for value in fetcher._inputs.values():
            inputs.extend(value.values())

        self.assertEqual(set(i.name for i in inputs), set([i1.name, i2.name]))
