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

import re
from typing import TYPE_CHECKING, Iterable, Iterator

from django.db.models import signals
from django.dispatch import receiver
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext as _

from creme.creme_core.global_info import get_per_request_cache
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    EntityFilterCondition,
    Relation,
)

from .entity_filter import (
    EntityFilterRegistry,
    condition_handler,
    entity_filter_registries,
    operators,
)
from .snapshot import Snapshot

if TYPE_CHECKING:
    from django.forms import Field as FormField

    from creme.creme_core.forms.workflows import BaseWorkflowActionForm
    from creme.creme_core.models import CremeUser


# The Workflow engine allows users to configure some actions (like Relationship
# creation or email sending) which are made automatically in some conditions
# E.g: IF an instance of 'StuffEntity' is created, AND IF its field "status" is
#      <Very important>, THEN an email is sent to the owner of the new instance.


class WorkflowBrokenData(Exception):
    """Stored data which describe a Workflow is invalid."""
    pass


# Events -----------------------------------------------------------------------
# TODO: __slots__?
class WorkflowEvent:
    """Represents events like <a Contact has been created> or
    <an Activity has been modified>. These events are pushed to a queue (see
    WorkflowEventQueue) in order to be managed later.
    """
    pass


# TODO: move to 'creme_core.workflows' ???
class _EntityEvent(WorkflowEvent):
    """Event representing the creation of a CremeEntity instance."""
    def __init__(self, entity: CremeEntity):
        self._entity = entity

    def __eq__(self, other):
        return isinstance(other, type(self)) and self._entity.id == other._entity.id

    def __repr__(self):
        return f'{type(self).__name__}(entity={self._entity})'

    @property
    def entity(self) -> CremeEntity:
        return self._entity


class EntityCreated(_EntityEvent):
    """Event representing the creation of a CremeEntity instance."""


class EntityEdited(_EntityEvent):
    """Event representing the modification of a CremeEntity instance."""


class PropertyAdded(WorkflowEvent):
    """Event representing the creation of a CremeProperty instance."""
    def __init__(self, creme_property: CremeProperty):
        self._property = creme_property

    def __eq__(self, other):
        return isinstance(other, type(self)) and self._property.id == other._property.id

    def __repr__(self):
        return f'PropertyAdded(creme_property={self._property!r})'

    @property
    def creme_property(self) -> CremeProperty:
        return self._property


class RelationAdded(WorkflowEvent):
    """Event representing the creation of a Relation instance."""
    def __init__(self, relation: Relation):
        self._relation = relation

    def __eq__(self, other):
        return isinstance(other, type(self)) and self._relation.id == other._relation.id

    def __repr__(self):
        return f'RelationAdded(relation={self._relation})'

    @property
    def relation(self) -> Relation:
        return self._relation


class WorkflowEventQueue:
    """Queue containing instances of WorkflowEvent.
    The idea is to create & push the instances in signal handlers, and manage
    (i.e. apply WorkflowActions) the events later (i.e. when the response is built),
    with a middleware (see 'creme_core.middleware.workflow.WorkflowMiddleware').
    """
    cache_key = 'creme_core-workflows'

    def __init__(self):
        self._events = []

    def append(self, event: WorkflowEvent) -> WorkflowEventQueue:
        """Append a new event IF NOT ALREADY HERE."""
        events = self._events
        if event not in events:
            events.append(event)

        return self

    @classmethod
    def get_current(cls) -> WorkflowEventQueue:
        """Get the instance of queue corresponding to the current HTTP request.
        The instance is stored in the request cache (so we are sure to get a
        unique instance of queue for the request).
        """
        cache = get_per_request_cache()
        cache_key = cls.cache_key
        queue = cache.get(cache_key)
        if queue is None:
            queue = cache[cache_key] = cls()

        return queue

    def pickup(self) -> list[WorkflowEvent]:
        """Retrieve all contained events as a list & empty the queue.
        Useful to treat events & avoid recursion issues.
        """
        events = self._events
        self._events = []

        return events


# Signal handlers ---
@receiver(signals.pre_save, dispatch_uid='creme_core-push_workflow_event')
def _push_event(sender, instance, **kwargs):
    """Fills the event queue."""
    if isinstance(instance, CremeEntity):
        WorkflowEventQueue.get_current().append(
            EntityEdited(entity=instance)
            if instance.pk else
            EntityCreated(entity=instance)
        )
    elif isinstance(instance, Relation):
        # TODO: should we only record the main side of the relationship as optimization?
        # NB: we check the pk to avoid duplicated event caused by double save()
        #     (reciprocal FKs)
        if not instance.pk:
            WorkflowEventQueue.get_current().append(RelationAdded(relation=instance))
    elif isinstance(instance, CremeProperty):
        WorkflowEventQueue.get_current().append(PropertyAdded(creme_property=instance))


# Triggers ---------------------------------------------------------------------
class WorkflowTrigger:
    """Part of a workflow containing the kind of WorkflowEvent which
    triggers this workflow (e.g. the workflow is triggered when a Contact is created).
    """
    # Must be unique by class; used by the registry for deserialize from the database.
    type_id = ''
    verbose_name = '??'

    # NB: override in child classes
    event_class = WorkflowEvent

    # Behaviour of the related WorkflowConditions:
    conditions_use_or = False  # accept()'s "use_or" argument
    conditions_detect_change = False  # accept()'s "detect_change" argument

    def _activate(self, event: WorkflowEvent) -> dict | None:
        """See 'activate()'."""
        raise NotImplementedError

    def activate(self, event: WorkflowEvent) -> dict | None:
        """Indicates if the workflow is triggered and build the context to be
        used by other partys of the workflows.
        @return <None> if the workflow is not triggered.
                The context (a dictionary) if the workflow is triggered; it
                contains WorkflowSource instance(s).

        BEWARE: see the method 'root_sources()' too.
        """
        return self._activate(event) if isinstance(event, self.event_class) else None

    @classmethod
    def config_formfield(cls, model: type[CremeEntity]) -> FormField:
        """Returns a form field which builds an instance of this trigger class.
        This field will be aggregated by 'creme_config.forms.workflow.TriggerField'
        in order to be used to configure the trigger part of the Workflow.

        @param model: Model corresponding to the 'creme_core.models.WorkFlow' instance.
        @return A field which 'clean()' method builds an instance of 'WorkflowTrigger'.
        """
        raise NotImplementedError

    @property
    def description(self) -> str:
        """A localized human-friendly string used in the configuration brick."""
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict) -> WorkflowTrigger:
        """Builds an instance from a dictionary (produced by the method 'to_dict()').
        @raise WorkflowBrokenData.
        """
        raise NotImplementedError

    def to_dict(self) -> dict:
        """Serialize into a JSON-friendly dictionary (which can be stored in database)."""
        return {'type': self.type_id}

    def root_sources(self) -> list[WorkflowSource]:
        """A trigger produces at least one source (i.e. an instance of
        'CremeEntity' to act on).
        BEWARE: these sources must correspond to the entities injected in the
                context by the method 'activate()'.
        """
        raise NotImplementedError


class BrokenTrigger(WorkflowTrigger):
    def __init__(self, message: str):
        self._message = message

    @property
    def message(self):
        return self._message

    def activate(self, event):
        # TODO: log?
        return None

    @property
    def description(self):
        return format_html(
            '<p class="errorlist">{message}</p>', message=self.message,
        )


# Sources ----------------------------------------------------------------------
class WorkflowSource:
    """A Source can retrieve a CremeEntity instance related to the current Trigger.
    - The conditions of the Workflow can check this entity (to know if the
      Actions have to be performed).
    - The Actions of the Workflow can use it to perform their work.

    Some sources can extract their CremeEntity instance directly from the context
    generated by an activated Trigger; we call them the 'root' sources.
     E.g.: the trigger 'creme_core.workflows.EntityCreationTrigger' creates a
           context containing the created instance; then the source
           'creme_core.workflows.CreatedEntitySource' can extract this instance
           from the context (so the concerned WorkflowAction can use it).
    Note that conditions are only checking these root sources.

    Some sources can retrieve their CremeEntity instance directly from the DB;
    they do not use the context generated by the trigger, directly or through a
    sub-source. We call them 'standalone' sources.
     E.g.: 'creme_core.workflows.FixedEntitySource' retrieves its entity by its uuid.

    Some sources need another source to provide a CremeEntity instance.
     E.g.: 'creme_core.workflows.EntityFKSource' needs a CremeEntity with a
           ForeignKey referencing another CremeEntity instance.
    """
    # Must be unique by class; used by the registry for deserialize from the database.
    type_id = ''
    # Description of the type (used for error).
    # Hint: use 'render()' to get a description of an instance.
    verbose_name = '??'

    # TODO: Enum
    TEXT_PLAIN = 1
    HTML = 2

    @classmethod
    def standalone_config_formfield(cls, user: CremeUser) -> FormField | None:
        """Returns a form field which builds an instance of this source class
        when it's a standalone source.
        This field will be aggregated by 'creme_config.forms.workflow.SourceField'
        in order to be used to configure the action part of the Workflow.

        @return A field which 'clean()' method builds an instance of
                'WorkflowSource', or None for not standalone sources.
        """
        return None

    @classmethod
    def composed_config_formfield(cls,
                                  sub_source: WorkflowSource,
                                  user: CremeUser,
                                  ) -> FormField | None:
        """Returns a form field which builds an instance of this source class
        when it needs a sub-source (not a root or a standalone source).
        This field will be aggregated by 'creme_config.forms.workflow.SourceField'
        in order to be used to configure the action part of the Workflow.

        @return A field which 'clean()' method builds an instance of
                'WorkflowSource' it this kind of source uses another sub-source.
                None for root/standalone sources.
        """
        return None

    def config_formfield(self, user: CremeUser) -> FormField:
        """Returns a form field which builds an instance of this source class.
        This field will be aggregated by 'creme_config.forms.workflow.SourceField'
        in order to be used to configure the action part of the Workflow.

        It works only with source classes designed to be root source; see the
        method 'composed_config_formfield()' for types of source needing another
        sub-source.

        @return A field which 'clean()' method builds an instance of
               'WorkflowSource'.
        @raise A ValueError if this not a root source.
        """
        raise ValueError('This type of source cannot be used as root source')

    @classmethod
    def config_formfield_kind_id(cls, sub_source: WorkflowSource | None = None) -> str:
        """Generate an ID for the related configuration form-field.
        This ID is used by 'creme_core.forms.workflows.SourceField' to
        distinguish the different kinds of source.
        Hint: you probably don't have to override this method in child classes.
        @parameter sub_source: Should the same sub-source used by the field itself.
        """
        return (
            cls.type_id
            if sub_source is None else
            f'{sub_source.config_formfield_kind_id()}|{cls.type_id}'
        )

    def extract(self, context: dict) -> CremeEntity | None:
        """Extract a CremeEntity from the context (generated by the trigger).
        @return A CremeEntity instance, or <None> (e.g. the used FK is 'null').
        """
        raise NotImplementedError

    @property
    def model(self) -> type[CremeEntity]:
        """Indicates what kind of entity the source will extract.
        It's important because the conditions & actions can need to know the model
        (e.g. they use a specific model field).
        """
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict, registry: WorkflowRegistry) -> WorkflowSource:
        """Builds an instance from a dictionary (produced by the method 'to_dict()').
        The registry is useful to build the 'non-root' sources.
        """
        raise NotImplementedError

    def to_dict(self) -> dict:
        """Serialize into a JSON-friendly dictionary (which can be stored in database)."""
        return {'type': self.type_id}

    # TODO: better type for 'mode'
    def render(self, user: CremeUser, mode: int) -> str:
        """Render a string (plain text or HTML) which can be used to describe
        the source to the users.
        Plain text is used in configuration form-fields.
        HTML is used in configuration brick.
        """
        raise NotImplementedError

    @property
    def sub_source(self) -> WorkflowSource | None:
        """Some source classes extract their entities from another source.
        E.g.: creme_core.workflows.EntityFKSource
        @return: The sub-source, or 'None' if no sub-source is used.
        """
        return None


class BrokenSource(WorkflowSource):
    def __init__(self, message):
        self._message = message

    @property
    def message(self):
        return self._message

    def extract(self, context):
        return None

    @property
    def model(self):
        raise WorkflowBrokenData(self._message)

    def render(self, user, mode):
        match mode:
            case self.HTML:
                return format_html(
                    '<p class="errorlist">{message}</p>',
                    message=self._message,
                )

            case self.TEXT_PLAIN:
                return _('Error ({message})').format(message=self._message)

            case _:
                raise ValueError()


# Conditions ----------------------------------------------------------------------
wf_efilter_registry = EntityFilterRegistry(
    id='creme_core-workflow',  # Not used
    verbose_name='Workflow conditions',  # Not used
).register_condition_handlers(
    condition_handler.RegularFieldConditionHandler,
    condition_handler.DateRegularFieldConditionHandler,

    condition_handler.CustomFieldConditionHandler,
    condition_handler.DateCustomFieldConditionHandler,

    # TODO?
    # condition_handler.RelationConditionHandler,
    # condition_handler.PropertyConditionHandler,

    # NOPE
    # RelationSubFilterConditionHandler,
    # SubFilterConditionHandler,
).register_operators(
    *operators.all_operators,
)
# TODO?
# .register_operands(
#     *operands.all_operands,
# )

# TODO: move to apps.py?
entity_filter_registries.register(wf_efilter_registry)


# TODO: docstring
class WorkflowConditions:
    _conditions_per_source: list[dict]

    class _Builder:
        def __init__(self, source, conditions):
            self._conditions_per_source = []
            self._add_conditions(source=source, conditions=conditions)

        def _add_conditions(self, source, conditions):
            # TODO: inner dataclass instead of dict?
            # TODO: merge for same source
            self._conditions_per_source.append({
                'entity': source, 'conditions': conditions,
            })

        def build(self, source, conditions):
            # TODO: copy conditions?
            self._add_conditions(source, conditions)

            return self

        def do(self):
            conds = WorkflowConditions()
            conds._conditions_per_source = self._conditions_per_source

            # TODO: make the builder invalid VS deepcopy
            return conds

    @classmethod
    def build(cls,
              source: WorkflowSource,
              conditions: list[EntityFilterCondition],
              ) -> _Builder:
        return cls._Builder(source, conditions)

    @classmethod
    def from_dicts(cls, data: list[dict], registry: WorkflowRegistry) -> WorkflowConditions:
        instance = cls()
        instance._conditions_per_source = conditions_per_source = []

        for d in data:
            source = registry.build_source(d['entity'])
            conditions_per_source.append({
                'entity': source,
                'conditions': [
                    EntityFilterCondition(
                        filter=None,
                        filter_type=wf_efilter_registry.id,
                        model=source.model,
                        type=data['type'],
                        name=data['name'],
                        value=data['value'],
                    ) for data in d['conditions']
                ],
            })

        return instance

    def accept(self, *, user: CremeUser, context: dict, detect_change: bool, use_or: bool) -> bool:
        def accepted():
            for source_conditions in self._conditions_per_source:
                entity = source_conditions['entity'].extract(context)

                if detect_change:
                    snapshot = Snapshot.get_for_instance(entity)
                    if snapshot is None:
                        raise ValueError(
                            'The "detect_edition" mode work only with edited entities'
                        )

                    previous = snapshot.get_initial_instance()

                    for condition in source_conditions['conditions']:
                        yield (
                            condition.accept(entity=entity, user=user)
                            and not condition.accept(entity=previous, user=user)
                        )
                else:
                    for condition in source_conditions['conditions']:
                        yield condition.accept(entity=entity, user=user)

        if use_or:
            # NB: 'any()' returns 'False' on empty sequences
            empty = True
            for cond_accepted in accepted():
                empty = False
                if cond_accepted:
                    return True

            return empty

        return all(accepted())

    def descriptions(self, user: CremeUser) -> Iterator[str]:
        for source_conditions in self._conditions_per_source:
            source: WorkflowSource = source_conditions['entity']
            rendered_source = source.render(user=user, mode=source.HTML)

            conditions = source_conditions['conditions']
            if conditions:
                yield format_html(
                    '{label}<ul>{conditions}</ul>',
                    label=_('Conditions on «{source}»:').format(
                        source=rendered_source,
                    ),
                    conditions=format_html_join(
                        '', '<li>{}</li>',
                        ([condition.description(user=user)] for condition in conditions)
                    ),
                )
            else:
                yield _('No condition on «{source}»').format(source=rendered_source)

    def to_dicts(self) -> list[dict]:
        return [
            {
                'entity': source_conditions['entity'].to_dict(),
                'conditions': [
                    {
                        'type': condition.type,
                        'name': condition.name,
                        'value': condition.value,
                    } for condition in source_conditions['conditions']
                ],
            } for source_conditions in self._conditions_per_source
        ]


# Action -----------------------------------------------------------------------
class WorkflowAction:
    """Part of a Workflow with performs "concrete" things (adds CremeProperties,
    sends emails etc...).
    """
    # Must be unique by class; used by the registry for deserialize from the database.
    type_id = ''
    verbose_name = '??'

    def __str__(self):
        return str(self.verbose_name)

    @classmethod
    def config_form_class(cls) -> BaseWorkflowActionForm:
        """Returns a configuration form for this kind of action."""
        raise NotImplementedError

    def execute(self, context: dict):
        """Perform the action (add RelationShips etc...).
        @param context: The context generated by the trigger of the concerned Workflow.
        """
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict, registry: WorkflowRegistry) -> WorkflowAction:
        """Builds an instance from a dictionary (produced by the method 'to_dict()').
        The registry is useful to build the 'non-root' sources.
        """
        raise NotImplementedError

    def to_dict(self) -> dict:
        """Serialize into a JSON-friendly dictionary (which can be stored in database)."""
        return {'type': self.type_id}

    # TODO: TEXT_PLAIN mode VS remove TEXT_PLAIN mode in source.render()?
    def render(self, user) -> str:
        """Render as an HTML string which can be used to describe the source to
        the users.
        """
        raise NotImplementedError


class BrokenAction(WorkflowAction):
    def __init__(self, message):
        self._message = message

    @property
    def message(self):
        return self._message

    def execute(self, context):
        # TODO: log?
        pass

    def render(self, user):
        return format_html(
            '<p class="errorlist">{message}</p>', message=self.message,
        )


# Registry ---------------------------------------------------------------------
# TODO: docstrings
# TODO: errors (empty id, duplicate, unknown id etc...)
# TODO: register filter (condition handler etc...)?
class WorkflowRegistry:
    """Registry related to these aspects of the Workflow engine:
     - triggers
     - sources
     - actions
     TODO: complete (conditions? other?)
    """
    type_id_re = re.compile(r'[A-Za-z0-9_-]*')  # TODO: in utils?

    class RegistrationError(Exception):
        pass

    class UnRegistrationError(RegistrationError):
        pass

    def __init__(self):
        self._source_classes: dict[str, type[WorkflowSource]] = {}
        self._action_classes: dict[str, type[WorkflowAction]] = {}
        self._trigger_classes: dict[str, type[WorkflowTrigger]] = {}

    @classmethod
    def checked_type_id(cls, registrable_cls):
        type_id = registrable_cls.type_id

        if not type_id:
            raise cls.RegistrationError(
                f'This class has an empty ID: {registrable_cls}'
            )

        if cls.type_id_re.fullmatch(type_id) is None:
            raise cls.RegistrationError(
                f'This class uses has an ID with invalid chars: {registrable_cls}'
            )

        return type_id

    # Actions ---
    def get_action_class(self, type_id: str) -> type[WorkflowAction] | None:
        return self._action_classes.get(type_id)

    @property
    def action_classes(self) -> Iterator[type[WorkflowAction]]:
        yield from self._action_classes.values()

    def build_action(self, data: dict) -> WorkflowAction:
        type_id = data['type']
        action_cls = self._action_classes.get(type_id)
        if action_cls is None:
            return BrokenAction(
                message=_(
                    'The type of action «{type}» is invalid (badly uninstalled app?)'
                ).format(type=type_id),
            )

        try:
            action = action_cls.from_dict(data=data, registry=self)
        except Exception as e:
            action = BrokenAction(
                message=_(
                    'The action «{name}» is broken (original error: {error})'
                ).format(name=action_cls.verbose_name, error=e),
            )

        return action

    def register_actions(self, *action_classes: type[WorkflowAction]) -> WorkflowRegistry:
        set_action = self._action_classes.setdefault

        for action_cls in action_classes:
            if set_action(self.checked_type_id(action_cls), action_cls) is not action_cls:
                raise self.RegistrationError(
                    f'This action class uses a duplicated ID: {action_cls}'
                )

        return self

    def unregister_actions(self,
                           *action_classes: type[WorkflowAction],
                           ) -> WorkflowRegistry:
        for action_cls in action_classes:
            try:
                del self._action_classes[action_cls.type_id]
            except KeyError as e:
                raise self.UnRegistrationError(
                    f'This action class is not registered: {action_cls}'
                ) from e

        return self

    # Sources ---
    @property
    def source_classes(self) -> Iterator[type[WorkflowSource]]:
        yield from self._source_classes.values()

    def source_formfields(self,
                          root_sources: Iterable[WorkflowSource],
                          user: CremeUser,
                          ) -> list[tuple[str, FormField]]:
        # TODO: check that root source classes are registered?
        fields = [
            (source.config_formfield_kind_id(), source.config_formfield(user=user))
            for source in root_sources
        ]

        for source_cls in self._source_classes.values():
            field = source_cls.standalone_config_formfield(user=user)
            if field is not None:
                fields.append((source_cls.config_formfield_kind_id(), field))

        for sub_source in root_sources:
            for source_cls in self._source_classes.values():
                field = source_cls.composed_config_formfield(
                    sub_source=sub_source, user=user,
                )
                if field is not None:
                    fields.append((
                        source_cls.config_formfield_kind_id(sub_source=sub_source),
                        field,
                    ))

        return fields

    def build_source(self, data: dict) -> WorkflowSource:
        type_id = data['type']
        source_cls = self._source_classes.get(type_id)
        if source_cls is None:
            return BrokenSource(
                message=_(
                    'The type of source «{type}» is invalid (badly uninstalled app?)'
                ).format(type=type_id),
            )

        try:
            source = source_cls.from_dict(data=data, registry=self)
        except Exception as e:
            source = BrokenSource(
                message=_(
                    'The source «{name}» is broken (original error: {error})'
                ).format(name=source_cls.verbose_name, error=e),
            )

        return source

    def register_sources(self,
                         *source_classes: type[WorkflowSource],
                         ) -> WorkflowRegistry:
        set_source = self._source_classes.setdefault

        for source_cls in source_classes:
            if set_source(self.checked_type_id(source_cls), source_cls) is not source_cls:
                raise self.RegistrationError(
                    f'This source class uses a duplicated ID: {source_cls}'
                )

        return self

    def unregister_sources(self,
                           *source_classes: type[WorkflowSource],
                           ) -> WorkflowRegistry:
        for source_cls in source_classes:
            try:
                del self._source_classes[source_cls.type_id]
            except KeyError as e:
                raise self.UnRegistrationError(
                    f'This source class is not registered: {source_cls}'
                ) from e

        return self

    # Triggers ---
    @property
    def trigger_classes(self) -> Iterator[type[WorkflowTrigger]]:
        yield from self._trigger_classes.values()

    def build_trigger(self, data: dict) -> WorkflowTrigger:
        type_id = data['type']
        trigger_cls = self._trigger_classes.get(type_id)
        if trigger_cls is None:
            return BrokenTrigger(
                message=_(
                    'The type of trigger «{type}» is invalid (badly uninstalled app?)'
                ).format(type=type_id),
            )

        try:
            trigger = trigger_cls.from_dict(data)
        except Exception as e:
            trigger = BrokenTrigger(
                message=_(
                    'The trigger «{name}» is broken (original error: {error})'
                ).format(name=trigger_cls.verbose_name, error=e),
            )

        return trigger

    def register_triggers(self,
                          *trigger_classes: type[WorkflowTrigger],
                          ) -> WorkflowRegistry:
        set_trigger = self._trigger_classes.setdefault

        for trigger_cls in trigger_classes:
            if set_trigger(self.checked_type_id(trigger_cls), trigger_cls) is not trigger_cls:
                raise self.RegistrationError(
                    f'This trigger class uses a duplicated ID: {trigger_cls}'
                )

        return self

    def unregister_triggers(self,
                            *trigger_classes: type[WorkflowTrigger],
                            ) -> WorkflowRegistry:
        for trigger_cls in trigger_classes:
            try:
                del self._trigger_classes[trigger_cls.type_id]
            except KeyError as e:
                raise self.UnRegistrationError(
                    f'This trigger class is not registered: {trigger_cls}'
                ) from e

        return self


workflow_registry = WorkflowRegistry()
