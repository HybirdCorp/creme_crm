from decimal import Decimal
from functools import partial

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Avg, Min, Sum
from django.utils.formats import number_format
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.gui.listview.aggregator import (
    AggregationResult,
    ListViewAggregatorRegistry,
    _ListViewAggregator,
    aggregator_registry,
)
from creme.creme_core.models import (
    FakeInvoice,
    FakeInvoiceLine,
    FakeOrganisation,
    FakeSector,
)
from creme.creme_core.tests.base import CremeTestCase


class ListViewAggregatorTestCase(CremeTestCase):
    def test_registry__register(self):
        registry = ListViewAggregatorRegistry()
        self.assertListEqual([], [*registry.models])

        field_name1 = 'total_vat'
        self.assertListEqual(
            [], [*registry.aggregators(model=FakeInvoice, field=field_name1)],
        )
        self.assertEqual(FakeInvoice, registry.model(FakeInvoice).model)

        # One aggregator ---
        label11 = 'Σ'
        registry.model(FakeInvoice).add_aggregator(
            field=field_name1, label=label11, function='Sum',
        )
        agg11 = self.get_alone_element(
            registry.aggregators(model=FakeInvoice, field=field_name1)
        )
        self.assertIsInstance(agg11, _ListViewAggregator)
        self.assertEqual(field_name1, agg11.field)
        self.assertEqual(label11,     agg11.label)
        self.assertEqual(Sum,         agg11.function)
        self.assertTupleEqual(('total_vat/Sum', Sum(field_name1)), agg11.as_args)

        # Two aggregators (same field) ---
        label12 = 'μ'
        registry.model(FakeInvoice).add_aggregator(
            field=field_name1, label=label12, function='Avg',
        )
        aggregators12 = [
            *registry.aggregators(model=FakeInvoice, field=field_name1)
        ]
        self.assertListEqual([FakeInvoice], [*registry.models])
        self.assertEqual(2, len(aggregators12))

        agg21 = aggregators12[0]
        self.assertEqual(field_name1, agg21.field)
        self.assertEqual(label11,     agg21.label)
        self.assertEqual(Sum,         agg21.function)
        self.assertTupleEqual(('total_vat/Sum', Sum(field_name1)), agg21.as_args)

        agg22 = aggregators12[1]
        self.assertEqual(field_name1, agg22.field)
        self.assertEqual(label12,     agg22.label)
        self.assertEqual(Avg,         agg22.function)
        self.assertTupleEqual(('total_vat/Avg', Avg(field_name1)), agg22.as_args)

        # Third aggregator on other field ---
        field_name2 = 'total_no_vat'
        label2 = 'Minimum'
        registry.model(FakeInvoice).add_aggregator(
            field=field_name2, label=label2, function='Min',
        )
        agg21 = self.get_alone_element(
            registry.aggregators(model=FakeInvoice, field=field_name2)
        )
        self.assertEqual(field_name2, agg21.field)
        self.assertEqual(label2,      agg21.label)
        self.assertEqual(Min,         agg21.function)
        self.assertTupleEqual(('total_no_vat/Min', Min(field_name2)), agg21.as_args)

    def test_registry__register__errors(self):
        registry = ListViewAggregatorRegistry()
        sub_registry = registry.model(FakeInvoice)

        with self.assertRaises(FieldDoesNotExist):
            sub_registry.add_aggregator(
                field='invalid', label='?', function='Sum',
            )

        with self.assertRaises(ValueError) as exc_mngr1:
            sub_registry.add_aggregator(
                field='name', label='?', function='Sum',
            )
        self.assertEqual(
            'This field is not a numeric field: name',
            str(exc_mngr1.exception),
        )

        with self.assertRaises(ValueError) as exc_mngr2:
            sub_registry.add_aggregator(
                field='total_vat', label='?', function='Invalid',
            )
        self.assertEqual(
            'This function is unknown: Invalid',
            str(exc_mngr2.exception),
        )

        with self.assertRaises(ValueError) as exc_mngr3:
            registry.model(FakeSector)
        self.assertEqual(
            '<FakeSector> is not a CremeEntity sub-class.',
            str(exc_mngr3.exception),
        )

    def test_registry__clear_model(self):
        registry = ListViewAggregatorRegistry()
        registry.model(FakeOrganisation).add_aggregator(
            field='capital', label='Average', function='Avg',
        )
        registry.model(FakeInvoice).add_aggregator(
            field='total_vat', label='Sum', function='Sum',
        )
        self.assertCountEqual([FakeOrganisation, FakeInvoice], [*registry.models])

        registry.clear_model(FakeInvoice)
        self.assertListEqual(
            [], [*registry.aggregators(model=FakeInvoice, field='total_vat')],
        )
        self.get_alone_element(
            registry.aggregators(model=FakeOrganisation, field='capital')
        )

    def test_registry__remove_aggregator(self):
        registry = ListViewAggregatorRegistry()
        registry.model(FakeInvoice).add_aggregator(
            field='total_vat', label='Sum (VAT)', function='Sum',
        ).add_aggregator(
            field='total_vat', label='Avg (vat)', function='Avg',
        ).add_aggregator(
            field='total_no_vat', label='Avg', function='Avg',
        )
        registry.model(FakeOrganisation).add_aggregator(
            field='capital', label='Sum', function='Sum',
        )

        registry.model(FakeInvoice).remove_aggregator(
            field='total_vat', function='Avg',
        )
        agg = self.get_alone_element(
            registry.aggregators(model=FakeInvoice, field='total_vat')
        )
        self.assertEqual(Sum, agg.function)

        self.get_alone_element(
            registry.aggregators(model=FakeOrganisation, field='capital')
        )

    def test_registry__remove_aggregator__errors(self):
        registry = ListViewAggregatorRegistry()

        with self.assertRaises(ValueError) as exc_mngr:
            registry.model(FakeInvoice).remove_aggregator(
                field='total_vat', function='Avg',
            )
        self.assertEqual(
            'No aggregator "Avg" registered for the field <FakeInvoice.total_vat>',
            str(exc_mngr.exception),
        )

        # ---
        registry.model(FakeOrganisation).add_aggregator(
            field='capital', label='Average', function='Avg',
        )

        with self.assertRaises(ValueError) as exc_mngr:
            registry.model(FakeOrganisation).remove_aggregator(
                field='capital', function='Sum',
            )
        self.assertEqual(
            'No aggregator "Sum" registered for the field <FakeOrganisation.capital>',
            str(exc_mngr.exception),
        )

    def test_global_registry(self):
        self.assertCountEqual(
            [
                {'label': 'Sum', 'function': Sum},
                {'label': 'Average', 'function': Avg},
            ],
            [
                {'label': agg.label, 'function': agg.function}
                for agg in aggregator_registry.aggregators(
                    model=FakeInvoice, field='total_vat',
                )
            ],
        )

    def test_aggregation_for_cells__one_aggregator(self):
        user = self.get_root_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        organisations = [
            create_orga(name='Acme #1', capital=1000),
            create_orga(name='Acme #2', capital=2000),
            create_orga(name='Acme #3'),
        ]

        registry = ListViewAggregatorRegistry()

        label = 'SUM'
        registry.model(FakeOrganisation).add_aggregator(
            field='capital', label=label, function='Sum',
        )

        # Empty ---
        qs = FakeOrganisation.objects.filter(id__in=[o.id for o in organisations])
        self.assertDictEqual({}, registry.aggregation_for_cells(queryset=qs, cells=[]))
        self.assertDictEqual(
            {},
            registry.aggregation_for_cells(
                queryset=qs,
                cells=[EntityCellRegularField.build(FakeOrganisation, 'name')],
            ),
        )

        # One aggregator ---
        aggregations = registry.aggregation_for_cells(
            queryset=qs,
            cells=[
                EntityCellRegularField.build(FakeOrganisation, 'capital'),
                EntityCellRegularField.build(FakeOrganisation, 'name'),
            ],
        )
        self.assertIsDict(aggregations, length=1)

        agg_results = aggregations.get('regular_field-capital')
        self.assertIsList(agg_results, length=1)

        agg_result = agg_results[0]
        self.assertIsInstance(agg_result, AggregationResult)

        value = 3000
        self.assertEqual(value, agg_result.value)
        self.assertEqual(
            _('{aggregation_label}: {aggregation_value}').format(
                aggregation_label=label,
                aggregation_value=number_format(value, force_grouping=True),
            ),
            agg_result.render(),
        )

    def test_aggregation_for_cells__several_aggregators(self):
        user = self.get_root_user()

        create_inv = partial(FakeInvoice.objects.create, user=user)
        invoices = [
            create_inv(name='IN#1', total_vat=Decimal('1100.11'), total_no_vat=Decimal('1000.10')),
            create_inv(name='IN#2', total_vat=Decimal('2200.22'), total_no_vat=Decimal('2000.20')),
            create_inv(name='IN#3',                               total_no_vat=Decimal('100.00')),
        ]

        registry = ListViewAggregatorRegistry()
        registry.model(FakeInvoice).add_aggregator(
            field='total_vat', label='SUM', function='Sum',
        ).add_aggregator(
            field='total_vat', label='MAX', function='Max',
        ).add_aggregator(
            field='total_no_vat', label='MIN', function='Min',
        )

        aggregations = registry.aggregation_for_cells(
            queryset=FakeInvoice.objects.filter(id__in=[i.id for i in invoices]),
            cells=[
                EntityCellRegularField.build(FakeInvoice, fname)
                for fname in ('name', 'total_vat', 'total_no_vat')
            ],
        )
        self.assertIsDict(aggregations, length=2)
        vat_results = aggregations.get('regular_field-total_vat')
        self.assertIsList(vat_results, length=2)

        vat_sum = vat_results[0]
        vat_sum_value = Decimal('3300.33')
        self.assertEqual(vat_sum_value, vat_sum.value)
        msg_fmt = _('{aggregation_label}: {aggregation_value}').format
        self.assertEqual(
            msg_fmt(
                aggregation_label='SUM',
                aggregation_value=number_format(vat_sum_value, force_grouping=True),
            ),
            vat_sum.render(),
        )

        vat_max = vat_results[1]
        vat_max_value = Decimal('2200.22')
        self.assertEqual(vat_max_value, vat_max.value)
        self.assertEqual(
            msg_fmt(
                aggregation_label='MAX',
                aggregation_value=number_format(vat_max_value, force_grouping=True),
            ),
            vat_max.render(),
        )

        no_vat_results = aggregations.get('regular_field-total_no_vat')
        self.assertIsList(no_vat_results, length=1)
        self.assertEqual(Decimal('100.00'), no_vat_results[0].value)

    def test_aggregation_for_cells__none_result(self):
        registry = ListViewAggregatorRegistry()
        registry.model(FakeOrganisation).add_aggregator(
            field='capital', label='SUM', function='Sum',
        )
        self.assertFalse(registry.aggregation_for_cells(
            queryset=FakeOrganisation.objects.none(),
            cells=[EntityCellRegularField.build(FakeOrganisation, 'capital')],
        ))

    def test_aggregation_for_cells__deep_field(self):
        user = self.get_root_user()

        create_invoice = partial(FakeInvoice.objects.create, user=user)
        invoices = [
            create_invoice(name='Invoice #1', total_vat=1000),
            create_invoice(name='Invoice #2', total_vat=2000),
            create_invoice(name='Invoice #3', total_vat=3500),
        ]

        create_line = partial(FakeInvoiceLine.objects.create, user=user)
        lines = [
            create_line(linked_invoice=invoices[0]),
            create_line(linked_invoice=invoices[2]),
        ]

        registry = ListViewAggregatorRegistry()

        deep_field = 'linked_invoice__total_vat'
        registry.model(FakeInvoiceLine).add_aggregator(
            field=deep_field, label='SUM', function='Sum',
        )
        aggregations = registry.aggregation_for_cells(
            queryset=FakeInvoiceLine.objects.filter(id__in=[line.id for line in lines]),
            cells=[EntityCellRegularField.build(FakeInvoiceLine, deep_field)],
        )
        self.assertIsDict(aggregations, length=1)

        agg_results = aggregations.get(f'regular_field-{deep_field}')
        self.assertIsList(agg_results, length=1)
        self.assertEqual(Decimal(4500), agg_results[0].value)

    def test_aggregation_for_cells__errors(self):
        registry = ListViewAggregatorRegistry()

        with self.assertRaises(ValueError) as exc_mngr:
            registry.aggregation_for_cells(
                queryset=FakeOrganisation.objects.all(),
                cells=[EntityCellRegularField.build(FakeInvoice, 'total_vat')],
            )

        self.assertEqual(
            'The cell "regular_field-total_vat" is not related to the model <FakeOrganisation>',
            str(exc_mngr.exception),
        )
