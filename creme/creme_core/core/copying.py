################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025 Hybird
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

import logging

from django.core.exceptions import ValidationError
from django.db.models import Field, Q

from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremeUser,
    CustomField,
    CustomFieldValue,
    Relation,
    RelationType,
)

logger = logging.getLogger(__name__)


class Copier:
    """A copier copies some data from a source entity to a target entity."""
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

    def copy_to(self, target: CremeEntity) -> bool | None:
        """Performs the copy to the target entity.
        @return: If true, the target has been modified & should be saved.
        """
        raise NotImplementedError


class PreSaveCopier(Copier):
    pass


class PostSaveCopier(Copier):
    """This kind of Copier must be used on a target entity which has already
    been saved once at least (& so have a PK).
    """


class FieldsCopierMixin(Copier):
    # Name of the fields to NOT copy from the source
    exclude: set[str] = set()

    def accept(self, field: Field) -> bool:
        return field.get_tag(FieldTag.CLONABLE) and field.name not in self.exclude


class RegularFieldsCopier(FieldsCopierMixin, PreSaveCopier):
    """Specialized copier for regular fields.
    Notice that ManyToManyFields are NOT copied (so this copier can be used
    before saving the cloned entity).
    """
    def copy_to(self, target):
        source = self.source

        for field in source._meta.fields:
            if self.accept(field):
                fname = field.name
                setattr(target, fname, getattr(source, fname))


class ManyToManyFieldsCopier(FieldsCopierMixin, PostSaveCopier):
    """Specialized copier for Many-To-Many fields."""
    def copy_to(self, target):
        source = self._source

        for field in source._meta.many_to_many:
            if self.accept(field):
                field_name = field.name
                getattr(target, field_name).set(getattr(source, field_name).all())


class CustomFieldsCopier(PostSaveCopier):
    """Specialized copier for Custom-Fields."""
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


class PropertiesCopier(PostSaveCopier):
    """Specialized copier for CremeProperties."""
    def _properties_qs(self):
        return self._source.properties.filter(type__is_copiable=True)

    def copy_to(self, target):
        property_create = CremeProperty.objects.safe_create

        for type_id in self._properties_qs().values_list('type', flat=True):
            property_create(type_id=type_id, creme_entity=target)


class StrongPropertiesCopier(PropertiesCopier):
    """Specialized copier for CremeProperties between a source & a target
    with different ContentTypes.
    It won't be useful in a classical cloning (source & target have the same type)
    but you should use this class when the types are mixed, because the
    ContentType constraints of the CremePropertyTypes are respected.
    """
    def copy_to(self, target):
        property_create = CremeProperty.objects.safe_create

        for prop in self._properties_qs().select_related('type').prefetch_related(
            'type__subject_ctypes'
        ):
            # TODO: implement/use CremeProperty.clean() (like Relation.clean())
            subject_ctypes = prop.type.subject_ctypes.all()

            if not subject_ctypes or target.entity_type in subject_ctypes:
                property_create(type=prop.type, creme_entity=target)


class RelationsCopier(PostSaveCopier):
    """Specialized copier for Relations."""
    # IDs of RelationType with <is_internal=True> which must be copied anyway.
    allowed_internal_rtype_ids: list[str] = []

    def _relations_qs(self):
        query = Q(type__is_internal=False, type__is_copiable=True)

        allowed_internal = self.allowed_internal_rtype_ids
        if allowed_internal:
            query |= Q(type__in=allowed_internal)

        return self._source.relations.filter(query)

    def copy_to(self, target):
        relation_create = Relation.objects.safe_create

        for relation in self._relations_qs().select_related('user').prefetch_related(
            'real_object',
        ):
            relation_create(
                # NB: it surprisingly produces additional queries
                # user_id=relation.user_id,
                user=relation.user,
                subject_entity=target,
                type=relation.type,
                real_object=relation.real_object,
            )


class StrongRelationsCopier(RelationsCopier):
    """Specialized copier for Relations which check all constraints of RelationTypes.
     - Constraints for ContentType (so the source & the target can have different
       types)
     - Constraint for CremeProperties. Notice you should use this Copier after
       CremeProperties have been copied.
    """
    # Check if the Relations already exist (see Relation.objects.safe_multi_save()).
    # Note that <False> does not mean duplicates can be created (it's forbidden by
    # a SQL constraint); it just means we avoid a SQL query to find possible
    # duplicates (we assume that "target" is a freshly created instance with no Relation).
    check_existing = False

    def copy_to(self, target):
        relations = []
        for relation in self._relations_qs().select_related('type', 'user').prefetch_related(
            'real_object',
            'type__subject_ctypes',
            'type__subject_properties',
            'type__subject_properties',
            'type__subject_forbidden_properties',
        ):
            rel = Relation(
                # NB: it surprisingly produces additional queries
                # user_id=relation.user_id,
                user=relation.user,
                subject_entity=target,
                type=relation.type,
                real_object=relation.real_object,
            )

            try:
                rel.clean()
            except ValidationError:
                pass
            else:
                relations.append(rel)

        Relation.objects.safe_multi_save(
            relations=relations, check_existing=self.check_existing,
        )


class RelationAdder(PostSaveCopier):
    """Add a Relation with a fixed type between the source & the target."""
    rtype_id = ''

    def copy_to(self, target):
        rtype_id = self.rtype_id

        if not self.rtype_id:
            raise ValueError('The attribute "rtype_id" has not been initialized')

        rtype = RelationType.objects.get(id=rtype_id)

        if rtype.enabled and rtype.is_copiable:
            Relation.objects.safe_create(
                user=self._user,
                subject_entity=target,
                type=rtype,
                object_entity=self._source,
            )
        else:
            logger.info(
                'RelationAdder => the relation type "%s" is '
                'disabled/not-copiable, no relationship is created.',
                rtype,
            )
