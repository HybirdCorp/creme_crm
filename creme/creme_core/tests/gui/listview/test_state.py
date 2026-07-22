from django.contrib.contenttypes.models import ContentType
from django.http import QueryDict
from django.test import RequestFactory

from creme.creme_core.gui.listview import (
    ListViewState,
    NoHeaderFilterAvailable,
)
from creme.creme_core.models import FakeContact, FakeProduct
from creme.creme_core.models.entity_filter import (
    EntityFilter,
    EntityFilterList,
)
from creme.creme_core.models.header_filter import (
    HeaderFilter,
    HeaderFilterList,
)
from creme.creme_core.tests.base import CremeTestCase


class ListViewStateTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.factory = RequestFactory()
        cls.user = cls.build_user()
        cls.url = FakeContact.get_lv_absolute_url()

    def _assertLVSEmpty(self, lvs):
        self.assertIsNone(lvs.entity_filter_id)
        self.assertIsNone(lvs.header_filter_id)
        self.assertIsNone(lvs.page)
        self.assertIsNone(lvs.rows)
        self.assertIsNone(lvs.sort_order)
        self.assertIsNone(lvs.sort_cell_key)
        self.assertEqual({}, lvs.search)

    def _build_request(self, method='GET', **kwargs):
        url = self.url
        request = self.factory.get(url) if method == 'GET' else self.factory.post(url)
        request.path = url
        request.user = self.user
        request.session = {}

        query = QueryDict(
            query_string='&'.join(
                f'{arg_name}={arg_value}'
                for arg_name, arg_value in kwargs.items()
            ),
        )
        if method == 'GET':
            request.GET = query
        else:
            request.POST = query

        return request

    def test_init(self):
        lvs = ListViewState()
        self._assertLVSEmpty(lvs)
        self.assertIsNone(lvs.url)

    def test_get_state__empty(self):
        request = self._build_request()

        lvs = ListViewState.get_state(request)
        self.assertIsNone(lvs)

    def test_get_state(self):
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

    def test_get_or_create_state__GET(self):
        page = '3'
        request1 = self._build_request(page=page)
        url = self.url

        lvs1 = ListViewState.get_or_create_state(request=request1, url=url)
        self.assertIsInstance(lvs1, ListViewState)
        self.assertEqual(url, lvs1.url)
        self.assertEqual(page, lvs1.page)

        # ---
        request2 = self._build_request()
        lvs1.register_in_session(request2)

        lvs2 = ListViewState.get_or_create_state(request=request2, url=url)
        self.assertIsInstance(lvs2, ListViewState)
        self.assertEqual(url, lvs2.url)
        self.assertEqual(page, lvs2.page)

    def test_get_or_create_state__POST(self):
        page = '4'
        rows = '100'
        request1 = self._build_request(method='POST', page=page, rows=rows)
        url = self.url

        lvs1 = ListViewState.get_or_create_state(request=request1, url=url)
        self.assertIsInstance(lvs1, ListViewState)
        self.assertEqual(url, lvs1.url)
        self.assertEqual(page, lvs1.page)
        self.assertEqual(rows, lvs1.rows)

        # ---
        request2 = self._build_request()
        lvs1.register_in_session(request2)

        lvs2 = ListViewState.get_or_create_state(request=request2, url=url)
        self.assertIsInstance(lvs2, ListViewState)
        self.assertEqual(url, lvs2.url)
        self.assertEqual(page, lvs2.page)
        self.assertEqual(rows, lvs2.rows)

    def test_set_headerfilter(self):
        hf1 = HeaderFilter.objects.proxy(
            id='test-lvs1', model=FakeContact, name='Other HF', cells=[],
        ).get_or_create()[0]
        hf2 = HeaderFilter.objects.proxy(
            id='test-lvs2', model=FakeContact, name='Yet another HF', cells=[],
        ).get_or_create()[0]

        hfl = HeaderFilterList(
            content_type=ContentType.objects.get_for_model(FakeContact),
            user=self.get_root_user(),
        )

        request = self._build_request(method='GET', hfilter=hf1.id)

        lvs = ListViewState.build_from_request(request.GET, request.path)
        self.assertEqual(hf1.id, lvs.header_filter_id)

        found_hf1 = lvs.set_headerfilter(header_filters=hfl)
        self.assertEqual(hf1, found_hf1)
        self.assertEqual(hf1.id, lvs.header_filter_id)
        self.assertEqual(hf1, hfl.selected)

        # ---
        found_hf2 = lvs.set_headerfilter(header_filters=hfl, id=hf2.id)
        self.assertEqual(hf2, found_hf2)
        self.assertEqual(hf2.id, lvs.header_filter_id)
        self.assertEqual(hf2, hfl.selected)

        # Falls back on stored ids
        found_hf3 = lvs.set_headerfilter(header_filters=hfl, id='doesnotexist')
        self.assertEqual(hf2, found_hf3)

        # Falls back on stored ids before default ID
        found_hf4 = lvs.set_headerfilter(
            header_filters=hfl, id='doesnotexist', default_id=hf1,
        )
        self.assertEqual(hf2, found_hf4)

    def test_set_headerfilter__default(self):
        hf = HeaderFilter.objects.proxy(
            id='test-lvs1', model=FakeContact, name='Other HF', cells=[],
        ).get_or_create()[0]

        hfl = HeaderFilterList(
            content_type=ContentType.objects.get_for_model(FakeContact),
            user=self.get_root_user(),
        )

        request = self._build_request(method='GET')  # hfilter=hf.id

        lvs = ListViewState.build_from_request(request.GET, request.path)
        self.assertIsNone(lvs.header_filter_id)

        found_hf = lvs.set_headerfilter(header_filters=hfl, default_id=hf.id)
        self.assertEqual(hf, found_hf)
        self.assertEqual(hf.id, lvs.header_filter_id)

    def test_set_headerfilter__no_available(self):
        ct = ContentType.objects.get_for_model(FakeProduct)
        self.assertFalse(HeaderFilter.objects.filter(entity_type=ct))

        hfl = HeaderFilterList(content_type=ct, user=self.get_root_user())
        request = self._build_request(method='GET')
        lvs = ListViewState.build_from_request(request.GET, request.path)

        with self.assertRaises(NoHeaderFilterAvailable):
            lvs.set_headerfilter(header_filters=hfl)

    def test_set_entityfilter(self):
        model = FakeContact
        user = self.get_root_user()
        efilter1 = EntityFilter.objects.smart_update_or_create(
            pk='test-nerds', name='Nerds', model=model, user=user, is_custom=True,
        )
        efilter2 = EntityFilter.objects.smart_update_or_create(
            pk='test-weebs', name='Weebs', model=model, user=user, is_custom=True,
        )

        efl = EntityFilterList(
            content_type=ContentType.objects.get_for_model(model), user=user,
        )

        request = self._build_request(method='GET', filter=efilter1.id)

        lvs = ListViewState.build_from_request(request.GET, request.path)
        self.assertEqual(efilter1.id, lvs.entity_filter_id)

        found_ef1 = lvs.set_entityfilter(entity_filters=efl, filter_id=efilter2.id)
        self.assertEqual(efilter2, found_ef1)
        self.assertEqual(efilter2.id, lvs.entity_filter_id)
        self.assertEqual(efilter2, efl.selected)

        # Falls back on stored ids
        found_ef2 = lvs.set_entityfilter(entity_filters=efl, filter_id='unknown')
        self.assertEqual(efilter2, found_ef2)
        self.assertEqual(efilter2.id, lvs.entity_filter_id)

        # Falls back on stored ids before default ID
        found_ef3 = lvs.set_entityfilter(
            entity_filters=efl, filter_id='unknown', default_id=efilter1.id,
        )
        self.assertEqual(efilter2, found_ef3)

    def test_set_entityfilter__default(self):
        model = FakeContact
        user = self.get_root_user()
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-nerds', name='Nerds', model=model, user=user, is_custom=True,
        )

        efl = EntityFilterList(
            content_type=ContentType.objects.get_for_model(model), user=user,
        )

        request = self._build_request(method='GET')  # filter=efilter.id

        lvs = ListViewState.build_from_request(request.GET, request.path)
        self.assertIsNone(lvs.entity_filter_id)

        found_ef = lvs.set_entityfilter(
            entity_filters=efl, filter_id='doesnotexist', default_id=efilter.id,
        )
        self.assertEqual(efilter, found_ef)

    def test_set_entityfilter__clear(self):
        model = FakeContact
        user = self.get_root_user()
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-nerds', name='Nerds', model=model, user=user, is_custom=True,
        )

        efl = EntityFilterList(
            content_type=ContentType.objects.get_for_model(model), user=user,
        )

        request = self._build_request(method='GET', filter=efilter.id)
        lvs = ListViewState.build_from_request(request.GET, request.path)

        found_ef = lvs.set_entityfilter(
            entity_filters=efl, filter_id='', default_id=efilter.id,
        )
        self.assertIsNone(found_ef)
        self.assertIsNone(efl.selected)
