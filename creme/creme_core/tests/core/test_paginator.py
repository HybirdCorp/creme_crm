# -*- coding: utf-8 -*-

from collections import OrderedDict
from datetime import date
from functools import partial
from random import shuffle

from django.core.exceptions import FieldDoesNotExist

from creme.creme_core.core.paginator import (
    FirstPage,
    FlowPaginator,
    InvalidPage,
    LastPage,
)
from creme.creme_core.models import UserRole
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_models import (
    FakeContact,
    FakeDocument,
    FakeFolder,
    FakeFolderCategory,
    FakeInvoice,
    FakeInvoiceLine,
    FakeOrganisation,
    FakeSector,
)
from creme.creme_core.utils.profiling import CaptureQueriesContext


class FlowPaginatorTestCase(CremeTestCase):
    # Build by setUpClass. Sequence of tuples (order, first_name, last_name)
    # 'order' is the 1-based-index of data sorted by last_name.
    CONTACTS_DATA = ()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        all_names = [
            ('Rei',     'Ichido'),
            ('Gô',      'Reietsu'),
            ('Jin',     'Daima'),
            ('Kiyoshi', 'Shusse'),
            ('Dai',     'Monohoshi'),
            ('Yui',     'Kawa'),
            ('Chie',    'Uru'),
        ]

        names_orders_map = OrderedDict((n, None) for n in all_names)
        all_names.sort(key=lambda t: t[1])

        for order, names in enumerate(all_names, start=1):
            names_orders_map[names] = order

        cls.CONTACTS_DATA = [
            (order, names[0], names[1])
            for names, order in names_orders_map.items()
        ]

    def setUp(self):
        super().setUp()
        self.login()

        self.assertIsNone(FakeContact.objects.first())

    @staticmethod
    def _get_sql(queryset):
        return queryset.query.get_compiler('default').as_sql()[0]

    @staticmethod
    def _qs_2_shuffled_list(qs):
        items = [*qs]
        shuffle(items)

        return items

    def _add_birthdays(self, count=None):
        qs = FakeContact.objects.all()

        if count:
            qs = qs[:count]

        # Notice that there are less than 12 contacts.
        for month, contact in enumerate(self._qs_2_shuffled_list(qs), start=1):
            contact.birthday = date(year=1981, month=month, day=12)
            contact.save()

    def _build_contacts(self, **counts):
        create_contact = partial(FakeContact.objects.create, user=self.user)

        for c_id, first_name, last_name in self.CONTACTS_DATA:
            for _i in range(counts.get(f'c{c_id}', 1)):
                create_contact(first_name=first_name, last_name=last_name)

    def test_all(self):
        self._build_contacts()
        contacts = FakeContact.objects.all()
        count = FakeContact.objects.count()
        self.assertIn(count, {7, 8})

        per_page = 3

        with self.assertNumQueries(0):
            paginator = FlowPaginator(
                contacts, key='last_name', per_page=per_page, count=count,
            )

        self.assertEqual(count, paginator.count)
        self.assertEqual(per_page, paginator.per_page)
        self.assertEqual(3, paginator.num_pages)

        with self.assertNumQueries(1):
            page = paginator.page()

        self.assertEqual(paginator, page.paginator)

        with self.assertNumQueries(0):
            entities = [*page.object_list]

        self.assertEqual([*contacts][:3], entities)

        self.assertEqual(per_page, len(page))
        self.assertIs(page.has_next(), True)
        self.assertIs(page.has_previous(), False)
        self.assertIs(page.has_other_pages(), True)

    def test_num_pages(self):
        self._build_contacts()
        contacts = FakeContact.objects.all()

        count = FakeContact.objects.count()
        self.assertIn(count, {7, 8})

        per_page = 4

        paginator = FlowPaginator(
            contacts, key='last_name', per_page=per_page, count=count,
        )

        with self.assertNumQueries(0):
            num_pages = paginator.num_pages

        self.assertEqual(2, num_pages)

    def test_get_item(self):
        self._build_contacts()

        contacts = FakeContact.objects.all()
        paginator = FlowPaginator(
            contacts.all(), key='last_name', per_page=3, count=len(contacts),
        )
        page = paginator.page()

        self.assertEqual(contacts[0], page[0])
        with self.assertNumQueries(0):
            page[0]  # NOQA

        with self.assertNumQueries(0):
            c = page[1]
        self.assertEqual(contacts[1], c)

        self.assertEqual(contacts[2], page[-1])

        with self.assertRaises(TypeError):
            page['notint']  # NOQA

        self.assertListEqual([contacts[1], contacts[2]], page[1:])
        self.assertListEqual([contacts[1], contacts[2]], page[1:3])

    def test_one_page(self):
        self._build_contacts()

        contacts = FakeContact.objects.all()
        count = len(contacts)
        paginator = FlowPaginator(contacts, key='last_name', per_page=count, count=count)

        page = paginator.page()
        self.assertIs(page.has_next(), False)
        self.assertIs(page.has_previous(), False)
        self.assertIs(page.has_other_pages(), False)

        self.assertIsNone(page.next_page_info())

    def test_invalid_paginator(self):
        contacts = FakeContact.objects.all()
        count = len(contacts)

        with self.assertRaises(TypeError):
            FlowPaginator(contacts, key='last_name', per_page='notint', count=count)

        with self.assertRaises(ValueError):
            FlowPaginator(contacts, key='last_name', per_page=2, count='notint')

        with self.assertRaises(FieldDoesNotExist):
            FlowPaginator(contacts, key='invalid', per_page=2, count=count)

        # ManyToManyFields cannot be used as key
        with self.assertRaises(ValueError):
            FlowPaginator(contacts, key='languages', per_page=2, count=count)

        with self.assertRaises(ValueError):
            FlowPaginator(contacts, key='languages__name', per_page=2, count=count)

        # No ordering
        self.assertFalse(UserRole._meta.ordering)
        with self.assertRaises(ValueError):
            FlowPaginator(contacts, key='user__role', per_page=2, count=count)

    def test_invalid_page_info01(self):
        self._build_contacts()

        contacts = FakeContact.objects.all()
        paginator = FlowPaginator(contacts, key='last_name', per_page=2, count=len(contacts))
        page = paginator.page()
        info = page.next_page_info()

        with self.assertRaises(InvalidPage):
            paginator.page({**info, 'type': 'invalid'})

        # No type -----
        info_tmp = {**info}
        del info_tmp['type']

        with self.assertRaises(InvalidPage):
            paginator.page(info_tmp)

        # Invalid offset --------------
        with self.assertRaises(InvalidPage):
            paginator.page({**info, 'offset': 'notint'})

        with self.assertRaises(InvalidPage):
            paginator.page({**info, 'offset': '-2'})

        # Key --------------
        info_tmp = {**info}
        del info_tmp['key']

        with self.assertRaises(InvalidPage):
            paginator.page(info_tmp)

        # Key is different from paginator's one
        with self.assertRaises(InvalidPage):
            paginator.page({**info, 'key': 'first_name'})

        with self.assertRaises(InvalidPage):
            paginator.page({**info, 'key': '-last_name'})

    def test_invalid_page_info02(self):
        "Last page: key is different from paginator's one."
        self._build_contacts()

        contacts = FakeContact.objects.all()
        paginator = FlowPaginator(contacts, key='last_name', per_page=2, count=len(contacts))
        page = paginator.last_page()
        info = page.info()

        with self.assertRaises(InvalidPage):
            paginator.page({**info, 'key': 'first_name'})

    def test_invalid_page_info03(self):
        "Invalid date value."
        self._build_contacts()

        contacts = FakeContact.objects.all()
        paginator = FlowPaginator(
            contacts, key='birthday', per_page=2, count=len(contacts),
        )
        info = paginator.page().next_page_info()
        self.assertIn('value', info)

        info['value'] = 'not a date'
        with self.assertRaises(InvalidPage):
            paginator.page(info)

        with self.assertRaises(InvalidPage):
            paginator.page({**info, 'type': 'backward'})

    def test_invalid_page_info04(self):
        "Invalid integer value."
        create_orga = partial(FakeOrganisation.objects.create, user=self.user)

        for i in range(1, 4):
            create_orga(name=f'High school#{i}')

        orgas = FakeOrganisation.objects.all()
        paginator = FlowPaginator(orgas, key='capital', per_page=2, count=len(orgas))
        info = paginator.page().next_page_info()
        self.assertIn('value', info)

        info['value'] = 'not an int'
        with self.assertRaises(InvalidPage):
            paginator.page(info)

        with self.assertRaises(InvalidPage):
            paginator.page({**info, 'type': 'backward'})

    def test_next_page01(self):
        self._build_contacts()

        contacts = FakeContact.objects.all()
        paginator = FlowPaginator(
            contacts.all(), key='last_name', per_page=2, count=len(contacts),
        )
        page = paginator.page()
        self.assertListEqual([contacts[0], contacts[1]], [*page.object_list])
        self.assertTrue(page.has_next())
        self.assertFalse(page.has_previous())

        with self.assertNumQueries(0):
            info = page.next_page_info()

        self.assertEqual(
            {
                'type': 'forward',
                'key': 'last_name',
                'value': contacts[2].last_name,
            },
            info,
        )

        # Page 2
        page = paginator.page(info)
        self.assertListEqual([contacts[2], contacts[3]], [*page.object_list])
        self.assertTrue(page.has_next())
        self.assertTrue(page.has_previous())
        self.assertDictEqual(
            {
                'type': 'forward',
                'key': 'last_name',
                'value': contacts[4].last_name,
            },
            page.next_page_info(),
        )

    def test_next_page02(self):
        "Other key."
        self._build_contacts()

        key = 'first_name'
        contacts = FakeContact.objects.order_by(key)
        paginator = FlowPaginator(contacts.all(), key=key, per_page=2, count=len(contacts))
        page = paginator.page()
        self.assertDictEqual(
            {
                'type': 'forward',
                'key': key,
                'value': contacts[2].first_name,
            },
            page.next_page_info(),
        )

    def test_next_page03(self):
        "OFFSET."
        self._build_contacts(c2=3)  # We create some duplicates

        qs = FakeContact.objects.order_by('last_name', 'id')
        contacts = [*qs]
        self.assertEqual(contacts[1].last_name, contacts[2].last_name)
        self.assertEqual(contacts[1].last_name, contacts[3].last_name)

        paginator = FlowPaginator(qs, key='last_name', per_page=3, count=len(contacts))
        page = paginator.page()
        self.assertListEqual(contacts[:3], [*page.object_list])
        self.assertTrue(page.has_next())
        self.assertFalse(page.has_previous())

        info = page.next_page_info()
        self.assertDictEqual(
            {
                'type': 'forward',
                'key': 'last_name',
                'value': contacts[1].last_name,
                'offset': 2,
            },
            info,
        )

        # ------------
        page = paginator.page(info)
        self.assertListEqual(contacts[3:6], [*page.object_list])
        self.assertDictEqual(
            {
                'type': 'forward',
                'key': 'last_name',
                'value': contacts[6].last_name,
            },
            page.next_page_info(),
        )

    def test_next_page04(self):
        "Cumulate OFFSET (many duplicates)."
        # We create 7 duplicates => a page with only duplicates => cumulate the offsets
        self._build_contacts(c2=7)

        qs = FakeContact.objects.order_by('last_name', 'id')
        contacts = [*qs]
        paginator = FlowPaginator(qs, key='last_name', per_page=3, count=len(contacts))

        # Page 2
        info1 = paginator.page().next_page_info()
        page2 = paginator.page(info1)
        self.assertListEqual(contacts[3:6], [*page2.object_list])

        with self.assertNumQueries(0):
            info2 = page2.next_page_info()

        self.assertDictEqual(
            {
                'type': 'forward',
                'key': 'last_name',
                'value': contacts[6].last_name,
                'offset': 5,  # 2 + 3
            },
            info2,
        )

        # Page 3: no duplicates anymore => offset = 0
        page3 = paginator.page(info2)
        self.assertListEqual(contacts[6:9], [*page3.object_list])
        self.assertDictEqual(
            {
                'type': 'forward',
                'key': 'last_name',
                'value': contacts[9].last_name,
                # 'offset': 0,
            },
            page3.next_page_info(),
        )

    def test_last_page01(self):
        self._build_contacts()

        contacts = FakeContact.objects.all()
        count = len(contacts)
        paginator = FlowPaginator(contacts, key='last_name', per_page=2, count=count)

        page = paginator.page({
            'type': 'forward',
            'key': 'last_name',
            'value': contacts[count - 2].last_name,
        })
        self.assertEqual(2, len(page))

        self.assertIs(page.has_next(), False)
        self.assertIs(page.has_previous(), True)
        self.assertIs(page.has_other_pages(), True)

    def test_last_page02(self):
        "Go directly to the last page."
        self._build_contacts()

        qs = FakeContact.objects.all()
        contacts = [*qs]
        paginator = FlowPaginator(qs, key='last_name', per_page=3, count=7)
        page = paginator.last_page()

        self.assertFalse(page.has_next())
        self.assertTrue(page.has_previous())
        self.assertListEqual(contacts[4:], [*page.object_list])
        self.assertDictEqual(
            {
                'type': 'backward',
                'key': 'last_name',
                'value': contacts[4].last_name,
            },
            page.previous_page_info(),
        )

    def test_last_page03(self):
        "Go directly to the last page, but it is the only page."
        create_contact = partial(FakeContact.objects.create, user=self.user)
        contacts = [
            create_contact(first_name='Rei', last_name='Ichido'),
            create_contact(first_name='Yui', last_name='Kawa'),
        ]

        paginator = FlowPaginator(FakeContact.objects.all(), key='last_name', per_page=2, count=2)
        page = paginator.last_page()
        self.assertFalse(page.has_next())
        self.assertFalse(page.has_previous())
        self.assertListEqual(contacts, [*page.object_list])

    def test_last_page04(self):
        """We delete the entities on the last pages when we are on the previous
         one => become the last page.
         """
        self._build_contacts()

        qs = FakeContact.objects.order_by('last_name', 'id')
        contacts = [*qs]

        paginator1 = FlowPaginator(qs.all(), key='last_name', per_page=3, count=7)
        page1 = paginator1.page()
        page2 = paginator1.page(page1.next_page_info())
        self.assertTrue(page2.has_next())

        info3 = page2.next_page_info()

        # We delete the content of the last page
        c = contacts[-1]
        c.delete()
        self.assertEqual(6, qs.all().count())

        # We simulate a request to go to the next page, which does not exist anymore
        paginator2 = FlowPaginator(qs.all(), key='last_name', per_page=3, count=6)

        with self.assertRaises(LastPage):
            paginator2.page(info3)

    def test_no_offset(self):
        self._build_contacts()

        contacts = FakeContact.objects.all()
        count = len(contacts)
        paginator = FlowPaginator(contacts, key='last_name', per_page=2, count=count)
        info = paginator.page().next_page_info()

        context = CaptureQueriesContext()

        with context:
            paginator.page(info)

        queries = context.captured_sql
        self.assertEqual(1, len(queries))
        self.assertNotIn('OFFSET', queries[0])

    def test_previous_page01(self):
        self._build_contacts()

        contacts = FakeContact.objects.all()
        paginator = FlowPaginator(contacts.all(), key='last_name', per_page=2, count=len(contacts))
        page1 = paginator.page()
        self.assertIsNone(page1.previous_page_info())

        # Page 2
        page2 = paginator.page(page1.next_page_info())
        self.assertDictEqual(
            {
                'type': 'backward',
                'key': 'last_name',
                'value': contacts[2].last_name,
            },
            page2.previous_page_info(),
        )

        # Page 3
        page3 = paginator.page(page2.next_page_info())
        info2a = page3.previous_page_info()
        self.assertDictEqual(
            {
                'type': 'backward',
                'key': 'last_name',
                'value': contacts[4].last_name,
            },
            info2a,
        )

        # Page 2 again
        paginator = FlowPaginator(contacts.all(), key='last_name', per_page=2, count=len(contacts))
        page2a = paginator.page(info2a)
        self.assertListEqual([contacts[2], contacts[3]], [*page2a.object_list])
        self.assertTrue(page2a.has_next())
        self.assertTrue(page2a.has_previous())

        info1a = page2a.previous_page_info()
        self.assertDictEqual(
            {
                'type': 'backward',
                'key': 'last_name',
                'value': contacts[2].last_name,
            },
            info1a,
        )

        # Page 1 again
        with self.assertRaises(FirstPage):
            paginator.page(info1a)

    def test_previous_page02(self):
        "Other key + page 3 => page 2: beware to reverse slice."
        self._build_contacts()

        key = 'first_name'
        contacts = FakeContact.objects.order_by(key)
        paginator = FlowPaginator(contacts.all(), key=key, per_page=2, count=len(contacts))

        page1 = paginator.page()
        page2 = paginator.page(page1.next_page_info())
        page3 = paginator.page(page2.next_page_info())

        info = page3.previous_page_info()
        self.assertEqual(
            {
                'type': 'backward',
                'key': key,
                'value': contacts[4].first_name,
            },
            info,
        )

        # Page 2 again
        page2a = paginator.page(info)
        self.assertListEqual([contacts[2], contacts[3]], [*page2a.object_list])
        self.assertTrue(page2a.has_next())
        self.assertTrue(page2a.has_previous())

    def test_previous_page03(self):
        "OFFSET."
        self._build_contacts(c6=3)

        qs = FakeContact.objects.order_by('last_name', 'id')
        contacts = [*qs]
        paginator = FlowPaginator(qs, key='last_name', per_page=3, count=len(contacts))
        page1 = paginator.page()
        page2 = paginator.page(page1.next_page_info())
        page3 = paginator.page(page2.next_page_info())
        self.assertListEqual(contacts[6:9], [*page3.object_list])

        with self.assertNumQueries(0):
            info2a = page3.previous_page_info()

        self.assertDictEqual(
            {
                'type': 'backward',
                'key': 'last_name',
                'value': contacts[5].last_name,  # == contacts[6 7].last_name
                'offset': 1,
            },
            info2a,
        )

        page2a = paginator.page(info2a)
        self.assertListEqual(contacts[3:6], [*page2a.object_list])
        self.assertTrue(page2a.has_next())
        self.assertTrue(page2a.has_previous())

        # Page 1 again
        with self.assertRaises(FirstPage):
            paginator.page(page2a.previous_page_info())

    def test_previous_page04(self):
        "Compute big OFFSET (many duplicates)."
        # We create 6 duplicates => a page with only duplicates => compute the total offset
        self._build_contacts(c6=6)

        key = 'last_name'
        qs = FakeContact.objects.order_by(key, 'id')
        contacts = [*qs]
        paginator = FlowPaginator(qs, key=key, per_page=3, count=len(contacts))
        page1 = paginator.page()
        page2 = paginator.page(page1.next_page_info())
        page3 = paginator.page(page2.next_page_info())
        self.assertListEqual(contacts[6:9], [*page3.object_list])

        with self.assertNumQueries(1):
            info2a = page3.previous_page_info()

        with self.assertNumQueries(0):
            page3.previous_page_info()  # Cache query

        self.assertDictEqual(
            {
                'type': 'backward',
                'key': key,
                'value': contacts[5].last_name,  # == contacts[6 .. 10].last_name
                'offset': 4,
            },
            info2a,
        )

        page2a = paginator.page(info2a)
        self.assertListEqual(contacts[3:6], [*page2a.object_list])
        self.assertTrue(page2a.has_next())
        self.assertTrue(page2a.has_previous())

        # Page 1 again
        with self.assertRaises(FirstPage):
            paginator.page(page2a.previous_page_info())

    def test_previous_page05(self):
        "Cumulate OFFSETs."
        # We create 8 duplicates => 2 pages with only duplicates
        self._build_contacts(c6=8)

        qs = FakeContact.objects.order_by('last_name', 'id')
        contacts = [*qs]
        paginator = FlowPaginator(qs, key='last_name', per_page=3, count=len(contacts))
        page1 = paginator.page()
        page2 = paginator.page(page1.next_page_info())
        page3 = paginator.page(page2.next_page_info())
        page4 = paginator.page(page3.next_page_info())
        self.assertListEqual(contacts[9:12], [*page4.object_list])

        with self.assertNumQueries(1):
            info3a = page4.previous_page_info()

        self.assertDictEqual(
            {
                'type': 'backward',
                'key': 'last_name',
                'value': contacts[5].last_name,  # == contacts[6 .. 12].last_name
                'offset': 3,
            },
            info3a,
        )

        page3a = paginator.page(info3a)
        self.assertListEqual(contacts[6:9], [*page3a.object_list])
        self.assertTrue(page3a.has_next())
        self.assertTrue(page3a.has_previous())

        with self.assertNumQueries(0):
            info2a = page3a.previous_page_info()

        self.assertDictEqual(
            {
                'type': 'backward',
                'key': 'last_name',
                'value': contacts[5].last_name,  # Idem
                'offset': 6,
            },
            info2a,
        )

        page2a = paginator.page(info2a)
        self.assertListEqual(contacts[3:6], [*page2a.object_list])

    def test_previous_page06(self):
        """OFFSET is relative to a value => do not cumulate offset if their are
        related to different duplicates.
        """
        # We fill the second page with duplicates, and the 3rd too (but from another source)
        self._build_contacts(c4=3, c5=3, c6=3)

        qs = FakeContact.objects.order_by('last_name', 'id')
        contacts = [*qs]
        paginator = FlowPaginator(qs, key='last_name', per_page=3, count=len(contacts))
        page1 = paginator.page()
        page2 = paginator.page(page1.next_page_info())
        page3 = paginator.page(page2.next_page_info())
        page4 = paginator.page(page3.next_page_info())
        self.assertListEqual(contacts[9:12], [*page4.object_list])

        page3a = paginator.page(page4.previous_page_info())
        self.assertListEqual(contacts[6:9], [*page3a.object_list])

        info2a = page3a.previous_page_info()
        self.assertDictEqual(
            {
                'type': 'backward',
                'key': 'last_name',
                'value': contacts[6].last_name,
                'offset': 2,  # not 5 !
            },
            info2a,
        )

        page2a = paginator.page(info2a)
        self.assertListEqual(contacts[3:6], [*page2a.object_list])

    def test_previous_page07(self):
        "Duplicates at end + last_page => 0-__backward__-offset."
        last_name = 'Ichido'
        create_contact = partial(
            FakeContact.objects.create, user=self.user, last_name=last_name,
        )
        for i in range(1, 8):
            create_contact(first_name=f'Rei #{i}')

        key = 'last_name'
        qs = FakeContact.objects.order_by(key, 'id')
        contacts = [*qs]

        paginator = FlowPaginator(qs.all(), key=key, per_page=2, count=len(contacts))

        # Going from the first page
        page1 = paginator.page()
        page2 = paginator.page(page1.next_page_info())
        page3 = paginator.page(page2.next_page_info())
        self.assertListEqual(
            contacts[2:4],
            [*paginator.page(page3.previous_page_info()).object_list],
        )

        # Going from the last page
        last_page = paginator.last_page()
        self.assertListEqual(contacts[5:], [*last_page.object_list])

        info = last_page.previous_page_info()
        self.assertDictEqual(
            {
                'type': 'backward',
                'key': key,
                'value': last_name,
                'offset': 1,
            },
            info,
        )

        before_last_page = paginator.page(info)
        self.assertListEqual(contacts[3:5], [*before_last_page.object_list])
        self.assertTrue(before_last_page.has_next())
        self.assertTrue(before_last_page.has_previous())

    def test_next_n_previous_page01(self):
        "Manage forward & backward OFFSET (many duplicates)."
        # We create a page filled with duplicates, & more
        self._build_contacts(c3=6)

        qs = FakeContact.objects.order_by('last_name', 'id')
        contacts = [*qs]
        paginator = FlowPaginator(qs, key='last_name', per_page=3, count=len(contacts))
        page1 = paginator.page()
        page2 = paginator.page(page1.next_page_info())
        page3 = paginator.page(page2.next_page_info())
        self.assertListEqual(contacts[6:9], [*page3.object_list])

        page2a = paginator.page(page3.previous_page_info())
        self.assertListEqual(contacts[3:6], [*page2a.object_list])

        with self.assertNumQueries(1):
            info3a = page2a.next_page_info()

        with self.assertNumQueries(0):
            page2a.next_page_info()  # Cache query

        self.assertDictEqual(
            {
                'type': 'forward',
                'key': 'last_name',
                'value': contacts[2].last_name,
                'offset': 4,
            },
            info3a,
        )

        page3a = paginator.page(info3a)
        self.assertListEqual(contacts[6:9], [*page3a.object_list])

    def test_desc01(self):
        "Next page."
        self._build_contacts()

        contacts = FakeContact.objects.order_by('-last_name')
        paginator = FlowPaginator(
            contacts.all(), key='-last_name', per_page=2, count=len(contacts),
        )
        page1 = paginator.page()
        self.assertEqual([contacts[0], contacts[1]], [*page1.object_list])
        self.assertTrue(page1.has_next())
        self.assertFalse(page1.has_previous())

        info = page1.next_page_info()
        self.assertDictEqual(
            {
                'type': 'forward',
                'key': '-last_name',
                'value': contacts[2].last_name,
            },
            info,
        )

        # Page 2
        page2 = paginator.page(info)
        self.assertEqual([contacts[2], contacts[3]], [*page2.object_list])
        self.assertTrue(page2.has_next())
        self.assertTrue(page2.has_previous())
        self.assertDictEqual(
            {
                'type': 'forward',
                'key': '-last_name',
                'value': contacts[4].last_name,
            },
            page2.next_page_info(),
        )

    def test_desc02(self):
        "Previous page."
        self._build_contacts()

        qs = FakeContact.objects.order_by('-last_name')
        contacts = [*qs]
        paginator = FlowPaginator(qs.all(), key='-last_name', per_page=2, count=len(contacts))
        page1 = paginator.page()
        page2 = paginator.page(page1.next_page_info())
        page3 = paginator.page(page2.next_page_info())
        self.assertListEqual(contacts[4:6], [*page3.object_list])
        self.assertTrue(page3.has_next())
        self.assertTrue(page3.has_previous())

        info2a = page3.previous_page_info()
        self.assertDictEqual(
            {
                'type': 'backward',
                'key': '-last_name',
                'value': contacts[4].last_name,
            },
            info2a,
        )

        # Page 2
        page2a = paginator.page(info2a)
        self.assertListEqual(contacts[2:4], [*page2a.object_list])
        self.assertTrue(page2a.has_next())
        self.assertTrue(page2a.has_previous())
        self.assertDictEqual(
            {
                'type': 'backward',
                'key': '-last_name',
                'value': contacts[2].last_name,
            },
            page2a.previous_page_info(),
        )

    def test_info01(self):
        self._build_contacts()

        qs = FakeContact.objects.all()
        contacts = [*qs]

        key = 'last_name'
        paginator = FlowPaginator(qs.all(), key=key, per_page=2, count=len(contacts))

        page1 = paginator.page()
        with self.assertNumQueries(0):
            info1 = page1.info()

        self.assertEqual({'type': 'first'}, info1)

        page1a = paginator.page(info1)
        self.assertListEqual(contacts[:2], [*page1a.object_list])
        self.assertFalse(page1a.has_previous())

        # Page 2
        page2 = paginator.page(page1.next_page_info())
        info2 = page2.info()
        self.assertDictEqual(
            {
                'type': 'forward',
                'key': key,
                'value': contacts[2].last_name,
            },
            info2,
        )
        self.assertListEqual(contacts[2:4], [*paginator.page(info2).object_list])

        # Page 3
        page3 = paginator.page(page2.next_page_info())
        info3 = page3.info()
        self.assertDictEqual(
            {
                'type': 'forward',
                'key': key,
                'value': contacts[4].last_name,
            },
            info3,
        )
        self.assertListEqual(contacts[4:6], [*paginator.page(info3).object_list])

    def test_info02(self):
        "Last page."
        self._build_contacts()

        qs = FakeContact.objects.all()
        contacts = [*qs]
        paginator = FlowPaginator(
            qs.all(), key='last_name', per_page=2, count=len(contacts),
        )

        info = paginator.last_page().info()
        self.assertEqual({'type': 'last', 'key': 'last_name'}, info)

        page = paginator.page(info)
        self.assertListEqual(contacts[-2:], [*page.object_list])
        self.assertFalse(page.has_next())
        self.assertTrue(page.has_previous())

    def test_info03(self):
        "Forward + other key."
        self._build_contacts()

        key = 'first_name'
        qs = FakeContact.objects.order_by(key)
        contacts = [*qs]

        paginator = FlowPaginator(
            qs.all(), key=key, per_page=2, count=len(contacts),
        )

        page1 = paginator.page()
        page2 = paginator.page(page1.next_page_info())
        self.assertDictEqual(
            {
                'type': 'forward',
                'key': key,
                'value': contacts[2].first_name,
            },
            page2.info(),
        )

    def test_info04(self):
        "Backward."
        self._build_contacts()

        qs = FakeContact.objects.all()
        contacts = [*qs]

        key = 'last_name'
        paginator = FlowPaginator(qs.all(), key=key, per_page=2, count=len(contacts))

        page1 = paginator.page()
        page2 = paginator.page(page1.next_page_info())
        page3 = paginator.page(page2.next_page_info())

        info2a = paginator.page(page3.previous_page_info()).info()
        self.assertDictEqual(
            {
                'type': 'backward',
                'key': key,
                'value': contacts[4].last_name,
            },
            info2a,
        )

        page2a = paginator.page(info2a)
        self.assertListEqual(contacts[2:4], [*page2a.object_list])
        self.assertTrue(page2a.has_next())
        self.assertTrue(page2a.has_previous())

    def test_info05(self):
        "Forward OFFSET."
        self._build_contacts(c2=3)  # We create some duplicates

        qs = FakeContact.objects.order_by('last_name', 'id')
        contacts = [*qs]

        paginator = FlowPaginator(
            qs, key='last_name', per_page=3, count=len(contacts),
        )
        page1 = paginator.page()

        info2 = paginator.page(page1.next_page_info()).info()
        self.assertDictEqual(
            {
                'type': 'forward',
                'key': 'last_name',
                'value': contacts[3].last_name,
                'offset': 2,
            },
            info2,
        )

        page2 = paginator.page(info2)
        self.assertListEqual(contacts[3:6], [*page2.object_list])
        self.assertTrue(page2.has_next())
        self.assertTrue(page2.has_previous())

    def test_info06(self):
        "Backward OFFSET."
        self._build_contacts(c4=5)  # We create some duplicates

        key = 'last_name'
        qs = FakeContact.objects.order_by(key, 'id')
        contacts = [*qs]

        paginator = FlowPaginator(qs, key=key, per_page=3, count=len(contacts))
        page1 = paginator.page()
        page2 = paginator.page(page1.next_page_info())
        page3 = paginator.page(page2.next_page_info())

        info2a = paginator.page(page3.previous_page_info()).info()
        self.assertDictEqual(
            {
                'type': 'backward',
                'key': key,
                'value': contacts[3].last_name,
                'offset': 1,
            },
            info2a,
        )

        page2a = paginator.page(info2a)
        self.assertListEqual(contacts[3:6], [*page2a.object_list])
        self.assertTrue(page2a.has_next())
        self.assertTrue(page2a.has_previous())

        with self.assertRaises(FirstPage):
            paginator.page(page2a.previous_page_info())

        # Page 3 again
        info3a = page2a.next_page_info()
        self.assertEqual(
            {
                'type': 'forward',
                'key': key,
                'value': contacts[3].last_name,
                'offset': 3,
            },
            info3a,
        )

        self.assertListEqual(contacts[6:9], [*paginator.page(info3a).object_list])

    def test_info07(self):
        "DESC."
        self._build_contacts()

        qs = FakeContact.objects.order_by('-last_name')
        contacts = [*qs]
        paginator = FlowPaginator(
            qs.all(), key='-last_name', per_page=2, count=len(contacts),
        )

        page1 = paginator.page()
        self.assertEqual({'type': 'first'}, page1.info())

        page2 = paginator.page(page1.next_page_info())
        info2a = page2.info()
        self.assertDictEqual(
            {
                'type': 'forward',
                'key': '-last_name',
                'value': contacts[2].last_name,
            },
            info2a,
        )

        # Page 2
        page2a = paginator.page(info2a)
        self.assertListEqual(contacts[2:4], [*page2a.object_list])
        self.assertTrue(page2a.has_next())
        self.assertTrue(page2a.has_previous())

    def test_serialize_date_field(self):
        self._build_contacts()
        self._add_birthdays()

        qs = FakeContact.objects.order_by('birthday')
        contacts = [*qs.all()]
        paginator = FlowPaginator(qs, key='birthday', per_page=2, count=len(contacts))
        page1 = paginator.page()
        self.assertListEqual(contacts[:2], [*page1.object_list])
        self.assertTrue(page1.has_next())
        self.assertFalse(page1.has_previous())

        info2 = page1.next_page_info()
        self.assertDictEqual(
            {
                'type': 'forward',
                'key': 'birthday',
                'value': '1981-03-12',
            },
            info2,
        )

        # Page 2
        page2 = paginator.page(info2)
        self.assertListEqual(contacts[2:4], [*page2.object_list])
        self.assertTrue(page2.has_next())
        self.assertTrue(page2.has_previous())
        self.assertDictEqual(
            {
                'type': 'forward',
                'key': 'birthday',
                'value': '1981-03-12',
            },
            page2.info()
        )
        self.assertDictEqual(
            {
                'type': 'backward',
                'key': 'birthday',
                'value': '1981-03-12',
            },
            page2.previous_page_info(),
        )

    def test_serialize_datetime_field(self):
        self._build_contacts()

        for minute, contact in enumerate(
            self._qs_2_shuffled_list(FakeContact.objects.all()), start=1,
        ):
            contact.created = self.create_datetime(
                utc=True,
                year=2016, month=3, day=24, hour=15, minute=minute,
            )
            contact.save()

        qs = FakeContact.objects.order_by('created')
        contacts = [*qs.all()]
        paginator = FlowPaginator(qs, key='created', per_page=2, count=len(contacts))
        page1 = paginator.page()
        self.assertListEqual(contacts[:2], [*page1.object_list])

        info2 = page1.next_page_info()
        self.assertDictEqual(
            {
                'type': 'forward',
                'key': 'created',
                'value': '2016-03-24T15:03:00.000000Z',
            },
            info2,
        )
        self.assertListEqual(contacts[2:4], [*paginator.page(info2).object_list])

    def test_serialize_decimal_field(self):
        user = self.user
        invoice = FakeInvoice.objects.create(user=user, name='Swords & shields')

        create_line = partial(FakeInvoiceLine.objects.create, user=user, linked_invoice=invoice)

        for i in range(5):
            create_line(item=f'Bento {i}', unit_price=f'1{i}.6')

        key = 'unit_price'
        qs = FakeInvoiceLine.objects.order_by(key)
        lines = [*qs.all()]
        paginator = FlowPaginator(qs, key=key, per_page=2, count=len(lines))
        page1 = paginator.page()
        self.assertEqual(lines[:2], [*page1.object_list])

        info2 = page1.next_page_info()
        self.assertDictEqual(
            {
                'type': 'forward',
                'key': key,
                'value': '12.60',
            },
            info2,
        )
        self.assertEqual(lines[2:4], [*paginator.page(info2).object_list])

    def test_none_value01(self):
        "None values + DESC."
        self._build_contacts()
        self._add_birthdays(count=3)

        key = '-birthday'
        qs = FakeContact.objects.order_by(key, 'id')
        contacts = [*qs.all()]
        paginator = FlowPaginator(qs, key=key, per_page=2, count=len(contacts))

        # Page 1
        page1 = paginator.page()
        self.assertListEqual(contacts[:2], [*page1.object_list])
        self.assertTrue(page1.has_next())
        self.assertFalse(page1.has_previous())

        # Page 2
        page2 = paginator.page(page1.next_page_info())
        self.assertListEqual(contacts[2:4], [*page2.object_list])
        self.assertTrue(page2.has_next())
        self.assertTrue(page2.has_previous())

        # Page 3
        info3 = page2.next_page_info()
        self.assertDictEqual(
            {
                'type': 'forward',
                'key': key,
                'value': None,
                'offset': 1,
            },
            info3,
        )

        page3 = paginator.page(info3)
        self.assertListEqual(contacts[4:6], [*page3.object_list])
        self.assertListEqual(contacts[6:],  [*paginator.page(page3.next_page_info()).object_list])

        # Page 2 again (test backward)
        info2a = page3.previous_page_info()
        self.assertDictEqual(
            {
                'type': 'backward',
                'key': key,
                'value': None,
                'offset': 2,
            },
            info2a,
        )

        page2a = paginator.page(info2a)
        self.assertListEqual(contacts[2:4], [*page2a.object_list])

    def test_none_value02(self):
        "None values + ASC."
        self._build_contacts()
        self._add_birthdays(count=3)

        key = 'birthday'
        qs = FakeContact.objects.order_by(key, 'id')
        contacts = [*qs.all()]
        paginator = FlowPaginator(qs, key=key, per_page=2, count=len(contacts))

        # Page 1
        page1 = paginator.page()
        self.assertListEqual(contacts[:2], [*page1.object_list])
        self.assertTrue(page1.has_next())
        self.assertFalse(page1.has_previous())

        # Page 2
        page2 = paginator.page(page1.next_page_info())
        self.assertListEqual(contacts[2:4], [*page2.object_list])
        self.assertTrue(page2.has_next())
        self.assertTrue(page2.has_previous())

        # Page 3
        page3 = paginator.page(page2.next_page_info())
        self.assertListEqual(contacts[4:6], [*page3.object_list])
        self.assertListEqual(contacts[6:],  [*paginator.page(page3.next_page_info()).object_list])

        # Page 2 again (test forward)
        info2a = page3.previous_page_info()
        page2a = paginator.page(info2a)
        self.assertListEqual(contacts[2:4], [*page2a.object_list])

    def test_none_value03(self):
        "None values + ASC + previous (info==None -> retrieve only NULL values)."
        self._build_contacts()
        self._add_birthdays(count=3)

        key = 'birthday'
        qs = FakeContact.objects.order_by(key, 'id')
        contacts = [*qs.all()]
        paginator = FlowPaginator(qs, key=key, per_page=2, count=len(contacts))

        page4 = paginator.last_page()
        self.assertListEqual(contacts[-2:], [*page4.object_list])

        page3 = paginator.page(page4.previous_page_info())
        self.assertListEqual(contacts[-4:-2], [*page3.object_list])

        info2 = page3.previous_page_info()
        self.assertDictEqual(
            {'type': 'backward', 'value': None, 'key': 'birthday'},
            info2,
        )

        page2 = paginator.page(info2)
        self.assertListEqual(contacts[-6:-4], [*page2.object_list])

    def test_none_value04(self):
        "None values + DESC (previous better tested: return to a a page without None)."
        self._build_contacts()
        # 3 last Contacts have birthday==None (if RDBMS order None as "very small")
        self._add_birthdays(count=4)

        key = '-birthday'
        qs = FakeContact.objects.order_by(key, 'id')
        contacts = [*qs.all()]
        paginator = FlowPaginator(qs, key=key, per_page=2, count=len(contacts))

        last_page = paginator.last_page()
        self.assertListEqual(contacts[-2:], [*last_page.object_list])

        info = last_page.previous_page_info()
        self.assertDictEqual(
            {
                'type': 'backward',
                'key': key,
                'value': None,
                'offset': 1,
            },
            info,
        )

        before_last_page = paginator.page(info)
        self.assertListEqual(
            contacts[-4:-2],
            [*before_last_page.object_list]
        )
        self.assertListEqual(
            contacts[-6:-4],
            [*paginator.page(before_last_page.previous_page_info()).object_list]
        )

    def _add_sectors(self):
        create_sector = FakeSector.objects.create
        s1 = create_sector(title='Swimming',    order=3)
        s2 = create_sector(title='Volley ball', order=1)
        s3 = create_sector(title='Golf',        order=2)

        for sector, contact in zip(
            [s1, s2, s2, s2, s3, s3],
            self._qs_2_shuffled_list(FakeContact.objects.all()),
        ):
            contact.sector = sector
            contact.save()

    def test_fk01(self):
        "Key: 'sector'."
        self._build_contacts()
        self._add_sectors()

        key = 'sector'
        qs = FakeContact.objects.order_by(key, 'id')
        self.assertRegex(
            self._get_sql(qs),
            r'ORDER BY '
            r'.creme_core_fakesector.\..order. ASC( NULLS FIRST)?\, '
            r'.creme_core_fakecontact.\..cremeentity_ptr_id. ASC( NULLS FIRST)?$',
        )

        contacts = [*qs]
        self.assertListEqual(
            contacts, [*FakeContact.objects.order_by('sector__order', 'id')],
        )
        self.assertNotEqual(
            contacts, [*FakeContact.objects.order_by('sector__pk', 'id')],
        )

        paginator = FlowPaginator(qs, key=key, per_page=2, count=len(contacts))
        page1 = paginator.page()
        self.assertListEqual(contacts[:2], [*page1.object_list])

        with self.assertNumQueries(1):
            info2 = page1.next_page_info()

        self.assertDictEqual(
            {
                'type': 'forward',
                'value': 1,  # == s2.order
                'key': key,
                'offset': 1,
            },
            info2,
        )

        page2 = paginator.page(info2)
        self.assertListEqual(contacts[2:4], [*page2.object_list])
        self.assertTrue(page2.has_next())

        page3 = paginator.page(page2.next_page_info())
        self.assertListEqual(contacts[4:6], [*page3.object_list])
        self.assertTrue(page3.has_next())
        self.assertTrue(page3.has_previous())

        page4 = paginator.page(page3.next_page_info())
        self.assertListEqual(contacts[6:], [*page4.object_list])
        self.assertFalse(page4.has_next())

        # Previous -----------
        info2a = page3.previous_page_info()
        self.assertDictEqual(
            {
                'type': 'backward',
                'value': 2,
                'key': key,
                'offset': 1,
            },
            info2a,
        )
        self.assertListEqual(contacts[2:4], [*paginator.page(info2a).object_list])

        # Info() -------------
        info3a = page3.info()
        self.assertDictEqual(
            {'type': 'forward', 'value': 2, 'key': key},
            info3a,
        )
        self.assertListEqual(contacts[4:6], [*paginator.page(info3a).object_list])

    def test_fk02(self):
        "Key: 'sector__order'."
        self._build_contacts()
        self._add_sectors()

        key = 'sector__order'
        qs = FakeContact.objects.order_by(key, 'id')
        contacts = [*qs]
        paginator = FlowPaginator(qs, key=key, per_page=2, count=len(contacts))

        page1 = paginator.page()
        self.assertListEqual(contacts[:2], [*page1.object_list])

        info2 = page1.next_page_info()
        self.assertDictEqual(
            {
                'type': 'forward',
                'value': 1,  # == s2.order
                'key': key,
                'offset': 1,
            },
            info2,
        )

        page2 = paginator.page(info2)
        self.assertListEqual(contacts[2:4], [*page2.object_list])

        page3 = paginator.page(page2.next_page_info())
        self.assertListEqual(contacts[4:6], [*page3.object_list])

        page4 = paginator.page(page3.next_page_info())
        self.assertListEqual(contacts[6:], [*page4.object_list])
        self.assertFalse(page4.has_next())

        # Previous
        page2a = paginator.page(page3.previous_page_info())
        self.assertListEqual(contacts[2:4], [*page2a.object_list])

        # Info()
        info3a = page3.info()
        self.assertListEqual(contacts[4:6], [*paginator.page(info3a).object_list])

    def test_fk03(self):
        "Key: 'sector__id'."
        self._build_contacts()
        self._add_sectors()

        key = 'sector__id'
        qs = FakeContact.objects.order_by(key, 'id')
        contacts = [*qs]
        paginator = FlowPaginator(qs, key=key, per_page=2, count=len(contacts))

        page1 = paginator.page()
        self.assertListEqual(contacts[:2], [*page1.object_list])

        page2 = paginator.page(page1.next_page_info())
        self.assertListEqual(contacts[2:4], [*page2.object_list])

        page3 = paginator.page(page2.next_page_info())
        self.assertListEqual(contacts[4:6], [*page3.object_list])

        page4 = paginator.page(page3.next_page_info())
        self.assertListEqual(contacts[6:], [*page4.object_list])
        self.assertFalse(page4.has_next())

        # Previous
        page2a = paginator.page(page3.previous_page_info())
        self.assertListEqual(contacts[2:4], [*page2a.object_list])

        # Info()
        info3a = page3.info()
        self.assertListEqual(contacts[4:6], [*paginator.page(info3a).object_list])

    def test_fk04(self):
        "Key: '-sector'."
        self._build_contacts()
        self._add_sectors()

        key = '-sector'
        qs = FakeContact.objects.order_by(key, 'id')
        contacts = [*qs]
        paginator = FlowPaginator(qs, key=key, per_page=2, count=len(contacts))

        page1 = paginator.page()
        self.assertListEqual(contacts[:2], [*page1.object_list])

        page2 = paginator.page(page1.next_page_info())
        self.assertListEqual(contacts[2:4], [*page2.object_list])

        page3 = paginator.page(page2.next_page_info())
        self.assertListEqual(contacts[4:6], [*page3.object_list])

        page4 = paginator.page(page3.next_page_info())
        self.assertListEqual(contacts[6:], [*page4.object_list])
        self.assertFalse(page4.has_next())

        # Previous
        page2a = paginator.page(page3.previous_page_info())
        self.assertListEqual(contacts[2:4], [*page2a.object_list])

        # Info()
        info3a = page3.info()
        self.assertListEqual(contacts[4:6], [*paginator.page(info3a).object_list])

    def test_fk05(self):
        "Key: pk1__pk2 (2 nullable ForeignKeys)."
        user = self.user

        create_cat = FakeFolderCategory.objects.create
        cat1 = create_cat(name='Maps')
        cat2 = create_cat(name='Blue prints')

        create_folder = partial(FakeFolder.objects.create, user=user)
        folder1 = create_folder(title='Earth maps', category=cat1)
        folder2 = create_folder(title='Mars maps',  category=cat1)
        folder3 = create_folder(title='Ships',      category=cat2)
        folder4 = create_folder(title="Faye's pix")

        create_doc = partial(FakeDocument.objects.create, user=user)
        create_doc(title='Japan map part#1', linked_folder=folder1)
        create_doc(title='Japan map part#2', linked_folder=folder1)
        create_doc(title='Mars city 1',      linked_folder=folder2)
        create_doc(title='Mars city 2',      linked_folder=folder2)
        create_doc(title='Swordfish',        linked_folder=folder3)
        create_doc(title='Money!!.jpg',      linked_folder=folder4)
        create_doc(title='selfie.jpg',       linked_folder=folder4)

        key = 'linked_folder__category'
        qs = FakeDocument.objects.order_by(key, 'id')
        docs = [*qs]
        self.assertListEqual(
            docs,
            [*FakeDocument.objects.order_by('linked_folder__category__name', 'id')]
        )
        self.assertNotEqual(
            docs,
            [*FakeDocument.objects.order_by('linked_folder__category__pk', 'id')]
        )

        paginator = FlowPaginator(qs, key=key, per_page=2, count=len(docs))
        page1 = paginator.page()
        self.assertEqual(docs[:2], [*page1.object_list])

        info2 = page1.next_page_info()
        self.assertDictEqual(
            {
                'type': 'forward',
                'value': cat2.name,
                'key': key,
            },
            info2,
        )

        page2 = paginator.page(info2)
        self.assertEqual(docs[2:4], [*page2.object_list])
        self.assertTrue(page2.has_next())

        page3 = paginator.page(page2.next_page_info())
        self.assertEqual(docs[4:6], [*page3.object_list])
        self.assertTrue(page3.has_next())
        self.assertTrue(page3.has_previous())

        page4 = paginator.page(page3.next_page_info())
        self.assertEqual(docs[6:], [*page4.object_list])
        self.assertFalse(page4.has_next())

    def test_fk06(self):
        "Key: pk1__pk2__foobar (pk1 not nullable) + ASC."
        self._build_contacts()

        other_user = self.other_user

        for contact in self._qs_2_shuffled_list(FakeContact.objects.all())[:3]:
            contact.user = other_user
            contact.save()

        key = '-user__role__name'
        qs = FakeContact.objects.order_by(key, 'id')
        contacts = [*qs]

        paginator = FlowPaginator(qs, key=key, per_page=2, count=len(contacts))
        page1 = paginator.page()
        self.assertListEqual(contacts[:2], [*page1.object_list])

        page2 = paginator.page(page1.next_page_info())
        self.assertListEqual(contacts[2:4], [*page2.object_list])

        page3 = paginator.page(page2.next_page_info())
        self.assertListEqual(contacts[4:6], [*page3.object_list])

        page4 = paginator.page(page3.next_page_info())
        self.assertListEqual(contacts[6:], [*page4.object_list])
        self.assertFalse(page4.has_next())

    def test_fk07(self):
        "Key: pk1__pk2__foobar (pk1 not nullable) + DESC."
        self._build_contacts()

        other_user = self.other_user

        for contact in self._qs_2_shuffled_list(FakeContact.objects.all())[:3]:
            contact.user = other_user
            contact.save()

        key = 'user__role__name'
        qs = FakeContact.objects.order_by(key, 'id')
        contacts = [*qs]

        paginator = FlowPaginator(qs, key=key, per_page=2, count=len(contacts))
        page4 = paginator.last_page()
        self.assertListEqual(contacts[-2:], [*page4.object_list])

        page3 = paginator.page(page4.previous_page_info())
        self.assertListEqual(contacts[-4:-2], [*page3.object_list])

        page2 = paginator.page(page3.previous_page_info())
        self.assertListEqual(contacts[-6:-4], [*page2.object_list])

        with self.assertRaises(FirstPage):
            paginator.page(page2.previous_page_info())

    def test_fk08(self):
        "Populate FK for previous_info()."
        self._build_contacts()
        self._add_sectors()

        key = 'sector'
        qs = FakeContact.objects.order_by(key, 'id')

        paginator = FlowPaginator(qs, key=key, per_page=2, count=len(qs))
        last_page = paginator.last_page()

        with self.assertNumQueries(1):
            last_page.previous_page_info()

    def test_pages01(self):
        self._build_contacts()

        key = 'last_name'
        qs = FakeContact.objects.order_by(key, 'id')
        contacts = [*qs]

        paginator = FlowPaginator(qs, key=key, per_page=3, count=len(contacts))
        it = paginator.pages()

        page1 = next(it)
        self.assertTrue(hasattr(page1, 'next_page_info'))
        self.assertListEqual(contacts[:3], [*page1.object_list])

        page2 = next(it)
        self.assertListEqual(contacts[3:6], [*page2.object_list])

        page3 = next(it)
        self.assertListEqual(contacts[6:], [*page3.object_list])
        self.assertFalse(page3.has_next())

        with self.assertRaises(StopIteration):
            next(it)

    def test_pages02(self):
        "Some elements are deleted."
        self._build_contacts()

        key = 'last_name'
        qs = FakeContact.objects.order_by(key, 'id')
        contacts = [*qs]

        paginator = FlowPaginator(qs, key=key, per_page=3, count=len(contacts))
        it = paginator.pages()

        next(it)  # Page 1 - contacts[:3]
        next(it)  # Page 2 - contacts[3:6]

        for contact in contacts[6:]:
            contact.delete()

        with self.assertRaises(StopIteration):
            next(it)

    def test_get_page01(self):
        "No info."
        self._build_contacts()

        contacts = FakeContact.objects.all()
        count = len(contacts)
        paginator = FlowPaginator(contacts, key='last_name', per_page=count, count=count)

        page = paginator.get_page()
        self.assertIs(page.has_next(), False)
        self.assertIs(page.has_previous(), False)
        self.assertIs(page.has_other_pages(), False)

        self.assertIsNone(page.next_page_info())

    def test_get_page02(self):
        "Invalid info type."
        self._build_contacts()

        contacts = FakeContact.objects.all()
        paginator = FlowPaginator(contacts, key='last_name', per_page=2, count=len(contacts))

        with self.assertNoException():
            page = paginator.get_page([('type', 'first')])

        self.assertTrue(page.has_next())
        self.assertFalse(page.has_previous())

    def test_get_page03(self):
        "Invalid info."
        self._build_contacts()

        contacts = FakeContact.objects.all()
        paginator = FlowPaginator(contacts, key='last_name', per_page=2, count=len(contacts))
        page = paginator.page()
        info = page.next_page_info()

        with self.assertNoException():
            page = paginator.get_page({**info, 'type': 'invalid'})

        self.assertTrue(page.has_next())
        self.assertFalse(page.has_previous())

    def test_get_page04(self):
        "Last page."
        self._build_contacts()
        paginator = FlowPaginator(
            FakeContact.objects.all(), key='last_name', per_page=3, count=7,
        )
        page = paginator.get_page(
            {'type': 'forward', 'key': 'last_name', 'value': 'ZZZZ'}
        )
        self.assertFalse(page.has_next())
        self.assertTrue(page.has_previous())
