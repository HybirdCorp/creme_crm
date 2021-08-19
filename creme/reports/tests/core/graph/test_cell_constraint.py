# -*- coding: utf-8 -*-

from functools import partial

from django import forms

from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.models import (
    CustomField,
    FakeContact,
    FakeOrganisation,
    FieldsConfig,
    RelationType,
)
from creme.creme_core.tests.base import CremeTestCase
# from creme.reports.constants import (
#     RGT_CUSTOM_RANGE,
#     RGT_FK,
#     RGT_MONTH,
#     RGT_RANGE,
#     RGT_RELATION,
#     RGT_YEAR,
# )
from creme.reports.constants import AbscissaGroup
from creme.reports.core.graph.cell_constraint import (
    GHCCCustomDate,
    GHCCCustomEnum,
    GHCCRegularDate,
    GHCCRegularFK,
    GHCCRelation,
    GraphHandCellConstraint,
    GraphHandConstraintsRegistry,
)


class GraphHandConstraintsTestCase(CremeTestCase):
    def find_rfield_cell(self, cells, field_name):
        for cell in cells:
            finfo = cell.field_info
            if len(finfo) == 1 and finfo[0].name == field_name:
                return

        self.fail(f'{field_name} not found in cells.')

    def test_regular_fk01(self):
        constraint = GHCCRegularFK(model=FakeOrganisation)

        build_cell = EntityCellRegularField.build
        self.assertIs(constraint.check_cell(build_cell(FakeOrganisation, 'sector')), True)
        self.assertIs(constraint.check_cell(build_cell(FakeOrganisation, 'name')),    False)
        self.assertIs(constraint.check_cell(build_cell(FakeOrganisation, 'created')), False)

        # ---
        cell1 = constraint.get_cell(cell_key='regular_field-sector')
        self.assertIsInstance(cell1, EntityCellRegularField)
        finfo = cell1.field_info
        self.assertEqual(1, len(finfo))
        self.assertEqual('sector', finfo[0].name)

        self.assertIsNone(constraint.get_cell(cell_key='regular_field-created'))

        # ---
        cells = [*constraint.cells()]
        self.assertEqual(3, len(cells))
        self.assertIsInstance(cells[0], EntityCellRegularField)

        self.find_rfield_cell(cells, 'user')
        self.find_rfield_cell(cells, 'sector')
        self.find_rfield_cell(cells, 'legal_form')

    def test_regular_fk02(self):
        "Fields config."
        constraint = GHCCRegularFK(FakeOrganisation)
        hidden_fname = 'sector'

        other_cell_key = 'regular_field-legal_form'
        hidden_cell_key = f'regular_field-{hidden_fname}'

        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        cells1 = [*constraint.cells()]
        self.assertEqual(2, len(cells1))
        self.assertIsInstance(cells1[0], EntityCellRegularField)

        self.find_rfield_cell(cells1, 'user')
        # self.find_rfield_cell(cells1, 'sector')  # NOPE
        self.find_rfield_cell(cells1, 'legal_form')

        cells2 = [
            *constraint.cells(not_hiddable_cell_keys={other_cell_key})
        ]
        self.assertEqual(2, len(cells2))

        cells3 = [
            *constraint.cells(not_hiddable_cell_keys={other_cell_key, hidden_cell_key})
        ]
        self.assertEqual(3, len(cells3))
        self.find_rfield_cell(cells3, 'sector')

        # ---
        self.assertFalse(
            constraint.check_cell(
                EntityCellRegularField.build(FakeOrganisation, hidden_fname)
            )
        )

        # ---
        cell = constraint.get_cell(cell_key='regular_field-legal_form')
        self.assertIsInstance(cell, EntityCellRegularField)
        finfo = cell.field_info
        self.assertEqual(1, len(finfo))
        self.assertEqual('legal_form', finfo[0].name)

        self.assertIsNone(constraint.get_cell(cell_key=hidden_cell_key))
        self.assertIsNone(constraint.get_cell(
            cell_key=hidden_cell_key,
            not_hiddable_cell_keys={other_cell_key},
        ))

        self.assertIsInstance(
            constraint.get_cell(
                cell_key=hidden_cell_key,
                not_hiddable_cell_keys={other_cell_key, hidden_cell_key},
            ),
            EntityCellRegularField
        )

    def test_regular_date01(self):
        constraint = GHCCRegularDate(model=FakeOrganisation)

        build_cell = EntityCellRegularField.build
        self.assertIs(constraint.check_cell(build_cell(FakeOrganisation, 'created')), True)
        self.assertIs(constraint.check_cell(build_cell(FakeOrganisation, 'name')), False)
        self.assertIs(constraint.check_cell(build_cell(FakeOrganisation, 'sector')), False)

        # ---
        cell1 = constraint.get_cell(cell_key='regular_field-creation_date')
        self.assertIsInstance(cell1, EntityCellRegularField)
        finfo = cell1.field_info
        self.assertEqual(1, len(finfo))
        self.assertEqual('creation_date', finfo[0].name)

        self.assertIsNone(constraint.get_cell(cell_key='regular_field-sector'))

        # ---
        cells = [*constraint.cells()]
        self.assertEqual(3, len(cells))
        self.assertIsInstance(cells[0], EntityCellRegularField)

        self.find_rfield_cell(cells, 'created')
        self.find_rfield_cell(cells, 'modified')
        self.find_rfield_cell(cells, 'creation_date')

    def test_regular_date02(self):
        "Fields config."
        model = FakeContact
        constraint = GHCCRegularDate(model=model)
        hidden_fname = 'birthday'

        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        for cell in constraint.cells():
            finfo = cell.field_info
            if len(finfo) == 1 and finfo[0].name == hidden_fname:
                self.fail(f'{hidden_fname} found in cells (should be hidden).')

        # ---
        self.assertFalse(
            constraint.check_cell(
                EntityCellRegularField.build(model, hidden_fname)
            )
        )

        # ---
        cell = constraint.get_cell(cell_key='regular_field-created')
        self.assertIsInstance(cell, EntityCellRegularField)

        finfo = cell.field_info
        self.assertEqual(1, len(finfo))
        self.assertEqual('created', finfo[0].name)

        cell_key = f'regular_field-{hidden_fname}'
        self.assertIsNone(constraint.get_cell(cell_key=cell_key))

        self.assertIsInstance(
            constraint.get_cell(
                cell_key=cell_key,
                not_hiddable_cell_keys=[cell_key],
            ),
            EntityCellRegularField,
        )

    def test_relationship(self):
        constraint = GHCCRelation(model=FakeContact)

        create_rtype = RelationType.objects.smart_update_or_create
        rtype1 = create_rtype(
            ('test-subject_likes', 'likes'),
            ('test-object_likes',  'is liked by'),
        )[0]
        self.assertTrue(constraint.check_cell(EntityCellRelation(FakeContact, rtype1)))

        rtype2 = create_rtype(
            ('test-subject_loves', 'is loving',   [FakeContact]),
            ('test-object_loves',  'is loved by', [FakeContact]),
        )[0]
        self.assertTrue(constraint.check_cell(EntityCellRelation(FakeContact, rtype2)))

        rtype3 = create_rtype(
            ('test-subject_branch', 'has branch',     [FakeOrganisation]),
            ('test-object_branch',  'is a branch of', [FakeOrganisation]),
        )[0]
        self.assertFalse(constraint.check_cell(EntityCellRelation(FakeContact, rtype3)))

        # ---
        cell1 = constraint.get_cell(cell_key=f'relation-{rtype2.id}')
        self.assertIsInstance(cell1, EntityCellRelation)
        self.assertEqual(rtype2, cell1.relation_type)

        self.assertIsNone(constraint.get_cell(cell_key=f'relation-{rtype3.id}'))

        # ---
        cells = [*constraint.cells()]
        self.assertGreaterEqual(len(cells), 2)
        self.assertIsInstance(cells[0], EntityCellRelation)

        def find_cell(rtype):
            for cell in cells:
                if cell.relation_type == rtype:
                    return

            self.fail(f'{rtype} not found in cells.')

        find_cell(rtype1)
        find_cell(rtype2)

        for cell in cells:
            if cell.relation_type == rtype3:
                self.fail(f'{rtype3} should not be found in cells.')

    def test_custom_enum(self):
        constraint = GHCCCustomEnum(model=FakeContact)

        create_cfield = partial(
            CustomField.objects.create,
            content_type=FakeContact,
            field_type=CustomField.ENUM,
        )
        cfield1 = create_cfield(name='Hair')
        cfield2 = create_cfield(name='First fight', field_type=CustomField.DATETIME)
        cfield3 = create_cfield(name='Main sector', content_type=FakeOrganisation)
        cfield4 = create_cfield(name='Eyes', is_deleted=True)

        self.assertTrue(constraint.check_cell(EntityCellCustomField(cfield1)))
        self.assertFalse(constraint.check_cell(EntityCellCustomField(cfield2)))

        # ---
        get_cell = constraint.get_cell
        key1 = f'custom_field-{cfield1.id}'
        cell1 = get_cell(cell_key=key1)
        self.assertIsInstance(cell1, EntityCellCustomField)
        self.assertEqual(cfield1, cell1.custom_field)

        self.assertIsNone(get_cell(cell_key=f'custom_field-{cfield2.id}'))
        self.assertIsNone(get_cell(cell_key=f'custom_field-{cfield3.id}'))

        key4 = f'custom_field-{cfield4.id}'
        self.assertIsNone(get_cell(cell_key=key4))
        self.assertIsInstance(
            get_cell(cell_key=key4, not_hiddable_cell_keys=[key4]),
            EntityCellCustomField
        )

        # ---
        cells = [*constraint.cells()]
        self.assertEqual(1, len(cells))

        cell2 = cells[0]
        self.assertIsInstance(cell2, EntityCellCustomField)
        self.assertEqual(cfield1, cell2.custom_field)

        self.assertListEqual(
            [key1, key4],
            [c.key for c in constraint.cells(not_hiddable_cell_keys=[key4])]
        )

    def test_custom_date(self):
        constraint = GHCCCustomDate(model=FakeContact)

        create_cfield = partial(
            CustomField.objects.create,
            content_type=FakeContact,
            field_type=CustomField.DATETIME,
        )
        cfield1 = create_cfield(name='First fight')
        cfield2 = create_cfield(name='Hair', field_type=CustomField.ENUM)
        cfield3 = create_cfield(name='Main sector', content_type=FakeOrganisation)

        self.assertTrue(constraint.check_cell(EntityCellCustomField(cfield1)))
        self.assertFalse(constraint.check_cell(EntityCellCustomField(cfield2)))

        # ---
        get_cell = constraint.get_cell
        cell1 = get_cell(cell_key=f'custom_field-{cfield1.id}')
        self.assertIsInstance(cell1, EntityCellCustomField)
        self.assertEqual(cfield1, cell1.custom_field)

        self.assertIsNone(get_cell(cell_key=f'custom_field-{cfield2.id}'))
        self.assertIsNone(get_cell(cell_key=f'custom_field-{cfield3.id}'))

        # ---
        cells = [*constraint.cells()]
        self.assertEqual(1, len(cells))

        cell2 = cells[0]
        self.assertIsInstance(cell2, EntityCellCustomField)
        self.assertEqual(cfield1, cell2.custom_field)


class GraphHandConstraintsRegistryTestCase(CremeTestCase):
    def test_empty(self):
        registry = GraphHandConstraintsRegistry()
        self.assertListEqual([], [*registry.cell_constraints(FakeContact)])
        self.assertListEqual([], [*registry.rgraph_types])
        self.assertListEqual([], [*registry.parameter_validators])
        # self.assertIsNone(registry.get_constraint_by_rgraph_type(FakeContact, RGT_FK))
        self.assertIsNone(registry.get_constraint_by_rgraph_type(FakeContact, AbscissaGroup.FK))
        # self.assertIsNone(registry.get_parameter_validator(RGT_FK))
        self.assertIsNone(registry.get_parameter_validator(AbscissaGroup.FK))

    def test_cell_constraints01(self):
        registry = GraphHandConstraintsRegistry().register_cell_constraint(
            constraint_class=GHCCRegularFK,
            # rgraph_types=[RGT_FK],
            rgraph_types=[AbscissaGroup.FK],
        )

        constraints = [*registry.cell_constraints(FakeContact)]
        self.assertEqual(1, len(constraints))
        self.assertIsInstance(constraints[0], GHCCRegularFK)

        # ---
        get_constraint = registry.get_constraint_by_rgraph_type
        # self.assertIsInstance(get_constraint(FakeContact, RGT_FK), GHCCRegularFK)
        self.assertIsInstance(get_constraint(FakeContact, AbscissaGroup.FK), GHCCRegularFK)
        # self.assertIsNone(get_constraint(FakeContact, RGT_RELATION))
        self.assertIsNone(get_constraint(FakeContact, AbscissaGroup.RELATION))

        # ---
        # self.assertListEqual([RGT_FK], [*registry.rgraph_types])
        self.assertListEqual([AbscissaGroup.FK], [*registry.rgraph_types])

    def test_cell_constraints02(self):
        "Several constraints."
        registry = GraphHandConstraintsRegistry(
        ).register_cell_constraint(
            constraint_class=GHCCRegularFK,
            # rgraph_types=[RGT_FK],
            rgraph_types=[AbscissaGroup.FK],
        ).register_cell_constraint(
            constraint_class=GHCCRelation,
            # rgraph_types=[RGT_RELATION],
            rgraph_types=[AbscissaGroup.RELATION],
        )

        self.assertEqual(2, len([*registry.cell_constraints(FakeContact)]))

        # ---
        get_constraint = registry.get_constraint_by_rgraph_type
        # self.assertIsInstance(get_constraint(FakeContact, RGT_FK), GHCCRegularFK)
        self.assertIsInstance(get_constraint(FakeContact, AbscissaGroup.FK), GHCCRegularFK)
        # self.assertIsInstance(get_constraint(FakeContact, RGT_RELATION), GHCCRelation)
        self.assertIsInstance(get_constraint(FakeContact, AbscissaGroup.RELATION), GHCCRelation)

        # ---
        # self.assertCountEqual([RGT_FK, RGT_RELATION], [*registry.rgraph_types])
        self.assertCountEqual(
            [AbscissaGroup.FK, AbscissaGroup.RELATION],
            [*registry.rgraph_types],
        )

    def test_cell_constraints03(self):
        "Several constraints (several types at once)."
        registry = GraphHandConstraintsRegistry().register_cell_constraint(
            constraint_class=GHCCRegularDate,
            # rgraph_types=[RGT_MONTH, RGT_YEAR],
            rgraph_types=[AbscissaGroup.MONTH, AbscissaGroup.YEAR],
        )

        constraints = [*registry.cell_constraints(FakeContact)]
        self.assertEqual(1, len(constraints))  # Not 2
        self.assertIsInstance(constraints[0], GHCCRegularDate)

    def test_cell_constraints04(self):
        "Duplicated constraints."
        registry = GraphHandConstraintsRegistry().register_cell_constraint(
            constraint_class=GHCCRegularFK,
            # rgraph_types=[RGT_FK],
            rgraph_types=[AbscissaGroup.FK],
        )

        with self.assertRaises(GraphHandConstraintsRegistry.RegistrationError):
            registry.register_cell_constraint(
                constraint_class=GHCCRegularDate,
                # rgraph_types=[RGT_FK],  # <==
                rgraph_types=[AbscissaGroup.FK],  # <==
            )

        # ---
        class TestGHCC(GraphHandCellConstraint):
            type_id = GHCCRegularFK.type_id   # <==

        with self.assertRaises(GraphHandConstraintsRegistry.RegistrationError):
            registry.register_cell_constraint(
                constraint_class=TestGHCC,
                # rgraph_types=[RGT_CUSTOM_RANGE],
                rgraph_types=[AbscissaGroup.CUSTOM_RANGE],
            )

    def test_validators01(self):
        formfield = forms.IntegerField(label='Number of days')
        registry = GraphHandConstraintsRegistry().register_parameter_validator(
            # rgraph_types=[RGT_RANGE, RGT_CUSTOM_RANGE],
            rgraph_types=[AbscissaGroup.RANGE, AbscissaGroup.CUSTOM_RANGE],
            formfield=formfield,
        )
        self.assertCountEqual(
            # [(RGT_RANGE, formfield), (RGT_CUSTOM_RANGE, formfield)],
            [(AbscissaGroup.RANGE, formfield), (AbscissaGroup.CUSTOM_RANGE, formfield)],
            [*registry.parameter_validators]
        )

        get_validator = registry.get_parameter_validator
        # self.assertIsNone(get_validator(RGT_FK))
        self.assertIsNone(get_validator(AbscissaGroup.FK))
        # self.assertEqual(formfield, get_validator(RGT_RANGE))
        self.assertEqual(formfield, get_validator(AbscissaGroup.RANGE))
        # self.assertEqual(formfield, get_validator(RGT_CUSTOM_RANGE))
        self.assertEqual(formfield, get_validator(AbscissaGroup.CUSTOM_RANGE))

    def test_validators02(self):
        "Duplicates."
        registry = GraphHandConstraintsRegistry().register_parameter_validator(
            # rgraph_types=[RGT_RANGE, RGT_CUSTOM_RANGE],
            rgraph_types=[AbscissaGroup.RANGE, AbscissaGroup.CUSTOM_RANGE],
            formfield=forms.IntegerField(label='Number of days'),
        )

        with self.assertRaises(GraphHandConstraintsRegistry.RegistrationError):
            registry.register_parameter_validator(
                # rgraph_types=[RGT_CUSTOM_RANGE],  # <==
                rgraph_types=[AbscissaGroup.CUSTOM_RANGE],  # <==
                formfield=forms.DecimalField(),
            )
