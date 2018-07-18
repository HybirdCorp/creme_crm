# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    # from django.test import override_settings
    from django.urls import reverse
    from django.utils.translation import ugettext as _

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.gui.bricks import QuerysetBrick
    from creme.creme_core.models import SearchConfigItem, FieldsConfig, SetCredentials

    from ..fake_models import FakeContact, FakeOrganisation, FakeSector

    from .base import ViewsTestCase, BrickTestCaseMixin
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class SearchViewTestCase(ViewsTestCase, BrickTestCaseMixin):
    LIGHT_URL = reverse('creme_core__light_search')

    CONTACT_BRICKID = 'block_creme_core-found-creme_core-fakecontact'
    ORGA_BRICKID    = 'block_creme_core-found-creme_core-fakeorganisation-'

    @classmethod
    def setUpClass(cls):
        # super(SearchViewTestCase, cls).setUpClass()
        super().setUpClass()
        cls.contact_ct_id = ContentType.objects.get_for_model(FakeContact).id

        QuerysetBrick.page_size = 10

        cls._sci_backup = list(SearchConfigItem.objects.all())
        SearchConfigItem.objects.all().delete()

    @classmethod
    def tearDownClass(cls):
        # super(SearchViewTestCase, cls).tearDownClass()
        super().tearDownClass()

        del QuerysetBrick.page_size
        assert QuerysetBrick.page_size  # In PaginatedBlock

        SearchConfigItem.objects.all().delete()
        SearchConfigItem.objects.bulk_create(cls._sci_backup)

    def _build_contacts(self, user=None):
        sector = FakeSector.objects.create(title='Linux dev')

        create_contact = partial(FakeContact.objects.create, user=user or self.user)
        self.linus  = create_contact(first_name='Linus',  last_name='Torvalds')
        self.alan   = create_contact(first_name='Alan',   last_name='Cox',      description='Cool beard')
        self.linus2 = create_contact(first_name='Linus',  last_name='Impostor', is_deleted=True)
        self.andrew = create_contact(first_name='Andrew', last_name='Morton',   sector=sector)

    def _setup_contacts(self, disabled=False, user=None):
        SearchConfigItem.create_if_needed(FakeContact,
                                          ['first_name', 'last_name', 'sector__title'],
                                          disabled=disabled,
                                         )
        self._build_contacts(user)

    def _setup_orgas(self):
        SearchConfigItem.create_if_needed(FakeOrganisation, ['name'])

        create_orga = partial(FakeOrganisation.objects.create, user=self.user)
        self.linusfo = create_orga(name='FoobarLinusFoundation')
        self.coxco   = create_orga(name='StuffCoxCorp')

    def _search(self, research=None, ct_id=None):
        data = {}

        if research is not None:
            data['research'] = research

        if ct_id is not None:
            data['ct_id'] = ct_id

        return self.client.get(reverse('creme_core__search'), data=data)

    def test_search01(self):
        self.login()
        self._setup_contacts()

        response = self._search('john', self.contact_ct_id)
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'creme_core/search_results.html')

        with self.assertNoException():
            ctxt = response.context
            models = ctxt['models']
            # bricks = ctxt['blocks']
            bricks = ctxt['bricks']

        self.assertEqual(['Test Contact'], models)

        self.assertIsInstance(bricks, list)
        self.assertEqual(1, len(bricks))

        block = bricks[0]
        self.assertIsInstance(block, QuerysetBrick)
        self.assertIn(self.CONTACT_BRICKID, block.id_)
        self.assertEqual('creme_core/bricks/found-entities.html',
                         block.template_name
                        )

        self.assertNotContains(response, self.linus.get_absolute_url())

    def test_search02(self):
        "Find result in field & sub-field ; deleted entities are found too"
        self.login()
        self._setup_contacts()

        response = self._search('linu', self.contact_ct_id)
        self.assertEqual(200, response.status_code)

        self.assertContains(response, self.linus.get_absolute_url())
        self.assertContains(response, self.linus2.get_absolute_url())  # Deleted
        self.assertContains(response, self.andrew.get_absolute_url())  # In sector__title
        self.assertNotContains(response, self.alan.get_absolute_url())

    def test_search03(self):
        self.login()
        self._setup_contacts()
        self._setup_orgas()

        response = self._search('cox')
        context = response.context

        self.assertGreaterEqual(len(context['bricks']), 2)

        self.assertContains(response, ' id="{}'.format(self.CONTACT_BRICKID))
        self.assertContains(response, self.alan.get_absolute_url())
        self.assertNotContains(response, self.linus.get_absolute_url())
        self.assertNotContains(response, self.linus2.get_absolute_url())

        self.assertContains(response, ' id="{}'.format(self.ORGA_BRICKID))
        self.assertContains(response, self.coxco.get_absolute_url())
        self.assertNotContains(response, self.linusfo.get_absolute_url())

        vnames = {str(vname) for vname in context['models']}
        self.assertIn(_(u'Contact'), vnames)
        self.assertIn(_(u'Organisation'), vnames)

    # @override_settings(OLD_MENU=False)
    def test_search04(self):
        "Error"
        self.login()
        self._setup_contacts()
        self._setup_orgas()

        self.assertEqual(_(u'Please enter at least {count} characters').format(count=3),
                         self._search('ox').context['error_message']
                        )
        self.assertEqual(404, self._search('linus', 1024).status_code)  # ct_id=1024 DOES NOT EXIST

    # @override_settings(OLD_MENU=True)
    # def test_search04_legacy(self):
    #     "Error"
    #     self.login()
    #     self._setup_contacts()
    #     self._setup_orgas()
    #
    #     self.assertEqual(_(u'Please enter at least %s characters') % 3,
    #                      self._search('ox').context['error_message']
    #                     )
    #     self.assertEqual(_(u'Empty search…'),
    #                      self._search().context['error_message']
    #                     )
    #     self.assertEqual(404, self._search('linus', 1024).status_code)  # ct_id=1024 DOES NOT EXIST

    def test_search05(self):
        "No config for Contact"
        self.login()
        self._build_contacts()
        self._setup_orgas()

        response = self._search('torvalds', self.contact_ct_id)

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

        response = self._search('very smart', self.contact_ct_id)
        self.assertNotContains(response, linus.get_absolute_url())

    def test_search07(self):
        "Disabled"
        self.login()
        self._setup_contacts(disabled=True)
        self._setup_orgas()

        response = self._search('cox')
        context = response.context

        self.assertContains(response, ' id="{}'.format(self.ORGA_BRICKID))
        self.assertContains(response, self.coxco.get_absolute_url())
        self.assertNotContains(response, self.linusfo.get_absolute_url())

        self.assertNotContains(response, ' id="{}'.format(self.CONTACT_BRICKID))
        self.assertNotContains(response, self.alan.get_absolute_url())

        vnames = {str(vname) for vname in context['models']}
        self.assertIn(FakeOrganisation._meta.verbose_name, vnames)
        self.assertNotIn(FakeContact._meta.verbose_name, vnames)

    def test_search08(self):
        "Use Role's config if it exists"
        self.login(is_superuser=False, allowed_apps=['creme_core'])

        SearchConfigItem.create_if_needed(FakeContact, ['description'], role=self.role)
        self._setup_contacts()

        response = self._search('bear', self.contact_ct_id)
        self.assertEqual(200, response.status_code)

        self.assertNotContains(response, self.linus.get_absolute_url())
        self.assertNotContains(response, self.linus2.get_absolute_url())
        self.assertContains(response, self.alan.get_absolute_url())

    def test_search09(self):
        "Use Role's config if it exists (super-user)"
        self.login()

        SearchConfigItem.create_if_needed(FakeContact, ['description'], role='superuser')
        self._setup_contacts()

        response = self._search('bear', self.contact_ct_id)
        self.assertEqual(200, response.status_code)

        self.assertNotContains(response, self.linus.get_absolute_url())
        self.assertNotContains(response, self.linus2.get_absolute_url())
        self.assertContains(response, self.alan.get_absolute_url())

    def test_search10(self):
        "With FieldsConfig"
        user = self.login()

        hidden_fname1 = 'description'
        hidden_fname2 = 'sector'
        SearchConfigItem.create_if_needed(FakeContact,
                                          ['first_name', 'last_name',
                                           hidden_fname1,
                                           hidden_fname2 + '__title',
                                          ],
                                         )

        sector = FakeSector.objects.create(title='Linux dev')

        create_contact = partial(FakeContact.objects.create, user=user)
        linus  = create_contact(first_name='Linus',  last_name='Torvalds', description="Alan's friend")
        alan   = create_contact(first_name='Alan',   last_name='Cox',      description="Linus' friend")
        andrew = create_contact(first_name='Andrew', last_name='Morton',   sector=sector)

        FieldsConfig.create(FakeContact,
                            descriptions=[(hidden_fname1, {FieldsConfig.HIDDEN: True}),
                                          (hidden_fname2, {FieldsConfig.HIDDEN: True}),
                                         ]
                           )

        response = self._search('Linu', self.contact_ct_id)
        self.assertEqual(200, response.status_code)

        self.assertContains(response, linus.get_absolute_url())
        self.assertNotContains(response, alan.get_absolute_url())
        self.assertNotContains(response, andrew.get_absolute_url())

        self.assertContains(response, _(u'First name'))
        self.assertContains(response, _(u'Last name'))
        self.assertNotContains(response, _(u'Description'))
        self.assertNotContains(response, _(u'Sector'))

    def test_search11(self):
        "With FieldsConfig: all fields are hidden"
        self.login()

        hidden_fname = 'description'
        SearchConfigItem.create_if_needed(FakeContact, [hidden_fname])
        FieldsConfig.create(FakeContact,
                            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})]
                           )
        self._build_contacts()

        response = self._search('Cool', self.contact_ct_id)
        self.assertEqual(200, response.status_code)

        self.assertNotContains(response, self.linus.get_absolute_url())
        self.assertNotContains(response, self.alan.get_absolute_url())
        self.assertNotContains(response, self.andrew.get_absolute_url())

        self.assertContains(response,
                            _(u'It seems that all fields are hidden. Ask your administrator to fix the configuration.')
                           )

    def test_search12(self):
        "Model is not a CremeEntity"
        self.login()

        response = self._search('john', ContentType.objects.get_for_model(ContentType).id)
        self.assertEqual(404, response.status_code)

    def test_reload_brick(self):
        self.login()
        self._setup_contacts()

        url = reverse('creme_core__reload_search_brick')
        brick_id = self.CONTACT_BRICKID + '-32132154'
        self.assertGET404(url, data={'brick_id': brick_id, 'search': 'da'})

        response = self.assertGET200(url, data={'brick_id': brick_id, 'search': 'linu'})

        results = response.json()
        self.assertIsInstance(results, list)
        self.assertEqual(1, len(results))

        result = results[0]
        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))

        self.assertEqual(brick_id, result[0])

        doc = self.get_html_tree(result[1])
        self.get_brick_node(doc, brick_id)

    def test_light_search01(self):
        user = self.login()

        self._setup_contacts()
        coxi = FakeContact.objects.create(user=user, first_name='Coxi', last_name='Nail')

        self._setup_orgas()

        response = self.assertGET200(self.LIGHT_URL, data={'value': 'cox'})

        results = response.json()

        alan = self.alan
        coxco = self.coxco

        self.maxDiff = None
        self.assertEqual(
            {'best':    {'label': str(coxco),
                         # 'score': 102,
                         'url':   coxco.get_absolute_url(),
                        },
             # 'query':   {'content': 'cox',
             #             'limit': 5,
             #             'ctype': None,
             #            },
             'results': [{'count':   2,
                          'id':      alan.entity_type_id,
                          'label':   'Test Contact',
                          'results': [{'label': str(alan),
                                       # 'score': 101,
                                       'url':   alan.get_absolute_url(),
                                      },
                                      {'label': str(coxi),
                                       # 'score': 101,
                                       'url':   coxi.get_absolute_url(),
                                      },
                                     ],
                         },
                         {'count':   1,
                          'id':      coxco.entity_type_id,
                          'label':   'Test Organisation',
                          'results': [{'label': str(coxco),
                                       # 'score': 102,
                                       'url':   coxco.get_absolute_url(),
                                      },
                                     ],
                         }
                        ],
            },
            results
        )

    def test_light_search02(self):
        "Credentials"
        user = self.login(is_superuser=False, allowed_apps=['creme_core'])

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        self._setup_contacts(user=self.other_user)
        coxi = FakeContact.objects.create(user=user, first_name='Coxi', last_name='Nail')

        response = self.assertGET200(self.LIGHT_URL, data={'value': 'cox'})

        self.maxDiff = None
        self.assertEqual(
            {'best':    {'label': str(coxi),
                         # 'score': 101,
                         'url':   coxi.get_absolute_url(),
                        },
             # 'query':   {'content': 'cox',
             #             'limit': 5,
             #             'ctype': None,
             #            },
             'results': [{'count':   1,
                          'id':      coxi.entity_type_id,
                          'label':   'Test Contact',
                          'results': [{'label': str(coxi),
                                       # 'score': 101,
                                       'url':   coxi.get_absolute_url(),
                                      },
                                     ],
                         },
                        ],
            },
            response.json()
        )

    def test_light_search03(self):
        "Errors"
        self.login()

        url = self.LIGHT_URL
        response = self.assertGET200(url)
        self.assertEqual(
            {
             # 'query': {'content': '',
             #           'limit': 5,
             #           'ctype': None,
             #          },
             'error': _(u'Empty search…'),
            },
            response.json()
        )

        response = self.assertGET200(url, data={'value': 'co'})
        self.assertEqual(
            {
             # 'query': {'content': 'co',
             #           'limit': 5,
             #           'ctype': None,
             #          },
             'error': _(u'Please enter at least {count} characters').format(count=3),
            },
            response.json()
        )
