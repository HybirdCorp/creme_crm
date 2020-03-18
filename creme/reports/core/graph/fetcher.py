# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2020  Hybird
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
from typing import Optional, List, Tuple

from django.utils.translation import gettext_lazy as _, gettext
from django.db.models import FieldDoesNotExist, ForeignKey, Q

from creme.creme_core.models import (
    CremeEntity,
    RelationType,
)
from creme.creme_core.utils.meta import FieldInfo

logger = logging.getLogger(__name__)


# TODO: use a map/registry of GraphFetcher classes, and use it in get_fetcher_from_instance_brick()
#       and in ReportGraph form to build choices.
class GraphFetcher:
    """A graph fetcher can fetch the result of a given ReportGraph, with or without
    a volatile link.
    It stores the verbose name of this link (for UI), and an error if the link data
    were invalid.
    """
    def __init__(self, graph):
        self.graph = graph
        self.error: Optional[str] = None
        self.verbose_volatile_column: str = _('No volatile column')

    def fetch(self, user, order: str = 'ASC') -> Tuple[List[str], list]:
        return self.graph.fetch(user=user, order=order)

    def _aux_fetch_4_entity(self,
                            entity: CremeEntity,
                            user,
                            order: str):
        "To be overload in child classes."
        return self.fetch(user=user, order=order)

    def fetch_4_entity(self,
                       entity: CremeEntity,
                       user,
                       order: str = 'ASC') -> Tuple[List[str], list]:
        return ([], []) \
               if self.error else \
               self._aux_fetch_4_entity(entity=entity, user=user, order=order)

    @property
    def verbose_name(self) -> str:
        return f'{self.graph} - {self.verbose_volatile_column}'


class RegularFieldLinkedGraphFetcher(GraphFetcher):
    def __init__(self, field_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        model = self.graph.model
        # self.field_name = None
        self._field_name = None
        self.verbose_volatile_column = '??'

        try:
            field = model._meta.get_field(field_name)
        except FieldDoesNotExist:
            logger.warning('Instance block: invalid field %s.%s in block config.',
                           model.__name__, field_name,
                          )
            self.error = _('The field is invalid.')
        else:
            if isinstance(field, ForeignKey):
                self.verbose_volatile_column = gettext('{field} (Field)').format(field=field.verbose_name)
                self._field_name = field_name
                self._volatile_model = field.remote_field.model
            else:
                logger.warning('Instance block: field %s.%s in block config is not a FK.',
                               model.__name__, field_name,
                              )
                self.error = _('The field is invalid (not a foreign key).')

    def _aux_fetch_4_entity(self, entity, order, user):
        return self.graph.fetch(extra_q=Q(**{self._field_name: entity.pk}), order=order, user=user) \
               if isinstance(entity, self._volatile_model) else \
               ([], [])

    @staticmethod
    def validate_fieldname(graph, field_name):
        try:
            field_info = FieldInfo(graph.model, field_name)
        except FieldDoesNotExist:
            return f'invalid field "{field_name}"'

        if len(field_info) > 1:
            return f'field "{field_name}" with deep > 1'

        field = field_info[0]

        if not (isinstance(field, ForeignKey) and issubclass(field.remote_field.model, CremeEntity)):
            return f'field "{field_name}" is not a ForeignKey to CremeEntity'


class RelationLinkedGraphFetcher(GraphFetcher):
    def __init__(self, rtype_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            rtype = RelationType.objects.get(pk=rtype_id)
        except RelationType.DoesNotExist:
            logger.warning('Instance block: invalid RelationType "%s" in block config.',
                           rtype_id,
                          )
            self.error = _('The relationship type is invalid.')
            self.verbose_volatile_column = '??'
        else:
            self.verbose_volatile_column = gettext('{rtype} (Relationship)').format(rtype=rtype)
            self._rtype = rtype

    def _aux_fetch_4_entity(self, entity, order, user):
        return self.graph.fetch(
            extra_q=Q(
                relations__type=self._rtype,
                relations__object_entity=entity.pk,
            ),
            user=user,
            order=order,
        )
