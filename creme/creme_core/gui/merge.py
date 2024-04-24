################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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

from creme.creme_core.models import CremeEntity

if TYPE_CHECKING:
    from typing import Callable, KeysView, Type

    from creme.creme_core.forms.merge import MergeEntitiesBaseForm

    FormFactory = Callable[[], Type[MergeEntitiesBaseForm]]


class _MergeFormRegistry:
    """Registry for forms uses to merge entities."""
    class RegistrationError(Exception):
        pass

    class UnRegistrationError(RegistrationError):
        pass

    def __init__(self) -> None:
        self._form_factories: dict[type[CremeEntity], FormFactory] = {}

    def __contains__(self, model: type[CremeEntity]) -> bool:
        return model in self._form_factories

    def register(self,
                 model: type[CremeEntity],
                 form_factory: FormFactory,
                 ) -> _MergeFormRegistry:
        """Register a form factory for a model.
        @param model: Class inheriting CremeEntity.
        @param form_factory: A callable with no parameter & which returns a form
               class inheriting <creme_core.forms.merge.MergeEntitiesBaseForm>.
        @return The registry instance (to chain register() calls).
        """
        factories = self._form_factories

        if model in factories:
            raise self.RegistrationError(f'Model {model} is already registered')

        factories[model] = form_factory

        return self

    def unregister(self, model: type[CremeEntity]) -> _MergeFormRegistry:
        try:
            del self._form_factories[model]
        except KeyError as e:
            raise self.UnRegistrationError(
                f'Invalid model {model} (already registered?)'
            ) from e

        return self

    def get(self, model: type[CremeEntity]) -> FormFactory | None:
        return self._form_factories.get(model)

    @property
    def models(self) -> KeysView[type[CremeEntity]]:
        return self._form_factories.keys()


merge_form_registry = _MergeFormRegistry()
