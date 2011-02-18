# -*- coding: utf-8 -*-

from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, UserRole

from graphs.models import *


class PersonsTestCase(TestCase):
    def login(self, is_superuser=True):
        password = 'test'

        superuser = User.objects.create(username='Kirika')
        superuser.set_password(password)
        superuser.is_superuser = True
        superuser.save()

        role = UserRole.objects.create(name='Basic')
        role.allowed_apps = ['graphs']
        role.save()
        basic_user = User.objects.create(username='Mireille', role=role)
        basic_user.set_password(password)
        basic_user.save()

        self.user, self.other_user = (superuser, basic_user) if is_superuser else \
                                     (basic_user, superuser)

        logged = self.client.login(username=self.user.username, password=password)
        self.assert_(logged, 'Not logged in')

    def setUp(self):
        self.password = 'test'
        self.user = None

    def assertNoFormError(self, response): #TODO: move in a CremeTestCase ??? (copied from creme_config)
        try:
            errors = response.context['form'].errors
        except Exception, e:
            pass
        else:
            if errors:
                self.fail(errors)

    def test_graph_create(self):
        self.login()

        url = '/graphs/graph/add'
        self.assertEqual(200, self.client.get(url).status_code)

        name = 'Graph01'
        response = self.client.post(url, follow=True,
                                    data={
                                            'user': self.user.id,
                                            'name': name,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        graphs = Graph.objects.all()
        self.assertEqual(1,    len(graphs))
        self.assertEqual(name, graphs[0].name)

    def test_graph_edit(self):
        self.login()

        name = 'Nodz-a-lapalooza'
        graph = Graph.objects.create(user=self.user, name=name)

        url = '/graphs/graph/edit/%s' % graph.id
        self.assertEqual(200, self.client.get(url).status_code)

        name += '_edited'
        response = self.client.post(url, follow=True,
                                    data={
                                            'user': self.user.id,
                                            'name': name,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200,  response.status_code)
        self.assertEqual(name, Graph.objects.get(pk=graph.id).name)

    def test_listview(self):
        self.login()

        Graph.objects.create(user=self.user, name='Graph01')
        Graph.objects.create(user=self.user, name='Graph02')

        self.assertEqual(200, self.client.get('/graphs/graphs').status_code)

    def test_relation_types01(self):
        self.login()

        graph = Graph.objects.create(user=self.user, name='Graph01')
        self.assertEqual(0, graph.orbital_relation_types.count())

        url = '/graphs/graph/%s/relation_types/add' % graph.id
        self.assertEqual(200, self.client.get(url).status_code)

        rtype_create = RelationType.create
        rtype01, srtype01 = rtype_create(('test-subject_love', 'loves'), ('test-object_love', 'is loved to'))
        rtype02, srtype02 = rtype_create(('test-subject_hate', 'hates'), ('test-object_hate', 'is hated to'))
        rtypes_ids = [rtype01.id, rtype02.id]

        response = self.client.post(url, data={'relation_types': rtypes_ids})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        rtypes = graph.orbital_relation_types.all()
        self.assertEqual(2,               len(rtypes))
        self.assertEqual(set(rtypes_ids), set(rt.id for rt in rtypes))

        response = self.client.post('/graphs/graph/%s/relation_type/delete' % graph.id,
                                    data={'id': rtype01.id}
                                   )
        self.assertEqual(200,          response.status_code)
        self.assertEqual([rtype02.id], [rt.id for rt in graph.orbital_relation_types.all()])

    def test_relation_types02(self):
        self.login(is_superuser=False)

        graph = Graph.objects.create(user=self.other_user, name='Graph01')
        self.assertEqual(403, self.client.get('/graphs/graph/%s/relation_types/add' % graph.id).status_code)

        rtype, srtype = RelationType.create(('test-subject_love', 'loves'), ('test-object_love', 'is loved to'))
        graph.orbital_relation_types.add(rtype)
        self.assertEqual(403,  self.client.post('/graphs/graph/%s/relation_type/delete' % graph.id,
                                                data={'id': rtype.id}
                                               ).status_code
                        )

    #TODO: def test_root_nodes_/add/edit/delete
    #TODO: test download ??
