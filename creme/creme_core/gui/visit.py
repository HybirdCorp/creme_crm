################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2023-2025  Hybird
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

import json
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.urls import reverse

from creme.creme_core.models import CremeEntity
from creme.creme_core.utils.queries import QSerializer


# TODO: factorise with ListViewState?
class EntityVisitor:
    """Class which stores the data used by the view <entity.NextEntityVisiting>
    to find the next entity.
    If contains notably the information on how the listview used to start the
    visit orders & filters the entity (EntityFilter, quick-search, extra Q).
    """
    class Error(ValueError):
        pass

    url_name = 'creme_core__visit_next_entity'

    def __init__(self, *, model: type[CremeEntity], hfilter_id: str, sort: str,
                 efilter_id: str | None = None,
                 internal_q: Q | str = '',
                 requested_q: Q | str = '',
                 search_dict: dict | None = None,
                 page_info: dict | None = None,
                 index: int | None = None,
                 callback_url: str = '',
                 ):
        "@raise <EntityVisitor.Error> if only one argument in {page_info, index} is given."
        self.model = model
        self.hfilter_id = hfilter_id
        self.efilter_id = efilter_id
        self.sort = sort
        self.serialized_internal_q = (
            internal_q if isinstance(internal_q, str) else QSerializer().dumps(internal_q)
        )
        self.serialized_requested_q = (
            requested_q if isinstance(requested_q, str) else QSerializer().dumps(requested_q)
        )
        self.search_dict = search_dict
        self.callback_url = callback_url or model.get_lv_absolute_url()

        if (index is None) ^ (page_info is None):
            raise self.Error(
                'Arguments "index" & "page_info" must be both given or both ignored'
            )

        self.page_info = page_info
        self.index = index

    @classmethod
    def _extract(cls, data: dict, key: str, exp_type: type = str, **kwargs):
        """Extract a value from a dictionary, & check its type.
        @param kwargs: Optional argument "default" to indicate the default value
               to use if the key is not found.
        """
        try:
            result = data[key]
        except KeyError:
            if 'default' not in kwargs:
                raise cls.Error(f'Key "{key}" is required.')

            return kwargs['default']

        if not isinstance(result, exp_type):
            raise cls.Error(f'The value for "{key}" must be a {exp_type.__name__}')

        return result

    @classmethod
    def from_json(cls, model: type[CremeEntity], json_data: str) -> EntityVisitor:
        """Build an instance of EntityVisitor from JSON data.
        @raise <EntityVisitor.DecodeError>.
        """
        try:
            visitor_dict = json.loads(json_data)
        except json.JSONDecodeError as e:
            raise cls.Error(str(e)) from e

        if not isinstance(visitor_dict, dict):
            raise cls.Error('Data must be a dictionary')

        extract = partial(cls._extract, data=visitor_dict)

        try:
            return cls(
                model=model,
                callback_url=extract(key='callback'),
                hfilter_id=extract(key='hfilter'),
                sort=extract(key='sort'),
                efilter_id=extract(key='efilter', default=None),
                internal_q=extract(key='internal_q', default=''),
                requested_q=extract(key='requested_q', default=''),
                search_dict=extract(key='search', default=None, exp_type=dict),
                page_info=extract(key='page', default=None, exp_type=dict),
                index=extract(key='index', default=None, exp_type=int),
            )
        except KeyError as e:
            raise cls.Error(str(e)) from e

    def to_json(self):
        visitor_dict = {
            'hfilter': self.hfilter_id,
            'sort': self.sort,
            'callback': self.callback_url,
        }

        if self.page_info:
            visitor_dict['page'] = self.page_info
            visitor_dict['index'] = self.index

        if self.efilter_id:
            visitor_dict['efilter'] = self.efilter_id

        if self.serialized_internal_q:
            visitor_dict['internal_q'] = self.serialized_internal_q
        if self.serialized_requested_q:
            visitor_dict['requested_q'] = self.serialized_requested_q

        if self.search_dict:
            visitor_dict['search'] = self.search_dict

        return json.dumps(visitor_dict)

    @property
    def uri(self) -> str:
        """Returns the URI of the "visit" view."""
        # TODO: get params names from <creme_core.views.entity.NextEntityVisiting>
        parameters = {
            'hfilter': self.hfilter_id,
            'sort': self.sort,
            'callback': self.callback_url,
        }

        if self.index is not None:
            parameters['index'] = self.index
        if self.page_info:
            parameters['page'] = json.dumps(self.page_info)
        if self.efilter_id:
            parameters['efilter'] = self.efilter_id
        if self.serialized_internal_q:
            parameters['internal_q'] = self.serialized_internal_q
        if self.serialized_requested_q:
            parameters['requested_q'] = self.serialized_requested_q
        if self.search_dict:
            parameters.update(self.search_dict)

        return reverse(
            self.url_name,
            args=(ContentType.objects.get_for_model(self.model).id,),
            query=parameters,
        )
