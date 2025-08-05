################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019-2025 Hybird
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
from collections.abc import Iterable
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _

from creme.creme_core.core.exceptions import ConflictError

if TYPE_CHECKING:
    from creme.creme_core.models import CremeEntity, CremeUser

logger = logging.getLogger(__name__)


# Deletion of Minion & other small models registered in creme_config -----------
class Replacer:
    type_id: str = 'OVERRIDE'

    def __init__(self, *, model_field):
        self.model_field = model_field

    def as_dict(self) -> dict:
        field = self.model_field

        return {
            'ctype': ContentType.objects.get_for_model(field.model).natural_key(),
            'field': field.name,
        }

    @classmethod
    def from_dict(cls, d: dict):
        raise NotImplementedError

    def get_value(self):
        raise NotImplementedError


# class ReplacersRegistry:
class ReplacerRegistry:
    __slots__ = ('_replacer_classes', )

    class RegistrationError(Exception):
        pass

    def __init__(self):
        self._replacer_classes = {}

    def __call__(self, cls: type[Replacer]):
        if self._replacer_classes.setdefault(cls.type_id, cls) is not cls:
            raise self.RegistrationError(f'Duplicated Replacer id: {cls.type_id}')

        return cls

    # TODO ?
    # def __getitem__(self, type_id):
    #     return self._replacer_classes[type_id]

    def serialize(self, replacers: Iterable[Replacer]) -> list:
        return [
            [r.type_id, r.as_dict()] for r in replacers
        ]

    def deserialize(self, data):
        assert isinstance(data, list)
        replacers = []

        for replacer_data in data:
            assert isinstance(replacer_data, list)
            assert len(replacer_data) == 2

            type_id, instance_data = replacer_data
            assert isinstance(type_id, str)
            assert isinstance(instance_data, dict)

            replacers.append(self._replacer_classes[type_id].from_dict(instance_data))

        return replacers


REPLACERS_MAP = ReplacerRegistry()


# def __getattr__(name):
#     if name == 'ReplacersRegistry':
#         warnings.warn(
#             '"ReplacersRegistry" is deprecated; use "ReplacerRegistry" instead.',
#             DeprecationWarning,
#         )
#         return ReplacerRegistry
#
#     raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


@REPLACERS_MAP
class FixedValueReplacer(Replacer):
    type_id = 'fixed_value'

    def __init__(self, *, model_field, value=None):
        super().__init__(model_field=model_field)
        self._fixed_value = value

    def __str__(self):
        value = self._fixed_value
        rel_field = self.model_field

        if value:
            return _('In «{model} - {field}», replace by «{new}»').format(
                model=rel_field.model._meta.verbose_name,
                field=rel_field.verbose_name,
                new=value,
            )

        msg = (
            _('Remove from «{model} - {field}»')
            if rel_field.many_to_many else
            _('Empty «{model} - {field}»')
        )

        return msg.format(
            model=rel_field.model._meta.verbose_name,
            field=rel_field.verbose_name,
        )

    def as_dict(self):
        d = super().as_dict()

        value = self._fixed_value
        if value is not None:
            d['pk'] = value.pk

        return d

    @classmethod
    def from_dict(cls, d):
        ctype = ContentType.objects.get_by_natural_key(*d['ctype'])
        fk = ctype.model_class()._meta.get_field(d['field'])
        pk = d.get('pk')

        if pk is None:
            value = None
        else:
            model = fk.remote_field.model
            try:
                value = model._default_manager.get(pk=pk)
            except model.DoesNotExist:
                logger.exception('Error in FixedValueReplacer.from_dict()')
                value = None

        return cls(model_field=fk, value=value)

    def get_value(self):
        return self._fixed_value


@REPLACERS_MAP
class SETReplacer(Replacer):
    type_id = 'SET'

    def __str__(self):
        fk = self.model_field

        return _('In «{model} - {field}», replace by a fallback value').format(
            model=fk.model._meta.verbose_name,
            field=fk.verbose_name,
        )

    @classmethod
    def from_dict(cls, d):
        # TODO: factorise
        ctype = ContentType.objects.get_by_natural_key(*d['ctype'])
        fk = ctype.model_class()._meta.get_field(d['field'])

        return cls(model_field=fk)

    def get_value(self):
        captured_value = None

        # NB: we get the value passed to SET()
        class CapturingValueCollector:
            def add_field_update(self, field, value, objs):
                nonlocal captured_value
                captured_value = value

        self.model_field.remote_field.on_delete(
            collector=CapturingValueCollector(),
            field=None,
            sub_objs=None,
            using=None,
        )

        return captured_value


# Deletion of entities ---------------------------------------------------------
class EntityDeletor:
    """This class manages the deletion of CremeEntities.
     - is the deletion definitive? (i.e. should the entity be moved to the trash)
     - is a user allowed to delete?
     - perform the deletion.

    Hint: see class <EntityDeletorRegistry>.
    """
    # TODO: split more? (e.g. separated is_disabled())
    def check_permissions(self, *, user: CremeUser, entity: CremeEntity) -> None:
        """Checks if the given instance can be deleted.
        If an exception is raised, the deletion is forbidden (the exception
        should contain the reason).
        @raise PermissionDenied, ConflictError.
        """
        if not user.has_perm_to_delete(entity):
            raise PermissionDenied(
                _('You are not allowed to delete this entity by your role')
            )

        if (
            self.is_definitive(entity=entity, user=user)
            and not settings.ENTITIES_DELETION_ALLOWED
            and not user.is_staff
            and not hasattr(entity, 'get_related_entity')
        ):
            raise ConflictError(
                _('Deletion has been disabled by your administrator')
            )

    # NB: separated method which can be overridden by child classes
    def _trash(self, user: CremeUser, entity: CremeEntity) -> None:
        entity.trash()

    # NB: separated method which can be overridden by child classes
    def _delete(self, user: CremeUser, entity: CremeEntity) -> None:
        entity.delete()

    def perform(self, *, user: CremeUser, entity: CremeEntity) -> None:
        """Performs the operation (definitive deletion, move to trash etc...).

        @param user: the logged user (could be used by some custom deletor
               classes to make some check).
        @param entity: Instance to delete.
        @raise <django.db.models.deletion.ProtectedError> (it could be the child
               class <creme.creme_core.core.exceptions.SpecificProtectedError>).
        """
        if self.is_definitive(entity=entity, user=user):
            self._delete(user=user, entity=entity)
        else:
            self._trash(user=user, entity=entity)

    def is_definitive(self, *, user: CremeUser, entity: CremeEntity) -> bool:
        "@return <True> means the instance will not be moved to the trash."
        return hasattr(entity, 'get_related_entity') or entity.is_deleted


class EntityDeletorRegistry:
    """Stores the deletion behaviours per CremeEntity model."""
    class RegistrationError(Exception):
        pass

    class UnRegistrationError(RegistrationError):
        pass

    _deletor_classes: dict[type[CremeEntity], type[EntityDeletor]]

    def __init__(self):
        self._deletor_classes = {}

    def get(self, model: type[CremeEntity]) -> EntityDeletor | None:
        """Hint: if None is returned, you should not delete the instances of
        the given model.
        """
        cls = self._deletor_classes.get(model)

        return None if cls is None else cls()

    def register(self,
                 model: type[CremeEntity],
                 deletor_class=EntityDeletor,
                 ) -> EntityDeletorRegistry:
        """Hint: register a child class of EntityDeletor if you want to
        customise the deletion behaviour.
        """
        if self._deletor_classes.setdefault(model, deletor_class) is not deletor_class:
            raise self.RegistrationError(f'{model} has already a deletor')

        return self

    def unregister(self, model: type[CremeEntity]) -> EntityDeletorRegistry:
        try:
            del self._deletor_classes[model]
        except KeyError as e:
            raise self.UnRegistrationError(
                f'{model} has no deletor (not registered or already unregistered)'
            ) from e

        return self


entity_deletor_registry = EntityDeletorRegistry()
