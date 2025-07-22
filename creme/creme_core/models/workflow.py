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

from collections.abc import Iterable
from uuid import uuid4

from django.db import models
from django.utils.translation import gettext_lazy as _

from ..core.workflow import (
    WorkflowAction,
    WorkflowConditions,
    WorkflowTrigger,
    workflow_registry,
)
from .base import CremeModel
from .fields import EntityCTypeForeignKey


class Workflow(CremeModel):
    """A Workflow stores actions (like sending emails or creating Relation)
    which are automatically performed:
     - when some event happened (see core.workflow.WorkflowEvent & WorkflowTrigger).
     - if some conditions are filler (see core.workflow.WorkflowConditions).

    Workflows can be created by user in creme_config & so avoid to write code.
    Workflows can be disabled, which is useful for some default behaviours which
    are populated in vanilla installation.
    """
    title = models.CharField(verbose_name=_('Title'), max_length=100)
    uuid = models.UUIDField(unique=True, editable=False, default=uuid4)
    content_type = EntityCTypeForeignKey(verbose_name=_('Related resource'))

    # NB: use the getter/setter instead of these raw fields.
    json_trigger = models.JSONField(default=dict)
    json_conditions = models.JSONField(default=list)
    json_actions = models.JSONField(default=list)

    # A disabled Workflow won't be executed
    enabled = models.BooleanField(default=True, editable=False)
    # False => not editable/deletable
    is_custom = models.BooleanField(default=True, editable=False)

    creation_label = _('Create a Workflow')
    save_label = _('Save the Workflow')

    # Caches (don't touch this)
    _trigger = None
    _actions = None
    _conditions = None

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
            f'json_conditions={self.json_conditions}, '
            f'json_actions={self.json_actions}'
            f')'
        )

    @property
    def actions(self) -> tuple[WorkflowAction, ...]:
        # NB: we use a tuple because the sequence is cached, so we prefer an immuable object
        actions = self._actions
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

    @property
    def conditions(self) -> WorkflowConditions:
        conditions = self._conditions
        if conditions is None:
            self._conditions = conditions = WorkflowConditions.from_dicts(
                data=self.json_conditions, registry=workflow_registry,
            )

        return conditions

    @conditions.setter
    def conditions(self, value: WorkflowConditions) -> None:
        self._conditions = None
        self.json_conditions = value.to_dicts()

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
