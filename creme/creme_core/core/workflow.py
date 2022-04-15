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

from typing import Iterator

from django.db.models import signals
from django.dispatch import receiver

from creme.creme_core.global_info import get_per_request_cache
from creme.creme_core.models import CremeEntity, Relation


# Events -----------------------------------------------------------------------
# TODO: __slots__
class WorkflowEvent:
    pass


# TODO: move to 'creme_core.workflows' ???
class EntityCreated(WorkflowEvent):
    def __init__(self, entity: CremeEntity):
        self._entity = entity

    def __repr__(self):
        return f'EntityCreated(entity={self._entity})'

    @property
    def entity(self) -> CremeEntity:
        return self._entity


# TODO: factorise
class EntityEdited(WorkflowEvent):
    def __init__(self, entity: CremeEntity):
        self._entity = entity

    def __repr__(self):
        return f'EntityEdited(entity={self._entity})'

    @property
    def entity(self) -> CremeEntity:
        return self._entity


class RelationAdded(WorkflowEvent):
    def __init__(self, relation: Relation):
        self._relation = relation

    def __repr__(self):
        return f'RelationAdded(relation={self._relation})'

    @property
    def relation(self) -> Relation:
        return self._relation


# TODO: doc-strings
class WorkflowEventQueue:
    cache_key = 'creme_core-workflows'

    def __init__(self):
        self._events = []

    def append(self, event: WorkflowEvent) -> WorkflowEventQueue:
        self._events.append(event)
        return self

    @classmethod
    def get_current(cls) -> WorkflowEventQueue:
        cache = get_per_request_cache()
        cache_key = cls.cache_key
        queue = cache.get(cache_key)
        if queue is None:
            queue = cache[cache_key] = cls()

        return queue

    def pickup(self) -> list[WorkflowEvent]:
        events = self._events
        self._events = []

        return events


# Signal handlers ---
@receiver(signals.pre_save, dispatch_uid='creme_core-push_workflow_event')
def _push_event(sender, instance, **kwargs):
    # TODO: other cases
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


# Triggers ---------------------------------------------------------------------
# TODO: doc-strings
class WorkflowTrigger:
    type_id = ''
    verbose_name = '??'

    def activate(self, event: WorkflowEvent) -> dict | None:
        raise NotImplementedError

    @classmethod
    def config_formfield(cls, model: CremeEntity):  # -> Field/ConfigField??:
        """ TODO: complete
        :param model:

        return EntityCreationTriggerField(
            model=model,
            label=cls.verbose_name,
        )
        """
        raise NotImplementedError

    @property
    def description(self) -> str:
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict) -> WorkflowTrigger:
        raise NotImplementedError

    def to_dict(self) -> dict:
        return {'type': self.type_id}


# Sources ----------------------------------------------------------------------
# TODO: doc-strings
class WorkflowActionSource:
    type_id = ''

    def extract(self, context: dict):
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict, registry: WorkflowRegistry) -> WorkflowActionSource:
        raise NotImplementedError

    def to_dict(self) -> dict:
        return {'type': self.type_id}


# Action -----------------------------------------------------------------------
# TODO: doc-strings
class WorkflowAction:
    type_id = ''
    verbose_name = '??'

    @classmethod
    # def config_formfield(cls, model: CremeEntity):  # -> Field/ConfigField??:
    def config_formfield(cls):  # -> Field/ConfigField??:
        # """ TODO: complete
        # :param model:
        #
        # return EntityCreationTriggerField(
        #     model=model,
        #     label=cls.verbose_name,
        # )
        # """
        raise NotImplementedError

    @property
    def description(self) -> str:
        raise NotImplementedError

    def execute(self, context: dict):
        raise NotImplementedError

    def to_dict(self) -> dict:
        return {'type': self.type_id}

    @classmethod
    def from_dict(cls, data: dict, registry: WorkflowRegistry) -> WorkflowAction:
        raise NotImplementedError


# Registry ---------------------------------------------------------------------
# TODO: static typing
# TODO: errors (empty id, duplicate, unknown id etc...)
# TODO: register filter (condition handler etc...) ?
class WorkflowRegistry:
    """TODO"""
    # TODO
    # class RegistrationError(Exception):
    #     pass

    def __init__(self):
        self._action_source_classes = {}
        self._action_classes = {}
        self._trigger_classes = {}

    # Actions ---
    @property
    def action_classes(self) -> Iterator[type[WorkflowAction]]:
        yield from self._action_classes.values()

    @property
    def action_source_classes(self) -> Iterator[type[WorkflowActionSource]]:
        yield from self._action_source_classes.values()

    # TODO: errors
    def build_action(self, data) -> WorkflowAction:
        return self._action_classes[data['type']].from_dict(data=data, registry=self)

    # TODO: errors
    def build_action_source(self, data: dict) -> WorkflowActionSource:
        return self._action_source_classes[data['type']].from_dict(data=data, registry=self)

    # TODO: errors
    def register_actions(self, *action_classes: type[WorkflowAction]) -> WorkflowRegistry:
        for action_class in action_classes:
            self._action_classes[action_class.type_id] = action_class

        return self

    # TODO: errors
    def register_action_sources(self,
                                *source_classes: type[WorkflowActionSource],
                                ) -> WorkflowRegistry:
        for src_class in source_classes:
            self._action_source_classes[src_class.type_id] = src_class

        return self

    # TODO: errors
    def unregister_actions(self,
                           *action_classes: type[WorkflowAction],
                           ) -> WorkflowRegistry:
        for action_class in action_classes:
            del self._action_classes[action_class.type_id]

        return self

    def unregister_action_sources(self,
                                  *source_classes: type[WorkflowActionSource],
                                  ) -> WorkflowRegistry:
        for src_class in source_classes:
            del self._action_source_classes[src_class.type_id]

        return self

    # Triggers ---
    @property
    def trigger_classes(self) -> Iterator[type[WorkflowTrigger]]:
        yield from self._trigger_classes.values()

    def build_trigger(self, data: dict) -> WorkflowTrigger:
        type_id = data['type']

        return self._trigger_classes[type_id].from_dict(data)

    # TODO: errors
    def register_triggers(self,
                          *trigger_classes: type[WorkflowTrigger],
                          ) -> WorkflowRegistry:
        for trigger_class in trigger_classes:
            self._trigger_classes[trigger_class.type_id] = trigger_class

        return self

    # TODO: errors
    def unregister_triggers(self,
                            *trigger_classes: type[WorkflowTrigger],
                            ) -> WorkflowRegistry:
        for trigger_class in trigger_classes:
            del self._trigger_classes[trigger_class.type_id]

        return self


workflow_registry = WorkflowRegistry()
