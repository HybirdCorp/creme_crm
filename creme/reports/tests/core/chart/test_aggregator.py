from functools import partial

from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellFunctionField,
    EntityCellRegularField,
)
from creme.creme_core.models import (
    CustomField,
    FakeContact,
    FakeInvoice,
    FakeOrganisation,
    FieldsConfig,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.reports.constants import OrdinateAggregator
from creme.reports.core.chart.aggregator import (
    ChartAverage,
    ChartCount,
    ChartSum,
    ReportChartAggregator,
    ReportChartAggregatorRegistry,
)
from creme.reports.core.chart.cell_constraint import (
    ACCCount,
    ACCFieldAggregation,
    AggregatorCellConstraint,
    AggregatorConstraintsRegistry,
)
from creme.reports.models import ReportChart
from creme.reports.tests.base import Report, skipIfCustomReport


# TODO: test annotate() + sum, max, min
# TODO: test aggregate() + sum, max, min
@skipIfCustomReport
class AggregatorTestCase(CremeTestCase):
    def test_registry01(self):
        registry = ReportChartAggregatorRegistry()
        report = Report(ct=FakeOrganisation)
        chart = ReportChart(
            linked_report=report, ordinate_type=OrdinateAggregator.COUNT,
        )

        aggregator1 = registry[chart]
        self.assertIsInstance(aggregator1, ReportChartAggregator)
        self.assertNotEqual(type(aggregator1), ChartCount)
        self.assertEqual('??', aggregator1.verbose_name)
        self.assertEqual(_('the aggregation function is invalid.'), aggregator1.error)

        # ---
        registry(OrdinateAggregator.COUNT)(ChartCount)
        aggregator2 = registry[chart]
        self.assertIsInstance(aggregator2, ChartCount)
        self.assertIsNone(aggregator2.error)

    def test_registry02(self):
        registry = ReportChartAggregatorRegistry()
        report = Report(ct=FakeOrganisation)
        chart = ReportChart(
            linked_report=report, ordinate_type=OrdinateAggregator.SUM,
        )

        registry(OrdinateAggregator.SUM)(ChartSum)
        aggregator1 = registry[chart]
        self.assertNotEqual(type(aggregator1), ChartCount)
        self.assertEqual('??', aggregator1.verbose_name)
        self.assertEqual(_('the field does not exist any more.'), aggregator1.error)

        # ---
        chart.ordinate_cell_key = 'regular_field-capital'
        aggregator2 = registry[chart]
        self.assertIsInstance(aggregator2, ChartSum)
        self.assertIsNone(aggregator2.error)

    def test_registry03(self):
        "FieldsConfig."
        hidden_fname = 'capital'
        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        registry = ReportChartAggregatorRegistry()
        report = Report(ct=FakeOrganisation)
        chart = ReportChart(
            linked_report=report,
            ordinate_type=OrdinateAggregator.SUM,
            ordinate_cell_key=f'regular_field-{hidden_fname}',
        )

        registry(OrdinateAggregator.SUM)(ChartSum)
        aggregator = registry[chart]
        self.assertIsInstance(aggregator, ChartSum)
        self.assertEqual(_('this field should be hidden.'), aggregator.error)

    def test_count(self):
        agg1 = ChartCount()
        self.assertIsNone(agg1.error)

        # ---
        with self.assertRaises(ValueError) as cm:
            ChartCount(cell=EntityCellRegularField.build(FakeOrganisation, 'capital'))

        self.assertEqual(
            'ChartCount does not work with a cell.',
            str(cm.exception),
        )

    def test_average01(self):
        "Regular field."
        agg = ChartAverage(cell=EntityCellRegularField.build(FakeOrganisation, 'capital'))
        self.assertIsNone(agg.error)

        # ---
        with self.assertRaises(ValueError) as cm1:
            ChartAverage(cell=None)

        self.assertEqual(
            _('the field does not exist any more.'),
            str(cm1.exception)
        )

        # ---
        with self.assertRaises(ValueError) as cm2:
            ChartAverage(
                cell=EntityCellFunctionField.build(FakeOrganisation, 'get_pretty_properties'),
            )

        self.assertIn('invalid type of cell', str(cm2.exception))

    def test_average02(self):
        "Hidden regular field."
        hidden_fname = 'capital'
        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        agg = ChartAverage(cell=EntityCellRegularField.build(FakeOrganisation, hidden_fname))
        self.assertEqual(_('this field should be hidden.'), agg.error)

    def test_average03(self):
        "Custom field."
        create_cfield = partial(
            CustomField.objects.create,
            content_type=FakeContact,
            field_type=CustomField.INT,
        )
        cfield1 = create_cfield(name='Hair size')
        cfield2 = create_cfield(name='Hair brightness', is_deleted=True)

        agg1 = ChartAverage(cell=EntityCellCustomField(cfield1))
        self.assertIsNone(agg1.error)

        agg2 = ChartAverage(cell=EntityCellCustomField(cfield2))
        self.assertEqual(_('this custom field is deleted.'), agg2.error)


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
        finfo1 = cell1.field_info
        self.assertEqual(1, len(finfo1))
        self.assertEqual('capital', finfo1[0].name)

        self.assertIsNone(constraint.get_cell(cell_key='regular_field-sector'))

        # ---
        cell2 = self.get_alone_element(constraint.cells())
        self.assertIsInstance(cell2, EntityCellRegularField)
        finfo2 = cell2.field_info
        self.assertEqual(1, len(finfo2))
        self.assertEqual('capital', finfo2[0].name)

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
        cfield3 = create_cfield(
            name='Hair brightness',
            field_type=CustomField.INT,
            is_deleted=True,
        )

        constraint = ACCFieldAggregation(model=FakeContact)
        ok_cell = EntityCellCustomField(cfield1)
        self.assertIs(constraint.check_cell(ok_cell), True)

        not_aggregable_cell = EntityCellCustomField(cfield2)
        self.assertIs(constraint.check_cell(not_aggregable_cell), False)
        self.assertFalse(constraint.check_cell(
            not_aggregable_cell,
            not_hiddable_cell_keys={ok_cell.key, not_aggregable_cell.key},
        ))

        deleted_cell = EntityCellCustomField(cfield3)
        self.assertFalse(constraint.check_cell(deleted_cell))
        self.assertTrue(constraint.check_cell(
            deleted_cell,
            not_hiddable_cell_keys={ok_cell.key, deleted_cell.key},
        ))

        # ---
        cell1 = constraint.get_cell(cell_key=ok_cell.key)
        self.assertIsInstance(cell1, EntityCellCustomField)
        self.assertEqual(cfield1, cell1.custom_field)

        self.assertIsNone(constraint.get_cell(cell_key=not_aggregable_cell.key))

        # ---
        cell2 = self.get_alone_element(constraint.cells())
        self.assertIsInstance(cell2, EntityCellCustomField)
        self.assertEqual(cfield1, cell2.custom_field)

        # ---
        self.assertSetEqual(
            {ok_cell.key, deleted_cell.key},
            {
                c.key
                for c in constraint.cells(
                    not_hiddable_cell_keys={
                        not_aggregable_cell.key,
                        deleted_cell.key,
                    },
                )
            }
        )

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

        cell1 = self.get_alone_element(constraint.cells())
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
            {cell.field_info[0].name for cell in cells3},
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
        self.assertIsNone(registry.get_constraint_by_aggr_id(
            FakeInvoice, OrdinateAggregator.COUNT,
        ))

    def test_cell_constraints01(self):
        registry = AggregatorConstraintsRegistry(
        ).register_cell_constraints(ACCCount)

        constraint = self.get_alone_element(registry.cell_constraints(FakeInvoice))
        self.assertIsInstance(constraint, ACCCount)

        # ---
        get_constraint = registry.get_constraint_by_aggr_id
        self.assertIsInstance(
            get_constraint(FakeInvoice, OrdinateAggregator.COUNT),
            ACCCount,
        )
        self.assertIsNone(get_constraint(FakeInvoice, OrdinateAggregator.SUM))

    def test_cell_constraints02(self):
        "Several constraints."
        registry = AggregatorConstraintsRegistry().register_cell_constraints(
            ACCCount,
            ACCFieldAggregation,
        )
        self.assertEqual(2, len([*registry.cell_constraints(FakeInvoice)]))

        # ---
        get_constraint = registry.get_constraint_by_aggr_id
        self.assertIsInstance(
            get_constraint(FakeInvoice, OrdinateAggregator.COUNT),
            ACCCount,
        )
        self.assertIsInstance(
            get_constraint(FakeInvoice, OrdinateAggregator.SUM),
            ACCFieldAggregation,
        )

    def test_cell_constraints03(self):
        "Duplicated constraints."
        registry = AggregatorConstraintsRegistry(
        ).register_cell_constraints(ACCCount)

        class TestACC(AggregatorCellConstraint):
            type_id = ACCCount.type_id  # <==

        with self.assertRaises(AggregatorConstraintsRegistry.RegistrationError):
            registry.register_cell_constraints(TestACC)
