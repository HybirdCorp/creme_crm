# -*- coding: utf-8 -*-

try:
    from datetime import date, timedelta
    from functools import partial
    from json import dumps as json_dump
    from random import shuffle
    import re

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.test.utils import override_settings
    from django.utils.timezone import now

    from .base import ViewsTestCase
    from ..fake_models import (FakeContact as Contact,
            FakeOrganisation as Organisation, FakeAddress as Address,
            FakeImage as Image, FakeImageCategory as ImageCategory,
            FakeActivity as Activity, FakeActivityType as ActivityType,
            FakeEmailCampaign as EmailCampaign, FakeMailingList as MailingList,
            FakeCivility as Civility, FakeSector as Sector,
            FakeDocument as Document,
            FakeFolder as Folder, FakeFolderCategory as FolderCategory)
    from creme.creme_core.core.entity_cell import (EntityCellRegularField,
            EntityCellCustomField, EntityCellFunctionField, EntityCellRelation)
    from creme.creme_core.models import (EntityFilter, EntityFilterCondition,
            HeaderFilter, RelationType, Relation, FieldsConfig,
            CremePropertyType, CremeProperty, CustomField, CustomFieldEnumValue)
    from creme.creme_core.models.header_filter import HeaderFilterList
    from creme.creme_core.models.entity_filter import EntityFilterList
    from creme.creme_core.utils import safe_unicode
    from creme.creme_core.utils.profiling import CaptureQueriesContext
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class ListViewTestCase(ViewsTestCase):
    @classmethod
    def setUpClass(cls):
        # ViewsTestCase.setUpClass()
        super(ListViewTestCase, cls).setUpClass()
        # cls.populate('creme_core')

        cls.url = Organisation.get_lv_absolute_url()
        cls.ctype = ContentType.objects.get_for_model(Organisation)

        cls._civ_backup = list(Civility.objects.all())
        Civility.objects.all().delete()

    @classmethod
    def tearDownClass(cls):
        # ViewsTestCase.tearDownClass()
        super(ListViewTestCase, cls).tearDownClass()
        Civility.objects.all().delete()
        Civility.objects.bulk_create(cls._civ_backup)

    # def setUp(self):
    #     super(ListViewTestCase, self).setUp()
    #     self._address_ordering = Address._meta.ordering
    #     Address._meta.ordering = ()

    # def tearDown(self):
    #     super(ListViewTestCase, self).tearDown()
    #     Address._meta.ordering = self._address_ordering

    def _assertNoDistinct(self, captured_sql):
        entities_q_re = re.compile(r'^SELECT (?P<distinct>DISTINCT )?(.)creme_core_cremeentity(.)\.(.)id(.)')

        count_q_found = False
        entities_q_found = False

        for sql in captured_sql:
            if sql.startswith('SELECT COUNT(*)'):
                self.assertNotIn('DISTINCT', sql)
                count_q_found = True

            match = entities_q_re.match(sql)
            if match is not None:
                self.assertFalse(match.groupdict().get('distinct'))
                entities_q_found = True

        joined_sql = '\n'.join(captured_sql)
        self.assertTrue(count_q_found,
                        'Not COUNT query found in %s' % joined_sql
                       )
        self.assertTrue(entities_q_found,
                        'Not query (which retrieve entities) found in %s' % joined_sql
                       )

    def _get_lv_content(self, response):  # TODO: slice end too
        content = response.content
        start_idx = content.find('<table id="list"')
        self.assertNotEqual(-1, start_idx)

        return content[start_idx:]

    def _get_entities_set(self, response):
        with self.assertNoException():
            entities_page = response.context['entities']

        return set(entities_page.object_list)

    @staticmethod
    def _get_sql(response):
        page = response.context['entities']
        return page.paginator.object_list.query.get_compiler('default').as_sql()[0]

    def _build_hf(self, *args):
        cells = [EntityCellRegularField.build(model=Organisation, name='name')]
        cells.extend(args)
        return HeaderFilter.create(pk='test-hf_orga', name='Orga view',
                                   model=Organisation, cells_desc=cells,
                                  )

    def test_content01(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')

        create_contact = partial(Contact.objects.create, user=user)
        spike = create_contact(first_name='Spike', last_name='Spiegel')
        faye  = create_contact(first_name='Faye',  last_name='Valentine')

        # Relation
        rtype = RelationType.create(('test-subject_piloted', 'is piloted by'),
                                    ('test-object_piloted',  'pilots'),
                                   )[0]
        Relation.objects.create(user=user, subject_entity=swordfish,
                                type=rtype, object_entity=spike,
                               )

        # Property
        create_ptype = CremePropertyType.create
        ptype1 = create_ptype(str_pk='test-prop_red',  text='is red')
        ptype2 = create_ptype(str_pk='test-prop_fast', text='is fast')
        CremeProperty.objects.create(type=ptype1, creme_entity=swordfish)

        # CustomField
        cfield = CustomField.objects.create(name='size (m)',
                                            content_type=self.ctype,
                                            field_type=CustomField.INT,
                                           )
        cfield_value = 42
        cfield.get_value_class()(custom_field=cfield, entity=bebop).set_value_n_save(cfield_value)

        hf = self._build_hf(EntityCellRelation(rtype=rtype),
                            EntityCellFunctionField.build(Organisation, 'get_pretty_properties'),
                            EntityCellCustomField(cfield),
                           )

        response = self.assertPOST200(self.url, data={'hfilter': hf.id})

        with self.assertNoException():
            ctxt = response.context
            hfilters = ctxt['header_filters']
            efilters = ctxt['entity_filters']
            orgas_page = ctxt['entities']

        self.assertIsInstance(hfilters, HeaderFilterList)
        self.assertIn(hf, hfilters)

        self.assertIsInstance(efilters, EntityFilterList)

        with self.assertNoException():
            sel_hf = hfilters.selected

        self.assertIsInstance(sel_hf, HeaderFilter)
        self.assertEqual(sel_hf.id, hf.id)

        orgas_set = set(orgas_page.object_list)
        self.assertIn(bebop,     orgas_set)
        self.assertIn(swordfish, orgas_set)

        content = self._get_lv_content(response)
        bebop_idx = self.assertFound(bebop.name, content)
        swordfish_idx = self.assertFound(swordfish.name, content)
        self.assertGreater(swordfish_idx, bebop_idx)  # Order

        content = safe_unicode(content)

        self.assertIn(rtype.predicate, content)
        self.assertCountOccurrences(unicode(spike), content, count=1)
        self.assertNotIn(faye.last_name, content)

        self.assertIn(u'<ul><li>%s</li></ul>' % ptype1.text, content)
        self.assertNotIn(ptype2.text, content)

        self.assertIn(cfield.name, content)
        self.assertIn(str(cfield_value), content)

        self.assertEqual(2, orgas_page.paginator.count)

    def test_content02(self):
        "FieldsConfig"
        user = self.login()

        valid_fname = 'name'
        hidden_fname = 'url_site'

        build_cell = partial(EntityCellRegularField.build, model=Organisation)
        hf = self._build_hf(build_cell(name=valid_fname), build_cell(name=hidden_fname))

        FieldsConfig.create(Organisation,
                            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
                           )

        bebop = Organisation.objects.create(user=user, name='Bebop', url_site='sww.bebop.mrs')

        response = self.assertPOST200(self.url, data={'hfilter': hf.id})

        content = self._get_lv_content(response)
        self.assertIn(bebop.name, content)
        self.assertNotIn(bebop.url_site, content, '"url_site" not hidden')

    def test_order01(self):  # TODO: test with ajax ?
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')

        self._build_hf()

        def post(first, second, sort_order='', sort_field='regular_field-name'):
            response = self.assertPOST200(self.url,
                                          data={'sort_field': sort_field,
                                                'sort_order': sort_order,
                                               }
                                         )
            content = self._get_lv_content(response)
            first_idx = self.assertFound(first.name, content)
            second_idx = self.assertFound(second.name, content)
            self.assertLess(first_idx, second_idx)

        post(bebop, swordfish)
        post(swordfish, bebop, '-')
        post(bebop, swordfish, '*')  # Invalid value
        post(bebop, swordfish, sort_field='unknown')  # Invalid value

    # TODO: for now there should not be CremeEntity with 'id' as ordering
    # def test_order02_prelude(self):
    #     "Sort by ForeignKey"
    #     #NB: the DatabaseError cannot be rollbacked here in the test context,
    #     #    so we cannot do this test in test_order02, because it cause an error.
    #     try:
    #         bool(Contact.objects.order_by('image'))
    #     except:
    #         pass
    #     else:
    #         self.fail('ORM bug has been fixed ?! => reactivate FK on CremeEntity sorting')

    def assertListViewContentOrder(self, response, key, entries):
        content = safe_unicode(self._get_lv_content(response))
        lines = [(self.assertFound(unicode(getattr(e, key)), content), e)
                    for e in entries
                ]
        self.assertListEqual(list(entries),
                             [line[1] for line in sorted(lines, key=lambda e: e[0])]
                            )

    def test_order02(self):
        "Sort by ForeignKey"
        user = self.login()

        create_civ = Civility.objects.create
        mister = create_civ(title='Mister')
        miss   = create_civ(title='Miss')
        self.assertLess(mister.id, miss.id)

        create_contact = partial(Contact.objects.create, user=user)
        spike = create_contact(first_name='Spike',  last_name='Spiegel',   civility=mister)
        faye  = create_contact(first_name='Faye',   last_name='Valentine', civility=miss)
        ed    = create_contact(first_name='Edward', last_name='Wong')

        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=Contact)

        build_cell = partial(EntityCellRegularField.build, model=Contact)
        cell_image    = build_cell(name='image')
        cell_img_name = build_cell(name='image__name')
        cell_civ      = build_cell(name='civility')
        cell_civ_name = build_cell(name='civility__title')

        self.assertTrue(cell_civ.sortable)
        self.assertTrue(cell_image.sortable)
        self.assertTrue(cell_img_name.sortable)
        self.assertTrue(cell_civ_name.sortable)

        hf.cells = [build_cell(name='last_name'),
                    cell_image, cell_img_name, cell_civ, cell_civ_name,
                   ]
        hf.save()

        url = Contact.get_lv_absolute_url()

        # ---------------------------------------------------------------------
        response = self.assertPOST200(url, data={'hfilter': hf.id})

        with self.assertNoException():
            selected_hf = response.context['header_filters'].selected

        self.assertEqual(hf, selected_hf)

        # ---------------------------------------------------------------------
        # FK on CremeEntity we just check that it does not crash
        self.assertPOST200(url, data={'sort_field': 'regular_field-image'})

        # ---------------------------------------------------------------------

        def post(field_name, reverse, *contacts):
            response = self.assertPOST200(url,
                                          data={'sort_field': field_name,
                                                'sort_order': '-' if reverse else '',
                                               }
                                         )
            content = self._get_lv_content(response)
            indices = [self.assertFound(c.last_name, content)
                        for c in contacts
                      ]
            self.assertEqual(indices, sorted(indices))

            return content

        # NB: it seems that NULL are not ordered in the same way on different DB engines
        content = post('regular_field-civility', False, faye, spike)  # Sorting is done by 'title'
        self.assertFound(ed.last_name, content)

        post('regular_field-civility', True, spike, faye)
        post('regular_field-civility__title', False, faye, spike)
        post('regular_field-civility__title', True, spike, faye)

    def test_order03(self):
        "Un-sortable fields: ManyToMany, FunctionFields"
        user = self.login()

        # Bug on ORM with M2M happens only if there is at least one entity
        EmailCampaign.objects.create(user=user, name='Camp01')

        fname = 'mailing_lists'
        func_field_name = 'get_pretty_properties'
        HeaderFilter.create(pk='test-hf_camp', name='Campaign view', model=EmailCampaign,
                            cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                                        (EntityCellRegularField, {'name': fname}),
                                        (EntityCellFunctionField, {'func_field_name': func_field_name}),
                                       ]
                           )

        url = EmailCampaign.get_lv_absolute_url()
        # We just check that it does not crash
        self.assertPOST200(url, data={'sort_field': 'regular_field-' + fname})
        self.assertPOST200(url, data={'sort_field': 'function_field-' + func_field_name})

    @override_settings(FAST_QUERY_MODE_THRESHOLD=100000)
    def test_order04(self):
        "Ordering = '-fieldname'"
        user = self.login()
        self.assertTrue('-start', Activity._meta.ordering[0])

        act_type = ActivityType.objects.all()[0]
        create_act = partial(Activity.objects.create, user=user, type=act_type)
        act1 = create_act(title='Act#1', start=now())
        act2 = create_act(title='Act#2', start=act1.start + timedelta(hours=1))

        hf = self.get_object_or_fail(HeaderFilter, pk='creme_core-hf_fakeactivity')  # See fake populate

        response = self.assertPOST200(Activity.get_lv_absolute_url(), {'hfilter': hf.pk})
        content = self._get_lv_content(response)
        first_idx  = self.assertFound(act2.title, content)
        second_idx = self.assertFound(act1.title, content)
        self.assertLess(first_idx, second_idx)

        with self.assertNoException():
            lvs = response.context['list_view_state']
            sort_field = lvs.sort_field
            sort_order = lvs.sort_order
            # ordering = lvs._ordering

        self.assertEqual('regular_field-start', sort_field)
        self.assertEqual('-',  sort_order)
        # self.assertEqual(['-start'], ordering)

        self.assertRegexpMatches(self._get_sql(response),
                                 'ORDER BY '
                                 '.creme_core_fakeactivity.\..start. DESC( NULLS LAST)?\, '
                                 '.creme_core_fakeactivity.\..cremeentity_ptr_id. DESC( NULLS LAST)?$'
                                )

    @override_settings(FAST_QUERY_MODE_THRESHOLD=100000)
    def test_ordering_default(self):
        user = self.login()
        self.assertEqual(('last_name', 'first_name'), Contact._meta.ordering)

        create_contact = partial(Contact.objects.create, user=user)
        create_contact(first_name='Spike',  last_name='Spiegel')
        create_contact(first_name='Faye',   last_name='Valentine')
        create_contact(first_name='Edward', last_name='Wong')

        url = Contact.get_lv_absolute_url()
        # For the filter to prevent an issue when HeaderFiltersTestCase is launched before this test
        hf = self.get_object_or_fail(HeaderFilter, pk='creme_core-hf_fakecontact')  # See fake populate
        response = self.assertPOST200(url, {'hfilter': hf.pk})

        entries = Contact.objects.all()
        self.assertListViewContentOrder(response, 'last_name', entries)

        listview_state = response.context['list_view_state']
        self.assertEqual('regular_field-last_name', listview_state.sort_field)
        self.assertEqual('', listview_state.sort_order)
        # self.assertListEqual(['last_name', 'first_name'], listview_state._ordering)

        self.assertRegexpMatches(self._get_sql(response),
                                 'ORDER BY '
                                 '.creme_core_fakecontact.\..last_name. ASC( NULLS FIRST)?\, '
                                 '.creme_core_fakecontact.\..first_name. ASC( NULLS FIRST)?\, '
                                 '.creme_core_fakecontact.\..cremeentity_ptr_id. ASC( NULLS FIRST)?$'
                                )

    def test_ordering_merge_column_and_default(self):
        self.assertEqual(('last_name', 'first_name'), Contact._meta.ordering)
        user = self.login()

        create_civ = Civility.objects.create
        mister = create_civ(title='Mister')
        miss   = create_civ(title='Miss')
        self.assertLess(mister.id, miss.id)

        create_contact = partial(Contact.objects.create, user=user)
        spike = create_contact(first_name='Spike',  last_name='Spiegel',   civility=mister)
        faye = create_contact(first_name='Faye',   last_name='Valentine', civility=miss)
        ed = create_contact(first_name='Edward', last_name='Wong')

        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=Contact,
                                 cells_desc=[(EntityCellRegularField, {'name': 'civility'}),
                                             (EntityCellRegularField, {'name': 'last_name'}),
                                             (EntityCellRegularField, {'name': 'first_name'}),
                                            ],
                                )

        contacts = Contact.objects.filter(pk__in=(spike, faye, ed))
        url = Contact.get_lv_absolute_url()
        response = self.assertPOST200(url, data={'hfilter': hf.id,
                                                 'sort_field': 'regular_field-civility',
                                                 'sort_order': ''})

        entries = contacts.order_by('civility', 'last_name', 'first_name')
        self.assertListViewContentOrder(response, 'last_name', entries)

        response = self.assertPOST200(url, data={'hfilter': hf.id,
                                                 'sort_field': 'regular_field-civility',
                                                 'sort_order': '-'})

        entries = contacts.order_by('-civility', 'last_name', 'first_name')
        self.assertListViewContentOrder(response, 'last_name', entries)

        response = self.assertPOST200(url, data={'hfilter': hf.id,
                                                 'sort_field': 'regular_field-first_name',
                                                 'sort_order': ''})

        entries = contacts.order_by('first_name', 'last_name')
        self.assertListViewContentOrder(response, 'last_name', entries)

        response = self.assertPOST200(url, data={'hfilter': hf.id,
                                                 'sort_field': 'regular_field-first_name',
                                                 'sort_order': '-'})

        entries = contacts.order_by('-first_name', 'last_name')
        self.assertListViewContentOrder(response, 'last_name', entries)

    def test_ordering_related_column(self):
        user = self.login()

        self.assertEqual(('last_name', 'first_name'), Contact._meta.ordering)
        self.assertFalse(bool(Address._meta.ordering))

        def create_contact(first_name, last_name, address):
            contact = Contact.objects.create(user=user, first_name=first_name, last_name=last_name)
            contact.address = Address.objects.create(entity=contact, value=address)
            contact.save()
            return contact

        create_contact(first_name='Spike',  last_name='Spiegel',   address='C')
        create_contact(first_name='Faye',   last_name='Valentine', address='B')
        create_contact(first_name='Edward', last_name='Wong',      address='A')

        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=Contact,
                                 cells_desc=[(EntityCellRegularField, {'name': 'civility'}),
                                             (EntityCellRegularField, {'name': 'last_name'}),
                                             (EntityCellRegularField, {'name': 'first_name'}),
                                             (EntityCellRegularField, {'name': 'address'}),
                                         ],
                                )

        url = Contact.get_lv_absolute_url()
        # For the filter to prevent an issue when HeaderFiltersTestCase is launched before this test
        response = self.assertPOST200(url, {'hfilter':     hf.id,
                                            'sort_field': 'regular_field-address',
                                            'sort_order': '',
                                           })

        entries = Contact.objects.order_by('address_id', 'last_name', 'first_name')
        self.assertListViewContentOrder(response, 'last_name', entries)

        listview_state = response.context['list_view_state']
        self.assertEqual('regular_field-address', listview_state.sort_field)
        self.assertEqual('', listview_state.sort_order)
        # self.assertListEqual(['address__pk', 'last_name', 'first_name'],
        #                      listview_state._ordering
        #                     )
        self.assertRegexpMatches(self._get_sql(response),
                                 'ORDER BY '
                                 '.creme_core_fakecontact.\..address_id. ASC( NULLS FIRST)?\, '
                                 '.creme_core_fakecontact.\..last_name. ASC( NULLS FIRST)?\, '
                                 '.creme_core_fakecontact.\..first_name. ASC( NULLS FIRST)?\, '
                                 '.creme_core_fakecontact.\..cremeentity_ptr_id. ASC( NULLS FIRST)?$'
                                )

        # tested in test_list_view_state
        # Address._meta.ordering = ('value',)  # TODO: create another test model instead ??
        #
        # response = self.assertPOST200(url, {'hfilter': hf.id,
        #                                     'sort_field': 'regular_field-address',
        #                                     'sort_order': '',
        #                                    }
        #                              )
        #
        # entries = Contact.objects.order_by('address__value', 'last_name', 'first_name')
        # self.assertListViewContentOrder(response, 'last_name', entries)
        #
        # listview_state = response.context['list_view_state']
        # self.assertEqual('regular_field-address', listview_state.sort_field)
        # self.assertEqual('', listview_state.sort_order)
        # self.assertListEqual(['address__value', 'last_name', 'first_name'],
        #                      listview_state._ordering
        #                     )

    def test_ordering_customfield_column(self):
        "Custom field ordering is ignored in current implementation"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')

        cfield = CustomField.objects.create(name='size (m)',
                                            content_type=self.ctype,
                                            field_type=CustomField.INT,
                                           )
        klass = cfield.get_value_class()

        def set_cfvalue(entity, value):
            klass(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(bebop,     42)
        set_cfvalue(swordfish, 12)
        set_cfvalue(redtail,   4)

        cfield_cell = EntityCellCustomField(cfield)
        hf = self._build_hf(cfield_cell)

        url = Organisation.get_lv_absolute_url()
        response = self.assertPOST200(url, {'hfilter': hf.pk,
                                            'sort_field': cfield_cell.key,
                                            'sort_order': '',
                                           }
                                     )

        entries = Organisation.objects.order_by('name')
        self.assertListViewContentOrder(response, 'name', entries)

    def _aux_test_ordering_fastmode(self):
        user = self.login()

        create_contact = partial(Contact.objects.create, user=user)
        create_contact(first_name='Spike',  last_name='Spiegel')
        create_contact(first_name='Faye',   last_name='Valentine')
        create_contact(first_name='Edward', last_name='Wong')

        build_cell = partial(EntityCellRegularField.build, model=Contact)
        cell1 = build_cell(name='birthday')
        hf = HeaderFilter.create(pk='test-hf_contact', name='Contact view',
                                 model=Contact,
                                 cells_desc=[cell1,
                                             build_cell(name='last_name'),
                                             build_cell(name='first_name'),
                                            ],
                                  )

        context = CaptureQueriesContext()

        with context:
            self.assertPOST200(Contact.get_lv_absolute_url(),
                               data={'hfilter': hf.pk,
                                     'sort_field': cell1.key,
                                     'sort_order': '',
                                    }
                               )

        main_sql_match = re.compile('SELECT .creme_core_cremeentity.\..id., .*'
                                    '.creme_core_fakecontact.\..last_name., .*'
                                    'WHERE .creme_core_cremeentity.\..is_deleted. = '
                                   ).match
        main_sql = [sql for sql in context.captured_sql if main_sql_match(sql)]

        if not main_sql:
            self.fail('No main Listview query in:\n%s' % '\n'.join(context.captured_sql))
        elif len(main_sql) >= 2:
            self.fail('There should be one SQL query: %s' % main_sql)

        return main_sql[0]

    @override_settings(FAST_QUERY_MODE_THRESHOLD=100000)
    def test_ordering_fastmode_01(self):
        "Fast mode=OFF"
        sql = self._aux_test_ordering_fastmode()
        self.assertRegexpMatches(sql,
                                 'ORDER BY '
                                 '.creme_core_fakecontact.\..birthday. ASC( NULLS FIRST)?, '
                                 '.creme_core_fakecontact.\..last_name. ASC( NULLS FIRST)?, '
                                 '.creme_core_fakecontact.\..first_name. ASC( NULLS FIRST)?, '
                                 '.creme_core_fakecontact.\..cremeentity_ptr_id. ASC( NULLS FIRST)? LIMIT'
                                )

    @override_settings(FAST_QUERY_MODE_THRESHOLD=2)
    def test_ordering_fastmode_02(self):
        "Fast mode=ON"
        sql = self._aux_test_ordering_fastmode()
        self.assertRegexpMatches(sql,
                                 'ORDER BY'
                                 ' .creme_core_fakecontact.\..birthday. ASC( NULLS FIRST)?,'
                                 ' .creme_core_fakecontact.\..cremeentity_ptr_id. ASC( NULLS FIRST)? LIMIT'
                                )

    def test_efilter01(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        efilter = EntityFilter.create('test-filter01', 'Red', Organisation,
                                      user=user, is_custom=False,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                        model=Organisation,
                                                        operator=EntityFilterCondition.ISTARTSWITH,
                                                        name='name', values=['Red'],
                                                    ),
                                                 ],
                                     )

        context = CaptureQueriesContext()

        with context:
            response = self.assertPOST200(self.url, data={'filter': efilter.id})

        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name, content)
        self.assertCountOccurrences(redtail.name, content, count=1)
        self.assertCountOccurrences(dragons.name, content, count=1)

        self.assertEqual(2, response.context['entities'].paginator.count)

        self._assertNoDistinct(context.captured_sql)

    def test_qfilter_GET(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        context = CaptureQueriesContext()

        with context:
            response = self.assertGET200(self.url, data={'q_filter': '{"name":"Bebop"}'})

        content = self._get_lv_content(response)
        self.assertCountOccurrences('value="{&quot;name&quot;:&quot;%s&quot;}"' % bebop.name,
                                    content, count=1
                                   )
        self.assertCountOccurrences(bebop.name, content, count=2)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        self.assertEqual(1, response.context['entities'].paginator.count)

        # TODO
        # self._assertNoDistinct(context.captured_sql)

    def test_qfilter_POST(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        response = self.assertPOST200(self.url, data={'q_filter': '{"name":"Bebop"}'})

        content = self._get_lv_content(response)
        self.assertCountOccurrences('value="{&quot;name&quot;:&quot;%s&quot;}"' % bebop.name,
                                    content, count=1
                                   )
        self.assertCountOccurrences(bebop.name, content, count=2)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        self.assertEqual(1, response.context['entities'].paginator.count)

    def test_qfilter_invalid_json(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        # Invalid json : ignore filter
        response = self.assertGET200(self.url, data={'q_filter': '{"name":"Bebop"'})

        content = self._get_lv_content(response)
        self.assertIn(bebop.name, content)
        self.assertIn(redtail.name, content)
        self.assertIn(dragons.name, content)

    def test_qfilter_invalid_Q(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        # Invalid field : ignore filter
        response = self.assertGET200(self.url, data={'q_filter': '{"unknown_model_field":"Bebop"}'})

        content = self._get_lv_content(response)
        self.assertIn(bebop.name, content)
        self.assertIn(redtail.name, content)
        self.assertIn(dragons.name, content)

    @override_settings(FAST_QUERY_MODE_THRESHOLD=1000000, PAGE_SIZES=[10, 25], DEFAULT_PAGE_SIZE_IDX=1)
    def test_search_regularfields01(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish',   phone='668899')
        redtail   = create_orga(name='Redtail',     phone='889977')
        dragons   = create_orga(name='Red Dragons', phone='123')

        self._build_hf(EntityCellRegularField.build(model=Organisation, name='phone'))

        url = self.url

        def build_data(name='', phone='', search=1):
            return {'_search': search,
                    'regular_field-name': name,
                    'regular_field-phone': phone,
                   }

        response = self.assertPOST200(url, data=build_data('Red'))
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,     content)
        self.assertNotIn(swordfish.name, content)
        self.assertCountOccurrences(redtail.name, content, count=1)
        self.assertCountOccurrences(dragons.name, content, count=1)
        self.assertEqual(2, response.context['entities'].paginator.count)

        response = self.assertPOST200(url, data=build_data('', '88'))
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertIn(redtail.name,    content)
        self.assertNotIn(dragons.name, content)

        response = self.assertPOST200(url, data=build_data('Red', '88'))
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,     content)
        self.assertNotIn(swordfish.name, content)
        self.assertIn(redtail.name,      content)
        self.assertNotIn(dragons.name,   content)

        context = CaptureQueriesContext()

        with context:
            response = self.assertPOST200(url, data=build_data(search=0))

        content = self._get_lv_content(response)
        self.assertIn(bebop.name,     content)
        self.assertIn(swordfish.name, content)
        self.assertIn(redtail.name,   content)
        self.assertIn(dragons.name,   content)
        self.assertEqual(4, response.context['entities'].paginator.count)

        optimized_count = 0

        # TODO: use regex to reduce code ?
        db_engine = settings.DATABASES['default']['ENGINE']
        if db_engine == 'django.db.backends.mysql':
            fast_sql = 'SELECT COUNT(*) AS `__count` FROM `creme_core_cremeentity` WHERE ' \
                       '(`creme_core_cremeentity`.`is_deleted` = 0 AND ' \
                       '`creme_core_cremeentity`.`entity_type_id` = %s)' % self.ctype.id
            slow_sql = 'SELECT COUNT(*) FROM (SELECT DISTINCT `creme_core_cremeentity`.`id`'
        elif db_engine == 'django.db.backends.sqlite3':
            fast_sql = 'SELECT COUNT(*) AS "__count" FROM "creme_core_cremeentity" ' \
                            'WHERE ("creme_core_cremeentity"."is_deleted" = %s AND ' \
                            '"creme_core_cremeentity"."entity_type_id" = %s)'
            slow_sql = 'SELECT COUNT(*) FROM (SELECT DISTINCT "creme_core_cremeentity"."id"'
        elif db_engine == 'django.db.backends.postgresql_psycopg2':
            fast_sql = 'SELECT COUNT(*) AS "__count" FROM "creme_core_cremeentity" WHERE ' \
                       '("creme_core_cremeentity"."is_deleted" = false AND ' \
                       '"creme_core_cremeentity"."entity_type_id" = %s)' % self.ctype.id
            slow_sql = 'SELECT COUNT(*) FROM (SELECT DISTINCT "creme_core_cremeentity"."id"'
        else:
            self.fail('This RDBMS is not managed by this test case.')

        for sql in context.captured_sql:
            if fast_sql in sql:
                optimized_count += 1

            self.assertNotIn(slow_sql, sql)

        self.assertEqual(1, optimized_count, context.captured_queries)

    def test_search_regularfields02(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop = create_orga(name='Bebop inc', subject_to_vat=False)
        nerv  = create_orga(name='NERV',      subject_to_vat=True)
        seele = create_orga(name='Seele',     subject_to_vat=True)

        hf = self._build_hf(EntityCellRegularField.build(model=Organisation, name='subject_to_vat'))
        url = self.url
        data = {'hfilter': hf.id, '_search': 1}
        response = self.assertPOST200(url, data=dict(data, **{'regular_field-subject_to_vat': '1'}))
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop, orgas_set)
        self.assertIn(nerv,     orgas_set)
        self.assertIn(seele,    orgas_set)

        # -------------------------------
        context = CaptureQueriesContext()
        with context:
            response = self.assertPOST200(url, data=dict(data, **{'regular_field-subject_to_vat': '0'}))

        orgas_set = self._get_entities_set(response)
        self.assertIn(bebop,    orgas_set)
        self.assertNotIn(nerv,  orgas_set)
        self.assertNotIn(seele, orgas_set)

        # TODO
        # self._assertNoDistinct(context.captured_sql)

    def test_search_regularfields03(self):
        "ForeignKey (NULL or not)"
        user = self.login()

        create_sector = Sector.objects.create
        mercenary = create_sector(title='Mercenary')
        robotics  = create_sector(title='Robotics')

        create_orga = partial(Organisation.objects.create, user=user)
        bebop = create_orga(name='Bebop inc', sector=mercenary)
        nerv  = create_orga(name='NERV',      sector=robotics)
        seele = create_orga(name='Seele')

        hf = self._build_hf(EntityCellRegularField.build(model=Organisation, name='sector'))

        url = self.url
        data = {'hfilter': hf.id, '_search': 1}
        response = self.assertPOST200(url, data=dict(data, **{'regular_field-sector': str(mercenary.id)}))
        orgas_set = self._get_entities_set(response)
        self.assertIn(bebop,    orgas_set)
        self.assertNotIn(nerv,  orgas_set)
        self.assertNotIn(seele, orgas_set)

        response = self.assertPOST200(url, data=dict(data, **{'regular_field-sector': 'NULL'}))
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop, orgas_set)
        self.assertNotIn(nerv,  orgas_set)
        self.assertIn(seele,    orgas_set)

    def test_search_datefields01(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop',     creation_date=date(year=2075, month=3, day=26))
        swordfish = create_orga(name='Swordfish', creation_date=date(year=2074, month=6, day=5))
        redtail   = create_orga(name='Redtail',   creation_date=date(year=2076, month=7, day=25))
        dragons   = create_orga(name='Red Dragons')

        hf = self._build_hf(EntityCellRegularField.build(model=Organisation, name='creation_date'))
        url = self.url
        build_data = lambda cdate: {'hfilter': hf.id, '_search': 1, 'regular_field-creation_date': cdate}

        response = self.assertPOST200(url, data=build_data(['1-1-2075']))
        content = self._get_lv_content(response)
        self.assertIn(bebop.name,        content)
        self.assertNotIn(swordfish.name, content)
        self.assertIn(redtail.name,      content)
        self.assertNotIn(dragons.name,   content)

        response = self.assertPOST200(url, data=build_data(['', '1-1-2075']))
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        response = self.assertPOST200(url, data=build_data(['1-1-2074', '31-12-2074']))
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

    def test_search_datetimefields01(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop      = create_orga(name='Bebop')
        swordfish  = create_orga(name='Swordfish')
        swordfish2 = create_orga(name='Swordfish II')
        sf_alpha   = create_orga(name='Swordfish Alpha')
        redtail    = create_orga(name='Redtail')

        def set_created(orga, dt):
            Organisation.objects.filter(pk=orga.id).update(created=dt)

        create_dt = self.create_datetime
        set_created(bebop,      create_dt(year=2075, month=3, day=26))
        set_created(swordfish,  create_dt(year=2074, month=6, day=5, hour=12))
        set_created(swordfish2, create_dt(year=2074, month=6, day=6, hour=0))  # Next day
        set_created(sf_alpha,   create_dt(year=2074, month=6, day=4, hour=23, minute=59))  # Previous day
        set_created(redtail,    create_dt(year=2076, month=7, day=25))

        hf = self._build_hf(EntityCellRegularField.build(model=Organisation, name='created'))
        url = self.url

        def post(created):
            response = self.assertPOST200(url, data={'hfilter': hf.id,
                                                     '_search': 1,
                                                     'regular_field-created': created,
                                                    }
                                         )
            return  self._get_lv_content(response)

        content = post(['1-1-2075'])
        self.assertIn(bebop.name,        content)
        self.assertNotIn(swordfish.name, content)
        self.assertIn(redtail.name,      content)

        content = post(['', '1-1-2075'])
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)

        content = post(['1-1-2074', '31-12-2074'])
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)

        content = post(['5-6-2074', '5-6-2074'])
        self.assertNotIn(bebop.name,      content)
        self.assertIn(swordfish.name,     content)
        self.assertNotIn(swordfish2.name, content)
        self.assertNotIn(sf_alpha.name,   content)
        self.assertNotIn(redtail.name,    content)

    def test_search_fk01(self):
        user = self.login()

        create_civ = Civility.objects.create
        mister = create_civ(title='Mister')
        miss   = create_civ(title='Miss')
        self.assertLess(mister.id, miss.id)

        create_img = partial(Image.objects.create, user=user)
        img_faye = create_img(name='Faye selfie')
        img_ed   = create_img(name='Ed selfie')

        create_contact = partial(Contact.objects.create, user=user)
        spike = create_contact(first_name='Spike',  last_name='Spiegel',   civility=mister)
        faye  = create_contact(first_name='Faye',   last_name='Valentine', civility=miss, image=img_faye)
        ed    = create_contact(first_name='Edward', last_name='Wong',                     image=img_ed)

        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=Contact)

        build_cell = partial(EntityCellRegularField.build, model=Contact)
        cell_image    = build_cell(name='image')
        cell_img_name = build_cell(name='image__name')
        cell_civ      = build_cell(name='civility')
        cell_civ_name = build_cell(name='civility__title')

        self.assertTrue(cell_civ.has_a_filter)
        self.assertTrue(cell_civ_name.has_a_filter)
        self.assertTrue(cell_img_name.has_a_filter)
        self.assertTrue(cell_image.has_a_filter)
        self.assertEqual('image__name__icontains', cell_img_name.filter_string)
        self.assertEqual('image__header_filter_search_field__icontains',
                         cell_image.filter_string
                        )

        hf.cells = [build_cell(name='last_name'),
                    cell_image, cell_img_name, cell_civ, cell_civ_name,
                   ]
        hf.save()

        url = Contact.get_lv_absolute_url()

        # ---------------------------------------------------------------------
        response = self.assertPOST200(url, data={'hfilter': hf.id})

        with self.assertNoException():
            selected_hf = response.context['header_filters'].selected

        self.assertEqual(hf, selected_hf)

        # ---------------------------------------------------------------------
        data = {'_search': 1}
        response = self.assertPOST200(url, data=dict(data, **{'regular_field-civility': mister.id}))
        content = self._get_lv_content(response)
        self.assertCountOccurrences(spike.last_name, content, count=1)
        self.assertNotIn(faye.last_name, content)
        self.assertNotIn(ed.last_name,   content)

        # ---------------------------------------------------------------------
        response = self.assertPOST200(url, data=dict(data, **{'regular_field-civility__title': 'iss'}))
        content = self._get_lv_content(response)
        self.assertNotIn(spike.last_name, content)
        self.assertIn(faye.last_name,     content)
        self.assertNotIn(ed.last_name,    content)

        # ---------------------------------------------------------------------
        response = self.assertPOST200(url, data=dict(data, **{'regular_field-image__name': img_ed.name}))
        content = self._get_lv_content(response)
        self.assertNotIn(spike.last_name, content)
        self.assertNotIn(faye.last_name,  content)
        self.assertIn(ed.last_name,       content)

        # ---------------------------------------------------------------------
        response = self.assertPOST200(url, data=dict(data, **{'regular_field-image': img_ed.name}))
        content = self._get_lv_content(response)
        self.assertNotIn(spike.last_name, content)
        self.assertNotIn(faye.last_name,  content)
        self.assertIn(ed.last_name,       content)

    def test_search_fk02(self):
        "Search on a subfield which is a FK too"
        user = self.login()

        create_cat = FolderCategory.objects.create
        cat1 = create_cat(name='Maps')
        cat2 = create_cat(name='Blue prints')

        create_folder = partial(Folder.objects.create, user=user)
        folder1 = create_folder(title='Earth maps', category=cat1)
        folder2 = create_folder(title='Mars maps',  category=cat1)
        folder3 = create_folder(title='Ships',      category=cat2)
        folder4 = create_folder(title="Faye's pix")

        create_doc = partial(Document.objects.create, user=user)
        doc1 = create_doc(title='Japan map',   folder=folder1)
        doc2 = create_doc(title='Mars city 1', folder=folder2)
        doc3 = create_doc(title='Swordfish',   folder=folder3)
        doc4 = create_doc(title='Money!!.jpg', folder=folder4)

        build_cell = partial(EntityCellRegularField.build, model=Document)
        hf = HeaderFilter.create(pk='test-hf_doc', name='Doc view', model=Document,
                                 cells_desc=[build_cell(name='title'),
                                             build_cell(name='folder__category'),
                                            ],
                                )

        response = self.assertPOST200(Document.get_lv_absolute_url(),
                                      data={'hfilter': hf.id, '_search': 1,
                                            'regular_field-folder__category': cat1.id,
                                           }
                                     )
        content = self._get_lv_content(response)
        self.assertIn(doc1.title, content)
        self.assertIn(doc2.title, content)
        self.assertNotIn(doc3.title, content)
        self.assertNotIn(doc4.title, content)

        # '*is empty*'
        response = self.assertPOST200(Document.get_lv_absolute_url(),
                                      data={'hfilter': hf.id, '_search': 1,
                                            'regular_field-folder__category': 'NULL',
                                           }
                                     )
        content = self._get_lv_content(response)
        self.assertNotIn(doc1.title, content)
        self.assertNotIn(doc2.title, content)
        self.assertNotIn(doc3.title, content)
        self.assertIn(doc4.title, content)

    def test_search_fk03(self):
        "Search on a subfield which is a FK on CremeEntity"
        user = self.login()

        create_folder = partial(Folder.objects.create, user=user)
        p_folder1 = create_folder(title='Maps')
        p_folder2 = create_folder(title='Pix')

        folder1 = create_folder(title='Earth', parent=p_folder1)
        folder2 = create_folder(title='Mars',  parent=p_folder1)
        folder3 = create_folder(title='Ships')
        folder4 = create_folder(title="Faye's pix", parent=p_folder2)

        create_doc = partial(Document.objects.create, user=user)
        doc1 = create_doc(title='Japan',       folder=folder1)
        doc2 = create_doc(title='Mars city 1', folder=folder2)
        doc3 = create_doc(title='Swordfish',   folder=folder3)
        doc4 = create_doc(title='Money!!.jpg', folder=folder4)

        build_cell = partial(EntityCellRegularField.build, model=Document)
        hf = HeaderFilter.create(pk='test-hf_doc', name='Doc view', model=Document,
                                 cells_desc=[build_cell(name='title'),
                                             build_cell(name='folder__parent'),
                                            ],
                                )

        response = self.assertPOST200(Document.get_lv_absolute_url(),
                                      data={'hfilter': hf.id,
                                            '_search': 1,
                                            'regular_field-folder__parent': p_folder1.title,
                                           }
                                     )
        content = self._get_lv_content(response)
        self.assertIn(doc1.title, content)
        self.assertIn(doc2.title, content)
        self.assertNotIn(doc3.title, content)
        self.assertNotIn(doc4.title, content)

    def test_search_m2mfields01(self):
        "M2M to CremeEntity model"
        user = self.login()
        hf = HeaderFilter.create(pk='test-hf_camp', name='Campaign view',
                                 model=EmailCampaign,
                                )
        build_cell = partial(EntityCellRegularField.build, model=EmailCampaign)

        cell_m2m = build_cell(name='mailing_lists')
        self.assertTrue(cell_m2m.has_a_filter)
        self.assertFalse(cell_m2m.sortable)
        self.assertEqual('mailing_lists__header_filter_search_field__icontains',
                         cell_m2m.filter_string
                        )

        hf.cells = [build_cell(name='name'), cell_m2m]
        hf.save()

        create_mlist = partial(MailingList.objects.create, user=user)
        ml1 = create_mlist(name='Bebop staff')
        ml2 = create_mlist(name='Mafia staff')

        create_camp = partial(EmailCampaign.objects.create, user=user)
        camp1 = create_camp(name='Ships')
        camp2 = create_camp(name='Bonzais')
        camp3 = create_camp(name='Mushrooms')

        camp1.mailing_lists = [ml1, ml2]
        camp2.mailing_lists = [ml1]

        def search(term):
            response = self.assertPOST200(EmailCampaign.get_lv_absolute_url(),
                                          data={'hfilter': hf.id,
                                                '_search': 1,
                                                'regular_field-mailing_lists': term,
                                               }
                                         )
            return self._get_lv_content(response)

        content = search('Bebo')
        self.assertCountOccurrences(camp1.name, content, count=1)
        self.assertCountOccurrences(camp2.name, content, count=1)
        self.assertNotIn(camp3.name, content)

        content = search('afia')
        self.assertCountOccurrences(camp1.name, content, count=1)
        self.assertNotIn(camp2.name, content)
        self.assertNotIn(camp3.name, content)

        content = search('staff')
        self.assertCountOccurrences(camp1.name, content, count=1)  # Not 2 !!

    def test_search_m2mfields02(self):
        "M2M to basic model"
        user = self.login()
        hf = HeaderFilter.create(pk='test-hf_img', name='Image view', model=Image)
        build_cell = partial(EntityCellRegularField.build, model=Image)

        cell_m2m = build_cell(name='categories')
        self.assertTrue(cell_m2m.has_a_filter)
        self.assertEqual('categories', cell_m2m.filter_string)

        hf.cells = [build_cell(name='name'), cell_m2m]
        hf.save()

        cat1, cat2 = ImageCategory.objects.all()[:2]

        create_img = partial(Image.objects.create, user=user)
        img1 = create_img(name='Bebop image')
        img2 = create_img(name='Dragon logo')
        img3 = create_img(name='Mushrooms image')

        img1.categories = [cat1, cat2]
        img2.categories = [cat1]

        def search(searched):
            response = self.assertPOST200(Image.get_lv_absolute_url(),
                                          data={'hfilter': hf.id,
                                                '_search': 1,
                                                cell_m2m.key: searched,
                                               }
                                         )
            return self._get_lv_content(response)

        content = search(cat1.name[:5])  # Invalid we need an ID => no filter
        self.assertIn(img1.name, content)
        self.assertIn(img3.name, content)

        content = search(cat1.id)
        self.assertIn(img1.name,    content)
        self.assertIn(img2.name,    content)
        self.assertNotIn(img3.name, content)

        content = search(cat2.id)
        self.assertIn(img1.name,    content)
        self.assertNotIn(img2.name, content)
        self.assertNotIn(img3.name, content)

        content = search('NULL')
        self.assertNotIn(img1.name, content)
        self.assertNotIn(img2.name, content)
        self.assertIn(img3.name,    content)

    def test_search_m2mfields03(self):
        "M2M to basic model + sub-field"
        user = self.login()
        hf = HeaderFilter.create(pk='test-hf_img', name='Image view', model=Image)
        build_cell = partial(EntityCellRegularField.build, model=Image)

        cell_m2m = build_cell(name='categories__name')
        self.assertTrue(cell_m2m.has_a_filter)

        hf.cells = [build_cell(name='name'), cell_m2m]
        hf.save()

        cat1, cat2 = ImageCategory.objects.all()[:2]

        create_img = partial(Image.objects.create, user=user)
        img1 = create_img(name='Bebop image')
        img2 = create_img(name='Dragon logo')
        img3 = create_img(name='Mushrooms image')

        img1.categories = [cat1, cat2]
        img2.categories = [cat1]

        def search(searched):
            response = self.assertPOST200(Image.get_lv_absolute_url(),
                                          data={'hfilter': hf.id,
                                                '_search': 1,
                                                cell_m2m.key: searched,
                                               }
                                         )
            return self._get_lv_content(response)

        content = search(cat1.name[:5])
        self.assertIn(img1.name,    content)
        self.assertIn(img2.name,    content)
        self.assertNotIn(img3.name, content)

    def test_search_relations01(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        create_contact = partial(Contact.objects.create, user=user)
        spike = create_contact(first_name='Spike', last_name='Spiegel')
        faye  = create_contact(first_name='Faye',  last_name='Spiegel')
        jet   = create_contact(first_name='Jet',   last_name='Black')

        rtype = RelationType.create(('test-subject_piloted', 'is piloted by'),
                                    ('test-object_piloted',  'pilots'),
                                   )[0]
        create_rel = partial(Relation.objects.create, user=user, type=rtype)
        create_rel(subject_entity=swordfish, object_entity=spike)
        create_rel(subject_entity=redtail,   object_entity=faye)
        create_rel(subject_entity=bebop,     object_entity=jet)

        hf = self._build_hf(EntityCellRelation(rtype=rtype))

        url = self.url
        data = {'hfilter': hf.id, '_search': 1, 'name': '', 'relation-%s' % rtype.pk: 'Spiege'}
        response = self.assertPOST200(url, data=data)
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertIn(redtail.name,    content)
        self.assertNotIn(dragons.name, content)

        data['regular_field-name'] = 'Swo'
        content = self._get_lv_content(self.assertPOST200(url, data=data))
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

    def test_search_relations02(self):
        "2 searches at the same time"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')

        create_contact = partial(Contact.objects.create, user=user)
        spike = create_contact(first_name='Spike', last_name='Spiegel')
        faye  = create_contact(first_name='Faye',  last_name='Spiegel')
        jet   = create_contact(first_name='Jet',   last_name='Black')

        create_rtype = RelationType.create
        rtype1 = create_rtype(('test-subject_piloted', 'is piloted by'),
                              ('test-object_piloted',  'pilots'),
                             )[0]
        rtype2 = create_rtype(('test-subject_repaired', 'is repaired by'),
                              ('test-object_repaired',  'repairs'),
                             )[0]

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=swordfish, object_entity=spike, type=rtype1)
        create_rel(subject_entity=redtail,   object_entity=faye,  type=rtype1)
        create_rel(subject_entity=bebop,     object_entity=jet,   type=rtype1)

        create_rel(subject_entity=swordfish, object_entity=jet, type=rtype2)
        create_rel(subject_entity=bebop,     object_entity=jet, type=rtype2)

        hf = self._build_hf(EntityCellRelation(rtype=rtype1),
                            EntityCellRelation(rtype=rtype2),
                           )

        response = self.assertPOST200(self.url,
                                      data={'hfilter': hf.id, '_search': 1,
                                            'relation-%s' % rtype1.pk: 'Jet',
                                            'relation-%s' % rtype2.pk: 'Jet',
                                           }
                                     )
        content = self._get_lv_content(response)
        self.assertIn(bebop.name, content)
        self.assertNotIn(swordfish.name, content)
        self.assertNotIn(redtail.name,   content)

    def test_search_customfield01(self):
        "INT"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        cfield = CustomField.objects.create(name='size (m)',
                                            content_type=self.ctype,
                                            field_type=CustomField.INT,
                                           )
        klass = cfield.get_value_class()

        def set_cfvalue(entity, value):
            klass(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(bebop,     42)
        set_cfvalue(swordfish, 12)
        set_cfvalue(redtail,   4)

        hf = self._build_hf(EntityCellCustomField(cfield))
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search': 1,
                                                      'regular_field-name': '',
                                                      'custom_field-%s' % cfield.pk: '4',
                                                     }
                                     )
        content = self._get_lv_content(response)
        self.assertIn(bebop.name,        content)
        self.assertNotIn(swordfish.name, content)
        self.assertIn(redtail.name,      content)
        self.assertNotIn(dragons.name,   content)

    def test_search_customfield02(self):
        "INT & STR"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        create_cfield = partial(CustomField.objects.create, content_type=self.ctype)
        cfield1 = create_cfield(name='size (m)',   field_type=CustomField.INT)
        cfield2 = create_cfield(name='color code', field_type=CustomField.STR)

        def set_cfvalue(cfield, entity, value):
            cfield.get_value_class()(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(cfield1, bebop,     42)
        set_cfvalue(cfield1, swordfish, 12)
        set_cfvalue(cfield1, redtail,   4)

        set_cfvalue(cfield2, swordfish, '#ff0000')
        set_cfvalue(cfield2, redtail,   '#050508')

        hf = self._build_hf(EntityCellCustomField(cfield1), EntityCellCustomField(cfield2))

        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search': 1,
                                                      'regular_field-name': '',
                                                      'custom_field-%s' % cfield1.pk: '4',
                                                      'custom_field-%s' % cfield2.pk: '#05',
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertIn(redtail,      orgas_set)
        self.assertNotIn(dragons,   orgas_set)

    def test_search_customfield03(self):
        "INT & INT"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        create_cfield = partial(CustomField.objects.create, content_type=self.ctype,
                                field_type=CustomField.INT,
                               )
        cfield1 = create_cfield(name='size (m)')
        cfield2 = create_cfield(name='weight')

        def set_cfvalue(cfield, entity, value):
            cfield.get_value_class()(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(cfield1, bebop,     42)
        set_cfvalue(cfield1, swordfish, 12)
        set_cfvalue(cfield1, redtail,   4)

        set_cfvalue(cfield2, swordfish, 1000)
        set_cfvalue(cfield2, redtail,   2000)

        hf = self._build_hf(EntityCellCustomField(cfield1),
                            EntityCellCustomField(cfield2),
                           )
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search': 1,
                                                      'regular_field-name': '',
                                                      'custom_field-%s' % cfield1.pk: '4',
                                                      'custom_field-%s' % cfield2.pk: '2000',
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertIn(redtail,      orgas_set)
        self.assertNotIn(dragons,   orgas_set)

    def test_search_customfield04(self):
        "ENUM"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        cfield = CustomField.objects.create(name='Type',
                                            content_type=self.ctype,
                                            field_type=CustomField.ENUM,
                                           )

        create_evalue = CustomFieldEnumValue.objects.create
        type1 = create_evalue(custom_field=cfield, value='Light')
        type2 = create_evalue(custom_field=cfield, value='Heavy')

        klass = cfield.get_value_class()
        def set_cfvalue(entity, value):
            klass(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(bebop,     type2.id)
        set_cfvalue(swordfish, type1.id)
        set_cfvalue(redtail,   type1.id)

        hf = self._build_hf(EntityCellCustomField(cfield))
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search': 1,
                                                      'regular_field-name': '',
                                                      'custom_field-%s' % cfield.pk: type1.id,
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,   orgas_set)
        self.assertIn(swordfish,  orgas_set)
        self.assertIn(redtail,    orgas_set)
        self.assertNotIn(dragons, orgas_set)

        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search': 1,
                                                      'name': '',
                                                      'custom_field-%s' % cfield.pk: 'NULL',
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertNotIn(redtail,   orgas_set)
        self.assertIn(dragons,      orgas_set)

    def test_search_customfield05(self):
        "MULTI_ENUM"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop    = create_orga(name='Bebop')
        dragons  = create_orga(name='Red Dragons')
        eva01    = create_orga(name='Eva01')
        valkyrie = create_orga(name='Valkyrie')

        cfield = CustomField.objects.create(name='Capabilities',
                                            content_type=self.ctype,
                                            field_type=CustomField.MULTI_ENUM,
                                           )

        create_evalue = CustomFieldEnumValue.objects.create
        can_walk = create_evalue(custom_field=cfield, value='Walk')
        can_fly  = create_evalue(custom_field=cfield, value='Fly')

        klass = cfield.get_value_class()
        def set_cfvalue(entity, value):
            klass(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(bebop,     [can_fly.id])
        set_cfvalue(eva01,     [can_walk.id])
        set_cfvalue(valkyrie,  [can_fly.id, can_walk.id])

        hf = self._build_hf(EntityCellCustomField(cfield))
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search': 1,
                                                      'regular_field-name':    '',
                                                      'custom_field-%s' % cfield.pk: can_walk.id,
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,   orgas_set)
        self.assertNotIn(dragons, orgas_set)
        self.assertIn(eva01,      orgas_set)
        self.assertIn(valkyrie,   orgas_set)

        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search': 1,
                                                      'regular_field-name': '',
                                                      'custom_field-%s' % cfield.pk: 'NULL',
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,    orgas_set)
        self.assertNotIn(eva01,    orgas_set)
        self.assertNotIn(valkyrie, orgas_set)
        self.assertIn(dragons,     orgas_set)

    def test_search_customfield06(self):
        "2 x ENUM"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        create_cfield = partial(CustomField.objects.create,
                                content_type=self.ctype, field_type=CustomField.ENUM,
                               )
        cfield_type  = create_cfield(name='Type')
        cfield_color = create_cfield(name='Color')

        create_evalue = CustomFieldEnumValue.objects.create
        type1 = create_evalue(custom_field=cfield_type, value='Light')
        type2 = create_evalue(custom_field=cfield_type, value='Heavy')

        color1 = create_evalue(custom_field=cfield_color, value='Red')
        color2 = create_evalue(custom_field=cfield_color, value='Grey')

        def set_cfvalue(cfield, entity, value):
            cfield.get_value_class()(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(cfield_type,  bebop,     type2.id)
        set_cfvalue(cfield_color, bebop,     color2.id)

        set_cfvalue(cfield_type,  swordfish, type1.id)
        set_cfvalue(cfield_color, swordfish, color1.id)

        set_cfvalue(cfield_type,  redtail,   type1.id)
        set_cfvalue(cfield_color, redtail,   color2.id)

        hf = self._build_hf(EntityCellCustomField(cfield_type),
                            EntityCellCustomField(cfield_color),
                           )
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search':       1,
                                                      'regular_field-name': '',
                                                      'custom_field-%s' % cfield_type.pk:  type1.id,
                                                      'custom_field-%s' % cfield_color.pk: color2.id,
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertIn(redtail,      orgas_set)
        self.assertNotIn(dragons,   orgas_set)

        set_cfvalue(cfield_color, dragons, color1.id)  # Type is NULL

        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search':       1,
                                                      'regular_field-name': '',
                                                      'custom_field-%s' % cfield_type.pk:  'NULL',
                                                      'custom_field-%s' % cfield_color.pk: color1.id,
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertNotIn(redtail,   orgas_set)
        self.assertIn(dragons,      orgas_set)

    def test_search_customfield07(self):
        "2 x MULTI_ENUM"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        eva02     = create_orga(name='Eva02')
        valkyrie  = create_orga(name='Valkyrie')

        create_cfield = partial(CustomField.objects.create,
                                content_type=self.ctype,
                                field_type=CustomField.MULTI_ENUM,
                               )
        cfield_cap   = create_cfield(name='Capabilities')
        cfield_color = create_cfield(name='Color')

        create_evalue = CustomFieldEnumValue.objects.create
        can_fly  = create_evalue(custom_field=cfield_cap, value='Walk')
        can_walk = create_evalue(custom_field=cfield_cap, value='Fly')

        red    = create_evalue(custom_field=cfield_color, value='Red')
        grey   = create_evalue(custom_field=cfield_color, value='Grey')
        orange = create_evalue(custom_field=cfield_color, value='Orange')

        def set_cfvalue(cfield, entity, value):
            cfield.get_value_class()(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(cfield_cap,   bebop,     [can_fly.id])
        set_cfvalue(cfield_color, bebop,     [grey.id])

        set_cfvalue(cfield_cap,   swordfish, [can_fly.id])
        set_cfvalue(cfield_color, swordfish, [red.id])

        set_cfvalue(cfield_cap,   eva02,     [can_walk.id])
        set_cfvalue(cfield_color, eva02,     [red.id, orange.id])

        set_cfvalue(cfield_cap,   valkyrie,  [can_fly.id, can_walk.id])

        hf = self._build_hf(EntityCellCustomField(cfield_cap),
                            EntityCellCustomField(cfield_color),
                           )
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search':       1,
                                                      'regular_field-name': '',
                                                      'custom_field-%s' % cfield_cap.pk:   can_walk.id,
                                                      'custom_field-%s' % cfield_color.pk: red.id,
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertIn(eva02,        orgas_set)
        self.assertNotIn(valkyrie,  orgas_set)

        response = self.assertPOST200(self.url, data={'_search':       1,
                                                      'regular_field-name': '',
                                                      'custom_field-%s' % cfield_cap.pk:   can_walk.id,
                                                      'custom_field-%s' % cfield_color.pk: 'NULL',
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertNotIn(eva02,     orgas_set)
        self.assertIn(valkyrie,     orgas_set)

    def test_search_customfield08(self):
        "DATETIME"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        cfield = CustomField.objects.create(name='First flight',
                                            content_type=self.ctype,
                                            field_type=CustomField.DATETIME,
                                           )
        create_cf_value = partial(cfield.get_value_class().objects.create, custom_field=cfield)
        create_dt = partial(self.create_datetime, utc=True)
        create_cf_value(entity=bebop,     value=create_dt(year=2075, month=3, day=26))
        create_cf_value(entity=swordfish, value=create_dt(year=2074, month=6, day=5))
        create_cf_value(entity=redtail,   value=create_dt(year=2076, month=7, day=25))

        hf = self._build_hf(EntityCellCustomField(cfield))

        def post(dates):
            response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                          '_search': 1,
                                                          'custom_field-%s' % cfield.pk: dates,
                                                         }
                                         )
            return self._get_lv_content(response)

        content = post(['2075-1-1'])
        self.assertIn(bebop.name,        content)
        self.assertNotIn(swordfish.name, content)
        self.assertIn(redtail.name,      content)
        self.assertNotIn(dragons.name,   content)

        content = post(['', '1-1-2075'])
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        content = post(['1-1-2074', '31-12-2074'])
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        content = post(['5-6-2074', '5-6-2074'])
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

    def test_search_customfield09(self):
        "2 x DATETIME"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop      = create_orga(name='Bebop')
        swordfish  = create_orga(name='Swordfish')
        redtail    = create_orga(name='Redtail')
        hammerhead = create_orga(name='HammerHead')
        dragons    = create_orga(name='Red Dragons')

        create_cfield = partial(CustomField.objects.create, content_type=self.ctype,
                                field_type=CustomField.DATETIME,
                               )
        cfield_flight = create_cfield(name='First flight')
        cfield_blood  = create_cfield(name='First blood')

        create_cf_value = partial(cfield_flight.get_value_class().objects.create)
        create_dt = partial(self.create_datetime, utc=True)
        create_cf_value(entity=bebop,      custom_field=cfield_flight, value=create_dt(year=2075, month=3, day=26))
        create_cf_value(entity=swordfish,  custom_field=cfield_flight, value=create_dt(year=2074, month=6, day=5))
        create_cf_value(entity=redtail,    custom_field=cfield_flight, value=create_dt(year=2076, month=7, day=25))
        create_cf_value(entity=hammerhead, custom_field=cfield_flight, value=create_dt(year=2074, month=7, day=6))

        create_cf_value(entity=swordfish,  custom_field=cfield_blood, value=create_dt(year=2074, month=6, day=8))
        create_cf_value(entity=hammerhead, custom_field=cfield_blood, value=create_dt(year=2075, month=7, day=6))

        hf = self._build_hf(EntityCellCustomField(cfield_flight),
                            EntityCellCustomField(cfield_blood),
                           )
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search': 1,
                                                      'custom_field-%s' % cfield_flight.pk: ['1-1-2074', '31-12-2074'],
                                                      'custom_field-%s' % cfield_blood.pk:  ['',         '1-1-2075'],
                                                     })
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,      content)
        self.assertIn(swordfish.name,     content)
        self.assertNotIn(redtail.name,    content)
        self.assertNotIn(hammerhead.name, content)
        self.assertNotIn(dragons.name,    content)

    def test_search_functionfield01(self):
        "_PrettyPropertiesField"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        eva01     = create_orga(name='Eva01')
        eva02     = create_orga(name='Eva02')

        create_ptype = CremePropertyType.create
        is_red  = create_ptype(str_pk='test-prop_red',  text='is red')
        is_fast = create_ptype(str_pk='test-prop_fast', text='is fast')

        create_prop = CremeProperty.objects.create
        create_prop(type=is_red, creme_entity=swordfish)
        create_prop(type=is_red, creme_entity=eva02)

        create_prop(type=is_fast, creme_entity=swordfish)
        create_prop(type=is_fast, creme_entity=bebop)

        ff_name = 'get_pretty_properties'
        hf = self._build_hf(EntityCellFunctionField.build(Organisation, ff_name))

        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search': 1,
                                                      'function_field-%s' % ff_name: 'red',
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertIn(swordfish, orgas_set)
        self.assertIn(eva02,     orgas_set)
        self.assertNotIn(bebop,  orgas_set)
        self.assertNotIn(eva01,  orgas_set)

    def test_search_functionfield02(self):
        "Can not search on this FunctionField"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')

        func_field = Organisation.function_fields.get('tests-get_fake_todos')
        self._build_hf(EntityCellFunctionField(func_field))

        response = self.assertPOST200(self.url, data={'_search': 1,
                                                      'regular_field-name': '',
                                                      'function_field-%s' % func_field.name: bebop.name,
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertIn(bebop,     orgas_set)
        self.assertIn(swordfish, orgas_set)

    def _build_orgas(self):
        count = Organisation.objects.count()
        expected_count = 13  # 13 = 10 (our page size) + 3
        self.assertLessEqual(count, expected_count)

        create_orga = partial(Organisation.objects.create, user=self.user)
        for i in xrange(expected_count - count):
            create_orga(name='Mafia #%02i' % i)

        organisations = list(Organisation.objects.all())
        self.assertEqual(expected_count, len(organisations))

        return organisations

    @override_settings(FAST_QUERY_MODE_THRESHOLD=100000, PAGE_SIZES=[10, 25, 200], DEFAULT_PAGE_SIZE_IDX=0)
    def test_pagination_slow01(self):
        "Paginator with only OFFSET (small number of lines)"
        self.login()
        organisations = self._build_orgas()
        hf = self._build_hf()

        def post(page, rows=10):
            return self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      'page':    page,
                                                      'rows':    rows,
                                                     }
                                     )

        # Page 1 --------------------
        response = post(page=1)
        with self.assertNoException():
            entities_page = response.context['entities']

        self.assertEqual(10, len(entities_page))
        self.assertTrue(entities_page.has_next())
        self.assertFalse(entities_page.has_previous())
        self.assertEqual(2, entities_page.next_page_number())

        paginator = entities_page.paginator
        self.assertEqual(10, paginator.per_page)
        self.assertEqual(13, paginator.count)
        self.assertEqual(2,  paginator.num_pages)

        entities = list(entities_page.object_list)
        idx1 = self.assertIndex(organisations[0], entities)
        self.assertEqual(0, idx1)
        idx10 = self.assertIndex(organisations[9], entities)
        self.assertEqual(9, idx10)

        # Page 2 --------------------
        response = post(page=2)
        entities_page = response.context['entities']

        self.assertEqual(3, len(entities_page))

        entities = list(entities_page.object_list)
        idx11 = self.assertIndex(organisations[10], entities)
        self.assertEqual(0, idx11)

        # Change 'rows' parameter -------------
        rows = 25
        response = post(page=1, rows=rows)
        self.assertEqual(rows, response.context['entities'].paginator.per_page)

        # Check invalid page size
        response = post(page=1, rows=1000)
        self.assertEqual(10, response.context['entities'].paginator.per_page)

    @override_settings(FAST_QUERY_MODE_THRESHOLD=100000, PAGE_SIZES=[10], DEFAULT_PAGE_SIZE_IDX=0)
    def test_pagination_slow02(self):
        "Page is saved"
        self.login()
        organisations = self._build_orgas()
        hf = self._build_hf()

        def post(page=None):
            data = {'hfilter': hf.id,
                    'rows':    10,
                   }

            if page:
                data['page'] = page

            return self.assertPOST200(self.url, data=data)

        post(page=1)

        # Go to page 2...
        response = post(page=2)
        entities_page = response.context['entities']
        self.assertEqual(2, entities_page.number)
        self.assertIndex(organisations[10], list(entities_page.object_list))

        # ... which should be kept in session
        response = post()
        entities_page = response.context['entities']
        self.assertEqual(2, entities_page.number)
        self.assertIndex(organisations[10], list(entities_page.object_list))

    @override_settings(FAST_QUERY_MODE_THRESHOLD=5, PAGE_SIZES=[10, 25], DEFAULT_PAGE_SIZE_IDX=0)
    def test_pagination_fast01(self):
        "Paginator with 'keyset' (big number of lines)"
        self.login()
        organisations = self._build_orgas()
        hf = self._build_hf()

        def post(page_info=None):
            return self.assertPOST200(self.url,
                                      data={'hfilter': hf.id,
                                            'page': json_dump(page_info) if page_info else '',
                                           }
                                     )

        # Page 1 --------------------
        response = post()
        with self.assertNoException():
            entities_page1 = response.context['entities']

        self.assertEqual(10, len(entities_page1))
        self.assertTrue(entities_page1.has_next())
        self.assertFalse(entities_page1.has_previous())
        self.assertFalse(hasattr(entities_page1, 'next_page_number'))
        self.assertTrue(hasattr(entities_page1, 'next_page_info'))

        paginator = entities_page1.paginator
        self.assertEqual(10, paginator.per_page)
        self.assertEqual(13, paginator.count)
        self.assertFalse(hasattr(paginator, 'num_pages'))

        entities = list(entities_page1.object_list)
        idx1 = self.assertIndex(organisations[0], entities)
        self.assertEqual(0, idx1)

        idx10 = self.assertIndex(organisations[9], entities)
        self.assertEqual(9, idx10)

        # Page 2 --------------------
        response = post(entities_page1.next_page_info())
        entities_page2 = response.context['entities']

        self.assertEqual(3, len(entities_page2))

        entities = list(entities_page2.object_list)
        idx11 = self.assertIndex(organisations[10], entities)
        self.assertEqual(0, idx11)

    @override_settings(FAST_QUERY_MODE_THRESHOLD=5, PAGE_SIZES=[10, 50], DEFAULT_PAGE_SIZE_IDX=0)
    def test_pagination_fast02(self):
        "ContentType = Contact"
        user = self.login()
        rows = 10
        expected_count = rows + 3

        count = Contact.objects.count()
        self.assertLessEqual(count, expected_count)

        create_contact = partial(Contact.objects.create, user=user)
        for i in xrange(expected_count - count):
            create_contact(first_name='Gally', last_name='Tuned%02i' % i)

        contacts = list(Contact.objects.all())
        self.assertEqual(expected_count, len(contacts))

        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=Contact,
                                 cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                                             (EntityCellRegularField, {'name': 'first_name'}),
                                            ],
                                )

        def post(page_info=None):
            return self.assertPOST200(Contact.get_lv_absolute_url(),
                                      data={'hfilter': hf.id,
                                            'page': json_dump(page_info) if page_info else '',
                                            'rows': rows,
                                           }
                                     )

        # Page 1 --------------------
        response = post()
        with self.assertNoException():
            entities_page1 = response.context['entities']

        self.assertEqual(rows, len(entities_page1))
        self.assertTrue(entities_page1.has_next())
        self.assertFalse(entities_page1.has_previous())
        self.assertFalse(hasattr(entities_page1, 'next_page_number'))

        paginator = entities_page1.paginator
        self.assertEqual(rows, paginator.per_page)
        self.assertEqual(expected_count, paginator.count)
        self.assertFalse(hasattr(paginator, 'num_pages'))

        entities = list(entities_page1.object_list)
        idx1 = self.assertIndex(contacts[0], entities)
        self.assertEqual(0, idx1)

        idx10 = self.assertIndex(contacts[9], entities)
        self.assertEqual(9, idx10)

        # Page 2 --------------------
        response = post(entities_page1.next_page_info())
        entities_page2 = response.context['entities']

        self.assertEqual(3, len(entities_page2))

        entities = list(entities_page2.object_list)
        idx11 = self.assertIndex(contacts[10], entities)
        self.assertEqual(0, idx11)

    @override_settings(FAST_QUERY_MODE_THRESHOLD=5, PAGE_SIZES=[10, 25], DEFAULT_PAGE_SIZE_IDX=1)
    def test_pagination_fast03(self):
        "Set an ORDER"
        user = self.login()
        rows = 10
        expected_count = rows + 3

        count = Contact.objects.count()
        self.assertLessEqual(count, expected_count)

        ids = range(expected_count - count)
        shuffle(ids)

        create_contact = partial(Contact.objects.create, user=user)
        for i, id_ in enumerate(ids):
            # NB: we want the ordering by 'first_name' to be different from the 'last_name' one
            create_contact(first_name='Gally%02i' % id_, last_name='Tuned%02i' % i)

        ordering_fname = 'first_name'
        contacts = list(Contact.objects.order_by(ordering_fname))
        self.assertEqual(expected_count, len(contacts))

        build_cell = partial(EntityCellRegularField.build, model=Contact)
        cell2 = build_cell(name=ordering_fname)
        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=Contact,
                                 cells_desc=[build_cell(name='last_name'), cell2],
                                 )

        def post(page_info=None):
            return self.assertPOST200(Contact.get_lv_absolute_url(),
                                      data={'hfilter': hf.id,
                                            'sort_field': cell2.key,
                                            'sort_order': '',  # TODO: '-'
                                            'page': json_dump(page_info) if page_info else '',
                                            'rows': rows,
                                           }
                                      )

        # Page 1 --------------------
        response = post()
        entities_page1 = response.context['entities']
        entities = list(entities_page1.object_list)
        idx1 = self.assertIndex(contacts[0], entities)
        self.assertEqual(0, idx1)

        idx10 = self.assertIndex(contacts[9], entities)
        self.assertEqual(9, idx10)

        # Page 2 --------------------
        response = post(entities_page1.next_page_info())
        entities_page2 = response.context['entities']

        self.assertEqual(3, len(entities_page2))

        entities = list(entities_page2.object_list)
        idx11 = self.assertIndex(contacts[10], entities)
        self.assertEqual(0, idx11)

    @override_settings(FAST_QUERY_MODE_THRESHOLD=5, PAGE_SIZES=[10], DEFAULT_PAGE_SIZE_IDX=0)
    def test_pagination_fast04(self):
        "Field key duplicates => use OFFSET too"
        user = self.login()
        rows = 10
        expected_count = rows + 3

        count = Contact.objects.count()
        self.assertLessEqual(count, expected_count)

        create_contact = partial(Contact.objects.create, user=user)
        for i in xrange(expected_count - count):
            # NB: same last_name
            create_contact(first_name='Gally', last_name='Tuned', phone='11 22 33 #%02i' % i)

        contacts = list(Contact.objects.order_by('last_name', 'first_name', 'cremeentity_ptr_id'))
        self.assertEqual(expected_count, len(contacts))

        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=Contact,
                                 cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                                             (EntityCellRegularField, {'name': 'first_name'}),
                                            ],
                                )

        def post(page_info=None):
            return self.assertPOST200(Contact.get_lv_absolute_url(),
                                      data={'hfilter': hf.id,
                                            'page': json_dump(page_info) if page_info else '',
                                            'rows': rows,
                                           }
                                     )

        # Page 1 --------------------
        response = post()
        entities_page1 = response.context['entities']
        idx10 = self.assertIndex(contacts[9], list(entities_page1.object_list))
        self.assertEqual(9, idx10)

        # Page 2 --------------------
        response = post(entities_page1.next_page_info())
        entities_page2 = response.context['entities']

        self.assertEqual(3, len(entities_page2))

        idx11 = self.assertIndex(contacts[10], list(entities_page2.object_list))
        self.assertEqual(0, idx11)

    @override_settings(FAST_QUERY_MODE_THRESHOLD=5, PAGE_SIZES=[5, 10])
    def test_pagination_fast05(self):
        "Errors => page 1"
        user = self.login()
        rows = 5
        expected_count = rows + 3

        count = Contact.objects.count()
        self.assertLessEqual(count, expected_count)

        create_contact = partial(Contact.objects.create, user=user)
        for i in xrange(expected_count - count):
            create_contact(first_name='Gally', last_name='Tuned#%02i' % i)

        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=Contact,
                                 cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                                             (EntityCellRegularField, {'name': 'first_name'}),
                                            ],
                                )

        def post(page_info=''):
            response = self.assertPOST200(Contact.get_lv_absolute_url(),
                                          data={'hfilter': hf.id,
                                                'page': page_info,
                                                'rows': rows,
                                               }
                                         )
            return response.context['entities']

        page1 = post()
        page2_info = page1.next_page_info()

        # Invalid Page => page 1
        page1_info = dict(page2_info)
        del page1_info['type']

        page = post(json_dump(page1_info))
        self.assertFalse(page.has_previous())

        # Invalid JSON => page 1
        invalid_json = json_dump(page2_info)[:-1]
        page = post(invalid_json)
        self.assertFalse(page.has_previous())

        # FirstPage => page 1
        page1a_info = page1.paginator.page(page2_info).previous_page_info()
        page = post(json_dump(page1a_info))
        self.assertFalse(page.has_previous())

    @override_settings(FAST_QUERY_MODE_THRESHOLD=5, PAGE_SIZES=[5, 10])
    def test_pagination_fast06(self):
        "LastPage => last page"
        user = self.login()
        rows = 5
        expected_count = 2 * rows + 3

        count = Contact.objects.count()
        self.assertLessEqual(count, expected_count)

        create_contact = partial(Contact.objects.create, user=user)
        for i in xrange(expected_count - count):
            create_contact(first_name='Gally', last_name='Tuned#%02i' % i)

        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=Contact,
                                 cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                                             (EntityCellRegularField, {'name': 'first_name'}),
                                            ],
                                )

        def post(page_info=''):
            response = self.assertPOST200(Contact.get_lv_absolute_url(),
                                          data={'hfilter': hf.id,
                                                'page': page_info,
                                                'rows': rows,
                                               }
                                         )
            return response.context['entities']

        page1 = post()
        paginator = page1.paginator
        self.assertEqual(rows, paginator.per_page)

        page2 = paginator.page(page1.next_page_info())
        page3_info = page2.next_page_info()

        # We delete the content of the 2nd page
        for c in Contact.objects.reverse()[:4]:
            c.delete()

        last_page = post(json_dump(page3_info))
        self.assertTrue(last_page.has_previous())

    @override_settings(FAST_QUERY_MODE_THRESHOLD=5, PAGE_SIZES=[10])
    def test_pagination_fast07(self):
        "Page is saved"
        self.login()
        organisations = self._build_orgas()
        hf = self._build_hf()
        url = Organisation.get_lv_absolute_url()

        def post(page_info=''):
            data = {'hfilter': hf.id,
                    'page': page_info,
                    'rows': 10,
                   }

            response = self.assertPOST200(url, data=data)
            return response.context['entities']

        page1 = post()

        # Go to page 2...
        page2 = post(json_dump(page1.next_page_info()))
        self.assertIndex(organisations[10], page2.object_list)

        # ... which should be kept in session
        page2a = post()
        self.assertIndex(organisations[10], page2a.object_list)

    @override_settings(FAST_QUERY_MODE_THRESHOLD=14, PAGE_SIZES=[10])
    def test_pagination_fast08(self):
        "Change paginator class slow => fast (so saved page info are not compatible)"
        user =  self.login()
        self._build_orgas()
        hf = self._build_hf()
        url = Organisation.get_lv_absolute_url()

        def post():
            response = self.assertPOST200(url,
                                          data={'hfilter': hf.id,
                                                'rows': 10,
                                               }
                                         )
            return response.context['entities']

        page1_slow = post()
        self.assertTrue(hasattr(page1_slow, 'number'))  # Means slow mode

        Organisation.objects.create(user=user, name='Zalem')  # We exceed the threshold
        page1_fast = post()
        self.assertTrue(hasattr(page1_fast, 'next_page_info'))  # Means fast mode
