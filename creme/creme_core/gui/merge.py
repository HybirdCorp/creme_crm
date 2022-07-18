################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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
    def __init__(self):
        self._form_factories: dict[type[CremeEntity], FormFactory] = {}

    def register(self,
                 model: type[CremeEntity],
                 form_factory: FormFactory) -> _MergeFormRegistry:
        """Register a form factory for a model.
        @param model: Class inheriting CremeEntity.
        @param form_factory: A callable with no parameter & which returns a form
               class inheriting <creme_core.forms.merge.MergeEntitiesBaseForm>.
        @return The registry instance (to chain register() calls).
        """
        self._form_factories[model] = form_factory

        return self

    def get(self, model: type[CremeEntity]) -> FormFactory | None:
        return self._form_factories.get(model)

    @property
    def models(self) -> KeysView[type[CremeEntity]]:
        return self._form_factories.keys()


merge_form_registry = _MergeFormRegistry()
