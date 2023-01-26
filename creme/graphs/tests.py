from functools import partial
from pathlib import Path
from unittest import skipIf

from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import (
    FakeContact,
    FakeOrganisation,
    FileRef,
    Relation,
    RelationType,
    SetCredentials,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from . import get_graph_model, graph_model_is_custom
from .bricks import (
    OrbitalRelationTypesBrick,
    RelationChartBrick,
    RootNodesBrick,
)
from .models import RootNode

skip_graph_tests = graph_model_is_custom()
Graph = get_graph_model()

try:
    import pygraphviz  # NOQA
except ImportError:
    skip_graphviz_tests = True
else:
    skip_graphviz_tests = False


def skipIfCustomGraph(test_func):
    return skipIf(skip_graph_tests, 'Custom Graph model in use')(test_func)


@skipIfCustomGraph
class GraphsTestCase(BrickTestCaseMixin, CremeTestCase):
    def login(self, allowed_apps=('graphs',), *args, **kwargs):
        return super().login(allowed_apps=allowed_apps, *args, **kwargs)

    def test_graph_create(self):
        user = self.login()

        url = reverse('graphs__create_graph')
        self.assertGET200(url)

        name = 'Graph01'
        response = self.client.post(
            url, follow=True, data={'user': user.id, 'name': name},
        )
        self.assertNoFormError(response)

        graphs = Graph.objects.all()
        self.assertEqual(1,    len(graphs))
        self.assertEqual(name, graphs[0].name)

        # self.assertTemplateUsed(response, 'graphs/bricks/graph-hat-bar.html')

        tree = self.get_html_tree(response.content)
        self.get_brick_node(tree, brick=RootNodesBrick)
        self.get_brick_node(tree, brick=OrbitalRelationTypesBrick)

    def test_graph_edit(self):
        user = self.login()

        name = 'Nodz-a-lapalooza'
        graph = Graph.objects.create(user=user, name=name)

        url = graph.get_edit_absolute_url()
        self.assertGET200(url)

        name += '_edited'
        response = self.client.post(
            url, follow=True, data={'user': user.id, 'name': name},
        )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(graph).name)

    def test_listview(self):
        user = self.login()

        create_graph = partial(Graph.objects.create, user=user)
        graph1 = create_graph(name='Graph01')
        graph2 = create_graph(name='Graph02')

        response = self.assertGET200(Graph.get_lv_absolute_url())

        with self.assertNoException():
            graphs = response.context['page_obj'].object_list

        self.assertIn(graph1, graphs)
        self.assertIn(graph2, graphs)

    def test_relation_types01(self):
        user = self.login()

        graph = Graph.objects.create(user=user, name='Graph01')
        self.assertEqual(0, graph.orbital_relation_types.count())

        rtype_create = RelationType.objects.smart_update_or_create
        rtype01 = rtype_create(
            ('test-subject_love', 'loves'),
            ('test-object_love',  'is loved to'),
        )[0]
        rtype02 = rtype_create(
            ('test-subject_hate', 'hates'),
            ('test-object_hate',  'is hated to'),
        )[0]

        disabled_rtype = rtype_create(
            ('test-subject_disabled', 'disabled'),
            ('test-object_disabled',  'whatever'),
        )[0]
        disabled_rtype.enabled = False
        disabled_rtype.save()

        url = reverse('graphs__add_rtypes', args=(graph.id,))
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/link-popup.html')

        context = response1.context
        self.assertEqual(
            _('Add relation types to «{entity}»').format(entity=graph),
            context.get('title'),
        )
        self.assertEqual(_('Save'), context.get('submit_label'))

        with self.assertNoException():
            rtypes_f = context['form'].fields['relation_types']

        allowed_rtype_ids = {*rtypes_f.queryset.values_list('id', flat=True)}
        self.assertIn(rtype01.id, allowed_rtype_ids)
        self.assertIn(rtype02.id, allowed_rtype_ids)
        self.assertNotIn(disabled_rtype.id, allowed_rtype_ids)

        # ---
        rtype_ids = [rtype01.id, rtype02.id]

        self.assertNoFormError(self.client.post(url, data={'relation_types': rtype_ids}))

        rtypes = graph.orbital_relation_types.all()
        self.assertEqual(2,             len(rtypes))
        self.assertEqual({*rtype_ids}, {rt.id for rt in rtypes})

        self.assertPOST200(
            reverse('graphs__remove_rtype', args=(graph.id,)),
            data={'id': rtype01.id},
            follow=True,
        )
        self.assertListEqual(
            [rtype02.id],
            [rt.id for rt in graph.orbital_relation_types.all()]
        )

    def test_relation_types02(self):
        self.login(is_superuser=False)

        graph = Graph.objects.create(user=self.other_user, name='Graph01')
        self.assertGET403(reverse('graphs__add_rtypes', args=(graph.id,)))

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'loves'),
            ('test-object_love', 'is loved to'),
        )[0]
        graph.orbital_relation_types.add(rtype)
        self.assertPOST403(
            reverse('graphs__remove_rtype', args=(graph.id,)),
            data={'id': rtype.id},
            follow=True,
        )

    @skipIf(skip_graphviz_tests, 'Pygraphviz is not installed (are you under Wind*ws ??')
    def test_download01(self):
        user = self.login()

        contact = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        orga = FakeOrganisation.objects.create(user=user, name='NERV')

        # Tests an encoding error, pygraphviz supports unicode...
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_hate', 'déteste'),
            ('test-object_hate',  'est détesté par'),
        )[0]
        Relation.objects.create(
            user=user,
            subject_entity=contact,
            type=rtype,
            object_entity=orga,
        )

        graph = Graph.objects.create(user=user, name='Graph01')
        url = reverse('graphs__add_roots', args=(graph.id,))
        self.assertGET200(url)

        response = self.client.post(
            url,
            data={
                'entities': self.formfield_value_multi_generic_entity(
                    contact, orga,
                ),
                'relation_types': [rtype.id],
            },
        )
        self.assertNoFormError(response)

        url = reverse('graphs__add_rtypes', args=(graph.id,))
        self.assertGET200(url)
        self.assertNoFormError(
            self.client.post(url, data={'relation_types': [rtype.id]}),
        )

        existing_fileref_ids = [*FileRef.objects.values_list('id', flat=True)]

        response = self.assertGET200(
            reverse('graphs__dl_image', args=(graph.id,)),
            follow=True,
        )
        self.assertEqual('image/png', response['Content-Type'])

        filerefs = FileRef.objects.exclude(id__in=existing_fileref_ids)
        self.assertEqual(1, len(filerefs))

        fileref = filerefs[0]
        self.assertTrue(fileref.temporary)
        self.assertEqual(f'graph_{graph.id}.png', fileref.basename)
        self.assertEqual(user, fileref.user)

        fullpath = Path(fileref.filedata.path)
        self.assertTrue(fullpath.exists(), f'<{fullpath}> does not exists ?!')
        self.assertEqual(Path(settings.MEDIA_ROOT, 'graphs'), fullpath.parent)
        self.assertEqual(
            f'attachment; filename="{fullpath.name}"',
            response['Content-Disposition'],
        )

        # Consume stream to avoid error message "ResourceWarning: unclosed file..."
        _ = [*response.streaming_content]

    def test_add_rootnode(self):
        user = self.login()

        contact = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        orga = FakeOrganisation.objects.create(user=user, name='NERV')

        # TODO: factorise
        rtype_create = RelationType.objects.smart_update_or_create
        rtype01 = rtype_create(
            ('test-subject_love', 'loves'),
            ('test-object_love',  'is loved to'),
        )[0]
        rtype02 = rtype_create(
            ('test-subject_hate', 'hates'),
            ('test-object_hate',  'is hated to'),
        )[0]
        disabled_rtype = rtype_create(
            ('test-subject_disabled', 'disabled'),
            ('test-object_disabled',  'what ever'),
        )[0]
        disabled_rtype.enabled = False
        disabled_rtype.save()

        graph = Graph.objects.create(user=user, name='Graph01')
        url = reverse('graphs__add_roots', args=(graph.id,))

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(
            _('Add root nodes to «{entity}»').format(entity=graph),
            context.get('title'),
        )
        self.assertEqual(_('Save'), context.get('submit_label'))

        with self.assertNoException():
            rtypes_f = context['form'].fields['relation_types']

        rtype_ids = {*rtypes_f.queryset.values_list('id', flat=True)}
        self.assertIn(rtype01.id, rtype_ids)
        self.assertIn(rtype02.id, rtype_ids)
        self.assertNotIn(disabled_rtype.id, rtype_ids)

        # ----
        response = self.client.post(
            url,
            data={
                'entities': self.formfield_value_multi_generic_entity(
                    contact, orga,
                ),
                'relation_types': [rtype01.id, rtype02.id],
            },
        )
        self.assertNoFormError(response)

        rnodes = RootNode.objects.filter(graph=graph).order_by('id')
        self.assertEqual(2, len(rnodes))

        self.assertSetEqual(
            {FakeContact, FakeOrganisation},
            {rnode.entity_ctype.model_class() for rnode in rnodes},
        )
        entities = {contact, orga}
        self.assertSetEqual(
            entities, {rnode.entity.get_real_entity() for rnode in rnodes},
        )
        self.assertSetEqual(
            entities, {rnode.real_entity for rnode in rnodes},
        )
        self.assertSetEqual(
            {rtype01, rtype02}, {*rnodes[0].relation_types.all()},
        )

        # Delete
        rnode = rnodes[1]
        url = reverse('graphs__remove_root')
        data = {'id': rnode.id}
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data, follow=True)
        self.assertDoesNotExist(rnode)

    def test_edit_rootnode01(self):
        user = self.login()
        orga = FakeOrganisation.objects.create(user=user, name='NERV')

        # TODO: factorise
        rtype_create = RelationType.objects.smart_update_or_create
        rtype01 = rtype_create(
            ('test-subject_love', 'loves'),
            ('test-object_love',  'is loved to'),
        )[0]
        rtype02 = rtype_create(
            ('test-subject_hate', 'hates'),
            ('test-object_hate',  'is hated to'),
        )[0]
        disabled_rtype = rtype_create(
            ('test-subject_disabled', 'disabled'),
            ('test-object_disabled',  'what ever'),
        )[0]
        disabled_rtype.enabled = False
        disabled_rtype.save()

        graph = Graph.objects.create(user=user, name='Graph01')
        # rnode = RootNode.objects.create(graph=graph, entity=orga)
        rnode = RootNode.objects.create(graph=graph, real_entity=orga)
        rnode.relation_types.set([rtype01])

        url = rnode.get_edit_absolute_url()
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(
            _('Edit root node for «{entity}»').format(entity=graph),
            response.context.get('title'),
        )

        with self.assertNoException():
            rtypes_f = response.context['form'].fields['relation_types']

        rtype_ids = {*rtypes_f.queryset.values_list('id', flat=True)}
        self.assertIn(rtype01.id, rtype_ids)
        self.assertIn(rtype02.id, rtype_ids)
        self.assertNotIn(disabled_rtype.id, rtype_ids)
        self.assertCountEqual([rtype01.id], rtypes_f.initial)

        # ---
        self.assertNoFormError(
            self.client.post(url, data={'relation_types': [rtype01.id, rtype02.id]})
        )
        self.assertSetEqual({rtype01, rtype02}, {*rnode.relation_types.all()})

    def test_edit_rootnode02(self):
        "Disabled relation types are already selected => still proposed."
        user = self.login()
        orga = FakeOrganisation.objects.create(user=user, name='NERV')

        rtype_create = RelationType.objects.smart_update_or_create
        rtype01 = rtype_create(
            ('test-subject_love', 'loves'),
            ('test-object_love',  'is loved to'),
        )[0]
        disabled_rtype = rtype_create(
            ('test-subject_disabled', 'disabled'),
            ('test-object_disabled',  'what ever'),
        )[0]
        disabled_rtype.enabled = False
        disabled_rtype.save()

        graph = Graph.objects.create(user=user, name='Graph01')
        rnode = RootNode.objects.create(graph=graph, real_entity=orga)
        rnode.relation_types.set([disabled_rtype])

        response = self.assertGET200(rnode.get_edit_absolute_url())

        with self.assertNoException():
            rtypes_f = response.context['form'].fields['relation_types']

        rtype_ids = {*rtypes_f.queryset.values_list('id', flat=True)}
        self.assertIn(rtype01.id, rtype_ids)
        self.assertIn(disabled_rtype.id, rtype_ids)

    def test_delete_rootnode01(self):
        "Not superuser."
        user = self.login(is_superuser=False)

        SetCredentials.objects.create(
            role=user.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE,
            set_type=SetCredentials.ESET_OWN,
        )

        orga = FakeOrganisation.objects.create(user=user, name='NERV')
        graph = Graph.objects.create(user=user, name='Graph01')
        # rnode = RootNode.objects.create(graph=graph, entity=orga)
        rnode = RootNode.objects.create(graph=graph, real_entity=orga)

        self.assertPOST200(
            reverse('graphs__remove_root'),
            data={'id': rnode.id},
            follow=True,
        )
        self.assertDoesNotExist(rnode)

    def test_delete_rootnode02(self):
        "Not superuser + cannot change Graph => error."
        user = self.login(is_superuser=False)

        SetCredentials.objects.create(
            role=user.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE,
            set_type=SetCredentials.ESET_OWN,
        )

        orga = FakeOrganisation.objects.create(user=user, name='NERV')
        graph = Graph.objects.create(user=self.other_user, name='Graph01')
        # rnode = RootNode.objects.create(graph=graph, entity=orga)
        rnode = RootNode.objects.create(graph=graph, real_entity=orga)

        self.assertPOST403(
            reverse('graphs__remove_root'),
            data={'id': rnode.id},
            follow=True,
        )
        self.assertStillExists(rnode)


class RelationChartBrickTestCase(BrickTestCaseMixin, CremeTestCase):
    def test_default_props(self):
        brick = RelationChartBrick()
        self.assertEqual(brick.get_chart_props({}), {
            "transition": False,
            "showLegend": True,
            "nodeFillColor": "white",
            "nodeStrokeColor": "#ccc",
            "nodeTextColor": "black",
            "nodeStrokeSize": 2,
            "nodeEdgeCountStep": 4,
            "nodeSize": 5,
            "edgeColors": None,
        })

    def test_chart_data(self):
        self.maxDiff = None

        user = self.login()

        is_employee, has_employee = RelationType.objects.smart_update_or_create(
            ('test-subject_employee', 'is employed by'),
            ('test-object_employee',  'has employee'),
        )

        def add_employee(orga, contact):
            Relation.objects.safe_get_or_create(
                user=user, type=is_employee, subject_entity=contact, object_entity=orga
            )

        orga_A = FakeOrganisation.objects.create(user=user, name='Orga A')

        contact_A = FakeContact.objects.create(user=user, first_name='John', last_name='A')
        contact_B = FakeContact.objects.create(user=user, first_name='John', last_name='B')
        contact_C = FakeContact.objects.create(user=user, first_name='John', last_name='C')

        add_employee(orga_A, contact_A)
        add_employee(orga_A, contact_B)
        add_employee(orga_A, contact_C)

        graph = Graph.objects.create(user=user, name='Graph01')

        node = RootNode.objects.create(graph=graph, real_entity=orga_A)
        node.relation_types.set([has_employee])

        data = RelationChartBrick().get_chart_data({
            'object': graph,
            'user': user
        })

        self.assertEqual(sorted(data, key=str), sorted([
            # First the root nodes
            {
                'id': orga_A.pk,
                'label': str(orga_A),
                'url': orga_A.get_absolute_url()
            },
            # "is employee" relations to the Orga A
            {
                'id': contact_A.pk,
                'parent': orga_A.pk,
                'label': str(contact_A),
                'relation': {
                    'label': str(has_employee.predicate),
                    'id': has_employee.id,
                },
                'url': contact_A.get_absolute_url()
            }, {
                'id': contact_B.pk,
                'parent': orga_A.pk,
                'label': str(contact_B),
                'relation': {
                    'label': str(has_employee.predicate),
                    'id': has_employee.id,
                },
                'url': contact_B.get_absolute_url()
            }, {
                'id': contact_C.pk,
                'parent': orga_A.pk,
                'label': str(contact_C),
                'relation': {
                    'label': str(has_employee.predicate),
                    'id': has_employee.id,
                },
                'url': contact_C.get_absolute_url()
            }
        ], key=str))

    def test_chart_data_multiple_roots(self):
        self.maxDiff = None

        user = self.login()

        is_employee, has_employee = RelationType.objects.smart_update_or_create(
            ('test-subject_employee', 'is employed by'),
            ('test-object_employee',  'has employee'),
        )

        is_client, has_client = RelationType.objects.smart_update_or_create(
            ('test-subject_client', 'is client of'),
            ('test-object_client',  'has client'),
        )

        def add_employee(orga, contact):
            Relation.objects.safe_get_or_create(
                user=user, type=is_employee, subject_entity=contact, object_entity=orga
            )

        def add_client(orga, client):
            Relation.objects.safe_get_or_create(
                user=user, type=is_client, subject_entity=client, object_entity=orga
            )

        orga_A = FakeOrganisation.objects.create(user=user, name='Orga A')
        orga_B = FakeOrganisation.objects.create(user=user, name='Orga B')

        contact_A = FakeContact.objects.create(user=user, first_name='John', last_name='A')
        contact_B = FakeContact.objects.create(user=user, first_name='John', last_name='B')
        contact_C = FakeContact.objects.create(user=user, first_name='John', last_name='C')

        add_employee(orga_A, contact_A)
        add_employee(orga_A, contact_B)
        add_employee(orga_B, contact_C)

        add_client(orga_A, contact_C)
        add_client(orga_A, orga_B)
        add_client(orga_B, contact_A)

        graph = Graph.objects.create(user=user, name='Graph01')

        node = RootNode.objects.create(graph=graph, real_entity=orga_A)
        node.relation_types.set([has_employee, has_client])

        node = RootNode.objects.create(graph=graph, real_entity=orga_B)
        node.relation_types.set([has_client])

        data = RelationChartBrick().get_chart_data({
            'object': graph,
            'user': user
        })

        self.assertEqual(sorted(data, key=str), sorted([
            # First the root nodes
            {
                'id': orga_A.pk,
                'label': str(orga_A),
                'url': orga_A.get_absolute_url()
            }, {
                'id': orga_B.pk,
                'label': str(orga_B),
                'url': orga_B.get_absolute_url()
            },
            # "is employee" relations to the Orga A
            {
                'id': contact_A.pk,
                'parent': orga_A.pk,
                'label': str(contact_A),
                'relation': {
                    'label': str(has_employee.predicate),
                    'id': has_employee.id,
                },
                'url': contact_A.get_absolute_url()
            }, {
                'id': contact_B.pk,
                'parent': orga_A.pk,
                'label': str(contact_B),
                'relation': {
                    'label': str(has_employee.predicate),
                    'id': has_employee.id,
                },
                'url': contact_B.get_absolute_url()
            },
            # "has client" relation to the Orga A
            {
                'id': orga_B.pk,
                'parent': orga_A.pk,
                'label': str(orga_B),
                'relation': {
                    'label': str(has_client.predicate),
                    'id': has_client.id,
                },
                'url': orga_B.get_absolute_url()
            },
            {
                'id': contact_C.pk,
                'parent': orga_A.pk,
                'label': str(contact_C),
                'relation': {
                    'label': str(has_client.predicate),
                    'id': has_client.id,
                },
                'url': contact_C.get_absolute_url()
            },
            # "has client" relation to the Orga B
            {
                'id': contact_A.pk,
                'parent': orga_B.pk,
                'label': str(contact_A),
                'relation': {
                    'label': str(has_client.predicate),
                    'id': has_client.id,
                },
                'url': contact_A.get_absolute_url()
            }
        ], key=str))

    def test_chart_data_orbital_relations(self):
        self.maxDiff = None

        user = self.login()

        is_employee, has_employee = RelationType.objects.smart_update_or_create(
            ('test-subject_employee', 'is employed by'),
            ('test-object_employee',  'has employee'),
        )

        is_manager, has_manager = RelationType.objects.smart_update_or_create(
            ('test-subject_manager', 'is managed by'),
            ('test-object_manager',  'has manager'),
        )

        def add_employee(orga, contact):
            Relation.objects.safe_get_or_create(
                user=user, type=is_employee, subject_entity=contact, object_entity=orga
            )

        def add_manager(manager, contact):
            Relation.objects.safe_get_or_create(
                user=user, type=is_manager, subject_entity=contact, object_entity=manager
            )

        orga_A = FakeOrganisation.objects.create(user=user, name='Orga A')

        contact_A = FakeContact.objects.create(user=user, first_name='John', last_name='A')
        contact_B = FakeContact.objects.create(user=user, first_name='John', last_name='B')
        contact_C = FakeContact.objects.create(user=user, first_name='John', last_name='C')

        add_employee(orga_A, contact_A)
        add_employee(orga_A, contact_B)
        add_employee(orga_A, contact_C)

        add_manager(contact_C, contact_A)
        add_manager(contact_C, contact_B)

        graph = Graph.objects.create(user=user, name='Graph01')

        node = RootNode.objects.create(graph=graph, real_entity=orga_A)
        node.relation_types.set([has_employee])
        graph.orbital_relation_types.set([is_manager])

        data = RelationChartBrick().get_chart_data({
            'object': graph,
            'user': user
        })

        self.assertEqual(sorted(data, key=str), sorted([
            # First the root nodes
            {
                'id': orga_A.pk,
                'label': str(orga_A),
                'url': orga_A.get_absolute_url()
            },
            # "is employee" relations to the Orga A
            {
                'id': contact_A.pk,
                'parent': orga_A.pk,
                'label': str(contact_A),
                'relation': {
                    'label': str(has_employee.predicate),
                    'id': has_employee.id,
                },
                'url': contact_A.get_absolute_url()
            }, {
                'id': contact_B.pk,
                'parent': orga_A.pk,
                'label': str(contact_B),
                'relation': {
                    'label': str(has_employee.predicate),
                    'id': has_employee.id,
                },
                'url': contact_B.get_absolute_url()
            }, {
                'id': contact_C.pk,
                'parent': orga_A.pk,
                'label': str(contact_C),
                'relation': {
                    'label': str(has_employee.predicate),
                    'id': has_employee.id,
                },
                'url': contact_C.get_absolute_url()
            }, {
                'id': contact_C.pk,
                'parent': contact_A.pk,
                'label': str(contact_C),
                'relation': {
                    'label': str(is_manager.predicate),
                    'id': is_manager.id,
                },
                'url': contact_C.get_absolute_url()
            }, {
                'id': contact_C.pk,
                'parent': contact_B.pk,
                'label': str(contact_C),
                'relation': {
                    'label': str(is_manager.predicate),
                    'id': is_manager.id,
                },
                'url': contact_C.get_absolute_url()
            }
        ], key=str))
