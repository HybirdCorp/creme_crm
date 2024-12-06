from creme.creme_core.models import (
    CustomEntityType,
    FakeContact,
    FakeDocument,
    FakeOrganisation,
    FakeSector,
)

from ..registry import CremeRegistry
from .base import CremeTestCase, skipIfNotInstalled


class CremeRegistryTestCase(CremeTestCase):
    def _enable_type(self, id, name):
        ce_type = self.get_object_or_fail(CustomEntityType, id=id)
        ce_type.enabled = True
        ce_type.name = name
        ce_type.plural_name = f'{name}s'
        ce_type.save()

        return ce_type

    def test_empty(self):
        registry = CremeRegistry()
        self.assertFalse([*registry.iter_entity_models()])
        self.assertFalse(registry.is_entity_model_registered(FakeContact))

    def test_register(self):
        registry = CremeRegistry().register_entity_models(
            FakeContact, FakeOrganisation,
        )
        self.assertListEqual(
            [FakeContact, FakeOrganisation],
            [*registry.iter_entity_models()],
        )

        is_registered = registry.is_entity_model_registered
        self.assertTrue(is_registered(FakeContact))
        self.assertTrue(is_registered(FakeOrganisation))
        self.assertFalse(is_registered(FakeDocument))

    def test_register_error(self):
        with self.assertLogs(level='CRITICAL') as logs_manager:
            registry = CremeRegistry().register_entity_models(
                FakeSector, FakeOrganisation,
            )

        self.assertListEqual(
            [FakeOrganisation],
            [*registry.iter_entity_models()],
        )
        self.assertListEqual(
            logs_manager.output,
            [
                "CRITICAL:"
                "creme.creme_core.registry:CremeRegistry.register_entity_models: "
                "<class 'creme.creme_core.tests.fake_models.FakeSector'> is not a "
                "subclass of CremeEntity, so we ignore it"
            ],
        )

    @skipIfNotInstalled('creme.persons')
    @skipIfNotInstalled('creme.documents')
    def test_filtered_entity_models(self):
        from creme import documents, persons

        Contact = persons.get_contact_model()
        Organisation = persons.get_organisation_model()
        Document = documents.get_document_model()

        registry = CremeRegistry().register_entity_models(
            FakeContact,
        ).register_entity_models(
            Contact, Organisation,
        ).register_entity_models(Document)
        self.assertListEqual(
            [FakeContact, Contact, Organisation, Document],
            [*registry.iter_entity_models()],
        )
        self.assertListEqual(
            [FakeContact, Contact, Organisation],
            [*registry.iter_entity_models(app_labels=['creme_core', 'persons'])],
        )

    def test_custom_entity_type(self):
        ce_type = self._enable_type(id=1, name='Shop')

        registry = CremeRegistry().register_entity_models(FakeContact)
        with self.assertNumQueries(1):
            models = [*registry.iter_entity_models()]
        self.assertCountEqual([FakeContact, ce_type.entity_model], models)

        with self.assertNumQueries(0):
            [*registry.iter_entity_models()] # NOQA

    def test_custom_entity_type__filtered(self):
        ce_type1 = self._enable_type(id=1, name='Shop')
        ce_type2 = self._enable_type(id=2, name='Land')
        ce_type3 = self.get_object_or_fail(CustomEntityType, id=3)
        self.assertFalse(ce_type3.enabled)

        registry = CremeRegistry().register_entity_models(FakeContact)
        with self.assertNumQueries(1):
            models = {
                *registry.iter_entity_models(app_labels=['creme_core', 'custom_entities'])
            }
        self.assertIn(FakeContact,           models)
        self.assertIn(ce_type1.entity_model, models)
        self.assertIn(ce_type2.entity_model, models)
        self.assertNotIn(ce_type3.entity_model, models)

        with self.assertNumQueries(0):
            [*registry.iter_entity_models(app_labels=['custom_entities'])]  # NOQA
