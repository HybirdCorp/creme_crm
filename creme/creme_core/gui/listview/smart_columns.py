################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2025  Hybird
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
from collections import defaultdict
from typing import DefaultDict, Literal

from creme.creme_core.core.entity_cell import (
    EntityCell,
    EntityCellFunctionField,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.models import CremeEntity, RelationType

logger = logging.getLogger(__name__)


class _ModelSmartColumnsRegistry:
    __slots__ = ('_cells', '_relationtype')

    def __init__(self) -> None:
        self._cells: list[tuple[type[EntityCell], str]] = []
        self._relationtype: RelationType | None | Literal[False] = None  # Cache

    # TODO: factorise with json deserialization of EntityCells
    def _get_cells(self, model: type[CremeEntity]) -> list[EntityCell]:
        cells: list[EntityCell] = []

        for cell_cls, data in self._cells:
            cell = None

            if cell_cls is EntityCellRegularField:
                cell = EntityCellRegularField.build(model=model, name=data)
            elif cell_cls is EntityCellFunctionField:
                # cell = EntityCellFunctionField.build(model, func_field_name=data)
                cell = EntityCellFunctionField.build(model, name=data)
            else:  # EntityCellRelation
                rtype = self._get_relationtype(data)

                if rtype is False:
                    logger.warning('SmartColumnsRegistry: relation type "%s" does not exist', data)
                else:
                    assert isinstance(rtype, RelationType)
                    cell = EntityCellRelation(model=model, rtype=rtype)

            # Has no sense here:
            #  EntityCellActions : not configurable in HeaderFilter form
            #  EntityCellCustomField : dynamically created by user
            # TODO: other types

            if cell is not None:
                cells.append(cell)

        return cells

    def _get_relationtype(self, rtype_id: str) -> RelationType | Literal[False]:
        rtype = self._relationtype

        if rtype is None:  # Means: not retrieved yet
            try:
                rtype = RelationType.objects.get(pk=rtype_id)
            except RelationType.DoesNotExist:
                rtype = False  # Means: does not exist

            self._relationtype = rtype

        return rtype

    def register_function_field(self, func_field_name: str) -> _ModelSmartColumnsRegistry:
        self._cells.append((EntityCellFunctionField, func_field_name))
        return self

    def register_field(self, field_name: str) -> _ModelSmartColumnsRegistry:
        self._cells.append((EntityCellRegularField, field_name))
        return self

    def register_relationtype(self, rtype_id: str) -> _ModelSmartColumnsRegistry:
        self._cells.append((EntityCellRelation, rtype_id))
        return self


class SmartColumnsRegistry:
    def __init__(self) -> None:
        self._model_registries: \
            DefaultDict[type[CremeEntity], _ModelSmartColumnsRegistry] \
            = defaultdict(_ModelSmartColumnsRegistry)

    def get_cells(self, model: type[CremeEntity]) -> list[EntityCell]:
        return self._model_registries[model]._get_cells(model)

    def register_model(self, model: type[CremeEntity]) -> _ModelSmartColumnsRegistry:
        return self._model_registries[model]


smart_columns_registry = SmartColumnsRegistry()
