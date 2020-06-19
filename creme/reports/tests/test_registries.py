# -*- coding: utf-8 -*-

from functools import partial

from django.db.models import aggregates
from django.utils.translation import gettext as _

from creme.creme_core.models import CustomField, FakeContact, FakeOrganisation
from creme.creme_core.tests.base import CremeTestCase
from creme.reports.constants import RGF_FK
from creme.reports.core.graph.fetcher import (
    GraphFetcher,
    RegularFieldLinkedGraphFetcher,
    RelationLinkedGraphFetcher,
    SimpleGraphFetcher,
)
from creme.reports.graph_fetcher_registry import GraphFetcherRegistry
from creme.reports.report_aggregation_registry import (
    FieldAggregation,
    FieldAggregationRegistry,
)
from creme.reports.tests.base import Report, ReportGraph


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


class GraphFetcherRegistryTestCase(CremeTestCase):
    def test_default_class(self):
        registry = GraphFetcherRegistry(SimpleGraphFetcher)
        self.assertEqual(SimpleGraphFetcher, registry.default_class)

        class OtherSimpleGraphFetcher(GraphFetcher):
            pass

        registry.default_class = OtherSimpleGraphFetcher
        self.assertEqual(OtherSimpleGraphFetcher, registry.default_class)

    def test_register01(self):
        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph(user=user, name='Field Test', linked_report=report)

        registry = GraphFetcherRegistry(SimpleGraphFetcher)
        self.assertFalse([*registry.fetcher_classes])
        fetcher_dict = {
            'type': RGF_FK,
            'value': 'image',
        }

        with self.assertLogs(level='WARNING') as logs_manager1:
            fetcher1 = registry.get(graph=graph, fetcher_dict=fetcher_dict)

        self.assertIsInstance(fetcher1, SimpleGraphFetcher)
        self.assertEqual(
            _('Invalid volatile link ; please contact your administrator.'),
            fetcher1.error
        )
        self.assertIn(
            'invalid ID "reports-fk" for fetcher (basic fetcher is used)',
            logs_manager1.output[0]
        )

        # -----
        registry.register(
            RegularFieldLinkedGraphFetcher,
            RelationLinkedGraphFetcher,
        )
        self.assertCountEqual(
            [
                RegularFieldLinkedGraphFetcher,
                RelationLinkedGraphFetcher,
            ],
            [*registry.fetcher_classes]
        )
        fetcher2 = registry.get(graph=graph, fetcher_dict=fetcher_dict)
        self.assertIsInstance(fetcher2, RegularFieldLinkedGraphFetcher)
        self.assertIsNone(fetcher2.error)

        # Invalid dict (no type) --
        with self.assertLogs(level='WARNING') as logs_manager2:
            fetcher3 = registry.get(graph=graph, fetcher_dict={'value': 'image'})

        self.assertIsInstance(fetcher3, SimpleGraphFetcher)
        self.assertEqual(
            _('Invalid volatile link ; please contact your administrator.'),
            fetcher3.error
        )
        self.assertIn(
            'no fetcher ID given (basic fetcher is used)',
            logs_manager2.output[0]
        )

    def test_register02(self):
        "Duplicates."
        registry = GraphFetcherRegistry(SimpleGraphFetcher).register(
            RegularFieldLinkedGraphFetcher,
            RelationLinkedGraphFetcher,
        )

        class OtherFKGraphFetcher(RegularFieldLinkedGraphFetcher):
            pass

        with self.assertRaises(GraphFetcherRegistry.RegistrationError):
            registry.register(OtherFKGraphFetcher)
