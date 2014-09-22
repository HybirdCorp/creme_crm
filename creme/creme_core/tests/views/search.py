# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    from django.core.serializers.json import simplejson
    #from django.test.utils import override_settings
    from django.utils.translation import ugettext as _

    from creme.creme_core.gui.block import QuerysetBlock
    from creme.creme_core.models import SearchConfigItem
    from .base import ViewsTestCase

    from creme.persons.models import Contact, Organisation
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('SearchViewTestCase', )


class SearchViewTestCase(ViewsTestCase):
    CONTACT_BLOCKID = 'block_creme_core-found-persons-contact'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_config', 'creme_core')
        cls.contact_ct_id = ContentType.objects.get_for_model(Contact).id

        QuerysetBlock.page_size = 10

    @classmethod
    def tearDownClass(cls):
        del QuerysetBlock.page_size
        assert QuerysetBlock.page_size #in PaginatedBlock

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
        self.assertTemplateUsed(response, 'creme_core/search_results.html')

        with self.assertNoException():
            ctxt = response.context
            #results = ctxt['results']
            #total  = ctxt['total']
            models = ctxt['models']
            blocks = ctxt['blocks']

        #self.assertEqual(0, total)
        #self.assertEqual(1, len(results))

        #result = results[0]
        #self.assertIs(result['model'], Contact)
        #self.assertEqual(0, len(result['entities']))

        self.assertEqual([_('Contact')], models)

        self.assertIsInstance(blocks, list)
        self.assertEqual(1, len(blocks))

        block = blocks[0]
        self.assertIsInstance(block, QuerysetBlock)
        self.assertIn(self.CONTACT_BLOCKID, block.id_)
        self.assertEqual('creme_core/templatetags/block_found_entities.html', block.template_name)

        self.assertNotContains(response, self.linus.get_absolute_url())

    #@override_settings(BLOCK_SIZE=10)
    def test_search02(self):
        "Deleted entities are found too"
        self.login()
        self._setup_contacts()

        response = self._search('linu', self.contact_ct_id)
        self.assertEqual(200, response.status_code)

        #results = response.context['results']
        #self.assertEqual(2, response.context['total'])
        #self.assertEqual(1, len(results))

        #entities = results[0]['entities']
        #self.assertEqual(2, len(entities))

        #self.assertIsInstance(entities[0], Contact)
        #self.assertIsInstance(entities[1], Contact)
        #self.assertEqual({self.linus.id, self.linus2.id}, {e.id for e in entities})

        #print response.content

        self.assertContains(response, self.linus.get_absolute_url())
        self.assertContains(response, self.linus2.get_absolute_url())
        self.assertNotContains(response, self.alan.get_absolute_url())

    #@override_settings(BLOCK_SIZE=10)
    def test_search03(self):
        self.login()
        self._setup_contacts()
        self._setup_orgas()

        #context = self._search('cox').context
        response = self._search('cox')
        context = response.context
        #self.assertEqual(2, context['total'])

        contacts_result = None
        orgas_result    = None

        #for result in context['results']:
            #model = result['model']
            #if model is Contact:
                #self.assertIsNone(contacts_result)
                #contacts_result = result
            #elif model is Organisation:
                #self.assertIsNone(orgas_result)
                #orgas_result = result
            #else:
                #self.assertEqual(0, len(result['entities']))

        #self.assertIsNotNone(contacts_result)
        #self.assertIsNotNone(orgas_result)

        #entities = contacts_result['entities']
        #self.assertEqual(1, len(entities))
        #self.assertEqual(self.alan, entities[0])

        #entities = orgas_result['entities']
        #self.assertEqual(1, len(entities))
        #self.assertEqual(self.coxco, entities[0])

        self.assertGreaterEqual(len(context['blocks']), 2)

        self.assertContains(response, ' id="%s' % self.CONTACT_BLOCKID)
        self.assertContains(response, self.alan.get_absolute_url())
        self.assertNotContains(response, self.linus.get_absolute_url())
        self.assertNotContains(response, self.linus2.get_absolute_url())

        self.assertContains(response, ' id="block_creme_core-found-persons-organisation-')
        self.assertContains(response, self.coxco.get_absolute_url())
        self.assertNotContains(response, self.linusfo.get_absolute_url())

        vnames = {unicode(vname) for vname in context['models']}
        self.assertIn(_('Contact'), vnames)
        self.assertIn(_('Organisation'), vnames)

    def test_search04(self):
        "Error"
        self.login()
        self._setup_contacts()
        self._setup_orgas()

        self.assertEqual(_(u"Please enter at least %s characters") % 3,
                         self._search('ox').context['error_message']
                        )
        self.assertEqual(_(u"Empty search…"),
                         self._search().context['error_message']
                        )
        self.assertEqual(404, self._search('linus', 1024).status_code) # ct_id=1024 DOES NOT EXIST

    def test_search05(self):
        "No config for contact"
        self.login()
        self._build_contacts()
        self._setup_orgas()

        response = self._search('torvalds', self.contact_ct_id)
        #results = response.context['results']
        #self.assertEqual(1, response.context['total'])
        #self.assertEqual(1, len(results))

        #entities = results[0]['entities']
        #self.assertEqual(1, len(entities))
        #self.assertEqual(self.linus.id, entities[0].id)

        self.assertContains(response, self.linus.get_absolute_url())
        self.assertNotContains(response, self.linus2.get_absolute_url())
        self.assertNotContains(response, self.alan.get_absolute_url())

    def test_search06(self):
        "Search only in configured fields if the config exists"
        self.login()
        self._setup_contacts()
        self._setup_orgas()

        linus = self.linus
        linus.description = 'He is very smart but wears ugly shorts.'
        linus.save()

        #self.assertEqual(0, self._search('very smart', self.contact_ct_id).context['total'])

        response = self._search('very smart', self.contact_ct_id)
        self.assertNotContains(response, linus.get_absolute_url())

    def test_reload_block(self):
        self.login()
        self._setup_contacts()

        url_fmt = '/creme_core/search/reload_block/%s/%s'
        block_id = self.CONTACT_BLOCKID + '-32132154'
        self.assertGET404(url_fmt % (block_id, 'da'))

        response = self.assertGET200(url_fmt % (block_id, 'linu'))

        with self.assertNoException():
            results = simplejson.loads(response.content)

        self.assertIsInstance(results, list)
        self.assertEqual(1, len(results))

        result = results[0]
        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))

        self.assertEqual(block_id, result[0])
        self.assertIn(' id="%s"' % block_id, result[1])
