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

from django import forms
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.workflow import workflow_registry
from creme.creme_core.forms import CremeModelForm
from creme.creme_core.forms import fields as core_fields
from creme.creme_core.forms.widgets import CremeRadioSelect
from creme.creme_core.models import CremeEntity, Workflow


class _WorkflowWizardFormStep(CremeModelForm):
    class Meta:
        model = Workflow
        fields: tuple[str, ...] = ()


# Fields ------------------------------------------------------------------------
class TriggerField(core_fields.UnionField):
    # TODO: argument to pass workflow_registry
    def __init__(self, model=CremeEntity, **kwargs):
        super().__init__(**kwargs)
        self.model = model

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, model):
        self._model = model
        self.fields_choices = [
            (
                trigger_cls.type_id,
                trigger_cls.config_formfield(model=model)
            ) for trigger_cls in workflow_registry.trigger_classes
        ]


# Forms ------------------------------------------------------------------------
class TriggerStep(_WorkflowWizardFormStep):
    trigger = TriggerField(
        label=_('Trigger'),
        help_text=_('Which kind of event will trigger the workflow?'),
    )

    class Meta(_WorkflowWizardFormStep.Meta):
        fields = ('title',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['trigger'].model = self.instance.content_type.model_class()

    def clean(self):
        cdata = super().clean()

        if not self._errors:
            # [0] == trigger class ID
            self.instance.trigger = cdata['trigger'][1]

        return cdata


# TODO
class ConditionsStep(_WorkflowWizardFormStep):
    pass


class ActionTypeStep(_WorkflowWizardFormStep):
    action_type = forms.ChoiceField(
        label=_('Type of action'), widget=CremeRadioSelect,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['action_type'].choices = [
            (action_cls.type_id, action_cls.verbose_name)
            for action_cls in workflow_registry.action_classes
        ]


class WorkflowRenamingForm(CremeModelForm):
    class Meta:
        model = Workflow
        fields = ('title',)
