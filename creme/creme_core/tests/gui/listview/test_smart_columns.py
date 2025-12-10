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
