from functools import partial

from creme.creme_core.models import (
    FakeContact,
    FakeOrganisation,
    Relation,
    RelationType,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.graphs import get_graph_model
from creme.graphs.bricks import RelationChartBrick
from creme.graphs.models import RootNode

Graph = get_graph_model()


class RelationChartBrickTestCase(BrickTestCaseMixin, CremeTestCase):
    def test_default_props(self):
        brick = RelationChartBrick()
        self.assertDictEqual(
            {
                "transition": False,
                "showLegend": True,
                "nodeFillColor": "white",
                "nodeStrokeColor": "#ccc",
                "nodeTextColor": "black",
                "nodeStrokeSize": 2,
                "nodeEdgeCountStep": 4,
                "nodeSize": 5,
                "edgeColors": None,
            },
            brick.get_chart_props({}),
        )

    def test_chart_data(self):
        # self.maxDiff = None
        user = self.login_as_root_and_get()

        is_employee = RelationType.objects.builder(
            id='test-subject_employee', predicate='is employed by',
        ).symmetric(
            id='test-object_employee', predicate='has employee',
        ).get_or_create()[0]
        has_employee = is_employee.symmetric_type

        def add_employee(orga, contact):
            Relation.objects.safe_get_or_create(
                user=user, type=is_employee, subject_entity=contact, object_entity=orga,
            )

        orga = FakeOrganisation.objects.create(user=user, name='NERV')

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Rei',    last_name='Ayanami')
        contact2 = create_contact(first_name='Shinji', last_name='Ikari')
        contact3 = create_contact(first_name='Asuka',  last_name='Langley')

        add_employee(orga, contact1)
        add_employee(orga, contact2)
        add_employee(orga, contact3)

        graph = Graph.objects.create(user=user, name='Employees graph')

        node = RootNode.objects.create(graph=graph, real_entity=orga)
        node.relation_types.set([has_employee])

        self.assertCountEqual(
            [
                # Root nodes
                {
                    'id': orga.pk,
                    'label': str(orga),
                    'url': orga.get_absolute_url()
                },
                # "is employee" relationships to the Organisation
                {
                    'id': contact1.pk,
                    'parent': orga.pk,
                    'label': str(contact1),
                    'relation': {
                        'label': str(has_employee.predicate),
                        'id': has_employee.id,
                    },
                    'url': contact1.get_absolute_url(),
                }, {
                    'id': contact2.pk,
                    'parent': orga.pk,
                    'label': str(contact2),
                    'relation': {
                        'label': str(has_employee.predicate),
                        'id': has_employee.id,
                    },
                    'url': contact2.get_absolute_url(),
                }, {
                    'id': contact3.pk,
                    'parent': orga.pk,
                    'label': str(contact3),
                    'relation': {
                        'label': str(has_employee.predicate),
                        'id': has_employee.id,
                    },
                    'url': contact3.get_absolute_url(),
                },
            ],
            RelationChartBrick().get_chart_data({'object': graph, 'user': user}),
        )

    def test_chart_data_multiple_roots(self):
        # self.maxDiff = None
        user = self.login_as_root_and_get()

        is_employee = RelationType.objects.builder(
            id='test-subject_employee', predicate='is employed by',
        ).symmetric(id='test-object_employee', predicate='has employee').get_or_create()[0]
        has_employee = is_employee.symmetric_type

        is_client = RelationType.objects.builder(
            id='test-subject_client', predicate='is client of',
        ).symmetric(id='test-object_client', predicate='has client').get_or_create()[0]
        has_client = is_client.symmetric_type

        def add_employee(orga, contact):
            Relation.objects.safe_get_or_create(
                user=user, type=is_employee, subject_entity=contact, object_entity=orga,
            )

        def add_client(orga, client):
            Relation.objects.safe_get_or_create(
                user=user, type=is_client, subject_entity=client, object_entity=orga,
            )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='NERV')
        orga2 = create_orga(name='Seele')

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Rei',    last_name='Ayanami')
        contact2 = create_contact(first_name='Gondo',  last_name='Ikari')
        contact3 = create_contact(first_name='Misato', last_name='Katsuragi')

        add_employee(orga=orga1, contact=contact1)
        add_employee(orga=orga1, contact=contact2)
        add_employee(orga=orga2, contact=contact3)

        add_client(orga=orga1, client=contact3)
        add_client(orga=orga1, client=orga2)
        add_client(orga=orga2, client=contact1)

        graph = Graph.objects.create(user=user, name='Employees & clients')

        node1 = RootNode.objects.create(graph=graph, real_entity=orga1)
        node1.relation_types.set([has_employee, has_client])

        node2 = RootNode.objects.create(graph=graph, real_entity=orga2)
        node2.relation_types.set([has_client])

        self.assertCountEqual(
            [
                # Root nodes
                {
                    'id': orga1.pk,
                    'label': str(orga1),
                    'url': orga1.get_absolute_url(),
                }, {
                    'id': orga2.pk,
                    'label': str(orga2),
                    'url': orga2.get_absolute_url(),
                },
                # "is employee" relations to orga1
                {
                    'id': contact1.pk,
                    'parent': orga1.pk,
                    'label': str(contact1),
                    'relation': {
                        'label': str(has_employee.predicate),
                        'id': has_employee.id,
                    },
                    'url': contact1.get_absolute_url(),
                }, {
                    'id': contact2.pk,
                    'parent': orga1.pk,
                    'label': str(contact2),
                    'relation': {
                        'label': str(has_employee.predicate),
                        'id': has_employee.id,
                    },
                    'url': contact2.get_absolute_url(),
                },
                # "has client" relation to 'orga1'
                {
                    'id': orga2.pk,
                    'parent': orga1.pk,
                    'label': str(orga2),
                    'relation': {
                        'label': str(has_client.predicate),
                        'id': has_client.id,
                    },
                    'url': orga2.get_absolute_url(),
                }, {
                    'id': contact3.pk,
                    'parent': orga1.pk,
                    'label': str(contact3),
                    'relation': {
                        'label': str(has_client.predicate),
                        'id': has_client.id,
                    },
                    'url': contact3.get_absolute_url(),
                },
                # "has client" relation to 'orga2'
                {
                    'id': contact1.pk,
                    'parent': orga2.pk,
                    'label': str(contact1),
                    'relation': {
                        'label': str(has_client.predicate),
                        'id': has_client.id,
                    },
                    'url': contact1.get_absolute_url(),
                },
            ],
            RelationChartBrick().get_chart_data({'object': graph, 'user': user}),
        )

    def test_chart_data_orbital_relations(self):
        # self.maxDiff = None
        user = self.login_as_root_and_get()

        is_employee = RelationType.objects.builder(
            id='test-subject_employee', predicate='is employed by',
        ).symmetric(id='test-object_employee', predicate='has employee').get_or_create()[0]
        has_employee = is_employee.symmetric_type

        is_manager = RelationType.objects.builder(
            id='test-subject_manager', predicate='is managed by',
        ).symmetric(id='test-object_manager', predicate='has manager').get_or_create()[0]

        def add_employee(orga, contact):
            Relation.objects.safe_get_or_create(
                user=user, type=is_employee, subject_entity=contact, object_entity=orga,
            )

        def add_manager(manager, contact):
            Relation.objects.safe_get_or_create(
                user=user, type=is_manager, subject_entity=contact, object_entity=manager,
            )

        orga = FakeOrganisation.objects.create(user=user, name='NERV')

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Rei',    last_name='Ayanami')
        contact2 = create_contact(first_name='Asuka',  last_name='Langley')
        contact3 = create_contact(first_name='Misato', last_name='Katsuragi')

        add_employee(orga=orga, contact=contact1)
        add_employee(orga=orga, contact=contact2)
        add_employee(orga=orga, contact=contact3)

        add_manager(manager=contact3, contact=contact1)
        add_manager(manager=contact3, contact=contact2)

        graph = Graph.objects.create(user=user, name='Managers')
        graph.orbital_relation_types.set([is_manager])

        node = RootNode.objects.create(graph=graph, real_entity=orga)
        node.relation_types.set([has_employee])

        self.assertCountEqual(
            [
                # Root node
                {
                    'id': orga.pk,
                    'label': str(orga),
                    'url': orga.get_absolute_url(),
                },
                # "is employee" relationships
                {
                    'id': contact1.pk,
                    'parent': orga.pk,
                    'label': str(contact1),
                    'relation': {
                        'label': str(has_employee.predicate),
                        'id': has_employee.id,
                    },
                    'url': contact1.get_absolute_url(),
                }, {
                    'id': contact2.pk,
                    'parent': orga.pk,
                    'label': str(contact2),
                    'relation': {
                        'label': str(has_employee.predicate),
                        'id': has_employee.id,
                    },
                    'url': contact2.get_absolute_url(),
                }, {
                    'id': contact3.pk,
                    'parent': orga.pk,
                    'label': str(contact3),
                    'relation': {
                        'label': str(has_employee.predicate),
                        'id': has_employee.id,
                    },
                    'url': contact3.get_absolute_url(),
                },
                # Orbital relationships
                {
                    'id': contact3.pk,
                    'parent': contact1.pk,
                    'label': str(contact3),
                    'relation': {
                        'label': str(is_manager.predicate),
                        'id': is_manager.id,
                    },
                    'url': contact3.get_absolute_url(),
                }, {
                    'id': contact3.pk,
                    'parent': contact2.pk,
                    'label': str(contact3),
                    'relation': {
                        'label': str(is_manager.predicate),
                        'id': is_manager.id,
                    },
                    'url': contact3.get_absolute_url(),
                },
            ],
            RelationChartBrick().get_chart_data({'object': graph, 'user': user}),
        )
