from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.core.entity_cell import (
    EntityCellFunctionField,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.function_fields import PropertiesField
from creme.creme_core.gui.listview.smart_columns import SmartColumnsRegistry
from creme.creme_core.models import FakeContact, FakeOrganisation
from creme.creme_core.tests.base import CremeTestCase


class SmartColumnsTestCase(CremeTestCase):
    def test_register(self):
        registry = SmartColumnsRegistry()
        self.assertListEqual([], registry.get_cells(FakeContact))
        self.assertListEqual([], registry.get_cells(FakeOrganisation))

        field_name = 'first_name'
        registry.register_model(FakeContact).register_field(field_name)
        self.assertListEqual(
            [EntityCellRegularField.build(FakeContact, field_name)],
            registry.get_cells(FakeContact),
        )

        funcfield_name = PropertiesField.name
        registry.register_model(FakeContact).register_function_field(
            funcfield_name,
        ).register_relationtype(REL_SUB_HAS)
        with self.assertNoLogs():
            cells = registry.get_cells(FakeContact)
        self.assertListEqual(
            [
                EntityCellRegularField.build(FakeContact, field_name),
                EntityCellFunctionField.build(FakeContact, funcfield_name),
                EntityCellRelation.build(FakeContact, REL_SUB_HAS),
            ],
            cells,
        )
        self.assertListEqual([], registry.get_cells(FakeOrganisation))

    def test_invalid_rtype(self):
        registry = SmartColumnsRegistry()

        field_name = 'name'
        registry.register_model(FakeOrganisation).register_field(
            field_name,
        ).register_relationtype('creme_core-subject_invalid')

        with self.assertLogs(level='WARNING'):
            cells = registry.get_cells(FakeOrganisation)
        self.assertListEqual(
            [EntityCellRegularField.build(FakeOrganisation, field_name)],
            cells,
        )

    def test_clear_model(self):
        registry = SmartColumnsRegistry()
        registry.register_model(FakeContact).register_field('first_name')

        registry.clear_model(FakeContact)
        self.assertListEqual([], registry.get_cells(FakeContact))

    def test_unregister_field(self):
        registry = SmartColumnsRegistry()

        field_name = 'first_name'
        registry.register_model(
            FakeContact
        ).register_field(field_name).register_relationtype(REL_SUB_HAS)

        registry.register_model(FakeContact).unregister_field(field_name)
        self.assertListEqual(
            [EntityCellRelation.build(FakeContact, REL_SUB_HAS)],
            registry.get_cells(FakeContact),
        )

        # ---
        with self.assertRaises(ValueError) as exc_mngr:
            registry.register_model(FakeContact).unregister_field('last_name')
        self.assertEqual(
            'The field "last_name" in not registered.',
            str(exc_mngr.exception),
        )

    def test_unregister_function_field(self):
        registry = SmartColumnsRegistry()

        field_name = 'first_name'
        funcfield_name = PropertiesField.name
        registry.register_model(
            FakeContact
        ).register_field(field_name).register_function_field(funcfield_name)

        registry.register_model(FakeContact).unregister_function_field(funcfield_name)
        self.assertListEqual(
            [EntityCellRegularField.build(FakeContact, field_name)],
            registry.get_cells(FakeContact),
        )

        # ---
        with self.assertRaises(ValueError) as exc_mngr:
            registry.register_model(FakeContact).unregister_function_field('invalid')
        self.assertEqual(
            'The function field "invalid" in not registered.',
            str(exc_mngr.exception),
        )

    def test_unregister_relationtype(self):
        registry = SmartColumnsRegistry()

        field_name = 'first_name'
        registry.register_model(
            FakeContact
        ).register_field(field_name).register_relationtype(REL_SUB_HAS)

        registry.register_model(FakeContact).unregister_relationtype(REL_SUB_HAS)
        self.assertListEqual(
            [EntityCellRegularField.build(FakeContact, field_name)],
            registry.get_cells(FakeContact),
        )

        # ---
        with self.assertRaises(ValueError) as exc_mngr:
            registry.register_model(FakeContact).unregister_relationtype(REL_SUB_HAS)
        self.assertEqual(
            f'The relation type "{REL_SUB_HAS}" in not registered.',
            str(exc_mngr.exception),
        )
