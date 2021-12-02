# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2021  Hybird
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

import logging
from typing import Callable, List, Optional

StatisticsFunc = Callable[[], list]
logger = logging.getLogger(__name__)


class _StatisticsRegistry:
    __slots__ = ('_items',)

    class _StatisticsItem:
        __slots__ = ('id', 'label', 'retrieve', 'perm', '_priority')

        def __init__(self,
                     id: str,
                     label: str,
                     func: StatisticsFunc,
                     perm: str):
            self.id = id
            self.label = label
            self.retrieve = func
            self.perm = perm
            self._priority: int = 1

    _items: List[_StatisticsItem]

    def __init__(self):
        self._items = []

    def __iter__(self):
        return iter(self._items)

    def _add_item(self,
                  new_item: _StatisticsItem,
                  priority: Optional[int]) -> '_StatisticsRegistry':
        items = self._items

        if priority is None:
            priority = items[-1]._priority if items else 1
            items.append(new_item)
        else:
            for i, item in enumerate(items):
                if item._priority > priority:
                    items.insert(i, new_item)
                    break
            else:
                items.append(new_item)

        new_item._priority = priority

        return self

    def _pop_item(self, item_id: str) -> Optional[_StatisticsItem]:
        items = self._items
        for i, item in enumerate(items):
            if item.id == item_id:
                return items.pop(i)

        logger.warning('Item with id=%s not found', item_id)

        return None

    def change_priority(self, priority: int, *item_ids: str) -> None:
        for item_id in item_ids:
            item = self._pop_item(item_id)

            if item is not None:
                self._add_item(item, priority)

    def remove(self, *item_ids: str) -> None:
        for item_id in item_ids:
            self._pop_item(item_id)

    def register(self,
                 id: str,
                 label: str,
                 func: StatisticsFunc,
                 perm: str = '',
                 priority: Optional[int] = None,
                 ) -> '_StatisticsRegistry':
        if any(id == item.id for item in self._items):
            # TODO: self.RegistrationError ?
            raise ValueError(f'Duplicated id "{id}"')

        return self._add_item(
            self._StatisticsItem(id=id, label=label, func=func, perm=perm),
            priority=priority,
        )


statistics_registry = _StatisticsRegistry()
