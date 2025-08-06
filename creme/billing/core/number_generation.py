################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025  Hybird
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

from collections.abc import Iterator

from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.utils.translation import gettext as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import CremeUser
from creme.persons.models import AbstractOrganisation

from ..forms import number_generation as number_forms
from ..models import Base, NumberGeneratorItem


class NumberGenerator:
    # Form used to configure the related NumberGeneratorItem instances
    form_class = number_forms.NumberGeneratorItemEditionForm

    def __init__(self, item: NumberGeneratorItem):
        """Notice that if you want to call the method 'perform()' (which modifies
        the value of <item> in the database), you should .select_for_update()
        <item> to avoid issue with concurrent number generations.
        """
        self._item = item

    @classmethod
    def _default_data(cls) -> dict:
        raise NotImplementedError

    @classmethod
    def create_default_item(cls, organisation: AbstractOrganisation, model: Base) -> Model:
        """Creates the instance corresponding to the default configuration.
        See <billing.signal.init_number_generation_config()>.
        """
        return NumberGeneratorItem.objects.get_or_create(
            organisation=organisation,
            numbered_type=ContentType.objects.get_for_model(model),
            defaults={
                'data': cls._default_data(),
            },
        )[0]

    def check_permissions(self, *, user: CremeUser, entity: Base) -> None:
        """Checks if a number can be generated for the given instance.
        If an exception is raised, the generation is forbidden (the exception
        should contain the reason -- a translated human readable one).
        @raise PermissionDenied, ConflictError.
        """
        if entity.number:
            raise ConflictError(_('This entity has already a number'))

        user.has_perm_to_change_or_die(entity)

    # TODO?
    # @property
    # def item(self) -> NumberGeneratorItem:
    #     return self._item

    def perform(self) -> str:
        raise NotImplementedError

    @property
    def description(self) -> list[str]:
        return [
            _('Edition is allowed')
            if self._item.is_edition_allowed else
            _('Edition is forbidden'),
        ]


class NumberGeneratorRegistry:
    class RegistrationError(Exception):
        pass

    class UnRegistrationError(RegistrationError):
        pass

    _generator_classes: dict[type[Base], type[NumberGenerator]]

    def __init__(self):
        self._generator_classes = {}

    def __getitem__(self, item: NumberGeneratorItem) -> NumberGenerator:
        gen = self.get(item)
        if gen is None:
            raise ConflictError(
                _('This kind of entity cannot not generate a number.')
            )

        return gen

    def get(self, item: NumberGeneratorItem) -> None | NumberGenerator:
        cls = self._generator_classes.get(item.numbered_type.model_class())

        return None if cls is None else cls(item=item)

    def register(self,
                 model: type[Base],
                 generator_cls: type[NumberGenerator],
                 ) -> NumberGeneratorRegistry:
        if self._generator_classes.setdefault(model, generator_cls) is not generator_cls:
            raise self.RegistrationError(
                f'The model {model} has already a registered generator class.'
            )

        return self

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
