# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.models import SearchConfigItem
    from .base import ViewsTestCase

    from creme.persons.models import Contact, Organisation
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('SearchViewTestCase', )


class SearchViewTestCase(ViewsTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_config')
        cls.contact_ct_id = ContentType.objects.get_for_model(Contact).id

    def _build_contacts(self):
        create_contact = partial(Contact.objects.create, user=self.user)
        self.linus = create_contact(first_name='Linus', last_name='Torvalds')
        self.alan  = create_contact(first_name='Alan',  last_name='Cox')
        self.linus2 = create_contact(first_name='Linus', last_name='Impostor', is_deleted=True)

    def _setup_contacts(self):
        SearchConfigItem.create_if_needed(Contact, ['first_name', 'last_name'])
        self._build_contacts()

    def _setup_orgas(self):
        SearchConfigItem.create_if_needed(Organisation, ['name'])

        create_orga = partial(Organisation.objects.create, user=self.user)
        self.linusfo = create_orga(name='FoobarLinusFoundation')
        self.coxco   = create_orga(name='StuffCoxCorp')

    def _search(self, research=None, ct_id=None):
        data = {}

        if research is not None:
            data['research'] = research

        if ct_id is not None:
            data['ct_id'] = ct_id

        return self.client.post('/creme_core/search', data=data)

    def test_search01(self):
        self.login()
        self._setup_contacts()

        response = self._search('john', self.contact_ct_id)
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            results = response.context['results']
            total   = response.context['total']

        self.assertEqual(0, total)
        self.assertEqual(1, len(results))

        result = results[0]
        self.assertIs(result['model'], Contact)
        self.assertEqual(0, len(result['entities']))

    def test_search02(self):
        "Deleted entities are found too"
        self.login()
        self._setup_contacts()

        response = self._search('linu', self.contact_ct_id)
        self.assertEqual(200, response.status_code)

        results = response.context['results']
        #self.assertEqual(1, response.context['total'])
        self.assertEqual(2, response.context['total'])
        self.assertEqual(1, len(results))

        entities = results[0]['entities']
        #self.assertEqual(1, len(entities))
        self.assertEqual(2, len(entities))

        #entity = entities[0]
        #self.assertIsInstance(entity, Contact)
        #self.assertEqual(self.linus.id, entity.id)
        self.assertIsInstance(entities[0], Contact)
        self.assertIsInstance(entities[1], Contact)
        self.assertEqual(set([self.linus.id, self.linus2.id]),
                         set(e.id for e in entities)
                        )

    def test_search03(self):
        self.login()
        self._setup_contacts()
        self._setup_orgas()

        context = self._search('cox').context
        self.assertEqual(2, context['total'])

        contacts_result = None
        orgas_result    = None

        for result in context['results']:
            model = result['model']
            if model is Contact:
                self.assertIsNone(contacts_result)
                contacts_result = result
            elif model is Organisation:
                self.assertIsNone(orgas_result)
                orgas_result = result
            else:
                self.assertEqual(0, len(result['entities']))

        self.assertIsNotNone(contacts_result)
        self.assertIsNotNone(orgas_result)

        entities = contacts_result['entities']
        self.assertEqual(1, len(entities))
        self.assertEqual(self.alan, entities[0])

        entities = orgas_result['entities']
        self.assertEqual(1, len(entities))
        self.assertEqual(self.coxco, entities[0])

    def test_search04(self):
        "Error"
        self.login()
        self._setup_contacts()
        self._setup_orgas()

        self.assertEqual(_(u"Please enter at least 3 characters"),
                         self._search('ox').context['error_message']
                        )
        self.assertEqual(_(u"Empty search..."),
                         self._search().context['error_message']
                        )
        self.assertEqual(404, self._search('linus', 1024).status_code) # ct_id=1024 DOES NOT EXIST

    def test_search05(self):
        "No config for contact"
        self.login()
        self._build_contacts()
        self._setup_orgas()

        response = self.client.post('/creme_core/search',
                                    data={'research': 'torvalds',
                                          'ct_id':    self.contact_ct_id,
                                         }
                                   )
        results = response.context['results']
        self.assertEqual(1, response.context['total'])
        self.assertEqual(1, len(results))

        entities = results[0]['entities']
        self.assertEqual(1, len(entities))
        self.assertEqual(self.linus.id, entities[0].id)

    def test_search06(self):
        "Search only in configured fields if the config exists"
        self.login()
        self._setup_contacts()
        self._setup_orgas()

        self.linus.description = 'He is very smart but wears ugly shorts.'
        self.linus.save()

        self.assertEqual(0, self._search('very smart', self.contact_ct_id).context['total'])
