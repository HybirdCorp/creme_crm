# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.test import RequestFactory

    from ..base import CremeTestCase
    from ..fake_models import (FakeContact as Contact,
            FakeOrganisation as Organisation, FakeActivity as Activity,
            FakeInvoice as Invoice, FakeDocument as Document,
            FakeSector as Sector)
    from creme.creme_core.core.entity_cell import EntityCellRegularField
    from creme.creme_core.gui.listview import ListViewState
    from creme.creme_core.models import CremeUser
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class ListViewStateTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()

        cls.factory = RequestFactory()
        cls.user = CremeUser(username='yui', email='kawa.yui@kimengumi.jp',
                             first_name='Yui', last_name='Kawa',
                            )
        cls.url = Contact.get_lv_absolute_url()

    def _assertLVSEmpty(self, lvs):
        self.assertIsNone(lvs.entity_filter_id)
        self.assertIsNone(lvs.header_filter_id)
        self.assertIsNone(lvs.page)
        self.assertIsNone(lvs.rows)
        self.assertIsNone(lvs._search)
        self.assertIsNone(lvs.sort_order)
        self.assertIsNone(lvs.sort_field)
        self.assertEqual('', lvs._extra_sort_field)
        self.assertEqual((), lvs.research)
        self.assertIsNone(lvs.extra_q)
        self.assertEqual([], lvs._ordering)

    def _build_request(self):
        url = self.url
        request = self.factory.get(url)
        request.path = url
        request.user = self.user
        request.session = {}

        return request

    @staticmethod
    def _get_sql(queryset):
        return queryset.query.get_compiler('default').as_sql()[0]

    def test_init(self):
        lvs = ListViewState()
        self._assertLVSEmpty(lvs)
        self.assertIsNone(lvs.url)

    def test_get_state01(self):
        request = self._build_request()

        lvs = ListViewState.get_state(request)
        self.assertIsNone(lvs)

    def test_get_state02(self):
        request = self._build_request()
        url = self.url

        lvs1 = ListViewState(url=url)
        lvs1.register_in_session(request)
        self.assertIsInstance(request.session.get(url), dict)

        lvs2 = ListViewState.get_state(request)
        self._assertLVSEmpty(lvs2)
        self.assertEqual(url, lvs2.url)

    def test_build_from_request(self):
        request = self._build_request()
        lvs = ListViewState.build_from_request(request)
        self.assertIsInstance(lvs, ListViewState)
        self.assertEqual(self.url, lvs.url)
        self._assertLVSEmpty(lvs)

    def test_sort_oneorder_01(self):
        "Ordering: natural ordering key"
        field_name1 = 'name'
        field_name2 = 'email'
        self.assertEqual((field_name1,), Organisation._meta.ordering)

        build_cell = partial(EntityCellRegularField.build, model=Organisation)
        cells = [build_cell(name=field_name2),
                 build_cell(name=field_name1),
                ]

        lvs = ListViewState(url=Organisation.get_lv_absolute_url())
        key = cells[1].key
        lvs.set_sort(model=Organisation, cells=cells, cell_key=key, order='')
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)
        self.assertEqual([field_name1], lvs._ordering)

        qs = Organisation.objects.all()
        re = 'ORDER BY .creme_core_fakeorganisation.\..name. ASC$'
        self.assertRegexpMatches(self._get_sql(qs), re)
        self.assertRegexpMatches(self._get_sql(lvs.sort_query(qs)), re)

        # DESC -------------------
        lvs.set_sort(model=Organisation, cells=cells, cell_key=key, order='-')
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('-', lvs.sort_order)
        self.assertEqual(['-' + field_name1], lvs._ordering)

        qs = Organisation.objects.all()
        self.assertRegexpMatches(self._get_sql(lvs.sort_query(qs)),
                                 'ORDER BY .creme_core_fakeorganisation.\..name. DESC$'
                                )

    def test_sort_oneorder_02(self):
        "Ordering: add a not natural ordering key"
        field_name1 = 'name'
        field_name2 = 'email'

        build_cell = partial(EntityCellRegularField.build, model=Organisation)
        cells = [build_cell(name=field_name2),
                 build_cell(name=field_name1),
                ]

        lvs = ListViewState()
        key = cells[0].key
        lvs.set_sort(model=Organisation, cells=cells, cell_key=key, order='')
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)
        self.assertEqual([field_name2, field_name1], lvs._ordering)

        self.assertRegexpMatches(self._get_sql(lvs.sort_query(Organisation.objects.all())),
                                 'ORDER BY '
                                 '.creme_core_fakeorganisation.\..email. ASC, '
                                 '.creme_core_fakeorganisation.\..name. ASC$',
                                )

    def test_sort_oneorder_03(self):
        "set_sort(): empty cell name"
        field_name1 = 'name'
        build_cell = partial(EntityCellRegularField.build, model=Organisation)
        cells = [build_cell(name='email'),
                 build_cell(name=field_name1),
                ]

        lvs = ListViewState(url=Organisation.get_lv_absolute_url())
        lvs.set_sort(model=Organisation, cells=cells, cell_key=None, order=None)
        self.assertEqual(cells[1].key, lvs.sort_field)  # Fallback on natural model ordering
        self.assertEqual('', lvs.sort_order)
        self.assertEqual([field_name1], lvs._ordering)

    def test_sort_oneorder_04(self):
        "set_sort(): invalid cell name"
        field_name1 = 'name'
        build_cell = partial(EntityCellRegularField.build, model=Organisation)
        cells = [build_cell(name=field_name1),
                 build_cell(name='email'),
                ]

        lvs = ListViewState()
        lvs.set_sort(model=Organisation, cells=cells, cell_key='invalid', order='')
        self.assertEqual(cells[0].key, lvs.sort_field) # Fallback on natural model ordering
        self.assertEqual('', lvs.sort_order)
        self.assertEqual([field_name1], lvs._ordering)

    def test_sort_oneorder_05(self):
        "set_sort(): cell name is not displayed"
        field_name1 = 'name'
        field_name2 = 'phone'
        build_cell = partial(EntityCellRegularField.build, model=Organisation)
        cells = [build_cell(name=field_name2),
                 build_cell(name=field_name1),
                ]

        lvs = ListViewState()
        lvs.set_sort(model=Organisation, cells=cells, cell_key='email', order='')
        self.assertEqual(cells[1].key, lvs.sort_field)  # Fallback on natural model ordering
        self.assertEqual('', lvs.sort_order)
        self.assertEqual([field_name1], lvs._ordering)

        # Natural ordering not displayed ---------------
        cells = [build_cell(name=field_name2),
                 build_cell(name='sector'),
                ]

        lvs.set_sort(model=Organisation, cells=cells, cell_key='email', order='')
        self.assertIsNone(lvs.sort_field) # TODO: Fallback on first column ?
        self.assertEqual('', lvs.sort_order)
        self.assertEqual([], lvs._ordering)

    def test_sort_oneorder_06(self):
        "Ordering: add a not natural ordering key (FK to CremeEntity)"
        field_name1 = 'title'
        field_name2 = 'folder'
        self.assertEqual((field_name1,), Document._meta.ordering)

        build_cell = partial(EntityCellRegularField.build, model=Document)
        cells = [build_cell(name=field_name1),
                 build_cell(name=field_name2),
                ]

        lvs = ListViewState()
        key = cells[1].key
        lvs.set_sort(model=Document, cells=cells, cell_key=key, order='')
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)
        self.assertEqual([field_name2 + '__header_filter_search_field', field_name1], lvs._ordering)

        self.assertRegexpMatches(self._get_sql(lvs.sort_query(Document.objects.all())),
                                 'ORDER BY '
                                 'T4\..header_filter_search_field. ASC, '
                                 '.creme_core_fakedocument.\..title. ASC$'
                                )

    def test_sort_oneorder_07(self):
        "Ordering: add a not natural ordering key (FK to CremeModel)"
        self.assertEqual(('order',), Sector._meta.ordering)

        field_name1 = 'name'
        field_name2 = 'sector'

        build_cell = partial(EntityCellRegularField.build, model=Organisation)
        cells = [build_cell(name=field_name1),
                 build_cell(name=field_name2),
                ]

        lvs = ListViewState()
        key = cells[1].key
        lvs.set_sort(model=Organisation, cells=cells, cell_key=key, order='')
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)
        self.assertEqual([field_name2 + '__order', field_name1], lvs._ordering)

        self.assertRegexpMatches(self._get_sql(lvs.sort_query(Organisation.objects.all())),
                                 'ORDER BY '
                                 '.creme_core_fakesector.\..order. ASC, '
                                 '.creme_core_fakeorganisation.\..name. ASC$'
                                )

    def test_sort_oneorder_08(self):
        "set_sort(): natural ordering field not in cells"
        build_cell = partial(EntityCellRegularField.build, model=Organisation)
        cells = [build_cell(name='phone'),
                 build_cell(name='email'),
                ]

        lvs = ListViewState()
        key = cells[0].key
        lvs.set_sort(model=Organisation, cells=cells, cell_key=key, order='')
        self.assertEqual(cells[0].key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)
        self.assertEqual(['phone'], lvs._ordering)

        qs = Organisation.objects.all()
        self.assertRegexpMatches(self._get_sql(lvs.sort_query(qs)),
                                 'ORDER BY .creme_core_fakeorganisation.\..phone. ASC$',
                                )

        # Initial
        lvs.set_sort(model=Organisation, cells=cells, cell_key=None, order=None)
        self.assertIsNone(lvs.sort_field)
        self.assertEqual('', lvs.sort_order)
        self.assertEqual([], lvs._ordering)

        self.assertNotIn('ORDER BY ', self._get_sql(lvs.sort_query(qs)))

    def test_sort_twoorders_01(self):
        "meta.ordering: 2 fields"
        field_name1 = 'first_name'
        field_name2 = 'last_name'
        self.assertEqual((field_name2, field_name1), Contact._meta.ordering)

        build_cell = partial(EntityCellRegularField.build, model=Contact)
        cells = [build_cell(name=field_name1),
                 build_cell(name=field_name2),
                ]

        lvs = ListViewState()
        key = cells[0].key
        lvs.set_sort(model=Contact, cells=cells, cell_key=key, order='')
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)
        self.assertEqual([field_name1, field_name2], lvs._ordering)

        qs = Contact.objects.all()
        self.assertRegexpMatches(self._get_sql(qs),
                                 'ORDER BY '
                                 '.creme_core_fakecontact.\..last_name. ASC, '
                                 '.creme_core_fakecontact.\..first_name. ASC$',
                                )
        self.assertRegexpMatches(self._get_sql(lvs.sort_query(qs)),
                                 'ORDER BY '
                                 '.creme_core_fakecontact.\..first_name. ASC, '
                                 '.creme_core_fakecontact.\..last_name. ASC$',
                                )

        # DESC -----------------------------
        lvs.set_sort(model=Contact, cells=cells, cell_key=key, order='-')
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('-', lvs.sort_order)
        self.assertEqual(['-' + field_name1, '-' + field_name2], lvs._ordering)

        self.assertRegexpMatches(self._get_sql(lvs.sort_query(qs)),
                                 'ORDER BY '
                                 '.creme_core_fakecontact.\..first_name. DESC, '
                                 '.creme_core_fakecontact.\..last_name. DESC$',
                                )

    def test_sort_twoorders_02(self):
        "Add not natural ordering"
        field_name1 = 'first_name'
        field_name2 = 'last_name'
        field_name3 = 'phone'

        build_cell = partial(EntityCellRegularField.build, model=Contact)
        cells = [build_cell(name=field_name1),
                 build_cell(name=field_name2),
                 build_cell(name=field_name3),
                ]

        lvs = ListViewState()
        key = cells[2].key
        lvs.set_sort(model=Contact, cells=cells, cell_key=key, order='')
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)
        self.assertEqual([field_name3, field_name2, field_name1], lvs._ordering)

        qs = Contact.objects.all()
        self.assertRegexpMatches(self._get_sql(lvs.sort_query(qs)),
                                 'ORDER BY '
                                 '.creme_core_fakecontact.\..phone. ASC, '
                                 '.creme_core_fakecontact.\..last_name. ASC, '
                                 '.creme_core_fakecontact.\..first_name. ASC$',
                                )

        # DESC ------------------
        lvs.set_sort(model=Contact, cells=cells, cell_key=key, order='-')
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('-', lvs.sort_order)
        self.assertEqual(['-' + field_name3, field_name2, field_name1], lvs._ordering)

        self.assertRegexpMatches(self._get_sql(lvs.sort_query(qs)),
                                 'ORDER BY '
                                 '.creme_core_fakecontact.\..phone. DESC, '
                                 '.creme_core_fakecontact.\..last_name. ASC, '
                                 '.creme_core_fakecontact.\..first_name. ASC$',
                                )

    def test_sort_twoorders_03(self):
        "Add invalid order"
        field_name1 = 'first_name'
        field_name2 = 'last_name'

        build_cell = partial(EntityCellRegularField.build, model=Contact)
        cells = [build_cell(name=field_name1),
                 build_cell(name=field_name2),
                ]

        lvs = ListViewState()
        lvs.set_sort(model=Contact, cells=cells, cell_key='invalid', order='')
        self.assertEqual(cells[1].key, lvs.sort_field)  # Fallback to (first) natural ordering field
        self.assertEqual('', lvs.sort_order)
        self.assertEqual([field_name2, field_name1], lvs._ordering)

    def test_sort_twoorders_04(self):
        "set_sort(): natural ordering fields not in cells"
        build_cell = partial(EntityCellRegularField.build, model=Contact)
        cells = [build_cell(name='phone'),
                 build_cell(name='email'),
                ]

        lvs = ListViewState()
        lvs.set_sort(model=Contact, cells=cells, cell_key=None, order=None)
        self.assertIsNone(lvs.sort_field)
        self.assertEqual('', lvs.sort_order)
        self.assertEqual([], lvs._ordering)

        self.assertNotIn('ORDER BY ',
                         self._get_sql(lvs.sort_query(Contact.objects.all()))
                        )

    def test_sort_twoorders_05(self):
        "set_sort(): one natural ordering field not in cells"
        field_name1 = 'last_name'

        build_cell = partial(EntityCellRegularField.build, model=Contact)
        cells = [build_cell(name='email'),
                 build_cell(name=field_name1),
                ]

        lvs = ListViewState()
        lvs.set_sort(model=Contact, cells=cells, cell_key=None, order=None)
        key = cells[1].key  # First natural order
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)
        self.assertEqual([field_name1], lvs._ordering)

        qs = Contact.objects.all()
        self.assertRegexpMatches(self._get_sql(lvs.sort_query(qs)),
                                 'ORDER BY '
                                 '.creme_core_fakecontact.\..last_name. ASC$',
                                 # TODO: if there is an index (last_name, first_name)
                                 # '.creme_core_fakecontact.\..last_name. ASC, '
                                 # '.creme_core_fakecontact.\..first_name. ASC$',
                                )

    def test_sort_descorder_01(self):
        "Natural ordering is DESC"
        field_name1 = 'start'
        field_name2 = 'title'
        self.assertEqual(('-' + field_name1,), Activity._meta.ordering)

        build_cell = partial(EntityCellRegularField.build, model=Activity)
        cells = [build_cell(name=field_name1),
                 build_cell(name=field_name2),
                ]

        lvs = ListViewState()
        key = cells[0].key
        lvs.set_sort(model=Activity, cells=cells, cell_key=key, order='')
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)
        self.assertEqual([field_name1], lvs._ordering)

        qs = Activity.objects.all()
        self.assertRegexpMatches(self._get_sql(qs),
                                 'ORDER BY .creme_core_fakeactivity.\..start. DESC$'
                                )
        self.assertRegexpMatches(self._get_sql(lvs.sort_query(qs)),
                                 'ORDER BY .creme_core_fakeactivity.\..start. ASC$'
                                )

        # DESC ------------
        lvs.set_sort(model=Activity, cells=cells, cell_key=key, order='-')
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('-', lvs.sort_order)
        self.assertEqual(['-' + field_name1], lvs._ordering)

        self.assertRegexpMatches(self._get_sql(lvs.sort_query(qs)),
                                 'ORDER BY .creme_core_fakeactivity.\..start. DESC$'
                                )

    def test_sort_descorder_02(self):
        "Natural ordering is DESC => Empty GET/POST => DESC"
        field_name1 = 'start'
        field_name2 = 'title'

        build_cell = partial(EntityCellRegularField.build, model=Activity)
        cells = [build_cell(name=field_name1),
                 build_cell(name=field_name2),
                ]

        lvs = ListViewState()
        key = cells[0].key
        lvs.set_sort(model=Activity, cells=cells, cell_key=None, order=None)
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('-', lvs.sort_order)
        self.assertEqual(['-' + field_name1], lvs._ordering)

        qs = Activity.objects.all()
        re = 'ORDER BY .creme_core_fakeactivity.\..start. DESC$'
        self.assertRegexpMatches(self._get_sql(qs), re)
        self.assertRegexpMatches(self._get_sql(lvs.sort_query(qs)), re)

    def test_sort_descorder_03(self):
        "Natural ordering is DESC + another field"
        field_name1 = 'start'
        field_name2 = 'title'

        build_cell = partial(EntityCellRegularField.build, model=Activity)
        cells = [build_cell(name=field_name1),
                 build_cell(name=field_name2),
                ]

        lvs = ListViewState()
        key = cells[1].key
        lvs.set_sort(model=Activity, cells=cells, cell_key=key, order='')
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)
        self.assertEqual([field_name2, '-' + field_name1], lvs._ordering)

        qs = Activity.objects.all()
        self.assertRegexpMatches(self._get_sql(lvs.sort_query(qs)),
                                 'ORDER BY '
                                 '.creme_core_fakeactivity.\..title. ASC, '
                                 '.creme_core_fakeactivity.\..start. DESC$'
                                )

        # DESC ------------------------------
        lvs.set_sort(model=Activity, cells=cells, cell_key=key, order='-')
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('-', lvs.sort_order)
        self.assertEqual(['-' + field_name2, '-' + field_name1], lvs._ordering)

        self.assertRegexpMatches(self._get_sql(lvs.sort_query(qs)),
                                 'ORDER BY '
                                 '.creme_core_fakeactivity.\..title. DESC, '
                                 '.creme_core_fakeactivity.\..start. DESC$'
                                )

    def test_sort_twoordersdesc_01(self):
        "meta.ordering: 2 fields (one is DESC)"
        field_name1 = 'name'
        field_name2 = 'expiration_date'
        self.assertEqual((field_name1, '-' + field_name2), Invoice._meta.ordering)

        build_cell = partial(EntityCellRegularField.build, model=Invoice)
        cells = [build_cell(name=field_name1),
                 build_cell(name=field_name2),
                ]

        lvs = ListViewState()
        key = cells[0].key
        lvs.set_sort(model=Invoice, cells=cells, cell_key=key, order='')
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)
        self.assertEqual([field_name1, '-' + field_name2], lvs._ordering)

        qs = Invoice.objects.all()
        re = 'ORDER BY ' \
             '.creme_core_fakeinvoice.\..name. ASC, ' \
             '.creme_core_fakeinvoice.\..expiration_date. DESC$'
        self.assertRegexpMatches(self._get_sql(qs), re)
        self.assertRegexpMatches(self._get_sql(lvs.sort_query(qs)), re)

        # DESC -----------------------------
        lvs.set_sort(model=Invoice, cells=cells, cell_key=key, order='-')
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('-', lvs.sort_order)
        self.assertEqual(['-' + field_name1, field_name2], lvs._ordering)

        self.assertRegexpMatches(self._get_sql(lvs.sort_query(qs)),
                                 'ORDER BY '
                                 '.creme_core_fakeinvoice.\..name. DESC, '
                                 '.creme_core_fakeinvoice.\..expiration_date. ASC$'
                                )

    # TODO: test handle_research() + get_q_with_research()