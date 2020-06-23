# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2020  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from typing import List, Optional

from django.utils.translation import gettext as _


class PagerLink:
    CHOOSE: str = 'choose'
    PREVIOUS: str = 'previous'
    NEXT: str = 'next'

    page: Optional[int]
    group: Optional[str]
    enabled: bool
    is_current: bool

    def __init__(self,
                 page: Optional[int],
                 label=None,
                 help=None,
                 group: str = None,
                 enabled: bool = True,
                 is_current: bool = False):
        self.page = page
        self.group = group
        self.enabled = enabled
        self.label = label or str(page)
        self.is_current = is_current

        if help is None:
            self.help = _('To page {}').format(page) if page else ''
        else:
            self.help = help

    @property
    def css(self) -> str:
        css = ['pager-link']

        if not self.enabled or self.is_current:
            css.append('is-disabled')

        if self.group:
            css.append(f'pager-link-{self.group}')

        if self.is_current:
            css.append('pager-link-current')

        return ' '.join(css)

    @property
    def is_choose(self) -> bool:
        return self.group == self.CHOOSE

    def __str__(self):
        return (
            f'PagerLink('
            f'label={self.label}, help={self.help}, group={self.group}, '
            f'enabled={self.enabled}, page={self.page}'
            f')'
        )


class PagerContext:
    SHOW_ALL_PAGES_LIMIT: int = 5
    SHOW_LAST_PAGE_LIMIT: int = 4
    SHOW_FIRST_PAGE_LIMIT: int = 4

    count: int
    current: int
    previous: Optional[int]
    next: Optional[int]
    first: int
    last: int

    def __init__(self, page):
        self.page = page

        self.count = page.paginator.num_pages
        self.current = page.number
        self.previous = page.previous_page_number() if page.has_previous() else None
        self.next = page.next_page_number() if page.has_next() else None
        self.first = 1
        self.last = self.count

        self._links = None

    @property
    def links(self) -> List[PagerLink]:
        links = self._links

        if links is None:
            links = self._links = self._build_links()

        return links

    def is_current(self, index: int) -> bool:
        return self.current == index

    def _build_links(self) -> List[PagerLink]:
        page_count = self.count
        page_current = self.current
        page_next = self.next
        page_previous = self.previous
        is_current = self.is_current

        if page_count < 1:
            return []

        links = [
            PagerLink(
                page_previous, label=_('Previous page'),
                group=PagerLink.PREVIOUS,
                enabled=page_previous is not None,
            ),
        ]

        if page_count < self.SHOW_ALL_PAGES_LIMIT:
            links.extend(
                PagerLink(index, is_current=is_current(index))
                for index in range(1, page_count + 1)
            )
        elif page_current <= self.SHOW_LAST_PAGE_LIMIT:
            assert page_next is not None

            links.extend(
                PagerLink(index, is_current=is_current(index))
                for index in range(1, page_next + 1)
            )
            links.append(
                PagerLink(page_next + 1, help=_('To another page'), group=PagerLink.CHOOSE)
            )
            links.append(PagerLink(page_count, help=_('To last page')))
        elif page_current >= page_count - self.SHOW_FIRST_PAGE_LIMIT:
            assert page_previous is not None

            links.append(PagerLink(1, help=_('To first page')))
            links.append(
                PagerLink(page_previous - 1, help=_('To another page'), group=PagerLink.CHOOSE)
            )
            links.extend(
                PagerLink(index, is_current=is_current(index))
                for index in range(page_previous, page_count + 1)
            )
        else:
            assert page_previous is not None
            assert page_next is not None

            links.append(PagerLink(1, help=_('To first page')))
            links.append(
                PagerLink(page_previous - 1, help=_('To another page'), group=PagerLink.CHOOSE)
            )
            links.extend(
                PagerLink(index, is_current=is_current(index))
                for index in range(page_previous, page_next + 1)
            )
            links.append(
                PagerLink(page_next + 1, help=_('To another page'), group=PagerLink.CHOOSE)
            )
            links.append(PagerLink(page_count, help=_('To last page')))

        links.append(
            PagerLink(
                page_next, label=_('Next page'),
                group=PagerLink.NEXT,
                enabled=page_next is not None,
            )
        )

        return links
