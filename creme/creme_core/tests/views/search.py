# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import *
    from creme_core.tests.views.base import ViewsTestCase

    from persons.models import Contact, Organisation
except Exception, e:
    print 'Error:', e


__all__ = ('SearchViewTestCase', )


class SearchViewTestCase(ViewsTestCase):
    def setUp(self):
        self.populate('creme_config')

    def _build_contacts(self):
        self.linus = Contact.objects.create(user=self.user, first_name='Linus', last_name='Torvalds')
        self.alan  = Contact.objects.create(user=self.user, first_name='Alan',  last_name='Cox')

    def _setup_contacts(self):
        SearchConfigItem.create_if_needed(Contact, ['first_name', 'last_name'])
        self._build_contacts()

    def _setup_orgas(self):
        SearchConfigItem.create_if_needed(Organisation, ['name'])

        self.linusfo = Organisation.objects.create(user=self.user, name='FoobarLinusFoundation')
        self.coxco   = Organisation.objects.create(user=self.user, name='StuffCoxCorp')

    def test_search01(self):
        self.login()
        self._setup_contacts()

        response = self.client.post('/creme_core/search',
                                    data={
                                            'research': 'john',
                                            'ct_id':    ContentType.objects.get_for_model(Contact).id,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        try:
            results = response.context['results']
            total   = response.context['total']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(0, total)
        self.assertEqual(1, len(results))

        result = results[0]
        self.assert_(result['model'] is Contact)
        self.assertEqual(0, len(result['entities']))

    def test_search02(self):
        self.login()
        self._setup_contacts()

        response = self.client.post('/creme_core/search',
                                    data={
                                            'research': 'linu',
                                            'ct_id':    ContentType.objects.get_for_model(Contact).id,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        results = response.context['results']
        self.assertEqual(1, response.context['total'])
        self.assertEqual(1, len(results))

        entities = results[0]['entities']
        self.assertEqual(1, len(entities))

        entity = entities[0]
        self.assert_(isinstance(entity, Contact))
        self.assertEqual(self.linus.id, entity.id)

    def test_search03(self):
        self.login()
        self._setup_contacts()
        self._setup_orgas()

        context = self.client.post('/creme_core/search', data={'research': 'cox'}).context
        self.assertEqual(2, context['total'])

        contacts_result = None
        orgas_result    = None

        for result in context['results']:
            model = result['model']
            if model is Contact:
                self.assert_(contacts_result is None)
                contacts_result = result
            elif model is Organisation:
                self.assert_(orgas_result is None)
                orgas_result = result
            else:
                self.assertEqual(0, len(result['entities']))

        self.assert_(contacts_result is not None)
        self.assert_(orgas_result is not None)

        entities = contacts_result['entities']
        self.assertEqual(1, len(entities))
        self.assertEqual(self.alan.id, entities[0].id)

        entities = orgas_result['entities']
        self.assertEqual(1, len(entities))
        self.assertEqual(self.coxco.id, entities[0].id)

    def test_search04(self): #error
        self.login()
        self._setup_contacts()
        self._setup_orgas()

        self.assert_(self.client.post('/creme_core/search', data={'research': 'ox'}).context['error_message'])
        self.assert_(self.client.post('/creme_core/search').context['error_message'])
        self.assertEqual(404, self.client.post('/creme_core/search',
                                               data={
                                                       'research': 'linus',
                                                       'ct_id':     1024, #DOES NOT EXIST
                                                    }
                                              ).status_code
                        )

    def test_search05(self): #no config for contact
        self.login()
        self._build_contacts()
        self._setup_orgas()

        response = self.client.post('/creme_core/search',
                                    data={
                                            'research': 'torvalds',
                                            'ct_id':    ContentType.objects.get_for_model(Contact).id,
                                         }
                                   )
        results = response.context['results']
        self.assertEqual(1, response.context['total'])
        self.assertEqual(1, len(results))

        entities = results[0]['entities']
        self.assertEqual(1, len(entities))
        self.assertEqual(self.linus.id, entities[0].id)

    def test_search06(self): #search only is configured fields if the config exists
        self.login()
        self._setup_contacts()
        self._setup_orgas()

        self.linus.description = 'He is very smart but wears ugly shorts.'
        self.linus.save()

        response = self.client.post('/creme_core/search',
                                    data={
                                            'research': 'very smart',
                                            'ct_id':    ContentType.objects.get_for_model(Contact).id,
                                         }
                                   )
        self.assertEqual(0, response.context['total'])
