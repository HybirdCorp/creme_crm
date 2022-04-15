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

from functools import cached_property
from typing import Iterable
from uuid import uuid4

from django.db import models
# from django.utils.translation import pgettext_lazy
from django.utils.translation import gettext_lazy as _

from ..core.entity_filter import EntityFilterRegistry, condition_handler
from ..core.workflow import WorkflowAction, WorkflowTrigger, workflow_registry
from .base import CremeModel
from .fields import EntityCTypeForeignKey

# TODO: better name
# TODO: move to core? apps.py?
_registry = EntityFilterRegistry(
    id='creme_core-workflow',  # Not used
    verbose_name='Workflow conditions',  # Not used
).register_condition_handlers(
    condition_handler.RegularFieldConditionHandler,
    # condition_handler.DateRegularFieldConditionHandler,

    # condition_handler.CustomFieldConditionHandler,
    # condition_handler.DateCustomFieldConditionHandler,
    #
    # condition_handler.RelationConditionHandler,
    #
    # condition_handler.PropertyConditionHandler,

    # NOPE
    # RelationSubFilterConditionHandler,
    # SubFilterConditionHandler,
)
# .register_operators(
#     *operators.all_operators,
# ).register_operands(
#     *operands.all_operands,
# )


# TODO: static typing
class WorkflowManager(models.Manager):
    # TODO: or_update?
    # TODO: really useful? properties are not enough?
    def smart_create(self, *,
                     model, title, trigger,
                     uuid=None, is_custom=True, conditions=(), actions=(),
                     ):
        return self.create(
            title=title,
            uuid=uuid or uuid4(),
            content_type=model,
            is_custom=is_custom,
            trigger=trigger,
            json_conditions=[
                {
                    'type': cond.type,
                    'name': cond.name,
                    'value': cond.value,
                } for cond in conditions
            ],
            actions=actions,
        )


# TODO: doc
# TODO: static typing
class Workflow(CremeModel):
    title = models.CharField(verbose_name=_('Title'), max_length=100)
    uuid = models.UUIDField(unique=True, editable=False, default=uuid4)
    content_type = EntityCTypeForeignKey(verbose_name=_('Related resource'))
    json_trigger = models.JSONField(default=dict)
    json_conditions = models.JSONField(default=list)
    json_actions = models.JSONField(default=list)

    # A disabled Workflow won't be executed
    enabled = models.BooleanField(default=True, editable=False)
    # False => not editable/deletable
    is_custom = models.BooleanField(default=True, editable=False)

    objects = WorkflowManager()

    creation_label = _('Create a workflow')
    save_label = _('Save the workflow')

    _trigger = None
    _actions = None

    class Meta:
        app_label = 'creme_core'
        verbose_name = ('Workflow')
        verbose_name_plural = _('Workflows')
        # ordering = ('id',)

    def __str__(self):
        return self.title

    def __repr__(self):
        return (
            f'Workflow('
            f'title="{self.title}", '
            f'uuid="{self.uuid}", '
            f'content_type={self.content_type.model}, '
            f'json_trigger={self.json_trigger}, '
            f'json_actions={self.json_actions}'
            f')'
        )

    @property
    def actions(self) -> tuple[WorkflowAction, ...]:
        # NB: we use a tuple because the sequence is cached, so we prefer an immuable object
        actions  = self._actions
        if actions is None:
            self._actions = actions = tuple(
                workflow_registry.build_action(data)
                for data in self.json_actions
            )

        return actions

    @actions.setter
    def actions(self, value: Iterable[WorkflowAction]) -> None:
        self._actions = None
        self.json_actions = [action.to_dict() for action in value]

    # TODO: cache
    @cached_property
    def conditions(self):
        from creme.creme_core.models import EntityFilterCondition  # TODO: move

        model = self.content_type.model_class()

        return tuple(
            EntityFilterCondition(
                filter=None,
                filter_type=_registry.id,
                model=model,
                type=data['type'],
                name=data['name'],
                value=data['value'],
            ) for data in self.json_conditions
        )

    # TODO?
    # def accept(self, entity: CremeEntity, user: CremeUser) -> bool:
    #     accepted = (
    #         condition.accept(entity=entity, user=user)
    #         for condition in self.get_conditions()
    #     )
    #
    #     return any(accepted) if self.use_or else all(accepted)

    @property
    def trigger(self) -> WorkflowTrigger:
        trigger = self._trigger
        if trigger is None:
            self._trigger = trigger = workflow_registry.build_trigger(self.json_trigger)

        return trigger

    @trigger.setter
    def trigger(self, value: WorkflowTrigger) -> None:
        self._trigger = None
        self.json_trigger = value.to_dict()
