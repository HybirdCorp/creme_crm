from functools import partial
from unittest import skipIf

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.models import FakeContact, FakeOrganisation, RelationType
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.graphs import get_graph_model, graph_model_is_custom
from creme.graphs.bricks import OrbitalRelationTypesBrick, RootNodesBrick
from creme.graphs.models import RootNode

skip_graph_tests = graph_model_is_custom()
Graph = get_graph_model()


def skipIfCustomGraph(test_func):
    return skipIf(skip_graph_tests, 'Custom Graph model in use')(test_func)


@skipIfCustomGraph
class GraphsTestCase(BrickTestCaseMixin, CremeTestCase):
    def login_as_graphs_user(self, *, allowed_apps=(), **kwargs):
        return super().login_as_standard(
            allowed_apps=['graphs', *allowed_apps],
            **kwargs
        )

    def test_graph_create(self):
        user = self.login_as_root_and_get()

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

        tree = self.get_html_tree(response.content)
        self.get_brick_node(tree, brick=RootNodesBrick)
        self.get_brick_node(tree, brick=OrbitalRelationTypesBrick)

    def test_graph_edit(self):
        user = self.login_as_root_and_get()

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
        user = self.login_as_root_and_get()

        create_graph = partial(Graph.objects.create, user=user)
        graph1 = create_graph(name='Graph01')
        graph2 = create_graph(name='Graph02')

        response = self.assertGET200(Graph.get_lv_absolute_url())

        with self.assertNoException():
            graphs = response.context['page_obj'].object_list

        self.assertIn(graph1, graphs)
        self.assertIn(graph2, graphs)

    def test_relation_types01(self):
        user = self.login_as_root_and_get()

        graph = Graph.objects.create(user=user, name='Graph01')
        self.assertEqual(0, graph.orbital_relation_types.count())

        rtype1 = RelationType.objects.builder(
            id='test-subject_love', predicate='loves',
        ).symmetric(id='test-object_love', predicate='is loved to').get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_hate', predicate='hates',
        ).symmetric(id='test-object_hate', predicate='is hated to').get_or_create()[0]

        disabled_rtype = RelationType.objects.builder(
            id='test-subject_disabled', predicate='disabled',
            enabled=False,
        ).symmetric(id='test-object_disabled', predicate='whatever').get_or_create()[0]

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
        self.assertIn(rtype1.id, allowed_rtype_ids)
        self.assertIn(rtype2.id, allowed_rtype_ids)
        self.assertNotIn(disabled_rtype.id, allowed_rtype_ids)

        # ---
        self.assertNoFormError(
            self.client.post(url, data={'relation_types': [rtype1.id, rtype2.id]})
        )
        self.assertCountEqual([rtype1, rtype2], graph.orbital_relation_types.all())

        self.assertPOST200(
            reverse('graphs__remove_rtype', args=(graph.id,)),
            data={'id': rtype1.id},
            follow=True,
        )
        self.assertListEqual(
            [rtype2.id], [rt.id for rt in graph.orbital_relation_types.all()],
        )

    def test_relation_types02(self):
        self.login_as_graphs_user()

        graph = Graph.objects.create(user=self.get_root_user(), name='Graph01')
        self.assertGET403(reverse('graphs__add_rtypes', args=(graph.id,)))

        rtype = RelationType.objects.builder(
            id='test-subject_love', predicate='loves',
        ).symmetric(id='test-object_love', predicate='is loved to').get_or_create()[0]

        graph.orbital_relation_types.add(rtype)
        self.assertPOST403(
            reverse('graphs__remove_rtype', args=(graph.id,)),
            data={'id': rtype.id},
            follow=True,
        )

    def test_add_rootnode(self):
        user = self.login_as_root_and_get()

        contact = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        orga = FakeOrganisation.objects.create(user=user, name='NERV')

        # TODO: factorise
        rtype1 = RelationType.objects.builder(
            id='test-subject_love', predicate='loves',
        ).symmetric(id='test-object_love', predicate='is loved to').get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_hate', predicate='hates',
        ).symmetric(id='test-object_hate', predicate='is hated to').get_or_create()[0]
        disabled_rtype = RelationType.objects.builder(
            id='test-subject_disabled', predicate='disabled',
            enabled=False,
        ).symmetric(id='test-object_disabled', predicate='what ever').get_or_create()[0]

        graph = Graph.objects.create(user=user, name='Graph01')
        url = reverse('graphs__add_roots', args=(graph.id,))

        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/link-popup.html')

        context = response1.context
        self.assertEqual(
            _('Add root nodes to «{entity}»').format(entity=graph),
            context.get('title'),
        )
        self.assertEqual(_('Save'), context.get('submit_label'))

        with self.assertNoException():
            rtypes_f = context['form'].fields['relation_types']

        rtype_ids = {*rtypes_f.queryset.values_list('id', flat=True)}
        self.assertIn(rtype1.id, rtype_ids)
        self.assertIn(rtype2.id, rtype_ids)
        self.assertNotIn(disabled_rtype.id, rtype_ids)

        # ----
        self.assertNoFormError(self.client.post(
            url,
            data={
                'entities': self.formfield_value_multi_generic_entity(
                    contact, orga,
                ),
                'relation_types': [rtype1.id, rtype2.id],
            },
        ))

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
        self.assertCountEqual(
            [rtype1, rtype2], rnodes[0].relation_types.all(),
        )

        # Delete
        rnode = rnodes[1]
        url = reverse('graphs__remove_root')
        data = {'id': rnode.id}
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data, follow=True)
        self.assertDoesNotExist(rnode)

    def test_edit_rootnode01(self):
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='NERV')

        # TODO: factorise
        rtype1 = RelationType.objects.builder(
            id='test-subject_love', predicate='loves',
        ).symmetric(id='test-object_love', predicate='is loved to').get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_hate', predicate='hates',
        ).symmetric(id='test-object_hate', predicate='is hated to').get_or_create()[0]
        disabled_rtype = RelationType.objects.builder(
            id='test-subject_disabled', predicate='disabled',
            enabled=False,
        ).symmetric(id='test-object_disabled', predicate='what ever').get_or_create()[0]

        graph = Graph.objects.create(user=user, name='Graph01')
        rnode = RootNode.objects.create(graph=graph, real_entity=orga)
        rnode.relation_types.set([rtype1])

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
        self.assertIn(rtype1.id, rtype_ids)
        self.assertIn(rtype2.id, rtype_ids)
        self.assertNotIn(disabled_rtype.id, rtype_ids)
        self.assertCountEqual([rtype1.id], rtypes_f.initial)

        # ---
        self.assertNoFormError(
            self.client.post(url, data={'relation_types': [rtype1.id, rtype2.id]})
        )
        self.assertCountEqual([rtype1, rtype2], rnode.relation_types.all())

    def test_edit_rootnode02(self):
        "Disabled relation types are already selected => still proposed."
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='NERV')

        rtype1 = RelationType.objects.builder(
            id='test-subject_love', predicate='loves',
        ).symmetric(id='test-object_love', predicate='is loved to').get_or_create()[0]
        disabled_rtype = RelationType.objects.builder(
            id='test-subject_disabled', predicate='disabled',
            enabled=False,
        ).symmetric(id='test-object_disabled', predicate='what ever').get_or_create()[0]

        graph = Graph.objects.create(user=user, name='Graph01')
        rnode = RootNode.objects.create(graph=graph, real_entity=orga)
        rnode.relation_types.set([disabled_rtype])

        response = self.assertGET200(rnode.get_edit_absolute_url())

        with self.assertNoException():
            rtypes_f = response.context['form'].fields['relation_types']

        rtype_ids = {*rtypes_f.queryset.values_list('id', flat=True)}
        self.assertIn(rtype1.id, rtype_ids)
        self.assertIn(disabled_rtype.id, rtype_ids)

    def test_delete_rootnode01(self):
        "Not superuser."
        user = self.login_as_graphs_user()
        self.add_credentials(user.role, own=['VIEW', 'CHANGE'])

        orga = FakeOrganisation.objects.create(user=user, name='NERV')
        graph = Graph.objects.create(user=user, name='Graph01')
        rnode = RootNode.objects.create(graph=graph, real_entity=orga)

        self.assertPOST200(
            reverse('graphs__remove_root'),
            data={'id': rnode.id},
            follow=True,
        )
        self.assertDoesNotExist(rnode)

    def test_delete_rootnode02(self):
        "Not superuser + cannot change Graph => error."
        user = self.login_as_graphs_user()
        self.add_credentials(user.role, own=['VIEW', 'CHANGE'])

        orga = FakeOrganisation.objects.create(user=user, name='NERV')
        graph = Graph.objects.create(user=self.get_root_user(), name='Graph01')
        rnode = RootNode.objects.create(graph=graph, real_entity=orga)

        self.assertPOST403(
            reverse('graphs__remove_root'),
            data={'id': rnode.id},
            follow=True,
        )
        self.assertStillExists(rnode)

    def test_clone(self):
        user = self.login_as_root_and_get()

        rtype1 = RelationType.objects.builder(
            id='test-subject_employee', predicate='is employed by',
        ).symmetric(id='test-object_employee', predicate='has employee').get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_pilot', predicate='is a pilot from',
        ).symmetric(id='test-object_pilot', predicate='has pilot').get_or_create()[0]

        graph = Graph.objects.create(user=user, name='Graph')
        graph.orbital_relation_types.add(rtype1)

        orga = FakeOrganisation.objects.create(user=user, name='NERV')
        rnode = RootNode.objects.create(graph=graph, real_entity=orga)
        rnode.relation_types.set([rtype2])

        cloned_graph = self.clone(graph)
        self.assertIsInstance(cloned_graph, Graph)
        self.assertNotEqual(graph.pk, cloned_graph.pk)
        self.assertEqual(graph.name, cloned_graph.name)
        self.assertCountEqual([rtype1], cloned_graph.orbital_relation_types.all())

        cloned_node = self.get_alone_element(cloned_graph.roots.all())
        self.assertEqual(orga, cloned_node.real_entity)
        self.assertCountEqual([rtype2], cloned_node.relation_types.all())

    # def test_clone__method(self):  # DEPRECATED
    #     user = self.get_root_user()
    #
    #     rtype1 = RelationType.objects.smart_update_or_create(
    #         ('test-subject_employee', 'is employed by'),
    #         ('test-object_employee',  'has employee'),
    #     )[0]
    #     rtype2 = RelationType.objects.smart_update_or_create(
    #         ('test-subject_pilot', 'is a pilot from'),
    #         ('test-object_pilot',  'has pilot'),
    #     )[0]
    #
    #     graph = Graph.objects.create(user=user, name='Graph')
    #     graph.orbital_relation_types.add(rtype1)
    #
    #     orga = FakeOrganisation.objects.create(user=user, name='NERV')
    #     rnode = RootNode.objects.create(graph=graph, real_entity=orga)
    #     rnode.relation_types.set([rtype2])
    #
    #     cloned_graph = graph.clone()
    #     self.assertIsInstance(cloned_graph, Graph)
    #     self.assertNotEqual(graph.pk, cloned_graph.pk)
    #     self.assertEqual(graph.name, cloned_graph.name)
    #     self.assertCountEqual([rtype1], cloned_graph.orbital_relation_types.all())
    #
    #     cloned_node = self.get_alone_element(cloned_graph.roots.all())
    #     self.assertEqual(orga, cloned_node.real_entity)
    #     self.assertCountEqual([rtype2], cloned_node.relation_types.all())
