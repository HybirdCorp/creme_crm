from creme.creme_core.core.search import SearchRegistry, search_registry
from creme.creme_core.models import (
    CremePropertyType,
    FakeContact,
    FakeOrganisation,
)
from creme.creme_core.tests.base import CremeTestCase


class SearchRegistryTestCase(CremeTestCase):
    def test_register(self):
        registry = SearchRegistry()
        self.assertListEqual([], [*registry.models])

        registry.register(FakeContact, FakeOrganisation)
        self.assertCountEqual(
            [FakeContact, FakeOrganisation], [*registry.models],
        )

        registry.unregister(FakeContact)
        self.assertListEqual([FakeOrganisation], [*registry.models])

    def test_global_registry(self):
        models = {*search_registry.models}
        self.assertIn(CremePropertyType, models)
        self.assertIn(FakeContact, models)
        self.assertIn(FakeOrganisation, models)
