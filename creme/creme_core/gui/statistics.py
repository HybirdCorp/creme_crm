################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2025  Hybird
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
# import warnings
from collections.abc import Callable

StatisticsFunc = Callable[[], list]
logger = logging.getLogger(__name__)


class StatisticRegistry:
    __slots__ = ('_items',)

    class _StatisticsItem:
        __slots__ = ('id', 'label', 'retrieve', 'perm', '_priority')

        def __init__(self,
                     id: str,
                     label: str,
                     func: StatisticsFunc,
                     perm: str,
                     ):
            self.id = id
            self.label = label
            self.retrieve = func
            self.perm = perm
            self._priority: int = 1

    _items: list[_StatisticsItem]

    def __init__(self):
        self._items = []

    def __iter__(self):
        return iter(self._items)

    def _add_item(self,
                  new_item: _StatisticsItem,
                  priority: int | None,
                  ) -> StatisticRegistry:
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

    def _pop_item(self, item_id: str) -> _StatisticsItem | None:
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
                 priority: int | None = None,
                 ) -> StatisticRegistry:
        if any(id == item.id for item in self._items):
            # TODO: self.RegistrationError ?
            raise ValueError(f'Duplicated id "{id}"')

        return self._add_item(
            self._StatisticsItem(id=id, label=label, func=func, perm=perm),
            priority=priority,
        )


statistic_registry = StatisticRegistry()


# def __getattr__(name):
#     if name == '_StatisticsRegistry':
#         warnings.warn(
#             '"_StatisticsRegistry" is deprecated; use "StatisticRegistry" instead.',
#             DeprecationWarning,
#         )
#         return StatisticRegistry
#
#     if name == 'statistics_registry':
#         warnings.warn(
#             '"statistics_registry" is deprecated; use "statistic_registry" instead.',
#             DeprecationWarning,
#         )
#         return statistic_registry
#
#     raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
