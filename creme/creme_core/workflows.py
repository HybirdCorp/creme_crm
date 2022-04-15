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

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

# from .core.workflow import SingleEntitySource, WorkflowActionIngredient,
from .core.workflow import (
    EntityCreated,
    EntityEdited,
    RelationAdded,
    WorkflowAction,
    WorkflowActionSource,
    WorkflowRegistry,
    WorkflowTrigger,
)
from .models import CremeEntity, CremeProperty, CremePropertyType, RelationType


# Triggers ---------------------------------------------------------------------
class EntityCreationTrigger(WorkflowTrigger):
    type_id = 'creme_core-entity_creation'
    verbose_name = _('An entity has been created')

    # TODO: accept Model class too?
    # TODO: docstring
    def __init__(self, *, model: str, **kwargs):
        super().__init__(**kwargs)
        self._model = ContentType.objects.get_by_natural_key(
            *model.split('-', 1)  # TODO: manage errors
        ).model_class()

    def activate(self, event):
        # return isinstance(event, EntityCreated) and isinstance(event.entity, self._model)
        # TODO: remove 'Source' class?
        return (
            {'created': event.entity}
            if isinstance(event, EntityCreated) and isinstance(event.entity, self._model) else
            None
        )

    @property
    def description(self):
        return gettext('A «{}» has been created').format(self._model._meta.verbose_name)

    @property
    def model(self):
        return self._model

    def to_dict(self):
        d = super().to_dict()
        meta = self._model._meta
        d['model'] = f'{meta.app_label}-{meta.model_name}'

        return d


# TODO: base model class instead
class EntityEditionTrigger(EntityCreationTrigger):
    type_id = 'creme_core-entity_edition'
    verbose_name = _('An entity has been modified')

    # TODO: factorise?
    def activate(self, event):
        # return isinstance(event, EntityEdited) and isinstance(event.entity, self._model)
        return (
            {'edited': event.entity}
            if isinstance(event, EntityEdited) and isinstance(event.entity, self._model) else
            None
        )

    # TODO: factorise?
    @property
    def description(self):
        return gettext('A «{}» has been modified').format(self._model._meta.verbose_name)


class RelationAddingTrigger(WorkflowTrigger):
    type_id = 'creme_core-relation_adding'
    verbose_name = _('A Relationship has been added')

    # TODO: rename arg? accept RelationType?
    def __init__(self, *, subject_model, rtype: str, object_model, **kwargs):
        assert isinstance(rtype, str)  # TODO: remove
        super().__init__(**kwargs)
        self._rtype_id = rtype

        # TODO: factorise
        self._subject_model = ContentType.objects.get_by_natural_key(
            *subject_model.split('-', 1)  # TODO: manage errors
        ).model_class()
        self._object_model = ContentType.objects.get_by_natural_key(
            *object_model.split('-', 1)  # TODO: manage errors
        ).model_class()

    # TODO: factorise?
    def activate(self, event):
        # return (
        #     isinstance(event, RelationAdded)
        #     and event.relation.type_id == self._rtype_id
        #     and isinstance(event.relation.object_entity, self._object_model)
        # )
        # TODO: Context with ContextDescriptor (label for source etc... in UI)
        if isinstance(event, RelationAdded):
            rel = event.relation

            if (
                rel.type_id == self._rtype_id
                and isinstance(rel.subject_entity, self._subject_model)
                and isinstance(rel.object_entity, self._object_model)
            ):
                return {'subject': rel.subject_entity, 'object': rel.object_entity}

        return None

    @property
    def description(self):
        return gettext(
            'A relationship «{predicate}» has been added to a «{model}»'
        ).format(
            predicate=self.relation_type.predicate,
            model=self._object_model._meta.verbose_name,
        )

    @property
    def object_model(self):
        return self._object_model

    # TODO: cache
    @property
    def relation_type(self) -> RelationType:
        return RelationType.objects.get(id=self._rtype_id)

    @property
    def subject_model(self):
        return self._subject_model

    def to_dict(self):
        d = super().to_dict()
        d['rtype'] = self._rtype_id

        # TODO: factorise
        subject_meta = self._subject_model._meta
        d['subject_model'] = f'{subject_meta.app_label}-{subject_meta.model_name}'
        object_meta = self._object_model._meta
        d['object_model'] = f'{object_meta.app_label}-{object_meta.model_name}'

        return d


# Action sources ---------------------------------------------------------------
# class CreatedEntitySource(SingleEntitySource):
#     @property
#     def label(self):
#         return gettext('Created entity ({type})').format(
#             type=self._model._meta.verbose_name,
#         )
#
#
# class EditedEntitySource(SingleEntitySource):
#     @property
#     def label(self):
#         return gettext('Modified entity ({type})').format(
#             type=self._model._meta.verbose_name,
#         )
# TODO: doc-strings
class FromContextSource(WorkflowActionSource):
    type_id = 'from_context'

    def __init__(self, context_key: str):
        self._key = context_key

    @property
    def context_key(self):
        return self._key

    def extract(self, context: dict):
        # TODO: error
        return context[self._key]

    @classmethod
    # def from_dict(cls, d):
    #     # TODO: error
    #     return cls(context_key=d['key'])
    def from_dict(cls, data, registry):
        # TODO: error
        return cls(context_key=data['key'])

    def to_dict(self):
        d = super().to_dict()
        d['key'] = self._key

        return d


class FixedEntitySource(WorkflowActionSource):
    type_id = 'fixed_entity'

    def __init__(self, entity: str):
        self._entity_uuid = entity

    # TODO: cache
    @property
    def entity(self):
        return CremeEntity.objects.get(uuid=self._entity_uuid).get_real_entity()

    def extract(self, context: dict):
        # TODO: error
        return self.entity

    @classmethod
    # def from_dict(cls, d):
    #     # TODO: error
    #     return cls(entity=d['uuid'])
    def from_dict(cls, data, registry):
        # TODO: error
        return cls(entity=data['uuid'])

    def to_dict(self):
        d = super().to_dict()
        d['uuid'] = self._entity_uuid

        return d


class InstanceFieldSource(WorkflowActionSource):
    type_id = 'field'

    def __init__(self, instance_source: WorkflowActionSource, field_name: str):
        self._sub_source = instance_source
        self._field_name = field_name

    @property
    def field_name(self):
        return self._field_name

    @property
    def instance_source(self):
        return self._sub_source

    def extract(self, context: dict):
        # TODO: error
        return getattr(self._sub_source.extract(context=context), self._field_name)

    # TODO: fixes other
    @classmethod
    # def from_dict(cls, d):
    def from_dict(cls, data: dict, registry: WorkflowRegistry):
        # TODO: error
        return cls(
            instance_source=registry.build_action_source(data['instance']),
            field_name=data['field'],
        )

    def to_dict(self):
        d = super().to_dict()
        d['instance'] = self._sub_source.to_dict()
        d['field'] = self._field_name

        return d


# Actions ----------------------------------------------------------------------
class PropertyAddingAction(WorkflowAction):
    type_id = 'creme_core-property_adding'
    verbose_name = _('Adding a property')

    # TODO: rename arg? accept CremePropertyType?
    # TODO: docstring
    def __init__(self, *, ptype, **kwargs):
        super().__init__(**kwargs)
        self._ptype_uuid = ptype

    @property
    def description(self):
        return _('Adding the property «{}»').format(self.property_type.text)

    # TODO: cache
    @property
    def property_type(self) -> CremePropertyType:
        return CremePropertyType.objects.get(uuid=self._ptype_uuid)

    # def execute(self, source):
    #     CremeProperty.objects.safe_create(creme_entity=source, type=self.property_type)
    def execute(self, context):
        # TODO: key error?
        CremeProperty.objects.safe_create(
            creme_entity=self._source.extract(context),
            type=self.property_type,
        )

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['ptype'] = self._ptype_uuid

        return d


class RelationAddingAction(WorkflowAction):
    type_id = 'creme_core-relation_adding'
    verbose_name = _('Adding a relationship')

    # TODO: rename arg? accept RelationType?
    def __init__(self, *, rtype, **kwargs):
        super().__init__(**kwargs)
        self._rtype_id = rtype

    @property
    def description(self):
        # TODO: talk about subject & object
        return _('Adding the relationship «{}»').format(self.relation_type.predicate)

    # def execute(self, source):
    def execute(self, context):
        raise NotImplementedError
        # TODO
        #   Relation.objects.safe_create(
        #      subject_entity=self.get_entity_from(source, ...),
        #      type=self.relation_type,
        #      object_entity=self.get_entity_from(source, ...),
        #    )

    @property
    def relation_type(self) -> RelationType:
        return RelationType.objects.get(id=self._rtype_id)

    def to_dict(self):
        d = super().to_dict()
        d['rtype'] = self._rtype_id

        return d
