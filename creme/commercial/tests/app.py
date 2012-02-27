# -*- coding: utf-8 -*-

try:
    from datetime import datetime

    from creme_core.models import CremeEntity
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact, Organisation

    from opportunities.models import Opportunity

    from commercial.models import Act, ActType, CommercialApproach
    from commercial.constants import *
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('CommercialTestCase',)


class CommercialTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'persons', 'commercial')

    def test_populate(self):
        self.get_relationtype_or_fail(REL_SUB_SOLD_BY)
        self.get_relationtype_or_fail(REL_OBJ_SOLD_BY)
        self.get_relationtype_or_fail(REL_SUB_OPPORT_LINKED, [Opportunity], [Act])
        self.get_relationtype_or_fail(REL_SUB_COMPLETE_GOAL, [], [Act])

        self.get_propertytype_or_fail(PROP_IS_A_SALESMAN, [Contact])

        self.assertEqual(3, ActType.objects.count())

    def test_commapp01(self):
        self.login()
        entity = CremeEntity.objects.create(user=self.user)
        url = '/commercial/approach/add/%s/' % entity.id
        self.assertEqual(200, self.client.get(url).status_code)

        title       = 'TITLE'
        description = 'DESCRIPTION'
        response = self.client.post(url, data={'title':       title,
                                               'description': description,
                                              }
                                   )
        self.assertEqual(200, response.status_code)

        commapps = CommercialApproach.objects.all()
        self.assertEqual(1, len(commapps))

        commapp = commapps[0]
        self.assertEqual(title,       commapp.title)
        self.assertEqual(description, commapp.description)
        self.assertEqual(entity.id,   commapp.entity_id)

        self.assertLess((datetime.today() - commapp.creation_date).seconds, 10)

    def test_commapp_merge(self):
        self.login()
        user = self.user

        create_orga = Organisation.objects.create
        orga01 = create_orga(user=user, name='NERV')
        orga02 = create_orga(user=user, name='Nerv')

        create_commapp = CommercialApproach.objects.create
        create_commapp(title='Commapp01', description='...', creation_date=datetime.now(), creme_entity=orga01)
        create_commapp(title='Commapp02', description='...', creation_date=datetime.now(), creme_entity=orga02)
        self.assertEqual(2, CommercialApproach.objects.count())

        response = self.client.post('/creme_core/entity/merge/%s,%s' % (orga01.id, orga02.id),
                                    follow=True,
                                    data={'user_1':      user.id,
                                          'user_2':      user.id,
                                          'user_merged': user.id,

                                          'name_1':      orga01.name,
                                          'name_2':      orga02.name,
                                          'name_merged': orga01.name,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        self.assertFalse(Organisation.objects.filter(pk=orga02).exists())

        with self.assertNoException():
            orga01 = self.refresh(orga01)

        commapps = CommercialApproach.objects.all()
        self.assertEqual(2, len(commapps))

        for commapp in commapps:
            self.assertEqual(orga01, commapp.creme_entity)

    def test_salesman_create(self):
        self.login()

        url = '/commercial/salesman/add'
        self.assertEqual(200, self.client.get(url).status_code)

        first_name = 'John'
        last_name  = 'Doe'
        response = self.client.post(url, follow=True,
                                    data={'user':       self.user.pk,
                                          'first_name': first_name,
                                          'last_name':  last_name,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.redirect_chain)
        self.assertEqual(1, len(response.redirect_chain))

        salesmen = Contact.objects.filter(properties__type=PROP_IS_A_SALESMAN)
        self.assertEqual(1, len(salesmen))

        salesman = salesmen[0]
        self.assertEqual(first_name, salesman.first_name)
        self.assertEqual(last_name,  salesman.last_name)

    def test_salesman_listview01(self):
        self.login()

        self.assertFalse(Contact.objects.filter(properties__type=PROP_IS_A_SALESMAN).exists())

        response = self.client.get('/commercial/salesmen')
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            salesmen_page = response.context['entities']

        self.assertEqual(1, salesmen_page.number)
        self.assertFalse(salesmen_page.paginator.count)

    def test_salesman_listview02(self):
        self.login()

        def add_salesman(first_name, last_name):
            self.client.post('/commercial/salesman/add',
                             data={'user':        self.user.pk,
                                   'first_name': 'first_name1',
                                   'last_name':   'last_name1',
                                  }
                            )
        
        #self.client.post('/commercial/salesman/add', data={'user': self.user.pk, 'first_name': 'first_name1', 'last_name': 'last_name1'})
        #self.client.post('/commercial/salesman/add', data={'user': self.user.pk, 'first_name': 'first_name2', 'last_name': 'last_name2'})
        add_salesman('first_name1', 'last_name1')
        add_salesman('first_name2', 'last_name2')
        salesmen = Contact.objects.filter(properties__type=PROP_IS_A_SALESMAN)
        self.assertEqual(2, len(salesmen))

        response = self.client.get('/commercial/salesmen')
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            salesmen_page = response.context['entities']

        self.assertEqual(1, salesmen_page.number)
        self.assertEqual(2, salesmen_page.paginator.count)
        self.assertEqual(set(salesmen), set(salesmen_page.object_list))

    def test_portal(self):
        self.login()
        self.assertEqual(200, self.client.get('/commercial/').status_code)
