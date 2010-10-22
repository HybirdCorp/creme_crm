# -*- coding: utf-8 -*-

from datetime import datetime

from django.test import TestCase
from django.contrib.auth.models import User

from creme_core.models import RelationType, CremePropertyType, CremeProperty, CremeEntity
from creme_core.management.commands.creme_populate import Command as PopulateCommand

from persons.models import Contact

from commercial.models import *
from commercial.constants import PROP_IS_A_SALESMAN, REL_OBJ_SOLD_BY, REL_SUB_SOLD_BY


class CommercialTestCase(TestCase):
    def login(self):
        if not self.user:
            user = User.objects.create(username='Frodo')
            user.set_password(self.password)
            user.is_superuser = True
            user.save()
            self.user = user

        logged = self.client.login(username=self.user.username, password=self.password)
        self.assert_(logged, 'Not logged in')

    def setUp(self):
        PopulateCommand().handle(application=['creme_core', 'persons', 'commercial'])
        self.password = 'test'
        self.user = None

    def test_commercial01(self): #populate
        try:
            RelationType.objects.get(pk=REL_SUB_SOLD_BY)
            RelationType.objects.get(pk=REL_OBJ_SOLD_BY)
            CremePropertyType.objects.get(pk=PROP_IS_A_SALESMAN)
        except Exception, e:
            self.fail(str(e))

    def test_commapp01(self):
        self.login()

        entity = CremeEntity.objects.create(user=self.user)

        response = self.client.get('/commercial/approach/add/%s/' % entity.id)
        self.assertEqual(response.status_code, 200)

        title       = 'TITLE'
        description = 'DESCRIPTION'
        response = self.client.post('/commercial/approach/add/%s/' % entity.id,
                                    data={
                                            'user':        self.user.pk,
                                            'title':       title,
                                            'description': description,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

        commapps = CommercialApproach.objects.all()
        self.assertEqual(1, len(commapps))

        commapp = commapps[0]
        self.assertEqual(title,       commapp.title)
        self.assertEqual(description, commapp.description)
        self.assertEqual(entity.id,   commapp.entity_id)

        tdelta = (datetime.today() - commapp.creation_date)
        self.assert_(tdelta.seconds < 10)

    def test_salesman_create(self):
        self.login()

        response = self.client.get('/commercial/salesman/add')
        self.assertEqual(response.status_code, 200)

        first_name = 'John'
        last_name  = 'Doe'

        response = self.client.post('/commercial/salesman/add', follow=True,
                                    data={
                                            'user':       self.user.pk,
                                            'first_name': first_name,
                                            'last_name':  last_name,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)
        self.assert_(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)

        salesmen = Contact.objects.filter(properties__type=PROP_IS_A_SALESMAN)
        self.assertEqual(1, len(salesmen))

        salesman = salesmen[0]
        self.assertEqual(first_name, salesman.first_name)
        self.assertEqual(last_name,  salesman.last_name)

    def test_salesman_listview01(self):
        self.login()

        self.failIf(Contact.objects.filter(properties__type=PROP_IS_A_SALESMAN).count())

        response = self.client.get('/commercial/salesmen')
        self.assertEqual(response.status_code, 200)

        try:
            salesmen_page = response.context['entities']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(1, salesmen_page.number)
        self.failIf(salesmen_page.paginator.count)

    def test_salesman_listview02(self):
        self.login()

        self.client.post('/commercial/salesman/add', data={'user': self.user.pk, 'first_name': 'first_name1', 'last_name': 'last_name1'})
        self.client.post('/commercial/salesman/add', data={'user': self.user.pk, 'first_name': 'first_name2', 'last_name': 'last_name2'})
        salesmen = Contact.objects.filter(properties__type=PROP_IS_A_SALESMAN)
        self.assertEqual(2, len(salesmen))

        response = self.client.get('/commercial/salesmen')
        self.assertEqual(response.status_code, 200)

        try:
            salesmen_page = response.context['entities']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(1, salesmen_page.number)
        self.assertEqual(2, salesmen_page.paginator.count)
        self.assertEqual(set(s.id for s in salesmen), set(o.id for o in salesmen_page.object_list))

    def test_portal(self):
        self.login()
        response = self.client.get('/commercial/')
        self.assertEqual(response.status_code, 200)


#TODO: tests for Act, (SellByRelation)
