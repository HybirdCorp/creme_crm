# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2019  Hybird
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

from collections import defaultdict
import logging

from creme.creme_core.core.entity_cell import (EntityCellRegularField,
        EntityCellFunctionField, EntityCellRelation)
from creme.creme_core.models import RelationType

logger = logging.getLogger(__name__)


class _ModelSmartColumnsRegistry:
    __slots__ = ('_cells', '_relationtype')

    def __init__(self):
        self._cells = []
        self._relationtype = None  # Cache

    # TODO: factorise with json deserialization of EntityCells
    def _get_cells(self, model):
        cells = []

        for cell_cls, data in self._cells:
            cell = None

            if cell_cls is EntityCellRegularField:
                cell = EntityCellRegularField.build(model=model, name=data)
            elif cell_cls is EntityCellFunctionField:
                cell = EntityCellFunctionField.build(model, func_field_name=data)
            else:  # EntityCellRelation
                rtype = self._get_relationtype(data)

                if rtype is False:
                    logger.warning('SmartColumnsRegistry: relation type "%s" does not exist', data)
                else:
                    cell = EntityCellRelation(model=model, rtype=rtype)

            # Has no sense here:
            #  EntityCellActions : not configurable in HeaderFilter form
            #  EntityCellCustomField : dynamically created by user
            # TODO: other types

            if cell is not None:
                cells.append(cell)

        return cells

    def _get_relationtype(self, rtype_id):
        rtype = self._relationtype

        if rtype is None:  # Means: not retrieved yet
            try:
                rtype = RelationType.objects.get(pk=rtype_id)
            except RelationType.DoesNotExist:
                rtype = False  # Means: does not exist

            self._relationtype = rtype

        return rtype

    def register_function_field(self, func_field_name):
        self._cells.append((EntityCellFunctionField, func_field_name))
        return self

    def register_field(self, field_name):
        self._cells.append((EntityCellRegularField, field_name))
        return self

    def register_relationtype(self, rtype_id):
        self._cells.append((EntityCellRelation, rtype_id))
        return self


class SmartColumnsRegistry:
    def __init__(self):
        self._model_registries = defaultdict(_ModelSmartColumnsRegistry)

    def get_cells(self, model):
        return self._model_registries[model]._get_cells(model)

    def register_model(self, model):
        return self._model_registries[model]


smart_columns_registry = SmartColumnsRegistry()
