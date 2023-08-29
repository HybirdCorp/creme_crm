import json
from urllib.parse import urlencode

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.urls import reverse

from creme.creme_core.gui.visit import EntityVisitor
from creme.creme_core.models import FakeContact, FakeOrganisation
from creme.creme_core.utils.queries import QSerializer

from .. import fake_constants
from ..base import CremeTestCase


class VisitTestCase(CremeTestCase):
    @staticmethod
    def _build_visit_uri(model, page=None, lv_url='', **kwargs):
        kwargs['callback'] = lv_url or model.get_lv_absolute_url()

        if page:
            kwargs['page'] = json.dumps(page)

        url = reverse(
            'creme_core__visit_next_entity',
            args=(ContentType.objects.get_for_model(model).id,),
        )

        return f'{url}?{urlencode(kwargs)}'

    def test_visitor_init01(self):
        sort = 'regular_field-last_name'
        hfilter_id = fake_constants.DEFAULT_HFILTER_FAKE_CONTACT
        visitor = EntityVisitor(
            model=FakeContact, sort=sort, hfilter_id=hfilter_id,
        )
        self.assertEqual(FakeContact, visitor.model)
        self.assertEqual(sort,        visitor.sort)
        self.assertEqual(hfilter_id,  visitor.hfilter_id)
        self.assertIsNone(visitor.efilter_id)
        self.assertEqual('', visitor.serialized_internal_q)
        self.assertEqual('', visitor.serialized_requested_q)
        self.assertIsNone(visitor.search_dict)
        self.assertIsNone(visitor.page_info)
        self.assertIsNone(visitor.index)
        self.assertURLEqual(FakeContact.get_lv_absolute_url(), visitor.callback_url)

        self.assertURLEqual(
            self._build_visit_uri(FakeContact, sort=sort, hfilter=hfilter_id),
            visitor.uri,
        )

    def test_visitor_init02(self):
        sort = '-regular_field-name'
        hfilter_id = fake_constants.DEFAULT_HFILTER_FAKE_ORGA
        efilter_id = 'creme_core-whatever'
        search_dict = {'search-phone': '11'}
        page_info = {'type': 'last'}
        lv_url = reverse('creme_core__list_fake_organisations_with_email')

        dump_q = QSerializer().dumps
        s_internal_q = dump_q(Q(name__startswith='Acme'))
        s_requested_q = dump_q(Q(phone__startswith='07'))

        visitor = EntityVisitor(
            model=FakeOrganisation, sort=sort, hfilter_id=hfilter_id,
            efilter_id=efilter_id,
            internal_q=s_internal_q,
            requested_q=s_requested_q,
            search_dict=search_dict,
            page_info=page_info,
            index=2,
            callback_url=lv_url,
        )
        self.assertEqual(FakeOrganisation, visitor.model)
        self.assertEqual(sort,             visitor.sort)
        self.assertEqual(hfilter_id,       visitor.hfilter_id)
        self.assertEqual(efilter_id,       visitor.efilter_id)
        self.assertEqual(s_internal_q,     visitor.serialized_internal_q)
        self.assertEqual(s_requested_q,    visitor.serialized_requested_q)
        self.assertEqual(search_dict,      visitor.search_dict)
        self.assertEqual(page_info,        visitor.page_info)
        self.assertEqual(2,                visitor.index)
        self.assertEqual(lv_url,           visitor.callback_url)

        self.maxDiff = None
        self.assertURLEqual(
            self._build_visit_uri(
                FakeOrganisation,
                sort=sort, hfilter=hfilter_id,
                efilter=efilter_id,
                internal_q=s_internal_q,
                requested_q=s_requested_q,
                page=page_info,
                index=2,
                lv_url=lv_url,
                **search_dict
            ),
            visitor.uri,
        )

    def test_visitor_init03(self):
        "Q instance."
        internal_q = Q(name__startswith='Acme')
        requested_q = Q(phone__startswith='08')
        visitor = EntityVisitor(
            model=FakeOrganisation,
            sort='-regular_field-name',
            hfilter_id=fake_constants.DEFAULT_HFILTER_FAKE_ORGA,
            internal_q=internal_q,
            requested_q=requested_q,
        )
        dump_q = QSerializer().dumps
        self.assertEqual(dump_q(internal_q),  visitor.serialized_internal_q)
        self.assertEqual(dump_q(requested_q), visitor.serialized_requested_q)

    def test_visitor_init_errors(self):
        "Page-info & index must be both given or both ignored."
        sort = 'regular_field-last_name'
        hfilter_id = fake_constants.DEFAULT_HFILTER_FAKE_CONTACT

        with self.assertRaises(EntityVisitor.Error) as cm1:
            EntityVisitor(
                model=FakeContact, sort=sort, hfilter_id=hfilter_id,
                index=1,  # Not page_info
            )
        self.assertEqual(
            'Arguments "index" & "page_info" must be both given or both ignored',
            str(cm1.exception),
        )

        with self.assertRaises(EntityVisitor.Error):
            EntityVisitor(
                model=FakeContact, sort=sort, hfilter_id=hfilter_id,
                page_info={'type': 'last'},   # Not index
            )

    def test_visitor_from_json01(self):
        lv_url = reverse('creme_core__list_fake_organisations_with_email')
        sort = '-regular_field-name'
        hfilter_id = fake_constants.DEFAULT_HFILTER_FAKE_ORGA
        efilter_id = 'creme_core-whatever'
        search_dict = {'search-phone': '11'}
        page_info = {'type': 'last'}

        dump_q = QSerializer().dumps
        s_internal_q = dump_q(Q(name__startswith='Acme'))
        s_requested_q = dump_q(Q(phone__startswith='06'))

        json_data = json.dumps({
            'callback': lv_url,
            'sort': sort,
            'hfilter': hfilter_id,
            'efilter': efilter_id,
            'internal_q': s_internal_q,
            'requested_q': s_requested_q,
            'search': search_dict,
            'page': page_info,
            'index': 1,
        })

        with self.assertNoException():
            visitor = EntityVisitor.from_json(FakeOrganisation, json_data)

        self.assertEqual(FakeOrganisation, visitor.model)
        self.assertEqual(lv_url,           visitor.callback_url)
        self.assertEqual(sort,             visitor.sort)
        self.assertEqual(hfilter_id,       visitor.hfilter_id)
        self.assertEqual(efilter_id,       visitor.efilter_id)
        self.assertEqual(s_internal_q,     visitor.serialized_internal_q)
        self.assertEqual(s_requested_q,    visitor.serialized_requested_q)
        self.assertEqual(search_dict,      visitor.search_dict)
        self.assertEqual(page_info,        visitor.page_info)
        self.assertEqual(1,                visitor.index)

    def test_visitor_from_json02(self):
        lv_url = FakeOrganisation.get_lv_absolute_url()
        sort = '-regular_field-name'
        hfilter_id = fake_constants.DEFAULT_HFILTER_FAKE_ORGA

        json_data = json.dumps({
            'callback': lv_url,
            'sort': sort,
            'hfilter': hfilter_id,
        })

        with self.assertNoException():
            visitor = EntityVisitor.from_json(FakeOrganisation, json_data)

        self.assertEqual(FakeOrganisation,   visitor.model)
        self.assertEqual(sort,               visitor.sort)
        self.assertEqual(hfilter_id,         visitor.hfilter_id)

        self.assertIsNone(visitor.efilter_id)
        self.assertEqual('', visitor.serialized_internal_q)
        self.assertEqual('', visitor.serialized_requested_q)
        self.assertIsNone(visitor.search_dict)
        self.assertIsNone(visitor.page_info)
        self.assertIsNone(visitor.index)

    def test_visitor_from_json_errors01(self):
        with self.assertRaises(EntityVisitor.Error):
            EntityVisitor.from_json(FakeOrganisation, '{')

        # ---
        with self.assertRaises(EntityVisitor.Error) as cm2:
            EntityVisitor.from_json(FakeOrganisation, '[]')

        self.assertEqual(
            'Data must be a dictionary',
            str(cm2.exception),
        )

    def test_visitor_from_json_errors02(self):
        sort = '-regular_field-name'
        hfilter_id = fake_constants.DEFAULT_HFILTER_FAKE_ORGA
        efilter_id = 'creme_core-whatever'
        serialized_extra_q = QSerializer().dumps(Q(name__startswith='Acme'))
        search_dict = {'search-phone': '11'}
        page_info = {'type': 'last'}

        data = {
            'callback': FakeOrganisation.get_lv_absolute_url(),
            'sort': sort,
            'hfilter': hfilter_id,
            'efilter': efilter_id,
            'extra_q': serialized_extra_q,
            'search': search_dict,
            'page': page_info,
            'index': 1,
        }

        with self.assertNoException():
            EntityVisitor.from_json(FakeOrganisation, json.dumps(data))

        def no_key(d, key):
            return {k: v for k, v in d.items() if k != key}

        # ---
        with self.assertRaises(EntityVisitor.Error) as cm1:
            EntityVisitor.from_json(
                FakeOrganisation,
                json.dumps(no_key(data, 'hfilter'))
            )
        self.assertIn('"hfilter"', str(cm1.exception))

        with self.assertRaises(EntityVisitor.Error) as cm2:
            EntityVisitor.from_json(
                FakeOrganisation,
                json.dumps({**data, 'hfilter': 1})
            )
        self.assertIn('The value for "hfilter" must be a str', str(cm2.exception))

        # ---
        with self.assertRaises(EntityVisitor.Error) as cm3:
            EntityVisitor.from_json(
                FakeOrganisation,
                json.dumps(no_key(data, 'sort'))
            )
        self.assertIn('"sort"', str(cm3.exception))

        with self.assertRaises(EntityVisitor.Error) as cm4:
            EntityVisitor.from_json(
                FakeOrganisation,
                json.dumps({**data, 'sort': 1})
            )
        self.assertIn('The value for "sort" must be a str', str(cm4.exception))

        # ---
        with self.assertRaises(EntityVisitor.Error):
            EntityVisitor.from_json(
                FakeOrganisation,
                json.dumps({**data, 'efilter': 1})
            )

        # ---
        with self.assertRaises(EntityVisitor.Error) as cm5:
            EntityVisitor.from_json(
                FakeOrganisation,
                json.dumps({**data, 'search': 1})
            )
        self.assertIn('The value for "search" must be a dict', str(cm5.exception))

        # ---
        with self.assertRaises(EntityVisitor.Error):
            EntityVisitor.from_json(
                FakeOrganisation,
                json.dumps({**data, 'page': 1})
            )

        # ---
        with self.assertRaises(EntityVisitor.Error) as cm6:
            EntityVisitor.from_json(
                FakeOrganisation,
                json.dumps(no_key(data, 'callback'))
            )
        self.assertIn('"callback"', str(cm6.exception))

    def test_visitor_to_json01(self):
        sort = 'regular_field-name'
        hfilter_id = fake_constants.DEFAULT_HFILTER_FAKE_ORGA
        page_info = {'type': 'last'}
        visitor = EntityVisitor(
            model=FakeOrganisation, sort=sort, hfilter_id=hfilter_id,
            page_info=page_info,
            index=1,
        )
        self.assertJSONEqual(
            json.dumps({
                'hfilter': hfilter_id,
                'sort': sort,
                'index': 1,
                'page': page_info,
                'callback': FakeOrganisation.get_lv_absolute_url(),
            }),
            visitor.to_json(),
        )

    def test_visitor_to_json02(self):
        lv_url = reverse('creme_core__list_fake_organisations_with_email')
        sort = '-regular_field-email'
        hfilter_id = fake_constants.DEFAULT_HFILTER_FAKE_CONTACT
        efilter_id = 'creme_core-whatever'
        internal_q = Q(last_name__startswith='Spieg')
        requested_q = Q(first_name__startswith='Spik')
        search_dict = {'search-first_name': 'Jet'}
        visitor = EntityVisitor(
            model=FakeContact, sort=sort, hfilter_id=hfilter_id,
            efilter_id=efilter_id,
            internal_q=internal_q,
            requested_q=requested_q,
            search_dict=search_dict,
            callback_url=lv_url,
        )
        dump_q = QSerializer().dumps
        self.assertJSONEqual(
            json.dumps({
                'hfilter': hfilter_id,
                'sort': sort,
                'efilter': efilter_id,
                'search': search_dict,
                'internal_q': dump_q(internal_q),
                'requested_q': dump_q(requested_q),
                'callback': lv_url,
            }),
            visitor.to_json(),
        )
