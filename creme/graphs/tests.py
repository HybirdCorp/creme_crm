# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.utils.unittest.case import skipIf

    from creme.creme_core.models import RelationType, Relation
    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons.models import Contact, Organisation

    from .models import *
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))

skip_graphviz_test = False

try:
    import pygraphviz
except ImportError:
    skip_graphviz_test = True


class GraphsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'graphs')

    def login(self, is_superuser=True):
        super(GraphsTestCase, self).login(is_superuser, allowed_apps=['graphs'])

    def test_portal(self):
        self.login()
        self.assertGET200('/graphs/')

    def test_graph_create(self):
        self.login()

        url = '/graphs/graph/add'
        self.assertGET200(url)

        name = 'Graph01'
        response = self.client.post(url, follow=True,
                                    data={'user': self.user.id,
                                          'name': name,
                                         }
                                   )
        self.assertNoFormError(response)

        graphs = Graph.objects.all()
        self.assertEqual(1,    len(graphs))
        self.assertEqual(name, graphs[0].name)

    def test_graph_edit(self):
        self.login()

        name = 'Nodz-a-lapalooza'
        graph = Graph.objects.create(user=self.user, name=name)

        url = '/graphs/graph/edit/%s' % graph.id
        self.assertGET200(url)

        name += '_edited'
        response = self.client.post(url, follow=True,
                                    data={'user': self.user.id,
                                          'name': name,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(graph).name)

    def test_listview(self):
        self.login()

        create_graph = partial(Graph.objects.create, user=self.user)
        graph1 = create_graph(name='Graph01')
        graph2 = create_graph(name='Graph02')

        response = self.assertGET200('/graphs/graphs')

        with self.assertNoException():
            graphs = response.context['entities'].object_list

        self.assertIn(graph1, graphs)
        self.assertIn(graph2, graphs)

    def test_relation_types01(self):
        self.login()

        graph = Graph.objects.create(user=self.user, name='Graph01')
        self.assertEqual(0, graph.orbital_relation_types.count())

        url = '/graphs/graph/%s/relation_types/add' % graph.id
        self.assertGET200(url)

        rtype_create = RelationType.create
        rtype01, srtype01 = rtype_create(('test-subject_love', 'loves'),
                                         ('test-object_love',  'is loved to')
                                        )
        rtype02, srtype02 = rtype_create(('test-subject_hate', 'hates'),
                                         ('test-object_hate',  'is hated to')
                                        )
        rtypes_ids = [rtype01.id, rtype02.id]

        self.assertNoFormError(self.client.post(url, data={'relation_types': rtypes_ids}))

        rtypes = graph.orbital_relation_types.all()
        self.assertEqual(2,               len(rtypes))
        self.assertEqual(set(rtypes_ids), {rt.id for rt in rtypes})

        self.assertPOST200('/graphs/graph/%s/relation_type/delete' % graph.id,
                           data={'id': rtype01.id}
                          )
        self.assertEqual([rtype02.id], [rt.id for rt in graph.orbital_relation_types.all()])

    def test_relation_types02(self):
        self.login(is_superuser=False)

        graph = Graph.objects.create(user=self.other_user, name='Graph01')
        self.assertGET403('/graphs/graph/%s/relation_types/add' % graph.id)

        rtype, srtype = RelationType.create(('test-subject_love', 'loves'), ('test-object_love', 'is loved to'))
        graph.orbital_relation_types.add(rtype)
        self.assertPOST403('/graphs/graph/%s/relation_type/delete' % graph.id,
                           data={'id': rtype.id}
                          )

    @skipIf(skip_graphviz_test, 'Pygraphviz is not installed (are you under Wind*ws ??')
    def test_download01(self):
        self.login()

        user = self.user
        contact = Contact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        orga = Organisation.objects.create(user=user, name='NERV')

        rtype = RelationType.create(('test-subject_hate', u'déteste'), # test an encoding error, pygraphviz supports unicode...
                                    ('test-object_hate',  u'est détesté par')
                                   )[0]
        Relation.objects.create(user=user,
                                subject_entity=contact,
                                type=rtype,
                                object_entity=orga
                               )

        graph = Graph.objects.create(user=user, name='Graph01')
        url = '/graphs/graph/%s/roots/add' % graph.id
        self.assertGET200(url)

        response = self.client.post(url, data={'entities': '[{"ctype":"%s","entity":"%s"}, {"ctype":"%s","entity":"%s"}]' % (
                                                                contact.entity_type_id, contact.pk,
                                                                orga.entity_type_id,    orga.pk
                                                            ),
                                               'relation_types': [rtype.pk],
                                              }
                                   )
        self.assertNoFormError(response)

        url = '/graphs/graph/%s/relation_types/add' % graph.id
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={'relation_types': [rtype.pk]}))

        self.assertGET200('/graphs/graph/%s/png' % graph.id, follow=True)

        #TODO: improve

    def test_add_rootnode(self):
        self.login()

        user = self.user
        contact = Contact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        orga = Organisation.objects.create(user=user, name='NERV')

        #TODO: factorise
        rtype_create = RelationType.create
        rtype01 = rtype_create(('test-subject_love', 'loves'),
                               ('test-object_love',  'is loved to')
                              )[0]
        rtype02 = rtype_create(('test-subject_hate', 'hates'),
                               ('test-object_hate',  'is hated to')
                              )[0]

        graph = Graph.objects.create(user=user, name='Graph01')
        url = '/graphs/graph/%s/roots/add' % graph.id
        self.assertGET200(url)

        response = self.client.post(url, data={'entities': '[{"ctype":"%s","entity":"%s"}, {"ctype":"%s","entity":"%s"}]' % (
                                                                contact.entity_type_id, contact.pk,
                                                                orga.entity_type_id,    orga.pk
                                                            ),
                                               'relation_types': [rtype01.pk, rtype02.pk],
                                              }
                                   )
        self.assertNoFormError(response)

        rnodes = RootNode.objects.filter(graph=graph).order_by('id')
        self.assertEqual(2, len(rnodes))

        self.assertEqual({contact, orga},
                         {rnode.entity.get_real_entity() for rnode in rnodes}
                        )
        self.assertEqual({rtype01, rtype02}, set(rnodes[0].relation_types.all()))

        #delete
        rnode = rnodes[1]
        url = '/graphs/root/delete'
        data = {'id': rnode.id}
        self.assertGET404(url, data=data)

        self.assertPOST200(url, data=data)
        self.assertDoesNotExist(rnode)

    def test_edit_rootnode(self):
        self.login()

        user = self.user
        orga = Organisation.objects.create(user=user, name='NERV')

        #TODO: factorise
        rtype_create = RelationType.create
        rtype01 = rtype_create(('test-subject_love', 'loves'),
                               ('test-object_love',  'is loved to')
                              )[0]
        rtype02 = rtype_create(('test-subject_hate', 'hates'),
                               ('test-object_hate',  'is hated to')
                              )[0]

        graph = Graph.objects.create(user=user, name='Graph01')
        rnode = RootNode.objects.create(graph=graph, entity=orga)
        rnode.relation_types = [rtype01]

        #url = '/graphs/root/edit/%s/' % rnode.id
        url = rnode.get_edit_absolute_url()
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(url, data={'relation_types': [rtype01.pk, rtype02.pk]}))
        self.assertEqual({rtype01, rtype02}, set(rnode.relation_types.all()))
