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
from typing import Literal
from uuid import UUID

from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db.models import ForeignKey
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from .core.workflow import (
    EntityCreated,
    EntityEdited,
    FromContextSource,
    PropertyAdded,
    RelationAdded,
    WorkflowAction,
    WorkflowBrokenData,
    WorkflowSource,
    WorkflowTrigger,
    _EntityEvent,
    model_as_key,
    model_from_key,
)
from .models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    Relation,
    RelationType,
)
from .models.utils import model_verbose_name
from .templatetags.creme_widgets import widget_entity_hyperlink

logger = logging.getLogger(__name__)


# Triggers ---------------------------------------------------------------------
class _EntityTrigger(WorkflowTrigger):
    # NB: override in child classes
    event_class = _EntityEvent
    description_format = 'A «{model}» is concerned'

    def __init__(self, *, model: type[CremeEntity]):
        self._model = model

    def __eq__(self, other):
        return isinstance(other, type(self)) and self._model == other._model

    def __repr__(self):
        return f'{type(self).__name__}(model={self._model.__name__})'

    @property
    def source_class(self):
        raise NotImplementedError

    def _activate(self, event):
        assert isinstance(event, _EntityEvent)

        # NB: we avoid isinstance() & call get_real_entity() because some code
        #     could use raw entities to be faster, and so we get a simple
        #     <CremeEntity> object (not sure this case happens in vanilla code) .
        return (
            # {self.source_class.type_id: event.entity}
            {self.source_class.type_id: event.entity.get_real_entity()}
            # if isinstance(event.entity, self._model) else
            if event.entity.entity_type.model_class() == self._model else
            None
        )

    @property
    def description(self):
        return self.description_format.format(model=self._model._meta.verbose_name)

    @property
    def model(self):
        return self._model

    @classmethod
    def from_dict(cls, data):
        return cls(model=model_from_key(data['model']))

    def to_dict(self):
        d = super().to_dict()
        d['model'] = model_as_key(self._model)

        return d

    def root_sources(self):
        return [self.source_class(model=self._model)]


class EntityCreationTrigger(_EntityTrigger):
    """Trigger corresponding to the creation of a CremeEntity with a specific model."""
    type_id = 'creme_core-entity_creation'
    verbose_name = _('An entity has been created')
    event_class = EntityCreated
    description_format = _('A «{model}» has been created')

    @property
    def source_class(self):
        return CreatedEntitySource

    @classmethod
    def config_formfield(cls, model):
        from .forms.workflows import EntityCreationTriggerField

        return EntityCreationTriggerField(model=model, label=cls.verbose_name)


class EntityEditionTrigger(_EntityTrigger):
    """Trigger corresponding to the modification of a CremeEntity with a specific model."""
    type_id = 'creme_core-entity_edition'
    verbose_name = _('An entity has been modified')
    event_class = EntityEdited
    conditions_use_or = True
    conditions_detect_change = True
    description_format = _('A «{model}» has been modified')

    @property
    def source_class(self):
        return EditedEntitySource

    @classmethod
    def config_formfield(cls, model):
        from .forms.workflows import EntityEditionTriggerField

        return EntityEditionTriggerField(model=model, label=cls.verbose_name)


class PropertyAddingTrigger(WorkflowTrigger):
    type_id = 'creme_core-property_adding'
    verbose_name = _('A property has been added')
    event_class = PropertyAdded

    _entity_model: type[CremeEntity]
    _ptype_uuid: UUID
    _ptype = CremePropertyType | None | Literal[False]

    def __init__(self, *,
                 entity_model: type[CremeEntity],
                 ptype: str | CremePropertyType,
                 ):
        self._entity_model = entity_model

        if isinstance(ptype, str):
            self._ptype_uuid = UUID(ptype)
            self._ptype = None
        else:
            assert isinstance(ptype, CremePropertyType)
            self._ptype_uuid = ptype.uuid
            self._ptype = ptype

    def __eq__(self, other):
        return (
            isinstance(other, type(self))
            and self._entity_model == other._entity_model
            and self._ptype_uuid == other._ptype_uuid
        )

    def __repr__(self):
        return (
            f'PropertyAddingTrigger('
            f'entity_model={self._entity_model.__name__}, '
            f'ptype="{self._ptype_uuid}"'
            f')'
        )

    def _activate(self, event):
        assert isinstance(event, PropertyAdded)

        prop = event.creme_property

        if (
            # We compare UUIDs in order to avoid retrieving the property-type
            prop.type.uuid == self._ptype_uuid
            # NB: we avoid isinstance() & call get_real_entity() because some code
            #     could use raw entities to be faster, and so we get a simple
            #     <CremeEntity> object (not sure this case happens in vanilla code) .
            # TODO: add a RealEntityForeignKey in CremeProperty?
            # and isinstance(prop.creme_entity, self._entity_model)
            and prop.creme_entity.entity_type.model_class() == self._entity_model
        ):
            return {
                # TaggedEntitySource.type_id: prop.creme_entity,
                TaggedEntitySource.type_id: prop.creme_entity.get_real_entity(),
            }

        return None

    @property
    def description(self):
        try:
            return gettext(
                'A property «{label}» has been added'
            ).format(label=self.property_type.text)
        except WorkflowBrokenData as e:
            return format_html(
                '{label}<p class="errorlist">{error}</p>',
                label=_('A property has been added'),
                error=str(e),
            )

    @property
    def entity_model(self) -> type[CremeEntity]:
        return self._entity_model

    # TODO: factorise
    @property
    def property_type(self) -> CremePropertyType:
        ptype = self._ptype
        if ptype is None:
            self._ptype = ptype = CremePropertyType.objects.filter(
                uuid=self._ptype_uuid,
            ).first() or False

        if ptype is False:
            raise WorkflowBrokenData(
                gettext('The property type does not exist anymore')
            )

        return ptype

    @classmethod
    def config_formfield(cls, model):
        from .forms.workflows import PropertyAddingTriggerField

        return PropertyAddingTriggerField(
            model=model, label=cls.verbose_name,
        )

    @classmethod
    def from_dict(cls, data) -> PropertyAddingTrigger:
        return cls(
            # TODO: check is an entity model?
            entity_model=model_from_key(data['entity_model']),
            ptype=data['ptype'],
        )

    def to_dict(self):
        d = super().to_dict()
        d['ptype'] = str(self._ptype_uuid)
        d['entity_model'] = model_as_key(self._entity_model)

        return d

    def root_sources(self):
        return [TaggedEntitySource(model=self._entity_model)]


class RelationAddingTrigger(WorkflowTrigger):
    type_id = 'creme_core-relation_adding'
    verbose_name = _('A relationship has been added')
    event_class = RelationAdded

    _subject_model: type[CremeEntity]
    _object_model: type[CremeEntity]
    _rtype_id: str
    _rtype = RelationType | None

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

    def _activate(self, event):
        assert isinstance(event, RelationAdded)

        rel = event.relation

        # NB: we avoid isinstance() & call get_real_entity() because some code
        #     use raw entities to be faster, and so we get simple <CremeEntity> objects.
        if (
            rel.type_id == self._rtype_id
            # and isinstance(rel.subject_entity, self._subject_model)
            and rel.subject_entity.entity_type.model_class() == self._subject_model
            # and isinstance(rel.object_entity, self._object_model)
            and rel.object_ctype.model_class() == self._object_model
        ):
            # TODO: populate real entities?
            return {
                # SubjectEntitySource.type_id: rel.subject_entity,
                SubjectEntitySource.type_id: rel.subject_entity.get_real_entity(),
                # ObjectEntitySource.type_id: rel.object_entity,
                ObjectEntitySource.type_id: rel.object_entity.get_real_entity(),
            }

        return None

    @property
    def description(self):
        try:
            return gettext(
                'A relationship «{predicate}» has been added to a «{model}»'
            ).format(
                predicate=self.relation_type.predicate,
                model=self._object_model._meta.verbose_name,
            )
        except WorkflowBrokenData as e:
            return format_html(
                '{label}<p class="errorlist">{error}</p>',
                label=_('A relationship has been added'),
                error=str(e),
            )

    @property
    def object_model(self) -> type[CremeEntity]:
        return self._object_model

    # TODO: factorise
    @property
    def relation_type(self) -> RelationType:
        rtype = self._rtype
        if rtype is None:
            self._rtype = rtype = RelationType.objects.filter(id=self._rtype_id).first() or False

        if rtype is False:
            raise WorkflowBrokenData(
                gettext('The relationship type does not exist anymore')
            )

        return rtype

    @property
    def subject_model(self) -> type[CremeEntity]:
        return self._subject_model

    @classmethod
    def config_formfield(cls, model):
        from .forms.workflows import RelationAddingTriggerField

        return RelationAddingTriggerField(model=model, label=cls.verbose_name)

    @classmethod
    def from_dict(cls, data):
        return cls(
            subject_model=model_from_key(data['subject_model']),
            rtype=data['rtype'],
            object_model=model_from_key(data['object_model']),
        )

    def to_dict(self):
        d = super().to_dict()
        d['rtype'] = self._rtype_id
        d['subject_model'] = model_as_key(self._subject_model)
        d['object_model'] = model_as_key(self._object_model)

        return d

    def root_sources(self):
        return [
            SubjectEntitySource(model=self._subject_model),
            ObjectEntitySource(model=self._object_model),
        ]


# Action sources ---------------------------------------------------------------
class CreatedEntitySource(FromContextSource):
    """Source corresponding to a created entity.
    This entity is injected in the context by a 'EntityCreationTrigger'.
    """
    type_id = 'created_entity'
    verbose_name = _('Created entity')
    description_format = _('Created entity ({type})')

    def config_formfield(self, user):
        from .forms.workflows import CreatedEntitySourceField

        return CreatedEntitySourceField(label=self._label(), model=self._model)


class EditedEntitySource(FromContextSource):
    """Source corresponding to a modified entity.
    This entity is injected in the context by a 'EntityEditionTrigger'.
    """
    type_id = 'edited_entity'
    verbose_name = _('Modified entity')
    description_format = _('Modified entity ({type})')

    def config_formfield(self, user):
        from .forms.workflows import EditedEntitySourceField

        return EditedEntitySourceField(label=self._label(), model=self._model)


class TaggedEntitySource(FromContextSource):
    """Source corresponding to the entity of a new CremeProperty.
    This entity is injected in the context by a 'PropertyAddingTrigger'.
    """
    type_id = 'tagged_entity'
    verbose_name = _('Received a new property')
    description_format = _('Received a new property ({type})')

    def config_formfield(self, user):
        from .forms.workflows import TaggedEntitySourceField

        return TaggedEntitySourceField(label=self._label(), model=self._model)


class SubjectEntitySource(FromContextSource):
    """Source corresponding to the subject of a new Relation.
    This entity is injected in the context by a 'RelationAddingTrigger'.
    """
    type_id = 'subject_entity'
    verbose_name = _('Subject of the created relationship')
    description_format = _('Subject of the created relationship ({type})')

    def config_formfield(self, user):
        from .forms.workflows import SubjectEntitySourceField

        return SubjectEntitySourceField(label=self._label(), model=self._model)


class ObjectEntitySource(FromContextSource):
    """Source corresponding to the object of a new Relation.
    This entity is injected in the context by a 'RelationAddingTrigger'.
    """
    type_id = 'object_entity'
    verbose_name = _('Object of the created relationship')
    description_format = _('Object of the created relationship ({type})')

    def config_formfield(self, user):
        from .forms.workflows import ObjectEntitySourceField

        return ObjectEntitySourceField(label=self._label(), model=self._model)


class FixedEntitySource(WorkflowSource):
    """Source corresponding to a specific/given instance in database."""
    type_id = 'fixed_entity'
    verbose_name = _('Fixed entity')

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
        return f'{type(self).__name__}(entity={self._entity_uuid}), model={self._model}))'

    @property
    def entity(self) -> CremeEntity:
        entity = self._entity
        if entity is None:
            self._entity = entity = self._model.objects.filter(
                uuid=self._entity_uuid,
            ).first() or False

        if entity is False:
            raise WorkflowBrokenData(
                gettext('The «{model}» does not exist anymore').format(
                    model=model_verbose_name(self._model)
                )
            )

        return entity

    @property
    def model(self) -> type[CremeEntity]:
        return self._model

    @classmethod
    def standalone_config_formfield(cls, user):
        from .forms.workflows import FixedEntitySourceField

        return FixedEntitySourceField(label=_('Fixed entity'), user=user)

    def extract(self, context):
        try:
            return self.entity
        except WorkflowBrokenData:
            return None

    @classmethod
    def from_dict(cls, data, registry) -> FixedEntitySource:
        return cls(model=model_from_key(data['model']), entity=data['uuid'])

    def to_dict(self):
        d = super().to_dict()
        d['uuid'] = self._entity_uuid
        d['model'] = model_as_key(self._model)

        return d

    def render(self, user, mode):
        try:
            entity = self.entity
        except WorkflowBrokenData:
            match mode:
                case self.RenderMode.HTML:
                    return format_html(
                        '{label}<p class="errorlist">{error}</p>',
                        label=gettext('A fixed «{model}»').format(
                            model=model_verbose_name(self._model),
                        ),
                        # Translators: "it" means "model"
                        error=gettext('It does not exist anymore'),
                    )

                case self.RenderMode.TEXT_PLAIN:
                    return gettext(
                        'The fixed «{model}» does not exist anymore'
                    ).format(model=model_verbose_name(self._model))

                case _:
                    raise ValueError()

        match mode:
            case self.RenderMode.HTML:
                return format_html(
                    '<span>{link}&nbsp;{label}</span>',
                    label=gettext('(fixed entity)'),
                    link=widget_entity_hyperlink(entity=entity, user=user),
                )

            case self.RenderMode.TEXT_PLAIN:
                return (
                    gettext('Fixed entity «{entity}» [deleted]')
                    if entity.is_deleted else
                    gettext('Fixed entity «{entity}»')
                ).format(entity=entity.allowed_str(user))  # TODO: test allowed_str()

            case _:
                raise ValueError()


# TODO: manage hidden field? (extract, render)
class EntityFKSource(WorkflowSource):
    """Source which uses a ForeignKey to a subclass of CremeEntity.
    So it needs a sub-source to work, for the instance owning the FK.
    """
    type_id = 'entity_fk'
    verbose_name = _('Field to another entity')

    def __init__(self, *, entity_source: WorkflowSource, field_name: str):
        model = entity_source.model  # NB: can raise exception on BrokenSource
        try:
            field = model._meta.get_field(field_name)
        except FieldDoesNotExist:
            raise WorkflowBrokenData(
                gettext('The field «{field}» is invalid in model «{model}»').format(
                    field=field_name, model=model_verbose_name(model),
                )
            )
        else:
            if (
                not isinstance(field, ForeignKey)
                or not issubclass(field.related_model, CremeEntity)
            ):
                raise WorkflowBrokenData(
                    gettext('The field «{field}» does not reference an entity').format(
                        field=field.verbose_name,
                    )
                )

        self._field = field
        self._entity_source = entity_source
        self._field_name = field_name

    def __eq__(self, other):
        return (
            isinstance(other, type(self))
            and self._field_name == other._field_name  # TODO: test
            and self._entity_source == other._entity_source
        )

    def __repr__(self):
        return (
            f'{type(self).__name__}('
            f'entity_source={self._entity_source!r}, '
            f'field_name="{self._field_name}"'
            f')'
        )

    @property
    def model(self):
        return self._field.related_model

    @property
    def field_name(self):
        return self._field_name

    @classmethod
    def composed_config_formfield(cls, sub_source, user):
        from .forms.workflows import EntityFKSourceField

        field = EntityFKSourceField(
            label=gettext('Field of: {source}').format(
                source=sub_source.render(user=user, mode=sub_source.RenderMode.TEXT_PLAIN),
            ),
            entity_source=sub_source,
        )

        return field if field.choices else None

    def extract(self, context):
        instance = self._entity_source.extract(context=context)
        return None if instance is None else getattr(instance, self._field_name)

    @classmethod
    def from_dict(cls, data, registry) -> EntityFKSource:
        return cls(
            entity_source=registry.build_source(data['entity']),
            field_name=data['field'],
        )

    def to_dict(self):
        d = super().to_dict()
        d['entity'] = self._entity_source.to_dict()
        d['field'] = self._field_name

        return d

    def render(self, user, mode):
        source = self._entity_source
        result = gettext('Field «{field}» of: {source}').format(
            field=self._field.verbose_name,
            source=source.render(user=user, mode=mode),
        )

        match mode:
            case self.RenderMode.HTML:
                return mark_safe(f'<span>{result}</span>')

            case self.RenderMode.TEXT_PLAIN:
                return result

            case _:
                raise ValueError()

    @property
    def sub_source(self):
        return self._entity_source


# TODO: manage disabled rtype? (render, extract? ...)
class FirstRelatedEntitySource(WorkflowSource):
    """Source which retrieves the first CremeEntity:
      - of a given model
      - which is linked to the sub-source's CremeEntity
      - by a Relation of a fixed type.
    """
    type_id = 'first_related'
    verbose_name = _('First related entity')

    def __init__(self, *,
                 subject_source: WorkflowSource,
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
            f'{type(self).__name__}('
            f'subject_source={self._subject_source!r}, '
            f'rtype="{self._rtype_id}", '
            f'object_model={self._object_model.__name__}'
            f')'
        )

    @property
    def model(self):
        return self._object_model

    @property
    def object_model(self):
        return self._object_model

    # TODO: factorise (see RelationAddingTrigger)
    @property
    def relation_type(self) -> RelationType:
        rtype = self._rtype
        if rtype is None:
            self._rtype = rtype = RelationType.objects.filter(id=self._rtype_id).first() or False

        if rtype is False:
            raise WorkflowBrokenData(
                gettext('The relationship type does not exist anymore')
            )

        return rtype

    @classmethod
    def composed_config_formfield(cls, sub_source, user):
        from .forms.workflows import FirstRelatedEntitySourceField

        return FirstRelatedEntitySourceField(
            label=gettext('First related entity to: {source}').format(
                source=sub_source.render(user=user, mode=sub_source.RenderMode.TEXT_PLAIN),
            ),
            subject_source=sub_source,
        )

    def extract(self, context: dict):
        subject = self._subject_source.extract(context=context)

        if subject is not None:
            try:
                return self._object_model.objects.filter(
                    relations__type=self.relation_type.symmetric_type_id,
                    relations__object_entity=subject,
                ).first()
            except WorkflowBrokenData:
                pass

        return None

    @classmethod
    def from_dict(cls, data: dict, registry) -> FirstRelatedEntitySource:
        return cls(
            subject_source=registry.build_source(data['subject']),
            rtype=data['rtype'],
            object_model=model_from_key(data['object_model']),
        )

    def to_dict(self):
        d = super().to_dict()
        d['subject'] = self._subject_source.to_dict()
        d['rtype'] = self._rtype_id
        d['object_model'] = model_as_key(self._object_model)

        return d

    def render(self, user, mode):
        try:
            predicate = self.relation_type.predicate
        except WorkflowBrokenData as e:
            match mode:
                case self.RenderMode.HTML:
                    return format_html(
                        '{label}<p class="errorlist">{error}</p>',
                        label=self.verbose_name,
                        error=e,
                    )

                case self.RenderMode.TEXT_PLAIN:
                    return gettext('{error} (first related entity)').format(error=e)

                case _:
                    raise ValueError()

        result = gettext(
            'First related «{type}» by «{predicate}» to: {source}'
        ).format(
            type=self._object_model._meta.verbose_name,
            predicate=predicate,
            source=self._subject_source.render(user=user, mode=mode),
        )

        match mode:
            case self.RenderMode.HTML:
                return mark_safe(f'<span>{result}</span>')

            case self.RenderMode.TEXT_PLAIN:
                return result

            case _:
                raise ValueError()

    @property
    def sub_source(self):
        return self._subject_source


# Actions ----------------------------------------------------------------------
class PropertyAddingAction(WorkflowAction):
    """Action which adds a CremeProperty to the chosen source."""
    type_id = 'creme_core-property_adding'
    verbose_name = _('Adding a property')

    def __init__(self, *,
                 entity_source: WorkflowSource,
                 ptype: str | CremePropertyType,  # TODO: accept UUID?
                 ):
        self._entity_source = entity_source
        if isinstance(ptype, str):
            self._ptype_uuid = UUID(ptype)
            self._ptype = None
        else:
            assert isinstance(ptype, CremePropertyType)
            self._ptype_uuid = ptype.uuid
            self._ptype = ptype

    def __eq__(self, other):
        return (
            isinstance(other, type(self))
            and self._entity_source == other._entity_source
            and self._ptype_uuid == other._ptype_uuid
        )

    def __repr__(self):
        return (
            f'{type(self).__name__}('
            f'entity_source={self._entity_source!r}, '
            f'ptype={self.property_type!r}'
            f')'
        )

    @classmethod
    def config_form_class(cls):
        from creme.creme_core.forms.workflows import PropertyAddingActionForm
        return PropertyAddingActionForm

    @property
    def entity_source(self) -> WorkflowSource:
        return self._entity_source

    # TODO: factorise
    @property
    def property_type(self) -> CremePropertyType:
        ptype = self._ptype
        if ptype is None:
            self._ptype = ptype = CremePropertyType.objects.filter(
                uuid=self._ptype_uuid,
            ).first() or False

        if ptype is False:
            raise WorkflowBrokenData(
                gettext('The property type does not exist anymore')
            )

        return ptype

    def execute(self, context, user=None):
        entity = self._entity_source.extract(context)
        if entity is not None:
            try:
                ptype = self.property_type
            except WorkflowBrokenData as e:
                # TODO: log in a model WorkflowResult?
                logger.error(
                    'The action PropertyAddingAction cannot be performed: %s', e,
                )
            else:
                if ptype.is_compatible(type(entity)):
                    CremeProperty.objects.safe_create(creme_entity=entity, type=ptype)
                else:
                    # TODO: log in a model WorkflowResult?
                    logger.warning(
                        'The action PropertyAddingAction will not add a property "%s" '
                        'because the content type of "%s" is not compatible',
                        ptype, entity,
                    )

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['entity'] = self._entity_source.to_dict()
        d['ptype'] = str(self._ptype_uuid)

        return d

    @classmethod
    def from_dict(cls, data: dict, registry) -> PropertyAddingAction:
        return cls(
            entity_source=registry.build_source(data['entity']),
            ptype=data['ptype'],
        )

    def render(self, user):
        source = self._entity_source

        try:
            ptype = self.property_type
        except WorkflowBrokenData as e:
            return format_html(
                '{label}<p class="errorlist">{error}</p>',
                label=gettext('Adding a property'),
                error=e,
            )

        label = format_html(
            gettext('Adding the property «{property}» to: {source}'),
            property=ptype.text,
            source=source.render(user=user, mode=source.RenderMode.HTML),
        )

        if not ptype.is_compatible(source.model):
            return format_html(
                '{label}<p class="errorlist">{error}</p>',
                label=label,
                error=gettext('The source type is not compatible with this property type'),
            )

        return label


class RelationAddingAction(WorkflowAction):
    """Action which creates a Relation between 2 chosen sources."""
    type_id = 'creme_core-relation_adding'
    verbose_name = _('Adding a relationship')

    def __init__(self, *,
                 subject_source: WorkflowSource,
                 rtype: str | RelationType,
                 object_source: WorkflowSource,
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

    def __eq__(self, other):
        return (
            isinstance(other, type(self))
            and self._subject_source == other._subject_source
            and self._rtype_id == other._rtype_id
            and self._object_source == other._object_source
        )

    def __repr__(self):
        return (
            f'{type(self).__name__}('
            f'subject_source={self._subject_source!r}, '
            f'rtype={self.relation_type!r}, '
            f'object_source={self._object_source!r}'
            f')'
        )

    @classmethod
    def config_form_class(cls):
        from creme.creme_core.forms.workflows import RelationAddingActionForm
        return RelationAddingActionForm

    def execute(self, context, user=None):
        subject_entity = self._subject_source.extract(context)
        object_entity = self._object_source.extract(context)

        if subject_entity is not None and object_entity is not None:
            try:
                rtype = self.relation_type
            except WorkflowBrokenData as e:
                # TODO: log in a model WorkflowResult?
                logger.error(
                    'The action RelationAddingAction cannot be performed: %s', e,
                )
            else:
                relation = Relation(
                    user=user or subject_entity.user,
                    subject_entity=subject_entity,
                    type=rtype,
                    object_entity=object_entity,
                )

                try:
                    relation.clean()
                except ValidationError as e:
                    logger.warning(
                        'Workflow action will not add a Relation. %s',
                        ' '.join(e.messages),
                    )
                else:
                    Relation.objects.safe_multi_save(relations=[relation])

    @property
    def object_source(self) -> WorkflowSource:
        return self._object_source

    @property
    def relation_type(self) -> RelationType:
        rtype = self._rtype
        if rtype is None:
            self._rtype = rtype = RelationType.objects.filter(id=self._rtype_id).first() or False

        if rtype is False:
            raise WorkflowBrokenData(
                gettext('The relationship type does not exist anymore')
            )

        return rtype

    @property
    def subject_source(self) -> WorkflowSource:
        return self._subject_source

    def to_dict(self):
        d = super().to_dict()
        d['subject'] = self._subject_source.to_dict()
        d['rtype'] = self._rtype_id
        d['object'] = self._object_source.to_dict()

        return d

    @classmethod
    def from_dict(cls, data: dict, registry) -> RelationAddingAction:
        return cls(
            subject_source=registry.build_source(data['subject']),
            rtype=data['rtype'],
            object_source=registry.build_source(data['object']),
        )

    def render(self, user):
        try:
            rtype = self.relation_type
        except WorkflowBrokenData as e:
            return format_html(
                '{label}<p class="errorlist">{error}</p>',
                label=gettext('Adding a relationship'), error=e,
            )

        subject_source = self._subject_source
        object_source = self._object_source

        return format_html(
            '<div>'
            '{label}'
            ' <ul>'
            '  <li>{subject}{subject_error}</li>'
            '  <li>{object}{object_error}</li>'
            ' </ul>'
            '</div>',
            label=gettext(
                'Adding the relationship «{predicate}» between:'
            ).format(predicate=rtype.predicate),
            subject=subject_source.render(user=user, mode=subject_source.RenderMode.HTML),
            subject_error='' if rtype.is_compatible(
                subject_source.model
            ) else format_html(
                '<p class="errorlist">{error}</p>',
                error=gettext(
                    'The source type is not compatible with this relationship type'
                ),
            ),
            object=object_source.render(user=user,  mode=object_source.RenderMode.HTML),
            object_error='' if rtype.symmetric_type.is_compatible(
                object_source.model
            ) else format_html(
                '<p class="errorlist">{error}</p>',
                error=gettext(
                    'The source type is not compatible with this relationship type'
                ),
            ),
        )
