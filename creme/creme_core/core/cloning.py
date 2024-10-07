################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024 Hybird
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

from django.db.models import Field, Q
from django.db.transaction import atomic
from django.utils.translation import gettext as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremeUser,
    CustomField,
    CustomFieldValue,
    Relation,
)


# Copiers ----------------------------------------------------------------------
class Copier:
    """A copier copies some data from a source entity to a target entity"""
    def __init__(self, *, user: CremeUser, source: CremeEntity):
        """Constructor.
        @param user: the user who performs the action.
        @param source: entity we want to copy.
        """
        self._source = source
        self._user = user

    @property
    def source(self):
        return self._source

    @property
    def user(self):
        return self._user

    def copy_to(self, target: CremeEntity) -> None:
        """Performs the copy to the target entity."""
        raise NotImplementedError


class BaseFieldsCopier(Copier):
    # Name of the fields to NOT copy from the source
    exclude = set()

    def accept(self, field: Field) -> bool:
        return field.get_tag(FieldTag.CLONABLE) and field.name not in self.exclude


class RegularFieldsCopier(BaseFieldsCopier):
    """Specialized copier for regular fields.
    Notice that ManyToManyFields are NOT copied (so this copier can be used
    before saving the cloned entity).
    """
    def copy_to(self, target):
        # TODO assert same type?
        source = self.source

        for field in source._meta.fields:
            if self.accept(field):
                fname = field.name
                setattr(target, fname, getattr(source, fname))


class ManyToManyFieldsCopier(BaseFieldsCopier):
    """Specialized copier for Many-To-Many fields.
    This copier must be used after the cloned entity has been saved.
    """
    def copy_to(self, target):
        source = self._source

        for field in source._meta.many_to_many:
            if self.accept(field):
                field_name = field.name
                getattr(target, field_name).set(getattr(source, field_name).all())


class CustomFieldsCopier(Copier):
    """Specialized copier for Custom-Fields.
    This copier must be used after the cloned entity has been saved.
    """
    def copy_to(self, target):
        source = self._source

        for custom_field in CustomField.objects.get_for_model(source.entity_type).values():
            custom_value_klass = custom_field.value_class
            try:
                value = custom_value_klass.objects.get(
                    custom_field=custom_field,
                    entity=source.id,
                ).value
            except custom_value_klass.DoesNotExist:
                continue  # TODO: log?

            if hasattr(value, 'id'):
                value = value.id
            elif hasattr(value, 'all'):
                value = [*value.all()]

            CustomFieldValue.save_values_for_entities(custom_field, [target], value)


class PropertiesCopier(Copier):
    """Specialized copier for CremeProperties.
    This copier must be used after the cloned entity has been saved.
    """
    def copy_to(self, target):
        creme_property_create = CremeProperty.objects.safe_create

        for type_id in self._source.properties.filter(
            type__is_copiable=True,
        ).values_list('type', flat=True):
            creme_property_create(type_id=type_id, creme_entity=target)


class RelationsCopier(Copier):
    """Specialized copier for Relations.
    This copier must be used after the cloned entity has been saved.
    """
    # IDs of RelationType with <is_internal=True> which must be copied anyway.
    allowed_internal_rtype_ids = []

    def copy_to(self, target):
        relation_create = Relation.objects.safe_create
        query = Q(type__is_internal=False, type__is_copiable=True)

        allowed_internal = self.allowed_internal_rtype_ids
        if allowed_internal:
            query |= Q(type__in=allowed_internal)

        for relation in self._source.relations.filter(query):
            relation_create(
                user_id=relation.user_id,
                subject_entity=target,
                type=relation.type,
                object_entity_id=relation.object_entity_id,
            )


# Cloner -----------------------------------------------------------------------
class EntityCloner:
    """This class manages the cloning of CremeEntities.
     - is a user allowed to clone?
     - perform the cloning.

    Hint: see class <EntityClonerRegistry>.
    """
    pre_save_copiers: list[Copier] = [
        RegularFieldsCopier,
    ]
    post_save_copiers: list[Copier] = [
        ManyToManyFieldsCopier,
        CustomFieldsCopier,
        PropertiesCopier,
        RelationsCopier,
    ]

    def check_permissions(self, *, user: CremeUser, entity: CremeEntity) -> None:
        """Checks if the given instance can be cloned.
        If an exception is raised, the cloning is forbidden (the exception
        should contain the reason -- a translated human readable one).
        @raise PermissionDenied, ConflictError.
        """
        if entity.is_deleted:
            raise ConflictError(_('A deleted entity cannot be cloned'))

        user.has_perm_to_create_or_die(entity)
        user.has_perm_to_view_or_die(entity)

    def _build_instance(self, *, user, source) -> CremeEntity:
        return type(source)()

    def _pre_save(self, *, user, source, target) -> None:
        for copier_class in self.pre_save_copiers:
            copier_class(source=source, user=user).copy_to(target=target)

    def _post_save(self, *, user, source, target) -> None:
        for copier_class in self.post_save_copiers:
            copier_class(source=source, user=user).copy_to(target=target)

    @atomic
    def perform(self, *, user: CremeUser, entity: CremeEntity) -> CremeEntity:
        """Performs the cloning.

        @param user: the logged user (could be used by some custom cloner
               classes to make some check).
        @param entity: Instance to clone.
        """
        clone = self._build_instance(user=user, source=entity)

        self._pre_save(user=user, source=entity, target=clone)
        clone.save()
        self._post_save(user=user, source=entity, target=clone)

        return clone


class EntityClonerRegistry:
    """Stores the cloning behaviours per CremeEntity model."""
    class RegistrationError(Exception):
        pass

    class UnRegistrationError(RegistrationError):
        pass

    def __init__(self):
        self._cloner_classes: dict[type[CremeEntity], type[EntityCloner]] = {}

    # TODO: 'def clone(instance):' ?

    def get(self, model: type[CremeEntity]) -> EntityCloner | None:
        """Hint: if None is returned, you should not clone the instances of
        the given model.
        """
        cls = self._cloner_classes.get(model)

        return None if cls is None else cls()

    def register(self,
                 model: type[CremeEntity],
                 cloner_class=EntityCloner,
                 ) -> EntityClonerRegistry:
        """Hint: register a child class of EntityCloner if you want to
        customise the cloning behaviour.
        """
        if self._cloner_classes.setdefault(model, cloner_class) is not cloner_class:
            raise self.RegistrationError(f'<{model.__name__}> has already a cloner')

        return self

    def unregister(self, model: type[CremeEntity]) -> EntityClonerRegistry:
        try:
            del self._cloner_classes[model]
        except KeyError as e:
            raise self.UnRegistrationError(
                f'<{model.__name__}> has no cloner (not registered or already unregistered)'
            ) from e

        return self


entity_cloner_registry = EntityClonerRegistry()
