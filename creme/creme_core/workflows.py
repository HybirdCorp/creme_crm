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
from django.utils.html import format_html
from django.utils.safestring import mark_safe
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
# from .forms import workflows as wf_forms
from .models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    Relation,
    RelationType,
)
from .models.utils import model_verbose_name
from .templatetags.creme_widgets import widget_entity_hyperlink


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

    def __init__(self, *, model: type[CremeEntity]):
        self._model = model

    def __eq__(self, other):
        return isinstance(other, type(self)) and self._model == other._model

    def __repr__(self):
        return f'EntityCreationTrigger(model={self._model.__name__})'

    def activate(self, event):
        return (
            {CreatedEntitySource.type_id: event.entity}
            if isinstance(event, EntityCreated) and isinstance(event.entity, self._model) else
            None
        )

    @property
    def description(self):
        return gettext('A «{}» has been created').format(self._model._meta.verbose_name)

    @property
    def model(self):
        return self._model

    @classmethod
    def config_formfield(cls, model):
        from .forms.workflows import EntityCreationTriggerField

        return EntityCreationTriggerField(
            model=model,
            label=cls.verbose_name,
        )

    # TODO: manage errors
    @classmethod
    def from_dict(cls, data: dict) -> WorkflowTrigger:
        return cls(model=_str_to_model(data['model']))

    def to_dict(self):
        d = super().to_dict()
        d['model'] = _model_to_str(self._model)

        return d

    def root_sources(self):
        return [CreatedEntitySource(model=self._model)]


# TODO: base model class instead
#       + factorise better?
class EntityEditionTrigger(EntityCreationTrigger):
    type_id = 'creme_core-entity_edition'
    verbose_name = _('An entity has been modified')

    def __repr__(self):
        return f'EntityEditionTrigger(model={self._model.__name__})'

    def activate(self, event):
        return (
            {EditedEntitySource.type_id: event.entity}
            if isinstance(event, EntityEdited) and isinstance(event.entity, self._model) else
            None
        )

    @property
    def description(self):
        return gettext('A «{model}» has been modified').format(
            model=self._model._meta.verbose_name,
        )

    @classmethod
    def config_formfield(cls, model):
        from .forms.workflows import EntityEditionTriggerField

        return EntityEditionTriggerField(
            model=model,
            label=cls.verbose_name,
        )

    def root_sources(self):
        return [EditedEntitySource(model=self._model)]


class RelationAddingTrigger(WorkflowTrigger):
    type_id = 'creme_core-relation_adding'
    verbose_name = _('A Relationship has been added')

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

    def __eq__(self, other):
        return (
            isinstance(other, type(self))
            and self._subject_model == other._subject_model
            and self._rtype_id == other._rtype_id
            and self._object_model == other._object_model
        )

    def __repr__(self):
        return (
            f'RelationAddingTrigger('
            f'subject_model={self._subject_model.__name__}, '
            f'rtype="{self._rtype_id}", '
            f'object_model={self._object_model.__name__}'
            f')'
        )

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
                return {
                    SubjectEntitySource.type_id: rel.subject_entity,
                    ObjectEntitySource.type_id: rel.object_entity,
                }

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
    def config_formfield(cls, model):
        from .forms.workflows import RelationAddingTriggerField

        return RelationAddingTriggerField(
            model=model, label=cls.verbose_name,
        )

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

    def root_sources(self):
        return [
            SubjectEntitySource(model=self._subject_model),
            ObjectEntitySource(model=self._object_model),
        ]


# Action sources ---------------------------------------------------------------
# TODO: move to core (+ tests)?
# TODO: doc-strings
class _FromContextSource(WorkflowActionSource):
    description_format = 'Entity ({type})'

    def __init__(self, model: type[CremeEntity]):
        # assert issubclass(model, CremeEntity)
        self._model = model

    def __eq__(self, other):
        return isinstance(other, type(self)) and self._model == other._model

    def __repr__(self):
        return f'{type(self).__name__}(model={self._model.__name__})'

    @property
    def model(self):
        return self._model

    def extract(self, context: dict):
        # TODO: error (key error, same model?)
        return context[self.type_id]

    @classmethod
    def from_dict(cls, data, registry):
        # TODO: error
        return cls(model=_str_to_model(data['model']))

    def to_dict(self):
        d = super().to_dict()
        d['model'] = _model_to_str(self._model)

        return d

    def _label(self):
        return self.description_format.format(type=model_verbose_name(self._model))

    def render(self, user, mode):
        return self._label()


class CreatedEntitySource(_FromContextSource):
    type_id = 'created_entity'
    description_format = _('Created entity ({type})')

    def config_formfield(self):
        from .forms.workflows import CreatedEntitySourceField

        return CreatedEntitySourceField(label=self._label(), model=self._model)


class EditedEntitySource(_FromContextSource):
    type_id = 'edited_entity'
    description_format = _('Modified entity ({type})')

    def config_formfield(self):
        from .forms.workflows import EditedEntitySourceField

        return EditedEntitySourceField(label=self._label(), model=self._model)


class SubjectEntitySource(_FromContextSource):
    type_id = 'subject_entity'
    description_format = _('Subject of the created relationship ({type})')

    def config_formfield(self):
        from .forms.workflows import SubjectEntitySourceField

        return SubjectEntitySourceField(label=self._label(), model=self._model)


class ObjectEntitySource(_FromContextSource):
    type_id = 'object_entity'
    description_format = _('Object of the created relationship ({type})')

    def config_formfield(self):
        from .forms.workflows import ObjectEntitySourceField

        return ObjectEntitySourceField(label=self._label(), model=self._model)


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

    @classmethod
    def composed_config_formfield(cls, sub_source, user):
        from .forms.workflows import FixedEntitySourceField

        return FixedEntitySourceField(label=_('Specific entity'), user=user)

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

    def render(self, user, mode):
        entity = self.entity

        match mode:
            case self.HTML:
                return format_html(
                    '<span>{link}&nbsp;{label}</span>',
                    label=gettext('(fixed entity)'),
                    link=widget_entity_hyperlink(entity=entity, user=user),
                )

            case self.TEXT_PLAIN:
                return (
                    gettext('Fixed entity «{entity}» [deleted]')
                    if entity.is_deleted else
                    gettext('Fixed entity «{entity}»')
                ).format(entity=entity.allowed_str(user))  # TODO: test allowed_str()

            case _:
                raise ValueError()


class EntityFKSource(WorkflowActionSource):
    type_id = 'entity_fk'

    def __init__(self, *, entity_source: WorkflowActionSource, field_name: str):
        self._entity_source = entity_source
        self._field_name = field_name

    def __eq__(self, other):
        return (
            isinstance(other, type(self))
            and self._field_name == other._field_name
            and self._entity_source == other._entity_source
        )

    def __repr__(self):
        return (
            f'EntityFKSource('
            f'entity_source={self._entity_source!r}, '
            f'field_name="{self._field_name}"'
            f')'
        )

    # TODO: error
    @property
    def model(self):
        return self._entity_source.model._meta.get_field(self._field_name).related_model

    @property
    def field_name(self):
        return self._field_name

    @property
    def instance_source(self):
        return self._entity_source

    @classmethod
    def composed_config_formfield(cls, sub_source, user):
        from .forms.workflows import EntityFKSourceField

        field = EntityFKSourceField(
            label=_('Field of: {source}').format(
                source=sub_source.render(user=user, mode=sub_source.TEXT_PLAIN),
            ),
            entity_source=sub_source,
        )

        return field if field.choices else None

    def extract(self, context: dict):
        # TODO: error?
        instance = self._entity_source.extract(context=context)
        return None if instance is None else getattr(instance, self._field_name)

    @classmethod
    def from_dict(cls, data: dict, registry):
        # TODO: error (key, field exists, field is FK?)
        return cls(
            entity_source=registry.build_action_source(data['entity']),
            field_name=data['field'],
        )

    def to_dict(self):
        d = super().to_dict()
        d['entity'] = self._entity_source.to_dict()
        d['field'] = self._field_name

        return d

    # TODO: manage hidden field?
    def render(self, user, mode):
        source = self._entity_source
        result = gettext('Field «{field}» of: {source}').format(
            # TODO: factorise?
            field=source.model._meta.get_field(self._field_name).verbose_name,
            source=source.render(user=user, mode=mode),
        )

        match mode:
            case self.HTML:
                return mark_safe(f'<span>{result}</span>')

            case self.TEXT_PLAIN:
                return result

            case _:
                raise ValueError()


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

    def __repr__(self):
        return (
            f'FirstRelatedEntitySource('
            f'subject_source={self._subject_source!r}, '
            f'rtype="{self._rtype_id}", '
            f'object_model={self._object_model.__name__}'
            f')'
        )

    @property
    def model(self):
        return self._object_model

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

    @classmethod
    def composed_config_formfield(cls, sub_source, user):
        from .forms.workflows import FirstRelatedEntitySourceField

        return FirstRelatedEntitySourceField(
            label=_('First related entity to: {source}').format(
                source=sub_source.render(user=user, mode=sub_source.TEXT_PLAIN),
            ),
            subject_source=sub_source,
        )

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

    # TODO: disabled rtype
    def render(self, user, mode):
        result = _('First related «{type}» by «{predicate}» to: {source}').format(
            type=self._object_model._meta.verbose_name,
            predicate=self.relation_type.predicate,
            source=self._subject_source.render(user=user, mode=mode),
        )

        match mode:
            case self.HTML:
                return mark_safe(f'<span>{result}</span>')

            case self.TEXT_PLAIN:
                return result

            case _:
                raise ValueError()


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

    @classmethod
    def config_form_class(cls):
        from creme.creme_core.forms.workflows import PropertyAddingActionForm
        return PropertyAddingActionForm

    @property
    def entity_source(self) -> WorkflowActionSource:
        return self._entity_source

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

    def render(self, user) -> str:
        source = self._entity_source

        return mark_safe(
            _('Adding the property «{property}» to: {source}').format(
                property=self.property_type.text,
                source=source.render(user=user, mode=source.HTML),
            )
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

    # TODO
    # @classmethod
    # def config_form_class(cls):
    #     from creme.creme_core.forms.workflows import RelationAddingActionForm
    #     return RelationAddingActionForm

    # TODO: do nothing (log?) if invalid rtype
    def execute(self, context):
        subject_entity = self._subject_source.extract(context)
        object_entity = self._object_source.extract(context)

        # TODO: check constraints (properties)

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

    def render(self, user):
        subject_source = self._subject_source
        object_source = self._object_source

        return format_html(
            '<div>'
            '{label}'
            ' <ul>'
            '  <li>{subject}</li>'
            '  <li>{object}</li>'
            ' </ul>'
            '</div>',
            label=_('Adding the relationship «{predicate}» between:').format(
                predicate=self.relation_type.predicate,
            ),
            subject=subject_source.render(user=user, mode=subject_source.HTML),
            object=object_source.render(user=user, mode=object_source.HTML),
        )
