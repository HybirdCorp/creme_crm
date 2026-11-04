from functools import partial

from creme.creme_core.core.soft_reference import soft_reference_registry
from creme.creme_core.models import RelationType
from creme.creme_core.tests.base import CremeTestCase
from creme.graphs.soft_references import GraphRelationTypeRefCollector

from .test_main import Graph, skipIfCustomGraph


@skipIfCustomGraph
class GraphRelationTypeRefCollectorTestCase(CremeTestCase):
    def test_collect(self):
        collector = GraphRelationTypeRefCollector()
        self.assertEqual(RelationType, collector.model)
        self.assertEqual('graphs-graph-rtype', collector.id)

        rtype1 = RelationType.objects.builder(
            id='test-subject_foo', predicate='has killed',
        ).symmetric(
            id='test-object_foo', predicate='has been killed by',
        ).get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_bar', predicate='has beaten',
        ).symmetric(
            id='test-object_bar', predicate='has been beaten by',
        ).get_or_create()[0]

        create_graph = partial(Graph.objects.create, user=self.get_root_user())
        graph1 = create_graph(name='My graph #1')
        graph1.orbital_relation_types.set([rtype1, rtype2])

        graph2 = create_graph(name='My graph #2')
        graph2.orbital_relation_types.set([rtype1])

        self.assertCountEqual([graph1, graph2], collector.collect(rtype1))
        self.assertCountEqual([graph1], collector.collect(rtype2))

    def test_global_registry(self):
        self.assertIn(
            GraphRelationTypeRefCollector,
            soft_reference_registry.collector_classes,
        )
