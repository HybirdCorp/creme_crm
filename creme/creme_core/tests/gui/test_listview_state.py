# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.test import RequestFactory

    from ..base import CremeTestCase
    from ..fake_models import (FakeContact, FakeOrganisation, FakeActivity,
            FakeInvoice, FakeDocument, FakeSector)
    from creme.creme_core.core.entity_cell import EntityCellRegularField
    from creme.creme_core.gui.listview import ListViewState
    from creme.creme_core.models import CremeUser
    from creme.creme_core.utils.db import get_indexed_ordering
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class ListViewStateTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super(ListViewStateTestCase, cls).setUpClass()

        cls.factory = RequestFactory()
        cls.user = CremeUser(username='yui', email='kawa.yui@kimengumi.jp',
                             first_name='Yui', last_name='Kawa',
                            )
        cls.url = FakeContact.get_lv_absolute_url()

    def _assertLVSEmpty(self, lvs):
        self.assertIsNone(lvs.entity_filter_id)
        self.assertIsNone(lvs.header_filter_id)
        self.assertIsNone(lvs.page)
        self.assertIsNone(lvs.rows)
        self.assertIsNone(lvs.sort_order)
        self.assertIsNone(lvs.sort_field)
        self.assertEqual((), lvs.research)
        self.assertIsNone(lvs.extra_q)

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
        lvs = ListViewState.build_from_request(request.GET, request.path)
        self.assertIsInstance(lvs, ListViewState)
        self.assertEqual(self.url, lvs.url)
        self._assertLVSEmpty(lvs)

    def test_order_sql(self):
        self.assertEqual(('name',), FakeOrganisation._meta.ordering)

        self.assertRegex(self._get_sql(FakeOrganisation.objects.all()),
                         'ORDER BY .creme_core_fakeorganisation.\..name. ASC( NULLS FIRST)?$'
                        )

        # Check that order by 'id' does not use cremeentity.id, but fakeorganisation.cremeentity_ptr_id
        self.assertRegex(self._get_sql(FakeOrganisation.objects.order_by('id')),
                         'ORDER BY .creme_core_fakeorganisation.\..cremeentity_ptr_id. ASC( NULLS FIRST)?$'
                        )
        self.assertRegex(self._get_sql(FakeOrganisation.objects.order_by('name', 'id')),
                         'ORDER BY '
                         '.creme_core_fakeorganisation.\..name. ASC( NULLS FIRST)?\, '
                         '.creme_core_fakeorganisation.\..cremeentity_ptr_id. ASC( NULLS FIRST)?$'
                        )

    def test_sort_oneorder_01(self):
        "Ordering: natural ordering key"
        field_name1 = 'name'
        field_name2 = 'email'
        self.assertEqual((field_name1,), FakeOrganisation._meta.ordering)

        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        cells = [build_cell(name=field_name2),
                 build_cell(name=field_name1),
                ]

        lvs = ListViewState(url=FakeOrganisation.get_lv_absolute_url())
        key = cells[1].key
        ordering = lvs.set_sort(model=FakeOrganisation, cells=cells, cell_key=key, order='')
        self.assertEqual((field_name1, 'cremeentity_ptr_id'), ordering)
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)

        # Fast mode
        self.assertEqual((field_name1, 'cremeentity_ptr_id'),
                         lvs.set_sort(model=FakeOrganisation, cells=cells,
                                      cell_key=key, order='', fast_mode=True,
                                     )
                        )

        # DESC -------------------
        ordering = lvs.set_sort(model=FakeOrganisation, cells=cells, cell_key=key, order='-')
        self.assertEqual(('-' + field_name1, '-cremeentity_ptr_id'), ordering)
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('-', lvs.sort_order)

    def test_sort_oneorder_02(self):
        "Ordering: add a not natural ordering key"
        field_name1 = 'name'
        field_name2 = 'email'

        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        cells = [build_cell(name=field_name2),
                 build_cell(name=field_name1),
                ]

        lvs = ListViewState()
        key = cells[0].key
        ordering = lvs.set_sort(model=FakeOrganisation, cells=cells, cell_key=key, order='')
        self.assertEqual((field_name2, field_name1, 'cremeentity_ptr_id'), ordering)
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)

    def test_sort_oneorder_03(self):
        "set_sort(): empty cell name"
        field_name1 = 'name'
        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        cells = [build_cell(name='email'),
                 build_cell(name=field_name1),
                ]

        lvs = ListViewState(url=FakeOrganisation.get_lv_absolute_url())
        ordering = lvs.set_sort(model=FakeOrganisation, cells=cells, cell_key=None, order=None)
        self.assertEqual(cells[1].key, lvs.sort_field)  # Fallback on natural model ordering
        self.assertEqual('', lvs.sort_order)
        self.assertEqual((field_name1, 'cremeentity_ptr_id'), ordering)

    def test_sort_oneorder_04(self):
        "set_sort(): invalid cell name"
        field_name1 = 'name'
        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        cells = [build_cell(name=field_name1),
                 build_cell(name='email'),
                ]

        lvs = ListViewState()
        ordering = lvs.set_sort(model=FakeOrganisation, cells=cells, cell_key='invalid', order='')
        self.assertEqual(cells[0].key, lvs.sort_field) # Fallback on natural model ordering
        self.assertEqual('', lvs.sort_order)
        self.assertEqual((field_name1, 'cremeentity_ptr_id'), ordering)

    def test_sort_oneorder_05(self):
        "set_sort(): cell name is not displayed"
        field_name1 = 'name'
        field_name2 = 'phone'
        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        cells = [build_cell(name=field_name2),
                 build_cell(name=field_name1),
                ]

        lvs = ListViewState()
        ordering = lvs.set_sort(model=FakeOrganisation, cells=cells, cell_key='email', order='')
        self.assertEqual(cells[1].key, lvs.sort_field)  # Fallback on natural model ordering
        self.assertEqual('', lvs.sort_order)
        self.assertEqual((field_name1, 'cremeentity_ptr_id'), ordering)

        # Natural ordering not displayed ---------------
        cells = [build_cell(name=field_name2),
                 build_cell(name='sector'),
                ]

        ordering = lvs.set_sort(model=FakeOrganisation, cells=cells, cell_key='email', order='')
        self.assertIsNone(lvs.sort_field)  # TODO: Fallback on first column ?
        self.assertEqual('', lvs.sort_order)
        self.assertEqual(('cremeentity_ptr_id',), ordering)

    def test_sort_oneorder_06(self):
        "Ordering: add a not natural ordering key (FK to CremeEntity)"
        field_name1 = 'title'
        field_name2 = 'linked_folder'
        self.assertEqual((field_name1,), FakeDocument._meta.ordering)

        build_cell = partial(EntityCellRegularField.build, model=FakeDocument)
        cells = [build_cell(name=field_name1),
                 build_cell(name=field_name2),
                ]

        lvs = ListViewState()
        key = cells[1].key
        ordering = lvs.set_sort(model=FakeDocument, cells=cells, cell_key=key, order='')
        self.assertEqual((field_name2 + '__header_filter_search_field', field_name1, 'cremeentity_ptr_id'),
                         ordering
                        )
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)

    def test_sort_oneorder_07(self):
        "Ordering: add a not natural ordering key (FK to CremeModel)"
        self.assertEqual(('order',), FakeSector._meta.ordering)

        field_name1 = 'name'
        field_name2 = 'sector'

        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        cells = [build_cell(name=field_name1),
                 build_cell(name=field_name2),
                ]

        lvs = ListViewState()
        key = cells[1].key
        ordering = lvs.set_sort(model=FakeOrganisation, cells=cells, cell_key=key, order='')
        self.assertEqual((field_name2 + '__order', field_name1, 'cremeentity_ptr_id'), ordering)
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)

    def test_sort_oneorder_08(self):
        "set_sort(): natural ordering field not in cells"
        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        cells = [build_cell(name='phone'),
                 build_cell(name='email'),
                ]

        lvs = ListViewState()
        key = cells[0].key
        ordering = lvs.set_sort(model=FakeOrganisation, cells=cells, cell_key=key, order='')
        self.assertEqual(('phone', 'cremeentity_ptr_id'), ordering)
        self.assertEqual(cells[0].key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)

        # Initial
        ordering = lvs.set_sort(model=FakeOrganisation, cells=cells, cell_key=None, order=None)
        self.assertEqual(('cremeentity_ptr_id',), ordering)
        self.assertIsNone(lvs.sort_field)
        self.assertEqual('', lvs.sort_order)

    def test_sort_twoorders_01(self):
        "meta.ordering: 2 fields"
        field_name1 = 'first_name'
        field_name2 = 'last_name'
        self.assertEqual((field_name2, field_name1), FakeContact._meta.ordering)

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cells = [build_cell(name=field_name1),
                 build_cell(name=field_name2),
                ]

        lvs = ListViewState()
        key = cells[0].key
        ordering = lvs.set_sort(model=FakeContact, cells=cells, cell_key=key, order='')
        self.assertEqual((field_name1, field_name2, 'cremeentity_ptr_id'), ordering)
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)

        # DESC -----------------------------
        ordering = lvs.set_sort(model=FakeContact, cells=cells, cell_key=key, order='-')
        self.assertEqual(('-' + field_name1, '-' + field_name2, '-cremeentity_ptr_id'), ordering)
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('-', lvs.sort_order)

    def test_sort_twoorders_02(self):
        "Add not natural ordering"
        field_name1 = 'first_name'
        field_name2 = 'last_name'
        field_name3 = 'phone'

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cells = [build_cell(name=field_name1),
                 build_cell(name=field_name2),
                 build_cell(name=field_name3),
                ]

        lvs = ListViewState()
        key = cells[2].key
        ordering = lvs.set_sort(model=FakeContact, cells=cells, cell_key=key, order='')
        self.assertEqual((field_name3, field_name2, field_name1, 'cremeentity_ptr_id'), ordering)
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)

        # DESC ------------------
        ordering = lvs.set_sort(model=FakeContact, cells=cells, cell_key=key, order='-')
        self.assertEqual(('-' + field_name3, field_name2, field_name1, '-cremeentity_ptr_id'), ordering)
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('-', lvs.sort_order)

    def test_sort_twoorders_03(self):
        "Add invalid order"
        field_name1 = 'first_name'
        field_name2 = 'last_name'

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cells = [build_cell(name=field_name1),
                 build_cell(name=field_name2),
                ]

        lvs = ListViewState()
        ordering = lvs.set_sort(model=FakeContact, cells=cells, cell_key='invalid', order='')
        self.assertEqual(cells[1].key, lvs.sort_field)  # Fallback to (first) natural ordering field
        self.assertEqual('', lvs.sort_order)
        self.assertEqual((field_name2, field_name1, 'cremeentity_ptr_id'), ordering)

    def test_sort_twoorders_04(self):
        "set_sort(): natural ordering fields not in cells"
        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cells = [build_cell(name='phone'),
                 build_cell(name='email'),
                ]

        lvs = ListViewState()
        ordering = lvs.set_sort(model=FakeContact, cells=cells, cell_key=None, order=None)
        self.assertEqual(('cremeentity_ptr_id',), ordering)
        self.assertIsNone(lvs.sort_field)
        self.assertEqual('', lvs.sort_order)

    def test_sort_twoorders_05(self):
        "set_sort(): one natural ordering field not in cells"
        self.assertEqual(('name', '-expiration_date'),
                         FakeInvoice._meta.ordering
                        )
        self.assertIsNone(get_indexed_ordering(FakeInvoice, ['name', '-expiration_date']))

        field_name1 = 'name'

        build_cell = partial(EntityCellRegularField.build, model=FakeInvoice)
        cells = [build_cell(name='number'),
                 build_cell(name=field_name1),
                 # Not expiration_date
                ]

        lvs = ListViewState()
        ordering = lvs.set_sort(model=FakeInvoice, cells=cells, cell_key=None, order=None)
        self.assertEqual((field_name1, 'cremeentity_ptr_id'), ordering)

        key = cells[1].key  # First natural order
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)

    def test_sort_twoorders_06(self):
        "set_sort(): one natural ordering field not in cells, but an smart index exists."
        field_name1 = 'last_name'

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cells = [build_cell(name='email'),
                 build_cell(name=field_name1),
                ]

        lvs = ListViewState()
        ordering = lvs.set_sort(model=FakeContact, cells=cells, cell_key=None, order=None)
        self.assertEqual((field_name1, 'first_name', 'cremeentity_ptr_id'), ordering)

        key = cells[1].key  # First natural order
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)

    def test_sort_descorder_01(self):
        "Natural ordering is DESC"
        field_name1 = 'start'
        field_name2 = 'title'
        self.assertEqual(('-' + field_name1,), FakeActivity._meta.ordering)

        build_cell = partial(EntityCellRegularField.build, model=FakeActivity)
        cells = [build_cell(name=field_name1),
                 build_cell(name=field_name2),
                ]

        lvs = ListViewState()
        key = cells[0].key
        ordering = lvs.set_sort(model=FakeActivity, cells=cells, cell_key=key, order='')
        self.assertEqual((field_name1, 'cremeentity_ptr_id'), ordering)
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)

        # DESC ------------
        ordering = lvs.set_sort(model=FakeActivity, cells=cells, cell_key=key, order='-')
        self.assertEqual(('-' + field_name1, '-cremeentity_ptr_id'), ordering)
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('-', lvs.sort_order)

    def test_sort_descorder_02(self):
        "Natural ordering is DESC => Empty GET/POST => DESC"
        field_name1 = 'start'
        field_name2 = 'title'

        build_cell = partial(EntityCellRegularField.build, model=FakeActivity)
        cells = [build_cell(name=field_name1),
                 build_cell(name=field_name2),
                ]

        lvs = ListViewState()
        key = cells[0].key
        ordering = lvs.set_sort(model=FakeActivity, cells=cells, cell_key=None, order=None)
        self.assertEqual(('-' + field_name1, '-cremeentity_ptr_id'), ordering)
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('-', lvs.sort_order)

    def test_sort_descorder_03(self):
        "Natural ordering is DESC + another field"
        field_name1 = 'start'
        field_name2 = 'title'

        build_cell = partial(EntityCellRegularField.build, model=FakeActivity)
        cells = [build_cell(name=field_name1),
                 build_cell(name=field_name2),
                ]

        lvs = ListViewState()
        key = cells[1].key
        ordering = lvs.set_sort(model=FakeActivity, cells=cells, cell_key=key, order='')
        self.assertEqual((field_name2, '-' + field_name1, 'cremeentity_ptr_id'), ordering)
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)

        # DESC ------------------------------
        ordering = lvs.set_sort(model=FakeActivity, cells=cells, cell_key=key, order='-')
        self.assertEqual(('-' + field_name2, '-' + field_name1, '-cremeentity_ptr_id'), ordering)
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('-', lvs.sort_order)

        # FAST MODE
        self.assertEqual((field_name2, 'cremeentity_ptr_id'),
                         lvs.set_sort(model=FakeActivity, cells=cells, cell_key=key, order='', fast_mode=True)
                        )

    def test_sort_twoordersdesc_01(self):
        "meta.ordering: 2 fields (one is DESC)"
        field_name1 = 'name'
        field_name2 = 'expiration_date'
        self.assertEqual((field_name1, '-' + field_name2), FakeInvoice._meta.ordering)

        build_cell = partial(EntityCellRegularField.build, model=FakeInvoice)
        cells = [build_cell(name=field_name1),
                 build_cell(name=field_name2),
                ]

        lvs = ListViewState()
        key = cells[0].key
        ordering = lvs.set_sort(model=FakeInvoice, cells=cells, cell_key=key, order='')
        self.assertEqual((field_name1, '-' + field_name2, 'cremeentity_ptr_id'), ordering)
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('', lvs.sort_order)

        # DESC -----------------------------
        ordering = lvs.set_sort(model=FakeInvoice, cells=cells, cell_key=key, order='-')
        self.assertEqual(('-' + field_name1, field_name2, '-cremeentity_ptr_id'), ordering)
        self.assertEqual(key, lvs.sort_field)
        self.assertEqual('-', lvs.sort_order)

    # TODO: test handle_research() + get_q_with_research()
