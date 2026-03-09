################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2025-2026  Hybird
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
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db.models import ForeignKey
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from .core.notification import OneEntityTemplateStringContent
from .core.workflow import (
    EntityCreated,
    EntityEdited,
    FromContextSource,
    PropertyAdded,
    RelationAdded,
    WorkflowAction,
    WorkflowBrokenData,
    WorkflowRegistry,
    WorkflowSource,
    WorkflowTrigger,
    _EntityEvent,
    model_as_key,
    model_from_key,
    workflow_registry,
)
from .models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    CremeUser,
    Notification,
    NotificationChannel,
    Relation,
    RelationType,
)
from .models.utils import model_verbose_name
from .templatetags.creme_widgets import widget_entity_hyperlink

if TYPE_CHECKING:
    from django.forms import Field as FormField


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
        return (
            f'{type(self).__name__}('
            f'entity="{self._entity_uuid}", '
            f'model={self._model.__name__}'
            f')'
        )

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


# User Sources------------------------------------------------------------------

class UserSource:
    """Base class to represent a user which can be used by an action.
    The user may be extracted from the Workflow's context.
    Example: used by the action which send notifications (<NotificationSendingAction>).
    """
    type_id: str = ''
    verbose_name = '??'

    @classmethod
    def config_formfield(cls,
                         user: CremeUser,
                         entity_source: WorkflowSource | None = None,
                         ) -> FormField:
        """Returns a form field which can be used in the configuration form of a
        WorkflowAction.
        @return A field with a 'clean()' method which returns an instance of
                'UserSource'.
        """
        raise NotImplementedError

    @classmethod
    def config_formfield_kind_id(cls,
                                 wf_source: WorkflowSource | None = None
                                 ) -> str:
        """Generate an ID for the related configuration form-field.
        This ID is used by 'UserSourceField' to distinguish the different kinds
        of sources.
        Hint: you probably don't have to override this method in child classes.
        @parameter wf_source: Should the same WorkflowSource instance used by
                   the form-field itself.
        """
        return (
            cls.type_id
            if wf_source is None else
            f'{wf_source.config_formfield_kind_id()}|{cls.type_id}'
        )

    @classmethod
    def from_dict(cls, data: dict, registry: WorkflowRegistry) -> UserSource:
        """Build an instance from a dictionary (produced by the method <to_dict()>)."""
        raise NotImplementedError

    def to_dict(self) -> dict:
        """Serialize to a JSON friendly dictionary
        Hint: see the method 'from_dict()' too.
        """
        return {'type': self.type_id}

    def render(self, user: CremeUser) -> str:
        """Render as HTML to describe in the configuration UI."""
        raise NotImplementedError

    def extract(self, context: dict) -> CremeUser | None:
        """Extract the user instance from the Workflow's context.
        @return None if the source did not manage to extract a user.
        """
        raise NotImplementedError

    @property
    def wf_source(self) -> WorkflowSource | None:
        """Some user-source classes extract their entities from a WorkflowSource.
        This property returns the source which is used.
        E.g.: UserFKSource
        @return: The source, or 'None' if no source is used.
        """
        return None


class FixedUserSource(UserSource):
    """This source just returns a CremeUser with a fixed UUID."""
    type_id = 'fixed_user'
    verbose_name = _('Fixed user')

    # TODO: accept UUID too?
    def __init__(self, *, user):
        if isinstance(user, str):
            self._user_uuid = UUID(user)
            self._user = None
        else:
            assert isinstance(user, CremeUser)
            self._user_uuid = user.uuid
            self._user = user

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.user == other.user

    def __repr__(self):
        return f'{type(self).__name__}(user={self.user!r})'

    @classmethod
    def config_formfield(cls, user, entity_source=None):
        from .forms.workflows import FixedUserSourceField

        return FixedUserSourceField(
            label=cls.verbose_name,
        )  if entity_source is None else None

    def extract(self, context):
        try:
            user = self.user
        except WorkflowBrokenData:
            return None

        return user if user.is_active else None

    @property
    def user(self):
        user = self._user
        if user is None:
            self._user = user = CremeUser.objects.filter(uuid=self._user_uuid).first() or False

        if user is False:
            raise WorkflowBrokenData(
                gettext('The user does not exist anymore')
            )

        return user

    @classmethod
    def from_dict(cls, data, registry):
        return cls(user=data['user'])

    def to_dict(self):
        d = super().to_dict()
        d['user'] = str(self._user_uuid)

        return d

    def render(self, user):
        try:
            user = self.user
        except WorkflowBrokenData as e:
            return format_html(
                '{label}<p class="errorlist">{error}</p>',
                label=gettext('Notify a fixed user'), error=e,
            )

        if not user.is_active:
            return format_html(
                '{label}<span class="warninglist">{warning}</span>',
                label=gettext('Notify:'),
                warning=gettext(
                    'The user «{username}» is disabled (no action will be performed)'
                ).format(username=user.username),
            )

        # TODO: link <a> to user/contact?
        return gettext('Notify: {user}').format(user=user)


# TODO: factorise with EntityFKSource?
class UserFKSource(UserSource):
    """A user with is read from a ForeignKey (to <User> of course)."""
    type_id = 'user_fk'
    verbose_name = _('User field')

    def __init__(self, *, entity_source, field_name):
        model = entity_source.model  # NB: can raise exception on BrokenSource
        try:
            field = model._meta.get_field(field_name)
        except FieldDoesNotExist:
            raise WorkflowBrokenData(
                gettext('The field «{field}» is invalid in model «{model}»').format(
                    field=field_name, model=model_verbose_name(model),
                )
            )

        if not isinstance(field, ForeignKey):
            raise WorkflowBrokenData(f'The field "{field_name}" is not a ForeignKey')
        if not issubclass(field.related_model, CremeUser):
            raise WorkflowBrokenData(
                f'The field "{field_name}" is not a ForeignKey to User'
            )

        self._entity_source = entity_source
        self._field_name = field_name
        self._field = field

    def __eq__(self, other):
        return (
            isinstance(other, type(self))
            and self._entity_source == other._entity_source
            and self._field_name == other._field_name
        )

    def __repr__(self):
        return (
            f'{type(self).__name__}('
            f'entity_source={self._entity_source!r}), '
            f'field_name="{self._field_name}"'
            f')'
        )

    @property
    def wf_source(self):
        return self._entity_source

    @property
    def field_name(self):
        return self._field_name

    @classmethod
    def config_formfield(cls, user, entity_source=None):
        from .forms.workflows import UserFKSourceField

        return None if entity_source is None else UserFKSourceField(
            label=gettext('Field to a user of: {source}').format(
                source=entity_source.render(user=user, mode=entity_source.RenderMode.HTML),
            ),
            entity_source=entity_source,
        )

    def extract(self, context):
        # TODO: errors
        instance = self._entity_source.extract(context=context)
        user = getattr(instance, self._field_name)

        return user if user and user.is_active else None

    @classmethod
    def from_dict(cls, data, registry):
        return cls(
            entity_source=registry.build_source(data['entity']),
            field_name=data['field'],
        )

    def to_dict(self):
        d = super().to_dict()
        d['entity'] = self._entity_source.to_dict()
        d['field'] = self._field_name

        return d

    def render(self, user):
        source = self._entity_source

        return gettext('Notify the user «{field}» of: {source}').format(
            field=self._field.verbose_name,
            source=source.render(user=user, mode=source.RenderMode.HTML),
        )


class BrokenUserSource(UserSource):
    """Represents a UserSource with an invalid configuration.
    It's useful to display errors in the UI.
    """
    def __init__(self, message):
        self._message = message

    @property
    def message(self):
        return self._message

    def render(self, user):
        return format_html(
            '<p class="errorlist">{message}</p>',
            message=self._message,
        )

    def extract(self, context):
        return None


class UserSourceRegistry:
    type_id_re = WorkflowRegistry.type_id_re

    class RegistrationError(Exception):
        pass

    class UnRegistrationError(RegistrationError):
        pass

    _user_source_classes: dict[str, type[UserSource]]

    def __init__(self, wf_registry=workflow_registry):
        self._user_source_classes = {}
        self._workflow_registry = wf_registry

    @property
    def user_source_classes(self):
        yield from self._user_source_classes.values()

    @classmethod
    def checked_type_id(cls, user_source_class):
        type_id = user_source_class.type_id

        if not type_id:
            raise cls.RegistrationError(
                f'This user-source class has an empty ID: {user_source_class}'
            )

        if cls.type_id_re.fullmatch(type_id) is None:
            raise cls.RegistrationError(
                f'This user-source class uses has an ID with invalid chars: '
                f'{user_source_class}'
            )

        return type_id

    def register(self,
                 *user_source_classes: type[UserSource],
                 ) -> UserSourceRegistry:
        set_cls = self._user_source_classes.setdefault

        for user_src_cls in user_source_classes:
            if set_cls(self.checked_type_id(user_src_cls), user_src_cls) is not user_src_cls:
                raise self.RegistrationError(
                    f'This user-source class uses an ID already used: {user_src_cls}'
                )

        return self

    def unregister(self,
                   *user_source_classes: type[UserSource],
                   ) -> UserSourceRegistry:
        for user_src_cls in user_source_classes:
            try:
                del self._user_source_classes[user_src_cls.type_id]
            except KeyError as e:
                raise self.UnRegistrationError(
                    f'This class is not registered: {user_src_cls}'
                ) from e

        return self

    def build_user_source(self, data: dict) -> UserSource:
        """Build any type of (registered) user-source from serialized data.
        @param See 'UserSource.to_dict()'.
        """
        type_id = data['type']
        user_src_cls = self._user_source_classes.get(type_id)
        if user_src_cls is None:
            return BrokenUserSource(
                message=gettext(
                    'The type of user-source «{type}» is invalid (uninstalled app?)'
                ).format(type=type_id),
            )

        try:
            user_source = user_src_cls.from_dict(
                data=data, registry=self._workflow_registry,
            )
        except WorkflowBrokenData as e:
            return BrokenUserSource(
                message=_(
                    'The user-source «{name}» is broken (original error: {error})'
                ).format(name=user_src_cls.verbose_name, error=e)
            )

        return user_source


user_source_registry = UserSourceRegistry().register(
    FixedUserSource,
    UserFKSource,
)


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


class NotificationSendingAction(WorkflowAction):
    """Action which sends a Notification"""  # TODO: complete
    type_id = 'creme_core-notification_sending'
    verbose_name = _('Sending a notification')

    def __init__(self, *,
                 channel: NotificationChannel,
                 user_source: UserSource,
                 entity_source: WorkflowSource,
                 subject: str,
                 body: str,
                 ):
        self._channel = channel
        self._user_source = user_source
        self._entity_source = entity_source
        self._subject = subject
        self._body = body

    def __eq__(self, other):
        return (
            isinstance(other, type(self))
            and self._channel == other._channel
            and self._user_source == other._user_source
            and self._entity_source == other._entity_source
            and self._subject == other._subject
            and self._body == other._body
        )

    def __repr__(self):
        return (
            f'{type(self).__name__}('
            f'channel={self._channel!r}, '
            # f'subject_source={self._subject_source!r}, '
            # f'rtype={self.relation_type!r}, '
            # f'object_source={self._object_source!r}'
            f')'
        )

    @classmethod
    def config_form_class(cls):
        from .forms.workflows import NotificationSendingActionForm
        return NotificationSendingActionForm

    @property
    def body(self) -> str:
        return self._body

    @property
    def channel(self) -> NotificationChannel:
        return self._channel

    @property
    def entity_source(self) -> WorkflowSource:
        return self._entity_source

    @property
    def user_source(self) -> UserSource:
        return self._user_source

    @property
    def subject(self) -> str:
        return self._subject

    def execute(self, context, user=None):
        user = self._user_source.extract(context)
        if not user:
            return

        entity = self._entity_source.extract(context)
        if entity is None:
            return None

        Notification.objects.send(
            channel=self._channel,
            users=[user],
            content=OneEntityTemplateStringContent.from_entity(
                subject=self._subject, body=self._body, entity=entity,
            ),
        )

    def to_dict(self):
        d = super().to_dict()
        d['channel'] = str(self._channel.uuid)
        d['user'] = self._user_source.to_dict()
        d['entity'] = self._entity_source.to_dict()
        d['subject'] = self._subject
        d['body'] = self._body

        return d

    @classmethod
    def from_dict(cls, data, registry):
        return cls(
            # TODO: localized error message
            channel=NotificationChannel.objects.get(uuid=data['channel']),
            user_source=user_source_registry.build_user_source(data['user']),
            entity_source=registry.build_source(data['entity']),
            subject=data['subject'],
            body=data['body'],
        )

    def render(self, user):
        return format_html(
            '<div>'
            '{label}'
            ' <ul>'
            '  <li>{channel}</li>'
            '  <li>{user}</li>'
            '  <li>{subject}</li>'
            '  <li>{body_label}<br><p>{body}</p></li>'
            ' </ul>'
            '</div>',
            label=gettext('Sending a notification:'),
            channel=gettext('On channel: {channel}').format(channel=self._channel),
            user=self._user_source.render(user=user),
            subject=gettext('Subject: {subject}').format(subject=self._subject),
            body_label=gettext('Body:'),
            body=self._body,
        )
