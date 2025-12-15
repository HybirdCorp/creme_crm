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

    def register_field(self, field_name: str) -> _ModelSmartColumnsRegistry:
        """Register a field by its name."""
        self._cells.append((EntityCellRegularField, field_name))
        return self

    def register_function_field(self, func_field_name: str) -> _ModelSmartColumnsRegistry:
        """Register a function field by its name."""
        self._cells.append((EntityCellFunctionField, func_field_name))
        return self

    def register_relationtype(self, rtype_id: str) -> _ModelSmartColumnsRegistry:
        """Register a RelationType by its ID."""
        self._cells.append((EntityCellRelation, rtype_id))
        return self

    def _unregister(self, cell_type, cell_name, error_message) -> _ModelSmartColumnsRegistry:
        try:
            self._cells.remove((cell_type, cell_name))
        except ValueError as e:
            raise ValueError(error_message.format(cell_name)) from e

        return self

    def unregister_field(self, field_name: str) -> _ModelSmartColumnsRegistry:
        """Unregister a field by its name."""
        return self._unregister(
            cell_type=EntityCellRegularField, cell_name=field_name,
            error_message='The field "{}" in not registered.',
        )

    def unregister_function_field(self, func_field_name: str) -> _ModelSmartColumnsRegistry:
        """Unregister a function field by its name."""
        return self._unregister(
            cell_type=EntityCellFunctionField, cell_name=func_field_name,
            error_message='The function field "{}" in not registered.',
        )

    def unregister_relationtype(self, rtype_id: str) -> _ModelSmartColumnsRegistry:
        """Unregister a RelationType by its ID."""
        return self._unregister(
            cell_type=EntityCellRelation, cell_name=rtype_id,
            error_message='The relation type "{}" in not registered.',
        )


class SmartColumnsRegistry:
    """Registry to indicate with EntityCells should be selected by default by
    the form for HeaderFilters (because these columns are often selected for
    this model).

    Example:
        registry = SmartColumnsRegistry()
        registry.register_model(
            Contact
        ).register_field('last_name').register_field('first_name')
        registry.register_model(
            Organisation
        ).register_field('name').register_relationtype(REL_SUB_PROVIDER)

    Hint: you'll probably use <CremeAppConfig.register_smart_columns()>.
    """
    _model_registries: DefaultDict[type[CremeEntity], _ModelSmartColumnsRegistry]

    def __init__(self):
        self._model_registries = defaultdict(_ModelSmartColumnsRegistry)

    def get_cells(self, model: type[CremeEntity]) -> list[EntityCell]:
        """Get the "smart" cells for a given model."""
        return self._model_registries[model]._get_cells(model)

    # TODO: rename just "model" (because it's used to retrieve existing too)
    def register_model(self, model: type[CremeEntity]) -> _ModelSmartColumnsRegistry:
        """Get the sub-registry containing the registered cells for a given model.
        Useful to register & unregister cells by chaining with:
         - [un]register_field()
         - [un]register_function_field()
         - [un]register_relationtype()
        """
        return self._model_registries[model]

    def clear_model(self, model: type[CremeEntity]) -> None:
        """Remove the sub-registry related to a madel (& so all related cells)."""
        del self._model_registries[model]


smart_columns_registry = SmartColumnsRegistry()
