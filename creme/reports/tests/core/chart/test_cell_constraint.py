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
    FakeEmailCampaign,
    FakeOrganisation,
    FieldsConfig,
    RelationType,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.reports.constants import AbscissaGroup
from creme.reports.core.chart.cell_constraint import (
    ChartHandCellConstraint,
    ChartHandConstraintsRegistry,
    CHCCCustomDate,
    CHCCCustomEnum,
    CHCCRegularChoices,
    CHCCRegularDate,
    CHCCRegularFK,
    CHCCRelation,
)


class ChartHandConstraintsTestCase(CremeTestCase):
    def find_rfield_cell(self, cells, field_name):
        for cell in cells:
            finfo = cell.field_info
            if len(finfo) == 1 and finfo[0].name == field_name:
                return

        self.fail(f'{field_name} not found in cells.')

    def test_regular_fk01(self):
        constraint = CHCCRegularFK(model=FakeOrganisation)

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
        constraint = CHCCRegularFK(FakeOrganisation)
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

    def test_regular_choices(self):
        model = FakeEmailCampaign
        constraint = CHCCRegularChoices(model=model)

        build_cell = EntityCellRegularField.build
        self.assertIs(constraint.check_cell(build_cell(model, 'type')),    True)
        self.assertIs(constraint.check_cell(build_cell(model, 'name')),    False)
        self.assertIs(constraint.check_cell(build_cell(model, 'created')), False)

        # ---
        cell1 = constraint.get_cell(cell_key='regular_field-type')
        self.assertIsInstance(cell1, EntityCellRegularField)
        finfo = cell1.field_info
        self.assertEqual(1, len(finfo))
        self.assertEqual('type', finfo[0].name)

        self.assertIsNone(constraint.get_cell(cell_key='regular_field-created'))

        # ---
        cells = [*constraint.cells()]
        self.assertEqual(2, len(cells))
        self.assertIsInstance(cells[0], EntityCellRegularField)

        self.find_rfield_cell(cells, 'type')
        self.find_rfield_cell(cells, 'status')

    def test_regular_date01(self):
        constraint = CHCCRegularDate(model=FakeOrganisation)

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
        constraint = CHCCRegularDate(model=model)
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
        constraint = CHCCRelation(model=FakeContact)

        rtype1 = RelationType.objects.builder(
            id='test-subject_likes', predicate='likes',
        ).symmetric(id='test-object_likes', predicate='is liked by').get_or_create()[0]
        self.assertTrue(constraint.check_cell(EntityCellRelation(FakeContact, rtype1)))

        rtype2 = RelationType.objects.builder(
            id='test-subject_loves', predicate='is loving', models=[FakeContact],
        ).symmetric(
            id='test-object_loves', predicate='is loved by', models=[FakeContact],
        ).get_or_create()[0]
        self.assertTrue(constraint.check_cell(EntityCellRelation(FakeContact, rtype2)))

        rtype3 = RelationType.objects.builder(
            id='test-subject_branch', predicate='has branch', models=[FakeOrganisation],
        ).symmetric(
            id='test-object_branch', predicate='is a branch of',
            models=[FakeOrganisation],
        ).get_or_create()[0]
        self.assertFalse(constraint.check_cell(EntityCellRelation(FakeContact, rtype3)))

        disabled_rtype = RelationType.objects.builder(
            id='test-subject_disabled', predicate='disabled',
            enabled=False,  # <==
        ).symmetric(id='test-object_disabled', predicate='what ever').get_or_create()[0]

        self.assertFalse(
            constraint.check_cell(EntityCellRelation(FakeContact, disabled_rtype)),
        )
        self.assertTrue(
            constraint.check_cell(
                cell=EntityCellRelation(FakeContact, disabled_rtype),
                not_hiddable_cell_keys=[f'relation-{disabled_rtype.id}'],
            ),
        )

        # ---
        cell1 = constraint.get_cell(cell_key=f'relation-{rtype2.id}')
        self.assertIsInstance(cell1, EntityCellRelation)
        self.assertEqual(rtype2, cell1.relation_type)

        self.assertIsNone(constraint.get_cell(cell_key=f'relation-{rtype3.id}'))

        # ---
        def find_cell(rtype, cells):
            for cell in cells:
                if cell.relation_type == rtype:
                    return

            self.fail(f'{rtype} not found in cells.')

        def dont_find_cell(rtype, cells):
            for cell in cells:
                if cell.relation_type == rtype:
                    self.fail(f'{rtype} should not be found in cells.')

        creation_cells = [*constraint.cells()]
        self.assertGreaterEqual(len(creation_cells), 2)
        self.assertIsInstance(creation_cells[0], EntityCellRelation)

        find_cell(rtype1, creation_cells)
        find_cell(rtype2, creation_cells)
        dont_find_cell(rtype3,         creation_cells)
        dont_find_cell(disabled_rtype, creation_cells)

        # ---
        edition_cells = [
            *constraint.cells(not_hiddable_cell_keys=[f'relation-{disabled_rtype.id}']),
        ]
        find_cell(rtype1, edition_cells)
        find_cell(rtype2, edition_cells)
        dont_find_cell(rtype3, edition_cells)
        find_cell(disabled_rtype, edition_cells)  # <== not ignored

    def test_custom_enum(self):
        constraint = CHCCCustomEnum(model=FakeContact)

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
        cell2 = self.get_alone_element(constraint.cells())
        self.assertIsInstance(cell2, EntityCellCustomField)
        self.assertEqual(cfield1, cell2.custom_field)

        self.assertListEqual(
            [key1, key4],
            [c.key for c in constraint.cells(not_hiddable_cell_keys=[key4])],
        )

    def test_custom_date(self):
        constraint = CHCCCustomDate(model=FakeContact)

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
        cell2 = self.get_alone_element(constraint.cells())
        self.assertIsInstance(cell2, EntityCellCustomField)
        self.assertEqual(cfield1, cell2.custom_field)


class ChartHandConstraintsRegistryTestCase(CremeTestCase):
    def test_empty(self):
        registry = ChartHandConstraintsRegistry()
        self.assertListEqual([], [*registry.cell_constraints(FakeContact)])
        self.assertListEqual([], [*registry.chart_types])
        self.assertListEqual([], [*registry.parameter_validators])
        self.assertIsNone(registry.get_constraint_by_chart_type(FakeContact, AbscissaGroup.FK))
        self.assertIsNone(registry.get_parameter_validator(AbscissaGroup.FK))

    def test_cell_constraints01(self):
        registry = ChartHandConstraintsRegistry().register_cell_constraint(
            constraint_class=CHCCRegularFK,
            chart_types=[AbscissaGroup.FK],
        )

        constraint = self.get_alone_element(registry.cell_constraints(FakeContact))
        self.assertIsInstance(constraint, CHCCRegularFK)

        # ---
        get_constraint = registry.get_constraint_by_chart_type
        self.assertIsInstance(get_constraint(FakeContact, AbscissaGroup.FK), CHCCRegularFK)
        self.assertIsNone(get_constraint(FakeContact, AbscissaGroup.RELATION))

        # ---
        self.assertListEqual([AbscissaGroup.FK], [*registry.chart_types])

    def test_cell_constraints02(self):
        "Several constraints."
        registry = ChartHandConstraintsRegistry(
        ).register_cell_constraint(
            constraint_class=CHCCRegularFK,
            chart_types=[AbscissaGroup.FK],
        ).register_cell_constraint(
            constraint_class=CHCCRelation,
            chart_types=[AbscissaGroup.RELATION],
        )

        self.assertEqual(2, len([*registry.cell_constraints(FakeContact)]))

        # ---
        get_constraint = registry.get_constraint_by_chart_type
        self.assertIsInstance(get_constraint(FakeContact, AbscissaGroup.FK), CHCCRegularFK)
        self.assertIsInstance(get_constraint(FakeContact, AbscissaGroup.RELATION), CHCCRelation)

        # ---
        self.assertCountEqual(
            [AbscissaGroup.FK, AbscissaGroup.RELATION],
            [*registry.chart_types],
        )

    def test_cell_constraints03(self):
        "Several constraints (several types at once)."
        registry = ChartHandConstraintsRegistry().register_cell_constraint(
            constraint_class=CHCCRegularDate,
            chart_types=[AbscissaGroup.MONTH, AbscissaGroup.YEAR],
        )

        constraint = self.get_alone_element(registry.cell_constraints(FakeContact))  # Not 2
        self.assertIsInstance(constraint, CHCCRegularDate)

    def test_cell_constraints04(self):
        "Duplicated constraints."
        registry = ChartHandConstraintsRegistry().register_cell_constraint(
            constraint_class=CHCCRegularFK,
            chart_types=[AbscissaGroup.FK],
        )

        with self.assertRaises(ChartHandConstraintsRegistry.RegistrationError):
            registry.register_cell_constraint(
                constraint_class=CHCCRegularDate,
                chart_types=[AbscissaGroup.FK],  # <==
            )

        # ---
        class TestCHCC(ChartHandCellConstraint):
            type_id = CHCCRegularFK.type_id   # <==

        with self.assertRaises(ChartHandConstraintsRegistry.RegistrationError):
            registry.register_cell_constraint(
                constraint_class=TestCHCC,
                chart_types=[AbscissaGroup.CUSTOM_RANGE],
            )

    def test_validators01(self):
        formfield = forms.IntegerField(label='Number of days')
        registry = ChartHandConstraintsRegistry().register_parameter_validator(
            chart_types=[AbscissaGroup.RANGE, AbscissaGroup.CUSTOM_RANGE],
            formfield=formfield,
        )
        self.assertCountEqual(
            [(AbscissaGroup.RANGE, formfield), (AbscissaGroup.CUSTOM_RANGE, formfield)],
            [*registry.parameter_validators]
        )

        get_validator = registry.get_parameter_validator
        self.assertIsNone(get_validator(AbscissaGroup.FK))
        self.assertEqual(formfield, get_validator(AbscissaGroup.RANGE))
        self.assertEqual(formfield, get_validator(AbscissaGroup.CUSTOM_RANGE))

    def test_validators02(self):
        "Duplicates."
        registry = ChartHandConstraintsRegistry().register_parameter_validator(
            chart_types=[AbscissaGroup.RANGE, AbscissaGroup.CUSTOM_RANGE],
            formfield=forms.IntegerField(label='Number of days'),
        )

        with self.assertRaises(ChartHandConstraintsRegistry.RegistrationError):
            registry.register_parameter_validator(
                chart_types=[AbscissaGroup.CUSTOM_RANGE],  # <==
                formfield=forms.DecimalField(),
            )
