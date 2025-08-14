from functools import partial

from django.db.models import aggregates

from creme.creme_core.models import CustomField, FakeOrganisation
from creme.creme_core.tests.base import CremeTestCase
from creme.reports.report_aggregation_registry import (
    FieldAggregation,
    FieldAggregationRegistry,
)


class FieldAggregationRegistryTestCase(CremeTestCase):
    def test_empty(self):
        registry = FieldAggregationRegistry()
        self.assertListEqual([], [*registry.aggregations])
        self.assertIsNone(registry.get('avg'))

    def test_register(self):
        name1 = 'avg'
        name2 = 'min'
        agg1 = FieldAggregation(name1, aggregates.Avg, '{}__avg', 'Average')
        agg2 = FieldAggregation(name2, aggregates.Avg, '{}__min', 'Minimum')
        registry = FieldAggregationRegistry().register(agg1).register(agg2)

        self.assertIs(agg1, registry.get(name1))
        self.assertIs(agg2, registry.get(name2))
        self.assertIsNone(registry.get('sum'))

        self.assertCountEqual([agg1, agg2], [*registry.aggregations])

    def test_is_regular_field_allowed(self):
        is_allowed = FieldAggregationRegistry().is_regular_field_allowed
        get_field = FakeOrganisation._meta.get_field
        self.assertIs(is_allowed(get_field('capital')), True)
        self.assertIs(is_allowed(get_field('name')), False)

    def test_is_custom_field_allowed(self):
        is_allowed = FieldAggregationRegistry().is_custom_field_allowed

        create_cf = partial(CustomField.objects.create, content_type=FakeOrganisation)
        cf1 = create_cf(name='Integer ID', field_type=CustomField.INT)
        cf2 = create_cf(name='String ID',  field_type=CustomField.STR)

        self.assertIs(is_allowed(cf1), True)
        self.assertIs(is_allowed(cf2), False)
