# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from typing import TYPE_CHECKING, Callable, Dict, Optional, Type

from django.contrib.contenttypes.models import ContentType

from ..models import CremeEntity

if TYPE_CHECKING:
    from ..forms.mass_import import ImportForm

FormFactory = Optional[Callable[[dict, list], 'ImportForm']]


class FormRegistry:
    """Registry for forms importing entities from CSV/XLS."""
    class UnregisteredCTypeException(Exception):
        pass

    def __init__(self):
        self._form_factories: Dict[Type[CremeEntity], FormFactory] = {}

    def register(self,
                 model: Type[CremeEntity],
                 factory: FormFactory = None) -> 'FormRegistry':
        """Register a form factory for a model.
        @param model: Class inheriting CremeEntity.
        @param factory: None or callable which takes 2 parameters
               "header_dict" a dictionary key=column slugified name; value=column index
               "choices" a list a choices, compliant with classical django Select widget.
               and which returns a form class which inherits
               <creme_core.forms.mass_import.ImportForm>.
               <None> means that this model uses a generic import form.
        @return The registry instance (to chain register() calls).
        """
        # TODO: check duplicates ?
        self._form_factories[model] = factory

        return self

    def get(self, ct: ContentType) -> FormFactory:  # TODO: accept model directly ??
        try:
            return self._form_factories[ct.model_class()]
        except KeyError as e:
            raise self.UnregisteredCTypeException(
                f'Unregistered ContentType: {ct}'
            ) from e

    def is_registered(self, ct: ContentType) -> bool:
        return ct.model_class() in self._form_factories  # TODO: accept model directly ??


import_form_registry = FormRegistry()
