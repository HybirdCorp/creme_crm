# -*- coding: utf-8 -*-

from django.core.paginator import Paginator
from django.utils.translation import gettext as _

from creme.creme_core.gui.pager import PagerContext, PagerLink
from creme.creme_core.tests.base import CremeTestCase


class PagerContextTestCase(CremeTestCase):
    def assertPagerLinks(self, links, expected):
        self.assertListEqual(
            [link.__dict__ for link in links],
            [element.__dict__ for element in expected],
        )

    def test_empty_page(self):
        page = Paginator([], 10).page(1)
        pager = PagerContext(page)

        self.assertEqual(1, pager.count)

        self.assertEqual(1, pager.first)
        self.assertEqual(1, pager.last)
        self.assertEqual(1, pager.current)

        self.assertIsNone(pager.next)
        self.assertIsNone(pager.previous)

        # <previous|1|next>
        self.assertPagerLinks([
            PagerLink(None, label=_('Previous page'), group='previous', enabled=False),
            PagerLink(1, label='1', is_current=True),
            PagerLink(None, label=_('Next page'), group='next', enabled=False)
        ], pager.links)

    def test_single_page(self):
        page = Paginator([1, 2], 10).page(1)
        pager = PagerContext(page)

        self.assertEqual(1, pager.count)

        self.assertEqual(1, pager.first)
        self.assertEqual(1, pager.last)
        self.assertEqual(1, pager.current)

        self.assertIsNone(pager.next)
        self.assertIsNone(pager.previous)

        # <previous|1|next>
        self.assertPagerLinks([
            PagerLink(None, label=_('Previous page'), group='previous', enabled=False),
            PagerLink(1, label='1', is_current=True),
            PagerLink(None, label=_('Next page'), group='next', enabled=False)
        ], pager.links)

    def test_firstpage_under_show_all_limit(self):
        page = Paginator([*range(5 * 3)], 5).page(1)
        pager = PagerContext(page)

        self.assertEqual(3, pager.count)

        self.assertEqual(1, pager.first)
        self.assertEqual(3, pager.last)
        self.assertEqual(1, pager.current)

        self.assertEqual(2, pager.next)
        self.assertIsNone(pager.previous)

        # <previous|1|2|3|next>
        self.assertPagerLinks([
            PagerLink(None, label=_('Previous page'), group='previous', enabled=False),
            PagerLink(1, label='1', is_current=True),
            PagerLink(2, label='2'),
            PagerLink(3, label='3'),
            PagerLink(2, label=_('Next page'), group='next')
        ], pager.links)

    def test_under_show_all_limit(self):
        page = Paginator([*range(5 * 3)], 5).page(2)
        pager = PagerContext(page)

        self.assertEqual(3, pager.count)

        self.assertEqual(1, pager.first)
        self.assertEqual(3, pager.last)
        self.assertEqual(2, pager.current)

        self.assertEqual(3, pager.next)
        self.assertEqual(1, pager.previous)

        # <previous|1|2|3|next>
        self.assertPagerLinks([
            PagerLink(1, label=_('Previous page'), group='previous'),
            PagerLink(1, label='1'),
            PagerLink(2, label='2', is_current=True),
            PagerLink(3, label='3'),
            PagerLink(3, label=_('Next page'), group='next')
        ], pager.links)

    def test_lastpage_under_show_all_limit(self):
        page = Paginator([*range(5 * 3)], 5).page(3)
        pager = PagerContext(page)

        self.assertEqual(3, pager.count)

        self.assertEqual(1, pager.first)
        self.assertEqual(3, pager.last)
        self.assertEqual(3, pager.current)

        self.assertIsNone(pager.next)
        self.assertEqual(2, pager.previous)

        # <previous|1|2|3|next>
        self.assertPagerLinks([
            PagerLink(2, label=_('Previous page'), group='previous'),
            PagerLink(1, label='1'),
            PagerLink(2, label='2'),
            PagerLink(3, label='3', is_current=True),
            PagerLink(None, label=_('Next page'), group='next', enabled=False)
        ], pager.links)

    def test_under_show_first_limit(self):
        page = Paginator([*range(5 * 10)], 5).page(3)
        pager = PagerContext(page)

        self.assertEqual(10, pager.count)

        self.assertEqual(1, pager.first)
        self.assertEqual(10, pager.last)
        self.assertEqual(3, pager.current)

        self.assertEqual(4, pager.next)
        self.assertEqual(2, pager.previous)

        # <previous|1|2|3|4|...|10|next>
        self.assertPagerLinks([
            PagerLink(2, label=_('Previous page'), group='previous'),
            PagerLink(1, label='1'),
            PagerLink(2, label='2'),
            PagerLink(3, label='3', is_current=True),
            PagerLink(4, label='4'),
            PagerLink(5, help=_('To another page'), group='choose'),
            PagerLink(10, help=_('To last page')),
            PagerLink(4, label=_('Next page'), group='next')
        ], pager.links)

    def test_under_show_last_limit(self):
        page = Paginator([*range(5 * 10)], 5).page(8)
        pager = PagerContext(page)

        self.assertEqual(10, pager.count)

        self.assertEqual(1, pager.first)
        self.assertEqual(10, pager.last)
        self.assertEqual(8, pager.current)

        self.assertEqual(9, pager.next)
        self.assertEqual(7, pager.previous)

        # <previous|1|...|7|8|9|10|next>
        self.assertPagerLinks([
            PagerLink(7, label=_('Previous page'), group='previous'),
            PagerLink(1, help=_('To first page')),
            PagerLink(6, help=_('To another page'), group='choose'),
            PagerLink(7, label='7'),
            PagerLink(8, label='8', is_current=True),
            PagerLink(9, label='9'),
            PagerLink(10, label='10'),
            PagerLink(9, label=_('Next page'), group='next')
        ], pager.links)

    def test_middle_page(self):
        page = Paginator([*range(5 * 10)], 5).page(5)
        pager = PagerContext(page)

        self.assertEqual(10, pager.count)

        self.assertEqual(1, pager.first)
        self.assertEqual(10, pager.last)
        self.assertEqual(5, pager.current)

        self.assertEqual(6, pager.next)
        self.assertEqual(4, pager.previous)

        # <previous|1|...|4|5|6|...|10|next>
        self.assertPagerLinks([
            PagerLink(4, label=_('Previous page'), group='previous'),
            PagerLink(1, help=_('To first page')),
            PagerLink(3, help=_('To another page'), group='choose'),
            PagerLink(4, label='4'),
            PagerLink(5, label='5', is_current=True),
            PagerLink(6, label='6'),
            PagerLink(7, help=_('To another page'), group='choose'),
            PagerLink(10, help=_('To last page')),
            PagerLink(6, label=_('Next page'), group='next')
        ], pager.links)

    def test_middle_page_huge_count(self):
        page = Paginator([*range(5 * 100)], 5).page(50)
        pager = PagerContext(page)

        self.assertEqual(100, pager.count)

        self.assertEqual(1, pager.first)
        self.assertEqual(100, pager.last)
        self.assertEqual(50, pager.current)

        self.assertEqual(51, pager.next)
        self.assertEqual(49, pager.previous)

        # <previous|1|...|49|50|51|...|100|next>
        self.assertPagerLinks([
            PagerLink(49, label=_('Previous page'), group='previous'),
            PagerLink(1, help=_('To first page')),
            PagerLink(48, help=_('To another page'), group='choose'),
            PagerLink(49, label='49'),
            PagerLink(50, label='50', is_current=True),
            PagerLink(51, label='51'),
            PagerLink(52, help=_('To another page'), group='choose'),
            PagerLink(100, help=_('To last page')),
            PagerLink(51, label=_('Next page'), group='next')
        ], pager.links)
