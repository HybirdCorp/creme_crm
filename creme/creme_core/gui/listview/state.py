################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2026  Hybird
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

from __future__ import annotations

import logging

from creme.creme_core.models.entity_filter import (
    EntityFilter,
    EntityFilterList,
)
from creme.creme_core.models.header_filter import (
    HeaderFilter,
    HeaderFilterList,
)

logger = logging.getLogger(__name__)


class NoHeaderFilterAvailable(Exception):
    pass


class ListViewState:
    def __init__(self, **kwargs):
        get_arg = kwargs.get
        self.entity_filter_id = get_arg('filter')
        self.header_filter_id = get_arg('hfilter')
        self.page = get_arg('page')
        self.rows = get_arg('rows')
        self.sort_order = get_arg('sort_order')
        self.sort_cell_key = get_arg('sort_cell_key')
        self.url = get_arg('url')
        self.search = {}

    def __repr__(self):
        return (
            f'<ListViewState('
            f'efilter_id={self.entity_filter_id}, '
            f'hfilter_id={self.header_filter_id}, '
            f'page={self.page}, '
            f'rows={self.rows}, '
            f'sort={self.sort_order}{self.sort_cell_key}, '
            f'url={self.url}, '
            f'search={self.search}'
            f')>'
        )

    def register_in_session(self, request) -> None:
        request.session[self.url] = self.__dict__

    @classmethod
    def get_state(cls, request, url=None) -> ListViewState | None:
        """Try to build a state, corresponding to an URL from data stored in session."""
        lvs = None
        data = request.session.get(url or request.path)

        if data is not None:
            lvs = cls()

            for k, v in data.items():
                setattr(lvs, k, v)

        return lvs

    @classmethod
    def build_from_request(cls, arguments, url: str, **kwargs) -> ListViewState:
        """Build a state from the arguments of a GET/POST request."""
        kwargs.update((str(k), v) for k, v in arguments.items())
        kwargs['url'] = url

        return cls(**kwargs)

    # TODO: rename "url" => "id" ?
    @classmethod
    def get_or_create_state(cls, request, url: str, **kwargs) -> ListViewState:
        """Retrieve the state stored in session, and create one if no state is stored."""
        state = cls.get_state(request, url)

        if state is None:
            arguments = request.POST if request.method == 'POST' else request.GET
            state = cls.build_from_request(arguments, url, **kwargs)

        return state

    def set_headerfilter(self,
                         header_filters: HeaderFilterList,
                         id: str = '',
                         default_id: str = '',
                         ) -> HeaderFilter:
        """Select a HeaderFilter & store it.

        @param header_filters: HeaderFilterList where filters are searched.
               Its 'selected' state is set.
        @param id: ID of the filter to select.
        @param default_id: ID to use if <id> is not found.
        @return: A HeaderFilter instance
        @raise NoHeaderFilterAvailable.
        """
        # Try first to get the posted header filter which is the most recent.
        # Then try to retrieve the header filter from session, then fallback
        hf = header_filters.select_by_id(
            id, self.header_filter_id, default_id,
        )

        if hf is None:
            raise NoHeaderFilterAvailable()

        self.header_filter_id = hf.id

        return hf

    def set_entityfilter(self,
                         entity_filters: EntityFilterList,
                         filter_id: str,
                         default_id: str = '',
                         ) -> EntityFilter | None:
        """Select an EntityFilter & store it.

        @param entity_filters: EntityFilterList where filters are searched.
               Its 'selected' state is set.
        @param filter_id: ID of the filter to select.
               An empty string means we want to clear the selection.
        @param default_id: ID to use if <filter_id> is not found.
        @return: An EntityFilter instance, or None.
        """
        efilter = (
            None
            if filter_id == '' else
            entity_filters.select_by_id(filter_id, self.entity_filter_id, default_id)
        )

        if efilter and efilter.disabled:
            # TODO: send a notification to the logged user to indicate that its
            #       current filter has been disabled?
            entity_filters.clear_selected()
            efilter = None

        self.entity_filter_id = efilter.id if efilter else None

        return efilter
