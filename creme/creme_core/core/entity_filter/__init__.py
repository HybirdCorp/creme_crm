################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019-2025  Hybird
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
from collections import OrderedDict
from collections.abc import Iterator
from typing import TYPE_CHECKING

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from creme.creme_core.models import CremeEntity

    from .condition_handler import FilterConditionHandler
    from .operands import ConditionDynamicOperand
    from .operators import ConditionOperator

logger = logging.getLogger(__name__)
EF_REGULAR = 'creme_core-regular'
EF_CREDENTIALS = 'creme_core-credentials'

TYPE_ID_MAX_LENGTH = 36


class EntityFilterRegistry:
    """A registry which stores information about a type of <models.EntityFilter>.
     (current types: regular, credentials, reports -- with the "reports" app).
     Base information:
       - ID (which is the type of filter too)
       - verbose name
       - tag (optional small name, see below).
       - URLs which works with this type of filter

     These components can be registered:
       - Conditions handlers (this type of filter can filter on regular fields?
         on custom fields? on relationships? etc...) .
       - Operators (for condition on fields, operators like "equals" or "start with").
       - Operands (special operand for condition on fields; used for <current user>).
    """
    class RegistrationError(Exception):
        pass

    id: str
    verbose_name: str
    detail_url_name: str
    edition_url_name: str
    deletion_url_name: str
    tag: str

    def __init__(self, *,
                 id: str, verbose_name: str,
                 detail_url_name: str = '',
                 edition_url_name: str = '',
                 deletion_url_name: str = '',
                 tag: str = '',
                 ):
        """Constructor.
        @param id: A string used to retrieve the registry in the super registry;
               it's used to set the field <EntityFilter.filter_type>.
        @param detail_url_name: Name of the URL which displays details about an
               EntityFilter linked to this registry.
               - The URL pattern must take a filter's ID as unique argument
                 (see method <detail_url()>).
               - An empty string indicates that there is no detail-view for this type.
        @param edition_url_name: Name of the URL which displays a form-view to
               edit an EntityFilter linked to this registry.
               - The URL pattern must take a filter's ID as unique argument
                 (see method <edition_url()>).
               - An empty string indicates that there is no edition view for this type.
        @param deletion_url_name: Name of the URL to delete an EntityFilter
               linked to this registry.
               - The URL pattern must take a filter's ID as unique argument
                 (see method <deletion_url()>).
               - An empty string indicates that there is no deletion view for this type.
               - The view should be a POST view.
        @param tag: Small string used to visually distinguish filter with a special type
               (i.e. not EF_REGULAR).
               - The regular type can use an empty string.
               - The internal types can use an empty string if they are never referenced.
               - Special types (e.g. app "Reports") should use a gettext_lazy() string.
        """
        if len(id) > TYPE_ID_MAX_LENGTH:
            raise ValueError(f'The "id" cannot be longer than {TYPE_ID_MAX_LENGTH}')

        self.id = id
        self.verbose_name = verbose_name
        self.detail_url_name = detail_url_name
        self.edition_url_name = edition_url_name
        self.deletion_url_name = deletion_url_name
        self.tag = tag

        # We keep the registration order for the form.
        self._handler_classes: dict[int, type[FilterConditionHandler]] = OrderedDict()

        self._operator_classes: dict[int, type[ConditionOperator]] = {}
        self._operand_classes: dict[str, type[ConditionDynamicOperand]] = {}

    def detail_url(self, efilter) -> str:
        url_name = self.detail_url_name

        return '' if not url_name else reverse(url_name, args=(efilter.id,))

    def edition_url(self, efilter) -> str:
        url_name = self.edition_url_name

        return '' if not url_name else reverse(url_name, args=(efilter.id,))

    def deletion_url(self, efilter) -> str:
        url_name = self.deletion_url_name

        return '' if not url_name else reverse(url_name, args=(efilter.id,))

    def register_condition_handlers(self,
                                    *classes: type[FilterConditionHandler],
                                    ) -> EntityFilterRegistry:
        """Register classes of handlers.

        @param classes: Classes inheriting
               <creme_core.core.entity_filter.condition_handler.FilterConditionHandler>.
        @return: self (to chain registrations).
        @raises: EntityFilterRegistry.RegistrationError if an ID is duplicated.
        """
        setdefault = self._handler_classes.setdefault

        for cls in classes:
            if setdefault(cls.type_id, cls) is not cls:
                raise self.RegistrationError(
                    f"Duplicated handler's ID (or handler registered twice): {cls.type_id}"
                )

        return self

    def register_operands(self,
                          *classes: type[ConditionDynamicOperand],
                          ) -> EntityFilterRegistry:
        """Register classes of operand.

        @param classes: Classes inheriting
               <creme_core.core.entity_filter.operands.ConditionDynamicOperand>.
        @return: self (to chain registrations).
        @raises: EntityFilterRegistry.RegistrationError if an ID is duplicated.
        """
        setdefault = self._operand_classes.setdefault

        for cls in classes:
            if setdefault(cls.type_id, cls) is not cls:
                raise self.RegistrationError(
                    f"Duplicated operand's ID (or operand registered twice): {cls.type_id}"
                )

        return self

    def register_operators(self,
                           *classes: type[ConditionOperator],
                           ) -> EntityFilterRegistry:
        """Register classes of operator.

        @param classes: Classes inheriting
               <creme_core.core.entity_filter.operators.ConditionOperator>.
        @return: self (to chain registrations).
        @raises: EntityFilterRegistry.RegistrationError if an ID is duplicated.
        """
        setdefault = self._operator_classes.setdefault

        for cls in classes:
            if setdefault(cls.type_id, cls) is not cls:
                raise self.RegistrationError(
                    f"Duplicated operator's ID (or operator registered twice):"
                    f" {cls.type_id}"
                )

        return self

    def get_handler(self, *,
                    type_id: int,
                    model: type[CremeEntity],
                    name: str,
                    data: dict | None,
                    ) -> FilterConditionHandler | None:
        """Get an instance of handler from its ID.

        @param type_id: ID of the handler's class
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
                '%s.get_handler(): no handler class with type_id="%s" found.',
                type(self).__name__, type_id,
            )
            return None

        try:
            return cls.build(efilter_type=self.id, model=model, name=name, data=data)
        except cls.DataError:
            return None

    def get_operand(self, *, type_id: str, user) -> ConditionDynamicOperand | None:
        """Get an instance of operand from its ID.

        @param type_id: ID of the operand's class
               (see attribute <ConditionDynamicOperand.type_id>).
        @param user: instance of <django.contrib.auth.get_user_model()>
        @return: Instance of a class inheriting <ConditionDynamicOperand>,
                 or None if the ID is invalid or not found.
        """
        cls = self._operand_classes.get(type_id) if isinstance(type_id, str) else None
        return None if cls is None else cls(user)

    def get_operator(self, type_id: int) -> ConditionOperator | None:
        """Get an instance of operator from its ID.

        @param type_id: ID of the operator's class
               (see attribute <ConditionOperator.type_id>).
        @return: Instance of a class inheriting <ConditionOperator>,
                 or None if the ID is invalid or not found.
        """
        cls = self._operator_classes.get(type_id)
        return None if cls is None else cls()

    @property
    def handler_classes(self) -> Iterator[type[FilterConditionHandler]]:
        """Iterator on registered handler classes."""
        return iter(self._handler_classes.values())

    def operands(self, user) -> Iterator[ConditionDynamicOperand]:
        """Generator of operand instances."""
        for op_cls in self._operand_classes.values():
            yield op_cls(user)

    @property
    def operators(self) -> Iterator[ConditionOperator]:
        """Generator of operator instances."""
        for op_cls in self._operator_classes.values():
            yield op_cls()


class EntityFilterSuperRegistry:
    """A registry of _EntityFilterRegistry, to manage different types of filter

    You'll probably never instantiate one & just used the global instance
    <entity_filter_registries> (excepted in unit tests).
    """
    class RegistrationError(Exception):
        pass

    class UnRegistrationError(RegistrationError):
        pass

    def __init__(self):
        self._registries = OrderedDict()

    def __getitem__(self, registry_id: str) -> EntityFilterRegistry:
        return self._registries[registry_id]

    def __iter__(self) -> Iterator[EntityFilterRegistry]:
        return iter(self._registries.values())

    def register(self, *registries: EntityFilterRegistry) -> EntityFilterSuperRegistry:
        set_default = self._registries.setdefault

        for registry in registries:
            if set_default(registry.id, registry) is not registry:
                raise self.RegistrationError(
                    f'_EntityFilterSuperRegistry.register(): '
                    f'the ID "{registry.id}" is already used.'
                )

        return self

    def unregister(self, *registry_ids: str) -> None:
        registries = self._registries

        for registry_id in registry_ids:
            try:
                del registries[registry_id]
            except KeyError as e:
                raise self.UnRegistrationError(
                    f'Invalid registry ID "{registry_id}" (already unregistered?)'
                ) from e


entity_filter_registries = EntityFilterSuperRegistry().register(
    EntityFilterRegistry(
        id=EF_CREDENTIALS,
        verbose_name=_('Credentials filter'),
    ),
    EntityFilterRegistry(
        id=EF_REGULAR,
        verbose_name=_('Regular filter (usable in list-view)'),
        detail_url_name='creme_core__efilter',
        edition_url_name='creme_core__edit_efilter',
        deletion_url_name='creme_core__delete_efilter',
    ),
)


# def __getattr__(name):
#     if name == '_EntityFilterRegistry':
#         warnings.warn(
#             '"_EntityFilterRegistry" is deprecated; use "EntityFilterRegistry" instead.',
#             DeprecationWarning,
#         )
#         return EntityFilterRegistry
#
#     if name == '_EntityFilterSuperRegistry':
#         warnings.warn(
#             '"_EntityFilterSuperRegistry" is deprecated;
#             use "EntityFilterSuperRegistry" instead.',
#             DeprecationWarning,
#         )
#         return EntityFilterSuperRegistry
#
#     raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
