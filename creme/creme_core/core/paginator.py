################################################################################
#
# Copyright (c) 2016-2025 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################

from __future__ import annotations

import logging
import sys
from collections.abc import Iterable, Iterator, Sequence
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from math import ceil

from django.core.exceptions import ValidationError
from django.core.paginator import InvalidPage
from django.db.models import Model, Q, QuerySet

from creme.creme_core.utils.dates import DATE_ISO8601_FMT, DATETIME_ISO8601_FMT
from creme.creme_core.utils.db import populate_related
from creme.creme_core.utils.meta import FieldInfo

logger = logging.getLogger(__name__)
_FORWARD = 'forward'
_BACKWARD = 'backward'


class FirstPage(InvalidPage):
    pass


class LastPage(InvalidPage):
    pass


class FlowPaginator:
    """Paginates a Queryset on CremeEntities.

    It should be fast on big databases, because it avoids SQL's OFFSET most of the time,
    because we use a KEYSET way (eg: the page is the X first items with name >= "foobar").
    Disadvantage is that you can only go to the next & previous pages.

    Beware: if you use a nullable key, NULL values must be ordered as the lowest values
            (i.e. first in ASC order, last in DESC order).
            Tip: you can use 'creme.models.manager.LowNullsQuerySet'.
    """
    queryset: QuerySet

    _per_page: int
    _count: int
    _key_field_info: FieldInfo
    _key: str
    _attr_name: str
    _reverse_order: bool

    def __init__(self, queryset: QuerySet, key: str, per_page: int, count: int = sys.maxsize):
        """Constructor.
        @param queryset: QuerySet instance.
               Beware #1: lines must have always the same order when sub-set
                queries are performed, or the paginated content won't be consistent.
                Tip: use the 'PK' as the (last) ordering field.
               Beware #2: the Queryset must contain real instances, not tuples
                or dicts (i.e. it is not compatible with QuerySets returned by
                the methods 'values()' & 'values_list()').
        @param key: Name of the field used as key (i.e. first ordering field).
               It can be a composed field name like 'user__username'.
               For ForeignKeys, you must use:
                - the low-level attribute (e.g. 'myfk' => 'myfk_id').
                - an order-able subfield's name (e.g. 'myfk__title).
               ManyToManyFields are not managed.
        @param per_page: Number of entities.
        @param count: Total number of entities (ie should be equal to object_list.count())
               (so no additional query is performed to get it).
               The default value _should_ be overridden with the correct value;
               it is only useful when a whole queryset is iterated with pages()
               (because count is not used).
        @raise ValueError: If key is invalid.
        """
        assert per_page > 1

        # TODO: check the order is stable & compatible with key.
        if not queryset.ordered:
            raise ValueError('The Queryset must be ordered')

        self.queryset = queryset
        self.per_page = per_page
        self.count = count
        self._num_pages: int | None = None

        self._attr_name: str = ''  # TODO: rename "attr_nameS"?
        self._reverse_order: bool = False
        self.key = key

    @property
    def attr_name(self) -> str:
        return self._attr_name

    @property
    def reverse_order(self) -> bool:
        return self._reverse_order

    @property
    def count(self) -> int:
        return self._count

    @count.setter
    def count(self, value):
        self._count = int(value)

    @property
    def key(self) -> str:
        return self._key

    @key.setter
    def key(self, value: str) -> None:
        self._key = value

        if value.startswith('-'):
            attr_name = value[1:]
            self._reverse_order = True
        else:
            attr_name = value
            self._reverse_order = False

        field_info = FieldInfo(self.queryset.model, attr_name)

        if any(f.many_to_many for f in field_info):
            raise ValueError('Invalid key: ManyToManyFields cannot be used as key.')

        # TODO: if related_model is not None ?
        last_field = field_info[-1]

        # TODO: other check?
        # NB: if the attribute name is different, it means the user talks
        #     about the low-level value "stuff_id", not the ForeignKey "stuff".
        # TODO: make a better API for that in FieldInfo?
        if last_field.is_relation and last_field.name == field_info.attname(-1):
            raise ValueError(
                f'Invalid key: last sub-field "{last_field}" seems to be a '
                f'ForeignKey & cannot be used as key (not order-able). '
                f'Hint: use a the raw field ("myfk_id") or a subfield ("myfk__name").'
            )

        self._attr_name = attr_name
        self._key_field_info = field_info

    def last_page(self):
        return self.page({'type': 'last', 'key': self.key})

    # TODO: 'allow_empty_first_page' feature like in django.core.paginator.Paginator
    @property
    def num_pages(self) -> int:
        """
        Returns the total number of pages.
        """
        if self._num_pages is None:
            self._num_pages = int(ceil(self.count / self.per_page))

        return self._num_pages

    @property
    def per_page(self) -> int:
        return self._per_page

    @per_page.setter
    def per_page(self, value):
        self._per_page = int(value)

    def _check_key_info(self, page_info: dict) -> None:
        try:
            info_key = page_info['key']
        except KeyError as e:
            raise InvalidPage('Missing "key".') from e
        else:
            if info_key != self.key:
                raise InvalidPage('Invalid "key" (different from paginator key).')

    @staticmethod
    def _offset_from_info(page_info: dict) -> int:
        try:
            offset = int(page_info.get('offset', 0))
        except ValueError as e:
            raise InvalidPage('Invalid "offset" (not integer).') from e

        if offset < 0:
            raise InvalidPage('Invalid "offset" (negative) .')

        return offset

    def _get_qs(self, page_info: dict, reverse: bool) -> QuerySet:
        value = page_info['value']
        attr_name = self._attr_name

        if value is None:
            q = Q(**{attr_name + '__isnull': True}) if reverse else Q()
        else:
            op = '__lte' if reverse else '__gte'
            q = Q(**{attr_name + op: value})

            if reverse and any(f.null for f in self._key_field_info):
                q |= Q(**{attr_name + '__isnull': True})

        try:
            qs = self.queryset.filter(q)
        except (ValueError, ValidationError) as e:
            raise InvalidPage(f'Invalid "value" [{e}].') from e

        return qs

    def get_page(self, page_info=None) -> FlowPage:
        if page_info is not None and not isinstance(page_info, dict):
            page_obj = self.page()
        else:
            try:
                page_obj = self.page(page_info)
            except LastPage:
                page_obj = self.last_page()
            except FirstPage:
                page_obj = self.page()
            except InvalidPage:
                logger.exception('FlowPagination.get_page(): invalid page')
                page_obj = self.page()

        return page_obj

    def page(self, page_info: dict | None = None) -> FlowPage:
        """Get the wanted page.
        @param page_info: A dictionary returned by the methods
                          info()/next_page_info()/previous_page_info() of a page,
                          or None (which means 'first page').
        @return An instance of FlowPage.

        @raise FirstPage: the first page has been reached when going backward
               (the page could be not complete).
        @raise LastPage: it seems that the last page has been exceeded
               (this page is empty).
        @raise InvalidPage: page_info is invalid.

        @see FlowPage.info()
        """
        if page_info is None:
            page_info = {'type': 'first'}

        per_page = self._per_page
        offset = 0
        forward = True
        first_page = False
        move_type = page_info.get('type')

        # PyCharm does not understand that it's not a problem to use list
        # methods in local contexts...
        # entities: Iterable[Model]

        if move_type == 'first' or self.count <= per_page:
            entities = [*self.queryset[:per_page + 1]]
            next_item = None if len(entities) <= per_page else entities.pop()
            first_page = True
        elif move_type == 'last':
            self._check_key_info(page_info)

            entities = reversed(self.queryset.reverse()[:per_page])
            next_item = None
            forward = False
        else:
            self._check_key_info(page_info)

            offset = self._offset_from_info(page_info)

            if move_type == _FORWARD:
                qs = self._get_qs(page_info, reverse=self._reverse_order)
                entities = [*qs[offset:offset + per_page + 1]]
                next_item = None if len(entities) <= per_page else entities.pop()

                if not entities:
                    raise LastPage()
            elif move_type == _BACKWARD:
                qs = self._get_qs(page_info, reverse=not self._reverse_order)

                # NB: we get 2 additional items:
                #  - 1 will be the next_item of the page.
                #  - if the second one exists, it indicates that there is at
                #    least one item before the page (so it is not the first one).
                size = per_page + 2
                entities = [*qs.reverse()[offset:offset + size]]

                if len(entities) != size:
                    raise FirstPage()

                entities.pop()
                entities.reverse()
                next_item = entities.pop()

                if self._key_field_info.value_from(entities[-1]) != page_info['value']:
                    offset = 0

                forward = False
            else:
                raise InvalidPage('Invalid or missing "type".')

        return FlowPage(
            object_list=entities, paginator=self, forward=forward,
            key=self._key, key_field_info=self._key_field_info,
            attr_name=self._attr_name,
            offset=offset, max_size=per_page,
            next_item=next_item, first_page=first_page,
        )

    def pages(self) -> Iterator[FlowPage]:
        page = self.page()

        while True:
            yield page

            if not page.has_next():
                break

            try:
                page = self.page(page.next_page_info())
            except LastPage:
                break


class FlowPage(Sequence):
    def __init__(self,
                 object_list: Iterable[Model],
                 paginator: FlowPaginator,
                 forward: bool,
                 key: str, key_field_info: FieldInfo, attr_name: str,
                 offset: int, max_size: int,
                 next_item: Model | None,
                 first_page: bool,
                 ):
        """Constructor.
        Do not use it directly ; use FlowPaginator.page().

        @param object_list: Iterable of model instances.
        @param paginator: A paginator with the following attribute: queryset.
        @param forward: Boolean ; True=>forward ; False=>backward.
        @param key: See FlowPaginator.
        @param key_field_info: Instance of FieldInfo corresponding to the key.
        @param attr_name: (Composite) attribute name corresponding to the key
               (i.e. key without the '-' prefix).
        @param offset: Positive integer indicating the offset used with the key
               to get the object_list.
        @param max_size: Maximum size of pages with the paginator.
        @param next_item: First item of the next page ; 'None' if it's the last page.
        @param first_page: Indicates if it's the first page (so there is no previous page).
        """
        # QuerySets do not manage negative indexing, so we build a list.
        self.object_list: list[Model] = [*object_list]
        self.paginator = paginator
        self._key = key
        self._key_field_info = key_field_info
        self._attr_name = attr_name
        self._offset = offset
        self._max_size = max_size
        self._forward = forward
        self._next_item = next_item
        self._first_page = bool(first_page)

    def __repr__(self):
        return f'<Page key={self._key} offset={self._offset} items[0]={self[0]}>'

    def __len__(self):
        return len(self.object_list)

    def __getitem__(self, index) -> Model:
        return self.object_list[index]

    # NB: 'maxsize=None' => avoid locking (will only be used with the same value)
    @lru_cache(maxsize=None)
    def _get_duplicates_count(self, value) -> int:
        return self.paginator.queryset.filter(**{self._attr_name: value}).count()

    def has_next(self) -> bool:
        return self._next_item is not None

    def has_previous(self) -> bool:
        return not self._first_page

    def has_other_pages(self) -> bool:
        return self.has_previous() or self.has_next()

    @staticmethod
    def _serialize_value(value):
        if isinstance(value, date):
            return value.strftime(
                DATETIME_ISO8601_FMT
                if isinstance(value, datetime) else
                DATE_ISO8601_FMT
            )

        if isinstance(value, Decimal):
            return str(value)

        return value

    def info(self) -> dict:
        """Returns a dictionary which can be given to FlowPaginator.page() to
        get this page again.
        This dictionary can be natively serialized to JSON.

        You do not have to understand the content on this dictionary ;
        you can just use it with FlowPaginator.page().

        Internal information:
        The dictionary contains the following items:
            'type': string in {'first', 'last', 'forward', 'backward'}.
            'key':  [not with 'first' type] field name used as key.
            'value': [not with 'first'/'last' types] value of the key.
            'offset': [optional & only with 'forward'/'backward' types] a
                      positive integer.
                      When this item is missing, it is considered to be 0.

        Behavior of 'type' (X == max_size)
        (notice that objects order is the paginator.queryset's order):
            - 'first': first page, the content is the X first objects.
            - 'last': last page, the content is the X last objects.
            - 'forward': forward mode, the content is the X first objects
               where object.key >= value.
               Offset behaviour: if offset==1, the first object will be the 2nd object with
               object.key >= value ; if offset==2, it will be the 3rd. etc...
            - 'backward': backward mode, the content is the X last objects
               where object.key <= value.
               Offset behaviour: with offset==0, the last item is ignored (because it is
               the first item of the next page) ;
               so with offset==1, we ignore the _2_ last items, etc...
        """
        if not self.has_previous():
            return {'type': 'first'}

        if not self.has_next():
            return {'type': 'last', 'key': self._key}

        if self._forward:
            move_type = _FORWARD
            value_item = self.object_list[0]
        else:
            move_type = _BACKWARD
            value_item = self._next_item

        return self._build_info(
            move_type,
            offset=self._offset,
            value=self._key_field_info.value_from(value_item),
        )

    def _build_info(self, move_type: str, value, offset) -> dict:
        info = {'type': move_type, 'key': self._key, 'value': self._serialize_value(value)}

        if offset:
            info['offset'] = offset

        return info

    def _compute_offset(self, value, objects) -> int:
        """Count the number of key duplicates.
        @param value: Value of the key for the reference object.
        @param objects: Iterable ; instances to evaluate.
        """
        offset = 0
        value_from = self._key_field_info.value_from

        for elt in objects:
            if value != value_from(elt):
                break

            offset += 1

        return offset

    def next_page_info(self) -> dict | None:
        """Returns a dictionary which can be given to FlowPaginator.page() to get the next page.

        @see info()
        Internal information ; notice that 'type' will always be 'forward'.
        """
        next_item = self._next_item

        if next_item is not None:
            populate_related([next_item, *self.object_list], (self._attr_name,))

            value = self._key_field_info.value_from(next_item)
            offset = self._compute_offset(value, reversed(self.object_list))

            if offset == self._max_size:
                # The duplicates fill this page & there can be some duplicates
                # on the previous page(s)
                if self._forward:
                    # Offsets are in the same direction (forward) => we accumulate them
                    offset += self._offset
                else:
                    # NB: it's easy to see (with a sketch) that
                    #     duplicates_count = forward_offset + backward_offset + 1
                    #     (with here forward_offset == offset & backward_offset == self._offset)
                    offset = self._get_duplicates_count(value) - self._offset - 1

            return self._build_info(_FORWARD, value, offset)

        return None

    def previous_page_info(self) -> dict | None:
        """Returns a dictionary which can be given to FlowPaginator.page()
        to get the previous page.

        @see info()
        Internal information ; notice that 'type' will always be 'backward'.
        """
        if self.has_previous():
            populate_related(self.object_list, (self._attr_name,))

            object_iter = iter(self.object_list)
            value = self._key_field_info.value_from(next(object_iter))
            offset = self._compute_offset(value, object_iter)

            if offset == self._max_size - 1:  # NB: _max_size > 1
                # The duplicates fill this page & there can be some duplicates on the next page(s)
                if self._forward:
                    # NB: it's easy to see (with a sketch) that
                    #     duplicates_count = forward_offset + backward_offset + 1
                    #     (with here forward_offset == self._offset  & backward_offset == offset)
                    offset = self._get_duplicates_count(value) - self._offset - 1
                elif self._offset:
                    # Offsets are in the same direction (backward) => we cumulate them
                    offset += self._offset + 1

            return self._build_info(_BACKWARD, value, offset)

        return None
