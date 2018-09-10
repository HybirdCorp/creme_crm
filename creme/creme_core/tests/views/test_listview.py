# -*- coding: utf-8 -*-

try:
    from datetime import date, timedelta
    from xml.etree.ElementTree import tostring as html_tostring
    from functools import partial
    from json import dumps as json_dump
    from random import shuffle
    import re

    import html5lib

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.db.models import Q
    from django.test.utils import override_settings
    from django.urls import reverse
    from django.utils.http import urlquote
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _

    from .base import ViewsTestCase
    from .. import fake_constants
    from ..fake_models import (FakeContact, FakeOrganisation, FakeAddress, FakeCivility, FakeSector,
            FakeImage, FakeImageCategory, FakeActivity, FakeActivityType,
            FakeEmailCampaign, FakeMailingList,
            FakeInvoice, FakeInvoiceLine,
            FakeDocument, FakeFolder, FakeFolderCategory)

    from creme.creme_core.core.entity_cell import (EntityCellRegularField,
            EntityCellCustomField, EntityCellFunctionField, EntityCellRelation)
    from creme.creme_core.core.function_field import function_field_registry
    from creme.creme_core.gui.listview import ListViewState
    from creme.creme_core.models import (EntityFilter, EntityFilterCondition,
            HeaderFilter, RelationType, Relation, FieldsConfig,
            CremePropertyType, CremeProperty, CustomField, CustomFieldEnumValue)
    from creme.creme_core.models.entity_filter import EntityFilterList
    from creme.creme_core.models.header_filter import HeaderFilterList
    from creme.creme_core.utils.profiling import CaptureQueriesContext
    from creme.creme_core.utils.queries import QSerializer
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class ListViewTestCase(ViewsTestCase):
    @classmethod
    def setUpClass(cls):
        # super(ListViewTestCase, cls).setUpClass()
        super().setUpClass()

        cls.url = FakeOrganisation.get_lv_absolute_url()
        cls.ctype = ContentType.objects.get_for_model(FakeOrganisation)

        cls._civ_backup = list(FakeCivility.objects.all())
        FakeCivility.objects.all().delete()

    @classmethod
    def tearDownClass(cls):
        # super(ListViewTestCase, cls).tearDownClass()
        super().tearDownClass()
        FakeCivility.objects.all().delete()
        FakeCivility.objects.bulk_create(cls._civ_backup)

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
                        'Not COUNT query found in {}'.format(joined_sql)
                       )
        self.assertTrue(entities_q_found,
                        'Not query (which retrieve entities) found in {}'.format(joined_sql)
                       )

    def _get_lv_node(self, response):
        page_tree = html5lib.parse(response.content, namespaceHTMLElements=False)

        table_node = page_tree.find(".//table[@id='list']")
        self.assertIsNotNone(table_node, 'The table id="list" is not found.')

        return table_node

    def _get_lv_header_titles(self, lv_node):
        thead_node = lv_node.find('.//thead')
        self.assertIsNotNone(thead_node)

        tr_node = thead_node.find(".//tr[@class='columns_top']")
        self.assertIsNotNone(tr_node)

        return [
            span_node.text
                for span_node in tr_node.findall(".//th/button/div/span[@class='lv-sort-toggle-title']")
        ]

    def _get_lv_header_widget_nodes(self, lv_node, cell_key, input_type='input', count=1):
        thead_node = lv_node.find('.//thead')
        self.assertIsNotNone(thead_node)

        tr_node = thead_node.find(".//tr[@id='list_thead_search']")
        self.assertIsNotNone(tr_node)

        widget_nodes = tr_node.findall(".//{}[@name='{}']".format(input_type, cell_key))
        self.assertEqual(count, len(widget_nodes))

        return widget_nodes

    def _assert_no_lv_header_widget_node(self, lv_node, cell_key):
        thead_node = lv_node.find('.//thead')
        self.assertIsNotNone(thead_node)

        tr_node = thead_node.find(".//tr[@id='list_thead_search']")
        self.assertIsNotNone(tr_node)

        input_node = tr_node.find(".//*[@name='{}']".format(cell_key))
        self.assertIsNone(input_node)

    def _get_lv_inputs_content(self, lv_node):
        thead_node = lv_node.find(".//thead")
        self.assertIsNotNone(thead_node)

        th_node = thead_node.find(".//tr/th")
        self.assertIsNotNone(th_node)

        return [
            (input_node.attrib.get('name'), input_node.attrib.get('value'))
                for input_node in th_node.findall('input')
        ]

    def _get_lv_content(self, lv_node):
        tbody_node = lv_node.find('.//tbody')
        self.assertIsNotNone(tbody_node)

        content = []

        for tr_node in tbody_node.findall('tr'):
            for td_node in tr_node.findall('td'):
                class_attr = td_node.attrib.get('class')

                if class_attr:
                    classes = class_attr.split()

                    if 'lv-cell-content' in classes:
                        div_node = td_node.find('.//div')

                        if div_node is not None:
                            content.append(list(div_node) or div_node.text.strip())

        return content

    def _get_entities_set(self, response):
        with self.assertNoException():
            entities_page = response.context['entities']

        return set(entities_page.object_list)

    def _get_options_for_select_node(self, select_node):
        return {
            (option_node.attrib.get('value'), option_node.text)
                for option_node in select_node.findall('option')
        }

    @staticmethod
    def _get_sql(response):
        page = response.context['entities']
        return page.paginator.object_list.query.get_compiler('default').as_sql()[0]

    def _build_hf(self, *args):
        cells = [EntityCellRegularField.build(model=FakeOrganisation, name='name')]
        cells.extend(args)
        return HeaderFilter.create(pk='test-hf_orga', name='Orga view',
                                   model=FakeOrganisation, cells_desc=cells,
                                  )

    def test_content01(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')

        create_contact = partial(FakeContact.objects.create, user=user)
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

        hf = self._build_hf(EntityCellRelation(model=FakeOrganisation, rtype=rtype),
                            EntityCellFunctionField.build(FakeOrganisation, 'get_pretty_properties'),
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

        lv_node = self._get_lv_node(response)
        content = self._get_lv_content(lv_node)
        bebop_idx = self.assertIndex(bebop.name, content)
        swordfish_idx = self.assertIndex(swordfish.name, content)
        self.assertGreater(swordfish_idx, bebop_idx)  # Order

        titles = self._get_lv_header_titles(lv_node)

        self.assertIn(rtype.predicate, titles)
        rtype_cell_content = content[5]
        self.assertIsInstance(rtype_cell_content, list)
        self.assertEqual(1, len(rtype_cell_content))
        self.assertEqual('<a href="/tests/contact/{id}">{value}</a>'.format(id=spike.id, value=spike).encode(),
                         html_tostring(rtype_cell_content[0]).strip()
                        )

        self.assertNotIn(faye.last_name, content)

        ptype_cell_content = content[6]
        self.assertIsInstance(ptype_cell_content, list)
        self.assertEqual(1, len(ptype_cell_content))
        self.assertEqual('<ul><li><a href="{}">{}</a></li></ul>'.format(
                                ptype1.get_absolute_url(), ptype1.text,
                            ).encode(),
                         html_tostring(ptype_cell_content[0]).strip()
                        )
        self.assertNotIn(ptype2.text, content)  # NB: not really useful...

        self.assertIn(cfield.name, titles)
        self.assertIn(str(cfield_value), content)

        self.assertEqual(2, orgas_page.paginator.count)

    def test_content02(self):
        "FieldsConfig"
        user = self.login()

        valid_fname = 'name'
        hidden_fname = 'url_site'

        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        hf = self._build_hf(build_cell(name=valid_fname), build_cell(name=hidden_fname))

        FieldsConfig.create(FakeOrganisation,
                            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
                           )

        bebop = FakeOrganisation.objects.create(user=user, name='Bebop', url_site='sww.bebop.mrs')

        response = self.assertPOST200(self.url, data={'hfilter': hf.id})

        content = self._get_lv_content(self._get_lv_node(response))
        self.assertIn(bebop.name, content)
        self.assertNotIn(bebop.url_site, content, '"url_site" not hidden')

    def test_selection_single(self):
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
        create_contact(first_name='Spike', last_name='Spiegel')
        create_contact(first_name='Faye',  last_name='Valentine')

        def post(selection, is_single):
            response = self.assertPOST200(self.url, data={'selection': selection} if selection is not None else {})
            pattern = r'<input[\s]+value="{}"[\s]+id="o2m"[\s]+type="hidden"[\s]+/>'.format(is_single)
            self.assertIsNotNone(re.search(pattern, response.content.decode()))

        post(None, False)
        post('single', True)
        post('multiple', False)

        self.assertPOST404(self.url, data={'selection': 'unknown'})

    def test_selection_single_GET(self):
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
        create_contact(first_name='Spike', last_name='Spiegel')
        create_contact(first_name='Faye',  last_name='Valentine')

        def get(selection, is_single):
            response = self.assertGET200(self.url, data={'selection': selection} if selection is not None else {})
            pattern = r'<input[\s]+value="{}"[\s]+id="o2m"[\s]+type="hidden"[\s]+/>'.format(is_single)
            self.assertIsNotNone(re.search(pattern, response.content.decode()))

        get(None, False)
        get('single', True)
        get('multiple', False)

        self.assertGET404(self.url, data={'selection': 'unknown'})

    def test_ordering_regularfield(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')

        self._build_hf()

        def post(first, second, sort_order='', sort_field='regular_field-name', **kwargs):
            response = self.assertPOST200(self.url,
                                          data={'sort_field': sort_field,
                                                'sort_order': sort_order,
                                               },
                                          **kwargs
                                         )

            content = self._get_lv_content(self._get_lv_node(response))
            first_idx = self.assertIndex(first.name, content)
            second_idx = self.assertIndex(second.name, content)
            self.assertLess(first_idx, second_idx)

        post(bebop, swordfish)
        post(swordfish, bebop, '-')
        post(bebop, swordfish, '*')  # Invalid value
        post(bebop, swordfish, sort_field='unknown')  # Invalid value

        # ajax POST request
        post(bebop, swordfish, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        post(swordfish, bebop, '-', HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        state = ListViewState.get_state(self.client, url=self.url)
        self.assertIsNotNone(state)
        self.assertEqual('regular_field-name', state.sort_field)
        self.assertEqual('-', state.sort_order)

    def test_ordering_regularfield_GET(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')

        self._build_hf()

        def get(first, second, sort_order='', sort_field='regular_field-name', **kwargs):
            response = self.assertGET200(self.url,
                                         data={'sort_field': sort_field,
                                               'sort_order': sort_order,
                                              },
                                         **kwargs
                                        )
            content = self._get_lv_content(self._get_lv_node(response))
            first_idx = self.assertIndex(first.name, content)
            second_idx = self.assertIndex(second.name, content)
            self.assertLess(first_idx, second_idx)

        get(bebop, swordfish)
        get(swordfish, bebop, '-')
        get(bebop, swordfish, '*')  # Invalid value
        get(bebop, swordfish, sort_field='unknown')  # Invalid value

        state = ListViewState.get_state(self.client, url=self.url)
        self.assertIsNone(state)

        # ajax GET request
        get(bebop, swordfish, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        get(swordfish, bebop, '-', HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        # state is not saved or update by GET requests.
        state = ListViewState.get_state(self.client, url=self.url)
        self.assertIsNone(state)

    def test_ordering_regularfield_transient(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')

        self._build_hf()

        def post(first, second, sort_order='', sort_field='regular_field-name', **kwargs):
            response = self.assertPOST200(self.url,
                                          data={'sort_field': sort_field,
                                                'sort_order': sort_order,
                                                'transient': '1',
                                               },
                                          **kwargs
                                         )
            content = self._get_lv_content(self._get_lv_node(response))
            first_idx = self.assertIndex(first.name, content)
            second_idx = self.assertIndex(second.name, content)
            self.assertLess(first_idx, second_idx)

        post(bebop, swordfish)
        post(swordfish, bebop, '-')
        post(bebop, swordfish, '*')  # Invalid value
        post(bebop, swordfish, sort_field='unknown')  # Invalid value

        state = ListViewState.get_state(self.client, url=self.url)
        self.assertIsNone(state)

        # ajax GET request
        post(bebop, swordfish, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        post(swordfish, bebop, '-', HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        # state is not saved or update by GET requests.
        state = ListViewState.get_state(self.client, url=self.url)
        self.assertIsNone(state)

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
        content = self._get_lv_content(self._get_lv_node(response))
        lines = [(self.assertIndex(str(getattr(e, key)), content), e)
                    for e in entries
                ]
        self.assertListEqual(list(entries),
                             [line[1] for line in sorted(lines, key=lambda e: e[0])]
                            )

    def test_ordering_regularfield_fk(self):
        "Sort by ForeignKey"
        user = self.login()

        create_civ = FakeCivility.objects.create
        mister = create_civ(title='Mister')
        miss   = create_civ(title='Miss')
        self.assertLess(mister.id, miss.id)

        create_contact = partial(FakeContact.objects.create, user=user)
        spike = create_contact(first_name='Spike',  last_name='Spiegel',   civility=mister)
        faye  = create_contact(first_name='Faye',   last_name='Valentine', civility=miss)
        ed    = create_contact(first_name='Edward', last_name='Wong')

        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=FakeContact)

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
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

        url = FakeContact.get_lv_absolute_url()

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
            content = self._get_lv_content(self._get_lv_node(response))
            indices = [self.assertIndex(c.last_name, content)
                        for c in contacts
                      ]
            self.assertEqual(indices, sorted(indices))

            return content

        # NB: it seems that NULL are not ordered in the same way on different DB engines
        content = post('regular_field-civility', False, faye, spike)  # Sorting is done by 'title'
        self.assertCountOccurrences(ed.last_name, content, count=1)

        post('regular_field-civility', True, spike, faye)
        post('regular_field-civility__title', False, faye, spike)
        post('regular_field-civility__title', True, spike, faye)

    def test_ordering_unsortable_fields(self):
        "Un-sortable fields: ManyToMany, FunctionFields"
        user = self.login()

        # Bug on ORM with M2M happens only if there is at least one entity
        FakeEmailCampaign.objects.create(user=user, name='Camp01')

        fname = 'mailing_lists'
        func_field_name = 'get_pretty_properties'
        HeaderFilter.create(pk='test-hf_camp', name='Campaign view', model=FakeEmailCampaign,
                            cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                                        (EntityCellRegularField, {'name': fname}),
                                        (EntityCellFunctionField, {'func_field_name': func_field_name}),
                                       ]
                           )

        url = FakeEmailCampaign.get_lv_absolute_url()
        # We just check that it does not crash
        self.assertPOST200(url, data={'sort_field': 'regular_field-' + fname})
        self.assertPOST200(url, data={'sort_field': 'function_field-' + func_field_name})

    @override_settings(FAST_QUERY_MODE_THRESHOLD=100000)
    def test_ordering_regularfield_fastmode(self):
        "Ordering = '-fieldname'"
        user = self.login()
        self.assertTrue('-start', FakeActivity._meta.ordering[0])

        act_type = FakeActivityType.objects.all()[0]
        create_act = partial(FakeActivity.objects.create, user=user, type=act_type)
        act1 = create_act(title='Act#1', start=now())
        act2 = create_act(title='Act#2', start=act1.start + timedelta(hours=1))

        hf = self.get_object_or_fail(HeaderFilter, pk='creme_core-hf_fakeactivity')  # See fake populate

        response = self.assertPOST200(FakeActivity.get_lv_absolute_url(), {'hfilter': hf.pk})
        content = self._get_lv_content(self._get_lv_node(response))
        first_idx  = self.assertIndex(act2.title, content)
        second_idx = self.assertIndex(act1.title, content)
        self.assertLess(first_idx, second_idx)

        with self.assertNoException():
            lvs = response.context['list_view_state']
            sort_field = lvs.sort_field
            sort_order = lvs.sort_order

        self.assertEqual('regular_field-start', sort_field)
        self.assertEqual('-',  sort_order)

        self.assertRegex(self._get_sql(response),
                         r'ORDER BY '
                         r'.creme_core_fakeactivity.\..start. DESC( NULLS LAST)?\, '
                         r'.creme_core_fakeactivity.\..cremeentity_ptr_id. DESC( NULLS LAST)?$'
                        )

    @override_settings(FAST_QUERY_MODE_THRESHOLD=100000)
    def test_ordering_default(self):
        user = self.login()
        self.assertEqual(('last_name', 'first_name'), FakeContact._meta.ordering)

        create_contact = partial(FakeContact.objects.create, user=user)
        create_contact(first_name='Spike',  last_name='Spiegel')
        create_contact(first_name='Faye',   last_name='Valentine')
        create_contact(first_name='Edward', last_name='Wong')

        url = FakeContact.get_lv_absolute_url()
        # For the filter to prevent an issue when HeaderFiltersTestCase is launched before this test
        hf = self.get_object_or_fail(HeaderFilter, pk='creme_core-hf_fakecontact')  # See fake populate
        response = self.assertPOST200(url, {'hfilter': hf.pk})

        entries = FakeContact.objects.all()
        self.assertListViewContentOrder(response, 'last_name', entries)

        listview_state = response.context['list_view_state']
        self.assertEqual('regular_field-last_name', listview_state.sort_field)
        self.assertEqual('', listview_state.sort_order)

        self.assertRegex(self._get_sql(response),
                         r'ORDER BY '
                         r'.creme_core_fakecontact.\..last_name. ASC( NULLS FIRST)?\, '
                         r'.creme_core_fakecontact.\..first_name. ASC( NULLS FIRST)?\, '
                         r'.creme_core_fakecontact.\..cremeentity_ptr_id. ASC( NULLS FIRST)?$'
                        )

    def test_ordering_merge_column_and_default(self):
        self.assertEqual(('last_name', 'first_name'), FakeContact._meta.ordering)
        user = self.login()

        create_civ = FakeCivility.objects.create
        mister = create_civ(title='Mister')
        miss   = create_civ(title='Miss')
        self.assertLess(mister.id, miss.id)

        create_contact = partial(FakeContact.objects.create, user=user)
        spike = create_contact(first_name='Spike',  last_name='Spiegel',   civility=mister)
        faye = create_contact(first_name='Faye',   last_name='Valentine', civility=miss)
        ed = create_contact(first_name='Edward', last_name='Wong')

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cell_civ   = build_cell(name='civility')
        cell_fname = build_cell(name='first_name')
        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=FakeContact,
                                 cells_desc=[cell_civ,
                                             (EntityCellRegularField, {'name': 'last_name'}),
                                             cell_fname,
                                            ],
                                )

        contacts = FakeContact.objects.filter(pk__in=(spike, faye, ed))
        url = FakeContact.get_lv_absolute_url()
        response = self.assertPOST200(url, data={'hfilter': hf.id,
                                                 'sort_field': cell_civ.key,
                                                 'sort_order': '',
                                                }
                                     )

        entries = contacts.order_by('civility', 'last_name', 'first_name')
        self.assertListViewContentOrder(response, 'last_name', entries)

        response = self.assertPOST200(url, data={'hfilter': hf.id,
                                                 'sort_field': cell_civ.key,
                                                 'sort_order': '-',
                                                }
                                     )

        entries = contacts.order_by('-civility', 'last_name', 'first_name')
        self.assertListViewContentOrder(response, 'last_name', entries)

        response = self.assertPOST200(url, data={'hfilter': hf.id,
                                                 'sort_field': cell_fname.key,
                                                 'sort_order': '',
                                                }
                                     )

        entries = contacts.order_by('first_name', 'last_name')
        self.assertListViewContentOrder(response, 'last_name', entries)

        response = self.assertPOST200(url, data={'hfilter': hf.id,
                                                 'sort_field': cell_fname.key,
                                                 'sort_order': '-',
                                                }
                                     )

        entries = contacts.order_by('-first_name', 'last_name')
        self.assertListViewContentOrder(response, 'last_name', entries)

    def test_ordering_related_column(self):
        user = self.login()

        self.assertEqual(('last_name', 'first_name'), FakeContact._meta.ordering)
        self.assertFalse(bool(FakeAddress._meta.ordering))

        def create_contact(first_name, last_name, address):
            contact = FakeContact.objects.create(user=user, first_name=first_name, last_name=last_name)
            contact.address = FakeAddress.objects.create(entity=contact, value=address)
            contact.save()
            return contact

        create_contact(first_name='Spike',  last_name='Spiegel',   address='C')
        create_contact(first_name='Faye',   last_name='Valentine', address='B')
        create_contact(first_name='Edward', last_name='Wong',      address='A')

        cell = EntityCellRegularField.build(model=FakeContact, name='address')
        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=FakeContact,
                                 cells_desc=[(EntityCellRegularField, {'name': 'civility'}),
                                             (EntityCellRegularField, {'name': 'last_name'}),
                                             (EntityCellRegularField, {'name': 'first_name'}),
                                             cell,
                                         ],
                                )

        url = FakeContact.get_lv_absolute_url()
        # For the filter to prevent an issue when HeaderFiltersTestCase is launched before this test
        response = self.assertPOST200(url, {'hfilter':    hf.id,
                                            'sort_field': cell.key,
                                            'sort_order': '',
                                           })

        entries = FakeContact.objects.order_by('address_id', 'last_name', 'first_name')
        self.assertListViewContentOrder(response, 'last_name', entries)

        listview_state = response.context['list_view_state']
        self.assertEqual(cell.key, listview_state.sort_field)
        self.assertEqual('', listview_state.sort_order)
        self.assertRegex(self._get_sql(response),
                         r'ORDER BY '
                         r'.creme_core_fakecontact.\..address_id. ASC( NULLS FIRST)?\, '
                         r'.creme_core_fakecontact.\..last_name. ASC( NULLS FIRST)?\, '
                         r'.creme_core_fakecontact.\..first_name. ASC( NULLS FIRST)?\, '
                         r'.creme_core_fakecontact.\..cremeentity_ptr_id. ASC( NULLS FIRST)?$'
                        )

    def test_ordering_customfield_column(self):
        "Custom field ordering is ignored in current implementation"
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
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

        url = FakeOrganisation.get_lv_absolute_url()
        response = self.assertPOST200(url, {'hfilter': hf.pk,
                                            'sort_field': cfield_cell.key,
                                            'sort_order': '',
                                           }
                                     )

        entries = FakeOrganisation.objects.order_by('name')
        self.assertListViewContentOrder(response, 'name', entries)

    def _aux_test_ordering_fastmode(self):
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
        create_contact(first_name='Spike',  last_name='Spiegel')
        create_contact(first_name='Faye',   last_name='Valentine')
        create_contact(first_name='Edward', last_name='Wong')

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cell1 = build_cell(name='birthday')
        hf = HeaderFilter.create(pk='test-hf_contact', name='Contact view',
                                 model=FakeContact,
                                 cells_desc=[cell1,
                                             build_cell(name='last_name'),
                                             build_cell(name='first_name'),
                                            ],
                                )

        context = CaptureQueriesContext()

        with context:
            self.assertPOST200(FakeContact.get_lv_absolute_url(),
                               data={'hfilter': hf.pk,
                                     'sort_field': cell1.key,
                                     'sort_order': '',
                                    }
                               )

        main_sql_match = re.compile(r'SELECT .creme_core_cremeentity.\..id., .*'
                                    r'.creme_core_fakecontact.\..last_name., .*'
                                    r'WHERE .creme_core_cremeentity.\..is_deleted. = '
                                   ).match
        main_sql = [sql for sql in context.captured_sql if main_sql_match(sql)]

        if not main_sql:
            self.fail('No main Listview query in:\n{}'.format('\n'.join(context.captured_sql)))
        elif len(main_sql) >= 2:
            self.fail('There should be one SQL query: {}'.format(main_sql))

        return main_sql[0]

    @override_settings(FAST_QUERY_MODE_THRESHOLD=100000)
    def test_ordering_fastmode_01(self):
        "Fast mode=OFF"
        sql = self._aux_test_ordering_fastmode()
        self.assertRegex(sql,
                         r'ORDER BY '
                         r'.creme_core_fakecontact.\..birthday. ASC( NULLS FIRST)?, '
                         r'.creme_core_fakecontact.\..last_name. ASC( NULLS FIRST)?, '
                         r'.creme_core_fakecontact.\..first_name. ASC( NULLS FIRST)?, '
                         r'.creme_core_fakecontact.\..cremeentity_ptr_id. ASC( NULLS FIRST)? LIMIT'
                        )

    @override_settings(FAST_QUERY_MODE_THRESHOLD=2)
    def test_ordering_fastmode_02(self):
        "Fast mode=ON"
        sql = self._aux_test_ordering_fastmode()
        self.assertRegex(sql,
                         r'ORDER BY'
                         r' .creme_core_fakecontact.\..birthday. ASC( NULLS FIRST)?,'
                         r' .creme_core_fakecontact.\..cremeentity_ptr_id. ASC( NULLS FIRST)? LIMIT'
                        )

    def test_efilter01(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        efilter = EntityFilter.create('test-filter01', 'Red', FakeOrganisation,
                                      user=user, is_custom=False,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                        model=FakeOrganisation,
                                                        operator=EntityFilterCondition.ISTARTSWITH,
                                                        name='name', values=['Red'],
                                                    ),
                                                 ],
                                     )

        context = CaptureQueriesContext()

        with context:
            response = self.assertPOST200(self.url, data={'filter': efilter.id})

        content = self._get_lv_content(self._get_lv_node(response))
        self.assertNotIn(bebop.name, content)
        self.assertCountOccurrences(redtail.name, content, count=1)
        self.assertCountOccurrences(dragons.name, content, count=1)

        self.assertEqual(2, response.context['entities'].paginator.count)

        self._assertNoDistinct(context.captured_sql)

    def test_qfilter_GET_legacy(self):
        "Old format"
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        context = CaptureQueriesContext()

        with context:
            response = self.assertGET200(self.url, data={'q_filter': '{"name":  "Bebop" }'})

        lv_node = self._get_lv_node(response)
        inputs_content = self._get_lv_inputs_content(lv_node)
        # self.assertIn(('q_filter', '{"name":"Bebop"}'), inputs_content)
        self.assertIn(('q_filter', QSerializer().dumps(Q(name='Bebop'))), inputs_content)

        content = self._get_lv_content(lv_node)
        self.assertCountOccurrences(bebop.name, content, count=1)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        self.assertEqual(1, response.context['entities'].paginator.count)

    def test_qfilter_GET(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        context = CaptureQueriesContext()
        qfilter_json = QSerializer().dumps(Q(name='Bebop'))

        with context:
            response = self.assertGET200(self.url, data={'q_filter': qfilter_json})

        lv_node = self._get_lv_node(response)
        inputs_content = self._get_lv_inputs_content(lv_node)
        self.assertIn(('q_filter', qfilter_json), inputs_content)

        content = self._get_lv_content(lv_node)
        self.assertCountOccurrences(bebop.name, content, count=1)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        self.assertEqual(1, response.context['entities'].paginator.count)

        # TODO
        # self._assertNoDistinct(context.captured_sql)

    def test_qfilter_POST_legacy(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        response = self.assertPOST200(self.url, data={'q_filter': '{"name":"Bebop"}'})

        lv_node = self._get_lv_node(response)
        inputs_content = self._get_lv_inputs_content(lv_node)
        # self.assertIn(('q_filter', '{"name":"Bebop"}'), inputs_content)
        self.assertIn(('q_filter', QSerializer().dumps(Q(name='Bebop'))), inputs_content)

        content = self._get_lv_content(lv_node)
        self.assertCountOccurrences(bebop.name, content, count=1)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        self.assertEqual(1, response.context['entities'].paginator.count)

    def test_qfilter_POST(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        qfilter_json = QSerializer().dumps(Q(name='Bebop'))
        response = self.assertPOST200(self.url, data={'q_filter': qfilter_json})

        lv_node = self._get_lv_node(response)
        inputs_content = self._get_lv_inputs_content(lv_node)
        self.assertIn(('q_filter', qfilter_json), inputs_content)

        content = self._get_lv_content(lv_node)
        self.assertCountOccurrences(bebop.name, content, count=1)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        self.assertEqual(1, response.context['entities'].paginator.count)

    def test_qfilter_invalid_json(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        # Invalid json : ignore filter
        response = self.assertGET200(self.url, data={'q_filter': '{"name":"Bebop"'})

        content = self._get_lv_content(self._get_lv_node(response))
        self.assertIn(bebop.name, content)
        self.assertIn(redtail.name, content)
        self.assertIn(dragons.name, content)

    def test_qfilter_invalid_Q(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        # Invalid field : ignore filter
        response = self.assertGET200(self.url, data={'q_filter': '{"unknown_model_field":"Bebop"}'})

        content = self._get_lv_content(self._get_lv_node(response))
        self.assertIn(bebop.name, content)
        self.assertIn(redtail.name, content)
        self.assertIn(dragons.name, content)

    def test_header_buttons(self):
        self.login()
        hf = self._build_hf()
        ct_id = self.ctype.id

        qdict = {'name': 'Bebop'}
        response = self.assertGET200(self.url, data={'hfilter': hf.id, 'q_filter': json_dump(qdict)})

        page_tree = html5lib.parse(response.content, namespaceHTMLElements=False)
        buttons_node = page_tree.find(".//div[@class='list-header-buttons clearfix']")
        self.assertIsNotNone(buttons_node)

        hrefs = [button_node.attrib.get('href') for button_node in buttons_node.findall('a')]
        self.assertEqual(FakeOrganisation.get_create_absolute_url(), hrefs[0])

        dl_url = '{}?ct_id={}'.format(reverse('creme_core__dl_listview'), ct_id)
        dl_uri = hrefs[1]
        self.assertTrue(dl_uri.startswith(dl_url),
                        'URI <{}> does not starts with <{}>'.format(dl_uri, dl_url)
                       )
        self.assertIn('list_url={}'.format(self.url), dl_uri)
        self.assertIn('hfilter={}'.format(hf.id),     dl_uri)
        self.assertIn('extra_q={}'.format(urlquote(QSerializer().dumps(Q(**qdict)))), dl_uri)

        dl_header_uri = hrefs[2]
        self.assertTrue(dl_header_uri.startswith(dl_url),
                        'URI <{}> does not starts with <{}>'.format(dl_header_uri, dl_url)
                       )
        self.assertIn('header=true', dl_header_uri)

        self.assertEqual(reverse('creme_core__mass_import',   args=(self.ctype.id,)), hrefs[3])
        self.assertEqual(reverse('creme_core__batch_process', args=(ct_id,)),         hrefs[4])

    @override_settings(FAST_QUERY_MODE_THRESHOLD=1000000, PAGE_SIZES=[10, 25], DEFAULT_PAGE_SIZE_IDX=1)
    def test_search_regularfields01(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish',   phone='668899')
        redtail   = create_orga(name='Redtail',     phone='889977')
        dragons   = create_orga(name='Red Dragons', phone='123')

        phone_cell = EntityCellRegularField.build(model=FakeOrganisation, name='phone')
        self._build_hf(phone_cell)

        url = self.url

        def build_data(name='', phone='', clear=0):
            return {'clear_search': clear,
                    'regular_field-name': name,
                    phone_cell.key: phone,
                   }

        response = self.assertPOST200(url, data=build_data('Red'))
        lv_node = self._get_lv_node(response)
        widget_node = self._get_lv_header_widget_nodes(lv_node, phone_cell.key, input_type='input')[0]
        self.assertEqual(_('Phone number'), widget_node.attrib.get('title'))

        content = self._get_lv_content(lv_node)
        self.assertNotIn(bebop.name,     content)
        self.assertNotIn(swordfish.name, content)
        self.assertCountOccurrences(redtail.name, content, count=1)
        self.assertCountOccurrences(dragons.name, content, count=1)
        self.assertEqual(2, response.context['entities'].paginator.count)

        response = self.assertPOST200(url, data=build_data('', '88', clear=1))
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertIn(redtail.name,    content)
        self.assertNotIn(dragons.name, content)

        response = self.assertPOST200(url, data=build_data('Red', '88', clear=1))
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertNotIn(bebop.name,     content)
        self.assertNotIn(swordfish.name, content)
        self.assertIn(redtail.name,      content)
        self.assertNotIn(dragons.name,   content)

        context = CaptureQueriesContext()

        with context:
            response = self.assertPOST200(url, data=build_data(clear=1))

        content = self._get_lv_content(self._get_lv_node(response))
        self.assertIn(bebop.name,     content)
        self.assertIn(swordfish.name, content)
        self.assertIn(redtail.name,   content)
        self.assertIn(dragons.name,   content)
        self.assertEqual(4, response.context['entities'].paginator.count)

        # optimized_count = 0
        #
        # todo: use regex to reduce code ?
        # db_engine = settings.DATABASES['default']['ENGINE']
        # if db_engine == 'django.db.backends.mysql':
        #     fast_sql = 'SELECT COUNT(*) AS `__count` FROM `creme_core_cremeentity` WHERE ' \
        #                '(`creme_core_cremeentity`.`is_deleted` = 0 AND ' \
        #                '`creme_core_cremeentity`.`entity_type_id` = %s)' % self.ctype.id
        #     slow_sql = 'SELECT COUNT(*) FROM (SELECT DISTINCT `creme_core_cremeentity`.`id`'
        # elif db_engine == 'django.db.backends.sqlite3':
        #     fast_sql = 'SELECT COUNT(*) AS "__count" FROM "creme_core_cremeentity" ' \
        #                     'WHERE ("creme_core_cremeentity"."is_deleted" = %s AND ' \
        #                     '"creme_core_cremeentity"."entity_type_id" = %s)'
        #     slow_sql = 'SELECT COUNT(*) FROM (SELECT DISTINCT "creme_core_cremeentity"."id"'
        # # elif db_engine == 'django.db.backends.postgresql_psycopg2':
        # elif db_engine.startswith('django.db.backends.postgresql'):
        #     fast_sql = 'SELECT COUNT(*) AS "__count" FROM "creme_core_cremeentity" WHERE ' \
        #                '("creme_core_cremeentity"."is_deleted" = false AND ' \
        #                '"creme_core_cremeentity"."entity_type_id" = %s)' % self.ctype.id
        #     slow_sql = 'SELECT COUNT(*) FROM (SELECT DISTINCT "creme_core_cremeentity"."id"'
        # else:
        #     self.fail('This RDBMS is not managed by this test case.')
        #
        # for sql in context.captured_sql:
        #     if fast_sql in sql:
        #         optimized_count += 1
        #
        #     self.assertNotIn(slow_sql, sql)
        #
        # self.assertEqual(1, optimized_count, context.captured_queries)
        db_engine = settings.DATABASES['default']['ENGINE']
        if db_engine == 'django.db.backends.mysql':
            trash_sql = 'SELECT COUNT(*) AS `__count` FROM `creme_core_cremeentity` WHERE `creme_core_cremeentity`.`is_deleted` = 1'
        elif db_engine == 'django.db.backends.sqlite3':
            trash_sql = 'SELECT COUNT(*) AS "__count" FROM "creme_core_cremeentity" WHERE "creme_core_cremeentity"."is_deleted" = 1'
        elif db_engine.startswith('django.db.backends.postgresql'):
            trash_sql = 'SELECT COUNT(*) AS "__count" FROM "creme_core_cremeentity" WHERE "creme_core_cremeentity"."is_deleted" = true'
        else:
            self.fail('This RDBMS is not managed by this test case.')

        optimized_counts = []
        for sql in context.captured_sql:
            if sql.startswith('SELECT COUNT(*)') and sql != trash_sql:
                if 'INNER JOIN' in sql:
                    self.fail('slow COUNT query found: {}'.format(sql))

                optimized_counts.append(sql)

        if len(optimized_counts) != 1:
            self.fail('{} fast queries found in:\n{}'.format(
                len(optimized_counts),
                '\n'.join(' - {}'.format(sql) for sql in optimized_counts),
            ))

    def test_search_regularfields02(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop = create_orga(name='Bebop inc', subject_to_vat=False)
        nerv  = create_orga(name='NERV',      subject_to_vat=True)
        seele = create_orga(name='Seele',     subject_to_vat=True)

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='subject_to_vat')
        hf = self._build_hf(cell)
        url = self.url
        data = {'hfilter': hf.id}
        response = self.assertPOST200(url, data=dict(data, **{cell.key: '1'}))
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop, orgas_set)
        self.assertIn(nerv,     orgas_set)
        self.assertIn(seele,    orgas_set)

        # -------------------------------
        context = CaptureQueriesContext()
        with context:
            response = self.assertPOST200(url, data=dict(data, **{cell.key: '0'}))

        orgas_set = self._get_entities_set(response)
        self.assertIn(bebop,    orgas_set)
        self.assertNotIn(nerv,  orgas_set)
        self.assertNotIn(seele, orgas_set)

        # TODO
        # self._assertNoDistinct(context.captured_sql)

    def test_search_regularfields03(self):
        "ForeignKey (NULL or not)"
        user = self.login()

        create_sector = FakeSector.objects.create
        mercenary = create_sector(title='Mercenary')
        robotics  = create_sector(title='Robotics')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop = create_orga(name='Bebop inc', sector=mercenary)
        nerv  = create_orga(name='NERV',      sector=robotics)
        seele = create_orga(name='Seele')

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='sector')
        hf = self._build_hf(cell)

        url = self.url
        data = {'hfilter': hf.id}
        # ----------------------------------------------------------------------
        response = self.assertGET200(url, data=data)
        widget_node = self._get_lv_header_widget_nodes(self._get_lv_node(response),
                                                       cell.key, input_type='select',
                                                      )[0]
        self.assertEqual(_('Sector'), widget_node.attrib.get('title'))

        options = self._get_options_for_select_node(widget_node)
        self.assertIn(('', _('All')), options)
        self.assertIn((str(mercenary.id), mercenary.title), options)
        self.assertIn((str(robotics.id),  robotics.title),  options)

        # ----------------------------------------------------------------------
        response = self.assertPOST200(url, data=dict(data, **{cell.key: str(mercenary.id)}))
        orgas_set = self._get_entities_set(response)
        self.assertIn(bebop,    orgas_set)
        self.assertNotIn(nerv,  orgas_set)
        self.assertNotIn(seele, orgas_set)

        # ----------------------------------------------------------------------
        response = self.assertPOST200(url, data=dict(data, **{cell.key: 'NULL'}))
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop, orgas_set)
        self.assertNotIn(nerv,  orgas_set)
        self.assertIn(seele,    orgas_set)

    def test_search_regularfields04(self):
        "BooleanField (NULL or not)"
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop = create_orga(name='Bebop inc', subject_to_vat=True)
        nerv  = create_orga(name='NERV',      subject_to_vat=False)
        seele = create_orga(name='Seele',     subject_to_vat=True)

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='subject_to_vat')
        hf = self._build_hf(cell)

        url = self.url
        data = {'hfilter': hf.id}

        # ----------------------------------------------------------------------
        response = self.assertGET200(url, data=data)
        widget_node = self._get_lv_header_widget_nodes(self._get_lv_node(response),
                                                       cell.key, input_type='select',
                                                      )[0]

        options = self._get_options_for_select_node(widget_node)
        self.assertIn(('',  _('All')), options)
        self.assertIn(('1', _('Yes')), options)
        self.assertIn(('0', _('No')),  options)
        self.assertEqual(3, len(options))

        # ----------------------------------------------------------------------
        response = self.assertPOST200(url, data=dict(data, **{cell.key: '1'}))
        orgas_set = self._get_entities_set(response)
        self.assertIn(bebop, orgas_set)
        self.assertIn(seele, orgas_set)
        self.assertNotIn(nerv, orgas_set)

        # ----------------------------------------------------------------------
        response = self.assertPOST200(url, data=dict(data, **{cell.key: '0'}))
        orgas_set = self._get_entities_set(response)
        self.assertIn(nerv, orgas_set)
        self.assertNotIn(bebop, orgas_set)
        self.assertNotIn(seele, orgas_set)

    def test_search_datefields01(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop',     creation_date=date(year=2075, month=3, day=26))
        swordfish = create_orga(name='Swordfish', creation_date=date(year=2074, month=6, day=5))
        redtail   = create_orga(name='Redtail',   creation_date=date(year=2076, month=7, day=25))
        dragons   = create_orga(name='Red Dragons')

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='creation_date')
        hf = self._build_hf(cell)
        url = self.url

        # ----------------------------------------------------------------------
        response = self.assertGET200(url, data={'hfilter': hf.id})
        widget_nodes = self._get_lv_header_widget_nodes(self._get_lv_node(response),
                                                        cell_key=cell.key,
                                                        input_type='input',
                                                        count=2,
                                                       )
        attrs = widget_nodes[0].attrib
        self.assertEqual('datefield',           attrs.get('type'))
        self.assertEqual(_('Date of creation'), attrs.get('title'))
        self.assertEqual(settings.DATE_FORMAT_JS.get(settings.DATE_FORMAT),
                         attrs.get('data-format')
                        )

        # ----------------------------------------------------------------------
        build_data = lambda cdate: {'hfilter': hf.id, cell.key: cdate}

        response = self.assertPOST200(url, data=build_data(['1-1-2075']))
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertIn(bebop.name,        content)
        self.assertNotIn(swordfish.name, content)
        self.assertIn(redtail.name,      content)
        self.assertNotIn(dragons.name,   content)

        response = self.assertPOST200(url, data=build_data(['', '1-1-2075']))
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        response = self.assertPOST200(url, data=build_data(['1-1-2074', '31-12-2074']))
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        response = self.assertPOST200(url, data=build_data(['notadate']))
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertIn(bebop.name,     content)
        self.assertIn(swordfish.name, content)
        self.assertIn(redtail.name,   content)
        self.assertIn(dragons.name,   content)

    def test_search_datetimefields01(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop      = create_orga(name='Bebop')
        swordfish  = create_orga(name='Swordfish')
        swordfish2 = create_orga(name='Swordfish II')
        sf_alpha   = create_orga(name='Swordfish Alpha')
        redtail    = create_orga(name='Redtail')

        def set_created(orga, dt):
            FakeOrganisation.objects.filter(pk=orga.id).update(created=dt)

        create_dt = self.create_datetime
        set_created(bebop,      create_dt(year=2075, month=3, day=26))
        set_created(swordfish,  create_dt(year=2074, month=6, day=5, hour=12))
        set_created(swordfish2, create_dt(year=2074, month=6, day=6, hour=0))  # Next day
        set_created(sf_alpha,   create_dt(year=2074, month=6, day=4, hour=23, minute=59))  # Previous day
        set_created(redtail,    create_dt(year=2076, month=7, day=25))

        cell = EntityCellRegularField.build(model=FakeOrganisation, name='created')
        hf = self._build_hf(cell)
        url = self.url

        def post(created):
            response = self.assertPOST200(url, data={'hfilter': hf.id,
                                                     cell.key: created,
                                                    }
                                         )
            return  self._get_lv_content(self._get_lv_node(response))

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

    def test_search_field_with_choices(self):
        user = self.login()

        invoice = FakeInvoice.objects.create(user=user, name='Invoice #1')
        create_line = partial(FakeInvoiceLine.objects.create, user=user, linked_invoice=invoice)
        line1 = create_line(item='Item #1', discount_unit=fake_constants.FAKE_PERCENT_UNIT)
        line2 = create_line(item='Item #2', discount_unit=fake_constants.FAKE_AMOUNT_UNIT)
        line3 = create_line(item='Item #3', discount_unit=fake_constants.FAKE_PERCENT_UNIT)

        build_cell = partial(EntityCellRegularField.build, model=FakeInvoiceLine)
        du_cell = build_cell(name='discount_unit')
        hf = HeaderFilter.create(
            pk='test-hf_invoiceline', name='Line view', model=FakeInvoiceLine,
            cells_desc=[build_cell(name='item'),
                        build_cell(name='discount'),
                        du_cell,
                       ],
        )

        url = FakeInvoiceLine.get_lv_absolute_url()
        response = self.assertGET200(url, data={'hfilter': hf.id})
        widget_node = self._get_lv_header_widget_nodes(self._get_lv_node(response),
                                                       du_cell.key, input_type='select',
                                                      )[0]

        options = self._get_options_for_select_node(widget_node)
        self.assertIn(('', _('All')), options)

        # ---------------------------------------------------------------------
        response = self.assertPOST200(
            url,
            data={'hfilter': hf.id,
                  du_cell.key: fake_constants.FAKE_PERCENT_UNIT,
                 },
        )
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertCountOccurrences(line1.item, content, count=1)
        self.assertCountOccurrences(line3.item, content, count=1)
        self.assertNotIn(line2.item, content)

    def test_search_fk01(self):
        user = self.login()

        create_civ = FakeCivility.objects.create
        mister = create_civ(title='Mister')
        miss   = create_civ(title='Miss')
        self.assertLess(mister.id, miss.id)

        create_img = partial(FakeImage.objects.create, user=user)
        img_faye = create_img(name='Faye selfie')
        img_ed   = create_img(name='Ed selfie')

        create_contact = partial(FakeContact.objects.create, user=user)
        spike = create_contact(first_name='Spike',  last_name='Spiegel',   civility=mister)
        faye  = create_contact(first_name='Faye',   last_name='Valentine', civility=miss, image=img_faye)
        ed    = create_contact(first_name='Edward', last_name='Wong',                     image=img_ed)

        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=FakeContact)

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
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

        url = FakeContact.get_lv_absolute_url()

        # ---------------------------------------------------------------------
        response = self.assertGET200(url, data={'hfilter': hf.id})
        get_widget_node = partial(self._get_lv_header_widget_nodes,
                                  lv_node=self._get_lv_node(response),
                                 )
        get_widget_node(cell_key=cell_image.key,    input_type='input')
        get_widget_node(cell_key=cell_img_name.key, input_type='input')
        get_widget_node(cell_key=cell_civ_name.key, input_type='input')

        civ_widget_node = get_widget_node(cell_key=cell_civ.key, input_type='select')[0]
        options = self._get_options_for_select_node(civ_widget_node)
        self.assertIn((str(mister.id), mister.title), options)
        self.assertIn((str(miss.id),   miss.title),   options)

        # ---------------------------------------------------------------------
        response = self.assertPOST200(url, data={'hfilter': hf.id})

        with self.assertNoException():
            selected_hf = response.context['header_filters'].selected

        self.assertEqual(hf, selected_hf)

        # ---------------------------------------------------------------------
        response = self.assertPOST200(url, data={cell_civ.key: mister.id})
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertCountOccurrences(spike.last_name, content, count=1)
        self.assertNotIn(faye.last_name, content)
        self.assertNotIn(ed.last_name,   content)

        # ---------------------------------------------------------------------
        response = self.assertPOST200(url, data={cell_civ_name.key: 'iss'})
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertNotIn(spike.last_name, content)
        self.assertIn(faye.last_name,     content)
        self.assertNotIn(ed.last_name,    content)

        # ---------------------------------------------------------------------
        response = self.assertPOST200(url, data={cell_img_name.key: img_ed.name})
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertNotIn(spike.last_name, content)
        self.assertNotIn(faye.last_name,  content)
        self.assertIn(ed.last_name,       content)

        # ---------------------------------------------------------------------
        response = self.assertPOST200(url, data={cell_image.key: img_ed.name})
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertNotIn(spike.last_name, content)
        self.assertNotIn(faye.last_name,  content)
        self.assertIn(ed.last_name,       content)

    def test_search_fk02(self):
        "Search on a subfield which is a FK too"
        user = self.login()

        create_cat = FakeFolderCategory.objects.create
        cat1 = create_cat(name='Maps')
        cat2 = create_cat(name='Blue prints')

        create_folder = partial(FakeFolder.objects.create, user=user)
        folder1 = create_folder(title='Earth maps', category=cat1)
        folder2 = create_folder(title='Mars maps',  category=cat1)
        folder3 = create_folder(title='Ships',      category=cat2)
        folder4 = create_folder(title="Faye's pix")

        create_doc = partial(FakeDocument.objects.create, user=user)
        doc1 = create_doc(title='Japan map',   linked_folder=folder1)
        doc2 = create_doc(title='Mars city 1', linked_folder=folder2)
        doc3 = create_doc(title='Swordfish',   linked_folder=folder3)
        doc4 = create_doc(title='Money!!.jpg', linked_folder=folder4)

        build_cell = partial(EntityCellRegularField.build, model=FakeDocument)
        cell = build_cell(name='linked_folder__category')
        hf = HeaderFilter.create(pk='test-hf_doc', name='Doc view', model=FakeDocument,
                                 cells_desc=[build_cell(name='title'), cell],
                                )

        response = self.assertPOST200(FakeDocument.get_lv_absolute_url(),
                                      data={'hfilter': hf.id,
                                            cell.key: cat1.id,
                                           }
                                     )
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertIn(doc1.title, content)
        self.assertIn(doc2.title, content)
        self.assertNotIn(doc3.title, content)
        self.assertNotIn(doc4.title, content)

        # '*is empty*'
        response = self.assertPOST200(FakeDocument.get_lv_absolute_url(),
                                      data={'hfilter': hf.id,
                                            cell.key: 'NULL',
                                           }
                                     )
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertNotIn(doc1.title, content)
        self.assertNotIn(doc2.title, content)
        self.assertNotIn(doc3.title, content)
        self.assertIn(doc4.title, content)

    def test_search_fk03(self):
        "Search on a subfield which is a FK on CremeEntity"
        user = self.login()

        create_folder = partial(FakeFolder.objects.create, user=user)
        p_folder1 = create_folder(title='Maps')
        p_folder2 = create_folder(title='Pix')

        folder1 = create_folder(title='Earth', parent=p_folder1)
        folder2 = create_folder(title='Mars',  parent=p_folder1)
        folder3 = create_folder(title='Ships')
        folder4 = create_folder(title="Faye's pix", parent=p_folder2)

        create_doc = partial(FakeDocument.objects.create, user=user)
        doc1 = create_doc(title='Japan',       linked_folder=folder1)
        doc2 = create_doc(title='Mars city 1', linked_folder=folder2)
        doc3 = create_doc(title='Swordfish',   linked_folder=folder3)
        doc4 = create_doc(title='Money!!.jpg', linked_folder=folder4)

        build_cell = partial(EntityCellRegularField.build, model=FakeDocument)
        cell = build_cell(name='linked_folder__parent')
        hf = HeaderFilter.create(pk='test-hf_doc', name='Doc view', model=FakeDocument,
                                 cells_desc=[build_cell(name='title'), cell],
                                )

        response = self.assertPOST200(FakeDocument.get_lv_absolute_url(),
                                      data={'hfilter': hf.id,
                                            cell.key: p_folder1.title,
                                           }
                                     )
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertIn(doc1.title, content)
        self.assertIn(doc2.title, content)
        self.assertNotIn(doc3.title, content)
        self.assertNotIn(doc4.title, content)

    def test_search_m2mfields01(self):
        "M2M to CremeEntity model"
        user = self.login()
        build_cell = partial(EntityCellRegularField.build, model=FakeEmailCampaign)

        cell_m2m = build_cell(name='mailing_lists')
        self.assertTrue(cell_m2m.has_a_filter)
        self.assertFalse(cell_m2m.sortable)
        self.assertEqual('mailing_lists__header_filter_search_field__icontains',
                         cell_m2m.filter_string
                        )

        hf = HeaderFilter.create(pk='test-hf_camp', name='Campaign view',
                                 model=FakeEmailCampaign,
                                 cells_desc=[build_cell(name='name'), cell_m2m]
                                )

        create_mlist = partial(FakeMailingList.objects.create, user=user)
        ml1 = create_mlist(name='Bebop staff')
        ml2 = create_mlist(name='Mafia staff')

        create_camp = partial(FakeEmailCampaign.objects.create, user=user)
        camp1 = create_camp(name='Ships')
        camp2 = create_camp(name='Bonzais')
        camp3 = create_camp(name='Mushrooms')

        # camp1.mailing_lists = [ml1, ml2]
        # camp2.mailing_lists = [ml1]
        camp1.mailing_lists.set([ml1, ml2])
        camp2.mailing_lists.set([ml1])

        url = FakeEmailCampaign.get_lv_absolute_url()
        # ----------------------------------------------------------------------
        response = self.assertGET200(url, data={'hfilter': hf.id})
        self._get_lv_header_widget_nodes(self._get_lv_node(response),
                                         cell_m2m.key, input_type='input',
                                        )

        # ----------------------------------------------------------------------
        def search(term):
            response = self.assertPOST200(url,
                                          data={'hfilter': hf.id,
                                                cell_m2m.key: term,
                                               }
                                         )
            return self._get_lv_content(self._get_lv_node(response))

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
        hf = HeaderFilter.create(pk='test-hf_img', name='Image view', model=FakeImage)
        build_cell = partial(EntityCellRegularField.build, model=FakeImage)

        cell_m2m = build_cell(name='categories')
        self.assertTrue(cell_m2m.has_a_filter)
        self.assertEqual('categories', cell_m2m.filter_string)

        hf.cells = [build_cell(name='name'), cell_m2m]
        hf.save()

        cat1, cat2 = FakeImageCategory.objects.all()[:2]

        create_img = partial(FakeImage.objects.create, user=user)
        img1 = create_img(name='Bebop image')
        img2 = create_img(name='Dragon logo')
        img3 = create_img(name='Mushrooms image')

        # img1.categories = [cat1, cat2]
        # img2.categories = [cat1]
        img1.categories.set([cat1, cat2])
        img2.categories.set([cat1])

        def search(searched):
            response = self.assertPOST200(FakeImage.get_lv_absolute_url(),
                                          data={'hfilter': hf.id,
                                                cell_m2m.key: searched,
                                               }
                                         )
            return self._get_lv_content(self._get_lv_node(response))

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
        hf = HeaderFilter.create(pk='test-hf_img', name='Image view', model=FakeImage)
        build_cell = partial(EntityCellRegularField.build, model=FakeImage)

        cell_m2m = build_cell(name='categories__name')
        self.assertTrue(cell_m2m.has_a_filter)

        hf.cells = [build_cell(name='name'), cell_m2m]
        hf.save()

        cat1, cat2 = FakeImageCategory.objects.all()[:2]

        create_img = partial(FakeImage.objects.create, user=user)
        img1 = create_img(name='Bebop image')
        img2 = create_img(name='Dragon logo')
        img3 = create_img(name='Mushrooms image')

        # img1.categories = [cat1, cat2]
        # img2.categories = [cat1]
        img1.categories.set([cat1, cat2])
        img2.categories.set([cat1])

        def search(searched):
            response = self.assertPOST200(FakeImage.get_lv_absolute_url(),
                                          data={'hfilter': hf.id,
                                                cell_m2m.key: searched,
                                               }
                                         )
            return self._get_lv_content(self._get_lv_node(response))

        content = search(cat1.name[:5])
        self.assertIn(img1.name,    content)
        self.assertIn(img2.name,    content)
        self.assertNotIn(img3.name, content)

    def test_search_relations01(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        create_contact = partial(FakeContact.objects.create, user=user)
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

        cell = EntityCellRelation(model=FakeOrganisation, rtype=rtype)
        hf = self._build_hf(cell)

        url = self.url
        # ----------------------------------------------------------------------
        response = self.assertGET200(url, data={'hfilter': hf.id})
        self._get_lv_header_widget_nodes(self._get_lv_node(response),
                                         cell.key, input_type='input',
                                        )

        # ----------------------------------------------------------------------
        data = {'hfilter': hf.id, 'name': '', cell.key: 'Spiege'}
        response = self.assertPOST200(url, data=data)
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertIn(redtail.name,    content)
        self.assertNotIn(dragons.name, content)

        data['regular_field-name'] = 'Swo'
        content = self._get_lv_content(self._get_lv_node(self.assertPOST200(url, data=data)))
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

    def test_search_relations02(self):
        "2 searches at the same time"
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')

        create_contact = partial(FakeContact.objects.create, user=user)
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

        cell1 = EntityCellRelation(model=FakeOrganisation, rtype=rtype1)
        cell2 = EntityCellRelation(model=FakeOrganisation, rtype=rtype2)
        hf = self._build_hf(cell1, cell2)

        response = self.assertPOST200(self.url,
                                      data={'hfilter': hf.id,
                                            cell1.key: 'Jet',
                                            cell2.key: 'Jet',
                                           }
                                     )
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertIn(bebop.name, content)
        self.assertNotIn(swordfish.name, content)
        self.assertNotIn(redtail.name,   content)

    def test_search_customfield01(self):
        "INT"
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
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

        cell = EntityCellCustomField(cfield)
        hf = self._build_hf(cell)

        # ----------------------------------------------------------------------
        response = self.assertGET200(self.url, data={'hfilter': hf.id})
        self._get_lv_header_widget_nodes(self._get_lv_node(response),
                                         cell.key, input_type='input',
                                        )

        # ----------------------------------------------------------------------
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      'regular_field-name': '',
                                                      cell.key: '4',
                                                     }
                                     )
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertIn(bebop.name,        content)
        self.assertNotIn(swordfish.name, content)
        self.assertIn(redtail.name,      content)
        self.assertNotIn(dragons.name,   content)

    def test_search_customfield02(self):
        "INT & STR"
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
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

        cell1 = EntityCellCustomField(cfield1)
        cell2 = EntityCellCustomField(cfield2)
        hf = self._build_hf(cell1, cell2)

        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      'regular_field-name': '',
                                                      cell1.key: '4',
                                                      cell2.key: '#05',
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

        create_orga = partial(FakeOrganisation.objects.create, user=user)
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

        cell1 = EntityCellCustomField(cfield1)
        cell2 = EntityCellCustomField(cfield2)
        hf = self._build_hf(cell1, cell2)
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      'regular_field-name': '',
                                                      cell1.key: '4',
                                                      cell2.key: '2000',
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

        create_orga = partial(FakeOrganisation.objects.create, user=user)
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

        cell = EntityCellCustomField(cfield)
        hf = self._build_hf(cell)
        # ----------------------------------------------------------------------
        response = self.assertGET200(self.url, data={'hfilter': hf.id})
        widget_node = self._get_lv_header_widget_nodes(self._get_lv_node(response),
                                                       cell.key, input_type='select',
                                                      )[0]

        options = self._get_options_for_select_node(widget_node)
        self.assertIn(('NULL',        _('* is empty *')), options)
        self.assertIn((str(type1.id), type1.value),       options)
        self.assertIn((str(type2.id), type2.value),       options)

        # ----------------------------------------------------------------------
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      'regular_field-name': '',
                                                      cell.key: type1.id,
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,   orgas_set)
        self.assertIn(swordfish,  orgas_set)
        self.assertIn(redtail,    orgas_set)
        self.assertNotIn(dragons, orgas_set)

        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      'name': '',
                                                      cell.key: 'NULL',
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

        create_orga = partial(FakeOrganisation.objects.create, user=user)
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

        cell = EntityCellCustomField(cfield)
        hf = self._build_hf(cell)
        # ----------------------------------------------------------------------
        response = self.assertGET200(self.url, data={'hfilter': hf.id})
        widget_node = self._get_lv_header_widget_nodes(self._get_lv_node(response),
                                                       cell.key, input_type='select',
                                                      )[0]

        options = self._get_options_for_select_node(widget_node)
        self.assertIn(('NULL',           _('* is empty *')), options)
        self.assertIn((str(can_walk.id), can_walk.value),    options)

        # ----------------------------------------------------------------------
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      'regular_field-name': '',
                                                      cell.key: can_walk.id,
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,   orgas_set)
        self.assertNotIn(dragons, orgas_set)
        self.assertIn(eva01,      orgas_set)
        self.assertIn(valkyrie,   orgas_set)

        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      'regular_field-name': '',
                                                      cell.key: 'NULL',
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

        create_orga = partial(FakeOrganisation.objects.create, user=user)
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

        cell_type  = EntityCellCustomField(cfield_type)
        cell_color = EntityCellCustomField(cfield_color)
        hf = self._build_hf(cell_type, cell_color)
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      'regular_field-name': '',
                                                      cell_type.key:  type1.id,
                                                      cell_color.key: color2.id,
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertIn(redtail,      orgas_set)
        self.assertNotIn(dragons,   orgas_set)

        set_cfvalue(cfield_color, dragons, color1.id)  # Type is NULL

        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      'regular_field-name': '',
                                                      cell_type.key:  'NULL',
                                                      cell_color.key: color1.id,
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

        create_orga = partial(FakeOrganisation.objects.create, user=user)
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

        cell_cap   = EntityCellCustomField(cfield_cap)
        cell_color = EntityCellCustomField(cfield_color)
        hf = self._build_hf(cell_cap, cell_color)
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      'regular_field-name': '',
                                                      cell_cap.key:   can_walk.id,
                                                      cell_color.key: red.id,
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertIn(eva02,        orgas_set)
        self.assertNotIn(valkyrie,  orgas_set)

        response = self.assertPOST200(self.url, data={'regular_field-name': '',
                                                      cell_cap.key:   can_walk.id,
                                                      cell_color.key: 'NULL',
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

        create_orga = partial(FakeOrganisation.objects.create, user=user)
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

        cell = EntityCellCustomField(cfield)
        hf = self._build_hf(cell)

        # ----------------------------------------------------------------------
        response = self.assertGET200(self.url, data={'hfilter': hf.id})
        widget_nodes = self._get_lv_header_widget_nodes(self._get_lv_node(response),
                                                        cell_key=cell.key,
                                                        input_type='input',
                                                        count=2,
                                                       )
        self.assertEqual('datefield', widget_nodes[0].attrib.get('type'))

        # ----------------------------------------------------------------------

        def post(dates):
            response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                          cell.key: dates,
                                                         }
                                         )
            return self._get_lv_content(self._get_lv_node(response))

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

        create_orga = partial(FakeOrganisation.objects.create, user=user)
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

        cell_flight = EntityCellCustomField(cfield_flight)
        cell_blood  = EntityCellCustomField(cfield_blood)
        hf = self._build_hf(cell_flight, cell_blood)
        response = self.assertPOST200(self.url,
                                      data={'hfilter': hf.id,
                                            cell_flight.key: ['1-1-2074', '31-12-2074'],
                                            cell_blood.key:  ['',         '1-1-2075'],
                                           },
                                     )
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertNotIn(bebop.name,      content)
        self.assertIn(swordfish.name,     content)
        self.assertNotIn(redtail.name,    content)
        self.assertNotIn(hammerhead.name, content)
        self.assertNotIn(dragons.name,    content)

    def test_search_customfield10(self):
        "BOOL"
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        dragons   = create_orga(name='Red Dragons')

        cfield = CustomField.objects.create(name='Is hunting?',
                                            content_type=self.ctype,
                                            field_type=CustomField.BOOL,
                                           )
        klass = cfield.get_value_class()

        def set_cfvalue(entity, value):
            klass(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(bebop,   True)
        set_cfvalue(dragons, False)

        cell = EntityCellCustomField(cfield)
        hf = self._build_hf(cell)

        # ----------------------------------------------------------------------
        response = self.assertGET200(self.url, data={'hfilter': hf.id})
        widget_node = self._get_lv_header_widget_nodes(self._get_lv_node(response),
                                                       cell.key, input_type='select',
                                                      )[0]

        options = self._get_options_for_select_node(widget_node)
        self.assertIn(('',  _('All')), options)
        self.assertIn(('1', _('Yes')), options)
        self.assertIn(('0', _('No')),  options)
        self.assertEqual(3, len(options))

        # ----------------------------------------------------------------------
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      cell.key: '1',
                                                     },
                                     )
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertIn(bebop.name,        content)
        self.assertNotIn(swordfish.name, content)
        self.assertNotIn(dragons.name,   content)

        # ----------------------------------------------------------------------
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      cell.key: '0',
                                                     },
                                     )
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertIn(dragons.name, content)
        self.assertNotIn(bebop.name,     content)
        self.assertNotIn(swordfish.name, content)

    def test_search_functionfield01(self):
        "PropertiesField"
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
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
        cell = EntityCellFunctionField.build(FakeOrganisation, ff_name)
        hf = self._build_hf(cell)

        # ----------------------------------------------------------------------
        response = self.assertGET200(self.url, data={'hfilter': hf.id})
        widget_node = self._get_lv_header_widget_nodes(self._get_lv_node(response),
                                                       cell.key, input_type='input',
                                                      )[0]
        self.assertEqual(_('Properties'), widget_node.attrib.get('title'))

        # ----------------------------------------------------------------------
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      cell.key: 'red',
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

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')

        # func_field = FakeOrganisation.function_fields.get('tests-get_fake_todos')
        func_field = function_field_registry.get(FakeOrganisation, 'tests-fake_todos')
        cell = EntityCellFunctionField(model=FakeOrganisation, func_field=func_field)
        hf = self._build_hf(cell)

        # ----------------------------------------------------------------------
        response = self.assertGET200(self.url, data={'hfilter': hf.id})
        self._assert_no_lv_header_widget_node(self._get_lv_node(response), cell.key)

        # ----------------------------------------------------------------------
        response = self.assertPOST200(self.url,
                                      data={'hfilter': hf.id,
                                            'regular_field-name': '',
                                            cell.key: bebop.name,
                                           }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertIn(bebop,     orgas_set)
        self.assertIn(swordfish, orgas_set)

    def test_search_functionfield03(self):
        "FunctionField with choices"
        user = self.login()

        invoice = FakeInvoice.objects.create(user=user, name='Invoice #1')
        create_line = partial(FakeInvoiceLine.objects.create, user=user, linked_invoice=invoice)
        line1 = create_line(item='Item #1', discount_unit=fake_constants.FAKE_PERCENT_UNIT, discount='0.5')
        line2 = create_line(item='Item #2', discount_unit=fake_constants.FAKE_AMOUNT_UNIT)
        line3 = create_line(item='Item #3', discount_unit=fake_constants.FAKE_PERCENT_UNIT)
        line4 = create_line(item='Item #4', discount_unit=fake_constants.FAKE_PERCENT_UNIT, discount='5.0')

        cell = EntityCellFunctionField.build(model=FakeInvoiceLine,
                                             func_field_name='tests-great_discount'
                                            )
        hf = HeaderFilter.create(
            pk='test-hf_invoiceline', name='Line view', model=FakeInvoiceLine,
            cells_desc=[
                (EntityCellRegularField, {'name': 'item'}),
                (EntityCellRegularField, {'name': 'discount'}),
                (EntityCellRegularField, {'name': 'discount_unit'}),
                cell,
            ]
        )

        url = FakeInvoiceLine.get_lv_absolute_url()

        # ----------------------------------------------------------------------
        response = self.assertGET200(url, data={'hfilter': hf.id})
        widget_node = self._get_lv_header_widget_nodes(self._get_lv_node(response),
                                                       cell.key, input_type='select',
                                                      )[0]
        self.assertEqual('Great discount', widget_node.attrib.get('title'))

        options = self._get_options_for_select_node(widget_node)
        self.assertIn(('',  _('All')), options)
        self.assertIn(('1', 'Bad'),    options)

        # ----------------------------------------------------------------------
        response = self.assertPOST200(url,
                                      data={'hfilter': hf.id,
                                            cell.key: 3,
                                           },
                                     )
        content = self._get_lv_content(self._get_lv_node(response))
        self.assertCountOccurrences(line4.item, content, count=1)
        self.assertNotIn(line1.item, content)
        self.assertNotIn(line2.item, content)
        self.assertNotIn(line3.item, content)

    def _build_orgas(self):
        count = FakeOrganisation.objects.count()
        expected_count = 13  # 13 = 10 (our page size) + 3
        self.assertLessEqual(count, expected_count)

        create_orga = partial(FakeOrganisation.objects.create, user=self.user)
        for i in range(expected_count - count):
            create_orga(name='Mafia #{:02}'.format(i))

        organisations = list(FakeOrganisation.objects.all())
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
        self.assertFalse(hasattr(entities_page1, 'start_index'))

        paginator = entities_page1.paginator
        self.assertEqual(10, paginator.per_page)
        self.assertEqual(13, paginator.count)
        self.assertEqual(2, paginator.num_pages)

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

        count = FakeContact.objects.count()
        self.assertLessEqual(count, expected_count)

        create_contact = partial(FakeContact.objects.create, user=user)
        for i in range(expected_count - count):
            create_contact(first_name='Gally', last_name='Tuned{:02}'.format(i))

        contacts = list(FakeContact.objects.all())
        self.assertEqual(expected_count, len(contacts))

        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=FakeContact,
                                 cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                                             (EntityCellRegularField, {'name': 'first_name'}),
                                            ],
                                )

        def post(page_info=None):
            return self.assertPOST200(FakeContact.get_lv_absolute_url(),
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

        count = FakeContact.objects.count()
        self.assertLessEqual(count, expected_count)

        ids = list(range(expected_count - count))
        shuffle(ids)

        create_contact = partial(FakeContact.objects.create, user=user)
        for i, id_ in enumerate(ids):
            # NB: we want the ordering by 'first_name' to be different from the 'last_name' one
            create_contact(first_name='Gally{:02}'.format(id_), last_name='Tuned{:02}'.format(i))

        ordering_fname = 'first_name'
        contacts = list(FakeContact.objects.order_by(ordering_fname))
        self.assertEqual(expected_count, len(contacts))

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cell2 = build_cell(name=ordering_fname)
        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=FakeContact,
                                 cells_desc=[build_cell(name='last_name'), cell2],
                                 )

        def post(page_info=None):
            return self.assertPOST200(FakeContact.get_lv_absolute_url(),
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

        count = FakeContact.objects.count()
        self.assertLessEqual(count, expected_count)

        create_contact = partial(FakeContact.objects.create, user=user)
        for i in range(expected_count - count):
            # NB: same last_name
            create_contact(first_name='Gally', last_name='Tuned', phone='11 22 33 #%02i' % i)

        contacts = list(FakeContact.objects.order_by('last_name', 'first_name', 'cremeentity_ptr_id'))
        self.assertEqual(expected_count, len(contacts))

        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=FakeContact,
                                 cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                                             (EntityCellRegularField, {'name': 'first_name'}),
                                            ],
                                )

        def post(page_info=None):
            return self.assertPOST200(FakeContact.get_lv_absolute_url(),
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

        count = FakeContact.objects.count()
        self.assertLessEqual(count, expected_count)

        create_contact = partial(FakeContact.objects.create, user=user)
        for i in range(expected_count - count):
            create_contact(first_name='Gally', last_name='Tuned#{:02}'.format(i))

        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=FakeContact,
                                 cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                                             (EntityCellRegularField, {'name': 'first_name'}),
                                            ],
                                )

        def post(page_info=''):
            response = self.assertPOST200(FakeContact.get_lv_absolute_url(),
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

        count = FakeContact.objects.count()
        self.assertLessEqual(count, expected_count)

        create_contact = partial(FakeContact.objects.create, user=user)
        for i in range(expected_count - count):
            create_contact(first_name='Gally', last_name='Tuned#%02i' % i)

        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=FakeContact,
                                 cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                                             (EntityCellRegularField, {'name': 'first_name'}),
                                            ],
                                )

        def post(page_info=''):
            response = self.assertPOST200(FakeContact.get_lv_absolute_url(),
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
        for c in FakeContact.objects.reverse()[:4]:
            c.delete()

        last_page = post(json_dump(page3_info))
        self.assertTrue(last_page.has_previous())

    @override_settings(FAST_QUERY_MODE_THRESHOLD=5, PAGE_SIZES=[10])
    def test_pagination_fast07(self):
        "Page is saved"
        self.login()
        organisations = self._build_orgas()
        hf = self._build_hf()
        url = FakeOrganisation.get_lv_absolute_url()

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
        url = FakeOrganisation.get_lv_absolute_url()

        def post():
            response = self.assertPOST200(url,
                                          data={'hfilter': hf.id,
                                                'rows': 10,
                                               }
                                         )
            return response.context['entities']

        page1_slow = post()
        self.assertTrue(hasattr(page1_slow, 'number'))  # Means slow mode

        FakeOrganisation.objects.create(user=user, name='Zalem')  # We exceed the threshold
        page1_fast = post()
        self.assertTrue(hasattr(page1_fast, 'next_page_info'))  # Means fast mode

    def test_listview_popup_GET_legacy(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        context = CaptureQueriesContext()

        with context:
            response = self.assertGET200(reverse('creme_core__listview_popup'), data={
                'ct_id': self.ctype.id,
                'q_filter': '{"name":  "Bebop" }',  # JSON with strange format
            })

        lv_node = self._get_lv_node(response)
        inputs_content = self._get_lv_inputs_content(lv_node)
        # self.assertIn(('q_filter', '{"name":"Bebop"}'), inputs_content)
        self.assertIn(('q_filter', QSerializer().dumps(Q(name='Bebop'))), inputs_content)

        content = self._get_lv_content(lv_node)
        self.assertCountOccurrences(bebop.name, content, count=1)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        self.assertEqual(1, response.context['entities'].paginator.count)

    def test_listview_popup_GET(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        context = CaptureQueriesContext()
        qfilter_json = QSerializer().dumps(Q(name='Bebop'))

        with context:
            response = self.assertGET200(reverse('creme_core__listview_popup'),
                                         data={'ct_id': self.ctype.id,
                                               'q_filter': qfilter_json,
                                              },
                                        )

        lv_node = self._get_lv_node(response)
        inputs_content = self._get_lv_inputs_content(lv_node)
        self.assertIn(('q_filter', qfilter_json), inputs_content)

        content = self._get_lv_content(lv_node)
        self.assertCountOccurrences(bebop.name, content, count=1)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        self.assertEqual(1, response.context['entities'].paginator.count)

    def test_listview_popup_POST_legacy(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        context = CaptureQueriesContext()

        with context:
            response = self.assertPOST200(reverse('creme_core__listview_popup'), data={
                'ct_id': self.ctype.id,
                'q_filter': '{"name":  "Bebop" }',
            })

        lv_node = self._get_lv_node(response)
        inputs_content = self._get_lv_inputs_content(lv_node)
        # self.assertIn(('q_filter', '{"name":"Bebop"}'), inputs_content)
        self.assertIn(('q_filter', QSerializer().dumps(Q(name='Bebop'))), inputs_content)

        content = self._get_lv_content(lv_node)
        self.assertCountOccurrences(bebop.name, content, count=1)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        self.assertEqual(1, response.context['entities'].paginator.count)

    def test_listview_popup_POST(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        context = CaptureQueriesContext()
        qfilter_json = QSerializer().dumps(Q(name='Bebop'))

        with context:
            response = self.assertPOST200(reverse('creme_core__listview_popup'),
                                          data={'ct_id': self.ctype.id,
                                                'q_filter': qfilter_json,
                                               },
                                         )

        lv_node = self._get_lv_node(response)
        inputs_content = self._get_lv_inputs_content(lv_node)
        self.assertIn(('q_filter', qfilter_json), inputs_content)

        content = self._get_lv_content(lv_node)
        self.assertCountOccurrences(bebop.name, content, count=1)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        self.assertEqual(1, response.context['entities'].paginator.count)
