################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020-2025  Hybird
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
from collections.abc import Iterator
from typing import TYPE_CHECKING

from django.utils.translation import gettext_lazy as _

from .core.graph.fetcher import GraphFetcher, SimpleGraphFetcher

if TYPE_CHECKING:
    from .models import AbstractReportGraph

logger = logging.getLogger(__name__)


class GraphFetcherRegistry:
    class RegistrationError(Exception):
        pass

    def __init__(self, default_class: type[GraphFetcher]):
        self._fetcher_classes: dict[str, type[GraphFetcher]] = {}
        self.default_class = default_class

    def _build_default_fetcher(self, graph):
        fetcher = self.default_class(graph=graph)
        fetcher.error = _('Invalid volatile link; please contact your administrator.')

        return fetcher

    def register(self, *fetcher_classes: type[GraphFetcher]) -> GraphFetcherRegistry:
        set_default = self._fetcher_classes.setdefault

        for fetcher_cls in fetcher_classes:
            if set_default(fetcher_cls.type_id, fetcher_cls) is not fetcher_cls:
                raise self.RegistrationError(
                    f'{type(self).__name__}.register(): '
                    f'the ID "{fetcher_cls.type_id}" is already used'
                    f'(trying to register class {fetcher_cls}).'
                )

        return self

    def get(self,
            graph: AbstractReportGraph,
            fetcher_dict: dict[str, str]) -> GraphFetcher:
        try:
            fetcher_type_id = fetcher_dict[GraphFetcher.DICT_KEY_TYPE]
        except KeyError:
            logger.warning(
                '%s.get(): no fetcher ID given (basic fetcher is used).',
                type(self).__name__,
            )

            return self._build_default_fetcher(graph)
        else:
            fetcher_cls = self._fetcher_classes.get(fetcher_type_id)

            if fetcher_cls is None:
                logger.warning(
                    '%s.get(): invalid ID "%s" for fetcher (basic fetcher is used).',
                    type(self).__name__, fetcher_type_id,
                )

                return self._build_default_fetcher(graph)

        return fetcher_cls(
            graph=graph,
            value=fetcher_dict.get(GraphFetcher.DICT_KEY_VALUE),
        )

    @property
    def fetcher_classes(self) -> Iterator[type[GraphFetcher]]:
        return iter(self._fetcher_classes.values())


graph_fetcher_registry = GraphFetcherRegistry(SimpleGraphFetcher)
