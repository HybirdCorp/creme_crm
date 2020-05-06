# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.utils.translation import gettext as _

    from creme.creme_core.core.entity_cell import (
        EntityCellRegularField,
        EntityCellCustomField,
    )
    from creme.creme_core.models import (
        CustomField,
        FieldsConfig,
        FakeOrganisation, FakeContact, FakeInvoice,
    )
    from creme.creme_core.tests.base import CremeTestCase

    from creme.reports.constants import (
        RGA_COUNT, RGA_SUM,
    )
    from creme.reports.core.graph.aggregator import (
        ReportGraphAggregatorRegistry,
        ReportGraphAggregator,
        RGACount, RGASum,
    )
    from creme.reports.core.graph.cell_constraint import (
        AggregatorCellConstraint,
        ACCCount, ACCFieldAggregation,
        AggregatorConstraintsRegistry,
    )
    from creme.reports.tests.base import (
        skipIfCustomReport, skipIfCustomRGraph,
        Report, ReportGraph,
    )
except Exception as e:
    print(f'Error in <{__name__}>: {e}')


@skipIfCustomReport
@skipIfCustomRGraph
class AggregatorTestCase(CremeTestCase):
    def test_registry01(self):
        registry = ReportGraphAggregatorRegistry()
        report = Report(ct=FakeOrganisation)
        rgraph = ReportGraph(
            linked_report=report,
            ordinate_type=RGA_COUNT,
        )

        aggregator1 = registry[rgraph]
        self.assertIsInstance(aggregator1, ReportGraphAggregator)
        self.assertNotEqual(type(aggregator1), RGACount)
        self.assertEqual('??', aggregator1.verbose_name)
        self.assertEqual(_('the aggregation function is invalid.'), aggregator1.error)

        # ---
        registry(RGA_COUNT)(RGACount)
        aggregator2 = registry[rgraph]
        self.assertIsInstance(aggregator2, RGACount)
        self.assertIsNone(aggregator2.error)

    def test_registry02(self):
        registry = ReportGraphAggregatorRegistry()
        report = Report(ct=FakeOrganisation)
        rgraph = ReportGraph(
            linked_report=report,
            ordinate_type=RGA_SUM,
        )

        registry(RGA_SUM)(RGASum)
        aggregator1 = registry[rgraph]
        self.assertNotEqual(type(aggregator1), RGACount)
        self.assertEqual('??', aggregator1.verbose_name)
        self.assertEqual(_('the field does not exist any more.'), aggregator1.error)

        # ---
        rgraph.ordinate_cell_key = 'regular_field-capital'
        aggregator2 = registry[rgraph]
        self.assertIsInstance(aggregator2, RGASum)
        self.assertIsNone(aggregator2.error)

    def test_registry03(self):
        "FieldsConfig."
        hidden_fname = 'capital'
        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        registry = ReportGraphAggregatorRegistry()
        report = Report(ct=FakeOrganisation)
        rgraph = ReportGraph(
            linked_report=report,
            ordinate_type=RGA_SUM,
            ordinate_cell_key=f'regular_field-{hidden_fname}',
        )

        registry(RGA_SUM)(RGASum)
        aggregator = registry[rgraph]
        self.assertIsInstance(aggregator, RGASum)
        self.assertEqual(_('this field should be hidden.'), aggregator.error)


class AggregatorCellConstraintsTestCase(CremeTestCase):
    def test_count(self):
        constraint = ACCCount(model=FakeOrganisation)
        self.assertIsNone(constraint.get_cell('regular_field-capital'))
        self.assertFalse([*constraint.cells()])
        self.assertIs(
            constraint.check_cell(EntityCellRegularField.build(FakeOrganisation, 'capital')),
            True,
        )

    def test_field_aggregation01(self):
        "Regular field."
        constraint = ACCFieldAggregation(model=FakeOrganisation)

        build_cell = EntityCellRegularField.build
        self.assertIs(constraint.check_cell(build_cell(FakeOrganisation, 'capital')), True)
        self.assertIs(constraint.check_cell(build_cell(FakeOrganisation, 'name')), False)
        self.assertIs(constraint.check_cell(build_cell(FakeOrganisation, 'created')), False)

        # ---
        cell1 = constraint.get_cell(cell_key='regular_field-capital')
        self.assertIsInstance(cell1, EntityCellRegularField)
        finfo = cell1.field_info
        self.assertEqual(1, len(finfo))
        self.assertEqual('capital', finfo[0].name)

        self.assertIsNone(constraint.get_cell(cell_key='regular_field-sector'))

        # ---
        cells = [*constraint.cells()]
        self.assertEqual(1, len(cells))

        cell2 = cells[0]
        self.assertIsInstance(cell2, EntityCellRegularField)
        self.assertEqual(1, len(finfo))
        self.assertEqual('capital', finfo[0].name)

    def test_field_aggregation02(self):
        "Custom field."
        create_cfield = partial(CustomField.objects.create, content_type=FakeContact)
        cfield1 = create_cfield(
            name='Hair size',
            field_type=CustomField.INT,
        )
        cfield2 = create_cfield(
            name='Hair color',
            field_type=CustomField.STR,
        )

        constraint = ACCFieldAggregation(model=FakeContact)
        self.assertIs(constraint.check_cell(EntityCellCustomField(cfield1)), True)
        self.assertIs(constraint.check_cell(EntityCellCustomField(cfield2)), False)

        # ---
        cell1 = constraint.get_cell(cell_key=f'custom_field-{cfield1.id}')
        self.assertIsInstance(cell1, EntityCellCustomField)
        self.assertEqual(cfield1, cell1.custom_field)

        self.assertIsNone(constraint.get_cell(cell_key=f'custom_field-{cfield2.id}'))

        # ---
        cells = [*constraint.cells()]
        self.assertEqual(1, len(cells))

        cell2 = cells[0]
        self.assertIsInstance(cell2, EntityCellCustomField)
        self.assertEqual(cfield1, cell2.custom_field)

    def test_field_aggregation03(self):
        "Fields config."
        constraint = ACCFieldAggregation(model=FakeInvoice)
        hidden_fname = 'total_no_vat'

        other_cell_key = 'regular_field-number'
        hidden_cell_key = f'regular_field-{hidden_fname}'

        FieldsConfig.objects.create(
            content_type=FakeInvoice,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        cells1 = [*constraint.cells()]
        self.assertEqual(1, len(cells1))
        cell1 = cells1[0]
        self.assertIsInstance(cell1, EntityCellRegularField)
        self.assertEqual('total_vat', cell1.field_info[0].name)

        cells2 = [
            *constraint.cells(not_hiddable_cell_keys={other_cell_key})
        ]
        self.assertEqual(1, len(cells2), cells2)

        cells3 = [
            *constraint.cells(not_hiddable_cell_keys={other_cell_key, hidden_cell_key})
        ]
        self.assertSetEqual(
            {'total_vat', 'total_no_vat'},
            {cell.field_info[0].name for cell in cells3}
        )

        # ---
        hidden_cell = EntityCellRegularField.build(FakeInvoice, hidden_fname)
        self.assertFalse(
            constraint.check_cell(hidden_cell)
        )
        self.assertTrue(
            constraint.check_cell(
                hidden_cell,
                not_hiddable_cell_keys={other_cell_key, hidden_cell_key},
            )
        )

        # ---
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
        self.assertIsInstance(
            constraint.get_cell(cell_key=hidden_cell_key, check=False),
            EntityCellRegularField
        )


class AggregatorConstraintsRegistryTestCase(CremeTestCase):
    def test_empty(self):
        registry = AggregatorConstraintsRegistry()
        self.assertListEqual([], [*registry.cell_constraints(FakeInvoice)])
        self.assertIsNone(registry.get_constraint_by_aggr_id(FakeInvoice, RGA_COUNT))

    def test_cell_constraints01(self):
        registry = AggregatorConstraintsRegistry(
        ).register_cell_constraints(ACCCount)

        constraints = [*registry.cell_constraints(FakeInvoice)]
        self.assertEqual(1, len(constraints))
        self.assertIsInstance(constraints[0], ACCCount)

        # ---
        get_constraint = registry.get_constraint_by_aggr_id
        self.assertIsInstance(get_constraint(FakeInvoice, RGA_COUNT), ACCCount)
        self.assertIsNone(get_constraint(FakeInvoice, RGA_SUM))

    def test_cell_constraints02(self):
        "Several constraints."
        registry = AggregatorConstraintsRegistry().register_cell_constraints(
            ACCCount,
            ACCFieldAggregation,
        )
        self.assertEqual(2, len([*registry.cell_constraints(FakeInvoice)]))

        # ---
        get_constraint = registry.get_constraint_by_aggr_id
        self.assertIsInstance(get_constraint(FakeInvoice, RGA_COUNT), ACCCount)
        self.assertIsInstance(get_constraint(FakeInvoice, RGA_SUM),   ACCFieldAggregation)

    def test_cell_constraints03(self):
        "Duplicated constraints."
        registry = AggregatorConstraintsRegistry(
        ).register_cell_constraints(ACCCount)

        class TestACC(AggregatorCellConstraint):
            type_id = ACCCount.type_id  # <==

        with self.assertRaises(AggregatorConstraintsRegistry.RegistrationError):
            registry.register_cell_constraints(TestACC)
