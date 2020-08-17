# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019-2020  Hybird
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
from collections import OrderedDict
from typing import TYPE_CHECKING, Dict, Iterator, Optional, Type

if TYPE_CHECKING:
    from creme.creme_core.models import CremeEntity

    from .condition_handler import FilterConditionHandler
    from .operands import ConditionDynamicOperand
    from .operators import ConditionOperator

logger = logging.getLogger(__name__)
EF_CREDENTIALS = 0
EF_USER = 1


class _EntityFilterRegistry:
    """Registry about EntityFilter components:
     - Conditions handlers.
     - Operators.
     - Operands.
    """
    class RegistrationError(Exception):
        pass

    id: int
    verbose_name: str

    def __init__(self, *, id: int, verbose_name: str):
        self.id = id
        self.verbose_name = verbose_name

        # We keep the registration order for the form.
        self._handler_classes: Dict[int, Type['FilterConditionHandler']] = OrderedDict()

        self._operator_classes: Dict[int, Type['ConditionOperator']] = {}
        self._operand_classes: Dict[str, Type['ConditionDynamicOperand']] = {}

    def register_condition_handlers(
            self,
            *classes: Type['FilterConditionHandler']) -> '_EntityFilterRegistry':
        """Register classes of handlers.

        @param classes: Classes inheriting
               <creme_core.core.entity_filter.condition_handler.FilterConditionHandler>.
        @return: self (to chain registrations).
        @raises: _EntityFilterRegistry.RegistrationError if an ID is duplicated.
        """
        setdefault = self._handler_classes.setdefault

        for cls in classes:
            if setdefault(cls.type_id, cls) is not cls:
                raise self.RegistrationError(
                    f"Duplicated handler's ID (or handler registered twice): {cls.type_id}"
                )

        return self

    def register_operands(
            self,
            *classes: Type['ConditionDynamicOperand']) -> '_EntityFilterRegistry':
        """Register classes of operand.

        @param classes: Classes inheriting
               <creme_core.core.entity_filter.operands.ConditionDynamicOperand>.
        @return: self (to chain registrations).
        @raises: _EntityFilterRegistry.RegistrationError if an ID is duplicated.
        """
        setdefault = self._operand_classes.setdefault

        for cls in classes:
            if setdefault(cls.type_id, cls) is not cls:
                raise self.RegistrationError(
                    f"Duplicated operand's ID (or operand registered twice): {cls.type_id}"
                )

        return self

    def register_operators(
            self,
            *classes: Type['ConditionOperator']) -> '_EntityFilterRegistry':
        """Register classes of operator.

        @param classes: Classes inheriting
               <creme_core.core.entity_filter.operators.ConditionOperator>.
        @return: self (to chain registrations).
        @raises: _EntityFilterRegistry.RegistrationError if an ID is duplicated.
        """
        setdefault = self._operator_classes.setdefault

        for cls in classes:
            if setdefault(cls.type_id, cls) is not cls:
                raise self.RegistrationError(
                    f"Duplicated operator's ID (or operator registered twice):"
                    f" {cls.type_id}"
                )

        return self

    def get_handler(
            self, *,
            type_id: int,
            model: Type['CremeEntity'],
            name: str,
            data: Optional[dict]) -> Optional['FilterConditionHandler']:
        """Get an instance of handler from its ID.

        @param type_id: Id of the handler's class
               (see attribute <FilterConditionHandler.type_id>).
        @param model: Class inheriting of <creme_core.models.CremeEntity>.
        @param name: Name of the handler.
        @param data: Data of the handler.
        @return: Instance of a class inheriting <FilterConditionHandler>,
                 or None if the ID is not found, or if data are invalid.
        """
        try:
            cls = self._handler_classes[type_id]
        except KeyError:
            logger.warning(
                '_EntityFilterRegistry.get_handler(): no handler class with type_id="%s" found.',
                type_id,
            )
            return None

        try:
            return cls.build(model=model, name=name, data=data)
        except cls.DataError:
            return None

    def get_operand(self, *, type_id: str, user) -> Optional['ConditionDynamicOperand']:
        """Get an instance of operand from its ID.

        @param type_id: Id of the operand's class
               (see attribute <ConditionDynamicOperand.type_id>).
        @param user: instance of <django.contrib.auth.get_user_model()>
        @return: Instance of a class inheriting <ConditionDynamicOperand>,
                 or None if the ID is invalid or not found.
        """
        cls = self._operand_classes.get(type_id) if isinstance(type_id, str) else None
        return None if cls is None else cls(user)

    def get_operator(self, type_id: int) -> Optional['ConditionOperator']:
        """Get an instance of operator from its ID.

        @param type_id: Id of the operator's class
               (see attribute <ConditionOperator.type_id>).
        @return: Instance of a class inheriting <ConditionOperator>,
                 or None if the ID is invalid or not found.
        """
        cls = self._operator_classes.get(type_id)
        return None if cls is None else cls()

    @property
    def handler_classes(self) -> Iterator[Type['FilterConditionHandler']]:
        """Iterator on registered handler classes."""
        return iter(self._handler_classes.values())

    def operands(self, user) -> Iterator['ConditionDynamicOperand']:
        """Generator of operand instances."""
        for op_cls in self._operand_classes.values():
            yield op_cls(user)

    @property
    def operators(self) -> Iterator['ConditionOperator']:
        """Generator of operator instances."""
        for op_cls in self._operator_classes.values():
            yield op_cls()


class _EntityFilterSuperRegistry:
    class RegistrationError(Exception):
        pass

    def __init__(self):
        self._registries = OrderedDict()

    def __getitem__(self, registry_id: int) -> _EntityFilterRegistry:
        return self._registries[registry_id]

    def __iter__(self) -> Iterator[_EntityFilterRegistry]:
        return iter(self._registries.values())

    def register(self, *registries: _EntityFilterRegistry) -> '_EntityFilterSuperRegistry':
        set_default = self._registries.setdefault

        for registry in registries:
            if set_default(registry.id, registry) is not registry:
                raise self.RegistrationError(
                    f'_EntityFilterSuperRegistry.register(): '
                    f'the ID "{registry.id}" is already used.'
                )

        return self

    def unregister(self, *registry_ids: int) -> None:
        registries = self._registries

        for registry_id in registry_ids:
            del registries[registry_id]


entity_filter_registries = _EntityFilterSuperRegistry().register(
    _EntityFilterRegistry(
        id=EF_CREDENTIALS,
        verbose_name='Credentials filter (internal use)',
    ),
    _EntityFilterRegistry(
        id=EF_USER,
        verbose_name='Regular filter (usable in list-view...',
    ),
)
