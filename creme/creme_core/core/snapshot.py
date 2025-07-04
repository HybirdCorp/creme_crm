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
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError
from django.db.models import Field, ForeignKey, signals
from django.db.models.base import Model, ModelState
from django.dispatch import receiver

from creme.creme_core.models import CremeEntity

logger = logging.getLogger(__name__)


class Snapshot:
    """It can build an instance with its "initial" state, i.e. the state it has
    just after its loading from the DB.
    It's used by:
        - the History system, to get the fields which have changed.
        - the Workflow engine, to check conditions before & after an edition.
    """
    HIDDEN_ATTR_NAME = '_creme_snapshot'

    _related_instance: Model
    _initial_values: dict[str, Any]

    @dataclass(kw_only=True, slots=True)
    class Difference:
        """Store the change on a regular model field."""
        field: Field
        old_value: Any
        new_value: Any

        @property
        def field_name(self) -> str:
            return self.field.get_attname()

    @classmethod
    def take(cls, instance: Model) -> None:
        """Store the initial state of an instance.
        It's automatically called by the signal handler '_take_snapshot()' for
        all model, you should probably avoid to call it by yourself.
        """
        initial_values = instance.__dict__.copy()
        del initial_values['_state']
        setattr(instance, cls.HIDDEN_ATTR_NAME, initial_values)

    @classmethod
    def get_for_instance(cls, instance: Model) -> Snapshot | None:
        """Get the Snapshot object corresponding to a Model instance.
        This is THE way to get a Snapshot, you should avoid to build one by yourself.

        @param instance: The returned Snapshot will be related to this instance.
        @return: None is returned if the instance just have been created during
                 the HTTP request treatment (i.e. there is no previous state).
        """
        try:
            initial_values = getattr(instance, cls.HIDDEN_ATTR_NAME)
        except AttributeError:
            return None

        data = initial_values.copy()
        data['_state'] = ModelState()

        snapshot = cls()
        snapshot._related_instance = instance
        snapshot._initial_values = data

        return snapshot

    @property
    def model(self) -> type[Model]:
        return type(self._related_instance)

    def compare(self, instance: Model) -> Iterator[Difference]:
        """Get the differences (related to regular model fields) between the
         initial & the current state of a given instance.

        Hint: used by the History system.
        Note: ManyToManyFields are ignored.
        """
        if not isinstance(instance, self.model):
            raise TypeError(
                f'You must compare with an instance of the same type '
                f'({self.model} != {type(instance)})'
            )

        old_instance = self.get_initial_instance()

        for field in instance._meta.fields:
            # Use 'get_attname()' instead of name to check IDs for ForeignKeys
            # instead of the entity to optimize queries' number
            fname = field.get_attname()

            # TODO: argument to filter fields?
            # if fname in excluded_fields or not field.get_tag(FieldTag.VIEWABLE):
            #     continue

            old_value = getattr(old_instance, fname)
            new_value = getattr(instance, fname)

            if not isinstance(field, ForeignKey):  # NB: avoid a query
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

    # TODO? (note: this --incomplete-- method is finally not used even by the History system)
    # def compare_custom_field(self, instance: CremeEntity, custom_field):
    #     # todo: check that the same entity is used?
    #     cvalue = instance.get_custom_value(custom_field=custom_field)
    #     # todo: test None
    #     snapshot = self.get_for_instance(cvalue)
    #
    #     return next(snapshot.compare(cvalue), None)

    def get_initial_instance(self) -> Model:
        """Get an instance with the initial state.
        Important things to know about this instance:
          - For basic regular fields, a classical 'my_obj.field' will work as
            expected (i.e. get the "old" values).
          - For ManyToManyFields, use the method 'get_m2m_values()' to get the
            initial values; if you perform queries you'll get the current values.
          - For CustomFields, use the method 'get_custom_value()' to get the
            initial value.

        Not implemented yet:
          - Initial values for Relations.
          - Initial values for CremeProperties.
        """
        initial = self.model()
        initial.__dict__ = self._initial_values

        # TODO: system to customize snapshots per model class?
        if isinstance(initial, CremeEntity):
            # TODO: (needed for workflow conditions on Relations/CremeProperties)
            #  - get_relations
            #  - get_properties

            def get_custom_value(custom_field):
                cvalue = self._related_instance.get_custom_value(custom_field)

                return Snapshot.get_for_instance(cvalue).get_initial_instance()

            def get_m2m_values(field_name):
                from ..models.base import _M2M_CACHE_NAME

                try:
                    return self._initial_values[_M2M_CACHE_NAME][field_name]
                except KeyError:
                    return self._related_instance.get_m2m_values(field_name)

            initial.get_custom_value = get_custom_value
            initial.get_m2m_values   = get_m2m_values

        return initial


# TODO: limit the models which are taken?
@receiver(signals.post_init, dispatch_uid='creme_core-take_snapshot')
def _take_snapshot(sender, instance, **kwargs):
    if instance.pk:
        Snapshot.take(instance)


@receiver(signals.m2m_changed, dispatch_uid='creme_core-snapshot_m2m_cache')
def _snapshot_m2m_cache(sender, instance, action, reverse, **kwargs):
    if reverse:  # Not cache for the reverse side.
        return

    if not action.startswith('pre_'):  # Avoids useless computing
        return

    initial_values = getattr(instance, Snapshot.HIDDEN_ATTR_NAME, None)
    if initial_values is not None:
        from ..models.base import _M2M_CACHE_NAME

        cache = initial_values.get(_M2M_CACHE_NAME)
        if cache is None:
            cache = initial_values[_M2M_CACHE_NAME] = {}

        # TODO: factorise (creme_core.models.base._update_m2m_cache,
        #       creme_core.models.history._log_m2m_edition)
        for field in type(instance)._meta.many_to_many:
            if sender is field.remote_field.through:
                m2m_name = field.attname
                break
        else:
            logger.warning('_snapshot_m2m_cache: ManyToManyField not found: %s', sender)
            return

        if m2m_name not in cache:
            # TODO: store only PKs?
            cache[m2m_name] = [*getattr(instance, m2m_name).all()]
