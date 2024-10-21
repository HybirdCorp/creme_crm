################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

from typing import Iterator

from django.db.models import Model

from creme.billing.forms import number_generation as number_forms
from creme.billing.models import Base
from creme.persons.models import AbstractOrganisation


class NumberGenerator:
    # Is the number generator when a related instance is created?
    trigger_at_creation = True
    # Form used to configure the related NumberGeneratorItem instances
    form_class = number_forms.NumberGeneratorItemEditionForm

    def __init__(self, model: type[Base]):
        self._model = model

    @classmethod
    def default_item(cls, organisation: AbstractOrganisation, model: Base) -> Model:
        """Return an unsaved instance corresponding to the default configuration.
        See <billing.signal.init_number_generation_config()>.
        """
        raise NotImplementedError

    @property
    def model(self) -> type[Base]:
        return self._model

    def perform(self, organisation: AbstractOrganisation) -> str:
        raise NotImplementedError


class NumberGeneratorRegistry:
    class RegistrationError(Exception):
        pass

    class UnRegistrationError(RegistrationError):
        pass

    def __init__(self):
        self._generator_classes: dict[type[Base], type[NumberGenerator]] = {}

    def get(self, model: type[Base]) -> None | NumberGenerator:
        cls = self._generator_classes.get(model)
        return None if cls is None else cls(model=model)

    def register(self,
                 model: type[Base],
                 generator_cls: type[NumberGenerator],
                 ) -> NumberGeneratorRegistry:
        if self._generator_classes.setdefault(model, generator_cls) is not generator_cls:
            raise self.RegistrationError(
                f'The model {model} has already a registered generator class.'
            )

        return self

    # TODO: unit test
    def registered_items(self) -> Iterator[tuple[type[Base], type[NumberGenerator]]]:
        yield from self._generator_classes.items()

    def unregister(self, model: type[Base]) -> NumberGeneratorRegistry:
        try:
            del self._generator_classes[model]
        except KeyError as e:
            raise self.UnRegistrationError(
                f'The model {model} has no registered generator class.'
            ) from e

        return self


number_generator_registry = NumberGeneratorRegistry()
