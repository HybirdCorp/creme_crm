################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2025  Hybird
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
from dataclasses import dataclass
from typing import Any, Iterator

from django.core.exceptions import ValidationError
from django.db.models import Field, ForeignKey, signals
from django.db.models.base import Model, ModelState
from django.dispatch import receiver

from creme.creme_core.models import CremeEntity

logger = logging.getLogger(__name__)


# TODO: complete typing
# TODO: doc
class Snapshot:
    HIDDEN_ATTR_NAME = '_creme_snapshot'

    _model: type[Model]
    _related_instance: Model
    _initial_values: dict[str, Any]

    @dataclass(kw_only=True, slots=True)
    class Difference:
        field: Field
        old_value: Any
        new_value: Any

        @property
        def field_name(self):
            return self.field.get_attname()

    @classmethod
    def take(cls, instance: Model) -> None:
        initial_values = instance.__dict__.copy()
        del initial_values['_state']
        setattr(instance, cls.HIDDEN_ATTR_NAME, initial_values)

    @classmethod
    def get_for_instance(cls, instance) -> Snapshot | None:
        try:
            initial_values = getattr(instance, cls.HIDDEN_ATTR_NAME)
        except AttributeError:
            return None

        data = initial_values.copy()
        data['_state'] = ModelState()

        snapshot = cls()
        snapshot._related_instance = instance  # TODO: type
        snapshot._model = type(instance)  # TODO: remove & use _related_instance?
        snapshot._initial_values = data
        # snapshot._cvalues_map = instance._cvalues_map

        return snapshot

    @property
    def model(self):
        return self._model

    def compare(self, instance: Model) -> Iterator[Difference]:
        if not isinstance(instance, self._model):
            raise TypeError(
                f'You must compare with an instance of the same type '
                f'({self._model} != {type(instance)})'
            )

        old_instance = self.get_initial_instance()

        for field in instance._meta.fields:
            # Use 'get_attname()' instead of name to check IDs for ForeignKeys
            # instead of the entity to optimize queries' number  TODO: unit test
            fname = field.get_attname()

            # TODO: argument to filter fields?
            # if fname in excluded_fields or not field.get_tag(FieldTag.VIEWABLE):
            #     continue

            old_value = getattr(old_instance, fname)
            new_value = getattr(instance, fname)

            # TODO: unit test (tested in history only)
            if not isinstance(field, ForeignKey):
                try:
                    # Sometimes a form sets a string representing an int in
                    # an IntegerField (for example)
                    #   => the type difference leads to a useless log like:
                    #      Set field “My field” from “X” to “X”
                    new_value = field.clean(new_value, instance)
                except ValidationError as e:
                    logger.critical(
                        'Snapshot.compare(): the field "%s.%s" has been assigned '
                        'with an invalid value <%s> (original error: %s)',
                        type(instance).__name__, fname, new_value, e,
                    )
                    continue

            if old_value != new_value:
                yield self.Difference(
                    field=field, old_value=old_value, new_value=new_value,
                )

    # TODO: use in history or remove?
    def compare_custom_field(self, instance: CremeEntity, custom_field):
        # TODO: check that the same entity is used?

        cvalue = instance.get_custom_value(custom_field=custom_field)
        # print(type(cvalue))
        # TODO: test None
        snapshot = self.get_for_instance(cvalue)
        # print('=>', snapshot, snapshot._initial_values)
        return next(snapshot.compare(cvalue), None)

    # TODO: what about?
    #   - M2M
    #   - CustomFields MULTI_ENUM
    def get_initial_instance(self) -> Model:
        old_instance = self._model()
        old_instance.__dict__ = self._initial_values

        # old_instance._relations_map = {}  TODO
        # old_instance._properties = None  TODO

        # TODO: system to customize snapshots?
        if isinstance(old_instance, CremeEntity):
            def get_custom_value(custom_field):
                cvalue = self._related_instance.get_custom_value(custom_field)

                return Snapshot.get_for_instance(cvalue).get_initial_instance()

            old_instance.get_custom_value = get_custom_value

        return old_instance


# TODO: limit the models that are snapshot?
@receiver(signals.post_init, dispatch_uid='creme_core-build_snapshot')
def _build_snapshot(sender, instance, **kwargs):
    if instance.pk:
        Snapshot.take(instance)
