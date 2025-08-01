################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from typing import TYPE_CHECKING

from ..models import CremeEntity

if TYPE_CHECKING:
    from typing import Callable, Union

    from ..forms.mass_import import ImportForm

    FormFactory = Union[Callable[[dict, list], ImportForm]]


class FormRegistry:
    """Registry for forms importing entities from CSV/XLS."""
    class RegistrationError(Exception):
        pass

    class UnRegistrationError(RegistrationError):
        pass

    def __init__(self) -> None:
        self._form_factories: dict[type[CremeEntity], FormFactory | None] = {}

    def register(self,
                 model: type[CremeEntity],
                 factory: FormFactory | None = None,
                 ) -> FormRegistry:
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
        factories = self._form_factories

        if model in factories:
            raise self.RegistrationError(f"Model {model} already registered for mass-import")

        factories[model] = factory

        return self

    def unregister(self, model: type[CremeEntity]) -> FormRegistry:
        try:
            del self._form_factories[model]
        except KeyError as e:
            raise self.UnRegistrationError(
                f'Invalid model (already unregistered?): {model}'
            ) from e

        return self

    def __getitem__(self, model: type[CremeEntity]) -> FormFactory | None:
        """@raise KeyError If model is not registered."""
        return self._form_factories[model]

    def __contains__(self, model: type[CremeEntity]) -> bool:
        return model in self._form_factories


import_form_registry = FormRegistry()
