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
from django.db.models import Model
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from .core.workflow import (
    EntityCreated,
    EntityEdited,
    RelationAdded,
    WorkflowAction,
    WorkflowActionSource,
    WorkflowTrigger,
)
from .models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    Relation,
    RelationType,
)


# TODO: test (+ move?)
def _model_to_str(model: type[Model]) -> str:
    meta = model._meta
    return f'{meta.app_label}-{meta.model_name}'


# TODO: test (+ move?)
# TODO: errors
def _str_to_model(model_key: str) -> type[Model]:
    return ContentType.objects.get_by_natural_key(*model_key.split('-', 1)).model_class()


# Triggers ---------------------------------------------------------------------
# TODO: doc-strings
class EntityCreationTrigger(WorkflowTrigger):
    type_id = 'creme_core-entity_creation'
    verbose_name = _('An entity has been created')

    CREATED = 'created'

    def __init__(self, *, model: type[CremeEntity]):
        self._model = model

    def activate(self, event):
        return (
            {self.CREATED: event.entity}
            if isinstance(event, EntityCreated) and isinstance(event.entity, self._model) else
            None
        )

    @property
    def description(self):
        return gettext('A «{}» has been created').format(self._model._meta.verbose_name)

    @property
    def model(self):
        return self._model

    # TODO: manage errors
    @classmethod
    def from_dict(cls, data: dict) -> WorkflowTrigger:
        return cls(model=_str_to_model(data['model']))

    def to_dict(self):
        d = super().to_dict()
        d['model'] = _model_to_str(self._model)

        return d


# TODO: base model class instead
class EntityEditionTrigger(EntityCreationTrigger):
    type_id = 'creme_core-entity_edition'
    verbose_name = _('An entity has been modified')

    EDITED = 'edited'

    # TODO: factorise?
    def activate(self, event):
        return (
            {self.EDITED: event.entity}
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

    SUBJECT = 'subject'
    OBJECT = 'object'

    def __init__(self, *,
                 subject_model: type[CremeEntity],
                 rtype: str | RelationType,
                 object_model: type[CremeEntity],
                 ):
        self._subject_model = subject_model
        self._object_model = object_model

        if isinstance(rtype, str):
            self._rtype_id = rtype
            self._rtype = None
        else:
            assert isinstance(rtype, RelationType)
            self._rtype_id = rtype.id
            self._rtype = rtype

    # TODO: factorise?
    def activate(self, event):
        # TODO: Context with ContextDescriptor (label for source etc... in UI)
        if isinstance(event, RelationAdded):
            rel = event.relation

            if (
                rel.type_id == self._rtype_id
                and isinstance(rel.subject_entity, self._subject_model)
                and isinstance(rel.object_entity, self._object_model)
            ):
                return {self.SUBJECT: rel.subject_entity, self.OBJECT: rel.object_entity}

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

    # TODO: factorise
    # TODO: manage errors (RelationType does not exist anymore)
    @property
    def relation_type(self) -> RelationType:
        rtype = self._rtype
        if rtype is None:
            self._rtype = rtype = RelationType.objects.get(id=self._rtype_id)

        return rtype

    @property
    def subject_model(self):
        return self._subject_model

    @classmethod
    def from_dict(cls, data: dict) -> WorkflowTrigger:
        # TODO: errors
        return cls(
            subject_model=_str_to_model(data['subject_model']),
            rtype=data['rtype'],
            object_model=_str_to_model(data['object_model']),
        )

    def to_dict(self):
        d = super().to_dict()
        d['rtype'] = self._rtype_id
        d['subject_model'] = _model_to_str(self._subject_model)
        d['object_model'] = _model_to_str(self._object_model)

        return d


# Action sources ---------------------------------------------------------------
# TODO: doc-strings
class FromContextSource(WorkflowActionSource):
    type_id = 'from_context'

    def __init__(self, context_key: str):
        self._key = context_key

    def __eq__(self, other):
        return isinstance(other, type(self)) and self._key == other._key

    def __repr__(self):
        return f'FromContextSource("{self._key}")'

    @property
    def context_key(self):
        return self._key

    def extract(self, context: dict):
        # TODO: error
        return context[self._key]

    @classmethod
    def from_dict(cls, data, registry):
        # TODO: error
        return cls(context_key=data['key'])

    def to_dict(self):
        d = super().to_dict()
        d['key'] = self._key

        return d


class FixedEntitySource(WorkflowActionSource):
    type_id = 'fixed_entity'

    # TODO: accept UUID() too?
    def __init__(self, *,
                 entity: str | CremeEntity,
                 model: type[CremeEntity] | None = None,
                 ):
        if isinstance(entity, str):
            assert model is not None  # TODO: test + ValueError
            assert issubclass(model, CremeEntity)  # TODO: test + TypeError
            self._entity_uuid = entity
            self._entity = None
        else:
            # TODO: <assert model is None>?
            self._entity_uuid = str(entity.uuid)
            self._entity = entity.get_real_entity()
            model = type(self._entity)

        self._model = model

    def __eq__(self, other):
        return isinstance(other, type(self)) and self._entity_uuid == other._entity_uuid

    def __repr__(self):
        return f'FixedEntitySource(entity={self._entity_uuid}), model={self._model}))'

    # TODO: manage error (CremeEntity does not exist anymore)
    @property
    def entity(self) -> CremeEntity:
        entity = self._entity
        if entity is None:
            self._entity = entity = self._model.objects.get(uuid=self._entity_uuid)

        return entity

    @property
    def model(self) -> type[CremeEntity]:
        return self._model

    # TODO: <None> if error
    def extract(self, context: dict):
        return self.entity

    @classmethod
    def from_dict(cls, data, registry):
        # TODO: error
        return cls(model=_str_to_model(data['model']), entity=data['uuid'])

    def to_dict(self):
        d = super().to_dict()
        d['uuid'] = self._entity_uuid
        d['model'] = _model_to_str(self._model)

        return d


class InstanceFieldSource(WorkflowActionSource):
    type_id = 'field'

    def __init__(self, *, instance_source: WorkflowActionSource, field_name: str):
        self._instance_source = instance_source
        self._field_name = field_name

    def __eq__(self, other):
        return (
            isinstance(other, type(self))
            and self._field_name == other._field_name
            and self._instance_source == other._instance_source
        )

    @property
    def field_name(self):
        return self._field_name

    @property
    def instance_source(self):
        return self._instance_source

    def extract(self, context: dict):
        # TODO: error?
        instance = self._instance_source.extract(context=context)
        return None if instance is None else getattr(instance, self._field_name)

    @classmethod
    def from_dict(cls, data: dict, registry):
        # TODO: error
        return cls(
            instance_source=registry.build_action_source(data['instance']),
            field_name=data['field'],
        )

    def to_dict(self):
        d = super().to_dict()
        d['instance'] = self._instance_source.to_dict()
        d['field'] = self._field_name

        return d


class FirstRelatedEntitySource(WorkflowActionSource):
    type_id = 'first_related'

    def __init__(self, *,
                 subject_source: WorkflowActionSource,
                 rtype: str | RelationType,
                 object_model: type[CremeEntity],
                 ):
        self._subject_source = subject_source
        self._object_model = object_model

        # TODO: factorise
        if isinstance(rtype, str):
            self._rtype_id = rtype
            self._rtype = None
        else:
            assert isinstance(rtype, RelationType)
            self._rtype_id = rtype.id
            self._rtype = rtype

    def __eq__(self, other):
        return (
            isinstance(other, type(self))
            and self._subject_source == other._subject_source
            and self._rtype_id == other._rtype_id
            and self._object_model == other._object_model
        )

    @property
    def subject_source(self):
        return self._subject_source

    @property
    def object_model(self):
        return self._object_model

    # TODO: factorise
    # TODO: manage errors (RelationType does not exist anymore)
    @property
    def relation_type(self) -> RelationType:
        rtype = self._rtype
        if rtype is None:
            self._rtype = rtype = RelationType.objects.get(id=self._rtype_id)

        return rtype

    def extract(self, context: dict):
        # TODO: manage error
        subject = self._subject_source.extract(context=context)

        if subject is not None:
            return self._object_model.objects.filter(
                relations__type=self.relation_type.symmetric_type_id,
                relations__object_entity=subject,
            ).first()

        return None

    @classmethod
    def from_dict(cls, data: dict, registry):
        # TODO: error
        return cls(
            subject_source=registry.build_action_source(data['subject']),
            rtype=data['rtype'],
            object_model=_str_to_model(data['object_model']),
        )

    def to_dict(self):
        d = super().to_dict()
        d['subject'] = self._subject_source.to_dict()
        d['rtype'] = self._rtype_id
        d['object_model'] = _model_to_str(self._object_model)

        return d


# Actions ----------------------------------------------------------------------
class PropertyAddingAction(WorkflowAction):
    type_id = 'creme_core-property_adding'
    verbose_name = _('Adding a property')

    # TODO: docstring
    def __init__(self, *,
                 entity_source: WorkflowActionSource,
                 ptype: str | CremePropertyType,  # TODO: accept UUID?
                 ):
        self._entity_source = entity_source
        if isinstance(ptype, str):
            self._ptype_uuid = ptype
            self._ptype = None
        else:
            assert isinstance(ptype, CremePropertyType)
            self._ptype_uuid = str(ptype.uuid)
            self._ptype = ptype

    @property
    def entity_source(self) -> WorkflowActionSource:
        return self._entity_source

    @property
    def description(self):
        # TODO: display info about source
        return _('Adding the property «{}»').format(self.property_type.text)

    # TODO: manage errors (CremePropertyType does not exist anymore)
    @property
    def property_type(self) -> CremePropertyType:
        ptype = self._ptype
        if ptype is None:
            self._ptype = ptype = CremePropertyType.objects.get(uuid=self._ptype_uuid)

        return ptype

    # TODO: do nothing (log?) if invalid ptype
    def execute(self, context):
        entity = self._entity_source.extract(context)
        if entity is not None:
            CremeProperty.objects.safe_create(
                creme_entity=entity, type=self.property_type,
            )

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['entity'] = self._entity_source.to_dict()
        d['ptype'] = self._ptype_uuid

        return d

    @classmethod
    def from_dict(cls, data: dict, registry):
        # TODO: error
        return cls(
            entity_source=registry.build_action_source(data['entity']),
            ptype=data['ptype'],
        )


class RelationAddingAction(WorkflowAction):
    type_id = 'creme_core-relation_adding'
    verbose_name = _('Adding a relationship')

    def __init__(self, *,
                 subject_source: WorkflowActionSource,
                 rtype: str | RelationType,
                 object_source: WorkflowActionSource,
                 ):
        self._subject_source = subject_source
        self._object_source = object_source

        if isinstance(rtype, str):
            self._rtype_id = rtype
            self._rtype = None
        else:
            assert isinstance(rtype, RelationType)
            self._rtype_id = rtype.id
            self._rtype = rtype

    @property
    def description(self):
        # TODO: display info about subject & object
        return _('Adding the relationship «{}»').format(self.relation_type.predicate)

    # TODO: do nothing (log?) if invalid rtype
    def execute(self, context):
        subject_entity = self._subject_source.extract(context)
        object_entity = self._object_source.extract(context)

        if subject_entity is not None and object_entity is not None:
            Relation.objects.safe_create(
                user=subject_entity.user,  # TODO: workflow user!
                subject_entity=subject_entity,
                type=self.relation_type,
                object_entity=object_entity,
            )

    @property
    def object_source(self) -> WorkflowActionSource:
        return self._object_source

    # TODO: manage errors (RelationType does not exist anymore)
    @property
    def relation_type(self) -> RelationType:
        rtype = self._rtype
        if rtype is None:
            self._rtype = rtype = RelationType.objects.get(id=self._rtype_id)

        return rtype

    @property
    def subject_source(self) -> WorkflowActionSource:
        return self._subject_source

    def to_dict(self):
        d = super().to_dict()
        d['subject'] = self._subject_source.to_dict()
        d['rtype'] = self._rtype_id
        d['object'] = self._object_source.to_dict()

        return d

    @classmethod
    def from_dict(cls, data: dict, registry):
        # TODO: error
        return cls(
            subject_source=registry.build_action_source(data['subject']),
            rtype=data['rtype'],
            object_source=registry.build_action_source(data['object']),
        )
