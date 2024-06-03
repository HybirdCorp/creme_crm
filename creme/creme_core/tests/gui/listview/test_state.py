from django.test import RequestFactory

from creme.creme_core.gui.listview import ListViewState
from creme.creme_core.models import FakeContact
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

    def _build_request(self):
        url = self.url
        request = self.factory.get(url)
        request.path = url
        request.user = self.user
        request.session = {}

        return request

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
