from django.core.paginator import Paginator

from creme.creme_core.utils.paginators import OnePagePaginator

from ..base import CremeTestCase
from ..fake_models import FakeSector


class OnePagePaginatorTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        create_sector = FakeSector.objects.create
        create_sector(title='Comics')
        create_sector(title='Toys')

    def test_django_paginator_big_content1(self):
        "More items than the first page can contain."
        qs = FakeSector.objects.order_by('id')
        sectors = [*qs]
        self.assertEqual(len(sectors), 5)

        per_page = 3

        with self.assertNumQueries(0):
            paginator = Paginator(qs.all(), per_page=per_page)

        with self.assertNumQueries(1):  # COUNT query
            page = paginator.page(1)

        with self.assertNumQueries(1):
            limited_sectors = [*page.object_list]

        self.assertEqual(per_page, len(limited_sectors))
        self.assertListEqual(sectors[:per_page], limited_sectors)

        with self.assertNumQueries(0):
            count = paginator.count

        self.assertEqual(len(sectors), count)
        self.assertEqual(2, paginator.num_pages)

    def test_django_paginator_big_content2(self):
        "More items than the first page can contain (count() called before)."
        qs = FakeSector.objects.order_by('id')
        sectors = [*qs]
        self.assertEqual(len(sectors), 5)

        per_page = 3

        with self.assertNumQueries(0):
            paginator = Paginator(qs.all(), per_page=per_page)

        with self.assertNumQueries(1):
            count = paginator.count
        self.assertEqual(len(sectors), count)

        with self.assertNumQueries(0):
            page = paginator.page(1)

        with self.assertNumQueries(1):
            limited_sectors = [*page.object_list]

        self.assertEqual(per_page, len(limited_sectors))
        self.assertListEqual(sectors[:per_page], limited_sectors)

        self.assertEqual(2, paginator.num_pages)

    def test_django_paginator_small_content(self):
        """The first page can contain all items => COUNT query is done anyway.
        Our class becomes useless if this test fails.
        """
        qs = FakeSector.objects.order_by('id')
        sectors = [*qs]
        self.assertEqual(len(sectors), 5)

        per_page = 13

        with self.assertNumQueries(0):
            paginator = Paginator(qs.all(), per_page=per_page)

        with self.assertNumQueries(1):  # COUNT query
            page = paginator.page(1)

        with self.assertNumQueries(1):  # Retrieve objects
            limited_sectors = [*page.object_list]

        self.assertEqual(len(sectors), len(limited_sectors))
        self.assertListEqual(sectors, limited_sectors)

        with self.assertNumQueries(0):
            count = paginator.count

        self.assertEqual(len(sectors), count)
        self.assertEqual(1, paginator.num_pages)

    def test_big_content(self):
        "More items than the first page can contain."
        qs = FakeSector.objects.order_by('id')
        sectors = [*qs]
        self.assertEqual(len(sectors), 5)

        per_page = 3

        with self.assertNumQueries(2):  # Retrieve objects + COUNT
            paginator = OnePagePaginator(qs.all(), per_page=per_page)
            num_pages = paginator.num_pages

        self.assertEqual(0, paginator.orphans)
        self.assertTrue(paginator.allow_empty_first_page)
        self.assertEqual(2, num_pages)

        with self.assertNumQueries(0):
            page = paginator.page(1)

        with self.assertNumQueries(0):
            limited_sectors = [*page.object_list]
            page_length = len(page)

        self.assertEqual(per_page, len(limited_sectors))
        self.assertEqual(per_page, page_length)
        self.assertListEqual(sectors[:per_page], limited_sectors)
        self.assertTrue(page.has_next())

        with self.assertNumQueries(0):
            count = paginator.count

        self.assertEqual(len(sectors), count)
        self.assertEqual([1], [*paginator.page_range])  # Not [1, 2]

        # __iter__ (only one page)
        self.assertListEqual([page], [*paginator])

    def test_small_content(self):
        """The first & unique page can contain all items
        => <COUNT> query is NOT performed.
        """
        qs = FakeSector.objects.order_by('id')
        sectors = [*qs]
        self.assertEqual(len(sectors), 5)

        per_page = 13

        with self.assertNumQueries(1):  # Retrieve objects
            paginator = OnePagePaginator(qs.all(), per_page=per_page)
            num_pages = paginator.num_pages

        self.assertEqual(1, num_pages)

        with self.assertNumQueries(0):
            page = paginator.page(1)

        with self.assertNumQueries(0):
            limited_sectors = [*page.object_list]

        self.assertEqual(len(sectors), len(limited_sectors))
        self.assertListEqual(sectors, limited_sectors)
        self.assertFalse(page.has_next())

        with self.assertNumQueries(0):
            count = paginator.count

        self.assertEqual(len(sectors), count)

    def test_count(self):
        """The first & unique page can contain all items
        => COUNT query is not performed.
        """
        qs = FakeSector.objects.order_by('id')
        sectors = [*qs]

        with self.assertNumQueries(1):
            paginator = OnePagePaginator(qs.all(), per_page=13)

        with self.assertNumQueries(0):
            count = paginator.count

        self.assertEqual(len(sectors), count)
