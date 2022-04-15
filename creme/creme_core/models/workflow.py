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

from django.db import models
# from django.utils.translation import pgettext_lazy
from django.utils.translation import gettext_lazy as _

from ..core.entity_filter import EntityFilterRegistry, condition_handler
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
    def smart_create(self, model, trigger, conditions=(), actions=()):
        return self.create(
            content_type=model,
            trigger=trigger,
            json_conditions=[
                {
                    'type': cond.type,
                    'name': cond.name,
                    'value': cond.value,
                } for cond in conditions
            ],
            json_actions=[action.to_dict() for action in actions],
        )


class Workflow(CremeModel):
    content_type = EntityCTypeForeignKey(verbose_name=_('Related resource'))
    json_trigger = models.JSONField(default=dict)
    json_conditions = models.JSONField(default=list)
    json_actions = models.JSONField(default=list)

    objects = WorkflowManager()

    # creation_label = pgettext_lazy('creme_core-workflow', 'Create a rule')
    # save_label = pgettext_lazy('creme_core-workflow', 'Save the rule')
    creation_label = _('Create a workflow')
    save_label = _('Save the workflow')

    # def __str__(self):
    #     return ...

    class Meta:
        app_label = 'creme_core'
        # verbose_name = pgettext_lazy('creme_core-workflow', 'Rule')
        # verbose_name_plural = pgettext_lazy('creme_core-workflow', 'Rules')
        verbose_name = ('Workflow')
        verbose_name_plural = _('Workflows')
        # ordering = ('id',)

    # TODO: cache
    @property
    def actions(self):
        from ..core.workflow import workflow_registry

        return [
            workflow_registry.build_action(data)
            for data in self.json_actions
        ]

    # TODO: cache
    @cached_property
    def conditions(self):
        from creme.creme_core.models import EntityFilterCondition  # TODO: move

        model = self.content_type.model_class()

        return [
            EntityFilterCondition(
                filter=None,
                filter_type=_registry.id,
                model=model,
                type=data['type'],
                name=data['name'],
                value=data['value'],
            ) for data in self.json_conditions
        ]

    # TODO?
    # def accept(self, entity: CremeEntity, user: CremeUser) -> bool:
    #     accepted = (
    #         condition.accept(entity=entity, user=user)
    #         for condition in self.get_conditions()
    #     )
    #
    #     return any(accepted) if self.use_or else all(accepted)

    # TODO: cache??
    @property
    def trigger(self):
        from ..core.workflow import workflow_registry

        return workflow_registry.build_trigger(self.json_trigger)

    @trigger.setter
    def trigger(self, value):
        self.json_trigger = value.to_dict()
